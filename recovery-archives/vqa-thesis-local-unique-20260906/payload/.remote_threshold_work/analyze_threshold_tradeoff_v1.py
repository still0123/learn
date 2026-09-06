#!/usr/bin/env python3
"""Compute calibration-only accuracy/cost thresholds and posthoc full-set sensitivity."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


A0_TOKENS = 1024
A2_TOKENS = 3104
ORIGINAL_THRESHOLD = 0.9602926671504974


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--full-scores", type=Path, required=True)
    parser.add_argument("--full-support", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_thresholds(rows: list[dict[str, Any]]) -> list[float]:
    values = sorted({float(row["a0_support_probability"]) for row in rows})
    return (
        [values[0] - 1e-9]
        + [(left + right) / 2 for left, right in zip(values, values[1:])]
        + [values[-1] + 1e-9]
    )


def evaluate_calibration(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    policy_scores = []
    wins = ties = losses = wrong_to_right = right_to_wrong = triggered = 0
    for row in rows:
        baseline = float(row["a0_score"])
        use_a2 = float(row["a0_support_probability"]) < threshold
        policy = float(row["a2_score"]) if use_a2 else baseline
        policy_scores.append(policy)
        triggered += int(use_a2)
        wins += int(policy > baseline)
        ties += int(policy == baseline)
        losses += int(policy < baseline)
        wrong_to_right += int(baseline == 0 and policy == 1)
        right_to_wrong += int(baseline == 1 and policy < 1)
    trigger_rate = triggered / len(rows)
    return {
        "threshold": threshold,
        "rows": len(rows),
        "triggered": triggered,
        "trigger_rate": trigger_rate,
        "strict": sum(score == 1 for score in policy_scores) / len(rows),
        "relaxed": sum(policy_scores) / len(rows),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "average_selected_answer_visual_tokens": (
            (1 - trigger_rate) * A0_TOKENS + trigger_rate * A2_TOKENS
        ),
        "average_executed_answer_visual_tokens": (
            A0_TOKENS + trigger_rate * A2_TOKENS
        ),
    }


def choose_accuracy_optimum(curve: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        curve,
        key=lambda row: (
            float(row["relaxed"]),
            float(row["strict"]),
            -int(row["right_to_wrong"]),
            -int(row["triggered"]),
        ),
    )


def choose_tolerance_optimum(
    curve: list[dict[str, Any]],
    tolerance: float,
) -> dict[str, Any]:
    max_relaxed = max(float(row["relaxed"]) for row in curve)
    max_strict = max(float(row["strict"]) for row in curve)
    eligible = [
        row
        for row in curve
        if float(row["relaxed"]) >= max_relaxed - tolerance
        and float(row["strict"]) >= max_strict - tolerance
    ]
    return min(
        eligible,
        key=lambda row: (
            int(row["triggered"]),
            -float(row["relaxed"]),
            -float(row["strict"]),
            int(row["right_to_wrong"]),
        ),
    )


def pareto_frontier(curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frontier = []
    for candidate in curve:
        dominated = any(
            int(other["triggered"]) <= int(candidate["triggered"])
            and float(other["strict"]) >= float(candidate["strict"])
            and float(other["relaxed"]) >= float(candidate["relaxed"])
            and (
                int(other["triggered"]) < int(candidate["triggered"])
                or float(other["strict"]) > float(candidate["strict"])
                or float(other["relaxed"]) > float(candidate["relaxed"])
            )
            for other in curve
        )
        if not dominated:
            frontier.append(candidate)
    return sorted(frontier, key=lambda row: int(row["triggered"]))


def evaluate_full(
    score_rows: list[dict[str, Any]],
    support_by_id: dict[str, float],
    threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluated = []
    for row in score_rows:
        qid = str(row["question_id"])
        support = support_by_id[qid]
        triggered = support < threshold
        if triggered and support >= ORIGINAL_THRESHOLD:
            raise RuntimeError("candidate threshold requires unavailable A2 score")
        baseline = float(row["MMR8_score"])
        policy = (
            float(row["ThresholdAdaptiveA2_score"])
            if triggered
            else baseline
        )
        evaluated.append({
            "question_id": qid,
            "video_id": str(row["video_id"]),
            "support_probability": support,
            "baseline_score": baseline,
            "policy_score": policy,
            "triggered": triggered,
        })
    triggered_count = sum(int(row["triggered"]) for row in evaluated)
    trigger_rate = triggered_count / len(evaluated)
    wins = sum(row["policy_score"] > row["baseline_score"] for row in evaluated)
    ties = sum(row["policy_score"] == row["baseline_score"] for row in evaluated)
    losses = sum(row["policy_score"] < row["baseline_score"] for row in evaluated)
    wrong_to_right = sum(
        row["baseline_score"] == 0 and row["policy_score"] == 1
        for row in evaluated
    )
    right_to_wrong = sum(
        row["baseline_score"] == 1 and row["policy_score"] < 1
        for row in evaluated
    )
    return {
        "threshold": threshold,
        "rows": len(evaluated),
        "triggered": triggered_count,
        "trigger_rate": trigger_rate,
        "strict": sum(row["policy_score"] == 1 for row in evaluated) / len(evaluated),
        "relaxed": sum(row["policy_score"] for row in evaluated) / len(evaluated),
        "baseline_strict": sum(row["baseline_score"] == 1 for row in evaluated) / len(evaluated),
        "baseline_relaxed": sum(row["baseline_score"] for row in evaluated) / len(evaluated),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "average_selected_answer_visual_tokens": (
            (1 - trigger_rate) * A0_TOKENS + trigger_rate * A2_TOKENS
        ),
        "average_executed_answer_visual_tokens": (
            A0_TOKENS + trigger_rate * A2_TOKENS
        ),
    }, evaluated


def clustered_bootstrap(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    samples: int,
    seed: int,
) -> dict[str, Any]:
    right_by_id = {row["question_id"]: row for row in right}
    by_video: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in left:
        peer = right_by_id[row["question_id"]]
        by_video[row["video_id"]].append(
            (float(row["policy_score"]), float(peer["policy_score"]))
        )
    videos = sorted(by_video)
    rng = random.Random(seed)
    relaxed_deltas = []
    strict_deltas = []
    for _ in range(samples):
        relaxed_sum = strict_sum = count = 0
        for video in rng.choices(videos, k=len(videos)):
            for left_score, right_score in by_video[video]:
                relaxed_sum += left_score - right_score
                strict_sum += int(left_score == 1) - int(right_score == 1)
                count += 1
        relaxed_deltas.append(relaxed_sum / count)
        strict_deltas.append(strict_sum / count)
    relaxed_deltas.sort()
    strict_deltas.sort()
    low = int(samples * 0.025)
    high = min(samples - 1, int(samples * 0.975))
    return {
        "samples": samples,
        "seed": seed,
        "cluster_count": len(videos),
        "relaxed_delta_ci95": [relaxed_deltas[low], relaxed_deltas[high]],
        "strict_delta_ci95": [strict_deltas[low], strict_deltas[high]],
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")
    calibration = load_jsonl(args.calibration)
    full_scores = load_jsonl(args.full_scores)
    full_support_rows = load_jsonl(args.full_support)
    if len(calibration) != 500 or len(full_scores) != 5319 or len(full_support_rows) != 5320:
        raise RuntimeError("unexpected calibration or full-set size")
    support_by_id = {
        str(row["source_question_id"]): float(row["support_probability"])
        for row in full_support_rows
    }
    if not {str(row["question_id"]) for row in full_scores}.issubset(support_by_id):
        raise RuntimeError("full scores and support probabilities do not align")

    curve = [
        evaluate_calibration(calibration, threshold)
        for threshold in candidate_thresholds(calibration)
    ]
    accuracy = choose_accuracy_optimum(curve)
    cost_half = choose_tolerance_optimum(curve, 0.005)
    cost_one = choose_tolerance_optimum(curve, 0.010)
    max_strict = max(
        curve,
        key=lambda row: (
            float(row["strict"]),
            float(row["relaxed"]),
            -int(row["triggered"]),
        ),
    )
    selected = {
        "accuracy_optimum": accuracy,
        "cost_aware_within_0.5pp": cost_half,
        "cost_aware_within_1.0pp": cost_one,
        "strict_optimum": max_strict,
    }

    full_metrics = {}
    full_rows = {}
    for name, calibration_metrics in selected.items():
        threshold = float(calibration_metrics["threshold"])
        if threshold > ORIGINAL_THRESHOLD:
            continue
        full_metrics[name], full_rows[name] = evaluate_full(
            full_scores,
            support_by_id,
            threshold,
        )
    for name, rows in full_rows.items():
        baseline_rows = [
            {**row, "policy_score": row["baseline_score"]}
            for row in rows
        ]
        full_metrics[name]["vs_mmr8_bootstrap"] = clustered_bootstrap(
            rows,
            baseline_rows,
            args.bootstrap_samples,
            2026072911 + len(full_metrics[name]),
        )
    if "accuracy_optimum" in full_rows and "cost_aware_within_0.5pp" in full_rows:
        cost_vs_accuracy = clustered_bootstrap(
            full_rows["cost_aware_within_0.5pp"],
            full_rows["accuracy_optimum"],
            args.bootstrap_samples,
            2026072920,
        )
    else:
        cost_vs_accuracy = None

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output_dir / "calibration_threshold_curve.jsonl", curve)
    write_jsonl(args.output_dir / "calibration_pareto_frontier.jsonl", pareto_frontier(curve))
    summary = {
        "schema_version": "adsqa_threshold_accuracy_cost_analysis_v1",
        "selection_data": "OOF-500 calibration only",
        "full_labels_used_for_threshold_selection": False,
        "full_analysis_role": "posthoc_sensitivity_only",
        "trigger_rule": "A0 support_probability < threshold",
        "token_accounting": {
            "a0_visual_tokens": A0_TOKENS,
            "a2_visual_tokens": A2_TOKENS,
            "selected_answer_average": "(1-trigger_rate)*A0 + trigger_rate*A2",
            "executed_answer_average": "A0 + trigger_rate*A2",
            "verifier_tokens_excluded": True,
        },
        "calibration_maxima": {
            "strict": max(float(row["strict"]) for row in curve),
            "relaxed": max(float(row["relaxed"]) for row in curve),
        },
        "selected_thresholds": selected,
        "full5319_posthoc_sensitivity": full_metrics,
        "full_cost_aware_0.5pp_vs_accuracy_optimum_bootstrap": cost_vs_accuracy,
        "input_sha256": {
            "calibration": sha256_file(args.calibration),
            "full_scores": sha256_file(args.full_scores),
            "full_support": sha256_file(args.full_support),
        },
    }
    dump_json(args.output_dir / "summary.json", summary)
    dump_json(args.output_dir / "manifest.json", {
        "schema_version": "adsqa_threshold_accuracy_cost_manifest_v1",
        "api_called": False,
        "gpu_inference_run": False,
        "output_files": [
            "calibration_threshold_curve.jsonl",
            "calibration_pareto_frontier.jsonl",
            "summary.json",
        ],
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
