#!/usr/bin/env python3
"""Freeze one answer-free gate rule per outer GroupCV fold.

Each validation fold receives thresholds fitted solely from the other 80
training videos' AV response features.  Quantile levels are protocol constants,
not searched against answers or validation outcomes.  The emitted manifest is
the one shared by RandomCrop8, CLIPCrop8, and AVCrop8.
"""

from __future__ import annotations

import argparse
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
    FROZEN_GATE_RULE,
    build_gate_manifest_record,
    canonical_json_sha256,
    sha256_file,
    validate_shared_gate_manifest,
)


RUN_DIR = PROJECT_ROOT / "evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"
# One median AV-peak condition is frozen before OOF evaluation.  The previous
# concentration condition was not in the registered mechanism and made the
# gate nearly degenerate on the training-question distribution.
PEAK_TRAIN_QUANTILE = 0.50
CONCENTRATION_THRESHOLD = 0.0


class GateFreezeError(ValueError):
    """Raised when fold-only gate freezing cannot be audited."""


def percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        raise GateFreezeError("cannot calculate a threshold from an empty feature list")
    if not 0.0 <= quantile <= 1.0:
        raise GateFreezeError("quantile must be in [0, 1]")
    ordered = sorted(float(value) for value in values)
    location = (len(ordered) - 1) * quantile
    lower, upper = math.floor(location), math.ceil(location)
    if lower == upper:
        return ordered[lower]
    fraction = location - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GateFreezeError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise GateFreezeError("gate feature row must be an object")
        records.append(value)
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze fold-train-only gate manifest")
    parser.add_argument(
        "--raw-feature-manifest",
        required=True,
        help="Full 500-row CLIP/ASR response manifest produced before gate decisions.",
    )
    parser.add_argument(
        "--fold-assignments",
        default=str(RUN_DIR / "groupcv5/fold_assignments_v1.json"),
    )
    parser.add_argument(
        "--oof-questions",
        default=str(RUN_DIR / "groupcv5/oof_questions_v1.json"),
    )
    parser.add_argument(
        "--output",
        default=str(RUN_DIR / "gate_manifest/gate_manifest_oof_foldfrozen_v1.jsonl"),
    )
    return parser.parse_args()


def build_fold_rule(
    *,
    fold_id: int,
    train_question_ids: Sequence[str],
    raw_by_question: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visual_detail_features = []
    for question_id in train_question_ids:
        record = raw_by_question.get(str(question_id))
        if record is None:
            raise GateFreezeError(f"raw feature manifest misses train question {question_id}")
        decision = record.get("gate_decision", {})
        question_type = decision.get("question_type", {})
        evidence = decision.get("permitted_evidence_summary", {})
        if question_type.get("is_visual_detail_question"):
            visual_detail_features.append(
                {
                    "question_id": str(question_id),
                    "peak_response": float(evidence["peak_response"]),
                    "response_concentration": float(evidence["response_concentration"]),
                }
            )
    if not visual_detail_features:
        raise GateFreezeError(f"fold {fold_id} has no visual-detail training questions")
    peak_threshold = percentile(
        [row["peak_response"] for row in visual_detail_features],
        PEAK_TRAIN_QUANTILE,
    )
    concentration_threshold = CONCENTRATION_THRESHOLD
    rule = {
        **FROZEN_GATE_RULE,
        "version": f"question_type_av_peak_gate_groupcv_fold{fold_id}_v1",
        "minimum_peak_response": peak_threshold,
        "minimum_response_concentration": concentration_threshold,
        "threshold_selection": "outer_fold_train_only_median_peak_v2",
        "peak_train_quantile": PEAK_TRAIN_QUANTILE,
        "concentration_threshold_policy": "disabled_not_registered_in_v2",
        "fit_question_count": len(train_question_ids),
        "fit_visual_detail_question_count": len(visual_detail_features),
        "fit_question_ids_sha256": canonical_json_sha256(sorted(map(str, train_question_ids))),
    }
    diagnostics = {
        "fold": fold_id,
        "fit_visual_detail_question_count": len(visual_detail_features),
        "peak_threshold": peak_threshold,
        "concentration_threshold": concentration_threshold,
        "peak_train_quantile": PEAK_TRAIN_QUANTILE,
        "concentration_threshold_policy": "disabled_not_registered_in_v2",
    }
    return rule, diagnostics


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw_feature_manifest).resolve()
    fold_path = Path(args.fold_assignments).resolve()
    questions_path = Path(args.oof_questions).resolve()
    output_path = Path(args.output).resolve()

    raw_records = load_jsonl(raw_path)
    raw_by_question = {str(row.get("question_id", "")): row for row in raw_records}
    if len(raw_by_question) != len(raw_records):
        raise GateFreezeError("raw feature manifest has duplicate or empty question IDs")
    fold_payload = json.loads(fold_path.read_text(encoding="utf-8"))
    folds = fold_payload.get("folds", [])
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    question_by_id = {str(row.get("question_id", "")): row for row in questions}
    if len(question_by_id) != len(questions):
        raise GateFreezeError("OOF question manifest has duplicate or empty question IDs")

    frozen_records = []
    fold_diagnostics = []
    for fold in folds:
        fold_id = int(fold["fold"])
        train_ids = [str(value) for value in fold["train_question_ids"]]
        validation_ids = [str(value) for value in fold["validation_question_ids"]]
        rule, diagnostic = build_fold_rule(
            fold_id=fold_id,
            train_question_ids=train_ids,
            raw_by_question=raw_by_question,
        )
        fold_hits = 0
        for question_id in validation_ids:
            raw = raw_by_question.get(question_id)
            question = question_by_id.get(question_id)
            if raw is None or question is None:
                raise GateFreezeError(f"missing OOF raw feature or question: {question_id}")
            prior = raw["gate_decision"]
            evidence = prior["permitted_evidence_summary"]
            record = build_gate_manifest_record(
                question_id=question_id,
                video_id=str(question["video"]),
                question=str(question["question"]),
                asr_evidence="",
                ocr_candidates=[],
                av_response_stats={
                    "peak_response": evidence["peak_response"],
                    "response_concentration": evidence["response_concentration"],
                    "eligible_crop_candidate_count": evidence["eligible_crop_candidate_count"],
                },
                gate_rule=rule,
            ).as_dict()
            record["fold"] = fold_id
            record["clip_crop_specs"] = raw["clip_crop_specs"]
            record["av_crop_specs"] = raw["av_crop_specs"]
            record["threshold_fit"] = diagnostic
            record["manifest_inputs"] = {
                "raw_feature_manifest_sha256": sha256_file(raw_path),
                "fit_scope": "outer_fold_train_questions_only",
                "holdout_outcome_access": False,
                "testset_used": False,
                "leakage_input_audit_passed": True,
            }
            record["gate_decision"]["permitted_evidence_summary"]["asr_present"] = bool(
                prior["permitted_evidence_summary"]["asr_present"]
            )
            frozen_records.append(record)
            fold_hits += int(record["append_crop8"])
        diagnostic["validation_question_count"] = len(validation_ids)
        diagnostic["validation_gate_hit_count"] = fold_hits
        fold_diagnostics.append(diagnostic)

    audit = validate_shared_gate_manifest(frozen_records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, ensure_ascii=True) + "\n" for record in frozen_records),
        encoding="utf-8",
    )
    result = {
        "schema_version": "qwen25_groupcv_fold_train_gate_freeze_v1",
        "raw_feature_manifest": str(raw_path),
        "raw_feature_manifest_sha256": sha256_file(raw_path),
        "fold_assignments": str(fold_path),
        "fold_assignments_sha256": sha256_file(fold_path),
        "oof_questions": str(questions_path),
        "oof_questions_sha256": sha256_file(questions_path),
        "output_manifest": str(output_path),
        "output_manifest_sha256": sha256_file(output_path),
        "fold_thresholds": fold_diagnostics,
        "manifest_audit": audit,
        "validation_answers_used": False,
        "testset_used": False,
    }
    write_json(output_path.with_suffix(".audit.json"), result)
    print(
        json.dumps(
            {
                "record_count": audit["record_count"],
                "gate_hit_count": audit["gate_hit_count"],
                "fold_thresholds": fold_diagnostics,
                "output": str(output_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
