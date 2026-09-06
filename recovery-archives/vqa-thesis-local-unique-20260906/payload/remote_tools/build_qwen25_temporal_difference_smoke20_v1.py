#!/usr/bin/env python3
"""Freeze 20 LOOK_TIME items without reading labels or judge outputs."""

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.source.read_text().splitlines() if line.strip()]
    rows = sorted(rows, key=lambda row: str(row["question_id"]))[:20]
    if len(rows) != 20 or len({row["video_id"] for row in rows}) < 5:
        raise RuntimeError("temporal smoke requires 20 items from at least five videos")
    args.output_root.mkdir(parents=True, exist_ok=True)
    output = args.output_root / "inputs.jsonl"
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    audit = {
        "schema_version": "qwen25_temporal_difference_smoke20_dataset_v1",
        "count": 20,
        "video_count": len({row["video_id"] for row in rows}),
        "selection": "lexicographic_first20_from_frozen_confirm100_LOOK_TIME",
        "judge_scores_read": False,
        "groundtruth_read": False,
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (args.output_root / "dataset_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
