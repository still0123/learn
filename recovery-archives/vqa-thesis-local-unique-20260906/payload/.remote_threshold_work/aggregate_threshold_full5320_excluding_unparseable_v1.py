#!/usr/bin/env python3
"""Aggregate the threshold policy after excluding one unparseable judge item."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from judge_adsqa_full5320_v1 import metrics, pairwise, primary_type


METHODS = ("MMR8", "ThresholdAdaptiveA2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
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


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")

    preflight = json.loads(
        (args.preflight_root / "dry_run_audit.json").read_text(encoding="utf-8")
    )
    if (
        preflight.get("passed") is not True
        or int(preflight.get("question_count", -1)) != 5320
        or int(preflight.get("required_new_api_call_count", -1)) != 4304
        or int(preflight.get("historical_exact_reuse_count", -1)) != 5833
    ):
        raise RuntimeError("preflight audit is invalid")

    groundtruth = load_records(args.groundtruth)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    candidate_path = args.preflight_root / "candidates_answer_free.jsonl"
    candidates = load_records(candidate_path)
    reused_path = args.preflight_root / "reused_scores.jsonl"
    partial_path = args.results_root / "api_results_partial.jsonl"
    first_failure_path = args.results_root / "api_failures.jsonl"
    retry_failure_path = args.results_root / "api_failures_retry1.jsonl"
    reused = load_records(reused_path)
    partial = load_records(partial_path)
    failures = load_records(first_failure_path)
    retry_failures = load_records(retry_failure_path)
    if (
        len(gt_by_id) != 5320
        or len(candidates) != 5320
        or len(reused) != 5833
        or len(partial) != 4303
        or len(failures) != 1
        or len(retry_failures) != 1
    ):
        raise RuntimeError("score or failure counts do not match frozen history")
    if (
        failures[0]["question_id"] != retry_failures[0]["question_id"]
        or failures[0]["candidate_prediction_sha256"]
        != retry_failures[0]["candidate_prediction_sha256"]
    ):
        raise RuntimeError("initial and retry failures differ")

    all_scores = {}
    for row in reused + partial:
        key = (
            str(row["question_id"]),
            str(row["candidate_prediction_sha256"]),
        )
        score = float(row["score"])
        if key in all_scores and all_scores[key] != score:
            raise RuntimeError(f"conflicting score: {key}")
        all_scores[key] = score

    expanded = []
    excluded = []
    for source in candidates:
        qid = str(source["question_id"])
        hashes = source["candidate_sha256"]
        missing = [
            method
            for method in METHODS
            if (qid, str(hashes[method])) not in all_scores
        ]
        if missing:
            excluded.append(
                {
                    "question_id": qid,
                    "candidate_prediction_sha256": {
                        method: str(hashes[method]) for method in missing
                    },
                    "missing_methods": missing,
                    "reason": "deepseek_output_unparseable_twice",
                }
            )
            continue
        gt = gt_by_id[qid]
        row = {
            "question_id": qid,
            "video_id": str(gt["video"]),
            "question_type": primary_type(gt),
            "triggered": bool(source["triggered"]),
        }
        for method in METHODS:
            row[f"{method}_score"] = all_scores[
                (qid, str(hashes[method]))
            ]
        expanded.append(row)
    if len(expanded) != 5319 or len(excluded) != 1:
        raise RuntimeError("expected exactly one excluded question")

    triggered = [row for row in expanded if row["triggered"]]
    nontriggered = [row for row in expanded if not row["triggered"]]
    type_results = {}
    for question_type in sorted(
        {row["question_type"] for row in expanded}
    ):
        subset = [
            row
            for row in expanded
            if row["question_type"] == question_type
        ]
        type_results[question_type] = {
            method: metrics(subset, f"{method}_score")
            for method in METHODS
        }
    comparison = pairwise(
        expanded,
        "ThresholdAdaptiveA2_score",
        "MMR8_score",
        10000,
        2026072901,
    )
    triggered_comparison = pairwise(
        triggered,
        "ThresholdAdaptiveA2_score",
        "MMR8_score",
        10000,
        2026072902,
    )
    usage_totals = {
        key: sum(
            int((row.get("judge_usage") or {}).get(key) or 0)
            for row in partial
        )
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    trigger_rate = 4905 / 5320
    summary = {
        "schema_version": (
            "qwen3_threshold_full5320_provisional_excluding_one_v1"
        ),
        "not_human_gold": True,
        "provisional": True,
        "evaluated_question_count": 5319,
        "excluded_question_count": 1,
        "excluded": excluded,
        "initial_authorized_calls": 4304,
        "authorized_retry_calls": 1,
        "successful_unique_new_scores": 4303,
        "initial_failures": 1,
        "retry_failures": 1,
        "automatic_retries": 0,
        "historical_exact_reuse_count": 5833,
        "new_api_usage_totals": usage_totals,
        "complete5319": {
            method: metrics(expanded, f"{method}_score")
            for method in METHODS
        },
        "ThresholdAdaptiveA2_vs_MMR8": comparison,
        "triggered_subset": {
            "count": len(triggered),
            "methods": {
                method: metrics(triggered, f"{method}_score")
                for method in METHODS
            },
            "comparison": triggered_comparison,
        },
        "nontriggered_subset": {
            "count": len(nontriggered),
            "identical_to_MMR8": all(
                row["MMR8_score"] == row["ThresholdAdaptiveA2_score"]
                for row in nontriggered
            ),
        },
        "question_type_stratified": type_results,
        "deployment": {
            "frozen_threshold": float(preflight["frozen_threshold"]),
            "full_trigger_count": 4905,
            "full_trigger_rate": trigger_rate,
            "MMR8_visual_tokens": 1024,
            "trigger_A2_visual_tokens": 3104,
            "full_average_answer_visual_tokens": (
                1024.0 + trigger_rate * (3104.0 - 1024.0)
            ),
        },
        "hashes": {
            "groundtruth_sha256": sha256_file(args.groundtruth),
            "candidates_sha256": sha256_file(candidate_path),
            "preflight_sha256": sha256_file(
                args.preflight_root / "dry_run_audit.json"
            ),
            "reuse_sha256": sha256_file(reused_path),
            "partial_sha256": sha256_file(partial_path),
            "initial_failure_sha256": sha256_file(first_failure_path),
            "retry_failure_sha256": sha256_file(retry_failure_path),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output_dir / "expanded_threshold_scores_5319.jsonl", expanded)
    write_jsonl(args.output_dir / "excluded_unparseable.jsonl", excluded)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
