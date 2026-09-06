#!/usr/bin/env python3
"""Audit ResponseCenter68 against frozen AdaptiveScale without outcome data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_FOLD_COUNTS = {0: 818, 1: 818, 2: 818, 3: 817, 4: 817, 5: 817}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    return parser.parse_args()


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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def centers(box: list[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")
    dataset_audit = json.loads(
        (args.dataset_root / "dataset_audit.json").read_text(encoding="utf-8")
    )
    if (
        dataset_audit.get("passed") is not True
        or dataset_audit.get("variant") != "response_center68"
        or float(dataset_audit.get("fixed_side", -1)) != 0.68
    ):
        raise RuntimeError("invalid ResponseCenter68 dataset audit")

    if args.mode == "smoke":
        source_groups = [(None, args.dataset_root / "smoke1.jsonl")]
        output_groups = [(None, args.inference_root)]
        expected_total = 1
    else:
        source_groups = [
            (fold, args.dataset_root / "full4905" / "shards" / f"fold_{fold}.jsonl")
            for fold in range(6)
        ]
        output_groups = [
            (fold, args.inference_root / f"fold_{fold}") for fold in range(6)
        ]
        expected_total = 4905

    source_by_id: dict[str, dict[str, Any]] = {}
    source_fold: dict[str, int | None] = {}
    for fold, path in source_groups:
        rows = load_jsonl(path)
        if args.mode == "full" and len(rows) != EXPECTED_FOLD_COUNTS[int(fold)]:
            raise RuntimeError(f"wrong source count for fold {fold}")
        for row in rows:
            qid = str(row["question_id"])
            if qid in source_by_id:
                raise RuntimeError(f"duplicate source question: {qid}")
            source_by_id[qid] = row
            source_fold[qid] = fold
    if len(source_by_id) != expected_total:
        raise RuntimeError("wrong source total")

    adaptive_trace_by_id: dict[str, dict[str, Any]] = {}
    adaptive_prediction_hash: dict[str, str] = {}
    for prediction_path in sorted(args.adaptive_root.glob("fold_*/*/a2_prediction.json")):
        trace_path = prediction_path.with_name("a2_trace.json")
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        qid = str(prediction["question_id"])
        if qid not in source_by_id:
            continue
        adaptive_trace_by_id[qid] = json.loads(trace_path.read_text(encoding="utf-8"))
        adaptive_prediction_hash[qid] = sha256_text(
            str(prediction["prediction"]).strip()
        )
    if set(adaptive_trace_by_id) != set(source_by_id):
        raise RuntimeError("adaptive comparison outputs do not match source questions")

    failures: list[str] = []
    records: list[dict[str, Any]] = []
    actual_ids: set[str] = set()
    for fold, root in output_groups:
        config_path = root / "run_config.json"
        summary_path = root / "run_summary.json"
        if not config_path.is_file() or not summary_path.is_file():
            failures.append(f"fold{fold}:missing run metadata")
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if (
            config.get("ablation_variant") != "response_center68"
            or config.get("ocr_evidence_in_prompt") is not True
            or config.get("asr_evidence_in_prompt") is not True
            or summary.get("complete") is not True
        ):
            failures.append(f"fold{fold}:invalid run metadata")
        error_path = root / "logs" / "errors.jsonl"
        if error_path.exists() and error_path.stat().st_size:
            failures.append(f"fold{fold}:contains inference errors")

        for prediction_path in sorted(root.glob("*/a2_prediction.json")):
            trace_path = prediction_path.with_name("a2_trace.json")
            if not trace_path.is_file():
                failures.append(f"fold{fold}:missing trace:{prediction_path.parent.name}")
                continue
            prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            qid = str(prediction["question_id"])
            if qid in actual_ids or qid not in source_by_id:
                failures.append(f"fold{fold}:unexpected or duplicate question:{qid}")
                continue
            if source_fold[qid] != fold:
                failures.append(f"fold{fold}:source fold mismatch:{qid}")
            actual_ids.add(qid)
            source = source_by_id[qid]
            adaptive_trace = adaptive_trace_by_id[qid]
            processor = trace.get("processor_trace", {})
            plan = trace.get("extra_view_plan", [])
            adaptive_plan = adaptive_trace.get("extra_view_plan", [])
            if (
                trace.get("crop_ablation_variant") != "response_center68"
                or trace.get("parse_valid") is not True
                or trace.get("ocr_evidence_in_prompt") is not True
                or trace.get("asr_evidence_in_prompt") is not True
                or processor.get("represented_views") != 12
                or processor.get("visual_tokens") != 3104
                or processor.get("secondary_frame_sampling") is not False
                or len(plan) != 4
                or len(adaptive_plan) != 4
                or trace.get("base_source_frame_indices")
                != adaptive_trace.get("base_source_frame_indices")
            ):
                failures.append(f"fold{fold}:protocol mismatch:{qid}")
                continue

            for anchor_index, anchor in enumerate(source["evidence_anchors"]):
                fixed_detail = plan[1 + 2 * anchor_index]
                adaptive_detail = adaptive_plan[1 + 2 * anchor_index]
                fixed = [float(value) for value in anchor["bbox_norm"]]
                adaptive = [
                    float(value) for value in anchor["adaptive_bbox_norm"]
                ]
                adaptive_center = centers(adaptive)
                expected_left = min(
                    max(adaptive_center[0] - 0.68 / 2.0, 0.0), 1.0 - 0.68
                )
                expected_top = min(
                    max(adaptive_center[1] - 0.68 / 2.0, 0.0), 1.0 - 0.68
                )
                expected_fixed = [
                    expected_left,
                    expected_top,
                    expected_left + 0.68,
                    expected_top + 0.68,
                ]
                if (
                    fixed_detail.get("view_type") != "evidence_mid_crop"
                    or fixed_detail.get("bbox_norm") != anchor["bbox_norm"]
                    or adaptive_detail.get("bbox_norm")
                    != anchor["adaptive_bbox_norm"]
                    or fixed_detail.get("source_global_rank32")
                    != adaptive_detail.get("source_global_rank32")
                    or fixed_detail.get("source_frame_index")
                    != adaptive_detail.get("source_frame_index")
                    or abs((fixed[2] - fixed[0]) - 0.68) > 1e-9
                    or abs((fixed[3] - fixed[1]) - 0.68) > 1e-9
                    or max(
                        abs(value - expected)
                        for value, expected in zip(fixed, expected_fixed)
                    ) > 1e-9
                ):
                    failures.append(
                        f"fold{fold}:geometry or evidence alignment mismatch:{qid}:{anchor_index}"
                    )
            records.append({
                "question_id": qid,
                "fold": fold,
                "response_prediction_sha256": sha256_text(
                    str(prediction["prediction"]).strip()
                ),
                "adaptive_prediction_sha256": adaptive_prediction_hash[qid],
                "represented_views": processor.get("represented_views"),
                "visual_tokens": processor.get("visual_tokens"),
                "same_preclipping_response_peak": True,
                "fixed_side": 0.68,
                "boundary_policy": "translate_square_inside_unit_frame",
            })

    if actual_ids != set(source_by_id):
        failures.append("output question IDs do not exactly match source")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = args.output_dir / "protocol_rows_answer_free.jsonl"
    manifest.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "threshold4905_response_center68_protocol_audit_v1",
        "passed": not failures,
        "mode": args.mode,
        "analysis_role": "posthoc_mechanism_attribution",
        "question_count": len(actual_ids),
        "expected_question_count": expected_total,
        "same_trigger_set": True,
        "same_base_frames": True,
        "same_evidence_moments": True,
        "same_preclipping_response_peaks": True,
        "boundary_policy": "translate_square_inside_unit_frame",
        "only_changed": "adaptive_entropy_scale_to_fixed_side_0.68",
        "represented_views": 12,
        "visual_tokens": 3104,
        "secondary_frame_sampling": False,
        "ocr_evidence_in_prompt": True,
        "asr_evidence_in_prompt": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "failures": failures,
        "dataset_audit_sha256": sha256_file(
            args.dataset_root / "dataset_audit.json"
        ),
        "manifest_sha256": sha256_file(manifest),
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if failures:
        raise RuntimeError(f"protocol audit failed: {len(failures)} issue(s)")


if __name__ == "__main__":
    main()
