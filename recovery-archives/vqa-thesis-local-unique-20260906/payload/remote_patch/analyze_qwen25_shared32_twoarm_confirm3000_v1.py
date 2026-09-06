#!/usr/bin/env python3
"""Analyze the frozen two-arm Confirm-3000 judge with video-cluster bootstrap."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
from typing import Any


METHODS = ("Shared32_ExtraGlobal8", "Shared32_Local8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def clustered_delta(
    qids_by_video: dict[str, list[str]],
    scores: dict[tuple[str, str], float],
    first: str,
    second: str,
    rng: random.Random,
) -> tuple[float, float]:
    videos = sorted(qids_by_video)
    sampled_videos = [rng.choice(videos) for _ in videos]
    sampled_qids = [qid for video in sampled_videos for qid in qids_by_video[video]]
    relaxed = [scores[(first, qid)] - scores[(second, qid)] for qid in sampled_qids]
    strict = [
        float(scores[(first, qid)] == 1.0) - float(scores[(second, qid)] == 1.0)
        for qid in sampled_qids
    ]
    return sum(relaxed) / len(relaxed), sum(strict) / len(strict)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--judge-results", required=True)
    parser.add_argument("--protocol-audit", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    groundtruth_path = Path(args.groundtruth).resolve()
    judge_path = Path(args.judge_results).resolve()
    audit_path = Path(args.protocol_audit).resolve()
    output_dir = Path(args.output_dir).resolve()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("passed") is not True:
        raise ValueError("Shared32 protocol audit did not pass")
    groundtruth_rows = json.loads(groundtruth_path.read_text(encoding="utf-8"))
    groundtruth = {str(row["question_id"]): row for row in groundtruth_rows}
    if len(groundtruth) != len(groundtruth_rows) or not groundtruth:
        raise ValueError("groundtruth question IDs must be unique and non-empty")
    qids = sorted(groundtruth)
    qids_by_video: dict[str, list[str]] = defaultdict(list)
    for qid in qids:
        qids_by_video[str(groundtruth[qid]["video"])].append(qid)
    rows = [
        json.loads(line)
        for line in judge_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected = {(method, qid) for method in METHODS for qid in qids}
    scores: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (str(row["method"]), str(row["question_id"]))
        if key in scores:
            raise ValueError(f"duplicate judge row: {key}")
        score = float(row["score"])
        if score not in {0.0, 0.5, 1.0}:
            raise ValueError(f"invalid score {score} for {key}")
        scores[key] = score
    if set(scores) != expected:
        missing = sorted(expected - set(scores))[:10]
        extra = sorted(set(scores) - expected)[:10]
        raise ValueError(f"judge coverage mismatch; missing={missing}, extra={extra}")

    def metrics(ids: list[str]) -> dict[str, Any]:
        values = [scores[(method, qid)] for method in METHODS for qid in ids]
        by_method = {}
        for method in METHODS:
            method_values = [scores[(method, qid)] for qid in ids]
            by_method[method] = {
                "n": len(method_values),
                "strict": sum(value == 1.0 for value in method_values) / len(method_values),
                "relaxed": sum(method_values) / len(method_values),
                "score_counts": dict(sorted(Counter(str(value) for value in method_values).items())),
            }
        return {"n": len(ids), "methods": by_method, "all_score_count": len(values)}

    method_metrics = metrics(qids)
    type_ids: dict[str, list[str]] = defaultdict(list)
    for qid in qids:
        raw_type = groundtruth[qid].get("question_type", "unknown")
        types = raw_type if isinstance(raw_type, list) else [raw_type]
        for item in types or ["unknown"]:
            type_ids[str(item)].append(qid)
    by_type = {name: metrics(sorted(ids)) for name, ids in sorted(type_ids.items())}

    first, second = METHODS
    deltas = [scores[(first, qid)] - scores[(second, qid)] for qid in qids]
    strict_deltas = [
        float(scores[(first, qid)] == 1.0) - float(scores[(second, qid)] == 1.0)
        for qid in qids
    ]
    rng = random.Random(args.seed)
    relaxed_samples = []
    strict_samples = []
    for _ in range(args.samples):
        relaxed, strict = clustered_delta(qids_by_video, scores, first, second, rng)
        relaxed_samples.append(relaxed)
        strict_samples.append(strict)
    pairwise = {
        "first": first,
        "second": second,
        "first_wins": sum(delta > 0 for delta in deltas),
        "ties": sum(delta == 0 for delta in deltas),
        "second_wins": sum(delta < 0 for delta in deltas),
        "relaxed_delta_first_minus_second": sum(deltas) / len(deltas),
        "strict_delta_first_minus_second": sum(strict_deltas) / len(strict_deltas),
        "video_cluster_bootstrap": {
            "samples": args.samples,
            "seed": args.seed,
            "relaxed_ci95": [percentile(relaxed_samples, 0.025), percentile(relaxed_samples, 0.975)],
            "strict_ci95": [percentile(strict_samples, 0.025), percentile(strict_samples, 0.975)],
        },
    }
    result = {
        "schema_version": "qwen25_confirm3000_shared32_twoarm_clustered_analysis_v1",
        "passed": True,
        "question_count": len(qids),
        "video_count": len(qids_by_video),
        "methods": method_metrics["methods"],
        "by_question_type": by_type,
        "pairwise": pairwise,
        "bootstrap_unit": "video_cluster",
        "judge_results_sha256": sha256_file(judge_path),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "protocol_audit_sha256": sha256_file(audit_path),
        "not_human_gold": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "confirm3000_shared32_twoarm_clustered_analysis_v1.json"
    output_path.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Confirm-3000 Shared32 Two-Arm Frozen Analysis",
        "",
        f"Questions: `{len(qids)}`; videos: `{len(qids_by_video)}`; bootstrap: `video_cluster/{args.samples}`",
        "",
        "| Method | Strict | Relaxed |",
        "|---|---:|---:|",
    ]
    for method in METHODS:
        item = method_metrics["methods"][method]
        lines.append(f"| {method} | {item['strict']:.4f} | {item['relaxed']:.4f} |")
    lines.extend(["", "| Pair | Relaxed delta | 95% CI | Strict delta | 95% CI |", "|---|---:|---|---:|---|"])
    boot = pairwise["video_cluster_bootstrap"]
    lines.append(
        f"| {first} vs {second} | {pairwise['relaxed_delta_first_minus_second']:+.4f} | "
        f"[{boot['relaxed_ci95'][0]:+.4f}, {boot['relaxed_ci95'][1]:+.4f}] | "
        f"{pairwise['strict_delta_first_minus_second']:+.4f} | "
        f"[{boot['strict_ci95'][0]:+.4f}, {boot['strict_ci95'][1]:+.4f}] |"
    )
    (output_dir / "confirm3000_shared32_twoarm_clustered_analysis_v1.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
