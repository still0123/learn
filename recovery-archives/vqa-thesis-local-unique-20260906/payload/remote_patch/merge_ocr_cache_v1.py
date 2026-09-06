#!/usr/bin/env python3
"""Merge disjoint answer-free OCR cache shards without changing records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    seen = set()
    for path in args.inputs:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            qid = str(row["question_id"])
            if qid in seen:
                raise RuntimeError(f"duplicate question_id: {qid}")
            seen.add(qid); rows.append(row)
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in sorted(rows, key=lambda x: str(x["question_id"]))), encoding="utf-8")
    print(json.dumps({"count": len(rows), "output": str(args.output), "answer_fields_read": False}))


if __name__ == "__main__":
    main()
