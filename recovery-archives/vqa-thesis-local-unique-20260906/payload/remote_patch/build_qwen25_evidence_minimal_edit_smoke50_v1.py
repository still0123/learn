#!/usr/bin/env python3
"""Build a deterministic answer-free Qwen2.5 minimal-edit Smoke-50."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "ground_truth",
    "reference_answer",
    "meta_info",
    "judge_score",
    "label",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    items = load_jsonl(args.items)
    scores = load_jsonl(args.scores)
    if len(items) != 500 or len(scores) != 500:
        raise RuntimeError("expected complete OOF-500 inputs and scores")
    item_map = {str(row["question_id"]): row for row in items}
    score_map = {
        str(row["source_question_id"]): float(row["support_probability"])
        for row in scores
    }
    if len(item_map) != 500 or set(item_map) != set(score_map):
        raise RuntimeError("item and support score IDs do not align")
    if any(FORBIDDEN & set(row) for row in items):
        raise RuntimeError("answer-free source contains a forbidden field")

    selected: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for fold in range(5):
        candidates = sorted(
            (
                row for row in items
                if int(row["fold"]) == fold
            ),
            key=lambda row: (
                score_map[str(row["question_id"])],
                str(row["question_id"]),
            ),
        )
        seen_videos: set[str] = set()
        fold_rows: list[dict[str, Any]] = []
        for row in candidates:
            video_id = str(row["video_id"])
            if video_id in seen_videos:
                continue
            seen_videos.add(video_id)
            fold_rows.append(row)
            if len(fold_rows) == 10:
                break
        if len(fold_rows) != 10:
            raise RuntimeError(f"fold {fold} lacks ten unique-video candidates")
        for rank, row in enumerate(fold_rows, 1):
            qid = str(row["question_id"])
            selected.append(row)
            manifest.append({
                "question_id": qid,
                "video_id": str(row["video_id"]),
                "fold": fold,
                "fold_support_rank": rank,
                "a0_support_probability": score_map[qid],
                "selection_fields": [
                    "fold",
                    "video_id",
                    "a0_support_probability",
                    "question_id",
                ],
            })
        write_jsonl(
            args.output_dir / "shards" / f"fold_{fold}.jsonl",
            fold_rows,
        )

    selected.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    manifest.sort(key=lambda row: (int(row["fold"]), int(row["fold_support_rank"])))
    write_jsonl(args.output_dir / "items_answer_free.jsonl", selected)
    write_jsonl(args.output_dir / "selection_manifest.jsonl", manifest)
    audit = {
        "schema_version": "qwen25_evidence_minimal_edit_smoke50_audit_v1",
        "question_count": len(selected),
        "video_count": len({str(row["video_id"]) for row in selected}),
        "fold_counts": {
            str(fold): sum(int(row["fold"]) == fold for row in selected)
            for fold in range(5)
        },
        "unique_video_per_selected_question": True,
        "selection_mode": "ten_lowest_a0_support_unique_videos_per_fold",
        "selection_uses_only_answer_free_support": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "external_knowledge_used": False,
        "forbidden_fields_present": False,
        "source_items_sha256": sha256_file(args.items),
        "source_scores_sha256": sha256_file(args.scores),
        "items_sha256": sha256_file(args.output_dir / "items_answer_free.jsonl"),
        "manifest_sha256": sha256_file(
            args.output_dir / "selection_manifest.jsonl"
        ),
        "passed": (
            len(selected) == 50
            and len({str(row["video_id"]) for row in selected}) == 50
            and all(
                sum(int(row["fold"]) == fold for row in selected) == 10
                for fold in range(5)
            )
        ),
    }
    write_json(args.output_dir / "audit.json", audit)
    if not audit["passed"]:
        raise RuntimeError("Smoke-50 audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
