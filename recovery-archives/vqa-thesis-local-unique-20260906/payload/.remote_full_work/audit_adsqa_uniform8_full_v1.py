#!/usr/bin/env python3
"""Audit frozen Uniform8 Qwen3 inference without reading references."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or len(questions) != args.expected_count:
        raise RuntimeError("question count mismatch")
    failures = []
    records = []
    files = {}
    for row in questions:
        qid = str(row["question_id"])
        fold = int(row["fold"])
        root = args.inference_root / f"fold_{fold}" / "base" / qid
        prediction_path = root / "prediction.json"
        evidence_path = root / "evidence.json"
        if not prediction_path.is_file() or not evidence_path.is_file():
            failures.append(f"{qid}: missing output")
            continue
        prediction = json.loads(
            prediction_path.read_text(encoding="utf-8")
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        trace = evidence.get("processor_trace", {})
        checks = {
            "method": prediction.get("method") == "CleanQwen3_Raw8",
            "views8": int(evidence.get("input_image_count", -1)) == 8,
            "represented8": int(trace.get("represented_frame_count", -1)) == 8,
            "tokens1024": (
                int(trace.get("post_merge_visual_token_count", -1)) == 1024
            ),
            "secondary_sampling_off": (
                trace.get("secondary_frame_sampling_disabled") is True
            ),
            "budget_respected": (
                trace.get("visual_token_budget_respected") is True
            ),
        }
        if not all(checks.values()):
            failures.append(f"{qid}: {checks}")
        records.append(
            {
                "question_id": qid,
                "fold": fold,
                "visual_tokens": int(
                    trace.get("post_merge_visual_token_count", -1)
                ),
                "checks": checks,
            }
        )
        files[str(prediction_path)] = sha256_file(prediction_path)
        files[str(evidence_path)] = sha256_file(evidence_path)
    audit = {
        "schema_version": "adsqa_qwen3_uniform8_full_audit_v1",
        "passed": (
            not failures
            and len(records) == args.expected_count
            and len({row["question_id"] for row in records})
            == args.expected_count
        ),
        "question_count": len(records),
        "fold_counts": dict(
            Counter(str(row["fold"]) for row in records)
        ),
        "visual_token_counts": dict(
            Counter(str(row["visual_tokens"]) for row in records)
        ),
        "failures": failures,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "questions_sha256": sha256_file(args.questions),
        "records": records,
        "files_sha256": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in audit.items()
                if key not in {"records", "files_sha256"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
