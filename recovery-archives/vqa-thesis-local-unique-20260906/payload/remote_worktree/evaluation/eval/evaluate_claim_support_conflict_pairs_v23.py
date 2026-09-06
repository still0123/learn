#!/usr/bin/env python3
"""Evaluate audited claim-pair separability from frozen Qwen support scores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from evaluation.methods.claim_evidence_verifier.reliability_v22 import auprc, auroc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_rows(labels: list[dict[str, Any]], scores: dict[str, dict[str, Any]]) -> dict[str, Any]:
    y, probabilities = [], []
    pairs: dict[str, dict[str, float]] = {}
    for row in labels:
        qid, source = str(row["question_id"]), str(row["source_question_id"])
        probability = float(scores[qid]["scores"]["full"]["supported"])
        y.append(int(row["supported"]))
        probabilities.append(probability)
        pairs.setdefault(source, {})[str(row["label_name"])] = probability
    pair_rows = []
    for source, values in sorted(pairs.items()):
        if set(values) != {"supported", "contradicted"}:
            raise RuntimeError(f"incomplete pair: {source}")
        delta = values["supported"] - values["contradicted"]
        pair_rows.append({"source_question_id": source, **values, "delta": delta, "correct": delta > 0})
    rng = random.Random(20260716)
    accuracies, deltas = [], []
    for _ in range(10000):
        sample = [pair_rows[rng.randrange(len(pair_rows))] for _ in pair_rows]
        accuracies.append(sum(row["correct"] for row in sample) / len(sample))
        deltas.append(sum(row["delta"] for row in sample) / len(sample))
    accuracies.sort()
    deltas.sort()
    return {
        "rows": len(labels), "pairs": len(pair_rows),
        "auroc": auroc(y, probabilities), "auprc": auprc(y, probabilities),
        "pair_accuracy": sum(row["correct"] for row in pair_rows) / len(pair_rows),
        "pair_accuracy_ci95": [accuracies[250], accuracies[9750]],
        "mean_support_delta": sum(row["delta"] for row in pair_rows) / len(pair_rows),
        "mean_support_delta_ci95": [deltas[250], deltas[9750]],
        "saturation_supported_ge_0_99": sum(row["supported"] >= 0.99 for row in pair_rows),
        "saturation_contradicted_ge_0_99": sum(row["contradicted"] >= 0.99 for row in pair_rows),
        "pair_rows": pair_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scores = {str(row["question_id"]): row for row in load_jsonl(args.scores)}
    labels = load_jsonl(args.labels)
    if set(scores) != {str(row["question_id"]) for row in labels}:
        raise RuntimeError("score/label alignment failed")
    report = {
        "schema": "adsqa_claim_support_conflict_pair_report_v23",
        **evaluate_rows(labels, scores),
    }
    split_names = sorted({str(row.get("split", "unknown")) for row in labels})
    if split_names != ["unknown"]:
        report["by_split"] = {
            split: evaluate_rows([row for row in labels if str(row.get("split")) == split], scores)
            for split in split_names
        }
    report["gate"] = {}
    report["gate"] = {
        "auroc_at_least_0_80": report["auroc"] >= 0.80,
        "pair_accuracy_at_least_0_80": report["pair_accuracy"] >= 0.80,
        "pair_accuracy_ci_lower_above_0_50": report["pair_accuracy_ci95"][0] > 0.50,
        "mean_delta_ci_lower_positive": report["mean_support_delta_ci95"][0] > 0.0,
    }
    report["gate"]["passed"] = all(report["gate"].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("pairs", "auroc", "auprc", "pair_accuracy", "pair_accuracy_ci95", "mean_support_delta", "mean_support_delta_ci95", "gate")}))


if __name__ == "__main__":
    main()
