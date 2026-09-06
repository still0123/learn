#!/usr/bin/env python3
"""Evaluate fixed-budget temporal caches against human evidence intervals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


OBSERVABLE = {"visual", "visual_audio", "partial"}


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_cache(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("cache must be NAME=PATH")
    name, path = value.split("=", 1)
    if not name:
        raise argparse.ArgumentTypeError("cache name cannot be empty")
    return name, Path(path)


def video_metadata(path: Path) -> tuple[int, float]:
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 1.0
    cap.release()
    if frame_count <= 0:
        raise RuntimeError(f"empty video: {path}")
    return frame_count, fps


def in_intervals(timestamp: float, intervals: list[list[float]], tolerance: float) -> bool:
    return any(float(start) - tolerance <= timestamp <= float(end) + tolerance for start, end in intervals)


def selection_metrics(
    frame_indices: list[int],
    frame_count: int,
    fps: float,
    units: list[dict[str, Any]],
    tolerance: float,
    coverage_bins: int,
) -> dict[str, Any]:
    timestamps = [float(index) / fps for index in frame_indices]
    visual_units = [unit for unit in units if "visual" in set(unit.get("modalities", []))]
    unit_hits = [
        any(in_intervals(timestamp, unit.get("intervals_sec", []), tolerance) for timestamp in timestamps)
        for unit in visual_units
    ]
    all_intervals = [interval for unit in visual_units for interval in unit.get("intervals_sec", [])]
    evidence_frame_hits = [in_intervals(timestamp, all_intervals, tolerance) for timestamp in timestamps]
    candidate_ranks = [
        min(coverage_bins - 1, int(index * coverage_bins / max(1, frame_count)))
        for index in frame_indices
    ]
    covered_bins = len(set(candidate_ranks))
    normalized = sorted(index / max(1, frame_count - 1) for index in frame_indices)
    boundaries = [0.0, *normalized, 1.0]
    max_gap = max((right - left for left, right in zip(boundaries, boundaries[1:])), default=1.0)
    return {
        "selected_count": len(frame_indices),
        "unique_frame_count": len(set(frame_indices)),
        "visual_unit_hits": unit_hits,
        "visual_units": len(unit_hits),
        "visual_unit_hit_count": sum(unit_hits),
        "evidence_frame_hits": sum(evidence_frame_hits),
        "evidence_frame_precision": sum(evidence_frame_hits) / len(frame_indices) if frame_indices else None,
        "covered_bins": covered_bins,
        "coverage_bins": coverage_bins,
        "max_normalized_gap": max_gap,
    }


def aggregate(details: list[dict[str, Any]], method: str) -> dict[str, Any]:
    rows = [row["methods"][method] for row in details if method in row["methods"]]
    units = sum(row["visual_units"] for row in rows)
    hits = sum(row["visual_unit_hit_count"] for row in rows)
    selected = sum(row["selected_count"] for row in rows)
    frame_hits = sum(row["evidence_frame_hits"] for row in rows)
    return {
        "eligible_questions": len(rows),
        "visual_units": units,
        "visual_unit_hits": hits,
        "visual_evidence_recall": hits / units if units else None,
        "evidence_frame_precision": frame_hits / selected if selected else None,
        "mean_covered_bins": float(np.mean([row["covered_bins"] for row in rows])) if rows else None,
        "mean_max_normalized_gap": float(np.mean([row["max_normalized_gap"] for row in rows])) if rows else None,
        "mean_unique_frames": float(np.mean([row["unique_frame_count"] for row in rows])) if rows else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--annotation_file", required=True)
    parser.add_argument("--video_root", required=True)
    parser.add_argument("--cache", action="append", type=parse_cache, default=[])
    parser.add_argument("--top_k", type=int, default=32)
    parser.add_argument("--coverage_bins", type=int, default=8)
    parser.add_argument("--tolerance_sec", type=float, default=0.5)
    parser.add_argument("--require_complete_cache", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    questions = {str(row["question_id"]): row for row in load_json(args.question_file)}
    annotations = {
        str(row["question_id"]): row
        for row in load_json(args.annotation_file)
        if row.get("annotation_status") == "complete"
        and row.get("evidence_observability") in OBSERVABLE
        and any("visual" in set(unit.get("modalities", [])) for unit in row.get("evidence_units", []))
    }
    caches: dict[str, dict[str, dict[str, Any]]] = {}
    inventories = []
    for name, path in args.cache:
        rows = load_jsonl(path)
        indexed = {str(row["question_id"]): row for row in rows}
        if len(indexed) != len(rows):
            raise RuntimeError(f"duplicate question ids in {path}")
        caches[name] = indexed
        inventories.append({"name": name, "path": str(path.resolve()), "sha256": sha256_file(path), "rows": len(rows)})

    method_names = ["raw_uniform", *caches]
    details = []
    missing = {name: [] for name in caches}
    for question_id, annotation in annotations.items():
        question = questions.get(question_id)
        if question is None:
            raise RuntimeError(f"annotated question missing from question file: {question_id}")
        video_id = str(question.get("video", annotation.get("video_id", "")))
        video_path = Path(args.video_root) / f"{video_id}.mp4"
        frame_count, fps = video_metadata(video_path)
        units = [unit for unit in annotation.get("evidence_units", []) if unit.get("required", True)]
        raw_indices = np.linspace(0, frame_count - 1, args.top_k, dtype=int).tolist()
        row = {
            "question_id": question_id,
            "video_id": video_id,
            "frame_count": frame_count,
            "fps": fps,
            "methods": {
                "raw_uniform": selection_metrics(raw_indices, frame_count, fps, units, args.tolerance_sec, args.coverage_bins)
            },
        }
        for name, indexed in caches.items():
            record = indexed.get(question_id)
            if record is None:
                missing[name].append(question_id)
                continue
            indices = [int(index) for index in record["selected_frame_indices"]]
            if len(indices) != args.top_k:
                raise RuntimeError(f"{name}/{question_id}: expected {args.top_k} frames, got {len(indices)}")
            row["methods"][name] = selection_metrics(
                indices, frame_count, fps, units, args.tolerance_sec, args.coverage_bins
            )
        details.append(row)

    if args.require_complete_cache and any(missing.values()):
        counts = {name: len(ids) for name, ids in missing.items()}
        raise RuntimeError(f"incomplete caches for annotated subset: {counts}")

    summary = {name: aggregate(details, name) for name in method_names}
    paired = {}
    for name in caches:
        changes = {"win": 0, "tie": 0, "loss": 0}
        for row in details:
            if name not in row["methods"]:
                continue
            raw_hits = row["methods"]["raw_uniform"]["visual_unit_hit_count"]
            method_hits = row["methods"][name]["visual_unit_hit_count"]
            changes["win" if method_hits > raw_hits else "loss" if method_hits < raw_hits else "tie"] += 1
        paired[name] = changes

    output = {
        "schema": "adsqa_temporal_evidence_evaluation_v1",
        "config": {
            "question_file": str(Path(args.question_file).resolve()),
            "question_file_sha256": sha256_file(args.question_file),
            "annotation_file": str(Path(args.annotation_file).resolve()),
            "annotation_file_sha256": sha256_file(args.annotation_file),
            "top_k": args.top_k,
            "coverage_bins": args.coverage_bins,
            "tolerance_sec": args.tolerance_sec,
        },
        "cache_inventory": inventories,
        "annotated_visual_questions": len(annotations),
        "summary": summary,
        "paired_vs_raw": paired,
        "missing_cache_question_ids": missing,
        "details": details,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "summary": summary, "paired_vs_raw": paired}, ensure_ascii=False))


if __name__ == "__main__":
    main()
