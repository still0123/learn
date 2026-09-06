#!/usr/bin/env python3
"""Count exact historical score reuse for the 20-item regenerated-answer smoke."""

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--historical-scores", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    source = rows(args.root / "inputs.jsonl")
    cache = {
        (str(row["question_id"]), str(row["prediction_sha256"])): float(row["score"])
        for row in rows(args.historical_scores)
    }
    candidates = []
    for item in source:
        qid = str(item["question_id"])
        regenerated = json.loads((args.root / "inference" / qid / "a2_prediction.json").read_text())["prediction"]
        for method, prediction in (("A0", str(item["a0_prediction"])), ("ASRTemporal", regenerated)):
            candidates.append({
                "question_id": qid,
                "video_id": str(item["video_id"]),
                "method": method,
                "prediction": prediction,
                "prediction_sha256": sha(prediction),
                "answer_free": True,
                "not_human_gold": True,
            })
    unique = {(row["question_id"], row["prediction_sha256"]): row for row in candidates}
    reused, pending = [], []
    for key, row in sorted(unique.items()):
        if key in cache:
            reused.append({"question_id": key[0], "prediction_sha256": key[1], "score": cache[key]})
        else:
            pending.append(row)
    audit = {
        "schema_version": "qwen25_temporal_asr_regenerate_smoke20_preflight_v1",
        "passed": len(candidates) == 40,
        "question_count": 20,
        "expanded_slots": 40,
        "unique_question_answers": len(unique),
        "historical_exact_reuses": len(reused),
        "new_api_calls": len(pending),
        "regenerated_text_changes": sum(
            norm(candidates[index + 1]["prediction"]) != norm(candidates[index]["prediction"])
            for index in range(0, 40, 2)
        ),
        "groundtruth_read": False,
        "api_called": False,
        "not_human_gold": True,
    }
    write_jsonl(args.output_root / "candidates_answer_free.jsonl", candidates)
    write_jsonl(args.output_root / "reused_scores.jsonl", reused)
    write_jsonl(args.output_root / "pending_new_scores.jsonl", pending)
    (args.output_root / "preflight.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "PREFLIGHT_COMPLETE").write_text("complete\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
