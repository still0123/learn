#!/usr/bin/env python3
"""Prepare answer-free per-fold active subsets for the formal AV run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN_FIELDS = {"answer", "ground_truth", "reference_answer", "judge_score", "prediction"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-manifest", required=True)
    parser.add_argument("--split-root", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    gate_path = Path(args.gate_manifest).resolve()
    split_root = Path(args.split_root).resolve()
    output_root = Path(args.output_root).resolve()
    gates = {
        str(row["question_id"]): row
        for row in (json.loads(line) for line in gate_path.read_text(encoding="utf-8").splitlines() if line.strip())
    }
    if len(gates) != 500:
        raise ValueError("gate manifest must contain 500 unique questions")

    fold_rows: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    seen_videos: set[str] = set()
    for fold in range(5):
        source = split_root / f"fold_{fold}" / "validation_questions_v1.json"
        questions = json.loads(source.read_text(encoding="utf-8"))
        if len(questions) != 100:
            raise ValueError(f"fold {fold} must contain 100 validation questions")
        for question in questions:
            if FORBIDDEN_FIELDS & set(question):
                raise ValueError(f"fold {fold} contains answer-side fields")
            question_id = str(question["question_id"])
            if question_id in seen_questions:
                raise ValueError(f"duplicate OOF question: {question_id}")
            if int(gates[question_id]["fold"]) != fold:
                raise ValueError(f"gate/split fold mismatch for {question_id}")
            seen_questions.add(question_id)
            seen_videos.add(str(question["video"]))
        active = [
            question
            for question in questions
            if bool(gates[str(question["question_id"])]["gate_decision"]["modality_active"])
        ]
        destination = output_root / f"fold_{fold}" / "active_questions_v1.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(active, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        fold_rows.append(
            {
                "fold": fold,
                "validation_count": len(questions),
                "active_count": len(active),
                "source_sha256": sha256_file(source),
                "active_questions_sha256": sha256_file(destination),
                "active_question_ids": [str(question["question_id"]) for question in active],
            }
        )

    audit = {
        "schema_version": "qwen25_modality_active_formal_subsets_audit_v1",
        "passed": len(seen_questions) == 500 and sum(row["active_count"] for row in fold_rows) > 0,
        "oof_question_count": len(seen_questions),
        "oof_video_count": len(seen_videos),
        "active_question_count": sum(row["active_count"] for row in fold_rows),
        "gate_manifest_sha256": sha256_file(gate_path),
        "answer_side_fields_present": False,
        "folds": fold_rows,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "subsets_audit_v1.json").write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
