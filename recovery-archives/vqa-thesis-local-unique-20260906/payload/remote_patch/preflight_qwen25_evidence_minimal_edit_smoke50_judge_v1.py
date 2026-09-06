#!/usr/bin/env python3
"""Count exact new judge calls for minimal-edit Smoke-50 without reading GT."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(args.project_root / "evaluation/tools"))
    from judge_adsqa_answer_lora_oof_v1 import (  # noqa: PLC0415
        extract_answer_section,
        truncate_words,
    )

    protocol_audit_path = args.smoke_root / "protocol_audit_v2/audit.json"
    protocol_audit = json.loads(protocol_audit_path.read_text(encoding="utf-8"))
    if protocol_audit.get("passed") is not True:
        raise RuntimeError("Smoke-50 protocol audit v2 did not pass")

    dataset_rows = load_jsonl(args.smoke_root / "dataset/items_answer_free.jsonl")
    selected = {str(row["question_id"]) for row in dataset_rows}
    if len(dataset_rows) != 50 or len(selected) != 50:
        raise RuntimeError("Smoke dataset must contain 50 unique questions")

    old_judge_root = args.baseline_root / "judge_deepseek_answeronly_v1"
    old_summary = json.loads(
        (old_judge_root / "summary.json").read_text(encoding="utf-8")
    )
    old_expanded = load_jsonl(old_judge_root / "expanded_results2000.jsonl")
    old_scores: dict[tuple[str, str], float] = {}
    old_owners: dict[tuple[str, str], list[str]] = {}
    for row in old_expanded:
        qid = str(row["question_id"])
        candidate_hash = str(row["candidate_prediction_sha256"])
        key = (qid, candidate_hash)
        old_scores[key] = float(row["score"])
        old_owners.setdefault(key, []).append(str(row["method"]))

    reuse_owner_counts: Counter[str] = Counter()
    changed_count = 0
    reused_count = 0
    new_call_count = 0
    candidate_hashes: list[str] = []
    for path in sorted(
        (args.smoke_root / "inference").glob("fold_*/*/a2_prediction.json")
    ):
        prediction = json.loads(path.read_text(encoding="utf-8"))
        qid = str(prediction["question_id"])
        if qid not in selected:
            raise RuntimeError(f"unexpected question: {qid}")
        answer, _, _ = extract_answer_section(str(prediction["prediction"]).strip())
        answer = truncate_words(answer.strip())
        if not answer:
            raise RuntimeError(f"empty normalized prediction: {qid}")
        candidate_hash = sha256_text(answer)
        candidate_hashes.append(f"{qid}:{candidate_hash}")
        key = (qid, candidate_hash)
        trace = json.loads(
            (path.parent / "a2_trace.json").read_text(encoding="utf-8")
        )
        changed_count += bool(trace.get("answer_changed_from_a0"))
        if key in old_scores:
            reused_count += 1
            for owner in sorted(set(old_owners[key])):
                reuse_owner_counts[owner] += 1
        else:
            new_call_count += 1

    if reused_count + new_call_count != 50:
        raise RuntimeError("judge preflight coverage mismatch")
    judge_protocol = old_summary["judge_protocol"]
    output = {
        "schema_version": "qwen25_evidence_minimal_edit_smoke50_judge_preflight_v1",
        "question_count": 50,
        "candidate_count": 50,
        "answer_changed_from_a0_count": changed_count,
        "existing_score_reuses": reused_count,
        "new_api_calls": new_call_count,
        "reuse_owner_counts_nonexclusive": dict(reuse_owner_counts),
        "judge_model": judge_protocol["judge_model"],
        "candidate_mode": judge_protocol["candidate_mode"],
        "prompt_sha256": judge_protocol["prompt_sha256"],
        "baseline_judge_failures": judge_protocol["failures"],
        "groundtruth_read": False,
        "api_called": False,
        "protocol_audit_sha256": sha256_file(protocol_audit_path),
        "candidate_set_sha256": sha256_text("\n".join(sorted(candidate_hashes))),
        "passed": True,
    }
    write_json(args.output_dir / "dry_run_audit.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
