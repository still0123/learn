#!/usr/bin/env python3
"""Build an answer-free OCR-box routed Smoke-20 from ReAd-R Calibration100."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "answers",
    "ground_truth",
    "reference_answer",
    "meta_info",
    "judge_score",
    "label",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--slots", type=int, default=2, choices=(2, 4))
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expand_box(box: list[float]) -> list[float]:
    left, top, right, bottom = [float(value) for value in box]
    width = right - left
    height = bottom - top
    side = min(0.58, max(0.28, 2.5 * max(width, height)))
    center_x = (left + right) / 2.0
    center_y = (top + bottom) / 2.0
    out_left = min(max(center_x - side / 2.0, 0.0), 1.0 - side)
    out_top = min(max(center_y - side / 2.0, 0.0), 1.0 - side)
    return [out_left, out_top, out_left + side, out_top + side]


def valid_ocr(item: dict[str, Any]) -> bool:
    box = item.get("bbox_norm")
    if not isinstance(box, list) or len(box) != 4:
        return False
    left, top, right, bottom = [float(value) for value in box]
    return (
        0.0 <= left < right <= 1.0
        and 0.0 <= top < bottom <= 1.0
        and float(item.get("confidence", 0.0)) >= 0.90
        and int(item.get("cross_frame_count", 0)) >= 2
        and bool(str(item.get("text", "")).strip())
    )


def ocr_score(item: dict[str, Any]) -> float:
    left, top, right, bottom = [float(value) for value in item["bbox_norm"]]
    area = max((right - left) * (bottom - top), 1e-6)
    return (
        8.0 * int(item.get("question_overlap", 0) > 0)
        + 1.5 * float(item.get("confidence", 0.0))
        + math.log1p(int(item.get("cross_frame_count", 0)))
        + min(2.0, -math.log(area)) * 0.25
    )


def choose_slots(row: dict[str, Any], slot_count: int) -> list[dict[str, Any]]:
    candidates = sorted(
        (item for item in row.get("ocr_evidence", []) if valid_ocr(item)),
        key=lambda item: (-ocr_score(item), int(item["frame_index"]), str(item["text"])),
    )
    selected: list[dict[str, Any]] = []
    frame_uses: dict[int, int] = {}
    base_frames = {int(value) for value in row["a0_frame_indices"]}
    for allow_base in (False, True):
        for item in candidates:
            frame_index = int(item["frame_index"])
            max_per_frame = 1 if slot_count == 2 else 2
            if frame_uses.get(frame_index, 0) >= max_per_frame or ((frame_index in base_frames) != allow_base):
                continue
            selected.append({
                "slot_index": len(selected),
                "source_frame_index": frame_index,
                "timestamp_sec": float(item["timestamp_sec"]),
                "bbox_norm": expand_box(item["bbox_norm"]),
                "raw_ocr_bbox_norm": [float(value) for value in item["bbox_norm"]],
                "ocr_id": str(item["id"]),
                "ocr_text": str(item["text"]),
                "ocr_confidence": float(item["confidence"]),
                "question_overlap": int(item.get("question_overlap", 0)),
                "cross_frame_count": int(item.get("cross_frame_count", 0)),
                "selection_score": ocr_score(item),
                "source_already_in_mmr8": frame_index in base_frames,
            })
            frame_uses[frame_index] = frame_uses.get(frame_index, 0) + 1
            if len(selected) == slot_count:
                if len(frame_uses) >= 2:
                    return selected
                selected.pop()
                frame_uses[frame_index] -= 1
    return selected


def main() -> None:
    args = parse_args()
    rows = [
        json.loads(line)
        for line in args.input_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(FORBIDDEN & set(row) for row in rows):
        raise RuntimeError("source contains forbidden answer or evaluation fields")

    eligible = []
    for row in rows:
        slots = choose_slots(row, args.slots)
        if len(slots) != args.slots or not any(slot["question_overlap"] > 0 for slot in slots):
            continue
        routed = dict(row)
        routed["ocr_crop_slots"] = slots
        routed["crop_route"] = {
            "eligible": True,
            "rule": "question_overlap_and_reliable_ocr_box_v1",
            "score": sum(slot["selection_score"] for slot in slots),
        }
        eligible.append(routed)

    eligible.sort(
        key=lambda row: (
            -float(row["crop_route"]["score"]),
            hashlib.sha256(str(row["question_id"]).encode("utf-8")).hexdigest(),
        )
    )
    eligible_question_count = len(eligible)
    eligible_by_video = []
    seen_videos: set[str] = set()
    for row in eligible:
        video_id = str(row["video_id"])
        if video_id in seen_videos:
            continue
        seen_videos.add(video_id)
        eligible_by_video.append(row)
    selected = eligible_by_video[: args.count]
    if len(selected) != args.count:
        raise RuntimeError(f"need {args.count} eligible rows, found {len(selected)}")
    if len({row["video_id"] for row in selected}) != len(selected):
        raise RuntimeError("Smoke-20 must contain one question per video")

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in selected),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "readr_ocrbox_routed_smoke20_v1",
        "source_count": len(rows),
        "eligible_question_count": eligible_question_count,
        "eligible_video_count": len(eligible_by_video),
        "selected_count": len(selected),
        "selected_video_count": len({row["video_id"] for row in selected}),
        "slot_count_per_question": args.slots,
        "selection_uses_answers": False,
        "selection_uses_judge_scores": False,
        "route_rule": f"at least one question-overlap OCR; {args.slots} reliable OCR regions across at least two frames",
        "crop_rule": "OCR bbox center with 2.5x context, square side clamped to [0.28, 0.58]",
        "source_sha256": sha256_file(args.input_jsonl),
        "output_sha256": sha256_file(args.output_jsonl),
        "question_ids": [row["question_id"] for row in selected],
    }
    args.audit_json.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
