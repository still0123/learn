#!/usr/bin/env python3
"""Build the fixed RealClaim985 + HardNeg180 joint replay dataset."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--realclaim", type=Path, required=True)
    p.add_argument("--hardneg", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    inputs = load(args.realclaim / "inputs.jsonl") + load(args.hardneg / "inputs.jsonl")
    labels = load(args.realclaim / "labels.jsonl") + load(args.hardneg / "labels.jsonl")
    input_ids = [row["question_id"] for row in inputs]
    label_ids = [row["question_id"] for row in labels]
    label_counts = Counter(row["label_name"] for row in labels)
    audit = {
        "schema": "adsqa_realclaim_hardneg_replay_audit_v1",
        "rows": len(inputs), "labels": len(labels),
        "unique_input_ids": len(set(input_ids)), "unique_label_ids": len(set(label_ids)),
        "id_alignment": set(input_ids) == set(label_ids),
        "label_counts": dict(label_counts),
        "unique_videos": len({row["video_id"] for row in inputs}),
        "input_supervision_leakage": any("binary_label" in row or "label_name" in row for row in inputs),
        "not_human_gold": True,
        "passed": len(inputs) == 1165 and len(set(input_ids)) == 1165 and set(input_ids) == set(label_ids),
    }
    write(args.output / "inputs.jsonl", inputs)
    write(args.output / "labels.jsonl", labels)
    (args.output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output / "manifest.json").write_text(json.dumps({
        "inputs_sha256": sha(args.output / "inputs.jsonl"),
        "labels_sha256": sha(args.output / "labels.jsonl"), "audit": audit,
    }, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
