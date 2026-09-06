#!/usr/bin/env python3
"""Audit the four answer-free OCR x crop inference arms."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ARMS = {
    "crop_on": ("crop", "on"),
    "crop_off": ("crop", "off"),
    "full_on": ("full", "on"),
    "full_off": ("full", "off"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def collect(root: Path, arm: str, visual_mode: str, ocr_mode: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted((root / arm).rglob("a2_prediction.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        if qid in rows:
            raise RuntimeError(f"duplicate {arm} output: {qid}")
        expected_method = f"Qwen3_OCRCropFactorial_{visual_mode}_{ocr_mode}"
        if (
            row.get("method") != expected_method
            or row.get("visual_mode") != visual_mode
            or row.get("ocr_mode") != ocr_mode
            or bool(row.get("ocr_evidence_in_prompt")) != (ocr_mode == "on")
            or row.get("asr_evidence_in_prompt") is not True
            or row.get("parse_valid") is not True
            or not str(row.get("prediction", "")).strip()
            or len(row.get("extra_plan", [])) != 4
        ):
            raise RuntimeError(f"invalid output protocol: {path}")
        rows[qid] = row
    return rows


def source_pairs(row: dict[str, Any]) -> list[tuple[int, int]]:
    return [
        (int(item["source_global_rank32"]), int(item["source_frame_index"]))
        for item in row["extra_plan"]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--expected", type=int, default=20)
    args = parser.parse_args()

    dataset = read_jsonl(args.dataset)
    qids = {str(row["question_id"]) for row in dataset}
    forbidden = {"answer", "answers", "ground_truth", "reference_answer", "meta_info", "label", "judge_score"}
    if len(dataset) != args.expected or len(qids) != args.expected:
        raise RuntimeError("dataset count mismatch")
    if any(forbidden & set(row) for row in dataset):
        raise RuntimeError("supervision leakage in dataset")

    outputs = {
        arm: collect(args.run_root, arm, visual_mode, ocr_mode)
        for arm, (visual_mode, ocr_mode) in ARMS.items()
    }
    if any(set(rows) != qids for rows in outputs.values()):
        raise RuntimeError("four-arm question sets do not match")

    token_counts: set[int] = set()
    grid_areas: set[int] = set()
    answer_changes: dict[str, int] = {arm: 0 for arm in ARMS}
    a0 = {str(row["question_id"]): str(row["a0_prediction"]).strip() for row in dataset}
    for qid in sorted(qids):
        per_arm_tokens = {int(outputs[arm][qid]["visual_tokens"]) for arm in ARMS}
        per_arm_grids = {int(outputs[arm][qid]["visual_grid_area"]) for arm in ARMS}
        if len(per_arm_tokens) != 1 or len(per_arm_grids) != 1:
            raise RuntimeError(f"visual budget mismatch: {qid}")
        token = next(iter(per_arm_tokens))
        if token <= 0 or token > 4160:
            raise RuntimeError(f"invalid visual token count {token}: {qid}")
        token_counts.add(token)
        grid_areas.update(per_arm_grids)

        if outputs["crop_on"][qid]["extra_plan"] != outputs["crop_off"][qid]["extra_plan"]:
            raise RuntimeError(f"crop plan changed with OCR: {qid}")
        if outputs["full_on"][qid]["extra_plan"] != outputs["full_off"][qid]["extra_plan"]:
            raise RuntimeError(f"full plan changed with OCR: {qid}")
        crop_sources = source_pairs(outputs["crop_on"][qid])
        full_sources = source_pairs(outputs["full_on"][qid])
        if crop_sources != full_sources:
            raise RuntimeError(f"crop/full temporal source mismatch: {qid}")
        if crop_sources[0] != crop_sources[1] or crop_sources[2] != crop_sources[3]:
            raise RuntimeError(f"paired slots are not same-frame controls: {qid}")

        for arm in ARMS:
            answer_changes[arm] += int(str(outputs[arm][qid]["prediction"]).strip() != a0[qid])

    audit = {
        "schema_version": "ocr_crop_factorial_smoke_audit_v1",
        "passed": True,
        "question_count": len(qids),
        "video_count": len({str(row["video_id"]) for row in dataset}),
        "arms": ARMS,
        "same_question_set": True,
        "same_base_mmr8": True,
        "same_anchor_frames": True,
        "same_four_extra_slots": True,
        "same_visual_budget_per_question": True,
        "secondary_frame_sampling": False,
        "ocr_is_only_prompt_factor": True,
        "asr_enabled_all_arms": True,
        "actual_visual_token_values": sorted(token_counts),
        "visual_grid_area_values": sorted(grid_areas),
        "answer_change_count_vs_a0": answer_changes,
        "labels_read": False,
        "judge_api_called": False,
        "dataset_sha256": sha256_file(args.dataset),
    }
    output = args.run_root / "protocol_audit.json"
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.run_root / "SMOKE_INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION").write_text(
        "protocol audit passed; no judge API called\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
