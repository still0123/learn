#!/usr/bin/env python3
"""Build a deterministic, video-disjoint pilot from an existing balanced set."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-source", required=True)
    parser.add_argument("--groundtruth-source", required=True)
    parser.add_argument("--question-out", required=True)
    parser.add_argument("--groundtruth-out", required=True)
    parser.add_argument("--manifest-out", required=True)
    parser.add_argument("--video-root", required=True)
    parser.add_argument("--asr-file", default="")
    parser.add_argument("--per-type", type=int, default=10)
    parser.add_argument(
        "--require-nonempty-answer",
        action="store_true",
        help="skip rows whose paired ground-truth answer is blank",
    )
    parser.add_argument(
        "--seed-question-file",
        default="",
        help="prefer eligible rows from this existing subset before filling from the source",
    )
    parser.add_argument(
        "--exclude-question-file",
        action="append",
        default=[],
        help="exclude every question and video listed in this subset; may be repeated",
    )
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"expected a list of objects: {path}")
    return data


def primary_type(item: dict[str, Any]) -> str:
    values = item.get("question_type", [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not values:
        raise ValueError(f"missing question_type for {item.get('question_id')}")
    return str(values[0])


def existing_video(video_root: Path, video_id: str) -> Path | None:
    candidates = [
        video_root / f"{video_id}.mp4",
        video_root / video_id,
        video_root / f"{video_id}.webm",
        video_root / f"{video_id}.mov",
    ]
    return next((path for path in candidates if path.exists()), None)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.per_type <= 0:
        raise ValueError("per-type must be positive")

    question_source = Path(args.question_source)
    groundtruth_source = Path(args.groundtruth_source)
    video_root = Path(args.video_root)
    questions = load_records(question_source)
    groundtruth = load_records(groundtruth_source)
    gt_by_id = {str(item["question_id"]): item for item in groundtruth}
    source_index_by_id = {str(item["question_id"]): index for index, item in enumerate(questions)}
    seed_questions = load_records(Path(args.seed_question_file)) if args.seed_question_file else []
    excluded_rows = [
        item
        for file_name in args.exclude_question_file
        for item in load_records(Path(file_name))
    ]
    excluded_question_ids = {str(item.get("question_id", "")) for item in excluded_rows}
    excluded_video_ids = {
        str(item.get("video", item.get("video_id", ""))) for item in excluded_rows
    }

    type_names = sorted({primary_type(item) for item in questions})
    selected: list[dict[str, Any]] = []
    source_indices: list[int] = []
    used_question_ids: set[str] = set()
    used_video_ids: set[str] = set()
    skipped_repeated_videos = Counter()
    skipped_missing_videos = Counter()
    skipped_empty_answers = Counter()
    selected_from_seed = Counter()
    skipped_excluded_questions = Counter()
    skipped_excluded_videos = Counter()

    for type_name in type_names:
        type_count = 0
        seen_candidates: set[str] = set()
        candidates = [(True, item) for item in seed_questions] + [(False, item) for item in questions]
        for from_seed, item in candidates:
            if primary_type(item) != type_name:
                continue
            question_id = str(item.get("question_id", ""))
            if question_id in seen_candidates:
                continue
            seen_candidates.add(question_id)
            source_index = source_index_by_id.get(question_id)
            if source_index is None:
                if from_seed:
                    raise ValueError(f"seed question is absent from source: {question_id}")
                continue
            video_id = str(item.get("video", item.get("video_id", "")))
            if not question_id or not video_id or question_id in used_question_ids:
                continue
            if question_id in excluded_question_ids:
                skipped_excluded_questions[type_name] += 1
                continue
            if video_id in excluded_video_ids:
                skipped_excluded_videos[type_name] += 1
                continue
            if video_id in used_video_ids:
                skipped_repeated_videos[type_name] += 1
                continue
            if existing_video(video_root, video_id) is None:
                skipped_missing_videos[type_name] += 1
                continue
            gt_item = gt_by_id.get(question_id)
            if gt_item is None:
                raise ValueError(f"ground truth missing for {question_id}")
            if args.require_nonempty_answer and not str(gt_item.get("answer", "")).strip():
                skipped_empty_answers[type_name] += 1
                continue
            if str(gt_item.get("video", gt_item.get("video_id", video_id))) != video_id:
                raise ValueError(f"video mismatch between question and ground truth for {question_id}")

            selected.append(item)
            source_indices.append(source_index)
            used_question_ids.add(question_id)
            used_video_ids.add(video_id)
            if from_seed:
                selected_from_seed[type_name] += 1
            type_count += 1
            if type_count == args.per_type:
                break
        if type_count != args.per_type:
            raise RuntimeError(f"only selected {type_count}/{args.per_type} rows for {type_name}")

    selected_gt = [gt_by_id[str(item["question_id"])] for item in selected]
    question_out = Path(args.question_out)
    groundtruth_out = Path(args.groundtruth_out)
    manifest_out = Path(args.manifest_out)
    for path in (question_out, groundtruth_out, manifest_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    question_out.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    groundtruth_out.write_text(json.dumps(selected_gt, ensure_ascii=False, indent=2), encoding="utf-8")

    asr_modes = Counter()
    if args.asr_file and Path(args.asr_file).exists():
        asr_data = json.loads(Path(args.asr_file).read_text(encoding="utf-8"))
        for item in selected:
            video_id = str(item["video"])
            raw = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id))
            if isinstance(raw, dict) and (raw.get("segments") or raw.get("chunks")):
                asr_modes["timestamped"] += 1
            elif isinstance(raw, str) and raw.strip():
                asr_modes["global_text"] += 1
            else:
                asr_modes["missing_or_other"] += 1

    manifest = {
        "selection": (
            "eligible seed rows followed by first source rows per primary type with globally unique, existing videos"
            if seed_questions
            else "first rows in source order per primary type with globally unique, existing videos"
        ),
        "source_seed": 42,
        "per_primary_type": args.per_type,
        "total": len(selected),
        "unique_question_ids": len(used_question_ids),
        "unique_video_ids": len(used_video_ids),
        "question_source": str(question_source),
        "question_source_sha256": file_sha256(question_source),
        "groundtruth_source": str(groundtruth_source),
        "groundtruth_source_sha256": file_sha256(groundtruth_source),
        "question_out": str(question_out),
        "question_out_sha256": file_sha256(question_out),
        "groundtruth_out": str(groundtruth_out),
        "groundtruth_out_sha256": file_sha256(groundtruth_out),
        "primary_type_counts": dict(Counter(primary_type(item) for item in selected)),
        "all_type_membership_counts": dict(
            Counter(str(value) for item in selected for value in item.get("question_type", []))
        ),
        "asr_modes": dict(asr_modes),
        "skipped_repeated_videos": dict(skipped_repeated_videos),
        "skipped_missing_videos": dict(skipped_missing_videos),
        "require_nonempty_answer": args.require_nonempty_answer,
        "skipped_empty_answers": dict(skipped_empty_answers),
        "seed_question_file": args.seed_question_file,
        "selected_from_seed": dict(selected_from_seed),
        "exclude_question_files": args.exclude_question_file,
        "excluded_question_count": len(excluded_question_ids),
        "excluded_video_count": len(excluded_video_ids),
        "skipped_excluded_questions": dict(skipped_excluded_questions),
        "skipped_excluded_videos": dict(skipped_excluded_videos),
        "source_indices": source_indices,
        "question_ids": [str(item["question_id"]) for item in selected],
        "video_ids": [str(item["video"]) for item in selected],
    }
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
