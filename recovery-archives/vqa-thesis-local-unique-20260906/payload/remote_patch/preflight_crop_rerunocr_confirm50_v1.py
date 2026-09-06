#!/usr/bin/env python3
"""Build answer-only judge inputs for crop/full re-OCR plus no-OCR controls."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


ARMS = ("crop_on", "crop_off", "full_on", "full_off")
VALID = {0.0, 0.5, 1.0}


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def ah(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def outputs(root: Path, arm: str) -> dict[str, str]:
    result = {}
    for path in (root / arm).rglob("a2_prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        result[str(row["question_id"])] = str(row["prediction"]).strip()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--historical-scored", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_dir}")

    dataset = read(args.dataset)
    qids = {str(row["question_id"]) for row in dataset}
    pred = {
        "crop_on": outputs(args.run_root, "crop_rerunocr"),
        "full_on": outputs(args.run_root, "full_rerunocr"),
        "crop_off": outputs(args.reference_root, "crop_off"),
        "full_off": outputs(args.reference_root, "full_off"),
    }
    pred = {arm: {qid: values[qid] for qid in qids} for arm, values in pred.items()}

    cache = defaultdict(set)
    sources = defaultdict(list)
    cache_files = []
    for path in args.historical_scored:
        accepted = 0
        for row in read(path):
            qid = str(row.get("question_id", ""))
            if qid not in qids:
                continue
            for key, score in row.items():
                if not key.startswith("_score_") or score is None:
                    continue
                method = key[7:]
                if method not in row or float(score) not in VALID:
                    continue
                ck = (qid, ah(str(row[method])))
                cache[ck].add(float(score)); sources[ck].append(str(path.resolve())); accepted += 1
        cache_files.append({"path": str(path.resolve()), "sha256": digest(path), "accepted": accepted})

    owners = defaultdict(list)
    text_by_key = {}
    candidates = []
    for qid in sorted(qids):
        values = {arm: pred[arm][qid] for arm in ARMS}
        hashes = {arm: ah(values[arm]) for arm in ARMS}
        candidates.append({"question_id": qid, "candidates": values, "candidate_sha256": hashes,
                           "groundtruth_included": False,
                           "arm_semantics": {"crop_on": "crop_rerunocr", "full_on": "full_rerunocr",
                                             "crop_off": "crop_noocr_reuse", "full_off": "full_noocr_reuse"}})
        for arm in ARMS:
            key = (qid, hashes[arm]); owners[key].append(arm); text_by_key[key] = values[arm]
    reused, pending, conflicts = [], [], []
    for key in sorted(owners):
        scores = cache.get(key, set())
        if len(scores) == 1:
            reused.append({"question_id": key[0], "candidate_prediction_sha256": key[1],
                           "score": next(iter(scores)), "owners": owners[key],
                           "sources": sorted(set(sources[key]))})
        else:
            if len(scores) > 1:
                conflicts.append({"question_id": key[0], "candidate_prediction_sha256": key[1],
                                  "scores": sorted(scores), "owners": owners[key]})
            pending.append({"question_id": key[0], "candidate_prediction": text_by_key[key],
                            "candidate_prediction_sha256": key[1], "owners": owners[key],
                            "historical_conflict_requires_fresh_score": len(scores) > 1})

    args.output_dir.mkdir(parents=True, exist_ok=False)
    write(args.output_dir / "candidates_answer_free.jsonl", candidates)
    write(args.output_dir / "reused_scores.jsonl", reused)
    write(args.output_dir / "pending_candidates_answer_only.jsonl", pending)
    write(args.output_dir / "cache_conflicts.jsonl", conflicts)
    audit = {
        "schema_version": "crop_rerunocr_confirm50_judge_preflight_v1",
        "passed": not conflicts,
        "question_count": len(qids),
        "expanded_candidate_slots": len(qids) * 4,
        "within_question_unique_answers": len(owners),
        "within_question_deduplicated_slots": len(qids) * 4 - len(owners),
        "historical_exact_reuse_count": len(reused),
        "required_new_api_call_count": len(pending),
        "historical_conflict_count": len(conflicts),
        "groundtruth_read": False,
        "api_called": False,
        "not_human_gold": True,
        "dataset_sha256": digest(args.dataset),
        "protocol_audit_sha256": digest(args.run_root / "protocol_audit.json"),
        "cache_files": cache_files,
    }
    (args.output_dir / "preflight_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
