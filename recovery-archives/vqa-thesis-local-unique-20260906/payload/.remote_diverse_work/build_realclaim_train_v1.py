#!/usr/bin/env python3
"""Build a leakage-audited weakly supervised RealClaim training set."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    inputs = load_jsonl(args.inputs)
    claims = {str(row["claim_id"]): row for row in load_jsonl(args.claims)}
    protected = {str(row["video_id"]) for row in inputs if row.get("split") in {"calibration", "development"}}
    model_inputs, labels = [], []
    forbidden = {"label", "reference_answer", "model_answer", "annotation_confidence", "annotation_rationale"}
    for row in inputs:
        if row.get("split") != "train":
            continue
        claim = claims[str(row["question_id"])]
        clean = {
            "schema": "adsqa_realclaim_train_input_v1",
            "question_id": str(row["question_id"]),
            "source_question_id": str(row["source_question_id"]),
            "video_id": str(row["video_id"]),
            "video_path": str(row["video_path"]),
            "primary_type": str(row["primary_type"]),
            "claim_type": str(claim.get("claim_type", "other")),
            "question": str(row["question"]),
            "claim": str(row["claim"]),
            "asr_excerpt": str(row.get("asr_excerpt", "")),
            "ocr_present": bool(row.get("ocr_present", False)),
            "selected_frame_indices": [int(value) for value in row["selected_frame_indices"]],
        }
        if forbidden & set(clean):
            raise RuntimeError(f"supervision leakage in input {clean['question_id']}")
        original = str(claim["label"])
        labels.append({
            "schema": "adsqa_realclaim_train_label_v1",
            "question_id": clean["question_id"],
            "binary_label": 1 if original == "supported" else 0,
            "label_name": "supported" if original == "supported" else "not_supported",
            "original_label": original,
            "annotation_confidence": float(claim.get("annotation_confidence", 0.5)),
            "label_policy": "reference_answer_derived_weak_supervision_not_human_gold",
            "not_human_gold": True,
        })
        model_inputs.append(clean)
    videos = {row["video_id"] for row in model_inputs}
    label_counts = Counter(row["label_name"] for row in labels)
    audit = {
        "schema": "adsqa_realclaim_train_audit_v1",
        "rows": len(model_inputs), "unique_questions": len({row["source_question_id"] for row in model_inputs}),
        "unique_videos": len(videos), "label_counts": dict(label_counts),
        "claim_type_counts": dict(Counter(row["claim_type"] for row in model_inputs)),
        "primary_type_counts": dict(Counter(row["primary_type"] for row in model_inputs)),
        "protected_video_overlap": sorted(videos & protected),
        "input_supervision_leakage": any(forbidden & set(row) for row in model_inputs),
        "inputs_source_sha256": sha256_file(args.inputs), "claims_source_sha256": sha256_file(args.claims),
        "not_human_gold": True,
        "passed": len(model_inputs) == 985 and min(label_counts.values()) >= 300 and not (videos & protected),
    }
    write_jsonl(args.output_root / "inputs.jsonl", model_inputs)
    write_jsonl(args.output_root / "labels.jsonl", labels)
    write_json(args.output_root / "audit.json", audit)
    write_json(args.output_root / "manifest.json", {
        "schema": "adsqa_realclaim_train_manifest_v1",
        "inputs_sha256": sha256_file(args.output_root / "inputs.jsonl"),
        "labels_sha256": sha256_file(args.output_root / "labels.jsonl"),
        "audit": audit,
    })
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
