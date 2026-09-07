#!/usr/bin/env python3
"""Freeze a failed counterfactual candidate without overwriting prior evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--run-summary", type=Path, required=True)
    parser.add_argument("--pair-results", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--failure-json", type=Path, required=True)
    parser.add_argument("--failure-markdown", type=Path, required=True)
    parser.add_argument("--ledger-jsonl", type=Path, required=True)
    parser.add_argument("--failure-types", nargs="+", required=True)
    parser.add_argument("--next-mechanism", required=True)
    parser.add_argument("--attribution", default="")
    parser.add_argument("--execution-note", default="")
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
    if args.failure_json.exists() or args.failure_markdown.exists():
        raise RuntimeError("refusing to overwrite a frozen failure attribution")
    summary = read_json(args.run_summary)
    protocol = read_json(args.protocol_audit)
    pairs = read_jsonl(args.pair_results)
    by_modality: dict[str, dict[str, int]] = {}
    by_operation: dict[str, dict[str, int]] = {}
    for field, output in (("required_modality", by_modality), ("negative_corruption_type", by_operation)):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for pair in pairs:
            grouped.setdefault(str(pair.get(field, "unknown")), []).append(pair)
        for key, values in grouped.items():
            output[key] = {
                "n": len(values),
                "strict_correct": sum(bool(value["strict_pairwise_correct"]) for value in values),
                "ties": sum(
                    float(value["positive_score"]) == float(value["negative_score"])
                    for value in values
                ),
                "positive_lower": sum(
                    float(value["positive_score"]) < float(value["negative_score"])
                    for value in values
                ),
            }

    evidence = {
        "pair_count": len(pairs),
        "pairwise_correct_count": summary.get("pairwise_correct_count"),
        "pairwise_accuracy": summary.get("pairwise_accuracy"),
        "protocol_passed": protocol.get("passed"),
        "protocol_failure_count": summary.get("protocol_failure_count"),
        "by_required_modality": by_modality,
        "by_negative_operation": by_operation,
        "run_summary_sha256": sha256_file(args.run_summary),
        "pair_results_sha256": sha256_file(args.pair_results),
        "protocol_audit_sha256": sha256_file(args.protocol_audit),
        "model_config_sha256": summary.get("model_config_sha256"),
        "dataset_manifest_sha256": summary.get("dataset_manifest_sha256"),
        "prompt_sha256": summary.get("prompt_sha256"),
        "visual_protocol": {
            "view_count": summary.get("visual_view_budget"),
            "post_merge_visual_tokens": summary.get("expected_post_merge_visual_tokens"),
            "secondary_frame_sampling_disabled": summary.get("secondary_frame_sampling_disabled"),
        },
    }
    attribution_text = args.attribution or (
        "The modality-aware prompt prevented ASR leakage for visual/OCR claims, but the "
        "generic four-to-eight-frame intervention left the decisive visual fact visible in "
        "other frames from the same video. The frozen verifier therefore assigned SUPPORT "
        "to both branches."
    )
    attribution = {
        "schema": "adsqa_innovation2_failure_attribution_v2",
        "candidate_id": args.candidate_id,
        "status": "candidate_failed",
        "failure_types": args.failure_types,
        "evidence": evidence,
        "attribution": attribution_text,
        "single_next_mechanism": args.next_mechanism,
        "execution_note": args.execution_note,
        "not_human_gold": True,
    }
    write_json(args.failure_json, attribution)
    markdown = "\n".join(
        [
            f"# {args.candidate_id} 失败归因",
            "",
            "- 状态：`candidate_failed`",
            f"- Smoke：`{evidence['pairwise_correct_count']}/{evidence['pair_count']}`，"
            f"严格方向准确率 `{evidence['pairwise_accuracy']:.4f}`。",
            f"- 视觉协议：`{evidence['protocol_passed']}`；"
            f"{evidence['visual_protocol']['view_count']} 个视图、"
            f"{evidence['visual_protocol']['post_merge_visual_tokens']} Token、"
            "二次采样关闭。",
            f"- 失败类型：{', '.join(args.failure_types)}。",
            "",
            "## 归因",
            "",
            attribution["attribution"],
            "",
            "## 下一步",
            "",
            args.next_mechanism,
            "",
            "该记录只描述内部非人工金标准的探索性反事实数据，不能作为正式 QA 提升结论。",
            "",
        ]
    )
    args.failure_markdown.write_text(markdown, encoding="utf-8")
    ledger_row = {
        "timestamp_epoch": int(time.time()),
        "candidate_id": args.candidate_id,
        "status": "candidate_failed",
        "failure_types": args.failure_types,
        "failure_attribution_json": str(args.failure_json),
        "failure_attribution_markdown": str(args.failure_markdown),
        "frozen_artifacts": {
            "run_summary": str(args.run_summary),
            "pair_results": str(args.pair_results),
            "protocol_audit": str(args.protocol_audit),
        },
        "next_action": args.next_mechanism,
        "not_human_gold": True,
    }
    with args.ledger_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(ledger_row, ensure_ascii=False) + "\n")
    print(json.dumps(attribution, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
