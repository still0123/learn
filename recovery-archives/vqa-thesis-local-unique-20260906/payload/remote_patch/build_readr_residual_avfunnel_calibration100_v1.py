#!/usr/bin/env python3
"""Build answer-free residual AV-Funnel12 inputs on ReAd-R Calibration100."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2

from build_avfunnel8_manifest_v1 import (
    build_candidates,
    center_of,
    hierarchical_sides,
    select_temporally_diverse_anchors,
    square_box,
    uncertainty_proxy,
)


VARIANTS = ("residual_mid", "residual_avfunnel")
FORBIDDEN = {
    "answer",
    "answers",
    "ground_truth",
    "gt_answer",
    "reference_answer",
    "judge_score",
    "label",
    "meta_info",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-questions", type=Path, required=True)
    parser.add_argument("--a2-source-items", type=Path, required=True)
    parser.add_argument("--raw-features", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--smoke-per-fold", type=int, default=5)
    return parser.parse_args()


def load_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise RuntimeError(f"expected JSON list: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def uniform_indices(total: int, count: int = 32) -> list[int]:
    if total <= 0:
        raise RuntimeError("video has no frames")
    if total == 1:
        return [0] * count
    return [round(index * (total - 1) / (count - 1)) for index in range(count)]


def video_frame_count(path: str, cache: dict[str, int]) -> int:
    if path in cache:
        return cache[path]
    capture = cv2.VideoCapture(path)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    if total <= 0:
        raise RuntimeError(f"cannot inspect video: {path}")
    cache[path] = total
    return total


def scale_level(candidate: dict[str, Any]) -> str:
    source = str(candidate["bbox_source"])
    if source == "ocr":
        return "focal"
    if source == "asr":
        return "broad"
    entropy = uncertainty_proxy(float(candidate["response_concentration"]))
    if entropy < 0.45:
        return "focal"
    if entropy > 0.75:
        return "broad"
    return "mid"


def make_anchor(
    candidate: dict[str, Any],
    anchor_index: int,
    variant: str,
) -> dict[str, Any]:
    entropy = uncertainty_proxy(float(candidate["response_concentration"]))
    selected_scale = "mid" if variant == "residual_mid" else scale_level(candidate)
    center_x, center_y = center_of(candidate["bbox_norm"])
    bbox = square_box(
        center_x,
        center_y,
        hierarchical_sides(candidate["bbox_norm"], entropy)[selected_scale],
    )
    return {
        "anchor_index": anchor_index,
        "source_global_rank": int(candidate["source_global_rank"]),
        "bbox_norm": bbox,
        "bbox_source": str(candidate["bbox_source"]),
        "fusion_score": float(candidate["fusion_score"]),
        "visual_rank_score": float(candidate["visual_rank_score"]),
        "asr_rank_score": float(candidate["asr_rank_score"]),
        "ocr_rank_score": float(candidate["ocr_rank_score"]),
        "entropy_proxy": entropy,
        "scale_level": selected_scale,
        "crop_mode": f"residual_avfunnel_{selected_scale}_v1",
        "residual_selection": "excluded_a0_frame_indices_then_av_fusion_v1",
    }


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError("output root already exists")
    calibration = load_json(args.calibration_questions)
    source_items = load_jsonl(args.a2_source_items)
    raw_rows = [
        row
        for path in args.raw_features
        for row in load_jsonl(path)
    ]
    if (
        len(calibration) != 100
        or len({str(row["question_id"]) for row in calibration}) != 100
        or any(FORBIDDEN & set(row) for row in calibration)
    ):
        raise RuntimeError("Calibration100 source is invalid")
    calibration_ids = {str(row["question_id"]) for row in calibration}
    items_by_id = {str(row["question_id"]): row for row in source_items}
    raw_by_id: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        qid = str(row["question_id"])
        if qid in raw_by_id:
            raise RuntimeError(f"duplicate raw feature: {qid}")
        raw_by_id[qid] = row
    if (
        len(items_by_id) != len(source_items)
        or not calibration_ids.issubset(items_by_id)
        or not calibration_ids.issubset(raw_by_id)
    ):
        raise RuntimeError("Calibration100 is missing candidate or raw-feature records")
    if any(FORBIDDEN & set(items_by_id[qid]) for qid in calibration_ids):
        raise RuntimeError("candidate item contains outcome-side field")
    if any(FORBIDDEN & set(raw_by_id[qid]) for qid in calibration_ids):
        raise RuntimeError("raw feature contains outcome-side field")

    frame_count_cache: dict[str, int] = {}
    variant_rows: dict[str, list[dict[str, Any]]] = {variant: [] for variant in VARIANTS}
    residual_candidate_counts: list[int] = []
    source_counts: dict[str, Counter[str]] = {variant: Counter() for variant in VARIANTS}
    scale_counts: dict[str, Counter[str]] = {variant: Counter() for variant in VARIANTS}
    selected_residual_ranks: dict[str, dict[str, list[int]]] = {variant: {} for variant in VARIANTS}

    for qid in sorted(calibration_ids):
        source = json.loads(json.dumps(items_by_id[qid]))
        if len(source.get("evidence_anchors", [])) != 2:
            raise RuntimeError(f"source lacks two anchors: {qid}")
        total_frames = video_frame_count(str(source["video_path"]), frame_count_cache)
        rank_to_frame = uniform_indices(total_frames)
        a0_indices = {int(value) for value in source["a0_frame_indices"]}
        candidates = [
            candidate
            for candidate in build_candidates(raw_by_id[qid])
            if rank_to_frame[int(candidate["source_global_rank"])] not in a0_indices
        ]
        if len(candidates) < 2:
            raise RuntimeError(f"fewer than two residual AV candidates: {qid}")
        selected, temporal_gap = select_temporally_diverse_anchors(candidates)
        if len(selected) != 2:
            raise RuntimeError(f"residual selection failed: {qid}")
        residual_candidate_counts.append(len(candidates))
        for variant in VARIANTS:
            output = json.loads(json.dumps(source))
            output["crop_ablation_variant"] = variant
            output["residual_anchor_selection"] = {
                "rule": "exclude_a0_source_frame_then_fixed_av_fusion_v1",
                "a0_frame_indices": sorted(a0_indices),
                "candidate_count_after_exclusion": len(candidates),
                "temporal_gap_satisfied": temporal_gap,
                "source_total_frames": total_frames,
            }
            output["evidence_anchors"] = [
                make_anchor(candidate, index, variant)
                for index, candidate in enumerate(selected)
            ]
            chosen_frames = [
                rank_to_frame[int(anchor["source_global_rank"])]
                for anchor in output["evidence_anchors"]
            ]
            if set(chosen_frames) & a0_indices:
                raise RuntimeError(f"residual frame overlap: {qid}")
            variant_rows[variant].append(output)
            selected_residual_ranks[variant][qid] = [
                int(anchor["source_global_rank"])
                for anchor in output["evidence_anchors"]
            ]
            source_counts[variant].update(
                str(anchor["bbox_source"]) for anchor in output["evidence_anchors"]
            )
            scale_counts[variant].update(
                str(anchor["scale_level"]) for anchor in output["evidence_anchors"]
            )

    args.output_root.mkdir(parents=True, exist_ok=False)
    files: dict[str, str] = {}
    for variant, rows in variant_rows.items():
        rows.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
        full_path = args.output_root / variant / "items_answer_free.jsonl"
        dump_jsonl(full_path, rows)
        files[str(full_path.relative_to(args.output_root))] = sha256_file(full_path)
        for fold in range(5):
            fold_rows = [row for row in rows if int(row["fold"]) == fold]
            shard_path = args.output_root / variant / "shards" / f"fold_{fold}.jsonl"
            smoke_path = args.output_root / variant / "smoke" / f"fold_{fold}.jsonl"
            dump_jsonl(shard_path, fold_rows)
            dump_jsonl(smoke_path, fold_rows[: args.smoke_per_fold])
            files[str(shard_path.relative_to(args.output_root))] = sha256_file(shard_path)
            files[str(smoke_path.relative_to(args.output_root))] = sha256_file(smoke_path)

    audit = {
        "schema_version": "readr_residual_avfunnel_calibration100_dataset_v1",
        "passed": True,
        "development_only": True,
        "question_count": len(calibration_ids),
        "video_count": len({str(row["video"]) for row in calibration}),
        "source_partition": "pilot300_calibration100",
        "variants": list(VARIANTS),
        "smoke_per_fold": args.smoke_per_fold,
        "frozen_across_variants": [
            "question",
            "a0_prediction",
            "a0_frame_indices",
            "A2_view_count",
            "A2_visual_token_budget",
            "OCR_evidence",
            "ASR_evidence",
            "prompt_template",
            "common_ReAdR_checkpoint",
        ],
        "residual_policy": "both A2 anchors must map to frames absent from MMR8 A0",
        "scale_policy": {
            "residual_mid": "mid for both anchors",
            "residual_avfunnel": "OCR=focal; ASR=broad; visual=focal/mid/broad by entropy",
        },
        "residual_candidate_count": {
            "min": min(residual_candidate_counts),
            "mean": sum(residual_candidate_counts) / len(residual_candidate_counts),
            "max": max(residual_candidate_counts),
        },
        "anchor_source_counts": {key: dict(value) for key, value in source_counts.items()},
        "anchor_scale_counts": {key: dict(value) for key, value in scale_counts.items()},
        "selected_residual_ranks": selected_residual_ranks,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "external_knowledge_used": False,
        "source_hashes": {
            "calibration_questions": sha256_file(args.calibration_questions),
            "a2_source_items": sha256_file(args.a2_source_items),
            "raw_features": [sha256_file(path) for path in args.raw_features],
        },
        "files_sha256": files,
    }
    dump_json(args.output_root / "dataset_audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
