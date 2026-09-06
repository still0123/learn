#!/usr/bin/env python3
"""Split one answer-free shard around a confirmed corrupt video."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN_FIELDS = {
    "answer",
    "ground_truth",
    "reference_answer",
    "prediction",
    "judge_score",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("input must be a non-empty JSON list")
    if any(not isinstance(row, dict) or FORBIDDEN_FIELDS & set(row) for row in rows):
        raise RuntimeError("input is not answer-free")
    matches = [index for index, row in enumerate(rows) if str(row.get("video")) == args.video_id]
    if len(matches) != 1:
        raise RuntimeError(f"expected one recovery video row, found {len(matches)}")

    recovery_index = matches[0]
    parts = {
        "before.json": rows[:recovery_index],
        "recovery.json": rows[recovery_index : recovery_index + 1],
        "after.json": rows[recovery_index + 1 :],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any((args.output_dir / name).exists() for name in parts):
        raise RuntimeError("refusing to overwrite an existing recovery split")
    for name, part in parts.items():
        write_json(args.output_dir / name, part)

    reconstructed = parts["before.json"] + parts["recovery.json"] + parts["after.json"]
    if reconstructed != rows:
        raise RuntimeError("split reconstruction does not equal source input")
    audit = {
        "schema_version": "adsqa_answer_free_decode_recovery_split_v1",
        "passed": True,
        "source_path": str(args.input.resolve()),
        "source_sha256": sha256_file(args.input),
        "source_count": len(rows),
        "recovery_video_id": args.video_id,
        "recovery_question_id": str(rows[recovery_index]["question_id"]),
        "recovery_zero_based_index": recovery_index,
        "part_counts": {name: len(part) for name, part in parts.items()},
        "part_sha256": {
            name: sha256_file(args.output_dir / name)
            for name in parts
        },
        "answer_or_outcome_fields_used": False,
    }
    write_json(args.output_dir / "audit.json", audit)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
