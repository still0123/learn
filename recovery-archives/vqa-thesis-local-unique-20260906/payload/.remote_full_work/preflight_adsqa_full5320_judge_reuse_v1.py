#!/usr/bin/env python3
"""Compute exact historical-score reuse and pending DeepSeek calls."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


METHODS = ("Uniform8", "MMR8", "AdaptiveScaleA2", "FullJointMethod")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--cache", type=Path, action="append", default=[])
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise RuntimeError(f"expected JSON list: {path}")
        return value
    return [
        json.loads(line) for line in text.splitlines() if line.strip()
    ]


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    protocol = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    if (
        protocol.get("passed") is not True
        or int(protocol.get("question_count", -1)) != 5320
        or protocol.get("groundtruth_read") is not False
        or protocol.get("judge_scores_read") is not False
        or int(protocol.get("deepseek_calls_made", -1)) != 0
    ):
        raise RuntimeError("answer-free full protocol audit did not pass")
    groundtruth = load_records(args.groundtruth)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    candidates = load_records(args.candidates)
    candidate_by_id = {str(row["question_id"]): row for row in candidates}
    if (
        len(groundtruth) != 5320
        or len(gt_by_id) != 5320
        or len(candidates) != 5320
        or set(gt_by_id) != set(candidate_by_id)
    ):
        raise RuntimeError("candidate/reference pools do not align")

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

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    candidate_text = {}
    method_counts = Counter()
    for qid, row in candidate_by_id.items():
        values = row.get("candidates")
        hashes = row.get("candidate_sha256")
        if (
            row.get("groundtruth_included") is not False
            or not isinstance(values, dict)
            or set(values) != set(METHODS)
            or not isinstance(hashes, dict)
        ):
            raise RuntimeError(f"invalid candidate row: {qid}")
        for method in METHODS:
            answer = str(values[method]).strip()
            candidate_hash = hashlib.sha256(
                answer.encode("utf-8")
            ).hexdigest()
            if candidate_hash != str(hashes[method]):
                raise RuntimeError(f"candidate hash mismatch: {qid}:{method}")
            key = (qid, candidate_hash)
            owners[key].append(method)
            candidate_text[key] = answer
            method_counts[method] += 1

    reused = {}
    pending = []
    conflicts = []
    for key in sorted(owners):
        scores = cache_scores.get(key, set())
        if len(scores) == 1:
            reused[key] = next(iter(scores))
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
                "candidate_prediction": candidate_text[key],
                "candidate_prediction_sha256": key[1],
                "owners": owners[key],
                "historical_conflict_requires_fresh_score": len(scores) > 1,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=False)
    pending_path = args.output_dir / "pending_candidates_answer_only.jsonl"
    pending_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in pending),
        encoding="utf-8",
    )
    reuse_path = args.output_dir / "reused_scores.jsonl"
    reuse_path.write_text(
        "".join(
            json.dumps(
                {
                    "question_id": key[0],
                    "candidate_prediction_sha256": key[1],
                    "score": score,
                    "owners": owners[key],
                    "sources": sorted(set(cache_sources[key])),
                },
                ensure_ascii=False,
            )
            + "\n"
            for key, score in sorted(reused.items())
        ),
        encoding="utf-8",
    )
    conflicts_path = args.output_dir / "cache_conflicts.jsonl"
    conflicts_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in conflicts
        ),
        encoding="utf-8",
    )
    total_owners = sum(len(value) for value in owners.values())
    audit = {
        "schema_version": "adsqa_full5320_judge_reuse_preflight_v1",
        "passed": True,
        "question_count": 5320,
        "expanded_candidate_slots": total_owners,
        "unique_question_answer_count": len(owners),
        "within_question_deduplicated_slots": total_owners - len(owners),
        "historical_exact_reuse_count": len(reused),
        "historical_conflict_count": len(conflicts),
        "required_new_api_call_count": len(pending),
        "candidate_mode": "answer_only",
        "reuse_key": [
            "question_id",
            "exact_extracted_candidate_sha256",
            "same_legacy_answer_only_protocol",
        ],
        "api_called": False,
        "contains_api_key": False,
        "not_human_gold": True,
        "candidate_owner_counts": dict(method_counts),
        "cache_files": cache_audit,
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "candidates_sha256": sha256_file(args.candidates),
        "protocol_audit_sha256": sha256_file(args.protocol_audit),
        "legacy_evaluator_sha256": sha256_file(args.legacy_evaluator),
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
