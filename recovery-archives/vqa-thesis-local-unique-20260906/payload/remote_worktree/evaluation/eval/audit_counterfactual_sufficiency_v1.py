#!/usr/bin/env python3
"""Audit fixed-budget counterfactual-sufficiency runs before judging answers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_phase(run_root: Path, phase: str) -> tuple[Dict[str, Path], Dict[str, Path]]:
    predictions: Dict[str, Path] = {}
    evidence: Dict[str, Path] = {}
    for path in run_root.glob(f"shard*of3/{phase}/*/prediction.json"):
        predictions[str(load_json(path).get("question_id"))] = path
    for path in run_root.glob(f"shard*of3/{phase}/*/evidence.json"):
        evidence[str(load_json(path).get("question_id"))] = path
    return predictions, evidence


def protocol_errors(row: Dict[str, Any], expected_views: int, expected_tokens: int) -> list[str]:
    trace = row.get("processor_trace") or {}
    checks = {
        "input_image_count": row.get("input_image_count") == expected_views,
        "submitted_frame_count": trace.get("submitted_frame_count") == expected_views,
        "represented_frame_count": trace.get("represented_frame_count") == expected_views,
        "post_merge_visual_token_count": trace.get("post_merge_visual_token_count") == expected_tokens,
        "secondary_frame_sampling_disabled": trace.get("secondary_frame_sampling_disabled") is True,
    }
    return [name for name, valid in checks.items() if not valid]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--run_root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected_views", type=int, default=32)
    parser.add_argument("--expected_tokens", type=int, default=11664)
    parser.add_argument("--cache", default="")
    parser.add_argument("--require_complete", action="store_true")
    args = parser.parse_args()

    question_path = Path(args.question_file)
    root = Path(args.run_root)
    expected_ids = {str(row["question_id"]) for row in load_json(question_path)}
    initial_pred, initial_evidence = collect_phase(root, "initial")
    final_pred, final_evidence = collect_phase(root, "final")
    trace_paths = {str(load_json(path).get("question_id")): path for path in root.glob("shard*of3/trace/*/evidence.json")}
    available_ids = set(initial_pred) | set(initial_evidence) | set(final_pred) | set(final_evidence) | set(trace_paths)
    phase_errors: Dict[str, list[Dict[str, Any]]] = {"initial": [], "final": [], "trace": []}
    for phase, evidence in (("initial", initial_evidence), ("final", final_evidence)):
        for qid, path in evidence.items():
            failed = protocol_errors(load_json(path), args.expected_views, args.expected_tokens)
            if failed:
                phase_errors[phase].append({"question_id": qid, "path": str(path), "failed": failed})

    cache = {}
    cache_mismatches = []
    if args.cache:
        for line in Path(args.cache).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                cache[str(row["question_id"])] = row
        for qid, path in initial_evidence.items():
            if qid not in cache:
                cache_mismatches.append({"question_id": qid, "failed": ["missing_cache"]})
                continue
            selected = [int(item["frame_index"]) for item in load_json(path).get("selected_frames", [])]
            cached = [int(value) for value in cache[qid]["selected_frame_indices"]]
            if selected != cached:
                cache_mismatches.append({"question_id": qid, "failed": ["initial_frames_not_cache_exact"]})

    for qid, path in trace_paths.items():
        row = load_json(path)
        failed = []
        if not isinstance(row.get("support_plus"), (float, int)) or not isinstance(row.get("support_minus"), (float, int)):
            failed.append("missing_numeric_counterfactual_scores")
        cf = row.get("counterfactual") or {}
        if cf.get("view_count_before") != args.expected_views or cf.get("view_count_after") != args.expected_views:
            failed.append("counterfactual_budget_drift")
        rescue = row.get("rescue") or {}
        if rescue.get("triggered"):
            plan = rescue.get("rescue_plan") or {}
            if plan.get("context_count") + plan.get("local_count") != args.expected_views:
                failed.append("rescue_budget_drift")
            if plan.get("context_count") != args.expected_views - 8 or plan.get("local_count") != 8:
                failed.append("rescue_not_fixed24plus8")
        if row.get("visual_views_per_forward_pass") != args.expected_views:
            failed.append("per_forward_budget_drift")
        if failed:
            phase_errors["trace"].append({"question_id": qid, "path": str(path), "failed": failed})

    missing = {
        "initial_prediction": sorted(expected_ids - set(initial_pred)),
        "initial_evidence": sorted(expected_ids - set(initial_evidence)),
        "final_prediction": sorted(expected_ids - set(final_pred)),
        "final_evidence": sorted(expected_ids - set(final_evidence)),
        "trace": sorted(expected_ids - set(trace_paths)),
    }
    config_paths = sorted(root.glob("shard*of3/run_config.json"))
    config_errors = []
    for config_path in config_paths:
        config = load_json(config_path)
        failed = []
        for key, expected in (("visual_view_budget", args.expected_views), ("max_post_merge_visual_tokens", 12000), ("secondary_frame_sampling_disabled", True), ("rag_enabled", False), ("reflection_enabled", False)):
            if config.get(key) != expected:
                failed.append(key)
        if failed:
            config_errors.append({"path": str(config_path), "failed": failed})
    complete = all(not values for values in missing.values())
    protocol_valid = not any(phase_errors.values()) and not cache_mismatches and not config_errors
    valid = protocol_valid and (complete or not args.require_complete)
    payload = {
        "schema": "adsqa_counterfactual_sufficiency_audit_v1",
        "question_file": str(question_path.resolve()),
        "question_file_sha256": sha256_file(question_path),
        "run_root": str(root.resolve()),
        "expected_count": len(expected_ids),
        "available_count": len(available_ids),
        "complete": complete,
        "missing": missing,
        "phase_errors": phase_errors,
        "cache": str(Path(args.cache).resolve()) if args.cache else "",
        "cache_mismatches": cache_mismatches,
        "config_paths": [str(path.resolve()) for path in config_paths],
        "config_errors": config_errors,
        "protocol_valid": protocol_valid,
        "valid": valid,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
