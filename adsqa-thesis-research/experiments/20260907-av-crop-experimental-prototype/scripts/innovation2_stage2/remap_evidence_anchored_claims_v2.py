#!/usr/bin/env python3
"""Recover evidence anchors when Qwen returns source frame indices, not view positions.

This is a CPU-only post-processing repair for frozen raw Qwen extraction traces.
It emits internal synthetic supervision only and never treats its output as human
gold annotation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any


MODALITY_SCHEDULE = ["asr", "visual", "ocr", "joint", "visual"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates-jsonl", type=Path, required=True)
    parser.add_argument("--raw-qwen-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260718)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_int(seed: int, value: str) -> int:
    return int(hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()[:16], 16)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def parse_object(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def normalize_box(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        return [0.0, 0.0, 1.0, 1.0]
    try:
        box = [max(0.0, min(1.0, float(item))) for item in value]
    except (TypeError, ValueError):
        return [0.0, 0.0, 1.0, 1.0]
    if box[2] <= box[0] or box[3] <= box[1]:
        return [0.0, 0.0, 1.0, 1.0]
    return box


def remap_anchor_position(value: Any, selected_frames: list[int]) -> tuple[int | None, str | None]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, None
    if 0 <= number < len(selected_frames):
        return number, "view_position"
    if number in selected_frames:
        return selected_frames.index(number), "source_frame_index"
    return None, None


def is_exact_asr_quote(quote: str, asr: str) -> bool:
    return bool(quote.strip()) and quote.casefold() in asr.casefold()


def fallback_asr(source: dict[str, Any], seed: int, reason: str) -> dict[str, Any]:
    words = str(source.get("asr_excerpt", "") or "").split()
    if not words:
        return {
            "claim_type": "audio",
            "text": "",
            "anchor_positions": [],
            "anchor_regions": [],
            "anchor_asr_quote": "",
            "extraction_status": f"invalid_no_asr_{reason}",
            "coordinate_encodings": [],
        }
    length = min(12, len(words))
    start = stable_int(seed, str(source["claim_id"])) % max(1, len(words) - length + 1)
    quote = " ".join(words[start : start + length]).strip()
    return {
        "claim_type": "audio",
        "text": f'The ASR excerpt contains the phrase "{quote}".',
        "anchor_positions": [],
        "anchor_regions": [],
        "anchor_asr_quote": quote,
        "extraction_status": f"fallback_asr_quote_{reason}",
        "coordinate_encodings": [],
    }


def requested_modalities(rows: list[dict[str, Any]]) -> dict[str, str]:
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    assigned: dict[str, str] = {}
    for video_rows in by_video.values():
        video_rows.sort(key=lambda row: str(row["claim_id"]))
        for rank, row in enumerate(video_rows):
            assigned[str(row["claim_id"])] = MODALITY_SCHEDULE[rank % len(MODALITY_SCHEDULE)]
    return assigned


def recover_anchor(
    source: dict[str, Any],
    raw_text: str,
    required_modality: str,
    seed: int,
) -> dict[str, Any]:
    raw = parse_object(raw_text)
    if not raw:
        return fallback_asr(source, seed, f"after_parse_failure_for_{required_modality}")

    source_asr = str(source.get("asr_excerpt", "") or "").strip()
    selected_frames = [int(value) for value in source.get("selected_frame_indices", [])]
    modality = str(raw.get("modality", "") or "").strip().lower()
    if modality == "brand":
        modality = "ocr"
    claim = str(raw.get("claim", "") or "").strip()
    quote = str(raw.get("anchor_asr_quote", "") or "").strip()
    compatible = modality == required_modality
    if required_modality == "ocr" and modality == "ocr":
        compatible = True
    if not compatible:
        return fallback_asr(source, seed, f"after_wrong_modality_{modality or 'missing'}_for_{required_modality}")

    position_values = list(raw.get("anchor_frame_positions", []) or [])
    remapped_positions: list[int] = []
    encodings: list[str] = []
    for value in position_values:
        position, encoding = remap_anchor_position(value, selected_frames)
        if position is not None:
            remapped_positions.append(position)
            if encoding:
                encodings.append(encoding)

    remapped_regions: list[dict[str, Any]] = []
    for region in raw.get("anchor_regions", []) or []:
        if not isinstance(region, dict):
            continue
        position, encoding = remap_anchor_position(region.get("position"), selected_frames)
        if position is None:
            continue
        remapped_regions.append({"position": position, "bbox_norm": normalize_box(region.get("bbox_norm"))})
        if encoding:
            encodings.append(encoding)

    positions = sorted(set(remapped_positions + [region["position"] for region in remapped_regions]))
    if modality == "asr":
        if is_exact_asr_quote(quote, source_asr):
            return {
                "claim_type": "audio",
                "text": f'The ASR excerpt contains the phrase "{quote}".',
                "anchor_positions": [],
                "anchor_regions": [],
                "anchor_asr_quote": quote,
                "extraction_status": "qwen_asr_quote_validated",
                "coordinate_encodings": [],
            }
        return fallback_asr(source, seed, "after_invalid_model_quote_for_asr")

    if len(claim) < 8 or len(claim) > 280 or not positions:
        return fallback_asr(source, seed, f"after_invalid_{required_modality}_claim")
    if modality == "joint" and not is_exact_asr_quote(quote, source_asr):
        return fallback_asr(source, seed, "after_invalid_joint_asr_quote")

    regions_by_position = {region["position"]: region for region in remapped_regions}
    anchor_regions = [
        regions_by_position.get(position, {"position": position, "bbox_norm": [0.0, 0.0, 1.0, 1.0]})
        for position in positions[:4]
    ]
    remapped = "source_frame_index" in encodings
    return {
        "claim_type": modality,
        "text": claim,
        "anchor_positions": positions[:4],
        "anchor_regions": anchor_regions,
        "anchor_asr_quote": quote if modality == "joint" else "",
        "extraction_status": (
            "qwen_evidence_anchored_remapped_source_frame_index"
            if remapped
            else "qwen_evidence_anchored_view_position"
        ),
        "coordinate_encodings": sorted(set(encodings)),
    }


def main() -> None:
    args = parse_args()
    if args.output_jsonl.exists() or args.audit_json.exists():
        raise RuntimeError("refusing to overwrite existing remap artifacts")

    candidates = read_jsonl(args.candidates_jsonl)
    raw_rows = read_jsonl(args.raw_qwen_jsonl)
    raw_by_source = {str(row["source_claim_id"]): row for row in raw_rows}
    requested = requested_modalities(candidates)
    outputs: list[dict[str, Any]] = []
    missing_raw: list[str] = []
    for source in candidates:
        source_id = str(source["claim_id"])
        raw = raw_by_source.get(source_id)
        if raw is None:
            missing_raw.append(source_id)
            anchor = fallback_asr(source, args.seed, "missing_raw_qwen_trace")
        else:
            anchor = recover_anchor(
                source,
                str(raw.get("model_text", "")),
                requested[source_id],
                args.seed,
            )
        outputs.append(
            {
                **source,
                "claim_id": f"{source_id}__anchored_remap",
                "claim_type": anchor["claim_type"],
                "text": anchor["text"],
                "evidence_anchor_positions": anchor["anchor_positions"],
                "evidence_anchor_regions": anchor["anchor_regions"],
                "evidence_anchor_asr_quote": anchor["anchor_asr_quote"],
                "requested_modality": requested[source_id],
                "extraction_status": anchor["extraction_status"],
                "anchor_coordinate_encodings": anchor["coordinate_encodings"],
                "annotation_confidence": 0.8,
                "source_label_policy": "frozen_qwen_evidence_extraction_coordinate_remap_not_human_gold",
                "not_human_gold": True,
            }
        )

    empty_claim_ids = [str(row["claim_id"]) for row in outputs if not str(row["text"]).strip()]
    coordinate_counts = Counter(
        encoding
        for row in outputs
        for encoding in row.get("anchor_coordinate_encodings", [])
    )
    direct_modalities = {"visual", "ocr", "joint"}
    audit = {
        "schema": "adsqa_evidence_anchored_claim_coordinate_remap_audit_v1",
        "input_candidate_count": len(candidates),
        "raw_qwen_count": len(raw_rows),
        "output_count": len(outputs),
        "missing_raw_count": len(missing_raw),
        "missing_raw_claim_ids": missing_raw,
        "empty_claim_count": len(empty_claim_ids),
        "empty_claim_ids": empty_claim_ids,
        "claim_type_counts": dict(sorted(Counter(row["claim_type"] for row in outputs).items())),
        "requested_modality_counts": dict(
            sorted(Counter(row["requested_modality"] for row in outputs).items())
        ),
        "extraction_status_counts": dict(
            sorted(Counter(row["extraction_status"] for row in outputs).items())
        ),
        "anchor_coordinate_encoding_counts": dict(sorted(coordinate_counts.items())),
        "direct_visual_ocr_joint_count": sum(
            row["claim_type"] in direct_modalities
            and row["extraction_status"].startswith("qwen_evidence_anchored")
            for row in outputs
        ),
        "candidates_sha256": sha256_file(args.candidates_jsonl),
        "raw_qwen_sha256": sha256_file(args.raw_qwen_jsonl),
        "not_human_gold": True,
        "passed": (
            len(outputs) == len(candidates)
            and len(raw_rows) == len(candidates)
            and not missing_raw
            and not empty_claim_ids
        ),
    }
    write_jsonl(args.output_jsonl, outputs)
    write_json(args.audit_json, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
