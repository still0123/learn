#!/usr/bin/env python3
"""Fail closed when candidate-E cannot elect answers without leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-dataset-root", type=Path, required=True)
    parser.add_argument("--pixel-audit", type=Path, required=True)
    parser.add_argument("--candidate-d-failure", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--ledger-jsonl", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_root}")
    manifest = read_json(args.formal_dataset_root / "manifest.json")
    pixel_audit = read_json(args.pixel_audit)
    candidate_d = read_json(args.candidate_d_failure)
    model_inputs = read_jsonl(args.formal_dataset_root / "model_inputs.jsonl")
    forbidden_answer_fields = {
        "answer",
        "candidate_answer",
        "draft_answer",
        "reference_answer",
        "gold_answer",
        "judge_score",
    }
    answer_fields_in_model_inputs = sorted(
        {
            key
            for row in model_inputs
            for key in forbidden_answer_fields
            if key in row
        }
    )
    d_by_modality = candidate_d.get("evidence", {}).get("by_required_modality", {})
    d_ocr = d_by_modality.get("ocr", {})
    ocr_certificate_reliability_passed = (
        d_ocr.get("n", 0) > 0
        and d_ocr.get("strict_correct", 0) / d_ocr["n"] > 0.8
    )
    invariant = {
        "alternative_answer_candidate_available_without_prompt_change": False,
        "candidate_answer_has_independent_answer_correctness_signal": False,
        "cross_modal_certificate_reliable_for_ocr": ocr_certificate_reliability_passed,
        "reference_answer_or_judge_score_in_election_features": bool(answer_fields_in_model_inputs),
        "answer_fields_in_model_inputs": answer_fields_in_model_inputs,
    }
    switch_allowed = (
        invariant["alternative_answer_candidate_available_without_prompt_change"]
        and invariant["candidate_answer_has_independent_answer_correctness_signal"]
        and invariant["cross_modal_certificate_reliable_for_ocr"]
        and not invariant["reference_answer_or_judge_score_in_election_features"]
    )
    audit = {
        "schema": "adsqa_candidate_e_precondition_audit_v1",
        "candidate_id": "candidate_E_conservative_answer_election_v1",
        "formal_data_audit_passed": bool(manifest.get("audit", {}).get("passed")),
        "pixel_audit_passed": bool(pixel_audit.get("passed")),
        "candidate_d_ocr_counterfactual": {
            "n": d_ocr.get("n"),
            "strict_correct": d_ocr.get("strict_correct"),
            "strict_accuracy": (
                d_ocr.get("strict_correct", 0) / d_ocr["n"] if d_ocr.get("n", 0) else None
            ),
        },
        "election_invariant": invariant,
        "switch_allowed": switch_allowed,
        "status": "candidate_failed_precondition" if not switch_allowed else "candidate_ready",
        "failure_types": (
            [
                "no_nonleaking_alternative_answer_candidate",
                "ocr_certificate_not_reliable_for_answer_election",
                "answer_correctness_signal_unavailable_without_labels",
            ]
            if not switch_allowed
            else []
        ),
        "decision": (
            "Do not generate or switch answers. A certificate of ASR/OCR presence is not an "
            "answer-correctness certificate, and the only available OCR-sensitive Qwen signal "
            "failed the controlled counterfactual gate. Using reference answers, judge scores, "
            "or a new answer prompt to create the deciding feature would violate the frozen "
            "protocol and introduce supervision leakage."
        ),
        "next_action": (
            "A-E are exhausted under the frozen protocol. Search literature for an independently "
            "annotated grounding or answer-selection formulation before proposing another mechanism."
        ),
        "input_hashes": {
            "formal_manifest": sha256_file(args.formal_dataset_root / "manifest.json"),
            "formal_model_inputs": sha256_file(args.formal_dataset_root / "model_inputs.jsonl"),
            "pixel_audit": sha256_file(args.pixel_audit),
            "candidate_d_failure": sha256_file(args.candidate_d_failure),
        },
        "not_human_gold": True,
    }
    args.output_root.mkdir(parents=True)
    write_json(args.output_root / "precondition_audit.json", audit)
    markdown = "\n".join(
        [
            "# Candidate E 保守答案选举前置门禁",
            "",
            "- 状态：`candidate_failed_precondition`",
            "- 数据构造与像素审计均通过，但这只能说明 ASR/OCR 证据存在或被删除。",
            f"- Candidate D 的 OCR 严格方向为 `{d_ocr.get('strict_correct')}/{d_ocr.get('n')}`，"
            "不足以作为答案切换证书。",
            "- 正式模型输入没有答案、参考答案或裁判分数；这是正确的防泄漏边界，"
            "也意味着当前没有独立的答案正确性信号。",
            "",
            "## 决策",
            "",
            audit["decision"],
            "",
            "因此不运行伪造的答案选举、不进行 Calibration 或 QA 评测。所有 A-E 候选已结束，"
            "后续仅基于文献提出新的、可独立监督的机制。",
            "",
        ]
    )
    (args.output_root / "precondition_audit.md").write_text(markdown, encoding="utf-8")
    with args.ledger_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp_epoch": int(time.time()),
                    "candidate_id": audit["candidate_id"],
                    "status": audit["status"],
                    "failure_types": audit["failure_types"],
                    "precondition_audit": str(args.output_root / "precondition_audit.json"),
                    "next_action": audit["next_action"],
                    "not_human_gold": True,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not switch_allowed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
