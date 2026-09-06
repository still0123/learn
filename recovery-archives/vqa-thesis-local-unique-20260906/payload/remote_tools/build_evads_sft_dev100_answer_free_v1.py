#!/usr/bin/env python3
"""Build a deterministic, answer-free, video-disjoint E-VAds SFT dev split."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import pyarrow.parquet as pq


FORBIDDEN_KEYS = {
    "answer",
    "reference_answer",
    "ground_truth",
    "reward",
    "label",
    "evidence_state",
    "pairwise_target",
}
SFT_COLUMNS = ("data_source", "videos", "prompt", "ability", "extra_info")
FOOTER_PREFIX = "\n\nYou are permitted to gather any relevant clues"
CATEGORY_RE = re.compile(r"^<video>Category: ([^\n]+)")


class SplitError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sft-parquet", required=True)
    parser.add_argument("--test-parquet", required=True)
    parser.add_argument("--video-index-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--selected-video-count", type=int, default=100)
    parser.add_argument("--selection-seed", default="evads-sft-dev100-v1")
    parser.add_argument("--exclude-questions")
    parser.add_argument("--split-name", default="evads_sft_dev100_v1")
    parser.add_argument(
        "--dev-stage",
        choices=("screen", "confirmation"),
        default="screen",
    )
    parser.add_argument("--fold-count", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def check_output_dir(path: Path, overwrite: bool) -> None:
    expected = ("questions_answer_free.json", "selection.json", "audit.json", "manifest.json")
    if path.exists() and any((path / name).exists() for name in expected) and not overwrite:
        raise SplitError(f"output already exists: {path}")
    path.mkdir(parents=True, exist_ok=True)


def require_columns(parquet_path: Path, columns: Iterable[str]) -> None:
    available = set(pq.ParquetFile(parquet_path).schema_arrow.names)
    missing = set(columns) - available
    if missing:
        raise SplitError(f"{parquet_path} is missing columns: {sorted(missing)}")


def parse_video_id(video_value: Any) -> str:
    if not isinstance(video_value, str) or not video_value.strip():
        raise SplitError("videos must be a non-empty relative path string")
    video_id = Path(video_value).stem
    if not video_id:
        raise SplitError(f"could not derive video id from {video_value!r}")
    return video_id


def extract_prompt_fields(prompt: Any) -> tuple[str, str, str]:
    if not isinstance(prompt, list) or len(prompt) != 1:
        raise SplitError("prompt must contain exactly one user message")
    message = prompt[0]
    if not isinstance(message, dict) or message.get("role") != "user":
        raise SplitError("prompt message must be a user message")
    official_prompt = message.get("content")
    if not isinstance(official_prompt, str) or not official_prompt.startswith("<video>"):
        raise SplitError("official prompt must be a non-empty <video> prompt")
    if FOOTER_PREFIX not in official_prompt:
        raise SplitError("official prompt is missing the fixed answer-format footer")
    prompt_body = official_prompt.split(FOOTER_PREFIX, 1)[0].rstrip()
    question = prompt_body.rsplit("\n", 1)[-1].strip()
    if not question or question.startswith("Time "):
        raise SplitError("could not extract a question from the official prompt")
    category_match = CATEGORY_RE.match(official_prompt)
    if category_match is None:
        raise SplitError("SFT prompt is missing its category header")
    return official_prompt, question, category_match.group(1).strip()


def extract_multimodal_context(official_prompt: str, question: str) -> str:
    body = official_prompt.removeprefix("<video>").split(
        FOOTER_PREFIX,
        1,
    )[0].rstrip()
    if not body.endswith(question):
        raise SplitError("official prompt does not end with its question")
    context = body[: -len(question)].rstrip()
    if "Time-aligned Events" not in context:
        raise SplitError("official prompt lacks time-aligned evidence")
    return context


def load_sft_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    require_columns(path, SFT_COLUMNS)
    rows = pq.ParquetFile(path).read(columns=list(SFT_COLUMNS)).to_pylist()
    cleaned: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    source_rows: list[dict[str, Any]] = []
    for row in rows:
        source_rows.append({key: row[key] for key in SFT_COLUMNS})
        extra_info = row["extra_info"]
        if not isinstance(extra_info, dict):
            raise SplitError("extra_info must be a struct")
        question_id = str(extra_info.get("id", ""))
        if not question_id or question_id in seen_questions:
            raise SplitError(f"duplicate or missing question id: {question_id}")
        seen_questions.add(question_id)
        video_id = parse_video_id(row["videos"])
        extra_video_path = str(extra_info.get("video_path", ""))
        if parse_video_id(extra_video_path) != video_id:
            raise SplitError(f"video path mismatch for {question_id}")
        official_prompt, question, category = extract_prompt_fields(row["prompt"])
        cleaned.append(
            {
                "question_id": question_id,
                "video": video_id,
                "question": question,
                "official_prompt_text": official_prompt,
                "ability": str(row["ability"]),
                "category": category,
                "data_source": str(row["data_source"]),
            }
        )
    return cleaned, {
        "row_count": len(rows),
        "allowed_column_content_sha256": canonical_sha256(source_rows),
        "columns_read": list(SFT_COLUMNS),
    }


def load_test_video_ids(path: Path) -> tuple[set[str], dict[str, Any]]:
    require_columns(path, ("videos",))
    rows = pq.ParquetFile(path).read(columns=["videos"]).to_pylist()
    values = [str(row["videos"]) for row in rows]
    return set(map(parse_video_id, values)), {
        "row_count": len(values),
        "columns_read": ["videos"],
        "allowed_column_content_sha256": canonical_sha256(values),
    }


def load_video_index(index_dir: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(index_dir.glob("index_shard*of4.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            video_id = str(row.get("video_id", ""))
            if not video_id or video_id in records:
                raise SplitError(f"duplicate or missing video index id: {video_id}")
            records[video_id] = row
    if not records:
        raise SplitError("video index is empty")
    return records


def group_sft_by_video(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["video"]].append(row)
    for video_id, items in groups.items():
        if len(items) != 5:
            raise SplitError(f"SFT video {video_id} has {len(items)} questions instead of five")
        categories = {item["category"] for item in items}
        if len(categories) != 1:
            raise SplitError(f"SFT video {video_id} has inconsistent categories")
    return groups


def stratified_quotas(video_categories: Counter[str], requested: int) -> dict[str, int]:
    available = sum(video_categories.values())
    if requested <= 0 or requested > available:
        raise SplitError(f"selected-video-count must be in [1, {available}]")
    raw = {category: count * requested / available for category, count in video_categories.items()}
    quotas = {category: int(value) for category, value in raw.items()}
    remaining = requested - sum(quotas.values())
    order = sorted(
        video_categories,
        key=lambda category: (-(raw[category] - quotas[category]), category),
    )
    for category in order[:remaining]:
        quotas[category] += 1
    for category, quota in quotas.items():
        if quota > video_categories[category]:
            raise SplitError(f"quota exceeds available videos for category {category}")
    return quotas


def select_videos(
    groups: dict[str, list[dict[str, Any]]],
    requested: int,
    seed: str,
) -> tuple[list[str], dict[str, int]]:
    by_category: dict[str, list[str]] = defaultdict(list)
    for video_id, items in groups.items():
        by_category[items[0]["category"]].append(video_id)
    available = Counter({category: len(video_ids) for category, video_ids in by_category.items()})
    quotas = stratified_quotas(available, requested)
    selected: list[str] = []
    for category in sorted(by_category):
        ranked = sorted(
            by_category[category],
            key=lambda video_id: hashlib.sha256(f"{seed}:{category}:{video_id}".encode("utf-8")).hexdigest(),
        )
        selected.extend(ranked[: quotas[category]])
    if len(selected) != requested or len(set(selected)) != requested:
        raise SplitError("stratified selection count is invalid")
    return sorted(selected), quotas


def assert_answer_free(records: list[dict[str, Any]]) -> None:
    for record in records:
        forbidden = FORBIDDEN_KEYS & set(record)
        if forbidden:
            raise SplitError(f"output contains forbidden fields: {sorted(forbidden)}")
        if record.get("answer_free") is not True:
            raise SplitError("output must explicitly certify answer_free=true")


def main() -> None:
    args = parse_args()
    sft_path = Path(args.sft_parquet).resolve()
    test_path = Path(args.test_parquet).resolve()
    index_dir = Path(args.video_index_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    check_output_dir(output_dir, args.overwrite)

    sft_rows, sft_provenance = load_sft_rows(sft_path)
    test_video_ids, test_provenance = load_test_video_ids(test_path)
    video_index = load_video_index(index_dir)
    groups = group_sft_by_video(sft_rows)
    sft_total_video_count = len(groups)
    excluded_videos: set[str] = set()
    if args.exclude_questions:
        excluded_rows = json.loads(
            Path(args.exclude_questions).read_text(encoding="utf-8")
        )
        if (
            not isinstance(excluded_rows, list)
            or any(FORBIDDEN_KEYS & set(row) for row in excluded_rows)
        ):
            raise SplitError("excluded questions are not answer-free")
        excluded_videos = {str(row["video"]) for row in excluded_rows}
        groups = {
            video_id: items
            for video_id, items in groups.items()
            if video_id not in excluded_videos
        }
    selected_videos, quotas = select_videos(groups, args.selected_video_count, args.selection_seed)
    if args.fold_count < 0 or (
        args.fold_count
        and args.selected_video_count % args.fold_count
    ):
        raise SplitError("fold-count must evenly divide selected-video-count")
    fold_by_video = {
        video_id: index % args.fold_count
        for index, video_id in enumerate(selected_videos)
    } if args.fold_count else {}
    overlap = sorted(set(selected_videos) & test_video_ids)
    if overlap:
        raise SplitError(f"selected videos overlap E-VAds Test: {overlap[:5]}")

    missing_index = []
    for video_id in selected_videos:
        record = video_index.get(video_id)
        if record is None:
            missing_index.append(video_id)
            continue
        if len(record.get("candidate_frame_indices", [])) != 64:
            raise SplitError(f"video {video_id} does not have 64 candidate frames")
        if len(record.get("baseline_frame_indices", [])) != 32:
            raise SplitError(f"video {video_id} does not have 32 Raw baseline frames")
    if missing_index:
        raise SplitError(f"selected videos missing frame index: {missing_index[:5]}")

    questions: list[dict[str, Any]] = []
    selection: list[dict[str, Any]] = []
    for video_id in selected_videos:
        items = sorted(groups[video_id], key=lambda item: item["question_id"])
        selection.append(
            {
                "video": video_id,
                "category": items[0]["category"],
                "question_ids": [item["question_id"] for item in items],
            }
        )
        for slot, item in enumerate(items):
            question = {
                "schema_version": "evads_sft_dev_answer_free_questions_v1",
                "question_id": item["question_id"],
                "video": video_id,
                "question": item["question"],
                "official_prompt_text": item["official_prompt_text"],
                "multimodal_context": extract_multimodal_context(
                    item["official_prompt_text"],
                    item["question"],
                ),
                "ability": item["ability"],
                "category": item["category"],
                "split": args.split_name,
                "dev_stage": args.dev_stage,
                "task_slot_within_video": slot,
                "answer_free": True,
                "prompt_sha256": hashlib.sha256(
                    item["official_prompt_text"].encode("utf-8")
                ).hexdigest(),
            }
            if args.fold_count:
                question["fold"] = fold_by_video[video_id]
            questions.append(question)
    assert_answer_free(questions)
    if len(questions) != args.selected_video_count * 5:
        raise SplitError("question count does not match five questions per selected video")

    question_path = output_dir / "questions_answer_free.json"
    selection_path = output_dir / "selection.json"
    audit_path = output_dir / "audit.json"
    manifest_path = output_dir / "manifest.json"
    write_json(question_path, questions)
    write_json(selection_path, selection)
    fold_hashes = {}
    if args.fold_count:
        for fold in range(args.fold_count):
            path = output_dir / "a0_shards" / f"fold_{fold}.json"
            write_json(
                path,
                [row for row in questions if int(row["fold"]) == fold],
            )
            fold_hashes[str(path.relative_to(output_dir))] = sha256_file(path)
    fold_counts = Counter(int(row["fold"]) for row in questions)
    audit = {
        "schema_version": "evads_sft_dev_answer_free_audit_v1",
        "passed": (
            len(selected_videos) == args.selected_video_count
            and len(questions) == args.selected_video_count * 5
            and not overlap
            and not (set(selected_videos) & excluded_videos)
            and (
                not args.fold_count
                or fold_counts
                == Counter({
                    fold: len(questions) // args.fold_count
                    for fold in range(args.fold_count)
                })
            )
        ),
        "split": args.split_name,
        "selected_video_count": len(selected_videos),
        "selected_question_count": len(questions),
        "questions_per_selected_video": 5,
        "sft_total_video_count": sft_total_video_count,
        "excluded_video_count": len(excluded_videos),
        "eligible_sft_video_count": len(groups),
        "selected_excluded_video_overlap_count": len(
            set(selected_videos) & excluded_videos
        ),
        "test_video_count": len(test_video_ids),
        "selected_test_video_overlap_count": len(overlap),
        "selected_video_index_coverage": len(selected_videos),
        "category_quotas": quotas,
        "selected_category_counts": dict(
            sorted(Counter(item["category"] for item in selection).items())
        ),
        "answer_or_outcome_fields_used": False,
        "forbidden_input_keys": sorted(FORBIDDEN_KEYS),
        "sft_provenance": sft_provenance,
        "test_provenance": test_provenance,
        "selection_seed": args.selection_seed,
        "fold_count": args.fold_count,
        "questions_per_fold": dict(sorted(fold_counts.items()))
        if args.fold_count
        else {},
        "fold_files_sha256": fold_hashes,
    }
    write_json(audit_path, audit)
    manifest = {
        "schema_version": "evads_sft_dev_answer_free_manifest_v1",
        "questions_sha256": sha256_file(question_path),
        "selection_sha256": sha256_file(selection_path),
        "audit_sha256": sha256_file(audit_path),
        "question_count": len(questions),
        "video_count": len(selected_videos),
        "answer_or_outcome_fields_used": False,
        "fold_files_sha256": fold_hashes,
    }
    write_json(manifest_path, manifest)
    print(json.dumps({"output_dir": str(output_dir), "audit": audit, "manifest": manifest}, ensure_ascii=True))


if __name__ == "__main__":
    main()
