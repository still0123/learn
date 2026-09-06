#!/usr/bin/env python3
"""Compare frame-local and video-global OCR relevance runs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--frame-run", required=True)
    parser.add_argument("--video-run", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_artifact(root: Path, question_id: str, name: str) -> Path:
    matches = sorted(root.glob(f"**/{question_id}/{name}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {name} for {question_id} under {root}, got {len(matches)}")
    return matches[0]


def prediction_text(payload: Any) -> str:
    item = payload[0] if isinstance(payload, list) else payload
    return str(item["prediction"])


def ocr_fusion_values(evidence: dict[str, Any], field: str) -> list[float]:
    values = []
    for trace in evidence.get("response_traces", []):
        fusion = trace.get("fusion", {})
        source = fusion.get(field, {})
        value = source.get("ocr") if isinstance(source, dict) else None
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def summarize_values(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def main() -> None:
    args = parse_args()
    questions = load_json(Path(args.question_file))
    frame_root = Path(args.frame_run)
    video_root = Path(args.video_run)
    equality = Counter()
    frame_reliabilities: list[float] = []
    video_reliabilities: list[float] = []
    frame_weights: list[float] = []
    video_weights: list[float] = []
    frame_scales: Counter[str] = Counter()
    video_scales: Counter[str] = Counter()
    video_traces: list[dict[str, Any]] = []

    for question in questions:
        qid = str(question["question_id"])
        frame_evidence = load_json(find_artifact(frame_root, qid, "evidence.json"))
        video_evidence = load_json(find_artifact(video_root, qid, "evidence.json"))
        frame_prediction = prediction_text(load_json(find_artifact(frame_root, qid, "prediction.json")))
        video_prediction = prediction_text(load_json(find_artifact(video_root, qid, "prediction.json")))
        equality["selected_frames"] += frame_evidence["selected_frames"] == video_evidence["selected_frames"]
        equality["crop_candidates"] += frame_evidence["crop_candidates"] == video_evidence["crop_candidates"]
        equality["selected_local_views"] += frame_evidence["selected_local_views"] == video_evidence["selected_local_views"]
        equality["visual_plan"] += frame_evidence["visual_plan"] == video_evidence["visual_plan"]
        equality["prediction"] += frame_prediction == video_prediction
        frame_reliabilities.extend(ocr_fusion_values(frame_evidence, "reliabilities"))
        video_reliabilities.extend(ocr_fusion_values(video_evidence, "reliabilities"))
        frame_weights.extend(ocr_fusion_values(frame_evidence, "weights"))
        video_weights.extend(ocr_fusion_values(video_evidence, "weights"))
        for item in frame_evidence["selected_local_views"]:
            frame_scales[f"{float(item.get('scale', 0.0)):.2f}"] += 1
        for item in video_evidence["selected_local_views"]:
            video_scales[f"{float(item.get('scale', 0.0)):.2f}"] += 1
        video_traces.append(video_evidence["ocr_relevance_trace"])

    trace_summary = {}
    for key in ("detection_count", "similarity_min", "similarity_max", "relevance_mean", "numeric_boost_count"):
        trace_summary[key] = summarize_values([
            float(trace[key]) for trace in video_traces if key in trace
        ])

    payload = {
        "question_file": str(Path(args.question_file).resolve()),
        "frame_run": str(frame_root.resolve()),
        "video_run": str(video_root.resolve()),
        "questions": len(questions),
        "exact_equality_counts": dict(equality),
        "changed_counts": {key: len(questions) - count for key, count in equality.items()},
        "ocr_source_reliability": {
            "frame": summarize_values(frame_reliabilities),
            "video": summarize_values(video_reliabilities),
        },
        "ocr_fusion_weight": {
            "frame": summarize_values(frame_weights),
            "video": summarize_values(video_weights),
        },
        "selected_local_scale_histogram": {
            "frame": dict(sorted(frame_scales.items())),
            "video": dict(sorted(video_scales.items())),
        },
        "video_relevance_trace": trace_summary,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
