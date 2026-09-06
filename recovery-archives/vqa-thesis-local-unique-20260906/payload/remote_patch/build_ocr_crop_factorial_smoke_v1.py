#!/usr/bin/env python3
"""Build an answer-free, OCR-relevant, video-distinct smoke set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN = {"answer", "answers", "ground_truth", "reference_answer", "meta_info", "label", "judge_score"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def order_key(row: dict[str, Any]) -> str:
    value = f"ocr-crop-factorial-smoke-v1:{row['question_id']}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--exclude-video-id", action="append", default=[])
    parser.add_argument("--exclude-dataset", type=Path, action="append", default=[])
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.source.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        leaked = FORBIDDEN & set(row)
        if leaked:
            raise RuntimeError(f"forbidden fields in source: {sorted(leaked)}")

    excluded_videos = {str(value) for value in args.exclude_video_id}
    for path in args.exclude_dataset:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                excluded_videos.add(str(json.loads(line)["video_id"]))
    eligible = [
        row
        for row in rows
        if any(int(item.get("question_overlap", 0)) > 0 for item in row.get("ocr_evidence", []))
        and str(row["video_id"]) not in excluded_videos
    ]
    selected: list[dict[str, Any]] = []
    used_videos: set[str] = set()
    for row in sorted(eligible, key=order_key):
        video_id = str(row["video_id"])
        if video_id in used_videos:
            continue
        selected.append(row)
        used_videos.add(video_id)
        if len(selected) == args.n:
            break
    if len(selected) != args.n:
        raise RuntimeError(f"only selected {len(selected)} of {args.n}")

    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "ocr_crop_factorial_smoke_dataset_v1",
        "source_count": len(rows),
        "ocr_relevant_count": len(eligible),
        "selected_count": len(selected),
        "selected_video_count": len(used_videos),
        "selection_rule": "question_overlap_gt_0_then_sha256_one_question_per_video",
        "excluded_decode_unstable_video_ids": sorted(excluded_videos),
        "labels_read": False,
        "source_sha256": sha256_file(args.source),
        "output_sha256": sha256_file(args.output),
    }
    args.output.with_name("dataset_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
