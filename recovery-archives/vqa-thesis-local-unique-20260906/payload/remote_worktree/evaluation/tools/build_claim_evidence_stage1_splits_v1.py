#!/usr/bin/env python3
"""Jointly preregister video-disjoint Dev300 and Confirm-D300 AdsQA splits."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


PRIMARY_TYPES = tuple(f"Type_{index}" for index in range(1, 6))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected JSON list: {path}")
    return value


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def video_exists(video_root: Path, video_id: str) -> bool:
    return any((video_root / f"{video_id}{suffix}").is_file() for suffix in (".mp4", ".mkv", ".webm", ".avi", ".mov"))


def stable_rank(seed: int, question_id: str) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def source_primary_type(index: int, count: int, row: dict[str, Any]) -> str:
    memberships = [str(value) for value in row.get("question_type", [])]
    explicit = next((value for value in memberships if value in PRIMARY_TYPES), None)
    if explicit:
        return explicit
    if count % len(PRIMARY_TYPES):
        raise ValueError("source length is not divisible into five primary-type blocks")
    return PRIMARY_TYPES[index // (count // len(PRIMARY_TYPES))]


def select_splits(
    questions: list[dict[str, Any]],
    groundtruth: list[dict[str, Any]],
    excluded_question_ids: set[str],
    excluded_video_ids: set[str],
    video_root: Path,
    per_type_per_split: int,
    seed: int,
) -> tuple[dict[str, list[tuple[int, dict[str, Any], dict[str, Any], str]]], dict[str, Any]]:
    if len(questions) != len(groundtruth):
        raise ValueError("question and groundtruth source lengths differ")
    pools: dict[str, list[tuple[int, dict[str, Any], dict[str, Any], str]]] = defaultdict(list)
    skipped: dict[str, Counter[str]] = defaultdict(Counter)
    for index, (question, gt) in enumerate(zip(questions, groundtruth)):
        if str(question.get("question_id")) != str(gt.get("question_id")):
            raise ValueError(f"question/groundtruth mismatch at source index {index}")
        primary_type = source_primary_type(index, len(questions), question)
        qid = str(question["question_id"])
        video_id = str(question["video"])
        if qid in excluded_question_ids:
            skipped[primary_type]["excluded_question"] += 1
        elif video_id in excluded_video_ids:
            skipped[primary_type]["excluded_video"] += 1
        elif not str(gt.get("answer", "")).strip():
            skipped[primary_type]["empty_answer"] += 1
        elif not video_exists(video_root, video_id):
            skipped[primary_type]["missing_video"] += 1
        else:
            pools[primary_type].append((index, question, gt, primary_type))
    for primary_type in PRIMARY_TYPES:
        pools[primary_type].sort(key=lambda row: stable_rank(seed, str(row[1]["question_id"])))

    split_rows = {"dev300": [], "confirmd300": []}
    selected_videos: set[str] = set()
    selected_questions: set[str] = set()
    pointers = {primary_type: 0 for primary_type in PRIMARY_TYPES}
    needed_per_type = per_type_per_split * 2
    for slot in range(needed_per_type):
        split_name = "dev300" if slot < per_type_per_split else "confirmd300"
        for primary_type in PRIMARY_TYPES:
            pool = pools[primary_type]
            selected = None
            while pointers[primary_type] < len(pool):
                candidate = pool[pointers[primary_type]]
                pointers[primary_type] += 1
                qid = str(candidate[1]["question_id"])
                video_id = str(candidate[1]["video"])
                if qid in selected_questions:
                    skipped[primary_type]["repeated_question"] += 1
                elif video_id in selected_videos:
                    skipped[primary_type]["repeated_video"] += 1
                else:
                    selected = candidate
                    break
            if selected is None:
                raise RuntimeError(
                    f"insufficient eligible rows for {primary_type}: "
                    f"need {needed_per_type}, selected {slot}"
                )
            split_rows[split_name].append(selected)
            selected_questions.add(str(selected[1]["question_id"]))
            selected_videos.add(str(selected[1]["video"]))
    audit = {
        "selected_question_count": len(selected_questions),
        "selected_video_count": len(selected_videos),
        "skipped": {primary_type: dict(skipped[primary_type]) for primary_type in PRIMARY_TYPES},
    }
    return split_rows, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-source", type=Path, required=True)
    parser.add_argument("--groundtruth-source", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--exclude-question-file", type=Path, action="append", default=[])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-type-per-split", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260713)
    args = parser.parse_args()
    questions = load_rows(args.question_source)
    groundtruth = load_rows(args.groundtruth_source)
    excluded_qids: set[str] = set()
    excluded_videos: set[str] = set()
    exclusions = []
    for path in args.exclude_question_file:
        rows = load_rows(path)
        excluded_qids.update(str(row["question_id"]) for row in rows)
        excluded_videos.update(str(row["video"]) for row in rows)
        exclusions.append({"path": str(path), "sha256": sha256_file(path), "rows": len(rows)})
    selected, audit = select_splits(
        questions, groundtruth, excluded_qids, excluded_videos,
        args.video_root, args.per_type_per_split, args.seed,
    )
    split_manifests = {}
    split_question_sets = {}
    split_video_sets = {}
    for split_name, rows in selected.items():
        rows = sorted(rows, key=lambda value: value[0])
        question_rows = [question for _, question, _, _ in rows]
        gt_rows = [gt for _, _, gt, _ in rows]
        question_path = args.output_root / split_name / "question.json"
        gt_path = args.output_root / split_name / "groundtruth.json"
        dump_json(question_path, question_rows)
        dump_json(gt_path, gt_rows)
        primary_counts = Counter(primary_type for _, _, _, primary_type in rows)
        split_question_sets[split_name] = {str(row["question_id"]) for row in question_rows}
        split_video_sets[split_name] = {str(row["video"]) for row in question_rows}
        split_manifests[split_name] = {
            "count": len(rows),
            "unique_questions": len(split_question_sets[split_name]),
            "unique_videos": len(split_video_sets[split_name]),
            "primary_type_counts": {value: primary_counts[value] for value in PRIMARY_TYPES},
            "question_path": str(question_path),
            "question_sha256": sha256_file(question_path),
            "groundtruth_path": str(gt_path),
            "groundtruth_sha256": sha256_file(gt_path),
            "source_indices": [index for index, _, _, _ in rows],
            "question_ids": [str(row["question_id"]) for row in question_rows],
            "video_ids": [str(row["video"]) for row in question_rows],
        }
    cross_question_overlap = split_question_sets["dev300"] & split_question_sets["confirmd300"]
    cross_video_overlap = split_video_sets["dev300"] & split_video_sets["confirmd300"]
    if cross_question_overlap or cross_video_overlap:
        raise RuntimeError("joint split overlap audit failed")
    manifest = {
        "schema": "adsqa_claim_evidence_stage1_splits_v1",
        "selection_policy": "seeded_hash_rank_unique_video_joint_dev_then_confirm_v1",
        "seed": args.seed,
        "per_type_per_split": args.per_type_per_split,
        "question_source": str(args.question_source),
        "question_source_sha256": sha256_file(args.question_source),
        "groundtruth_source": str(args.groundtruth_source),
        "groundtruth_source_sha256": sha256_file(args.groundtruth_source),
        "exclusions": exclusions,
        "excluded_question_count": len(excluded_qids),
        "excluded_video_count": len(excluded_videos),
        "splits": split_manifests,
        "cross_split_question_overlap": 0,
        "cross_split_video_overlap": 0,
        "audit": audit,
        "confirmd_policy": "single frozen run after Dev300 gate; no tuning",
    }
    manifest_path = args.output_root / "stage1_split_manifest.json"
    dump_json(manifest_path, manifest)
    print(json.dumps({
        "manifest": str(manifest_path),
        "dev300": split_manifests["dev300"]["count"],
        "confirmd300": split_manifests["confirmd300"]["count"],
        "question_overlap": 0,
        "video_overlap": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
