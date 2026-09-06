#!/usr/bin/env python3
"""Fair fixed-budget baselines for the AdsQA innovation-1 experiments.

This is a new entrypoint. It does not overwrite or redefine historical runs.
Raw, CLIP single-peak, and AdSlot modes share the same Qwen input path, prompt,
32-view budget, visual-token guard, and no-RAG/no-reflection protocol.
"""

import os
import sys
import json
import time
import gc
import shutil
import argparse
import hashlib
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Avoid torchcodec compatibility surprises seen in some remote envs.
sys.modules["torchcodec"] = None

_EARLY_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_EARLY_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EARLY_PROJECT_ROOT))
from evaluation.methods.common.adsqa_prompt import (  # noqa: E402
    ADSQA_ANSWER_PROMPT_VERSION,
    adsqa_answer_prompt_sha256,
    build_adsqa_answer_prompt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AdsQA fair fixed-budget baselines V1")

    # Runtime / sharding
    parser.add_argument("--gpu_id", type=str, required=True, help="Physical GPU id, e.g. 0")
    parser.add_argument("--shard_id", type=int, default=0, help="Current shard id")
    parser.add_argument("--num_shards", type=int, default=1, help="Total number of shards")
    parser.add_argument("--start_idx", type=int, default=0, help="Start index in question file")
    parser.add_argument("--end_idx", type=int, default=-1, help="End index, -1 means all")
    parser.add_argument("--seed", type=int, default=42)

    # Paths
    parser.add_argument("--project_root", type=str, default="/data1/rmx/projectb/AdsQA-main")
    parser.add_argument("--model_dir", type=str, default="/data1/qky/Model/Qwen3Vl-8B")
    parser.add_argument("--model_label", type=str, default="", help="Explicit model label for logs and per-question provenance")
    parser.add_argument("--clip_path", type=str, default="/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14")
    parser.add_argument("--video_root", type=str, default="/data1/rmx/projectb/AdsQA-main/data/videos")
    parser.add_argument("--frames_fallback_root", type=str, default="/data1/rmx/projectb/AdsQA-main/data/frames_8", help="Fallback pre-extracted frame root when video/decord is unavailable")
    parser.add_argument("--question_file", type=str, default="/data1/rmx/projectb/AdsQA-main/data/testset_question.json")
    parser.add_argument("--groundtruth_file", type=str, default="/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json")
    parser.add_argument("--asr_file", type=str, default="/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json")
    parser.add_argument("--output_dir", type=str, default="/data1/rmx/projectb/AdsQA-main/evaluation/runs/fair_baseline_v1")

    # RAG / external marketing knowledge
    parser.add_argument("--rag_mode", choices=["none", "lexical", "embedding", "hybrid"], default="none", help="External marketing RAG mode")
    parser.add_argument("--rag_kb", type=str, default="/data1/rmx/projectb/AdsQA-main/evaluation/rag/marketing_kb_curated.json")
    parser.add_argument("--rag_index", type=str, default="/data1/rmx/projectb/AdsQA-main/evaluation/rag/marketing_kb_minilm.index.npz")
    parser.add_argument("--rag_model", type=str, default="/data1/rmx/projectb/AdsQA-main/models/all-MiniLM-L6-v2")
    parser.add_argument("--rag_topk", type=int, default=3)
    parser.add_argument("--rag_device", type=str, default="cpu")
    parser.add_argument("--rag_dense_weight", type=float, default=0.65, help="Dense embedding weight for hybrid RAG")
    parser.add_argument("--rag_lexical_weight", type=float, default=0.35, help="Lexical weight for hybrid RAG")
    parser.add_argument("--rag_backend", type=str, default="sentence_transformer", help="Retriever backend label for tracing")
    parser.add_argument("--rag_require_index", action="store_true", help="Require embedding index for embedding/hybrid RAG")
    parser.add_argument("--rag_disable_types", nargs="*", default=[], help="Question route primary types for which RAG is disabled")
    parser.add_argument("--rag_v2", action="store_true", help="Enable question-aware gated/reranked RAG v2")
    parser.add_argument("--rag_candidate_k", type=int, default=8, help="Candidate pool size before RAG v2 reranking")
    parser.add_argument("--strict_no_leak", action="store_true", help="Block RAG entries that may leak current test answer/video")

    # Existing result policy
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing prediction/evidence files")
    parser.add_argument("--previous_output_dir", type=str, default="", help="Optional previous result dir")
    parser.add_argument(
        "--previous_mode",
        choices=["ignore", "skip", "copy"],
        default="ignore",
        help="How to handle existing previous_output_dir/qid/prediction.json. Default ignore for clean experiments.",
    )

    # Evidence pipeline
    parser.add_argument(
        "--fair_method",
        choices=["raw_uniform", "clip_singlepeak", "adslot_fixed", "coverage_adslot", "external_temporal"],
        default="raw_uniform",
    )
    parser.add_argument(
        "--temporal_index_cache",
        type=str,
        default="",
        help="VideoITG/self-selector JSONL file or sharded JSONL directory",
    )
    parser.add_argument("--visual_view_budget", type=int, default=32)
    parser.add_argument("--max_post_merge_visual_tokens", type=int, default=12000)
    parser.add_argument("--metadata_fps", type=float, default=1.0)
    parser.add_argument("--oversample_count", type=int, default=32)
    parser.add_argument("--top_k_frames", type=int, default=16)
    parser.add_argument("--unified_size", type=int, default=896, help="Square resize for global/local frames")
    parser.add_argument("--crop_scales", type=float, nargs="*", default=[0.6, 0.8, 1.0])
    parser.add_argument("--question_weight", type=float, default=0.5)
    parser.add_argument("--audio_weight", type=float, default=0.3)
    parser.add_argument("--ocr_weight", type=float, default=0.2)
    parser.add_argument("--select_question_weight", type=float, default=0.6)
    parser.add_argument("--select_audio_weight", type=float, default=0.4)
    parser.add_argument("--adslot_mode", choices=["off", "on"], default="on", help="Enable ad evidence slot routing and slot-adaptive input reconstruction")
    parser.add_argument("--adslot_min_top_k", type=int, default=16, help="Minimum global frames kept under the fixed total budget")
    parser.add_argument("--adslot_max_top_k", type=int, default=20, help="Maximum frames kept after slot-adaptive budget")

    # Generation / prompt
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--reflection_max_new_tokens", type=int, default=512)
    parser.add_argument("--disable_reflection", action="store_true")
    parser.add_argument(
        "--reflection_triggers",
        nargs="*",
        default=["text", "say", "number", "logo", "url", "why", "reason", "logic"],
    )
    parser.add_argument("--save_prompts", action="store_true", help="Save full prompts in evidence.json")
    parser.add_argument("--save_evidence_images", action="store_true", help="Save selected global/local evidence jpgs; storage-heavy")
    parser.add_argument("--dry_run", action="store_true", help="Only inspect data/sharding; do not load models or generate")

    parser.set_defaults(disable_reflection=True)

    return parser.parse_args()


args = parse_args()
args.disable_reflection = True
args.adslot_mode = "on" if args.fair_method in {"adslot_fixed", "coverage_adslot"} else "off"

# Must be set before importing torch/transformers.
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
print(f"[System] CUDA_VISIBLE_DEVICES={args.gpu_id}")


def run_early_dry_run() -> None:
    if args.rag_mode != "none" or args.rag_v2:
        raise ValueError("fair protocol V1 requires RAG to be disabled")
    if args.visual_view_budget <= 0 or args.max_post_merge_visual_tokens <= 0:
        raise ValueError("fair protocol budgets must be positive")
    if args.oversample_count < args.visual_view_budget:
        raise ValueError("oversample_count must be at least visual_view_budget")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    end_idx = len(questions) if args.end_idx < 0 else min(args.end_idx, len(questions))
    start_idx = max(0, args.start_idx)
    indexed = list(enumerate(questions[start_idx:end_idx], start=start_idx))
    shard_items = [(index, item) for index, item in indexed if index % args.num_shards == args.shard_id]
    preview = []
    for index, item in shard_items[:10]:
        qid = str(item["question_id"])
        video_id = str(item.get("video", item.get("video_id", qid.split("_")[0])))
        candidates = [
            Path(args.video_root) / f"{video_id}.mp4",
            Path(args.video_root) / video_id,
            Path(args.video_root) / f"{video_id}.webm",
            Path(args.video_root) / f"{video_id}.mov",
            Path(args.frames_fallback_root) / video_id,
        ]
        video_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        preview.append({
            "global_idx": index,
            "question_id": qid,
            "video_id": video_id,
            "video_path": str(video_path),
            "video_path_exists": video_path.exists(),
            "fair_method": args.fair_method,
        })

    config = vars(args).copy()
    config.update({
        "script": str(Path(__file__).resolve()),
        "protocol": "fair_visual_budget_v1",
        "rag_enabled": False,
        "reflection_enabled": False,
        "secondary_frame_sampling_disabled": True,
        "answer_prompt_version": ADSQA_ANSWER_PROMPT_VERSION,
        "answer_prompt_template_sha256": adsqa_answer_prompt_sha256(),
        "dry_run_fast_path": True,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    (output_dir / "run_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "dry_run_preview.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dry run complete: method={args.fair_method} items={len(preview)} output={output_dir}")


if args.dry_run:
    run_early_dry_run()
    raise SystemExit(0)

import numpy as np
from PIL import Image, ImageFile
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    import torch
    import torch.nn.functional as F
    import transformers
    from transformers import AutoModelForVision2Seq, AutoProcessor
    from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer
except Exception as import_exc:  # fail early with readable error
    print(f"[ImportError] {import_exc}", file=sys.stderr)
    raise

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except Exception:
    DECORD_AVAILABLE = False

# Make evaluation/rag importable from both the organized path and legacy symlinks.
_SCRIPT_PATH = Path(__file__).resolve()
_EVAL_DIR = next((parent for parent in _SCRIPT_PATH.parents if parent.name == "evaluation"), _SCRIPT_PATH.parent)
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))
_PROJECT_ROOT = _EVAL_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.methods.common.qwen_video_budget import (  # noqa: E402
    VideoBudgetError,
    fixed_global_local_split,
    prepare_qwen_video_inputs,
)
from evaluation.methods.temporal_evidence.temporal_cache import (  # noqa: E402
    load_temporal_index_cache,
    nested_uniform_candidate_indices,
    temporal_cache_inventory,
    validate_temporal_record,
)


LOGGER = logging.getLogger("adsqa_fair_baselines_v1")


def setup_logging(output_dir: Path, gpu_id: str) -> None:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"inference_gpu{gpu_id}_shard{args.shard_id}of{args.num_shards}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, mode="a", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        force=True,
    )
    LOGGER.info("Log file: %s", log_file)


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smart_resize(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.BICUBIC)


def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


AD_SLOT_KEYWORDS = {
    "brand_logo": [
        "brand", "logo", "company", "product name", "name of", "packaging", "package",
        "label", "visual identity", "recognize", "recognise",
    ],
    "price_promo": [
        "price", "discount", "deal", "offer", "sale", "promotion", "coupon", "free",
        "trial", "limited", "save", "cost", "money", "cheap", "percent", "%", "$", "£", "€",
    ],
    "cta": [
        "call to action", "cta", "buy", "purchase", "download", "install", "order",
        "subscribe", "sign up", "visit", "scan", "click", "app", "website", "now",
    ],
    "claim_benefit": [
        "claim", "benefit", "feature", "advantage", "function", "promise", "assertion",
        "protection", "speed", "faster", "better", "effective", "why", "reason",
    ],
    "audience_emotion": [
        "audience", "target", "emotion", "feeling", "mood", "tone", "appeal", "persuade",
        "strategy", "message", "lifestyle", "family", "men", "women", "children", "parents",
    ],
    "speech_audio": [
        "say", "says", "said", "voice", "voiceover", "narrator", "spoken", "audio",
        "sound", "music", "heard", "hear",
    ],
    "text_ocr": [
        "text", "word", "words", "caption", "subtitle", "written", "displayed", "shown",
        "screen", "number", "url", "website", "small print", "disclaimer",
    ],
}


def route_ad_slots(question: str, q_types: Any = None) -> Dict[str, Any]:
    """Rule-based AdsQA evidence slot router for reproducible MVP experiments."""
    q = (question or "").lower()
    slots: List[str] = []
    triggers: Dict[str, List[str]] = {}
    for slot, kws in AD_SLOT_KEYWORDS.items():
        matched = [kw for kw in kws if kw in q]
        if matched:
            slots.append(slot)
            triggers[slot] = matched[:6]
    if not slots:
        # AdsQA Type_1 often asks visual detail; keep a conservative visual default.
        slots.append("claim_benefit")
        triggers["claim_benefit"] = ["default_visual_claim"]

    q_type_list: List[str] = []
    if isinstance(q_types, (list, tuple)):
        q_type_list = [str(x) for x in q_types]
    elif q_types:
        q_type_list = [str(q_types)]

    if any(s in slots for s in ("price_promo", "cta", "text_ocr", "brand_logo")):
        top_k_delta = 2
    elif "audience_emotion" in slots:
        top_k_delta = 0
    else:
        top_k_delta = 1

    weights = {
        "select_question": 0.60,
        "select_audio": 0.40,
        "crop_question": 0.50,
        "crop_audio": 0.30,
        "crop_ocr": 0.20,
    }
    if "speech_audio" in slots:
        weights["select_audio"] = 0.55
        weights["select_question"] = 0.45
        weights["crop_audio"] = 0.40
    if any(s in slots for s in ("price_promo", "cta", "text_ocr", "brand_logo")):
        weights["crop_ocr"] = 0.38
        weights["crop_question"] = 0.44
        weights["crop_audio"] = 0.18
    if "audience_emotion" in slots:
        weights["select_question"] = 0.68
        weights["select_audio"] = 0.32
        weights["crop_question"] = 0.58

    return {
        "slots": slots,
        "triggers": triggers,
        "question_types": q_type_list,
        "top_k_delta": top_k_delta,
        "weights": weights,
    }


def apply_adslot_weights(cfg: argparse.Namespace, route: Dict[str, Any]) -> Dict[str, float]:
    """Temporarily apply slot-adaptive weights, returning the previous values."""
    prev = {
        "select_question_weight": cfg.select_question_weight,
        "select_audio_weight": cfg.select_audio_weight,
        "question_weight": cfg.question_weight,
        "audio_weight": cfg.audio_weight,
        "ocr_weight": cfg.ocr_weight,
    }
    if getattr(cfg, "adslot_mode", "off") != "on":
        return prev
    w = route.get("weights", {})
    cfg.select_question_weight = float(w.get("select_question", cfg.select_question_weight))
    cfg.select_audio_weight = float(w.get("select_audio", cfg.select_audio_weight))
    cfg.question_weight = float(w.get("crop_question", cfg.question_weight))
    cfg.audio_weight = float(w.get("crop_audio", cfg.audio_weight))
    cfg.ocr_weight = float(w.get("crop_ocr", cfg.ocr_weight))
    return prev


def restore_adslot_weights(cfg: argparse.Namespace, prev: Dict[str, float]) -> None:
    for key, value in prev.items():
        setattr(cfg, key, value)


def load_groundtruth_map(path: str) -> Dict[str, str]:
    gt_map: Dict[str, str] = {}
    if not path or not os.path.exists(path):
        return gt_map
    try:
        with open(path, "r", encoding="utf-8") as f:
            for x in json.load(f):
                qid = str(x.get("question_id"))
                ans = x.get("answer", x.get("gt_answer", x.get("answers", "N/A")))
                if isinstance(ans, list):
                    ans = "; ".join(map(str, ans))
                gt_map[qid] = str(ans)
    except Exception as e:
        LOGGER.warning("Failed to load GT map: %s", e)
    return gt_map


def resolve_video_path(video_root: str, vid: str, frames_fallback_root: str = "") -> str:
    candidates = [
        os.path.join(video_root, f"{vid}.mp4"),
        os.path.join(video_root, vid),
        os.path.join(video_root, f"{vid}.webm"),
        os.path.join(video_root, f"{vid}.mov"),
    ]
    if frames_fallback_root:
        candidates.extend([
            os.path.join(frames_fallback_root, str(vid)),
            os.path.join(frames_fallback_root, f"{vid}.mp4"),
        ])
    for p in candidates:
        if os.path.exists(p):
            # If decord is unavailable, prefer extracted-frame directories over raw videos.
            if (not DECORD_AVAILABLE) and os.path.isfile(p):
                continue
            return p
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def load_frames_oversampled(video_path: str, sample_count: int = 32, nested_baseline_count: int = 0) -> Tuple[List[Image.Image], List[Dict[str, Any]]]:
    """Return sampled PIL frames and metadata. Supports raw video or pre-extracted frame directory."""
    frames: List[Image.Image] = []
    meta: List[Dict[str, Any]] = []
    if not os.path.exists(video_path):
        return frames, meta

    if DECORD_AVAILABLE and os.path.isfile(video_path):
        try:
            vr = VideoReader(video_path, ctx=cpu(0))
            n = len(vr)
            if n > 0:
                indices = (
                    nested_uniform_candidate_indices(n, sample_count, nested_baseline_count)
                    if nested_baseline_count
                    else np.linspace(0, n - 1, sample_count, dtype=int).tolist()
                )
                for rank, idx in enumerate(indices):
                    frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
                    meta.append({"sample_rank": rank, "source": "video", "frame_index": int(idx), "total_frames": int(n)})
                return frames, meta
        except Exception as e:
            LOGGER.warning("Decord load failed for %s: %s; fallback to directory mode", video_path, e)

    if os.path.isdir(video_path):
        files = sorted(Path(video_path).glob("*.jpg")) + sorted(Path(video_path).glob("*.png"))
        if files:
            indices = np.linspace(0, len(files) - 1, sample_count, dtype=int)
            for rank, i in enumerate(indices.tolist()):
                fp = files[i]
                try:
                    frames.append(Image.open(fp).convert("RGB"))
                    meta.append({"sample_rank": rank, "source": "frames", "frame_index": int(i), "frame_file": str(fp), "total_frames": len(files)})
                except Exception as e:
                    LOGGER.warning("Frame open failed %s: %s", fp, e)
    return frames, meta


class S23VisualProcessor:
    """CLIP-based frame selector and response-density cropper with audit metadata."""

    def __init__(self, device: str, clip_path: str, cfg: argparse.Namespace):
        self.device = device
        self.cfg = cfg
        self.valid = False
        self.error = ""
        try:
            kwargs = {"local_files_only": True, "ignore_mismatched_sizes": True}
            self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, **kwargs).to(device).eval()
            self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path, **kwargs).to(device).eval()
            self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
            from torchvision.transforms import Normalize, ToTensor
            self.normalize = Normalize(
                (0.48145466, 0.4578275, 0.40821073),
                (0.26862954, 0.26130258, 0.27577711),
            )
            self.to_tensor = ToTensor()
            self.valid = True
            LOGGER.info("CLIP evidence processor loaded: %s", clip_path)
        except Exception as e:
            self.error = repr(e)
            LOGGER.warning("CLIP evidence processor unavailable, fallback to uniform frames. Error: %s", e)

    def _encode_text(self, text: str):
        if not text:
            return None
        tokens = self.tokenizer(
            [text[:300]],
            padding=True,
            truncation=True,
            max_length=77,
            return_tensors="pt",
        ).to(self.device)
        return F.normalize(self.text_enc(**tokens).text_embeds, dim=-1)

    def _safe_preprocess(self, image: Image.Image):
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = image.resize((224, 224), Image.BICUBIC)
            tensor = self.to_tensor(image)
            if tensor.shape[0] == 1:
                tensor = tensor.repeat(3, 1, 1)
            elif tensor.shape[0] == 4:
                tensor = tensor[:3]
            return self.normalize(tensor) if tensor.shape[0] == 3 else None
        except Exception:
            return None

    def select_top_frames(
        self,
        frames: List[Image.Image],
        frame_meta: List[Dict[str, Any]],
        question: str,
        audio_text: str,
        top_k: int,
    ) -> Tuple[List[Image.Image], List[Dict[str, Any]]]:
        if not frames:
            return [], []
        if not self.valid:
            selected = frames[:top_k]
            selected_meta = []
            for j, m in enumerate(frame_meta[:top_k]):
                mm = dict(m)
                mm.update({"selection_rank": j, "selection_score": None, "selection_mode": "uniform_fallback"})
                selected_meta.append(mm)
            return selected, selected_meta

        try:
            with torch.no_grad():
                processed, valid_idx = [], []
                for i, f in enumerate(frames):
                    t = self._safe_preprocess(f)
                    if t is not None:
                        processed.append(t)
                        valid_idx.append(i)
                if not processed:
                    return frames[:top_k], frame_meta[:top_k]

                img_ts = torch.stack(processed).to(self.device)
                img_emb = F.normalize(self.vision(img_ts).image_embeds, dim=-1)
                q_emb = self._encode_text(question)
                a_emb = self._encode_text(audio_text)

                if q_emb is None:
                    scores = torch.zeros(img_emb.shape[0], device=self.device)
                else:
                    scores = torch.matmul(img_emb, q_emb.T).view(-1) * self.cfg.select_question_weight
                if a_emb is not None:
                    scores = scores + torch.matmul(img_emb, a_emb.T).view(-1) * self.cfg.select_audio_weight

                score_np = scores.detach().cpu().numpy()
                chosen_local = sorted(np.argsort(score_np)[-min(top_k, len(score_np)):].tolist())
                selected_frames = [frames[valid_idx[i]] for i in chosen_local]
                selected_meta = []
                for out_rank, local_i in enumerate(chosen_local):
                    original_i = valid_idx[local_i]
                    mm = dict(frame_meta[original_i]) if original_i < len(frame_meta) else {"sample_rank": original_i}
                    mm.update({
                        "selection_rank": out_rank,
                        "selection_score": safe_float(score_np[local_i]),
                        "selection_mode": "clip_question_audio",
                    })
                    selected_meta.append(mm)
                return selected_frames, selected_meta
        except Exception as e:
            LOGGER.warning("Frame selection failed, fallback uniform: %s", e)
            selected = frames[:top_k]
            selected_meta = []
            for j, m in enumerate(frame_meta[:top_k]):
                mm = dict(m)
                mm.update({"selection_rank": j, "selection_score": None, "selection_mode": "selection_error_fallback"})
                selected_meta.append(mm)
            return selected, selected_meta

    def smart_crop(self, frame: Image.Image, question: str, audio_text: str) -> Tuple[Image.Image, Dict[str, Any]]:
        ow, oh = frame.size
        fallback = {
            "bbox": [0, 0, ow, oh],
            "bbox_norm": [0.0, 0.0, 1.0, 1.0],
            "crop_score": None,
            "crop_mode": "full_fallback",
        }
        if not self.valid:
            return frame, fallback

        try:
            with torch.no_grad():
                t = self._safe_preprocess(frame)
                if t is None:
                    return frame, fallback
                img_ts = t.unsqueeze(0).to(self.device)
                vis_out = self.vision(img_ts)
                last_hidden = vis_out.last_hidden_state[:, 1:]
                if hasattr(self.vision, "visual_projection"):
                    last_hidden = self.vision.visual_projection(last_hidden)
                patch_emb = F.normalize(last_hidden, dim=-1)

                q_emb = self._encode_text(question)
                if q_emb is None:
                    hm_q = torch.zeros(patch_emb.shape[1], device=self.device)
                else:
                    hm_q = torch.matmul(patch_emb, q_emb.T).view(-1)

                safe_audio = audio_text if audio_text and len(audio_text) > 1 else "sound"
                a_emb = self._encode_text(safe_audio)
                hm_audio = torch.matmul(patch_emb, a_emb.T).view(-1) if a_emb is not None else torch.zeros_like(hm_q)

                ocr_tokens = self.tokenizer(["text", "logo", "brand", "words"], padding=True, return_tensors="pt").to(self.device)
                ocr_emb = F.normalize(self.text_enc(**ocr_tokens).text_embeds, dim=-1)
                # patch_emb: [1, num_patches, dim], ocr_emb.T: [dim, 4]
                # similarity -> [1, num_patches, 4], then max over OCR keywords -> [num_patches]
                hm_ocr = torch.matmul(patch_emb, ocr_emb.T).squeeze(0).max(dim=1).values

                fused = (hm_q * self.cfg.question_weight) + (hm_audio * self.cfg.audio_weight) + (hm_ocr * self.cfg.ocr_weight)
                side = int(fused.shape[0] ** 0.5)
                hm = fused[: side * side].view(side, side).detach().cpu().numpy()
                hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)

                h, w = hm.shape
                y_grid, x_grid = np.indices((h, w))
                total = hm.sum() + 1e-8
                cy = float(np.sum(y_grid * hm) / total)
                cx = float(np.sum(x_grid * hm) / total)
                center_x = int((cx / w) * ow)
                center_y = int((cy / h) * oh)

                best_box = (0, 0, ow, oh)
                max_energy = -1.0
                scale_records = []
                total_energy = float(hm.sum() + 1e-8)
                for scale in self.cfg.crop_scales:
                    if scale >= 1.0:
                        box = (0, 0, ow, oh)
                    else:
                        cw, ch = int(ow * scale), int(oh * scale)
                        l = max(0, center_x - cw // 2)
                        t0 = max(0, center_y - ch // 2)
                        r, b = min(ow, l + cw), min(oh, t0 + ch)
                        if (r - l) < cw:
                            l = max(0, r - cw)
                        if (b - t0) < ch:
                            t0 = max(0, b - ch)
                        box = (int(l), int(t0), int(r), int(b))

                    l, t0, r, b = box
                    grid_l, grid_r = int((l / ow) * w), int((r / ow) * w)
                    grid_t, grid_b = int((t0 / oh) * h), int((b / oh) * h)
                    if grid_r > grid_l and grid_b > grid_t:
                        box_energy = float(hm[grid_t:grid_b, grid_l:grid_r].sum())
                        box_area = float((grid_r - grid_l) * (grid_b - grid_t))
                        density = box_energy / (box_area + 1e-8)
                        coverage = box_energy / total_energy
                        score = float((0.7 * density) + (0.3 * coverage))
                        if scale >= 0.95:
                            # Global frames are already supplied separately; discourage
                            # the local branch from degenerating into another full frame.
                            score *= 0.5
                    else:
                        box_energy = 0.0
                        box_area = 0.0
                        density = 0.0
                        coverage = 0.0
                        score = -1.0
                    scale_records.append({
                        "scale": float(scale),
                        "box": list(box),
                        "score": score,
                        "energy": box_energy,
                        "density": density,
                        "coverage": coverage,
                        "score_mode": "density_0.7_coverage_0.3_full_penalty",
                    })
                    if score > max_energy:
                        max_energy = score
                        best_box = box

                l, t0, r, b = best_box
                crop_meta = {
                    "bbox": [int(l), int(t0), int(r), int(b)],
                    "bbox_norm": [l / ow, t0 / oh, r / ow, b / oh],
                    "crop_score": float(max_energy),
                    "crop_mode": "clip_fused_response_density",
                    "center_xy": [center_x, center_y],
                    "scales": scale_records,
                    "weights": {"question": self.cfg.question_weight, "audio": self.cfg.audio_weight, "ocr": self.cfg.ocr_weight},
                }
                return frame.crop(best_box), crop_meta
        except Exception as e:
            LOGGER.warning("Smart crop failed, fallback full image: %s", e)
            return frame, fallback


class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question: str, asr: str, rag_context: str = "") -> str:
        return build_adsqa_answer_prompt(question, asr, rag_context)

    @staticmethod
    def reflection_prompt(question: str, initial_ans: str) -> str:
        return f"""Role: Fact-Checker.
Question: {question}
Draft: "{initial_ans}"
Task: Verify the draft against the video/audio evidence.
Output exactly one of:
[KEEP]
[Final Answer]: <corrected concise answer>
"""


def generate_response(
    model,
    processor,
    frames: List[Image.Image],
    prompt: str,
    max_new_tokens: int,
) -> Tuple[str, Dict[str, Any]]:
    msg = [{"role": "user", "content": [{"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt}]}]
    text_in = processor.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
    inputs, processor_trace = prepare_qwen_video_inputs(
        processor=processor,
        text_input=text_in,
        frames=frames,
        device=model.device,
        expected_view_count=args.visual_view_budget,
        max_post_merge_visual_tokens=args.max_post_merge_visual_tokens,
        metadata_fps=args.metadata_fps,
        require_exact_frame_count=True,
    )
    with torch.no_grad():
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens)
    trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated)]
    decoded = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return (decoded[0].strip() if decoded else ""), processor_trace


def _uniform_indices(length: int, count: int) -> List[int]:
    if count <= 0 or length <= 0:
        raise VideoBudgetError(f"cannot choose {count} uniform views from {length} frames")
    return np.linspace(0, length - 1, count, dtype=int).tolist()


def _crop_score(meta: Dict[str, Any]) -> float:
    value = safe_float(meta.get("crop_score"))
    return value if value is not None else -1e9


def select_coverage_adslot_frames(
    visual_processor: S23VisualProcessor,
    frames: List[Image.Image],
    frame_meta: List[Dict[str, Any]],
    question: str,
    audio_text: str,
    global_count: int,
    coverage_bin_count: int = 8,
) -> Tuple[List[Image.Image], List[Dict[str, Any]]]:
    """Select scored frames while reserving one candidate in each temporal bin."""
    if not frames:
        return [], []
    if global_count <= 0 or global_count > len(frames):
        raise VideoBudgetError(
            f"coverage selection count must be within candidates: global_count={global_count}, candidates={len(frames)}"
        )

    # Score the complete candidate set once, then apply only the fixed coverage rule.
    _, scored_meta = visual_processor.select_top_frames(
        frames,
        frame_meta,
        question,
        audio_text,
        len(frames),
    )
    score_by_position: Dict[int, Optional[float]] = {}
    for fallback_position, meta in enumerate(scored_meta):
        position = meta.get("sample_rank")
        if not isinstance(position, int) or position < 0 or position >= len(frames):
            position = fallback_position
        score_by_position[position] = safe_float(meta.get("selection_score"))

    def score_key(position: int) -> Tuple[float, int]:
        score = score_by_position.get(position)
        return (score if score is not None else -1e9, -position)

    bin_for_position: Dict[int, int] = {}
    reserved_positions: List[int] = []
    bin_count = min(max(1, int(coverage_bin_count)), len(frames))
    for bin_id in range(bin_count):
        start = (bin_id * len(frames)) // bin_count
        end = ((bin_id + 1) * len(frames)) // bin_count
        positions = list(range(start, end))
        if not positions:
            continue
        for position in positions:
            bin_for_position[position] = bin_id
        reserved_positions.append(max(positions, key=score_key))

    chosen_positions = list(dict.fromkeys(reserved_positions))
    for position in sorted(range(len(frames)), key=score_key, reverse=True):
        if len(chosen_positions) >= global_count:
            break
        if position not in chosen_positions:
            chosen_positions.append(position)
    chosen_positions.sort()

    selected_frames = [frames[position] for position in chosen_positions]
    selected_meta: List[Dict[str, Any]] = []
    reserved_set = set(reserved_positions)
    for selection_rank, position in enumerate(chosen_positions):
        meta = dict(frame_meta[position])
        meta.update({
            "selection_rank": selection_rank,
            "selection_score": score_by_position.get(position),
            "selection_mode": "coverage_adslot_question_audio",
            "candidate_rank": position,
            "coverage_bin": bin_for_position.get(position),
            "coverage_reserved": position in reserved_set,
        })
        selected_meta.append(meta)
    return selected_frames, selected_meta


def build_fair_visual_sequence(
    visual_processor: Optional[S23VisualProcessor],
    raw_frames: List[Image.Image],
    raw_meta: List[Dict[str, Any]],
    item: Dict[str, Any],
    asr_text: str,
    temporal_cache: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[
    List[Image.Image],
    List[Dict[str, Any]],
    List[Image.Image],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
]:
    """Build one of the three baselines under one fixed submitted-view budget."""
    budget = int(args.visual_view_budget)
    if budget <= 0:
        raise ValueError("visual_view_budget must be positive")

    empty_route = {
        "slots": [],
        "triggers": {},
        "question_types": item.get("question_type", []),
        "top_k_delta": 0,
        "weights": {},
    }
    crop_metas: List[Dict[str, Any]] = []
    visual_plan: List[Dict[str, Any]] = []

    if args.fair_method == "raw_uniform":
        chosen = _uniform_indices(len(raw_frames), budget)
        selected_frames = [raw_frames[index] for index in chosen]
        selected_meta = []
        final_frames = []
        source_occurrences: Dict[int, int] = {}
        for frame_rank, index in enumerate(chosen):
            repeat_ordinal = source_occurrences.get(index, 0)
            source_occurrences[index] = repeat_ordinal + 1
            meta = dict(raw_meta[index])
            meta.update({
                "temporal_order": frame_rank,
                "selection_mode": "uniform_global_only",
                "source_repeat_ordinal": repeat_ordinal,
            })
            selected_meta.append(meta)
            final_frames.append(smart_resize(raw_frames[index], args.unified_size))
            visual_plan.append({
                "input_index": len(final_frames) - 1,
                "view_type": "global",
                "frame_rank": frame_rank,
                "sample_rank": meta.get("sample_rank"),
                "frame_index": meta.get("frame_index"),
                "source_repeat_ordinal": repeat_ordinal,
            })
        unique_source_count = len(set(chosen))
        protocol = {
            "method": args.fair_method,
            "view_budget": budget,
            "global_count": len(final_frames),
            "local_count": 0,
            "selection": "uniform",
            "crop": "none",
            "unique_source_count": unique_source_count,
            "repeated_source_view_count": len(chosen) - unique_source_count,
            "short_video_repeat_policy": (
                "linspace_floor_repeat" if unique_source_count < len(chosen) else "not_needed"
            ),
        }
        return selected_frames, selected_meta, final_frames, crop_metas, visual_plan, empty_route, protocol

    if args.fair_method == "external_temporal":
        question_id = str(item.get("question_id", ""))
        if temporal_cache is None or question_id not in temporal_cache:
            raise RuntimeError(f"missing temporal cache record for {question_id}")
        chosen = validate_temporal_record(
            temporal_cache[question_id],
            question_id=question_id,
            question=str(item.get("question", "")),
            candidate_count=len(raw_frames),
            selected_count=budget,
        )
        record = temporal_cache[question_id]
        cached_frame_indices = record.get("candidate_frame_indices")
        current_frame_indices = [meta.get("frame_index") for meta in raw_meta]
        if cached_frame_indices is not None and cached_frame_indices != current_frame_indices:
            raise RuntimeError(f"candidate frame indices drifted for {question_id}")
        scores = record.get("candidate_scores", [])
        selected_frames = [raw_frames[index] for index in chosen]
        selected_meta = []
        final_frames = []
        for temporal_order, index in enumerate(chosen):
            meta = dict(raw_meta[index])
            meta.update({
                "temporal_order": temporal_order,
                "selection_mode": str(record.get("selector", "external_temporal")),
                "candidate_rank": index,
                "selection_score": safe_float(scores[index]) if index < len(scores) else None,
                "cache_file": record.get("_cache_file"),
                "cache_line": record.get("_cache_line"),
            })
            selected_meta.append(meta)
            final_frames.append(smart_resize(raw_frames[index], args.unified_size))
            visual_plan.append({
                "input_index": temporal_order,
                "view_type": "global",
                "frame_rank": temporal_order,
                "sample_rank": meta.get("sample_rank"),
                "frame_index": meta.get("frame_index"),
                "candidate_rank": index,
                "selection_score": meta.get("selection_score"),
            })
        protocol = {
            "method": args.fair_method,
            "selector": record.get("selector"),
            "view_budget": budget,
            "candidate_count": len(raw_frames),
            "global_count": len(final_frames),
            "local_count": 0,
            "selection": "offline_question_conditioned_temporal_cache",
            "selection_order": "chronological_after_topk",
            "crop": "none",
        }
        return selected_frames, selected_meta, final_frames, crop_metas, visual_plan, empty_route, protocol

    if budget % 2 != 0:
        raise ValueError("clip/adslot fair methods require an even visual_view_budget")
    if visual_processor is None:
        raise RuntimeError(f"{args.fair_method} requires the CLIP visual processor")

    question = str(item.get("question", ""))
    adslot_route = empty_route
    previous_weights: Dict[str, float] | None = None
    if args.fair_method == "clip_singlepeak":
        effective_top_k = budget // 2
    elif args.fair_method == "coverage_adslot":
        if budget != 32:
            raise ValueError("coverage_adslot is frozen to a 32-view protocol")
        adslot_route = route_ad_slots(question, item.get("question_type"))
        previous_weights = apply_adslot_weights(args, adslot_route)
        effective_top_k = 18
    else:
        adslot_route = route_ad_slots(question, item.get("question_type"))
        previous_weights = apply_adslot_weights(args, adslot_route)
        split = fixed_global_local_split(
            total_view_budget=budget,
            requested_global_count=int(args.top_k_frames) + int(adslot_route.get("top_k_delta", 0)),
            minimum_global_count=int(args.adslot_min_top_k),
            maximum_global_count=int(args.adslot_max_top_k),
        )
        effective_top_k = int(split["global_count"])

    try:
        if args.fair_method == "coverage_adslot":
            selected_frames, selected_meta = select_coverage_adslot_frames(
                visual_processor,
                raw_frames,
                raw_meta,
                question,
                asr_text[:100],
                effective_top_k,
                coverage_bin_count=8,
            )
        else:
            selected_frames, selected_meta = visual_processor.select_top_frames(
                raw_frames,
                raw_meta,
                question,
                asr_text[:100],
                effective_top_k,
            )
        if len(selected_frames) != effective_top_k:
            raise VideoBudgetError(
                f"selected frame count mismatch: got={len(selected_frames)}, expected={effective_top_k}"
            )

        crop_images: Dict[int, Image.Image] = {}
        for frame_rank, (frame, frame_meta) in enumerate(zip(selected_frames, selected_meta)):
            frame_meta["adslot_route"] = adslot_route.get("slots", [])
            frame_meta["adslot_selection_weights"] = {
                "question": args.select_question_weight,
                "audio": args.select_audio_weight,
            }
            local, crop_meta = visual_processor.smart_crop(frame, question, asr_text[:100])
            crop_meta.update({
                "frame_rank": frame_rank,
                "sample_rank": frame_meta.get("sample_rank"),
                "frame_index": frame_meta.get("frame_index"),
                "adslot_route": adslot_route.get("slots", []),
                "adslot_crop_weights": {
                    "question": args.question_weight,
                    "audio": args.audio_weight,
                    "ocr": args.ocr_weight,
                },
            })
            crop_metas.append(crop_meta)
            crop_images[frame_rank] = local

        local_budget = budget - len(selected_frames)
        if local_budget < 0 or local_budget > len(crop_metas):
            raise VideoBudgetError(
                f"local budget cannot be filled: globals={len(selected_frames)}, locals={local_budget}"
            )
        ranked_local_frames = sorted(
            range(len(crop_metas)),
            key=lambda index: (_crop_score(crop_metas[index]), -index),
            reverse=True,
        )[:local_budget]
        local_budget_rank = {frame_rank: rank for rank, frame_rank in enumerate(ranked_local_frames)}
        chosen_local_frames = set(ranked_local_frames)

        final_frames: List[Image.Image] = []
        for frame_rank, (frame, frame_meta) in enumerate(zip(selected_frames, selected_meta)):
            final_frames.append(smart_resize(frame, args.unified_size))
            visual_plan.append({
                "input_index": len(final_frames) - 1,
                "view_type": "global",
                "frame_rank": frame_rank,
                "sample_rank": frame_meta.get("sample_rank"),
                "frame_index": frame_meta.get("frame_index"),
            })
            selected_for_budget = frame_rank in chosen_local_frames
            crop_metas[frame_rank]["selected_for_budget"] = selected_for_budget
            crop_metas[frame_rank]["budget_rank"] = local_budget_rank.get(frame_rank)
            if selected_for_budget:
                final_frames.append(smart_resize(crop_images[frame_rank], args.unified_size))
                visual_plan.append({
                    "input_index": len(final_frames) - 1,
                    "view_type": "local",
                    "frame_rank": frame_rank,
                    "sample_rank": frame_meta.get("sample_rank"),
                    "frame_index": frame_meta.get("frame_index"),
                    "bbox": crop_metas[frame_rank].get("bbox"),
                    "crop_score": crop_metas[frame_rank].get("crop_score"),
                    "budget_rank": local_budget_rank[frame_rank],
                })

        if len(final_frames) != budget:
            raise VideoBudgetError(f"view budget mismatch after reconstruction: {len(final_frames)} != {budget}")
        protocol = {
            "method": args.fair_method,
            "view_budget": budget,
            "global_count": len(selected_frames),
            "local_count": local_budget,
            "selection": (
                "clip_question_audio_temporal_coverage"
                if args.fair_method == "coverage_adslot"
                else "clip_question_audio"
            ),
            "crop": "single_peak_response_density",
            "adslot_fixed_total_budget": args.fair_method in {"adslot_fixed", "coverage_adslot"},
            "effective_top_k_frames": effective_top_k,
            "coverage_bin_count": 8 if args.fair_method == "coverage_adslot" else 0,
            "coverage_reserved_global_count": (
                min(8, len(selected_frames)) if args.fair_method == "coverage_adslot" else 0
            ),
            "coverage_global_local_policy": (
                "fixed_18_global_plus_14_local" if args.fair_method == "coverage_adslot" else "route_adaptive"
            ),
        }
        return selected_frames, selected_meta, final_frames, crop_metas, visual_plan, adslot_route, protocol
    finally:
        if previous_weights is not None:
            restore_adslot_weights(args, previous_weights)


def save_evidence_images(
    q_dir: Path,
    frames: List[Image.Image],
    visual_plan: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    img_dir = q_dir / "evidence_images"
    img_dir.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = []
    for frame, plan in zip(frames, visual_plan):
        name = f"input{int(plan['input_index']):02d}_{plan['view_type']}_frame{int(plan['frame_rank']):02d}.jpg"
        path = img_dir / name
        frame.save(path, quality=90)
        records.append({**plan, "path": str(path)})
    return records


def main() -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(output_dir, args.gpu_id)

    if args.num_shards <= 0 or args.shard_id < 0 or args.shard_id >= args.num_shards:
        raise ValueError(f"Invalid shard: shard_id={args.shard_id}, num_shards={args.num_shards}")
    if args.rag_mode != "none" or args.rag_v2:
        raise ValueError("fair protocol V1 requires RAG to be disabled")
    if not args.disable_reflection:
        raise ValueError("fair protocol V1 requires reflection to be disabled")
    if args.visual_view_budget <= 0:
        raise ValueError("visual_view_budget must be positive")
    if args.max_post_merge_visual_tokens <= 0:
        raise ValueError("max_post_merge_visual_tokens must be positive")
    if args.oversample_count < args.visual_view_budget:
        raise ValueError("oversample_count must be at least visual_view_budget")

    LOGGER.info("Starting parameterized inference on GPU %s", args.gpu_id)
    LOGGER.info("Output dir: %s", output_dir)
    LOGGER.info("Decord available: %s", DECORD_AVAILABLE)

    temporal_cache = None
    temporal_cache_files: List[Dict[str, Any]] = []
    if args.fair_method == "external_temporal":
        if not args.temporal_index_cache:
            raise ValueError("external_temporal requires --temporal_index_cache")
        temporal_cache = load_temporal_index_cache(args.temporal_index_cache)
        temporal_cache_files = temporal_cache_inventory(args.temporal_index_cache)
        LOGGER.info("Loaded %d temporal cache records from %s", len(temporal_cache), args.temporal_index_cache)

    # Persist run config for reproducibility.
    run_config = vars(args).copy()
    common_input_path = _PROJECT_ROOT / "evaluation" / "methods" / "common" / "qwen_video_budget.py"
    run_config.update({
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "common_input_module": str(common_input_path),
        "common_input_module_sha256": sha256_file(common_input_path),
        "transformers_version": transformers.__version__,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "pytorch_cuda_alloc_conf": os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "protocol": "fair_visual_budget_v1",
        "rag_enabled": False,
        "reflection_enabled": False,
        "secondary_frame_sampling_disabled": True,
        "answer_prompt_version": ADSQA_ANSWER_PROMPT_VERSION,
        "answer_prompt_template_sha256": adsqa_answer_prompt_sha256(),
        "budget_unit": "submitted_views_and_post_merge_visual_tokens",
        "temporal_cache_record_count": len(temporal_cache) if temporal_cache is not None else 0,
        "temporal_cache_files": temporal_cache_files,
    })
    dump_json(output_dir / "run_config.json", run_config)

    with open(args.question_file, "r", encoding="utf-8") as f:
        questions = json.load(f)
    with open(args.asr_file, "r", encoding="utf-8") as f:
        asr_data = json.load(f) if os.path.exists(args.asr_file) else {}
    gt_map = load_groundtruth_map(args.groundtruth_file)

    end_idx = len(questions) if args.end_idx == -1 else min(args.end_idx, len(questions))
    start_idx = max(0, args.start_idx)
    selected_questions = list(enumerate(questions[start_idx:end_idx], start=start_idx))
    shard_questions = [(idx, item) for idx, item in selected_questions if idx % args.num_shards == args.shard_id]
    LOGGER.info("Questions total=%d selected_range=%d shard_items=%d", len(questions), len(selected_questions), len(shard_questions))

    if args.dry_run:
        preview = []
        for idx, item in shard_questions[:10]:
            qid = str(item["question_id"])
            vid = item.get("video", item.get("video_id", qid.split("_")[0]))
            preview.append({
                "global_idx": idx,
                "question_id": qid,
                "video": vid,
                "video_path": resolve_video_path(args.video_root, vid, args.frames_fallback_root),
                "fair_method": args.fair_method,
                "visual_view_budget": args.visual_view_budget,
                "max_post_merge_visual_tokens": args.max_post_merge_visual_tokens,
            })
        dump_json(output_dir / "dry_run_preview.json", preview)
        LOGGER.info("Dry run completed. Preview saved to %s", output_dir / "dry_run_preview.json")
        return

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    s23 = None
    if args.fair_method in {"clip_singlepeak", "adslot_fixed", "coverage_adslot"}:
        s23 = S23VisualProcessor(device="cuda", clip_path=args.clip_path, cfg=args)

    model_label = args.model_label or Path(args.model_dir).name
    LOGGER.info("Loading vision-language model [%s] from %s", model_label, args.model_dir)
    model = AutoModelForVision2Seq.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    processor = AutoProcessor.from_pretrained(
        args.model_dir,
        min_pixels=256 * 256,
        max_pixels=1280 * 1280,
        trust_remote_code=True,
    )

    rag_engine = None
    if args.rag_mode != "none":
        try:
            from rag.rag_retriever import MarketingRAGRetriever
            rag_engine = MarketingRAGRetriever(
                kb_path=args.rag_kb,
                index_path=args.rag_index,
                model_path=args.rag_model,
                device=args.rag_device,
                mode=args.rag_mode,
                dense_weight=args.rag_dense_weight,
                lexical_weight=args.rag_lexical_weight,
                backend=args.rag_backend,
                require_index=args.rag_require_index,
            )
            LOGGER.info("RAG enabled: mode=%s kb=%s index=%s", args.rag_mode, args.rag_kb, args.rag_index)
        except Exception as e:
            LOGGER.error("RAG initialization failed: %s", e)
            raise

    stats = {"processed": 0, "skipped_existing": 0, "skipped_previous": 0, "copied_previous": 0, "missing_video_or_frames": 0, "errors": 0}
    errors_path = output_dir / "logs" / f"errors_gpu{args.gpu_id}_shard{args.shard_id}.jsonl"

    for global_idx, item in tqdm(shard_questions, desc=f"GPU {args.gpu_id} shard {args.shard_id}/{args.num_shards}"):
        q_start = time.time()
        qid = str(item["question_id"])
        q_dir = output_dir / qid
        pred_path = q_dir / "prediction.json"
        evidence_path = q_dir / "evidence.json"

        try:
            if pred_path.exists() and not args.overwrite:
                stats["skipped_existing"] += 1
                continue

            prev_path = Path(args.previous_output_dir) / qid / "prediction.json" if args.previous_output_dir else None
            if prev_path and prev_path.exists() and args.previous_mode == "skip" and not args.overwrite:
                stats["skipped_previous"] += 1
                continue
            if prev_path and prev_path.exists() and args.previous_mode == "copy" and not args.overwrite:
                q_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(prev_path, pred_path)
                dump_json(evidence_path, {"question_id": qid, "copied_from_previous": str(prev_path), "warning": "prediction copied, no new evidence generated"})
                stats["copied_previous"] += 1
                continue

            vid = item.get("video", item.get("video_id", qid.split("_")[0]))
            video_path = resolve_video_path(args.video_root, str(vid), args.frames_fallback_root)
            raw_frames, raw_meta = load_frames_oversampled(
                video_path,
                args.oversample_count,
                args.visual_view_budget if args.fair_method == "external_temporal" else 0,
            )
            if not raw_frames:
                stats["missing_video_or_frames"] += 1
                append_jsonl(errors_path, {"question_id": qid, "global_idx": global_idx, "error": "no_frames", "video": vid, "video_path": video_path})
                continue

            asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(str(vid), "") or ""
            (
                selected_frames,
                selected_meta,
                final_input_frames,
                crop_metas,
                visual_plan,
                adslot_route,
                fair_trace,
            ) = build_fair_visual_sequence(
                s23,
                raw_frames,
                raw_meta,
                item,
                asr_text,
                temporal_cache,
            )
            effective_top_k = int(fair_trace["global_count"])

            rag_trace = {"mode": args.rag_mode, "query": "", "retrieved": [], "filtered_by_leakage_guard": []}
            rag_context = ""
            if rag_engine is not None and args.rag_v2:
                from rag.question_router import route_question
                from rag.evidence_cues import build_evidence_cues
                from rag.rag_policy import build_rag_policy
                from rag.reranker import rerank_candidates
                from rag.rag_prompt_builder import build_rag_query_v2, build_structured_rag_block

                route = route_question(item["question"], asr_text=asr_text)
                cues = build_evidence_cues(
                    question=item["question"],
                    asr_text=asr_text,
                    selected_frames=selected_meta,
                    crop_metas=crop_metas,
                )
                policy = build_rag_policy(route, cues, default_mode=args.rag_mode, strict_no_leak=args.strict_no_leak)
                if str(route.get("primary_type", "")) in set(args.rag_disable_types or []):
                    policy["enabled"] = False
                    policy["reason"] = "disabled_by_cli_type_gate:" + str(route.get("primary_type", ""))
                policy["top_k"] = min(int(policy.get("top_k", args.rag_topk) or args.rag_topk), int(args.rag_topk))
                rag_query = ""
                candidate_trace = {"retrieved": [], "filtered_by_leakage_guard": [], "filtered_by_category": []}
                reranked = []
                chosen = []
                if policy.get("enabled"):
                    rag_query = build_rag_query_v2(item["question"], asr_text, cues=cues, route=route)
                    candidate_trace = rag_engine.retrieve_candidates(
                        rag_query,
                        top_k=max(args.rag_candidate_k, int(policy.get("top_k", args.rag_topk)) * 3),
                        question_id=qid,
                        video_id=str(vid),
                        strict_no_leak=args.strict_no_leak,
                        allowed_categories=policy.get("allowed_categories"),
                        blocked_categories=policy.get("blocked_categories"),
                    )
                    reranked = rerank_candidates(
                        candidate_trace.get("retrieved", []),
                        route=route,
                        cues=cues,
                        question=item["question"],
                        asr_text=asr_text,
                    )
                    chosen = reranked[: int(policy.get("top_k", args.rag_topk) or args.rag_topk)]
                    rag_context = build_structured_rag_block(route, cues, chosen, policy)
                rag_trace = {
                    "mode": args.rag_mode,
                    "version": "v2",
                    "query": rag_query,
                    "route": route,
                    "policy": policy,
                    "cues": cues,
                    "candidates": candidate_trace.get("retrieved", []),
                    "reranked": reranked,
                    "retrieved": chosen,
                    "filtered_by_leakage_guard": candidate_trace.get("filtered_by_leakage_guard", []),
                    "filtered_by_category": candidate_trace.get("filtered_by_category", []),
                }
            elif rag_engine is not None:
                from rag.rag_prompt_builder import build_rag_query, format_knowledge_for_prompt
                evidence_for_query = {"selected_frames": selected_meta}
                rag_query = build_rag_query(item["question"], asr_text, evidence_for_query)
                rag_trace = rag_engine.retrieve(
                    rag_query,
                    top_k=args.rag_topk,
                    question_id=qid,
                    video_id=str(vid),
                    strict_no_leak=args.strict_no_leak,
                )
                rag_context = format_knowledge_for_prompt(rag_trace.get("retrieved", []), max_rules=args.rag_topk)

            prompt_1 = CoTReflectionPrompts.initial_prompt(item["question"], asr_text, rag_context)
            t_gen1 = time.time()
            ans_1, processor_trace = generate_response(
                model,
                processor,
                final_input_frames,
                prompt_1,
                args.max_new_tokens,
            )
            gen1_sec = time.time() - t_gen1

            q_lower = item["question"].lower()
            needs_reflect = (not args.disable_reflection) and any(t.lower() in q_lower for t in args.reflection_triggers)
            final_ans, status, reflection_text, gen2_sec = ans_1, "Skipped", "", 0.0
            prompt_2 = ""
            if needs_reflect:
                prompt_2 = CoTReflectionPrompts.reflection_prompt(item["question"], ans_1)
                t_gen2 = time.time()
                reflection_text, _ = generate_response(
                    model,
                    processor,
                    final_input_frames,
                    prompt_2,
                    args.reflection_max_new_tokens,
                )
                gen2_sec = time.time() - t_gen2
                if "[Final Answer]:" in reflection_text:
                    final_ans = reflection_text.split("[Final Answer]:", 1)[-1].strip()
                    status = "Corrected"
                elif "[KEEP]" in reflection_text:
                    status = "Verified"
                elif len(reflection_text.strip()) > 20:
                    final_ans = reflection_text.strip()
                    status = "UnstructuredCorrection"
                else:
                    status = "UnclearKeepInitial"

            q_dir.mkdir(parents=True, exist_ok=True)
            prediction_record = {
                "question_id": qid,
                "prediction": final_ans,
                "ground_truth": gt_map.get(qid, "N/A"),
                "initial_reasoning": ans_1,
                "pipeline": f"Fair_Budget_V1_{args.fair_method}_{model_label}",
                "reflection_status": status,
                "rag_mode": "none",
                "adslot_mode": "on" if args.fair_method in {"adslot_fixed", "coverage_adslot"} else "off",
                "adslot_route": adslot_route,
                "retrieved_knowledge_ids": [x.get("knowledge_id") for x in rag_trace.get("retrieved", [])],
                "score": "",
            }
            dump_json(pred_path, prediction_record)

            image_records = []
            if args.save_evidence_images:
                image_records = save_evidence_images(q_dir, final_input_frames, visual_plan)

            evidence_record = {
                "question_id": qid,
                "global_idx": global_idx,
                "video_id": vid,
                "video_path": video_path,
                "question": item.get("question", ""),
                "asr_excerpt": asr_text[:1000],
                "raw_sample_count": len(raw_frames),
                "selected_count": len(selected_frames),
                "input_image_count": len(final_input_frames),
                "fair_protocol": fair_trace,
                "processor_trace": processor_trace,
                "visual_plan": visual_plan,
                "adslot_route": adslot_route,
                "selected_frames": selected_meta,
                "crop_metas": crop_metas,
                "rag_trace": rag_trace,
                "image_records": image_records,
                "generation": {
                    "max_new_tokens": args.max_new_tokens,
                    "reflection_max_new_tokens": args.reflection_max_new_tokens,
                    "gen1_seconds": gen1_sec,
                    "gen2_seconds": gen2_sec,
                    "total_seconds": time.time() - q_start,
                    "processor_trace": processor_trace,
                },
                "reflection": {
                    "enabled": not args.disable_reflection,
                    "triggered": needs_reflect,
                    "status": status,
                    "reflection_text": reflection_text,
                },
                "config_subset": {
                    "oversample_count": args.oversample_count,
                    "top_k_frames": args.top_k_frames,
                    "effective_top_k_frames": effective_top_k,
                    "fair_method": args.fair_method,
                    "visual_view_budget": args.visual_view_budget,
                    "max_post_merge_visual_tokens": args.max_post_merge_visual_tokens,
                    "adslot_mode": "on" if args.fair_method in {"adslot_fixed", "coverage_adslot"} else "off",
                    "unified_size": args.unified_size,
                    "crop_scales": args.crop_scales,
                    "select_weights": {"question": args.select_question_weight, "audio": args.select_audio_weight},
                    "crop_weights": {"question": args.question_weight, "audio": args.audio_weight, "ocr": args.ocr_weight},
                },
            }
            if args.save_prompts:
                evidence_record["prompts"] = {"initial": prompt_1, "reflection": prompt_2}
            dump_json(evidence_path, evidence_record)
            if args.rag_mode != "none":
                dump_json(q_dir / "rag_trace.json", rag_trace)

            stats["processed"] += 1
            if stats["processed"] % 10 == 0:
                LOGGER.info("Progress stats: %s", stats)

        except Exception as e:
            stats["errors"] += 1
            LOGGER.error("Inference failed qid=%s: %s", qid, e)
            append_jsonl(errors_path, {
                "question_id": qid,
                "global_idx": global_idx,
                "error": repr(e),
                "traceback": traceback.format_exc(),
            })
        finally:
            try:
                torch.cuda.empty_cache()
                gc.collect()
            except Exception:
                pass

    run_config["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    run_config["stats"] = stats
    dump_json(output_dir / f"run_summary_gpu{args.gpu_id}_shard{args.shard_id}.json", run_config)
    LOGGER.info("Done. Final stats: %s", stats)


if __name__ == "__main__":
    main()
