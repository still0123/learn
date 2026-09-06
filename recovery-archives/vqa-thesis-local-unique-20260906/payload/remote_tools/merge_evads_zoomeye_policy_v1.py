#!/usr/bin/env python3
"""Merge and audit sharded answer-free ZoomEye policy outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-questions", type=int, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() or args.expected_questions <= 0:
        raise RuntimeError("invalid merge arguments or existing output")

    merged = []
    source_results_sha256 = {}
    source_summaries_sha256 = {}
    errors = 0
    for fold in range(5):
        fold_dir = args.input_root / f"fold_{fold}"
        results_path = fold_dir / "policy_results.jsonl"
        summary_path = fold_dir / "run_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows = read_jsonl(results_path)
        if (
            summary.get("complete") is not True
            or int(summary.get("result_count", -1)) != len(rows)
            or summary.get("results_sha256") != sha256(results_path)
            or any(int(row.get("fold", -1)) != fold for row in rows)
        ):
            raise RuntimeError(f"incomplete or changed policy fold: {fold}")
        errors += int(summary.get("stats", {}).get("errors", 0))
        source_results_sha256[f"fold_{fold}"] = sha256(results_path)
        source_summaries_sha256[f"fold_{fold}"] = sha256(summary_path)
        merged.extend(rows)

    expected_anchors = 2 * args.expected_questions
    keys = {
        (str(row["question_id"]), int(row["anchor_index"]))
        for row in merged
    }
    anchors_by_question: dict[str, set[int]] = defaultdict(set)
    for row in merged:
        anchors_by_question[str(row["question_id"])].add(
            int(row["anchor_index"])
        )
    structural_parse_failures = [
        (str(row["question_id"]), int(row["anchor_index"]))
        for row in merged
        if not row.get("parse_valid")
    ]
    cue_parse_failures = [
        (str(row["question_id"]), int(row["anchor_index"]))
        for row in merged
        if not row.get("cue_parse_valid")
    ]
    if (
        len(merged) != expected_anchors
        or len(keys) != expected_anchors
        or len(anchors_by_question) != args.expected_questions
        or any(indices != {0, 1} for indices in anchors_by_question.values())
        or errors
        or structural_parse_failures
        or any(
            row.get("bbox_norm") is not None
            or int(row.get("selected_node_count", -1)) != 0
            for row in merged
            if not row.get("cue_parse_valid")
        )
    ):
        raise RuntimeError(
            "merged policy output failed integrity checks: "
            f"rows={len(merged)}, keys={len(keys)}, "
            f"questions={len(anchors_by_question)}, errors={errors}, "
            f"structural_parse_failures={structural_parse_failures}, "
            f"unsafe_cue_parse_failures={cue_parse_failures}"
        )

    merged.sort(
        key=lambda row: (
            int(row["fold"]),
            str(row["question_id"]),
            int(row["anchor_index"]),
        )
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    merged_path = args.output_dir / "policy_results.jsonl"
    write_jsonl(merged_path, merged)

    triggered_questions = {
        str(row["question_id"]) for row in merged if row.get("bbox_norm")
    }
    question_fold = {
        str(row["question_id"]): int(row["fold"]) for row in merged
    }
    bbox_areas = [
        float(row["bbox_area_ratio"])
        for row in merged
        if row.get("bbox_area_ratio") is not None
    ]
    latencies = [float(row["latency_seconds"]) for row in merged]
    valid_bbox_anchors_per_trigger = Counter(
        sum(
            bool(row.get("bbox_norm"))
            for row in merged
            if str(row["question_id"]) == question_id
        )
        for question_id in triggered_questions
    )
    audit = {
        "schema_version": "evads_zoomeye_policy_merged_v1",
        "passed": True,
        "anchor_count": len(merged),
        "question_count": len(anchors_by_question),
        "video_count": len({str(row["video_id"]) for row in merged}),
        "valid_bbox_anchor_count": len(bbox_areas),
        "trigger_question_count": len(triggered_questions),
        "trigger_video_count": len({
            str(row["video_id"])
            for row in merged
            if str(row["question_id"]) in triggered_questions
        }),
        "trigger_fold_counts": dict(sorted(Counter(
            question_fold[question_id]
            for question_id in triggered_questions
        ).items())),
        "valid_bbox_anchors_per_trigger": dict(sorted(
            valid_bbox_anchors_per_trigger.items()
        )),
        "selected_node_count": dict(sorted(Counter(
            int(row["selected_node_count"]) for row in merged
        ).items())),
        "bbox_area_ratio": {
            "mean": statistics.fmean(bbox_areas) if bbox_areas else None,
            "median": statistics.median(bbox_areas) if bbox_areas else None,
            "min": min(bbox_areas) if bbox_areas else None,
            "max": max(bbox_areas) if bbox_areas else None,
        },
        "exact_full_bbox_anchors": sum(area == 1.0 for area in bbox_areas),
        "structural_parse_failures": len(structural_parse_failures),
        "cue_parse_failures": len(cue_parse_failures),
        "cue_parse_failure_disposition": (
            "no_selected_node_fallback_AVFunnel_mid_no_retry"
        ),
        "errors": errors,
        "policy_latency_seconds_total": sum(latencies),
        "policy_latency_seconds_mean": statistics.fmean(latencies),
        "source_results_sha256": source_results_sha256,
        "source_summaries_sha256": source_summaries_sha256,
        "merged_results_sha256": sha256(merged_path),
        "reference_answer_used": False,
        "judge_scores_used": False,
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
