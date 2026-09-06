#!/usr/bin/env python3
"""Video-clustered analysis and frozen gate decision for FreshQ-500."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Mapping, Sequence


RAW = "B_Raw40"
CROP = "D_CLIPCrop40"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-results", required=True)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--protocol-audit", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def primary_type(row: Mapping[str, Any]) -> str:
    value = row.get("question_type", [])
    return str(value[0]) if isinstance(value, list) and value else str(value)


def report(
    question_ids: Sequence[str],
    groundtruth: Mapping[str, Mapping[str, Any]],
    scores: Mapping[tuple[str, str], float],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    videos: dict[str, list[str]] = defaultdict(list)
    for qid in question_ids:
        videos[str(groundtruth[qid]["video"])].append(qid)
    video_ids = sorted(videos)
    raw_scores = [scores[(RAW, qid)] for qid in question_ids]
    crop_scores = [scores[(CROP, qid)] for qid in question_ids]
    deltas = [crop - raw for raw, crop in zip(raw_scores, crop_scores)]
    strict_deltas = [float(crop == 1.0) - float(raw == 1.0) for raw, crop in zip(raw_scores, crop_scores)]
    rng = random.Random(seed)
    relaxed_samples = []
    strict_samples = []
    for _ in range(samples):
        sampled_videos = [rng.choice(video_ids) for _ in video_ids]
        sampled_qids = [qid for video in sampled_videos for qid in videos[video]]
        relaxed_samples.append(
            sum(scores[(CROP, qid)] - scores[(RAW, qid)] for qid in sampled_qids)
            / len(sampled_qids)
        )
        strict_samples.append(
            sum(
                float(scores[(CROP, qid)] == 1.0) - float(scores[(RAW, qid)] == 1.0)
                for qid in sampled_qids
            )
            / len(sampled_qids)
        )
    transitions = Counter(
        f"{scores[(RAW, qid)]:g}->{scores[(CROP, qid)]:g}" for qid in question_ids
    )
    return {
        "question_count": len(question_ids),
        "video_count": len(video_ids),
        "raw": {
            "strict": sum(score == 1.0 for score in raw_scores) / len(raw_scores),
            "relaxed": sum(raw_scores) / len(raw_scores),
        },
        "clipcrop": {
            "strict": sum(score == 1.0 for score in crop_scores) / len(crop_scores),
            "relaxed": sum(crop_scores) / len(crop_scores),
        },
        "pairwise": {
            "crop_wins": sum(delta > 0 for delta in deltas),
            "ties": sum(delta == 0 for delta in deltas),
            "raw_wins": sum(delta < 0 for delta in deltas),
            "relaxed_delta_crop_minus_raw": sum(deltas) / len(deltas),
            "relaxed_delta_ci95": [
                percentile(relaxed_samples, 0.025),
                percentile(relaxed_samples, 0.975),
            ],
            "strict_delta_crop_minus_raw": sum(strict_deltas) / len(strict_deltas),
            "strict_delta_ci95": [
                percentile(strict_samples, 0.025),
                percentile(strict_samples, 0.975),
            ],
            "transitions": dict(sorted(transitions.items())),
        },
    }


def main() -> None:
    args = parse_args()
    judge_path = Path(args.judge_results).resolve()
    groundtruth_path = Path(args.groundtruth).resolve()
    protocol_audit_path = Path(args.protocol_audit).resolve()
    output_dir = Path(args.output_dir).resolve()
    protocol_audit = json.loads(protocol_audit_path.read_text(encoding="utf-8"))
    if protocol_audit.get("passed") is not True:
        raise ValueError("formal protocol audit did not pass")
    rows = [
        json.loads(line)
        for line in judge_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scores = {
        (str(row["method"]), str(row["question_id"])): float(row["score"])
        for row in rows
    }
    groundtruth_rows = json.loads(groundtruth_path.read_text(encoding="utf-8"))
    groundtruth = {str(row["question_id"]): row for row in groundtruth_rows}
    question_ids = sorted(groundtruth)
    expected_pairs = {(method, qid) for method in (RAW, CROP) for qid in question_ids}
    if len(question_ids) != 500 or set(scores) != expected_pairs:
        raise ValueError("judge results must contain exactly two methods for 500 questions")
    reports = {
        "overall": report(
            question_ids,
            groundtruth,
            scores,
            samples=args.samples,
            seed=args.seed,
        )
    }
    for qtype in [f"Type_{index}" for index in range(1, 6)]:
        subset = [qid for qid in question_ids if primary_type(groundtruth[qid]) == qtype]
        reports[qtype] = report(
            subset,
            groundtruth,
            scores,
            samples=args.samples,
            seed=args.seed,
        )
    overall = reports["overall"]["pairwise"]
    type_deltas = {
        qtype: reports[qtype]["pairwise"]["relaxed_delta_crop_minus_raw"]
        for qtype in [f"Type_{index}" for index in range(1, 6)]
    }
    gates = {
        "relaxed_point_positive": overall["relaxed_delta_crop_minus_raw"] > 0.0,
        "relaxed_ci_lower_nonnegative": overall["relaxed_delta_ci95"][0] >= 0.0,
        "strict_point_nonnegative": overall["strict_delta_crop_minus_raw"] >= 0.0,
        "wins_exceed_losses": overall["crop_wins"] > overall["raw_wins"],
        "no_type_relaxed_drop_below_minus_5pp": min(type_deltas.values()) >= -0.05,
    }
    result = {
        "schema_version": "qwen25_clipcrop_freshq500_clustered_analysis_v1",
        "passed": True,
        "bootstrap": {"unit": "video_cluster", "samples": args.samples, "seed": args.seed},
        "reports": reports,
        "frozen_confirmation_gates": gates,
        "confirmation_passed": all(gates.values()),
        "limitations": {
            "question_disjoint_from_prior_sets": True,
            "video_disjoint_from_prior_sets": False,
            "selected_questions_have_unique_videos": True,
        },
        "judge_results_sha256": sha256_file(judge_path),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "protocol_audit_sha256": sha256_file(protocol_audit_path),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "freshq500_clustered_analysis_v1.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# FreshQ-500 Frozen Confirmation",
        "",
        f"Confirmation passed: `{str(result['confirmation_passed']).lower()}`",
        "",
        "| Group | Raw Strict | Raw Relaxed | Crop Strict | Crop Relaxed | Relaxed delta |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, item in reports.items():
        lines.append(
            f"| {name} | {item['raw']['strict']:.4f} | {item['raw']['relaxed']:.4f} | "
            f"{item['clipcrop']['strict']:.4f} | {item['clipcrop']['relaxed']:.4f} | "
            f"{item['pairwise']['relaxed_delta_crop_minus_raw']:+.4f} |"
        )
    (output_dir / "freshq500_clustered_analysis_v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
