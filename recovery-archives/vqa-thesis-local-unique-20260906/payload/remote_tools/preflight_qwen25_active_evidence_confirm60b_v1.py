#!/usr/bin/env python3
"""Materialize Confirm-60B A0/Active arms and count exact score reuse."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def sha(value: str) -> str:
    return hashlib.sha256(norm(value).encode()).hexdigest()


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values))


def predictions(root: Path) -> dict[str, str]:
    result = {}
    for path in root.glob("*/a2_prediction.json"):
        row = json.loads(path.read_text())
        result[str(row["question_id"])] = str(row["prediction"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--expanded-scores", type=Path, required=True)
    parser.add_argument("--api-cache", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    master = rows(args.root / "master_answer_free.jsonl")
    items = {str(row["question_id"]): row for row in rows(args.items)}
    scores = {str(row["question_id"]): row for row in rows(args.expanded_scores)}
    time, region = predictions(args.root / "inference" / "time"), predictions(args.root / "inference" / "region")
    if len(master) != 60 or len(time) != 13 or len(region) != 37:
        raise RuntimeError("Confirm-60B inference population changed")
    candidates = []
    for row in master:
        qid = str(row["question_id"])
        a0 = str(items[qid]["a0_prediction"])
        active = a0 if row["action"] == "DIRECT" else (time[qid] if row["action"] == "LOOK_TIME" else region[qid])
        for method, prediction in (("A0", a0), ("ActiveLook", active)):
            candidates.append({
                "question_id": qid, "video_id": row["video_id"], "method": method,
                "prediction": prediction, "prediction_sha256": sha(prediction),
                "action": row["action"], "answer_free": True, "not_human_gold": True,
            })
    cache = {(qid, norm(str(items[qid]["a0_prediction"]))): (float(value["MMR8_score"]), "pilot_mmr8_exact") for qid, value in scores.items() if qid in items}
    for row in rows(args.api_cache):
        cache.setdefault((str(row["question_id"]), norm(str(row["candidate_prediction"]))), (float(row["score"]), "pilot_api_exact"))
    unique = {(row["question_id"], norm(row["prediction"])): row for row in candidates}
    reused, pending = [], []
    for key, row in sorted(unique.items()):
        if key in cache:
            score, source = cache[key]
            reused.append({"question_id": key[0], "prediction_sha256": row["prediction_sha256"], "score": score, "score_source": source})
        else:
            pending.append(row)
    audit = {
        "schema_version": "qwen25_active_evidence_confirm60b_preflight_v1",
        "passed": len(candidates) == 120,
        "question_count": 60, "expanded_slots": 120,
        "unique_question_answers": len(unique),
        "historical_exact_reuses": len(reused), "new_api_calls": len(pending),
        "text_changes": sum(row["method"] == "ActiveLook" and norm(row["prediction"]) != norm(str(items[row["question_id"]]["a0_prediction"])) for row in candidates),
        "api_called": False, "groundtruth_read": False, "not_human_gold": True,
        "limitation": "internal calibration100 partition; not final independent test",
    }
    write_jsonl(args.output_root / "candidates_answer_free.jsonl", candidates)
    write_jsonl(args.output_root / "reused_scores.jsonl", reused)
    write_jsonl(args.output_root / "pending_new_scores.jsonl", pending)
    (args.output_root / "preflight.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "PREFLIGHT_COMPLETE").write_text("complete\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
