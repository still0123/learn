"""Metrics and preregistered conservative switching gate."""

from __future__ import annotations

from collections import defaultdict
import math
import random
from typing import Any, Iterable, Sequence


SENSITIVE_CATEGORIES = {"brand", "price_promo", "ocr_text"}


def binary_metrics(labels: Sequence[int], probabilities: Sequence[float], threshold: float = 0.5) -> dict[str, float]:
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("labels and probabilities must be non-empty and aligned")
    predictions = [int(value >= threshold) for value in probabilities]
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    tn = len(labels) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": (tp + tn) / len(labels),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auroc": auroc(labels, probabilities),
        "ece_10bin": expected_calibration_error(labels, probabilities, bins=10),
    }


def auroc(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return 0.5
    ordered = sorted(zip(probabilities, labels), key=lambda row: row[0])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def expected_calibration_error(labels: Sequence[int], probabilities: Sequence[float], bins: int = 10) -> float:
    total = len(labels)
    error = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        members = [
            row for row in zip(labels, probabilities)
            if lower <= row[1] < upper or (index == bins - 1 and row[1] == 1.0)
        ]
        if members:
            accuracy = sum(label for label, _ in members) / len(members)
            confidence = sum(probability for _, probability in members) / len(members)
            error += len(members) / total * abs(accuracy - confidence)
    return error


def _selection_rows(records: Sequence[dict[str, Any]], probabilities: Sequence[float], threshold: float):
    rows = []
    for record, probability in zip(records, probabilities):
        supervision = record.get("supervision") or {}
        initial = float(supervision["initial_score"])
        rescue = float(supervision["rescue_score"])
        switched = probability >= threshold
        rows.append({
            "question_id": record.get("question_id"),
            "category": record.get("category", "unknown"),
            "probability": float(probability),
            "switched": switched,
            "initial_score": initial,
            "rescue_score": rescue,
            "selected_score": rescue if switched else initial,
        })
    return rows


def selection_metrics(records: Sequence[dict[str, Any]], probabilities: Sequence[float], threshold: float) -> dict[str, Any]:
    rows = _selection_rows(records, probabilities, threshold)
    count = len(rows)
    switched = [row for row in rows if row["switched"]]
    beneficial = [row for row in switched if row["rescue_score"] > row["initial_score"]]
    harmful = [row for row in switched if row["rescue_score"] < row["initial_score"]]
    initial_mean = sum(row["initial_score"] for row in rows) / count
    selected_mean = sum(row["selected_score"] for row in rows) / count
    oracle_mean = sum(max(row["initial_score"], row["rescue_score"]) for row in rows) / count
    oracle_gain = oracle_mean - initial_mean
    category_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        category_rows[str(row["category"])].append(row)
    by_category = {}
    for category, members in sorted(category_rows.items()):
        before = sum(row["initial_score"] for row in members) / len(members)
        after = sum(row["selected_score"] for row in members) / len(members)
        by_category[category] = {"n": len(members), "initial_relaxed": before, "selected_relaxed": after, "delta": after - before}
    return {
        "n": count,
        "threshold": threshold,
        "switches": len(switched),
        "beneficial_switches": len(beneficial),
        "harmful_switches": len(harmful),
        "tie_switches": len(switched) - len(beneficial) - len(harmful),
        "switch_precision": len(beneficial) / len(switched) if switched else 1.0,
        "severe_1_to_0": sum(row["initial_score"] == 1.0 and row["selected_score"] == 0.0 for row in rows),
        "strict_initial": sum(row["initial_score"] == 1.0 for row in rows) / count,
        "strict_selected": sum(row["selected_score"] == 1.0 for row in rows) / count,
        "relaxed_initial": initial_mean,
        "relaxed_selected": selected_mean,
        "relaxed_delta": selected_mean - initial_mean,
        "oracle_relaxed": oracle_mean,
        "oracle_gain": oracle_gain,
        "oracle_recovery": (selected_mean - initial_mean) / oracle_gain if oracle_gain > 0 else 0.0,
        "by_category": by_category,
        "rows": rows,
    }


def paired_bootstrap_ci(rows: Sequence[dict[str, Any]], samples: int = 10000, seed: int = 42) -> list[float]:
    deltas = [row["selected_score"] - row["initial_score"] for row in rows]
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        means.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
    means.sort()
    return [means[int(0.025 * samples)], means[min(samples - 1, int(0.975 * samples))]]


def select_conservative_threshold(
    records: Sequence[dict[str, Any]],
    probabilities: Sequence[float],
    min_switch_precision: float = 0.70,
    bootstrap_samples: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    candidates = sorted({float(value) for value in probabilities}, reverse=True)
    candidates = [min(1.000001, max(candidates) + 1e-6), *candidates]
    summaries = [selection_metrics(records, probabilities, threshold) for threshold in candidates]
    eligible = [row for row in summaries if row["switches"] > 0 and row["switch_precision"] >= min_switch_precision]
    if not eligible:
        selected = summaries[0]
        reason = "no_threshold_meets_switch_precision"
    else:
        selected = max(eligible, key=lambda row: (row["relaxed_delta"], -row["severe_1_to_0"], row["threshold"]))
        reason = "max_relaxed_delta_subject_to_precision"
    ci = paired_bootstrap_ci(selected["rows"], samples=bootstrap_samples, seed=seed)
    selected = {**selected, "bootstrap_ci95": ci, "selection_reason": reason}
    selected["gate"] = stage_gate(selected, min_switch_precision)
    return selected


def stage_gate(selection: dict[str, Any], min_switch_precision: float = 0.70) -> dict[str, bool]:
    sensitive_regression = any(
        value["n"] >= 10 and value["delta"] < -0.02
        for category, value in selection["by_category"].items()
        if category in SENSITIVE_CATEGORIES
    )
    ci = selection.get("bootstrap_ci95") or [float("-inf"), float("inf")]
    gate = {
        "mean_positive": selection["relaxed_delta"] > 0.0,
        "bootstrap_lower_nonnegative": ci[0] >= 0.0,
        "strict_non_decreasing": selection["strict_selected"] >= selection["strict_initial"],
        "switch_precision_at_least_0_70": selection["switch_precision"] >= min_switch_precision,
        "oracle_recovery_at_least_half": selection["oracle_recovery"] >= 0.50,
        "no_broad_sensitive_category_regression": not sensitive_regression,
        "severe_regressions_controlled": selection["severe_1_to_0"] <= max(1, selection["beneficial_switches"] // 3),
    }
    gate["passed"] = all(gate.values())
    return gate
