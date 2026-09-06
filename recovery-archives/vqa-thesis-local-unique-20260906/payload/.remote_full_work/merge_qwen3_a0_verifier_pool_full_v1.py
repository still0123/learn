#!/usr/bin/env python3
"""Merge five full-set RealClaim score shards with variable-sized videos."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-dir", type=Path, required=True)
    parser.add_argument("--scores-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--expected-videos", type=int, required=True)
    parser.add_argument("--expected-per-fold", type=int, required=True)
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


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    inputs = load_jsonl(args.pool_dir / "model_inputs_all.jsonl")
    by_id = {str(row["question_id"]): row for row in inputs}
    if len(inputs) != args.expected_count or len(by_id) != args.expected_count:
        raise RuntimeError("A0 verifier pool count mismatch")
    scores: list[dict[str, Any]] = []
    shard_hashes = {}
    for fold in range(5):
        path = args.scores_root / f"fold_{fold}" / "scores.jsonl"
        summary_path = args.scores_root / f"fold_{fold}" / "summary.json"
        if not path.is_file() or not summary_path.is_file():
            raise RuntimeError(f"missing verifier shard {fold}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if (
            summary.get("complete") is not True
            or int(summary.get("rows", -1)) != args.expected_per_fold
            or summary.get("secondary_frame_sampling_disabled") is not True
        ):
            raise RuntimeError(f"invalid verifier summary for fold {fold}")
        shard = load_jsonl(path)
        if len(shard) != args.expected_per_fold:
            raise RuntimeError(f"incomplete verifier shard {fold}")
        scores.extend(shard)
        shard_hashes[str(fold)] = sha256_file(path)
    if (
        len(scores) != args.expected_count
        or len({str(row["question_id"]) for row in scores})
        != args.expected_count
        or set(by_id) != {str(row["question_id"]) for row in scores}
    ):
        raise RuntimeError("merged verifier scores do not align with pool")
    enriched = []
    for score in scores:
        source = by_id[str(score["question_id"])]
        enriched.append(
            {
                **score,
                "source_question_id": str(source["source_question_id"]),
                "fold": int(source["fold"]),
                "video_id": str(source["video_id"]),
            }
        )
    enriched.sort(
        key=lambda row: (int(row["fold"]), str(row["source_question_id"]))
    )
    probabilities = [float(row["support_probability"]) for row in enriched]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    output = args.output_dir / "scores_all.jsonl"
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in enriched),
        encoding="utf-8",
    )
    summary = {
        "schema_version": "qwen3_a0_realclaim_full5320_merge_v1",
        "passed": (
            len(enriched) == args.expected_count
            and len({str(row["video_id"]) for row in enriched})
            == args.expected_videos
        ),
        "row_count": len(enriched),
        "video_count": len({str(row["video_id"]) for row in enriched}),
        "fold_counts": {
            str(fold): sum(int(row["fold"]) == fold for row in enriched)
            for fold in range(5)
        },
        "support_probability": {
            "min": min(probabilities),
            "q10": quantile(probabilities, 0.10),
            "median": quantile(probabilities, 0.50),
            "mean": mean(probabilities),
            "max": max(probabilities),
        },
        "all_have_eight_views": all(
            int(row["represented_views"]) == 8 for row in enriched
        ),
        "secondary_sampling_disabled": all(
            row.get("secondary_frame_sampling") is False for row in enriched
        ),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "shard_sha256": shard_hashes,
        "scores_all_sha256": sha256_file(output),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not summary["passed"]:
        raise RuntimeError("full A0 verifier merge audit failed")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
