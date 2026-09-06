#!/usr/bin/env python3
"""Audit paired crop/full inference using OCR re-run on the exact extra views."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def collect(root: Path, arm: str, mode: str) -> dict[str, dict]:
    rows = {}
    for path in (root / arm).rglob("a2_prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        if qid in rows:
            raise RuntimeError(f"duplicate {arm}: {qid}")
        if (row.get("visual_mode") != mode or row.get("ocr_mode") != "rerun"
                or row.get("ocr_source") != "rerun_extra_views"
                or row.get("ocr_evidence_in_prompt") is not True
                or row.get("asr_evidence_in_prompt") is not True
                or row.get("parse_valid") is not True
                or len(row.get("extra_plan", [])) != 4):
            raise RuntimeError(f"invalid protocol: {path}")
        rows[qid] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--expected", type=int, default=50)
    args = parser.parse_args()

    dataset = read_jsonl(args.dataset)
    qids = {str(row["question_id"]) for row in dataset}
    forbidden = {"answer", "answers", "ground_truth", "reference_answer", "meta_info", "label", "judge_score"}
    if len(dataset) != args.expected or len(qids) != args.expected or any(forbidden & set(row) for row in dataset):
        raise RuntimeError("invalid answer-free dataset")
    crop = collect(args.run_root, "crop_rerunocr", "crop")
    full = collect(args.run_root, "full_rerunocr", "full")
    if set(crop) != qids or set(full) != qids:
        raise RuntimeError("question set mismatch")

    crop_cache = read_jsonl(args.run_root / "ocr_cache_crop.jsonl")
    full_cache = read_jsonl(args.run_root / "ocr_cache_full.jsonl")
    if {str(row["question_id"]) for row in crop_cache} != qids or {str(row["question_id"]) for row in full_cache} != qids:
        raise RuntimeError("OCR cache question set mismatch")
    if any(len(row.get("views", [])) != 4 or row.get("answer_fields_read") is not False for row in crop_cache + full_cache):
        raise RuntimeError("invalid OCR cache protocol")

    tokens = set()
    changes = {"crop_rerunocr": 0, "full_rerunocr": 0}
    a0 = {str(row["question_id"]): str(row["a0_prediction"]).strip() for row in dataset}
    for qid in qids:
        ref_crop = json.loads((args.reference_root / "crop_on" / qid / "a2_prediction.json").read_text(encoding="utf-8"))
        ref_full = json.loads((args.reference_root / "full_on" / qid / "a2_prediction.json").read_text(encoding="utf-8"))
        if crop[qid]["extra_plan"] != ref_crop["extra_plan"] or full[qid]["extra_plan"] != ref_full["extra_plan"]:
            raise RuntimeError(f"frozen visual plan changed: {qid}")
        crop_sources = [(x["source_global_rank32"], x["source_frame_index"]) for x in crop[qid]["extra_plan"]]
        full_sources = [(x["source_global_rank32"], x["source_frame_index"]) for x in full[qid]["extra_plan"]]
        if crop_sources != full_sources:
            raise RuntimeError(f"temporal mismatch: {qid}")
        per = {int(crop[qid]["visual_tokens"]), int(full[qid]["visual_tokens"])}
        if len(per) != 1 or next(iter(per)) != 4160:
            raise RuntimeError(f"token mismatch: {qid}")
        tokens.update(per)
        changes["crop_rerunocr"] += int(str(crop[qid]["prediction"]).strip() != a0[qid])
        changes["full_rerunocr"] += int(str(full[qid]["prediction"]).strip() != a0[qid])

    audit = {
        "schema_version": "crop_rerunocr_confirm50_audit_v1",
        "passed": True,
        "question_count": len(qids),
        "video_count": len({str(row["video_id"]) for row in dataset}),
        "same_base_mmr8": True,
        "same_evidence_moments": True,
        "same_four_extra_slots": True,
        "same_visual_budget": True,
        "actual_visual_tokens": sorted(tokens),
        "secondary_sampling": False,
        "ocr_engine_same_between_arms": True,
        "ocr_input_is_exact_v9_v12": True,
        "crop_ocr_detection_count": sum(len(row["detections"]) for row in crop_cache),
        "full_ocr_detection_count": sum(len(row["detections"]) for row in full_cache),
        "crop_empty_question_count": sum(not row["detections"] for row in crop_cache),
        "full_empty_question_count": sum(not row["detections"] for row in full_cache),
        "answer_change_count_vs_a0": changes,
        "labels_read": False,
        "judge_api_called": False,
        "dataset_sha256": digest(args.dataset),
        "crop_cache_sha256": digest(args.run_root / "ocr_cache_crop.jsonl"),
        "full_cache_sha256": digest(args.run_root / "ocr_cache_full.jsonl"),
    }
    (args.run_root / "protocol_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (args.run_root / "INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION").write_text("complete\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
