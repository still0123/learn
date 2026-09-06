#!/usr/bin/env python3
"""Build an answer-only judge preflight with exact historical score reuse."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


ARMS = ("crop_on", "crop_off", "full_on", "full_off")
VALID_SCORES = {0.0, 0.5, 1.0}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def answer_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--historical-scored", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")

    dataset = read_jsonl(args.dataset)
    qids = {str(row["question_id"]) for row in dataset}
    predictions: dict[str, dict[str, str]] = {qid: {} for qid in qids}
    for arm in ARMS:
        for path in (args.run_root / arm).rglob("a2_prediction.json"):
            row = json.loads(path.read_text(encoding="utf-8"))
            predictions[str(row["question_id"])][arm] = str(row["prediction"]).strip()
    if any(set(values) != set(ARMS) for values in predictions.values()):
        raise RuntimeError("missing four-arm predictions")

    cache: defaultdict[tuple[str, str], set[float]] = defaultdict(set)
    cache_sources: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    cache_audit = []
    for path in args.historical_scored:
        accepted = 0
        for row in read_jsonl(path):
            qid = str(row.get("question_id", ""))
            if qid not in qids:
                continue
            for key, value in row.items():
                if not key.startswith("_score_") or value is None:
                    continue
                method = key[len("_score_"):]
                candidate = row.get(method)
                if candidate is None:
                    continue
                score = float(value)
                if score not in VALID_SCORES:
                    continue
                cache_key = (qid, answer_hash(str(candidate)))
                cache[cache_key].add(score)
                cache_sources[cache_key].append(str(path.resolve()))
                accepted += 1
        cache_audit.append({"path": str(path.resolve()), "sha256": sha256_file(path), "accepted": accepted})

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    answer_by_key: dict[tuple[str, str], str] = {}
    candidates = []
    for qid in sorted(qids):
        values = predictions[qid]
        hashes = {arm: answer_hash(values[arm]) for arm in ARMS}
        candidates.append({
            "question_id": qid,
            "candidates": values,
            "candidate_sha256": hashes,
            "groundtruth_included": False,
        })
        for arm in ARMS:
            key = (qid, hashes[arm])
            owners[key].append(arm)
            answer_by_key[key] = values[arm]

    reused = []
    pending = []
    conflicts = []
    for key in sorted(owners):
        scores = cache.get(key, set())
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
                })
            pending.append({
                "question_id": key[0],
                "candidate_prediction": answer_by_key[key],
                "candidate_prediction_sha256": key[1],
                "owners": owners[key],
                "historical_conflict_requires_fresh_score": len(scores) > 1,
            })

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output_dir / "candidates_answer_free.jsonl", candidates)
    write_jsonl(args.output_dir / "reused_scores.jsonl", reused)
    write_jsonl(args.output_dir / "pending_candidates_answer_only.jsonl", pending)
    write_jsonl(args.output_dir / "cache_conflicts.jsonl", conflicts)
    audit = {
        "schema_version": "ocr_crop_factorial_judge_preflight_v1",
        "passed": len(conflicts) == 0,
        "question_count": len(qids),
        "expanded_candidate_slots": len(qids) * len(ARMS),
        "within_question_unique_answers": len(owners),
        "within_question_deduplicated_slots": len(qids) * len(ARMS) - len(owners),
        "historical_exact_reuse_count": len(reused),
        "required_new_api_call_count": len(pending),
        "historical_conflict_count": len(conflicts),
        "groundtruth_read": False,
        "api_called": False,
        "not_human_gold": True,
        "dataset_sha256": sha256_file(args.dataset),
        "protocol_audit_sha256": sha256_file(args.run_root / "protocol_audit.json"),
        "cache_files": cache_audit,
    }
    (args.output_dir / "preflight_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
