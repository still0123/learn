#!/usr/bin/env python3
"""Compare correct-evidence and mismatched-evidence claim-pair scores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pair_deltas(path: Path) -> dict[str, float]:
    rows = load_jsonl(path)
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        pair_id = str(row["question_id"])
        source, label = pair_id.rsplit("__", 1)
        grouped.setdefault(source, {})[label] = float(row["scores"]["full"]["supported"])
    return {source: values["supported"] - values["contradicted"] for source, values in grouped.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--correct-scores", type=Path, required=True)
    parser.add_argument("--mismatched-scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    correct, mismatched = pair_deltas(args.correct_scores), pair_deltas(args.mismatched_scores)
    if set(correct) != set(mismatched):
        raise RuntimeError("correct/mismatched pair alignment failed")
    rows = [{
        "source_question_id": qid, "correct_evidence_delta": correct[qid],
        "mismatched_evidence_delta": mismatched[qid], "evidence_gain": correct[qid] - mismatched[qid],
    } for qid in sorted(correct)]
    rng = random.Random(20260716)
    means = sorted(
        sum(rows[rng.randrange(len(rows))]["evidence_gain"] for _ in rows) / len(rows)
        for _ in range(10000)
    )
    report = {
        "schema": "adsqa_claim_evidence_dependence_report_v23", "pairs": len(rows),
        "correct_pair_accuracy": sum(row["correct_evidence_delta"] > 0 for row in rows) / len(rows),
        "mismatched_pair_accuracy": sum(row["mismatched_evidence_delta"] > 0 for row in rows) / len(rows),
        "correct_mean_delta": sum(row["correct_evidence_delta"] for row in rows) / len(rows),
        "mismatched_mean_delta": sum(row["mismatched_evidence_delta"] for row in rows) / len(rows),
        "mean_evidence_gain": sum(row["evidence_gain"] for row in rows) / len(rows),
        "mean_evidence_gain_ci95": [means[250], means[9750]], "rows": rows,
    }
    report["gate"] = {
        "correct_accuracy_exceeds_mismatched_by_0_20": report["correct_pair_accuracy"] - report["mismatched_pair_accuracy"] >= 0.20,
        "evidence_gain_ci_lower_positive": report["mean_evidence_gain_ci95"][0] > 0.0,
    }
    report["gate"]["passed"] = all(report["gate"].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("pairs", "correct_pair_accuracy", "mismatched_pair_accuracy", "correct_mean_delta", "mismatched_mean_delta", "mean_evidence_gain", "mean_evidence_gain_ci95", "gate")}))


if __name__ == "__main__":
    main()
