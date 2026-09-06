#!/usr/bin/env python3
"""Materialize the frozen threshold policy and compute exact judge reuse."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


METHODS = ("MMR8", "ThresholdAdaptiveA2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--old-candidates", type=Path, required=True)
    parser.add_argument("--trigger-dataset", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--frozen-threshold", type=Path, required=True)
    parser.add_argument("--cache", type=Path, action="append", default=[])
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise RuntimeError(f"expected JSON list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def sha256_bytes(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")

    protocol = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    if (
        protocol.get("passed") is not True
        or int(protocol.get("record_count", -1)) != 4905
        or protocol.get("groundtruth_read") is not False
        or protocol.get("judge_scores_read") is not False
        or protocol.get("failures") != []
    ):
        raise RuntimeError("threshold A2 protocol audit did not pass")

    frozen = json.loads(args.frozen_threshold.read_text(encoding="utf-8"))
    tau = frozen.get(
        "final_threshold",
        frozen.get("threshold", frozen.get("tau")),
    )
    if tau is None:
        raise RuntimeError("frozen threshold file does not contain tau")

    groundtruth = load_records(args.groundtruth)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    old_candidates = load_records(args.old_candidates)
    old_by_id = {str(row["question_id"]): row for row in old_candidates}
    trigger_rows = load_records(args.trigger_dataset)
    trigger_by_id = {str(row["question_id"]): row for row in trigger_rows}
    if (
        len(gt_by_id) != 5320
        or len(old_by_id) != 5320
        or set(gt_by_id) != set(old_by_id)
        or len(trigger_by_id) != 4905
        or not set(trigger_by_id).issubset(gt_by_id)
    ):
        raise RuntimeError("reference, old candidate, or trigger pools do not align")

    a2_by_id: dict[str, str] = {}
    for path in sorted(args.inference_root.glob("fold_*/*/a2_prediction.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        prediction = str(row["prediction"]).strip()
        if qid in a2_by_id:
            raise RuntimeError(f"duplicate A2 prediction: {qid}")
        if qid not in trigger_by_id or not prediction:
            raise RuntimeError(f"unexpected or empty A2 prediction: {qid}")
        a2_by_id[qid] = prediction
    if set(a2_by_id) != set(trigger_by_id):
        raise RuntimeError("A2 prediction pool does not match trigger pool")

    cache_scores: defaultdict[tuple[str, str], set[float]] = defaultdict(set)
    cache_sources: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    cache_audit = []
    for path in args.cache:
        rows = load_records(path)
        accepted = 0
        for row in rows:
            qid = str(row.get("question_id", ""))
            candidate_hash = str(
                row.get(
                    "candidate_prediction_sha256",
                    row.get("prediction_sha256", ""),
                )
            )
            if (
                qid not in gt_by_id
                or len(candidate_hash) != 64
                or "score" not in row
            ):
                continue
            score = float(row["score"])
            if score not in {0.0, 0.5, 1.0}:
                continue
            cache_scores[(qid, candidate_hash)].add(score)
            cache_sources[(qid, candidate_hash)].append(str(path.resolve()))
            accepted += 1
        cache_audit.append(
            {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
                "rows": len(rows),
                "accepted_rows": accepted,
            }
        )

    candidates = []
    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    text_by_key: dict[tuple[str, str], str] = {}
    exact_a0_a2 = 0
    trigger_a0_mismatch = []
    for qid in sorted(gt_by_id):
        old = old_by_id[qid]
        mmr = str(old["candidates"]["MMR8"]).strip()
        if qid in trigger_by_id:
            dataset_a0 = str(trigger_by_id[qid]["a0_prediction"]).strip()
            if dataset_a0 != mmr:
                trigger_a0_mismatch.append(qid)
            policy = a2_by_id[qid]
            if policy == mmr:
                exact_a0_a2 += 1
        else:
            policy = mmr
        values = {"MMR8": mmr, "ThresholdAdaptiveA2": policy}
        hashes = {method: sha256_bytes(values[method]) for method in METHODS}
        candidates.append(
            {
                "question_id": qid,
                "candidates": values,
                "candidate_sha256": hashes,
                "triggered": qid in trigger_by_id,
                "groundtruth_included": False,
            }
        )
        for method in METHODS:
            key = (qid, hashes[method])
            owners[key].append(method)
            text_by_key[key] = values[method]
    if trigger_a0_mismatch:
        raise RuntimeError(
            f"trigger A0 does not match frozen MMR8 for "
            f"{len(trigger_a0_mismatch)} questions"
        )

    reused = []
    pending = []
    conflicts = []
    method_reuse = defaultdict(int)
    method_pending = defaultdict(int)
    for key in sorted(owners):
        scores = cache_scores.get(key, set())
        if len(scores) == 1:
            score = next(iter(scores))
            for method in owners[key]:
                method_reuse[method] += 1
            reused.append(
                {
                    "question_id": key[0],
                    "candidate_prediction_sha256": key[1],
                    "score": score,
                    "owners": owners[key],
                    "sources": sorted(set(cache_sources[key])),
                }
            )
            continue
        if len(scores) > 1:
            conflicts.append(
                {
                    "question_id": key[0],
                    "candidate_prediction_sha256": key[1],
                    "scores": sorted(scores),
                    "sources": sorted(set(cache_sources[key])),
                }
            )
        for method in owners[key]:
            method_pending[method] += 1
        pending.append(
            {
                "question_id": key[0],
                "candidate_prediction": text_by_key[key],
                "candidate_prediction_sha256": key[1],
                "owners": owners[key],
                "historical_conflict_requires_fresh_score": len(scores) > 1,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=False)
    candidate_path = args.output_dir / "candidates_answer_free.jsonl"
    reuse_path = args.output_dir / "reused_scores.jsonl"
    pending_path = args.output_dir / "pending_candidates_answer_only.jsonl"
    conflicts_path = args.output_dir / "cache_conflicts.jsonl"
    write_jsonl(candidate_path, candidates)
    write_jsonl(reuse_path, reused)
    write_jsonl(pending_path, pending)
    write_jsonl(conflicts_path, conflicts)

    failed_old = {
        str(row.get("question_id", "")): str(
            row.get("candidate_prediction_sha256", "")
        )
        for path in args.cache
        if path.name == "api_failures.jsonl"
        for row in load_records(path)
    }
    failed_overlap = [
        {
            "question_id": qid,
            "candidate_prediction_sha256": candidate_hash,
            "owners": owners.get((qid, candidate_hash), []),
        }
        for qid, candidate_hash in failed_old.items()
        if (qid, candidate_hash) in owners
    ]

    audit = {
        "schema_version": "qwen3_threshold_full5320_judge_preflight_v1",
        "passed": len(conflicts) == 0,
        "question_count": 5320,
        "triggered_count": len(trigger_by_id),
        "nontriggered_count": 5320 - len(trigger_by_id),
        "frozen_threshold": float(tau),
        "method_count": len(METHODS),
        "expanded_candidate_slots": 5320 * len(METHODS),
        "unique_question_answer_count": len(owners),
        "within_question_deduplicated_slots": 5320 * len(METHODS) - len(owners),
        "triggered_a2_exactly_equals_a0_count": exact_a0_a2,
        "historical_exact_reuse_count": len(reused),
        "required_new_api_call_count": len(pending),
        "historical_conflict_count": len(conflicts),
        "method_reuse_counts": dict(method_reuse),
        "method_pending_counts": dict(method_pending),
        "old_failed_candidate_overlap": failed_overlap,
        "candidate_mode": "answer_only",
        "reuse_key": [
            "question_id",
            "exact_extracted_candidate_sha256",
            "same_legacy_answer_only_protocol",
        ],
        "api_called": False,
        "contains_api_key": False,
        "not_human_gold": True,
        "cache_files": cache_audit,
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "old_candidates_sha256": sha256_file(args.old_candidates),
        "trigger_dataset_sha256": sha256_file(args.trigger_dataset),
        "protocol_audit_sha256": sha256_file(args.protocol_audit),
        "frozen_threshold_sha256": sha256_file(args.frozen_threshold),
        "legacy_evaluator_sha256": sha256_file(args.legacy_evaluator),
        "candidates_sha256": sha256_file(candidate_path),
        "pending_sha256": sha256_file(pending_path),
        "reuse_sha256": sha256_file(reuse_path),
        "conflicts_sha256": sha256_file(conflicts_path),
    }
    (args.output_dir / "dry_run_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
