#!/usr/bin/env python3
"""Replace video and ASR evidence with a deterministic same-type derangement."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


EVIDENCE_KEYS = (
    "video_id", "video_path", "selected_frame_indices", "asr_excerpt",
    "asr_segments", "ocr_present", "router_inputs",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    rows = load_jsonl(args.inputs)
    sources: dict[str, dict[str, Any]] = {}
    by_type: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        source = str(row["source_question_id"])
        sources.setdefault(source, row)
        if source not in by_type[str(row["primary_type"])]:
            by_type[str(row["primary_type"])].append(source)
    mapping = {}
    for primary_type, qids in sorted(by_type.items()):
        if len(qids) < 2:
            raise RuntimeError(f"cannot derange {primary_type} with {len(qids)} source questions")
        ordered = sorted(qids, key=lambda value: hashlib.sha256(f"20260716:{value}".encode()).hexdigest())
        mapping.update({qid: ordered[(index + 1) % len(ordered)] for index, qid in enumerate(ordered)})
    output = []
    for row in rows:
        source = str(row["source_question_id"])
        donor_id = mapping[source]
        donor = sources[donor_id]
        changed = dict(row)
        for key in EVIDENCE_KEYS:
            if key in donor:
                changed[key] = donor[key]
            else:
                changed.pop(key, None)
        changed["evidence_control"] = {
            "mode": "same_primary_type_derangement_v23",
            "original_source_question_id": source,
            "donor_source_question_id": donor_id,
            "original_video_id": row.get("video_id"),
            "donor_video_id": donor.get("video_id"),
        }
        if changed.get("video_id") == row.get("video_id"):
            raise RuntimeError(f"derangement retained original video: {source}")
        output.append(changed)
    output_path = args.output_root / "input.jsonl"
    dump_jsonl(output_path, output)
    dump_json(args.output_root / "audit.json", {
        "schema": "adsqa_mismatched_evidence_control_audit_v23",
        "rows": len(output), "source_questions": len(sources),
        "same_question_claims_preserved": all(
            left["question"] == right["question"] and left["claim"] == right["claim"]
            for left, right in zip(rows, output)
        ),
        "all_videos_changed": all(left.get("video_id") != right.get("video_id") for left, right in zip(rows, output)),
        "passed": True,
    })
    print(json.dumps({"rows": len(output), "source_questions": len(sources), "passed": True}))


if __name__ == "__main__":
    main()
