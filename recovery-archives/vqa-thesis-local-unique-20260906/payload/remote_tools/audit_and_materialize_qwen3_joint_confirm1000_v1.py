#!/usr/bin/env python3
"""Audit four frozen Confirm-1000 arms and materialize answer-free candidates."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-marker", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--a0-root", type=Path, required=True)
    parser.add_argument("--a0-pool", type=Path, required=True)
    parser.add_argument("--mmr-root", type=Path, required=True)
    parser.add_argument("--mmr-audit-root", type=Path, required=True)
    parser.add_argument("--trigger-dataset", type=Path, required=True)
    parser.add_argument("--full-inference", type=Path, required=True)
    parser.add_argument("--full-choices", type=Path, required=True)
    parser.add_argument("--control-inference", type=Path, required=True)
    parser.add_argument("--control-choices", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def extract_answer(value: str) -> str:
    text = str(value).strip()
    match = re.search(
        r"\[(?:final\s+)?answer\]\s*:\s*(.+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        answer = match.group(1).strip().splitlines()[0].strip()
        if answer:
            return answer
    cleaned = re.sub(
        r"^\s*(?:final\s+)?answer\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned or text


def load_choice_map(path: Path) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(path)
    result = {str(row["question_id"]): row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError(f"duplicate choice question IDs: {path}")
    return result


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    if (
        args.protocol_marker.read_text(encoding="utf-8").strip()
        != sha256_file(args.protocol)
    ):
        raise RuntimeError("frozen protocol hash mismatch")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if len(questions) != 1000 or len({row["video"] for row in questions}) != 1000:
        raise RuntimeError("prepared Confirm-1000 coverage mismatch")

    a0_pool_rows = load_jsonl(args.a0_pool / "model_inputs_all.jsonl")
    a0_claims = {
        str(row["source_question_id"]): str(row["claim"])
        for row in a0_pool_rows
    }
    full_choices = load_choice_map(
        args.full_choices / "frozen_choices_answer_free.jsonl"
    )
    control_choices = load_choice_map(
        args.control_choices / "frozen_choices_answer_free.jsonl"
    )
    trigger_items = load_jsonl(args.trigger_dataset / "items_answer_free.jsonl")
    trigger_ids = {str(row["question_id"]) for row in trigger_items}
    if not (
        len(a0_claims) == 1000
        and len(trigger_ids) == 100
        and set(full_choices) == set(control_choices) == trigger_ids
    ):
        raise RuntimeError("A0, trigger, or choice coverage mismatch")

    full_protocol_audit = json.loads(
        (args.full_choices / "protocol_audit.json").read_text(encoding="utf-8")
    )
    control_protocol_audit = json.loads(
        (args.control_choices / "protocol_audit.json").read_text(encoding="utf-8")
    )
    trigger_audit = json.loads(
        (args.trigger_dataset / "audit.json").read_text(encoding="utf-8")
    )
    mmr_audits = [
        json.loads(
            (args.mmr_audit_root / f"fold_{fold}.json").read_text(
                encoding="utf-8"
            )
        )
        for fold in range(5)
    ]

    checks: dict[str, bool] = {
        "protocol_frozen": protocol.get("status") == "frozen_before_inference",
        "question_count_1000": len(questions) == 1000,
        "a0_pool_count_1000": len(a0_claims) == 1000,
        "trigger_exactly_100": len(trigger_ids) == 100,
        "trigger_audit_passed": trigger_audit.get("passed") is True,
        "full_choice_audit_passed": full_protocol_audit.get("passed") is True,
        "control_choice_audit_passed": control_protocol_audit.get("passed") is True,
        "mmr_shard_audits_passed": all(
            audit.get("passed") is True for audit in mmr_audits
        ),
    }
    rows = []
    a0_tokens = []
    mmr_tokens = []
    full_tokens = []
    control_tokens = []
    paired_extra_frames_match = True
    output_failures = []
    for question in questions:
        question_id = str(question["question_id"])
        fold = int(question["fold"])
        a0_prediction_path = (
            args.a0_root / f"fold_{fold}" / "base" / question_id / "prediction.json"
        )
        a0_evidence_path = (
            args.a0_root / f"fold_{fold}" / "base" / question_id / "evidence.json"
        )
        mmr_prediction_path = (
            args.mmr_root / f"fold_{fold}" / question_id / "prediction.json"
        )
        mmr_evidence_path = (
            args.mmr_root / f"fold_{fold}" / question_id / "evidence.json"
        )
        if not all(
            path.is_file()
            for path in (
                a0_prediction_path,
                a0_evidence_path,
                mmr_prediction_path,
                mmr_evidence_path,
            )
        ):
            output_failures.append(
                {"question_id": question_id, "kind": "missing_baseline_output"}
            )
            continue
        a0_prediction = json.loads(a0_prediction_path.read_text(encoding="utf-8"))
        a0_evidence = json.loads(a0_evidence_path.read_text(encoding="utf-8"))
        mmr_prediction = json.loads(mmr_prediction_path.read_text(encoding="utf-8"))
        mmr_evidence = json.loads(mmr_evidence_path.read_text(encoding="utf-8"))
        a0_trace = a0_evidence["processor_trace"]
        mmr_trace = mmr_evidence["processor_trace"]
        a0_tokens.append(int(a0_trace["post_merge_visual_token_count"]))
        mmr_tokens.append(int(mmr_trace["post_merge_visual_token_count"]))
        if not (
            int(a0_evidence["input_image_count"]) == 8
            and int(a0_trace["represented_frame_count"]) == 8
            and a0_trace["secondary_frame_sampling_disabled"] is True
            and a0_tokens[-1] == 1024
        ):
            output_failures.append(
                {"question_id": question_id, "kind": "invalid_a0_protocol"}
            )
        if not (
            int(mmr_evidence["input_image_count"]) == 8
            and int(mmr_trace["represented_frame_count"]) == 8
            and mmr_trace["secondary_frame_sampling_disabled"] is True
            and mmr_tokens[-1] == 1024
        ):
            output_failures.append(
                {"question_id": question_id, "kind": "invalid_mmr_protocol"}
            )
        a0_answer = a0_claims[question_id]
        mmr_answer = extract_answer(str(mmr_prediction["prediction"]))
        full_answer = a0_answer
        control_answer = a0_answer
        if question_id in trigger_ids:
            full_choice = full_choices[question_id]
            control_choice = control_choices[question_id]
            full_answer = str(full_choice["a3_prediction"])
            control_answer = str(control_choice["a3_prediction"])
            runtime_fold = int(full_choice["fold"])
            full_trace_path = (
                args.full_inference
                / f"fold_{runtime_fold}"
                / question_id
                / "a2_trace.json"
            )
            control_trace_path = (
                args.control_inference
                / f"fold_{runtime_fold}"
                / question_id
                / "a2_trace.json"
            )
            full_trace = json.loads(full_trace_path.read_text(encoding="utf-8"))
            control_trace = json.loads(
                control_trace_path.read_text(encoding="utf-8")
            )
            full_processor = full_trace["processor_trace"]
            control_processor = control_trace["processor_trace"]
            full_tokens.append(int(full_processor["visual_tokens"]))
            control_tokens.append(int(control_processor["visual_tokens"]))
            if not (
                int(full_processor["represented_views"]) == 12
                and int(control_processor["represented_views"]) == 12
                and full_processor["secondary_frame_sampling"] is False
                and control_processor["secondary_frame_sampling"] is False
                and full_tokens[-1] == control_tokens[-1] == 3104
            ):
                output_failures.append(
                    {
                        "question_id": question_id,
                        "kind": "invalid_or_unmatched_rewrite_budget",
                    }
                )
            full_plan = full_trace["extra_view_plan"]
            control_plan = control_trace["extra_view_plan"]
            source_match = [
                int(item["source_frame_index"]) for item in full_plan
            ] == [
                int(item["source_frame_index"]) for item in control_plan
            ]
            paired_extra_frames_match &= source_match
            if not source_match:
                output_failures.append(
                    {
                        "question_id": question_id,
                        "kind": "control_anchor_frame_mismatch",
                    }
                )
        rows.append(
            {
                "question_id": question_id,
                "video_id": str(question["video"]),
                "primary_type": str(question["primary_type"]),
                "fold": fold,
                "triggered": question_id in trigger_ids,
                "candidates": {
                    "Uniform8": a0_answer,
                    "MMR8": mmr_answer,
                    "ExtraGlobalControl": control_answer,
                    "FullJointMethod": full_answer,
                },
                "groundtruth_included": False,
            }
        )

    checks.update(
        {
            "all_outputs_present": not output_failures and len(rows) == 1000,
            "a0_fixed_1024_tokens": len(a0_tokens) == 1000
            and set(a0_tokens) == {1024},
            "mmr_fixed_1024_tokens": len(mmr_tokens) == 1000
            and set(mmr_tokens) == {1024},
            "full_fixed_3104_tokens": len(full_tokens) == 100
            and set(full_tokens) == {3104},
            "control_fixed_3104_tokens": len(control_tokens) == 100
            and set(control_tokens) == {3104},
            "full_control_anchor_frames_match": paired_extra_frames_match,
            "answer_free_materialization": all(
                row.get("groundtruth_included") is False for row in rows
            ),
        }
    )
    passed = all(checks.values())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    candidates_path = args.output_dir / "candidates_answer_free.jsonl"
    dump_jsonl(candidates_path, rows)
    audit = {
        "schema_version": "adsqa_qwen3_joint_confirm1000_final_protocol_audit_v1",
        "passed": passed,
        "checks": checks,
        "question_count": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "type_counts": dict(Counter(row["primary_type"] for row in rows)),
        "trigger_count": len(trigger_ids),
        "full_switch_count": sum(
            bool(row["a3_switched"]) for row in full_choices.values()
        ),
        "control_switch_count": sum(
            bool(row["a3_switched"]) for row in control_choices.values()
        ),
        "visual_token_ranges": {
            "Uniform8": [min(a0_tokens), max(a0_tokens)] if a0_tokens else [],
            "MMR8": [min(mmr_tokens), max(mmr_tokens)] if mmr_tokens else [],
            "FullJointMethod_triggered": (
                [min(full_tokens), max(full_tokens)] if full_tokens else []
            ),
            "ExtraGlobalControl_triggered": (
                [min(control_tokens), max(control_tokens)]
                if control_tokens
                else []
            ),
        },
        "protocol_sha256": sha256_file(args.protocol),
        "questions_sha256": sha256_file(args.questions),
        "candidates_sha256": sha256_file(candidates_path),
        "output_failures": output_failures,
        "groundtruth_read": False,
        "judge_scores_read": False,
    }
    dump_json(args.output_dir / "protocol_audit.json", audit)
    dump_json(args.output_dir / "failures.json", output_failures)
    if not passed:
        raise RuntimeError("final Confirm-1000 protocol audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
