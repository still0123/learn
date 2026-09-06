#!/usr/bin/env python3
"""Analyze answer transitions and reflection behavior after the fixed-input judge."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/data1/rmx/projectb/AdsQA-main")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from evaluation.methods.evidence_reflection.reflection_protocol import extract_answer_section


def load_scores(path: Path) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        score = row.get("score")
        if score is not None:
            result[str(row["method"])][str(row["question_id"])] = float(score)
    return result


def transition(base: float, new: float) -> str:
    if base == new:
        return "unchanged"
    if base < 1.0 and new == 1.0:
        return "wrong_to_correct"
    if base == 1.0 and new < 1.0:
        return "correct_to_wrong"
    if new > base:
        return "partial_improvement"
    return "partial_regression"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-dir", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    judge_dir = Path(args.judge_dir)
    run_root = Path(args.run_root)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    qids = [str(row["question_id"]) for row in questions]
    type_by_id = {str(row["question_id"]): (row.get("question_type") or ["unknown"])[0] for row in questions}
    scores = load_scores(judge_dir / "results.jsonl")
    base = scores["raw_uniform"]
    methods = ["generic", "structured", "conservative"]
    report: dict[str, Any] = {
        "schema": "adsqa_evidence_reflection_analysis_v1",
        "judge_dir": str(judge_dir),
        "question_count": len(qids),
        "methods": {},
    }
    for method in methods:
        current = scores[method]
        if set(current) != set(qids) or set(base) != set(qids):
            raise RuntimeError(f"incomplete scores for {method}")
        transitions = Counter()
        deltas = []
        by_type: dict[str, Counter] = defaultdict(Counter)
        for qid in qids:
            kind = transition(base[qid], current[qid])
            transitions[kind] += 1
            deltas.append(current[qid] - base[qid])
            by_type[type_by_id[qid]][kind] += 1
        trace_files = sorted((run_root / method).glob("*/reflection.json"))
        parse_status = Counter()
        decisions = Counter()
        changed = 0
        for path in trace_files:
            trace = json.loads(path.read_text(encoding="utf-8"))
            parsed = trace.get("reflection_parsed", {})
            parse_status[str(parsed.get("parse_status", "unknown"))] += 1
            decisions[str(parsed.get("decision", "unknown"))] += 1
            draft_answer = extract_answer_section(str(trace.get("draft_answer", "")))
            prediction = json.loads((run_root / method / path.parent.name / "prediction.json").read_text(encoding="utf-8"))
            final_answer = str(prediction.get("prediction", ""))
            if draft_answer.strip() != final_answer.strip():
                changed += 1
        report["methods"][method] = {
            "n": len(qids),
            "mean_score_delta_vs_raw": sum(deltas) / len(deltas),
            "strict_delta_vs_raw": sum(current[qid] == 1.0 for qid in qids) / len(qids) - sum(base[qid] == 1.0 for qid in qids) / len(qids),
            "relaxed_delta_vs_raw": sum(deltas) / len(deltas),
            "transitions": dict(sorted(transitions.items())),
            "by_primary_type": {key: dict(sorted(value.items())) for key, value in sorted(by_type.items())},
            "reflection_parse_status": dict(sorted(parse_status.items())),
            "reflection_decisions": dict(sorted(decisions.items())),
            "trace_count": len(trace_files),
            "parsed_final_answer_changed_count": changed,
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
