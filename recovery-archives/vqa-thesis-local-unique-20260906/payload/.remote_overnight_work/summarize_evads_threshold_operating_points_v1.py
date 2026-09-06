#!/usr/bin/env python3
"""Summarize frozen threshold operating points from answer-free A0 scores."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


THRESHOLDS = {
    "tau_knee": 0.9195213913917542,
    "tau_cost": 0.9361832141876221,
    "tau_accuracy": 0.9602926671504974,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
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
    if args.output.exists():
        raise FileExistsError("immutable operating-point summary exists")
    scores = load_jsonl(args.scores)
    pool = load_jsonl(args.pool)
    source_by_verifier = {
        str(row["question_id"]): str(row["source_question_id"]) for row in pool
    }
    if (
        len(scores) != args.expected_count
        or len(pool) != args.expected_count
        or {str(row["question_id"]) for row in scores}
        != set(source_by_verifier)
    ):
        raise RuntimeError("score and pool coverage mismatch")
    selected: dict[str, set[str]] = {}
    for name, threshold in THRESHOLDS.items():
        selected[name] = {
            source_by_verifier[str(row["question_id"])]
            for row in scores
            if float(row["support_probability"]) <= threshold
        }
    if not (
        selected["tau_knee"]
        <= selected["tau_cost"]
        <= selected["tau_accuracy"]
    ):
        raise RuntimeError("frozen threshold pools are not nested")
    summary = {
        "schema_version": "evads_threshold_operating_points_v1",
        "passed": True,
        "source_question_count": args.expected_count,
        "operating_points": {
            name: {
                "threshold": THRESHOLDS[name],
                "trigger_count": len(question_ids),
                "trigger_rate": len(question_ids) / args.expected_count,
            }
            for name, question_ids in selected.items()
        },
        "nested": True,
        "a2_pool_threshold": THRESHOLDS["tau_accuracy"],
        "a2_pool_count": len(selected["tau_accuracy"]),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "scores_sha256": sha256_file(args.scores),
        "pool_sha256": sha256_file(args.pool),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
