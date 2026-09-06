#!/usr/bin/env python3
"""Judge 39 new active-tool candidates and aggregate paired Confirm-60B results."""

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import random
import sys


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values))


def reference_answer(row: dict) -> str:
    value = row.get("answer") or row.get("gt_answer") or row.get("answers")
    if isinstance(value, list):
        value = value[0] if value else ""
    if not str(value or "").strip():
        raise RuntimeError(f"missing reference answer: {row.get('question_id')}")
    return str(value)


def metrics(values: list[float]) -> dict:
    return {
        "n": len(values),
        "strict": sum(value == 1 for value in values) / len(values),
        "relaxed": sum(values) / len(values),
    }


def paired(values: list[dict], samples: int = 10000) -> dict:
    by_video = defaultdict(list)
    for row in values:
        by_video[row["video_id"]].append(row)
    videos = sorted(by_video)
    rng = random.Random(2026080501)
    strict, relaxed = [], []
    for _ in range(samples):
        sample = [row for video in rng.choices(videos, k=len(videos)) for row in by_video[video]]
        strict.append(sum(int(row["ActiveLook"] == 1) - int(row["A0"] == 1) for row in sample) / len(sample))
        relaxed.append(sum(row["ActiveLook"] - row["A0"] for row in sample) / len(sample))
    def ci(values_: list[float]) -> list[float]:
        ordered = sorted(values_)
        return [ordered[int(0.025 * len(ordered))], ordered[int(0.975 * len(ordered))]]
    return {
        "wins": sum(row["ActiveLook"] > row["A0"] for row in values),
        "ties": sum(row["ActiveLook"] == row["A0"] for row in values),
        "losses": sum(row["ActiveLook"] < row["A0"] for row in values),
        "wrong_to_right": sum(row["A0"] == 0 and row["ActiveLook"] == 1 for row in values),
        "right_to_wrong": sum(row["A0"] == 1 and row["ActiveLook"] < 1 for row in values),
        "strict_delta": sum(int(row["ActiveLook"] == 1) - int(row["A0"] == 1) for row in values) / len(values),
        "relaxed_delta": sum(row["ActiveLook"] - row["A0"] for row in values) / len(values),
        "correction_precision": sum(row["ActiveLook"] > row["A0"] for row in values) / max(1, sum(row["ActiveLook"] != row["A0"] for row in values)),
        "video_cluster_bootstrap_ci95": {
            "samples": samples,
            "clusters": len(videos),
            "strict_delta": ci(strict),
            "relaxed_delta": ci(relaxed),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(args.project_root / "evaluation/tools"))
    from judge_adsqa_answer_lora_oof_v1 import VALID_SCORES, legacy_parse_score, legacy_protocol

    preflight = json.loads((args.preflight_root / "preflight.json").read_text())
    candidates = rows(args.preflight_root / "candidates_answer_free.jsonl")
    reused = rows(args.preflight_root / "reused_scores.jsonl")
    pending = rows(args.preflight_root / "pending_new_scores.jsonl")
    if not preflight["passed"] or len(candidates) != 120 or len(reused) != 60 or len(pending) != 39:
        raise RuntimeError("authorized frozen call set changed")
    wanted = {row["question_id"] for row in pending}
    groundtruth = {str(row["question_id"]): row for row in json.loads(args.groundtruth.read_text()) if str(row["question_id"]) in wanted}
    if set(groundtruth) != wanted:
        raise RuntimeError("private reference coverage mismatch")
    for row in groundtruth.values():
        reference_answer(row)
    protocol = legacy_protocol(args.legacy_evaluator)
    validation = {
        "passed": True,
        "expected_new_calls": 39,
        "judge_model": protocol["model_name"],
        "prompt_sha256": protocol["prompt_sha256"],
        "api_called": False,
        "not_human_gold": True,
    }
    write(args.output_root / "validation.json", validation)
    if args.validate_only:
        print(json.dumps(validation))
        return
    if (args.output_root / "JUDGE_COMPLETE").exists():
        raise RuntimeError("refusing to overwrite completed judge output")
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=protocol["base_url"], timeout=60)
    api_rows = []
    for item in pending:
        reference = groundtruth[item["question_id"]]
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"], question=reference["question"],
            golden_answer=reference_answer(reference), response=item["prediction"],
        )
        response = client.chat.completions.create(
            model=protocol["model_name"], temperature=0, max_tokens=20,
            messages=[
                {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                {"role": "user", "content": prompt},
            ],
        )
        output = str(response.choices[0].message.content)
        score = legacy_parse_score(output)
        if score not in VALID_SCORES:
            raise RuntimeError(f"unparsed judge output: {item['question_id']}")
        usage = getattr(response, "usage", None)
        api_rows.append({
            "question_id": item["question_id"], "prediction_sha256": item["prediction_sha256"],
            "score": score, "judge_output": output,
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "not_human_gold": True,
        })
    write_jsonl(args.output_root / "api_results.jsonl", api_rows)
    score_map = {(row["question_id"], row["prediction_sha256"]): float(row["score"]) for row in reused + api_rows}
    expanded = [{**row, "score": score_map[(row["question_id"], row["prediction_sha256"])]} for row in candidates]
    write_jsonl(args.output_root / "expanded_scores120.jsonl", expanded)
    by_qid = defaultdict(dict)
    for row in expanded:
        by_qid[row["question_id"]][row["method"]] = row["score"]
        by_qid[row["question_id"]]["video_id"] = row["video_id"]
    paired_rows = [{"question_id": qid, **value} for qid, value in sorted(by_qid.items())]
    write_jsonl(args.output_root / "paired_results60.jsonl", paired_rows)
    usage = Counter()
    for row in api_rows:
        for key, value in (row.get("judge_usage") or {}).items():
            if isinstance(value, int):
                usage[key] += value
    summary = {
        "schema_version": "qwen25_active_evidence_confirm60b_judge_v1",
        "methods": {method: metrics([row[method] for row in paired_rows]) for method in ("A0", "ActiveLook")},
        "paired_vs_a0": paired(paired_rows),
        "judge_protocol": {
            "model": protocol["model_name"], "prompt_sha256": protocol["prompt_sha256"],
            "historical_exact_reuses": 60, "new_api_calls": 39,
            "automatic_retries": 0, "failures": 0, "usage": dict(usage),
            "not_human_gold": True,
        },
    }
    write(args.output_root / "summary.json", summary)
    (args.output_root / "JUDGE_COMPLETE").write_text("complete\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
