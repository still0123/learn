#!/usr/bin/env python3
"""Split frozen answer-free E-VAds policy requests by fold."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "reference_answer",
    "ground_truth",
    "label",
    "reward",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-items", type=int, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError("output directory already exists")
    rows = read_jsonl(args.requests)
    keys = {
        (str(row["question_id"]), int(row["anchor_index"])) for row in rows
    }
    counts = Counter(int(row["fold"]) for row in rows)
    expected_per_fold = args.expected_items // 5
    if (
        args.expected_items <= 0
        or args.expected_items % 5
        or len(rows) != args.expected_items
        or len(keys) != args.expected_items
        or any(FORBIDDEN & set(row) for row in rows)
        or counts != Counter({fold: expected_per_fold for fold in range(5)})
    ):
        raise RuntimeError("policy requests are not a complete answer-free set")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for fold in range(5):
        path = args.output_dir / f"fold_{fold}.jsonl"
        fold_rows = [row for row in rows if int(row["fold"]) == fold]
        write_jsonl(path, fold_rows)
        hashes[path.name] = sha256(path)
    audit = {
        "schema_version": "evads_policy_request_shards_audit_v1",
        "passed": True,
        "source_requests_sha256": sha256(args.requests),
        "counts": dict(sorted(counts.items())),
        "hashes": hashes,
        "reference_answer_used": False,
        "judge_scores_used": False,
    }
    (args.output_dir.parent / "shard_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
