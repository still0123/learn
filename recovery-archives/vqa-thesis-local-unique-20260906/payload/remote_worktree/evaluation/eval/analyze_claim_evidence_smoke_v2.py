#!/usr/bin/env python3
"""Audit claim-verifier smoke scores without modifying the frozen run."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import random
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def auroc(labels: list[int], scores: list[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return 0.5
    ordered = sorted(zip(scores, labels), key=lambda row: row[0])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        rank_sum += ((index + 1 + end) / 2.0) * sum(label for _, label in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def log_odds(probability: float) -> float:
    value = min(1.0 - 1e-8, max(1e-8, probability))
    return math.log(value / (1.0 - value))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    contrasts = [row["necessity_contrast"] for row in rows]
    ordered = sorted(contrasts)
    trim = max(0, int(len(ordered) * 0.10))
    trimmed = ordered[trim:len(ordered) - trim] if trim else ordered
    accuracy = sum(row["necessity_contrast"] > 0 for row in rows) / len(rows)
    z = 1.959963984540054
    denominator = 1.0 + z * z / len(rows)
    center = (accuracy + z * z / (2.0 * len(rows))) / denominator
    half_width = z * math.sqrt(accuracy * (1.0 - accuracy) / len(rows) + z * z / (4.0 * len(rows) ** 2)) / denominator
    rng = random.Random(20260716)
    bootstrap_means = sorted(
        sum(rows[rng.randrange(len(rows))]["necessity_contrast"] for _ in rows) / len(rows)
        for _ in range(10000)
    )
    return {
        "n": len(rows),
        "strict_pair_accuracy": accuracy,
        "strict_pair_wilson_ci95": [max(0.0, center - half_width), min(1.0, center + half_width)],
        "target_drop_positive_rate": sum(row["target_drop"] > 0 for row in rows) / len(rows),
        "control_drop_positive_rate": sum(row["control_drop"] > 0 for row in rows) / len(rows),
        "mean_target_drop": sum(row["target_drop"] for row in rows) / len(rows),
        "mean_control_drop": sum(row["control_drop"] for row in rows) / len(rows),
        "mean_necessity_contrast": sum(contrasts) / len(rows),
        "median_necessity_contrast": ordered[len(ordered) // 2],
        "trimmed_mean_necessity_contrast": sum(trimmed) / len(trimmed),
        "mean_necessity_bootstrap_ci95": [bootstrap_means[250], bootstrap_means[9750]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--supervision", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scores = load_jsonl(args.scores)
    supervision = {str(row["question_id"]): row for row in load_jsonl(args.supervision)}
    if len(scores) != 30 or len({str(row["question_id"]) for row in scores}) != 30:
        raise RuntimeError("smoke score file must contain 30 unique rows")
    rows = []
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_modality: dict[str, list[dict[str, Any]]] = defaultdict(list)
    labels, full_support, full_log_odds = [], [], []
    for record in scores:
        qid = str(record["question_id"])
        judge_score = float(supervision[qid]["raw_judge_score"])
        full = float(record["scores"]["full"]["supported"])
        target = float(record["scores"]["target_removed"]["supported"])
        control = float(record["scores"]["control_removed"]["supported"])
        row = {
            "question_id": qid,
            "primary_type": record["primary_type"],
            "modality": str((record.get("metadata") or {}).get("modality", "unknown")),
            "judge_score": judge_score,
            "full_support": full,
            "target_drop": full - target,
            "control_drop": full - control,
            "necessity_contrast": control - target,
            "log_odds_necessity_contrast": (log_odds(full) - log_odds(target)) - (log_odds(full) - log_odds(control)),
        }
        rows.append(row)
        by_type[str(record["primary_type"])].append(row)
        by_modality[row["modality"]].append(row)
        labels.append(int(judge_score == 1.0))
        full_support.append(full)
        full_log_odds.append(log_odds(full))
    largest = sorted(rows, key=lambda row: abs(row["necessity_contrast"]), reverse=True)[:5]
    correctness_by_modality = {}
    for modality, members in sorted(by_modality.items()):
        modality_labels = [int(row["judge_score"] == 1.0) for row in members]
        correctness_by_modality[modality] = {
            "n": len(members),
            "strict_correct": sum(modality_labels),
            "full_support_auroc_for_strict_correct": auroc(
                modality_labels, [row["full_support"] for row in members]
            ),
            "necessity_contrast_auroc_for_strict_correct": auroc(
                modality_labels, [row["necessity_contrast"] for row in members]
            ),
            "full_support_saturation_ge_0_99": sum(row["full_support"] >= 0.99 for row in members),
        }
    overall_summary = summarize(rows)
    modality_summaries = {key: summarize(value) for key, value in sorted(by_modality.items())}
    report = {
        "schema": "adsqa_claim_evidence_smoke_analysis_v2",
        "overall": overall_summary,
        "by_primary_type": {key: summarize(value) for key, value in sorted(by_type.items())},
        "by_modality": modality_summaries,
        "correctness_by_modality": correctness_by_modality,
        "answer_correctness": {
            "strict_correct": sum(labels),
            "not_strict_correct": len(labels) - sum(labels),
            "full_support_auroc_for_strict_correct": auroc(labels, full_support),
            "full_log_odds_auroc_for_strict_correct": auroc(labels, full_log_odds),
            "full_support_saturation_ge_0_99": sum(value >= 0.99 for value in full_support),
            "full_support_saturation_ge_0_999": sum(value >= 0.999 for value in full_support),
        },
        "largest_absolute_contrasts": largest,
        "diagnostic_gate": {
            "target_drop_exceeds_control_drop": summarize(rows)["mean_necessity_contrast"] > 0,
            "strict_pair_accuracy_above_chance": summarize(rows)["strict_pair_accuracy"] > 0.5,
            "correctness_auroc_above_0_60": auroc(labels, full_support) > 0.60,
        },
    }
    report["diagnostic_gate"]["passed"] = all(report["diagnostic_gate"].values())
    visual = modality_summaries.get("visual")
    asr = modality_summaries.get("asr")
    report["scope_decision"] = {
        "overall_mean_ci_excludes_zero": overall_summary["mean_necessity_bootstrap_ci95"][0] > 0.0,
        "visual_intervention_robust": bool(
            visual and visual["strict_pair_wilson_ci95"][0] > 0.5
            and visual["mean_necessity_bootstrap_ci95"][0] > 0.0
        ),
        "asr_intervention_robust": bool(
            asr and asr["strict_pair_wilson_ci95"][0] > 0.5
            and asr["mean_necessity_bootstrap_ci95"][0] > 0.0
        ),
    }
    report["scope_decision"]["cross_modal_intervention_validated"] = all(
        report["scope_decision"].values()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["diagnostic_gate"]["passed"], **report["overall"]}))


if __name__ == "__main__":
    main()
