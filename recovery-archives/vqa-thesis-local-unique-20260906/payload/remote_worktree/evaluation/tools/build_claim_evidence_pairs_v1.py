#!/usr/bin/env python3
"""Build supervised candidate pairs from frozen traces and immutable judge rows."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.claim_evidence_verifier.dataset import pair_record_from_trace


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def trace_paths(root: Path) -> list[Path]:
    paths = sorted(root.glob("shard*of*/trace/*/evidence.json"))
    if not paths:
        paths = sorted(root.glob("trace/*/evidence.json"))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--groundtruth-file", type=Path, required=True)
    parser.add_argument("--judge-results-jsonl", type=Path, required=True)
    parser.add_argument("--source-method", choices=["raw_uniform", "innovation1_mmr32"], required=True)
    parser.add_argument("--initial-judge-method", required=True)
    parser.add_argument("--rescue-judge-method", required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    args = parser.parse_args()
    gt_rows = load_json(args.groundtruth_file)
    gt_map = {str(row["question_id"]): row for row in gt_rows}
    judge_rows = load_jsonl(args.judge_results_jsonl)
    scores = {
        (str(row.get("method")), str(row.get("question_id"))): float(row["score"])
        for row in judge_rows if row.get("score") in {0, 0.0, 0.5, 1, 1.0}
    }
    paths = trace_paths(args.trace_root)
    if len(paths) != args.expected_count:
        raise RuntimeError(f"expected {args.expected_count} traces, found {len(paths)}")
    records = []
    seen = set()
    trace_hashes = []
    for path in paths:
        trace = load_json(path)
        qid = str(trace["question_id"])
        if qid in seen:
            raise RuntimeError(f"duplicate trace for {qid}")
        seen.add(qid)
        if qid not in gt_map:
            raise RuntimeError(f"missing ground truth row for {qid}")
        initial_key = (args.initial_judge_method, qid)
        rescue_key = (args.rescue_judge_method, qid)
        if initial_key not in scores or rescue_key not in scores:
            raise RuntimeError(f"missing immutable judge score for {qid}")
        record = pair_record_from_trace(
            trace, args.source_method, gt_map[qid], scores[initial_key], scores[rescue_key]
        )
        record["provenance"] = {"trace_path": str(path), "trace_sha256": sha256_file(path)}
        records.append(record)
        trace_hashes.append(record["provenance"])
    records.sort(key=lambda row: str(row["question_id"]))
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"
    )
    transitions = Counter(
        "rescue_better" if row["supervision"]["rescue_better"] else
        "initial_better" if row["supervision"]["initial_better"] else "tie"
        for row in records
    )
    manifest = {
        "schema": "adsqa_claim_evidence_pair_manifest_v1",
        "source_method": args.source_method,
        "count": len(records),
        "unique_questions": len(seen),
        "unique_videos": len({row["video_id"] for row in records}),
        "transition_counts": dict(transitions),
        "trace_root": str(args.trace_root),
        "trace_hashes": trace_hashes,
        "groundtruth_file": str(args.groundtruth_file),
        "groundtruth_sha256": sha256_file(args.groundtruth_file),
        "judge_results_jsonl": str(args.judge_results_jsonl),
        "judge_results_sha256": sha256_file(args.judge_results_jsonl),
        "initial_judge_method": args.initial_judge_method,
        "rescue_judge_method": args.rescue_judge_method,
        "output_jsonl": str(args.output_jsonl),
        "output_sha256": sha256_file(args.output_jsonl),
        "leakage_rule": "ground truth and judge scores are supervision only; feature extractor ignores supervision",
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(records), "transitions": dict(transitions), "sha256": manifest["output_sha256"]}))


if __name__ == "__main__":
    main()
