#!/usr/bin/env python3
"""Materialize audited answer-free candidates for full AdsQA evaluation."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


METHODS = ("Uniform8", "MMR8", "AdaptiveScaleA2", "FullJointMethod")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--uniform-root", type=Path, required=True)
    parser.add_argument("--uniform-audit-root", type=Path, required=True)
    parser.add_argument("--mmr-root", type=Path, required=True)
    parser.add_argument("--mmr-audit-root", type=Path, required=True)
    parser.add_argument("--trigger-dataset", type=Path, required=True)
    parser.add_argument("--crop-audit", type=Path, required=True)
    parser.add_argument("--choices-dir", type=Path, required=True)
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


def extract_answer(value: str) -> str:
    text = str(value).strip()
    matches = []
    for marker in ("[Answer]:", "[ANSWER]:", "Answer:", "ANSWER:"):
        index = text.find(marker)
        if index >= 0:
            matches.append((index, marker))
    if matches:
        index, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
        answer = text[index + len(marker):].strip()
        if answer:
            return answer
    cleaned = re.sub(
        r"^\s*(?:final\s+)?answer\s*:\s*", "", text, flags=re.I
    ).strip()
    return cleaned or text


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    question_by_id = {str(row["question_id"]): row for row in questions}
    if len(questions) != 5320 or len(question_by_id) != 5320:
        raise RuntimeError("full5320 question pool mismatch")
    crop_audit = json.loads(args.crop_audit.read_text(encoding="utf-8"))
    if (
        crop_audit.get("passed") is not True
        or int(crop_audit.get("record_count", -1)) != 530
    ):
        raise RuntimeError("inference protocol audits did not pass")
    for fold in range(5):
        uniform_audit = json.loads(
            (args.uniform_audit_root / f"fold_{fold}.json").read_text(
                encoding="utf-8"
            )
        )
        if (
            uniform_audit.get("passed") is not True
            or int(uniform_audit.get("question_count", -1)) != 1064
        ):
            raise RuntimeError(f"Uniform audit failed for fold {fold}")
        audit = json.loads(
            (args.mmr_audit_root / f"fold_{fold}.json").read_text(
                encoding="utf-8"
            )
        )
        mmr_question_count = audit.get(
            "question_count", audit.get("completed_count", -1)
        )
        if (
            audit.get("passed") is not True
            or int(mmr_question_count) != 1064
        ):
            raise RuntimeError(f"MMR audit failed for fold {fold}")

    trigger = load_jsonl(args.trigger_dataset / "items_answer_free.jsonl")
    choices_path = args.choices_dir / "frozen_choices_answer_free.jsonl"
    choices = load_jsonl(choices_path)
    choice_by_id = {str(row["question_id"]): row for row in choices}
    trigger_ids = {str(row["question_id"]) for row in trigger}
    choice_audit = json.loads(
        (args.choices_dir / "protocol_audit.json").read_text(encoding="utf-8")
    )
    if (
        len(trigger_ids) != 530
        or len(choices) != 530
        or set(choice_by_id) != trigger_ids
        or choice_audit.get("passed") is not True
        or int(choice_audit.get("rows", -1)) != 530
        or choice_audit.get("choices_sha256") != sha256_file(choices_path)
    ):
        raise RuntimeError("frozen full530 choices do not align")

    rows = []
    method_hashes = Counter()
    for qid, question in question_by_id.items():
        fold = int(question["fold"])
        uniform_path = (
            args.uniform_root / f"fold_{fold}" / "base" / qid
            / "prediction.json"
        )
        mmr_path = args.mmr_root / f"fold_{fold}" / qid / "prediction.json"
        uniform_row = json.loads(uniform_path.read_text(encoding="utf-8"))
        mmr_row = json.loads(mmr_path.read_text(encoding="utf-8"))
        if (
            uniform_row.get("method") != "CleanQwen3_Raw8"
            or mmr_row.get("method") != "CLIPMMR64_8_lambda070"
        ):
            raise RuntimeError(f"unexpected A0 method for {qid}")
        uniform = extract_answer(str(uniform_row["prediction"]))
        mmr = extract_answer(str(mmr_row["prediction"]))
        if qid in choice_by_id:
            choice = choice_by_id[qid]
            if str(choice["a0_prediction"]) != mmr:
                raise RuntimeError(f"choice A0 mismatch: {qid}")
            a2 = str(choice["a2_prediction"])
            final = str(choice["a3_prediction"])
            triggered = True
            switched = bool(choice["a3_switched"])
        else:
            a2 = mmr
            final = mmr
            triggered = False
            switched = False
        candidates = {
            "Uniform8": uniform,
            "MMR8": mmr,
            "AdaptiveScaleA2": a2,
            "FullJointMethod": final,
        }
        if any(not str(value).strip() for value in candidates.values()):
            raise RuntimeError(f"empty candidate: {qid}")
        for method, value in candidates.items():
            method_hashes[(method, sha256_text(value))] += 1
        rows.append(
            {
                "question_id": qid,
                "video_id": str(question["video"]),
                "fold": fold,
                "question_type": list(question["question_type"]),
                "triggered": triggered,
                "full_method_switched": switched,
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
    audit = {
        "schema_version": "adsqa_full5320_answer_free_protocol_audit_v1",
        "passed": True,
        "question_count": len(rows),
        "video_count": len({str(row["video_id"]) for row in rows}),
        "methods": list(METHODS),
        "expanded_candidate_slots": len(rows) * len(METHODS),
        "trigger_count": sum(bool(row["triggered"]) for row in rows),
        "switch_count": sum(
            bool(row["full_method_switched"]) for row in rows
        ),
        "uniform_visual_tokens": 1024,
        "mmr_visual_tokens": 1024,
        "trigger_a2_visual_tokens": 3104,
        "full_policy_average_answer_visual_tokens": (
            (5320 - 530) * 1024 + 530 * 3104
        )
        / 5320,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "deepseek_calls_made": 0,
        "questions_sha256": sha256_file(args.questions),
        "uniform_audit_sha256": {
            str(fold): sha256_file(
                args.uniform_audit_root / f"fold_{fold}.json"
            )
            for fold in range(5)
        },
        "crop_audit_sha256": sha256_file(args.crop_audit),
        "choices_sha256": sha256_file(choices_path),
        "candidates_sha256": sha256_file(output),
    }
    (args.output_dir / "protocol_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
