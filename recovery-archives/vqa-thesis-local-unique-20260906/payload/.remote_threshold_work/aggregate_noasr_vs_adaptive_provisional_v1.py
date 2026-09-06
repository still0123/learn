#!/usr/bin/env python3
"""Aggregate a no-API paired summary after one authorized judge call failed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from judge_adsqa_full5320_v1 import metrics, pairwise, primary_type


METHODS = ("AdaptiveScale12", "NoASR12")


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")
    failures = load_records(args.results_root / "api_failures.jsonl")
    partial = load_records(args.results_root / "api_results_partial.jsonl")
    reused = load_records(args.preflight_root / "reused_scores.jsonl")
    candidates = load_records(args.preflight_root / "candidates_answer_free.jsonl")
    groundtruth = load_records(args.groundtruth)
    if len(failures) != 1 or len(partial) != 3158 or len(reused) != 5249 or len(candidates) != 4905:
        raise RuntimeError("unexpected incomplete judge state")
    failed_qid = str(failures[0]["question_id"])
    failed_hash = str(failures[0]["candidate_prediction_sha256"])
    candidate_by_id = {str(row["question_id"]): row for row in candidates}
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    if len(candidate_by_id) != 4905 or not set(candidate_by_id).issubset(gt_by_id):
        raise RuntimeError("candidate/reference pools do not align")
    score_by_key = {
        (str(row["question_id"]), str(row["candidate_prediction_sha256"])): float(row["score"])
        for row in reused + partial
    }
    failed_owners = [
        method
        for method in METHODS
        if str(candidate_by_id[failed_qid]["candidate_sha256"][method]) == failed_hash
    ]
    if failed_owners != ["AdaptiveScale12", "NoASR12"]:
        raise RuntimeError("failed candidate does not map to the expected shared answer")

    rows = []
    for qid, candidate in sorted(candidate_by_id.items()):
        if qid == failed_qid:
            continue
        reference = gt_by_id[qid]
        row = {
            "question_id": qid,
            "video_id": str(reference["video"]),
            "question_type": primary_type(reference),
        }
        for method in METHODS:
            key = (qid, str(candidate["candidate_sha256"][method]))
            if key not in score_by_key:
                raise RuntimeError(f"missing score for {qid}:{method}")
            row[f"{method}_score"] = score_by_key[key]
        rows.append(row)
    if len(rows) != 4904:
        raise RuntimeError("wrong provisional paired sample size")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output_dir / "expanded_scores_4904.jsonl", rows)
    summary = {
        "schema_version": "adsqa_noasr_vs_adaptive_provisional_4904_v1",
        "complete": False,
        "analysis_role": "posthoc_mechanism_attribution",
        "not_human_gold": True,
        "api_called_by_aggregation": False,
        "authorized_calls_attempted": 3159,
        "successful_new_api_calls": 3158,
        "failed_new_api_calls": 1,
        "excluded_question_count": 1,
        "excluded_question_id": failed_qid,
        "excluded_failed_arm": "shared_AdaptiveScale12_NoASR12",
        "evaluated_paired_questions": len(rows),
        "historical_exact_reuse_count": len(reused),
        "triggered4904": {method: metrics(rows, f"{method}_score") for method in METHODS},
        "NoASR12_vs_AdaptiveScale12": pairwise(
            rows, "NoASR12_score", "AdaptiveScale12_score", 10000, 2026072908
        ),
    }
    dump_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
