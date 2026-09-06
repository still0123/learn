#!/usr/bin/env python3
"""Materialize private references and answer-free candidates for Pilot-300."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHODS = {
    "Uniform8": ("uniform8", "prediction.json", "ReAdR_Uniform8"),
    "MMR8": ("mmr8", "prediction.json", "ReAdR_MMR8"),
    "Adaptive12": ("adaptive12", "a2_prediction.json", "ReAdR_Adaptive12_A2"),
    "ExtraGlobal12": (
        "extra_global12",
        "a2_prediction.json",
        "ReAdR_ExtraGlobal12_A2",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--groundtruth-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def answer_from(record: dict[str, Any]) -> str:
    for field in ("answer", "gt_answer", "answers"):
        value = record.get(field)
        if isinstance(value, list):
            value = next((item for item in value if str(item).strip()), "")
        text = str(value or "").strip()
        if text:
            return text
    raise RuntimeError(f"no reference answer: {record.get('question_id')}")


def main() -> None:
    args = parse_args()
    root = args.run_root.resolve()
    out = args.output_root.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"refusing to overwrite nonempty output: {out}")
    questions = json.loads((root / "inputs_v1/questions_answer_free.json").read_text())
    if len(questions) != 300:
        raise RuntimeError("Pilot-300 question pool is incomplete")
    qids = [str(row["question_id"]) for row in questions]
    if len(set(qids)) != 300 or any(row.get("answer_free") is not True for row in questions):
        raise RuntimeError("invalid answer-free Pilot question pool")
    if {str(row.get("pilot_partition")) for row in questions} != {"calibration100", "confirm200"}:
        raise RuntimeError("Pilot partitions are incomplete")
    if sum(row["pilot_partition"] == "calibration100" for row in questions) != 100:
        raise RuntimeError("calibration100 is not exactly 100 questions")
    if sum(row["pilot_partition"] == "confirm200" for row in questions) != 200:
        raise RuntimeError("confirm200 is not exactly 200 questions")
    calibration_videos = {str(row["video"]) for row in questions if row["pilot_partition"] == "calibration100"}
    confirm_videos = {str(row["video"]) for row in questions if row["pilot_partition"] == "confirm200"}
    if len(calibration_videos) != 20 or len(confirm_videos) != 40 or calibration_videos & confirm_videos:
        raise RuntimeError("Pilot video isolation audit failed")

    audit_files = {
        "Uniform8": root / "uniform8/protocol_audit.json",
        "MMR8": root / "mmr8/protocol_audit.json",
        "Adaptive12": root / "adaptive12_protocol_audit.json",
        "ExtraGlobal12": root / "extra_global12_protocol_audit.json",
    }
    audit_summary: dict[str, Any] = {}
    for method, path in audit_files.items():
        audit = json.loads(path.read_text())
        if audit.get("passed") is not True or int(audit.get("question_count", -1)) != 300:
            raise RuntimeError(f"failed inference audit: {method}")
        audit_summary[method] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "expected_visual_tokens": audit.get("expected_visual_tokens"),
        }

    candidates: list[dict[str, Any]] = []
    for question in sorted(questions, key=lambda row: str(row["question_id"])):
        qid = str(question["question_id"])
        fold = int(question["fold"])
        values: dict[str, str] = {}
        hashes: dict[str, str] = {}
        for method, (arm, filename, expected_method) in METHODS.items():
            source = root / arm / f"fold_{fold}" / qid / filename
            prediction = json.loads(source.read_text())
            answer = str(prediction.get("prediction", "")).strip()
            if (
                str(prediction.get("question_id")) != qid
                or str(prediction.get("method")) != expected_method
                or not answer
            ):
                raise RuntimeError(f"invalid prediction artifact: {source}")
            values[method] = answer
            hashes[method] = sha256_text(answer)
        candidates.append(
            {
                "question_id": qid,
                "video_id": str(question["video"]),
                "question_type": question.get("question_type", ["unknown"]),
                "pilot_partition": str(question["pilot_partition"]),
                "candidates": values,
                "candidate_sha256": hashes,
                "groundtruth_included": False,
            }
        )

    raw_groundtruth = json.loads(args.groundtruth_source.read_text())
    gt_rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in raw_groundtruth:
        gt_rows_by_id.setdefault(str(row["question_id"]), []).append(row)
    if set(qids) - set(gt_rows_by_id):
        raise RuntimeError("reference pool does not cover Pilot questions")
    gt_by_id: dict[str, dict[str, Any]] = {}
    for qid in qids:
        options = gt_rows_by_id[qid]
        signatures = {
            (
                str(row.get("question", "")),
                str(row.get("meta_info", "")),
                answer_from(row),
            )
            for row in options
        }
        if len(signatures) != 1:
            raise RuntimeError(f"ambiguous selected reference: {qid}")
        gt_by_id[qid] = options[0]
    private_refs = []
    for question in sorted(questions, key=lambda row: str(row["question_id"])):
        source = gt_by_id[str(question["question_id"])]
        private_refs.append(
            {
                "question_id": str(source["question_id"]),
                "question": str(source["question"]),
                "meta_info": str(source.get("meta_info", "")),
                "answer": answer_from(source),
            }
        )

    candidate_path = out / "candidates_answer_free.jsonl"
    private_path = out / "private_references/groundtruth_pilot300.json"
    write_jsonl(candidate_path, candidates)
    write_json(private_path, private_refs)
    audit = {
        "schema_version": "readr_increment_pilot300_materialize_v1",
        "passed": True,
        "question_count": 300,
        "video_count": 60,
        "calibration_questions": 100,
        "confirm_questions": 200,
        "calibration_video_count": 20,
        "confirm_video_count": 40,
        "video_overlap_count": 0,
        "groundtruth_read": False,
        "reference_materialized_after_inference": True,
        "groundtruth_used_in_candidate_construction": False,
        "judge_scores_read": False,
        "deepseek_calls_made": 0,
        "candidate_mode": "answer_only",
        "groundtruth_included": False,
        "candidate_methods": sorted(METHODS),
        "candidate_slots": 1200,
        "candidate_file_sha256": sha256_file(candidate_path),
        "private_reference_sha256": sha256_file(private_path),
        "inference_audits": audit_summary,
    }
    write_json(out / "protocol_audit.json", audit)
    write_json(out / "MATERIALIZE_COMPLETE", {"passed": True})
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
