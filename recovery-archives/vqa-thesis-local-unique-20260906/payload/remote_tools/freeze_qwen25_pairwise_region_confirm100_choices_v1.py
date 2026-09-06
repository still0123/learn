#!/usr/bin/env python3
"""Freeze conservative symmetric pairwise choices for Confirm-100."""

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path("evaluation/runs/qwen25_active_evidence_look_v1")
RUN = ROOT / "pairwise_region_confirm100_v1"
BASE = ROOT / "region_gate_confirm100_v1/frozen_choices_v1/choices_answer_free.jsonl"


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(value):
    return hashlib.sha256(" ".join(value.strip().casefold().split()).encode()).hexdigest()


changed = {row["question_id"]: row for row in rows(RUN / "inputs/changed49.jsonl")}
arms = {}
traces = []
for order in ("a0_first", "a2_first"):
    arms[order] = {}
    for path in (RUN / "inference" / order).glob("*/pairwise_choice.json"):
        row = json.loads(path.read_text())
        arms[order][row["question_id"]] = row
    for path in (RUN / "inference" / order).glob("*/pairwise_trace.json"):
        traces.append(json.loads(path.read_text()))

assert len(changed) == len(arms["a0_first"]) == len(arms["a2_first"]) == 49
selected = {
    qid for qid in changed
    if arms["a0_first"][qid]["candidate_selected"]
    and arms["a2_first"][qid]["candidate_selected"]
}
conflicts = {
    qid for qid in changed
    if arms["a0_first"][qid]["candidate_selected"]
    != arms["a2_first"][qid]["candidate_selected"]
}

choices = []
for old in rows(BASE):
    qid = old["question_id"]
    candidate = changed.get(qid, {}).get("candidate_prediction", old["candidate_prediction"])
    switched = qid in selected
    final = candidate if switched else old["a0_prediction"]
    choices.append({
        "question_id": qid,
        "video_id": old["video_id"],
        "action": "LOOK_REGION" if qid in changed else old["action"],
        "a0_prediction": old["a0_prediction"],
        "candidate_prediction": candidate,
        "final_prediction": final,
        "final_sha256": digest(final),
        "switched": switched,
        "pairwise_a0_first_choice": arms["a0_first"].get(qid, {}).get("choice"),
        "pairwise_a2_first_choice": arms["a2_first"].get(qid, {}).get("choice"),
        "symmetric_candidate_required": True,
        "answer_free": True,
        "not_human_gold": True,
    })

assert len(choices) == 100 and sum(row["switched"] for row in choices) == 7
out = RUN / "frozen_choices_v1"
out.mkdir(parents=True, exist_ok=True)
(out / "choices_answer_free.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in choices)
)
audit = {
    "schema_version": "qwen25_pairwise_region_confirm100_choices_v1",
    "passed": True,
    "questions": 100,
    "changed_candidates_considered": 49,
    "switched": len(selected),
    "order_conflicts_fallback_to_a0": len(conflicts),
    "parse_invalid_fallback_to_a0": sum(not row["parse_valid"] for row in traces),
    "a0_first_choices": dict(Counter(row["choice"] for row in arms["a0_first"].values())),
    "a2_first_choices": dict(Counter(row["choice"] for row in arms["a2_first"].values())),
    "visual_tokens": sorted({row["processor_trace"]["visual_tokens"] for row in traces}),
    "represented_views": sorted({row["processor_trace"]["represented_views"] for row in traces}),
    "groundtruth_read": False,
    "judge_scores_read": False,
    "not_human_gold": True,
}
(out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
(out / "CHOICES_FROZEN").write_text("complete\n")
print(json.dumps(audit))
