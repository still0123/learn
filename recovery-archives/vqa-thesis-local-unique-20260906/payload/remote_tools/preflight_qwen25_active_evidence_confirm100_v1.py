#!/usr/bin/env python3
"""Materialize Confirm-100 arms and count exact DeepSeek reuse/new calls."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values), encoding="utf-8")


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def sha(value: str) -> str:
    return hashlib.sha256(norm(value).encode()).hexdigest()


def load_predictions(root: Path) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    predictions, traces = {}, {}
    for path_name in glob.glob(str(root / "**/a2_prediction.json"), recursive=True):
        path = Path(path_name)
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        predictions[qid] = str(row["prediction"])
        traces[qid] = json.loads((path.parent / "a2_trace.json").read_text(encoding="utf-8"))
    return predictions, traces


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-root", type=Path, required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--extra-root", type=Path, required=True)
    parser.add_argument("--old-expanded-scores", type=Path, required=True)
    parser.add_argument("--old-api-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    master = jsonl(args.confirm_root / "confirm100_master_answer_free.jsonl")
    items = {str(row["question_id"]): row for row in jsonl(args.items)}
    action = {str(row["question_id"]): row for row in master}
    old_scores = {str(row["question_id"]): row for row in jsonl(args.old_expanded_scores)}
    old_api = {(str(row["question_id"]), norm(str(row["candidate_prediction"]))): float(row["score"]) for row in jsonl(args.old_api_results)}
    old_adaptive, _ = load_predictions(args.adaptive_root)
    old_extra, _ = load_predictions(args.extra_root)

    arms, traces = {}, {}
    for name in ("active_region", "active_time", "full_only", "random_region", "random_time"):
        arms[name], traces[name] = load_predictions(args.confirm_root / "inference" / name)
    expected = {"active_region": 53, "active_time": 26, "full_only": 79, "random_region": 34, "random_time": 45}
    if {name: len(values) for name, values in arms.items()} != expected:
        raise RuntimeError("inference arm counts changed")
    for name, rows_by_qid in traces.items():
        for qid, trace in rows_by_qid.items():
            processor = trace["processor_trace"]
            if processor["represented_views"] != 12 or processor["visual_tokens"] != 3992 or processor["secondary_frame_sampling"]:
                raise RuntimeError(f"visual protocol mismatch: {name}/{qid}")

    candidates = []
    for qid in sorted(action):
        row, a0 = action[qid], str(items[qid]["a0_prediction"])
        if row["action"] == "DIRECT":
            active = full = random = a0
        else:
            active = arms["active_region" if row["action"] == "LOOK_REGION" else "active_time"][qid]
            full = arms["full_only"][qid]
            random = arms["random_region" if row["random_action"] == "LOOK_REGION" else "random_time"][qid]
        for method, prediction in (("A0", a0), ("ActiveLook", active), ("FullOnly", full), ("RandomLook", random)):
            candidates.append({
                "question_id": qid,
                "video_id": row["video_id"],
                "method": method,
                "prediction": prediction,
                "prediction_sha256": sha(prediction),
                "action": row["action"] if method == "ActiveLook" else None,
                "answer_free": True,
                "not_human_gold": True,
            })

    score_cache: dict[tuple[str, str], tuple[float, str]] = {}
    for qid in action:
        score_cache[(qid, norm(str(items[qid]["a0_prediction"])))] = (float(old_scores[qid]["MMR8_score"]), "pilot_mmr8_exact")
        score_cache[(qid, norm(old_adaptive[qid]))] = (float(old_scores[qid]["Adaptive12_score"]), "pilot_adaptive_exact")
        score_cache[(qid, norm(old_extra[qid]))] = (float(old_scores[qid]["ExtraGlobal12_score"]), "pilot_extra_exact")
    for key, score in old_api.items():
        score_cache.setdefault(key, (score, "pilot_api_exact"))

    unique = {}
    for row in candidates:
        unique[(row["question_id"], norm(row["prediction"]))] = row
    reused, pending = [], []
    for key, row in sorted(unique.items()):
        if key in score_cache:
            score, source = score_cache[key]
            reused.append({"question_id": key[0], "prediction_sha256": row["prediction_sha256"], "score": score, "score_source": source})
        else:
            pending.append(row)

    a0_by_qid = {qid: norm(str(items[qid]["a0_prediction"])) for qid in action}
    audit = {
        "schema_version": "qwen25_active_evidence_confirm100_preflight_v1",
        "passed": True,
        "question_count": len(action),
        "expanded_slots": len(candidates),
        "unique_question_answers": len(unique),
        "historical_exact_reuses": len(reused),
        "new_api_calls": len(pending),
        "method_text_change_counts": {
            method: sum(row["method"] == method and norm(row["prediction"]) != a0_by_qid[row["question_id"]] for row in candidates)
            for method in ("ActiveLook", "FullOnly", "RandomLook")
        },
        "all_visual_protocols_12views_3992tokens": True,
        "secondary_frame_sampling": False,
        "groundtruth_read": False,
        "api_called": False,
        "not_human_gold": True,
    }
    dump_jsonl(args.output_root / "candidates_answer_free.jsonl", candidates)
    dump_jsonl(args.output_root / "reused_scores.jsonl", reused)
    dump_jsonl(args.output_root / "pending_new_scores.jsonl", pending)
    dump(args.output_root / "preflight.json", audit)
    (args.output_root / "PREFLIGHT_COMPLETE").write_text("complete\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
