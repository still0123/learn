#!/usr/bin/env python3
"""Freeze an answer-free, video-disjoint ReAd-R increment Pilot-300."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


FORBIDDEN = {
    "answer",
    "answers",
    "ground_truth",
    "gt_answer",
    "reference_answer",
    "judge_score",
    "prediction",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--mmr-manifest", type=Path, required=True)
    parser.add_argument("--av-manifest", type=Path, required=True)
    parser.add_argument("--exclude", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", default="readr_increment_pilot300_v1")
    parser.add_argument("--calibration-videos", type=int, default=20)
    parser.add_argument("--confirm-videos", type=int, default=40)
    parser.add_argument("--questions-per-video", type=int, default=5)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def dump_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_rows(path: Path) -> Any:
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return json.loads(path.read_text(encoding="utf-8"))


def collect_video_ids(value: Any) -> set[str]:
    found: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if key in {"video", "video_id"} and isinstance(nested, str):
                    found.add(nested.removesuffix(".mp4"))
                else:
                    visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value)
    return found


def keyed_hash(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}::{value}".encode("utf-8")).hexdigest()


def index_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in load_rows(path):
        qid = str(row["question_id"])
        if qid in rows:
            raise RuntimeError(f"duplicate question in {path}: {qid}")
        rows[qid] = row
    return rows


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")

    questions = load_rows(args.questions)
    if not isinstance(questions, list) or not questions:
        raise RuntimeError("questions must be a non-empty JSON list")
    required = {
        "question_id",
        "video",
        "question",
        "official_prompt_text",
        "answer_free",
    }
    if any(
        not isinstance(row, dict)
        or not required.issubset(row)
        or row.get("answer_free") is not True
        or FORBIDDEN & set(row)
        for row in questions
    ):
        raise RuntimeError("question source is not answer-free")

    excluded_videos: set[str] = set()
    exclusion_audit: list[dict[str, Any]] = []
    for path in args.exclude:
        if not path.is_file():
            raise RuntimeError(f"exclusion source does not exist: {path}")
        videos = collect_video_ids(load_rows(path))
        excluded_videos.update(videos)
        exclusion_audit.append(
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
                "video_count": len(videos),
            }
        )

    by_video: dict[str, list[dict[str, Any]]] = {}
    for row in questions:
        by_video.setdefault(str(row["video"]), []).append(row)
    eligible = [
        video_id
        for video_id, rows in by_video.items()
        if video_id not in excluded_videos
        and len(rows) == args.questions_per_video
    ]
    eligible.sort(key=lambda value: (keyed_hash(args.seed, value), value))
    required_videos = args.calibration_videos + args.confirm_videos
    if len(eligible) < required_videos:
        raise RuntimeError(
            f"only {len(eligible)} eligible videos, need {required_videos}"
        )

    selected_videos = eligible[:required_videos]
    calibration_videos = set(selected_videos[: args.calibration_videos])
    confirm_videos = set(selected_videos[args.calibration_videos :])
    selected_rows = [
        row
        for video_id in selected_videos
        for row in sorted(
            by_video[video_id],
            key=lambda item: str(item["question_id"]),
        )
    ]
    expected = required_videos * args.questions_per_video
    if len(selected_rows) != expected:
        raise RuntimeError("selected question count is inconsistent")

    video_fold = {
        video_id: index % 5 for index, video_id in enumerate(selected_videos)
    }
    frozen_rows: list[dict[str, Any]] = []
    for row in selected_rows:
        frozen = dict(row)
        frozen["source_fold"] = row.get("fold")
        frozen["fold"] = video_fold[str(row["video"])]
        frozen["pilot_partition"] = (
            "calibration100"
            if str(row["video"]) in calibration_videos
            else "confirm200"
        )
        frozen["selection_rule"] = "video_sha256_order_without_labels_v1"
        frozen_rows.append(frozen)

    selected_qids = {str(row["question_id"]) for row in frozen_rows}
    mmr = index_jsonl(args.mmr_manifest)
    av = index_jsonl(args.av_manifest)
    if selected_qids - set(mmr) or selected_qids - set(av):
        raise RuntimeError("selected questions are missing from evidence manifests")
    mmr_rows = [mmr[str(row["question_id"])] for row in frozen_rows]
    av_rows = [av[str(row["question_id"])] for row in frozen_rows]

    args.output_dir.mkdir(parents=True, exist_ok=False)
    dump_json(args.output_dir / "questions_answer_free.json", frozen_rows)
    dump_json(
        args.output_dir / "calibration100_questions_answer_free.json",
        [
            row
            for row in frozen_rows
            if row["pilot_partition"] == "calibration100"
        ],
    )
    dump_json(
        args.output_dir / "confirm200_questions_answer_free.json",
        [
            row
            for row in frozen_rows
            if row["pilot_partition"] == "confirm200"
        ],
    )
    for fold in range(5):
        dump_json(
            args.output_dir / "shards" / f"fold_{fold}.json",
            [row for row in frozen_rows if int(row["fold"]) == fold],
        )
    smoke_rows = [
        next(row for row in frozen_rows if int(row["fold"]) == fold)
        for fold in range(5)
    ]
    dump_json(args.output_dir / "smoke5_questions_answer_free.json", smoke_rows)
    dump_jsonl(args.output_dir / "mmr8_manifest.jsonl", mmr_rows)
    dump_jsonl(args.output_dir / "av_manifest.jsonl", av_rows)

    audit = {
        "schema_version": "readr_increment_pilot300_prepare_audit_v1",
        "seed": args.seed,
        "selection_rule": "sort eligible video IDs by sha256(seed::video_id)",
        "labels_or_predictions_used_for_selection": False,
        "answer_free": True,
        "question_count": len(frozen_rows),
        "video_count": len(selected_videos),
        "questions_per_video": args.questions_per_video,
        "calibration_question_count": sum(
            row["pilot_partition"] == "calibration100" for row in frozen_rows
        ),
        "calibration_video_count": len(calibration_videos),
        "confirm_question_count": sum(
            row["pilot_partition"] == "confirm200" for row in frozen_rows
        ),
        "confirm_video_count": len(confirm_videos),
        "calibration_confirm_video_overlap": len(
            calibration_videos & confirm_videos
        ),
        "fold_question_counts": dict(
            Counter(str(row["fold"]) for row in frozen_rows)
        ),
        "excluded_video_count": len(excluded_videos),
        "exclusion_sources": exclusion_audit,
        "source_files": {
            "questions": {
                "path": str(args.questions.resolve()),
                "sha256": sha256_file(args.questions),
            },
            "mmr_manifest": {
                "path": str(args.mmr_manifest.resolve()),
                "sha256": sha256_file(args.mmr_manifest),
            },
            "av_manifest": {
                "path": str(args.av_manifest.resolve()),
                "sha256": sha256_file(args.av_manifest),
            },
        },
        "selected_video_ids_sha256": hashlib.sha256(
            "\n".join(selected_videos).encode("utf-8")
        ).hexdigest(),
    }
    dump_json(args.output_dir / "audit.json", audit)
    dump_json(
        args.output_dir / "manifest.json",
        {
            "schema_version": "readr_increment_pilot300_manifest_v1",
            "files": {
                str(path.relative_to(args.output_dir)): sha256_file(path)
                for path in sorted(args.output_dir.rglob("*"))
                if path.is_file()
            },
        },
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
