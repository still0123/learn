#!/usr/bin/env python3
"""Build answer-free verifier inputs for the frozen CropOrFull12 candidate."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError("output directory exists")

    predictions = {}
    for path in args.inference_root.glob("shard_*/*/a2_prediction.json"):
        qid = path.parent.name
        if qid in predictions:
            raise RuntimeError(f"duplicate prediction: {qid}")
        predictions[qid] = path.parent

    rows = []
    for item in load_jsonl(args.dataset_dir / "items_answer_free.jsonl"):
        qid = str(item["question_id"])
        fold = int(item["fold"])
        directory = predictions.get(qid)
        if directory is None:
            raise RuntimeError(f"missing prediction: {qid}")
        prediction = json.loads((directory / "a2_prediction.json").read_text())
        trace = json.loads((directory / "a2_trace.json").read_text())
        if not trace.get("parse_valid"):
            raise RuntimeError(f"invalid prediction parse: {qid}")
        rows.append(
            {
                "question_id": f"q{qid}__A2",
                "source_question_id": qid,
                "video_id": str(item["video_id"]),
                "video_path": str(item["video_path"]),
                "question": str(item["question"]),
                "claim": str(prediction["prediction"]),
                "candidate_method": "ReAdR_CropOrFull12_A2",
                "selected_frame_indices": [int(x) for x in item["a0_frame_indices"]],
                "asr_excerpt": str(item.get("a0_asr_excerpt", "")),
                "fold": fold,
            }
        )

    rows.sort(key=lambda row: (row["fold"], row["source_question_id"]))
    args.output_dir.mkdir(parents=True)
    all_path = args.output_dir / "model_inputs_all.jsonl"
    all_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    shard_dir = args.output_dir / "shards"
    shard_dir.mkdir()
    for fold in range(5):
        fold_rows = [row for row in rows if row["fold"] == fold]
        (shard_dir / f"fold_{fold}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in fold_rows)
        )

    audit = {
        "schema_version": "readr_crop_or_full_verifier_inputs_v1",
        "passed": len(rows) == 152 and len(predictions) == 152,
        "row_count": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "fold_counts": dict(Counter(str(row["fold"]) for row in rows)),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "labels_in_model_inputs": False,
        "model_inputs_sha256": sha256(all_path),
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    )
    if not audit["passed"]:
        raise RuntimeError("verifier input audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
