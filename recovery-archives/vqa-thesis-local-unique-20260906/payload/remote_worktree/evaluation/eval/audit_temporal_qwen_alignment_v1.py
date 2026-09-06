#!/usr/bin/env python3
"""Audit that Qwen evidence consumed the exact frames from a temporal cache."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--run_root", required=True)
    parser.add_argument("--expected_model", required=True)
    parser.add_argument("--expected_prompt_sha256", required=True)
    parser.add_argument("--expected_views", type=int, default=32)
    parser.add_argument("--expected_tokens", type=int, default=11664)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    question_path = Path(args.question_file)
    cache_path = Path(args.cache)
    run_root = Path(args.run_root)
    expected_ids = {str(row["question_id"]) for row in load_json(question_path)}
    cache_rows = [
        json.loads(line)
        for line in cache_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cache = {str(row["question_id"]): row for row in cache_rows}
    if len(cache) != len(cache_rows):
        raise RuntimeError("duplicate question ids in cache")

    evidence_paths = sorted(run_root.rglob("evidence.json"))
    evidence: dict[str, tuple[Path, dict[str, Any]]] = {}
    duplicates = []
    for path in evidence_paths:
        row = load_json(path)
        question_id = str(row["question_id"])
        if question_id in evidence:
            duplicates.append(question_id)
        evidence[question_id] = (path, row)

    mismatches = []
    for question_id in sorted(expected_ids & set(cache) & set(evidence)):
        path, row = evidence[question_id]
        consumed = [int(item["frame_index"]) for item in row.get("selected_frames", [])]
        cached = [int(value) for value in cache[question_id]["selected_frame_indices"]]
        trace = row.get("processor_trace") or {}
        checks = {
            "source_frames_exact": consumed == cached,
            "input_image_count": row.get("input_image_count") == args.expected_views,
            "submitted_frame_count": trace.get("submitted_frame_count") == args.expected_views,
            "represented_frame_count": trace.get("represented_frame_count") == args.expected_views,
            "post_merge_visual_tokens": trace.get("post_merge_visual_token_count") == args.expected_tokens,
            "secondary_sampling_disabled": trace.get("secondary_frame_sampling_disabled") is True,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            mismatches.append({"question_id": question_id, "evidence": str(path), "failed": failed})

    config_checks = []
    for path in sorted(run_root.rglob("run_config.json")):
        row = load_json(path)
        checks = {
            "model": row.get("model_dir") == args.expected_model,
            "prompt": row.get("answer_prompt_template_sha256") == args.expected_prompt_sha256,
            "method": row.get("fair_method") == "external_temporal",
            "views": row.get("visual_view_budget") == args.expected_views,
            "secondary_sampling_disabled": row.get("secondary_frame_sampling_disabled") is True,
            "rag_disabled": row.get("rag_enabled") is False,
            "reflection_disabled": row.get("reflection_enabled") is False,
        }
        config_checks.append({
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "failed": [name for name, passed in checks.items() if not passed],
        })

    missing_cache = sorted(expected_ids - set(cache))
    missing_evidence = sorted(expected_ids - set(evidence))
    extra_cache = sorted(set(cache) - expected_ids)
    extra_evidence = sorted(set(evidence) - expected_ids)
    valid = not any(
        [missing_cache, missing_evidence, extra_cache, extra_evidence, duplicates, mismatches]
    ) and len(config_checks) == 3 and all(not row["failed"] for row in config_checks)
    payload = {
        "schema": "adsqa_temporal_qwen_alignment_audit_v1",
        "question_file": str(question_path.resolve()),
        "question_file_sha256": sha256_file(question_path),
        "cache": str(cache_path.resolve()),
        "cache_sha256": sha256_file(cache_path),
        "expected": len(expected_ids),
        "cache_count": len(cache),
        "evidence_count": len(evidence),
        "exact_alignment_count": len(expected_ids & set(cache) & set(evidence)) - len(mismatches),
        "missing_cache": missing_cache,
        "missing_evidence": missing_evidence,
        "extra_cache": extra_cache,
        "extra_evidence": extra_evidence,
        "duplicates": duplicates,
        "mismatches": mismatches,
        "run_configs": config_checks,
        "valid": valid,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
