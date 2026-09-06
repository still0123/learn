#!/usr/bin/env python3
"""Merge immutable one-row raw-feature files in frozen question order."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--expected-count", required=True, type=int)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.audit.exists():
        raise RuntimeError("refusing to overwrite merged singleton artifacts")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    expected_ids = [str(row["question_id"]) for row in questions]
    if len(expected_ids) != args.expected_count or len(set(expected_ids)) != len(expected_ids):
        raise RuntimeError("frozen question list does not match expected count")

    rows_by_id = {}
    inputs = sorted(args.input_dir.glob("*.jsonl"))
    for path in inputs:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(lines) != 1:
            raise RuntimeError(f"singleton output must contain one row: {path}")
        row = json.loads(lines[0])
        question_id = str(row.get("question_id", ""))
        if not question_id or question_id in rows_by_id:
            raise RuntimeError(f"missing or duplicate question ID: {question_id}")
        rows_by_id[question_id] = row
    if set(rows_by_id) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(rows_by_id))
        extra = sorted(set(rows_by_id) - set(expected_ids))
        raise RuntimeError(f"singleton coverage mismatch missing={missing[:5]} extra={extra[:5]}")

    ordered = [rows_by_id[question_id] for question_id in expected_ids]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in ordered),
        encoding="utf-8",
    )
    temporary.replace(args.output)
    fallback_audits = sorted(
        path.name
        for path in (
            args.input_dir.parents[3] / "decode_recovery_v1"
        ).glob("*.json")
        if "decord_retry" not in path.name
    )
    audit = {
        "schema_version": "adsqa_answer_free_raw_feature_singleton_merge_v1",
        "passed": True,
        "expected_count": args.expected_count,
        "record_count": len(ordered),
        "input_file_count": len(inputs),
        "question_order_preserved": [row["question_id"] for row in ordered] == expected_ids,
        "questions_sha256": sha256_file(args.questions),
        "output_sha256": sha256_file(args.output),
        "decode_fallback_audit_files": fallback_audits,
        "answer_or_outcome_fields_used": False,
    }
    args.audit.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
