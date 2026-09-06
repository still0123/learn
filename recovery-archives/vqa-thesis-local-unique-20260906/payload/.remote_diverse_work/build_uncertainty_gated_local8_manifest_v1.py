#!/usr/bin/env python3
"""Build an answer-free uncertainty-gated Shared32+Local8 manifest.

The selector reuses frozen 32-frame CLIP candidates.  It estimates temporal
uncertainty from adjacent candidate responses and changes at most two of the
baseline Local8 crops, only when the baseline tail is both crowded and
unstable.  No answer, label, or judge output is read.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, pstdev


COUNT = 8
RAW_COUNT = 32
MAX_REPLACEMENTS = 2
MARGIN_THRESHOLD = 0.05
MAX_SPAN_BINS = 4
MAX_ADJACENT_PAIRS = 4
NEIGHBOR_RADIUS = 2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized_scores(candidates: list[dict]) -> dict[int, float]:
    values = [float(row["global_response"]) for row in candidates]
    low, high = min(values), max(values)
    scale = high - low
    return {
        int(row["source_global_rank"]): ((float(row["global_response"]) - low) / scale if scale > 1e-8 else 1.0)
        for row in candidates
    }


def uncertainty_scores(candidates: list[dict]) -> tuple[dict[int, float], dict[int, float], dict[int, float]]:
    scores = normalized_scores(candidates)
    by_rank = {int(row["source_global_rank"]): row for row in candidates}
    robust: dict[int, float] = {}
    sigma: dict[int, float] = {}
    for rank in sorted(by_rank):
        neighborhood = [scores[r] for r in range(max(0, rank - NEIGHBOR_RADIUS), min(RAW_COUNT, rank + NEIGHBOR_RADIUS + 1)) if r in scores]
        sigma[rank] = pstdev(neighborhood) if len(neighborhood) > 1 else 0.0
        robust[rank] = mean(neighborhood) - sigma[rank]
    return scores, robust, sigma


def select(candidates: list[dict], baseline: list[dict]) -> tuple[list[dict], dict]:
    if len(candidates) != RAW_COUNT or len(baseline) != COUNT:
        raise ValueError("expected 32 candidates and 8 baseline crops")
    scores, robust, sigma = uncertainty_scores(candidates)
    by_rank = {int(row["source_global_rank"]): row for row in candidates}
    baseline_ranks = [int(row["source_global_rank"]) for row in baseline]
    ranked = sorted(scores, key=lambda rank: (-scores[rank], rank))
    top8 = ranked[:COUNT]
    rank8, rank9 = scores[top8[-1]], scores[ranked[COUNT]]
    margin = (rank8 - rank9) / max(abs(rank8), 1e-8)
    span_bins = max(top8) - min(top8)
    adjacent_pairs = sum(abs(top8[i] - top8[i - 1]) <= 1 for i in range(1, len(top8)))
    gate = margin <= MARGIN_THRESHOLD and (span_bins <= MAX_SPAN_BINS or adjacent_pairs >= MAX_ADJACENT_PAIRS)
    selected = list(baseline_ranks)
    replacements: list[dict] = []
    if gate:
        baseline_set = set(selected)
        # Replace only redundant, low-robustness members; preserve the strongest
        # baseline evidence and the highest-scoring temporal neighbor.
        protected = {max(selected, key=lambda rank: (scores.get(rank, 0.0), -rank))}
        for rank in selected:
            if rank in protected:
                continue
            near_selected = sum(abs(rank - other) <= 1 for other in selected if other != rank)
            if near_selected == 0:
                continue
            candidates_outside = [r for r in ranked if r not in baseline_set and r not in selected]
            if not candidates_outside:
                break
            replacement = max(
                candidates_outside,
                key=lambda r: (robust[r], scores[r], -abs(r - rank), -r),
            )
            if robust[replacement] + 0.02 < robust[rank]:
                continue
            selected[selected.index(rank)] = replacement
            baseline_set.add(replacement)
            replacements.append({
                "removed_rank": rank,
                "added_rank": replacement,
                "removed_robust": robust[rank],
                "added_robust": robust[replacement],
                "removed_sigma": sigma[rank],
                "added_sigma": sigma[replacement],
            })
            if len(replacements) >= MAX_REPLACEMENTS:
                break
    output = []
    for selection_rank, rank in enumerate(selected):
        item = copy.deepcopy(by_rank[rank])
        item["crop_mode"] = "uncertainty_gated_local8_v1"
        item["selection_rank"] = selection_rank
        item["robust_response"] = robust[rank]
        item["response_uncertainty"] = sigma[rank]
        output.append(item)
    decision = {
        "method": "uncertainty_gated_local8_v1",
        "candidate_count": RAW_COUNT,
        "selected_count": COUNT,
        "baseline_ranks": baseline_ranks,
        "selected_ranks": selected,
        "rank_margin_top8_top9": margin,
        "top8_span_bins": span_bins,
        "top8_adjacent_pairs": adjacent_pairs,
        "gate_activated": gate,
        "max_replacements": MAX_REPLACEMENTS,
        "replacements": replacements,
    }
    return output, decision


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-gate", required=True)
    parser.add_argument("--raw-features", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    base_path, raw_path, output_path = map(lambda value: Path(value).resolve(), (args.base_gate, args.raw_features, args.output))
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"output exists: {output_path}")
    base_by_id = {str(row["question_id"]): row for row in rows(base_path)}
    raw_by_id = {str(row["question_id"]): row for row in rows(raw_path)}
    if set(base_by_id) != set(raw_by_id):
        raise SystemExit("base gate and raw feature question IDs differ")
    output_rows = []
    decisions = []
    for question_id in sorted(base_by_id, key=lambda value: int(value)):
        base = copy.deepcopy(base_by_id[question_id])
        raw = raw_by_id[question_id]
        selected, decision = select(raw["clip_candidate_specs"], raw["clip_crop_specs"])
        base["clip_crop_specs"] = selected
        base["schema_version"] = "qwen25_shared32_uncertainty_gated_local8_v1"
        base["uncertainty_selection"] = decision
        base["manifest_inputs"]["raw_features_sha256"] = sha256_file(raw_path)
        base["gate_decision"]["method"] = "uncertainty_gated_local8_v1"
        output_rows.append(base)
        decisions.append(decision)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in output_rows), encoding="utf-8")
    audit = {
        "schema_version": "qwen25_shared32_uncertainty_gated_local8_manifest_audit_v1",
        "passed": len(output_rows) == len(base_by_id) and all(len(row["clip_crop_specs"]) == COUNT for row in output_rows),
        "record_count": len(output_rows),
        "candidate_count": RAW_COUNT,
        "selected_count": COUNT,
        "activated_count": sum(bool(item["gate_activated"]) for item in decisions),
        "changed_question_count": sum(item["baseline_ranks"] != item["selected_ranks"] for item in decisions),
        "replacement_count": sum(len(item["replacements"]) for item in decisions),
        "base_gate_sha256": sha256_file(base_path),
        "raw_features_sha256": sha256_file(raw_path),
        "output_manifest_sha256": sha256_file(output_path),
        "not_human_gold": True,
        "policy": {
            "margin_threshold": MARGIN_THRESHOLD,
            "max_span_bins": MAX_SPAN_BINS,
            "max_adjacent_pairs": MAX_ADJACENT_PAIRS,
            "max_replacements": MAX_REPLACEMENTS,
            "neighbor_radius": NEIGHBOR_RADIUS,
        },
    }
    output_path.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    output_path.with_suffix(".decisions.jsonl").write_text("".join(json.dumps(item, ensure_ascii=True) + "\n" for item in decisions), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
