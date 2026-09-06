#!/usr/bin/env python3
"""Analyze innovation-2 corrections after the immutable DeepSeek evaluation."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def trace_map(root: str) -> dict[str, dict[str, Any]]:
    return {
        str(row["question_id"]): row
        for path in Path(root).glob("shard*of3/trace/*/evidence.json")
        for row in [load_json(str(path))]
    }


def transition_summary(initial: str, final: str, scores: dict[tuple[str, str], float], questions: dict[str, dict[str, Any]], traces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    transitions: Counter[str] = Counter()
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    cases = []
    shared = 0
    for qid, item in questions.items():
        if (initial, qid) not in scores or (final, qid) not in scores:
            continue
        shared += 1
        before, after = scores[(initial, qid)], scores[(final, qid)]
        key = f"{before:g}->{after:g}"
        transitions[key] += 1
        category = str((item.get("question_type") or ["unknown"])[0])
        by_category[category][key] += 1
        if before != after:
            trace = traces.get(qid, {})
            cases.append({
                "question_id": qid,
                "category": category,
                "question": item.get("question"),
                "ground_truth": item.get("answer"),
                "score_before": before,
                "score_after": after,
                "initial_answer": trace.get("initial_answer"),
                "final_answer": trace.get("final_answer"),
                "support_plus": trace.get("support_plus"),
                "support_minus": trace.get("support_minus"),
                "rescue_reasons": (trace.get("rescue") or {}).get("reasons"),
            })
    return {
        "shared": shared,
        "transitions": dict(sorted(transitions.items())),
        "strict_wrong_to_correct": transitions["0->1"],
        "strict_correct_to_wrong": transitions["1->0"],
        "by_category": {category: dict(sorted(values.items())) for category, values in sorted(by_category.items())},
        "changed_cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groundtruth_file", required=True)
    parser.add_argument("--results_jsonl", required=True)
    parser.add_argument("--raw_trace_root", required=True)
    parser.add_argument("--mmr_trace_root", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()
    questions = {str(row["question_id"]): row for row in load_json(args.groundtruth_file)}
    scores = {
        (str(row["method"]), str(row["question_id"])): float(row["score"])
        for row in load_jsonl(args.results_jsonl)
        if row.get("score") in {0.0, 0.5, 1.0}
    }
    raw_traces = trace_map(args.raw_trace_root)
    mmr_traces = trace_map(args.mmr_trace_root)
    methods = {
        "raw": "raw_uniform",
        "raw_plus2": "raw_plus_counterfactual2",
        "mmr": "innovation1_mmr32",
        "mmr_plus2": "innovation1_mmr32_plus_counterfactual2",
    }
    result = {
        "schema": "adsqa_counterfactual_dev100_analysis_v1",
        "question_count": len(questions),
        "raw_plus2": transition_summary(methods["raw"], methods["raw_plus2"], scores, questions, raw_traces),
        "mmr_plus2": transition_summary(methods["mmr"], methods["mmr_plus2"], scores, questions, mmr_traces),
        "raw_trace_mechanism": {
            "count": len(raw_traces),
            "rescue_triggered": sum(bool((row.get("rescue") or {}).get("triggered")) for row in raw_traces.values()),
            "switched": sum(bool((row.get("rescue") or {}).get("decision", {}).get("switched")) for row in raw_traces.values()),
            "positive_counterfactual_delta": sum(float(row.get("support_delta", 0.0)) > 0 for row in raw_traces.values()),
        },
        "mmr_trace_mechanism": {
            "count": len(mmr_traces),
            "rescue_triggered": sum(bool((row.get("rescue") or {}).get("triggered")) for row in mmr_traces.values()),
            "switched": sum(bool((row.get("rescue") or {}).get("decision", {}).get("switched")) for row in mmr_traces.values()),
            "positive_counterfactual_delta": sum(float(row.get("support_delta", 0.0)) > 0 for row in mmr_traces.values()),
        },
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "counterfactual_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cases = result["raw_plus2"]["changed_cases"] + result["mmr_plus2"]["changed_cases"]
    (output_dir / "changed_cases.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in cases), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("raw_plus2", "mmr_plus2", "raw_trace_mechanism", "mmr_trace_mechanism")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
