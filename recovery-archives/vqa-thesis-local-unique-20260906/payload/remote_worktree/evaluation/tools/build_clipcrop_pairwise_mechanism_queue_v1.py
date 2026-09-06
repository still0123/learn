#!/usr/bin/env python3
"""Build an auditable review queue for Raw40/CLIPCrop40 score changes."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


OCR_TERMS = (
    "brand",
    "logo",
    "text",
    "word",
    "written",
    "caption",
    "sign",
    "label",
    "number",
    "price",
    "discount",
    "percentage",
    "website",
    "url",
)
AUDIO_TERMS = (
    "voiceover",
    "speaker",
    "narrator",
    "spoken",
    "say",
    "said",
    "hear",
    "sound",
    "music",
    "audio",
)
VISUAL_DETAIL_TERMS = (
    "color",
    "colour",
    "wearing",
    "holding",
    "object",
    "product",
    "package",
    "screen",
    "shown",
    "visual",
    "appear",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-results", required=True)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--crop-root", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_artifacts(root: Path, filename: str) -> dict[str, dict[str, Any]]:
    rows = {}
    for path in root.rglob(filename):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        if qid in rows:
            raise ValueError(f"duplicate {filename} for question {qid}")
        rows[qid] = row
    return rows


def question_intent(question: str) -> str:
    normalized = " ".join(extract_question_text(question).lower().split())
    if any(term in normalized for term in OCR_TERMS):
        return "ocr_brand_text"
    if any(term in normalized for term in AUDIO_TERMS):
        return "audio_speech"
    if any(term in normalized for term in VISUAL_DETAIL_TERMS):
        return "visual_object_detail"
    if normalized.startswith("why") or "how does" in normalized:
        return "narrative_strategy"
    return "other"


def extract_question_text(value: str) -> str:
    marker = "question:"
    lower = value.lower()
    index = lower.rfind(marker)
    extracted = value[index + len(marker) :].strip() if index >= 0 else value.strip()
    if not extracted:
        raise ValueError("question text is empty after removing the Voiceover prefix")
    return extracted


def qid_key(value: str) -> tuple[int, str]:
    try:
        return (0, f"{int(value):012d}")
    except ValueError:
        return (1, value)


def main() -> None:
    args = parse_args()
    judge_path = Path(args.judge_results).resolve()
    groundtruth_path = Path(args.groundtruth).resolve()
    raw_root = Path(args.raw_root).resolve()
    crop_root = Path(args.crop_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    judge_rows = load_jsonl(judge_path)
    scores = {
        (str(row["method"]), str(row["question_id"])): float(row["score"])
        for row in judge_rows
    }
    groundtruth_rows = json.loads(groundtruth_path.read_text(encoding="utf-8"))
    groundtruth = {str(row["question_id"]): row for row in groundtruth_rows}
    raw_predictions = load_artifacts(raw_root, "prediction.json")
    crop_predictions = load_artifacts(crop_root, "prediction.json")
    raw_evidence = load_artifacts(raw_root, "evidence.json")
    crop_evidence = load_artifacts(crop_root, "evidence.json")
    shared_ids = set(raw_predictions) & set(crop_predictions)
    if len(shared_ids) != 500:
        raise ValueError(f"expected 500 paired predictions, found {len(shared_ids)}")

    queue = []
    transition_counts = Counter()
    intent_counts = Counter()
    for qid in sorted(shared_ids, key=qid_key):
        raw_score = scores[("B_Raw40", qid)]
        crop_score = scores[("D_CLIPCrop40", qid)]
        if raw_score == crop_score:
            continue
        direction = "clip_gain" if crop_score > raw_score else "clip_harm"
        transition = f"{raw_score:g}->{crop_score:g}"
        gt = groundtruth[qid]
        source_question = str(gt["question"])
        question = extract_question_text(source_question)
        intent = question_intent(source_question)
        transition_counts[f"{direction}:{transition}"] += 1
        intent_counts[f"{direction}:{intent}"] += 1
        local_views = [
            {
                "local_rank": int(view["local_rank"]),
                "source_global_rank": int(view["source_global_rank"]),
                "source_frame_index": int(view["source_frame_index"]),
                "bbox_norm": [float(value) for value in view["bbox_norm"]],
                "crop_mode": str(view.get("crop_mode", "")),
            }
            for view in crop_evidence[qid]["visual_plan"]
            if view.get("view_type") == "local"
        ]
        queue.append(
            {
                "schema_version": "clipcrop_pairwise_mechanism_review_v1",
                "question_id": qid,
                "video_id": str(gt.get("video", raw_predictions[qid].get("video", ""))),
                "question": question,
                "source_question_sha256": hashlib.sha256(source_question.encode("utf-8")).hexdigest(),
                "question_type": gt.get("question_type", []),
                "automatic_question_intent": intent,
                "reference_answer": str(gt["answer"]),
                "raw_prediction": str(raw_predictions[qid]["prediction"]),
                "clipcrop_prediction": str(crop_predictions[qid]["prediction"]),
                "raw_score": raw_score,
                "clipcrop_score": crop_score,
                "score_delta_clip_minus_raw": crop_score - raw_score,
                "direction": direction,
                "transition": transition,
                "clipcrop_local_views": local_views,
                "raw_latency_seconds": float(raw_evidence[qid].get("latency_seconds", 0.0)),
                "clipcrop_latency_seconds": float(crop_evidence[qid].get("latency_seconds", 0.0)),
                "review": {
                    "mechanism_label": "",
                    "raw_failure_reason": "",
                    "clip_gain_or_harm_reason": "",
                    "global_context_effect": "",
                    "review_confidence": "",
                    "review_notes": "",
                    "review_source": "",
                },
                "review_status": "pending",
                "not_human_gold": True,
            }
        )

    queue.sort(
        key=lambda row: (
            0 if row["direction"] == "clip_gain" else 1,
            -abs(float(row["score_delta_clip_minus_raw"])),
            qid_key(str(row["question_id"])),
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    queue_path = output_dir / "pairwise_mechanism_review_queue_v1.jsonl"
    queue_path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in queue),
        encoding="utf-8",
    )
    direction_counts = Counter(row["direction"] for row in queue)
    audit = {
        "schema_version": "clipcrop_pairwise_mechanism_queue_audit_v1",
        "passed": (
            len(queue) == 181
            and direction_counts["clip_gain"] == 104
            and direction_counts["clip_harm"] == 77
            and all(len(row["clipcrop_local_views"]) == 8 for row in queue)
        ),
        "paired_question_count": len(shared_ids),
        "changed_score_count": len(queue),
        "direction_counts": dict(sorted(direction_counts.items())),
        "transition_counts": dict(sorted(transition_counts.items())),
        "automatic_intent_counts": dict(sorted(intent_counts.items())),
        "review_status_counts": dict(Counter(row["review_status"] for row in queue)),
        "not_human_gold": True,
        "judge_results_sha256": sha256_file(judge_path),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "queue_sha256": sha256_file(queue_path),
    }
    audit_path = output_dir / "audit.json"
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
