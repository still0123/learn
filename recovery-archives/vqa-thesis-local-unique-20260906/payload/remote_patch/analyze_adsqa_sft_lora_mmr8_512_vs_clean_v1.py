#!/usr/bin/env python3
"""Pair AdsSFTLoRA MMR8-512 scores with clean Qwen2.5 MMR8 scores."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lora-results", type=Path, required=True)
    parser.add_argument("--clean-paired", type=Path, required=True)
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    lora = {
        str(row["question_id"]): row
        for row in load_jsonl(args.lora_results)
        if row.get("method") == "AdsSFTLoRA_MMR8_512"
    }
    clean = {str(row["question_id"]): row for row in load_jsonl(args.clean_paired)}
    if len(lora) != 500 or len(clean) != 500 or set(lora) != set(clean):
        raise RuntimeError("paired inputs must contain the same 500 question IDs")

    paired: list[dict[str, Any]] = []
    for question_id in sorted(lora):
        lora_score = float(lora[question_id]["score"])
        clean_score = float(clean[question_id]["MMR8_score"])
        video = str(lora[question_id]["video"])
        if video != str(clean[question_id]["video_id"]):
            raise RuntimeError(f"video mismatch for question {question_id}")
        paired.append(
            {
                "question_id": question_id,
                "video": video,
                "lora512_score": lora_score,
                "clean512_score": clean_score,
                "relaxed_delta_lora_minus_clean": lora_score - clean_score,
                "strict_delta_lora_minus_clean": (
                    float(lora_score == 1.0) - float(clean_score == 1.0)
                ),
            }
        )

    relaxed = [row["relaxed_delta_lora_minus_clean"] for row in paired]
    strict = [row["strict_delta_lora_minus_clean"] for row in paired]
    summary = {
        "schema_version": "adsqa_sft_lora_mmr8_512_vs_clean_paired_v1",
        "passed": True,
        "rows": len(paired),
        "video_clusters": len({row["video"] for row in paired}),
        "lora512": {
            "strict": sum(row["lora512_score"] == 1.0 for row in paired) / len(paired),
            "relaxed": sum(row["lora512_score"] for row in paired) / len(paired),
        },
        "clean512": {
            "strict": sum(row["clean512_score"] == 1.0 for row in paired) / len(paired),
            "relaxed": sum(row["clean512_score"] for row in paired) / len(paired),
        },
        "paired_lora_minus_clean": {
            "wins": sum(value > 0 for value in relaxed),
            "ties": sum(value == 0 for value in relaxed),
            "losses": sum(value < 0 for value in relaxed),
            "mean_strict_delta": sum(strict) / len(strict),
            "mean_relaxed_delta": sum(relaxed) / len(relaxed),
            "video_cluster_bootstrap_ci95": {
                "strict_delta": bootstrap(
                    paired,
                    "strict_delta_lora_minus_clean",
                    args.bootstrap_samples,
                ),
                "relaxed_delta": bootstrap(
                    paired,
                    "relaxed_delta_lora_minus_clean",
                    args.bootstrap_samples,
                ),
                "samples": args.bootstrap_samples,
                "seed": 42,
            },
        },
        "inputs": {
            "lora_results_sha256": sha256_file(args.lora_results),
            "clean_paired_sha256": sha256_file(args.clean_paired),
        },
        "api_called": False,
        "not_human_gold": True,
    }
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "paired_vs_clean500.jsonl").open("w", encoding="utf-8") as handle:
        for row in paired:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output_root / "summary_vs_clean.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
