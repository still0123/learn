#!/usr/bin/env python3
"""Merge and audit sharded answer-free Q-Zoom policy outputs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any

from PIL import Image


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


def valid_bbox(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and 0.0 <= float(item) <= 1.0
            for item in value
        )
        and float(value[0]) < float(value[2])
        and float(value[1]) < float(value[3])
    )


def self_check() -> None:
    assert valid_bbox([0, 0.1, 0.8, 1])
    assert not valid_bbox([0.5, 0.5, 0.4, 0.9])


def main() -> None:
    self_check()
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
            raise RuntimeError(f"incomplete or changed Q-Zoom fold: {fold}")
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
    artifact_failures = []
    for row in merged:
        qid = str(row["question_id"])
        anchor_index = int(row["anchor_index"])
        anchors_by_question[qid].add(anchor_index)
        crop_value = row.get("roi_image_path")
        crop_path = Path(str(crop_value)) if crop_value else None
        crop_valid = True
        if crop_path is not None:
            size = row.get("roi_image_size")
            crop_valid = (
                crop_path.is_file()
                and sha256(crop_path) == row.get("roi_image_sha256")
                and valid_bbox(row.get("bbox_norm"))
                and isinstance(size, list)
                and len(size) == 2
                and all(
                    isinstance(item, int) and item > 0 for item in size
                )
            )
            if crop_valid:
                with Image.open(crop_path) as image:
                    crop_valid = list(image.size) == size
        if (
            not row.get("parse_valid")
            or row.get("answer_generation_executed") is not False
            or row.get("reference_answer_used") is not False
            or (crop_path is not None and not crop_valid)
            or (
                crop_path is None
                and any(
                    row.get(field) is not None
                    for field in (
                        "bbox_norm",
                        "bbox_pixel_xyxy",
                        "bbox_feature_xyxy",
                    )
                )
            )
        ):
            artifact_failures.append((qid, anchor_index))
    if (
        len(merged) != expected_anchors
        or len(keys) != expected_anchors
        or len(anchors_by_question) != args.expected_questions
        or any(indices != {0, 1} for indices in anchors_by_question.values())
        or errors
        or artifact_failures
    ):
        raise RuntimeError(
            "merged Q-Zoom output failed integrity checks: "
            f"rows={len(merged)}, keys={len(keys)}, "
            f"questions={len(anchors_by_question)}, errors={errors}, "
            f"artifact_failures={artifact_failures}"
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
    areas = [
        (float(row["bbox_norm"][2]) - float(row["bbox_norm"][0]))
        * (float(row["bbox_norm"][3]) - float(row["bbox_norm"][1]))
        for row in merged
        if row.get("bbox_norm")
    ]
    latencies = [float(row["latency_seconds"]) for row in merged]
    audit = {
        "schema_version": "evads_qzoom_roi_policy_merged_v1",
        "passed": True,
        "anchor_count": len(merged),
        "question_count": len(anchors_by_question),
        "video_count": len({str(row["video_id"]) for row in merged}),
        "roi_anchor_count": len(areas),
        "no_roi_anchor_count": len(merged) - len(areas),
        "trigger_question_count": len(triggered_questions),
        "trigger_video_count": len({
            str(row["video_id"])
            for row in merged
            if str(row["question_id"]) in triggered_questions
        }),
        "trigger_fold_counts": dict(sorted(Counter(
            question_fold[qid] for qid in triggered_questions
        ).items())),
        "bbox_area_ratio": {
            "mean": statistics.fmean(areas) if areas else None,
            "median": statistics.median(areas) if areas else None,
            "min": min(areas) if areas else None,
            "max": max(areas) if areas else None,
        },
        "distinct_roi_image_hashes": len({
            str(row["roi_image_sha256"])
            for row in merged
            if row.get("roi_image_sha256")
        }),
        "errors": errors,
        "policy_latency_seconds_total": sum(latencies),
        "policy_latency_seconds_mean": statistics.fmean(latencies),
        "policy_latency_seconds_median": statistics.median(latencies),
        "source_results_sha256": source_results_sha256,
        "source_summaries_sha256": source_summaries_sha256,
        "merged_results_sha256": sha256(merged_path),
        "answer_generation_executed": False,
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
