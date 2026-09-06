#!/usr/bin/env python3
"""Materialize the frozen AdaptiveScale-only full-threshold evidence arm."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "ground_truth",
    "reference_answer",
    "judge_score",
    "label",
    "meta_info",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--smoke-per-fold", type=int, default=2)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError("output root already exists")
    rows = load_jsonl(args.input_jsonl)
    if (
        len(rows) != 4905
        or len({str(row["question_id"]) for row in rows}) != 4905
        or Counter(int(row["fold"]) for row in rows)
        != Counter({0: 818, 1: 818, 2: 818, 3: 817, 4: 817, 5: 817})
        or any(FORBIDDEN & set(row) for row in rows)
    ):
        raise RuntimeError("expected answer-free 4905-row threshold trigger set")
    transformed = []
    for source in rows:
        row = json.loads(json.dumps(source))
        row["crop_ablation_variant"] = "adaptive_scale"
        for anchor in row["evidence_anchors"]:
            anchor["adaptive_bbox_norm"] = [
                float(value) for value in anchor["bbox_norm"]
            ]
            anchor["adaptive_entropy_proxy"] = float(anchor["entropy_proxy"])
            anchor["crop_mode"] = (
                "adaptive_response_center_entropy_scale_v1"
            )
        transformed.append(row)

    args.output_root.mkdir(parents=True, exist_ok=False)
    files = {}
    for fold in range(6):
        fold_rows = [
            row for row in transformed if int(row["fold"]) == fold
        ]
        full_path = (
            args.output_root / "full4905" / "adaptive_scale" / "shards"
            / f"fold_{fold}.jsonl"
        )
        smoke_path = (
            args.output_root / "smoke10" / "adaptive_scale" / "shards"
            / f"fold_{fold}.jsonl"
        )
        write_jsonl(full_path, fold_rows)
        write_jsonl(smoke_path, fold_rows[: args.smoke_per_fold])
        files[str(full_path.relative_to(args.output_root))] = sha256_file(
            full_path
        )
        files[str(smoke_path.relative_to(args.output_root))] = sha256_file(
            smoke_path
        )
    audit = {
        "schema_version": "qwen3_adaptive_scale_full_threshold4905_arms_audit_v1",
        "passed": True,
        "source_rows": len(rows),
        "variant": "adaptive_scale",
        "full_rows": 4905,
        "full_fold_counts": {
            str(fold): sum(int(row["fold"]) == fold for row in transformed)
            for fold in range(6)
        },
        "smoke_rows": args.smoke_per_fold * 6,
        "anchors_per_question": 2,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "files_sha256": files,
    }
    (args.output_root / "dataset_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
