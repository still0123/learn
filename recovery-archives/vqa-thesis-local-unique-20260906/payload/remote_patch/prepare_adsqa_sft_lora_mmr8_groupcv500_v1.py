#!/usr/bin/env python3
"""Prepare immutable answer-free MMR8 inputs for AdsSFTLoRA GroupCV-500."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    forbidden = {
        "answer",
        "answers",
        "ground_truth",
        "reference_answer",
        "judge_score",
        "prediction",
    }
    source: dict[str, dict[str, Any]] = {}
    for line in args.source_manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if forbidden & set(row):
            raise RuntimeError("source manifest contains outcome fields")
        qid = str(row["question_id"])
        indices = [int(value) for value in row["siglip_mmr8_frame_indices"]]
        if len(indices) != 8 or len(set(indices)) != 8 or indices != sorted(indices):
            raise RuntimeError(f"invalid MMR8 indices for {qid}")
        source[qid] = {
            "schema_version": "adsqa_sft_lora_mmr8_manifest_v1",
            "question_id": qid,
            "video_id": str(row["video_id"]),
            "fold": int(row["fold"]),
            "selection_method": "SigLIP_MMR8_answer_free",
            "selected_frame_indices": indices,
            "answer_or_outcome_fields_used": False,
        }
    all_qids: set[str] = set()
    fold_counts: dict[str, int] = {}
    fold_videos: dict[int, set[str]] = {}
    for fold in range(5):
        question_path = args.splits_root / f"fold_{fold}/validation_questions.json"
        questions = json.loads(question_path.read_text(encoding="utf-8"))
        if len(questions) != 100:
            raise RuntimeError(f"fold {fold} does not contain 100 questions")
        qids = [str(row["question_id"]) for row in questions]
        videos = {str(row["video"]) for row in questions}
        if len(set(qids)) != 100 or any(int(row["fold"]) != fold for row in questions):
            raise RuntimeError(f"fold {fold} question schema mismatch")
        if any(forbidden & set(row) for row in questions):
            raise RuntimeError(f"fold {fold} question file contains outcomes")
        if any(qid not in source or int(source[qid]["fold"]) != fold for qid in qids):
            raise RuntimeError(f"fold {fold} manifest coverage mismatch")
        if any(source[qid]["video_id"] != str(row["video"]) for qid, row in zip(qids, questions)):
            raise RuntimeError(f"fold {fold} video mapping mismatch")
        write_json(args.output_dir / f"fold_{fold}/questions100.json", questions)
        write_json(args.output_dir / f"fold_{fold}/smoke5_questions.json", questions[:5])
        fold_counts[str(fold)] = len(qids)
        fold_videos[fold] = videos
        all_qids.update(qids)
    if len(all_qids) != 500 or set(source) != all_qids:
        raise RuntimeError("MMR8 source and GroupCV-500 questions do not align")
    leakage = {
        str(fold): sorted(
            fold_videos[fold]
            & set().union(
                *(fold_videos[other] for other in range(5) if other != fold)
            )
        )
        for fold in range(5)
    }
    if any(leakage.values()):
        raise RuntimeError("video leakage across folds")
    manifest = [source[qid] for qid in sorted(source)]
    write_jsonl(args.output_dir / "mmr8_manifest.jsonl", manifest)
    audit = {
        "schema_version": "adsqa_sft_lora_mmr8_inputs_audit_v1",
        "passed": True,
        "question_count": len(all_qids),
        "video_count": len(set().union(*fold_videos.values())),
        "fold_counts": fold_counts,
        "fold_video_leakage": leakage,
        "exact_views": all(
            len(row["selected_frame_indices"]) == 8 for row in manifest
        ),
        "answer_or_outcome_fields_used": False,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "normalized_manifest_sha256": sha256_file(
            args.output_dir / "mmr8_manifest.jsonl"
        ),
    }
    write_json(args.output_dir / "audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
