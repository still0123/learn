#!/usr/bin/env python3
"""Freeze fold-train-only modality routes and emit a fixed 40-view manifest."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    PROTOCOL_VERSION,
    RAW_GLOBAL_VIEW_COUNT,
    canonical_json_sha256,
    sha256_file,
    validate_shared_gate_manifest,
)


ASR_TRAIN_QUANTILE = 0.75
MIN_MODALITY_DRIVEN_CROPS = 2
MIN_SIGNATURE_DIFFERENCE = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-features", required=True)
    parser.add_argument("--fold-assignments", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot freeze an ASR threshold from an empty train fold")
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def crop_signature(spec: Mapping[str, Any]) -> tuple[int, tuple[float, ...]]:
    return (
        int(spec["source_global_rank"]),
        tuple(round(float(value), 6) for value in spec["bbox_norm"]),
    )


def signature_difference(first: Sequence[Mapping[str, Any]], second: Sequence[Mapping[str, Any]]) -> int:
    first_set = {crop_signature(spec) for spec in first}
    second_set = {crop_signature(spec) for spec in second}
    return max(len(first_set - second_set), len(second_set - first_set))


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw_features).resolve()
    fold_path = Path(args.fold_assignments).resolve()
    output_path = Path(args.output).resolve()
    raw_rows = load_jsonl(raw_path)
    raw_by_id = {str(row["question_id"]): row for row in raw_rows}
    if len(raw_rows) != 500 or len(raw_by_id) != 500:
        raise ValueError("raw feature manifest must contain 500 unique questions")
    folds = json.loads(fold_path.read_text(encoding="utf-8"))["folds"]
    records = []
    diagnostics = []
    for fold in folds:
        fold_id = int(fold["fold"])
        train_ids = [str(value) for value in fold["train_question_ids"]]
        validation_ids = [str(value) for value in fold["validation_question_ids"]]
        train_contrasts = [
            float(raw_by_id[question_id]["asr_relevance_contrast"])
            for question_id in train_ids
            if int(raw_by_id[question_id]["asr_modality_driven_crop_count"]) >= MIN_MODALITY_DRIVEN_CROPS
        ]
        threshold = percentile(train_contrasts, ASR_TRAIN_QUANTILE)
        fold_routes = Counter()
        fold_active = 0
        for question_id in validation_ids:
            raw = raw_by_id[question_id]
            clip_specs = raw["clip_crop_specs"]
            selected_specs = clip_specs
            requested_route = "clip_fallback"
            if raw["matched_ocr_query_terms"] and int(raw["ocr_modality_driven_crop_count"]) >= MIN_MODALITY_DRIVEN_CROPS:
                requested_route = "ocr_explicit"
                selected_specs = raw["ocr_crop_specs"]
            elif raw["matched_audio_query_terms"] and int(raw["asr_modality_driven_crop_count"]) >= MIN_MODALITY_DRIVEN_CROPS:
                requested_route = "asr_explicit"
                selected_specs = raw["asr_crop_specs"]
            elif (
                int(raw["asr_modality_driven_crop_count"]) >= MIN_MODALITY_DRIVEN_CROPS
                and float(raw["asr_relevance_contrast"]) >= threshold
            ):
                requested_route = "asr_high_confidence"
                selected_specs = raw["asr_crop_specs"]
            difference = signature_difference(clip_specs, selected_specs)
            modality_active = requested_route != "clip_fallback" and difference >= MIN_SIGNATURE_DIFFERENCE
            route = requested_route if modality_active else "clip_fallback"
            if not modality_active:
                selected_specs = clip_specs
                difference = 0
            fold_routes[route] += 1
            fold_active += int(modality_active)
            rule = {
                "version": f"modality_active_groupcv_fold{fold_id}_v1",
                "asr_train_quantile": ASR_TRAIN_QUANTILE,
                "asr_relevance_contrast_threshold": threshold,
                "minimum_modality_driven_crops": MIN_MODALITY_DRIVEN_CROPS,
                "minimum_signature_difference": MIN_SIGNATURE_DIFFERENCE,
                "fit_scope": "outer_fold_train_questions_only",
                "fit_question_count": len(train_ids),
                "fit_question_ids_sha256": canonical_json_sha256(sorted(train_ids, key=int)),
            }
            decision = {
                "protocol_version": PROTOCOL_VERSION,
                "gate_rule": rule,
                "modality_route": route,
                "requested_modality_route": requested_route,
                "modality_active": modality_active,
                "permitted_evidence_summary": {
                    "usable_asr_segment_count": int(raw["usable_asr_segment_count"]),
                    "usable_ocr_detection_count": int(raw["usable_ocr_detection_count"]),
                    "asr_modality_driven_crop_count": int(raw["asr_modality_driven_crop_count"]),
                    "ocr_modality_driven_crop_count": int(raw["ocr_modality_driven_crop_count"]),
                    "asr_relevance_contrast": float(raw["asr_relevance_contrast"]),
                    "crop_signature_difference_vs_clip": difference,
                },
                "criteria": {
                    "preinference_modality_available": requested_route != "clip_fallback",
                    "crop_signature_differs": modality_active,
                    "fixed_local_budget": True,
                },
                "append_crop8": True,
                "local_view_count": APPENDED_LOCAL_VIEW_COUNT,
                "submitted_view_count": RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT,
                "decision_reason": route,
            }
            records.append(
                {
                    "schema_version": "qwen25_modality_active_gate_manifest_v1",
                    "question_id": question_id,
                    "video_id": str(raw["video_id"]),
                    "fold": fold_id,
                    "append_crop8": True,
                    "local_view_count": APPENDED_LOCAL_VIEW_COUNT,
                    "submitted_view_count": RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT,
                    "gate_decision": decision,
                    "clip_crop_specs": clip_specs,
                    "av_crop_specs": selected_specs,
                    "raw_feature_sha256": canonical_json_sha256(raw),
                    "manifest_inputs": {
                        "raw_features_sha256": sha256_file(raw_path),
                        "fold_assignments_sha256": sha256_file(fold_path),
                    },
                }
            )
        diagnostics.append(
            {
                "fold": fold_id,
                "asr_relevance_contrast_threshold": threshold,
                "train_eligible_asr_count": len(train_contrasts),
                "validation_count": len(validation_ids),
                "active_count": fold_active,
                "route_counts": dict(sorted(fold_routes.items())),
            }
        )
    records.sort(key=lambda row: int(row["question_id"]))
    audit = validate_shared_gate_manifest(records)
    routes = Counter(row["gate_decision"]["modality_route"] for row in records)
    active_rows = [row for row in records if row["gate_decision"]["modality_active"]]
    result = {
        "schema_version": "qwen25_modality_active_gate_freeze_audit_v1",
        "passed": audit["record_count"] == 500 and audit["gate_hit_count"] == 500,
        "manifest_audit": audit,
        "modality_active_question_count": len(active_rows),
        "modality_active_video_count": len({row["video_id"] for row in active_rows}),
        "route_counts": dict(sorted(routes.items())),
        "fold_diagnostics": diagnostics,
        "raw_features_sha256": sha256_file(raw_path),
        "fold_assignments_sha256": sha256_file(fold_path),
        "validation_answers_used": False,
        "testset_used": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in records), encoding="utf-8")
    result["output_manifest_sha256"] = sha256_file(output_path)
    output_path.with_suffix(".audit.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
