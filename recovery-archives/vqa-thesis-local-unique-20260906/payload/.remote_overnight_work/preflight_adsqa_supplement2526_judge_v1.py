#!/usr/bin/env python3
"""Freeze and deduplicate AdsQA supplement candidates before judging."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


METHODS = ("Uniform8", "CLIPTopK8", "MMR8", "AdaptiveScale")
EXPECTED_QUESTIONS = 2526
EXPECTED_TRIGGERED = 2270
EXPECTED_UNIQUE = 9807


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path)
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


def sha256_text(value: str) -> str:
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
        or int(protocol.get("question_count", -1)) != EXPECTED_QUESTIONS
        or int(protocol.get("trigger_count", -1)) != EXPECTED_TRIGGERED
        or tuple(protocol.get("methods", [])) != METHODS
        or protocol.get("groundtruth_read") is not False
        or protocol.get("judge_scores_read") is not False
        or int(protocol.get("deepseek_calls_made", -1)) != 0
    ):
        raise RuntimeError("answer-free candidate protocol did not pass")

    references = load_records(args.groundtruth)
    candidates = load_records(args.candidates)
    ref_by_id = {str(row["question_id"]): row for row in references}
    candidate_by_id = {str(row["question_id"]): row for row in candidates}
    if (
        len(ref_by_id) != EXPECTED_QUESTIONS
        or len(candidate_by_id) != EXPECTED_QUESTIONS
        or set(ref_by_id) != set(candidate_by_id)
    ):
        raise RuntimeError("candidate/reference pools do not align")

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    text_by_key: dict[tuple[str, str], str] = {}
    trigger_count = 0
    method_slots = defaultdict(int)
    for qid, row in sorted(candidate_by_id.items()):
        values = row.get("candidates")
        hashes = row.get("candidate_sha256")
        if (
            row.get("groundtruth_included") is not False
            or not isinstance(values, dict)
            or tuple(values) != METHODS
            or not isinstance(hashes, dict)
            or set(hashes) != set(METHODS)
        ):
            raise RuntimeError(f"invalid candidate row: {qid}")
        trigger_count += int(bool(row.get("triggered")))
        for method in METHODS:
            answer = str(values[method]).strip()
            answer_hash = sha256_text(answer)
            if not answer or answer_hash != str(hashes[method]):
                raise RuntimeError(f"candidate hash mismatch: {qid}:{method}")
            key = (qid, answer_hash)
            owners[key].append(method)
            text_by_key[key] = answer
            method_slots[method] += 1
    if trigger_count != EXPECTED_TRIGGERED or len(owners) != EXPECTED_UNIQUE:
        raise RuntimeError("frozen trigger or unique-call count changed")

    cache_scores: defaultdict[tuple[str, str], set[float]] = defaultdict(set)
    cache_sources: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    cache_inventory = []
    if args.cache_root:
        paths = sorted(
            set(args.cache_root.rglob("api_results_partial.jsonl"))
            | set(args.cache_root.rglob("reused_scores.jsonl"))
        )
        output_resolved = args.output_dir.resolve()
        for path in paths:
            if output_resolved in path.resolve().parents:
                continue
            accepted = 0
            matched = 0
            for row in load_records(path):
                qid = str(row.get("question_id", ""))
                candidate_hash = str(
                    row.get(
                        "candidate_prediction_sha256",
                        row.get("prediction_sha256", ""),
                    )
                )
                if len(candidate_hash) != 64 or "score" not in row:
                    continue
                score = float(row["score"])
                if score not in {0.0, 0.5, 1.0}:
                    continue
                accepted += 1
                key = (qid, candidate_hash)
                if key in owners:
                    matched += 1
                    cache_scores[key].add(score)
                    cache_sources[key].append(str(path.resolve()))
            cache_inventory.append(
                {
                    "path": str(path.resolve()),
                    "sha256": sha256_file(path),
                    "accepted_rows": accepted,
                    "matched_rows": matched,
                }
            )

    reused = []
    pending = []
    conflicts = []
    for key in sorted(owners):
        scores = cache_scores.get(key, set())
        if len(scores) == 1:
            reused.append(
                {
                    "question_id": key[0],
                    "candidate_prediction_sha256": key[1],
                    "score": next(iter(scores)),
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
        pending.append(
            {
                "question_id": key[0],
                "candidate_prediction": text_by_key[key],
                "candidate_prediction_sha256": key[1],
                "owners": owners[key],
                "historical_conflict_requires_fresh_score": len(scores) > 1,
            }
        )

    if reused or conflicts or len(pending) != EXPECTED_UNIQUE:
        raise RuntimeError("historical reuse result changed from authorized preflight")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    candidate_path = args.output_dir / "candidates_answer_free.jsonl"
    pending_path = args.output_dir / "pending_candidates_answer_only.jsonl"
    reuse_path = args.output_dir / "reused_scores.jsonl"
    conflicts_path = args.output_dir / "cache_conflicts.jsonl"
    shutil.copyfile(args.candidates, candidate_path)
    write_jsonl(pending_path, pending)
    write_jsonl(reuse_path, reused)
    write_jsonl(conflicts_path, conflicts)

    audit = {
        "schema_version": "adsqa_supplement2526_judge_preflight_v1",
        "passed": True,
        "question_count": EXPECTED_QUESTIONS,
        "triggered_count": trigger_count,
        "nontriggered_count": EXPECTED_QUESTIONS - trigger_count,
        "methods": list(METHODS),
        "expanded_candidate_slots": EXPECTED_QUESTIONS * len(METHODS),
        "unique_question_answer_count": len(owners),
        "within_question_deduplicated_slots": (
            EXPECTED_QUESTIONS * len(METHODS) - len(owners)
        ),
        "historical_exact_reuse_count": len(reused),
        "required_new_api_call_count": len(pending),
        "historical_conflict_count": len(conflicts),
        "method_slot_counts": dict(method_slots),
        "candidate_mode": "answer_only",
        "reuse_key": [
            "question_id",
            "exact_extracted_candidate_sha256",
            "same_legacy_answer_only_protocol",
        ],
        "api_called": False,
        "contains_api_key": False,
        "not_human_gold": True,
        "cache_files_scanned": len(cache_inventory),
        "cache_inventory": cache_inventory,
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "source_candidates_sha256": sha256_file(args.candidates),
        "protocol_audit_sha256": sha256_file(args.protocol_audit),
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
