#!/usr/bin/env python3
"""Aggregate a paired AdsQA result while excluding judge-missing questions."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from judge_adsqa_full5320_v1 import (
    METHODS,
    dump_json,
    metrics,
    pairwise,
    primary_type,
    sha256_file,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--api-results", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-missing-keys", type=int, default=1)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise RuntimeError(f"expected JSON list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    protocol = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    if (
        protocol.get("passed") is not True
        or int(protocol.get("question_count", -1)) != 5320
        or args.bootstrap_samples != 10000
    ):
        raise RuntimeError("frozen protocol audit is invalid")

    candidates = load_records(args.candidates)
    candidate_by_id = {str(row["question_id"]): row for row in candidates}
    if len(candidates) != 5320 or len(candidate_by_id) != 5320:
        raise RuntimeError("candidate pool is not Full-5320")

    reused_path = args.preflight_root / "reused_scores.jsonl"
    pending_path = (
        args.preflight_root / "pending_candidates_answer_only.jsonl"
    )
    reused = load_records(reused_path)
    pending = load_records(pending_path)
    api_rows = load_records(args.api_results)
    scores: dict[tuple[str, str], float] = {}
    for row in reused + api_rows:
        key = (
            str(row["question_id"]),
            str(row["candidate_prediction_sha256"]),
        )
        score = float(row["score"])
        if score not in {0.0, 0.5, 1.0}:
            raise RuntimeError(f"invalid score: {key}")
        if key in scores and scores[key] != score:
            raise RuntimeError(f"conflicting score: {key}")
        scores[key] = score

    all_keys = {
        (
            str(row["question_id"]),
            str(row["candidate_prediction_sha256"]),
        )
        for row in pending
    } | {
        (
            str(row["question_id"]),
            str(row["candidate_prediction_sha256"]),
        )
        for row in reused
    }
    missing_keys = sorted(all_keys - set(scores))
    if len(missing_keys) != args.expected_missing_keys:
        raise RuntimeError(
            f"expected {args.expected_missing_keys} missing keys, "
            f"found {len(missing_keys)}"
        )
    owners_by_key: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for qid, row in candidate_by_id.items():
        for method in METHODS:
            owners_by_key[
                (qid, str(row["candidate_sha256"][method]))
            ].append(method)
    excluded_qids = sorted({key[0] for key in missing_keys})

    expanded: list[dict[str, Any]] = []
    for qid, source in sorted(candidate_by_id.items()):
        if qid in excluded_qids:
            continue
        row: dict[str, Any] = {
            "question_id": qid,
            "video_id": str(source["video_id"]),
            "question_type": primary_type(source),
            "triggered": bool(source["triggered"]),
            "full_method_switched": bool(source["full_method_switched"]),
        }
        for method in METHODS:
            key = (qid, str(source["candidate_sha256"][method]))
            if key not in scores:
                raise RuntimeError(f"unexpected missing method score: {key}")
            row[f"{method}_score"] = scores[key]
        expanded.append(row)
    if len(expanded) != 5320 - len(excluded_qids):
        raise RuntimeError("paired result count mismatch")

    comparisons_spec = [
        ("MMR8_vs_Uniform8", "MMR8_score", "Uniform8_score"),
        (
            "AdaptiveScaleA2_vs_Uniform8",
            "AdaptiveScaleA2_score",
            "Uniform8_score",
        ),
        (
            "FullJointMethod_vs_Uniform8",
            "FullJointMethod_score",
            "Uniform8_score",
        ),
        (
            "AdaptiveScaleA2_vs_MMR8",
            "AdaptiveScaleA2_score",
            "MMR8_score",
        ),
        (
            "FullJointMethod_vs_MMR8",
            "FullJointMethod_score",
            "MMR8_score",
        ),
        (
            "FullJointMethod_vs_AdaptiveScaleA2",
            "FullJointMethod_score",
            "AdaptiveScaleA2_score",
        ),
    ]

    def comparisons(
        rows: list[dict[str, Any]], seed_base: int
    ) -> dict[str, Any]:
        return {
            name: pairwise(
                rows,
                selected_key,
                baseline_key,
                args.bootstrap_samples,
                seed_base + index,
            )
            for index, (name, selected_key, baseline_key)
            in enumerate(comparisons_spec)
        }

    triggered = [row for row in expanded if row["triggered"]]
    switched = [row for row in expanded if row["full_method_switched"]]
    type_results: dict[str, Any] = {}
    for question_type in sorted(
        {row["question_type"] for row in expanded}
    ):
        subset = [
            row for row in expanded
            if row["question_type"] == question_type
        ]
        type_results[question_type] = {
            method: metrics(subset, f"{method}_score")
            for method in METHODS
        }

    args.output_dir.mkdir(parents=True, exist_ok=False)
    expanded_path = args.output_dir / "expanded_scores_excluding_missing.jsonl"
    write_jsonl(expanded_path, expanded)
    missing_audit = [
        {
            "question_id": qid,
            "candidate_prediction_sha256": candidate_hash,
            "owners": sorted(owners_by_key[(qid, candidate_hash)]),
        }
        for qid, candidate_hash in missing_keys
    ]
    dump_json(args.output_dir / "excluded_judge_missing.json", missing_audit)
    summary = {
        "schema_version": (
            "adsqa_full5320_provisional_excluding_judge_missing_v1"
        ),
        "provisional": True,
        "exclusion_reason": "one DeepSeek output repeatedly failed parsing",
        "original_question_count": 5320,
        "paired_question_count": len(expanded),
        "excluded_question_count": len(excluded_qids),
        "excluded_unique_score_count": len(missing_keys),
        "reused_score_count": len(reused),
        "new_api_score_count": len(api_rows),
        "not_human_gold": True,
        "complete_paired": {
            method: metrics(expanded, f"{method}_score")
            for method in METHODS
        },
        "complete_comparisons": comparisons(expanded, 2026072930),
        "triggered_subset": {
            "count": len(triggered),
            "methods": {
                method: metrics(triggered, f"{method}_score")
                for method in METHODS
            },
            "comparisons": comparisons(triggered, 2026072940),
        },
        "switched_subset": {
            "count": len(switched),
            "methods": {
                method: metrics(switched, f"{method}_score")
                for method in METHODS
            },
            "comparisons": comparisons(switched, 2026072950),
        },
        "question_type_stratified": type_results,
        "deployment": {
            "trigger_count_original": int(protocol["trigger_count"]),
            "switch_count_original": int(protocol["switch_count"]),
            "Uniform8_visual_tokens": int(
                protocol["uniform_visual_tokens"]
            ),
            "MMR8_visual_tokens": int(protocol["mmr_visual_tokens"]),
            "trigger_A2_visual_tokens": int(
                protocol["trigger_a2_visual_tokens"]
            ),
            "FullJointMethod_average_answer_visual_tokens": float(
                protocol["full_policy_average_answer_visual_tokens"]
            ),
        },
        "hashes": {
            "candidates_sha256": sha256_file(args.candidates),
            "protocol_audit_sha256": sha256_file(args.protocol_audit),
            "reused_scores_sha256": sha256_file(reused_path),
            "pending_manifest_sha256": sha256_file(pending_path),
            "api_results_sha256": sha256_file(args.api_results),
            "expanded_scores_sha256": sha256_file(expanded_path),
        },
    }
    dump_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
