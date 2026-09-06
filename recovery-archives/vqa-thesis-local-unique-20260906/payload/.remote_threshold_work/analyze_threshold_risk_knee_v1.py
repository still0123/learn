#!/usr/bin/env python3
"""Select and audit a balanced support threshold from calibration data only."""

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
ACCURACY_THRESHOLD = 0.9602926671504974
COST_THRESHOLD = 0.9361833035945892
RISK_CEILING = 0.03


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


def write_json(path: Path, value: Any) -> None:
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


def evaluate_calibration(
    rows: list[dict[str, Any]],
    threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluated = []
    for row in rows:
        baseline = float(row["a0_score"])
        triggered = float(row["a0_support_probability"]) < threshold
        policy = float(row["a2_score"]) if triggered else baseline
        evaluated.append({
            "question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "baseline_score": baseline,
            "policy_score": policy,
            "triggered": triggered,
        })
    return metrics(evaluated, threshold), evaluated


def metrics(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    count = len(rows)
    triggered = sum(int(row["triggered"]) for row in rows)
    trigger_rate = triggered / count
    return {
        "threshold": threshold,
        "rows": count,
        "triggered": triggered,
        "trigger_rate": trigger_rate,
        "strict": sum(row["policy_score"] == 1 for row in rows) / count,
        "relaxed": sum(float(row["policy_score"]) for row in rows) / count,
        "baseline_strict": sum(row["baseline_score"] == 1 for row in rows) / count,
        "baseline_relaxed": sum(float(row["baseline_score"]) for row in rows) / count,
        "wins": sum(row["policy_score"] > row["baseline_score"] for row in rows),
        "ties": sum(row["policy_score"] == row["baseline_score"] for row in rows),
        "losses": sum(row["policy_score"] < row["baseline_score"] for row in rows),
        "wrong_to_right": sum(
            row["baseline_score"] == 0 and row["policy_score"] == 1
            for row in rows
        ),
        "right_to_wrong": sum(
            row["baseline_score"] == 1 and row["policy_score"] < 1
            for row in rows
        ),
        "right_to_wrong_rate_all": sum(
            row["baseline_score"] == 1 and row["policy_score"] < 1
            for row in rows
        ) / count,
        "average_selected_answer_visual_tokens": (
            (1 - trigger_rate) * A0_TOKENS + trigger_rate * A2_TOKENS
        ),
        "average_executed_answer_visual_tokens": (
            A0_TOKENS + trigger_rate * A2_TOKENS
        ),
    }


def choose_knee(curve: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_relaxed = min(
        curve,
        key=lambda row: int(row["triggered"]),
    )["relaxed"]
    maximum_relaxed = max(float(row["relaxed"]) for row in curve)
    gain_span = maximum_relaxed - float(baseline_relaxed)
    if gain_span <= 0:
        raise RuntimeError("calibration curve has no positive relaxed gain")
    for row in curve:
        normalized_gain = (
            float(row["relaxed"]) - float(baseline_relaxed)
        ) / gain_span
        row["normalized_relaxed_gain"] = normalized_gain
        row["knee_score"] = normalized_gain - float(row["trigger_rate"])
    return max(
        curve,
        key=lambda row: (
            float(row["knee_score"]),
            float(row["relaxed"]),
            float(row["strict"]),
            -int(row["right_to_wrong"]),
            -int(row["triggered"]),
        ),
    )


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * quantile))
    return ordered[index]


def clustered_risk_bootstrap(
    rows: list[dict[str, Any]],
    samples: int,
    seed: int,
) -> dict[str, Any]:
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    videos = sorted(by_video)
    rng = random.Random(seed)
    strict_deltas = []
    relaxed_deltas = []
    harm_rates = []
    trigger_rates = []
    for _ in range(samples):
        sampled = []
        for video in rng.choices(videos, k=len(videos)):
            sampled.extend(by_video[video])
        count = len(sampled)
        strict_deltas.append(
            sum(
                int(row["policy_score"] == 1) - int(row["baseline_score"] == 1)
                for row in sampled
            ) / count
        )
        relaxed_deltas.append(
            sum(
                float(row["policy_score"]) - float(row["baseline_score"])
                for row in sampled
            ) / count
        )
        harm_rates.append(
            sum(
                row["baseline_score"] == 1 and row["policy_score"] < 1
                for row in sampled
            ) / count
        )
        trigger_rates.append(
            sum(int(row["triggered"]) for row in sampled) / count
        )
    return {
        "samples": samples,
        "seed": seed,
        "cluster_count": len(videos),
        "strict_delta_ci95": [
            percentile(strict_deltas, 0.025),
            percentile(strict_deltas, 0.975),
        ],
        "relaxed_delta_ci95": [
            percentile(relaxed_deltas, 0.025),
            percentile(relaxed_deltas, 0.975),
        ],
        "right_to_wrong_rate_all_ci95": [
            percentile(harm_rates, 0.025),
            percentile(harm_rates, 0.975),
        ],
        "trigger_rate_ci95": [
            percentile(trigger_rates, 0.025),
            percentile(trigger_rates, 0.975),
        ],
    }


def evaluate_full(
    score_rows: list[dict[str, Any]],
    support_by_id: dict[str, float],
    threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluated = []
    for row in score_rows:
        question_id = str(row["question_id"])
        support = support_by_id[question_id]
        triggered = support < threshold
        if triggered and support >= ACCURACY_THRESHOLD:
            raise RuntimeError("selected threshold requires unavailable A2 output")
        baseline = float(row["MMR8_score"])
        policy = (
            float(row["ThresholdAdaptiveA2_score"])
            if triggered
            else baseline
        )
        evaluated.append({
            "question_id": question_id,
            "video_id": str(row["video_id"]),
            "baseline_score": baseline,
            "policy_score": policy,
            "triggered": triggered,
        })
    return metrics(evaluated, threshold), evaluated


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")
    calibration = load_jsonl(args.calibration)
    full_scores = load_jsonl(args.full_scores)
    full_support_rows = load_jsonl(args.full_support)
    if len(calibration) != 500 or len(full_scores) != 5319:
        raise RuntimeError("unexpected calibration or full score count")
    support_by_id = {
        str(row["source_question_id"]): float(row["support_probability"])
        for row in full_support_rows
    }
    if not {str(row["question_id"]) for row in full_scores}.issubset(support_by_id):
        raise RuntimeError("full scores and support probabilities do not align")

    curve = []
    evaluated_by_threshold = {}
    for threshold in candidate_thresholds(calibration):
        row, evaluated = evaluate_calibration(calibration, threshold)
        curve.append(row)
        evaluated_by_threshold[threshold] = evaluated
    knee = choose_knee(curve)
    knee_threshold = float(knee["threshold"])
    knee_bootstrap = clustered_risk_bootstrap(
        evaluated_by_threshold[knee_threshold],
        args.bootstrap_samples,
        2026072931,
    )
    risk_audit = {
        "exploratory_not_preregistered": True,
        "risk_ceiling_right_to_wrong_rate_all": RISK_CEILING,
        "relaxed_gain_lcb_positive": (
            knee_bootstrap["relaxed_delta_ci95"][0] > 0
        ),
        "strict_gain_lcb_positive": (
            knee_bootstrap["strict_delta_ci95"][0] > 0
        ),
        "harm_ucb_within_ceiling": (
            knee_bootstrap["right_to_wrong_rate_all_ci95"][1] <= RISK_CEILING
        ),
    }
    risk_audit["passed"] = all(
        value
        for key, value in risk_audit.items()
        if key not in {
            "exploratory_not_preregistered",
            "risk_ceiling_right_to_wrong_rate_all",
        }
    )

    full_knee, full_knee_rows = evaluate_full(
        full_scores,
        support_by_id,
        knee_threshold,
    )
    full_knee_bootstrap = clustered_risk_bootstrap(
        full_knee_rows,
        args.bootstrap_samples,
        2026072932,
    )
    full_comparisons = {}
    for name, threshold in {
        "accuracy_optimum": ACCURACY_THRESHOLD,
        "cost_aware_0.5pp": COST_THRESHOLD,
    }.items():
        peer_metrics, peer_rows = evaluate_full(
            full_scores,
            support_by_id,
            threshold,
        )
        peer_by_id = {row["question_id"]: row for row in peer_rows}
        delta_rows = [
            {
                **row,
                "baseline_score": peer_by_id[row["question_id"]]["policy_score"],
            }
            for row in full_knee_rows
        ]
        full_comparisons[name] = {
            "peer_metrics": peer_metrics,
            "knee_minus_peer_bootstrap": clustered_risk_bootstrap(
                delta_rows,
                args.bootstrap_samples,
                2026072933 + len(full_comparisons),
            ),
        }

    middle_budget = [
        row for row in curve if 0.40 <= float(row["trigger_rate"]) <= 0.60
    ]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output_dir / "calibration_curve_with_knee_score.jsonl", curve)
    write_jsonl(args.output_dir / "middle_budget_candidates_40_60.jsonl", middle_budget)
    summary = {
        "schema_version": "adsqa_threshold_risk_knee_analysis_v1",
        "selection_data": "OOF-500 calibration only",
        "selection_rule": (
            "maximize normalized Relaxed gain minus trigger rate; tie-break by "
            "Relaxed, Strict, fewer right-to-wrong, then fewer triggers"
        ),
        "full_labels_used_for_threshold_selection": False,
        "full_analysis_role": "posthoc_sensitivity_only",
        "selected_knee": knee,
        "calibration_video_cluster_bootstrap": knee_bootstrap,
        "calibration_risk_audit": risk_audit,
        "full5319_posthoc": {
            "metrics": full_knee,
            "vs_mmr8_bootstrap": full_knee_bootstrap,
            "comparisons": full_comparisons,
        },
        "token_accounting": {
            "a0_visual_tokens": A0_TOKENS,
            "a2_visual_tokens": A2_TOKENS,
            "verifier_tokens_excluded": True,
        },
        "input_sha256": {
            "calibration": sha256_file(args.calibration),
            "full_scores": sha256_file(args.full_scores),
            "full_support": sha256_file(args.full_support),
        },
    }
    write_json(args.output_dir / "summary.json", summary)
    write_json(args.output_dir / "manifest.json", {
        "schema_version": "adsqa_threshold_risk_knee_manifest_v1",
        "api_called": False,
        "gpu_inference_run": False,
        "historical_results_modified": False,
        "output_files": [
            "calibration_curve_with_knee_score.jsonl",
            "middle_budget_candidates_40_60.jsonl",
            "summary.json",
        ],
    })
    checksums = []
    for name in [
        "calibration_curve_with_knee_score.jsonl",
        "middle_budget_candidates_40_60.jsonl",
        "summary.json",
        "manifest.json",
    ]:
        checksums.append(f"{sha256_file(args.output_dir / name)}  {name}")
    (args.output_dir / "SHA256SUMS").write_text(
        "\n".join(checksums) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
