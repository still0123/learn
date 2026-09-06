#!/usr/bin/env python3
"""Audit the three-arm Shared32 causal-isolation inference protocol."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


EXPECTED_VIEWS = 40
EXPECTED_SHARED_VIEWS = 32
EXPECTED_EXTRA_VIEWS = 8
EXPECTED_VISUAL_TOKENS = 20480
METHODS = (
    "Shared32_Local8",
    "Shared32_UncertaintyGatedLocal8",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--gate-manifest", required=True)
    parser.add_argument("--expected-count", required=True, type=int)
    parser.add_argument("--folds", default="0,1,2,3,4")
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


def load_artifacts(roots: list[Path]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int]:
    evidence: dict[str, dict[str, Any]] = {}
    predictions: dict[str, dict[str, Any]] = {}
    for root in roots:
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
    error_count = sum(
        bool(line.strip())
        for root in roots
        for path in root.rglob("errors.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
    )
    return evidence, predictions, error_count


def config_signatures(roots: list[Path]) -> dict[str, Any]:
    configs = [
        json.loads(path.read_text(encoding="utf-8"))
        for root in roots
        for path in root.rglob("run_config.json")
    ]
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
        "model_identity",
        "submitted_view_count",
        "shared_global_view_count",
    )
    signatures = {
        canonical_sha256({key: config.get(key) for key in keys})
        for config in configs
    }
    return {"config_count": len(configs), "common_signature_count": len(signatures), "signatures": sorted(signatures)}


def shared_signature(row: Mapping[str, Any]) -> list[tuple[int, int | None]]:
    return [
        (int(view.get("global_rank", -1)), view.get("source_frame_index"))
        for view in row["visual_plan"][:EXPECTED_SHARED_VIEWS]
    ]


def validate_evidence(rows: Mapping[str, Mapping[str, Any]], method: str) -> dict[str, Any]:
    problems = []
    token_counts = Counter()
    for question_id, row in rows.items():
        trace = row["processor_trace"]
        plan = row["visual_plan"]
        shared = plan[:EXPECTED_SHARED_VIEWS]
        intervention = plan[EXPECTED_SHARED_VIEWS:]
        local_count = sum(view.get("view_type") == "local" for view in intervention)
        extra_count = sum(view.get("view_type") == "extra_global" for view in intervention)
        if method == "Shared32_ExtraGlobal8":
            intervention_ok = extra_count == EXPECTED_EXTRA_VIEWS and local_count == 0
            extra_indices = [int(view.get("source_frame_index", -1)) for view in intervention]
            shared_indices = {int(view.get("source_frame_index", -1)) for view in shared}
            intervention_ok = intervention_ok and not (set(extra_indices) & shared_indices)
        else:
            intervention_ok = local_count == EXPECTED_EXTRA_VIEWS and extra_count == 0
            if method == "Shared32_RandomLocal8":
                intervention_ok = intervention_ok and all(
                    view.get("crop_mode") == "deterministic_random_control_v1" for view in intervention
                )
            if method == "Shared32_Local8":
                intervention_ok = intervention_ok and all(
                    view.get("crop_mode") != "deterministic_random_control_v1" for view in intervention
                )
            if method == "Shared32_UncertaintyGatedLocal8":
                intervention_ok = intervention_ok and all(
                    view.get("crop_mode") == "uncertainty_gated_local8_v1" for view in intervention
                )
        checks = {
            "input_image_count": int(row["input_image_count"]) == EXPECTED_VIEWS,
            "shared_global_view_count": len(shared) == EXPECTED_SHARED_VIEWS,
            "intervention_view_count": len(intervention) == EXPECTED_EXTRA_VIEWS,
            "intervention_type": intervention_ok,
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


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root).resolve()
    gate_path = Path(args.gate_manifest).resolve()
    output_path = Path(args.output).resolve()
    folds = [int(value) for value in args.folds.split(",") if value.strip()]
    gates = {
        str(row["question_id"]): row
        for row in (json.loads(line) for line in gate_path.read_text(encoding="utf-8").splitlines() if line.strip())
    }
    loaded = {}
    protocol = {}
    errors = {}
    configs = {}
    method_roots = {}
    for method in METHODS:
        direct_root = run_root / method
        roots = [direct_root] if direct_root.exists() else sorted(run_root.glob(f"fold_*/{method}"))
        if not roots:
            roots = [direct_root]
        method_roots[method] = [str(root) for root in roots]
        loaded[method] = load_artifacts(roots)
        protocol[method] = validate_evidence(loaded[method][0], method)
        errors[method] = loaded[method][2]
        configs[method] = config_signatures(roots)

    ids_by_method = {method: set(loaded[method][1]) for method in METHODS}
    common_ids = set.intersection(*ids_by_method.values()) if ids_by_method else set()
    expected_total = args.expected_count
    shared_mismatches = []
    intervention_mismatches = []
    for question_id in sorted(common_ids, key=int):
        rows = {method: loaded[method][0][question_id] for method in METHODS}
        signatures = {method: shared_signature(row) for method, row in rows.items()}
        if len({tuple(signature) for signature in signatures.values()}) != 1:
            shared_mismatches.append({"question_id": question_id, "signatures": signatures})
        local_signature = canonical_sha256(rows["Shared32_Local8"]["visual_plan"][EXPECTED_SHARED_VIEWS:])
        uncertainty_signature = canonical_sha256(rows["Shared32_UncertaintyGatedLocal8"]["visual_plan"][EXPECTED_SHARED_VIEWS:])
        if local_signature == uncertainty_signature:
            intervention_mismatches.append(question_id)

    config_signature_set = {
        signature
        for value in configs.values()
        for signature in value["signatures"]
    }
    passed = all(
        (
            all(len(ids_by_method[method]) == expected_total for method in METHODS),
            all(set(loaded[method][0]) == ids_by_method[method] for method in METHODS),
            len(common_ids) == expected_total,
            not shared_mismatches,
            not intervention_mismatches,
            all(errors[method] == 0 for method in METHODS),
            all(protocol[method]["passed"] for method in METHODS),
            all(configs[method]["common_signature_count"] == 1 for method in METHODS),
            len(config_signature_set) == 1,
        )
    )
    audit = {
        "schema_version": "qwen25_shared32_isolation_audit_v1",
        "passed": passed,
        "methods": list(METHODS),
        "folds": folds,
        "expected_question_count_per_method": expected_total,
        "question_counts": {method: len(ids_by_method[method]) for method in METHODS},
        "common_question_count": len(common_ids),
        "error_counts": errors,
        "protocol": protocol,
        "configs": configs,
        "method_roots": method_roots,
        "shared32_mismatch_count": len(shared_mismatches),
        "shared32_mismatches": shared_mismatches[:20],
        "local_random_control_signature_collision_count": len(intervention_mismatches),
        "gate_manifest_sha256": sha256_file(gate_path),
        "prediction_sha256": {
            method: canonical_sha256({key: loaded[method][1][key]["prediction"] for key in sorted(loaded[method][1], key=int)})
            for method in METHODS
        },
        "not_human_gold": True,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
