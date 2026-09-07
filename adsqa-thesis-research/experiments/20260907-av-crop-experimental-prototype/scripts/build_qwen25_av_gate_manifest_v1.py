#!/usr/bin/env python3
"""Precompute the answer-free shared gate manifest for GroupCV C/D/E.

The manifest stores only pre-inference inputs and deterministic crop plans:
question text, ASR, CLIP response statistics, and crop coordinates.  It is
created once from the AdsQA training split and is shared by all three gated
methods.  No answer, judge result, test data, or generated prediction is read.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Mapping, Sequence

sys.modules["torchcodec"] = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.av_evidence.av_response import (  # noqa: E402
    normalize_response,
    response_concentration,
)
from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    FROZEN_GATE_RULE,
    RAW_GLOBAL_VIEW_COUNT,
    build_gate_manifest_record,
    extract_question_text,
    sha256_file,
    validate_clean_model_path,
    validate_shared_gate_manifest,
)
from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import (  # noqa: E402
    ensure_idle_allowed_gpu,
    load_answer_free_questions,
    load_asr,
    load_uniform_frames,
    resolve_video_path,
)


RUN_DIR = PROJECT_ROOT / "evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"


class GateManifestError(RuntimeError):
    """Raised when a gate plan cannot be generated reproducibly."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen GroupCV AV gate manifest")
    parser.add_argument("--gpu-id", required=True, choices=["4", "5"])
    parser.add_argument(
        "--question-file",
        default=str(RUN_DIR / "groupcv5/oof_questions_v1.json"),
    )
    parser.add_argument(
        "--asr-file",
        default=str(PROJECT_ROOT / "evaluation/asr_set.json"),
    )
    parser.add_argument(
        "--model-dir",
        default="/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct",
    )
    parser.add_argument(
        "--clip-path",
        default=str(PROJECT_ROOT / "models/clip-vit-large-patch14"),
    )
    parser.add_argument("--video-root", default=str(PROJECT_ROOT / "data/videos"))
    parser.add_argument(
        "--frames-fallback-root",
        default=str(PROJECT_ROOT / "data/frames_8"),
    )
    parser.add_argument(
        "--output",
        default=str(RUN_DIR / "gate_manifest/gate_manifest_all_oof_v1.jsonl"),
    )
    parser.add_argument("--unified-size", type=int, default=896)
    parser.add_argument("--max-items", type=int, default=-1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def setup_logging(output_path: Path, gpu_id: str) -> logging.Logger:
    log_path = output_path.parent / "logs" / f"gate_manifest_gpu{gpu_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return logging.getLogger("qwen25_av_gate_manifest")


def normalized_crop_box(response: Any, scale: float) -> list[float]:
    """Decode a response heatmap to one fixed-scale crop around its centroid."""
    import numpy as np

    heatmap = normalize_response(response)
    if heatmap.ndim != 2 or heatmap.size == 0:
        raise GateManifestError("response heatmap must be non-empty and two-dimensional")
    height, width = heatmap.shape
    mass = float(heatmap.sum())
    if mass <= 1e-8:
        center_x = 0.5
        center_y = 0.5
    else:
        y_grid, x_grid = np.indices((height, width))
        center_x = float((x_grid * heatmap).sum() / mass + 0.5) / width
        center_y = float((y_grid * heatmap).sum() / mass + 0.5) / height
    side = float(scale)
    left = min(max(center_x - side / 2.0, 0.0), 1.0 - side)
    top = min(max(center_y - side / 2.0, 0.0), 1.0 - side)
    return [left, top, left + side, top + side]


class CLIPGatePlanner:
    """Question-only and question+ASR crop planner with fixed weights."""

    def __init__(self, clip_path: str, device: str):
        import torch
        import torch.nn.functional as F
        from transformers import (
            CLIPTextModelWithProjection,
            CLIPTokenizer,
            CLIPVisionModelWithProjection,
        )
        from torchvision.transforms import Normalize, ToTensor

        self.torch = torch
        self.F = F
        self.device = device
        options = {"local_files_only": True, "ignore_mismatched_sizes": True}
        self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, **options).to(device).eval()
        self.text = CLIPTextModelWithProjection.from_pretrained(clip_path, **options).to(device).eval()
        self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
        self.normalize = Normalize(
            (0.48145466, 0.4578275, 0.40821073),
            (0.26862954, 0.26130258, 0.27577711),
        )
        self.to_tensor = ToTensor()
        self._text_cache: dict[str, Any] = {}

    def encode_text(self, text: str):
        key = text.strip()[:300]
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
            self._text_cache[key] = self.F.normalize(self.text(**tokens).text_embeds, dim=-1)
        return self._text_cache[key]

    def preprocess(self, frames: Sequence[Any]):
        tensors = []
        for frame in frames:
            image = frame.convert("RGB").resize((224, 224))
            tensors.append(self.normalize(self.to_tensor(image)))
        return self.torch.stack(tensors).to(self.device)

    def plan(
        self,
        frames: Sequence[Any],
        question: str,
        asr_text: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        if len(frames) != RAW_GLOBAL_VIEW_COUNT:
            raise GateManifestError("gate planning requires exactly 32 Raw global frames")
        question_text = extract_question_text(question)
        question_embedding = self.encode_text(question_text)
        if question_embedding is None:
            raise GateManifestError("question text embedding is unavailable")
        audio_embedding = self.encode_text(asr_text)

        with self.torch.no_grad():
            output = self.vision(self.preprocess(frames))
            global_embeddings = self.F.normalize(output.image_embeds, dim=-1)
            question_scores = self.torch.matmul(global_embeddings, question_embedding.T).view(-1)
            if audio_embedding is not None:
                audio_scores = self.torch.matmul(global_embeddings, audio_embedding.T).view(-1)
            else:
                audio_scores = self.torch.zeros_like(question_scores)

            patch_embeddings = output.last_hidden_state[:, 1:]
            if hasattr(self.vision, "visual_projection"):
                patch_embeddings = self.vision.visual_projection(patch_embeddings)
            patch_embeddings = self.F.normalize(patch_embeddings, dim=-1)
            question_maps = self.torch.matmul(patch_embeddings, question_embedding.T).squeeze(-1)
            audio_maps = (
                self.torch.matmul(patch_embeddings, audio_embedding.T).squeeze(-1)
                if audio_embedding is not None
                else self.torch.zeros_like(question_maps)
            )

        side = int(question_maps.shape[-1] ** 0.5)
        if side * side != question_maps.shape[-1]:
            raise GateManifestError("CLIP patch count is not square")
        q_weight = float(FROZEN_GATE_RULE["av_question_weight"])
        a_weight = float(FROZEN_GATE_RULE["av_asr_weight"]) if audio_embedding is not None else 0.0
        denominator = q_weight + a_weight
        q_weight, a_weight = q_weight / denominator, a_weight / denominator

        q_global = question_scores.detach().float().cpu().numpy()
        a_global = audio_scores.detach().float().cpu().numpy()
        q_maps = question_maps.detach().float().cpu().numpy().reshape(len(frames), side, side)
        a_maps = audio_maps.detach().float().cpu().numpy().reshape(len(frames), side, side)
        av_global = q_weight * q_global + a_weight * a_global
        av_maps = q_weight * q_maps + a_weight * a_maps

        def crop_specs(global_scores: Any, maps: Any, mode: str) -> list[dict[str, Any]]:
            rankings = sorted(
                range(len(frames)),
                key=lambda index: (float(global_scores[index]), -index),
                reverse=True,
            )[:APPENDED_LOCAL_VIEW_COUNT]
            return [
                {
                    "source_global_rank": int(index),
                    "bbox_norm": normalized_crop_box(
                        maps[index], float(FROZEN_GATE_RULE["local_crop_scale"])
                    ),
                    "crop_mode": mode,
                    "global_response": float(global_scores[index]),
                    "response_concentration": float(response_concentration(maps[index])),
                }
                for index in rankings
            ]

        # Convert raw cosine response to [0,1] without per-video max normalization.
        av_peak_values = [float((map_value.max() + 1.0) / 2.0) for map_value in av_maps]
        av_stats = {
            "peak_response": max(0.0, min(1.0, max(av_peak_values))),
            "response_concentration": max(
                float(response_concentration(map_value)) for map_value in av_maps
            ),
            "eligible_crop_candidate_count": RAW_GLOBAL_VIEW_COUNT,
            "audio_available": audio_embedding is not None,
            "av_question_weight": q_weight,
            "av_asr_weight": a_weight,
        }
        return (
            av_stats,
            crop_specs(q_global, q_maps, "clip_question_patch_response_v1"),
            crop_specs(av_global, av_maps, "av_question_asr_patch_response_v1"),
        )


def main() -> None:
    args = parse_args()
    question_path = Path(args.question_file).resolve()
    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.overwrite:
        raise GateManifestError(f"output already exists: {output_path}; use --overwrite")
    questions = load_answer_free_questions(question_path)
    if args.max_items > 0:
        questions = questions[: args.max_items]
    if not questions:
        raise GateManifestError("no questions selected")

    gpu_snapshot = ensure_idle_allowed_gpu(args.gpu_id)
    model_identity = validate_clean_model_path(args.model_dir)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    logger = setup_logging(output_path, args.gpu_id)
    import torch

    planner = CLIPGatePlanner(args.clip_path, "cuda")
    asr_data = load_asr(Path(args.asr_file))
    video_root = Path(args.video_root)
    fallback_root = Path(args.frames_fallback_root)
    records = []
    failures = []
    started = time.time()
    for item in questions:
        question_id = str(item["question_id"])
        video_id = str(item["video"])
        try:
            frames, _ = load_uniform_frames(
                resolve_video_path(video_id, video_root, fallback_root),
                RAW_GLOBAL_VIEW_COUNT,
            )
            raw_asr = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, ""))
            asr_text = (
                str(raw_asr.get("transcript", raw_asr.get("text", "")))
                if isinstance(raw_asr, Mapping)
                else str(raw_asr or "")
            )
            av_stats, clip_specs, av_specs = planner.plan(frames, str(item["question"]), asr_text)
            record = build_gate_manifest_record(
                question_id=question_id,
                video_id=video_id,
                question=str(item["question"]),
                asr_evidence=asr_text,
                ocr_candidates=[],
                av_response_stats=av_stats,
            ).as_dict()
            record["clip_crop_specs"] = clip_specs
            record["av_crop_specs"] = av_specs
            record["manifest_inputs"] = {
                "question_file_sha256": sha256_file(question_path),
                "asr_file": str(Path(args.asr_file).resolve()),
                "ocr_candidates_used": False,
                "leakage_input_audit_passed": True,
            }
            records.append(record)
        except Exception as exc:
            logger.exception("gate planning failed for %s", question_id)
            failures.append({"question_id": question_id, "video": video_id, "error": repr(exc)})
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    if failures:
        raise GateManifestError(f"gate manifest has {len(failures)} failures; no partial manifest is valid")
    audit = validate_shared_gate_manifest(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, ensure_ascii=True) + "\n" for record in records),
        encoding="utf-8",
    )
    config = {
        "schema_version": "qwen25_groupcv_shared_gate_manifest_v1",
        "question_file": str(question_path),
        "question_file_sha256": sha256_file(question_path),
        "question_count": len(records),
        "gpu_id": args.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "model_identity": model_identity,
        "clip_path": str(Path(args.clip_path).resolve()),
        "frozen_gate_rule": FROZEN_GATE_RULE,
        "manifest_path": str(output_path),
        "manifest_sha256": sha256_file(output_path),
        "manifest_audit": audit,
        "testset_answers_read": False,
        "groundtruth_read": False,
        "elapsed_seconds": time.time() - started,
    }
    dump_json(output_path.with_suffix(".audit.json"), config)
    logger.info("Gate manifest complete: %s", config["manifest_audit"])


if __name__ == "__main__":
    main()
