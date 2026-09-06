#!/usr/bin/env python3
"""Materialize answer-only ReAd-R predictions without modifying raw outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--raw-method", required=True)
    parser.add_argument("--normalized-method", required=True)
    parser.add_argument("--minimum-parse-rate", type=float, default=0.98)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def extract_answer(text: str) -> tuple[str, str]:
    patterns = [
        (
            "xml_answer",
            r"<answer>\s*(.*?)\s*</answer>",
        ),
        (
            "bracket_answer",
            r"\[Answer\]\s*:\s*(.+?)(?=\n\s*\[[A-Za-z ]+\]\s*:|\Z)",
        ),
    ]
    for label, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip()
            if answer:
                return answer, label
    stripped = text.strip()
    if stripped and "\n" not in stripped and len(stripped) <= 800:
        return stripped, "single_line_fallback"
    return stripped, "unparsed_raw_fallback"


def main() -> None:
    args = parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise RuntimeError("normalized output root must be empty")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    fold_by_qid = {
        str(row["question_id"]): int(row["fold"]) for row in questions
    }
    qids = set(fold_by_qid)
    raw_predictions: dict[str, Path] = {}
    for path in args.raw_root.rglob("prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row.get("question_id", ""))
        if qid in raw_predictions:
            raise RuntimeError(f"duplicate raw prediction for {qid}")
        raw_predictions[qid] = path
    if set(raw_predictions) != qids:
        raise RuntimeError(
            f"raw/question mismatch: raw={len(raw_predictions)} questions={len(qids)}"
        )

    counts: dict[str, int] = {}
    for qid, prediction_path in raw_predictions.items():
        row = json.loads(prediction_path.read_text(encoding="utf-8"))
        if row.get("method") != args.raw_method:
            raise RuntimeError(f"unexpected raw method for {qid}")
        raw_text = str(row.get("prediction", "")).strip()
        answer, parse_format = extract_answer(raw_text)
        if not answer:
            raise RuntimeError(f"empty normalized answer for {qid}")
        counts[parse_format] = counts.get(parse_format, 0) + 1
        normalized = dict(row)
        normalized["method"] = args.normalized_method
        normalized["prediction"] = answer
        normalized["raw_prediction"] = raw_text
        normalized["answer_normalization"] = parse_format
        destination = (
            args.output_root
            / f"fold_{fold_by_qid[qid]}"
            / qid
            / "prediction.json"
        )
        dump_json(destination, normalized)
        evidence_source = prediction_path.with_name("evidence.json")
        if not evidence_source.is_file():
            raise RuntimeError(f"missing evidence for {qid}")
        evidence_destination = destination.with_name("evidence.json")
        evidence_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(evidence_source, evidence_destination)

    parsed = sum(
        count
        for label, count in counts.items()
        if label != "unparsed_raw_fallback"
    )
    parse_rate = parsed / len(qids)
    audit = {
        "schema_version": "readr_answer_normalization_audit_v1",
        "question_count": len(qids),
        "raw_method": args.raw_method,
        "normalized_method": args.normalized_method,
        "format_counts": counts,
        "parsed_count": parsed,
        "parse_rate": parse_rate,
        "minimum_parse_rate": args.minimum_parse_rate,
        "raw_root": str(args.raw_root.resolve()),
        "raw_question_sha256": sha256_file(args.questions),
        "raw_outputs_preserved": True,
        "passed": parse_rate >= args.minimum_parse_rate,
    }
    dump_json(args.output_root / "normalization_audit.json", audit)
    if not audit["passed"]:
        raise RuntimeError(f"ReAd-R parse rate too low: {parse_rate:.4f}")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
