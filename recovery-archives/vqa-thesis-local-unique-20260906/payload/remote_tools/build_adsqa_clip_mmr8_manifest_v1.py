#!/usr/bin/env python3
"""Build answer-free CLIPTopK8 and MMR8 manifests from audited 64-frame caches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


MMR_LAMBDA = 0.70
EXPECTED_CANDIDATES = 64
SELECTED_VIEWS = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["1", "2", "3", "4", "5"])
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--clip-cache-root", type=Path, required=True)
    parser.add_argument("--clip-model", type=Path, required=True)
    parser.add_argument("--clip-output", type=Path, required=True)
    parser.add_argument("--mmr-output", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=-1)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_idle_gpu(gpu_id: str) -> list[str]:
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
    active = [line.strip() for line in apps.stdout.splitlines() if line.strip()]
    if active:
        raise RuntimeError(f"GPU{gpu_id} is not idle: {active}")
    return [row for row in rows if row.split(",", 1)[0].strip() == gpu_id]


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def extract_question_text(value: str) -> str:
    marker = "\n\nQuestion:"
    return value.rsplit(marker, 1)[-1].strip() if marker in value else value.strip()


def unique_ranked_indices(scores: Any, frame_indices: Any, count: int) -> list[int]:
    order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    selected: list[int] = []
    seen: set[int] = set()
    for candidate in order:
        frame_index = int(frame_indices[candidate])
        if frame_index in seen:
            continue
        selected.append(candidate)
        seen.add(frame_index)
        if len(selected) == count:
            return selected
    raise RuntimeError("fewer than eight unique cached frames")


def mmr_indices(relevance: Any, embeddings: Any, frame_indices: Any, count: int) -> list[int]:
    import numpy as np

    selected: list[int] = []
    seen_frames: set[int] = set()
    candidates = list(range(len(relevance)))
    while len(selected) < count:
        best_index = None
        best_key = None
        for candidate in candidates:
            frame_index = int(frame_indices[candidate])
            if frame_index in seen_frames:
                continue
            redundancy = (
                max(float(np.dot(embeddings[candidate], embeddings[chosen])) for chosen in selected)
                if selected
                else 0.0
            )
            score = MMR_LAMBDA * float(relevance[candidate]) - (1.0 - MMR_LAMBDA) * redundancy
            key = (score, float(relevance[candidate]), -candidate)
            if best_key is None or key > best_key:
                best_index, best_key = candidate, key
        if best_index is None:
            raise RuntimeError("MMR could not select eight unique frames")
        selected.append(best_index)
        seen_frames.add(int(frame_indices[best_index]))
    return selected


def main() -> None:
    args = parse_args()
    if any(path.exists() for path in (args.clip_output, args.mmr_output, args.audit_output)):
        raise RuntimeError("immutable output already exists")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    required = {"question_id", "video", "question", "fold", "source_split"}
    forbidden = {"answer", "ground_truth", "reference_answer", "label", "prediction", "judge_score"}
    if not isinstance(questions, list) or any(not required.issubset(row) for row in questions):
        raise RuntimeError("invalid answer-free question file")
    if any(forbidden & set(row) for row in questions):
        raise RuntimeError("question file contains outcome-side fields")
    if args.max_items > 0:
        questions = questions[: args.max_items]

    gpu_snapshot = ensure_idle_gpu(args.gpu_id)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id

    import numpy as np
    import torch
    import torch.nn.functional as functional
    from transformers import CLIPTextModelWithProjection, CLIPTokenizer

    options = {"local_files_only": True, "ignore_mismatched_sizes": True}
    text_model = CLIPTextModelWithProjection.from_pretrained(args.clip_model, **options).cuda().eval()
    tokenizer = CLIPTokenizer.from_pretrained(args.clip_model, local_files_only=True)
    query_texts = [extract_question_text(str(row["question"]))[:300] for row in questions]
    query_embeddings: list[Any] = []
    for offset in range(0, len(query_texts), 64):
        batch = query_texts[offset : offset + 64]
        tokens = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=77,
            return_tensors="pt",
        ).to("cuda")
        with torch.inference_mode():
            encoded = functional.normalize(text_model(**tokens).text_embeds, dim=-1)
        query_embeddings.extend(encoded.float().cpu().numpy())

    clip_rows: list[dict[str, Any]] = []
    mmr_rows: list[dict[str, Any]] = []
    cache_hashes: dict[str, str] = {}
    for row, query_embedding in zip(questions, query_embeddings):
        question_id = str(row["question_id"])
        video_id = str(row["video"])
        cache_path = args.clip_cache_root / f"{video_id}.npz"
        payload = np.load(cache_path)
        frame_indices = payload["frame_indices"].astype(np.int64)
        embeddings = payload["embeddings"].astype(np.float32)
        if len(frame_indices) != EXPECTED_CANDIDATES or embeddings.shape != (EXPECTED_CANDIDATES, 768):
            raise RuntimeError(f"invalid CLIP cache for {video_id}")
        embeddings /= np.maximum(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12)
        query_embedding = query_embedding / max(float(np.linalg.norm(query_embedding)), 1e-12)
        relevance = embeddings @ query_embedding
        clip_selected = unique_ranked_indices(relevance, frame_indices, SELECTED_VIEWS)
        mmr_selected = mmr_indices(relevance, embeddings, frame_indices, SELECTED_VIEWS)
        common = {
            "schema_version": "adsqa_answer_free_selected8_manifest_v1",
            "question_id": question_id,
            "video_id": video_id,
            "fold": int(row["fold"]),
            "candidate_count": EXPECTED_CANDIDATES,
            "selected_view_count": SELECTED_VIEWS,
            "selection_inputs": ["question", "cached_clip_image_embeddings", "frame_indices"],
            "answer_or_outcome_fields_used": False,
        }
        clip_rows.append(
            {
                **common,
                "selection_method": "clip_topk64_then_chronological_v1",
                "selected_frame_indices": sorted(int(frame_indices[index]) for index in clip_selected),
                "selected_relevance": [float(relevance[index]) for index in clip_selected],
            }
        )
        mmr_rows.append(
            {
                **common,
                "selection_method": "clip_mmr64_lambda070_then_chronological_v1",
                "mmr_lambda": MMR_LAMBDA,
                "selected_frame_indices": sorted(int(frame_indices[index]) for index in mmr_selected),
                "selected_relevance": [float(relevance[index]) for index in mmr_selected],
            }
        )
        cache_hashes[video_id] = sha256_file(cache_path)

    dump_jsonl(args.clip_output, clip_rows)
    dump_jsonl(args.mmr_output, mmr_rows)
    audit = {
        "schema_version": "adsqa_clip_mmr8_manifest_audit_v1",
        "passed": len(clip_rows) == len(mmr_rows) == len(questions),
        "question_count": len(questions),
        "video_count": len({str(row["video"]) for row in questions}),
        "candidate_count_per_question": EXPECTED_CANDIDATES,
        "selected_view_count": SELECTED_VIEWS,
        "mmr_lambda": MMR_LAMBDA,
        "gpu_snapshot_before_load": gpu_snapshot,
        "question_file_sha256": sha256_file(args.questions),
        "clip_model_config_sha256": sha256_file(args.clip_model / "config.json"),
        "clip_manifest_sha256": sha256_file(args.clip_output),
        "mmr_manifest_sha256": sha256_file(args.mmr_output),
        "cache_hashes": cache_hashes,
        "answer_or_outcome_fields_used": False,
        "chronological_model_input": True,
    }
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "cache_hashes"}, indent=2))


if __name__ == "__main__":
    main()
