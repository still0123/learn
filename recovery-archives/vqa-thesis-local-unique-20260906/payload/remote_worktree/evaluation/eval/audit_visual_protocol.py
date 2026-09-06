#!/usr/bin/env python3
"""Audit AdsQA run coverage and frozen visual-input protocol fields."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--run", nargs=2, action="append", metavar=("METHOD", "ROOT"), required=True)
    parser.add_argument("--expected-frames", type=int, default=32)
    parser.add_argument("--expected-tokens", type=int, default=11664)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_expected(path: str | Path) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("question file must be a JSON list")
    return [str(row["question_id"]) for row in payload]


def processor_trace(evidence: dict[str, Any]) -> dict[str, Any]:
    trace = evidence.get("processor_trace")
    if isinstance(trace, dict):
        return trace
    trace = (evidence.get("generation") or {}).get("processor_trace")
    return trace if isinstance(trace, dict) else {}


def audit_run(
    method: str,
    root: str | Path,
    expected_ids: list[str],
    expected_frames: int,
    expected_tokens: int,
) -> dict[str, Any]:
    root_path = Path(root)
    evidence_by_id: dict[str, Path] = {}
    duplicate_ids: list[str] = []
    parse_errors: list[dict[str, str]] = []
    for path in root_path.rglob("evidence.json"):
        try:
            question_id = str(json.loads(path.read_text(encoding="utf-8"))["question_id"])
        except (OSError, KeyError, json.JSONDecodeError) as error:
            parse_errors.append({"path": str(path), "error": repr(error)})
            continue
        if question_id in evidence_by_id:
            duplicate_ids.append(question_id)
        evidence_by_id[question_id] = path

    expected_set = set(expected_ids)
    prediction_ids = {path.parent.name for path in root_path.rglob("prediction.json")}
    violations = []
    distributions: dict[str, Counter[str]] = {
        "input_image_count": Counter(),
        "represented_frame_count": Counter(),
        "submitted_frame_count": Counter(),
        "post_merge_visual_token_count": Counter(),
        "secondary_frame_sampling_disabled": Counter(),
    }
    for question_id, path in evidence_by_id.items():
        evidence = json.loads(path.read_text(encoding="utf-8"))
        trace = processor_trace(evidence)
        values = {
            "input_image_count": evidence.get("input_image_count"),
            "represented_frame_count": trace.get("represented_frame_count"),
            "submitted_frame_count": trace.get("submitted_frame_count"),
            "post_merge_visual_token_count": trace.get("post_merge_visual_token_count"),
            "secondary_frame_sampling_disabled": trace.get("secondary_frame_sampling_disabled"),
        }
        for key, value in values.items():
            distributions[key][str(value)] += 1
        checks = {
            "input_image_count": values["input_image_count"] == expected_frames,
            "represented_frame_count": values["represented_frame_count"] == expected_frames,
            "submitted_frame_count": values["submitted_frame_count"] == expected_frames,
            "post_merge_visual_token_count": (
                values["post_merge_visual_token_count"] == expected_tokens
            ),
            "secondary_frame_sampling_disabled": (
                values["secondary_frame_sampling_disabled"] is True
            ),
            "all_submitted_frames_represented": (
                trace.get("all_submitted_frames_represented") is True
            ),
            "visual_token_budget_respected": trace.get("visual_token_budget_respected") is True,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            violations.append({"question_id": question_id, "failed": failed, "values": values})

    missing_evidence = sorted(expected_set - set(evidence_by_id))
    extra_evidence = sorted(set(evidence_by_id) - expected_set)
    missing_predictions = sorted(expected_set - prediction_ids)
    valid = not any(
        (
            missing_evidence,
            extra_evidence,
            missing_predictions,
            duplicate_ids,
            parse_errors,
            violations,
        )
    )
    return {
        "method": method,
        "root": str(root_path.resolve()),
        "expected": len(expected_ids),
        "evidence_count": len(evidence_by_id),
        "prediction_count": len(prediction_ids & expected_set),
        "missing_evidence_count": len(missing_evidence),
        "missing_prediction_count": len(missing_predictions),
        "extra_evidence_count": len(extra_evidence),
        "duplicate_count": len(duplicate_ids),
        "parse_error_count": len(parse_errors),
        "protocol_violation_count": len(violations),
        "distributions": {key: dict(value) for key, value in distributions.items()},
        "diagnostic_preview": {
            "missing_evidence": missing_evidence[:20],
            "missing_predictions": missing_predictions[:20],
            "extra_evidence": extra_evidence[:20],
            "duplicate_ids": duplicate_ids[:20],
            "parse_errors": parse_errors[:20],
            "violations": violations[:20],
        },
        "valid": valid,
    }


def main() -> None:
    args = parse_args()
    expected_ids = load_expected(args.question_file)
    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("question file contains duplicate question_id values")
    runs = [
        audit_run(method, root, expected_ids, args.expected_frames, args.expected_tokens)
        for method, root in args.run
    ]
    payload = {
        "question_file": str(Path(args.question_file).resolve()),
        "expected": len(expected_ids),
        "expected_frames": args.expected_frames,
        "expected_tokens": args.expected_tokens,
        "runs": runs,
        "all_valid": all(run["valid"] for run in runs),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
