#!/usr/bin/env python3
"""Audit fixed-budget CLIP/AV outputs and deterministic fallback reuse."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_VIEWS = 40
EXPECTED_LOCAL_VIEWS = 8
EXPECTED_VISUAL_TOKENS = 20480


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip-root", required=True)
    parser.add_argument("--av-root", required=True)
    parser.add_argument("--gate-manifest", required=True)
    parser.add_argument("--expected-count", required=True, type=int)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_artifacts(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int]:
    evidence: dict[str, dict[str, Any]] = {}
    predictions: dict[str, dict[str, Any]] = {}
    for path in root.rglob("evidence.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        question_id = str(row["question_id"])
        if question_id in evidence:
            raise ValueError(f"duplicate evidence for {question_id} under {root}")
        evidence[question_id] = row
    for path in root.rglob("prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        question_id = str(row["question_id"])
        if question_id in predictions:
            raise ValueError(f"duplicate prediction for {question_id} under {root}")
        predictions[question_id] = row
    error_count = 0
    for path in root.rglob("errors.jsonl"):
        error_count += sum(bool(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())
    return evidence, predictions, error_count


def local_signature(evidence: Mapping[str, Any]) -> list[tuple[int, tuple[float, ...]]]:
    return [
        (
            int(view["source_global_rank"]),
            tuple(round(float(value), 6) for value in view["bbox_norm"]),
        )
        for view in evidence["visual_plan"]
        if view["view_type"] == "local"
    ]


def validate_evidence(rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    problems = []
    token_counts = Counter()
    for question_id, row in rows.items():
        trace = row["processor_trace"]
        local_count = sum(view["view_type"] == "local" for view in row["visual_plan"])
        checks = {
            "input_image_count": int(row["input_image_count"]) == EXPECTED_VIEWS,
            "local_view_count": local_count == EXPECTED_LOCAL_VIEWS,
            "submitted_frame_count": int(trace["submitted_frame_count"]) == EXPECTED_VIEWS,
            "represented_frame_count": int(trace["represented_frame_count"]) == EXPECTED_VIEWS,
            "all_frames_represented": bool(trace["all_submitted_frames_represented"]),
            "secondary_sampling_disabled": bool(trace["secondary_frame_sampling_disabled"]),
            "visual_tokens": int(trace["post_merge_visual_token_count"]) == EXPECTED_VISUAL_TOKENS,
            "visual_budget": int(trace["post_merge_visual_token_budget"]) == EXPECTED_VISUAL_TOKENS,
        }
        token_counts[int(trace["post_merge_visual_token_count"])] += 1
        if not all(checks.values()):
            problems.append({"question_id": question_id, "checks": checks})
    return {
        "record_count": len(rows),
        "passed": not problems,
        "problem_count": len(problems),
        "problems": problems[:20],
        "visual_token_counts": dict(sorted(token_counts.items())),
    }


def config_signatures(root: Path) -> dict[str, Any]:
    configs = [json.loads(path.read_text(encoding="utf-8")) for path in root.rglob("run_config.json")]
    keys = (
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
    signatures = {
        canonical_sha256(
            {
                **{key: config.get(key) for key in keys},
                "model_content_manifest_sha256": config["model_identity"]["content_manifest_sha256"],
            }
        )
        for config in configs
    }
    return {"config_count": len(configs), "common_signature_count": len(signatures), "signatures": sorted(signatures)}


def main() -> None:
    args = parse_args()
    clip_root = Path(args.clip_root).resolve()
    av_root = Path(args.av_root).resolve()
    gate_path = Path(args.gate_manifest).resolve()
    output_path = Path(args.output).resolve()
    gates = {
        str(row["question_id"]): row
        for row in (json.loads(line) for line in gate_path.read_text(encoding="utf-8").splitlines() if line.strip())
    }
    clip_evidence, clip_predictions, clip_errors = load_artifacts(clip_root)
    av_evidence, av_predictions, av_errors = load_artifacts(av_root)
    clip_ids = set(clip_predictions)
    active_ids = {question_id for question_id in clip_ids if gates[question_id]["gate_decision"]["modality_active"]}
    fallback_ids = clip_ids - active_ids
    av_ids = set(av_predictions)

    if set(clip_evidence) != clip_ids or set(av_evidence) != av_ids:
        raise ValueError("prediction/evidence question IDs are misaligned")
    if not active_ids.issubset(av_ids):
        raise ValueError("AV outputs are missing one or more active questions")
    if not av_ids.issubset(clip_ids):
        raise ValueError("AV outputs contain questions outside the CLIP set")

    active_plan_differences = sum(
        local_signature(clip_evidence[question_id]) != local_signature(av_evidence[question_id])
        for question_id in active_ids
    )
    provided_fallback_ids = fallback_ids & av_ids
    fallback_plan_matches = sum(
        local_signature(clip_evidence[question_id]) == local_signature(av_evidence[question_id])
        for question_id in provided_fallback_ids
    )
    fallback_prediction_matches = sum(
        clip_predictions[question_id]["prediction"] == av_predictions[question_id]["prediction"]
        for question_id in provided_fallback_ids
    )
    active_prediction_differences = sum(
        clip_predictions[question_id]["prediction"] != av_predictions[question_id]["prediction"]
        for question_id in active_ids
    )
    effective_av_predictions = {
        question_id: (
            av_predictions[question_id]["prediction"]
            if question_id in active_ids
            else clip_predictions[question_id]["prediction"]
        )
        for question_id in sorted(clip_ids, key=int)
    }
    clip_config = config_signatures(clip_root)
    av_config = config_signatures(av_root)
    clip_protocol = validate_evidence(clip_evidence)
    av_protocol = validate_evidence(av_evidence)
    passed = all(
        (
            len(clip_ids) == args.expected_count,
            len(active_ids) > 0,
            active_ids.issubset(av_ids),
            active_plan_differences == len(active_ids),
            fallback_plan_matches == len(provided_fallback_ids),
            fallback_prediction_matches == len(provided_fallback_ids),
            clip_errors == 0,
            av_errors == 0,
            clip_protocol["passed"],
            av_protocol["passed"],
            clip_config["common_signature_count"] == 1,
            av_config["common_signature_count"] == 1,
            clip_config["signatures"] == av_config["signatures"],
        )
    )
    audit = {
        "schema_version": "qwen25_modality_active_outputs_audit_v1",
        "passed": passed,
        "expected_question_count": args.expected_count,
        "clip_question_count": len(clip_ids),
        "active_question_count": len(active_ids),
        "fallback_question_count": len(fallback_ids),
        "av_computed_question_count": len(av_ids),
        "fallback_reused_question_count": len(fallback_ids - av_ids),
        "provided_fallback_question_count": len(provided_fallback_ids),
        "active_plan_difference_count": active_plan_differences,
        "active_prediction_difference_count": active_prediction_differences,
        "provided_fallback_plan_match_count": fallback_plan_matches,
        "provided_fallback_prediction_match_count": fallback_prediction_matches,
        "clip_error_count": clip_errors,
        "av_error_count": av_errors,
        "clip_protocol": clip_protocol,
        "av_protocol": av_protocol,
        "clip_config": clip_config,
        "av_config": av_config,
        "gate_manifest_sha256": sha256_file(gate_path),
        "effective_av_predictions_sha256": canonical_sha256(effective_av_predictions),
        "fallback_reuse_rule": "reuse CLIP prediction only when the frozen AV crop plan equals the CLIP crop plan",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
