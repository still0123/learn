#!/usr/bin/env python3
"""Freeze and score a 20-item answer-free active-evidence-look smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def predictions(root: Path) -> dict[str, str]:
    result = {}
    for path in root.glob("fold_*/*/a2_prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        result[str(row["question_id"])] = str(row["prediction"])
    return result


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


def metrics(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    values = [float(row[key]) for row in rows]
    return {
        "strict": sum(value == 1.0 for value in values) / len(values),
        "relaxed": sum(values) / len(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logic-trees", type=Path, required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--verifier-scores", type=Path, required=True)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--extra-root", type=Path, required=True)
    parser.add_argument("--judge-scores", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    items = {str(row["question_id"]): row for row in jsonl(args.items)}
    trees = {str(row["question_id"]): row for row in jsonl(args.logic_trees)}
    supports = {str(row["source_question_id"]): float(row["support_probability"]) for row in jsonl(args.verifier_scores)}
    adaptive = predictions(args.adaptive_root)
    extra = predictions(args.extra_root)
    common = set(items) & set(trees) & set(supports) & set(adaptive) & set(extra)
    if len(common) < 299:
        raise RuntimeError(f"expected at least 299 aligned rows, found {len(common)}")

    pools: dict[str, list[dict[str, Any]]] = {"LOOK_REGION": [], "LOOK_TIME": [], "DIRECT": []}
    for qid in sorted(common):
        action, reason = action_for(trees[qid], supports[qid])
        pools[action].append({"qid": qid, "action": action, "reason": reason, "support": supports[qid]})
    pools["LOOK_REGION"].sort(key=lambda row: (row["support"], row["qid"]))
    pools["LOOK_TIME"].sort(key=lambda row: (row["support"], row["qid"]))
    pools["DIRECT"].sort(key=lambda row: (-row["support"], row["qid"]))

    selected, used_videos = [], set()
    for action, target in (("LOOK_REGION", 7), ("LOOK_TIME", 7), ("DIRECT", 6)):
        for row in pools[action]:
            video_id = str(items[row["qid"]]["video_id"])
            if video_id in used_videos:
                continue
            selected.append(row)
            used_videos.add(video_id)
            if sum(item["action"] == action for item in selected) == target:
                break
    if len(selected) != 20:
        raise RuntimeError(f"unable to freeze 7/7/6 action-balanced smoke: {len(selected)}")

    trajectories = []
    for row in selected:
        qid, action = row["qid"], row["action"]
        item, tree = items[qid], trees[qid]
        random_action = "LOOK_REGION" if int(hashlib.sha256(qid.encode()).hexdigest(), 16) % 2 else "LOOK_TIME"
        active_answer = item["a0_prediction"] if action == "DIRECT" else (adaptive[qid] if action == "LOOK_REGION" else extra[qid])
        random_answer = item["a0_prediction"] if action == "DIRECT" else (adaptive[qid] if random_action == "LOOK_REGION" else extra[qid])
        full_answer = item["a0_prediction"] if action == "DIRECT" else extra[qid]
        trajectories.append({
            "schema_version": "qwen25_active_evidence_look_smoke_v1",
            "question_id": qid,
            "video_id": str(item["video_id"]),
            "question": str(item["question"]),
            "support_probability": row["support"],
            "logic_tree": tree["logic_tree"],
            "gap_reason": row["reason"],
            "action": action,
            "random_action": random_action if action != "DIRECT" else "DIRECT",
            "evidence_anchor_count": len(item.get("evidence_anchors", [])),
            "ocr_evidence_count": len(item.get("ocr_evidence", [])),
            "asr_quality": item.get("asr_quality"),
            "a0_prediction": item["a0_prediction"],
            "active_look_prediction": active_answer,
            "random_look_prediction": random_answer,
            "full_only_prediction": full_answer,
            "answer_free": True,
            "not_human_gold": True,
        })

    trajectory_path = args.output_root / "trajectories_answer_free.jsonl"
    dump_jsonl(trajectory_path, trajectories)
    audit = {
        "schema_version": "qwen25_active_evidence_look_smoke_audit_v1",
        "count": len(trajectories),
        "aligned_source_count": len(common),
        "excluded_logic_parse_failures": 300 - len(common),
        "video_count": len({row["video_id"] for row in trajectories}),
        "action_counts": {action: sum(row["action"] == action for row in trajectories) for action in pools},
        "all_non_direct_have_anchors": all(row["action"] == "DIRECT" or row["evidence_anchor_count"] >= 1 for row in trajectories),
        "selection_read_judge_scores": False,
        "answer_free": True,
        "trajectory_sha256_before_scoring": sha256(trajectory_path),
        "source_hashes": {str(path): sha256(path) for path in (args.logic_trees, args.items, args.verifier_scores)},
    }
    if not audit["all_non_direct_have_anchors"]:
        raise RuntimeError("non-direct action without an evidence anchor")
    dump(args.output_root / "audit.json", audit)

    judged = {str(row["question_id"]): row for row in jsonl(args.judge_scores)}
    scored = []
    for row in trajectories:
        score = judged[row["question_id"]]
        active_key = "MMR8_score" if row["action"] == "DIRECT" else ("Adaptive12_score" if row["action"] == "LOOK_REGION" else "ExtraGlobal12_score")
        random_key = "MMR8_score" if row["action"] == "DIRECT" else ("Adaptive12_score" if row["random_action"] == "LOOK_REGION" else "ExtraGlobal12_score")
        full_key = "MMR8_score" if row["action"] == "DIRECT" else "ExtraGlobal12_score"
        scored.append({
            "question_id": row["question_id"],
            "a0": float(score["MMR8_score"]),
            "active": float(score[active_key]),
            "random": float(score[random_key]),
            "full_only": float(score[full_key]),
        })
    summary = {"count": len(scored), "metrics": {key: metrics(scored, key) for key in ("a0", "active", "random", "full_only")}}
    for challenger in ("active", "random", "full_only"):
        summary[f"{challenger}_vs_a0"] = {
            "wins": sum(row[challenger] > row["a0"] for row in scored),
            "ties": sum(row[challenger] == row["a0"] for row in scored),
            "losses": sum(row[challenger] < row["a0"] for row in scored),
            "relaxed_delta": summary["metrics"][challenger]["relaxed"] - summary["metrics"]["a0"]["relaxed"],
        }
    summary["judge_scores_loaded_after_frozen_trajectory_sha256"] = audit["trajectory_sha256_before_scoring"]
    summary["not_human_gold"] = True
    dump(args.output_root / "score_summary_existing_judge.json", summary)
    (args.output_root / "SMOKE20_REUSE_EVALUATION_COMPLETE").write_text("complete\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
