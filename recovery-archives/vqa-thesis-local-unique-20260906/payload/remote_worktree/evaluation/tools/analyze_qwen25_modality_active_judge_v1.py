#!/usr/bin/env python3
"""Analyze overall and frozen modality-active-subset OOF judge results."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Mapping, Sequence


METHOD_RAW = "B_Raw40"
METHOD_CLIP = "D_CLIPCrop40"
METHOD_AV = "E_ModalityActiveAVCrop40"
METHODS = (METHOD_RAW, METHOD_CLIP, METHOD_AV)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-results", required=True)
    parser.add_argument("--judge-provenance", required=True)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--gate-manifest", required=True)
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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def metrics(question_ids: Sequence[str], score_map: Mapping[tuple[str, str], float], method: str) -> dict[str, Any]:
    scores = [score_map[(method, question_id)] for question_id in question_ids]
    return {
        "n": len(scores),
        "strict": sum(score == 1.0 for score in scores) / len(scores),
        "relaxed": sum(scores) / len(scores),
        "score_counts": dict(sorted(Counter(str(score) for score in scores).items())),
    }


def clustered_pairwise(
    question_ids: Sequence[str],
    videos: Mapping[str, str],
    score_map: Mapping[tuple[str, str], float],
    first: str,
    second: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    by_video: dict[str, list[str]] = defaultdict(list)
    for question_id in question_ids:
        by_video[videos[question_id]].append(question_id)
    clusters = sorted(by_video)
    deltas = [score_map[(first, question_id)] - score_map[(second, question_id)] for question_id in question_ids]
    strict_deltas = [
        float(score_map[(first, question_id)] == 1.0) - float(score_map[(second, question_id)] == 1.0)
        for question_id in question_ids
    ]
    rng = random.Random(seed)
    boot_relaxed = []
    boot_strict = []
    for _ in range(samples):
        selected = [rng.choice(clusters) for _ in clusters]
        sampled_ids = [question_id for video in selected for question_id in by_video[video]]
        boot_relaxed.append(
            sum(score_map[(first, question_id)] - score_map[(second, question_id)] for question_id in sampled_ids)
            / len(sampled_ids)
        )
        boot_strict.append(
            sum(
                float(score_map[(first, question_id)] == 1.0) - float(score_map[(second, question_id)] == 1.0)
                for question_id in sampled_ids
            )
            / len(sampled_ids)
        )
    transitions = Counter(
        f"{score_map[(second, question_id)]:g}->{score_map[(first, question_id)]:g}"
        for question_id in question_ids
    )
    return {
        "n": len(question_ids),
        "video_cluster_count": len(clusters),
        "first_wins": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
        "second_wins": sum(delta < 0 for delta in deltas),
        "relaxed_delta_first_minus_second": sum(deltas) / len(deltas),
        "relaxed_delta_ci95": [percentile(boot_relaxed, 0.025), percentile(boot_relaxed, 0.975)],
        "strict_delta_first_minus_second": sum(strict_deltas) / len(strict_deltas),
        "strict_delta_ci95": [percentile(boot_strict, 0.025), percentile(boot_strict, 0.975)],
        "transitions_second_to_first": dict(sorted(transitions.items())),
        "bootstrap_samples": samples,
        "seed": seed,
    }


def main() -> None:
    args = parse_args()
    results_path = Path(args.judge_results).resolve()
    provenance_path = Path(args.judge_provenance).resolve()
    groundtruth_path = Path(args.groundtruth).resolve()
    gate_path = Path(args.gate_manifest).resolve()
    output_dir = Path(args.output_dir).resolve()
    rows = load_jsonl(results_path)
    if len(rows) != 1500:
        raise ValueError("judge results must contain three methods x 500 questions")
    score_map = {(str(row["method"]), str(row["question_id"])): float(row["score"]) for row in rows}
    if len(score_map) != 1500 or {method for method, _ in score_map} != set(METHODS):
        raise ValueError("judge results contain duplicate or unexpected method/question pairs")
    groundtruth = {str(row["question_id"]): row for row in json.loads(groundtruth_path.read_text(encoding="utf-8"))}
    gates = {str(row["question_id"]): row for row in load_jsonl(gate_path)}
    all_ids = sorted(gates, key=int)
    videos = {question_id: str(groundtruth[question_id]["video"]) for question_id in all_ids}
    subsets = {
        "overall": all_ids,
        "modality_active": [question_id for question_id in all_ids if gates[question_id]["gate_decision"]["modality_active"]],
        "clip_fallback": [question_id for question_id in all_ids if not gates[question_id]["gate_decision"]["modality_active"]],
    }
    for route in ("ocr_explicit", "asr_explicit", "asr_high_confidence"):
        subsets[route] = [
            question_id
            for question_id in all_ids
            if gates[question_id]["gate_decision"]["modality_route"] == route
        ]

    reports: dict[str, Any] = {}
    for subset_name, question_ids in subsets.items():
        if not question_ids:
            continue
        reports[subset_name] = {
            "question_count": len(question_ids),
            "video_count": len({videos[question_id] for question_id in question_ids}),
            "methods": {method: metrics(question_ids, score_map, method) for method in METHODS},
            "pairwise": {
                f"{first}__vs__{second}": clustered_pairwise(
                    question_ids, videos, score_map, first, second, args.samples, args.seed
                )
                for first, second in (
                    (METHOD_CLIP, METHOD_RAW),
                    (METHOD_AV, METHOD_RAW),
                    (METHOD_AV, METHOD_CLIP),
                )
            },
        }
    fallback_pair = reports["clip_fallback"]["pairwise"][f"{METHOD_AV}__vs__{METHOD_CLIP}"]
    passed = (
        len(subsets["overall"]) == 500
        and len(subsets["modality_active"]) == 147
        and fallback_pair["ties"] == len(subsets["clip_fallback"])
        and fallback_pair["first_wins"] == 0
        and fallback_pair["second_wins"] == 0
    )
    result = {
        "schema_version": "qwen25_modality_active_clustered_judge_analysis_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "bootstrap": {"unit": "video_cluster", "samples": args.samples, "seed": args.seed},
        "judge_results_sha256": sha256_file(results_path),
        "judge_provenance_sha256": sha256_file(provenance_path),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "gate_manifest_sha256": sha256_file(gate_path),
        "reports": reports,
        "decision_tree": {
            "full_av_claim": "requires AV>CLIP on the frozen active subset and no overall disadvantage to Raw40",
            "visual_only_claim": "use when AV and CLIP are indistinguishable but CLIP improves over Raw40",
            "localization_analysis_only": "use when neither crop method improves over Raw40",
            "thresholds_or_crop_budget_retuned_after_oof": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "modality_active_clustered_analysis_v1.json"
    output_path.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Modality-Active AVCrop40 OOF Analysis",
        "",
        f"Protocol passed: `{passed}`. Bootstrap: video clusters, {args.samples} samples, seed {args.seed}.",
        "",
        "| Subset | Method | N | Strict | Relaxed |",
        "|---|---|---:|---:|---:|",
    ]
    for subset_name, report in reports.items():
        for method in METHODS:
            item = report["methods"][method]
            lines.append(f"| {subset_name} | {method} | {item['n']} | {item['strict']:.4f} | {item['relaxed']:.4f} |")
    lines.extend(["", "## Paired Relaxed Deltas", "", "| Subset | Pair | Delta | 95% CI | W/T/L |", "|---|---|---:|---:|---:|"])
    for subset_name, report in reports.items():
        for pair, item in report["pairwise"].items():
            lines.append(
                f"| {subset_name} | {pair} | {item['relaxed_delta_first_minus_second']:.4f} | "
                f"[{item['relaxed_delta_ci95'][0]:.4f}, {item['relaxed_delta_ci95'][1]:.4f}] | "
                f"{item['first_wins']}/{item['ties']}/{item['second_wins']} |"
            )
    (output_dir / "modality_active_clustered_analysis_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
