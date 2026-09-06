#!/usr/bin/env python3
"""Build a frozen, method-specific AdsQA Confirm-1000 split."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable


PRIMARY_TYPES = tuple(f"Type_{index}" for index in range(1, 6))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_rank(seed: int, *parts: str) -> str:
    value = ":".join((str(seed),) + parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected a JSON list: {path}")
    return value


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return load_json_list(path)


def canonicalize_exact_duplicate_ids(
    rows: list[dict[str, Any]], label: str
) -> tuple[list[dict[str, Any]], int]:
    canonical = {}
    duplicate_count = 0
    for row in rows:
        question_id = str(row["question_id"])
        existing = canonical.get(question_id)
        if existing is None:
            canonical[question_id] = row
            continue
        if json.dumps(existing, ensure_ascii=False, sort_keys=True) != json.dumps(
            row, ensure_ascii=False, sort_keys=True
        ):
            raise ValueError(
                f"conflicting duplicate {label} question ID: {question_id}"
            )
        duplicate_count += 1
    return list(canonical.values()), duplicate_count


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


def dump_jsonl(
    path: Path, rows: Iterable[dict[str, Any]], mode: int | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(path)
    if mode is not None:
        os.chmod(path, mode)


def primary_types(row: dict[str, Any]) -> tuple[str, ...]:
    values = tuple(
        str(value)
        for value in row.get("question_type", [])
        if str(value) in PRIMARY_TYPES
    )
    if not values:
        raise ValueError(
            f"question has no recognized primary type: {row.get('question_id')}"
        )
    return values


def video_id(row: dict[str, Any]) -> str:
    value = row.get("video", row.get("video_id"))
    if value is None:
        raise ValueError("exclusion row lacks video/video_id")
    return str(value)


def indexed_video_ids(index_dir: Path) -> set[str]:
    result = set()
    for path in sorted(index_dir.glob("index_shard*.jsonl")):
        for row in load_rows(path):
            result.add(video_id(row))
    return result


class Dinic:
    def __init__(self, size: int) -> None:
        self.graph: list[list[list[int]]] = [[] for _ in range(size)]

    def add_edge(self, source: int, target: int, capacity: int) -> None:
        forward = [target, capacity, len(self.graph[target])]
        reverse = [source, 0, len(self.graph[source])]
        self.graph[source].append(forward)
        self.graph[target].append(reverse)

    def max_flow(self, source: int, sink: int) -> int:
        total = 0
        while True:
            level = [-1] * len(self.graph)
            level[source] = 0
            queue = deque([source])
            while queue:
                node = queue.popleft()
                for target, capacity, _ in self.graph[node]:
                    if capacity and level[target] < 0:
                        level[target] = level[node] + 1
                        queue.append(target)
            if level[sink] < 0:
                return total
            cursor = [0] * len(self.graph)

            def send(node: int, flow: int) -> int:
                if node == sink:
                    return flow
                while cursor[node] < len(self.graph[node]):
                    edge = self.graph[node][cursor[node]]
                    target, capacity, reverse_index = edge
                    if capacity and level[target] == level[node] + 1:
                        pushed = send(target, min(flow, capacity))
                        if pushed:
                            edge[1] -= pushed
                            self.graph[target][reverse_index][1] += pushed
                            return pushed
                    cursor[node] += 1
                return 0

            while True:
                pushed = send(source, 10**9)
                if not pushed:
                    break
                total += pushed


def assign_videos(
    eligible_types: dict[str, set[str]],
    per_type: int,
    seed: int,
) -> dict[str, list[str]]:
    videos = sorted(set().union(*eligible_types.values()))
    source = 0
    type_offset = 1
    video_offset = type_offset + len(PRIMARY_TYPES)
    sink = video_offset + len(videos)
    flow = Dinic(sink + 1)
    video_node = {
        value: video_offset + index for index, value in enumerate(videos)
    }
    for type_index, kind in enumerate(PRIMARY_TYPES):
        type_node = type_offset + type_index
        flow.add_edge(source, type_node, per_type)
        candidates = sorted(
            eligible_types[kind],
            key=lambda value: stable_rank(seed, "assign", kind, value),
        )
        for value in candidates:
            flow.add_edge(type_node, video_node[value], 1)
    for value in videos:
        flow.add_edge(video_node[value], sink, 1)
    required = per_type * len(PRIMARY_TYPES)
    achieved = flow.max_flow(source, sink)
    if achieved != required:
        raise RuntimeError(
            f"insufficient type-balanced unique-video flow: {achieved}/{required}"
        )
    assignment: dict[str, list[str]] = {}
    reverse_video = {node: value for value, node in video_node.items()}
    for type_index, kind in enumerate(PRIMARY_TYPES):
        type_node = type_offset + type_index
        selected = []
        for target, capacity, _ in flow.graph[type_node]:
            if target in reverse_video and capacity == 0:
                selected.append(reverse_video[target])
        if len(selected) != per_type:
            raise RuntimeError(
                f"assignment count mismatch for {kind}: {len(selected)}"
            )
        assignment[kind] = sorted(
            selected,
            key=lambda value: stable_rank(seed, "selected", kind, value),
        )
    return assignment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--video-index-dir", type=Path, required=True)
    parser.add_argument("--video-dir", type=Path, required=True)
    parser.add_argument("--clip-cache-dir", type=Path, required=True)
    parser.add_argument("--ocr-cache-dir", type=Path, required=True)
    parser.add_argument(
        "--existing-asr-dir", type=Path, action="append", default=[]
    )
    parser.add_argument(
        "--exclude-file", type=Path, action="append", default=[]
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-type", type=int, default=200)
    parser.add_argument("--num-shards", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260728)
    args = parser.parse_args()

    expected = args.per_type * len(PRIMARY_TYPES)
    if expected != 1000:
        raise ValueError("this frozen builder requires exactly 1000 questions")
    if args.num_shards <= 0 or args.per_type % args.num_shards:
        raise ValueError("per-type count must divide evenly across shards")
    if (args.output_root / "FROZEN").exists():
        raise RuntimeError(f"output is already frozen: {args.output_root}")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise RuntimeError(f"refusing to overwrite nonempty output: {args.output_root}")

    raw_questions = load_json_list(args.questions)
    raw_groundtruth = load_json_list(args.groundtruth)
    if len(raw_questions) != len(raw_groundtruth):
        raise ValueError("question and groundtruth source lengths differ")
    questions, duplicate_question_rows = canonicalize_exact_duplicate_ids(
        raw_questions, "question"
    )
    groundtruth, duplicate_groundtruth_rows = (
        canonicalize_exact_duplicate_ids(raw_groundtruth, "groundtruth")
    )
    if len(questions) != len(groundtruth):
        raise ValueError(
            "canonical question and groundtruth source lengths differ"
        )
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    for row in questions:
        question_id = str(row["question_id"])
        gt = gt_by_id.get(question_id)
        if gt is None or video_id(gt) != video_id(row):
            raise ValueError(f"question/groundtruth alignment failed: {question_id}")

    exclusion_records = []
    excluded_videos = set()
    excluded_questions = set()
    for path in args.exclude_file:
        rows = load_rows(path)
        file_videos = {video_id(row) for row in rows}
        file_questions = {
            str(row["question_id"])
            for row in rows
            if row.get("question_id") is not None
        }
        excluded_videos.update(file_videos)
        excluded_questions.update(file_questions)
        exclusion_records.append(
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
                "row_count": len(rows),
                "unique_video_count": len(file_videos),
                "unique_question_count": len(file_questions),
            }
        )

    indexed = indexed_video_ids(args.video_index_dir)
    by_video_type: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    skipped = Counter()
    candidate_videos = set()
    for source_index, row in enumerate(questions):
        question_id = str(row["question_id"])
        value = video_id(row)
        if question_id in excluded_questions:
            skipped["excluded_question"] += 1
            continue
        if value in excluded_videos:
            skipped["excluded_video"] += 1
            continue
        if value not in indexed:
            skipped["missing_video_index"] += 1
            continue
        if not (args.video_dir / f"{value}.mp4").is_file():
            skipped["missing_video"] += 1
            continue
        if not (args.clip_cache_dir / f"{value}.npz").is_file():
            skipped["missing_clip_cache"] += 1
            continue
        if not (args.ocr_cache_dir / f"{value}.json").is_file():
            skipped["missing_ocr_cache"] += 1
            continue
        if not str(gt_by_id[question_id].get("answer") or "").strip():
            skipped["invalid_empty_private_reference"] += 1
            continue
        candidate_videos.add(value)
        item = dict(row)
        item["_source_index"] = source_index
        for kind in primary_types(row):
            by_video_type[(value, kind)].append(item)

    eligible_types = {
        kind: {
            value
            for value in candidate_videos
            if (value, kind) in by_video_type
        }
        for kind in PRIMARY_TYPES
    }
    assignment = assign_videos(eligible_types, args.per_type, args.seed)

    selected = []
    for kind in PRIMARY_TYPES:
        for value in assignment[kind]:
            candidates = sorted(
                by_video_type[(value, kind)],
                key=lambda row: stable_rank(
                    args.seed, "question", kind, str(row["question_id"])
                ),
            )
            row = dict(candidates[0])
            row["_primary_type"] = kind
            selected.append(row)
    if len({video_id(row) for row in selected}) != expected:
        raise RuntimeError("selected videos are not globally unique")
    if len({str(row["question_id"]) for row in selected}) != expected:
        raise RuntimeError("selected question IDs are not unique")

    shards: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for kind in PRIMARY_TYPES:
        typed = sorted(
            [row for row in selected if row["_primary_type"] == kind],
            key=lambda row: stable_rank(
                args.seed, "shard", kind, str(row["question_id"])
            ),
        )
        for index, row in enumerate(typed):
            shards[index % args.num_shards].append(row)
    if any(len(rows) != expected // args.num_shards for rows in shards.values()):
        raise RuntimeError("shard sizes are not balanced")

    ordered = []
    selection_records = []
    for shard_id in range(args.num_shards):
        rows = sorted(
            shards[shard_id],
            key=lambda row: (
                PRIMARY_TYPES.index(row["_primary_type"]),
                stable_rank(args.seed, "order", str(row["question_id"])),
            ),
        )
        for row in rows:
            clean = {
                key: value
                for key, value in row.items()
                if not key.startswith("_")
            }
            clean["primary_type"] = row["_primary_type"]
            clean["confirm_shard"] = shard_id
            ordered.append(clean)
            selection_records.append(
                {
                    "question_id": str(row["question_id"]),
                    "video": video_id(row),
                    "primary_type": row["_primary_type"],
                    "confirm_shard": shard_id,
                    "source_index": int(row["_source_index"]),
                }
            )

    selected_ids = {str(row["question_id"]) for row in ordered}
    private_references = []
    for row in ordered:
        reference = dict(gt_by_id[str(row["question_id"])])
        if not str(reference.get("answer", "")).strip():
            raise RuntimeError(
                f"selected private reference has empty answer: {row['question_id']}"
            )
        private_references.append(reference)
    if {str(row["question_id"]) for row in private_references} != selected_ids:
        raise RuntimeError("private reference IDs do not match answer-free inputs")

    asr_coverage = {}
    for path in args.existing_asr_dir:
        covered = {
            video_id(row)
            for row in ordered
            if (path / f"{video_id(row)}.json").is_file()
        }
        asr_coverage[str(path.resolve())] = {
            "covered_selected_videos": len(covered),
            "missing_selected_videos": expected - len(covered),
        }

    answer_free_path = args.output_root / "questions_answer_free.json"
    selection_path = args.output_root / "selection_records_answer_free.jsonl"
    private_root = args.output_root / "private_references"
    private_path = private_root / "groundtruth.json"
    os.makedirs(private_root, mode=0o700, exist_ok=True)
    dump_json(answer_free_path, ordered)
    dump_jsonl(selection_path, selection_records)
    dump_json(private_path, private_references, mode=0o600)
    for shard_id in range(args.num_shards):
        shard_rows = [
            row for row in ordered if int(row["confirm_shard"]) == shard_id
        ]
        dump_json(
            args.output_root
            / "shards"
            / f"shard{shard_id}of{args.num_shards}.json",
            shard_rows,
        )

    selected_video_ids = {video_id(row) for row in ordered}
    type_counts = Counter(str(row["primary_type"]) for row in ordered)
    shard_counts = Counter(int(row["confirm_shard"]) for row in ordered)
    shard_type_counts = {
        str(shard_id): dict(
            Counter(
                str(row["primary_type"])
                for row in ordered
                if int(row["confirm_shard"]) == shard_id
            )
        )
        for shard_id in range(args.num_shards)
    }
    forbidden_keys = {
        "answer",
        "meta_info",
        "reference_answer",
        "golden_answer",
        "score",
        "judge_output",
        "label",
    }
    answer_free_leaks = sorted(
        {
            key
            for row in ordered
            for key in row
            if key.lower() in forbidden_keys
        }
    )
    audit = {
        "schema_version": "adsqa_qwen3_joint_confirm1000_audit_v1",
        "passed": all(
            (
                len(ordered) == expected,
                len(selected_ids) == expected,
                len(selected_video_ids) == expected,
                all(type_counts[kind] == args.per_type for kind in PRIMARY_TYPES),
                all(
                    shard_counts[index] == expected // args.num_shards
                    for index in range(args.num_shards)
                ),
                not answer_free_leaks,
                not (selected_video_ids & excluded_videos),
            )
        ),
        "count": len(ordered),
        "unique_questions": len(selected_ids),
        "unique_videos": len(selected_video_ids),
        "primary_type_counts": {
            kind: type_counts[kind] for kind in PRIMARY_TYPES
        },
        "shard_counts": dict(sorted(shard_counts.items())),
        "shard_type_counts": shard_type_counts,
        "answer_free_forbidden_keys": answer_free_leaks,
        "selected_excluded_video_overlap": len(
            selected_video_ids & excluded_videos
        ),
        "selected_excluded_question_overlap": len(
            selected_ids & excluded_questions
        ),
        "video_file_coverage": sum(
            (args.video_dir / f"{value}.mp4").is_file()
            for value in selected_video_ids
        ),
        "video_index_coverage": len(selected_video_ids & indexed),
        "clip_cache_coverage": sum(
            (args.clip_cache_dir / f"{value}.npz").is_file()
            for value in selected_video_ids
        ),
        "ocr_cache_coverage": sum(
            (args.ocr_cache_dir / f"{value}.json").is_file()
            for value in selected_video_ids
        ),
        "existing_segmented_asr_coverage": asr_coverage,
        "private_reference_count": len(private_references),
        "private_reference_nonempty_answer_count": sum(
            bool(str(row.get("answer", "")).strip())
            for row in private_references
        ),
        "eligible_unique_video_count": len(candidate_videos),
        "eligible_video_counts_by_type": {
            kind: len(eligible_types[kind]) for kind in PRIMARY_TYPES
        },
        "skipped_question_counts": dict(skipped),
        "source_raw_question_count": len(raw_questions),
        "source_canonical_question_count": len(questions),
        "source_exact_duplicate_question_rows_removed": (
            duplicate_question_rows
        ),
        "source_exact_duplicate_groundtruth_rows_removed": (
            duplicate_groundtruth_rows
        ),
        "selection_did_not_read": [
            "answer_semantics_or_content_except_nonempty_validity",
            "meta_info",
            "model_prediction",
            "judge_score",
            "support_probability",
        ],
        "boundary": (
            "method-specific frozen confirmation split; excludes every video "
            "used by the current joint method for training, calibration, "
            "development, or Confirm-D, but is not a globally untouched split "
            "with respect to unrelated historical experiments"
        ),
    }
    if audit["passed"] is not True:
        raise RuntimeError(f"final audit failed: {audit}")
    audit_path = args.output_root / "audit.json"
    dump_json(audit_path, audit)

    manifest = {
        "schema_version": "adsqa_qwen3_joint_confirm1000_manifest_v1",
        "status": "frozen_before_inference",
        "selection_policy": (
            "seeded_hash_type_balanced_global_unique_video_maxflow_v1"
        ),
        "seed": args.seed,
        "per_type": args.per_type,
        "num_shards": args.num_shards,
        "question_source": str(args.questions.resolve()),
        "question_source_sha256": sha256_file(args.questions),
        "groundtruth_source": str(args.groundtruth.resolve()),
        "groundtruth_source_sha256": sha256_file(args.groundtruth),
        "source_raw_row_count": len(raw_questions),
        "source_canonical_row_count": len(questions),
        "source_exact_duplicate_rows_removed": duplicate_question_rows,
        "video_index_dir": str(args.video_index_dir.resolve()),
        "excluded_video_count_total": len(excluded_videos),
        "excluded_video_count_in_question_source": len(
            excluded_videos
            & {video_id(row) for row in questions}
        ),
        "exclusions": exclusion_records,
        "answer_free_questions": str(answer_free_path.resolve()),
        "answer_free_questions_sha256": sha256_file(answer_free_path),
        "selection_records": str(selection_path.resolve()),
        "selection_records_sha256": sha256_file(selection_path),
        "private_references": str(private_path.resolve()),
        "private_references_sha256": sha256_file(private_path),
        "audit": str(audit_path.resolve()),
        "audit_sha256": sha256_file(audit_path),
        "shards": {
            str(index): {
                "path": str(
                    (
                        args.output_root
                        / "shards"
                        / f"shard{index}of{args.num_shards}.json"
                    ).resolve()
                ),
                "sha256": sha256_file(
                    args.output_root
                    / "shards"
                    / f"shard{index}of{args.num_shards}.json"
                ),
            }
            for index in range(args.num_shards)
        },
        "policy": (
            "single final frozen use; no threshold, prompt, trigger-rate, "
            "anchor, OCR/ASR, crop, or token-budget tuning on this split"
        ),
        "not_global_historical_blind": True,
        "answer_free_inputs_physically_separated_from_private_references": True,
    }
    manifest_path = args.output_root / "manifest.json"
    dump_json(manifest_path, manifest)
    frozen_hash = sha256_file(manifest_path)
    (args.output_root / "FROZEN").write_text(
        frozen_hash + "\n", encoding="ascii"
    )
    os.chmod(args.output_root / "FROZEN", 0o444)
    print(
        json.dumps(
            {
                "status": "frozen",
                "count": len(ordered),
                "unique_videos": len(selected_video_ids),
                "primary_type_counts": audit["primary_type_counts"],
                "shard_counts": audit["shard_counts"],
                "manifest": str(manifest_path),
                "manifest_sha256": frozen_hash,
                "audit_sha256": sha256_file(audit_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
