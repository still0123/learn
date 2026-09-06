#!/usr/bin/env python3
"""Freeze all remaining Pilot-300 videos as an internal Confirm-60B."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def action(tree: dict, support: float) -> str:
    if support >= 0.97:
        return "DIRECT"
    logic = tree["logic_tree"]
    experts = {str(leaf["expert"]) for leaf in logic.get("leaves", []) if leaf.get("required", True)}
    if "OCR" in experts:
        return "LOOK_REGION"
    if experts & {"ASR", "VISUAL_ACTION"} or logic.get("operator") in {"SEQ", "RIGHT_AFTER"}:
        return "LOOK_TIME"
    return "DIRECT"


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--logic-trees", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--smoke", type=Path, required=True)
    parser.add_argument("--confirm100", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    items = {str(row["question_id"]): row for row in rows(args.items)}
    trees = {str(row["question_id"]): row for row in rows(args.logic_trees)}
    scores = {str(row["source_question_id"]): float(row["support_probability"]) for row in rows(args.scores)}
    used_videos = {str(row["video_id"]) for row in rows(args.smoke)} | {str(row["video_id"]) for row in rows(args.confirm100)}
    selected = [qid for qid in sorted(set(items) & set(trees) & set(scores)) if str(items[qid]["video_id"]) not in used_videos]
    master, time_inputs, region_inputs = [], [], []
    for qid in selected:
        selected_action = action(trees[qid], scores[qid])
        master.append({
            "question_id": qid, "video_id": str(items[qid]["video_id"]),
            "action": selected_action, "support_probability": scores[qid],
            "answer_free": True, "not_human_gold": True,
        })
        if selected_action == "LOOK_TIME":
            time_inputs.append(items[qid])
        elif selected_action == "LOOK_REGION":
            region_inputs.append(items[qid])
    counts = Counter(row["action"] for row in master)
    if len(master) != 60 or len({row["video_id"] for row in master}) != 12 or counts != {"LOOK_REGION": 37, "LOOK_TIME": 13, "DIRECT": 10}:
        raise RuntimeError(f"frozen Confirm-60B population changed: {len(master)}, {counts}")
    if any(len(row.get("asr_evidence", [])) < 2 for row in time_inputs):
        raise RuntimeError("LOOK_TIME item lacks two ASR segments")
    write_jsonl(args.output_root / "master_answer_free.jsonl", master)
    write_jsonl(args.output_root / "inputs" / "time.jsonl", time_inputs)
    write_jsonl(args.output_root / "inputs" / "region.jsonl", region_inputs)
    audit = {
        "schema_version": "qwen25_active_evidence_confirm60b_dataset_v1",
        "count": 60, "video_count": 12, "prior_video_overlap": 0,
        "action_counts": dict(counts), "selection_read_judge_scores": False,
        "answer_free": True, "not_human_gold": True,
        "master_sha256": hashlib.sha256((args.output_root / "master_answer_free.jsonl").read_bytes()).hexdigest(),
        "limitation": "internal calibration100 partition; not final independent test",
    }
    (args.output_root / "dataset_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "DATASET_COMPLETE").write_text("complete\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
