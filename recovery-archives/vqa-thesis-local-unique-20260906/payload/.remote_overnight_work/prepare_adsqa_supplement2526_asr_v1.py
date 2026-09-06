#!/usr/bin/env python3
"""Prepare answer-free ASR worklists for the AdsQA gt_answer supplement."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--clip-root", type=Path, required=True)
    parser.add_argument("--ocr-root", type=Path, required=True)
    parser.add_argument("--asr-root", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--shards", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026073001)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise RuntimeError(f"expected a JSON list: {path}")
    return value


def canonical(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        qid = str(row["question_id"])
        if qid in result:
            if json.dumps(result[qid], sort_keys=True) != json.dumps(
                row, sort_keys=True
            ):
                raise RuntimeError(f"conflicting duplicate: {qid}")
            continue
        result[qid] = row
    return result


def video_id(row: dict[str, Any]) -> str:
    return str(row.get("video", row.get("video_id")))


def stable_rank(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.shards != 5:
        raise RuntimeError("the supplement ASR protocol requires five shards")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise RuntimeError("refusing to overwrite non-empty output")

    questions = canonical(load_rows(args.questions))
    references = canonical(load_rows(args.groundtruth))
    if (
        len(questions) != 7846
        or len(references) != 7846
        or set(questions) != set(references)
    ):
        raise RuntimeError("unexpected AdsQA test source")
    supplement_ids = {
        qid
        for qid, row in references.items()
        if (
            not str(row.get("answer") or "").strip()
            and str(row.get("gt_answer") or "").strip()
        )
    }
    if len(supplement_ids) != 2526:
        raise RuntimeError("gt_answer supplement count changed")

    questions_by_video: dict[str, list[str]] = defaultdict(list)
    for qid in supplement_ids:
        questions_by_video[video_id(questions[qid])].append(qid)
    videos = set(questions_by_video)
    if len(videos) != 1258:
        raise RuntimeError("supplement video count changed")

    missing_asr: list[str] = []
    existing_asr = 0
    for video in sorted(videos):
        assets = (
            args.video_root / f"{video}.mp4",
            args.clip_root / f"{video}.npz",
            args.ocr_root / f"{video}.json",
        )
        if not all(path.is_file() for path in assets):
            raise RuntimeError(f"missing visual asset: {video}")
        matches = [
            root / f"{video}.json"
            for root in args.asr_root
            if (root / f"{video}.json").is_file()
        ]
        if len(matches) > 1:
            raise RuntimeError(f"duplicate segmented ASR records: {video}")
        if matches:
            existing_asr += 1
        else:
            missing_asr.append(video)
    if existing_asr != 983 or len(missing_asr) != 275:
        raise RuntimeError(
            f"segmented ASR inventory changed: {existing_asr}/{len(missing_asr)}"
        )

    ordered = sorted(missing_asr, key=lambda value: stable_rank(args.seed, value))
    shard_rows: dict[int, list[dict[str, str]]] = defaultdict(list)
    for index, video in enumerate(ordered):
        qid = min(questions_by_video[video])
        shard_rows[index % args.shards].append(
            {
                "question_id": qid,
                "video": video,
                "answer_free": "true",
            }
        )
    counts = Counter({fold: len(shard_rows[fold]) for fold in range(args.shards)})
    for fold in range(args.shards):
        dump_json(
            args.output_root / "selection_shards" / f"fold_{fold}.json",
            shard_rows[fold],
        )
    preflight = {
        "schema_version": "adsqa_supplement2526_asr_preflight_v1",
        "passed": (
            len(supplement_ids) == 2526
            and len(videos) == 1258
            and existing_asr == 983
            and len(missing_asr) == 275
            and max(counts.values()) - min(counts.values()) <= 1
        ),
        "question_count": len(supplement_ids),
        "video_count": len(videos),
        "existing_segmented_asr_videos": existing_asr,
        "missing_segmented_asr_videos": len(missing_asr),
        "shard_counts": {str(key): value for key, value in sorted(counts.items())},
        "answers_read_only_to_select_reference_field": True,
        "answers_written_to_worklists": False,
    }
    dump_json(args.output_root / "preflight.json", preflight)
    if not preflight["passed"]:
        raise RuntimeError("supplement ASR preflight failed")
    print(json.dumps(preflight, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
