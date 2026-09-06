#!/usr/bin/env python3
"""AdsQA innovation 1: dynamic audio-visual response and budgeted crops.

The answer model is frozen. This entrypoint changes only evidence localization
and visual input reconstruction. RAG and reflection are intentionally absent so
the method can be compared against the existing evidence baseline cleanly.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any


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
    parser = argparse.ArgumentParser(description="AdsQA dynamic audio-visual evidence response V1")

    parser.add_argument("--gpu_id", required=True, help="Physical GPU id")
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=-1)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--model_dir", default="/data1/qky/Model/Qwen3Vl-8B")
    parser.add_argument("--clip_path", default="/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14")
    parser.add_argument("--video_root", default="/data1/rmx/projectb/AdsQA-main/data/videos")
    parser.add_argument("--frames_fallback_root", default="/data1/rmx/projectb/AdsQA-main/data/frames_8")
    parser.add_argument("--question_file", default="/data1/rmx/projectb/AdsQA-main/data/testset_question.json")
    parser.add_argument("--groundtruth_file", default="/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json")
    parser.add_argument("--asr_file", default="/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json")
    parser.add_argument("--output_dir", default="/data1/rmx/projectb/AdsQA-main/evaluation/runs/av_evidence_budget_v1")

    parser.add_argument("--oversample_count", type=int, default=32)
    parser.add_argument("--top_k_frames", type=int, default=16)
    parser.add_argument("--temporal_coverage_bins", type=int, default=0)
    parser.add_argument("--global_question_weight", type=float, default=-1.0)
    parser.add_argument("--global_audio_weight", type=float, default=-1.0)
    parser.add_argument("--visual_image_budget", type=int, default=32)
    parser.add_argument("--max_post_merge_visual_tokens", type=int, default=12000)
    parser.add_argument("--unified_size", type=int, default=896)
    parser.add_argument("--crop_scales", type=float, nargs="*", default=[0.50, 0.70, 0.85])
    parser.add_argument("--crop_coverage_target", type=float, default=0.60)
    parser.add_argument("--max_response_peaks", type=int, default=4)
    parser.add_argument("--min_peak_distance", type=int, default=2)
    parser.add_argument("--crop_nms_iou", type=float, default=0.65)
    parser.add_argument("--max_crop_candidates_per_frame", type=int, default=6)
    parser.add_argument("--max_local_views_per_frame", type=int, default=2)
    parser.add_argument("--focus_context_budget", type=int, default=0)
    parser.add_argument("--focus_context_global_fraction", type=float, default=0.50)
    parser.add_argument(
        "--spatial_response_mode",
        choices=["patch_cosine", "contrastive_gradient"],
        default="patch_cosine",
    )
    parser.add_argument("--ocr_proxy", choices=["off", "semantic", "cache"], default="semantic")
    parser.add_argument("--ocr_proxy_reliability", type=float, default=0.35)
    parser.add_argument("--ocr_cache_file", default="")
    parser.add_argument("--ocr_min_confidence", type=float, default=0.50)
    parser.add_argument(
        "--ocr_relevance_scope",
        choices=["frame", "video", "train_null"],
        default="frame",
    )
    parser.add_argument(
        "--ocr_null_question_file",
        default="/data1/rmx/projectb/AdsQA-main/data/train.json",
    )
    parser.add_argument(
        "--response_fusion",
        choices=["dynamic_prior", "consistency_calibrated"],
        default="dynamic_prior",
    )
    parser.add_argument(
        "--consistency_perturbations",
        nargs="*",
        default=["original", "blur", "downscale"],
    )
    parser.add_argument("--uncertainty_temperature", type=float, default=0.50)
    parser.add_argument("--uncertainty_refinement_weight", type=float, default=0.25)
    parser.add_argument("--reliability_floor", type=float, default=0.35)
    parser.add_argument("--consistency_downscale_ratio", type=float, default=0.75)
    parser.add_argument("--timestamped_asr_reliability", type=float, default=0.90)
    parser.add_argument("--global_asr_reliability", type=float, default=0.25)

    parser.add_argument("--asr_window_seconds", type=float, default=3.0)
    parser.add_argument("--asr_offset_candidates", type=float, nargs="*", default=[-4.0, -2.0, 0.0, 2.0, 4.0])
    parser.add_argument("--disable_offset_estimation", action="store_true")

    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--save_prompts", action="store_true")
    parser.add_argument("--save_evidence_images", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--localization_only", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    return parser.parse_args()


args = parse_args()
if (args.global_question_weight >= 0) != (args.global_audio_weight >= 0):
    raise ValueError("global_question_weight and global_audio_weight must be overridden together")
if args.global_question_weight == 0 and args.global_audio_weight == 0:
    raise ValueError("global selection weights cannot both be zero")
METHOD_NAME = (
    "reliability_calibrated_av_response_budget_v2"
    if args.response_fusion == "consistency_calibrated"
    else "dynamic_av_response_budget_v1"
)
if args.ocr_proxy == "cache":
    METHOD_NAME += "_cached_ocr"
    if args.ocr_relevance_scope == "video":
        METHOD_NAME += "_video_relevance"
    elif args.ocr_relevance_scope == "train_null":
        METHOD_NAME += "_train_null"
if args.focus_context_budget:
    METHOD_NAME += "_focus_context"
if args.spatial_response_mode == "contrastive_gradient":
    METHOD_NAME += "_contrastive_gradient"
ENTRYPOINT_PATH = os.environ.get("ADSQA_ENTRYPOINT", str(Path(__file__).resolve()))
SUPPORTED_PERTURBATIONS = {"original", "blur", "downscale"}
unsupported_perturbations = set(args.consistency_perturbations) - SUPPORTED_PERTURBATIONS
if unsupported_perturbations:
    raise ValueError(f"unsupported consistency perturbations: {sorted(unsupported_perturbations)}")
if args.uncertainty_temperature <= 0.0:
    raise ValueError("uncertainty_temperature must be positive")
if args.uncertainty_refinement_weight < 0.0:
    raise ValueError("uncertainty_refinement_weight must be non-negative")
if not 0.0 <= args.reliability_floor <= 1.0:
    raise ValueError("reliability_floor must be in [0, 1]")
if not 0.0 < args.consistency_downscale_ratio <= 1.0:
    raise ValueError("consistency_downscale_ratio must be in (0, 1]")
if not 0.0 <= args.timestamped_asr_reliability <= 1.0:
    raise ValueError("timestamped_asr_reliability must be in [0, 1]")
if not 0.0 <= args.global_asr_reliability <= 1.0:
    raise ValueError("global_asr_reliability must be in [0, 1]")
if args.focus_context_budget < 0 or args.focus_context_budget > args.visual_image_budget:
    raise ValueError("focus_context_budget must be in [0, visual_image_budget]")
if args.focus_context_budget and args.max_local_views_per_frame != 1:
    raise ValueError("focus-context mode requires max_local_views_per_frame=1")
if not 0.35 <= args.focus_context_global_fraction <= 0.75:
    raise ValueError("focus_context_global_fraction must be in [0.35, 0.75]")
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


def run_early_dry_run() -> None:
    """Validate data and paths without importing torch/transformers."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    asr_data = json.loads(Path(args.asr_file).read_text(encoding="utf-8")) if Path(args.asr_file).exists() else {}
    end_index = len(questions) if args.end_idx < 0 else min(args.end_idx, len(questions))
    start_index = max(0, args.start_idx)
    indexed = list(enumerate(questions[start_index:end_index], start=start_index))
    shard_items = [(index, item) for index, item in indexed if index % args.num_shards == args.shard_id]

    preview = []
    for index, item in shard_items[:10]:
        question_id = str(item["question_id"])
        video_id = str(item.get("video", item.get("video_id", question_id.split("_")[0])))
        candidates = [
            Path(args.video_root) / f"{video_id}.mp4",
            Path(args.video_root) / video_id,
            Path(args.video_root) / f"{video_id}.webm",
            Path(args.video_root) / f"{video_id}.mov",
            Path(args.frames_fallback_root) / video_id,
        ]
        video_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        raw_asr = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, ""))
        has_segments = isinstance(raw_asr, dict) and bool(raw_asr.get("segments") or raw_asr.get("chunks"))
        asr_mode = "timestamped_segments" if has_segments else "global_text" if isinstance(raw_asr, str) and raw_asr.strip() else "missing"
        preview.append({
            "global_idx": index,
            "question_id": question_id,
            "video_id": video_id,
            "video_path": str(video_path),
            "video_path_exists": video_path.exists(),
            "asr_mode": asr_mode,
        })

    run_config = vars(args).copy()
    run_config.update({
        "method": METHOD_NAME,
        "script": ENTRYPOINT_PATH,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rag_enabled": False,
        "reflection_enabled": False,
        "answer_prompt_version": ADSQA_ANSWER_PROMPT_VERSION,
        "answer_prompt_template_sha256": adsqa_answer_prompt_sha256(),
        "dry_run_fast_path": True,
        "visual_budget_unit": "submitted_pil_frames",
    })
    (output_dir / "run_config.json").write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "dry_run_preview.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dry run complete: items={len(preview)} output={output_dir}")


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
    from transformers import AutoModelForVision2Seq, AutoProcessor
    from transformers import CLIPTextModelWithProjection, CLIPTokenizer, CLIPVisionModelWithProjection
except Exception as import_error:
    print(f"[ImportError] {import_error}", file=sys.stderr)
    raise

try:
    from decord import VideoReader, cpu

    DECORD_AVAILABLE = True
except Exception:
    DECORD_AVAILABLE = False

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.methods.common.qwen_video_budget import prepare_qwen_video_inputs

from av_response import (
    allocate_local_budget,
    fuse_consistency_calibrated_responses,
    fuse_dynamic_responses,
    generate_multipeak_candidates,
    normalize_asr,
    question_modality_priors,
    response_region_statistics,
    select_topk_with_temporal_coverage,
    windowed_asr_text,
)
from ocr_response import (
    empirical_null_confidence,
    load_ocr_cache,
    load_question_bank,
    normalize_ocr_relevance,
    rasterize_ocr_response,
    validate_ocr_frame_coverage,
    validate_ocr_question_coverage,
)
from focus_context import compose_focus_context


LOGGER = logging.getLogger("adsqa_av_evidence_v1")


def setup_logging(output_dir: Path) -> None:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"inference_gpu{args.gpu_id}_shard{args.shard_id}of{args.num_shards}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, mode="a", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        force=True,
    )


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def smart_resize(image: Image.Image) -> Image.Image:
    return image.resize((args.unified_size, args.unified_size), Image.BICUBIC)


def load_groundtruth_map(path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path or not Path(path).exists():
        return result
    for item in json.loads(Path(path).read_text(encoding="utf-8")):
        answer = item.get("answer", item.get("gt_answer", item.get("answers", "N/A")))
        if isinstance(answer, list):
            answer = "; ".join(map(str, answer))
        result[str(item.get("question_id"))] = str(answer)
    return result


def resolve_video_path(video_id: str) -> str:
    candidates = [
        Path(args.video_root) / f"{video_id}.mp4",
        Path(args.video_root) / video_id,
        Path(args.video_root) / f"{video_id}.webm",
        Path(args.video_root) / f"{video_id}.mov",
        Path(args.frames_fallback_root) / video_id,
    ]
    for candidate in candidates:
        if candidate.exists() and (DECORD_AVAILABLE or candidate.is_dir()):
            return str(candidate)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def load_frames_oversampled(video_path: str, sample_count: int) -> tuple[list[Image.Image], list[dict[str, Any]]]:
    frames: list[Image.Image] = []
    metadata: list[dict[str, Any]] = []
    path = Path(video_path)
    if not path.exists():
        return frames, metadata

    if DECORD_AVAILABLE and path.is_file():
        try:
            reader = VideoReader(str(path), ctx=cpu(0))
            frame_count = len(reader)
            fps = float(reader.get_avg_fps()) if frame_count else 0.0
            if frame_count > 0:
                indices = np.linspace(0, frame_count - 1, sample_count, dtype=int)
                for sample_rank, frame_index in enumerate(indices.tolist()):
                    frames.append(Image.fromarray(reader[frame_index].asnumpy()).convert("RGB"))
                    metadata.append({
                        "sample_rank": sample_rank,
                        "source": "video",
                        "frame_index": int(frame_index),
                        "total_frames": int(frame_count),
                        "fps": fps,
                        "timestamp_sec": float(frame_index / fps) if fps > 0 else None,
                        "normalized_time": float(frame_index / max(frame_count - 1, 1)),
                    })
                return frames, metadata
        except Exception as error:
            LOGGER.warning("Video decode failed for %s: %s", video_path, error)

    if path.is_dir():
        files = sorted(path.glob("*.jpg")) + sorted(path.glob("*.png"))
        if files:
            indices = np.linspace(0, len(files) - 1, sample_count, dtype=int)
            for sample_rank, frame_index in enumerate(indices.tolist()):
                frame_file = files[frame_index]
                try:
                    frames.append(Image.open(frame_file).convert("RGB"))
                    metadata.append({
                        "sample_rank": sample_rank,
                        "source": "frames",
                        "frame_index": int(frame_index),
                        "frame_file": str(frame_file),
                        "total_frames": len(files),
                        "fps": None,
                        "timestamp_sec": None,
                        "normalized_time": float(frame_index / max(len(files) - 1, 1)),
                    })
                except Exception as error:
                    LOGGER.warning("Frame open failed for %s: %s", frame_file, error)
    return frames, metadata


class VisualEvidenceProcessor:
    def __init__(self, device: str, clip_path: str):
        self.device = device
        self.valid = False
        self.error = ""
        self._text_cache: dict[str, Any] = {}
        self.ocr_null_question_embeddings = None
        self.ocr_null_question_count = 0
        try:
            options = {"local_files_only": True, "ignore_mismatched_sizes": True}
            self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, **options).to(device).eval()
            self.text_encoder = CLIPTextModelWithProjection.from_pretrained(clip_path, **options).to(device).eval()
            self.vision.requires_grad_(False)
            self.text_encoder.requires_grad_(False)
            self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
            from torchvision.transforms import Normalize, ToTensor

            self.normalize = Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))
            self.to_tensor = ToTensor()
            if args.ocr_proxy == "cache" and args.ocr_relevance_scope == "train_null":
                question_bank = load_question_bank(args.ocr_null_question_file)
                embeddings = []
                for start in range(0, len(question_bank), 128):
                    embeddings.append(self._encode_texts(question_bank[start:start + 128]))
                self.ocr_null_question_embeddings = torch.cat(embeddings, dim=0)
                self.ocr_null_question_count = len(question_bank)
            self.valid = True
        except Exception as error:
            self.error = repr(error)
            LOGGER.warning("CLIP evidence processor unavailable: %s", error)

    def _preprocess(self, image: Image.Image):
        try:
            image = image.convert("RGB").resize((224, 224), Image.BICUBIC)
            tensor = self.to_tensor(image)
            if tensor.shape[0] == 1:
                tensor = tensor.repeat(3, 1, 1)
            elif tensor.shape[0] == 4:
                tensor = tensor[:3]
            return self.normalize(tensor) if tensor.shape[0] == 3 else None
        except Exception:
            return None

    def _response_observations(self, tensor):
        names = ["original"]
        if args.response_fusion == "consistency_calibrated":
            names.extend(args.consistency_perturbations)
        names = list(dict.fromkeys(names))
        observations = []
        source = tensor.unsqueeze(0)
        for name in names:
            if name == "original":
                observation = tensor
            elif name == "blur":
                observation = F.avg_pool2d(source, kernel_size=3, stride=1, padding=1).squeeze(0)
            elif name == "downscale":
                target = max(32, int(round(tensor.shape[-1] * args.consistency_downscale_ratio)))
                reduced = F.interpolate(source, size=(target, target), mode="bilinear", align_corners=False)
                observation = F.interpolate(
                    reduced,
                    size=tensor.shape[-2:],
                    mode="bilinear",
                    align_corners=False,
                ).squeeze(0)
            else:
                raise ValueError(f"unsupported response perturbation: {name}")
            observations.append(observation)
        return torch.stack(observations), names

    def _encode_text(self, text: str):
        key = (text or "")[:300]
        if not key:
            return None
        if key not in self._text_cache:
            tokens = self.tokenizer(
                [key],
                padding=True,
                truncation=True,
                max_length=77,
                return_tensors="pt",
            ).to(self.device)
            self._text_cache[key] = F.normalize(self.text_encoder(**tokens).text_embeds, dim=-1)
        return self._text_cache[key]

    def _encode_texts(self, texts: list[str]):
        if not texts:
            return None
        tokens = self.tokenizer(
            [text[:300] for text in texts],
            padding=True,
            truncation=True,
            max_length=77,
            return_tensors="pt",
        ).to(self.device)
        return F.normalize(self.text_encoder(**tokens).text_embeds, dim=-1)

    def _global_image_embeddings(self, frames: list[Image.Image]):
        processed, indices = [], []
        for index, frame in enumerate(frames):
            tensor = self._preprocess(frame)
            if tensor is not None:
                processed.append(tensor)
                indices.append(index)
        if not processed:
            return None, []
        batch = torch.stack(processed).to(self.device)
        return F.normalize(self.vision(batch).image_embeds, dim=-1), indices

    def _contrastive_gradient_map(self, tensor, text_embedding, side: int):
        """Attribute global image-text agreement to spatial input patches."""
        if text_embedding is None:
            return None, {"mode": "contrastive_gradient", "available": False}
        with torch.enable_grad():
            image_input = tensor.detach().unsqueeze(0).to(self.device).requires_grad_(True)
            image_embedding = F.normalize(self.vision(image_input).image_embeds, dim=-1)
            score = torch.sum(image_embedding * text_embedding.detach())
            gradient = torch.autograd.grad(score, image_input, retain_graph=False)[0]
            contribution = torch.relu(gradient * image_input).sum(dim=1, keepdim=True)
            positive_mass = float(contribution.sum().detach().cpu())
            if positive_mass <= 1e-12:
                contribution = torch.abs(gradient * image_input).sum(dim=1, keepdim=True)
            pooled = F.adaptive_avg_pool2d(contribution, (side, side)).squeeze(0).squeeze(0)
        values = pooled.detach().float().cpu().numpy()
        return values, {
            "mode": "contrastive_gradient",
            "available": True,
            "global_similarity": float(score.detach().cpu()),
            "positive_mass": positive_mass,
            "raw_min": float(values.min()),
            "raw_max": float(values.max()),
        }

    def estimate_audio_offset(
        self,
        frames: list[Image.Image],
        frame_metadata: list[dict[str, Any]],
        asr_evidence: dict[str, Any],
    ) -> dict[str, Any]:
        if args.disable_offset_estimation:
            return {"mode": "disabled", "offset_seconds": 0.0, "candidate_scores": {}}
        if not asr_evidence.get("has_timestamps"):
            return {"mode": "global_asr_no_timestamps", "offset_seconds": 0.0, "candidate_scores": {}}
        if not self.valid or not any(item.get("timestamp_sec") is not None for item in frame_metadata):
            return {"mode": "unavailable", "offset_seconds": 0.0, "candidate_scores": {}}

        with torch.no_grad():
            image_embeddings, valid_indices = self._global_image_embeddings(frames)
            if image_embeddings is None:
                return {"mode": "image_encoding_failed", "offset_seconds": 0.0, "candidate_scores": {}}
            candidate_scores: dict[str, float | None] = {}
            for offset in args.asr_offset_candidates:
                texts, image_rows = [], []
                for embedding_row, frame_index in enumerate(valid_indices):
                    text, _ = windowed_asr_text(
                        asr_evidence,
                        frame_metadata[frame_index].get("timestamp_sec"),
                        radius=args.asr_window_seconds,
                        offset=float(offset),
                    )
                    if text:
                        texts.append(text)
                        image_rows.append(embedding_row)
                if not texts:
                    candidate_scores[str(float(offset))] = None
                    continue
                text_embeddings = self._encode_texts(texts)
                similarities = (image_embeddings[image_rows] * text_embeddings).sum(dim=-1)
                candidate_scores[str(float(offset))] = float(similarities.mean().detach().cpu())
            valid_scores = {key: value for key, value in candidate_scores.items() if value is not None}
            if not valid_scores:
                return {"mode": "no_aligned_segments", "offset_seconds": 0.0, "candidate_scores": candidate_scores}
            best = max(valid_scores, key=valid_scores.get)
            return {"mode": "clip_offset_search", "offset_seconds": float(best), "candidate_scores": candidate_scores}

    def select_frames(
        self,
        frames: list[Image.Image],
        frame_metadata: list[dict[str, Any]],
        question: str,
        asr_evidence: dict[str, Any],
        audio_offset: float,
        top_k: int,
    ) -> tuple[list[Image.Image], list[dict[str, Any]]]:
        if not frames:
            return [], []
        top_k = min(max(int(top_k), 1), len(frames))
        if not self.valid:
            return frames[:top_k], [dict(item, selection_mode="uniform_fallback") for item in frame_metadata[:top_k]]

        with torch.no_grad():
            image_embeddings, valid_indices = self._global_image_embeddings(frames)
            if image_embeddings is None:
                return frames[:top_k], [dict(item, selection_mode="image_encoding_fallback") for item in frame_metadata[:top_k]]
            question_embedding = self._encode_text(question)
            question_scores = (
                torch.matmul(image_embeddings, question_embedding.T).view(-1)
                if question_embedding is not None
                else torch.zeros(image_embeddings.shape[0], device=self.device)
            )

            audio_texts: list[str] = []
            audio_traces: list[dict[str, Any]] = []
            for frame_index in valid_indices:
                text, trace = windowed_asr_text(
                    asr_evidence,
                    frame_metadata[frame_index].get("timestamp_sec"),
                    radius=args.asr_window_seconds,
                    offset=audio_offset,
                )
                audio_texts.append(text)
                audio_traces.append(trace)

            audio_scores = torch.zeros_like(question_scores)
            nonempty = [index for index, text in enumerate(audio_texts) if text]
            if nonempty:
                if len(set(audio_texts[index] for index in nonempty)) == 1:
                    audio_embedding = self._encode_text(audio_texts[nonempty[0]])
                    audio_scores[nonempty] = torch.matmul(image_embeddings[nonempty], audio_embedding.T).view(-1)
                else:
                    audio_embeddings = self._encode_texts([audio_texts[index] for index in nonempty])
                    audio_scores[nonempty] = (image_embeddings[nonempty] * audio_embeddings).sum(dim=-1)

            fixed_global_weights = args.global_question_weight >= 0
            if fixed_global_weights:
                question_weight = args.global_question_weight
                audio_weight = args.global_audio_weight if nonempty else 0.0
            else:
                priors = question_modality_priors(question)
                question_weight = priors["question"]
                audio_weight = priors["audio"] if nonempty else 0.0
            denominator = question_weight + audio_weight or 1.0
            question_weight /= denominator
            audio_weight /= denominator
            scores = question_weight * question_scores + audio_weight * audio_scores
            score_values = scores.detach().cpu().numpy()
            if args.temporal_coverage_bins > 0:
                chosen_rows, coverage_trace = select_topk_with_temporal_coverage(
                    score_values,
                    top_k=top_k,
                    coverage_bins=args.temporal_coverage_bins,
                )
            else:
                chosen_rows = sorted(np.argsort(score_values)[-top_k:].tolist())
                coverage_trace = {
                    "mode": "score_topk",
                    "coverage_bins": 0,
                    "anchor_rows": [],
                    "selected_rows": chosen_rows,
                }
            score_order = {row: rank for rank, row in enumerate(np.argsort(score_values)[::-1].tolist())}
            coverage_anchors = set(coverage_trace["anchor_rows"])

            selected_frames = [frames[valid_indices[row]] for row in chosen_rows]
            selected_metadata: list[dict[str, Any]] = []
            for temporal_order, row in enumerate(chosen_rows):
                original_index = valid_indices[row]
                item = dict(frame_metadata[original_index])
                item.update({
                    "temporal_order": temporal_order,
                    "selection_rank": score_order[row],
                    "selection_score": safe_float(score_values[row]),
                    "question_score": safe_float(question_scores[row].detach().cpu()),
                    "audio_score": safe_float(audio_scores[row].detach().cpu()),
                    "selection_mode": (
                        "question_audio_fixed_prior_temporal_coverage"
                        if fixed_global_weights and coverage_trace["coverage_bins"]
                        else "question_audio_dynamic_prior_temporal_coverage"
                        if coverage_trace["coverage_bins"]
                        else "question_audio_fixed_prior"
                        if fixed_global_weights
                        else "question_audio_dynamic_prior"
                    ),
                    "temporal_coverage_bins": coverage_trace["coverage_bins"],
                    "temporal_coverage_anchor": row in coverage_anchors,
                    "selection_weights": {"question": question_weight, "audio": audio_weight},
                    "audio_window_text": audio_texts[row][:500],
                    "audio_window_trace": audio_traces[row],
                })
                selected_metadata.append(item)
            return selected_frames, selected_metadata

    def crop_candidates(
        self,
        frame: Image.Image,
        question: str,
        audio_text: str,
        audio_mode: str,
        ocr_detections: list[dict[str, Any]] | None = None,
    ) -> tuple[list[tuple[Image.Image, dict[str, Any]]], dict[str, Any]]:
        if not self.valid:
            return [], {"mode": "clip_unavailable", "error": self.error}
        with torch.no_grad():
            tensor = self._preprocess(frame)
            if tensor is None:
                return [], {"mode": "frame_preprocess_failed"}
            observation_tensors, observation_names = self._response_observations(tensor)
            vision_output = self.vision(observation_tensors.to(self.device))
            patch_embeddings = vision_output.last_hidden_state[:, 1:]
            if hasattr(self.vision, "visual_projection"):
                patch_embeddings = self.vision.visual_projection(patch_embeddings)
            patch_embeddings = F.normalize(patch_embeddings, dim=-1)

            question_embedding = self._encode_text(question)
            question_maps = (
                torch.matmul(patch_embeddings, question_embedding.T).squeeze(-1)
                if question_embedding is not None
                else None
            )
            spatial_response_trace: dict[str, Any] = {"mode": "patch_cosine"}
            audio_embedding = self._encode_text(audio_text)
            audio_maps = (
                torch.matmul(patch_embeddings, audio_embedding.T).squeeze(-1)
                if audio_embedding is not None
                else None
            )

            ocr_maps = None
            ocr_trace: dict[str, Any] = {"mode": "off"}
            if args.ocr_proxy == "semantic":
                ocr_embeddings = self._encode_texts(["text", "logo", "brand", "words"])
                ocr_maps = torch.matmul(patch_embeddings, ocr_embeddings.T).max(dim=-1).values
                ocr_trace = {"mode": "semantic_proxy_not_real_ocr"}

            map_length = patch_embeddings.shape[1]
            side = int(map_length**0.5)
            if side <= 0:
                return [], {"mode": "empty_patch_map"}
            if args.spatial_response_mode == "contrastive_gradient":
                attribution, spatial_response_trace = self._contrastive_gradient_map(
                    tensor,
                    question_embedding,
                    side,
                )
                question_maps = (
                    torch.from_numpy(attribution).to(self.device).view(1, side * side)
                    if attribution is not None
                    else None
                )

            if args.ocr_proxy == "cache" and ocr_detections:
                texts = [str(item.get("text", "")) for item in ocr_detections]
                numeric_query = any(term in question.lower() for term in (
                    "how much", "amount", "price", "cost", "saving", "annual", "percent", "number",
                ))
                if args.ocr_relevance_scope == "video":
                    relevance_values = np.asarray(
                        [float(item["_video_relevance"]) for item in ocr_detections],
                        dtype=np.float32,
                    )
                    raw_similarities = [float(item["_video_similarity"]) for item in ocr_detections]
                else:
                    text_embeddings = self._encode_texts(texts)
                    similarities = torch.zeros(len(texts), device=self.device)
                    if text_embeddings is not None and question_embedding is not None:
                        similarities = torch.matmul(text_embeddings, question_embedding.T).view(-1)
                    if (
                        args.ocr_relevance_scope == "frame"
                        and text_embeddings is not None
                        and audio_embedding is not None
                    ):
                        similarities = torch.maximum(
                            similarities,
                            torch.matmul(text_embeddings, audio_embedding.T).view(-1),
                        )
                    raw_similarities = similarities.detach().float().cpu().tolist()
                    relative_relevance = normalize_ocr_relevance(raw_similarities)
                    if args.ocr_relevance_scope == "train_null":
                        if self.ocr_null_question_embeddings is None or text_embeddings is None:
                            raise RuntimeError("OCR train-null question bank is unavailable")
                        null_similarities = torch.matmul(
                            text_embeddings,
                            self.ocr_null_question_embeddings.T,
                        ).detach().float().cpu().numpy()
                        absolute_confidence, null_percentiles = empirical_null_confidence(
                            raw_similarities,
                            null_similarities,
                        )
                        relevance_values = relative_relevance * absolute_confidence
                    else:
                        absolute_confidence = None
                        null_percentiles = None
                        relevance_values = relative_relevance
                    relevance_values = self._apply_numeric_ocr_boost(question, texts, relevance_values)
                ocr_map, ocr_trace = rasterize_ocr_response(
                    ocr_detections,
                    (side, side),
                    relevance_values,
                    min_confidence=args.ocr_min_confidence,
                    source_reliability_mode=(
                        "weighted"
                        if args.ocr_relevance_scope in {"video", "train_null"}
                        else "confidence"
                    ),
                )
                ocr_maps = torch.from_numpy(ocr_map).to(self.device).view(1, side * side)
                ocr_trace.update({
                    "mode": "cached_rapidocr_query_relevance",
                    "texts": texts[:40],
                    "semantic_scores": [float(value) for value in relevance_values[:40]],
                    "numeric_query": numeric_query,
                })
                if args.ocr_relevance_scope == "video":
                    ocr_trace.update({
                        "raw_similarities": raw_similarities[:40],
                        "relevance_scope": "video",
                    })
                elif args.ocr_relevance_scope == "train_null":
                    ocr_trace.update({
                        "raw_similarities": raw_similarities[:40],
                        "null_percentiles": [float(value) for value in null_percentiles[:40]],
                        "absolute_confidences": [float(value) for value in absolute_confidence[:40]],
                        "relevance_scope": "train_null",
                        "null_question_count": self.ocr_null_question_count,
                    })

            def square_maps(value):
                if value is None:
                    return None
                return [
                    row[: side * side].view(side, side).detach().float().cpu().numpy()
                    for row in value
                ]

            response_variants = {
                "question": square_maps(question_maps),
                "audio": square_maps(audio_maps),
                "ocr": square_maps(ocr_maps),
            }
            audio_reliability = (
                args.timestamped_asr_reliability
                if audio_text and audio_mode == "timestamp_window"
                else args.global_asr_reliability
                if audio_text and args.response_fusion == "consistency_calibrated"
                else 0.50
                if audio_text
                else 0.0
            )
            reliabilities = {
                "question": 1.0,
                "audio": audio_reliability,
                "ocr": (
                    args.ocr_proxy_reliability * float(ocr_trace.get("source_reliability", 1.0))
                    if ocr_maps is not None else 0.0
                ),
            }
            auxiliary_maps: dict[str, np.ndarray] = {}
            if args.response_fusion == "consistency_calibrated":
                fused, auxiliary_maps, fusion_trace = fuse_consistency_calibrated_responses(
                    question,
                    response_variants,
                    reliabilities,
                    uncertainty_temperature=args.uncertainty_temperature,
                    refinement_weight=args.uncertainty_refinement_weight,
                    reliability_floor=args.reliability_floor,
                )
            else:
                responses = {
                    name: variants[0] if variants else None
                    for name, variants in response_variants.items()
                }
                fused, fusion_trace = fuse_dynamic_responses(question, responses, reliabilities)
            fusion_trace["observation_names"] = observation_names
            decoded = generate_multipeak_candidates(
                fused,
                image_size=frame.size,
                scales=args.crop_scales,
                coverage_target=args.crop_coverage_target,
                max_peaks=args.max_response_peaks,
                min_peak_distance=args.min_peak_distance,
                nms_iou=args.crop_nms_iou,
                max_candidates=args.max_crop_candidates_per_frame,
            )
            output = []
            for candidate in decoded:
                box = tuple(int(value) for value in candidate["bbox"])
                metadata = dict(candidate)
                region_diagnostics = {
                    name: response_region_statistics(response, candidate["bbox_norm"])
                    for name, response in auxiliary_maps.items()
                }
                metadata.update({
                    "crop_mode": (
                        "reliability_calibrated_av_multipeak"
                        if args.response_fusion == "consistency_calibrated"
                        else "dynamic_av_multipeak"
                    ),
                    "fusion": fusion_trace,
                    "audio_mode": audio_mode,
                    "ocr_mode": ocr_trace.get("mode", "off"),
                    "ocr_trace": ocr_trace,
                    "response_shape": list(fused.shape),
                    "region_diagnostics": region_diagnostics,
                    "spatial_response": spatial_response_trace,
                })
                output.append((frame.crop(box), metadata))
            return output, {
                "mode": args.response_fusion,
                "fusion": fusion_trace,
                "audio_mode": audio_mode,
                "ocr_mode": ocr_trace.get("mode", "off"),
                "ocr_trace": ocr_trace,
                "response_shape": list(fused.shape),
                "candidate_count": len(output),
                "spatial_response": spatial_response_trace,
            }

    @staticmethod
    def _apply_numeric_ocr_boost(
        question: str,
        texts: list[str],
        relevance: np.ndarray,
    ) -> np.ndarray:
        values = np.asarray(relevance, dtype=np.float32).copy()
        numeric_query = any(term in question.lower() for term in (
            "how much", "amount", "price", "cost", "saving", "annual", "percent", "number",
        ))
        if numeric_query:
            for index, text in enumerate(texts):
                if any(character.isdigit() for character in text) or any(
                    symbol in text for symbol in ("£", "$", "%", "€")
                ):
                    values[index] = max(float(values[index]), 0.90)
        return values

    def prepare_video_ocr_relevance(
        self,
        question: str,
        selected_metadata: list[dict[str, Any]],
        ocr_frames: dict[int, list[dict[str, Any]]],
    ) -> tuple[dict[int, list[dict[str, Any]]], dict[str, Any]]:
        records: list[tuple[int, dict[str, Any], str]] = []
        for metadata in selected_metadata:
            sample_rank = int(metadata["sample_rank"])
            audio_text = str(metadata.get("audio_window_text", ""))
            for detection in ocr_frames[sample_rank]:
                records.append((sample_rank, dict(detection), audio_text))
        if not records:
            return {rank: [dict(item) for item in detections] for rank, detections in ocr_frames.items()}, {
                "scope": "video",
                "detection_count": 0,
            }

        texts = [str(detection.get("text", "")) for _, detection, _ in records]
        text_embeddings = self._encode_texts(texts)
        question_embedding = self._encode_text(question)
        similarities = torch.zeros(len(records), device=self.device)
        if text_embeddings is not None and question_embedding is not None:
            similarities = torch.matmul(text_embeddings, question_embedding.T).view(-1)

        audio_groups: dict[str, list[int]] = {}
        for index, (_, _, audio_text) in enumerate(records):
            if audio_text:
                audio_groups.setdefault(audio_text, []).append(index)
        if text_embeddings is not None:
            for audio_text, indices in audio_groups.items():
                audio_embedding = self._encode_text(audio_text)
                if audio_embedding is None:
                    continue
                index_tensor = torch.tensor(indices, device=self.device)
                audio_scores = torch.matmul(text_embeddings[index_tensor], audio_embedding.T).view(-1)
                similarities[index_tensor] = torch.maximum(similarities[index_tensor], audio_scores)

        raw_values = similarities.detach().float().cpu().numpy()
        base_relevance = normalize_ocr_relevance(raw_values)
        relevance = self._apply_numeric_ocr_boost(question, texts, base_relevance)
        prepared = {rank: [] for rank in ocr_frames}
        for (sample_rank, detection, _), raw, score in zip(records, raw_values, relevance):
            detection["_video_similarity"] = float(raw)
            detection["_video_relevance"] = float(score)
            prepared[sample_rank].append(detection)
        return prepared, {
            "scope": "video",
            "detection_count": len(records),
            "similarity_min": float(raw_values.min()),
            "similarity_max": float(raw_values.max()),
            "relevance_mean": float(relevance.mean()),
            "numeric_boost_count": int(np.sum(relevance > base_relevance + 1e-8)),
        }


def build_visual_input(
    visual_processor: VisualEvidenceProcessor,
    selected_frames: list[Image.Image],
    selected_metadata: list[dict[str, Any]],
    question: str,
    ocr_frames: dict[int, list[dict[str, Any]]] | None = None,
) -> tuple[list[Image.Image], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    crop_images: dict[str, Image.Image] = {}
    crop_candidates: list[dict[str, Any]] = []
    response_traces: list[dict[str, Any]] = []
    ocr_relevance_trace: dict[str, Any] = {"scope": args.ocr_relevance_scope}

    if args.ocr_proxy == "cache":
        if ocr_frames is None:
            raise ValueError("OCR cache frames are required when ocr_proxy=cache")
        validate_ocr_frame_coverage(ocr_frames, selected_metadata)
        if args.ocr_relevance_scope == "video":
            ocr_frames, ocr_relevance_trace = visual_processor.prepare_video_ocr_relevance(
                question, selected_metadata, ocr_frames
            )

    for frame_rank, (frame, frame_meta) in enumerate(zip(selected_frames, selected_metadata)):
        audio_trace = frame_meta.get("audio_window_trace", {})
        candidates, response_trace = visual_processor.crop_candidates(
            frame,
            question,
            frame_meta.get("audio_window_text", ""),
            str(audio_trace.get("mode", "global_fallback")),
            (ocr_frames or {}).get(int(frame_meta.get("sample_rank", -1)), []),
        )
        response_traces.append({"frame_rank": frame_rank, **response_trace})
        for local_rank, (crop_image, crop_meta) in enumerate(candidates):
            candidate_id = f"{frame_rank}:{local_rank}"
            record = dict(crop_meta)
            record.update({
                "candidate_id": candidate_id,
                "frame_rank": frame_rank,
                "sample_rank": frame_meta.get("sample_rank"),
                "frame_index": frame_meta.get("frame_index"),
                "timestamp_sec": frame_meta.get("timestamp_sec"),
                "selection_score": frame_meta.get("selection_score"),
            })
            crop_candidates.append(record)
            crop_images[candidate_id] = crop_image

    if args.focus_context_budget:
        if len(selected_frames) != args.visual_image_budget:
            raise RuntimeError(
                "focus-context mode requires one source frame per visual budget slot: "
                f"selected={len(selected_frames)} budget={args.visual_image_budget}"
            )
        chosen_locals, budget_trace = allocate_local_budget(
            crop_candidates,
            global_count=len(selected_frames),
            visual_budget=len(selected_frames) + args.focus_context_budget,
            max_per_frame=1,
        )
        for local in chosen_locals:
            local["submission_mode"] = "embedded_focus_context"
        budget_trace.update({
            "allocation_mode": "embedded_focus_context",
            "candidate_allocation_budget": budget_trace["visual_budget"],
            "focus_context_budget": args.focus_context_budget,
            "submitted_visual_budget": args.visual_image_budget,
            "visual_budget": args.visual_image_budget,
        })
    else:
        chosen_locals, budget_trace = allocate_local_budget(
            crop_candidates,
            global_count=len(selected_frames),
            visual_budget=args.visual_image_budget,
            max_per_frame=args.max_local_views_per_frame,
        )
    chosen_by_frame: dict[int, list[dict[str, Any]]] = {}
    for item in chosen_locals:
        chosen_by_frame.setdefault(int(item["frame_rank"]), []).append(item)

    final_frames: list[Image.Image] = []
    visual_plan: list[dict[str, Any]] = []
    for frame_rank, (frame, frame_meta) in enumerate(zip(selected_frames, selected_metadata)):
        embedded = chosen_by_frame.get(frame_rank, []) if args.focus_context_budget else []
        if embedded:
            local = embedded[0]
            candidate_id = str(local["candidate_id"])
            visual_plan.append({
                "input_index": len(final_frames),
                "view_type": "focus_context",
                "frame_rank": frame_rank,
                "sample_rank": frame_meta.get("sample_rank"),
                "frame_index": frame_meta.get("frame_index"),
                "timestamp_sec": frame_meta.get("timestamp_sec"),
                "candidate_id": candidate_id,
                "bbox": local.get("bbox"),
                "bbox_norm": local.get("bbox_norm"),
                "budget_rank": local.get("budget_rank"),
                "budget_utility": local.get("budget_utility"),
                "context_fraction": args.focus_context_global_fraction,
                "focus_context_layout": "vertical_stack",
            })
            final_frames.append(smart_resize(compose_focus_context(
                frame,
                crop_images[candidate_id],
                context_fraction=args.focus_context_global_fraction,
            )))
            continue
        visual_plan.append({
            "input_index": len(final_frames),
            "view_type": "global",
            "frame_rank": frame_rank,
            "sample_rank": frame_meta.get("sample_rank"),
            "frame_index": frame_meta.get("frame_index"),
            "timestamp_sec": frame_meta.get("timestamp_sec"),
        })
        final_frames.append(smart_resize(frame))
        for local in sorted(chosen_by_frame.get(frame_rank, []), key=lambda item: item["budget_rank"]):
            candidate_id = str(local["candidate_id"])
            visual_plan.append({
                "input_index": len(final_frames),
                "view_type": "local",
                "frame_rank": frame_rank,
                "candidate_id": candidate_id,
                "bbox": local.get("bbox"),
                "bbox_norm": local.get("bbox_norm"),
                "budget_rank": local.get("budget_rank"),
                "budget_utility": local.get("budget_utility"),
            })
            final_frames.append(smart_resize(crop_images[candidate_id]))

    budget_trace["actual_input_count"] = len(final_frames)
    budget_trace["budget_respected"] = len(final_frames) <= args.visual_image_budget
    budget_trace["budget_unit"] = "submitted_pil_frames"
    if not budget_trace["budget_respected"]:
        raise RuntimeError(f"visual budget exceeded: {len(final_frames)} > {args.visual_image_budget}")
    reconstruction_trace = {
        "budget": budget_trace,
        "responses": response_traces,
    }
    if args.ocr_proxy == "cache" and args.ocr_relevance_scope == "video":
        reconstruction_trace["ocr_relevance"] = ocr_relevance_trace
    return final_frames, visual_plan, crop_candidates, chosen_locals, reconstruction_trace


def build_prompt(question: str, transcript: str) -> str:
    return build_adsqa_answer_prompt(question, transcript)


def generate_response(model, processor, frames: list[Image.Image], prompt: str) -> tuple[str, dict[str, Any]]:
    message = [{"role": "user", "content": [{"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt}]}]
    text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
    inputs, processor_trace = prepare_qwen_video_inputs(
        processor=processor,
        text_input=text_input,
        frames=frames,
        device=model.device,
        expected_view_count=args.visual_image_budget,
        max_post_merge_visual_tokens=args.max_post_merge_visual_tokens,
        metadata_fps=1.0,
        require_exact_frame_count=True,
    )
    with torch.no_grad():
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=args.max_new_tokens)
    trimmed = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, generated)]
    decoded = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return (decoded[0].strip() if decoded else ""), processor_trace


def save_evidence_images(q_dir: Path, frames: list[Image.Image], plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    image_dir = q_dir / "evidence_images"
    image_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for frame, item in zip(frames, plan):
        name = f"input{item['input_index']:02d}_{item['view_type']}_frame{item['frame_rank']:02d}.jpg"
        path = image_dir / name
        frame.save(path, quality=90)
        records.append({**item, "path": str(path)})
    return records


def main() -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(output_dir)
    if args.num_shards <= 0 or not 0 <= args.shard_id < args.num_shards:
        raise ValueError("invalid shard configuration")
    if args.visual_image_budget <= 0:
        raise ValueError("visual_image_budget must be positive")
    if args.focus_context_budget and args.top_k_frames != args.visual_image_budget:
        raise ValueError("focus-context mode requires top_k_frames=visual_image_budget")
    if args.temporal_coverage_bins < 0:
        raise ValueError("temporal_coverage_bins must be non-negative")
    if not 0.0 < args.crop_coverage_target <= 1.0:
        raise ValueError("crop_coverage_target must be in (0, 1]")
    if args.ocr_proxy == "cache" and not args.ocr_cache_file:
        raise ValueError("ocr_cache_file is required when ocr_proxy=cache")
    if args.ocr_proxy == "cache" and args.ocr_relevance_scope == "train_null":
        if not Path(args.ocr_null_question_file).is_file():
            raise ValueError("ocr_null_question_file is required for train_null relevance")
    if not 0.0 <= args.ocr_min_confidence <= 1.0:
        raise ValueError("ocr_min_confidence must be in [0, 1]")

    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    asr_data = json.loads(Path(args.asr_file).read_text(encoding="utf-8")) if Path(args.asr_file).exists() else {}
    groundtruth = load_groundtruth_map(args.groundtruth_file)
    ocr_cache: dict[str, dict[int, list[dict[str, Any]]]] = {}
    ocr_cache_provenance: dict[str, Any] = {}
    if args.ocr_proxy == "cache":
        ocr_cache, ocr_cache_provenance = load_ocr_cache(args.ocr_cache_file)
    end_index = len(questions) if args.end_idx < 0 else min(args.end_idx, len(questions))
    indexed = list(enumerate(questions[max(0, args.start_idx):end_index], start=max(0, args.start_idx)))
    shard_items = [(index, item) for index, item in indexed if index % args.num_shards == args.shard_id]
    if args.ocr_proxy == "cache":
        validate_ocr_question_coverage(
            ocr_cache,
            [str(item["question_id"]) for _, item in shard_items],
        )

    run_config = vars(args).copy()
    run_config.update({
        "method": METHOD_NAME,
        "script": ENTRYPOINT_PATH,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rag_enabled": False,
        "reflection_enabled": False,
        "answer_prompt_version": ADSQA_ANSWER_PROMPT_VERSION,
        "answer_prompt_template_sha256": adsqa_answer_prompt_sha256(),
        "visual_budget_unit": "submitted_pil_frames",
        "ocr_cache_provenance": ocr_cache_provenance,
        "ocr_cache_sha256": (
            hashlib.sha256(Path(args.ocr_cache_file).read_bytes()).hexdigest()
            if args.ocr_proxy == "cache" else None
        ),
        "ocr_null_question_sha256": (
            hashlib.sha256(Path(args.ocr_null_question_file).read_bytes()).hexdigest()
            if args.ocr_proxy == "cache" and args.ocr_relevance_scope == "train_null"
            else None
        ),
    })
    dump_json(output_dir / "run_config.json", run_config)

    if args.dry_run:
        preview = []
        for index, item in shard_items[:10]:
            question_id = str(item["question_id"])
            video_id = str(item.get("video", item.get("video_id", question_id.split("_")[0])))
            raw_asr = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, ""))
            preview.append({
                "global_idx": index,
                "question_id": question_id,
                "video_id": video_id,
                "video_path": resolve_video_path(video_id),
                "asr_mode": normalize_asr(raw_asr)["mode"],
            })
        dump_json(output_dir / "dry_run_preview.json", preview)
        LOGGER.info("Dry run complete: %s", output_dir / "dry_run_preview.json")
        return

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    visual_processor = VisualEvidenceProcessor(device="cuda", clip_path=args.clip_path)
    if not visual_processor.valid:
        raise RuntimeError(f"CLIP processor failed to load: {visual_processor.error}")

    model = None
    processor = None
    if not args.localization_only:
        LOGGER.info("Loading Qwen3-VL from %s", args.model_dir)
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

    stats = {"processed": 0, "skipped_existing": 0, "missing_video_or_frames": 0, "errors": 0}
    errors_path = output_dir / "logs" / f"errors_gpu{args.gpu_id}_shard{args.shard_id}.jsonl"
    for global_index, item in tqdm(shard_items, desc=f"GPU {args.gpu_id} {METHOD_NAME}"):
        started = time.time()
        question_id = str(item["question_id"])
        q_dir = output_dir / question_id
        prediction_path = q_dir / "prediction.json"
        completion_path = q_dir / ("evidence.json" if args.localization_only else "prediction.json")
        try:
            if completion_path.exists() and not args.overwrite:
                stats["skipped_existing"] += 1
                continue
            video_id = str(item.get("video", item.get("video_id", question_id.split("_")[0])))
            video_path = resolve_video_path(video_id)
            raw_frames, raw_metadata = load_frames_oversampled(video_path, args.oversample_count)
            if not raw_frames:
                stats["missing_video_or_frames"] += 1
                append_jsonl(errors_path, {"question_id": question_id, "error": "no_frames", "video_path": video_path})
                continue

            raw_asr = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, ""))
            asr_evidence = normalize_asr(raw_asr)
            offset_trace = visual_processor.estimate_audio_offset(raw_frames, raw_metadata, asr_evidence)
            audio_offset = float(offset_trace.get("offset_seconds", 0.0))
            effective_top_k = min(max(1, args.top_k_frames), args.visual_image_budget, len(raw_frames))
            selected_frames, selected_metadata = visual_processor.select_frames(
                raw_frames,
                raw_metadata,
                item["question"],
                asr_evidence,
                audio_offset,
                effective_top_k,
            )
            final_frames, visual_plan, crop_candidates, chosen_locals, reconstruction_trace = build_visual_input(
                visual_processor,
                selected_frames,
                selected_metadata,
                item["question"],
                ocr_cache.get(question_id, {}),
            )
            if not final_frames:
                raise RuntimeError("visual reconstruction returned no input frames")

            prompt = build_prompt(item["question"], asr_evidence.get("transcript", ""))
            if args.localization_only:
                answer = ""
                processor_trace = {"localization_only": True}
                generation_seconds = 0.0
            else:
                generation_started = time.time()
                answer, processor_trace = generate_response(model, processor, final_frames, prompt)
                generation_seconds = time.time() - generation_started

            q_dir.mkdir(parents=True, exist_ok=True)
            if not args.localization_only:
                dump_json(prediction_path, {
                    "question_id": question_id,
                    "prediction": answer,
                    "ground_truth": groundtruth.get(question_id, "N/A"),
                    "pipeline": f"{METHOD_NAME}_Qwen3VL",
                    "rag_mode": "none",
                    "reflection_status": "disabled_for_innovation1",
                    "score": "",
                })
            image_records = save_evidence_images(q_dir, final_frames, visual_plan) if args.save_evidence_images else []
            evidence_record = {
                "question_id": question_id,
                "global_idx": global_index,
                "video_id": video_id,
                "video_path": video_path,
                "question": item.get("question", ""),
                "method": METHOD_NAME,
                "asr": {
                    "mode": asr_evidence.get("mode"),
                    "has_timestamps": asr_evidence.get("has_timestamps"),
                    "segment_count": len(asr_evidence.get("segments", [])),
                    "transcript_excerpt": str(asr_evidence.get("transcript", ""))[:1000],
                    "offset_trace": offset_trace,
                },
                "raw_sample_count": len(raw_frames),
                "selected_count": len(selected_frames),
                "input_image_count": len(final_frames),
                "selected_frames": selected_metadata,
                "response_traces": reconstruction_trace["responses"],
                "crop_candidates": crop_candidates,
                "selected_local_views": chosen_locals,
                "visual_plan": visual_plan,
                "budget_trace": reconstruction_trace["budget"],
                "image_records": image_records,
                "generation": {
                    "max_new_tokens": args.max_new_tokens,
                    "generation_seconds": generation_seconds,
                    "total_seconds": time.time() - started,
                    "processor_trace": processor_trace,
                },
                "limitations": {
                    "timestamp_alignment_active": bool(asr_evidence.get("has_timestamps")),
                    "ocr_mode": (
                        "cached_rapidocr_query_relevance"
                        if args.ocr_proxy == "cache"
                        else "semantic_proxy_not_real_ocr"
                        if args.ocr_proxy == "semantic"
                        else "off"
                    ),
                    "rag_enabled": False,
                    "reflection_enabled": False,
                    "processor_secondary_sampling_disabled": True,
                    "uncertainty_mode": (
                        "deterministic_consistency_not_calibrated_probability"
                        if args.response_fusion == "consistency_calibrated"
                        else "disabled"
                    ),
                    "focus_context_mode": (
                        "embedded_global_plus_roi"
                        if args.focus_context_budget
                        else "disabled"
                    ),
                    "localization_only": args.localization_only,
                },
                "config_subset": {
                    "oversample_count": args.oversample_count,
                    "top_k_frames": args.top_k_frames,
                    "effective_top_k_frames": effective_top_k,
                    "temporal_coverage_bins": args.temporal_coverage_bins,
                    "global_question_weight": args.global_question_weight,
                    "global_audio_weight": args.global_audio_weight,
                    "visual_image_budget": args.visual_image_budget,
                    "max_post_merge_visual_tokens": args.max_post_merge_visual_tokens,
                    "crop_scales": args.crop_scales,
                    "crop_coverage_target": args.crop_coverage_target,
                    "max_response_peaks": args.max_response_peaks,
                    "max_local_views_per_frame": args.max_local_views_per_frame,
                    "focus_context_budget": args.focus_context_budget,
                    "focus_context_global_fraction": args.focus_context_global_fraction,
                    "spatial_response_mode": args.spatial_response_mode,
                    "ocr_proxy": args.ocr_proxy,
                    "ocr_proxy_reliability": args.ocr_proxy_reliability,
                    "ocr_min_confidence": args.ocr_min_confidence,
                    "ocr_relevance_scope": args.ocr_relevance_scope,
                    "ocr_null_question_file": (
                        args.ocr_null_question_file
                        if args.ocr_relevance_scope == "train_null"
                        else None
                    ),
                    "response_fusion": args.response_fusion,
                    "consistency_perturbations": args.consistency_perturbations,
                    "uncertainty_temperature": args.uncertainty_temperature,
                    "uncertainty_refinement_weight": args.uncertainty_refinement_weight,
                    "reliability_floor": args.reliability_floor,
                    "global_asr_reliability": args.global_asr_reliability,
                },
            }
            if args.ocr_proxy == "cache" and args.ocr_relevance_scope == "video":
                evidence_record["limitations"]["ocr_mode"] = "cached_rapidocr_video_relevance"
                evidence_record["config_subset"]["ocr_relevance_scope"] = "video"
                evidence_record["ocr_relevance_trace"] = reconstruction_trace["ocr_relevance"]
            elif args.ocr_proxy == "cache" and args.ocr_relevance_scope == "train_null":
                evidence_record["limitations"]["ocr_mode"] = "cached_rapidocr_train_null"
            if args.save_prompts:
                evidence_record["prompt"] = prompt
            dump_json(q_dir / "evidence.json", evidence_record)
            stats["processed"] += 1
            if stats["processed"] % 10 == 0:
                LOGGER.info("Progress: %s", stats)
        except Exception as error:
            stats["errors"] += 1
            LOGGER.error("Inference failed qid=%s: %s", question_id, error)
            append_jsonl(errors_path, {
                "question_id": question_id,
                "global_idx": global_index,
                "error": repr(error),
                "traceback": traceback.format_exc(),
            })
        finally:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    dump_json(output_dir / f"summary_gpu{args.gpu_id}_shard{args.shard_id}.json", stats)
    LOGGER.info("Completed: %s", stats)


if __name__ == "__main__":
    main()
