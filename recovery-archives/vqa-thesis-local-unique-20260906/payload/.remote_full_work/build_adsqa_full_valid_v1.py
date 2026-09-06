#!/usr/bin/env python3
"""Freeze the complete AdsQA test subset with non-empty references."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "meta_info",
    "reference_answer",
    "golden_answer",
    "label",
    "prediction",
    "score",
    "judge_output",
}
ALLOWED_ASR_STATUS = {
    "success",
    "no_speech",
    "no_audio",
    "transcription_failed",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--clip-root", type=Path, required=True)
    parser.add_argument("--ocr-root", type=Path, required=True)
    parser.add_argument("--asr-root", type=Path, action="append", required=True)
    parser.add_argument("--history-file", type=Path, action="append", default=[])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026072804)
    return parser.parse_args()


def load_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected JSON list: {path}")
    return value


def canonicalize(
    rows: list[dict[str, Any]], label: str
) -> tuple[dict[str, dict[str, Any]], int]:
    result: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for row in rows:
        qid = str(row["question_id"])
        if qid not in result:
            result[qid] = row
            continue
        if json.dumps(result[qid], ensure_ascii=False, sort_keys=True) != json.dumps(
            row, ensure_ascii=False, sort_keys=True
        ):
            raise RuntimeError(f"conflicting duplicate {label}: {qid}")
        duplicates += 1
    return result, duplicates


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_rank(seed: int, *parts: str) -> str:
    value = ":".join((str(seed),) + parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def dump_json(path: Path, value: Any, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    if mode is not None:
        os.chmod(path, mode)


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def video_id(row: dict[str, Any]) -> str:
    value = row.get("video", row.get("video_id"))
    if value is None:
        raise RuntimeError("row lacks video/video_id")
    return str(value)


def main() -> None:
    args = parse_args()
    if args.folds != 5:
        raise RuntimeError("the frozen full-set protocol requires five folds")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise RuntimeError("refusing to overwrite non-empty output")

    raw_questions = load_list(args.questions)
    raw_groundtruth = load_list(args.groundtruth)
    questions, duplicate_questions = canonicalize(raw_questions, "question")
    groundtruth, duplicate_groundtruth = canonicalize(
        raw_groundtruth, "groundtruth"
    )
    if (
        len(raw_questions) != 7859
        or len(raw_groundtruth) != 7859
        or len(questions) != 7846
        or len(groundtruth) != 7846
        or set(questions) != set(groundtruth)
    ):
        raise RuntimeError("unexpected AdsQA test source")

    valid_ids = {
        qid
        for qid, row in groundtruth.items()
        if str(row.get("answer") or "").strip()
    }
    if len(valid_ids) != 5320:
        raise RuntimeError(f"valid reference count changed: {len(valid_ids)}")

    historical_videos: set[str] = set()
    historical_question_ids: set[str] = set()
    history_sources = []
    for path in args.history_file:
        rows = load_list(path)
        historical_question_ids.update(str(row["question_id"]) for row in rows)
        historical_videos.update(video_id(row) for row in rows)
        history_sources.append(
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
                "rows": len(rows),
                "videos": len({video_id(row) for row in rows}),
            }
        )

    rows_by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    private_by_id: dict[str, dict[str, Any]] = {}
    asr_sources: dict[str, Path] = {}
    cache_inventory = []
    for qid in valid_ids:
        question = questions[qid]
        reference = groundtruth[qid]
        video = video_id(question)
        if video != video_id(reference):
            raise RuntimeError(f"question/reference video mismatch: {qid}")
        clean = {
            "question_id": qid,
            "video": video,
            "question": str(question["question"]),
            "question_type": [
                str(value) for value in question.get("question_type", [])
            ],
        }
        if not clean["question_type"] or FORBIDDEN & set(clean):
            raise RuntimeError(f"invalid answer-free question: {qid}")
        rows_by_video[video].append(clean)
        private_by_id[qid] = reference

    videos = set(rows_by_video)
    if len(videos) != 1521:
        raise RuntimeError(f"valid video count changed: {len(videos)}")
    for video in sorted(videos):
        video_path = args.video_root / f"{video}.mp4"
        clip_path = args.clip_root / f"{video}.npz"
        ocr_path = args.ocr_root / f"{video}.json"
        matches = [
            root / f"{video}.json"
            for root in args.asr_root
            if (root / f"{video}.json").is_file()
        ]
        if not all(path.is_file() for path in (video_path, clip_path, ocr_path)):
            raise RuntimeError(f"missing visual asset for {video}")
        if len(matches) != 1:
            raise RuntimeError(
                f"expected exactly one segmented ASR record for {video}, got {len(matches)}"
            )
        asr = json.loads(matches[0].read_text(encoding="utf-8"))
        if (
            str(asr.get("video_id")) != video
            or str(asr.get("status")) not in ALLOWED_ASR_STATUS
        ):
            raise RuntimeError(f"invalid segmented ASR record: {matches[0]}")
        asr_sources[video] = matches[0]
        cache_inventory.append(
            {
                "video_id": video,
                "video_path": str(video_path.resolve()),
                "clip_path": str(clip_path.resolve()),
                "ocr_path": str(ocr_path.resolve()),
                "asr_path": str(matches[0].resolve()),
                "asr_status": str(asr["status"]),
            }
        )

    ordered_videos = sorted(
        videos,
        key=lambda value: (
            -len(rows_by_video[value]),
            stable_rank(args.seed, "video", value),
        ),
    )
    fold_videos: dict[int, list[str]] = defaultdict(list)
    fold_question_counts = Counter()
    for video in ordered_videos:
        fold = min(
            range(args.folds),
            key=lambda index: (
                fold_question_counts[index],
                len(fold_videos[index]),
                stable_rank(args.seed, "fold", str(index), video),
            ),
        )
        fold_videos[fold].append(video)
        fold_question_counts[fold] += len(rows_by_video[video])

    answer_free = []
    private = []
    overlap_rows = []
    for fold in range(args.folds):
        fold_rows = []
        for video in sorted(fold_videos[fold]):
            fold_rows.extend(
                sorted(
                    rows_by_video[video],
                    key=lambda row: stable_rank(
                        args.seed, "question", str(row["question_id"])
                    ),
                )
            )
        for row in fold_rows:
            output = dict(row)
            output["fold"] = fold
            output["source_split"] = "adsqa_full_valid5320_frozen_v1"
            answer_free.append(output)
            private.append(private_by_id[str(row["question_id"])])
            overlap_rows.append(
                {
                    "question_id": str(row["question_id"]),
                    "video_id": str(row["video"]),
                    "fold": fold,
                    "historical_question_overlap": (
                        str(row["question_id"]) in historical_question_ids
                    ),
                    "historical_video_overlap": (
                        str(row["video"]) in historical_videos
                    ),
                }
            )

    output = args.output_root
    private_root = output / "private_references"
    os.makedirs(private_root, mode=0o700, exist_ok=True)
    dump_json(output / "questions_answer_free.json", answer_free)
    dump_json(private_root / "groundtruth.json", private, mode=0o600)
    dump_jsonl(output / "history_overlap_private_ids.jsonl", overlap_rows)
    dump_jsonl(output / "cache_inventory_answer_free.jsonl", cache_inventory)
    for fold in range(args.folds):
        rows = [row for row in answer_free if int(row["fold"]) == fold]
        dump_json(output / "shards" / f"fold_{fold}.json", rows)
        dump_json(output / "smoke_shards" / f"fold_{fold}.json", rows[:2])

    union_root = output / "asr_union_records"
    union_root.mkdir(parents=True, exist_ok=False)
    combined = {}
    status_counts = Counter()
    for video, source in sorted(asr_sources.items()):
        os.symlink(source.resolve(), union_root / f"{video}.json")
        row = json.loads(source.read_text(encoding="utf-8"))
        status = str(row["status"])
        status_counts[status] += 1
        combined[video] = {
            "transcript": str(row.get("text") or ""),
            "status": status,
        }
    dump_json(output / "asr_combined_answer_free.json", combined)

    fold_counts = Counter(int(row["fold"]) for row in answer_free)
    fold_video_counts = {
        str(fold): len(fold_videos[fold]) for fold in range(args.folds)
    }
    audit = {
        "schema_version": "adsqa_full_valid5320_dataset_audit_v1",
        "passed": True,
        "raw_question_rows": len(raw_questions),
        "canonical_question_count": len(questions),
        "duplicate_question_rows_removed": duplicate_questions,
        "duplicate_groundtruth_rows_removed": duplicate_groundtruth,
        "empty_reference_unique_questions_excluded": len(questions) - len(valid_ids),
        "question_count": len(answer_free),
        "video_count": len(videos),
        "fold_question_counts": {
            str(key): value for key, value in sorted(fold_counts.items())
        },
        "fold_video_counts": fold_video_counts,
        "asr_status_counts": dict(status_counts),
        "video_coverage": len(videos),
        "clip_coverage": len(videos),
        "ocr_coverage": len(videos),
        "segmented_asr_coverage": len(videos),
        "historical_question_overlap_count": sum(
            bool(row["historical_question_overlap"]) for row in overlap_rows
        ),
        "historical_video_overlap_question_count": sum(
            bool(row["historical_video_overlap"]) for row in overlap_rows
        ),
        "history_sources": history_sources,
        "answer_free": True,
        "groundtruth_private": True,
        "questions_sha256": sha256_file(output / "questions_answer_free.json"),
        "references_sha256": sha256_file(private_root / "groundtruth.json"),
        "asr_combined_sha256": sha256_file(
            output / "asr_combined_answer_free.json"
        ),
    }
    dump_json(output / "audit.json", audit)
    manifest = {
        "schema_version": "adsqa_full_valid5320_manifest_v1",
        "dataset_audit_sha256": sha256_file(output / "audit.json"),
        "source_questions": str(args.questions.resolve()),
        "source_questions_sha256": sha256_file(args.questions),
        "source_groundtruth": str(args.groundtruth.resolve()),
        "source_groundtruth_sha256": sha256_file(args.groundtruth),
        "question_count": len(answer_free),
        "video_count": len(videos),
        "fold_counts": {
            str(key): value for key, value in sorted(fold_counts.items())
        },
        "seed": args.seed,
    }
    dump_json(output / "manifest.json", manifest)
    (output / "FROZEN").write_text(
        sha256_file(output / "manifest.json") + "\n", encoding="ascii"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
