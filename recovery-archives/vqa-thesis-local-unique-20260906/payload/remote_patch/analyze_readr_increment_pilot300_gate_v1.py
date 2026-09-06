#!/usr/bin/env python3
"""Calibrate a selective ReAd-R evidence gate on Pilot-300 without API calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from judge_readr_increment_pilot300_v1 import metrics, pairwise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def make_rows(
    scored: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    a0_scores: list[dict[str, Any]],
    a2_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_candidate = {str(row["question_id"]): row for row in candidates}
    a0_by_id = {str(row["source_question_id"]): row for row in a0_scores}
    a2_by_id = {str(row["source_question_id"]): row for row in a2_scores}
    if not (len(scored) == len(by_candidate) == len(a0_by_id) == len(a2_by_id) == 300):
        raise RuntimeError("Pilot score pools are incomplete")
    rows = []
    for score in scored:
        qid = str(score["question_id"])
        candidate = by_candidate[qid]
        if score["pilot_partition"] != candidate["pilot_partition"]:
            raise RuntimeError(f"partition mismatch: {qid}")
        rows.append(
            {
                **score,
                "a0_support": float(a0_by_id[qid]["support_probability"]),
                "a2_support": float(a2_by_id[qid]["support_probability"]),
                "a2_changes_answer": (
                    candidate["candidate_sha256"]["MMR8"]
                    != candidate["candidate_sha256"]["Adaptive12"]
                ),
            }
        )
    return rows


def gated_rows(
    source: list[dict[str, Any]], tau: float, margin: float
) -> list[dict[str, Any]]:
    rows = []
    for row in source:
        review = row["a0_support"] < tau
        switch = bool(
            review
            and row["a2_changes_answer"]
            and row["a2_support"] >= row["a0_support"] + margin
        )
        rows.append(
            {
                **row,
                "review_triggered": review,
                "gate_switched": switch,
                "GatedAdaptive_score": (
                    row["Adaptive12_score"] if switch else row["MMR8_score"]
                ),
            }
        )
    return rows


def gate_summary(rows: list[dict[str, Any]], bootstrap_seed: int) -> dict[str, Any]:
    comparison = pairwise(
        rows,
        "GatedAdaptive_score",
        "MMR8_score",
        bootstrap_samples=10000,
        seed=bootstrap_seed,
    )
    review_count = sum(bool(row["review_triggered"]) for row in rows)
    switch_count = sum(bool(row["gate_switched"]) for row in rows)
    return {
        "metrics": metrics(rows, "GatedAdaptive_score"),
        "vs_mmr8": comparison,
        "review_trigger_count": review_count,
        "review_trigger_rate": review_count / len(rows),
        "switch_count": switch_count,
        "switch_rate": switch_count / len(rows),
        "average_answer_visual_tokens": 1296.0 + 2696.0 * review_count / len(rows),
    }


def grid_selection(calibration: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    supports = np.asarray([row["a0_support"] for row in calibration], dtype=float)
    # The grid is fixed before reading Confirm200: 11 empirical calibration quantiles
    # and six support margins. Ties prefer lower cost, then stronger margin.
    tau_values = sorted({float(np.quantile(supports, q)) for q in np.linspace(0.1, 1.0, 10)} | {1.0})
    margin_values = [0.0, 0.02, 0.05, 0.08, 0.10, 0.15]
    grid = []
    for tau in tau_values:
        for margin in margin_values:
            result = gate_summary(gated_rows(calibration, tau, margin), 2026073001)
            comp = result["vs_mmr8"]
            grid.append(
                {
                    "tau": tau,
                    "margin": margin,
                    "relaxed_delta": comp["mean_relaxed_delta"],
                    "strict_delta": comp["mean_strict_delta"],
                    "wrong_to_right": comp["wrong_to_right"],
                    "right_to_wrong": comp["right_to_wrong"],
                    "review_trigger_rate": result["review_trigger_rate"],
                    "switch_rate": result["switch_rate"],
                    "correction_precision": comp["strict_correction_precision"],
                }
            )
    eligible = [
        row for row in grid
        if row["wrong_to_right"] >= row["right_to_wrong"]
    ]
    if not eligible:
        eligible = grid
    selected = max(
        eligible,
        key=lambda row: (
            row["relaxed_delta"],
            row["strict_delta"],
            -row["review_trigger_rate"],
            row["margin"],
        ),
    )
    return selected, grid


def main() -> None:
    args = parse_args()
    root = args.run_root.resolve()
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"refusing to overwrite nonempty output: {out}")
    scored_path = root / "judge_deepseek_legacy_answeronly_v1/results_v1/expanded_four_method_scores.jsonl"
    candidate_path = root / "judge_deepseek_legacy_answeronly_v1/materialized_v1/candidates_answer_free.jsonl"
    a0_path = root / "mmr8_verifier_merged/scores_all.jsonl"
    a2_path = root / "adaptive12_verifier_merged/scores_all.jsonl"
    rows = make_rows(
        load_jsonl(scored_path),
        load_jsonl(candidate_path),
        load_jsonl(a0_path),
        load_jsonl(a2_path),
    )
    calibration = [row for row in rows if row["pilot_partition"] == "calibration100"]
    confirm = [row for row in rows if row["pilot_partition"] == "confirm200"]
    if len(calibration) != 100 or len(confirm) != 200:
        raise RuntimeError("Pilot partitions are incomplete")
    selected, grid = grid_selection(calibration)
    tau, margin = float(selected["tau"]), float(selected["margin"])
    calibration_result = gate_summary(gated_rows(calibration, tau, margin), 2026073002)
    confirm_result = gate_summary(gated_rows(confirm, tau, margin), 2026073003)
    raw_results = {
        partition: {
            method: metrics(subset, f"{method}_score")
            for method in ("Uniform8", "MMR8", "Adaptive12", "ExtraGlobal12")
        }
        for partition, subset in (("calibration100", calibration), ("confirm200", confirm))
    }
    output = {
        "schema_version": "readr_increment_pilot300_gate_analysis_v1",
        "not_human_gold": True,
        "selection_protocol": {
            "calibration_partition": "calibration100",
            "confirmation_partition": "confirm200",
            "confirmation_used_for_selection": False,
            "gate_rule": "review if a0_support < tau; replace only if candidate changes answer and a2_support >= a0_support + margin",
            "tau_grid": "10 fixed empirical calibration deciles plus 1.0",
            "margin_grid": [0.0, 0.02, 0.05, 0.08, 0.10, 0.15],
            "selection_objective": "maximize calibration relaxed delta vs MMR8 subject to wrong_to_right >= right_to_wrong; tie-break strict delta, lower review rate, then larger margin",
        },
        "selected_threshold": selected,
        "calibration100": calibration_result,
        "confirm200": confirm_result,
        "raw_arm_metrics": raw_results,
        "grid": grid,
        "input_hashes": {
            "scored": sha256_file(scored_path),
            "candidates": sha256_file(candidate_path),
            "a0_support": sha256_file(a0_path),
            "a2_support": sha256_file(a2_path),
        },
    }
    dump_json(out / "summary.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
