#!/usr/bin/env python3
"""Explain per-question judge changes introduced by OCR evidence fusion."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


TEXT_INTENT_PATTERNS = {
    "explicit_text": re.compile(
        r"\b(text|word|phrase|written|write|read|say|says|shown|displayed|caption|label|sign)\b",
        re.IGNORECASE,
    ),
    "brand_or_cta": re.compile(
        r"\b(brand|logo|slogan|tagline|call[- ]to[- ]action|website|url)\b",
        re.IGNORECASE,
    ),
    "numeric": re.compile(
        r"\b(price|cost|number|amount|date|time|percent|percentage|phone)\b",
        re.IGNORECASE,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-results", required=True)
    parser.add_argument("--baseline-method", required=True)
    parser.add_argument("--candidate-method", required=True)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--baseline-run")
    parser.add_argument("--candidate-run")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def load_judge_rows(path: str | Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["method"]), str(row["question_id"]))
        if key in rows:
            raise ValueError(f"duplicate judge row: {key}")
        rows[key] = row
    return rows


def load_groundtruth(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("ground truth must be a JSON list")
    return {str(row["question_id"]): row for row in payload}


def index_run(run_dir: str | None) -> dict[str, dict[str, Path]]:
    if not run_dir:
        return {}
    root = Path(run_dir)
    indexed: dict[str, dict[str, Path]] = {}
    for name in ("prediction.json", "evidence.json"):
        for path in root.rglob(name):
            indexed.setdefault(path.parent.name, {})[name] = path
    return indexed


def read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def classify_text_intent(question: str) -> list[str]:
    return [name for name, pattern in TEXT_INTENT_PATTERNS.items() if pattern.search(question)]


def summarize_ocr(evidence: dict[str, Any] | None) -> dict[str, Any] | None:
    if not evidence:
        return None
    active = []
    texts: list[str] = []
    for trace in evidence.get("response_traces", []):
        ocr_trace = trace.get("ocr_trace") or {}
        weight = (trace.get("fusion") or {}).get("weights", {}).get("ocr")
        if ocr_trace.get("mode") == "off" and weight is None:
            continue
        active.append(
            {
                "frame_rank": trace.get("frame_rank"),
                "weight": weight,
                "source_reliability": ocr_trace.get("source_reliability"),
                "max_weighted_score": ocr_trace.get("max_weighted_score"),
                "semantic_scores": ocr_trace.get("semantic_scores", []),
                "texts": ocr_trace.get("texts", []),
            }
        )
        texts.extend(str(text) for text in ocr_trace.get("texts", []) if str(text).strip())
    return {
        "active_frame_count": len(active),
        "max_fusion_weight": max(
            (float(item["weight"]) for item in active if item["weight"] is not None),
            default=None,
        ),
        "max_source_reliability": max(
            (
                float(item["source_reliability"])
                for item in active
                if item["source_reliability"] is not None
            ),
            default=None,
        ),
        "unique_texts": list(dict.fromkeys(texts)),
        "active_frames": active,
    }


def prediction_text(index: dict[str, dict[str, Path]], question_id: str) -> str | None:
    payload = read_json(index.get(question_id, {}).get("prediction.json"))
    return None if not payload else payload.get("prediction")


def selected_view_ids(evidence: dict[str, Any] | None) -> list[str]:
    if not evidence:
        return []
    values = []
    for view in evidence.get("selected_local_views", []):
        values.append(str(view.get("candidate_id", view.get("view_id", ""))))
    return values


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    judge = load_judge_rows(args.judge_results)
    groundtruth = load_groundtruth(args.groundtruth)
    baseline_index = index_run(args.baseline_run)
    candidate_index = index_run(args.candidate_run)
    question_ids = sorted(
        qid
        for method, qid in judge
        if method == args.baseline_method and (args.candidate_method, qid) in judge
    )
    changed = []
    all_deltas = []
    for qid in question_ids:
        baseline_score = float(judge[(args.baseline_method, qid)]["score"])
        candidate_score = float(judge[(args.candidate_method, qid)]["score"])
        delta = candidate_score - baseline_score
        all_deltas.append(delta)
        if delta == 0.0:
            continue
        gt = groundtruth.get(qid, {})
        baseline_evidence = read_json(baseline_index.get(qid, {}).get("evidence.json"))
        candidate_evidence = read_json(candidate_index.get(qid, {}).get("evidence.json"))
        question = str(gt.get("question", ""))
        changed.append(
            {
                "question_id": qid,
                "question": question,
                "ground_truth": gt.get("answer"),
                "question_types": gt.get("question_type", []),
                "text_intent_hints": classify_text_intent(question),
                "baseline_score": baseline_score,
                "candidate_score": candidate_score,
                "candidate_minus_baseline": delta,
                "baseline_prediction": prediction_text(baseline_index, qid),
                "candidate_prediction": prediction_text(candidate_index, qid),
                "baseline_selected_view_ids": selected_view_ids(baseline_evidence),
                "candidate_selected_view_ids": selected_view_ids(candidate_evidence),
                "ocr": summarize_ocr(candidate_evidence),
            }
        )
    intent_counts = Counter(
        "text_intent" if row["text_intent_hints"] else "no_text_intent" for row in changed
    )
    return {
        "judge_results": str(Path(args.judge_results).resolve()),
        "baseline_method": args.baseline_method,
        "candidate_method": args.candidate_method,
        "shared": len(question_ids),
        "candidate_wins": sum(delta > 0 for delta in all_deltas),
        "ties": sum(delta == 0 for delta in all_deltas),
        "candidate_losses": sum(delta < 0 for delta in all_deltas),
        "mean_candidate_minus_baseline": sum(all_deltas) / len(all_deltas),
        "changed_text_intent_counts": dict(intent_counts),
        "changed": changed,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# OCR Judge Boundary Analysis",
        "",
        f"- Comparison: `{payload['candidate_method']}` minus `{payload['baseline_method']}`",
        f"- Shared: {payload['shared']}",
        (
            f"- Candidate wins/ties/losses: {payload['candidate_wins']} / "
            f"{payload['ties']} / {payload['candidate_losses']}"
        ),
        f"- Mean score delta: {payload['mean_candidate_minus_baseline']:+.4f}",
        f"- Changed intent counts: `{json.dumps(payload['changed_text_intent_counts'], sort_keys=True)}`",
        "",
        "| Question ID | Delta | Text intent | Question | OCR max weight | OCR max reliability | OCR text excerpt |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for row in payload["changed"]:
        ocr = row.get("ocr") or {}
        texts = "; ".join(ocr.get("unique_texts", []))[:160]
        question = row["question"].replace("|", "\\|")
        text_intent = ", ".join(row["text_intent_hints"]) or "none"
        weight = ocr.get("max_fusion_weight")
        reliability = ocr.get("max_source_reliability")
        text_excerpt = texts.replace("|", "\\|")
        lines.append(
            f"| `{row['question_id']}` | {row['candidate_minus_baseline']:+.1f} | "
            f"{text_intent} | {question} | "
            f"{weight if weight is not None else 'n/a'} | "
            f"{reliability if reliability is not None else 'n/a'} | "
            f"{text_excerpt} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "changed"}, indent=2))


if __name__ == "__main__":
    main()
