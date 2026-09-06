"""Utilities for turning cached OCR detections into spatial response maps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def load_ocr_cache(path: str | Path) -> tuple[dict[str, dict[int, list[dict[str, Any]]]], dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("OCR cache must contain an items list")
    indexed: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for item in payload["items"]:
        qid = str(item["question_id"])
        if qid in indexed:
            raise ValueError(f"duplicate OCR cache question_id: {qid}")
        frames: dict[int, list[dict[str, Any]]] = {}
        for frame in item.get("frames", []):
            sample_rank = int(frame["sample_rank"])
            if sample_rank in frames:
                raise ValueError(f"duplicate OCR cache sample_rank {sample_rank} for {qid}")
            detections = frame.get("detections", [])
            if not isinstance(detections, list):
                raise ValueError(f"OCR cache detections must be a list for {qid} rank {sample_rank}")
            frames[sample_rank] = [dict(value) for value in detections]
        indexed[qid] = frames
    return indexed, dict(payload.get("provenance", {}))


def validate_ocr_question_coverage(
    indexed: Mapping[str, Mapping[int, Sequence[Mapping[str, Any]]]],
    question_ids: Sequence[str],
) -> None:
    missing = sorted({str(qid) for qid in question_ids} - set(indexed))
    if missing:
        preview = ", ".join(missing[:5])
        raise ValueError(f"OCR cache is missing {len(missing)} question(s): {preview}")


def validate_ocr_frame_coverage(
    frames: Mapping[int, Sequence[Mapping[str, Any]]],
    selected_metadata: Sequence[Mapping[str, Any]],
) -> None:
    expected = {int(item["sample_rank"]) for item in selected_metadata}
    missing = sorted(expected - set(frames))
    if missing:
        raise ValueError(f"OCR cache is missing selected sample_rank(s): {missing}")


def load_question_bank(path: str | Path) -> list[str]:
    """Load question text without optional Voiceover/Question prefixes."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("OCR null question bank must be a JSON list")
    questions = []
    for row in payload:
        if not isinstance(row, Mapping) or not str(row.get("question", "")).strip():
            raise ValueError("OCR null question bank rows must contain question text")
        question = str(row["question"])
        if "Question:" in question:
            question = question.rsplit("Question:", 1)[-1]
        questions.append(question.strip())
    if not questions:
        raise ValueError("OCR null question bank cannot be empty")
    return questions


def empirical_null_confidence(
    target_similarities: Sequence[float],
    null_similarities: Sequence[Sequence[float]],
) -> tuple[np.ndarray, np.ndarray]:
    """Map query-text similarity to one-sided confidence above a null median."""
    targets = np.asarray(target_similarities, dtype=np.float32)
    nulls = np.asarray(null_similarities, dtype=np.float32)
    if targets.ndim != 1:
        raise ValueError("target_similarities must be one-dimensional")
    if nulls.ndim != 2 or nulls.shape[0] != targets.size or nulls.shape[1] == 0:
        raise ValueError("null_similarities must align with targets and have a non-empty bank")
    percentiles = np.mean(nulls < targets[:, None], axis=1, dtype=np.float32)
    confidence = np.clip(2.0 * percentiles - 1.0, 0.0, 1.0)
    return confidence.astype(np.float32), percentiles.astype(np.float32)


def rasterize_ocr_response(
    detections: Sequence[Mapping[str, Any]],
    shape: tuple[int, int],
    semantic_scores: Sequence[float] | None = None,
    min_confidence: float = 0.50,
    semantic_floor: float = 0.25,
    source_reliability_mode: str = "confidence",
) -> tuple[np.ndarray, dict[str, Any]]:
    """Rasterize normalized OCR polygons with confidence and query relevance."""
    height, width = [int(value) for value in shape]
    if height <= 0 or width <= 0:
        raise ValueError("shape must be positive")
    if semantic_scores is not None and len(semantic_scores) != len(detections):
        raise ValueError("semantic_scores must align with detections")
    if source_reliability_mode not in {"confidence", "weighted"}:
        raise ValueError("source_reliability_mode must be confidence or weighted")

    response = np.zeros((height, width), dtype=np.float32)
    kept = 0
    confidences: list[float] = []
    weighted_scores: list[float] = []
    floor = float(np.clip(semantic_floor, 0.0, 1.0))
    for index, detection in enumerate(detections):
        confidence = float(np.clip(detection.get("score", 0.0), 0.0, 1.0))
        box = detection.get("bbox_norm")
        if confidence < float(min_confidence) or not box or len(box) != 4:
            continue
        left, top, right, bottom = [float(np.clip(value, 0.0, 1.0)) for value in box]
        if right <= left or bottom <= top:
            continue
        relevance = 1.0 if semantic_scores is None else float(np.clip(semantic_scores[index], 0.0, 1.0))
        value = confidence * (floor + (1.0 - floor) * relevance)
        x1 = min(width - 1, max(0, int(np.floor(left * width))))
        y1 = min(height - 1, max(0, int(np.floor(top * height))))
        x2 = min(width, max(x1 + 1, int(np.ceil(right * width))))
        y2 = min(height, max(y1 + 1, int(np.ceil(bottom * height))))
        response[y1:y2, x1:x2] = np.maximum(response[y1:y2, x1:x2], value)
        kept += 1
        confidences.append(confidence)
        weighted_scores.append(value)

    reliability_values = confidences if source_reliability_mode == "confidence" else weighted_scores
    top_reliabilities = sorted(reliability_values, reverse=True)[:5]
    source_reliability = float(np.mean(top_reliabilities)) if top_reliabilities else 0.0
    trace = {
        "detection_count": len(detections),
        "kept_count": kept,
        "source_reliability": source_reliability,
        "max_weighted_score": max(weighted_scores, default=0.0),
        "mean_weighted_score": float(np.mean(weighted_scores)) if weighted_scores else 0.0,
    }
    if source_reliability_mode != "confidence":
        trace["source_reliability_mode"] = source_reliability_mode
    return response, trace


def normalize_ocr_relevance(similarities: Sequence[float]) -> np.ndarray:
    """Normalize OCR relevance jointly, preserving competition across frames."""
    values = np.asarray(similarities, dtype=np.float32)
    if values.ndim != 1:
        raise ValueError("similarities must be one-dimensional")
    if values.size == 0:
        return values
    minimum = float(values.min())
    maximum = float(values.max())
    if maximum - minimum <= 1e-8:
        return np.ones_like(values)
    return (values - minimum) / (maximum - minimum)
