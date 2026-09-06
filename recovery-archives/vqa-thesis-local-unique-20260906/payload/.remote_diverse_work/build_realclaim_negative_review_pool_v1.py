#!/usr/bin/env python3
"""Prepare train-split negative claims for independent visual evidence review."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    args = p.parse_args()
    labels = {row["question_id"]: row for row in load(args.labels)}
    pool, private = [], []
    for row in load(args.inputs):
        label = labels[row["question_id"]]
        if int(label["binary_label"]) != 0:
            continue
        clean = {
            "schema": "adsqa_realclaim_negative_review_input_v1",
            "question_id": row["question_id"], "source_question_id": row["source_question_id"],
            "video_id": row["video_id"], "video_path": row["video_path"],
            "primary_type": row["primary_type"], "claim_type": row["claim_type"],
            "question": row["question"], "claim": row["claim"],
            "asr_excerpt": row.get("asr_excerpt", ""),
            "ocr_present": row.get("ocr_present", False),
            "selected_frame_indices": row["selected_frame_indices"],
        }
        pool.append(clean)
        private.append({"question_id": row["question_id"], **label})
    forbidden = {"binary_label", "label_name", "original_label", "annotation_confidence", "reference_answer"}
    audit = {
        "schema": "adsqa_realclaim_negative_review_pool_audit_v1",
        "rows": len(pool), "unique_videos": len({row["video_id"] for row in pool}),
        "claim_types": dict(Counter(row["claim_type"] for row in pool)),
        "input_supervision_leakage": any(forbidden & set(row) for row in pool),
        "private_labels_separate": True, "not_human_gold": True,
        "passed": len(pool) == 343 and not any(forbidden & set(row) for row in pool),
    }
    write_jsonl(args.output_root / "review_inputs.jsonl", pool)
    write_jsonl(args.output_root / "private_source_labels.jsonl", private)
    (args.output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "manifest.json").write_text(json.dumps({
        "review_inputs_sha256": sha(args.output_root / "review_inputs.jsonl"),
        "private_labels_sha256": sha(args.output_root / "private_source_labels.jsonl"),
        "audit": audit,
    }, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
