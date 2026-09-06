"""Conservative calibration and held-out gates for adaptive temporal routing."""

from __future__ import annotations

from collections import defaultdict
import random
from typing import Any, Sequence


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
    return {"accuracy": (tp + tn) / len(labels), "precision": precision, "recall": recall, "f1": f1}


def _rows(records: Sequence[dict[str, Any]], probabilities: Sequence[float], threshold: float):
    rows = []
    for record, probability in zip(records, probabilities):
        supervision = record["supervision"]
        raw = float(supervision["raw_score"])
        mmr = float(supervision["mmr_score"])
        switched = float(probability) >= threshold
        rows.append({
            "question_id": record["question_id"],
            "primary_type": record["primary_type"],
            "probability": float(probability),
            "switched": switched,
            "raw_score": raw,
            "mmr_score": mmr,
            "selected_score": mmr if switched else raw,
        })
    return rows


def bootstrap_ci(rows: Sequence[dict[str, Any]], samples: int = 10000, seed: int = 42) -> list[float]:
    deltas = [row["selected_score"] - row["raw_score"] for row in rows]
    rng = random.Random(seed)
    means = [
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(samples)
    ]
    means.sort()
    return [means[int(0.025 * samples)], means[min(samples - 1, int(0.975 * samples))]]


def selection_metrics(
    records: Sequence[dict[str, Any]],
    probabilities: Sequence[float],
    threshold: float,
    *,
    bootstrap_samples: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    rows = _rows(records, probabilities, threshold)
    switched = [row for row in rows if row["switched"]]
    beneficial = [row for row in switched if row["mmr_score"] > row["raw_score"]]
    harmful = [row for row in switched if row["mmr_score"] < row["raw_score"]]
    raw_mean = sum(row["raw_score"] for row in rows) / len(rows)
    selected_mean = sum(row["selected_score"] for row in rows) / len(rows)
    oracle_mean = sum(max(row["raw_score"], row["mmr_score"]) for row in rows) / len(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["primary_type"]].append(row)
    by_type = {}
    for primary_type, members in sorted(grouped.items()):
        before = sum(row["raw_score"] for row in members) / len(members)
        after = sum(row["selected_score"] for row in members) / len(members)
        by_type[primary_type] = {"n": len(members), "raw_relaxed": before, "selected_relaxed": after, "delta": after - before}
    report = {
        "n": len(rows), "threshold": float(threshold), "switches": len(switched),
        "beneficial_switches": len(beneficial), "harmful_switches": len(harmful),
        "tie_switches": len(switched) - len(beneficial) - len(harmful),
        "switch_precision": len(beneficial) / len(switched) if switched else 1.0,
        "severe_1_to_0": sum(row["raw_score"] == 1.0 and row["selected_score"] == 0.0 for row in rows),
        "strict_raw": sum(row["raw_score"] == 1.0 for row in rows) / len(rows),
        "strict_selected": sum(row["selected_score"] == 1.0 for row in rows) / len(rows),
        "relaxed_raw": raw_mean, "relaxed_selected": selected_mean,
        "relaxed_delta": selected_mean - raw_mean,
        "oracle_relaxed": oracle_mean, "oracle_gain": oracle_mean - raw_mean,
        "by_primary_type": by_type, "rows": rows,
    }
    report["bootstrap_ci95"] = bootstrap_ci(rows, samples=bootstrap_samples, seed=seed)
    return report


def choose_calibration_threshold(
    records: Sequence[dict[str, Any]],
    probabilities: Sequence[float],
    min_switch_precision: float = 0.70,
) -> dict[str, Any]:
    thresholds = [min(1.000001, max(probabilities) + 1e-6), *sorted(set(float(x) for x in probabilities), reverse=True)]
    reports = [selection_metrics(records, probabilities, value, bootstrap_samples=1000) for value in thresholds]
    eligible = [
        row for row in reports
        if row["switches"] > 0
        and row["relaxed_delta"] > 0.0
        and row["strict_selected"] >= row["strict_raw"]
        and row["switch_precision"] >= min_switch_precision
        and row["severe_1_to_0"] <= 1
    ]
    if eligible:
        selected = max(eligible, key=lambda row: (row["relaxed_delta"], row["switch_precision"], -row["switches"], row["threshold"]))
        selected["selection_reason"] = "max_delta_under_preregistered_constraints"
    else:
        selected = reports[0]
        selected["selection_reason"] = "no_threshold_met_calibration_constraints"
    selected.pop("rows", None)
    return selected


def development_gate(report: dict[str, Any], min_switch_precision: float = 0.70) -> dict[str, bool]:
    checks = {
        "has_switches": report["switches"] > 0,
        "relaxed_positive": report["relaxed_delta"] > 0.0,
        "strict_non_decreasing": report["strict_selected"] >= report["strict_raw"],
        "switch_precision_at_least_0_70": report["switch_precision"] >= min_switch_precision,
        "severe_1_to_0_at_most_one": report["severe_1_to_0"] <= 1,
    }
    checks["passed"] = all(checks.values())
    return checks
