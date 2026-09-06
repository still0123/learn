#!/usr/bin/env python3
"""Train and gate one fixed L2 logistic claim reliability verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
from evaluation.methods.claim_evidence_verifier.reliability_v22 import (
    FEATURE_SCHEMA_VERSION, build_feature_vector, classification_metrics,
    feature_names, feature_schema_sha256,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sigmoid(values):
    import numpy as np
    return 1.0 / (1.0 + np.exp(-np.clip(values, -40.0, 40.0)))


def bce(labels, probabilities) -> float:
    import numpy as np
    probabilities = np.clip(probabilities, 1e-8, 1.0 - 1e-8)
    return float(-np.mean(labels * np.log(probabilities) + (1.0 - labels) * np.log(1.0 - probabilities)))


def fit_logistic(x, y, l2: float = 0.01, learning_rate: float = 0.05, epochs: int = 2000):
    import numpy as np
    weights = np.zeros(x.shape[1], dtype=np.float64)
    bias = math.log(float(y.mean()) / (1.0 - float(y.mean())))
    for _ in range(epochs):
        probability = sigmoid(x @ weights + bias)
        error = probability - y
        weights -= learning_rate * ((x.T @ error) / len(y) + l2 * weights)
        bias -= learning_rate * float(error.mean())
    return weights, bias


def best_temperature(logits, labels) -> float:
    candidates = [0.50 + 0.05 * index for index in range(91)]
    return min(candidates, key=lambda value: bce(labels, sigmoid(logits / value)))


def best_f1_threshold(labels, probabilities) -> float:
    candidates = sorted(set(float(value) for value in probabilities), reverse=True)
    return max(
        candidates,
        key=lambda threshold: (
            classification_metrics(labels.tolist(), probabilities.tolist(), threshold)["f1"], threshold
        ),
    )


def risk_monotonic(metrics: dict[str, Any]) -> bool:
    risks = metrics["risk_coverage"]["risks"]
    return risks["0.4"] <= risks["0.6"] <= risks["0.8"] <= risks["1.0"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--support-scores", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    import numpy as np

    inputs = load_jsonl(args.inputs)
    labels = {str(row["question_id"]): row for row in load_jsonl(args.labels)}
    support = {str(row["question_id"]): row for row in load_jsonl(args.support_scores)}
    if set(labels) != {str(row["question_id"]) for row in inputs} or set(labels) != set(support):
        raise RuntimeError("v2.2 inputs, labels, and support scores must align exactly")
    records = []
    for row in inputs:
        qid = str(row["question_id"])
        records.append({
            "input": row, "label": int(labels[qid]["reliable"]),
            "features": build_feature_vector(row, support[qid]),
            "baseline": float(support[qid]["scores"]["full"]["supported"]),
        })
    partitions = {name: [row for row in records if row["input"]["split"] == name] for name in ("train", "calibration", "development")}
    train_x = np.asarray([row["features"] for row in partitions["train"]], dtype=np.float64)
    mean, std = train_x.mean(axis=0), train_x.std(axis=0)
    std[std < 1e-8] = 1.0
    arrays = {}
    for name, rows in partitions.items():
        arrays[name] = (
            (np.asarray([row["features"] for row in rows], dtype=np.float64) - mean) / std,
            np.asarray([row["label"] for row in rows], dtype=np.float64),
        )
    weights, bias = fit_logistic(*arrays["train"])
    calibration_logits = arrays["calibration"][0] @ weights + bias
    temperature = best_temperature(calibration_logits, arrays["calibration"][1])
    calibration_probabilities = sigmoid(calibration_logits / temperature)
    threshold = best_f1_threshold(arrays["calibration"][1], calibration_probabilities)
    reports, decisions = {}, []
    for name, rows in partitions.items():
        x, y = arrays[name]
        probabilities = sigmoid((x @ weights + bias) / temperature)
        baseline = np.asarray([row["baseline"] for row in rows], dtype=np.float64)
        reports[name] = {
            "model": classification_metrics(y.astype(int).tolist(), probabilities.tolist(), threshold),
            "baseline_full_support": classification_metrics(y.astype(int).tolist(), baseline.tolist(), 0.5),
        }
        for row, probability, baseline_probability in zip(rows, probabilities, baseline):
            decisions.append({
                "question_id": row["input"]["question_id"], "split": name,
                "primary_type": row["input"]["primary_type"], "label": row["label"],
                "probability": float(probability), "baseline_probability": float(baseline_probability),
            })
    dev_model, dev_baseline = reports["development"]["model"], reports["development"]["baseline_full_support"]
    gate = {
        "auroc_at_least_0_70": dev_model["auroc"] >= 0.70,
        "auroc_exceeds_full_support_baseline": dev_model["auroc"] > dev_baseline["auroc"],
        "aurc_improves": dev_model["risk_coverage"]["aurc"] < dev_baseline["risk_coverage"]["aurc"],
        "risk_monotonic_across_frozen_coverages": risk_monotonic(dev_model),
        "ece_not_worse": dev_model["ece_10bin"] <= dev_baseline["ece_10bin"],
    }
    gate["passed"] = all(gate.values())
    args.output_root.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "schema": "adsqa_claim_reliability_checkpoint_v22", "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(), "feature_names": feature_names(),
        "mean": mean.tolist(), "std": std.tolist(), "weights": weights.tolist(), "bias": bias,
        "temperature": temperature, "threshold": threshold, "l2": 0.01,
        "learning_rate": 0.05, "epochs": 2000,
        "groundtruth_feature_access": False, "judge_score_feature_access": False,
    }
    checkpoint_path = args.output_root / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.output_root / "decisions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in decisions), encoding="utf-8"
    )
    report = {
        "schema": "adsqa_claim_reliability_gate_report_v22", "partitions": reports,
        "temperature": temperature, "threshold": threshold, "gate": gate,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "input_sha256": sha256_file(args.inputs), "label_sha256": sha256_file(args.labels),
        "support_scores_sha256": sha256_file(args.support_scores),
    }
    (args.output_root / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"development": reports["development"], "gate": gate}))


if __name__ == "__main__":
    main()
