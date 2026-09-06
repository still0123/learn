#!/usr/bin/env python3
"""Build answer-free full same-budget ablation inputs by source fold."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


VARIANTS = ("extra_global", "no_ocr", "no_asr")
FOLDS = tuple(range(6))
EXPECTED_FOLD_COUNTS = Counter({0: 818, 1: 818, 2: 818, 3: 817, 4: 817, 5: 817})
FORBIDDEN = {"answer", "ground_truth", "reference_answer", "judge_score", "label", "meta_info"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_root}")
    rows = load_jsonl(args.input_jsonl)
    source_ids = [str(row.get("question_id", "")) for row in rows]
    if (
        len(rows) != 4905
        or len(set(source_ids)) != 4905
        or Counter(int(row["fold"]) for row in rows) != EXPECTED_FOLD_COUNTS
        or any(FORBIDDEN & set(row) for row in rows)
        or any(len(row.get("evidence_anchors", [])) != 2 for row in rows)
    ):
        raise RuntimeError("expected answer-free threshold4905 source inputs with two anchors")

    args.output_root.mkdir(parents=True, exist_ok=False)
    files: dict[str, str] = {}
    for variant in VARIANTS:
        for fold in FOLDS:
            shard = []
            for source in rows:
                if int(source["fold"]) != fold:
                    continue
                row = json.loads(json.dumps(source))
                row["ablation_variant"] = variant
                shard.append(row)
            if len(shard) != EXPECTED_FOLD_COUNTS[fold]:
                raise RuntimeError(f"invalid {variant} fold {fold} count")
            path = args.output_root / "full4905" / variant / "shards" / f"fold_{fold}.jsonl"
            write_jsonl(path, shard)
            files[str(path.relative_to(args.output_root))] = sha256_file(path)

    audit = {
        "schema_version": "threshold4905_samebudget_ablation_full_dataset_v1",
        "passed": True,
        "analysis_role": "posthoc_mechanism_attribution",
        "source_rows": len(rows),
        "source_input_sha256": sha256_file(args.input_jsonl),
        "fold_counts": {str(fold): EXPECTED_FOLD_COUNTS[fold] for fold in FOLDS},
        "variants": list(VARIANTS),
        "same_trigger_set": True,
        "same_evidence_anchors": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "files_sha256": files,
    }
    (args.output_root / "dataset_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
