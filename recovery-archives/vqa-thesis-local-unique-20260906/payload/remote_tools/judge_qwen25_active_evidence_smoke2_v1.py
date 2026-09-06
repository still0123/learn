#!/usr/bin/env python3
"""Judge exactly two frozen ActiveEvidence revisions with the legacy answer-only protocol."""

from __future__ import annotations

import argparse
from collections import Counter
import glob
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--pilot-scores", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(args.project_root / "evaluation/tools"))
    from judge_adsqa_answer_lora_oof_v1 import (  # noqa: PLC0415
        JudgeProtocolError,
        VALID_SCORES,
        legacy_parse_score,
        legacy_protocol,
        truncate_words,
    )

    candidates = []
    for trace_name in sorted(glob.glob(str(args.inference_root / "shard*/*/a2_trace.json"))):
        trace = json.loads(Path(trace_name).read_text(encoding="utf-8"))
        if not trace.get("parse_valid") or not trace.get("answer_changed_from_a0"):
            continue
        prediction = json.loads(Path(trace_name.replace("a2_trace.json", "a2_prediction.json")).read_text(encoding="utf-8"))
        candidates.append({
            "question_id": str(trace["question_id"]),
            "prediction": truncate_words(str(prediction["prediction"]).strip()),
            "prediction_sha256": sha(str(prediction["prediction"]).strip()),
        })
    if len(candidates) != 2 or len({row["question_id"] for row in candidates}) != 2:
        raise JudgeProtocolError(f"expected exactly two frozen revisions, got {len(candidates)}")

    all_gt = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    wanted = {row["question_id"] for row in candidates}
    gt = {str(row["question_id"]): row for row in all_gt if str(row["question_id"]) in wanted}
    if set(gt) != wanted:
        raise JudgeProtocolError("private references do not cover both candidates")
    old = {str(row["question_id"]): row for row in rows(args.pilot_scores)}
    if not wanted <= set(old):
        raise JudgeProtocolError("pilot A0 scores do not cover both candidates")

    protocol = legacy_protocol(args.legacy_evaluator)
    preflight = {
        "schema_version": "qwen25_active_evidence_smoke2_preflight_v1",
        "passed": True,
        "expected_new_calls": 2,
        "candidate_hashes": {row["question_id"]: row["prediction_sha256"] for row in candidates},
        "judge_model": protocol["model_name"],
        "prompt_sha256": protocol["prompt_sha256"],
        "api_called": False,
        "not_human_gold": True,
    }
    dump(args.output_dir / "preflight.json", preflight)
    if args.validate_only:
        print(json.dumps(preflight, ensure_ascii=False))
        return
    if (args.output_dir / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite completed output")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=protocol["base_url"], timeout=60.0)
    judged = []
    for item in candidates:
        reference = gt[item["question_id"]]
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=item["prediction"],
        )
        response = client.chat.completions.create(
            model=protocol["model_name"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        output = str(response.choices[0].message.content)
        score = legacy_parse_score(output)
        if score not in VALID_SCORES:
            raise JudgeProtocolError(f"unparsed judge output for {item['question_id']}")
        usage = getattr(response, "usage", None)
        judged.append({
            "question_id": item["question_id"],
            "candidate_prediction_sha256": item["prediction_sha256"],
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "not_human_gold": True,
        })
    (args.output_dir / "api_results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in judged), encoding="utf-8"
    )

    paired = []
    for result in judged:
        qid = result["question_id"]
        paired.append({"question_id": qid, "a0_score": float(old[qid]["MMR8_score"]), "candidate_score": float(result["score"])})
    usage = Counter()
    for result in judged:
        for key, value in (result.get("judge_usage") or {}).items():
            if isinstance(value, int):
                usage[key] += value
    summary = {
        "schema_version": "qwen25_active_evidence_smoke2_judge_v1",
        "n": 2,
        "wins": sum(row["candidate_score"] > row["a0_score"] for row in paired),
        "ties": sum(row["candidate_score"] == row["a0_score"] for row in paired),
        "losses": sum(row["candidate_score"] < row["a0_score"] for row in paired),
        "wrong_to_right": sum(row["a0_score"] == 0 and row["candidate_score"] == 1 for row in paired),
        "right_to_wrong": sum(row["a0_score"] == 1 and row["candidate_score"] < 1 for row in paired),
        "a0_relaxed": sum(row["a0_score"] for row in paired) / 2,
        "candidate_relaxed": sum(row["candidate_score"] for row in paired) / 2,
        "relaxed_delta": sum(row["candidate_score"] - row["a0_score"] for row in paired) / 2,
        "judge_protocol": {
            "model": protocol["model_name"],
            "prompt_sha256": protocol["prompt_sha256"],
            "new_api_calls": 2,
            "automatic_retries": 0,
            "failures": 0,
            "usage": dict(usage),
            "not_human_gold": True,
        },
        "diagnostic_only": True,
    }
    dump(args.output_dir / "paired_results.json", paired)
    dump(args.output_dir / "summary.json", summary)
    (args.output_dir / "JUDGE_COMPLETE").write_text("complete\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
