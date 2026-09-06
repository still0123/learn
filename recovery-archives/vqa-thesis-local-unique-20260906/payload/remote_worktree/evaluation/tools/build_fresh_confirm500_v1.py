#!/usr/bin/env python3
"""Freeze a video-disjoint, type-balanced AdsQA confirmation set."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


FORBIDDEN_QUESTION_FIELDS = {
    "answer",
    "ground_truth",
    "groundtruth",
    "reference_answer",
    "judge_score",
    "prediction",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument(
        "--technical-exclude",
        action="append",
        default=[],
        help="Always exclude listed videos for technical decode failures.",
    )
    parser.add_argument("--video-root", required=True)
    parser.add_argument("--frames-fallback-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", default="fresh_confirm500_seed20260719_v1")
    parser.add_argument("--per-type", type=int, default=100)
    parser.add_argument(
        "--types",
        default="Type_1,Type_2,Type_3,Type_4,Type_5",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--exclude-video-overlap",
        action="store_true",
        help="Require zero overlap with prior videos; omitted for FreshQ question-only disjointness.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping):
        for key in ("questions", "records", "rows", "items", "data"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        else:
            raise ValueError(f"cannot locate records in {path}")
    else:
        raise ValueError(f"unsupported JSON payload in {path}")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError(f"non-object record in {path}")
    return [dict(row) for row in rows]


def deduplicate_exact_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    source_name: str,
) -> tuple[list[dict[str, Any]], int]:
    by_id: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for raw in rows:
        row = dict(raw)
        qid = question_id(row)
        if not qid:
            raise ValueError(f"{source_name} contains an empty question ID")
        previous = by_id.get(qid)
        if previous is None:
            by_id[qid] = row
            continue
        if canonical_sha256(previous) != canonical_sha256(row):
            raise ValueError(f"{source_name} has conflicting rows for question ID {qid}")
        duplicate_count += 1
    return list(by_id.values()), duplicate_count


def question_id(row: Mapping[str, Any]) -> str:
    value = row.get("question_id", row.get("id", ""))
    return str(value)


def video_id(row: Mapping[str, Any]) -> str:
    value = row.get("video", row.get("video_id", ""))
    return str(value)


def primary_type(row: Mapping[str, Any]) -> str:
    value = row.get("question_type", [])
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and value:
        return str(value[0])
    return ""


def answer_is_usable(row: Mapping[str, Any]) -> bool:
    answer = str(row.get("answer", "")).strip()
    return bool(answer) and answer.lower() not in {"none", "null", "nan", "n/a"}


def video_exists(video: str, video_root: Path, fallback_root: Path) -> bool:
    return any(
        path.exists()
        for path in (
            video_root / f"{video}.mp4",
            video_root / video,
            video_root / f"{video}.webm",
            video_root / f"{video}.mov",
            fallback_root / video,
        )
    )


def deterministic_key(seed: str, row: Mapping[str, Any]) -> str:
    value = f"{seed}|{primary_type(row)}|{video_id(row)}|{question_id(row)}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    question_path = Path(args.questions).resolve()
    groundtruth_path = Path(args.groundtruth).resolve()
    exclude_paths = [Path(value).resolve() for value in args.exclude]
    technical_exclude_paths = [Path(value).resolve() for value in args.technical_exclude]
    video_root = Path(args.video_root).resolve()
    fallback_root = Path(args.frames_fallback_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    protected_outputs = (
        output_dir / "question.json",
        output_dir / "groundtruth.json",
        output_dir / "selection_manifest.json",
        output_dir / "audit.json",
    )
    if not args.overwrite and any(path.exists() for path in protected_outputs):
        raise ValueError(f"frozen output already exists under {output_dir}")
    expected_types = [value.strip() for value in args.types.split(",") if value.strip()]
    if len(expected_types) != len(set(expected_types)) or not expected_types:
        raise ValueError("--types must contain unique non-empty values")
    if args.per_type <= 0:
        raise ValueError("--per-type must be positive")

    source_questions = load_rows(question_path)
    source_groundtruth = load_rows(groundtruth_path)
    questions, question_exact_duplicate_count = deduplicate_exact_rows(
        source_questions,
        source_name="questions",
    )
    groundtruth, groundtruth_exact_duplicate_count = deduplicate_exact_rows(
        source_groundtruth,
        source_name="groundtruth",
    )
    question_by_id = {question_id(row): row for row in questions}
    groundtruth_by_id = {question_id(row): row for row in groundtruth}
    if set(question_by_id) != set(groundtruth_by_id):
        raise ValueError("source questions and groundtruth IDs are not aligned")
    for row in questions:
        if FORBIDDEN_QUESTION_FIELDS & set(row):
            raise ValueError("source question file contains answer-side fields")

    excluded_questions: set[str] = set()
    excluded_videos: set[str] = set()
    exclusion_audit = []
    for path in exclude_paths:
        rows = load_rows(path)
        ids = {question_id(row) for row in rows if question_id(row)}
        videos = {video_id(row) for row in rows if video_id(row)}
        excluded_questions.update(ids)
        excluded_videos.update(videos)
        exclusion_audit.append(
            {
                "path": str(path),
                "sha256": sha256_file(path),
                "question_count": len(ids),
                "video_count": len(videos),
            }
        )
    technical_excluded_videos: set[str] = set()
    technical_exclusion_audit = []
    for path in technical_exclude_paths:
        rows = load_rows(path)
        videos = {video_id(row) for row in rows if video_id(row)}
        if not videos:
            raise ValueError(f"technical exclusion file has no video IDs: {path}")
        technical_excluded_videos.update(videos)
        technical_exclusion_audit.append(
            {
                "path": str(path),
                "sha256": sha256_file(path),
                "video_count": len(videos),
            }
        )

    eligible_by_type: dict[str, list[dict[str, Any]]] = {
        value: [] for value in expected_types
    }
    rejection_counts = Counter()
    for qid, row in question_by_id.items():
        gt = groundtruth_by_id[qid]
        video = video_id(row)
        qtype = primary_type(row)
        if qid in excluded_questions:
            rejection_counts["prior_question"] += 1
            continue
        if video in technical_excluded_videos:
            rejection_counts["technical_video_failure"] += 1
            continue
        if args.exclude_video_overlap and video in excluded_videos:
            rejection_counts["prior_video"] += 1
            continue
        if qtype not in eligible_by_type:
            rejection_counts["unsupported_primary_type"] += 1
            continue
        if not answer_is_usable(gt):
            rejection_counts["empty_reference_answer"] += 1
            continue
        if not video_exists(video, video_root, fallback_root):
            rejection_counts["missing_video"] += 1
            continue
        eligible_by_type[qtype].append(dict(row))

    for qtype in expected_types:
        eligible_by_type[qtype].sort(key=lambda row: deterministic_key(args.seed, row))

    selected: list[dict[str, Any]] = []
    selected_counts = Counter()
    used_videos: set[str] = set()
    cursors = {qtype: 0 for qtype in expected_types}
    while any(selected_counts[qtype] < args.per_type for qtype in expected_types):
        made_progress = False
        for qtype in expected_types:
            if selected_counts[qtype] >= args.per_type:
                continue
            candidates = eligible_by_type[qtype]
            while cursors[qtype] < len(candidates):
                candidate = candidates[cursors[qtype]]
                cursors[qtype] += 1
                if video_id(candidate) in used_videos:
                    continue
                selected.append(candidate)
                selected_counts[qtype] += 1
                used_videos.add(video_id(candidate))
                made_progress = True
                break
        if not made_progress:
            shortages = {
                qtype: args.per_type - selected_counts[qtype]
                for qtype in expected_types
                if selected_counts[qtype] < args.per_type
            }
            diagnostic = {
                "shortages": shortages,
                "selected_counts": dict(sorted(selected_counts.items())),
                "eligible_primary_type_counts": {
                    key: len(value) for key, value in sorted(eligible_by_type.items())
                },
                "rejection_counts": dict(sorted(rejection_counts.items())),
                "excluded_question_count": len(excluded_questions),
                "excluded_video_count": len(excluded_videos),
            }
            raise ValueError(
                "cannot satisfy unique-video quotas: "
                + json.dumps(diagnostic, ensure_ascii=True, sort_keys=True)
            )

    selected.sort(key=lambda row: (expected_types.index(primary_type(row)), deterministic_key(args.seed, row)))
    output_questions = [
        {
            "question_id": question_id(row),
            "video": video_id(row),
            "question": str(row["question"]),
            "question_type": row.get("question_type", [primary_type(row)]),
            "fold": 0,
        }
        for row in selected
    ]
    output_groundtruth = [groundtruth_by_id[question_id(row)] for row in selected]
    manifest = [
        {
            "selection_rank": index,
            "question_id": question_id(row),
            "video_id": video_id(row),
            "primary_type": primary_type(row),
            "selection_key_sha256": deterministic_key(args.seed, row),
        }
        for index, row in enumerate(selected)
    ]

    question_output = output_dir / "question.json"
    groundtruth_output = output_dir / "groundtruth.json"
    manifest_output = output_dir / "selection_manifest.json"
    write_json(question_output, output_questions)
    write_json(groundtruth_output, output_groundtruth)
    write_json(manifest_output, manifest)

    selected_ids = {question_id(row) for row in selected}
    selected_videos = {video_id(row) for row in selected}
    audit = {
        "schema_version": "adsqa_fresh_confirm500_selection_audit_v1",
        "passed": all(
            (
                len(selected) == args.per_type * len(expected_types),
                len(selected_ids) == len(selected),
                len(selected_videos) == len(selected),
                not (selected_ids & excluded_questions),
                not args.exclude_video_overlap or not (selected_videos & excluded_videos),
                not (selected_videos & technical_excluded_videos),
                all(selected_counts[qtype] == args.per_type for qtype in expected_types),
                all(not (FORBIDDEN_QUESTION_FIELDS & set(row)) for row in output_questions),
            )
        ),
        "seed": args.seed,
        "source_question_row_count": len(source_questions),
        "source_groundtruth_row_count": len(source_groundtruth),
        "source_unique_question_count": len(questions),
        "question_exact_duplicate_count": question_exact_duplicate_count,
        "groundtruth_exact_duplicate_count": groundtruth_exact_duplicate_count,
        "selected_question_count": len(selected),
        "selected_video_count": len(selected_videos),
        "selected_primary_type_counts": dict(sorted(selected_counts.items())),
        "eligible_primary_type_counts": {
            key: len(value) for key, value in sorted(eligible_by_type.items())
        },
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "excluded_question_count": len(excluded_questions),
        "excluded_video_count": len(excluded_videos),
        "question_overlap_with_exclusions": len(selected_ids & excluded_questions),
        "video_overlap_with_exclusions": len(selected_videos & excluded_videos),
        "technical_excluded_video_count": len(technical_excluded_videos),
        "technical_video_overlap": len(selected_videos & technical_excluded_videos),
        "disjointness_scope": (
            "question_and_video"
            if args.exclude_video_overlap
            else "question_only_with_unique_selected_videos"
        ),
        "prior_video_overlap_allowed": not args.exclude_video_overlap,
        "answer_content_used_for_ranking": False,
        "reference_answer_filter": "non-empty only",
        "source_questions_sha256": sha256_file(question_path),
        "source_groundtruth_sha256": sha256_file(groundtruth_path),
        "exclusions": exclusion_audit,
        "technical_exclusions": technical_exclusion_audit,
        "question_sha256": sha256_file(question_output),
        "groundtruth_sha256": sha256_file(groundtruth_output),
        "selection_manifest_sha256": sha256_file(manifest_output),
        "selected_ids_canonical_sha256": canonical_sha256(sorted(selected_ids)),
        "selected_videos_canonical_sha256": canonical_sha256(sorted(selected_videos)),
    }
    write_json(output_dir / "audit.json", audit)
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
