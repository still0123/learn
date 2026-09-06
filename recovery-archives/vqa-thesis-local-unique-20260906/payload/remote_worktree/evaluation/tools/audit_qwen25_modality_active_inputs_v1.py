#!/usr/bin/env python3
"""Audit answer-free ASR/OCR eligibility for the modality-active OOF repair."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


OCR_QUERY_TERMS = (
    "brand",
    "logo",
    "text",
    "word",
    "written",
    "caption",
    "subtitle",
    "sign",
    "label",
    "number",
    "price",
    "discount",
    "percentage",
    "url",
    "website",
    "barcode",
)
AUDIO_QUERY_TERMS = (
    "voiceover",
    "speaker",
    "narrator",
    "spoken",
    "say",
    "said",
    "hear",
    "sound",
    "music",
    "dialogue",
    "audio",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--segmented-asr-root", required=True)
    parser.add_argument("--ocr-root", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def extract_question_text(raw: str) -> str:
    marker = "question:"
    lower = raw.lower()
    position = lower.rfind(marker)
    return (raw[position + len(marker) :] if position >= 0 else raw).strip()


def matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    normalized = " ".join(text.lower().split())
    return [term for term in terms if term in normalized]


def usable_asr_segments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    usable = []
    for segment in payload.get("segments", []):
        text = " ".join(str(segment.get("text", "")).split())
        words = segment.get("words", [])
        probabilities = [float(word.get("probability", 0.0)) for word in words]
        mean_probability = sum(probabilities) / len(probabilities) if probabilities else 0.0
        if (
            len(text.split()) >= 2
            and float(segment.get("avg_logprob", -99.0)) >= -1.0
            and float(segment.get("no_speech_prob", 1.0)) <= 0.6
            and mean_probability >= 0.5
        ):
            usable.append(
                {
                    "segment_id": int(segment.get("id", len(usable))),
                    "start": float(segment["start"]),
                    "end": float(segment["end"]),
                    "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "word_count": len(text.split()),
                    "mean_word_probability": mean_probability,
                    "avg_logprob": float(segment.get("avg_logprob", -99.0)),
                }
            )
    return usable


def usable_ocr_detections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    usable = []
    for frame in payload.get("frames", []):
        for detection in frame.get("detections", []):
            text = " ".join(str(detection.get("text", "")).split())
            box = [float(value) for value in detection.get("bbox_norm", [])]
            if len(box) != 4:
                continue
            area = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
            if (
                float(detection.get("score", 0.0)) >= 0.5
                and 2 <= len(text) <= 80
                and 0.0001 <= area <= 0.5
            ):
                usable.append(
                    {
                        "candidate_rank": int(frame["candidate_rank"]),
                        "frame_index": int(frame["frame_index"]),
                        "timestamp_sec": float(frame["timestamp_sec"]),
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "score": float(detection["score"]),
                        "bbox_norm": box,
                        "bbox_area": area,
                    }
                )
    return usable


def main() -> None:
    args = parse_args()
    questions_path = Path(args.questions).resolve()
    asr_root = Path(args.segmented_asr_root).resolve()
    ocr_root = Path(args.ocr_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or len(questions) != 500:
        raise ValueError("expected the answer-free 500-question OOF manifest")

    rows = []
    failures = []
    asr_cache: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    ocr_cache: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for question in questions:
        if any(key in question for key in ("answer", "ground_truth", "reference_answer", "judge_score")):
            raise ValueError("question manifest contains answer-side fields")
        question_id = str(question["question_id"])
        video = str(question["video"])
        asr_path = asr_root / f"{video}.json"
        ocr_path = ocr_root / f"{video}.json"
        if not asr_path.exists() or not ocr_path.exists():
            failures.append({"question_id": question_id, "video": video, "missing_asr": not asr_path.exists(), "missing_ocr": not ocr_path.exists()})
            continue
        if video not in asr_cache:
            payload = json.loads(asr_path.read_text(encoding="utf-8"))
            asr_cache[video] = (payload, usable_asr_segments(payload))
        if video not in ocr_cache:
            payload = json.loads(ocr_path.read_text(encoding="utf-8"))
            ocr_cache[video] = (payload, usable_ocr_detections(payload))
        asr_payload, asr_segments = asr_cache[video]
        _, ocr_detections = ocr_cache[video]
        query = extract_question_text(str(question["question"]))
        ocr_terms = matched_terms(query, OCR_QUERY_TERMS)
        audio_terms = matched_terms(query, AUDIO_QUERY_TERMS)
        if ocr_terms and ocr_detections:
            route = "ocr"
        elif audio_terms and asr_segments:
            route = "asr"
        else:
            route = "none"
        rows.append(
            {
                "schema_version": "qwen25_modality_active_input_audit_row_v1",
                "question_id": question_id,
                "video": video,
                "fold": int(question["fold"]),
                "question_text_sha256": hashlib.sha256(query.encode()).hexdigest(),
                "matched_ocr_query_terms": ocr_terms,
                "matched_audio_query_terms": audio_terms,
                "segmented_asr_status": str(asr_payload.get("status", "unknown")),
                "usable_asr_segment_count": len(asr_segments),
                "usable_ocr_detection_count": len(ocr_detections),
                "explicit_modality_route": route,
                "candidate_for_general_asr_context": bool(asr_segments),
            }
        )

    if failures or len(rows) != 500:
        raise RuntimeError(f"input audit incomplete: rows={len(rows)}, failures={len(failures)}")
    route_counts = Counter(row["explicit_modality_route"] for row in rows)
    route_videos = {
        route: len({row["video"] for row in rows if row["explicit_modality_route"] == route})
        for route in sorted(route_counts)
    }
    audit = {
        "schema_version": "qwen25_modality_active_input_audit_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": True,
        "question_count": len(rows),
        "video_count": len({row["video"] for row in rows}),
        "questions_sha256": sha256_file(questions_path),
        "segmented_asr_record_count": len(asr_cache),
        "ocr_record_count": len(ocr_cache),
        "asr_usable_question_count": sum(row["usable_asr_segment_count"] > 0 for row in rows),
        "ocr_usable_question_count": sum(row["usable_ocr_detection_count"] > 0 for row in rows),
        "explicit_route_counts": dict(sorted(route_counts.items())),
        "explicit_route_video_counts": route_videos,
        "explicit_active_question_count": sum(row["explicit_modality_route"] != "none" for row in rows),
        "explicit_active_video_count": len({row["video"] for row in rows if row["explicit_modality_route"] != "none"}),
        "answer_or_outcome_fields_used": False,
        "thresholds": {
            "asr_min_words": 2,
            "asr_min_avg_logprob": -1.0,
            "asr_max_no_speech_probability": 0.6,
            "asr_min_mean_word_probability": 0.5,
            "ocr_min_confidence": 0.5,
            "ocr_bbox_area_range": [0.0001, 0.5],
        },
        "manifest_sha256": canonical_sha256(rows),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "modality_availability_manifest_v1.jsonl"
    manifest_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    audit["manifest_file_sha256"] = sha256_file(manifest_path)
    (output_dir / "modality_availability_audit_v1.json").write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
