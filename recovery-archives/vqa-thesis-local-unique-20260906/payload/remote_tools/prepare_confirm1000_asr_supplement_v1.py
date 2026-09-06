#!/usr/bin/env python3
"""Prepare an answer-free list of Confirm-1000 videos missing segmented ASR."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def stable_rank(seed: int, video_id: str) -> str:
    return hashlib.sha256(f"{seed}:{video_id}".encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--existing-asr-dir", type=Path, action="append", default=[])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-question-count", type=int, default=1000)
    parser.add_argument("--expected-missing-count", type=int, default=70)
    parser.add_argument("--smoke-count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260728)
    args = parser.parse_args()

    questions = load_json_list(args.questions)
    if len(questions) != args.expected_question_count:
        raise ValueError(
            f"question count mismatch: {len(questions)} != "
            f"{args.expected_question_count}"
        )

    video_ids = []
    seen = set()
    forbidden_keys = {
        "answer",
        "reference_answer",
        "groundtruth",
        "label",
        "meta_info",
        "prediction",
        "score",
    }
    leaked_keys = set()
    for row in questions:
        leaked_keys.update(forbidden_keys.intersection(row))
        video_id = str(row.get("video", row.get("video_id")))
        if not video_id or video_id == "None":
            raise ValueError("question row is missing video/video_id")
        if video_id in seen:
            raise ValueError(f"Confirm-1000 is not unique-video: {video_id}")
        seen.add(video_id)
        video_ids.append(video_id)
    if leaked_keys:
        raise ValueError(f"answer-free question file contains: {sorted(leaked_keys)}")

    coverage: dict[str, int] = {}
    invalid_records = []
    covered = set()
    for directory in args.existing_asr_dir:
        directory_count = 0
        for video_id in video_ids:
            path = directory / f"{video_id}.json"
            if not path.exists():
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if str(record.get("video_id")) != video_id:
                    raise ValueError("video identity mismatch")
                if record.get("status") not in ALLOWED_STATUS:
                    raise ValueError(f"invalid status: {record.get('status')}")
            except Exception as exc:
                invalid_records.append(
                    {
                        "video_id": video_id,
                        "path": str(path.resolve()),
                        "error": str(exc),
                    }
                )
                continue
            covered.add(video_id)
            directory_count += 1
        coverage[str(directory.resolve())] = directory_count

    missing = sorted(
        set(video_ids) - covered,
        key=lambda value: stable_rank(args.seed, value),
    )
    if invalid_records:
        raise ValueError(f"invalid existing ASR records: {invalid_records[:5]}")
    if len(missing) != args.expected_missing_count:
        raise ValueError(
            f"missing count mismatch: {len(missing)} != "
            f"{args.expected_missing_count}"
        )
    if args.smoke_count <= 0 or args.smoke_count > len(missing):
        raise ValueError("invalid smoke count")

    missing_rows = [{"video_id": video_id} for video_id in missing]
    smoke_rows = missing_rows[: args.smoke_count]
    missing_path = args.output_root / "missing_videos_answer_free.json"
    smoke_path = args.output_root / "smoke_videos_answer_free.json"
    dump_json(missing_path, missing_rows)
    dump_json(smoke_path, smoke_rows)

    audit = {
        "schema_version": "adsqa_confirm1000_asr_supplement_selection_v1",
        "passed": True,
        "questions_path": str(args.questions.resolve()),
        "questions_sha256": sha256_file(args.questions),
        "question_count": len(questions),
        "unique_video_count": len(video_ids),
        "existing_asr_coverage_by_dir": coverage,
        "existing_asr_union_coverage": len(covered),
        "missing_count": len(missing),
        "smoke_count": len(smoke_rows),
        "missing_selection_path": str(missing_path.resolve()),
        "missing_selection_sha256": sha256_file(missing_path),
        "smoke_selection_path": str(smoke_path.resolve()),
        "smoke_selection_sha256": sha256_file(smoke_path),
        "selection_fields": ["video_id"],
        "answer_free": True,
        "invalid_existing_records": invalid_records,
    }
    dump_json(args.output_root / "selection_audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
