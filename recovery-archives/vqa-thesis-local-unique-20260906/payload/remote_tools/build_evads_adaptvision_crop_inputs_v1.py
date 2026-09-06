#!/usr/bin/env python3
"""Freeze policy crops and matched global control inputs."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


BASELINE = "anchor_global10"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen-shards-dir", type=Path, required=True)
    parser.add_argument("--policy-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-questions", type=int, default=100)
    parser.add_argument(
        "--candidate",
        choices=(
            "adaptvision_bbox10",
            "deepeyes_firstzoom10",
            "zoomeye_union10",
            "vlmr3_lastbbox10",
            "hide_layout10",
            "qzoom_roi10",
        ),
        default="adaptvision_bbox10",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_bbox(bbox: list[Any]) -> list[float]:
    normalized = [float(value) for value in bbox]
    if (
        len(normalized) != 4
        or not all(0.0 <= value <= 1.0 for value in normalized)
        or normalized[2] <= normalized[0]
        or normalized[3] <= normalized[1]
    ):
        raise RuntimeError(f"invalid policy bbox: {normalized}")
    return normalized


def self_check() -> None:
    assert validate_bbox([0, 0.1, 0.8, 1]) == [0.0, 0.1, 0.8, 1.0]
    try:
        validate_bbox([0.5, 0.5, 0.4, 0.9])
    except RuntimeError:
        return
    raise AssertionError("invalid bbox was accepted")


def main() -> None:
    self_check()
    args = parse_args()
    variants = (BASELINE, args.candidate)
    if args.output_dir.exists():
        raise RuntimeError("output directory already exists")
    source_rows = []
    source_hashes = {}
    for fold in range(5):
        path = args.screen_shards_dir / f"fold_{fold}.jsonl"
        source_hashes[path.name] = sha256(path)
        source_rows.extend(
            row
            for row in read_jsonl(path)
            if str(row["view_variant"]) == "anchor_global10"
        )
    source = {str(row["question_id"]): row for row in source_rows}
    policy_rows = read_jsonl(args.policy_results)
    policy = {
        (str(row["question_id"]), int(row["anchor_index"])): row
        for row in policy_rows
    }
    if (
        len(source) != args.expected_questions
        or len(policy_rows) != 2 * args.expected_questions
        or len(policy) != 2 * args.expected_questions
        or any(qid not in source for qid, _ in policy)
        or any(not row.get("parse_valid") for row in policy_rows)
    ):
        raise RuntimeError("source screen or policy results changed")

    triggered = {
        qid
        for qid in source
        if any(
            policy[(qid, anchor_index)].get(
                "compact_image_path"
                if args.candidate == "hide_layout10"
                else "roi_image_path"
                if args.candidate == "qzoom_roi10"
                else "bbox_norm"
            )
            for anchor_index in (0, 1)
        )
    }
    frozen = []
    fallback_anchor_count = 0
    crop_areas = []
    layout_anchor_count = 0
    roi_anchor_count = 0
    selected_region_count = 0
    for qid in sorted(triggered):
        for variant in variants:
            row = copy.deepcopy(source[qid])
            row["view_variant"] = variant
            if variant == args.candidate:
                for anchor in row["evidence_anchors"]:
                    anchor_index = int(anchor["anchor_index"])
                    decision = policy[(qid, anchor_index)]
                    bbox = decision.get("bbox_norm")
                    anchor["source_avfunnel_bbox_norm"] = list(
                        anchor["bbox_norm"]
                    )
                    if args.candidate == "qzoom_roi10":
                        roi_value = decision.get("roi_image_path")
                        roi_path = (
                            Path(str(roi_value)) if roi_value else None
                        )
                        roi_sha256 = decision.get("roi_image_sha256")
                        roi_size = decision.get("roi_image_size")
                        if (
                            int(decision.get("source_frame_index", -1))
                            != int(anchor["source_frame_index"])
                            or (
                                roi_path is not None
                                and (
                                    not roi_path.is_file()
                                    or sha256(roi_path) != roi_sha256
                                    or not isinstance(roi_size, list)
                                    or len(roi_size) != 2
                                    or not bbox
                                )
                            )
                            or (roi_path is None and bbox is not None)
                        ):
                            raise RuntimeError(
                                f"invalid Q-Zoom ROI artifact: "
                                f"{qid} anchor {anchor_index}"
                            )
                        anchor.update({
                            "qzoom_roi_image_path": (
                                str(roi_path)
                                if roi_path is not None
                                else None
                            ),
                            "qzoom_roi_image_sha256": roi_sha256,
                            "qzoom_roi_image_size": roi_size,
                            "qzoom_bbox_feature_xyxy": decision.get(
                                "bbox_feature_xyxy"
                            ),
                            "qzoom_bbox_pixel_xyxy": decision.get(
                                "bbox_pixel_xyxy"
                            ),
                            "qzoom_policy_prompt_sha256": str(
                                decision["policy_prompt_sha256"]
                            ),
                        })
                        if roi_path is not None:
                            normalized = validate_bbox(bbox)
                            anchor["bbox_norm"] = normalized
                            anchor["detail_image_path"] = str(roi_path)
                            anchor["detail_image_sha256"] = roi_sha256
                            anchor["detail_image_size"] = roi_size
                            anchor["bbox_source"] = (
                                "QZoom_SD_RPN_official_ROI_v1"
                            )
                            crop_areas.append(
                                (normalized[2] - normalized[0])
                                * (normalized[3] - normalized[1])
                            )
                            roi_anchor_count += 1
                        else:
                            anchor["bbox_source"] = (
                                "QZoom_no_ROI_fallback_AVFunnel_mid_v1"
                            )
                            fallback_anchor_count += 1
                        continue
                    if args.candidate == "hide_layout10":
                        compact_value = decision.get("compact_image_path")
                        compact_path = (
                            Path(str(compact_value))
                            if compact_value
                            else None
                        )
                        compact_sha256 = decision.get(
                            "compact_image_sha256"
                        )
                        compact_size = decision.get("compact_image_size")
                        regions = decision.get("selected_regions_norm")
                        region_count = int(
                            decision.get("selected_region_count", -1)
                        )
                        if (
                            not decision.get("entity_parse_valid")
                            or int(decision.get("source_frame_index", -1))
                            != int(anchor["source_frame_index"])
                            or not isinstance(regions, list)
                            or region_count != len(regions)
                            or (
                                compact_path is not None
                                and (
                                    not compact_path.is_file()
                                    or sha256(compact_path)
                                    != compact_sha256
                                    or region_count <= 0
                                    or not isinstance(compact_size, list)
                                    or len(compact_size) != 2
                                )
                            )
                            or (
                                compact_path is None
                                and region_count != 0
                            )
                        ):
                            raise RuntimeError(
                                f"invalid HiDe layout artifact: "
                                f"{qid} anchor {anchor_index}"
                            )
                        anchor.update({
                            "hide_compact_image_path": (
                                str(compact_path)
                                if compact_path is not None
                                else None
                            ),
                            "hide_compact_image_sha256": compact_sha256,
                            "hide_compact_image_size": compact_size,
                            "hide_selected_regions_norm": regions,
                            "hide_selected_region_count": region_count,
                            "hide_entity_response_sha256": str(
                                decision["entity_response_sha256"]
                            ),
                        })
                        if compact_path is not None:
                            anchor["detail_image_path"] = str(compact_path)
                            anchor["detail_image_sha256"] = compact_sha256
                            anchor["detail_image_size"] = compact_size
                            anchor["bbox_source"] = (
                                "HiDe_layout_preserving_compact_v1"
                            )
                            layout_anchor_count += 1
                            selected_region_count += region_count
                        else:
                            anchor["bbox_source"] = (
                                "HiDe_no_region_fallback_AVFunnel_mid_v1"
                            )
                            fallback_anchor_count += 1
                        continue
                    if args.candidate == "adaptvision_bbox10":
                        anchor["adaptvision_tool_called"] = bool(
                            decision["tool_called"]
                        )
                        anchor["adaptvision_raw_response_sha256"] = str(
                            decision["raw_response_sha256"]
                        )
                    elif args.candidate == "deepeyes_firstzoom10":
                        anchor["deepeyes_zoom_call_count"] = int(
                            decision["zoom_call_count"]
                        )
                        anchor["deepeyes_trace_response_sha256"] = [
                            str(turn["response_sha256"])
                            for turn in decision["trace"]
                        ]
                    elif args.candidate == "zoomeye_union10":
                        anchor["zoomeye_selected_node_count"] = int(
                            decision["selected_node_count"]
                        )
                        anchor["zoomeye_cue_response_sha256"] = (
                            decision["cue_response_sha256"]
                        )
                        anchor["zoomeye_search_trace_sha256"] = (
                            hashlib.sha256(
                                json.dumps(
                                    decision["search_trace"],
                                    ensure_ascii=True,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ).encode("utf-8")
                            ).hexdigest()
                        )
                    elif args.candidate == "vlmr3_lastbbox10":
                        anchor["vlmr3_bbox_call_count"] = int(
                            decision["bbox_call_count"]
                        )
                        anchor["vlmr3_answer_present"] = bool(
                            decision["answer_present"]
                        )
                        anchor["vlmr3_trace_response_sha256"] = [
                            str(turn["response_sha256"])
                            for turn in decision["trace"]
                        ]
                    if bbox:
                        normalized = validate_bbox(bbox)
                        anchor["bbox_norm"] = normalized
                        anchor["bbox_source"] = {
                            "adaptvision_bbox10": (
                                "AdaptVision_continuous_bbox_v1"
                            ),
                            "deepeyes_firstzoom10": (
                                "DeepEyes_last_accepted_zoom_bbox_v1"
                            ),
                            "zoomeye_union10": (
                                "ZoomEye_context_expanded_node_union_v1"
                            ),
                            "vlmr3_lastbbox10": (
                                "VLMR3_last_executed_bbox_v1"
                            ),
                        }[args.candidate]
                        crop_areas.append(
                            (normalized[2] - normalized[0])
                            * (normalized[3] - normalized[1])
                        )
                    else:
                        anchor["bbox_source"] = {
                            "adaptvision_bbox10": (
                                "AdaptVision_no_call_fallback_AVFunnel_mid_v1"
                            ),
                            "deepeyes_firstzoom10": (
                                "DeepEyes_no_call_fallback_AVFunnel_mid_v1"
                            ),
                            "zoomeye_union10": (
                                "ZoomEye_no_selected_node_fallback_AVFunnel_mid_v1"
                            ),
                            "vlmr3_lastbbox10": (
                                "VLMR3_no_call_fallback_AVFunnel_mid_v1"
                            ),
                        }[args.candidate]
                        fallback_anchor_count += 1
            frozen.append(row)
    frozen.sort(
        key=lambda row: (
            int(row["fold"]),
            str(row["question_id"]),
            str(row["view_variant"]),
        )
    )
    counts = Counter(str(row["view_variant"]) for row in frozen)
    expected = len(triggered)
    if counts != Counter({variant: expected for variant in variants}):
        raise RuntimeError("paired trigger rows are incomplete")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    files = {}
    for fold in range(5):
        path = args.output_dir / "shards" / f"fold_{fold}.jsonl"
        rows = [row for row in frozen if int(row["fold"]) == fold]
        write_jsonl(path, rows)
        files[str(path.relative_to(args.output_dir))] = sha256(path)
    trigger_rows = []
    for qid in sorted(triggered):
        trigger_row = {
            "question_id": qid,
            "video_id": str(source[qid]["video_id"]),
            "fold": int(source[qid]["fold"]),
            "reference_answer_used": False,
        }
        if args.candidate == "hide_layout10":
            trigger_row["anchor_compact_image_sha256"] = {
                str(anchor_index): policy[
                    (qid, anchor_index)
                ]["compact_image_sha256"]
                for anchor_index in (0, 1)
            }
            trigger_row["anchor_selected_region_count"] = {
                str(anchor_index): int(
                    policy[(qid, anchor_index)]["selected_region_count"]
                )
                for anchor_index in (0, 1)
            }
        elif args.candidate == "qzoom_roi10":
            trigger_row["anchor_roi_image_sha256"] = {
                str(anchor_index): policy[
                    (qid, anchor_index)
                ]["roi_image_sha256"]
                for anchor_index in (0, 1)
            }
            trigger_row["anchor_bbox_norm"] = {
                str(anchor_index): policy[
                    (qid, anchor_index)
                ]["bbox_norm"]
                for anchor_index in (0, 1)
            }
        else:
            trigger_row["anchor_bbox_norm"] = {
                str(anchor_index): policy[(qid, anchor_index)]["bbox_norm"]
                for anchor_index in (0, 1)
            }
        trigger_rows.append(trigger_row)
    trigger_manifest = args.output_dir / "trigger_manifest.jsonl"
    write_jsonl(trigger_manifest, trigger_rows)
    audit = {
        "schema_version": {
            "adaptvision_bbox10": "evads_adaptvision_crop_inputs_audit_v1",
            "deepeyes_firstzoom10": (
                "evads_deepeyes_firstzoom_crop_inputs_audit_v1"
            ),
            "zoomeye_union10": "evads_zoomeye_union_crop_inputs_audit_v1",
            "vlmr3_lastbbox10": (
                "evads_vlmr3_lastbbox_crop_inputs_audit_v1"
            ),
            "hide_layout10": "evads_hide_layout_inputs_audit_v1",
            "qzoom_roi10": "evads_qzoom_roi_inputs_audit_v1",
        }[args.candidate],
        "passed": True,
        "source_question_count": args.expected_questions,
        "trigger_question_count": len(triggered),
        "trigger_video_count": len({
            str(source[qid]["video_id"]) for qid in triggered
        }),
        "trigger_fold_counts": dict(sorted(Counter(
            int(source[qid]["fold"]) for qid in triggered
        ).items())),
        "valid_bbox_anchor_count": len(crop_areas),
        "layout_anchor_count": layout_anchor_count,
        "roi_anchor_count": roi_anchor_count,
        "selected_region_count_total": selected_region_count,
        "candidate_fallback_anchor_count": fallback_anchor_count,
        "bbox_area_ratio": {
            "mean": statistics.fmean(crop_areas) if crop_areas else None,
            "median": statistics.median(crop_areas) if crop_areas else None,
            "min": min(crop_areas) if crop_areas else None,
            "max": max(crop_areas) if crop_areas else None,
        },
        "variants": list(variants),
        "same_mmr8_a0": True,
        "same_trigger_set": True,
        "same_anchor_times": True,
        "same_ocr_asr": True,
        "views": 10,
        "visual_tokens": 2592,
        "reference_answer_used": False,
        "judge_scores_used": False,
        "source_shards_sha256": source_hashes,
        "policy_results_sha256": sha256(args.policy_results),
        "trigger_manifest_sha256": sha256(trigger_manifest),
        "files_sha256": files,
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
