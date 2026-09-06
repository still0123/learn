#!/usr/bin/env python3
"""Materialize answer-free candidates for the AdsQA 2,526-question supplement."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


METHODS = ("Uniform8", "CLIPTopK8", "MMR8", "AdaptiveScale")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--uniform-root", type=Path, required=True)
    parser.add_argument("--uniform-audit-root", type=Path, required=True)
    parser.add_argument("--clip-root", type=Path, required=True)
    parser.add_argument("--clip-audit-root", type=Path, required=True)
    parser.add_argument("--mmr-root", type=Path, required=True)
    parser.add_argument("--mmr-audit-root", type=Path, required=True)
    parser.add_argument("--trigger-dataset", type=Path, required=True)
    parser.add_argument("--adaptive-root", type=Path, required=True)
    parser.add_argument("--crop-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def extract_answer(value: str) -> str:
    text = str(value).strip()
    matches = []
    for marker in ("[Answer]:", "[ANSWER]:", "Answer:", "ANSWER:"):
        index = text.find(marker)
        if index >= 0:
            matches.append((index, marker))
    if matches:
        index, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
        answer = text[index + len(marker) :].strip()
        if answer:
            return answer
    return re.sub(
        r"^\s*(?:final\s+)?answer\s*:\s*", "", text, flags=re.I
    ).strip() or text


def audit_folds(
    questions: list[dict[str, Any]],
    audit_root: Path,
    label: str,
) -> dict[str, str]:
    hashes = {}
    for fold in range(5):
        expected = sum(int(row["fold"]) == fold for row in questions)
        path = audit_root / f"fold_{fold}.json"
        audit = json.loads(path.read_text(encoding="utf-8"))
        count = audit.get("question_count", audit.get("completed_count", -1))
        if audit.get("passed") is not True or int(count) != expected:
            raise RuntimeError(f"{label} audit failed for fold {fold}")
        hashes[str(fold)] = sha256_file(path)
    return hashes


def prediction(root: Path, fold: int, qid: str, *, uniform: bool) -> dict[str, Any]:
    path = (
        root / f"fold_{fold}" / "base" / qid / "prediction.json"
        if uniform
        else root / f"fold_{fold}" / qid / "prediction.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    question_by_id = {str(row["question_id"]): row for row in questions}
    if len(questions) != 2526 or len(question_by_id) != 2526:
        raise RuntimeError("supplement question pool mismatch")
    forbidden = {"answer", "gt_answer", "meta_info", "reference_answer"}
    if any(forbidden & set(row) for row in questions):
        raise RuntimeError("supplement questions are not answer-free")

    uniform_hashes = audit_folds(
        questions, args.uniform_audit_root, "Uniform8"
    )
    clip_hashes = audit_folds(questions, args.clip_audit_root, "CLIPTopK8")
    mmr_hashes = audit_folds(questions, args.mmr_audit_root, "MMR8")
    crop_audit = json.loads(args.crop_audit.read_text(encoding="utf-8"))
    if crop_audit.get("passed") is not True:
        raise RuntimeError("AdaptiveScale audit failed")
    trigger = load_jsonl(args.trigger_dataset / "items_answer_free.jsonl")
    trigger_by_id = {str(row["question_id"]): row for row in trigger}
    if len(trigger_by_id) != len(trigger):
        raise RuntimeError("duplicate trigger question")

    rows = []
    for qid, question in question_by_id.items():
        source_fold = int(question["fold"])
        uniform_row = prediction(args.uniform_root, source_fold, qid, uniform=True)
        clip_row = prediction(args.clip_root, source_fold, qid, uniform=False)
        mmr_row = prediction(args.mmr_root, source_fold, qid, uniform=False)
        if (
            uniform_row.get("method") != "CleanQwen3_Raw8"
            or clip_row.get("method") != "CleanQwen3_CLIPTopK8"
            or mmr_row.get("method") != "CLIPMMR64_8_lambda070"
        ):
            raise RuntimeError(f"unexpected A0 method for {qid}")
        uniform = extract_answer(str(uniform_row["prediction"]))
        clip = extract_answer(str(clip_row["prediction"]))
        mmr = extract_answer(str(mmr_row["prediction"]))
        if qid in trigger_by_id:
            runtime_fold = int(trigger_by_id[qid]["fold"])
            a2_path = (
                args.adaptive_root / f"fold_{runtime_fold}" / qid
                / "a2_prediction.json"
            )
            a2_row = json.loads(a2_path.read_text(encoding="utf-8"))
            if a2_row.get("method") != "Qwen3_adaptive_scale_AVEvidenceRewrite12_A2":
                raise RuntimeError(f"unexpected AdaptiveScale method for {qid}")
            adaptive = extract_answer(str(a2_row["prediction"]))
            triggered = True
        else:
            adaptive = mmr
            triggered = False
        candidates = {
            "Uniform8": uniform,
            "CLIPTopK8": clip,
            "MMR8": mmr,
            "AdaptiveScale": adaptive,
        }
        if any(not value for value in candidates.values()):
            raise RuntimeError(f"empty candidate for {qid}")
        rows.append(
            {
                "question_id": qid,
                "video_id": str(question["video"]),
                "fold": source_fold,
                "question_type": list(question["question_type"]),
                "triggered": triggered,
                "candidates": candidates,
                "candidate_sha256": {
                    method: sha256_text(value)
                    for method, value in candidates.items()
                },
                "groundtruth_included": False,
            }
        )
    rows.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    output = args.output_dir / "candidates_answer_free.jsonl"
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    trigger_count = sum(bool(row["triggered"]) for row in rows)
    average_tokens = (
        (len(rows) - trigger_count) * 1024 + trigger_count * 3104
    ) / len(rows)
    audit = {
        "schema_version": "adsqa_supplement2526_candidates_audit_v1",
        "passed": len(rows) == 2526,
        "question_count": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "methods": list(METHODS),
        "expanded_candidate_slots": len(rows) * len(METHODS),
        "trigger_count": trigger_count,
        "trigger_rate": trigger_count / len(rows),
        "a0_visual_tokens": 1024,
        "trigger_a2_visual_tokens": 3104,
        "adaptive_average_visual_tokens": average_tokens,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "deepseek_calls_made": 0,
        "questions_sha256": sha256_file(args.questions),
        "uniform_audit_sha256": uniform_hashes,
        "clip_audit_sha256": clip_hashes,
        "mmr_audit_sha256": mmr_hashes,
        "crop_audit_sha256": sha256_file(args.crop_audit),
        "candidates_sha256": sha256_file(output),
    }
    (args.output_dir / "protocol_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not audit["passed"]:
        raise RuntimeError("supplement candidate audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
