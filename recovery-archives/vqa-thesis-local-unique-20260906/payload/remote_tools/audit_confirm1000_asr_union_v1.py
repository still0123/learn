#!/usr/bin/env python3
"""Audit complete segmented-ASR coverage for frozen Confirm-1000 videos."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ALLOWED_STATUS = {
    "success",
    "no_speech",
    "no_audio",
    "transcription_failed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected JSON list: {path}")
    return value


def load_index(index_dir: Path) -> dict[str, dict[str, Any]]:
    records = {}
    for path in sorted(index_dir.glob("index_shard*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            records[str(record["video_id"])] = record
    return records


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def validate_record(
    path: Path,
    video_id: str,
    duration: float,
) -> tuple[str, int, int]:
    record = json.loads(path.read_text(encoding="utf-8"))
    status = str(record.get("status"))
    if str(record.get("video_id")) != video_id:
        raise ValueError("video identity mismatch")
    if status not in ALLOWED_STATUS:
        raise ValueError(f"invalid status: {status}")

    segments = record.get("segments", [])
    previous_start = -1.0
    word_count = 0
    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("non-finite segment timestamp")
        if start < -0.05 or end < start or end > duration + 1.5:
            raise ValueError("segment timestamp outside video")
        if start < previous_start:
            raise ValueError("segments are not time ordered")
        previous_start = start
        if not str(segment.get("text", "")).strip() and not segment.get("words"):
            raise ValueError("empty segment")
        for word in segment.get("words", []):
            word_start = float(word["start"])
            word_end = float(word["end"])
            if word_start < start - 1.0 or word_end > end + 1.0:
                raise ValueError("word timestamp outside segment")
            if word_end < word_start or not str(word.get("word", "")).strip():
                raise ValueError("invalid word timestamp or text")
            word_count += 1

    if status == "success" and (not record.get("text") or not segments):
        raise ValueError("success record lacks text or segments")
    if status in {"no_audio", "no_speech"} and record.get("text") is not None:
        raise ValueError(f"{status} record must not contain text")
    if status == "transcription_failed" and not record.get("error"):
        raise ValueError("failed record lacks explicit error")
    return status, len(segments), word_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--asr-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=1000)
    args = parser.parse_args()

    questions = load_json_list(args.questions)
    video_ids = [str(row.get("video", row.get("video_id"))) for row in questions]
    failures = []
    if len(video_ids) != args.expected_count:
        failures.append(
            {
                "kind": "question_count_mismatch",
                "actual": len(video_ids),
                "expected": args.expected_count,
            }
        )
    if len(set(video_ids)) != len(video_ids):
        failures.append({"kind": "duplicate_video_ids"})

    index = load_index(args.index_dir)
    source_counts = Counter()
    status_counts = Counter()
    inventory = []
    segment_count = 0
    word_count = 0
    for video_id in video_ids:
        paths = [
            directory / f"{video_id}.json"
            for directory in args.asr_dir
            if (directory / f"{video_id}.json").exists()
        ]
        if not paths:
            failures.append({"video_id": video_id, "kind": "missing_record"})
            continue
        if len(paths) > 1:
            failures.append(
                {
                    "video_id": video_id,
                    "kind": "duplicate_records",
                    "paths": [str(path.resolve()) for path in paths],
                }
            )
            continue
        if video_id not in index:
            failures.append({"video_id": video_id, "kind": "missing_video_index"})
            continue
        path = paths[0]
        try:
            status, segments, words = validate_record(
                path,
                video_id,
                float(index[video_id]["duration_sec"]),
            )
        except Exception as exc:
            failures.append(
                {
                    "video_id": video_id,
                    "kind": "invalid_record",
                    "path": str(path.resolve()),
                    "error": str(exc),
                }
            )
            continue
        source_counts[str(path.parent.resolve())] += 1
        status_counts[status] += 1
        segment_count += segments
        word_count += words
        inventory.append(
            {
                "video_id": video_id,
                "status": status,
                "path": str(path.resolve()),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    aggregate = hashlib.sha256()
    for item in sorted(inventory, key=lambda value: value["video_id"]):
        aggregate.update(
            f"{item['video_id']}\t{item['sha256']}\n".encode("utf-8")
        )
    passed = not failures and len(inventory) == args.expected_count
    result = {
        "schema_version": "adsqa_confirm1000_segmented_asr_union_audit_v1",
        "passed": passed,
        "expected_count": args.expected_count,
        "record_count": len(inventory),
        "source_counts": dict(source_counts),
        "status_counts": dict(status_counts),
        "segment_count": segment_count,
        "word_count": word_count,
        "aggregate_sha256": aggregate.hexdigest(),
        "questions_path": str(args.questions.resolve()),
        "questions_sha256": sha256_file(args.questions),
        "asr_dirs": [str(path.resolve()) for path in args.asr_dir],
        "failures": failures,
        "inventory": inventory,
    }
    dump_json(args.output_json, result)
    dump_json(
        args.output_json.parent / "union_failures.json",
        failures,
    )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "inventory"},
            ensure_ascii=False,
            indent=2,
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
