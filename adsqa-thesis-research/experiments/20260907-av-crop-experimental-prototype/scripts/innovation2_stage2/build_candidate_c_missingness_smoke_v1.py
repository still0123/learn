#!/usr/bin/env python3
"""Build candidate-C smoke data with explicit non-empty modality-unavailable states."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


ASR_UNAVAILABLE = "[[ASR_UNAVAILABLE: extraction_failed]]"
ASR_NOT_DETECTED = "[[ASR_AVAILABLE: no matching aligned speech segment detected]]"
FORBIDDEN_INPUT_KEYS = {
    "evidence_state",
    "label",
    "pairwise_target",
    "reference_answer",
    "role",
    "source_label",
    "visual_operation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--visual-ocr-claims", type=Path, required=True)
    parser.add_argument("--all-anchored-claims", type=Path, required=True)
    parser.add_argument("--evidence-questions", type=Path, required=True)
    parser.add_argument("--holdout-claims", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--stage2-dev-video-count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--goal-start-epoch", type=int, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_int(seed: int, value: str) -> int:
    return int(hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()[:16], 16)


def opaque_input_id(seed: int, pair_id: str, branch: str) -> str:
    return f"in_{hashlib.sha256(f'{seed}:{pair_id}:{branch}'.encode()).hexdigest()[:24]}"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for item in value.values():
            if isinstance(item, list) and all(isinstance(row, dict) for row in item):
                return item
    raise ValueError(f"cannot load rows from {path}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def video_id_from_row(row: dict[str, Any]) -> str:
    for key in ("video_id", "video", "video_path", "video_file"):
        if row.get(key):
            return Path(str(row[key])).stem
    return ""


def linspace_indices(start: int, end: int, count: int = 32) -> list[int]:
    if end - start + 1 < count:
        return []
    output = [start + round(index * (end - start) / (count - 1)) for index in range(count)]
    return output if len(set(output)) == count else []


def hard_negative_frames(frame_count: int, anchors: list[int], variant: int) -> tuple[list[int], dict[str, Any]] | None:
    if frame_count < 64 or not anchors:
        return None
    radius = max(16, frame_count // 12)
    lower = max(0, min(anchors) - radius)
    upper = min(frame_count - 1, max(anchors) + radius)
    intervals = [(0, lower - 1), (upper + 1, frame_count - 1)]
    viable = [interval for interval in intervals if interval[1] - interval[0] + 1 >= 32]
    if not viable:
        return None
    viable.sort(key=lambda item: (item[1] - item[0] + 1, item), reverse=True)
    if len(viable) >= 2:
        start, end = viable[variant % 2]
    else:
        start, end = viable[0]
        midpoint = start + (end - start + 1) // 2
        halves = [segment for segment in [(start, midpoint - 1), (midpoint, end)] if segment[1] - segment[0] + 1 >= 32]
        if not halves:
            return None
        start, end = halves[variant % len(halves)]
    frames = linspace_indices(start, end)
    if not frames or set(frames) & set(anchors):
        return None
    return frames, {
        "valid": True,
        "operation": "same_video_anchor_exclusion_segment",
        "frame_indices": frames,
        "source_anchor_frame_indices": anchors,
        "excluded_radius_frames": radius,
        "selected_segment_start": start,
        "selected_segment_end": end,
        "same_video": True,
        "fallback_used": False,
        "fallback_reason": None,
    }


def make_input(source: dict[str, Any], pair_id: str, input_id: str, frames: list[int], asr: str) -> dict[str, Any]:
    return {
        "schema": "adsqa_candidate_c_model_input_v1",
        "input_id": input_id,
        "pair_id": pair_id,
        "source_claim_id": source["source_claim_id"],
        "source_question_id": source["source_question_id"],
        "video_id": source["video_id"],
        "video_path": source["video_path"],
        "question": source["question"],
        "atomic_claim": source["atomic_claim"],
        "claim_type": source["claim_type"],
        "required_modality": source["required_modality"],
        "asr_excerpt": asr,
        "frame_indices": frames,
    }


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_root}")
    visual_rows = read_jsonl(args.visual_ocr_claims)
    all_rows = read_jsonl(args.all_anchored_claims)
    asr_rows = [
        row
        for row in all_rows
        if row.get("extraction_status") == "qwen_asr_quote_validated"
        and row.get("claim_type") == "audio"
        and len(str(row.get("evidence_anchor_asr_quote", "")).split()) >= 4
    ]
    visual_keys = {(str(row["video_id"]), str(row["text"]).casefold()) for row in visual_rows}
    asr_unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in sorted(asr_rows, key=lambda item: stable_int(args.seed, str(item["claim_id"]))):
        key = (str(row["video_id"]), str(row["text"]).casefold())
        if key not in visual_keys:
            asr_unique.setdefault(key, row)
    raw_sources = visual_rows + sorted(asr_unique.values(), key=lambda item: stable_int(args.seed, str(item["claim_id"])))
    videos = sorted({str(row["video_id"]) for row in raw_sources})
    if not 0 < args.stage2_dev_video_count < len(videos):
        raise ValueError("invalid stage2-dev video count")
    dev_videos = set(sorted(videos, key=lambda item: stable_int(args.seed + 101, item))[:args.stage2_dev_video_count])

    evidence_videos = {video_id_from_row(row) for row in read_rows(args.evidence_questions) if video_id_from_row(row)}
    holdout_rows = read_rows(args.holdout_claims)
    calibration_videos = {video_id_from_row(row) for row in holdout_rows if row.get("split") == "calibration" and video_id_from_row(row)}
    development_videos = {video_id_from_row(row) for row in holdout_rows if row.get("split") == "development" and video_id_from_row(row)}
    sources: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for row in raw_sources:
        selected = [int(value) for value in row.get("selected_frame_indices", [])]
        is_asr = row.get("claim_type") == "audio"
        required = "asr" if is_asr else ("ocr" if row.get("claim_type") == "ocr" else "visual")
        anchors = [
            selected[int(position)]
            for position in row.get("evidence_anchor_positions", [])
            if isinstance(position, int) and 0 <= position < len(selected)
        ]
        if len(selected) != 32 or len(set(selected)) != 32:
            rejected.append({"claim_id": row.get("claim_id"), "reason": "invalid_positive_frame_plan"})
            continue
        if not is_asr and not anchors:
            rejected.append({"claim_id": row.get("claim_id"), "reason": "missing_visual_anchor"})
            continue
        source = {
            "schema": "adsqa_candidate_c_source_v1",
            "source_claim_id": str(row["claim_id"]),
            "source_question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "video_path": str(row["video_path"]),
            "claim_type": "audio" if is_asr else str(row["claim_type"]),
            "required_modality": required,
            "stage2_partition": "stage2_dev" if str(row["video_id"]) in dev_videos else "train_fit",
            "question": str(row["question"]),
            "atomic_claim": str(row["text"]),
            "asr_excerpt": str(row.get("asr_excerpt", "") or ""),
            "selected_frame_indices": selected,
            "evidence_anchor_frame_indices": anchors,
            "source_label_policy": "frozen_qwen_evidence_extraction_not_human_gold",
            "not_human_gold": True,
        }
        plans: list[tuple[list[int], str, dict[str, Any]]] = []
        if is_asr:
            unavailable_plan = {
                "valid": bool(source["asr_excerpt"].strip()),
                "modality_missingness": {
                    "asr": "unavailable_due_to_extraction_failure",
                    "ocr": "not_applicable",
                    "visual": "available_but_ignored_for_asr_claim",
                },
                "visual_operation": "none",
                "fallback_used": False,
                "fallback_reason": None,
            }
            not_detected_plan = {
                "valid": bool(source["asr_excerpt"].strip()),
                "modality_missingness": {
                    "asr": "available_but_target_quote_not_detected",
                    "ocr": "not_applicable",
                    "visual": "available_but_ignored_for_asr_claim",
                },
                "visual_operation": "none",
                "fallback_used": False,
                "fallback_reason": None,
            }
            plans = [
                (selected, ASR_UNAVAILABLE, unavailable_plan),
                (selected, ASR_NOT_DETECTED, not_detected_plan),
            ]
        else:
            for variant in range(2):
                result = hard_negative_frames(int(row.get("frame_count", 0) or 0), anchors, variant)
                if result is None:
                    break
                frames, operation = result
                operation["original_frame_indices"] = selected
                operation["replacement_frame_indices"] = frames
                plans.append(
                    (
                        frames,
                        source["asr_excerpt"],
                        {
                            "valid": True,
                            "modality_missingness": {
                                "asr": "available_but_not_used_for_visual_claim",
                                "ocr": "available_current_view" if required == "ocr" else "not_applicable",
                                "visual": "current_view_available_anchor_excluded",
                            },
                            "visual_operation": operation,
                            "fallback_used": False,
                            "fallback_reason": None,
                        },
                    )
                )
        if len(plans) != 2:
            rejected.append({"claim_id": row.get("claim_id"), "reason": "cannot_build_two_variants"})
            continue
        sources.append(source)
        for variant, (negative_frames, negative_asr, plan) in enumerate(plans):
            pair_id = f"{source['source_claim_id']}__missingness_cf{variant + 1:02d}"
            positive_id = opaque_input_id(args.seed, pair_id, "a")
            negative_id = opaque_input_id(args.seed, pair_id, "b")
            inputs.extend(
                [
                    make_input(source, pair_id, positive_id, selected, source["asr_excerpt"]),
                    make_input(source, pair_id, negative_id, negative_frames, negative_asr),
                ]
            )
            labels.extend(
                [
                    {"input_id": positive_id, "pair_id": pair_id, "label": 1, "evidence_state": "supported", "not_human_gold": True},
                    {"input_id": negative_id, "pair_id": pair_id, "label": 0, "evidence_state": "synthetic_missingness_or_anchor_exclusion", "not_human_gold": True},
                ]
            )
            pairs.append(
                {
                    "schema": "adsqa_candidate_c_pair_v1",
                    "pair_id": pair_id,
                    "source_claim_id": source["source_claim_id"],
                    "source_question_id": source["source_question_id"],
                    "video_id": source["video_id"],
                    "stage2_partition": source["stage2_partition"],
                    "required_modality": required,
                    "positive_input_id": positive_id,
                    "negative_input_id": negative_id,
                    "negative_corruption_type": (
                        "asr_unavailable_explicit" if is_asr else "same_video_anchor_exclusion"
                    ),
                    "negative_plan": plan,
                    "not_human_gold": True,
                }
            )

    inputs.sort(key=lambda row: stable_int(args.seed, str(row["input_id"])))
    source_path = args.output_root / "source_claims.jsonl"
    input_path = args.output_root / "model_inputs.jsonl"
    pair_path = args.output_root / "pairs.jsonl"
    label_path = args.output_root / "labels.jsonl"
    audit_path = args.output_root / "audit.json"
    write_jsonl(source_path, sources)
    write_jsonl(input_path, inputs)
    write_jsonl(pair_path, pairs)
    write_jsonl(label_path, labels)
    forbidden = [
        f"model_inputs.jsonl[{index}].{key}"
        for index, row in enumerate(inputs)
        for key in FORBIDDEN_INPUT_KEYS
        if key in row
    ]
    invalid_negative = [
        pair["pair_id"]
        for pair in pairs
        if (
            pair["required_modality"] != "asr"
            and (
                len(pair["negative_plan"]["visual_operation"]["frame_indices"]) != 32
                or set(pair["negative_plan"]["visual_operation"]["frame_indices"])
                & set(pair["negative_plan"]["visual_operation"]["source_anchor_frame_indices"])
            )
        )
    ]
    source_videos = {source["video_id"] for source in sources}
    overlap = {
        "calibration": sorted(source_videos & calibration_videos),
        "development": sorted(source_videos & development_videos),
        "evidence300": sorted(source_videos & evidence_videos),
    }
    audit = {
        "schema": "adsqa_candidate_c_missingness_audit_v1",
        "source_count": len(sources),
        "pair_count": len(pairs),
        "model_input_count": len(inputs),
        "positive_count": len(pairs),
        "negative_count": len(pairs),
        "unique_source_video_count": len(source_videos),
        "required_modality_counts": dict(sorted(Counter(source["required_modality"] for source in sources).items())),
        "negative_corruption_counts": dict(sorted(Counter(pair["negative_corruption_type"] for pair in pairs).items())),
        "nonempty_asr_state_sentinels": [ASR_UNAVAILABLE, ASR_NOT_DETECTED],
        "rejected_count": len(rejected),
        "rejected": rejected,
        "invalid_negative_pairs": invalid_negative,
        "source_video_overlap": overlap,
        "forbidden_input_paths": forbidden,
        "not_human_gold": True,
        "passed": (
            len(sources) >= 20
            and len(pairs) == len(sources) * 2
            and len(inputs) == len(pairs) * 2
            and not rejected
            and not invalid_negative
            and not forbidden
            and not any(overlap.values())
        ),
    }
    write_json(audit_path, audit)
    manifest = {
        "schema": "adsqa_candidate_c_missingness_manifest_v1",
        "seed": args.seed,
        "goal_start_epoch": args.goal_start_epoch,
        "visual_ocr_claims_sha256": sha256_file(args.visual_ocr_claims),
        "all_anchored_claims_sha256": sha256_file(args.all_anchored_claims),
        "source_claims_sha256": sha256_file(source_path),
        "model_inputs_sha256": sha256_file(input_path),
        "pairs_sha256": sha256_file(pair_path),
        "labels_sha256": sha256_file(label_path),
        "audit_sha256": sha256_file(audit_path),
        "not_human_gold": True,
        "audit": audit,
    }
    write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
