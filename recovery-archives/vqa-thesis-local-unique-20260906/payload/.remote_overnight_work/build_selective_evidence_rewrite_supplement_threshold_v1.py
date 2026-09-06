#!/usr/bin/env python3
"""Freeze AdsQA supplement questions selected by the calibrated threshold."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from build_selective_evidence_rewrite_smoke50_v1 import (
    FORBIDDEN,
    dump_json,
    load_av_manifest,
    load_jsonl,
    select_anchors,
    select_asr,
    select_ocr,
    sha256_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-dir", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--av-manifest", type=Path, required=True)
    parser.add_argument("--ocr-root", type=Path, required=True)
    parser.add_argument("--asr-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=2526)
    parser.add_argument("--trigger-count", type=int, required=True)
    parser.add_argument("--support-threshold", type=float, required=True)
    parser.add_argument("--runtime-folds", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if (
        args.expected_count != 2526
        or abs(args.support_threshold - 0.9602926671504974) > 1e-12
        or args.runtime_folds != 5
    ):
        raise RuntimeError("frozen full-set trigger protocol changed")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    pool = load_jsonl(args.pool_dir / "model_inputs_all.jsonl")
    source_manifest = {
        str(row["question_id"]): row
        for row in load_jsonl(args.pool_dir / "source_manifest.jsonl")
    }
    scores = load_jsonl(args.scores)
    pool_by_verifier = {str(row["question_id"]): row for row in pool}
    av_manifest = load_av_manifest(args.av_manifest)
    if (
        len(pool) != args.expected_count
        or len(scores) != args.expected_count
        or set(pool_by_verifier)
        != {str(row["question_id"]) for row in scores}
    ):
        raise RuntimeError("full-set A0 pool and scores do not align")

    candidates: list[dict[str, Any]] = []
    for score in scores:
        source = pool_by_verifier[str(score["question_id"])]
        row = {
            "question_id": str(source["source_question_id"]),
            "video_id": str(source["video_id"]),
            "source_fold": int(source["fold"]),
            "support_probability": float(score["support_probability"]),
            "pool": source,
        }
        if float(row["support_probability"]) < args.support_threshold:
            candidates.append(row)
    candidates.sort(
        key=lambda row: (
            float(row["support_probability"]),
            str(row["video_id"]),
            str(row["question_id"]),
        )
    )
    selected = candidates
    if len(selected) != args.trigger_count:
        raise RuntimeError(
            f"calibrated threshold selected {len(selected)}, "
            f"expected {args.trigger_count}"
        )

    items = []
    selection_rows = []
    for rank, candidate in enumerate(selected):
        source = candidate["pool"]
        qid = str(candidate["question_id"])
        video = str(candidate["video_id"])
        runtime_fold = rank % args.runtime_folds
        if qid not in av_manifest:
            raise RuntimeError(f"AV manifest misses {qid}")
        source_row = source_manifest[qid]
        ocr_path = args.ocr_root / f"{video}.json"
        asr_path = args.asr_root / f"{video}.json"
        ocr, ocr_quality = select_ocr(ocr_path, str(source["question"]))
        asr, asr_quality, asr_full = select_asr(
            asr_path, str(source["question"])
        )
        items.append(
            {
                "question_id": qid,
                "video_id": video,
                "fold": runtime_fold,
                "source_fold": int(candidate["source_fold"]),
                "question": str(source["question"]),
                "a0_prediction": str(source["claim"]),
                "a0_asr_excerpt": str(source.get("asr_excerpt", "")),
                "a0_frame_indices": [
                    int(value) for value in source["selected_frame_indices"]
                ],
                "video_path": str(source["video_path"]),
                "evidence_anchors": select_anchors(av_manifest[qid]),
                "ocr_evidence": ocr,
                "ocr_quality": ocr_quality,
                "asr_evidence": asr,
                "asr_quality": asr_quality,
                "asr_full_text": asr_full,
            }
        )
        selection_rows.append(
            {
                "selection_rank": rank,
                "question_id": qid,
                "video_id": video,
                "runtime_fold": runtime_fold,
                "source_fold": int(candidate["source_fold"]),
                "a0_support_probability": float(
                    candidate["support_probability"]
                ),
                "a0_prediction_path": source_row["a0_prediction_path"],
                "a0_prediction_sha256": source_row["a0_prediction_sha256"],
                "a0_evidence_path": source_row["a0_evidence_path"],
                "a0_evidence_sha256": source_row["a0_evidence_sha256"],
                "ocr_cache_sha256": sha256_file(ocr_path),
                "asr_cache_sha256": sha256_file(asr_path),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=False)
    items_path = args.output_dir / "items_answer_free.jsonl"
    selection_path = (
        args.output_dir / "selection_manifest_private_support_only.jsonl"
    )
    items_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in items),
        encoding="utf-8",
    )
    selection_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in selection_rows
        ),
        encoding="utf-8",
    )
    for fold in range(args.runtime_folds):
        path = args.output_dir / "shards" / f"fold_{fold}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in items
                if int(row["fold"]) == fold
            ),
            encoding="utf-8",
        )
    probabilities = [
        float(row["a0_support_probability"]) for row in selection_rows
    ]
    audit = {
        "schema_version": "qwen3_selective_rewrite_supplement_threshold_audit_v1",
        "passed": (
            len(items) == args.trigger_count
            and max(
                sum(int(row["fold"]) == fold for row in items)
                for fold in range(args.runtime_folds)
            )
            - min(
                sum(int(row["fold"]) == fold for row in items)
                for fold in range(args.runtime_folds)
            )
            <= 1
            and all(not (FORBIDDEN & set(row)) for row in items)
        ),
        "question_count": len(items),
        "video_count": len({str(row["video_id"]) for row in items}),
        "runtime_fold_counts": dict(
            Counter(str(row["fold"]) for row in items)
        ),
        "source_fold_counts": dict(
            Counter(str(row["source_fold"]) for row in items)
        ),
        "selection_policy": "a0_support_probability_below_frozen_threshold_v1",
        "support_threshold": args.support_threshold,
        "trigger_rate_over_questions": len(items) / args.expected_count,
        "a0_support_min": min(probabilities),
        "a0_support_max": max(probabilities),
        "all_support_below_threshold": all(
            probability < args.support_threshold for probability in probabilities
        ),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "items_sha256": sha256_file(items_path),
        "selection_sha256": sha256_file(selection_path),
    }
    dump_json(args.output_dir / "audit.json", audit)
    if not audit["passed"]:
        raise RuntimeError("full threshold trigger audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
