#!/usr/bin/env python3
"""Audit how query-conditioned OCR changes an AdsQA evidence plan."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--baseline-run", required=True)
    parser.add_argument("--candidate-run", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_question_ids(path: str | Path) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("question file must be a JSON list")
    values = [str(row["question_id"]) for row in payload]
    if len(values) != len(set(values)):
        raise ValueError("question file contains duplicate question_id values")
    return values


def index_evidence(root: str | Path) -> dict[str, Path]:
    indexed: dict[str, Path] = {}
    for path in Path(root).rglob("evidence.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        question_id = str(payload["question_id"])
        if question_id in indexed:
            raise ValueError(f"duplicate evidence for {question_id}: {indexed[question_id]}, {path}")
        indexed[question_id] = path
    return indexed


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def global_frame_signature(evidence: dict[str, Any]) -> list[tuple[int, int]]:
    return [
        (int(frame.get("sample_rank", -1)), int(frame.get("frame_index", -1)))
        for frame in evidence.get("selected_frames", [])
    ]


def local_view_signature(evidence: dict[str, Any]) -> list[tuple[int, tuple[float, ...]]]:
    values = []
    for view in evidence.get("selected_local_views", []):
        bbox = tuple(round(float(value), 8) for value in view.get("bbox_norm", []))
        values.append((int(view.get("frame_rank", -1)), bbox))
    return values


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def distribution(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": mean(values) if values else None,
        "min": min(values) if values else None,
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "max": max(values) if values else None,
    }


def processor_trace(evidence: dict[str, Any]) -> dict[str, Any]:
    trace = evidence.get("processor_trace")
    if isinstance(trace, dict):
        return trace
    trace = (evidence.get("generation") or {}).get("processor_trace")
    return trace if isinstance(trace, dict) else {}


def main() -> None:
    args = parse_args()
    expected = load_question_ids(args.question_file)
    baseline_index = index_evidence(args.baseline_run)
    candidate_index = index_evidence(args.candidate_run)
    expected_set = set(expected)
    missing_baseline = sorted(expected_set - set(baseline_index))
    missing_candidate = sorted(expected_set - set(candidate_index))
    if missing_baseline or missing_candidate:
        raise RuntimeError(
            f"incomplete evidence: baseline={len(missing_baseline)} candidate={len(missing_candidate)}"
        )

    same_global = 0
    same_local = 0
    active_frames_per_question = []
    active_ocr_weights: list[float] = []
    active_ocr_reliabilities: list[float] = []
    active_absolute_confidences: list[float] = []
    crop_scales: Counter[str] = Counter()
    represented_frames: Counter[str] = Counter()
    visual_tokens: Counter[str] = Counter()
    changed_ids = []

    for question_id in expected:
        baseline = load(baseline_index[question_id])
        candidate = load(candidate_index[question_id])
        if global_frame_signature(baseline) == global_frame_signature(candidate):
            same_global += 1
        baseline_local = local_view_signature(baseline)
        candidate_local = local_view_signature(candidate)
        if baseline_local == candidate_local:
            same_local += 1
        else:
            changed_ids.append(question_id)

        active_count = 0
        for trace in candidate.get("response_traces", []):
            ocr = trace.get("ocr_trace") or {}
            weight = (trace.get("fusion") or {}).get("weights", {}).get("ocr")
            if ocr.get("mode") == "off" or weight is None:
                continue
            active_count += 1
            active_ocr_weights.append(float(weight))
            if ocr.get("source_reliability") is not None:
                active_ocr_reliabilities.append(float(ocr["source_reliability"]))
            active_absolute_confidences.extend(
                float(value) for value in ocr.get("absolute_confidences", [])
            )
        active_frames_per_question.append(float(active_count))
        crop_scales.update(str(view.get("scale")) for view in candidate.get("selected_local_views", []))
        proc = processor_trace(candidate)
        represented_frames[str(proc.get("represented_frame_count"))] += 1
        visual_tokens[str(proc.get("post_merge_visual_token_count"))] += 1

    shared = len(expected)
    payload = {
        "question_file": str(Path(args.question_file).resolve()),
        "baseline_run": str(Path(args.baseline_run).resolve()),
        "candidate_run": str(Path(args.candidate_run).resolve()),
        "shared": shared,
        "global_frame_plan": {
            "identical": same_global,
            "changed": shared - same_global,
            "identical_rate": same_global / shared,
        },
        "local_crop_plan": {
            "identical": same_local,
            "changed": shared - same_local,
            "identical_rate": same_local / shared,
            "changed_question_ids": changed_ids,
        },
        "ocr": {
            "active_frames_per_question": distribution(active_frames_per_question),
            "active_fusion_weights": distribution(active_ocr_weights),
            "active_source_reliabilities": distribution(active_ocr_reliabilities),
            "absolute_confidences": distribution(active_absolute_confidences),
        },
        "candidate_crop_scale_counts": dict(sorted(crop_scales.items())),
        "candidate_represented_frame_counts": dict(represented_frames),
        "candidate_visual_token_counts": dict(visual_tokens),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "local_crop_plan"}, indent=2))


if __name__ == "__main__":
    main()
