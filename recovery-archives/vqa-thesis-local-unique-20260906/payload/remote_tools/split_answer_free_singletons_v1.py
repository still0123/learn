#!/usr/bin/env python3
"""Split an answer-free question list into immutable one-row JSON files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("input must be a non-empty JSON list")
    if any(not isinstance(row, dict) or FORBIDDEN_FIELDS & set(row) for row in rows):
        raise RuntimeError("input is not answer-free")
    if len({str(row.get("question_id")) for row in rows}) != len(rows):
        raise RuntimeError("question IDs are missing or duplicated")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.output_dir.iterdir()):
        raise RuntimeError("refusing to overwrite singleton directory")
    records = []
    for index, row in enumerate(rows):
        path = args.output_dir / f"{index:04d}.json"
        path.write_text(
            json.dumps([row], ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        records.append(
            {
                "index": index,
                "question_id": str(row["question_id"]),
                "video_id": str(row["video"]),
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
        )
    audit = {
        "schema_version": "adsqa_answer_free_singleton_split_v1",
        "passed": True,
        "source_path": str(args.input.resolve()),
        "source_sha256": sha256_file(args.input),
        "record_count": len(rows),
        "records": records,
        "answer_or_outcome_fields_used": False,
    }
    audit_path = args.output_dir.parent / "singleton_split_audit.json"
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in audit.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
