#!/usr/bin/env python3
"""Train and gate the fixed Evidence-300 Raw/MMR pre-answer router."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.adaptive_temporal_router.features import (
    DEFAULT_HASH_DIM, FEATURE_SCHEMA_VERSION, build_feature_vector, feature_names, feature_schema_sha256,
)
from evaluation.methods.adaptive_temporal_router.metrics import (
    binary_metrics, choose_calibration_threshold, development_gate, selection_metrics,
)
from evaluation.methods.adaptive_temporal_router.numpy_model import BinaryMLP, Standardizer, sigmoid


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def internal_group_split(records, fraction: float = 0.20, seed: int = 42):
    groups = sorted(
        {row["video_id"] for row in records},
        key=lambda value: hashlib.sha256(f"{seed}:{value}".encode()).hexdigest(),
    )
    validation_groups = set(groups[: max(1, round(len(groups) * fraction))])
    fit = [row for row in records if row["video_id"] not in validation_groups]
    validation = [row for row in records if row["video_id"] in validation_groups]
    return fit, validation, sorted(validation_groups)


def bce(labels, probabilities):
    epsilon = 1e-8
    return -sum(
        label * math.log(probability + epsilon) + (1 - label) * math.log(1 - probability + epsilon)
        for label, probability in zip(labels, probabilities)
    ) / len(labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-jsonl", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--hash-dim", type=int, default=DEFAULT_HASH_DIM)
    parser.add_argument("--hidden-dim", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--l2", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=80)
    parser.add_argument("--min-switch-precision", type=float, default=0.70)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = load_jsonl(args.dataset_jsonl)
    splits = {name: [row for row in records if row["split"] == name] for name in ("train", "calibration", "development")}
    if {key: len(value) for key, value in splits.items()} != {"train": 200, "calibration": 50, "development": 50}:
        raise RuntimeError("frozen 200/50/50 split is required")
    fit, validation, validation_groups = internal_group_split(splits["train"], seed=args.seed)
    import numpy as np

    def x(rows): return np.asarray([build_feature_vector(row, args.hash_dim) for row in rows], dtype=np.float64)
    def y(rows): return np.asarray([row["supervision"]["mmr_better"] for row in rows], dtype=np.float64)
    fit_x, validation_x = x(fit), x(validation)
    fit_y, validation_y = y(fit), y(validation)
    if min(fit_y.sum(), validation_y.sum()) < 1:
        raise RuntimeError("internal fit and validation both require positive examples")
    standardizer = Standardizer.fit(fit_x)
    fit_x, validation_x = standardizer.transform(fit_x), standardizer.transform(validation_x)
    model = BinaryMLP(fit_x.shape[1], args.hidden_dim, args.seed)
    training = model.fit(
        fit_x, fit_y, validation_x, validation_y,
        epochs=args.epochs, learning_rate=args.learning_rate, l2=args.l2, patience=args.patience,
    )
    validation_logits = model.logits(validation_x)
    temperatures = [0.50 + 0.05 * index for index in range(91)]
    temperature = min(temperatures, key=lambda value: bce(validation_y.tolist(), sigmoid(validation_logits / value).tolist()))

    def probabilities(rows):
        return model.predict_proba(standardizer.transform(x(rows)), temperature).tolist()
    fit_prob = probabilities(fit)
    validation_prob = probabilities(validation)
    calibration_prob = probabilities(splits["calibration"])
    development_prob = probabilities(splits["development"])
    threshold_report = choose_calibration_threshold(
        splits["calibration"], calibration_prob, min_switch_precision=args.min_switch_precision
    )
    threshold = float(threshold_report["threshold"])
    development_report = selection_metrics(
        splits["development"], development_prob, threshold,
        bootstrap_samples=args.bootstrap_samples, seed=args.seed,
    )
    development_report["gate"] = development_gate(development_report, args.min_switch_precision)

    args.output_root.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "schema": "adsqa_adaptive_temporal_router_checkpoint_v1",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(args.hash_dim),
        "feature_names": feature_names(args.hash_dim), "hash_dim": args.hash_dim,
        "hidden_dim": args.hidden_dim, "temperature": temperature, "threshold": threshold,
        "standardizer": standardizer.to_dict(), "model": model.to_dict(), "seed": args.seed,
        "groundtruth_feature_access": False, "judge_score_feature_access": False,
        "answer_feature_access": False, "dataset_sha256": sha256(args.dataset_jsonl),
    }
    checkpoint_path = args.output_root / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {
        "schema": "adsqa_adaptive_temporal_router_gate_report_v1",
        "dataset_sha256": sha256(args.dataset_jsonl),
        "split_counts": {key: len(value) for key, value in splits.items()},
        "internal_fit_count": len(fit), "internal_validation_count": len(validation),
        "internal_validation_groups": validation_groups,
        "positive_counts": {key: int(y(value).sum()) for key, value in splits.items()},
        "training": training, "temperature": temperature,
        "fit_binary_metrics": binary_metrics(fit_y.astype(int).tolist(), fit_prob),
        "internal_validation_binary_metrics": binary_metrics(validation_y.astype(int).tolist(), validation_prob),
        "calibration_threshold_selection": threshold_report,
        "development_selection": development_report,
        "checkpoint": str(checkpoint_path), "checkpoint_sha256": sha256(checkpoint_path),
    }
    report_path = args.output_root / "gate_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    decisions = []
    for split_name in ("calibration", "development"):
        rows = splits[split_name]
        probs = calibration_prob if split_name == "calibration" else development_prob
        for row, probability in zip(rows, probs):
            decisions.append({
                "question_id": row["question_id"], "split": split_name,
                "primary_type": row["primary_type"], "mmr_probability": probability,
                "threshold": threshold, "route": "mmr32" if probability >= threshold else "raw_uniform",
                "supervision": row["supervision"],
            })
    (args.output_root / "decisions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in decisions), encoding="utf-8"
    )
    if development_report["gate"]["passed"]:
        (args.output_root / "DEVELOPMENT_GATE_PASS").write_text(sha256(report_path) + "\n", encoding="utf-8")
    print(json.dumps({
        "threshold": threshold, "development_gate": development_report["gate"],
        "development_delta": development_report["relaxed_delta"],
        "development_switches": development_report["switches"],
        "report_sha256": sha256(report_path),
    }))


if __name__ == "__main__":
    main()
