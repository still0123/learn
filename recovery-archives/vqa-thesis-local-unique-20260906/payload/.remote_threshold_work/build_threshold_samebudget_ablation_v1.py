#!/usr/bin/env python3
"""Build answer-free same-budget component-ablation smoke shards."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


VARIANTS = ("extra_global", "no_ocr", "no_asr")
FORBIDDEN = {
    "answer", "ground_truth", "reference_answer", "judge_score", "label", "meta_info",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--smoke-per-fold", type=int, default=4)
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
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.output_root.exists() or args.smoke_per_fold <= 0:
        raise RuntimeError("output root exists or smoke size is invalid")
    rows = load_jsonl(args.input_jsonl)
    expected_folds = Counter({0: 818, 1: 818, 2: 818, 3: 817, 4: 817, 5: 817})
    if (
        len(rows) != 4905
        or len({str(row["question_id"]) for row in rows}) != 4905
        or Counter(int(row["fold"]) for row in rows) != expected_folds
        or any(FORBIDDEN & set(row) for row in rows)
        or any(len(row.get("evidence_anchors", [])) != 2 for row in rows)
    ):
        raise RuntimeError("expected answer-free threshold4905 source rows")
    args.output_root.mkdir(parents=True, exist_ok=False)
    files: dict[str, str] = {}
    selected_ids: set[str] = set()
    for variant in VARIANTS:
        variant_rows = []
        for fold in range(6):
            fold_rows = [row for row in rows if int(row["fold"]) == fold]
            selected = []
            for source in fold_rows[: args.smoke_per_fold]:
                row = json.loads(json.dumps(source))
                row["ablation_variant"] = variant
                selected.append(row)
                selected_ids.add(str(row["question_id"]))
                variant_rows.append(row)
            path = args.output_root / "smoke24" / variant / "shards" / f"fold_{fold}.jsonl"
            write_jsonl(path, selected)
            files[str(path.relative_to(args.output_root))] = sha256_file(path)
        combined_path = args.output_root / "smoke24" / variant / "items.jsonl"
        write_jsonl(combined_path, variant_rows)
        files[str(combined_path.relative_to(args.output_root))] = sha256_file(combined_path)
    audit = {
        "schema_version": "threshold4905_samebudget_ablation_smoke_v1",
        "passed": True,
        "analysis_role": "posthoc_mechanism_attribution",
        "source_rows": len(rows),
        "variants": list(VARIANTS),
        "smoke_per_variant": args.smoke_per_fold * 6,
        "smoke_unique_question_count": len(selected_ids),
        "same_trigger_set": True,
        "same_evidence_anchors": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "files_sha256": files,
    }
    (args.output_root / "dataset_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
