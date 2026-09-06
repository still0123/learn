#!/usr/bin/env python3
"""Stratify judge results by ground-truth answer availability."""

import argparse
import itertools
import json
import random
from collections import Counter
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_results(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    methods = sorted({row["method"] for row in rows})
    scores = {method: {} for method in methods}
    for row in rows:
        scores[row["method"]][str(row["question_id"])] = float(row["score"])
    return methods, scores


def bootstrap_delta(first, second, ids, samples, seed):
    deltas = [first[qid] - second[qid] for qid in ids]
    rng = random.Random(seed)
    values = sorted(
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(samples)
    )
    return [values[int(0.025 * samples)], values[min(samples - 1, int(0.975 * samples))]]


def method_metrics(values):
    return {
        "n": len(values),
        "strict": sum(value == 1.0 for value in values) / len(values),
        "relaxed": sum(values) / len(values),
        "score_counts": dict(Counter(str(value) for value in values)),
    }


def analyze(methods, scores, groundtruth, samples, seed):
    gt = {str(row["question_id"]): row for row in groundtruth}
    common = set(gt)
    for method in methods:
        common &= set(scores[method])
    ordered = [str(row["question_id"]) for row in groundtruth if str(row["question_id"]) in common]
    strata = {
        "all": ordered,
        "nonempty_answer": [qid for qid in ordered if str(gt[qid].get("answer", "")).strip()],
        "empty_answer": [qid for qid in ordered if not str(gt[qid].get("answer", "")).strip()],
    }
    report = {"methods": methods, "strata": {}, "bootstrap_samples": samples, "seed": seed}
    for stratum, ids in strata.items():
        method_report = {method: method_metrics([scores[method][qid] for qid in ids]) for method in methods}
        pairwise = {}
        for first, second in itertools.combinations(methods, 2):
            deltas = [scores[first][qid] - scores[second][qid] for qid in ids]
            pairwise[f"{first}__vs__{second}"] = {
                "first_wins": sum(delta > 0 for delta in deltas),
                "ties": sum(delta == 0 for delta in deltas),
                "second_wins": sum(delta < 0 for delta in deltas),
                "mean_delta": sum(deltas) / len(deltas),
                "mean_delta_ci95": bootstrap_delta(scores[first], scores[second], ids, samples, seed),
            }
        report["strata"][stratum] = {
            "n": len(ids),
            "question_ids": ids,
            "primary_type_counts": dict(Counter(gt[qid].get("question_type", [None])[0] for qid in ids)),
            "methods": method_report,
            "pairwise": pairwise,
        }
    return report


def render_markdown(report):
    lines = ["# Ground-truth Answer Availability Audit", ""]
    for stratum, data in report["strata"].items():
        lines += [f"## {stratum} (n={data['n']})", "", "| Method | Strict | Relaxed | 1/0.5/0 |", "|---|---:|---:|---:|"]
        for method, metrics in data["methods"].items():
            counts = metrics["score_counts"]
            lines.append(
                f"| {method} | {metrics['strict']:.2%} | {metrics['relaxed']:.2%} | "
                f"{counts.get('1.0', 0)}/{counts.get('0.5', 0)}/{counts.get('0.0', 0)} |"
            )
        lines.append("")
    lines += [
        "## Interpretation", "",
        "Rows with an empty ground-truth answer are not standard answer-reference evaluations. "
        "They may still receive scores because the legacy prompt includes meta-information, but must be reported separately.", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-jsonl", required=True)
    parser.add_argument("--groundtruth-file", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    methods, scores = load_results(args.results_jsonl)
    report = analyze(methods, scores, load_json(args.groundtruth_file), args.bootstrap_samples, args.seed)
    Path(args.out_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.out_md).write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({name: data["n"] for name, data in report["strata"].items()}))


if __name__ == "__main__":
    main()
