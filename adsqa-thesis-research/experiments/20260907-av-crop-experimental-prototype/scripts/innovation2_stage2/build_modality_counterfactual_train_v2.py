#!/usr/bin/env python3
"""Build a video-disjoint, auditable modality-counterfactual training corpus.

Labels are internal synthetic supervision, never human gold.  The model-input
file deliberately excludes both labels and intervention metadata; intervention
plans remain only in pairs.jsonl and are applied before frozen-Qwen inference.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN_INPUT_KEYS = {
    "annotation_rationale",
    "corruption_type",
    "evidence_state",
    "label",
    "label_provenance",
    "meta_info",
    "model_answer",
    "not_human_gold",
    "pairwise_target",
    "reference_answer",
    "role",
    "single_factor",
    "source_label",
    "visual_operation",
}
VISUAL_CORRUPTION_TYPES = {"temporal_drop", "visual_mosaic", "same_video_distractor"}


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_int_list(value: Any) -> list[int]:
    return [int(item) for item in (value or [])]


def video_id_from_row(row: dict[str, Any]) -> str:
    for key in ("video_id", "video", "video_path", "video_file"):
        value = row.get(key)
        if value:
            return Path(str(value)).stem
    return ""


def required_modality(row: dict[str, Any]) -> str:
    claim_type = str(row.get("claim_type", "")).lower()
    asr = str(row.get("asr_excerpt", "") or "").strip()
    if claim_type == "audio":
        return "asr"
    if claim_type in {"ocr", "brand"}:
        return "ocr"
    if claim_type in {"visual", "temporal"}:
        return "visual"
    return "joint" if len(asr) >= 20 else "visual"


def selected_candidate_positions(row: dict[str, Any]) -> list[int]:
    selected = as_int_list(row.get("selected_frame_indices"))
    router = row.get("router_inputs") or {}
    candidates = as_int_list(router.get("candidate_frame_indices"))
    scores = [float(item) for item in router.get("candidate_scores", [])]
    rank = {frame: index for index, frame in enumerate(candidates)}
    ranked = [
        (scores[rank[frame]], position)
        for position, frame in enumerate(selected)
        if frame in rank and rank[frame] < len(scores)
    ]
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [position for _, position in ranked]


def deterministic_positions(row: dict[str, Any], seed: int, count: int) -> list[int]:
    selected = as_int_list(row.get("selected_frame_indices"))
    if len(selected) < count:
        return []
    anchored = sorted(
        {
            int(position)
            for position in row.get("evidence_anchor_positions", [])
            if str(position).lstrip("-").isdigit() and 0 <= int(position) < len(selected)
        }
    )
    if anchored:
        positions = anchored[:count]
        if len(positions) < count:
            for position in range(len(selected)):
                if position not in positions and all(abs(position - used) > 1 for used in positions):
                    positions.append(position)
                if len(positions) == count:
                    break
        if len(positions) == count:
            return sorted(positions)
    ranked = selected_candidate_positions(row)
    if len(ranked) >= count:
        return sorted(ranked[:count])
    stride = max(1, len(selected) // count)
    start = stable_int(seed, str(row["claim_id"])) % stride
    positions = [(start + index * stride) % len(selected) for index in range(count)]
    if len(set(positions)) != count:
        positions = list(range(0, len(selected), stride))[:count]
    return sorted(positions)


def neighbor_replacement_plan(
    row: dict[str, Any],
    positions: list[int],
    fallback_reason: str,
) -> dict[str, Any]:
    selected = as_int_list(row.get("selected_frame_indices"))
    max_frame_index = int(row.get("frame_count", 0) or 0) - 1
    if len(selected) != 32 or not positions:
        return {"valid": False, "reason": "missing_32_frame_plan"}

    output = list(selected)
    occupied = set(selected)
    originals: list[int] = []
    replacements: list[int] = []
    for position in positions:
        original = selected[position]
        occupied.discard(original)
        lower = selected[position - 1] + 1 if position > 0 else 0
        upper = selected[position + 1] - 1 if position + 1 < len(selected) else max_frame_index
        if upper < lower:
            return {"valid": False, "reason": "no_neighbor_frame_available"}
        offsets = (-1, 1, -2, 2, -3, 3) if position == len(selected) - 1 else (1, -1, 2, -2, 3, -3)
        replacement = next(
            (
                original + offset
                for offset in offsets
                if lower <= original + offset <= upper and original + offset not in occupied
            ),
            None,
        )
        if replacement is None:
            return {"valid": False, "reason": "no_distinct_neighbor_frame_available"}
        output[position] = replacement
        occupied.add(replacement)
        originals.append(original)
        replacements.append(replacement)

    valid = (
        len(output) == 32
        and len(set(output)) == 32
        and len(originals) == len(replacements)
        and all(left != right for left, right in zip(originals, replacements))
    )
    return {
        "valid": valid,
        "operation": "deterministic_neighbor_frame_replacement",
        "frame_indices": sorted(output),
        "replaced_positions": positions,
        "original_frame_indices": originals,
        "replacement_frame_indices": replacements,
        "fallback_used": True,
        "fallback_reason": fallback_reason,
    }


def temporal_drop_plan(row: dict[str, Any], seed: int, count: int = 4) -> dict[str, Any]:
    selected = as_int_list(row.get("selected_frame_indices"))
    candidates = as_int_list((row.get("router_inputs") or {}).get("candidate_frame_indices"))
    positions = deterministic_positions(row, seed, count)
    if len(selected) != 32 or len(positions) != count:
        return {"valid": False, "reason": "missing_32_frame_plan"}
    alternatives = [frame for frame in candidates if frame not in selected]
    if len(alternatives) < count:
        return neighbor_replacement_plan(row, positions, "candidate_frames_missing_or_insufficient")

    replacement_offset = stable_int(seed, str(row["claim_id"])) % len(alternatives)
    replacements = [alternatives[(replacement_offset + index) % len(alternatives)] for index in range(count)]
    output = list(selected)
    for position, replacement in zip(positions, replacements):
        output[position] = replacement
    valid = len(set(output)) == 32 and all(
        original != replacement for original, replacement in zip((selected[pos] for pos in positions), replacements)
    )
    return {
        "valid": valid,
        "operation": "temporal_block_replacement",
        "frame_indices": sorted(output),
        "replaced_positions": positions,
        "original_frame_indices": [selected[position] for position in positions],
        "replacement_frame_indices": replacements,
        "fallback_used": False,
        "fallback_reason": None,
    }


def same_video_distractor_plan(row: dict[str, Any], seed: int, count: int = 8) -> dict[str, Any]:
    selected = as_int_list(row.get("selected_frame_indices"))
    candidates = as_int_list((row.get("router_inputs") or {}).get("candidate_frame_indices"))
    positions = deterministic_positions(row, seed + 7919, count)
    if len(selected) != 32 or len(positions) != count:
        return {"valid": False, "reason": "missing_32_frame_plan"}
    alternatives = [frame for frame in candidates if frame not in selected]
    if len(alternatives) < count:
        return neighbor_replacement_plan(row, positions, "candidate_frames_missing_or_insufficient")

    step = max(1, len(alternatives) // count)
    offset = stable_int(seed, str(row["claim_id"])) % step
    replacements = [alternatives[(offset + index * step) % len(alternatives)] for index in range(count)]
    output = list(selected)
    for position, replacement in zip(positions, replacements):
        output[position] = replacement
    valid = len(set(output)) == 32 and all(
        original != replacement for original, replacement in zip((selected[pos] for pos in positions), replacements)
    )
    return {
        "valid": valid,
        "operation": "same_video_candidate_distractor",
        "frame_indices": sorted(output),
        "replaced_positions": positions,
        "original_frame_indices": [selected[position] for position in positions],
        "replacement_frame_indices": replacements,
        "fallback_used": False,
        "fallback_reason": None,
    }


def visual_mosaic_plan(row: dict[str, Any], seed: int, count: int = 4) -> dict[str, Any]:
    selected = as_int_list(row.get("selected_frame_indices"))
    positions = deterministic_positions(row, seed + 1543, count)
    if len(selected) != 32 or len(positions) != count:
        return {"valid": False, "reason": "missing_32_frame_plan"}
    has_response_scores = bool(selected_candidate_positions(row))
    affected = [selected[position] for position in positions]
    boxes_by_position = {
        int(region["position"]): region.get("bbox_norm")
        for region in row.get("evidence_anchor_regions", [])
        if isinstance(region, dict)
        and str(region.get("position", "")).lstrip("-").isdigit()
        and 0 <= int(region["position"]) < len(selected)
    }
    mosaic_boxes_norm = [
        boxes_by_position.get(position, [0.0, 0.0, 1.0, 1.0])
        for position in positions
    ]
    return {
        "valid": True,
        "operation": "same_area_mosaic",
        "frame_indices": selected,
        "mosaic_positions": positions,
        "mosaic_side": 14,
        "affected_frame_indices": affected,
        "original_frame_indices": affected,
        "replacement_frame_indices": affected,
        "mosaic_boxes_norm": mosaic_boxes_norm,
        "pixel_evidence_changed": True,
        "fallback_used": not has_response_scores,
        "fallback_reason": None if has_response_scores else "candidate_response_scores_missing",
    }


def asr_withheld_plan(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("asr_excerpt", "") or "").strip()
    return {
        "valid": bool(source),
        "operation": "withhold_asr",
        "asr_excerpt": "",
        "original_asr_excerpt": source,
        "visual_operation": "none",
        "fallback_used": False,
        "fallback_reason": None,
    }


def asr_span_redaction_plan(row: dict[str, Any], seed: int) -> dict[str, Any]:
    source = str(row.get("asr_excerpt", "") or "").strip()
    tokens = source.split()
    if not tokens:
        return {
            "valid": False,
            "reason": "empty_source_asr",
            "asr_excerpt": source,
            "visual_operation": "none",
        }
    anchor_quote = str(row.get("evidence_anchor_asr_quote", "") or "").strip()
    anchor_tokens = anchor_quote.split()
    normalized_tokens = [token.lower().strip(".,!?;:") for token in tokens]
    normalized_anchor = [token.lower().strip(".,!?;:") for token in anchor_tokens]
    start = -1
    if normalized_anchor:
        for candidate in range(len(tokens) - len(normalized_anchor) + 1):
            if normalized_tokens[candidate : candidate + len(normalized_anchor)] == normalized_anchor:
                start = candidate
                break
    span = len(normalized_anchor) if start >= 0 else max(1, len(tokens) // 3)
    if start < 0:
        start = stable_int(seed, str(row["claim_id"])) % max(1, len(tokens) - span + 1)
    retained = tokens[:start] + tokens[start + span :]
    redacted = " ".join(retained).strip() or "[AUDIO_EVIDENCE_REDACTED]"
    return {
        "valid": redacted != source,
        "operation": "redact_deterministic_asr_span",
        "asr_excerpt": redacted,
        "original_asr_excerpt": source,
        "redacted_token_start": start,
        "redacted_token_count": span,
        "visual_operation": "none",
        "fallback_used": False,
        "fallback_reason": None,
    }


def build_negative(row: dict[str, Any], variant: int, seed: int, modality: str) -> tuple[str, dict[str, Any]]:
    source_asr = str(row.get("asr_excerpt", "") or "")
    if modality == "asr":
        if variant == 0:
            return "asr_withheld", asr_withheld_plan(row)
        return "asr_span_redaction", asr_span_redaction_plan(row, seed + 31)
    if modality == "ocr":
        if variant == 0:
            return "visual_mosaic", {
                "asr_excerpt": source_asr,
                "visual_operation": visual_mosaic_plan(row, seed),
                "single_factor": "mosaic_text_or_brand_evidence",
            }
        return "temporal_drop", {
            "asr_excerpt": source_asr,
            "visual_operation": temporal_drop_plan(row, seed + 37),
            "single_factor": "replace_visual_evidence_block",
        }
    if modality == "joint":
        if variant == 0:
            return "asr_withheld", asr_withheld_plan(row)
        return "temporal_drop", {
            "asr_excerpt": source_asr,
            "visual_operation": temporal_drop_plan(row, seed + 53),
            "single_factor": "replace_visual_evidence_block",
        }
    if variant == 0:
        return "temporal_drop", {
            "asr_excerpt": source_asr,
            "visual_operation": temporal_drop_plan(row, seed),
            "single_factor": "replace_visual_evidence_block",
        }
    return "same_video_distractor", {
        "asr_excerpt": source_asr,
        "visual_operation": same_video_distractor_plan(row, seed + 71),
        "single_factor": "same_video_visual_distractor",
    }


def visual_operation_valid(corruption_type: str, plan: dict[str, Any]) -> bool:
    operation = plan.get("visual_operation")
    if corruption_type not in VISUAL_CORRUPTION_TYPES:
        return bool(plan.get("valid", False))
    if not isinstance(operation, dict) or not operation.get("valid", False):
        return False
    if corruption_type == "visual_mosaic":
        return bool(operation.get("pixel_evidence_changed")) and bool(operation.get("mosaic_positions"))
    before = operation.get("original_frame_indices") or []
    after = operation.get("replacement_frame_indices") or []
    frames = operation.get("frame_indices") or []
    return (
        len(before) == len(after) > 0
        and all(left != right for left, right in zip(before, after))
        and len(frames) == 32
        and len(set(frames)) == 32
    )


def evidence_changed(
    source: dict[str, Any],
    corruption_type: str,
    plan: dict[str, Any],
) -> bool:
    if corruption_type in VISUAL_CORRUPTION_TYPES:
        return visual_operation_valid(corruption_type, plan)
    return (
        bool(plan.get("valid", False))
        and str(plan.get("asr_excerpt", "")) != str(source.get("asr_excerpt", ""))
    )


def select_sources(rows: list[dict[str, Any]], target: int, seed: int) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if row.get("split") == "train"
        and row.get("label") == "supported"
        and float(row.get("annotation_confidence", 0) or 0) >= 0.8
        and str(row.get("text", "")).strip()
        and len(as_int_list(row.get("selected_frame_indices"))) == 32
    ]
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        pools[str(row.get("claim_type", "other"))].append(row)
    for pool in pools.values():
        pool.sort(key=lambda row: stable_int(seed, str(row["claim_id"])))
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    while len(selected) < min(target, len(candidates)):
        progressed = False
        for claim_type in sorted(pools):
            row = next((item for item in pools[claim_type] if str(item["claim_id"]) not in used), None)
            if row is None:
                continue
            used.add(str(row["claim_id"]))
            selected.append(row)
            progressed = True
            if len(selected) >= min(target, len(candidates)):
                break
        if not progressed:
            break
    selected.sort(key=lambda row: stable_int(seed, str(row["claim_id"])))
    return selected


def stage2_dev_videos(source_videos: set[str], seed: int, count: int) -> set[str]:
    if count <= 0 or count >= len(source_videos):
        raise ValueError("stage2-dev video count must be within the source-video range")
    ranked = sorted(source_videos, key=lambda value: stable_int(seed + 101, value))
    return set(ranked[:count])


def materialize_model_input(
    source: dict[str, Any],
    pair_id: str,
    input_id: str,
    asr_excerpt: str,
    frame_indices: list[int],
) -> dict[str, Any]:
    return {
        "schema": "adsqa_modality_counterfactual_model_input_v2",
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
        "asr_excerpt": asr_excerpt,
        "frame_indices": frame_indices,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--evidence-questions", type=Path, required=True)
    parser.add_argument("--holdout-claims", type=Path, required=True)
    parser.add_argument("--target-sources", type=int, default=500)
    parser.add_argument("--variants-per-source", type=int, default=2)
    parser.add_argument("--stage2-dev-video-count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--goal-start-epoch", type=int, required=True)
    args = parser.parse_args()
    if args.variants_per_source != 2:
        raise ValueError("exactly two counterfactual variants are required")

    rows = read_jsonl(args.claims)
    evidence_rows = read_rows(args.evidence_questions)
    holdout_rows = read_rows(args.holdout_claims)
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

    eligible_count = sum(
        row.get("split") == "train"
        and row.get("label") == "supported"
        and float(row.get("annotation_confidence", 0) or 0) >= 0.8
        and str(row.get("text", "")).strip()
        and len(as_int_list(row.get("selected_frame_indices"))) == 32
        for row in rows
    )
    selected = select_sources(rows, args.target_sources, args.seed)
    if len(selected) < args.target_sources:
        raise RuntimeError(f"need {args.target_sources} eligible sources, found {len(selected)}")

    source_videos = {str(row["video_id"]) for row in selected}
    dev_videos = stage2_dev_videos(source_videos, args.seed, args.stage2_dev_video_count)
    positive_inputs: list[dict[str, Any]] = []
    negative_inputs: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for row in selected:
        source_claim_id = str(row["claim_id"])
        modality = required_modality(row)
        partition = "stage2_dev" if str(row["video_id"]) in dev_videos else "train_fit"
        source_provenance = str(
            row.get(
                "source_label_policy",
                "train_reference_answer_not_human_gold",
            )
        )
        source = {
            "schema": "adsqa_modality_counterfactual_source_v2",
            "source_claim_id": source_claim_id,
            "source_question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "video_path": str(row["video_path"]),
            "claim_type": str(row.get("claim_type", "other")),
            "required_modality": modality,
            "stage2_partition": partition,
            "question": str(row["question"]),
            "atomic_claim": str(row["text"]),
            "asr_excerpt": str(row.get("asr_excerpt", "") or ""),
            "selected_frame_indices": as_int_list(row.get("selected_frame_indices")),
            "router_inputs": row.get("router_inputs", {}),
            "frame_count": int(row.get("frame_count", 0) or 0),
            "requested_modality": str(row.get("requested_modality", "")),
            "extraction_status": str(row.get("extraction_status", "")),
            "source_label": source_provenance,
            "label_provenance": source_provenance,
            "not_human_gold": True,
        }
        source_rows.append(source)
        for variant in range(args.variants_per_source):
            pair_id = f"{source_claim_id}__cf{variant + 1:02d}"
            positive_input_id = opaque_input_id(args.seed, pair_id, "a")
            negative_input_id = opaque_input_id(args.seed, pair_id, "b")
            corruption_type, negative_plan = build_negative(row, variant, args.seed, modality)
            visual_operation = negative_plan.get("visual_operation")
            negative_frames = (
                as_int_list(visual_operation.get("frame_indices"))
                if isinstance(visual_operation, dict)
                else source["selected_frame_indices"]
            )
            positive_inputs.append(
                materialize_model_input(
                    source,
                    pair_id,
                    positive_input_id,
                    source["asr_excerpt"],
                    source["selected_frame_indices"],
                )
            )
            negative_inputs.append(
                materialize_model_input(
                    source,
                    pair_id,
                    negative_input_id,
                    str(negative_plan.get("asr_excerpt", source["asr_excerpt"])),
                    negative_frames,
                )
            )
            label_rows.extend(
                [
                    {
                        "schema": "adsqa_modality_counterfactual_label_v2",
                        "input_id": positive_input_id,
                        "pair_id": pair_id,
                        "label": 1,
                        "evidence_state": "supported",
                        "label_source": source_provenance,
                        "not_human_gold": True,
                    },
                    {
                        "schema": "adsqa_modality_counterfactual_label_v2",
                        "input_id": negative_input_id,
                        "pair_id": pair_id,
                        "label": 0,
                        "evidence_state": "insufficient",
                        "label_source": "synthetic_intervention_not_human_gold",
                        "not_human_gold": True,
                    },
                ]
            )
            pair_rows.append(
                {
                    "schema": "adsqa_modality_counterfactual_pair_v2",
                    "pair_id": pair_id,
                    "source_claim_id": source_claim_id,
                    "source_question_id": source["source_question_id"],
                    "video_id": source["video_id"],
                    "stage2_partition": partition,
                    "required_modality": modality,
                    "positive_input_id": positive_input_id,
                    "negative_input_id": negative_input_id,
                    "negative_corruption_type": corruption_type,
                    "negative_plan": negative_plan,
                    "label_provenance": "synthetic_intervention_not_human_gold",
                    "not_human_gold": True,
                }
            )

    inputs = positive_inputs + negative_inputs
    inputs.sort(key=lambda row: stable_int(args.seed, str(row["input_id"])))
    source_path = args.output_root / "source_claims.jsonl"
    inputs_path = args.output_root / "model_inputs.jsonl"
    pairs_path = args.output_root / "pairs.jsonl"
    labels_path = args.output_root / "labels.jsonl"
    audit_path = args.output_root / "audit.json"
    write_jsonl(source_path, source_rows)
    write_jsonl(inputs_path, inputs)
    write_jsonl(pairs_path, pair_rows)
    write_jsonl(labels_path, label_rows)

    forbidden_input_paths = [
        f"model_inputs.jsonl[{index}].{key}"
        for index, row in enumerate(inputs)
        for key in FORBIDDEN_INPUT_KEYS
        if key in row
    ]
    input_role_markers = [
        row["input_id"]
        for row in inputs
        if "positive" in row["input_id"].lower() or "negative" in row["input_id"].lower()
    ]
    invalid_operations = [
        row["pair_id"]
        for row in pair_rows
        if not visual_operation_valid(row["negative_corruption_type"], row["negative_plan"])
    ]
    unchanged_negative_pairs = [
        row["pair_id"]
        for row in pair_rows
        if not evidence_changed(
            next(source for source in source_rows if source["source_claim_id"] == row["source_claim_id"]),
            row["negative_corruption_type"],
            row["negative_plan"],
        )
    ]
    fallback_pairs = [
        row
        for row in pair_rows
        if isinstance(row["negative_plan"].get("visual_operation"), dict)
        and row["negative_plan"]["visual_operation"].get("fallback_used", False)
    ]
    source_video_overlap = {
        "calibration": sorted(source_videos & calibration_videos),
        "development": sorted(source_videos & development_videos),
        "evidence300": sorted(source_videos & evidence_videos),
    }
    audit = {
        "schema": "adsqa_modality_counterfactual_train_audit_v2",
        "source_count": len(source_rows),
        "pair_count": len(pair_rows),
        "model_input_count": len(inputs),
        "positive_count": len(positive_inputs),
        "negative_count": len(negative_inputs),
        "unique_source_video_count": len(source_videos),
        "stage2_partition_counts": dict(sorted(Counter(row["stage2_partition"] for row in source_rows).items())),
        "stage2_partition_video_counts": {
            "train_fit": len(source_videos - dev_videos),
            "stage2_dev": len(dev_videos),
        },
        "claim_type_counts": dict(sorted(Counter(row["claim_type"] for row in source_rows).items())),
        "requested_modality_counts": dict(
            sorted(Counter(row["requested_modality"] for row in source_rows).items())
        ),
        "extraction_status_counts": dict(
            sorted(Counter(row["extraction_status"] for row in source_rows).items())
        ),
        "source_label_provenance_counts": dict(
            sorted(Counter(row["label_provenance"] for row in source_rows).items())
        ),
        "required_modality_counts": dict(sorted(Counter(row["required_modality"] for row in source_rows).items())),
        "corruption_counts": dict(sorted(Counter(row["negative_corruption_type"] for row in pair_rows).items())),
        "fallback_count": len(fallback_pairs),
        "fallback_operation_counts": dict(
            sorted(
                Counter(
                    row["negative_plan"]["visual_operation"].get("operation", "unknown")
                    for row in fallback_pairs
                ).items()
            )
        ),
        "source_video_overlap": source_video_overlap,
        "invalid_negative_operation_count": len(invalid_operations),
        "invalid_negative_operation_pairs": invalid_operations,
        "unchanged_negative_count": len(unchanged_negative_pairs),
        "unchanged_negative_pairs": unchanged_negative_pairs,
        "forbidden_input_paths": forbidden_input_paths,
        "input_role_markers": input_role_markers,
        "reference_answers_in_model_inputs": False,
        "old_labels_in_model_inputs": False,
        "eligible_source_count": eligible_count,
        "not_human_gold": True,
        "development_used_for_selection": False,
        "passed": (
            len(source_rows) >= args.target_sources
            and len(pair_rows) == args.target_sources * args.variants_per_source
            and len(positive_inputs) == len(negative_inputs)
            and len(inputs) == len(pair_rows) * 2
            and not any(source_video_overlap.values())
            and not invalid_operations
            and not unchanged_negative_pairs
            and not forbidden_input_paths
            and not input_role_markers
        ),
    }
    write_json(audit_path, audit)
    manifest = {
        "schema": "adsqa_modality_counterfactual_train_manifest_v2",
        "seed": args.seed,
        "goal_start_epoch": args.goal_start_epoch,
        "claims_sha256": sha256_file(args.claims),
        "evidence_questions_sha256": sha256_file(args.evidence_questions),
        "holdout_claims_sha256": sha256_file(args.holdout_claims),
        "source_claims_sha256": sha256_file(source_path),
        "model_inputs_sha256": sha256_file(inputs_path),
        "pairs_sha256": sha256_file(pairs_path),
        "labels_sha256": sha256_file(labels_path),
        "audit_sha256": sha256_file(audit_path),
        "label_policy": "synthetic_intervention_not_human_gold",
        "not_human_gold": True,
        "audit": audit,
    }
    write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
