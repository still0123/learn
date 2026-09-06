#!/usr/bin/env python3
"""Prepare a balanced Smoke10 subset from the frozen FreshQ-500 manifest."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--gate-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def primary_type(row: dict[str, Any]) -> str:
    value = row.get("question_type", [])
    return str(value[0]) if isinstance(value, list) and value else str(value)


def main() -> None:
    args = parse_args()
    question_path = Path(args.questions).resolve()
    gate_path = Path(args.gate_manifest).resolve()
    output_dir = Path(args.output_dir).resolve()
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    gates = {
        str(row["question_id"]): row
        for row in (
            json.loads(line)
            for line in gate_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    selected = []
    counts = Counter()
    for row in questions:
        qtype = primary_type(row)
        if counts[qtype] >= 2:
            continue
        selected.append(row)
        counts[qtype] += 1
    if len(selected) != 10 or any(counts[f"Type_{index}"] != 2 for index in range(1, 6)):
        raise ValueError(f"cannot construct balanced Smoke10: {dict(counts)}")
    selected_ids = {str(row["question_id"]) for row in selected}
    if not selected_ids.issubset(gates):
        raise ValueError("gate manifest misses one or more Smoke10 questions")
    selected_gates = [gates[str(row["question_id"])] for row in selected]
    output_dir.mkdir(parents=True, exist_ok=True)
    question_output = output_dir / "smoke10_question.json"
    gate_output = output_dir / "smoke10_gate_manifest.jsonl"
    question_output.write_text(
        json.dumps(selected, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    gate_output.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in selected_gates),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "fresh_confirm500_smoke10_prepare_audit_v1",
        "passed": len(selected_ids) == 10 and set(counts.values()) == {2},
        "question_count": len(selected_ids),
        "video_count": len({str(row["video"]) for row in selected}),
        "primary_type_counts": dict(sorted(counts.items())),
        "source_questions_sha256": sha256_file(question_path),
        "source_gate_manifest_sha256": sha256_file(gate_path),
        "smoke_questions_sha256": sha256_file(question_output),
        "smoke_gate_manifest_sha256": sha256_file(gate_output),
    }
    (output_dir / "smoke10_prepare_audit.json").write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
