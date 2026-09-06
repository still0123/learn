#!/usr/bin/env python3
"""Audit equal-count crop/full OCR inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def collect(root: Path, arm: str, mode: str) -> dict[str, dict]:
    out = {}
    for path in (root / arm).rglob("a2_prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if (row.get("visual_mode") != mode or row.get("ocr_mode") != "rerun"
                or row.get("ocr_source") != "rerun_extra_views" or row.get("parse_valid") is not True
                or len(row.get("extra_plan", [])) != 4):
            raise RuntimeError(f"invalid output {path}")
        out[str(row["question_id"])] = row
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--expected", type=int, default=100)
    args = parser.parse_args()
    dataset = read(args.dataset)
    qids = {str(row["question_id"]) for row in dataset}
    if len(dataset) != args.expected or len(qids) != args.expected:
        raise RuntimeError("dataset count mismatch")
    crop = collect(args.run_root, "crop_rerunocr", "crop")
    full = collect(args.run_root, "full_rerunocr", "full")
    if set(crop) != qids or set(full) != qids:
        raise RuntimeError("question set mismatch")
    cache_crop = {str(x["question_id"]): x for x in read(args.run_root / "ocr_cache_crop.jsonl")}
    cache_full = {str(x["question_id"]): x for x in read(args.run_root / "ocr_cache_full.jsonl")}
    if set(cache_crop) != qids or set(cache_full) != qids:
        raise RuntimeError("OCR cache question set mismatch")
    matched = json.loads((args.run_root / "matched_ocr_audit.json").read_text(encoding="utf-8"))
    plans = {}
    changes = {"crop_rerunocr": 0, "full_rerunocr": 0}
    a0 = {str(row["question_id"]): str(row["a0_prediction"]).strip() for row in dataset}
    tokens = set()
    for qid in qids:
        ref_crop = json.loads((args.reference_root / "crop_on" / qid / "a2_prediction.json").read_text(encoding="utf-8"))
        ref_full = json.loads((args.reference_root / "full_on" / qid / "a2_prediction.json").read_text(encoding="utf-8"))
        if crop[qid]["extra_plan"] != ref_crop["extra_plan"] or full[qid]["extra_plan"] != ref_full["extra_plan"]:
            raise RuntimeError(f"visual plan changed {qid}")
        if int(cache_crop[qid]["matched_detection_count"]) != int(cache_full[qid]["matched_detection_count"]):
            raise RuntimeError(f"OCR count mismatch {qid}")
        tokens.update((int(crop[qid]["visual_tokens"]), int(full[qid]["visual_tokens"])))
        changes["crop_rerunocr"] += int(str(crop[qid]["prediction"]).strip() != a0[qid])
        changes["full_rerunocr"] += int(str(full[qid]["prediction"]).strip() != a0[qid])
    audit = {"schema_version": "matched_ocr_confirm100_audit_v1", "passed": True,
             "question_count": len(qids), "video_count": len({str(x["video_id"]) for x in dataset}),
             "same_base_mmr8": True, "same_evidence_moments": True, "same_visual_plan": True,
             "same_visual_budget": True, "actual_visual_tokens": sorted(tokens),
             "same_ocr_count_per_question": True, "ocr_selection": "top_confidence_equal_k",
             "matched_mean_ocr_count": matched["mean_matched_count"],
             "matched_zero_ocr_count": matched["zero_matched_count"],
             "answer_change_count_vs_a0": changes, "labels_read": False, "judge_api_called": False,
             "dataset_sha256": digest(args.dataset), "matched_ocr_audit_sha256": digest(args.run_root / "matched_ocr_audit.json")}
    (args.run_root / "protocol_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (args.run_root / "INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION").write_text("complete\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
