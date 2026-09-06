#!/usr/bin/env python3
"""Build an audited Evidence-300 dataset for pre-answer Raw/MMR routing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    return [json.loads(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def map_raw_ranks(candidate_frames: list[int], top_k: int = 32) -> list[int]:
    raw_sources = np.linspace(0, max(candidate_frames), top_k, dtype=int).tolist()
    available: dict[int, list[int]] = {}
    for rank, source in enumerate(candidate_frames):
        available.setdefault(int(source), []).append(rank)
    mapped = []
    for source in raw_sources:
        choices = available.get(int(source), [])
        if not choices:
            raise RuntimeError(f"Raw frame {source} missing from nested Candidate64")
        mapped.append(choices.pop(0))
    return mapped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-file", type=Path, required=True)
    parser.add_argument("--assignments-file", type=Path, required=True)
    parser.add_argument("--judge-results", type=Path, required=True)
    parser.add_argument("--mmr-cache", type=Path, action="append", required=True)
    parser.add_argument("--asr-file", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    args = parser.parse_args()

    questions = {str(row["question_id"]): row for row in load_json(args.question_file)}
    assignments = {str(row["question_id"]): row for row in load_json(args.assignments_file)}
    caches = {str(row["question_id"]): row for row in load_jsonl(args.mmr_cache)}
    asr = load_json(args.asr_file)
    judged: dict[str, dict[str, float]] = {}
    for row in load_jsonl([args.judge_results]):
        judged.setdefault(str(row["question_id"]), {})[str(row["method"])] = float(row["score"])
    expected = set(questions)
    problems = {
        "assignment_mismatch": sorted(expected ^ set(assignments)),
        "cache_mismatch": sorted(expected ^ set(caches)),
        "judge_mismatch": sorted(expected ^ set(judged)),
        "missing_judge_methods": sorted(qid for qid in expected if set(judged.get(qid, {})) != {"raw_uniform", "mmr32"}),
    }
    if any(problems.values()):
        raise RuntimeError(json.dumps({key: len(value) for key, value in problems.items()}))

    records = []
    for qid in [str(row["question_id"]) for row in load_json(args.question_file)]:
        question = questions[qid]
        assignment = assignments[qid]
        cache = caches[qid]
        video_id = str(assignment["video_id"])
        asr_text = str(asr.get(f"{video_id}.mp4", asr.get(video_id, "")) or "")
        trace = cache.get("selector_trace") or {}
        raw_score = judged[qid]["raw_uniform"]
        mmr_score = judged[qid]["mmr32"]
        record = {
            "schema": "adsqa_adaptive_temporal_router_record_v1",
            "question_id": qid,
            "video_id": video_id,
            "split": str(assignment["split"]),
            "primary_type": str(assignment["primary_type"]),
            "question": str(question["question"]),
            "router_inputs": {
                "asr_present": bool(asr_text.strip()),
                "asr_length": len(asr_text),
                "candidate_count": int(cache["candidate_count"]),
                "candidate_frame_indices": list(cache["candidate_frame_indices"]),
                "candidate_scores": list(cache.get("candidate_scores") or []),
                "raw_candidate_ranks": map_raw_ranks(list(cache["candidate_frame_indices"])),
                "mmr_selected_candidate_ranks": list(cache["selected_candidate_ranks"]),
                "selector_trace": trace,
            },
            "supervision": {
                "raw_score": raw_score,
                "mmr_score": mmr_score,
                "score_delta": mmr_score - raw_score,
                "mmr_better": int(mmr_score > raw_score),
            },
        }
        records.append(record)

    split_counts: dict[str, int] = {}
    split_videos: dict[str, set[str]] = {}
    for record in records:
        split_counts[record["split"]] = split_counts.get(record["split"], 0) + 1
        split_videos.setdefault(record["split"], set()).add(record["video_id"])
    overlaps = {
        f"{left}__{right}": len(split_videos[left] & split_videos[right])
        for index, left in enumerate(sorted(split_videos))
        for right in sorted(split_videos)[index + 1:]
    }
    if split_counts != {"train": 200, "calibration": 50, "development": 50} or any(overlaps.values()):
        raise RuntimeError(f"invalid frozen split: counts={split_counts} overlaps={overlaps}")
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    audit = {
        "schema": "adsqa_adaptive_temporal_router_dataset_audit_v1",
        "record_count": len(records), "split_counts": split_counts,
        "split_video_counts": {key: len(value) for key, value in split_videos.items()},
        "split_video_overlaps": overlaps,
        "positive_counts": {
            split: sum(row["supervision"]["mmr_better"] for row in records if row["split"] == split)
            for split in split_counts
        },
        "feature_inputs_contain_answers": False,
        "source_hashes": {
            "question": sha256(args.question_file), "assignments": sha256(args.assignments_file),
            "judge_results": sha256(args.judge_results), "asr": sha256(args.asr_file),
            "mmr_caches": [{"path": str(path), "sha256": sha256(path)} for path in args.mmr_cache],
        },
        "output_sha256": sha256(args.output_jsonl),
    }
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "split_counts": split_counts, "positive_counts": audit["positive_counts"], "output_sha256": audit["output_sha256"]}))


if __name__ == "__main__":
    main()

