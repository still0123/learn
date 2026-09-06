#!/usr/bin/env python3
"""Validate and freeze the completed Dev100 counterfactual experiment assets."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_METHODS = {
    "raw_uniform",
    "raw_plus_counterfactual2",
    "innovation1_mmr32",
    "innovation1_mmr32_plus_counterfactual2",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def aggregate_tree(root: Path) -> dict[str, Any]:
    paths = sorted(path for path in root.rglob("*") if path.is_file())
    records = [{"path": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in paths]
    digest = hashlib.sha256()
    for row in records:
        digest.update(f"{row['path']}\0{row['sha256']}\n".encode("utf-8"))
    return {"root": str(root), "file_count": len(records), "content_digest": digest.hexdigest(), "files": records}


def validate_audit(path: Path, expected_count: int) -> dict[str, Any]:
    audit = load_json(path)
    if audit.get("expected_count") != expected_count or audit.get("available_count") != expected_count:
        raise RuntimeError(f"audit count mismatch: {path}")
    if audit.get("complete") is not True or audit.get("protocol_valid") is not True or audit.get("valid") is not True:
        raise RuntimeError(f"audit is not complete and valid: {path}")
    return audit


def validate_run_root(root: Path, expected_count: int) -> dict[str, Any]:
    counts = {
        "initial_prediction": len(list(root.glob("shard*of3/initial/*/prediction.json"))),
        "initial_evidence": len(list(root.glob("shard*of3/initial/*/evidence.json"))),
        "final_prediction": len(list(root.glob("shard*of3/final/*/prediction.json"))),
        "final_evidence": len(list(root.glob("shard*of3/final/*/evidence.json"))),
        "trace": len(list(root.glob("shard*of3/trace/*/evidence.json"))),
        "run_config": len(list(root.glob("shard*of3/run_config.json"))),
    }
    if any(counts[key] != expected_count for key in counts if key != "run_config") or counts["run_config"] != 3:
        raise RuntimeError(f"run root is incomplete: {root} {counts}")
    configs = [load_json(path) for path in sorted(root.glob("shard*of3/run_config.json"))]
    frozen_fields = {
        "model_dir": sorted({str(row.get("model_dir")) for row in configs}),
        "answer_prompt_version": sorted({str(row.get("answer_prompt_version")) for row in configs}),
        "answer_prompt_template_sha256": sorted({str(row.get("answer_prompt_template_sha256")) for row in configs}),
        "script_sha256": sorted({str(row.get("script_sha256")) for row in configs}),
        "visual_view_budget": sorted({row.get("visual_view_budget") for row in configs}),
        "secondary_frame_sampling_disabled": sorted({row.get("secondary_frame_sampling_disabled") for row in configs}),
    }
    if frozen_fields["visual_view_budget"] != [32] or frozen_fields["secondary_frame_sampling_disabled"] != [True]:
        raise RuntimeError(f"run protocol drifted: {root}")
    return {"counts": counts, "frozen_fields": frozen_fields, "tree": aggregate_tree(root)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-audit", type=Path, required=True)
    parser.add_argument("--mmr-audit", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--raw-run-root", type=Path)
    parser.add_argument("--mmr-run-root", type=Path)
    parser.add_argument("--mmr-cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=100)
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    if manifest.get("row_count") != args.expected_count or manifest.get("unique_question_count") != args.expected_count:
        raise RuntimeError("Dev100 split manifest count mismatch")
    raw_audit = validate_audit(args.raw_audit, args.expected_count)
    mmr_audit = validate_audit(args.mmr_audit, args.expected_count)
    summary = load_json(args.summary)
    if set(summary.get("methods", {})) != EXPECTED_METHODS:
        raise RuntimeError("Dev100 summary method set drifted")
    for method in EXPECTED_METHODS:
        method_summary = summary["methods"][method]
        if method_summary.get("expected") != args.expected_count or method_summary.get("parsed") != args.expected_count:
            raise RuntimeError(f"incomplete summary method: {method}")
    results = load_jsonl(args.results)
    result_keys = {(str(row.get("method")), str(row.get("question_id"))) for row in results}
    if len(results) != args.expected_count * len(EXPECTED_METHODS) or len(result_keys) != len(results):
        raise RuntimeError("Dev100 judge results are incomplete or duplicated")
    if {method for method, _ in result_keys} != EXPECTED_METHODS:
        raise RuntimeError("Dev100 judge method set mismatch")
    analysis = load_json(args.analysis)
    if analysis.get("question_count") != args.expected_count:
        raise RuntimeError("Dev100 analysis count mismatch")
    provenance = load_json(args.provenance)
    response_models = provenance.get("judge_response_models") or {}
    if sum(int(value) for value in response_models.values()) != len(results):
        raise RuntimeError("judge response model provenance count mismatch")
    input_paths = [
        args.manifest, args.raw_audit, args.mmr_audit, args.summary,
        args.results, args.analysis, args.provenance,
    ]
    payload: dict[str, Any] = {
        "schema": "adsqa_counterfactual_dev100_freeze_v1",
        "expected_count": args.expected_count,
        "methods": sorted(EXPECTED_METHODS),
        "judge_response_models": response_models,
        "input_files": [{"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in input_paths],
        "manifest_source_train_sha256": manifest.get("source_train_sha256"),
        "question_sha256": manifest.get("question_output_sha256"),
        "groundtruth_sha256": manifest.get("groundtruth_output_sha256"),
        "raw_question_sha256": raw_audit.get("question_file_sha256"),
        "mmr_question_sha256": mmr_audit.get("question_file_sha256"),
        "result_method_counts": dict(Counter(row["method"] for row in results)),
        "full_run_assets_included": bool(args.raw_run_root and args.mmr_run_root),
    }
    if args.raw_run_root or args.mmr_run_root:
        if not args.raw_run_root or not args.mmr_run_root:
            raise ValueError("both raw and MMR run roots are required for a full freeze")
        payload["raw_run"] = validate_run_root(args.raw_run_root, args.expected_count)
        payload["mmr_run"] = validate_run_root(args.mmr_run_root, args.expected_count)
    if args.mmr_cache:
        cache_rows = load_jsonl(args.mmr_cache)
        if len(cache_rows) != args.expected_count or len({str(row["question_id"]) for row in cache_rows}) != args.expected_count:
            raise RuntimeError("MMR cache is incomplete or duplicated")
        payload["mmr_cache"] = {
            "path": str(args.mmr_cache),
            "sha256": sha256_file(args.mmr_cache),
            "rows": len(cache_rows),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "valid": True,
        "full_run_assets_included": payload["full_run_assets_included"],
        "output": str(args.output),
        "output_sha256": sha256_file(args.output),
    }))


if __name__ == "__main__":
    main()
