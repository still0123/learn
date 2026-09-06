#!/usr/bin/env python3
"""Merge and audit sharded answer-free HiDe policy outputs."""

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


def valid_regions(row: dict[str, Any]) -> bool:
    regions = row.get("selected_regions_norm")
    if not isinstance(regions, list):
        return False
    for bbox in regions:
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and 0.0 <= float(value) <= 1.0
                for value in bbox
            )
            or float(bbox[0]) >= float(bbox[2])
            or float(bbox[1]) >= float(bbox[3])
        ):
            return False
    return int(row.get("selected_region_count", -1)) == len(regions)


def self_check() -> None:
    assert valid_regions({
        "selected_regions_norm": [[0, 0.1, 0.8, 1]],
        "selected_region_count": 1,
    })
    assert not valid_regions({
        "selected_regions_norm": [[0.5, 0.5, 0.4, 0.9]],
        "selected_region_count": 1,
    })


def main() -> None:
    self_check()
    args = parse_args()
    if args.output_dir.exists() or args.expected_questions <= 0:
        raise RuntimeError("invalid merge arguments or existing output")

    merged = []
    source_results_sha256 = {}
    source_summaries_sha256 = {}
    errors = 0
    entity_parse_failures = 0
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
            raise RuntimeError(f"incomplete or changed HiDe fold: {fold}")
        stats = summary.get("stats", {})
        errors += int(stats.get("errors", 0))
        entity_parse_failures += int(
            stats.get("entity_parse_failures", 0)
        )
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
        layout_value = row.get("compact_image_path")
        layout_path = Path(str(layout_value)) if layout_value else None
        layout_valid = True
        if layout_path is not None:
            size = row.get("compact_image_size")
            layout_valid = (
                layout_path.is_file()
                and sha256(layout_path) == row.get("compact_image_sha256")
                and isinstance(size, list)
                and len(size) == 2
                and all(
                    isinstance(value, int) and value > 0
                    for value in size
                )
            )
            if layout_valid:
                with Image.open(layout_path) as image:
                    layout_valid = list(image.size) == size
        if (
            not row.get("parse_valid")
            or not row.get("entity_parse_valid")
            or not valid_regions(row)
            or row.get("reference_answer_used") is not False
            or (
                layout_path is not None
                and (
                    not layout_valid
                    or int(row.get("selected_region_count", 0)) <= 0
                )
            )
            or (
                layout_path is None
                and int(row.get("selected_region_count", 0)) != 0
            )
        ):
            artifact_failures.append((qid, anchor_index))
    if (
        len(merged) != expected_anchors
        or len(keys) != expected_anchors
        or len(anchors_by_question) != args.expected_questions
        or any(indices != {0, 1} for indices in anchors_by_question.values())
        or errors
        or entity_parse_failures
        or artifact_failures
    ):
        raise RuntimeError(
            "merged HiDe output failed integrity checks: "
            f"rows={len(merged)}, keys={len(keys)}, "
            f"questions={len(anchors_by_question)}, errors={errors}, "
            f"entity_parse_failures={entity_parse_failures}, "
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
        str(row["question_id"])
        for row in merged
        if row.get("compact_image_path")
    }
    question_fold = {
        str(row["question_id"]): int(row["fold"]) for row in merged
    }
    latencies = [float(row["latency_seconds"]) for row in merged]
    region_counts = [
        int(row["selected_region_count"]) for row in merged
    ]
    layout_sizes = [
        row["compact_image_size"]
        for row in merged
        if row.get("compact_image_size") is not None
    ]
    audit = {
        "schema_version": "evads_hide_policy_merged_v1",
        "passed": True,
        "anchor_count": len(merged),
        "question_count": len(anchors_by_question),
        "video_count": len({str(row["video_id"]) for row in merged}),
        "layout_anchor_count": sum(
            bool(row.get("compact_image_path")) for row in merged
        ),
        "no_region_anchor_count": sum(
            not row.get("compact_image_path") for row in merged
        ),
        "selected_region_count_total": sum(region_counts),
        "selected_region_count": dict(sorted(Counter(region_counts).items())),
        "distinct_compact_image_hashes": len({
            str(row["compact_image_sha256"])
            for row in merged
            if row.get("compact_image_sha256")
        }),
        "compact_width": {
            "min": min((size[0] for size in layout_sizes), default=None),
            "median": (
                statistics.median(size[0] for size in layout_sizes)
                if layout_sizes
                else None
            ),
            "max": max((size[0] for size in layout_sizes), default=None),
        },
        "compact_height": {
            "min": min((size[1] for size in layout_sizes), default=None),
            "median": (
                statistics.median(size[1] for size in layout_sizes)
                if layout_sizes
                else None
            ),
            "max": max((size[1] for size in layout_sizes), default=None),
        },
        "trigger_question_count": len(triggered_questions),
        "trigger_video_count": len({
            str(row["video_id"])
            for row in merged
            if str(row["question_id"]) in triggered_questions
        }),
        "trigger_fold_counts": dict(sorted(Counter(
            question_fold[qid] for qid in triggered_questions
        ).items())),
        "entity_parse_failures": entity_parse_failures,
        "errors": errors,
        "policy_latency_seconds_total": sum(latencies),
        "policy_latency_seconds_mean": statistics.fmean(latencies),
        "policy_latency_seconds_median": statistics.median(latencies),
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
