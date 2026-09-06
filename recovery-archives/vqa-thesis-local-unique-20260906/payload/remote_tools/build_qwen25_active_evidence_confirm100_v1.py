#!/usr/bin/env python3
"""Freeze a video-separated Confirm-100 for Qwen2.5 active evidence tools."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action_for(tree: dict[str, Any], support: float) -> tuple[str, str]:
    if support >= 0.97:
        return "DIRECT", "high_support"
    logic = tree["logic_tree"]
    experts = {str(leaf["expert"]) for leaf in logic.get("leaves", []) if leaf.get("required", True)}
    if "OCR" in experts:
        return "LOOK_REGION", "required_ocr_leaf_low_support"
    if experts & {"ASR", "VISUAL_ACTION"} or logic.get("operator") in {"SEQ", "RIGHT_AFTER"}:
        return "LOOK_TIME", "required_temporal_leaf_low_support"
    return "DIRECT", "no_localizable_gap"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--logic-trees", type=Path, required=True)
    parser.add_argument("--verifier-scores", type=Path, required=True)
    parser.add_argument("--smoke-trajectories", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    questions = {str(row["question_id"]): row for row in json.loads(args.questions.read_text(encoding="utf-8"))}
    items = {str(row["question_id"]): row for row in jsonl(args.items)}
    trees = {str(row["question_id"]): row for row in jsonl(args.logic_trees)}
    supports = {str(row["source_question_id"]): float(row["support_probability"]) for row in jsonl(args.verifier_scores)}
    smoke_videos = {str(row["video_id"]) for row in jsonl(args.smoke_trajectories)}
    eligible = [
        qid for qid in sorted(set(items) & set(trees) & set(supports) & set(questions))
        if questions[qid].get("pilot_partition") == "confirm200"
        and str(items[qid]["video_id"]) not in smoke_videos
    ]
    by_video: dict[str, list[str]] = defaultdict(list)
    for qid in eligible:
        by_video[str(items[qid]["video_id"])].append(qid)
    selected = []
    round_index = 0
    while len(selected) < 100:
        added = 0
        for video_id in sorted(by_video):
            if round_index < len(by_video[video_id]):
                selected.append(by_video[video_id][round_index])
                added += 1
                if len(selected) == 100:
                    break
        if not added:
            break
        round_index += 1
    if len(selected) != 100:
        raise RuntimeError(f"only {len(selected)} eligible confirm questions")

    master = []
    inputs: dict[str, list[dict[str, Any]]] = {
        "active_region": [], "active_time": [], "full_only": [],
        "random_region": [], "random_time": [],
    }
    for qid in selected:
        action, reason = action_for(trees[qid], supports[qid])
        random_action = "LOOK_REGION" if int(hashlib.sha256(qid.encode()).hexdigest(), 16) % 2 else "LOOK_TIME"
        master.append({
            "schema_version": "qwen25_active_evidence_confirm100_v1",
            "question_id": qid,
            "video_id": str(items[qid]["video_id"]),
            "support_probability": supports[qid],
            "logic_tree": trees[qid]["logic_tree"],
            "action": action,
            "gap_reason": reason,
            "random_action": random_action if action != "DIRECT" else "DIRECT",
            "answer_free": True,
            "not_human_gold": True,
        })
        if action == "DIRECT":
            continue
        row = dict(items[qid])
        if action == "LOOK_REGION":
            inputs["active_region"].append(row)
        else:
            inputs["active_time"].append(row)
        inputs["full_only"].append(row)
        inputs["random_region" if random_action == "LOOK_REGION" else "random_time"].append(row)

    master_path = args.output_root / "confirm100_master_answer_free.jsonl"
    write_jsonl(master_path, master)
    for name, part in inputs.items():
        write_jsonl(args.output_root / "inputs" / f"{name}.jsonl", part)
    audit = {
        "schema_version": "qwen25_active_evidence_confirm100_audit_v1",
        "count": len(master),
        "video_count": len({row["video_id"] for row in master}),
        "smoke_video_overlap": len({row["video_id"] for row in master} & smoke_videos),
        "action_counts": {name: sum(row["action"] == name for row in master) for name in ("DIRECT", "LOOK_TIME", "LOOK_REGION")},
        "inference_input_counts": {name: len(part) for name, part in inputs.items()},
        "selection_read_judge_scores": False,
        "answer_free": True,
        "source_hashes": {str(path): sha(path) for path in (args.questions, args.items, args.logic_trees, args.verifier_scores, args.smoke_trajectories)},
        "master_sha256": sha(master_path),
    }
    if audit["smoke_video_overlap"]:
        raise RuntimeError("Smoke/Confirm video overlap")
    dump(args.output_root / "audit.json", audit)
    (args.output_root / "CONFIRM100_DATASET_COMPLETE").write_text("complete\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
