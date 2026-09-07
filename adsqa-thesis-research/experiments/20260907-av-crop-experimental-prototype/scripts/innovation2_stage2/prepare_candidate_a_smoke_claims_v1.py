#!/usr/bin/env python3
"""Prepare a deterministic visual/OCR smoke subset for candidate A.

The subset contains only frozen-Qwen records that supplied an in-range visual
anchor and does not replace the 500-source internal training corpus.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260718)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_int(seed: int, value: str) -> int:
    return int(hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()[:16], 16)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def is_valid_visual_anchor(row: dict[str, Any]) -> bool:
    positions = row.get("evidence_anchor_positions", [])
    return (
        row.get("extraction_status") == "qwen_evidence_anchored"
        and row.get("claim_type") in {"visual", "ocr"}
        and isinstance(positions, list)
        and bool(positions)
        and all(isinstance(position, int) and 0 <= position < 32 for position in positions)
        and str(row.get("text", "")).strip()
    )


def main() -> None:
    args = parse_args()
    if args.output_jsonl.exists() or args.audit_json.exists():
        raise RuntimeError("refusing to overwrite candidate A smoke subset")
    rows = read_jsonl(args.input_jsonl)
    valid = [row for row in rows if is_valid_visual_anchor(row)]
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for row in sorted(valid, key=lambda value: stable_int(args.seed, str(value["claim_id"]))):
        key = (str(row["video_id"]), str(row["text"]).strip().casefold())
        deduplicated.setdefault(key, row)
    selected = sorted(
        deduplicated.values(),
        key=lambda value: stable_int(args.seed, str(value["claim_id"])),
    )
    audit = {
        "schema": "adsqa_candidate_a_visual_ocr_smoke_subset_audit_v1",
        "input_count": len(rows),
        "eligible_count": len(valid),
        "selected_count": len(selected),
        "unique_video_count": len({str(row["video_id"]) for row in selected}),
        "claim_type_counts": dict(sorted(Counter(row["claim_type"] for row in selected).items())),
        "source_status_counts": dict(
            sorted(Counter(row["extraction_status"] for row in selected).items())
        ),
        "deduplication_key": "video_id + casefolded_atomic_claim",
        "input_sha256": sha256_file(args.input_jsonl),
        "not_human_gold": True,
        "passed": len(selected) >= 20 and len({str(row["video_id"]) for row in selected}) >= 20,
    }
    write_jsonl(args.output_jsonl, selected)
    write_json(args.audit_json, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
