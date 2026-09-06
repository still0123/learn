#!/usr/bin/env python3
"""Prepare an answer-only paired judge manifest for AdaptiveScale12 vs ExtraGlobal12."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


METHODS = ("AdaptiveScale12", "ExtraGlobal12")
VALID_SCORES = {0.0, 0.5, 1.0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trigger-dataset", type=Path, required=True)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--extra-global-root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def collect_predictions(root: Path, expected_detail_type: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for prediction_path in sorted(root.glob("fold_*/*/a2_prediction.json")):
        trace_path = prediction_path.with_name("a2_trace.json")
        if not trace_path.is_file():
            raise RuntimeError(f"missing trace: {prediction_path}")
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        qid = str(prediction["question_id"])
        processor = trace.get("processor_trace", {})
        plan = trace.get("extra_view_plan", [])
        detail_types = [str(item.get("view_type")) for item in plan[1::2]]
        if (
            qid in rows
            or not str(prediction.get("prediction", "")).strip()
            or trace.get("parse_valid") is not True
            or processor.get("represented_views") != 12
            or processor.get("visual_tokens") != 3104
            or processor.get("secondary_frame_sampling") is not False
            or len(plan) != 4
            or detail_types != [expected_detail_type, expected_detail_type]
        ):
            raise RuntimeError(f"invalid protocol output: {prediction_path}")
        rows[qid] = {
            "prediction": str(prediction["prediction"]).strip(),
            "base_frame_indices": [int(value) for value in trace["base_source_frame_indices"]],
            "extra_source_indices": [int(plan[0]["source_frame_index"]), int(plan[2]["source_frame_index"])],
            "extra_source_ranks": [int(plan[0]["source_global_rank32"]), int(plan[2]["source_global_rank32"])],
            "prediction_sha256": sha256_text(str(prediction["prediction"]).strip()),
        }
    return rows


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")
    trigger_rows = load_jsonl(args.trigger_dataset)
    trigger_ids = {str(row["question_id"]) for row in trigger_rows}
    if len(trigger_rows) != 4905 or len(trigger_ids) != 4905:
        raise RuntimeError("expected frozen 4905 answer-free trigger set")

    adaptive = collect_predictions(args.adaptive_root, "evidence_mid_crop")
    extra_global = collect_predictions(args.extra_global_root, "evidence_full_highres")
    if set(adaptive) != trigger_ids or set(extra_global) != trigger_ids:
        raise RuntimeError("adaptive or extra-global outputs do not exactly match trigger set")
    for qid in sorted(trigger_ids):
        if (
            adaptive[qid]["base_frame_indices"] != extra_global[qid]["base_frame_indices"]
            or adaptive[qid]["extra_source_indices"] != extra_global[qid]["extra_source_indices"]
            or adaptive[qid]["extra_source_ranks"] != extra_global[qid]["extra_source_ranks"]
        ):
            raise RuntimeError(f"view alignment mismatch: {qid}")

    cache_scores: defaultdict[tuple[str, str], set[float]] = defaultdict(set)
    cache_sources: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    cache_audit = []
    for path in args.cache:
        rows = load_jsonl(path)
        accepted = 0
        for row in rows:
            qid = str(row.get("question_id", ""))
            candidate_hash = str(row.get("candidate_prediction_sha256", row.get("prediction_sha256", "")))
            try:
                score = float(row["score"])
            except (KeyError, TypeError, ValueError):
                continue
            if qid not in trigger_ids or len(candidate_hash) != 64 or score not in VALID_SCORES:
                continue
            cache_scores[(qid, candidate_hash)].add(score)
            cache_sources[(qid, candidate_hash)].append(str(path.resolve()))
            accepted += 1
        cache_audit.append({"path": str(path.resolve()), "sha256": sha256_file(path), "rows": len(rows), "accepted_rows": accepted})

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    answer_by_key: dict[tuple[str, str], str] = {}
    candidates = []
    exact_same_answer = 0
    for qid in sorted(trigger_ids):
        values = {
            "AdaptiveScale12": adaptive[qid]["prediction"],
            "ExtraGlobal12": extra_global[qid]["prediction"],
        }
        hashes = {method: sha256_text(value) for method, value in values.items()}
        if values["AdaptiveScale12"] == values["ExtraGlobal12"]:
            exact_same_answer += 1
        candidates.append({
            "question_id": qid,
            "candidates": values,
            "candidate_sha256": hashes,
            "groundtruth_included": False,
        })
        for method in METHODS:
            key = (qid, hashes[method])
            owners[key].append(method)
            answer_by_key[key] = values[method]

    pending = []
    reused = []
    conflicts = []
    for key in sorted(owners):
        scores = cache_scores.get(key, set())
        if len(scores) == 1:
            reused.append({
                "question_id": key[0],
                "candidate_prediction_sha256": key[1],
                "score": next(iter(scores)),
                "owners": owners[key],
                "sources": sorted(set(cache_sources[key])),
            })
        else:
            if len(scores) > 1:
                conflicts.append({
                    "question_id": key[0],
                    "candidate_prediction_sha256": key[1],
                    "scores": sorted(scores),
                    "owners": owners[key],
                    "sources": sorted(set(cache_sources[key])),
                })
            pending.append({
                "question_id": key[0],
                "candidate_prediction": answer_by_key[key],
                "candidate_prediction_sha256": key[1],
                "owners": owners[key],
                "historical_conflict_requires_fresh_score": len(scores) > 1,
            })

    args.output_dir.mkdir(parents=True, exist_ok=False)
    candidates_path = args.output_dir / "candidates_answer_free.jsonl"
    pending_path = args.output_dir / "pending_candidates_answer_only.jsonl"
    reuse_path = args.output_dir / "reused_scores.jsonl"
    conflicts_path = args.output_dir / "cache_conflicts.jsonl"
    write_jsonl(candidates_path, candidates)
    write_jsonl(pending_path, pending)
    write_jsonl(reuse_path, reused)
    write_jsonl(conflicts_path, conflicts)
    audit = {
        "schema_version": "adsqa_extra_global_vs_adaptive_preflight_v1",
        "passed": len(conflicts) == 0,
        "analysis_role": "posthoc_mechanism_attribution",
        "question_count": len(trigger_ids),
        "methods": list(METHODS),
        "expanded_candidate_slots": len(trigger_ids) * len(METHODS),
        "unique_question_answer_count": len(owners),
        "within_question_deduplicated_slots": len(trigger_ids) * len(METHODS) - len(owners),
        "exact_same_answer_count": exact_same_answer,
        "historical_exact_reuse_count": len(reused),
        "required_new_api_call_count": len(pending),
        "historical_conflict_count": len(conflicts),
        "same_trigger_set": True,
        "same_base_frames": True,
        "same_evidence_moments": True,
        "same_visual_tokens": 3104,
        "adaptive_detail_view_type": "evidence_mid_crop",
        "control_detail_view_type": "evidence_full_highres",
        "groundtruth_read": False,
        "historical_judge_cache_read": True,
        "api_called": False,
        "contains_api_key": False,
        "not_human_gold": True,
        "cache_files": cache_audit,
        "trigger_dataset_sha256": sha256_file(args.trigger_dataset),
        "adaptive_root": str(args.adaptive_root.resolve()),
        "extra_global_root": str(args.extra_global_root.resolve()),
        "candidates_sha256": sha256_file(candidates_path),
        "pending_sha256": sha256_file(pending_path),
        "reuse_sha256": sha256_file(reuse_path),
        "conflicts_sha256": sha256_file(conflicts_path),
    }
    (args.output_dir / "dry_run_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
