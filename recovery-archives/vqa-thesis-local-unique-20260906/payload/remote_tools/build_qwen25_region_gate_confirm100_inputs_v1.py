#!/usr/bin/env python3
"""Split the frozen Confirm-100 LOOK_REGION arm for two-GPU inference."""

import argparse
import hashlib
import json
from pathlib import Path


FORBIDDEN = {"answer", "reference_answer", "ground_truth", "judge_score", "label"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.source.read_text().splitlines() if line.strip()]
    rows.sort(key=lambda row: str(row["question_id"]))
    if len(rows) != 53 or any(FORBIDDEN & set(row) for row in rows):
        raise RuntimeError("frozen Confirm-100 region population changed")
    args.output_root.mkdir(parents=True, exist_ok=False)
    for index, part in enumerate((rows[:27], rows[27:])):
        (args.output_root / f"shard{index}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in part)
        )
    audit = {
        "schema_version": "qwen25_region_gate_confirm100_inputs_v1",
        "count": 53, "shard_counts": [27, 26],
        "answer_free": True, "judge_scores_read": False,
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
    }
    (args.output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
