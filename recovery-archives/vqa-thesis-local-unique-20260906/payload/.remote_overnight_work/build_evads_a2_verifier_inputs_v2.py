#!/usr/bin/env python3
"""Build answer-free RealClaim inputs for variable-size E-VAds A2 outputs."""

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-a2-method", required=True)
    parser.add_argument("--candidate-method", required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    items = load_jsonl(args.dataset_dir / "items_answer_free.jsonl")
    if not items:
        raise RuntimeError("A2 dataset is empty")
    rows: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for item in items:
        qid = str(item["question_id"])
        fold = int(item["fold"])
        item_dir = args.inference_root / f"fold_{fold}" / qid
        prediction_path = item_dir / "a2_prediction.json"
        trace_path = item_dir / "a2_trace.json"
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if prediction.get("method") != args.expected_a2_method:
            raise RuntimeError(f"unexpected A2 method for {qid}")
        if not trace.get("parse_valid"):
            raise RuntimeError(f"A2 parse failed for {qid}")
        rows.append({
            "question_id": f"q{qid}__A2",
            "source_question_id": qid,
            "video_id": str(item["video_id"]),
            "video_path": str(item["video_path"]),
            "question": str(item["question"]),
            "claim": str(prediction["prediction"]),
            "candidate_method": args.candidate_method,
            "selected_frame_indices": [
                int(value) for value in item["a0_frame_indices"]
            ],
            "asr_excerpt": str(item.get("a0_asr_excerpt", "")),
            "fold": fold,
        })
        source_hashes[qid] = sha256_file(prediction_path)
    rows.sort(key=lambda row: (int(row["fold"]), str(row["source_question_id"])))
    fold_counts = Counter(int(row["fold"]) for row in rows)

    args.output_dir.mkdir(parents=True, exist_ok=False)
    all_path = args.output_dir / "model_inputs_all.jsonl"
    write_jsonl(all_path, rows)
    for fold in range(5):
        write_jsonl(
            args.output_dir / "shards" / f"fold_{fold}.jsonl",
            [row for row in rows if int(row["fold"]) == fold],
        )
    audit = {
        "schema_version": "evads_a2_verifier_input_audit_v2",
        "passed": (
            len(rows) == len(items)
            and all(len(row["selected_frame_indices"]) == 8 for row in rows)
            and sum(fold_counts.values()) == len(rows)
        ),
        "row_count": len(rows),
        "video_count": len({str(row["video_id"]) for row in rows}),
        "fold_counts": dict(sorted(fold_counts.items())),
        "all_have_eight_frozen_verifier_views": True,
        "candidate_answers_read": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "labels_in_model_inputs": False,
        "model_inputs_sha256": sha256_file(all_path),
        "source_prediction_sha256": source_hashes,
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: value
        for key, value in audit.items()
        if key != "source_prediction_sha256"
    }, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise RuntimeError("A2 verifier input audit failed")


if __name__ == "__main__":
    main()
