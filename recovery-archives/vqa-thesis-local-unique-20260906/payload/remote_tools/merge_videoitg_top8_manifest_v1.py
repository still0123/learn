#!/usr/bin/env python3
"""Merge and audit two answer-free VideoITG Top-8 cache shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--cache-shard", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.audit.exists():
        raise RuntimeError("immutable merged output already exists")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    required = {"question_id", "video", "question", "fold", "source_split"}
    forbidden = {"answer", "ground_truth", "reference_answer", "label", "prediction", "judge_score"}
    if len(questions) != 500 or any(not required.issubset(row) for row in questions):
        raise RuntimeError("questions are not the frozen answer-free OOF500")
    if any(forbidden & set(row) for row in questions):
        raise RuntimeError("question file contains outcome-side fields")
    question_by_id = {str(row["question_id"]): row for row in questions}

    cache_rows: list[dict[str, Any]] = []
    for path in args.cache_shard:
        cache_rows.extend(load_jsonl(path))
    cache_by_id = {str(row["question_id"]): row for row in cache_rows}
    if len(cache_rows) != 500 or len(cache_by_id) != 500 or set(cache_by_id) != set(question_by_id):
        raise RuntimeError("VideoITG shards do not exactly cover OOF500")

    output_rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for question_id, question in question_by_id.items():
        row = cache_by_id[question_id]
        selected = [int(value) for value in row["selected_frame_indices"]]
        candidates = [int(value) for value in row["candidate_frame_indices"]]
        if (
            str(row["video_id"]) != str(question["video"])
            or int(row["candidate_count"]) != 64
            or len(candidates) != 64
            or len(selected) != 8
            or selected != sorted(selected)
            or len(set(selected)) != 8
            or not set(selected).issubset(candidates)
        ):
            failures.append(question_id)
            continue
        output_rows.append(
            {
                "schema_version": "adsqa_answer_free_selected8_manifest_v1",
                "question_id": question_id,
                "video_id": str(row["video_id"]),
                "fold": int(question["fold"]),
                "selection_method": "videoitg_top8_of_nested64_then_chronological_v1",
                "candidate_count": 64,
                "selected_view_count": 8,
                "selected_frame_indices": selected,
                "selection_inputs": ["question", "video_frames"],
                "selector": "videoitg_8b",
                "candidate_sampling_policy": row["candidate_sampling_policy"],
                "answer_or_outcome_fields_used": False,
            }
        )
    if failures or len(output_rows) != 500:
        raise RuntimeError(f"invalid VideoITG rows: {failures[:10]}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in output_rows),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "adsqa_videoitg_top8_manifest_audit_v1",
        "passed": True,
        "question_count": 500,
        "video_count": len({row["video_id"] for row in output_rows}),
        "candidate_count": 64,
        "selected_view_count": 8,
        "all_selected_frames_unique_and_chronological": True,
        "answer_or_outcome_fields_used": False,
        "question_file_sha256": sha256_file(args.questions),
        "cache_shard_sha256": {str(path): sha256_file(path) for path in args.cache_shard},
        "output_sha256": sha256_file(args.output),
    }
    args.audit.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
