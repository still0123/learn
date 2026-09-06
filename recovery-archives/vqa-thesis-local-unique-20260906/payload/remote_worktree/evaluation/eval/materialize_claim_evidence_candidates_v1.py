#!/usr/bin/env python3
"""Materialize initial and rescue candidates for the immutable legacy judge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_traces(root: Path) -> list[Path]:
    paths = sorted(root.glob("shard*of*/trace/*/evidence.json"))
    return paths or sorted(root.glob("trace/*/evidence.json"))


def prediction(qid: str, answer: str, ground_truth: str, pipeline: str) -> dict[str, Any]:
    return {
        "question_id": qid,
        "prediction": answer,
        "ground_truth": ground_truth,
        "initial_reasoning": answer,
        "pipeline": pipeline,
        "reflection_status": "disabled_claim_evidence_candidate_v1",
        "rag_mode": "none",
        "score": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--groundtruth-file", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-method", choices=["raw_uniform", "innovation1_mmr32"], required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    args = parser.parse_args()
    gt_rows = load_json(args.groundtruth_file)
    gt_map = {str(row["question_id"]): str(row.get("answer", "")) for row in gt_rows}
    paths = find_traces(args.trace_root)
    if len(paths) != args.expected_count:
        raise RuntimeError(f"expected {args.expected_count} traces, found {len(paths)}")
    records = []
    seen = set()
    for path in paths:
        trace = load_json(path)
        qid = str(trace["question_id"])
        rescue = trace.get("rescue") or {}
        initial_answer = str(trace.get("initial_answer", "")).strip()
        rescue_answer = str(rescue.get("rescue_answer", "")).strip()
        conditional_answer = str(trace.get("final_answer", "")).strip()
        if qid in seen or qid not in gt_map or not initial_answer or not rescue.get("triggered") or not rescue_answer or not conditional_answer:
            raise RuntimeError(f"invalid candidate trace: {qid}")
        seen.add(qid)
        groups = {
            f"{args.source_method}_initial_candidate": initial_answer,
            f"{args.source_method}_rescue_candidate": rescue_answer,
            f"{args.source_method}_conditional_selector": conditional_answer,
        }
        for group, answer in groups.items():
            target = args.output_root / group / qid / "prediction.json"
            dump_json(target, prediction(qid, answer, gt_map[qid], group))
        records.append({"question_id": qid, "trace": str(path), "trace_sha256": sha256_file(path)})
    manifest = {
        "schema": "adsqa_claim_evidence_candidate_collection_v1",
        "source_method": args.source_method,
        "count": len(records),
        "trace_root": str(args.trace_root),
        "groundtruth_file": str(args.groundtruth_file),
        "groundtruth_sha256": sha256_file(args.groundtruth_file),
        "groups": [
            f"{args.source_method}_initial_candidate",
            f"{args.source_method}_rescue_candidate",
            f"{args.source_method}_conditional_selector",
        ],
        "records": records,
    }
    dump_json(args.output_root / f"{args.source_method}_candidate_manifest.json", manifest)
    print(json.dumps({"source_method": args.source_method, "count": len(records), "groups": manifest["groups"]}))


if __name__ == "__main__":
    main()
