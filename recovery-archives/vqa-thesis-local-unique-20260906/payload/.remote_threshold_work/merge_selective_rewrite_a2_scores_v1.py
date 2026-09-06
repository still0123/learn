#!/usr/bin/env python3
"""Merge five A2 RealClaim score shards and audit frozen coverage."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=50)
    parser.add_argument("--expected-per-fold", type=int, default=10)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    rows: list[dict[str, Any]] = []
    shard_hashes: dict[str, str] = {}
    for fold in range(5):
        path = args.shard_root / f"fold_{fold}" / "scores.jsonl"
        shard = load_jsonl(path)
        if len(shard) != args.expected_per_fold:
            raise RuntimeError(
                f"fold {fold} does not contain {args.expected_per_fold} A2 scores"
            )
        for row in shard:
            row["fold"] = fold
        rows.extend(shard)
        shard_hashes[str(fold)] = sha256_file(path)
    rows.sort(key=lambda row: (int(row["fold"]), str(row["source_question_id"])))
    if (
        len(rows) != args.expected_count
        or len({str(row["source_question_id"]) for row in rows})
        != args.expected_count
    ):
        raise RuntimeError("A2 score coverage mismatch")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    output = args.output_dir / "scores_all.jsonl"
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    values = [float(row["support_probability"]) for row in rows]
    summary = {
        "schema_version": "qwen3_selective_rewrite_a2_score_merge_v1",
        "row_count": len(rows),
        "fold_counts": dict(Counter(str(row["fold"]) for row in rows)),
        "support_probability": {
            "min": min(values),
            "mean": sum(values) / len(values),
            "max": max(values),
        },
        "all_have_eight_verifier_views": all(
            int(row["represented_views"]) == 8 for row in rows
        ),
        "secondary_sampling_disabled": all(
            not row["secondary_frame_sampling"] for row in rows
        ),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "expected_count": args.expected_count,
        "expected_per_fold": args.expected_per_fold,
        "shard_sha256": shard_hashes,
        "scores_all_sha256": sha256_file(output),
        "passed": True,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
