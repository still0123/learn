#!/usr/bin/env python3
"""Audit paired E-VAds policy crop inference outputs."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-per-variant", type=int, default=500)
    parser.add_argument("--variants", nargs="+", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError("output directory already exists")
    variants = tuple(args.variants)
    if (
        len(variants) < 2
        or len(set(variants)) != len(variants)
        or "anchor_global10" not in variants
    ):
        raise RuntimeError("audit requires unique variants including anchor_global10")
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for fold_dir in sorted(args.inference_root.glob("fold_*")):
        fold = int(fold_dir.name.split("_")[-1])
        for variant in variants:
            for item_dir in sorted((fold_dir / variant).glob("*")):
                prediction_path = item_dir / "a2_prediction.json"
                trace_path = item_dir / "a2_trace.json"
                if not prediction_path.is_file() or not trace_path.is_file():
                    failures.append({
                        "fold": fold,
                        "variant": variant,
                        "question_id": item_dir.name,
                        "reason": "missing_output",
                    })
                    continue
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                processor = trace.get("processor_trace", {})
                checks = {
                    "parse_valid": bool(trace.get("parse_valid")),
                    "variant": str(trace.get("view_variant")) == variant,
                    "views": int(processor.get("represented_views", -1)) == 10,
                    "extra_images": int(processor.get("represented_extra_images", -1)) == 2,
                    "visual_tokens": int(processor.get("visual_tokens", -1)) == 2592,
                    "secondary_sampling": processor.get("secondary_frame_sampling") is False,
                    "extra_plan": len(trace.get("extra_view_plan", [])) == 2,
                }
                plans = trace.get("extra_view_plan", [])
                if variant == "awares_first10":
                    checks["render"] = all(
                        plan.get("view_type") == "awares_first10_896"
                        for plan in plans
                    )
                elif variant == "adaptvision_bbox10":
                    checks["render"] = all(
                        plan.get("view_type") == "adaptvision_bbox10_896"
                        for plan in plans
                    )
                elif variant == "deepeyes_firstzoom10":
                    checks["render"] = all(
                        plan.get("view_type") == "deepeyes_firstzoom10_896"
                        for plan in plans
                    )
                elif variant == "zoomeye_union10":
                    checks["render"] = all(
                        plan.get("view_type") == "zoomeye_union10_896"
                        for plan in plans
                    )
                elif variant == "vlmr3_lastbbox10":
                    checks["render"] = all(
                        plan.get("view_type") == "vlmr3_lastbbox10_896"
                        for plan in plans
                    )
                elif variant == "hide_layout10":
                    checks["render"] = all(
                        plan.get("view_type") == "hide_layout10_896"
                        and (
                            (
                                plan.get("render_mode")
                                == "layout_preserving_compact"
                                and len(str(
                                    plan.get(
                                        "detail_image_sha256",
                                        "",
                                    )
                                )) == 64
                                and int(plan.get(
                                    "selected_region_count",
                                    0,
                                )) > 0
                            )
                            or plan.get("render_mode")
                            == "no_region_fallback_AVFunnel_mid"
                        )
                        for plan in plans
                    )
                elif variant == "qzoom_roi10":
                    checks["render"] = all(
                        plan.get("view_type") == "qzoom_roi10_896"
                        and (
                            (
                                plan.get("render_mode")
                                == "official_qzoom_roi_crop"
                                and len(str(
                                    plan.get(
                                        "detail_image_sha256",
                                        "",
                                    )
                                )) == 64
                                and len(plan.get("bbox_norm", [])) == 4
                            )
                            or plan.get("render_mode")
                            == "no_roi_fallback_AVFunnel_mid"
                        )
                        for plan in plans
                    )
                elif variant == "anchor_global10":
                    checks["render"] = all(
                        plan.get("view_type") == "same_anchor_full_896"
                        for plan in plans
                    )
                else:
                    checks["render"] = False
                if not all(checks.values()):
                    failures.append({
                        "fold": fold,
                        "variant": variant,
                        "question_id": item_dir.name,
                        "reason": "protocol_check_failed",
                        "checks": checks,
                    })
                    continue
                records.append({
                    "question_id": item_dir.name,
                    "variant": variant,
                    "fold": fold,
                    "prediction_path": str(prediction_path.resolve()),
                    "prediction_sha256": sha256(prediction_path),
                    "trace_path": str(trace_path.resolve()),
                    "trace_sha256": sha256(trace_path),
                    "visual_tokens": int(processor["visual_tokens"]),
                    "latency_seconds": float(trace["latency_seconds"]),
                    "base_source_frame_indices": trace[
                        "base_source_frame_indices"
                    ],
                    "anchor_source_frame_indices": [
                        int(plan["source_frame_index"]) for plan in plans
                    ],
                    "detail_image_sha256": [
                        plan.get("detail_image_sha256") for plan in plans
                    ],
                    "prompt_sha256": str(trace.get("prompt_sha256", "")),
                })

    counts = Counter(row["variant"] for row in records)
    qids = {
        variant: {
            str(row["question_id"])
            for row in records
            if row["variant"] == variant
        }
        for variant in variants
    }
    paired = set.intersection(*(qids[variant] for variant in variants))
    for qid in sorted(paired):
        rows = [row for row in records if row["question_id"] == qid]
        for field in (
            "base_source_frame_indices",
            "anchor_source_frame_indices",
            "prompt_sha256",
        ):
            values = {
                json.dumps(row[field], sort_keys=True)
                for row in rows
            }
            if len(values) != 1:
                failures.append({
                    "question_id": qid,
                    "reason": f"paired_{field}_mismatch",
                })
    passed = (
        not failures
        and all(
            counts[variant] == args.expected_per_variant
            for variant in variants
        )
        and all(qids[variant] == paired for variant in variants)
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = args.output_dir / "candidate_manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "evads_qwen3_policy_crop_inference_audit_v2",
        "passed": passed,
        "variants": list(variants),
        "expected_per_variant": args.expected_per_variant,
        "counts": dict(counts),
        "paired_question_count": len(paired),
        "failure_count": len(failures),
        "visual_tokens": 2592,
        "represented_views": 10,
        "latency_seconds": {
            variant: {
                "mean": statistics.fmean(
                    row["latency_seconds"]
                    for row in records
                    if row["variant"] == variant
                ),
                "median": statistics.median(
                    row["latency_seconds"]
                    for row in records
                    if row["variant"] == variant
                ),
            }
            for variant in variants
            if counts[variant]
        },
        "groundtruth_read": False,
        "judge_scores_read": False,
        "candidate_manifest_sha256": sha256(manifest_path),
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not passed:
        raise RuntimeError("paired 10-view inference audit failed")


if __name__ == "__main__":
    main()
