#!/usr/bin/env python3
"""Build a symlink-only video overlay for the frozen Confirm-3000 set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--original-root", required=True)
    parser.add_argument("--repair-root", required=True)
    parser.add_argument("--frames-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--manifest", required=True)
    return parser.parse_args()


def source_candidates(video_id: str, root: Path) -> list[Path]:
    return [
        root / f"{video_id}.mp4",
        root / video_id,
        root / f"{video_id}.webm",
        root / f"{video_id}.mov",
    ]


def main() -> None:
    args = parse_args()
    question_path = Path(args.question_file).resolve()
    original_root = Path(args.original_root).resolve()
    repair_root = Path(args.repair_root).resolve()
    frames_root = Path(args.frames_root).resolve()
    output_root = Path(args.output_root).resolve()
    manifest_path = Path(args.manifest).resolve()
    rows = json.loads(question_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise SystemExit("question file must contain a non-empty JSON list")
    video_ids = sorted({str(row["video"]) for row in rows})
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for video_id in video_ids:
        repair_candidates = source_candidates(video_id, repair_root)
        original_candidates = source_candidates(video_id, original_root)
        frame_candidate = frames_root / video_id
        source = next((path for path in repair_candidates if path.is_file()), None)
        source_kind = "repair_cache"
        if source is None:
            source = next((path for path in original_candidates if path.exists()), None)
            source_kind = "original"
        if source is None and frame_candidate.is_dir():
            source = frame_candidate
            source_kind = "frame_fallback"
        if source is None:
            raise SystemExit(f"no source for video {video_id}")

        target = output_root / (f"{video_id}.mp4" if source.is_file() else video_id)
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or Path(os.readlink(target)).resolve() != source.resolve():
                raise SystemExit(f"overlay target conflicts with existing path: {target}")
        else:
            target.symlink_to(source)

        record: dict[str, Any] = {
            "video_id": video_id,
            "overlay_path": str(target),
            "source_path": str(source),
            "source_kind": source_kind,
            "repair_cache_used": source_kind == "repair_cache",
        }
        if source.is_file():
            record["source_size_bytes"] = source.stat().st_size
            record["source_sha256"] = sha256_file(source)
        else:
            files = sorted(path for path in source.iterdir() if path.is_file())
            record["source_file_count"] = len(files)
            record["source_file_names_sha256"] = hashlib.sha256(
                "\n".join(path.name for path in files).encode("utf-8")
            ).hexdigest()
        records.append(record)

    manifest = {
        "schema_version": "confirm3000_video_overlay_v1",
        "question_file": str(question_path),
        "question_count": len(rows),
        "unique_video_count": len(video_ids),
        "overlay_root": str(output_root),
        "records": records,
        "repair_cache_video_count": sum(row["repair_cache_used"] for row in records),
        "answer_content_used_for_overlay": False,
        "groundtruth_read": False,
        "not_human_gold": True,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "question_count": len(rows),
        "unique_video_count": len(video_ids),
        "repair_cache_video_count": manifest["repair_cache_video_count"],
        "manifest": str(manifest_path),
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
