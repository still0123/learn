#!/usr/bin/env python3
"""Compare per-question scores from two AdsQA judge result files."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--left-name", default="left")
    parser.add_argument("--right-name", default="right")
    parser.add_argument("--method", action="append", required=True)
    parser.add_argument("--pair", nargs=2, metavar=("FIRST", "SECOND"))
    parser.add_argument("--min-pooled-exact-rate", type=float)
    parser.add_argument("--max-pooled-mad", type=float)
    parser.add_argument("--require-pair-mean-sign-match", action="store_true")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_scores(path: str | Path) -> dict[tuple[str, str], float]:
    scores = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        score = row.get("score")
        if score is None:
            continue
        key = (str(row["method"]), str(row["question_id"]))
        if key in scores:
            raise ValueError(f"duplicate judge score: {key}")
        scores[key] = float(score)
    return scores


def sign(value: float) -> int:
    return (value > 0.0) - (value < 0.0)


def score_matrix(pairs: list[tuple[float, float]]) -> dict[str, int]:
    counts = Counter(f"{left:g}->{right:g}" for left, right in pairs)
    return dict(sorted(counts.items()))


def method_agreement(
    method: str,
    left: dict[tuple[str, str], float],
    right: dict[tuple[str, str], float],
) -> dict[str, Any]:
    question_ids = sorted(
        question_id for name, question_id in left
        if name == method and (name, question_id) in right
    )
    pairs = [(left[(method, qid)], right[(method, qid)]) for qid in question_ids]
    if not pairs:
        raise ValueError(f"no shared scores for method {method}")
    return {
        "shared": len(pairs),
        "exact": sum(a == b for a, b in pairs),
        "exact_rate": sum(a == b for a, b in pairs) / len(pairs),
        "mean_absolute_difference": sum(abs(a - b) for a, b in pairs) / len(pairs),
        "mean_right_minus_left": sum(b - a for a, b in pairs) / len(pairs),
        "score_matrix_left_to_right": score_matrix(pairs),
    }


def pairwise_agreement(
    first: str,
    second: str,
    left: dict[tuple[str, str], float],
    right: dict[tuple[str, str], float],
) -> dict[str, Any]:
    question_ids = sorted({qid for name, qid in left if name == first})
    shared = [
        qid for qid in question_ids
        if all((method, qid) in scores for method in (first, second) for scores in (left, right))
    ]
    deltas = [
        (left[(second, qid)] - left[(first, qid)], right[(second, qid)] - right[(first, qid)])
        for qid in shared
    ]
    if not deltas:
        raise ValueError(f"no shared pairwise scores for {first} and {second}")
    both_non_tie = [(a, b) for a, b in deltas if a != 0.0 and b != 0.0]
    return {
        "comparison": f"{second}_minus_{first}",
        "shared": len(deltas),
        "mean_delta_left": sum(a for a, _ in deltas) / len(deltas),
        "mean_delta_right": sum(b for _, b in deltas) / len(deltas),
        "sign_or_tie_agreement": sum(sign(a) == sign(b) for a, b in deltas),
        "both_non_tie": len(both_non_tie),
        "same_direction_when_both_non_tie": sum(sign(a) == sign(b) for a, b in both_non_tie),
        "delta_matrix_left_to_right": score_matrix(deltas),
    }


def calibration_gate(
    payload: dict[str, Any],
    min_pooled_exact_rate: float | None,
    max_pooled_mad: float | None,
    require_pair_mean_sign_match: bool,
) -> dict[str, Any] | None:
    checks: dict[str, bool] = {}
    if min_pooled_exact_rate is not None:
        checks["pooled_exact_rate"] = (
            payload["pooled"]["exact_rate"] >= min_pooled_exact_rate
        )
    if max_pooled_mad is not None:
        checks["pooled_mean_absolute_difference"] = (
            payload["pooled"]["weighted_mean_absolute_difference"] <= max_pooled_mad
        )
    if require_pair_mean_sign_match:
        ranking = payload.get("pairwise_method_ranking")
        if ranking is None:
            raise ValueError("--require-pair-mean-sign-match requires --pair")
        checks["pair_mean_sign_match"] = (
            sign(ranking["mean_delta_left"]) == sign(ranking["mean_delta_right"])
        )
    if not checks:
        return None
    return {
        "thresholds": {
            "min_pooled_exact_rate": min_pooled_exact_rate,
            "max_pooled_mean_absolute_difference": max_pooled_mad,
            "require_pair_mean_sign_match": require_pair_mean_sign_match,
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    args = parse_args()
    left = load_scores(args.left)
    right = load_scores(args.right)
    methods = {method: method_agreement(method, left, right) for method in args.method}
    pooled_shared = sum(item["shared"] for item in methods.values())
    payload: dict[str, Any] = {
        "left": {"name": args.left_name, "path": str(Path(args.left).resolve())},
        "right": {"name": args.right_name, "path": str(Path(args.right).resolve())},
        "methods": methods,
        "pooled": {
            "shared": pooled_shared,
            "exact": sum(item["exact"] for item in methods.values()),
            "exact_rate": sum(item["exact"] for item in methods.values()) / pooled_shared,
            "weighted_mean_absolute_difference": sum(
                item["mean_absolute_difference"] * item["shared"] for item in methods.values()
            ) / pooled_shared,
            "weighted_mean_right_minus_left": sum(
                item["mean_right_minus_left"] * item["shared"] for item in methods.values()
            ) / pooled_shared,
        },
    }
    if args.pair:
        payload["pairwise_method_ranking"] = pairwise_agreement(
            args.pair[0], args.pair[1], left, right
        )
    gate = calibration_gate(
        payload,
        args.min_pooled_exact_rate,
        args.max_pooled_mad,
        args.require_pair_mean_sign_match,
    )
    if gate is not None:
        payload["calibration_gate"] = gate
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
