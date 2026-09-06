#!/usr/bin/env python3
"""Evaluate verifier probabilities and freeze the Dev-selected threshold."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.claim_evidence_verifier.metrics import (
    binary_metrics,
    selection_metrics,
    paired_bootstrap_ci,
    select_conservative_threshold,
    stage_gate,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-jsonl", type=Path, required=True)
    parser.add_argument("--decisions-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold-output", type=Path)
    parser.add_argument("--select-threshold", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min-switch-precision", type=float, default=0.70)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    records = load_jsonl(args.pair_jsonl)
    decisions = load_jsonl(args.decisions_jsonl)
    record_map = {(str(row["source_method"]), str(row["question_id"])): row for row in records}
    probability_map = {
        (str(row["source_method"]), str(row["question_id"])): float(row["rescue_better_probability"])
        for row in decisions
    }
    if set(record_map) != set(probability_map):
        raise RuntimeError("pair and decision keys are not exactly aligned")
    ordered_keys = sorted(record_map)
    ordered_records = [record_map[key] for key in ordered_keys]
    probabilities = [probability_map[key] for key in ordered_keys]
    if any("supervision" not in row for row in ordered_records):
        raise RuntimeError("evaluation pairs require immutable supervision")
    labels = [int(row["supervision"]["rescue_better"]) for row in ordered_records]
    if args.select_threshold:
        selection = select_conservative_threshold(
            ordered_records,
            probabilities,
            min_switch_precision=args.min_switch_precision,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
    else:
        selection = selection_metrics(ordered_records, probabilities, args.threshold)
        selection["bootstrap_ci95"] = paired_bootstrap_ci(
            selection["rows"], samples=args.bootstrap_samples, seed=args.seed
        )
        selection["gate"] = stage_gate(selection, args.min_switch_precision)
    rows = selection.pop("rows")
    report = {
        "schema": "adsqa_claim_evidence_verifier_evaluation_v1",
        "pairwise": binary_metrics(labels, probabilities),
        "selection": selection,
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "pair_jsonl": str(args.pair_jsonl),
        "pair_jsonl_sha256": sha256_file(args.pair_jsonl),
        "decisions_jsonl": str(args.decisions_jsonl),
        "decisions_jsonl_sha256": sha256_file(args.decisions_jsonl),
        "per_question": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.select_threshold:
        if not args.threshold_output:
            raise ValueError("--threshold-output is required with --select-threshold")
        threshold_config = {
            "schema": "adsqa_claim_evidence_dev_threshold_v1",
            "threshold": selection["threshold"],
            "selection_reason": selection["selection_reason"],
            "min_switch_precision": args.min_switch_precision,
            "dev_report": str(args.output),
            "dev_report_sha256": sha256_file(args.output),
            "confirm_policy": "frozen threshold; one run; no tuning",
        }
        args.threshold_output.parent.mkdir(parents=True, exist_ok=True)
        args.threshold_output.write_text(json.dumps(threshold_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pairwise_auroc": report["pairwise"]["auroc"],
        "threshold": selection["threshold"],
        "switch_precision": selection["switch_precision"],
        "relaxed_delta": selection["relaxed_delta"],
        "gate_passed": (selection.get("gate") or {}).get("passed"),
    }))


if __name__ == "__main__":
    main()
