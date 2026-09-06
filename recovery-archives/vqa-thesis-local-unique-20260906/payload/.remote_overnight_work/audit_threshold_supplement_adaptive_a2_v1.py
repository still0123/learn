#!/usr/bin/env python3
"""Audit threshold-triggered AdaptiveScaleA2 outputs for AdsQA supplement."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--runtime-folds", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    expected_folds: dict[int, int] = {}
    for fold in range(args.runtime_folds):
        input_path = (
            args.dataset_root / "full_triggered" / "adaptive_scale" / "shards"
            / f"fold_{fold}.jsonl"
        )
        rows = load_jsonl(input_path)
        expected = len(rows)
        expected_folds[fold] = expected
        if len(rows) != expected:
            failures.append(f"fold_{fold}: input count {len(rows)} != {expected}")
        output = args.run_root / f"fold_{fold}"
        summary_path = output / "run_summary.json"
        if not summary_path.is_file():
            failures.append(f"fold_{fold}: missing summary")
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        stats = summary.get("stats", {})
        if (
            summary.get("complete") is not True
            or int(stats.get("processed", -1))
            + int(stats.get("skipped_existing", -1)) != expected
            or int(stats.get("errors", -1)) != 0
        ):
            failures.append(f"fold_{fold}: incomplete summary")
        for row in rows:
            qid = str(row["question_id"])
            trace_path = output / qid / "a2_trace.json"
            prediction_path = output / qid / "a2_prediction.json"
            if not trace_path.is_file() or not prediction_path.is_file():
                failures.append(f"{qid}: missing output")
                continue
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
            processor = trace.get("processor_trace", {})
            checks = {
                "parse_valid": trace.get("parse_valid") is True,
                "views12": int(processor.get("represented_views", -1)) == 12,
                "base8": int(processor.get("represented_video_frames", -1)) == 8,
                "extra4": int(processor.get("represented_extra_images", -1)) == 4,
                "tokens3104": int(processor.get("visual_tokens", -1)) == 3104,
                "secondary_sampling_off": (
                    processor.get("secondary_frame_sampling") is False
                ),
                "variant_matches": (
                    str(trace.get("crop_ablation_variant")) == "adaptive_scale"
                ),
                "method_matches": (
                    "adaptive_scale" in str(prediction.get("method", ""))
                ),
                "base_frames_exact": [
                    int(value) for value in trace.get("base_source_frame_indices", [])
                ] == [int(value) for value in row["a0_frame_indices"]],
                "four_planned_views": len(trace.get("extra_view_plan", [])) == 4,
            }
            if not all(checks.values()):
                failures.append(f"{qid}: {checks}")
            records.append({
                "question_id": qid,
                "video_id": str(row["video_id"]),
                "fold": fold,
                "prediction_sha256": sha256_file(prediction_path),
                "trace_sha256": sha256_file(trace_path),
                "visual_tokens": int(processor.get("visual_tokens", -1)),
            })

    records.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = args.output_dir / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "qwen3_threshold_supplement_adaptive_a2_audit_v1",
        "passed": (
            not failures
            and len(records) == args.expected_count
            and sum(expected_folds.values()) == args.expected_count
        ),
        "expected_records": args.expected_count,
        "record_count": len(records),
        "video_count": len({row["video_id"] for row in records}),
        "fold_counts": dict(Counter(str(row["fold"]) for row in records)),
        "newly_inferred_count": len(records),
        "visual_token_counts": dict(
            Counter(str(row["visual_tokens"]) for row in records)
        ),
        "failures": failures,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "manifest_sha256": sha256_file(manifest_path),
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
