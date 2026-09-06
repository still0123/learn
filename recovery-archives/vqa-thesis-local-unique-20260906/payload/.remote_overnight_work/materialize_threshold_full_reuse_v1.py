#!/usr/bin/env python3
"""Reuse exact Full-530 AdaptiveScaleA2 outputs in the threshold run."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
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
    by_id = {str(row["question_id"]): row for row in rows}
    if len(rows) != 4905 or len(by_id) != 4905:
        raise RuntimeError("threshold dataset is not frozen 4905")
    source: dict[str, Path] = {}
    for prediction_path in args.source_root.glob("fold_*/*/a2_prediction.json"):
        qid = prediction_path.parent.name
        if qid in source:
            raise RuntimeError(f"duplicate source A2 output: {qid}")
        source[qid] = prediction_path.parent
    if len(source) != 530 or not set(source).issubset(by_id):
        raise RuntimeError("Full-530 reuse set does not align with threshold set")

    manifest = []
    for qid, source_dir in sorted(source.items()):
        row = by_id[qid]
        fold = int(row["fold"])
        destination = args.output_root / f"fold_{fold}" / qid
        if destination.exists():
            raise RuntimeError(f"reuse destination exists: {destination}")
        prediction = json.loads(
            (source_dir / "a2_prediction.json").read_text(encoding="utf-8")
        )
        trace = json.loads(
            (source_dir / "a2_trace.json").read_text(encoding="utf-8")
        )
        processor = trace["processor_trace"]
        checks = {
            "parse_valid": trace.get("parse_valid") is True,
            "adaptive_method": "adaptive_scale" in str(prediction.get("method", "")),
            "base_frames_exact": [
                int(value) for value in trace["base_source_frame_indices"]
            ] == [int(value) for value in row["a0_frame_indices"]],
            "views12": int(processor["represented_views"]) == 12,
            "tokens3104": int(processor["visual_tokens"]) == 3104,
            "secondary_sampling_off": processor["secondary_frame_sampling"] is False,
        }
        if not all(checks.values()):
            raise RuntimeError(f"source output fails reuse audit for {qid}: {checks}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, destination)
        manifest.append({
            "question_id": qid,
            "source_runtime_fold": int(source_dir.parent.name.split("_")[-1]),
            "threshold_runtime_fold": fold,
            "prediction_sha256": sha256_file(destination / "a2_prediction.json"),
            "trace_sha256": sha256_file(destination / "a2_trace.json"),
        })

    args.audit.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = args.audit.with_name("reuse_manifest.jsonl")
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "qwen3_threshold_full5320_reuse_audit_v1",
        "passed": len(manifest) == 530,
        "reused_count": len(manifest),
        "destination_fold_counts": dict(
            Counter(str(row["threshold_runtime_fold"]) for row in manifest)
        ),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "manifest_sha256": sha256_file(manifest_path),
    }
    args.audit.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not audit["passed"]:
        raise RuntimeError("reuse audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
