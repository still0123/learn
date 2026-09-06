#!/usr/bin/env python3
"""Merge the two disjoint AdsQA partitions into a Full-7,844 result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from judge_adsqa_full5320_v1 import metrics, pairwise


METHODS = ("Uniform8", "MMR8", "AdaptiveScale")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-four-arm-rows", type=Path, required=True)
    parser.add_argument("--old-threshold-rows", type=Path, required=True)
    parser.add_argument("--supplement-rows", type=Path, required=True)
    parser.add_argument("--old-excluded", type=Path, required=True)
    parser.add_argument("--supplement-excluded", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise RuntimeError(f"expected JSON list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def normalize_old(
    four_arm_rows: list[dict[str, Any]],
    threshold_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    four_by_id = {str(row["question_id"]): row for row in four_arm_rows}
    threshold_by_id = {str(row["question_id"]): row for row in threshold_rows}
    if (
        len(four_by_id) != 5319
        or len(threshold_by_id) != 5319
        or set(four_by_id) != set(threshold_by_id)
    ):
        raise RuntimeError("old Full-5,319 pools do not align")
    normalized = []
    for qid in sorted(four_by_id):
        old = four_by_id[qid]
        threshold = threshold_by_id[qid]
        if float(old["MMR8_score"]) != float(threshold["MMR8_score"]):
            raise RuntimeError(f"old MMR score mismatch: {qid}")
        normalized.append(
            {
                "question_id": qid,
                "video_id": str(threshold["video_id"]),
                "question_type": str(threshold["question_type"]),
                "triggered": bool(threshold["triggered"]),
                "source_partition": "answer",
                "Uniform8_score": float(old["Uniform8_score"]),
                "MMR8_score": float(threshold["MMR8_score"]),
                "AdaptiveScale_score": float(
                    threshold["ThresholdAdaptiveA2_score"]
                ),
            }
        )
    return normalized


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")

    old = normalize_old(
        load_records(args.old_four_arm_rows),
        load_records(args.old_threshold_rows),
    )
    supplement_source = load_records(args.supplement_rows)
    if len(supplement_source) != 2525:
        raise RuntimeError("supplement result is not frozen 2,525")
    supplement = [
        {
            "question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "question_type": str(row["question_type"]),
            "triggered": bool(row["triggered"]),
            "source_partition": "gt_answer",
            "Uniform8_score": float(row["Uniform8_score"]),
            "MMR8_score": float(row["MMR8_score"]),
            "AdaptiveScale_score": float(row["AdaptiveScale_score"]),
        }
        for row in supplement_source
    ]
    old_ids = {row["question_id"] for row in old}
    supplement_ids = {row["question_id"] for row in supplement}
    if old_ids & supplement_ids:
        raise RuntimeError("old and supplement result pools overlap")

    expanded = sorted(old + supplement, key=lambda row: row["question_id"])
    if len(expanded) != 7844:
        raise RuntimeError("combined pool is not frozen 7,844")
    excluded = (
        load_records(args.old_excluded)
        + load_records(args.supplement_excluded)
    )
    if len(excluded) != 2:
        raise RuntimeError("expected two distinct excluded questions")
    excluded_ids = {str(row["question_id"]) for row in excluded}
    if len(excluded_ids) != 2 or excluded_ids & {
        row["question_id"] for row in expanded
    }:
        raise RuntimeError("excluded question audit failed")

    comparisons = {
        "MMR8_vs_Uniform8": pairwise(
            expanded, "MMR8_score", "Uniform8_score", 10000, 2026073011
        ),
        "AdaptiveScale_vs_MMR8": pairwise(
            expanded, "AdaptiveScale_score", "MMR8_score", 10000, 2026073012
        ),
        "AdaptiveScale_vs_Uniform8": pairwise(
            expanded, "AdaptiveScale_score", "Uniform8_score", 10000, 2026073013
        ),
    }
    partition_results = {}
    for partition in ("answer", "gt_answer"):
        subset = [
            row for row in expanded if row["source_partition"] == partition
        ]
        partition_results[partition] = {
            "count": len(subset),
            "methods": {
                method: metrics(subset, f"{method}_score")
                for method in METHODS
            },
            "AdaptiveScale_vs_MMR8": pairwise(
                subset,
                "AdaptiveScale_score",
                "MMR8_score",
                10000,
                2026073014 if partition == "answer" else 2026073015,
            ),
        }
    type_results = {}
    for question_type in sorted({row["question_type"] for row in expanded}):
        subset = [
            row for row in expanded if row["question_type"] == question_type
        ]
        type_results[question_type] = {
            method: metrics(subset, f"{method}_score")
            for method in METHODS
        }

    triggered = [row for row in expanded if row["triggered"]]
    trigger_rate = len(triggered) / len(expanded)
    summary = {
        "schema_version": "adsqa_full7844_combined_summary_v1",
        "not_human_gold": True,
        "provisional": True,
        "source_question_count": 7846,
        "evaluated_question_count": len(expanded),
        "excluded_question_count": len(excluded),
        "excluded": excluded,
        "partition_counts": {
            "answer": len(old),
            "gt_answer": len(supplement),
        },
        "complete7844": {
            method: metrics(expanded, f"{method}_score")
            for method in METHODS
        },
        "comparisons": comparisons,
        "partition_results": partition_results,
        "question_type_stratified": type_results,
        "deployment": {
            "frozen_threshold": 0.9602926671504974,
            "trigger_count_evaluated": len(triggered),
            "trigger_rate_evaluated": trigger_rate,
            "MMR8_visual_tokens": 1024,
            "trigger_A2_visual_tokens": 3104,
            "average_answer_visual_tokens": (
                1024.0 + trigger_rate * (3104.0 - 1024.0)
            ),
        },
        "hashes": {
            "old_four_arm_rows_sha256": sha256_file(args.old_four_arm_rows),
            "old_threshold_rows_sha256": sha256_file(args.old_threshold_rows),
            "supplement_rows_sha256": sha256_file(args.supplement_rows),
            "old_excluded_sha256": sha256_file(args.old_excluded),
            "supplement_excluded_sha256": sha256_file(
                args.supplement_excluded
            ),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows_path = args.output_dir / "expanded_scores_7844.jsonl"
    excluded_path = args.output_dir / "excluded_two_unparseable.jsonl"
    write_jsonl(rows_path, expanded)
    write_jsonl(excluded_path, excluded)
    summary["hashes"]["expanded_scores_sha256"] = sha256_file(rows_path)
    summary["hashes"]["excluded_sha256"] = sha256_file(excluded_path)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
