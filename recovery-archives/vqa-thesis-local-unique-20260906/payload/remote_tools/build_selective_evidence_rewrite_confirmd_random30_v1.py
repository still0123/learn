#!/usr/bin/env python3
"""Build a deterministic random 10% Confirm-D300 trigger control."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

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
    parser.add_argument("--low-support-selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--trigger-count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260728)
    return parser.parse_args()


def stable_key(seed: int, question_id: str) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def main() -> None:
    args = parse_args()
    if args.trigger_count != 30:
        raise RuntimeError("random control requires exactly 30 triggers")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    pool = load_jsonl(args.pool_dir / "model_inputs_all.jsonl")
    source_manifest = {
        str(row["question_id"]): row
        for row in load_jsonl(args.pool_dir / "source_manifest.jsonl")
    }
    score_rows = load_jsonl(args.scores)
    score_by_qid = {
        str(row["question_id"]): float(row["support_probability"])
        for row in score_rows
    }
    pool_by_verifier = {str(row["question_id"]): row for row in pool}
    av_manifest = load_av_manifest(args.av_manifest)
    if len(pool) != 300 or len(score_rows) != 300:
        raise RuntimeError("Confirm-D pool and A0 support coverage must both be 300")
    if set(pool_by_verifier) != set(score_by_qid):
        raise RuntimeError("Confirm-D pool and support scores do not align")

    candidates = []
    for verifier_qid, source in pool_by_verifier.items():
        qid = str(source["source_question_id"])
        candidates.append({
            "question_id": qid,
            "video_id": str(source["video_id"]),
            "source_fold": int(source["fold"]),
            "support_probability": score_by_qid[verifier_qid],
            "random_key": stable_key(args.seed, qid),
            "pool": source,
        })
    candidates.sort(key=lambda row: (row["random_key"], row["question_id"]))
    selected = candidates[: args.trigger_count]
    if len({row["video_id"] for row in selected}) != 30:
        raise RuntimeError("random selection must contain 30 unique videos")

    low_support_ids = {
        str(row["question_id"])
        for row in load_jsonl(args.low_support_selection)
    }
    items, selection_rows = [], []
    for rank, candidate in enumerate(selected):
        source = candidate["pool"]
        qid = candidate["question_id"]
        video_id = candidate["video_id"]
        runtime_fold = rank % 5
        if qid not in av_manifest:
            raise RuntimeError(f"AV manifest misses {qid}")
        source_row = source_manifest[qid]
        ocr_path = args.ocr_root / f"{video_id}.json"
        asr_path = args.asr_root / f"{video_id}.json"
        ocr, ocr_quality = select_ocr(ocr_path, str(source["question"]))
        asr, asr_quality, asr_full = select_asr(asr_path, str(source["question"]))
        items.append({
            "question_id": qid,
            "video_id": video_id,
            "fold": runtime_fold,
            "source_fold": candidate["source_fold"],
            "question": str(source["question"]),
            "a0_prediction": str(source["claim"]),
            "a0_asr_excerpt": str(source.get("asr_excerpt", "")),
            "a0_frame_indices": [int(value) for value in source["selected_frame_indices"]],
            "video_path": str(source["video_path"]),
            "evidence_anchors": select_anchors(av_manifest[qid]),
            "ocr_evidence": ocr,
            "ocr_quality": ocr_quality,
            "asr_evidence": asr,
            "asr_quality": asr_quality,
            "asr_full_text": asr_full,
        })
        selection_rows.append({
            "selection_rank": rank,
            "question_id": qid,
            "video_id": video_id,
            "runtime_fold": runtime_fold,
            "source_fold": candidate["source_fold"],
            "random_key": candidate["random_key"],
            "a0_support_probability": candidate["support_probability"],
            "also_in_lowest_support30": qid in low_support_ids,
            "a0_prediction_path": source_row["a0_prediction_path"],
            "a0_prediction_sha256": source_row["a0_prediction_sha256"],
            "a0_evidence_path": source_row["a0_evidence_path"],
            "a0_evidence_sha256": source_row["a0_evidence_sha256"],
            "ocr_cache_path": str(ocr_path.resolve()),
            "ocr_cache_sha256": sha256_file(ocr_path),
            "asr_cache_path": str(asr_path.resolve()),
            "asr_cache_sha256": sha256_file(asr_path),
        })

    args.output_dir.mkdir(parents=True, exist_ok=False)
    items_path = args.output_dir / "items_answer_free.jsonl"
    selection_path = args.output_dir / "selection_manifest_random_only.jsonl"
    items_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in items),
        encoding="utf-8",
    )
    selection_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selection_rows),
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
    audit = {
        "schema_version": "qwen3_selective_rewrite_confirmd_random30_audit_v1",
        "question_count": len(items),
        "video_count": len({row["video_id"] for row in items}),
        "runtime_fold_counts": dict(Counter(str(row["fold"]) for row in items)),
        "source_fold_counts": dict(Counter(str(row["source_fold"]) for row in items)),
        "random_seed": args.seed,
        "selection_policy": "sha256_seeded_question_id_lowest30_v1",
        "overlap_with_lowest_support30": sum(
            row["also_in_lowest_support30"] for row in selection_rows
        ),
        "support_probability_not_used_for_selection": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "answer_free_generation_items": all(not (FORBIDDEN & set(row)) for row in items),
        "pool_scores_sha256": sha256_file(args.scores),
        "av_manifest_sha256": sha256_file(args.av_manifest),
        "low_support_selection_sha256": sha256_file(args.low_support_selection),
        "items_sha256": sha256_file(items_path),
        "selection_manifest_sha256": sha256_file(selection_path),
        "passed": (
            len(items) == 30
            and len({row["video_id"] for row in items}) == 30
            and all(sum(int(row["fold"]) == fold for row in items) == 6 for fold in range(5))
        ),
    }
    dump_json(args.output_dir / "audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
