#!/usr/bin/env python3
"""Count exact historical score reuse for frozen Confirm-100 gated choices."""

import argparse
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--choices", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    choices = rows(args.choices)
    cache = {(str(row["question_id"]), str(row["prediction_sha256"])): float(row["score"]) for row in rows(args.historical)}
    candidates = []
    for row in choices:
        for method, prediction, digest in (
            ("A0", row["a0_prediction"], __import__("hashlib").sha256(" ".join(row["a0_prediction"].strip().casefold().split()).encode()).hexdigest()),
            ("Gated", row["final_prediction"], row["final_sha256"]),
        ):
            candidates.append({
                "question_id": row["question_id"], "video_id": row["video_id"],
                "method": method, "prediction": prediction, "prediction_sha256": digest,
                "switched": row["switched"], "not_human_gold": True,
            })
    unique = {(row["question_id"], row["prediction_sha256"]): row for row in candidates}
    reused, pending = [], []
    for key, row in sorted(unique.items()):
        if key in cache:
            reused.append({"question_id": key[0], "prediction_sha256": key[1], "score": cache[key]})
        else:
            pending.append(row)
    audit = {
        "schema_version": "qwen25_region_gate_confirm100_judge_preflight_v1",
        "passed": len(candidates) == 200,
        "expanded_slots": 200, "unique_question_answers": len(unique),
        "historical_exact_reuses": len(reused), "new_api_calls": len(pending),
        "switched": sum(row["switched"] for row in choices),
        "api_called": False, "not_human_gold": True,
    }
    write_jsonl(args.output_root / "candidates_answer_free.jsonl", candidates)
    write_jsonl(args.output_root / "reused_scores.jsonl", reused)
    write_jsonl(args.output_root / "pending_new_scores.jsonl", pending)
    (args.output_root / "preflight.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "PREFLIGHT_COMPLETE").write_text("complete\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
