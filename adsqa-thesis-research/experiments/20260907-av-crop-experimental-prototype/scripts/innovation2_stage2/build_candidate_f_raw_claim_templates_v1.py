#!/usr/bin/env python3
"""Build leak-free human templates for answer-conditioned Raw32 claim grounding."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inference-inputs", type=Path, required=True)
    parser.add_argument("--blind-manifest", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def answer_section(prediction: str) -> str:
    match = re.search(r"\[Answer\]\s*:\s*(.+)$", prediction, flags=re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else prediction).strip()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.output_root.exists():
        raise RuntimeError(f"refusing to overwrite {args.output_root}")
    inputs = {
        row["question_id"]: row
        for row in read_jsonl(args.inference_inputs)
        if row.get("split") == "calibration"
    }
    manifest = {row["claim_id"]: row for row in read_jsonl(args.blind_manifest)}
    if len(inputs) != 240 or len(manifest) != 240 or set(inputs) != set(manifest):
        raise RuntimeError("Calibration240 inputs and blind manifest must align exactly")
    template_rows: list[dict[str, Any]] = []
    protected = {"ground_truth", "label", "reference_answer", "score"}
    for index, claim_id in enumerate(sorted(inputs), start=1):
        source = inputs[claim_id]
        blind = manifest[claim_id]
        prediction_path = args.raw_root / source["source_question_id"] / "prediction.json"
        evidence_path = args.raw_root / source["source_question_id"] / "evidence.json"
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        raw_answer = answer_section(str(prediction["prediction"]))
        if any(key in {"raw_answer", "claim", "question"} and key in protected for key in prediction):
            raise RuntimeError(f"protected field unexpectedly mapped for {claim_id}")
        template_rows.append(
            {
                "review_index": index,
                "claim_id": claim_id,
                "source_question_id": source["source_question_id"],
                "video_id": source["video_id"],
                "question": source["question"],
                "raw32_candidate_answer": raw_answer,
                "atomic_claim": source["claim"],
                "transcript": source["asr_excerpt"],
                "raw32_contact_sheet": blind["contact_sheet"],
                "raw32_frame_indices": source["selected_frame_indices"],
                "allowed_answer_relation": [
                    "claim_absent_from_answer",
                    "claim_present_supported",
                    "claim_present_refuted",
                    "claim_present_insufficient",
                ],
                "allowed_required_modalities": ["asr", "ocr", "visual", "joint"],
                "human_answer_relation": None,
                "human_required_modalities": [],
                "human_frame_indices": [],
                "human_asr_spans": [],
                "human_ocr_text": [],
                "human_confidence": None,
                "human_rationale": None,
            }
        )
    reviewer_rows = []
    for reviewer_id in ("human_reviewer_a", "human_reviewer_b"):
        reviewer_rows.append([{**row, "reviewer_id": reviewer_id} for row in template_rows])
    args.output_root.mkdir(parents=True)
    path_a = args.output_root / "human_review_a_template.jsonl"
    path_b = args.output_root / "human_review_b_template.jsonl"
    write_jsonl(path_a, reviewer_rows[0])
    write_jsonl(path_b, reviewer_rows[1])
    instructions = """# Candidate F: answer-conditioned evidence review

Review Raw32 candidate answers independently. For each atomic claim, first decide
whether it is present in the Raw32 answer, then judge whether the listed evidence
supports it. Use only the question, candidate answer, transcript, and Raw32 contact
sheet. Do not infer support from a plausible campaign story.

If the claim is present, record every necessary modality and the exact frame indices,
ASR character spans, and/or OCR strings that support it. A visual cue without a
specific index is not sufficient. Leave all fields empty when the claim is absent.
Do not consult reference answers, old labels, model scores, or the other reviewer.
"""
    instruction_path = args.output_root / "instructions.md"
    instruction_path.write_text(instructions, encoding="utf-8")
    forbidden_fields = sorted(
        {key for row in reviewer_rows[0] + reviewer_rows[1] for key in protected if key in row}
    )
    audit = {
        "schema": "adsqa_candidate_f_raw_claim_templates_v1",
        "rows": len(template_rows),
        "reviewers": ["human_reviewer_a", "human_reviewer_b"],
        "raw_predictions_complete": all(row["raw32_candidate_answer"] for row in template_rows),
        "protected_fields_absent": not forbidden_fields,
        "forbidden_fields": forbidden_fields,
        "labels_filled": False,
        "threshold_calibration_allowed": False,
        "development_evaluation_allowed": False,
        "not_human_gold": True,
        "input_hashes": {
            "inference_inputs": sha256_file(args.inference_inputs),
            "blind_manifest": sha256_file(args.blind_manifest),
            "template_a": sha256_file(path_a),
            "template_b": sha256_file(path_b),
            "instructions": sha256_file(instruction_path),
        },
    }
    audit["passed"] = audit["rows"] == 240 and audit["raw_predictions_complete"] and audit["protected_fields_absent"]
    (args.output_root / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
