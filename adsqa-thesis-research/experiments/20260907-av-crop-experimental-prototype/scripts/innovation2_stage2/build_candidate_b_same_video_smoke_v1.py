#!/usr/bin/env python3
"""Build candidate-B same-video hard-negative smoke pairs.

Each negative keeps the source video but replaces the complete 32-view evidence
set with a temporally disjoint segment outside the frozen anchor window. Labels
remain internal synthetic intervention labels and are never human gold.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


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
    parser.add_argument("--claims-jsonl", type=Path, required=True)
    parser.add_argument("--evidence-questions", type=Path, required=True)
    parser.add_argument("--holdout-claims", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--stage2-dev-video-count", type=int, default=5)
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
    digest = hashlib.sha256(f"{seed}:{pair_id}:{branch}".encode("utf-8")).hexdigest()
    return f"in_{digest[:24]}"


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
        value = row.get(key)
        if value:
            return Path(str(value)).stem
    return ""


def linspace_indices(start: int, end: int, count: int) -> list[int]:
    if end - start + 1 < count:
        return []
    if count == 1:
        return [start]
    output = [
        start + round(index * (end - start) / (count - 1))
        for index in range(count)
    ]
    return output if len(set(output)) == count else []


def outside_anchor_segments(
    frame_count: int,
    anchor_frames: list[int],
    variant: int,
) -> tuple[list[int], int, int, int] | None:
    """Return one 32-frame segment on a side of the anchor exclusion window."""
    if frame_count < 64 or not anchor_frames:
        return None
    radius = max(16, frame_count // 12)
    lower = max(0, min(anchor_frames) - radius)
    upper = min(frame_count - 1, max(anchor_frames) + radius)
    intervals = [(0, lower - 1), (upper + 1, frame_count - 1)]
    viable = [(start, end) for start, end in intervals if end - start + 1 >= 32]
    if not viable:
        return None
    viable.sort(key=lambda interval: (interval[1] - interval[0] + 1, interval), reverse=True)
    if len(viable) >= 2:
        start, end = viable[variant % 2]
    else:
        start, end = viable[0]
        midpoint = start + (end - start + 1) // 2
        halves = [(start, midpoint - 1), (midpoint, end)]
        usable_halves = [item for item in halves if item[1] - item[0] + 1 >= 32]
        if not usable_halves:
            return None
        start, end = usable_halves[variant % len(usable_halves)]
    indices = linspace_indices(start, end, 32)
    if not indices:
        return None
    return indices, start, end, radius


def materialize_input(
    source: dict[str, Any],
    pair_id: str,
    input_id: str,
    frame_indices: list[int],
) -> dict[str, Any]:
    return {
        "schema": "adsqa_candidate_b_model_input_v1",
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
        "asr_excerpt": source["asr_excerpt"],
        "frame_indices": frame_indices,
    }


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite output root: {args.output_root}")
    rows = read_jsonl(args.claims_jsonl)
    evidence_rows = read_rows(args.evidence_questions)
    holdout_rows = read_rows(args.holdout_claims)
    source_videos = sorted({str(row["video_id"]) for row in rows})
    if not source_videos:
        raise RuntimeError("no input videos")
    if not 0 < args.stage2_dev_video_count < len(source_videos):
        raise ValueError("stage2-dev video count must be inside source video range")
    dev_videos = set(
        sorted(source_videos, key=lambda value: stable_int(args.seed + 101, value))[
            : args.stage2_dev_video_count
        ]
    )
    evidence_videos = {video_id_from_row(row) for row in evidence_rows if video_id_from_row(row)}
    calibration_videos = {
        video_id_from_row(row)
        for row in holdout_rows
        if row.get("split") == "calibration" and video_id_from_row(row)
    }
    development_videos = {
        video_id_from_row(row)
        for row in holdout_rows
        if row.get("split") == "development" and video_id_from_row(row)
    }

    sources: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        selected = [int(value) for value in row.get("selected_frame_indices", [])]
        positions = [int(value) for value in row.get("evidence_anchor_positions", [])]
        anchors = [selected[position] for position in positions if 0 <= position < len(selected)]
        if len(selected) != 32 or len(set(selected)) != 32 or not anchors:
            rejected.append({"claim_id": row.get("claim_id"), "reason": "invalid_positive_anchor_plan"})
            continue
        source = {
            "schema": "adsqa_candidate_b_same_video_source_v1",
            "source_claim_id": str(row["claim_id"]),
            "source_question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "video_path": str(row["video_path"]),
            "claim_type": str(row["claim_type"]),
            "required_modality": "ocr" if row["claim_type"] == "ocr" else "visual",
            "stage2_partition": (
                "stage2_dev" if str(row["video_id"]) in dev_videos else "train_fit"
            ),
            "question": str(row["question"]),
            "atomic_claim": str(row["text"]),
            "asr_excerpt": str(row.get("asr_excerpt", "") or ""),
            "selected_frame_indices": selected,
            "evidence_anchor_positions": positions,
            "evidence_anchor_frame_indices": anchors,
            "source_label_policy": "frozen_qwen_evidence_extraction_not_human_gold",
            "not_human_gold": True,
        }
        plans: list[tuple[int, list[int], int, int, int]] = []
        for variant in range(2):
            result = outside_anchor_segments(int(row.get("frame_count", 0) or 0), anchors, variant)
            if result is None:
                rejected.append(
                    {"claim_id": row.get("claim_id"), "reason": f"no_hard_negative_segment_cf{variant + 1}"}
                )
                break
            frames, start, end, radius = result
            if set(frames) & set(anchors):
                rejected.append(
                    {"claim_id": row.get("claim_id"), "reason": f"anchor_leaked_cf{variant + 1}"}
                )
                break
            plans.append((variant, frames, start, end, radius))
        if len(plans) != 2:
            continue
        sources.append(source)
        for variant, negative_frames, start, end, radius in plans:
            pair_id = f"{source['source_claim_id']}__same_video_hard_cf{variant + 1:02d}"
            positive_id = opaque_input_id(args.seed, pair_id, "a")
            negative_id = opaque_input_id(args.seed, pair_id, "b")
            plan = {
                "valid": True,
                "asr_excerpt": source["asr_excerpt"],
                "visual_operation": {
                    "valid": True,
                    "operation": "same_video_anchor_exclusion_segment",
                    "frame_indices": negative_frames,
                    "original_frame_indices": source["selected_frame_indices"],
                    "replacement_frame_indices": negative_frames,
                    "source_anchor_frame_indices": source["evidence_anchor_frame_indices"],
                    "source_anchor_positions": source["evidence_anchor_positions"],
                    "excluded_radius_frames": radius,
                    "selected_segment_start": start,
                    "selected_segment_end": end,
                    "same_video": True,
                    "fallback_used": False,
                    "fallback_reason": None,
                },
                "single_factor": "replace_entire_evidence_view_set_with_same_video_anchor_exclusion_segment",
            }
            inputs.extend(
                [
                    materialize_input(source, pair_id, positive_id, source["selected_frame_indices"]),
                    materialize_input(source, pair_id, negative_id, negative_frames),
                ]
            )
            labels.extend(
                [
                    {
                        "schema": "adsqa_candidate_b_label_v1",
                        "input_id": positive_id,
                        "pair_id": pair_id,
                        "label": 1,
                        "evidence_state": "supported",
                        "label_source": "frozen_qwen_evidence_extraction_not_human_gold",
                        "not_human_gold": True,
                    },
                    {
                        "schema": "adsqa_candidate_b_label_v1",
                        "input_id": negative_id,
                        "pair_id": pair_id,
                        "label": 0,
                        "evidence_state": "synthetic_same_video_anchor_exclusion",
                        "label_source": "synthetic_intervention_not_human_gold",
                        "not_human_gold": True,
                    },
                ]
            )
            pairs.append(
                {
                    "schema": "adsqa_candidate_b_same_video_pair_v1",
                    "pair_id": pair_id,
                    "source_claim_id": source["source_claim_id"],
                    "source_question_id": source["source_question_id"],
                    "video_id": source["video_id"],
                    "stage2_partition": source["stage2_partition"],
                    "required_modality": source["required_modality"],
                    "positive_input_id": positive_id,
                    "negative_input_id": negative_id,
                    "negative_corruption_type": "same_video_anchor_exclusion",
                    "negative_plan": plan,
                    "not_human_gold": True,
                }
            )

    inputs.sort(key=lambda row: stable_int(args.seed, str(row["input_id"])))
    source_path = args.output_root / "source_claims.jsonl"
    inputs_path = args.output_root / "model_inputs.jsonl"
    pairs_path = args.output_root / "pairs.jsonl"
    labels_path = args.output_root / "labels.jsonl"
    write_jsonl(source_path, sources)
    write_jsonl(inputs_path, inputs)
    write_jsonl(pairs_path, pairs)
    write_jsonl(labels_path, labels)
    forbidden_input_paths = [
        f"model_inputs.jsonl[{index}].{key}"
        for index, row in enumerate(inputs)
        for key in FORBIDDEN_INPUT_KEYS
        if key in row
    ]
    invalid_pairs = [
        pair["pair_id"]
        for pair in pairs
        if (
            len(pair["negative_plan"]["visual_operation"]["frame_indices"]) != 32
            or len(set(pair["negative_plan"]["visual_operation"]["frame_indices"])) != 32
            or set(pair["negative_plan"]["visual_operation"]["frame_indices"])
            & set(pair["negative_plan"]["visual_operation"]["source_anchor_frame_indices"])
        )
    ]
    source_video_set = {row["video_id"] for row in sources}
    overlap = {
        "calibration": sorted(source_video_set & calibration_videos),
        "development": sorted(source_video_set & development_videos),
        "evidence300": sorted(source_video_set & evidence_videos),
    }
    audit = {
        "schema": "adsqa_candidate_b_same_video_hard_negative_audit_v1",
        "source_count": len(sources),
        "pair_count": len(pairs),
        "model_input_count": len(inputs),
        "positive_count": len(pairs),
        "negative_count": len(pairs),
        "unique_source_video_count": len(source_video_set),
        "stage2_partition_counts": dict(
            sorted(Counter(row["stage2_partition"] for row in sources).items())
        ),
        "claim_type_counts": dict(sorted(Counter(row["claim_type"] for row in sources).items())),
        "required_modality_counts": dict(
            sorted(Counter(row["required_modality"] for row in sources).items())
        ),
        "rejected_count": len(rejected),
        "rejected": rejected,
        "invalid_negative_pair_count": len(invalid_pairs),
        "invalid_negative_pairs": invalid_pairs,
        "source_video_overlap": overlap,
        "forbidden_input_paths": forbidden_input_paths,
        "not_human_gold": True,
        "passed": (
            len(sources) >= 20
            and len(pairs) == len(sources) * 2
            and len(inputs) == len(pairs) * 2
            and not invalid_pairs
            and not forbidden_input_paths
            and not any(overlap.values())
        ),
    }
    audit_path = args.output_root / "audit.json"
    write_json(audit_path, audit)
    manifest = {
        "schema": "adsqa_candidate_b_same_video_manifest_v1",
        "seed": args.seed,
        "goal_start_epoch": args.goal_start_epoch,
        "source_claims_sha256": sha256_file(source_path),
        "model_inputs_sha256": sha256_file(inputs_path),
        "pairs_sha256": sha256_file(pairs_path),
        "labels_sha256": sha256_file(labels_path),
        "audit_sha256": sha256_file(audit_path),
        "claims_input_sha256": sha256_file(args.claims_jsonl),
        "not_human_gold": True,
        "audit": audit,
    }
    write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
