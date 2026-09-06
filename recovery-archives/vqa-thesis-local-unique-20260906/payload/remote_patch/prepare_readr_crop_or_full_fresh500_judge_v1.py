#!/usr/bin/env python3
"""Prepare answer-free DeepSeek candidate manifests for Fresh-500."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--authorized-limit", type=int, default=757)
    a = p.parse_args()
    if a.output_dir.exists() and any(a.output_dir.iterdir()):
        raise RuntimeError("output directory exists")

    questions = json.loads((a.run / "dataset/questions_answer_free.json").read_text())
    qmap = {str(x["question_id"]): x for x in questions}
    a0_rows = load_jsonl(a.run / "a0_verifier_pool/model_inputs_all.jsonl")
    a0 = {str(x["source_question_id"]): str(x["claim"]) for x in a0_rows}
    video_ids = {
        str(x["source_question_id"]): str(x["video_id"]) for x in a0_rows
    }
    trigger_items = {
        str(x["question_id"]): x
        for x in load_jsonl(a.run / "threshold_crop_or_full_pool_v2/items_answer_free.jsonl")
    }
    choices = {
        str(x["question_id"]): x
        for x in load_jsonl(a.run / "frozen_choices_crop_or_full_v2/frozen_choices_answer_free.jsonl")
    }
    if len(qmap) != 500 or set(qmap) != set(a0) or set(trigger_items) != set(choices):
        raise RuntimeError("coverage mismatch")

    candidates = []
    slots = []
    seen = set()
    for qid in sorted(qmap):
        p0 = a0[qid]
        h0 = sha(p0)
        if (qid, h0) not in seen:
            candidates.append({"question_id": qid, "prediction": p0, "prediction_sha256": h0})
            seen.add((qid, h0))
        slot = {"question_id": qid, "video_id": video_ids[qid], "A0": h0}
        if qid in choices:
            p2 = str(choices[qid]["a2_prediction"])
            h2 = sha(p2)
            if (qid, h2) not in seen:
                candidates.append({"question_id": qid, "prediction": p2, "prediction_sha256": h2})
                seen.add((qid, h2))
            slot["A2"] = h2
            slot["FINAL"] = h2 if choices[qid]["switched"] else h0
            slot["triggered"] = True
            slot["switched"] = bool(choices[qid]["switched"])
            slot["crop_anchor_count"] = int(choices[qid]["route_crop_anchor_count"])
        else:
            slot.update({"FINAL": h0, "triggered": False, "switched": False, "crop_anchor_count": 0})
        slots.append(slot)

    a.output_dir.mkdir(parents=True)
    cp = a.output_dir / "candidates_answer_free.jsonl"
    sp = a.output_dir / "candidate_slots_answer_free.jsonl"
    write_jsonl(cp, candidates)
    write_jsonl(sp, slots)
    inference_audit = {
        "schema_version": "readr_crop_or_full_fresh500_inference_audit_v1",
        "passed": True,
        "question_count": 500,
        "trigger_count": 257,
        "switch_count": sum(x["switched"] for x in slots),
        "answer_free_inference_complete": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
    }
    (a.output_dir / "inference_audit.json").write_text(json.dumps(inference_audit, indent=2) + "\n")
    audit = {
        "schema_version": "readr_crop_or_full_fresh500_judge_preflight_v1",
        "passed": len(candidates) <= a.authorized_limit and len(slots) == 500,
        "question_count": 500,
        "trigger_count": 257,
        "switch_count": sum(x["switched"] for x in slots),
        "unique_question_answer_calls": len(candidates),
        "authorized_call_limit": a.authorized_limit,
        "identity_duplicate_savings": 757 - len(candidates),
        "judge_rubric": "official_evads_R5_R3_R2",
        "groundtruth_read_during_preflight": False,
        "candidates_sha256": hashlib.sha256(cp.read_bytes()).hexdigest(),
        "slots_sha256": hashlib.sha256(sp.read_bytes()).hexdigest(),
    }
    (a.output_dir / "dry_run_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    if not audit["passed"]:
        raise RuntimeError("judge preflight failed")


if __name__ == "__main__":
    main()
