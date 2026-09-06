#!/usr/bin/env python3
"""Freeze A3 choices and audit one answer-free component ablation."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--reference-inference-root", type=Path, required=True)
    parser.add_argument(
        "--ablation",
        choices=("no_ocr", "no_segmented_asr", "no_local_crop"),
        required=True,
    )
    parser.add_argument("--a0-scores", type=Path, required=True)
    parser.add_argument("--a2-scores", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--support-threshold",
        type=float,
        default=0.8933094143867493,
    )
    parser.add_argument("--minimum-margin", type=float, default=0.25)
    parser.add_argument("--expected-count", type=int, default=50)
    parser.add_argument("--expected-videos", type=int, default=50)
    parser.add_argument("--expected-per-fold", type=int, default=10)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: Any) -> None:
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    items = load_jsonl(args.dataset_dir / "items_answer_free.jsonl")
    a0_scores = {
        str(row["source_question_id"]): row for row in load_jsonl(args.a0_scores)
    }
    a2_scores = {
        str(row["source_question_id"]): row for row in load_jsonl(args.a2_scores)
    }
    choices: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for item in items:
        qid = str(item["question_id"])
        fold = int(item["fold"])
        item_dir = args.inference_root / f"fold_{fold}" / qid
        reference_item_dir = args.reference_inference_root / f"fold_{fold}" / qid
        a1_path = reference_item_dir / "a1_prediction.json"
        a2_path = item_dir / "a2_prediction.json"
        a1_trace_path = reference_item_dir / "a1_trace.json"
        a2_trace_path = item_dir / "a2_trace.json"
        a1 = json.loads(a1_path.read_text(encoding="utf-8"))
        a2 = json.loads(a2_path.read_text(encoding="utf-8"))
        a1_trace = json.loads(a1_trace_path.read_text(encoding="utf-8"))
        a2_trace = json.loads(a2_trace_path.read_text(encoding="utf-8"))
        p0 = float(a0_scores[qid]["support_probability"])
        p2 = float(a2_scores[qid]["support_probability"])
        switch = (
            p2 >= args.support_threshold
            and p0 < args.support_threshold
            and p2 - p0 >= args.minimum_margin
        )
        a0_answer = str(item["a0_prediction"])
        a2_answer = str(a2["prediction"])
        choices.append({
            "schema_version": "qwen3_selective_evidence_rewrite_ablation_choice_v1",
            "ablation": args.ablation,
            "question_id": qid,
            "video_id": str(item["video_id"]),
            "fold": fold,
            "a0_prediction": a0_answer,
            "a1_prediction": str(a1["prediction"]),
            "a2_prediction": a2_answer,
            "a3_prediction": a2_answer if switch else a0_answer,
            "a3_selected_method": (
                f"Qwen3_AVEvidenceRewrite12_{args.ablation}"
                if switch
                else "CleanQwen3_Raw8_A0"
            ),
            "a3_switched": switch,
            "a3_answer_changed": switch and (
                " ".join(a2_answer.casefold().split())
                != " ".join(a0_answer.casefold().split())
            ),
            "a0_support_probability": p0,
            "a2_support_probability": p2,
            "support_difference_a2_minus_a0": p2 - p0,
            "support_threshold": args.support_threshold,
            "minimum_margin": args.minimum_margin,
            "a0_prediction_sha256": hashlib.sha256(
                a0_answer.encode("utf-8")
            ).hexdigest(),
            "a1_prediction_sha256": sha256_file(a1_path),
            "a2_prediction_sha256": sha256_file(a2_path),
        })
        a1_processor = a1_trace["processor_trace"]
        a2_processor = a2_trace["processor_trace"]
        traces.append({
            "question_id": qid,
            "fold": fold,
            "ablation": args.ablation,
            "trace_ablation": str(a2_trace["ablation"]),
            "a1_parse_valid": bool(a1_trace["parse_valid"]),
            "a2_parse_valid": bool(a2_trace["parse_valid"]),
            "a1_base_indices": [
                int(value) for value in a1_trace["base_source_frame_indices"]
            ],
            "a2_base_indices": [
                int(value) for value in a2_trace["base_source_frame_indices"]
            ],
            "expected_base_indices": [
                int(value) for value in item["a0_frame_indices"]
            ],
            "a1_views": int(a1_processor["represented_views"]),
            "a2_views": int(a2_processor["represented_views"]),
            "a1_visual_tokens": int(a1_processor["visual_tokens"]),
            "a2_visual_tokens": int(a2_processor["visual_tokens"]),
            "a1_secondary_sampling": bool(
                a1_processor["secondary_frame_sampling"]
            ),
            "a2_secondary_sampling": bool(
                a2_processor["secondary_frame_sampling"]
            ),
            "a2_extra_view_count": len(a2_trace["extra_view_plan"]),
            "a2_extra_view_types": [
                str(row["view_type"]) for row in a2_trace["extra_view_plan"]
            ],
            "ocr_evidence_count_supplied": int(
                a2_trace["ocr_evidence_count_supplied"]
            ),
            "segmented_asr_count_supplied": int(
                a2_trace["segmented_asr_count_supplied"]
            ),
            "local_crop_supplied": bool(a2_trace["local_crop_supplied"]),
        })

    choices.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    traces.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    selected_path = args.dataset_dir / "selection_manifest_private_support_only.jsonl"
    protocol_checks = {
        "dataset_expected_questions": len(items) == args.expected_count,
        "dataset_expected_videos": len({
            str(row["video_id"]) for row in items
        }) == args.expected_videos,
        "expected_questions_per_fold": all(
            sum(int(row["fold"]) == fold for row in items)
            == args.expected_per_fold
            for fold in range(5)
        ),
        "a0_scores_cover_selected": set(a0_scores) >= {
            str(row["question_id"]) for row in items
        },
        "a2_scores_exact_selected": set(a2_scores) == {
            str(row["question_id"]) for row in items
        },
        "all_generation_parses_valid": all(
            row["a1_parse_valid"] and row["a2_parse_valid"] for row in traces
        ),
        "a1_base_frames_match_a0": all(
            row["a1_base_indices"] == row["expected_base_indices"] for row in traces
        ),
        "a2_base_frames_match_a0": all(
            row["a2_base_indices"] == row["expected_base_indices"] for row in traces
        ),
        "a1_exactly_eight_views": all(row["a1_views"] == 8 for row in traces),
        "a2_exactly_twelve_views": all(row["a2_views"] == 12 for row in traces),
        "a2_four_frozen_extra_views": all(
            row["a2_extra_view_count"] == 4
            and row["a2_extra_view_types"]
            == (
                [
                    "evidence_full",
                    "evidence_highres_full_control",
                    "evidence_full",
                    "evidence_highres_full_control",
                ]
                if args.ablation == "no_local_crop"
                else [
                    "evidence_full",
                    "evidence_mid_crop",
                    "evidence_full",
                    "evidence_mid_crop",
                ]
            )
            for row in traces
        ),
        "ablation_content_matches_protocol": all(
            row["trace_ablation"] == args.ablation
            and (
                row["ocr_evidence_count_supplied"] == 0
                if args.ablation == "no_ocr"
                else row["segmented_asr_count_supplied"] == 0
                if args.ablation == "no_segmented_asr"
                else not row["local_crop_supplied"]
            )
            for row in traces
        ),
        "all_visual_tokens_within_4096": all(
            row["a1_visual_tokens"] <= 4096
            and row["a2_visual_tokens"] <= 4096
            for row in traces
        ),
        "secondary_sampling_disabled": all(
            not row["a1_secondary_sampling"] and not row["a2_secondary_sampling"]
            for row in traces
        ),
    }
    passed = all(protocol_checks.values())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    choices_path = args.output_dir / "frozen_choices_answer_free.jsonl"
    write_jsonl(choices_path, choices)
    write_jsonl(args.output_dir / "protocol_rows.jsonl", traces)
    audit = {
        "schema_version": "qwen3_selective_evidence_rewrite_ablation_audit_v1",
        "ablation": args.ablation,
        "protocol_checks": protocol_checks,
        "passed": passed,
        "rows": len(choices),
        "video_count": len({str(row["video_id"]) for row in choices}),
        "fold_counts": dict(Counter(str(row["fold"]) for row in choices)),
        "a3_gate_acceptances": sum(bool(row["a3_switched"]) for row in choices),
        "a3_actual_answer_changes": sum(
            bool(row["a3_answer_changed"]) for row in choices
        ),
        "a1_visual_token_range": [
            min(row["a1_visual_tokens"] for row in traces),
            max(row["a1_visual_tokens"] for row in traces),
        ],
        "a2_visual_token_range": [
            min(row["a2_visual_tokens"] for row in traces),
            max(row["a2_visual_tokens"] for row in traces),
        ],
        "support_threshold": args.support_threshold,
        "minimum_margin": args.minimum_margin,
        "expected_count": args.expected_count,
        "expected_videos": args.expected_videos,
        "expected_per_fold": args.expected_per_fold,
        "selection_used_groundtruth": False,
        "selection_used_judge_scores": False,
        "external_knowledge_used": False,
        "selection_manifest_sha256": sha256_file(selected_path),
        "a0_scores_sha256": sha256_file(args.a0_scores),
        "a2_scores_sha256": sha256_file(args.a2_scores),
        "choices_sha256": sha256_file(choices_path),
    }
    dump_json(args.output_dir / "protocol_audit.json", audit)
    if not passed:
        raise RuntimeError("protocol audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
