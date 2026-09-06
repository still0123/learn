#!/usr/bin/env python3
"""Aggregate the AdsQA supplement after excluding one unparseable item."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from judge_adsqa_full5320_v1 import metrics, pairwise, primary_type


METHODS = ("Uniform8", "CLIPTopK8", "MMR8", "AdaptiveScale")


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
        or int(preflight.get("question_count", -1)) != 2526
        or int(preflight.get("required_new_api_call_count", -1)) != 9807
        or int(preflight.get("historical_exact_reuse_count", -1)) != 0
        or tuple(preflight.get("methods", [])) != METHODS
    ):
        raise RuntimeError("preflight audit is invalid")

    groundtruth = load_records(args.groundtruth)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    candidate_path = args.preflight_root / "candidates_answer_free.jsonl"
    candidates = load_records(candidate_path)
    partial_path = args.results_root / "api_results_partial.jsonl"
    first_failure_path = args.results_root / "api_failures.jsonl"
    retry_failure_path = args.results_root / "api_failures_retry1.jsonl"
    partial = load_records(partial_path)
    failures = load_records(first_failure_path)
    retry_failures = load_records(retry_failure_path)
    if (
        len(gt_by_id) != 2526
        or len(candidates) != 2526
        or len(partial) != 9806
        or len(failures) != 3950
        or len(retry_failures) != 1
    ):
        raise RuntimeError("score or failure counts do not match frozen history")

    retry_key = (
        str(retry_failures[0]["question_id"]),
        str(retry_failures[0]["candidate_prediction_sha256"]),
    )
    initial_failure_keys = {
        (
            str(row["question_id"]),
            str(row["candidate_prediction_sha256"]),
        )
        for row in failures
    }
    if retry_key not in initial_failure_keys:
        raise RuntimeError("retry failure is absent from initial failures")

    all_scores = {}
    for row in partial:
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
    if len(expanded) != 2525 or len(excluded) != 1:
        raise RuntimeError("expected exactly one excluded question")

    triggered = [row for row in expanded if row["triggered"]]
    nontriggered = [row for row in expanded if not row["triggered"]]
    if not all(
        row["MMR8_score"] == row["AdaptiveScale_score"]
        for row in nontriggered
    ):
        raise RuntimeError("nontriggered AdaptiveScale differs from MMR8")

    type_results = {}
    for question_type in sorted({row["question_type"] for row in expanded}):
        subset = [
            row for row in expanded if row["question_type"] == question_type
        ]
        type_results[question_type] = {
            method: metrics(subset, f"{method}_score")
            for method in METHODS
        }

    comparisons = {
        "MMR8_vs_Uniform8": pairwise(
            expanded, "MMR8_score", "Uniform8_score", 10000, 2026073001
        ),
        "CLIPTopK8_vs_Uniform8": pairwise(
            expanded, "CLIPTopK8_score", "Uniform8_score", 10000, 2026073002
        ),
        "AdaptiveScale_vs_MMR8": pairwise(
            expanded, "AdaptiveScale_score", "MMR8_score", 10000, 2026073003
        ),
        "AdaptiveScale_vs_Uniform8": pairwise(
            expanded, "AdaptiveScale_score", "Uniform8_score", 10000, 2026073004
        ),
    }
    triggered_comparison = pairwise(
        triggered,
        "AdaptiveScale_score",
        "MMR8_score",
        10000,
        2026073005,
    )
    usage_totals = {
        key: sum(
            int((row.get("judge_usage") or {}).get(key) or 0)
            for row in partial
        )
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    trigger_rate = len(triggered) / len(expanded)
    summary = {
        "schema_version": "adsqa_supplement2526_excluding_one_v1",
        "not_human_gold": True,
        "provisional": True,
        "original_question_count": 2526,
        "evaluated_question_count": len(expanded),
        "excluded_question_count": len(excluded),
        "excluded": excluded,
        "initial_authorized_calls": 9807,
        "authorized_retry_calls": 3950,
        "successful_unique_scores": len(partial),
        "initial_failures": len(failures),
        "retry_failures": len(retry_failures),
        "automatic_retries": 0,
        "new_api_usage_totals": usage_totals,
        "complete2525": {
            method: metrics(expanded, f"{method}_score")
            for method in METHODS
        },
        "comparisons": comparisons,
        "triggered_subset": {
            "count": len(triggered),
            "methods": {
                method: metrics(triggered, f"{method}_score")
                for method in METHODS
            },
            "AdaptiveScale_vs_MMR8": triggered_comparison,
        },
        "nontriggered_subset": {
            "count": len(nontriggered),
            "identical_to_MMR8": True,
        },
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
            "groundtruth_sha256": sha256_file(args.groundtruth),
            "candidates_sha256": sha256_file(candidate_path),
            "preflight_sha256": sha256_file(
                args.preflight_root / "dry_run_audit.json"
            ),
            "partial_sha256": sha256_file(partial_path),
            "initial_failure_sha256": sha256_file(first_failure_path),
            "retry_failure_sha256": sha256_file(retry_failure_path),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output_dir / "expanded_scores_2525.jsonl", expanded)
    write_jsonl(args.output_dir / "excluded_unparseable.jsonl", excluded)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
