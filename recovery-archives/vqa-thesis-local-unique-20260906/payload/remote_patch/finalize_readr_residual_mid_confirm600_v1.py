#!/usr/bin/env python3
"""Finalize Confirm-600 residual scores already collected by the judge."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from judge_readr_residual_mid_confirm600_v1 import (
    GATE,
    OLD,
    ROOT,
    clustered_ci,
    load,
    metrics,
    sha256_file,
    write_jsonl,
)


OUT = ROOT / "judge_deepseek_residual_mid_v1"


def pairwise(rows, selected_key, baseline_key, seed):
    selected = np.asarray([float(row[selected_key]) for row in rows])
    baseline = np.asarray([float(row[baseline_key]) for row in rows])
    delta = selected - baseline
    wrong_to_right = int(np.sum((baseline < 1.0) & (selected == 1.0)))
    right_to_wrong = int(np.sum((baseline == 1.0) & (selected < 1.0)))
    return {
        "rows": len(rows),
        "wins": int(np.sum(delta > 0)),
        "ties": int(np.sum(delta == 0)),
        "losses": int(np.sum(delta < 0)),
        "mean_relaxed_delta": float(np.mean(delta)),
        "mean_strict_delta": float(
            np.mean((selected == 1.0).astype(float) - (baseline == 1.0).astype(float))
        ),
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "correction_precision": (
            wrong_to_right / (wrong_to_right + right_to_wrong)
            if wrong_to_right + right_to_wrong
            else None
        ),
        "video_cluster_bootstrap_ci95": clustered_ci(
            rows, selected_key, baseline_key, 10000, seed
        ),
    }


def main() -> None:
    if not OUT.is_dir():
        raise RuntimeError(f"missing judge output: {OUT}")
    partial = load(OUT / "api_results_partial.jsonl")
    failures = load(OUT / "api_failures.jsonl") if (OUT / "api_failures.jsonl").exists() else []
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    switched_rows = [row for row in gate["rows_detail"] if row.get("gate_switched") is True]
    if len(partial) != 22 or failures or len(switched_rows) != 22:
        raise RuntimeError("incomplete or failed authorized score set")
    api_by_qid = {str(row["question_id"]): float(row["score"]) for row in partial}
    if len(api_by_qid) != 22 or set(api_by_qid) != {str(row["question_id"]) for row in switched_rows}:
        raise RuntimeError("API scores do not exactly match gate whitelist")

    old = {str(row["question_id"]): row for row in load(OLD)}
    if len(old) != 600:
        raise RuntimeError("old Confirm-600 score count mismatch")
    switched_ids = set(api_by_qid)
    expanded = []
    for qid, old_row in sorted(old.items()):
        mmr = float(old_row["MMR8_score"])
        adaptive = float(old_row["Adaptive12Gated_score"])
        expanded.append({
            "question_id": qid,
            "video_id": str(old_row["video_id"]),
            "question_type": str(old_row.get("question_type", "unknown")),
            "MMR8_score": mmr,
            "Adaptive12Gated_score": adaptive,
            "ResidualMid12Gated_score": api_by_qid[qid] if qid in switched_ids else mmr,
            "switched": qid in switched_ids,
        })
    write_jsonl(OUT / "api_results.jsonl", partial)
    write_jsonl(OUT / "api_failures.jsonl", [])
    write_jsonl(OUT / "expanded_scores.jsonl", expanded)

    comparisons = {
        "ResidualMid12Gated_vs_MMR8": pairwise(expanded, "ResidualMid12Gated_score", "MMR8_score", 2026073103),
        "ResidualMid12Gated_vs_Adaptive12Gated": pairwise(expanded, "ResidualMid12Gated_score", "Adaptive12Gated_score", 2026073104),
        "Adaptive12Gated_vs_MMR8": pairwise(expanded, "Adaptive12Gated_score", "MMR8_score", 2026073105),
    }
    type_results = {}
    for qtype in sorted({row["question_type"] for row in expanded}):
        subset = [row for row in expanded if row["question_type"] == qtype]
        type_results[qtype] = {
            "MMR8": metrics(subset, "MMR8_score"),
            "Adaptive12Gated": metrics(subset, "Adaptive12Gated_score"),
            "ResidualMid12Gated": metrics(subset, "ResidualMid12Gated_score"),
        }
    usage_totals = {
        key: sum(int((row.get("judge_usage") or {}).get(key) or 0) for row in partial)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary = {
        "schema_version": "readr_residual_mid_confirm600_judge_v1",
        "not_human_gold": True,
        "authorized_new_calls": 22,
        "actual_new_successful_calls": 22,
        "automatic_retries": 0,
        "one_shot_failures": 0,
        "historical_exact_reuse_count": 578,
        "generated_answer_change_count": 30,
        "gate_switch_count": 22,
        "judge_response_models": sorted({str(row.get("judge_response_model")) for row in partial}),
        "new_api_usage_totals": usage_totals,
        "confirm600": {
            "MMR8": metrics(expanded, "MMR8_score"),
            "Adaptive12Gated": metrics(expanded, "Adaptive12Gated_score"),
            "ResidualMid12Gated": metrics(expanded, "ResidualMid12Gated_score"),
        },
        "complete_comparisons": comparisons,
        "question_type_stratified": type_results,
        "protocol": {
            "reference_answers_read": True,
            "reference_answers_in_model_inputs": False,
            "candidate_mode": "answer_only",
            "gate_summary_sha256": sha256_file(GATE),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "JUDGE_COMPLETE").touch()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
