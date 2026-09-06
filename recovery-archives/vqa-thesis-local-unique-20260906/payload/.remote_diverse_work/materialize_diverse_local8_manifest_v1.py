#!/usr/bin/env python3
"""Create an answer-free temporal-diverse eight-crop manifest from 32 CLIP candidates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any


LAMBDA = 0.35
TEMPORAL_SIGMA = 2.0
COUNT = 8
RAW_COUNT = 32


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_temporal_diverse(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(candidates) != RAW_COUNT:
        raise ValueError(f"expected {RAW_COUNT} candidates, got {len(candidates)}")
    scores = [float(row["global_response"]) for row in candidates]
    low, high = min(scores), max(scores)
    scale = high - low
    normalized = {
        int(row["source_global_rank"]): ((float(row["global_response"]) - low) / scale if scale > 1e-8 else 1.0)
        for row in candidates
    }
    by_rank = {int(row["source_global_rank"]): row for row in candidates}
    selected = [max(normalized, key=lambda rank: (normalized[rank], -rank))]
    while len(selected) < COUNT:
        remaining = [rank for rank in normalized if rank not in selected]
        best = max(
            remaining,
            key=lambda rank: (
                normalized[rank]
                - LAMBDA
                * max(
                    math.exp(-abs(rank - chosen) / TEMPORAL_SIGMA)
                    for chosen in selected
                ),
                normalized[rank],
                -rank,
            ),
        )
        selected.append(best)
    return [
        {
            **copy.deepcopy(by_rank[rank]),
            "crop_mode": "clip_temporal_diverse_v1",
            "selection_rank": index,
        }
        for index, rank in enumerate(selected)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", required=True)
    parser.add_argument("--candidate-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    base_path = Path(args.base_manifest).resolve()
    candidate_path = Path(args.candidate_manifest).resolve()
    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"output exists: {output_path}")
    base_rows = [json.loads(line) for line in base_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidate_rows = [json.loads(line) for line in candidate_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidates_by_id = {str(row["question_id"]): row for row in candidate_rows}
    if len(candidates_by_id) != len(candidate_rows):
        raise SystemExit("duplicate candidate question_id")
    output_rows = []
    selection_stats = []
    for base in base_rows:
        question_id = str(base["question_id"])
        source = candidates_by_id.get(question_id)
        if source is None:
            raise SystemExit(f"missing candidate row for {question_id}")
        candidates = source.get("clip_candidate_specs")
        if not isinstance(candidates, list):
            raise SystemExit(f"{question_id} has no 32-frame candidate list")
        diverse = select_temporal_diverse(candidates)
        row = copy.deepcopy(base)
        original = [int(item["source_global_rank"]) for item in row["clip_crop_specs"]]
        selected = [int(item["source_global_rank"]) for item in diverse]
        row["clip_crop_specs"] = diverse
        row["diverse_selection"] = {
            "enabled": True,
            "method": "temporal_mmr_v1",
            "candidate_count": RAW_COUNT,
            "selected_count": COUNT,
            "lambda": LAMBDA,
            "temporal_sigma": TEMPORAL_SIGMA,
            "baseline_top8_ranks": original,
            "selected_ranks": selected,
            "mean_selected_rank_gap": sum(abs(selected[index] - selected[index - 1]) for index in range(1, len(selected))) / (len(selected) - 1),
        }
        row["schema_version"] = "qwen25_shared32_diverse_local8_gate_manifest_v1"
        output_rows.append(row)
        selection_stats.append({"question_id": question_id, "baseline": original, "selected": selected})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in output_rows), encoding="utf-8")
    audit = {
        "schema_version": "qwen25_shared32_diverse_local8_manifest_audit_v1",
        "passed": len(output_rows) == len(base_rows) and all(len(row["clip_crop_specs"]) == COUNT for row in output_rows),
        "record_count": len(output_rows),
        "candidate_record_count": len(candidate_rows),
        "base_manifest_sha256": sha256_file(base_path),
        "candidate_manifest_sha256": sha256_file(candidate_path),
        "output_manifest_sha256": sha256_file(output_path),
        "selection_policy": {"method": "temporal_mmr_v1", "lambda": LAMBDA, "temporal_sigma": TEMPORAL_SIGMA},
        "answer_or_outcome_fields_used": False,
        "not_human_gold": True,
        "changed_question_count": sum(item["baseline"] != item["selected"] for item in selection_stats),
    }
    output_path.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
