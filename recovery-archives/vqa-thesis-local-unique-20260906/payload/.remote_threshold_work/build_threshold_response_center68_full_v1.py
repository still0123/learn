#!/usr/bin/env python3
"""Build answer-free ResponseCenter68 inputs for the frozen threshold4905 set."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_SIDE = 0.68
FOLDS = tuple(range(6))
EXPECTED_FOLD_COUNTS = Counter({0: 818, 1: 818, 2: 818, 3: 817, 4: 817, 5: 817})
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
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def square_box(center_x: float, center_y: float) -> list[float]:
    left = min(max(center_x - FIXED_SIDE / 2.0, 0.0), 1.0 - FIXED_SIDE)
    top = min(max(center_y - FIXED_SIDE / 2.0, 0.0), 1.0 - FIXED_SIDE)
    return [left, top, left + FIXED_SIDE, top + FIXED_SIDE]


def transform(source: dict[str, Any]) -> dict[str, Any]:
    row = json.loads(json.dumps(source))
    row["ablation_variant"] = "response_center68"
    for anchor in row["evidence_anchors"]:
        adaptive = [float(value) for value in anchor["bbox_norm"]]
        center_x = (adaptive[0] + adaptive[2]) / 2.0
        center_y = (adaptive[1] + adaptive[3]) / 2.0
        anchor["adaptive_bbox_norm"] = adaptive
        anchor["adaptive_entropy_proxy"] = float(anchor["entropy_proxy"])
        anchor["bbox_norm"] = square_box(center_x, center_y)
        anchor["bbox_source"] = "frozen_response_center_side068_control_v1"
        anchor["crop_mode"] = "response_center68"
        anchor["fixed_crop_side"] = FIXED_SIDE
    return row


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_root}")
    source_rows = load_jsonl(args.input_jsonl)
    source_ids = [str(row.get("question_id", "")) for row in source_rows]
    if (
        len(source_rows) != 4905
        or len(set(source_ids)) != 4905
        or Counter(int(row["fold"]) for row in source_rows) != EXPECTED_FOLD_COUNTS
        or any(FORBIDDEN & set(row) for row in source_rows)
        or any(len(row.get("evidence_anchors", [])) != 2 for row in source_rows)
    ):
        raise RuntimeError("expected frozen answer-free threshold4905 source inputs")

    rows = [transform(row) for row in source_rows]
    args.output_root.mkdir(parents=True, exist_ok=False)
    files: dict[str, str] = {}
    for fold in FOLDS:
        shard = [row for row in rows if int(row["fold"]) == fold]
        if len(shard) != EXPECTED_FOLD_COUNTS[fold]:
            raise RuntimeError(f"invalid fold {fold} count")
        path = args.output_root / "full4905" / "shards" / f"fold_{fold}.jsonl"
        write_jsonl(path, shard)
        files[str(path.relative_to(args.output_root))] = sha256_file(path)

    smoke_path = args.output_root / "smoke1.jsonl"
    write_jsonl(smoke_path, [rows[0]])
    files[str(smoke_path.relative_to(args.output_root))] = sha256_file(smoke_path)
    audit = {
        "schema_version": "threshold4905_response_center68_dataset_v1",
        "passed": True,
        "analysis_role": "posthoc_mechanism_attribution",
        "source_rows": len(source_rows),
        "source_input_sha256": sha256_file(args.input_jsonl),
        "fold_counts": {
            str(fold): EXPECTED_FOLD_COUNTS[fold] for fold in FOLDS
        },
        "variant": "response_center68",
        "fixed_side": FIXED_SIDE,
        "same_trigger_set": True,
        "same_evidence_anchors": True,
        "same_response_centers": True,
        "only_changed": "adaptive_entropy_scale_to_fixed_side_0.68",
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
