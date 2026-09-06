#!/usr/bin/env python3
"""Audit selected-frame AdsQA inference without reading labels or judge outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--inference-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--expected-visual-tokens", type=int, required=True)
    parser.add_argument("--visual-token-budget", type=int, default=4096)
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    args = parse_args()
    all_questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if args.num_shards <= 0 or not 0 <= args.shard_id < args.num_shards:
        raise RuntimeError("invalid shard configuration")
    questions = [
        row
        for index, row in enumerate(all_questions)
        if index % args.num_shards == args.shard_id
    ]
    if len(questions) != args.expected_count:
        raise RuntimeError(
            f"shard contains {len(questions)} questions, expected {args.expected_count}"
        )

    selections = {
        str(row["question_id"]): row for row in load_jsonl(args.selection_manifest)
    }
    qids = [str(row["question_id"]) for row in questions]
    checks = {
        "expected_question_count": len(qids) == args.expected_count,
        "unique_question_ids": len(set(qids)) == len(qids),
        "selection_covers_questions": all(qid in selections for qid in qids),
        "answer_free_selection": all(
            row.get("answer_or_outcome_fields_used") is False
            for row in selections.values()
        ),
    }

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for qid in qids:
        prediction_path = args.inference_dir / qid / "prediction.json"
        evidence_path = args.inference_dir / qid / "evidence.json"
        if not prediction_path.exists() or not evidence_path.exists():
            missing.append(qid)
            continue
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        trace = evidence["processor_trace"]
        selected = [int(value) for value in selections[qid]["selected_frame_indices"]]
        submitted = [int(item["source_frame_index"]) for item in evidence["visual_plan"]]
        rows.append(
            {
                "question_id": qid,
                "prediction_nonempty": bool(str(prediction.get("prediction", "")).strip()),
                "selected_indices_match": submitted == selected,
                "input_image_count": int(evidence["input_image_count"]),
                "represented_frame_count": int(trace["represented_frame_count"]),
                "submitted_frame_count": int(trace["submitted_frame_count"]),
                "visual_token_count": int(trace["post_merge_visual_token_count"]),
                "visual_token_budget": int(trace["post_merge_visual_token_budget"]),
                "visual_token_budget_respected": trace["visual_token_budget_respected"] is True,
                "secondary_frame_sampling_disabled": (
                    trace["secondary_frame_sampling_disabled"] is True
                ),
                "all_submitted_frames_represented": (
                    trace["all_submitted_frames_represented"] is True
                ),
            }
        )

    checks.update(
        {
            "all_outputs_present": not missing and len(rows) == args.expected_count,
            "all_predictions_nonempty": all(row["prediction_nonempty"] for row in rows),
            "all_indices_match_manifest": all(
                row["selected_indices_match"] for row in rows
            ),
            "exactly_eight_views": all(
                row["input_image_count"]
                == row["represented_frame_count"]
                == row["submitted_frame_count"]
                == 8
                for row in rows
            ),
            "fixed_expected_visual_tokens": all(
                row["visual_token_count"] == args.expected_visual_tokens
                for row in rows
            ),
            "all_within_visual_token_budget": all(
                row["visual_token_budget"] == args.visual_token_budget
                and row["visual_token_budget_respected"]
                for row in rows
            ),
            "secondary_sampling_disabled": all(
                row["secondary_frame_sampling_disabled"] for row in rows
            ),
            "all_frames_represented": all(
                row["all_submitted_frames_represented"] for row in rows
            ),
        }
    )
    audit = {
        "schema_version": "adsqa_selected8_inference_protocol_audit_v2",
        "passed": all(checks.values()),
        "checks": checks,
        "expected_count": args.expected_count,
        "expected_visual_tokens": args.expected_visual_tokens,
        "visual_token_budget": args.visual_token_budget,
        "shard_id": args.shard_id,
        "num_shards": args.num_shards,
        "completed_count": len(rows),
        "missing_question_ids": missing,
        "visual_token_range": (
            [
                min(row["visual_token_count"] for row in rows),
                max(row["visual_token_count"] for row in rows),
            ]
            if rows
            else []
        ),
        "question_file_sha256": sha256_file(args.questions),
        "selection_manifest_sha256": sha256_file(args.selection_manifest),
        "run_config_sha256": sha256_file(args.inference_dir / "run_config.json"),
        "groundtruth_read": False,
        "judge_outputs_read": False,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in audit.items() if key != "rows"}, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
