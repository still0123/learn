#!/usr/bin/env python3
"""Equalize crop/full OCR prompt counts using confidence-only top-K selection."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop-cache", type=Path, required=True)
    parser.add_argument("--full-cache", type=Path, required=True)
    parser.add_argument("--output-crop", type=Path, required=True)
    parser.add_argument("--output-full", type=Path, required=True)
    args = parser.parse_args()
    crop = {str(row["question_id"]): row for row in read(args.crop_cache)}
    full = {str(row["question_id"]): row for row in read(args.full_cache)}
    if set(crop) != set(full):
        raise RuntimeError("cache question sets differ")

    crop_out, full_out, audits = [], [], []
    for qid in sorted(crop):
        crop_items = list(crop[qid].get("detections", []))
        full_items = list(full[qid].get("detections", []))
        k = min(len(crop_items), len(full_items))
        key = lambda item: (-float(item.get("score", 0.0)), str(item.get("view_id", "")), str(item.get("text", "")))
        crop_items = sorted(crop_items, key=key)[:k]
        full_items = sorted(full_items, key=key)[:k]
        crop_out.append({"question_id": qid, "video_id": crop[qid]["video_id"],
                         "visual_mode": "crop", "detections": crop_items,
                         "matched_detection_count": k, "ocr_selection": "top_confidence_equal_k"})
        full_out.append({"question_id": qid, "video_id": full[qid]["video_id"],
                         "visual_mode": "full", "detections": full_items,
                         "matched_detection_count": k, "ocr_selection": "top_confidence_equal_k"})
        audits.append({"question_id": qid, "crop_original_count": len(crop[qid].get("detections", [])),
                       "full_original_count": len(full[qid].get("detections", [])), "matched_count": k})

    for path, rows in ((args.output_crop, crop_out), (args.output_full, full_out)):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    audit = {"schema_version": "matched_ocr_count_v1", "question_count": len(audits),
             "matched_count_distribution": {str(k): sum(x["matched_count"] == k for x in audits) for k in sorted({x["matched_count"] for x in audits})},
             "mean_matched_count": sum(x["matched_count"] for x in audits) / len(audits),
             "zero_matched_count": sum(x["matched_count"] == 0 for x in audits),
             "selection": "per-question min(crop_count, full_count), top confidence, no question/answer text used",
             "crop_input_sha256": digest(args.crop_cache), "full_input_sha256": digest(args.full_cache),
             "answer_fields_read": False}
    audit_path = args.output_crop.with_name("matched_ocr_audit.json")
    audit_path.write_text(json.dumps({**audit, "rows": audits}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
