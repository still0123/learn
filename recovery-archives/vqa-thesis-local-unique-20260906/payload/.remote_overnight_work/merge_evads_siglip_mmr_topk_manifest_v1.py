#!/usr/bin/env python3
"""Merge and audit five E-VAds SigLIP-MMR8/TopK8 manifest shards."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--shard-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--expected-videos", type=int, required=True)
    parser.add_argument("--expected-per-fold", type=int, required=True)
    parser.add_argument("--expected-videos-per-fold", type=int, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_selection(
    row: dict[str, Any],
    field: str,
    candidates: list[int],
    qid: str,
) -> None:
    selected = [int(value) for value in row[field]]
    if (
        len(selected) != 8
        or len(set(selected)) != 8
        or selected != sorted(selected)
        or not set(selected).issubset(candidates)
    ):
        raise RuntimeError(f"invalid {field} selection for {qid}")


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.audit_output.exists():
        raise RuntimeError("immutable output already exists")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    expected = {str(row["question_id"]): row for row in questions}
    if (
        len(questions) != args.expected_count
        or len(expected) != args.expected_count
    ):
        raise RuntimeError("question count does not match frozen protocol")

    rows: list[dict[str, Any]] = []
    shard_hashes: dict[str, str] = {}
    shard_audit_hashes: dict[str, str] = {}
    for fold in range(5):
        path = args.shard_dir / f"fold_{fold}.jsonl"
        audit_path = path.with_suffix(".audit.json")
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if (
            audit.get("passed") is not True
            or int(audit.get("record_count", -1)) != args.expected_per_fold
            or int(audit.get("video_count", -1))
            != args.expected_videos_per_fold
        ):
            raise RuntimeError(f"fold {fold} audit did not pass")
        shard_rows = load_jsonl(path)
        if any(int(row["fold"]) != fold for row in shard_rows):
            raise RuntimeError(f"fold {fold} contains another fold")
        rows.extend(shard_rows)
        shard_hashes[str(fold)] = sha256_file(path)
        shard_audit_hashes[str(fold)] = sha256_file(audit_path)

    by_id = {str(row["question_id"]): row for row in rows}
    if (
        len(rows) != args.expected_count
        or len(by_id) != args.expected_count
        or set(by_id) != set(expected)
    ):
        raise RuntimeError("merged manifest does not align with questions")
    for qid, row in by_id.items():
        question = expected[qid]
        if str(row["video_id"]) != str(question["video"]):
            raise RuntimeError(f"video mismatch for {qid}")
        candidates = [int(value) for value in row["candidate64_frame_indices"]]
        if len(candidates) != 64:
            raise RuntimeError(f"invalid candidate64 selection for {qid}")
        validate_selection(row, "siglip_mmr8_frame_indices", candidates, qid)
        validate_selection(row, "siglip_topk8_frame_indices", candidates, qid)
        if row.get("answer_or_outcome_fields_used") is not False:
            raise RuntimeError(f"non-answer-free manifest row for {qid}")

    rows.sort(key=lambda row: str(row["question_id"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    fold_counts = Counter(int(row["fold"]) for row in rows)
    video_count = len({str(row["video_id"]) for row in rows})
    audit = {
        "schema_version": "evads_siglip_mmr_topk_merge_audit_v1",
        "passed": (
            len(rows) == args.expected_count
            and video_count == args.expected_videos
            and dict(fold_counts)
            == {fold: args.expected_per_fold for fold in range(5)}
        ),
        "record_count": len(rows),
        "video_count": video_count,
        "fold_question_counts": dict(sorted(fold_counts.items())),
        "candidate_count": 64,
        "selected_view_count": 8,
        "mmr_lambda": 0.70,
        "all_selected_unique_chronological": True,
        "answer_or_outcome_fields_used": False,
        "question_file_sha256": sha256_file(args.questions),
        "shard_sha256": shard_hashes,
        "shard_audit_sha256": shard_audit_hashes,
        "output_sha256": sha256_file(args.output),
    }
    args.audit_output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise RuntimeError("merged SigLIP manifest protocol audit failed")


if __name__ == "__main__":
    main()
