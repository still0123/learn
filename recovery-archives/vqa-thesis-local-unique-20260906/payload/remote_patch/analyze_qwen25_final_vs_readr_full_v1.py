#!/usr/bin/env python3
"""Pair clean-Qwen2.5 final AdsQA scores with the ReAd-R re-evaluation."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen25-results", type=Path, required=True)
    parser.add_argument("--readr-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def bootstrap(
    rows: list[dict[str, Any]], key: str, samples: int, seed: int = 42
) -> list[float]:
    by_video: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video"])].append(float(row[key]))
    videos = sorted(by_video)
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(samples):
        sample: list[float] = []
        for _ in videos:
            sample.extend(by_video[videos[rng.randrange(len(videos))]])
        values.append(sum(sample) / len(sample))
    values.sort()
    return [values[round((samples - 1) * 0.025)], values[round((samples - 1) * 0.975)]]


def metrics(rows: list[dict[str, Any]], score_key: str) -> dict[str, Any]:
    scores = [float(row[score_key]) for row in rows]
    return {
        "n": len(scores),
        "strict": sum(score == 1.0 for score in scores) / len(scores),
        "relaxed": sum(scores) / len(scores),
        "score_counts": dict(sorted(Counter(str(score) for score in scores).items())),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    qwen25 = {
        str(row["question_id"]): row for row in load_jsonl(args.qwen25_results)
    }
    readr = {
        str(row["question_id"]): row for row in load_jsonl(args.readr_results)
    }
    shared = sorted(set(qwen25) & set(readr))
    if len(shared) < 7800:
        raise RuntimeError(f"unexpectedly small shared pool: {len(shared)}")

    rows: list[dict[str, Any]] = []
    for qid in shared:
        ours = qwen25[qid]
        baseline = readr[qid]
        if str(ours["video_id"]) != str(baseline["video"]):
            raise RuntimeError(f"video mismatch for {qid}")
        ours_score = float(ours["AdaptiveFinal_score"])
        readr_score = float(baseline["score"])
        rows.append(
            {
                "question_id": qid,
                "video": str(ours["video_id"]),
                "question_type": str(ours.get("question_type", "unknown")),
                "triggered": bool(ours.get("triggered")),
                "switched": bool(ours.get("switched")),
                "qwen25_final_score": ours_score,
                "readr_score": readr_score,
                "relaxed_delta_ours_minus_readr": ours_score - readr_score,
                "strict_delta_ours_minus_readr": (
                    float(ours_score == 1.0) - float(readr_score == 1.0)
                ),
            }
        )

    by_type: dict[str, Any] = {}
    for question_type in sorted({row["question_type"] for row in rows}):
        subset = [row for row in rows if row["question_type"] == question_type]
        by_type[question_type] = {
            "rows": len(subset),
            "qwen25_final": metrics(subset, "qwen25_final_score"),
            "readr": metrics(subset, "readr_score"),
            "strict_delta": sum(row["strict_delta_ours_minus_readr"] for row in subset)
            / len(subset),
            "relaxed_delta": sum(row["relaxed_delta_ours_minus_readr"] for row in subset)
            / len(subset),
        }

    relaxed = [row["relaxed_delta_ours_minus_readr"] for row in rows]
    strict = [row["strict_delta_ours_minus_readr"] for row in rows]
    transitions = Counter(
        f"{row['qwen25_final_score']}->{row['readr_score']}" for row in rows
    )
    summary = {
        "schema_version": "qwen25_final_vs_readr_full_paired_v1",
        "passed": True,
        "shared_rows": len(rows),
        "video_clusters": len({row["video"] for row in rows}),
        "qwen25_only": len(set(qwen25) - set(readr)),
        "readr_only": len(set(readr) - set(qwen25)),
        "qwen25_final": metrics(rows, "qwen25_final_score"),
        "readr": metrics(rows, "readr_score"),
        "paired": {
            "wins": sum(value > 0 for value in relaxed),
            "ties": sum(value == 0 for value in relaxed),
            "losses": sum(value < 0 for value in relaxed),
            "mean_strict_delta": sum(strict) / len(strict),
            "mean_relaxed_delta": sum(relaxed) / len(relaxed),
            "score_transition_counts_qwen25_to_readr": dict(sorted(transitions.items())),
            "video_cluster_bootstrap_ci95": {
                "strict_delta": bootstrap(
                    rows, "strict_delta_ours_minus_readr", args.bootstrap_samples
                ),
                "relaxed_delta": bootstrap(
                    rows, "relaxed_delta_ours_minus_readr", args.bootstrap_samples
                ),
                "samples": args.bootstrap_samples,
                "seed": 42,
            },
        },
        "by_question_type": by_type,
        "trigger_analysis": {
            "triggered": metrics(
                [row for row in rows if row["triggered"]], "qwen25_final_score"
            ),
            "not_triggered": metrics(
                [row for row in rows if not row["triggered"]], "qwen25_final_score"
            ),
            "switched_count": sum(row["switched"] for row in rows),
        },
        "inputs": {
            "qwen25_results_sha256": sha256(args.qwen25_results),
            "readr_results_sha256": sha256(args.readr_results),
        },
        "api_called": False,
        "not_human_gold": True,
    }
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "paired_results.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
