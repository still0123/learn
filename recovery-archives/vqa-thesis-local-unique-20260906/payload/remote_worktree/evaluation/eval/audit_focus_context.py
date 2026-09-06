#!/usr/bin/env python3
"""Audit source-frame preservation and embedded ROI plans for focus-context runs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--raw-run", required=True)
    parser.add_argument("--focus-run", required=True)
    parser.add_argument("--expected-frames", type=int, default=32)
    parser.add_argument("--expected-focus", type=int, default=8)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_ids(path: str | Path) -> list[str]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    values = [str(row["question_id"]) for row in rows]
    if len(values) != len(set(values)):
        raise ValueError("question file contains duplicate IDs")
    return values


def index_evidence(root: str | Path) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for path in Path(root).rglob("evidence.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        question_id = str(payload["question_id"])
        if question_id in indexed:
            raise ValueError(f"duplicate evidence for {question_id}")
        indexed[question_id] = payload
    return indexed


def frame_signature(evidence: dict[str, Any]) -> list[tuple[int, int]]:
    return [
        (int(frame.get("sample_rank", -1)), int(frame.get("frame_index", -1)))
        for frame in evidence.get("selected_frames", [])
    ]


def audit_item(
    raw: dict[str, Any],
    focus: dict[str, Any],
    expected_frames: int,
    expected_focus: int,
) -> list[str]:
    failed = []
    raw_frames = frame_signature(raw)
    focus_frames = frame_signature(focus)
    locals_ = focus.get("selected_local_views", [])
    plan = focus.get("visual_plan", [])
    focus_plan = [row for row in plan if row.get("view_type") == "focus_context"]
    global_plan = [row for row in plan if row.get("view_type") == "global"]

    checks = {
        "raw_frame_count": len(raw_frames) == expected_frames,
        "focus_source_frame_count": len(focus_frames) == expected_frames,
        "source_frames_identical": raw_frames == focus_frames,
        "embedded_roi_count": len(locals_) == expected_focus,
        "embedded_submission_mode": all(
            row.get("submission_mode") == "embedded_focus_context" for row in locals_
        ),
        "visual_plan_count": len(plan) == expected_frames,
        "focus_plan_count": len(focus_plan) == expected_focus,
        "global_plan_count": len(global_plan) == expected_frames - expected_focus,
        "input_image_count": focus.get("input_image_count") == expected_frames,
    }
    local_by_id = {str(row.get("candidate_id")): row for row in locals_}
    plan_by_id = {str(row.get("candidate_id")): row for row in focus_plan}
    checks["unique_embedded_candidate_ids"] = len(local_by_id) == expected_focus
    checks["embedded_plan_ids_match"] = set(local_by_id) == set(plan_by_id)
    checks["embedded_frame_ranks_match"] = all(
        int(local_by_id[key].get("frame_rank", -1)) == int(plan_by_id[key].get("frame_rank", -2))
        for key in set(local_by_id) & set(plan_by_id)
    )
    for name, passed in checks.items():
        if not passed:
            failed.append(name)
    return failed


def main() -> None:
    args = parse_args()
    question_ids = load_ids(args.question_file)
    raw = index_evidence(args.raw_run)
    focus = index_evidence(args.focus_run)
    expected = set(question_ids)
    missing_raw = sorted(expected - set(raw))
    missing_focus = sorted(expected - set(focus))
    violations = []
    distributions = {
        "focus_source_frames": Counter(),
        "embedded_roi_count": Counter(),
        "visual_plan_count": Counter(),
    }
    source_frames_identical_count = 0
    for question_id in question_ids:
        if question_id not in raw or question_id not in focus:
            continue
        distributions["focus_source_frames"][str(len(focus[question_id].get("selected_frames", [])))] += 1
        distributions["embedded_roi_count"][str(len(focus[question_id].get("selected_local_views", [])))] += 1
        distributions["visual_plan_count"][str(len(focus[question_id].get("visual_plan", [])))] += 1
        if frame_signature(raw[question_id]) == frame_signature(focus[question_id]):
            source_frames_identical_count += 1
        failed = audit_item(raw[question_id], focus[question_id], args.expected_frames, args.expected_focus)
        if failed:
            violations.append({"question_id": question_id, "failed": failed})

    payload = {
        "question_file": str(Path(args.question_file).resolve()),
        "raw_run": str(Path(args.raw_run).resolve()),
        "focus_run": str(Path(args.focus_run).resolve()),
        "expected": len(question_ids),
        "missing_raw_count": len(missing_raw),
        "missing_focus_count": len(missing_focus),
        "violation_count": len(violations),
        "source_frames_identical_count": source_frames_identical_count,
        "distributions": {name: dict(values) for name, values in distributions.items()},
        "diagnostic_preview": {
            "missing_raw": missing_raw[:20],
            "missing_focus": missing_focus[:20],
            "violations": violations[:20],
        },
        "valid": not missing_raw and not missing_focus and not violations,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
