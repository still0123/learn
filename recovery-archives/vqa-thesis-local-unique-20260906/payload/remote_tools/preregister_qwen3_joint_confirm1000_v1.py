#!/usr/bin/env python3
"""Write the immutable four-arm protocol for the joint Qwen3 Confirm-1000 run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--confirm-manifest", type=Path, required=True)
    parser.add_argument("--asr-union-audit", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--adapter-config", type=Path, required=True)
    parser.add_argument("--adapter-weights", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", default=[])
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    protocol_path = args.run_root / "PREREGISTERED_PROTOCOL.json"
    frozen_path = args.run_root / "FROZEN_PROTOCOL"
    if protocol_path.exists() or frozen_path.exists():
        raise RuntimeError("protocol is already frozen")
    args.run_root.mkdir(parents=True, exist_ok=True)
    sources = [
        {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
        }
        for path in args.source
    ]
    protocol = {
        "schema_version": "adsqa_qwen3_joint_confirm1000_protocol_v1",
        "status": "frozen_before_inference",
        "dataset": {
            "questions_path": str(args.questions.resolve()),
            "questions_sha256": sha256_file(args.questions),
            "confirm_manifest_path": str(args.confirm_manifest.resolve()),
            "confirm_manifest_sha256": sha256_file(args.confirm_manifest),
            "question_count": 1000,
            "unique_video_count": 1000,
            "primary_type_counts": {
                f"Type_{index}": 200 for index in range(1, 6)
            },
            "private_references_not_read_before_judging": True,
            "not_global_historical_blind": True,
        },
        "evidence_assets": {
            "asr_union_audit_path": str(args.asr_union_audit.resolve()),
            "asr_union_audit_sha256": sha256_file(args.asr_union_audit),
            "asr_aggregate_sha256": (
                "084446e1f685647d402115d3284ab368c95b121387ae7880d41b07024e9ebbd6"
            ),
            "video_clip_ocr_asr_expected_coverage": 1000,
        },
        "models": {
            "answer_model": "clean_Qwen3-VL-8B",
            "answer_model_config": str(args.model_config.resolve()),
            "answer_model_config_sha256": sha256_file(args.model_config),
            "answer_adapter": None,
            "support_verifier": "Qwen3-VL-8B_RealClaim985_LoRA",
            "support_adapter_config": str(args.adapter_config.resolve()),
            "support_adapter_config_sha256": sha256_file(args.adapter_config),
            "support_adapter_weights": str(args.adapter_weights.resolve()),
            "support_adapter_weights_sha256": sha256_file(args.adapter_weights),
        },
        "shared_generation": {
            "deterministic_decoding": True,
            "answer_max_new_tokens": 256,
            "rewrite_max_new_tokens": 192,
            "secondary_frame_sampling_disabled": True,
            "external_knowledge_used": False,
            "base_asr_condition_shared": True,
        },
        "arms": {
            "Uniform8": {
                "role": "primary_baseline_and_A0",
                "selection": "eight_uniform_chronological_frames",
                "views": 8,
                "size": 512,
                "expected_visual_tokens": 1024,
            },
            "MMR8": {
                "role": "strong_static_secondary_baseline",
                "selection": "CLIP64_MMR8_lambda_0.70_then_chronological",
                "views": 8,
                "size": 512,
                "expected_visual_tokens": 1024,
                "parameter_scan_on_confirm1000": False,
            },
            "ExtraGlobalControl": {
                "role": "same_trigger_same_compute_control",
                "trigger": "global_lowest_A0_support_100_of_1000",
                "base_views": 8,
                "extra_views": [
                    "anchor1_full_512",
                    "anchor1_uncropped_full_896",
                    "anchor2_full_512",
                    "anchor2_uncropped_full_896",
                ],
                "total_views": 12,
                "expected_visual_tokens": 3104,
                "ocr_asr_and_anchor_inputs_match_full_method": True,
            },
            "FullJointMethod": {
                "role": "primary_method",
                "trigger": "global_lowest_A0_support_100_of_1000",
                "base_views": 8,
                "extra_views": [
                    "anchor1_full_512",
                    "anchor1_mid_crop_896",
                    "anchor2_full_512",
                    "anchor2_mid_crop_896",
                ],
                "total_views": 12,
                "expected_visual_tokens": 3104,
                "uses_question_visual_OCR_segmented_ASR_evidence": True,
            },
        },
        "selection_and_gate": {
            "trigger_rate": 0.10,
            "trigger_count": 100,
            "trigger_rank": "A0_support_probability_ascending_then_question_id",
            "support_threshold": 0.8933094143867493,
            "minimum_margin_A2_minus_A0": 0.25,
            "switch_rule": (
                "P(A2)>=threshold and P(A0)<threshold and "
                "P(A2)-P(A0)>=0.25"
            ),
            "otherwise_fallback_to_A0": True,
            "same_rule_for_full_and_control": True,
        },
        "hypotheses": {
            "primary": "FullJointMethod improves Strict and Relaxed over Uniform8",
            "secondary_static": "FullJointMethod is competitive with or better than MMR8",
            "secondary_mechanism": (
                "FullJointMethod outperforms same-trigger same-token "
                "ExtraGlobalControl"
            ),
        },
        "metrics": [
            "Strict",
            "Relaxed",
            "paired_win_tie_loss",
            "wrong_to_right",
            "right_to_wrong",
            "correction_precision",
            "trigger_rate",
            "switch_rate",
            "mean_visual_tokens",
            "latency",
            "video_cluster_bootstrap_10000",
            "Type1_to_Type5_strata",
        ],
        "decision_boundary": {
            "no_threshold_prompt_trigger_margin_anchor_OCR_ASR_crop_token_tuning": True,
            "no_posthoc_choice_between_full_and_control": True,
            "no_question_replacement_after_results": True,
            "no_DeepSeek_judging_without_separate_user_authorization": True,
            "report_point_estimates_and_confidence_intervals_together": True,
        },
        "source_snapshots": sources,
    }
    dump_json(protocol_path, protocol)
    frozen_path.write_text(sha256_file(protocol_path) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "protocol_path": str(protocol_path.resolve()),
                "protocol_sha256": sha256_file(protocol_path),
                "source_count": len(sources),
                "status": "frozen_before_inference",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
