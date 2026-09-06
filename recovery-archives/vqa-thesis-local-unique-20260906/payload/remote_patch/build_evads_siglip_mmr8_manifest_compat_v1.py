#!/usr/bin/env python3
"""Build answer-free SigLIP-MMR8 frame plans for E-VAds."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

sys.modules["torchcodec"] = None

from build_evads_siglip_manifest_v1 import (  # noqa: E402
    decode_frames,
    encode_images,
    encode_texts,
    ensure_idle_gpu,
    load_video_index,
    sha256_file,
)


MMR_LAMBDA = 0.70
EXPECTED_CANDIDATES = 64
SELECTED_VIEWS = 8
FORBIDDEN_KEYS = {
    "answer",
    "reference_answer",
    "ground_truth",
    "reward",
    "label",
    "evidence_state",
    "pairwise_target",
}


class ProtocolError(RuntimeError):
    pass


def encode_images(model, processor, images, device, batch_size=48):
    import torch

    outputs = []
    for offset in range(0, len(images), batch_size):
        batch = processor(
            images=images[offset : offset + batch_size],
            return_tensors="pt",
        ).to(device)
        batch["pixel_values"] = batch["pixel_values"].to(
            dtype=next(model.parameters()).dtype
        )
        with torch.no_grad():
            features = model.get_image_features(**batch)
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        outputs.append(
            torch.nn.functional.normalize(features.float(), dim=-1).cpu()
        )
    return torch.cat(outputs, dim=0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["1", "2", "3", "4", "5"])
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--video-index-dir", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument(
        "--siglip-path",
        type=Path,
        default=Path("/data1/rmx/projectb/models/siglip-so400m-patch14-384"),
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def mmr_indices(
    relevance: np.ndarray,
    embeddings: np.ndarray,
    frame_indices: list[int],
) -> list[int]:
    selected: list[int] = []
    seen_frames: set[int] = set()
    candidates = list(range(len(relevance)))
    while len(selected) < SELECTED_VIEWS:
        best_index = None
        best_key = None
        for candidate in candidates:
            frame_index = int(frame_indices[candidate])
            if frame_index in seen_frames:
                continue
            redundancy = (
                max(
                    float(np.dot(embeddings[candidate], embeddings[chosen]))
                    for chosen in selected
                )
                if selected else 0.0
            )
            score = (
                MMR_LAMBDA * float(relevance[candidate])
                - (1.0 - MMR_LAMBDA) * redundancy
            )
            key = (score, float(relevance[candidate]), -candidate)
            if best_key is None or key > best_key:
                best_index = candidate
                best_key = key
        if best_index is None:
            raise ProtocolError("MMR could not select eight unique frames")
        selected.append(best_index)
        seen_frames.add(int(frame_indices[best_index]))
    return selected


def load_questions(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "question_id",
        "video",
        "question",
        "official_prompt_text",
        "fold",
        "answer_free",
    }
    if not isinstance(rows, list) or not rows:
        raise ProtocolError("question shard must be a non-empty list")
    if any(not required.issubset(row) for row in rows):
        raise ProtocolError("question shard misses required fields")
    if any(FORBIDDEN_KEYS & set(row) for row in rows):
        raise ProtocolError("question shard contains supervision fields")
    if any(row.get("answer_free") is not True for row in rows):
        raise ProtocolError("question shard is not answer-free")
    return rows


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    audit_path = output.with_suffix(".audit.json")
    if output.exists() or audit_path.exists():
        raise ProtocolError("immutable output already exists")
    question_path = args.questions.resolve()
    questions = load_questions(question_path)
    by_video: dict[str, list[dict[str, Any]]] = {}
    for row in questions:
        by_video.setdefault(str(row["video"]), []).append(row)
    if any(len(rows) != 5 for rows in by_video.values()):
        raise ProtocolError("each selected video must contribute five questions")

    video_index = load_video_index(args.video_index_dir.resolve())
    gpu_snapshot = ensure_idle_gpu(args.gpu_id)
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch
    from transformers import AutoModel, AutoProcessor

    processor = AutoProcessor.from_pretrained(
        args.siglip_path,
        local_files_only=True,
        use_fast=False,
    )
    model = AutoModel.from_pretrained(
        args.siglip_path,
        torch_dtype=torch.bfloat16,
        local_files_only=True,
    ).to("cuda").eval()

    started = time.time()
    results: list[dict[str, Any]] = []
    cache_hashes: dict[str, str] = {}
    for video_number, (video_id, rows) in enumerate(
        sorted(by_video.items()), start=1
    ):
        index = video_index.get(video_id)
        if index is None:
            raise ProtocolError(f"video index missing {video_id}")
        candidate_indices = [
            int(value) for value in index["candidate_frame_indices"]
        ]
        raw32_indices = [
            int(value) for value in index["baseline_frame_indices"]
        ]
        if (
            len(candidate_indices) != EXPECTED_CANDIDATES
            or len(raw32_indices) != 32
            or not set(raw32_indices).issubset(candidate_indices)
        ):
            raise ProtocolError(f"invalid candidate nesting for {video_id}")
        frames = decode_frames(
            args.video_root.resolve() / f"{video_id}.mp4",
            candidate_indices,
        )
        image_features = encode_images(
            model, processor, frames, "cuda"
        ).float().numpy()
        ordered_rows = sorted(rows, key=lambda row: str(row["question_id"]))
        text_features = encode_texts(
            model,
            processor,
            [str(row["question"])[:300] for row in ordered_rows],
            "cuda",
        ).float().numpy()
        for row, text_feature in zip(ordered_rows, text_features):
            relevance = image_features @ text_feature
            selected = mmr_indices(
                relevance, image_features, candidate_indices
            )
            chronological = sorted(
                int(candidate_indices[index]) for index in selected
            )
            results.append({
                "schema_version": "evads_siglip_mmr8_manifest_v1",
                "question_id": str(row["question_id"]),
                "video_id": video_id,
                "fold": int(row["fold"]),
                "candidate64_frame_indices": candidate_indices,
                "raw32_frame_indices": raw32_indices,
                "siglip_mmr8_frame_indices": chronological,
                "selected_view_count": SELECTED_VIEWS,
                "mmr_lambda": MMR_LAMBDA,
                "selection_method": "siglip_mmr64_lambda070_then_chronological_v1",
                "selected_relevance": [
                    float(relevance[index]) for index in selected
                ],
                "query_text_sha256": hashlib.sha256(
                    str(row["question"]).encode("utf-8")
                ).hexdigest(),
                "answer_or_outcome_fields_used": False,
            })
        cache_hashes[video_id] = hashlib.sha256(
            json.dumps(index, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if video_number % 10 == 0:
            print(
                f"processed_videos={video_number}/{len(by_video)}",
                flush=True,
            )
        gc.collect()
        torch.cuda.empty_cache()

    results.sort(key=lambda row: str(row["question_id"]))
    if len(results) != len(questions):
        raise ProtocolError("manifest row count mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "evads_siglip_mmr8_manifest_audit_v1",
        "passed": True,
        "record_count": len(results),
        "video_count": len(by_video),
        "folds": sorted({int(row["fold"]) for row in results}),
        "candidate_count": EXPECTED_CANDIDATES,
        "selected_view_count": SELECTED_VIEWS,
        "mmr_lambda": MMR_LAMBDA,
        "chronological_model_input": True,
        "raw32_nested_in_candidate64": True,
        "answer_or_outcome_fields_used": False,
        "gpu_snapshot_before_load": gpu_snapshot,
        "question_file_sha256": sha256_file(question_path),
        "siglip_config_sha256": sha256_file(
            args.siglip_path.resolve() / "config.json"
        ),
        "output_sha256": sha256_file(output),
        "video_index_record_hashes": cache_hashes,
        "elapsed_seconds": time.time() - started,
    }
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: value
        for key, value in audit.items()
        if key != "video_index_record_hashes"
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
