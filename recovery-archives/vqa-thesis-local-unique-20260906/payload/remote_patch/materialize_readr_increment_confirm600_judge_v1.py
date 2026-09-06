#!/usr/bin/env python3
"""Materialize frozen ReAd-R Confirm-600 final candidates for answer-only judging."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHODS = {
    "Uniform8": ("uniform8", "prediction.json", "ReAdR_Uniform8"),
    "MMR8": ("mmr8", "prediction.json", "ReAdR_MMR8"),
}
TAU = 0.9241418242454529
MARGIN = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--groundtruth-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def answer_from(record: dict[str, Any]) -> str:
    for field in ("answer", "gt_answer", "answers"):
        value = record.get(field)
        if isinstance(value, list):
            value = next((item for item in value if str(item).strip()), "")
        text = str(value or "").strip()
        if text:
            return text
    raise RuntimeError(f"no reference answer: {record.get('question_id')}")


def prediction(root: Path, arm: str, fold: int, qid: str, filename: str, method: str) -> str:
    path = root / arm / f"fold_{fold}" / qid / filename
    row = json.loads(path.read_text())
    value = str(row.get("prediction", "")).strip()
    if str(row.get("question_id")) != qid or str(row.get("method")) != method or not value:
        raise RuntimeError(f"invalid prediction: {path}")
    return value


def main() -> None:
    args = parse_args()
    root = args.run_root.resolve()
    out = args.output_root.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"refusing to overwrite nonempty output: {out}")
    if not (root / "INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION").is_file():
        raise RuntimeError("inference is not complete")
    questions = json.loads((root / "inputs_v1/questions_answer_free.json").read_text())
    if (
        len(questions) != 600
        or len({str(row["question_id"]) for row in questions}) != 600
        or any(row.get("answer_free") is not True for row in questions)
        or {str(row.get("evaluation_partition")) for row in questions} != {"confirm600"}
    ):
        raise RuntimeError("invalid Confirm-600 question pool")

    audit_paths = {
        "Uniform8": root / "uniform8/protocol_audit.json",
        "MMR8": root / "mmr8/protocol_audit.json",
        "Adaptive12": root / "adaptive12_protocol_audit.json",
        "ExtraGlobal12": root / "extra_global12_protocol_audit.json",
    }
    audit_summary = {}
    for name, path in audit_paths.items():
        audit = json.loads(path.read_text())
        if audit.get("passed") is not True:
            raise RuntimeError(f"failed source audit: {name}")
        audit_summary[name] = {"sha256": sha256_file(path), "path": str(path)}

    a0_rows = load_jsonl(root / "mmr8_verifier_merged/scores_all.jsonl")
    adaptive_rows = load_jsonl(root / "adaptive12_verifier_merged/scores_all.jsonl")
    extra_rows = load_jsonl(root / "extra_global12_verifier_merged/scores_all.jsonl")
    a0 = {str(row["source_question_id"]): float(row["support_probability"]) for row in a0_rows}
    adaptive = {str(row["source_question_id"]): float(row["support_probability"]) for row in adaptive_rows}
    extra = {str(row["source_question_id"]): float(row["support_probability"]) for row in extra_rows}
    trigger_rows = load_jsonl(root / "frozen_triggered_candidates/selection_manifest_private_support_only.jsonl")
    triggered = {str(row["question_id"]) for row in trigger_rows}
    if len(a0) != 600 or len(triggered) != len(adaptive) or len(triggered) != len(extra):
        raise RuntimeError("support-score coverage is incomplete")
    expected_triggered = {qid for qid, support in a0.items() if support < TAU}
    if triggered != expected_triggered:
        raise RuntimeError("triggered set does not match frozen threshold")

    candidates: list[dict[str, Any]] = []
    adaptive_switches = 0
    extra_switches = 0
    for question in sorted(questions, key=lambda row: str(row["question_id"])):
        qid, fold = str(question["question_id"]), int(question["fold"])
        uniform = prediction(root, "uniform8", fold, qid, "prediction.json", "ReAdR_Uniform8")
        mmr = prediction(root, "mmr8", fold, qid, "prediction.json", "ReAdR_MMR8")
        adaptive_final, extra_final = mmr, mmr
        adaptive_switch = extra_switch = False
        if qid in triggered:
            adaptive_answer = prediction(root, "adaptive12", fold, qid, "a2_prediction.json", "ReAdR_Adaptive12_A2")
            extra_answer = prediction(root, "extra_global12", fold, qid, "a2_prediction.json", "ReAdR_ExtraGlobal12_A2")
            adaptive_switch = (
                sha256_text(adaptive_answer) != sha256_text(mmr)
                and adaptive[qid] >= a0[qid] + MARGIN
            )
            extra_switch = (
                sha256_text(extra_answer) != sha256_text(mmr)
                and extra[qid] >= a0[qid] + MARGIN
            )
            if adaptive_switch:
                adaptive_final = adaptive_answer
                adaptive_switches += 1
            if extra_switch:
                extra_final = extra_answer
                extra_switches += 1
        values = {
            "Uniform8": uniform,
            "MMR8": mmr,
            "Adaptive12Gated": adaptive_final,
            "ExtraGlobal12Gated": extra_final,
        }
        candidates.append(
            {
                "question_id": qid,
                "video_id": str(question["video"]),
                "question_type": question.get("question_type", ["unknown"]),
                "evaluation_partition": "confirm600",
                "review_triggered": qid in triggered,
                "adaptive_switched": adaptive_switch,
                "extra_global_switched": extra_switch,
                "candidates": values,
                "candidate_sha256": {name: sha256_text(value) for name, value in values.items()},
                "groundtruth_included": False,
            }
        )

    raw_refs = json.loads(args.groundtruth_source.read_text())
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in raw_refs:
        by_id.setdefault(str(row["question_id"]), []).append(row)
    private_refs = []
    for qid in sorted(str(row["question_id"]) for row in questions):
        options = by_id.get(qid, [])
        signatures = {(str(row.get("question", "")), str(row.get("meta_info", "")), answer_from(row)) for row in options}
        if len(signatures) != 1:
            raise RuntimeError(f"missing or ambiguous reference: {qid}")
        row = options[0]
        private_refs.append({"question_id": qid, "question": str(row["question"]), "meta_info": str(row.get("meta_info", "")), "answer": answer_from(row)})

    candidate_path = out / "candidates_answer_free.jsonl"
    private_path = out / "private_references/groundtruth_confirm600.json"
    write_jsonl(candidate_path, candidates)
    write_json(private_path, private_refs)
    trigger_count = len(triggered)
    audit = {
        "schema_version": "readr_increment_confirm600_materialize_v1",
        "passed": True,
        "question_count": 600,
        "video_count": 120,
        "evaluation_partition": "confirm600",
        "groundtruth_read": False,
        "reference_materialized_after_inference": True,
        "groundtruth_used_in_candidate_construction": False,
        "judge_scores_read": False,
        "deepseek_calls_made": 0,
        "candidate_mode": "answer_only",
        "groundtruth_included": False,
        "frozen_threshold": TAU,
        "frozen_margin": MARGIN,
        "review_trigger_count": trigger_count,
        "review_trigger_rate": trigger_count / 600,
        "adaptive_switch_count": adaptive_switches,
        "extra_global_switch_count": extra_switches,
        "average_answer_visual_tokens": 1296.0 + 2696.0 * trigger_count / 600,
        "candidate_methods": ["Uniform8", "MMR8", "Adaptive12Gated", "ExtraGlobal12Gated"],
        "candidate_slots": 2400,
        "candidate_file_sha256": sha256_file(candidate_path),
        "private_reference_sha256": sha256_file(private_path),
        "inference_audits": audit_summary,
    }
    write_json(out / "protocol_audit.json", audit)
    write_json(out / "MATERIALIZE_COMPLETE", {"passed": True})
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
