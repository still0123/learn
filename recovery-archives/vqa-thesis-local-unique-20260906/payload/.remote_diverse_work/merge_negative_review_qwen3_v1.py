#!/usr/bin/env python3
"""Merge and audit four Qwen3 negative-review shards."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-root", type=Path, required=True)
    args = p.parse_args()
    source = load(args.run_root / "dataset/review_inputs.jsonl")
    by_qid, duplicates = {}, []
    for index in range(4):
        for row in load(args.run_root / f"shards/shard_{index}/scores.jsonl"):
            qid = str(row["question_id"])
            if qid in by_qid:
                duplicates.append(qid)
            by_qid[qid] = row
    source_ids = [str(row["question_id"]) for row in source]
    merged = [by_qid[qid] for qid in source_ids if qid in by_qid]
    protocol_errors = []
    high = []
    metadata = {str(row["question_id"]): row for row in source}
    predicted = Counter()
    for row in merged:
        scores = row["scores"]["full"]
        predicted[max(scores, key=scores.get)] += 1
        trace = row["processor_traces"]["full"]
        if trace.get("submitted_frame_count") != 32 or trace.get("represented_frame_count") != 32:
            protocol_errors.append({"question_id": row["question_id"], "error": "view_count"})
        if int(trace.get("post_merge_visual_token_count", 999999)) > 12000:
            protocol_errors.append({"question_id": row["question_id"], "error": "token_budget"})
        if trace.get("secondary_frame_sampling_disabled") is not True:
            protocol_errors.append({"question_id": row["question_id"], "error": "secondary_sampling"})
        if float(scores["supported"]) <= 0.20 and float(scores["refuted"] + scores["insufficient"]) >= 0.80:
            high.append({
                "question_id": row["question_id"], "video_id": row["video_id"],
                "claim_type": metadata[str(row["question_id"])]["claim_type"],
                "scores": scores, "reviewer": "Qwen3-VL-8B", "not_human_gold": True,
            })
    high_videos = {row["video_id"] for row in high}
    audit = {
        "schema": "adsqa_negative_review_qwen3_merge_audit_v1",
        "source_rows": len(source), "merged_rows": len(merged), "unique_rows": len(by_qid),
        "duplicates": duplicates, "missing": sorted(set(source_ids) - set(by_qid)),
        "protocol_errors": protocol_errors, "predicted_label_counts": dict(predicted),
        "high_confidence_definition": "P(supported)<=0.20 and P(refuted)+P(insufficient)>=0.80",
        "high_confidence_rows": len(high), "high_confidence_videos": len(high_videos),
        "high_confidence_claim_types": dict(Counter(row["claim_type"] for row in high)),
        "training_gate_passed": len(high) >= 150 and len(high_videos) >= 60,
        "not_human_gold": True,
        "passed": len(merged) == 343 and len(by_qid) == 343 and not duplicates and not protocol_errors,
    }
    out = args.run_root / "merged"
    write_jsonl(out / "scores.jsonl", merged)
    write_jsonl(out / "high_confidence_negatives.jsonl", high)
    (out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (out / "manifest.json").write_text(json.dumps({
        "scores_sha256": sha(out / "scores.jsonl"),
        "high_confidence_sha256": sha(out / "high_confidence_negatives.jsonl"), "audit": audit,
    }, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
