#!/usr/bin/env python3
"""Audit offline temporal-selector caches before Qwen inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPORAL_DIR = PROJECT_ROOT / "evaluation" / "methods" / "temporal_evidence"
if str(TEMPORAL_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPORAL_DIR))

from temporal_cache import (  # noqa: E402
    load_temporal_index_cache,
    nested_uniform_candidate_indices,
    temporal_cache_inventory,
    validate_temporal_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit AdsQA temporal cache V1")
    parser.add_argument("--cache", required=True)
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--candidate_count", type=int, default=64)
    parser.add_argument("--selected_count", type=int, default=32)
    parser.add_argument("--coverage_bins", type=int, default=8)
    parser.add_argument("--video_root", default="")
    parser.add_argument("--verify_video_sources", action="store_true")
    parser.add_argument("--require_complete", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uniform_ranks(candidate_count: int, selected_count: int) -> list[int]:
    return np.linspace(0, candidate_count - 1, selected_count, dtype=int).tolist()


def resolve_video(video_root: str, video_id: str) -> Path:
    candidates = [
        Path(video_root) / f"{video_id}.mp4",
        Path(video_root) / video_id,
        Path(video_root) / f"{video_id}.webm",
        Path(video_root) / f"{video_id}.mov",
    ]
    return next((path for path in candidates if path.is_file()), candidates[0])


def expected_source_indices(video_path: Path, candidate_count: int, baseline_count: int) -> list[int]:
    from decord import VideoReader, cpu

    reader = VideoReader(str(video_path), ctx=cpu(0), num_threads=2)
    total = len(reader)
    if total <= 0:
        raise RuntimeError(f"empty video: {video_path}")
    return nested_uniform_candidate_indices(total, candidate_count, baseline_count)


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def main() -> None:
    args = parse_args()
    if args.candidate_count < args.selected_count or args.selected_count <= 0:
        raise ValueError("require candidate_count >= selected_count > 0")
    if not 0 < args.coverage_bins <= args.selected_count:
        raise ValueError("coverage_bins must be within selected_count")
    if args.verify_video_sources and not args.video_root:
        raise ValueError("--verify_video_sources requires --video_root")

    question_path = Path(args.question_file)
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    question_map = {str(item["question_id"]): item for item in questions}
    records = load_temporal_index_cache(args.cache)
    cache_qids = set(records)
    expected_qids = set(question_map)
    missing = sorted(expected_qids - cache_qids)
    extra = sorted(cache_qids - expected_qids)
    if args.require_complete and (missing or extra):
        raise RuntimeError(f"cache coverage mismatch: missing={len(missing)} extra={len(extra)}")

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for question_id in sorted(cache_qids & expected_qids):
        item = question_map[question_id]
        record = records[question_id]
        try:
            selected = validate_temporal_record(
                record,
                question_id=question_id,
                question=str(item.get("question", "")),
                candidate_count=args.candidate_count,
                selected_count=args.selected_count,
            )
            source_indices = record.get("candidate_frame_indices")
            if not isinstance(source_indices, list) or len(source_indices) != args.candidate_count:
                raise RuntimeError("candidate_frame_indices missing or wrong length")
            video_source_match = None
            if args.verify_video_sources:
                video_id = str(record.get("video_id", item.get("video", question_id.split("_")[0])))
                expected = expected_source_indices(
                    resolve_video(args.video_root, video_id), args.candidate_count, args.selected_count
                )
                video_source_match = source_indices == expected
                if not video_source_match:
                    raise RuntimeError("candidate source indices do not match current video decode")

            bin_ids = {
                min((rank * args.coverage_bins) // args.candidate_count, args.coverage_bins - 1)
                for rank in selected
            }
            boundary_ranks = [0, *selected, args.candidate_count - 1]
            gaps = [right - left for left, right in zip(boundary_ranks, boundary_ranks[1:])]
            selected_sources = [int(source_indices[rank]) for rank in selected]
            raw_sources = np.linspace(
                0, int(source_indices[-1]), args.selected_count, dtype=int
            ).tolist()
            overlap = len(set(selected_sources) & set(raw_sources))
            row = {
                "question_id": question_id,
                "selector": record.get("selector"),
                "candidate_count": args.candidate_count,
                "selected_count": len(selected),
                "chronological": selected == sorted(selected),
                "coverage_bins_hit": len(bin_ids),
                "coverage_bins_total": args.coverage_bins,
                "max_candidate_gap": max(gaps) if gaps else None,
                "mean_candidate_gap": mean([float(value) for value in gaps]),
                "raw_overlap_count": overlap,
                "raw_uniform_source_indices": raw_sources,
                "replacement_count_vs_raw": args.selected_count - overlap,
                "unique_selected_source_frames": len(set(selected_sources)),
                "repeated_selected_source_views": len(selected_sources) - len(set(selected_sources)),
                "video_source_match": video_source_match,
            }
            trace = record.get("selector_trace")
            if isinstance(trace, dict):
                row["question_asr_reliability"] = trace.get("question_asr_reliability")
                row["selector_bin_counts"] = trace.get("bin_counts")
            rows.append(row)
        except Exception as exc:
            errors.append({"question_id": question_id, "error": repr(exc)})

    summary = {
        "schema": "adsqa_temporal_cache_audit_v1",
        "cache": str(Path(args.cache).resolve()),
        "cache_files": temporal_cache_inventory(args.cache),
        "question_file": str(question_path.resolve()),
        "question_file_sha256": sha256_file(question_path),
        "candidate_count": args.candidate_count,
        "selected_count": args.selected_count,
        "coverage_bins": args.coverage_bins,
        "question_count": len(questions),
        "cache_record_count": len(records),
        "audited_count": len(rows),
        "missing_question_ids": missing,
        "extra_question_ids": extra,
        "error_count": len(errors),
        "errors": errors,
        "all_chronological": all(row["chronological"] for row in rows),
        "all_bins_covered_count": sum(
            row["coverage_bins_hit"] == args.coverage_bins for row in rows
        ),
        "mean_bins_hit": mean([float(row["coverage_bins_hit"]) for row in rows]),
        "mean_max_candidate_gap": mean([float(row["max_candidate_gap"]) for row in rows]),
        "mean_replacement_count_vs_raw": mean(
            [float(row["replacement_count_vs_raw"]) for row in rows]
        ),
        "mean_unique_selected_source_frames": mean(
            [float(row["unique_selected_source_frames"]) for row in rows]
        ),
        "video_source_match_count": sum(row["video_source_match"] is True for row in rows),
        "rows": rows,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, ensure_ascii=False, indent=2))
    if errors or (args.require_complete and (missing or extra)):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
