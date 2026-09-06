#!/usr/bin/env python3
"""Audit answer-free same-budget ablation smoke outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VARIANTS = ("extra_global", "no_ocr", "no_asr")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError("audit output already exists")
    dataset_audit = json.loads((args.dataset_root / "dataset_audit.json").read_text(encoding="utf-8"))
    if dataset_audit.get("passed") is not True or dataset_audit.get("analysis_role") != "posthoc_mechanism_attribution":
        raise RuntimeError("dataset audit is not valid")
    records = []
    failures = []
    for variant in VARIANTS:
        expected_ids = set()
        for fold in range(6):
            shard = args.dataset_root / "smoke24" / variant / "shards" / f"fold_{fold}.jsonl"
            rows = load_jsonl(shard)
            if len(rows) != 4:
                failures.append(f"{variant}:fold{fold}:expected four input rows")
            expected_ids.update(str(row["question_id"]) for row in rows)
        actual_ids = set()
        variant_root = args.inference_root / variant
        config_path = variant_root / "run_config.json"
        summary_path = variant_root / "run_summary.json"
        if not config_path.is_file() or not summary_path.is_file():
            failures.append(f"{variant}:missing run metadata")
            continue
        config = json.loads(config_path.read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if config.get("ablation_variant") != variant or summary.get("complete") is not True:
            failures.append(f"{variant}:invalid config or incomplete run")
        errors = variant_root / "logs" / "errors.jsonl"
        if errors.exists() and errors.stat().st_size:
            failures.append(f"{variant}:contains errors")
        for prediction_path in sorted(variant_root.glob("*/a2_prediction.json")):
            trace_path = prediction_path.with_name("a2_trace.json")
            if not trace_path.is_file():
                failures.append(f"{variant}:missing trace for {prediction_path.parent.name}")
                continue
            prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            qid = str(prediction["question_id"])
            actual_ids.add(qid)
            processor_trace = trace.get("processor_trace", {})
            plan = trace.get("extra_view_plan", [])
            if (
                trace.get("crop_ablation_variant") != variant
                or trace.get("parse_valid") is not True
                or processor_trace.get("represented_views") != 12
                or processor_trace.get("visual_tokens") != 3104
                or processor_trace.get("secondary_frame_sampling") is not False
                or len(plan) != 4
                or bool(trace.get("ocr_evidence_in_prompt")) != (variant != "no_ocr")
                or bool(trace.get("asr_evidence_in_prompt")) != (variant != "no_asr")
            ):
                failures.append(f"{variant}:protocol mismatch for {qid}")
            detail_types = [str(item.get("view_type")) for item in plan[1::2]]
            required = "evidence_full_highres" if variant == "extra_global" else "evidence_mid_crop"
            if detail_types != [required, required]:
                failures.append(f"{variant}:view type mismatch for {qid}")
            records.append({
                "variant": variant,
                "question_id": qid,
                "prediction_sha256": hashlib.sha256(str(prediction["prediction"]).strip().encode("utf-8")).hexdigest(),
                "visual_tokens": processor_trace.get("visual_tokens"),
                "represented_views": processor_trace.get("represented_views"),
            })
        if actual_ids != expected_ids or len(actual_ids) != 24:
            failures.append(f"{variant}:output ids do not match smoke inputs")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = args.output_dir / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    audit = {
        "schema_version": "threshold4905_samebudget_ablation_smoke_audit_v1",
        "passed": not failures,
        "analysis_role": "posthoc_mechanism_attribution",
        "variants": list(VARIANTS),
        "records": len(records),
        "groundtruth_read": False,
        "judge_scores_read": False,
        "deepseek_calls_made": 0,
        "failures": failures,
        "dataset_audit_sha256": sha256_file(args.dataset_root / "dataset_audit.json"),
        "manifest_sha256": sha256_file(manifest),
    }
    (args.output_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
