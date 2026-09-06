#!/usr/bin/env python3
"""Judge six frozen Confirm-100 candidates and aggregate four arms."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import sys
from typing import Any


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values), encoding="utf-8")


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * p))]


def metrics(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "strict": sum(value == 1.0 for value in values) / len(values),
        "relaxed": sum(values) / len(values),
        "score_counts": dict(Counter(str(value) for value in values)),
    }


def paired(rows: list[dict[str, Any]], method: str, samples: int = 10000) -> dict[str, Any]:
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[row["video_id"]].append(row)
    videos = sorted(by_video)
    rng = random.Random(2026080401 + sum(ord(char) for char in method))
    strict, relaxed = [], []
    for _ in range(samples):
        sampled = [item for video in rng.choices(videos, k=len(videos)) for item in by_video[video]]
        strict.append(sum(int(item[method] == 1) - int(item["A0"] == 1) for item in sampled) / len(sampled))
        relaxed.append(sum(item[method] - item["A0"] for item in sampled) / len(sampled))
    return {
        "wins": sum(row[method] > row["A0"] for row in rows),
        "ties": sum(row[method] == row["A0"] for row in rows),
        "losses": sum(row[method] < row["A0"] for row in rows),
        "wrong_to_right": sum(row["A0"] == 0 and row[method] == 1 for row in rows),
        "right_to_wrong": sum(row["A0"] == 1 and row[method] < 1 for row in rows),
        "strict_delta": sum(int(row[method] == 1) - int(row["A0"] == 1) for row in rows) / len(rows),
        "relaxed_delta": sum(row[method] - row["A0"] for row in rows) / len(rows),
        "correction_precision": (
            sum(row[method] > row["A0"] for row in rows)
            / max(1, sum(row[method] != row["A0"] for row in rows))
        ),
        "video_cluster_bootstrap_ci95": {
            "samples": samples,
            "clusters": len(videos),
            "strict_delta": [percentile(strict, 0.025), percentile(strict, 0.975)],
            "relaxed_delta": [percentile(relaxed, 0.025), percentile(relaxed, 0.975)],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(args.project_root / "evaluation/tools"))
    from judge_adsqa_answer_lora_oof_v1 import (  # noqa: PLC0415
        JudgeProtocolError, VALID_SCORES, legacy_parse_score, legacy_protocol
    )

    preflight = json.loads((args.preflight_root / "preflight.json").read_text(encoding="utf-8"))
    pending = jsonl(args.preflight_root / "pending_new_scores.jsonl")
    candidates = jsonl(args.preflight_root / "candidates_answer_free.jsonl")
    reused = jsonl(args.preflight_root / "reused_scores.jsonl")
    if preflight.get("passed") is not True or preflight.get("api_called") is not False:
        raise JudgeProtocolError("preflight did not pass")
    if int(preflight.get("new_api_calls", -1)) != 6 or len(pending) != 6:
        raise JudgeProtocolError("authorized call set is not exactly six")
    if len(candidates) != 400 or len(reused) != 101:
        raise JudgeProtocolError("frozen candidate/reuse counts changed")

    wanted = {str(row["question_id"]) for row in pending}
    gt = {str(row["question_id"]): row for row in json.loads(args.groundtruth.read_text(encoding="utf-8")) if str(row["question_id"]) in wanted}
    if set(gt) != wanted:
        raise JudgeProtocolError("private references do not cover pending candidates")
    protocol = legacy_protocol(args.legacy_evaluator)
    validation = {
        "passed": True,
        "expected_new_calls": 6,
        "candidate_hashes": sorted(row["prediction_sha256"] for row in pending),
        "judge_model": protocol["model_name"],
        "prompt_sha256": protocol["prompt_sha256"],
        "api_called": False,
        "not_human_gold": True,
    }
    dump(args.output_dir / "validation.json", validation)
    if args.validate_only:
        print(json.dumps(validation))
        return
    if (args.output_dir / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite completed output")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")

    from openai import OpenAI
    client = OpenAI(api_key=key, base_url=protocol["base_url"], timeout=60.0)
    api_rows = []
    for item in pending:
        reference = gt[str(item["question_id"])]
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"], question=reference["question"],
            golden_answer=reference["answer"], response=item["prediction"],
        )
        response = client.chat.completions.create(
            model=protocol["model_name"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0, max_tokens=20,
        )
        output = str(response.choices[0].message.content)
        score = legacy_parse_score(output)
        if score not in VALID_SCORES:
            raise JudgeProtocolError(f"unparsed output for {item['question_id']}")
        usage = getattr(response, "usage", None)
        api_rows.append({
            "question_id": item["question_id"], "prediction_sha256": item["prediction_sha256"],
            "score": score, "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "not_human_gold": True,
        })
    dump_jsonl(args.output_dir / "api_results.jsonl", api_rows)

    score_map = {(row["question_id"], row["prediction_sha256"]): float(row["score"]) for row in reused + api_rows}
    expanded = []
    for row in candidates:
        key_pair = (row["question_id"], row["prediction_sha256"])
        if key_pair not in score_map:
            raise JudgeProtocolError(f"missing score for {key_pair}")
        expanded.append({**row, "score": score_map[key_pair]})
    dump_jsonl(args.output_dir / "expanded_scores400.jsonl", expanded)
    by_qid: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in expanded:
        by_qid[row["question_id"]][row["method"]] = float(row["score"])
        by_qid[row["question_id"]]["video_id"] = row["video_id"]
    if any(set(row) != {"A0", "ActiveLook", "FullOnly", "RandomLook", "video_id"} for row in by_qid.values()):
        raise JudgeProtocolError("incomplete four-arm score matrix")
    paired_rows = [{"question_id": qid, **row} for qid, row in sorted(by_qid.items())]
    dump_jsonl(args.output_dir / "paired_results100.jsonl", paired_rows)
    usage = Counter()
    for row in api_rows:
        for name, value in (row.get("judge_usage") or {}).items():
            if isinstance(value, int):
                usage[name] += value
    methods = ("A0", "ActiveLook", "FullOnly", "RandomLook")
    summary = {
        "schema_version": "qwen25_active_evidence_confirm100_judge_v1",
        "methods": {method: metrics([row[method] for row in paired_rows]) for method in methods},
        "paired_vs_a0": {method: paired(paired_rows, method) for method in methods[1:]},
        "judge_protocol": {
            "model": protocol["model_name"], "prompt_sha256": protocol["prompt_sha256"],
            "historical_exact_reuses": len(reused), "new_api_calls": len(api_rows),
            "automatic_retries": 0, "failures": 0, "usage": dict(usage),
            "not_human_gold": True,
        },
    }
    dump(args.output_dir / "summary.json", summary)
    (args.output_dir / "JUDGE_COMPLETE").write_text("complete\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
