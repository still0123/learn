#!/usr/bin/env python3
"""Freeze E-VAds evidence with answer-free SigLIP spatial anchors."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from build_evads_mmr_selectrescue_trigger100_v1 import (
    FORBIDDEN,
    dump_json,
    load_jsonl,
    parse_events,
    rank_events,
    select_anchor_events,
    select_text_evidence,
    sha256_file,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-dir", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--av-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--support-threshold", type=float, required=True)
    parser.add_argument("--expected-source-count", type=int, required=True)
    parser.add_argument("--expected-trigger-count", type=int)
    parser.add_argument("--minimum-trigger-count", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0.0 <= args.support_threshold <= 1.0:
        raise RuntimeError("support threshold must be in [0, 1]")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if (
        not isinstance(questions, list)
        or len(questions) != args.expected_source_count
        or any(FORBIDDEN & set(row) for row in questions)
    ):
        raise RuntimeError("questions do not match frozen answer-free protocol")
    question_by_id = {str(row["question_id"]): row for row in questions}
    av_rows = load_jsonl(args.av_manifest)
    av_by_id = {str(row["question_id"]): row for row in av_rows}
    if len(av_by_id) != args.expected_source_count or set(av_by_id) != set(question_by_id):
        raise RuntimeError("AV manifest does not align with frozen questions")
    pool = load_jsonl(args.pool_dir / "model_inputs_all.jsonl")
    pool_by_verifier = {str(row["question_id"]): row for row in pool}
    sources = {
        str(row["question_id"]): row
        for row in load_jsonl(args.pool_dir / "source_manifest.jsonl")
    }
    scores = load_jsonl(args.scores)
    if (
        len(pool) != args.expected_source_count
        or len(scores) != args.expected_source_count
        or set(pool_by_verifier)
        != {str(row["question_id"]) for row in scores}
    ):
        raise RuntimeError("A0 pool and verifier scores do not align")

    candidates: list[dict[str, Any]] = []
    for score in scores:
        source = pool_by_verifier[str(score["question_id"])]
        probability = float(score["support_probability"])
        if probability <= args.support_threshold:
            candidates.append({
                "question_id": str(source["source_question_id"]),
                "video_id": str(source["video_id"]),
                "fold": int(source["fold"]),
                "support_probability": probability,
                "pool": source,
            })
    candidates.sort(
        key=lambda row: (
            int(row["fold"]),
            float(row["support_probability"]),
            str(row["question_id"]),
        )
    )
    if len(candidates) < args.minimum_trigger_count:
        raise RuntimeError("threshold trigger count is below the frozen minimum")
    if (
        args.expected_trigger_count is not None
        and len(candidates) != args.expected_trigger_count
    ):
        raise RuntimeError(
            f"threshold trigger count changed: {len(candidates)} "
            f"!= {args.expected_trigger_count}"
        )

    items: list[dict[str, Any]] = []
    selection: list[dict[str, Any]] = []
    for candidate in candidates:
        qid = str(candidate["question_id"])
        question = question_by_id[qid]
        source = candidate["pool"]
        source_record = sources[qid]
        events, duration = parse_events(str(question["multimodal_context"]))
        ocr, asr = select_text_evidence(str(question["question"]), events)
        evidence_anchors = []
        av_record = av_by_id[qid]
        mid_specs = sorted(
            (
                spec for spec in av_record["funnel_crop_specs"]
                if str(spec["scale_level"]) == "mid"
            ),
            key=lambda spec: int(spec["anchor_index"]),
        )
        if len(mid_specs) != 2 or [int(spec["anchor_index"]) for spec in mid_specs] != [0, 1]:
            raise RuntimeError(f"question {qid} does not have two AV mid-scale anchors")
        for anchor in mid_specs:
            evidence_anchors.append({
                "anchor_index": int(anchor["anchor_index"]),
                "source_global_rank": int(anchor["source_global_rank"]),
                "source_frame_index": int(anchor["source_frame_index"]),
                "bbox_norm": [float(value) for value in anchor["bbox_norm"]],
                "bbox_source": "siglip_3x3_grid_response",
                "fusion_score": float(anchor["fusion_score"]),
                "visual_rank_score": float(anchor["visual_rank_score"]),
                "asr_rank_score": float(anchor["asr_score"]),
                "ocr_rank_score": float(anchor["ocr_score"]),
                "entropy_proxy": float(anchor["entropy_proxy"]),
                "crop_mode": "evads_av_funnel_mid_entropy_v1",
            })
        items.append({
            "question_id": qid,
            "video_id": str(candidate["video_id"]),
            "fold": int(candidate["fold"]),
            "question": str(question["question"]),
            "a0_prediction": str(source["claim"]),
            "a0_asr_excerpt": str(source.get("asr_excerpt", "")),
            "a0_frame_indices": [
                int(value) for value in source["selected_frame_indices"]
            ],
            "video_path": str(source["video_path"]),
            "evidence_anchors": evidence_anchors,
            "ocr_evidence": ocr,
            "ocr_quality": {
                "status": "official_time_aligned_text",
                "selected_count": len(ocr),
            },
            "asr_evidence": asr,
            "asr_quality": {
                "status": "official_time_aligned_text",
                "selected_count": len(asr),
            },
            "asr_full_text": str(source.get("asr_excerpt", "")),
        })
        selection.append({
            "question_id": qid,
            "video_id": str(candidate["video_id"]),
            "fold": int(candidate["fold"]),
            "a0_support_probability": float(candidate["support_probability"]),
            "a0_prediction_path": source_record["a0_prediction_path"],
            "a0_prediction_sha256": source_record["a0_prediction_sha256"],
            "a0_evidence_path": source_record["a0_evidence_path"],
            "a0_evidence_sha256": source_record["a0_evidence_sha256"],
        })

    args.output_dir.mkdir(parents=True, exist_ok=False)
    items_path = args.output_dir / "items_answer_free.jsonl"
    selection_path = (
        args.output_dir / "selection_manifest_private_support_only.jsonl"
    )
    write_jsonl(items_path, items)
    write_jsonl(selection_path, selection)
    for fold in range(5):
        write_jsonl(
            args.output_dir / "shards" / f"fold_{fold}.jsonl",
            [row for row in items if int(row["fold"]) == fold],
        )
    fold_counts = Counter(int(row["fold"]) for row in items)
    audit = {
        "schema_version": "evads_threshold_crop_or_full_dataset_audit_v1",
        "passed": True,
        "source_question_count": args.expected_source_count,
        "question_count": len(items),
        "video_count": len({str(row["video_id"]) for row in items}),
        "fold_counts": dict(sorted(fold_counts.items())),
        "trigger_rule": "a0_support_probability_lte_frozen_threshold",
        "support_threshold": args.support_threshold,
        "trigger_rate": len(items) / args.expected_source_count,
        "anchor_rule": "siglip_visual_rank055_asr030_ocr015_two_temporally_separated",
        "crop_rule": "siglip_3x3_centered_av_funnel_mid_with_normalized_entropy",
        "ocr_confidence_semantics": "presence_flag_not_detector_probability",
        "answer_free": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "scores_sha256": sha256_file(args.scores),
        "questions_sha256": sha256_file(args.questions),
        "av_manifest_sha256": sha256_file(args.av_manifest),
        "items_sha256": sha256_file(items_path),
        "selection_sha256": sha256_file(selection_path),
    }
    dump_json(args.output_dir / "audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
