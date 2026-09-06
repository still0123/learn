#!/usr/bin/env python3
"""Materialize one isolated A0 repair without overwriting frozen predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


FORBIDDEN_FIELDS = {
    "answer",
    "ground_truth",
    "reference_answer",
    "prediction",
    "judge_score",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", required=True, type=Path)
    parser.add_argument("--repair-root", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--expected-question-id", required=True)
    parser.add_argument("--audit", required=True, type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.audit.exists():
        raise RuntimeError("refusing to overwrite repair audit")
    questions = json.loads(args.question_file.read_text(encoding="utf-8"))
    if (
        not isinstance(questions, list)
        or len(questions) != 1
        or not isinstance(questions[0], dict)
        or FORBIDDEN_FIELDS & set(questions[0])
    ):
        raise RuntimeError("repair question file is not one-row answer-free JSON")
    question_id = str(questions[0].get("question_id", ""))
    if question_id != args.expected_question_id:
        raise RuntimeError(f"unexpected repair question ID: {question_id}")

    source = args.repair_root / question_id
    target = args.target_root / question_id
    required = {"prediction.json", "evidence.json"}
    if not source.is_dir() or not required.issubset({path.name for path in source.iterdir()}):
        raise RuntimeError("isolated repair did not produce complete artifacts")
    if target.exists():
        raise RuntimeError("refusing to overwrite an existing A0 question artifact")

    args.target_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    source_hashes = {
        path.name: sha256_file(path)
        for path in sorted(source.iterdir())
        if path.is_file()
    }
    target_hashes = {
        path.name: sha256_file(path)
        for path in sorted(target.iterdir())
        if path.is_file()
    }
    if source_hashes != target_hashes:
        raise RuntimeError("materialized repair hashes do not match isolated source")
    audit = {
        "schema_version": "adsqa_a0_single_repair_materialization_v1",
        "passed": True,
        "question_id": question_id,
        "video_id": str(questions[0]["video"]),
        "question_file": str(args.question_file.resolve()),
        "question_file_sha256": sha256_file(args.question_file),
        "source": str(source.resolve()),
        "target": str(target.resolve()),
        "artifact_sha256": target_hashes,
        "overwrote_existing_artifact": False,
        "answer_or_outcome_fields_used": False,
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
