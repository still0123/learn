#!/usr/bin/env python3
"""Audit threshold-triggered E-VAds A2 and ExtraGlobal12 outputs."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--extra-global-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
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


def audit_method(
    items: list[dict[str, Any]],
    root: Path,
    expected_variant: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    token_counts: Counter[int] = Counter()
    changed = 0
    hashes: dict[str, dict[str, str]] = {}
    for item in items:
        qid = str(item["question_id"])
        fold = int(item["fold"])
        item_dir = root / f"fold_{fold}" / qid
        prediction_path = item_dir / "a2_prediction.json"
        trace_path = item_dir / "a2_trace.json"
        if not prediction_path.is_file() or not trace_path.is_file():
            errors.append({"question_id": qid, "error": "missing_artifact"})
            continue
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        processor = trace.get("processor_trace", {})
        checks = {
            "parse_valid": trace.get("parse_valid") is True,
            "variant": trace.get("crop_ablation_variant") == expected_variant,
            "represented_views": int(processor.get("represented_views", -1)) == 12,
            "represented_video_frames": (
                int(processor.get("represented_video_frames", -1)) == 8
            ),
            "represented_extra_images": (
                int(processor.get("represented_extra_images", -1)) == 4
            ),
            "visual_tokens": int(processor.get("visual_tokens", -1)) == 3104,
            "secondary_sampling": (
                processor.get("secondary_frame_sampling") is False
            ),
            "base_frames": (
                [int(value) for value in trace.get("base_source_frame_indices", [])]
                == [int(value) for value in item["a0_frame_indices"]]
            ),
            "extra_views": len(trace.get("extra_view_plan", [])) == 4,
            "prediction_nonempty": bool(str(prediction.get("prediction", "")).strip()),
        }
        token_counts[int(processor.get("visual_tokens", -1))] += 1
        changed += int(trace.get("answer_changed_from_a0") is True)
        if not all(checks.values()):
            errors.append({
                "question_id": qid,
                "checks": checks,
            })
        hashes[qid] = {
            "prediction": sha256_file(prediction_path),
            "trace": sha256_file(trace_path),
        }
    return {
        "expected_variant": expected_variant,
        "record_count": len(items) - sum(
            error.get("error") == "missing_artifact" for error in errors
        ),
        "error_count": len(errors),
        "answer_changed_count": changed,
        "visual_token_counts": dict(sorted(token_counts.items())),
        "artifact_sha256": hashes,
    }, errors


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise FileExistsError("immutable audit output already exists")
    items_path = args.dataset_dir / "items_answer_free.jsonl"
    items = load_jsonl(items_path)
    adaptive, adaptive_errors = audit_method(
        items, args.adaptive_root, "adaptive_scale"
    )
    extra, extra_errors = audit_method(
        items, args.extra_global_root, "extra_global"
    )
    fold_counts = Counter(int(row["fold"]) for row in items)
    passed = (
        len(items) > 0
        and not adaptive_errors
        and not extra_errors
        and adaptive["record_count"] == len(items)
        and extra["record_count"] == len(items)
    )
    audit = {
        "schema_version": "evads_threshold_a2_controls_audit_v1",
        "passed": passed,
        "question_count": len(items),
        "video_count": len({str(row["video_id"]) for row in items}),
        "fold_counts": dict(sorted(fold_counts.items())),
        "adaptive": adaptive,
        "extra_global": extra,
        "adaptive_errors": adaptive_errors[:20],
        "extra_global_errors": extra_errors[:20],
        "answer_free": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "dataset_sha256": sha256_file(items_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        **audit,
        "adaptive": {
            key: value
            for key, value in adaptive.items()
            if key != "artifact_sha256"
        },
        "extra_global": {
            key: value
            for key, value in extra.items()
            if key != "artifact_sha256"
        },
    }, ensure_ascii=False, indent=2))
    if not passed:
        raise RuntimeError("threshold A2 protocol audit failed")


if __name__ == "__main__":
    main()
