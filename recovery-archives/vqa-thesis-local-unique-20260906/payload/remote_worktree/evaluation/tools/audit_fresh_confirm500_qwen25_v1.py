#!/usr/bin/env python3
"""Audit Fresh Confirm-500 Raw40 and Global32+Local8 outputs."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any, Mapping


EXPECTED_VIEWS = 40
EXPECTED_VISUAL_TOKENS = 20480
EXPECTED_LOCAL = {"B_Raw40": 0, "D_Gated_CLIPCrop8": 8}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--selection-audit", required=True)
    parser.add_argument("--gate-manifest", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--crop-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-count", type=int, default=500)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def load_artifacts(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int]:
    evidence: dict[str, dict[str, Any]] = {}
    predictions: dict[str, dict[str, Any]] = {}
    for path in root.rglob("evidence.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        if qid in evidence:
            raise ValueError(f"duplicate evidence for {qid}")
        evidence[qid] = row
    for path in root.rglob("prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        if qid in predictions:
            raise ValueError(f"duplicate prediction for {qid}")
        predictions[qid] = row
    errors = sum(
        bool(line.strip())
        for path in root.rglob("errors.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
    )
    return evidence, predictions, errors


def config_signature(root: Path) -> dict[str, Any]:
    paths = list(root.rglob("run_config.json"))
    if len(paths) != 1:
        raise ValueError(f"expected one run_config.json under {root}, found {len(paths)}")
    row = json.loads(paths[0].read_text(encoding="utf-8"))
    shared_keys = (
        "question_file_sha256",
        "python_executable",
        "transformers_version",
        "answer_prompt_version",
        "answer_prompt_sha256",
        "unified_size",
        "max_new_tokens",
        "secondary_frame_sampling_disabled",
        "rag_enabled",
        "reflection_enabled",
        "answer_rewrite_enabled",
    )
    shared = {key: row.get(key) for key in shared_keys}
    shared["model_path"] = row["model_identity"]["path"]
    shared["model_content_manifest_sha256"] = row["model_identity"]["content_manifest_sha256"]
    return {
        "method": row["method"],
        "shared": shared,
        "shared_sha256": canonical_sha256(shared),
        "gate_manifest_sha256": row.get("gate_manifest_sha256", ""),
    }


def audit_method(
    method: str,
    expected_ids: set[str],
    evidence: Mapping[str, Mapping[str, Any]],
    predictions: Mapping[str, Mapping[str, Any]],
    error_count: int,
) -> dict[str, Any]:
    problems = []
    token_counts = Counter()
    latencies = []
    for qid in sorted(expected_ids):
        row = evidence.get(qid)
        prediction = predictions.get(qid)
        if row is None or prediction is None:
            problems.append({"question_id": qid, "reason": "missing_artifact"})
            continue
        trace = row["processor_trace"]
        local_count = sum(view.get("view_type") == "local" for view in row["visual_plan"])
        global_count = sum(view.get("view_type") == "global" for view in row["visual_plan"])
        token_count = int(trace["post_merge_visual_token_count"])
        token_counts[token_count] += 1
        latencies.append(float(row.get("latency_seconds", 0.0)))
        checks = {
            "pipeline": prediction.get("pipeline") == method,
            "input_image_count": int(row["input_image_count"]) == EXPECTED_VIEWS,
            "global_view_count": global_count == EXPECTED_VIEWS - EXPECTED_LOCAL[method],
            "local_view_count": local_count == EXPECTED_LOCAL[method],
            "submitted_frame_count": int(trace["submitted_frame_count"]) == EXPECTED_VIEWS,
            "represented_frame_count": int(trace["represented_frame_count"]) == EXPECTED_VIEWS,
            "all_frames_represented": bool(trace["all_submitted_frames_represented"]),
            "secondary_sampling_disabled": bool(trace["secondary_frame_sampling_disabled"]),
            "visual_tokens": token_count == EXPECTED_VISUAL_TOKENS,
            "visual_budget": int(trace["post_merge_visual_token_budget"]) == EXPECTED_VISUAL_TOKENS,
        }
        if not all(checks.values()):
            problems.append({"question_id": qid, "checks": checks})
    extra_ids = (set(evidence) | set(predictions)) - expected_ids
    if extra_ids:
        problems.append({"reason": "extra_question_ids", "count": len(extra_ids)})
    return {
        "method": method,
        "expected_count": len(expected_ids),
        "evidence_count": len(evidence),
        "prediction_count": len(predictions),
        "error_count": error_count,
        "problem_count": len(problems),
        "problems": problems[:30],
        "visual_token_counts": dict(sorted(token_counts.items())),
        "mean_latency_seconds": mean(latencies) if latencies else None,
        "passed": not problems and error_count == 0,
    }


def main() -> None:
    args = parse_args()
    question_path = Path(args.questions).resolve()
    selection_audit_path = Path(args.selection_audit).resolve()
    gate_path = Path(args.gate_manifest).resolve()
    raw_root = Path(args.raw_root).resolve()
    crop_root = Path(args.crop_root).resolve()
    output_path = Path(args.output).resolve()
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    expected_ids = {str(row["question_id"]) for row in questions}
    selection_audit = json.loads(selection_audit_path.read_text(encoding="utf-8"))
    gate_rows = [
        json.loads(line)
        for line in gate_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gate_ids = {str(row["question_id"]) for row in gate_rows}
    raw_evidence, raw_predictions, raw_errors = load_artifacts(raw_root)
    crop_evidence, crop_predictions, crop_errors = load_artifacts(crop_root)
    raw_config = config_signature(raw_root)
    crop_config = config_signature(crop_root)
    raw_audit = audit_method(
        "B_Raw40",
        expected_ids,
        raw_evidence,
        raw_predictions,
        raw_errors,
    )
    crop_audit = audit_method(
        "D_Gated_CLIPCrop8",
        expected_ids,
        crop_evidence,
        crop_predictions,
        crop_errors,
    )
    shared_config_match = raw_config["shared_sha256"] == crop_config["shared_sha256"]
    gate_hash_match = crop_config["gate_manifest_sha256"] == sha256_file(gate_path)
    passed = all(
        (
            selection_audit.get("passed") is True,
            len(expected_ids) == args.expected_count,
            gate_ids == expected_ids,
            raw_audit["passed"],
            crop_audit["passed"],
            shared_config_match,
            gate_hash_match,
            "Qwen2.5-VL-7B-Instruct" in raw_config["shared"]["model_path"],
            "ReAd-R" not in raw_config["shared"]["model_path"],
        )
    )
    audit = {
        "schema_version": "fresh_confirm500_qwen25_protocol_audit_v1",
        "passed": passed,
        "question_count": len(expected_ids),
        "question_sha256": sha256_file(question_path),
        "selection_audit_sha256": sha256_file(selection_audit_path),
        "gate_manifest_sha256": sha256_file(gate_path),
        "gate_question_count": len(gate_ids),
        "gate_ids_match_questions": gate_ids == expected_ids,
        "shared_config_match": shared_config_match,
        "gate_hash_match": gate_hash_match,
        "raw_config": raw_config,
        "crop_config": crop_config,
        "raw_audit": raw_audit,
        "crop_audit": crop_audit,
        "raw_predictions_sha256": canonical_sha256(
            {qid: raw_predictions[qid]["prediction"] for qid in sorted(raw_predictions)}
        ),
        "crop_predictions_sha256": canonical_sha256(
            {qid: crop_predictions[qid]["prediction"] for qid in sorted(crop_predictions)}
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
