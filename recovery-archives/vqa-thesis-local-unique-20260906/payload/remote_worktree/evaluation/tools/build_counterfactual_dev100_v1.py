#!/usr/bin/env python3
"""Build one deterministic, video-disjoint AdsQA counterfactual dev item per train video."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_file", required=True)
    parser.add_argument("--video_root", required=True)
    parser.add_argument("--question_output", required=True)
    parser.add_argument("--groundtruth_output", required=True)
    parser.add_argument("--manifest_output", required=True)
    parser.add_argument("--exclude_question_files", nargs="*", default=[])
    parser.add_argument("--expected_count", type=int, default=100)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_video(video_root: Path, video_id: str) -> Path:
    candidates = [
        video_root / f"{video_id}.mp4", video_root / video_id,
        video_root / f"{video_id}.webm", video_root / f"{video_id}.mov",
    ]
    return next((path for path in candidates if path.exists()), candidates[0])


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[2]
    import sys

    sys.path.insert(0, str(project_root))
    from evaluation.methods.counterfactual_sufficiency.counterfactual import (
        CATEGORY_KEYWORDS,
        categorize_question,
        question_stem,
    )

    rows: List[Dict[str, Any]] = load_json(args.train_file)
    by_video: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for source_index, row in enumerate(rows):
        item = dict(row)
        item["_source_index"] = source_index
        item["_category"] = categorize_question(str(item.get("question", "")))
        by_video[str(item["video"])].append(item)

    priority = {category: rank for rank, category in enumerate(CATEGORY_KEYWORDS)}
    priority["narrative_other"] = len(priority)
    selected: List[Dict[str, Any]] = []
    for video_id in sorted(by_video):
        candidates = sorted(
            by_video[video_id],
            key=lambda item: (priority[item["_category"]], item["_source_index"]),
        )
        selected.append(candidates[0])
    if len(selected) != args.expected_count:
        raise RuntimeError(f"expected {args.expected_count} videos, found {len(selected)}")

    exclude_qids: set[str] = set()
    exclude_videos: set[str] = set()
    exclusions = []
    for path_str in args.exclude_question_files:
        path = Path(path_str)
        excluded = load_json(str(path))
        qids = {str(item.get("question_id")) for item in excluded}
        videos = {str(item.get("video", item.get("video_id", ""))) for item in excluded}
        exclude_qids.update(qids)
        exclude_videos.update(videos)
        exclusions.append({"path": str(path), "sha256": sha256_file(path), "rows": len(excluded)})

    questions = []
    groundtruth = []
    manifest_rows = []
    missing_videos = []
    for row in selected:
        source_qid = str(row["question_id"])
        qid = f"traincf_{source_qid}"
        video_id = str(row["video"])
        normalized_question = question_stem(str(row["question"]))
        category = str(row["_category"])
        video_path = resolve_video(Path(args.video_root), video_id)
        if not video_path.exists():
            missing_videos.append(video_id)
        question_row = {
            "question_id": qid,
            "video": video_id,
            "question": normalized_question,
            "question_type": [category],
            "source_split": "train",
        }
        gt_row = {
            **question_row,
            "answer": str(row.get("answer", "")),
            "meta_info": str(row.get("meta_info", "")),
        }
        questions.append(question_row)
        groundtruth.append(gt_row)
        manifest_rows.append({
            "question_id": qid,
            "source_question_id": source_qid,
            "source_index": int(row["_source_index"]),
            "video": video_id,
            "category": category,
            "video_path": str(video_path),
        })

    question_overlap = sorted({row["question_id"] for row in questions} & exclude_qids)
    video_overlap = sorted({row["video"] for row in questions} & exclude_videos)
    if question_overlap or video_overlap or missing_videos:
        raise RuntimeError(
            f"split audit failed: q_overlap={len(question_overlap)} "
            f"video_overlap={len(video_overlap)} missing_videos={len(missing_videos)}"
        )

    question_output = Path(args.question_output)
    groundtruth_output = Path(args.groundtruth_output)
    manifest_output = Path(args.manifest_output)
    dump_json(question_output, questions)
    dump_json(groundtruth_output, groundtruth)
    manifest = {
        "schema_version": "adsqa_counterfactual_dev100_v1",
        "source_train_file": str(Path(args.train_file)),
        "source_train_sha256": sha256_file(Path(args.train_file)),
        "selection_policy": "one_per_train_video_rare_evidence_category_priority_v1",
        "category_priority": list(CATEGORY_KEYWORDS) + ["narrative_other"],
        "row_count": len(questions),
        "unique_question_count": len({row["question_id"] for row in questions}),
        "unique_video_count": len({row["video"] for row in questions}),
        "category_counts": dict(sorted(Counter(row["question_type"][0] for row in questions).items())),
        "question_output": str(question_output),
        "question_output_sha256": sha256_file(question_output),
        "groundtruth_output": str(groundtruth_output),
        "groundtruth_output_sha256": sha256_file(groundtruth_output),
        "excluded_splits": exclusions,
        "overlap_audit": {
            "question_overlap_count": 0,
            "video_overlap_count": 0,
            "missing_video_count": 0,
        },
        "items": manifest_rows,
    }
    dump_json(manifest_output, manifest)
    print(json.dumps({key: manifest[key] for key in (
        "row_count", "unique_video_count", "category_counts", "overlap_audit"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
