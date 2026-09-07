#!/usr/bin/env python3
"""Build the AdsQA-train GroupCV split and audit Fresh Confirm capacity.

The tool deliberately keeps training answers separate from the inference-facing
question manifest.  It never opens test ground truth, and it does not create a
Fresh Confirm evaluation set: it only records the currently eligible video
pool after excluding all named historical development/evaluation resources.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


RUN_DIR = PROJECT_ROOT / "evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"
GROUPCV_FOLD_COUNT = 5
GROUPCV_SEED = 42
FRESH_CONFIRM_TARGET_VIDEOS = 300


class AuditError(ValueError):
    """Raised when the requested leakage or grouping invariants are violated."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def load_question_rows(path: Path, *, require_answer: bool | None = None) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise AuditError(f"question file must be a list of objects: {path}")
    for row in payload:
        if not row.get("question_id") or not row.get("video") or not row.get("question"):
            raise AuditError(f"question file row lacks question_id/video/question: {path}")
        has_answer = "answer" in row
        if require_answer is True and not has_answer:
            raise AuditError(f"answer is required in training split: {path}")
        if require_answer is False and has_answer:
            raise AuditError(f"test question file must not contain answers: {path}")
    return payload


def build_groupcv_folds(
    train_rows: Sequence[Mapping[str, Any]],
    *,
    fold_count: int = GROUPCV_FOLD_COUNT,
    seed: int = GROUPCV_SEED,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Create exact video-level folds and answer-separated OOF manifests."""
    if fold_count <= 1:
        raise AuditError("fold_count must be greater than one")
    video_rows: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in train_rows:
        video_rows[str(row["video"])].append(row)
    videos = sorted(video_rows)
    if len(videos) % fold_count:
        raise AuditError("training video count must divide exactly by fold_count")

    question_ids = [str(row["question_id"]) for row in train_rows]
    if len(question_ids) != len(set(question_ids)):
        raise AuditError("training question IDs must be unique")
    shuffled = list(videos)
    random.Random(seed).shuffle(shuffled)
    videos_per_fold = len(videos) // fold_count
    folds = []
    oof_questions = []
    oof_groundtruth = []
    seen_validation_videos: set[str] = set()
    seen_oof_questions: set[str] = set()

    for fold_id in range(fold_count):
        start = fold_id * videos_per_fold
        validation_videos = sorted(shuffled[start : start + videos_per_fold])
        validation_set = set(validation_videos)
        train_videos = sorted(set(videos) - validation_set)
        if validation_set & set(train_videos):
            raise AuditError(f"video leakage in fold {fold_id}")
        if seen_validation_videos & validation_set:
            raise AuditError(f"validation video repeated across folds: {fold_id}")
        seen_validation_videos.update(validation_set)

        validation_rows = [
            row for video in validation_videos for row in sorted(
                video_rows[video], key=lambda item: int(item["question_id"])
            )
        ]
        train_rows_fold = [
            row for video in train_videos for row in sorted(
                video_rows[video], key=lambda item: int(item["question_id"])
            )
        ]
        for row in validation_rows:
            question_id = str(row["question_id"])
            if question_id in seen_oof_questions:
                raise AuditError(f"OOF question repeated across folds: {question_id}")
            seen_oof_questions.add(question_id)
            oof_questions.append(
                {
                    "fold": fold_id,
                    "question_id": question_id,
                    "video": str(row["video"]),
                    "question": str(row["question"]),
                }
            )
            oof_groundtruth.append(
                {
                    "fold": fold_id,
                    "question_id": question_id,
                    "video": str(row["video"]),
                    "answer": str(row["answer"]),
                    "not_gate_input": True,
                    "not_inference_input": True,
                }
            )
        folds.append(
            {
                "fold": fold_id,
                "train_video_ids": train_videos,
                "validation_video_ids": validation_videos,
                "train_question_ids": [str(row["question_id"]) for row in train_rows_fold],
                "validation_question_ids": [str(row["question_id"]) for row in validation_rows],
                "train_video_count": len(train_videos),
                "validation_video_count": len(validation_videos),
                "train_question_count": len(train_rows_fold),
                "validation_question_count": len(validation_rows),
                "video_overlap_count": 0,
            }
        )

    if seen_validation_videos != set(videos):
        raise AuditError("not every training video is used once as OOF validation")
    if seen_oof_questions != set(question_ids):
        raise AuditError("not every training question appears exactly once OOF")
    return folds, oof_questions, oof_groundtruth


def extract_video_ids_from_question_file(path: Path) -> set[str]:
    rows = load_question_rows(path)
    return {str(row["video"]) for row in rows}


def historical_question_sources(root: Path) -> list[tuple[str, Path]]:
    """Return the closed, named legacy sources that must not enter Fresh Confirm."""
    sources: list[tuple[str, Path]] = []
    for path in sorted((root / "data").glob("pilot*question.json")):
        sources.append(("pilot", path))
    for path in sorted((root / "data").glob("confirm*question.json")):
        sources.append(("historical_confirm", path))
    for path in sorted((root / "data").glob("innovation1_confirm*/question.json")):
        sources.append(("historical_confirm", path))
    for path in sorted((root / "data").glob("innovation1_evidence*/question.json")):
        sources.append(("evidence", path))

    for relative, category in (
        ("evaluation/runs/innovation1_evidence300_stage_v1/exploratory_dev200_v1/question.json", "development"),
        ("evaluation/runs/innovation1_evidence300_stage_v1/exploratory_tail100_v1/tail100_question.json", "development"),
        ("data/counterfactual_dev100_v1/question.json", "development"),
    ):
        path = root / relative
        if path.exists():
            sources.append((category, path))
    return sorted(set(sources), key=lambda item: (item[0], str(item[1])))


def load_claim_split_video_ids(
    path: Path,
    allowed_splits: set[str],
) -> dict[str, set[str]]:
    result = {name: set() for name in allowed_splits}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditError(f"invalid claim JSONL at {path}:{line_number}") from exc
        split = str(row.get("split", ""))
        if split in result:
            video_id = str(row.get("video_id", ""))
            if not video_id:
                raise AuditError(f"claim row has no video_id at {path}:{line_number}")
            result[split].add(video_id)
    return result


def collect_historical_exclusions(root: Path) -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    categories: dict[str, set[str]] = defaultdict(set)
    source_records = []
    for category, path in historical_question_sources(root):
        video_ids = extract_video_ids_from_question_file(path)
        categories[category].update(video_ids)
        source_records.append(
            {
                "category": category,
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
                "unique_video_count": len(video_ids),
            }
        )

    claims_path = (
        root
        / "evaluation/runs/innovation2_realclaim300_v2_corrected_frames/claims.jsonl"
    )
    claim_splits = load_claim_split_video_ids(claims_path, {"calibration", "development"})
    for split, video_ids in claim_splits.items():
        categories[split].update(video_ids)
        source_records.append(
            {
                "category": split,
                "path": str(claims_path.resolve()),
                "sha256": sha256_file(claims_path),
                "unique_video_count": len(video_ids),
                "selector": f"split={split}",
            }
        )
    return dict(categories), source_records


def audit_fresh_confirm_capacity(
    test_rows: Sequence[Mapping[str, Any]],
    exclusions: Mapping[str, set[str]],
) -> dict[str, Any]:
    test_videos = {str(row["video"]) for row in test_rows}
    used_videos = set().union(*exclusions.values()) if exclusions else set()
    candidate_videos = sorted(test_videos - used_videos)
    candidate_set = set(candidate_videos)
    candidate_questions = [
        {
            "question_id": str(row["question_id"]),
            "video": str(row["video"]),
            "question_type": row.get("question_type", []),
        }
        for row in test_rows
        if str(row["video"]) in candidate_set
    ]
    type_counts = Counter(
        str(question_type)
        for row in candidate_questions
        for question_type in (
            row["question_type"]
            if isinstance(row["question_type"], list)
            else [row["question_type"]]
        )
    )
    overlaps = {
        category: len(test_videos & video_ids)
        for category, video_ids in sorted(exclusions.items())
    }
    candidate_overlaps = {
        category: len(candidate_set & video_ids)
        for category, video_ids in sorted(exclusions.items())
    }
    if any(candidate_overlaps.values()):
        raise AuditError("Fresh Confirm candidate pool overlaps a historical exclusion category")
    return {
        "candidate_source": "testset_question.json_only",
        "test_groundtruth_read": False,
        "selection_deferred_until_final_method_freeze": True,
        "fresh_confirm_target_unique_videos": FRESH_CONFIRM_TARGET_VIDEOS,
        "test_unique_video_count": len(test_videos),
        "excluded_unique_video_count": len(used_videos),
        "candidate_unique_video_count": len(candidate_videos),
        "candidate_video_ids": candidate_videos,
        "candidate_video_ids_sha256": canonical_sha256(candidate_videos),
        "candidate_question_count": len(candidate_questions),
        "candidate_question_type_membership_counts": dict(sorted(type_counts.items())),
        "test_overlap_by_exclusion_category": overlaps,
        "candidate_overlap_by_exclusion_category": candidate_overlaps,
        "fresh_confirm_300_available": len(candidate_videos) >= FRESH_CONFIRM_TARGET_VIDEOS,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AdsQA train GroupCV and audit Fresh Confirm capacity"
    )
    parser.add_argument("--train-file", default=str(PROJECT_ROOT / "data/train.json"))
    parser.add_argument(
        "--test-question-file",
        default=str(PROJECT_ROOT / "data/testset_question.json"),
    )
    parser.add_argument("--seed", type=int, default=GROUPCV_SEED)
    parser.add_argument("--output-dir", default=str(RUN_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_path = Path(args.train_file).resolve()
    test_question_path = Path(args.test_question_file).resolve()
    output_dir = Path(args.output_dir).resolve()

    train_rows = load_question_rows(train_path, require_answer=True)
    test_rows = load_question_rows(test_question_path, require_answer=False)
    train_videos = {str(row["video"]) for row in train_rows}
    test_videos = {str(row["video"]) for row in test_rows}
    if train_videos & test_videos:
        raise AuditError("train/test video overlap detected")

    folds, oof_questions, oof_groundtruth = build_groupcv_folds(
        train_rows,
        fold_count=GROUPCV_FOLD_COUNT,
        seed=args.seed,
    )
    exclusions, source_records = collect_historical_exclusions(PROJECT_ROOT)
    fresh_confirm = audit_fresh_confirm_capacity(test_rows, exclusions)

    groupcv_dir = output_dir / "groupcv5"
    preflight_dir = output_dir / "preflight"
    rows_by_question_id = {str(row["question_id"]): row for row in train_rows}
    for fold in folds:
        fold_dir = groupcv_dir / f"fold_{int(fold['fold'])}"
        train_questions = [
            {
                "question_id": question_id,
                "video": str(rows_by_question_id[question_id]["video"]),
                "question": str(rows_by_question_id[question_id]["question"]),
            }
            for question_id in fold["train_question_ids"]
        ]
        validation_questions = [
            {
                "question_id": question_id,
                "video": str(rows_by_question_id[question_id]["video"]),
                "question": str(rows_by_question_id[question_id]["question"]),
            }
            for question_id in fold["validation_question_ids"]
        ]
        validation_groundtruth = [
            {
                "question_id": question_id,
                "video": str(rows_by_question_id[question_id]["video"]),
                "answer": str(rows_by_question_id[question_id]["answer"]),
                "not_gate_input": True,
                "not_inference_input": True,
            }
            for question_id in fold["validation_question_ids"]
        ]
        train_question_path = fold_dir / "train_questions_v1.json"
        validation_question_path = fold_dir / "validation_questions_v1.json"
        validation_groundtruth_path = fold_dir / "validation_groundtruth_v1.json"
        write_json(train_question_path, train_questions)
        write_json(validation_question_path, validation_questions)
        write_json(validation_groundtruth_path, validation_groundtruth)
        fold["train_questions_path"] = str(train_question_path.resolve())
        fold["train_questions_sha256"] = sha256_file(train_question_path)
        fold["validation_questions_path"] = str(validation_question_path.resolve())
        fold["validation_questions_sha256"] = sha256_file(validation_question_path)
        fold["validation_groundtruth_path"] = str(validation_groundtruth_path.resolve())
        fold["validation_groundtruth_sha256"] = sha256_file(validation_groundtruth_path)
        fold["validation_groundtruth_not_gate_input"] = True

    fold_payload = {
        "schema_version": "adsqa_train_groupcv5_v1",
        "seed": args.seed,
        "fold_count": GROUPCV_FOLD_COUNT,
        "train_file": str(train_path),
        "train_file_sha256": sha256_file(train_path),
        "train_question_count": len(train_rows),
        "train_unique_video_count": len(train_videos),
        "questions_per_video": sorted(Counter(str(row["video"]) for row in train_rows).values()),
        "folds": folds,
    }
    write_json(groupcv_dir / "fold_assignments_v1.json", fold_payload)
    write_json(groupcv_dir / "oof_questions_v1.json", oof_questions)
    write_json(groupcv_dir / "oof_groundtruth_v1.json", oof_groundtruth)
    write_json(preflight_dir / "fresh_confirm_candidate_inventory_v1.json", fresh_confirm)

    report = {
        "schema_version": "adsqa_groupcv_and_fresh_confirm_audit_v1",
        "train_test_video_overlap_count": len(train_videos & test_videos),
        "groupcv": {
            "fold_assignment_path": str((groupcv_dir / "fold_assignments_v1.json").resolve()),
            "fold_assignment_sha256": sha256_file(groupcv_dir / "fold_assignments_v1.json"),
            "oof_questions_path": str((groupcv_dir / "oof_questions_v1.json").resolve()),
            "oof_questions_sha256": sha256_file(groupcv_dir / "oof_questions_v1.json"),
            "oof_groundtruth_path": str((groupcv_dir / "oof_groundtruth_v1.json").resolve()),
            "oof_groundtruth_sha256": sha256_file(groupcv_dir / "oof_groundtruth_v1.json"),
            "fold_count": GROUPCV_FOLD_COUNT,
            "validation_video_count_per_fold": [fold["validation_video_count"] for fold in folds],
            "validation_question_count_per_fold": [fold["validation_question_count"] for fold in folds],
            "all_training_videos_oof_once": True,
            "all_training_questions_oof_once": True,
            "train_validation_video_overlap_count_per_fold": [fold["video_overlap_count"] for fold in folds],
            "testset_answers_used_for_groupcv": False,
        },
        "fresh_confirm": {
            "inventory_path": str((preflight_dir / "fresh_confirm_candidate_inventory_v1.json").resolve()),
            "inventory_sha256": sha256_file(preflight_dir / "fresh_confirm_candidate_inventory_v1.json"),
            "historical_exclusion_sources": source_records,
            "historical_exclusion_category_counts": {
                category: len(video_ids) for category, video_ids in sorted(exclusions.items())
            },
            **fresh_confirm,
        },
        "audit_passed": True,
    }
    write_json(preflight_dir / "groupcv_and_fresh_confirm_audit_v1.json", report)
    print(
        json.dumps(
            {
                "audit_passed": report["audit_passed"],
                "train_test_video_overlap_count": report["train_test_video_overlap_count"],
                "groupcv_validation_videos_per_fold": report["groupcv"]["validation_video_count_per_fold"],
                "fresh_confirm_candidate_unique_videos": fresh_confirm["candidate_unique_video_count"],
                "fresh_confirm_300_available": fresh_confirm["fresh_confirm_300_available"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
