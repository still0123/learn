#!/usr/bin/env python3
"""Build answer-free CLIP, segmented-ASR, and OCR crop candidates for GroupCV."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

sys.modules["torchcodec"] = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.av_evidence.av_response import normalize_response, response_concentration  # noqa: E402
from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    RAW_GLOBAL_VIEW_COUNT,
    extract_question_text,
    sha256_file,
)
from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import (  # noqa: E402
    ensure_idle_allowed_gpu as _base_ensure_idle_allowed_gpu,
    load_answer_free_questions,
    load_uniform_frames,
    resolve_video_path,
)


def ensure_idle_allowed_gpu(gpu_id: str) -> list[str]:
    """Allow only the user-authorized idle cards for this isolated build."""
    if gpu_id not in {"1", "2", "4", "5"}:
        raise ManifestBuildError("this build is restricted to GPU1/GPU2/GPU4/GPU5")
    snapshot = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = [line.strip() for line in snapshot.stdout.splitlines() if line.strip()]
    matching = [line for line in rows if line.split(",", 1)[0].strip() == gpu_id]
    if len(matching) != 1:
        raise ManifestBuildError(f"GPU {gpu_id} is not visible")
    apps = subprocess.run(
        [
            "nvidia-smi",
            f"--id={gpu_id}",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    active_apps = [line.strip() for line in apps.stdout.splitlines() if line.strip()]
    if active_apps:
        raise ManifestBuildError(f"GPU {gpu_id} is not idle: {active_apps}")
    return matching


OCR_QUERY_TERMS = (
    "brand", "logo", "text", "word", "written", "caption", "subtitle", "sign",
    "label", "number", "price", "discount", "percentage", "url", "website", "barcode",
)
AUDIO_QUERY_TERMS = (
    "voiceover", "speaker", "narrator", "spoken", "say", "said", "hear", "sound",
    "music", "dialogue", "audio",
)
LOCAL_CROP_SCALE = 0.60
ASR_MIN_WORDS = 2
ASR_MIN_AVG_LOGPROB = -1.0
ASR_MAX_NO_SPEECH = 0.6
ASR_MIN_MEAN_WORD_PROBABILITY = 0.5
OCR_MIN_CONFIDENCE = 0.5
OCR_MIN_AREA = 0.0001
OCR_MAX_AREA = 0.5


class ManifestBuildError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["1", "2", "4", "5"])
    parser.add_argument("--questions", required=True)
    parser.add_argument("--segmented-asr-root", required=True)
    parser.add_argument("--ocr-root", required=True)
    parser.add_argument("--clip-path", default=str(PROJECT_ROOT / "models/clip-vit-large-patch14"))
    parser.add_argument("--video-root", default=str(PROJECT_ROOT / "data/videos"))
    parser.add_argument("--frames-fallback-root", default=str(PROJECT_ROOT / "data/frames_8"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-items", type=int, default=-1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalized_crop_box(response: Any, scale: float = LOCAL_CROP_SCALE) -> list[float]:
    import numpy as np

    heatmap = normalize_response(response)
    height, width = heatmap.shape
    mass = float(heatmap.sum())
    if mass <= 1e-8:
        center_x = center_y = 0.5
    else:
        y_grid, x_grid = np.indices((height, width))
        center_x = float((x_grid * heatmap).sum() / mass + 0.5) / width
        center_y = float((y_grid * heatmap).sum() / mass + 0.5) / height
    left = min(max(center_x - scale / 2.0, 0.0), 1.0 - scale)
    top = min(max(center_y - scale / 2.0, 0.0), 1.0 - scale)
    return [left, top, left + scale, top + scale]


def matched_terms(text: str, terms: Sequence[str]) -> list[str]:
    normalized = " ".join(text.lower().split())
    return [term for term in terms if term in normalized]


def usable_asr_segments(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for segment in payload.get("segments", []):
        text = " ".join(str(segment.get("text", "")).split())
        probabilities = [float(word.get("probability", 0.0)) for word in segment.get("words", [])]
        mean_probability = sum(probabilities) / len(probabilities) if probabilities else 0.0
        if (
            len(text.split()) >= ASR_MIN_WORDS
            and float(segment.get("avg_logprob", -99.0)) >= ASR_MIN_AVG_LOGPROB
            and float(segment.get("no_speech_prob", 1.0)) <= ASR_MAX_NO_SPEECH
            and mean_probability >= ASR_MIN_MEAN_WORD_PROBABILITY
        ):
            rows.append(
                {
                    "segment_id": int(segment.get("id", len(rows))),
                    "start": float(segment["start"]),
                    "end": float(segment["end"]),
                    "text": text,
                    "mean_word_probability": mean_probability,
                }
            )
    return rows


def usable_ocr_detections(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for frame in payload.get("frames", []):
        for detection in frame.get("detections", []):
            text = " ".join(str(detection.get("text", "")).split())
            box = [float(value) for value in detection.get("bbox_norm", [])]
            if len(box) != 4:
                continue
            area = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
            if (
                float(detection.get("score", 0.0)) >= OCR_MIN_CONFIDENCE
                and 2 <= len(text) <= 80
                and OCR_MIN_AREA <= area <= OCR_MAX_AREA
            ):
                rows.append(
                    {
                        "candidate_rank": int(frame["candidate_rank"]),
                        "frame_index": int(frame["frame_index"]),
                        "timestamp_sec": float(frame["timestamp_sec"]),
                        "text": text,
                        "confidence": float(detection["score"]),
                        "bbox_norm": box,
                    }
                )
    return rows


class Planner:
    def __init__(self, clip_path: str, device: str):
        import torch
        import torch.nn.functional as functional
        from transformers import CLIPTextModelWithProjection, CLIPTokenizer, CLIPVisionModelWithProjection
        from torchvision.transforms import Normalize, ToTensor

        self.torch = torch
        self.functional = functional
        self.device = device
        options = {"local_files_only": True, "ignore_mismatched_sizes": True}
        self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, **options).to(device).eval()
        self.text = CLIPTextModelWithProjection.from_pretrained(clip_path, **options).to(device).eval()
        self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
        self.normalize = Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))
        self.to_tensor = ToTensor()
        self.text_cache: dict[str, Any] = {}

    def encode_texts(self, texts: Sequence[str]):
        normalized = [" ".join(str(text).split())[:300] for text in texts]
        missing = list(dict.fromkeys(text for text in normalized if text and text not in self.text_cache))
        for offset in range(0, len(missing), 64):
            batch = missing[offset : offset + 64]
            tokens = self.tokenizer(batch, padding=True, truncation=True, max_length=77, return_tensors="pt").to(self.device)
            with self.torch.no_grad():
                embeddings = self.functional.normalize(self.text(**tokens).text_embeds, dim=-1)
            for text, embedding in zip(batch, embeddings):
                self.text_cache[text] = embedding.unsqueeze(0)
        return [self.text_cache.get(text) for text in normalized]

    def preprocess(self, frames: Sequence[Any]):
        tensors = [self.normalize(self.to_tensor(frame.convert("RGB").resize((224, 224)))) for frame in frames]
        return self.torch.stack(tensors).to(self.device)

    @staticmethod
    def nearest_rank(timestamp: float, frame_metadata: Sequence[Mapping[str, Any]]) -> int:
        valid = [
            (rank, float(item["source_timestamp_sec"]))
            for rank, item in enumerate(frame_metadata)
            if item.get("source_timestamp_sec") is not None
        ]
        if not valid:
            return 0
        return min(valid, key=lambda item: (abs(item[1] - timestamp), item[0]))[0]

    @staticmethod
    def fill_with_clip(specs: list[dict[str, Any]], clip_specs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        result = list(specs[:APPENDED_LOCAL_VIEW_COUNT])
        if len(result) == APPENDED_LOCAL_VIEW_COUNT:
            return result
        seen = {(int(item["source_global_rank"]), tuple(round(float(v), 8) for v in item["bbox_norm"])) for item in result}
        for clip in clip_specs:
            signature = (int(clip["source_global_rank"]), tuple(round(float(v), 8) for v in clip["bbox_norm"]))
            if signature in seen:
                continue
            fallback = dict(clip)
            fallback["crop_mode"] = "clip_fallback_for_modality_v1"
            result.append(fallback)
            seen.add(signature)
            if len(result) == APPENDED_LOCAL_VIEW_COUNT:
                break
        if len(result) != APPENDED_LOCAL_VIEW_COUNT:
            raise ManifestBuildError("unable to create exactly eight crop candidates")
        return result

    def plan(
        self,
        frames: Sequence[Any],
        frame_metadata: Sequence[Mapping[str, Any]],
        question: str,
        asr_segments: Sequence[Mapping[str, Any]],
        ocr_detections: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        import numpy as np

        query = extract_question_text(question)
        query_embedding = self.encode_texts([query])[0]
        if query_embedding is None:
            raise ManifestBuildError("query embedding is unavailable")
        with self.torch.no_grad():
            output = self.vision(self.preprocess(frames))
            global_embeddings = self.functional.normalize(output.image_embeds, dim=-1)
            global_similarity = self.torch.matmul(global_embeddings, query_embedding.T).view(-1)
            patch_embeddings = output.last_hidden_state[:, 1:]
            if hasattr(self.vision, "visual_projection"):
                patch_embeddings = self.vision.visual_projection(patch_embeddings)
            patch_embeddings = self.functional.normalize(patch_embeddings, dim=-1)
            patch_similarity = self.torch.matmul(patch_embeddings, query_embedding.T).squeeze(-1)
        side = int(math.sqrt(patch_similarity.shape[-1]))
        if side * side != patch_similarity.shape[-1]:
            raise ManifestBuildError("CLIP patch count is not square")
        global_values = global_similarity.detach().float().cpu().numpy()
        maps = patch_similarity.detach().float().cpu().numpy().reshape(len(frames), side, side)
        clip_ranks = sorted(range(len(frames)), key=lambda index: (float(global_values[index]), -index), reverse=True)[:8]
        clip_specs = [
            {
                "source_global_rank": int(rank),
                "bbox_norm": normalized_crop_box(maps[rank]),
                "crop_mode": "clip_question_patch_response_v2",
                "global_response": float(global_values[rank]),
                "response_concentration": float(response_concentration(maps[rank])),
            }
            for rank in clip_ranks
        ]
        clip_candidate_specs = [
            {
                "source_global_rank": int(rank),
                "bbox_norm": normalized_crop_box(maps[rank]),
                "crop_mode": "clip_question_patch_response_candidate_v1",
                "global_response": float(global_values[rank]),
                "response_concentration": float(response_concentration(maps[rank])),
            }
            for rank in sorted(
                range(len(frames)),
                key=lambda index: (float(global_values[index]), -index),
                reverse=True,
            )
        ]

        segment_embeddings = self.encode_texts([str(item["text"]) for item in asr_segments])
        asr_candidates = []
        asr_similarities = []
        for segment, embedding in zip(asr_segments, segment_embeddings):
            if embedding is None:
                continue
            similarity = float(self.torch.matmul(embedding, query_embedding.T).item())
            asr_similarities.append(similarity)
            rank = self.nearest_rank((float(segment["start"]) + float(segment["end"])) / 2.0, frame_metadata)
            asr_candidates.append((similarity, float(segment["mean_word_probability"]), rank, segment))
        asr_candidates.sort(key=lambda item: (item[0], item[1], -item[2]), reverse=True)
        asr_specs = []
        seen_ranks = set()
        for similarity, reliability, rank, segment in asr_candidates:
            if rank in seen_ranks:
                continue
            seen_ranks.add(rank)
            asr_specs.append(
                {
                    "source_global_rank": int(rank),
                    "bbox_norm": normalized_crop_box(maps[rank]),
                    "crop_mode": "segmented_asr_temporal_question_patch_v1",
                    "segment_id": int(segment["segment_id"]),
                    "segment_start": float(segment["start"]),
                    "segment_end": float(segment["end"]),
                    "query_segment_similarity": similarity,
                    "segment_reliability": reliability,
                }
            )
            if len(asr_specs) == 8:
                break
        asr_driven_count = len(asr_specs)
        asr_specs = self.fill_with_clip(asr_specs, clip_specs)

        ocr_embeddings = self.encode_texts([str(item["text"]) for item in ocr_detections])
        ocr_candidates = []
        for detection, embedding in zip(ocr_detections, ocr_embeddings):
            if embedding is None:
                continue
            similarity = float(self.torch.matmul(embedding, query_embedding.T).item())
            combined = 0.7 * ((similarity + 1.0) / 2.0) + 0.3 * float(detection["confidence"])
            rank = self.nearest_rank(float(detection["timestamp_sec"]), frame_metadata)
            ocr_candidates.append((combined, similarity, rank, detection))
        ocr_candidates.sort(key=lambda item: (item[0], item[1], -item[2]), reverse=True)
        ocr_specs = []
        seen_ocr = set()
        for combined, similarity, rank, detection in ocr_candidates:
            signature = (rank, tuple(round(float(value), 8) for value in detection["bbox_norm"]))
            if signature in seen_ocr:
                continue
            seen_ocr.add(signature)
            ocr_specs.append(
                {
                    "source_global_rank": int(rank),
                    "bbox_norm": list(detection["bbox_norm"]),
                    "crop_mode": "question_conditioned_ocr_bbox_v1",
                    "ocr_confidence": float(detection["confidence"]),
                    "query_ocr_similarity": similarity,
                    "combined_relevance": combined,
                    "ocr_text_sha256": hashlib.sha256(str(detection["text"]).encode()).hexdigest(),
                }
            )
            if len(ocr_specs) == 8:
                break
        ocr_driven_count = len(ocr_specs)
        ocr_specs = self.fill_with_clip(ocr_specs, clip_specs)
        asr_contrast = (
            max(asr_similarities) - statistics.median(asr_similarities)
            if len(asr_similarities) >= 2
            else 0.0
        )
        return {
            "query_text_sha256": hashlib.sha256(query.encode()).hexdigest(),
            "matched_ocr_query_terms": matched_terms(query, OCR_QUERY_TERMS),
            "matched_audio_query_terms": matched_terms(query, AUDIO_QUERY_TERMS),
            "clip_crop_specs": clip_specs,
            "clip_candidate_specs": clip_candidate_specs,
            "asr_crop_specs": asr_specs,
            "ocr_crop_specs": ocr_specs,
            "usable_asr_segment_count": len(asr_segments),
            "usable_ocr_detection_count": len(ocr_detections),
            "asr_modality_driven_crop_count": asr_driven_count,
            "ocr_modality_driven_crop_count": ocr_driven_count,
            "asr_relevance_max": max(asr_similarities) if asr_similarities else None,
            "asr_relevance_median": statistics.median(asr_similarities) if asr_similarities else None,
            "asr_relevance_contrast": asr_contrast,
            "visual_peak_response": float((maps.max() + 1.0) / 2.0),
        }


def main() -> None:
    args = parse_args()
    questions_path = Path(args.questions).resolve()
    asr_root = Path(args.segmented_asr_root).resolve()
    ocr_root = Path(args.ocr_root).resolve()
    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.overwrite:
        raise ManifestBuildError(f"output exists: {output_path}")
    questions = load_answer_free_questions(questions_path)
    if args.max_items > 0:
        questions = questions[: args.max_items]
    gpu_snapshot = ensure_idle_allowed_gpu(args.gpu_id)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = output_path.parent / "logs/build_modality_manifest_gpu4.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)], force=True)
    logger = logging.getLogger("modality_manifest")
    planner = Planner(args.clip_path, "cuda")
    video_root = Path(args.video_root)
    fallback_root = Path(args.frames_fallback_root)
    rows = []
    started = time.time()
    for index, item in enumerate(questions, start=1):
        question_id = str(item["question_id"])
        video = str(item["video"])
        asr_payload = json.loads((asr_root / f"{video}.json").read_text(encoding="utf-8"))
        ocr_payload = json.loads((ocr_root / f"{video}.json").read_text(encoding="utf-8"))
        frames, frame_metadata = load_uniform_frames(resolve_video_path(video, video_root, fallback_root), RAW_GLOBAL_VIEW_COUNT)
        plan = planner.plan(frames, frame_metadata, str(item["question"]), usable_asr_segments(asr_payload), usable_ocr_detections(ocr_payload))
        rows.append(
            {
                "schema_version": "qwen25_diverse_local8_raw_feature_v1",
                "question_id": question_id,
                "video_id": video,
                "fold": int(item["fold"]),
                **plan,
                "inputs": {
                    "questions_sha256": sha256_file(questions_path),
                    "segmented_asr_record_sha256": sha256_file(asr_root / f"{video}.json"),
                    "ocr_record_sha256": sha256_file(ocr_root / f"{video}.json"),
                    "answer_or_outcome_fields_used": False,
                },
            }
        )
        if index % 25 == 0:
            logger.info("processed=%d/%d elapsed=%.1f", index, len(questions), time.time() - started)
        gc.collect()
        planner.torch.cuda.empty_cache()
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(output_path)
    audit = {
        "schema_version": "qwen25_modality_active_raw_feature_audit_v1",
        "passed": len(rows) == len(questions),
        "record_count": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "gpu_snapshot_before_load": gpu_snapshot,
        "output_sha256": sha256_file(output_path),
        "asr_candidate_count": sum(row["asr_modality_driven_crop_count"] >= 2 for row in rows),
        "ocr_candidate_count": sum(row["ocr_modality_driven_crop_count"] >= 2 for row in rows),
        "explicit_audio_question_count": sum(bool(row["matched_audio_query_terms"]) for row in rows),
        "explicit_ocr_question_count": sum(bool(row["matched_ocr_query_terms"]) for row in rows),
        "answer_or_outcome_fields_used": False,
        "elapsed_seconds": time.time() - started,
    }
    output_path.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
