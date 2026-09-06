#!/usr/bin/env python3
"""Train a frozen-feature MLP to predict whether the rescue answer is better."""

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

from evaluation.methods.claim_evidence_verifier.features import (
    DEFAULT_HASH_DIM,
    FEATURE_SCHEMA_VERSION,
    build_feature_vector,
    feature_names,
    feature_schema_sha256,
)
from evaluation.methods.claim_evidence_verifier.metrics import binary_metrics
from evaluation.methods.claim_evidence_verifier.numpy_mlp import BinaryMLP, Standardizer, sigmoid


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stable_group_split(records: list[dict[str, Any]], fraction: float, seed: int):
    groups = sorted(
        {str(row.get("video_id") or row["question_id"]) for row in records},
        key=lambda value: hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest(),
    )
    calibration_count = max(1, round(len(groups) * fraction))
    calibration_groups = set(groups[:calibration_count])
    train = [row for row in records if str(row.get("video_id") or row["question_id"]) not in calibration_groups]
    calibration = [row for row in records if str(row.get("video_id") or row["question_id"]) in calibration_groups]
    if not train or not calibration:
        raise RuntimeError("group split produced an empty partition")
    return train, calibration, sorted(calibration_groups)


def bce(labels, probabilities) -> float:
    epsilon = 1e-8
    return -sum(
        label * math.log(probability + epsilon) + (1 - label) * math.log(1 - probability + epsilon)
        for label, probability in zip(labels, probabilities)
    ) / len(labels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-jsonl", type=Path, action="append", required=True)
    parser.add_argument("--checkpoint-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--hash-dim", type=int, default=DEFAULT_HASH_DIM)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=80)
    parser.add_argument("--calibration-fraction", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not 0.05 <= args.calibration_fraction <= 0.40:
        raise ValueError("calibration-fraction must be between 0.05 and 0.40")
    records = [row for path in args.pair_jsonl for row in load_jsonl(path)]
    if not records or any("supervision" not in row for row in records):
        raise RuntimeError("all training records must contain immutable supervision")
    train_records, calibration_records, calibration_groups = stable_group_split(
        records, args.calibration_fraction, args.seed
    )
    import numpy as np

    train_x = np.asarray([build_feature_vector(row, args.hash_dim) for row in train_records], dtype=np.float64)
    calibration_x = np.asarray([build_feature_vector(row, args.hash_dim) for row in calibration_records], dtype=np.float64)
    train_y = np.asarray([int(row["supervision"]["rescue_better"]) for row in train_records], dtype=np.float64)
    calibration_y = np.asarray([int(row["supervision"]["rescue_better"]) for row in calibration_records], dtype=np.float64)
    if train_y.sum() == 0 or calibration_y.sum() == 0:
        raise RuntimeError("both train and calibration partitions require at least one rescue-better example")
    standardizer = Standardizer.fit(train_x)
    train_x = standardizer.transform(train_x)
    calibration_x = standardizer.transform(calibration_x)
    model = BinaryMLP(train_x.shape[1], args.hidden_dim, args.seed)
    training = model.fit(
        train_x, train_y, calibration_x, calibration_y,
        epochs=args.epochs, learning_rate=args.learning_rate, l2=args.l2, patience=args.patience,
    )
    calibration_logits = model.logits(calibration_x)
    temperature_candidates = [0.50 + 0.05 * index for index in range(91)]
    temperature = min(
        temperature_candidates,
        key=lambda value: bce(calibration_y.tolist(), sigmoid(calibration_logits / value).tolist()),
    )
    train_probabilities = model.predict_proba(train_x, temperature).tolist()
    calibration_probabilities = model.predict_proba(calibration_x, temperature).tolist()
    names = feature_names(args.hash_dim)
    checkpoint = {
        "schema": "adsqa_claim_evidence_verifier_checkpoint_v1",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(args.hash_dim),
        "hash_dim": args.hash_dim,
        "feature_count": len(names),
        "feature_names": names,
        "hidden_dim": args.hidden_dim,
        "temperature": temperature,
        "default_threshold": 0.5,
        "standardizer": standardizer.to_dict(),
        "model": model.to_dict(),
        "seed": args.seed,
        "input_pair_files": [
            {"path": str(path), "sha256": sha256_file(path)} for path in args.pair_jsonl
        ],
        "groundtruth_feature_access": False,
        "judge_score_feature_access": False,
    }
    args.checkpoint_output.parent.mkdir(parents=True, exist_ok=True)
    args.checkpoint_output.write_text(json.dumps(checkpoint, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {
        "schema": "adsqa_claim_evidence_verifier_training_report_v1",
        "record_count": len(records),
        "unique_videos": len({str(row.get("video_id")) for row in records}),
        "train_count": len(train_records),
        "calibration_count": len(calibration_records),
        "calibration_groups": calibration_groups,
        "train_positive_count": int(train_y.sum()),
        "calibration_positive_count": int(calibration_y.sum()),
        "temperature": temperature,
        "training": training,
        "train_metrics": binary_metrics(train_y.astype(int).tolist(), train_probabilities),
        "calibration_metrics": binary_metrics(calibration_y.astype(int).tolist(), calibration_probabilities),
        "checkpoint": str(args.checkpoint_output),
        "checkpoint_sha256": sha256_file(args.checkpoint_output),
    }
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "train": len(train_records), "calibration": len(calibration_records),
        "calibration_auroc": report["calibration_metrics"]["auroc"],
        "checkpoint_sha256": report["checkpoint_sha256"],
    }))


if __name__ == "__main__":
    main()
