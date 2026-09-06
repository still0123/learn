#!/usr/bin/env python3
"""Audit safe fallback and adopted revisions in minimal-edit Smoke-50."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_METHOD = "CleanQwen25_AdsQA_EvidenceMinimalEdit12_A2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    dataset_audit = json.loads(
        (args.dataset_dir / "audit.json").read_text(encoding="utf-8")
    )
    if dataset_audit.get("passed") is not True:
        raise RuntimeError("dataset audit did not pass")
    selected = {
        str(json.loads(line)["question_id"])
        for line in (args.dataset_dir / "items_answer_free.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    if len(selected) != 50:
        raise RuntimeError("dataset does not contain 50 unique questions")

    manifest: list[dict[str, Any]] = []
    violations: list[dict[str, str]] = []
    decision_counts: Counter[str] = Counter()
    parse_valid_count = 0
    changed_count = 0
    fallback_count = 0
    unsafe_changed_count = 0
    contract_reason_counts: Counter[str] = Counter()
    for fold in range(5):
        fold_root = args.inference_root / f"fold_{fold}"
        summary_path = fold_root / "run_summary.json"
        if not summary_path.is_file():
            violations.append({
                "scope": f"fold_{fold}",
                "reason": "missing_run_summary",
            })
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("complete") is not True:
            violations.append({
                "scope": f"fold_{fold}",
                "reason": "inference_summary_incomplete",
            })
        for key in ("groundtruth_read", "judge_scores_read", "external_knowledge_used"):
            if summary.get(key) is not False:
                violations.append({
                    "scope": f"fold_{fold}",
                    "reason": f"invalid_{key}",
                })
        if int(summary.get("a2_views", -1)) != 12:
            violations.append({
                "scope": f"fold_{fold}",
                "reason": "a2_views_not_12",
            })
        for prediction_path in sorted(fold_root.glob("*/a2_prediction.json")):
            qid = prediction_path.parent.name
            trace_path = prediction_path.parent / "a2_trace.json"
            if not trace_path.is_file():
                violations.append({
                    "scope": qid,
                    "reason": "missing_trace",
                })
                continue
            prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            processor = trace.get("processor_trace", {})
            contract_audit = trace.get("contract_audit", {})
            contract_reason_counts[str(contract_audit.get("reason", "unknown"))] += 1
            decision = str(trace.get("decision", "UNKNOWN"))
            decision_counts[decision] += 1
            parse_valid = bool(trace.get("parse_valid"))
            parse_valid_count += parse_valid
            changed = bool(trace.get("answer_changed_from_a0"))
            changed_count += changed
            fallback = bool(trace.get("fallback_to_a0"))
            fallback_count += fallback
            reasons: list[str] = []
            if changed and not parse_valid:
                unsafe_changed_count += 1
                reasons.append("unsafe_changed_output")
            if qid not in selected:
                reasons.append("question_not_selected")
            if str(prediction.get("method")) != EXPECTED_METHOD:
                reasons.append("method_mismatch")
            if int(processor.get("represented_views", -1)) != 12:
                reasons.append("represented_views_not_12")
            if int(processor.get("represented_video_frames", -1)) != 8:
                reasons.append("represented_video_frames_not_8")
            if int(processor.get("represented_extra_images", -1)) != 4:
                reasons.append("represented_extra_images_not_4")
            if int(processor.get("visual_tokens", 999999)) > 4096:
                reasons.append("visual_token_budget_exceeded")
            if processor.get("secondary_frame_sampling") is not False:
                reasons.append("secondary_frame_sampling_not_disabled")
            if len(trace.get("base_source_frame_indices", [])) != 8:
                reasons.append("base_frame_count_not_8")
            if len(trace.get("extra_view_plan", [])) != 4:
                reasons.append("extra_view_plan_count_not_4")
            if trace.get("ocr_evidence_in_prompt") is not True:
                reasons.append("ocr_not_in_prompt")
            if trace.get("asr_evidence_in_prompt") is not True:
                reasons.append("asr_not_in_prompt")
            if decision not in {"KEEP", "REVISE", "PARSE_FALLBACK"}:
                reasons.append("invalid_decision")
            if decision == "REVISE" and parse_valid and not trace.get(
                "cited_evidence_ids"
            ):
                reasons.append("valid_revise_without_citation")
            for reason in reasons:
                violations.append({"scope": qid, "reason": reason})
            manifest.append({
                "question_id": qid,
                "fold": fold,
                "method": str(prediction.get("method")),
                "prediction_sha256": sha256_file(prediction_path),
                "trace_sha256": sha256_file(trace_path),
                "decision": decision,
                "parse_valid": parse_valid,
                "fallback_to_a0": fallback,
                "answer_changed_from_a0": changed,
                "cited_evidence_ids": trace.get("cited_evidence_ids", []),
                "represented_views": processor.get("represented_views"),
                "visual_tokens": processor.get("visual_tokens"),
                "latency_seconds": trace.get("latency_seconds"),
            })

    manifest.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    coverage = {str(row["question_id"]) for row in manifest}
    protocol_passed = (
        len(manifest) == 50
        and coverage == selected
        and not violations
    )
    quality_gate_passed = (
        changed_count >= 5
        and unsafe_changed_count == 0
        and fallback_count + parse_valid_count == 50
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "manifest.jsonl", manifest)
    audit = {
        "schema_version": "qwen25_evidence_minimal_edit_smoke50_protocol_v2",
        "question_count": len(manifest),
        "video_count": dataset_audit["video_count"],
        "fold_counts": {
            str(fold): sum(int(row["fold"]) == fold for row in manifest)
            for fold in range(5)
        },
        "decision_counts": dict(decision_counts),
        "contract_reason_counts": dict(contract_reason_counts),
        "parse_valid_count": parse_valid_count,
        "fallback_count": fallback_count,
        "answer_changed_from_a0_count": changed_count,
        "unsafe_changed_output_count": unsafe_changed_count,
        "protocol_violations": violations,
        "protocol_passed": protocol_passed,
        "quality_gate": {
            "criterion": (
                "at_least_5_valid_evidence_cited_revisions_and_"
                "all_invalid_outputs_fallback_to_a0"
            ),
            "passed": quality_gate_passed,
        },
        "groundtruth_read": False,
        "judge_scores_read": False,
        "external_knowledge_used": False,
        "manifest_sha256": sha256_file(args.output_dir / "manifest.jsonl"),
        "passed": protocol_passed and quality_gate_passed,
    }
    write_json(args.output_dir / "audit.json", audit)
    if not audit["passed"]:
        raise RuntimeError(json.dumps(audit, ensure_ascii=False))
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
