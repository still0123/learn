#!/usr/bin/env python3
"""Convert audited Candidate-B pairs into leakage-free LoRA inputs and labels."""

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


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    raw_inputs = load(args.source_root / "model_inputs.jsonl")
    raw_labels = {row["input_id"]: row for row in load(args.source_root / "labels.jsonl")}
    raw_pairs = load(args.source_root / "pairs.jsonl")
    inputs, labels = [], []
    for row in raw_inputs:
        input_id = str(row["input_id"])
        label = raw_labels[input_id]
        inputs.append({
            "schema": "adsqa_same_video_hardneg_lora_input_v1",
            "question_id": input_id,
            "source_question_id": str(row["source_question_id"]),
            "video_id": str(row["video_id"]),
            "video_path": str(row["video_path"]),
            "primary_type": "hard_negative",
            "claim_type": str(row["claim_type"]),
            "question": str(row["question"]),
            "claim": str(row["atomic_claim"]),
            "asr_excerpt": str(row.get("asr_excerpt", "")),
            "ocr_present": row.get("claim_type") == "ocr",
            "selected_frame_indices": [int(value) for value in row["frame_indices"]],
        })
        labels.append({
            "schema": "adsqa_same_video_hardneg_lora_label_v1",
            "question_id": input_id,
            "binary_label": int(label["label"]),
            "label_name": "supported" if int(label["label"]) else "not_supported",
            "original_label": str(label["evidence_state"]),
            "annotation_confidence": 0.9,
            "label_policy": "same_video_anchor_exclusion_synthetic_not_human_gold",
            "not_human_gold": True,
        })
    pair_ids = {row["pair_id"] for row in raw_pairs}
    negative_valid = all((row.get("negative_plan") or {}).get("valid") is True for row in raw_pairs)
    audit = {
        "schema": "adsqa_same_video_hardneg_lora_audit_v1",
        "rows": len(inputs), "pairs": len(pair_ids),
        "unique_videos": len({row["video_id"] for row in inputs}),
        "label_counts": dict(Counter(row["label_name"] for row in labels)),
        "claim_type_counts": dict(Counter(row["claim_type"] for row in inputs)),
        "negative_plans_valid": negative_valid,
        "input_supervision_leakage": any("label" in row or "evidence_state" in row for row in inputs),
        "not_human_gold": True,
        "passed": len(inputs) == 180 and len(pair_ids) == 90 and negative_valid,
    }
    write_jsonl(args.output_root / "inputs.jsonl", inputs)
    write_jsonl(args.output_root / "labels.jsonl", labels)
    (args.output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "manifest.json").write_text(json.dumps({
        "schema": "adsqa_same_video_hardneg_lora_manifest_v1",
        "inputs_sha256": digest(args.output_root / "inputs.jsonl"),
        "labels_sha256": digest(args.output_root / "labels.jsonl"), "audit": audit,
    }, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
