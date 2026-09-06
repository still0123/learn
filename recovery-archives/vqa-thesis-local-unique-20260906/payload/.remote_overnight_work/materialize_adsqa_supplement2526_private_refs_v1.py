#!/usr/bin/env python3
"""Build private judge references for the frozen AdsQA supplement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


EXPECTED_QUESTIONS = 2526


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--private-answers", type=Path, required=True)
    parser.add_argument("--raw-groundtruth", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise RuntimeError(f"expected JSON list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def main() -> None:
    args = parse_args()
    if args.output.exists() or args.audit.exists():
        raise RuntimeError("refusing to overwrite private references")

    questions = load_records(args.questions)
    answers = load_records(args.private_answers)
    raw = load_records(args.raw_groundtruth)
    question_by_id = {str(row["question_id"]): row for row in questions}
    answer_by_id = {str(row["question_id"]): row for row in answers}
    raw_by_id = {str(row["question_id"]): row for row in raw}
    if (
        len(question_by_id) != EXPECTED_QUESTIONS
        or len(answer_by_id) != EXPECTED_QUESTIONS
        or set(question_by_id) != set(answer_by_id)
        or not set(question_by_id).issubset(raw_by_id)
    ):
        raise RuntimeError("private reference pools do not align")

    rows = []
    for qid in sorted(question_by_id):
        question = question_by_id[qid]
        answer = answer_by_id[qid]
        source = raw_by_id[qid]
        reference = str(answer.get("answer", "")).strip()
        if not reference:
            raise RuntimeError(f"empty private answer: {qid}")
        if str(question["question"]).strip() != str(source["question"]).strip():
            raise RuntimeError(f"question text mismatch: {qid}")
        if str(question["video"]) != str(answer["video"]):
            raise RuntimeError(f"video mismatch: {qid}")
        raw_reference = str(
            source.get("answer")
            or source.get("gt_answer")
            or source.get("answers")
            or ""
        ).strip()
        if raw_reference != reference:
            raise RuntimeError(f"reference answer mismatch: {qid}")
        rows.append(
            {
                "question_id": qid,
                "video": str(question["video"]),
                "question": str(question["question"]),
                "question_type": question.get("question_type", ["unknown"]),
                "meta_info": source.get("meta_info", ""),
                "answer": reference,
            }
        )

    write_jsonl(args.output, rows)
    audit = {
        "schema_version": "adsqa_supplement2526_private_refs_audit_v1",
        "passed": len(rows) == EXPECTED_QUESTIONS,
        "question_count": len(rows),
        "question_ids_aligned": True,
        "questions_match_raw_source": True,
        "answers_match_raw_source_fallback": True,
        "private_reference_mode": True,
        "questions_sha256": sha256_file(args.questions),
        "private_answers_sha256": sha256_file(args.private_answers),
        "raw_groundtruth_sha256": sha256_file(args.raw_groundtruth),
        "output_sha256": sha256_file(args.output),
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.audit, 0o600)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
