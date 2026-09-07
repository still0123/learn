#!/usr/bin/env python3
"""Build auditable 500-source data for candidate-D continuous pairwise ranking.

The builder creates two controlled negative pairs per source:

* ASR sources replace the evidence excerpt with explicit, non-empty missingness
  states.
* OCR sources derive a claim from a high-confidence OCR detection and mosaic
  every matching text box in the fixed 32-frame evidence packet.

All supervision is machine-derived weak supervision and is explicitly marked
``not_human_gold=true`` outside model inputs. Labels and provenance are kept
out of ``model_inputs.jsonl``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any


ASR_UNAVAILABLE = "[[ASR_UNAVAILABLE: extraction_failed]]"
ASR_NOT_DETECTED = "[[ASR_AVAILABLE: no matching aligned speech segment detected]]"
FORBIDDEN_INPUT_KEYS = {
    "evidence_state",
    "label",
    "label_provenance",
    "not_human_gold",
    "pairwise_target",
    "reference_answer",
    "role",
    "source_label",
    "source_label_policy",
    "visual_operation",
}
_OCR: Any = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-claims", type=Path, required=True)
    parser.add_argument("--evidence-questions", type=Path, required=True)
    parser.add_argument("--holdout-claims", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--rapidocr-package-dir", type=Path, required=True)
    parser.add_argument("--target-sources", type=int, default=500)
    parser.add_argument("--target-ocr-sources", type=int, default=250)
    parser.add_argument("--minimum-ocr-sources", type=int, default=150)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--threads-per-worker", type=int, default=1)
    parser.add_argument("--min-ocr-score", type=float, default=0.80)
    parser.add_argument("--max-text-positions", type=int, default=4)
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
    value = f"{seed}:{pair_id}:{branch}".encode("utf-8")
    return f"in_{hashlib.sha256(value).hexdigest()[:24]}"


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


def normalize_text(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def expand_box(box: list[float], padding: float) -> list[float]:
    left, top, right, bottom = [max(0.0, min(1.0, float(value))) for value in box]
    return [
        max(0.0, left - padding),
        max(0.0, top - padding),
        min(1.0, right + padding),
        min(1.0, bottom + padding),
    ]


def quote_from_asr(asr_excerpt: str) -> str | None:
    compact = " ".join(asr_excerpt.split())
    if not compact:
        return None
    candidates = [segment.strip() for segment in re.split(r"[.!?]+", compact) if segment.strip()]
    for candidate in candidates:
        words = candidate.split()
        if len(words) >= 4:
            return " ".join(words[: min(18, len(words))])
    words = compact.split()
    return " ".join(words[: min(18, len(words))]) if len(words) >= 4 else None


def init_ocr_worker(package_dir: str, threads_per_worker: int) -> None:
    global _OCR
    if package_dir not in sys.path:
        sys.path.insert(0, package_dir)
    os.environ["OMP_NUM_THREADS"] = str(max(1, threads_per_worker))
    os.environ["OPENBLAS_NUM_THREADS"] = str(max(1, threads_per_worker))
    from rapidocr import RapidOCR

    _OCR = RapidOCR(
        params={
            "Global.use_cls": False,
            "Global.log_level": "error",
            "EngineConfig.onnxruntime.intra_op_num_threads": max(1, threads_per_worker),
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        }
    )


def scan_video_ocr(task: dict[str, Any]) -> dict[str, Any]:
    import cv2
    from decord import VideoReader, cpu

    reader = VideoReader(task["video_path"], ctx=cpu(0), num_threads=1)
    frames: list[dict[str, Any]] = []
    for position, frame_index in enumerate(task["frame_indices"]):
        rgb = reader.get_batch([frame_index]).asnumpy()[0]
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        height, width = bgr.shape[:2]
        result = _OCR(bgr)
        serialized = result.to_json() if result is not None else None
        detections: list[dict[str, Any]] = []
        for detection in serialized or []:
            score = float(detection.get("score", 0.0))
            points = detection.get("box") or []
            text = str(detection.get("txt", "")).strip()
            if score < task["min_ocr_score"] or not points or not text:
                continue
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            bbox_norm = [
                min(xs) / width,
                min(ys) / height,
                max(xs) / width,
                max(ys) / height,
            ]
            detections.append(
                {
                    "text": text,
                    "normalized_text": normalize_text(text),
                    "score": score,
                    "bbox_norm": bbox_norm,
                }
            )
        frames.append(
            {
                "position": position,
                "frame_index": frame_index,
                "detections": detections,
            }
        )
    return {
        "schema": "adsqa_candidate_d_ocr_cache_v1",
        "video_id": task["video_id"],
        "video_path": task["video_path"],
        "frame_indices": task["frame_indices"],
        "min_ocr_score": task["min_ocr_score"],
        "frames": frames,
        "not_human_gold": True,
    }


def scan_ocr_cache(
    rows: list[dict[str, Any]],
    package_dir: Path,
    workers: int,
    threads_per_worker: int,
    min_ocr_score: float,
) -> dict[str, dict[str, Any]]:
    by_video: dict[str, dict[str, Any]] = {}
    for row in rows:
        video_id = str(row["video_id"])
        plan = [int(value) for value in row.get("selected_frame_indices", [])]
        if len(plan) != 32 or len(set(plan)) != 32:
            raise ValueError(f"invalid fixed frame plan for {row['source_claim_id']}")
        existing = by_video.get(video_id)
        if existing is not None and existing["frame_indices"] != plan:
            raise ValueError(f"inconsistent fixed frame plans for video {video_id}")
        by_video[video_id] = {
            "video_id": video_id,
            "video_path": str(row["video_path"]),
            "frame_indices": plan,
            "min_ocr_score": min_ocr_score,
        }
    scanned: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(
        max_workers=max(1, workers),
        initializer=init_ocr_worker,
        initargs=(str(package_dir), max(1, threads_per_worker)),
    ) as executor:
        futures = {
            executor.submit(scan_video_ocr, task): task["video_id"]
            for task in by_video.values()
        }
        for complete, future in enumerate(as_completed(futures), start=1):
            item = future.result()
            scanned[str(item["video_id"])] = item
            nonempty = sum(bool(frame["detections"]) for frame in item["frames"])
            print(
                f"ocr {complete}/{len(futures)} {item['video_id']} nonempty_frames={nonempty}",
                flush=True,
            )
    return scanned


def choose_ocr_candidate(
    row: dict[str, Any],
    cache: dict[str, Any],
    max_text_positions: int,
) -> dict[str, Any] | None:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in cache["frames"]:
        for detection in frame["detections"]:
            normalized = str(detection["normalized_text"])
            if len(normalized) < 3:
                continue
            groups[normalized].append(
                {
                    "position": int(frame["position"]),
                    "frame_index": int(frame["frame_index"]),
                    "text": str(detection["text"]),
                    "score": float(detection["score"]),
                    "bbox_norm": [float(value) for value in detection["bbox_norm"]],
                }
            )
    candidates: list[dict[str, Any]] = []
    for normalized, detections in groups.items():
        positions = sorted({item["position"] for item in detections})
        if len(positions) > max_text_positions:
            continue
        best = max(detections, key=lambda item: (item["score"], len(item["text"])))
        candidates.append(
            {
                "normalized_text": normalized,
                "text": best["text"],
                "max_score": max(item["score"] for item in detections),
                "positions": positions,
                "detections": sorted(
                    detections,
                    key=lambda item: (item["position"], item["bbox_norm"], item["text"]),
                ),
            }
        )
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            len(item["positions"]),
            -item["max_score"],
            -len(item["text"]),
            item["normalized_text"],
        )
    )
    return candidates[0]


def allocate_partition_targets(
    source_counts: dict[str, int],
    target: int,
) -> dict[str, int]:
    total = sum(source_counts.values())
    if total <= 0 or target < 0 or target > total:
        raise ValueError(f"invalid target allocation total={total} target={target}")
    fractional = {
        partition: target * count / total for partition, count in source_counts.items()
    }
    allocated = {partition: int(value) for partition, value in fractional.items()}
    remaining = target - sum(allocated.values())
    for partition in sorted(
        source_counts,
        key=lambda item: (fractional[item] - allocated[item], source_counts[item], item),
        reverse=True,
    ):
        if remaining <= 0:
            break
        allocated[partition] += 1
        remaining -= 1
    return allocated


def make_model_input(
    source: dict[str, Any],
    pair_id: str,
    input_id: str,
    asr_excerpt: str,
) -> dict[str, Any]:
    return {
        "schema": "adsqa_candidate_d_formal_model_input_v1",
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
        "frame_indices": source["selected_frame_indices"],
    }


def make_mosaic_operation(candidate: dict[str, Any], padding: float) -> dict[str, Any]:
    positions = [int(item["position"]) for item in candidate["detections"]]
    boxes = [expand_box(list(item["bbox_norm"]), padding) for item in candidate["detections"]]
    return {
        "valid": bool(positions) and len(positions) == len(boxes),
        "operation": "same_area_mosaic",
        "mosaic_positions": positions,
        "mosaic_boxes_norm": boxes,
        "mosaic_side": 1,
        "target_text": candidate["text"],
        "target_text_normalized": candidate["normalized_text"],
        "target_text_occurrence_positions": candidate["positions"],
        "box_padding": padding,
        "fallback_used": False,
        "fallback_reason": None,
    }


def labels_are_separate(
    labels: list[dict[str, Any]],
    model_inputs_by_id: dict[str, dict[str, Any]],
) -> bool:
    return all(
        input_id not in model_inputs_by_id or "label" not in model_inputs_by_id[input_id]
        for input_id in (row["input_id"] for row in labels)
    )


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_root}")
    if not args.rapidocr_package_dir.is_dir():
        raise FileNotFoundError(f"missing RapidOCR package: {args.rapidocr_package_dir}")
    if args.target_sources != 500:
        raise ValueError("candidate-D formal data requires exactly 500 sources")
    if not 0 < args.minimum_ocr_sources <= args.target_ocr_sources <= args.target_sources:
        raise ValueError("invalid OCR source requirements")

    source_rows = read_jsonl(args.source_claims)
    if len(source_rows) != args.target_sources:
        raise ValueError(
            f"expected exactly {args.target_sources} frozen source rows, got {len(source_rows)}"
        )
    source_ids = [str(row["source_claim_id"]) for row in source_rows]
    source_question_ids = [str(row["source_question_id"]) for row in source_rows]
    if len(set(source_ids)) != args.target_sources or len(set(source_question_ids)) != args.target_sources:
        raise ValueError("source claims must provide unique source and question IDs")
    if any(row.get("not_human_gold") is not True for row in source_rows):
        raise ValueError("every frozen source must be explicitly not_human_gold=true")
    if any(row.get("stage2_partition") not in {"train_fit", "stage2_dev"} for row in source_rows):
        raise ValueError("source partitions must be train_fit or stage2_dev")

    started_at = int(time.time())
    ocr_cache = scan_ocr_cache(
        source_rows,
        args.rapidocr_package_dir,
        args.workers,
        args.threads_per_worker,
        args.min_ocr_score,
    )
    cache_rows = [ocr_cache[video_id] for video_id in sorted(ocr_cache)]
    write_jsonl(args.output_root / "ocr_cache.jsonl", cache_rows)

    ocr_candidates: dict[str, dict[str, Any]] = {}
    for row in source_rows:
        candidate = choose_ocr_candidate(
            row,
            ocr_cache[str(row["video_id"])],
            args.max_text_positions,
        )
        if candidate is not None:
            ocr_candidates[str(row["source_claim_id"])] = candidate

    source_counts = Counter(str(row["stage2_partition"]) for row in source_rows)
    ocr_target = min(args.target_ocr_sources, len(ocr_candidates))
    coverage_audit = {
        "schema": "adsqa_candidate_d_ocr_coverage_audit_v1",
        "source_count": len(source_rows),
        "unique_video_count": len(ocr_cache),
        "ocr_eligible_source_count": len(ocr_candidates),
        "requested_ocr_source_count": args.target_ocr_sources,
        "minimum_ocr_source_count": args.minimum_ocr_sources,
        "not_human_gold": True,
    }
    write_json(args.output_root / "ocr_coverage_audit.json", coverage_audit)
    if ocr_target < args.minimum_ocr_sources:
        raise RuntimeError(
            f"OCR coverage is insufficient: eligible={len(ocr_candidates)} "
            f"minimum={args.minimum_ocr_sources}"
        )
    partition_targets = allocate_partition_targets(dict(source_counts), ocr_target)
    selected_ocr_ids: set[str] = set()
    for partition, target in partition_targets.items():
        eligible = [
            row
            for row in source_rows
            if row["stage2_partition"] == partition
            and str(row["source_claim_id"]) in ocr_candidates
        ]
        eligible.sort(key=lambda row: stable_int(args.seed, f"ocr:{row['source_claim_id']}"))
        if len(eligible) < target:
            raise RuntimeError(
                f"OCR coverage is insufficient in {partition}: eligible={len(eligible)} target={target}"
            )
        selected_ocr_ids.update(str(row["source_claim_id"]) for row in eligible[:target])

    sources: list[dict[str, Any]] = []
    model_inputs: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    rejected_sources: list[dict[str, Any]] = []
    for row in sorted(source_rows, key=lambda item: stable_int(args.seed, str(item["source_claim_id"]))):
        source_claim_id = str(row["source_claim_id"])
        selected_frames = [int(value) for value in row["selected_frame_indices"]]
        is_ocr = source_claim_id in selected_ocr_ids
        if is_ocr:
            candidate = ocr_candidates[source_claim_id]
            source = {
                "schema": "adsqa_candidate_d_formal_source_v1",
                "source_claim_id": source_claim_id,
                "source_question_id": str(row["source_question_id"]),
                "video_id": str(row["video_id"]),
                "video_path": str(row["video_path"]),
                "stage2_partition": str(row["stage2_partition"]),
                "claim_type": "ocr",
                "required_modality": "ocr",
                "question": str(row["question"]),
                "atomic_claim": f'The on-screen text "{candidate["text"]}" is visible.',
                "asr_excerpt": "",
                "selected_frame_indices": selected_frames,
                "source_label_policy": "rapidocr_detected_text_not_human_gold",
                "not_human_gold": True,
            }
            variants = [
                ("ocr_text_mosaic_tight", make_mosaic_operation(candidate, 0.01)),
                ("ocr_text_mosaic_padded", make_mosaic_operation(candidate, 0.04)),
            ]
        else:
            quote = quote_from_asr(str(row.get("asr_excerpt", "")))
            if quote is None:
                rejected_sources.append(
                    {"source_claim_id": source_claim_id, "reason": "missing_usable_asr_quote"}
                )
                continue
            source = {
                "schema": "adsqa_candidate_d_formal_source_v1",
                "source_claim_id": source_claim_id,
                "source_question_id": str(row["source_question_id"]),
                "video_id": str(row["video_id"]),
                "video_path": str(row["video_path"]),
                "stage2_partition": str(row["stage2_partition"]),
                "claim_type": "audio",
                "required_modality": "asr",
                "question": str(row["question"]),
                "atomic_claim": f'The supplied ASR excerpt contains the phrase "{quote}".',
                "asr_excerpt": str(row["asr_excerpt"]),
                "selected_frame_indices": selected_frames,
                "source_label_policy": "asr_excerpt_span_not_human_gold",
                "not_human_gold": True,
            }
            variants = [
                (
                    "asr_unavailable_explicit",
                    {
                        "valid": True,
                        "operation": "none",
                        "modality_missingness": "asr_unavailable_due_to_extraction_failure",
                        "fallback_used": False,
                        "fallback_reason": None,
                    },
                ),
                (
                    "asr_not_detected_explicit",
                    {
                        "valid": True,
                        "operation": "none",
                        "modality_missingness": "asr_available_but_target_quote_not_detected",
                        "fallback_used": False,
                        "fallback_reason": None,
                    },
                ),
            ]
        sources.append(source)
        for variant_index, (corruption_type, operation) in enumerate(variants, start=1):
            pair_id = f"{source_claim_id}__formal_cf{variant_index:02d}"
            positive_id = opaque_input_id(args.seed, pair_id, "positive")
            negative_id = opaque_input_id(args.seed, pair_id, "negative")
            negative_asr = (
                ASR_UNAVAILABLE
                if corruption_type == "asr_unavailable_explicit"
                else ASR_NOT_DETECTED
                if corruption_type == "asr_not_detected_explicit"
                else ""
            )
            model_inputs.extend(
                [
                    make_model_input(source, pair_id, positive_id, source["asr_excerpt"]),
                    make_model_input(source, pair_id, negative_id, negative_asr),
                ]
            )
            labels.extend(
                [
                    {
                        "schema": "adsqa_candidate_d_formal_label_v1",
                        "input_id": positive_id,
                        "pair_id": pair_id,
                        "label": 1,
                        "evidence_state": "supported",
                        "label_source": source["source_label_policy"],
                        "not_human_gold": True,
                    },
                    {
                        "schema": "adsqa_candidate_d_formal_label_v1",
                        "input_id": negative_id,
                        "pair_id": pair_id,
                        "label": 0,
                        "evidence_state": "synthetic_modality_missingness_or_text_mosaic",
                        "label_source": "synthetic_intervention_not_human_gold",
                        "not_human_gold": True,
                    },
                ]
            )
            pairs.append(
                {
                    "schema": "adsqa_candidate_d_formal_pair_v1",
                    "pair_id": pair_id,
                    "source_claim_id": source_claim_id,
                    "source_question_id": source["source_question_id"],
                    "video_id": source["video_id"],
                    "stage2_partition": source["stage2_partition"],
                    "required_modality": source["required_modality"],
                    "positive_input_id": positive_id,
                    "negative_input_id": negative_id,
                    "negative_corruption_type": corruption_type,
                    "negative_plan": {
                        "valid": bool(operation.get("valid", False)),
                        "visual_operation": operation,
                        "fallback_used": False,
                        "fallback_reason": None,
                    },
                    "label_provenance": "synthetic_intervention_not_human_gold",
                    "not_human_gold": True,
                }
            )

    model_inputs.sort(key=lambda row: stable_int(args.seed, str(row["input_id"])))
    sources.sort(key=lambda row: stable_int(args.seed, str(row["source_claim_id"])))
    pairs.sort(key=lambda row: stable_int(args.seed, str(row["pair_id"])))
    labels.sort(key=lambda row: stable_int(args.seed, str(row["input_id"])))
    model_inputs_by_id = {row["input_id"]: row for row in model_inputs}
    forbidden_input_paths = [
        f"model_inputs.jsonl[{index}].{key}"
        for index, row in enumerate(model_inputs)
        for key in FORBIDDEN_INPUT_KEYS
        if key in row
    ]
    source_video_ids = {str(row["video_id"]) for row in sources}
    evidence_videos = {
        video_id_from_row(row) for row in read_rows(args.evidence_questions) if video_id_from_row(row)
    }
    holdout_rows = read_rows(args.holdout_claims)
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
    source_video_overlap = {
        "calibration": sorted(source_video_ids & calibration_videos),
        "development": sorted(source_video_ids & development_videos),
        "evidence300": sorted(source_video_ids & evidence_videos),
    }
    invalid_ocr_pairs: list[str] = []
    for pair in pairs:
        if pair["required_modality"] != "ocr":
            continue
        operation = pair["negative_plan"]["visual_operation"]
        positions = operation.get("mosaic_positions", [])
        boxes = operation.get("mosaic_boxes_norm", [])
        if (
            operation.get("operation") != "same_area_mosaic"
            or not operation.get("valid")
            or not positions
            or len(positions) != len(boxes)
            or any(not 0 <= int(position) < 32 for position in positions)
            or any(len(box) != 4 for box in boxes)
        ):
            invalid_ocr_pairs.append(pair["pair_id"])
    input_role_markers = [
        row["input_id"]
        for row in model_inputs
        if any(key in row for key in ("branch", "role", "pairwise_target", "evidence_state"))
    ]
    label_separation_passed = labels_are_separate(labels, model_inputs_by_id)
    audit = {
        "schema": "adsqa_candidate_d_formal_data_audit_v1",
        "source_count": len(sources),
        "source_question_count": len({row["source_question_id"] for row in sources}),
        "pair_count": len(pairs),
        "model_input_count": len(model_inputs),
        "positive_count": len(pairs),
        "negative_count": len(pairs),
        "unique_source_video_count": len(source_video_ids),
        "stage2_partition_counts": dict(
            sorted(Counter(row["stage2_partition"] for row in sources).items())
        ),
        "required_modality_counts": dict(
            sorted(Counter(row["required_modality"] for row in sources).items())
        ),
        "negative_corruption_counts": dict(
            sorted(Counter(row["negative_corruption_type"] for row in pairs).items())
        ),
        "ocr_eligible_source_count": len(ocr_candidates),
        "ocr_selected_source_count": len(selected_ocr_ids),
        "ocr_cache_video_count": len(ocr_cache),
        "rejected_source_count": len(rejected_sources),
        "rejected_sources": rejected_sources,
        "invalid_ocr_pair_count": len(invalid_ocr_pairs),
        "invalid_ocr_pairs": invalid_ocr_pairs,
        "source_video_overlap": source_video_overlap,
        "forbidden_input_paths": forbidden_input_paths,
        "input_role_markers": input_role_markers,
        "labels_are_separate_from_model_inputs": label_separation_passed,
        "not_human_gold": True,
        "passed": (
            len(sources) == args.target_sources
            and len({row["source_question_id"] for row in sources}) == args.target_sources
            and len(pairs) == args.target_sources * 2
            and len(model_inputs) == args.target_sources * 4
            and len(labels) == len(model_inputs)
            and len(selected_ocr_ids) >= args.minimum_ocr_sources
            and not rejected_sources
            and not invalid_ocr_pairs
            and not any(source_video_overlap.values())
            and not forbidden_input_paths
            and not input_role_markers
            and label_separation_passed
        ),
    }
    write_json(args.output_root / "audit.json", audit)
    write_jsonl(args.output_root / "source_claims.jsonl", sources)
    write_jsonl(args.output_root / "model_inputs.jsonl", model_inputs)
    write_jsonl(args.output_root / "pairs.jsonl", pairs)
    write_jsonl(args.output_root / "labels.jsonl", labels)
    manifest = {
        "schema": "adsqa_candidate_d_formal_data_manifest_v1",
        "seed": args.seed,
        "goal_start_epoch": args.goal_start_epoch,
        "source_claims_input_sha256": sha256_file(args.source_claims),
        "evidence_questions_sha256": sha256_file(args.evidence_questions),
        "holdout_claims_sha256": sha256_file(args.holdout_claims),
        "source_claims_sha256": sha256_file(args.output_root / "source_claims.jsonl"),
        "model_inputs_sha256": sha256_file(args.output_root / "model_inputs.jsonl"),
        "pairs_sha256": sha256_file(args.output_root / "pairs.jsonl"),
        "labels_sha256": sha256_file(args.output_root / "labels.jsonl"),
        "ocr_cache_sha256": sha256_file(args.output_root / "ocr_cache.jsonl"),
        "ocr_coverage_audit_sha256": sha256_file(args.output_root / "ocr_coverage_audit.json"),
        "audit_sha256": sha256_file(args.output_root / "audit.json"),
        "rapidocr_package_dir": str(args.rapidocr_package_dir),
        "not_human_gold": True,
        "audit": audit,
        "started_at_epoch": started_at,
        "ended_at_epoch": int(time.time()),
    }
    write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
