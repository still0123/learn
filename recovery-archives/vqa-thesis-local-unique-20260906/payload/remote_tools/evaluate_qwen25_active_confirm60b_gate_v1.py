#!/usr/bin/env python3
"""Apply the historical frozen sufficiency gate and evaluate with cached judge scores."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import random


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--candidate-scores", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.8933094143867493)
    parser.add_argument("--margin", type=float, default=0.25)
    args = parser.parse_args()
    master = {str(row["question_id"]): row for row in rows(args.root / "master_answer_free.jsonl")}
    judged = {str(row["question_id"]): row for row in rows(args.root / "judge_results_v1" / "paired_results60.jsonl")}
    candidate = {str(row["source_question_id"]): float(row["support_probability"]) for row in rows(args.candidate_scores)}
    hashes = defaultdict(dict)
    for row in rows(args.candidates):
        hashes[str(row["question_id"])][str(row["method"])] = str(row["prediction_sha256"])
    output = []
    for qid, row in sorted(judged.items()):
        p0 = float(master[qid]["support_probability"])
        p2 = candidate.get(qid, p0)
        changed = hashes[qid]["ActiveLook"] != hashes[qid]["A0"]
        switch = master[qid]["action"] != "DIRECT" and changed and p2 >= args.threshold and p0 < args.threshold and p2 - p0 >= args.margin
        output.append({
            "question_id": qid, "video_id": row["video_id"], "action": master[qid]["action"],
            "A0": float(row["A0"]), "ActiveLook": float(row["ActiveLook"]),
            "Gated": float(row["ActiveLook"] if switch else row["A0"]),
            "switched": switch, "p0": p0, "p2": p2, "margin": p2 - p0,
        })
    by_video = defaultdict(list)
    for row in output:
        by_video[row["video_id"]].append(row)
    videos = sorted(by_video)
    rng = random.Random(2026080502)
    boot = []
    for _ in range(10000):
        sample = [row for video in rng.choices(videos, k=len(videos)) for row in by_video[video]]
        boot.append(sum(row["Gated"] - row["A0"] for row in sample) / len(sample))
    boot.sort()
    summary = {
        "schema_version": "qwen25_active_confirm60b_frozen_gate_v1",
        "threshold": args.threshold, "minimum_margin": args.margin,
        "threshold_source": "historical_qwen3_selective_evidence_rewrite_oof50",
        "threshold_tuned_on_confirm60b": False,
        "n": 60, "switched": sum(row["switched"] for row in output),
        "a0_strict": sum(row["A0"] == 1 for row in output) / 60,
        "gated_strict": sum(row["Gated"] == 1 for row in output) / 60,
        "a0_relaxed": sum(row["A0"] for row in output) / 60,
        "gated_relaxed": sum(row["Gated"] for row in output) / 60,
        "wins": sum(row["Gated"] > row["A0"] for row in output),
        "ties": sum(row["Gated"] == row["A0"] for row in output),
        "losses": sum(row["Gated"] < row["A0"] for row in output),
        "wrong_to_right": sum(row["A0"] == 0 and row["Gated"] == 1 for row in output),
        "right_to_wrong": sum(row["A0"] == 1 and row["Gated"] < 1 for row in output),
        "relaxed_delta_bootstrap_ci95": [boot[250], boot[9750]],
        "judge_api_called": False,
    }
    args.output_root.mkdir(parents=True, exist_ok=False)
    (args.output_root / "choices.jsonl").write_text("".join(json.dumps(row) + "\n" for row in output))
    (args.output_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output_root / "COMPLETE").write_text("complete\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
