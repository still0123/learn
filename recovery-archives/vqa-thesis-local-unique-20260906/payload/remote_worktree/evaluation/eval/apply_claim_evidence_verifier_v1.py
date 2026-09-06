#!/usr/bin/env python3
"""Apply a frozen verifier to paired candidates and materialize predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.claim_evidence_verifier.features import build_feature_vector, feature_schema_sha256
from evaluation.methods.claim_evidence_verifier.numpy_mlp import BinaryMLP, Standardizer


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-jsonl", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--threshold-config", type=Path)
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--method-name", default="claim_evidence_verifier_v1")
    args = parser.parse_args()
    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    hash_dim = int(checkpoint["hash_dim"])
    if checkpoint["feature_schema_sha256"] != feature_schema_sha256(hash_dim):
        raise RuntimeError("feature schema does not match checkpoint")
    threshold = float(checkpoint.get("default_threshold", 0.5))
    threshold_source = "checkpoint_default"
    if args.threshold_config:
        config = json.loads(args.threshold_config.read_text(encoding="utf-8"))
        threshold = float(config["threshold"])
        threshold_source = str(args.threshold_config)
    if args.threshold is not None:
        threshold = args.threshold
        threshold_source = "command_line"
    if not 0.0 <= threshold <= 1.000001:
        raise ValueError("threshold must be in [0, 1]")
    records = load_jsonl(args.pair_jsonl)
    import numpy as np

    features = np.asarray([build_feature_vector(row, hash_dim) for row in records], dtype=np.float64)
    standardizer = Standardizer.from_dict(checkpoint["standardizer"])
    model = BinaryMLP.from_dict(checkpoint["model"])
    probabilities = model.predict_proba(standardizer.transform(features), checkpoint["temperature"]).tolist()
    decisions = []
    for record, probability in zip(records, probabilities):
        switched = probability >= threshold
        selected_answer = record["rescue_answer"] if switched else record["initial_answer"]
        qid = str(record["question_id"])
        supervision = record.get("supervision") or {}
        prediction = {
            "question_id": qid,
            "prediction": selected_answer,
            "ground_truth": str(supervision.get("ground_truth", "N/A")),
            "initial_reasoning": selected_answer,
            "pipeline": args.method_name,
            "reflection_status": "disabled_learned_pairwise_selector_v1",
            "rag_mode": "none",
            "score": "",
        }
        dump_json(args.output_root / "predictions" / qid / "prediction.json", prediction)
        decisions.append({
            "question_id": qid,
            "video_id": record.get("video_id"),
            "source_method": record.get("source_method"),
            "category": record.get("category"),
            "rescue_better_probability": probability,
            "threshold": threshold,
            "switched": switched,
            "selected_candidate": "rescue" if switched else "initial",
        })
    decision_path = args.output_root / "decisions.jsonl"
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in decisions), encoding="utf-8"
    )
    manifest = {
        "schema": "adsqa_claim_evidence_verifier_application_v1",
        "count": len(decisions),
        "switches": sum(row["switched"] for row in decisions),
        "threshold": threshold,
        "threshold_source": threshold_source,
        "pair_jsonl": str(args.pair_jsonl),
        "pair_jsonl_sha256": sha256_file(args.pair_jsonl),
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "decision_jsonl": str(decision_path),
        "decision_jsonl_sha256": sha256_file(decision_path),
    }
    dump_json(args.output_root / "application_manifest.json", manifest)
    print(json.dumps({"count": len(decisions), "switches": manifest["switches"], "threshold": threshold}))


if __name__ == "__main__":
    main()
