#!/usr/bin/env python3
"""Apply the frozen ReAd-R support gate to CropOrFull12 without references."""

import argparse
import hashlib
import json
from pathlib import Path

TAU = 0.9241418242454529
MARGIN = 0.0


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def normalize(value):
    return " ".join(str(value).casefold().split())


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--a0-scores", type=Path, required=True)
    parser.add_argument("--verifier-shard-root", type=Path, required=True)
    args = parser.parse_args()

    items = {
        str(row["question_id"]): row
        for row in load_jsonl(args.run_root / "dataset/items_answer_free.jsonl")
    }
    a0_scores = {
        str(row["source_question_id"]): row for row in load_jsonl(args.a0_scores)
    }
    a2_scores = {}
    for path in sorted(args.verifier_shard_root.glob("fold_*/scores.jsonl")):
        for row in load_jsonl(path):
            qid = str(row["source_question_id"])
            if qid in a2_scores:
                raise RuntimeError(f"duplicate A2 score: {qid}")
            a2_scores[qid] = row

    predictions = {}
    for path in args.run_root.glob("inference/shard_*/*/a2_prediction.json"):
        predictions[path.parent.name] = json.loads(path.read_text())["prediction"]

    if set(items) != set(a2_scores) or set(items) != set(predictions):
        raise RuntimeError("coverage mismatch")

    rows = []
    for qid, item in items.items():
        prediction = predictions[qid]
        a0_prediction = str(item["a0_prediction"])
        a0_support = float(a0_scores[qid]["support_probability"])
        a2_support = float(a2_scores[qid]["support_probability"])
        changed = normalize(prediction) != normalize(a0_prediction)
        review = a0_support < TAU
        switch = review and changed and a2_support >= a0_support + MARGIN
        rows.append(
            {
                "question_id": qid,
                "video_id": str(item["video_id"]),
                "fold": int(item["fold"]),
                "crop_anchor_count": int(item["crop_or_full_route"]["crop_anchor_count"]),
                "a0_support": a0_support,
                "a2_support": a2_support,
                "support_delta": a2_support - a0_support,
                "answer_changed": changed,
                "review_triggered": review,
                "gate_switched": switch,
                "candidate_prediction": prediction,
                "candidate_prediction_sha256": digest(prediction),
                "a0_prediction": a0_prediction,
            }
        )
    rows.sort(key=lambda row: (row["fold"], row["question_id"]))
    summary = {
        "schema_version": "readr_crop_or_full_gate_v1",
        "passed": len(rows) == 152,
        "reference_answers_read": False,
        "judge_scores_read": False,
        "rows": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "tau": TAU,
        "margin": MARGIN,
        "review_trigger_count": sum(row["review_triggered"] for row in rows),
        "answer_change_count": sum(row["answer_changed"] for row in rows),
        "switch_count": sum(row["gate_switched"] for row in rows),
        "crop_question_count": sum(row["crop_anchor_count"] > 0 for row in rows),
        "crop_switch_count": sum(
            row["gate_switched"] and row["crop_anchor_count"] > 0 for row in rows
        ),
        "rows_detail": rows,
    }
    output_dir = args.run_root / "gate_analysis_v1"
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "rows_detail"}, indent=2))


if __name__ == "__main__":
    main()
