#!/usr/bin/env python3
"""Audit complete OOF-500 A2 inference without reading labels or references."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "ground_truth",
    "reference_answer",
    "meta_info",
    "judge_score",
    "label",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--reused-root", type=Path, required=True)
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
    rows = load_jsonl(args.dataset)
    if len(rows) != 500 or any(FORBIDDEN & set(row) for row in rows):
        raise RuntimeError("dataset is not the complete answer-free OOF-500 pool")

    manifest: list[dict[str, Any]] = []
    checks = Counter()
    reused = 0
    for row in rows:
        qid = str(row["question_id"])
        fold = int(row["fold"])
        item_dir = args.inference_root / f"fold_{fold}" / qid
        prediction_path = item_dir / "a2_prediction.json"
        trace_path = item_dir / "a2_trace.json"
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        processor = trace["processor_trace"]
        source_dir = args.reused_root / f"fold_{fold}" / qid
        was_reused = source_dir.is_dir()
        reused += int(was_reused)

        row_checks = {
            "parse_valid": trace.get("parse_valid") is True,
            "method_exact": prediction.get("method") == "Qwen3_AVEvidenceRewrite12_A2",
            "base_frames_exact": [
                int(value) for value in trace["base_source_frame_indices"]
            ] == [int(value) for value in row["a0_frame_indices"]],
            "extra_views_exact": len(trace["extra_view_plan"]) == 4,
            "represented_views_exact": int(processor["represented_views"]) == 12,
            "visual_tokens_exact": int(processor["visual_tokens"]) == 3104,
            "secondary_sampling_disabled": (
                processor.get("secondary_frame_sampling") is False
            ),
        }
        for name, passed in row_checks.items():
            checks[name] += int(passed)
        if not all(row_checks.values()):
            raise RuntimeError(f"protocol audit failed for {qid}: {row_checks}")

        manifest.append({
            "question_id": qid,
            "video_id": str(row["video_id"]),
            "fold": fold,
            "reused_from_frozen_smoke50": was_reused,
            "prediction_sha256": sha256_file(prediction_path),
            "trace_sha256": sha256_file(trace_path),
            "represented_views": int(processor["represented_views"]),
            "visual_tokens": int(processor["visual_tokens"]),
            "secondary_frame_sampling": False,
        })

    manifest.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = args.output_dir / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "qwen3_threshold_calibration500_a2_audit_v1",
        "question_count": len(manifest),
        "video_count": len({row["video_id"] for row in manifest}),
        "fold_counts": dict(Counter(str(row["fold"]) for row in manifest)),
        "reused_from_frozen_smoke50": reused,
        "newly_inferred": len(manifest) - reused,
        "checks_passed_count": dict(checks),
        "answer_free_generation": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "manifest_sha256": sha256_file(manifest_path),
        "passed": (
            len(manifest) == 500
            and len({row["video_id"] for row in manifest}) == 100
            and reused == 50
            and all(value == 500 for value in checks.values())
        ),
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not audit["passed"]:
        raise RuntimeError(f"aggregate protocol audit failed: {audit}")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
