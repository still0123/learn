#!/usr/bin/env python3
"""Select the frozen lowest-support 10% of Confirm-1000 for evidence rewriting."""

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
    parser.add_argument("--trigger-count", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.trigger_count != 100:
        raise RuntimeError("frozen Confirm-1000 protocol requires exactly 100 triggers")
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
    if len(pool) != 1000 or len(scores) != 1000:
        raise RuntimeError("Confirm-1000 A0 pool and score coverage must both be 1000")
    if set(pool_by_verifier) != {str(row["question_id"]) for row in scores}:
        raise RuntimeError("Confirm-1000 A0 pool and scores do not align")

    ranked: list[dict[str, Any]] = []
    for score in scores:
        source = pool_by_verifier[str(score["question_id"])]
        ranked.append(
            {
                "question_id": str(source["source_question_id"]),
                "video_id": str(source["video_id"]),
                "source_fold": int(source["fold"]),
                "support_probability": float(score["support_probability"]),
                "pool": source,
            }
        )
    ranked.sort(
        key=lambda row: (
            float(row["support_probability"]),
            str(row["question_id"]),
        )
    )
    selected = ranked[: args.trigger_count]
    if len(selected) != 100 or len({str(row["video_id"]) for row in selected}) != 100:
        raise RuntimeError("global lowest-support selection is not 100 unique videos")

    items: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    for rank, candidate in enumerate(selected):
        source = candidate["pool"]
        question_id = str(candidate["question_id"])
        video_id = str(candidate["video_id"])
        runtime_fold = rank % 5
        if question_id not in av_manifest:
            raise RuntimeError(f"AV manifest misses {question_id}")
        source_row = source_manifest[question_id]
        ocr_path = args.ocr_root / f"{video_id}.json"
        asr_path = args.asr_root / f"{video_id}.json"
        ocr, ocr_quality = select_ocr(ocr_path, str(source["question"]))
        asr, asr_quality, asr_full = select_asr(
            asr_path,
            str(source["question"]),
        )
        items.append(
            {
                "question_id": question_id,
                "video_id": video_id,
                "fold": runtime_fold,
                "source_fold": int(candidate["source_fold"]),
                "question": str(source["question"]),
                "a0_prediction": str(source["claim"]),
                "a0_asr_excerpt": str(source.get("asr_excerpt", "")),
                "a0_frame_indices": [
                    int(value) for value in source["selected_frame_indices"]
                ],
                "video_path": str(source["video_path"]),
                "evidence_anchors": select_anchors(av_manifest[question_id]),
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
                "question_id": question_id,
                "video_id": video_id,
                "runtime_fold": runtime_fold,
                "source_fold": int(candidate["source_fold"]),
                "a0_support_probability": float(candidate["support_probability"]),
                "a0_prediction_path": source_row["a0_prediction_path"],
                "a0_prediction_sha256": source_row["a0_prediction_sha256"],
                "a0_evidence_path": source_row["a0_evidence_path"],
                "a0_evidence_sha256": source_row["a0_evidence_sha256"],
                "ocr_cache_path": str(ocr_path.resolve()),
                "ocr_cache_sha256": sha256_file(ocr_path),
                "asr_cache_path": str(asr_path.resolve()),
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
    for fold in range(5):
        shard_path = args.output_dir / "shards" / f"fold_{fold}.jsonl"
        shard_path.parent.mkdir(parents=True, exist_ok=True)
        shard_path.write_text(
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
        "schema_version": "qwen3_selective_rewrite_confirm100_dataset_audit_v1",
        "question_count": len(items),
        "video_count": len({str(row["video_id"]) for row in items}),
        "runtime_fold_counts": dict(Counter(str(row["fold"]) for row in items)),
        "source_fold_counts": dict(Counter(str(row["source_fold"]) for row in items)),
        "a0_support_min": min(probabilities),
        "a0_support_max": max(probabilities),
        "a0_support_mean": sum(probabilities) / len(probabilities),
        "ocr_status_counts": dict(Counter(row["ocr_quality"]["status"] for row in items)),
        "asr_status_counts": dict(Counter(row["asr_quality"]["status"] for row in items)),
        "all_have_two_anchors": all(
            len(row["evidence_anchors"]) == 2 for row in items
        ),
        "answer_free_generation_items": all(
            not (FORBIDDEN & set(row)) for row in items
        ),
        "selection_policy": "global_lowest_support_probability_then_question_id_v1",
        "selection_uses_only_support_probability": True,
        "trigger_rate": 0.10,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "pool_scores_sha256": sha256_file(args.scores),
        "av_manifest_sha256": sha256_file(args.av_manifest),
        "items_sha256": sha256_file(items_path),
        "selection_manifest_sha256": sha256_file(selection_path),
        "passed": (
            len(items) == 100
            and len({str(row["video_id"]) for row in items}) == 100
            and all(
                sum(int(row["fold"]) == fold for row in items) == 20
                for fold in range(5)
            )
        ),
    }
    dump_json(args.output_dir / "audit.json", audit)
    if not audit["passed"]:
        raise RuntimeError("Confirm-100 trigger audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
