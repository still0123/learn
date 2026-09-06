#!/usr/bin/env python3
"""Materialize Uniform8 and a TopK8 compatibility manifest from SigLIP plans."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


POSITIONS = [round(index * 63 / 7) for index in range(8)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--uniform-output", type=Path, required=True)
    parser.add_argument("--topk-alias-output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--expected-videos", type=int, required=True)
    parser.add_argument("--expected-per-fold", type=int, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    targets = (args.uniform_output, args.topk_alias_output, args.audit)
    if any(path.exists() for path in targets):
        raise FileExistsError("an evidence8 output already exists")
    source = [
        json.loads(line)
        for line in args.source_manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(source) != args.expected_count:
        raise RuntimeError("source manifest count does not match protocol")
    uniform_rows: list[dict[str, Any]] = []
    topk_rows: list[dict[str, Any]] = []
    for row in source:
        candidates = [int(value) for value in row["candidate64_frame_indices"]]
        if len(candidates) != 64:
            raise RuntimeError("candidate64 coverage mismatch")
        uniform = [candidates[position] for position in POSITIONS]
        topk = [int(value) for value in row["siglip_topk8_frame_indices"]]
        for name, selected in (("Uniform8", uniform), ("TopK8", topk)):
            if len(set(selected)) != 8 or selected != sorted(selected):
                raise RuntimeError(f"{name} indices are invalid")
        common = {
            "question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "fold": int(row["fold"]),
            "candidate64_frame_indices": candidates,
            "selected_view_count": 8,
            "answer_or_outcome_fields_used": False,
        }
        uniform_rows.append({
            "schema_version": "evads_uniform8_manifest_v1",
            **common,
            "uniform8_candidate_positions": POSITIONS,
            "uniform8_frame_indices": uniform,
            "selection_method": "uniform8_from_candidate64_v1",
        })
        # The existing immutable Qwen runner reads this compatibility field.
        topk_rows.append({
            "schema_version": "evads_siglip_topk8_compat_manifest_v1",
            **common,
            "siglip_mmr8_frame_indices": topk,
            "native_frame_field": "siglip_topk8_frame_indices",
            "compatibility_frame_field": "siglip_mmr8_frame_indices",
            "selection_method": "siglip_topk64_then_chronological_v1",
        })

    fold_counts = Counter(int(row["fold"]) for row in uniform_rows)
    video_count = len({str(row["video_id"]) for row in uniform_rows})
    passed = (
        len(uniform_rows) == args.expected_count
        and len(topk_rows) == args.expected_count
        and video_count == args.expected_videos
        and dict(fold_counts)
        == {fold: args.expected_per_fold for fold in range(5)}
    )
    if not passed:
        raise RuntimeError("evidence8 manifest coverage audit failed")
    write_jsonl(args.uniform_output, uniform_rows)
    write_jsonl(args.topk_alias_output, topk_rows)
    audit = {
        "schema_version": "evads_evidence8_materialization_audit_v1",
        "passed": True,
        "record_count": len(uniform_rows),
        "video_count": video_count,
        "fold_counts": dict(sorted(fold_counts.items())),
        "candidate_positions": POSITIONS,
        "all_unique_chronological": True,
        "topk_compatibility_alias_explicit": True,
        "answer_or_outcome_fields_used": False,
        "source_manifest_sha256": sha256_file(args.source_manifest),
        "uniform_output_sha256": sha256_file(args.uniform_output),
        "topk_alias_output_sha256": sha256_file(args.topk_alias_output),
    }
    write_json(args.audit, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
