#!/usr/bin/env python3
"""Authorized answer-only judge for an OCR x crop factorial experiment."""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any

import numpy as np

from judge_adsqa_answer_lora_oof_v1 import (
    VALID_SCORES,
    legacy_parse_score,
    legacy_protocol,
)


ARMS = ("crop_on", "crop_off", "full_on", "full_off")
COMPARISONS = (
    ("crop_on", "full_on"),
    ("crop_off", "full_off"),
    ("crop_on", "crop_off"),
    ("full_on", "full_off"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise RuntimeError(f"expected list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def answer_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def metric(score: float, relaxed: bool) -> float:
    if not relaxed:
        return float(score == 1.0)
    return 1.0 if score == 1.0 else 0.5 if score == 0.5 else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--authorization-manifest", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    preflight_path = args.preflight_root / "preflight_audit.json"
    candidates_path = args.preflight_root / "candidates_answer_free.jsonl"
    pending_path = args.preflight_root / "pending_candidates_answer_only.jsonl"
    reused_path = args.preflight_root / "reused_scores.jsonl"
    conflicts_path = args.preflight_root / "cache_conflicts.jsonl"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    authorization = json.loads(args.authorization_manifest.read_text(encoding="utf-8"))
    if preflight.get("passed") is not True or preflight.get("groundtruth_read") is not False:
        raise RuntimeError("invalid preflight")
    pending = read_records(pending_path)
    reused = read_records(reused_path)
    conflicts = read_records(conflicts_path)
    if conflicts:
        raise RuntimeError("historical score conflicts present")
    if (
        int(preflight["required_new_api_call_count"]) != len(pending)
        or int(authorization["authorized_new_api_call_count"]) != len(pending)
        or authorization.get("automatic_retries") != 0
        or authorization["input_sha256"]["preflight"] != sha256_file(preflight_path)
        or authorization["input_sha256"]["pending"] != sha256_file(pending_path)
        or authorization["input_sha256"]["groundtruth"] != sha256_file(args.groundtruth)
        or authorization["input_sha256"]["dataset"] != sha256_file(args.dataset)
        or authorization["input_sha256"]["legacy_evaluator"] != sha256_file(args.legacy_evaluator)
    ):
        raise RuntimeError("authorization manifest mismatch")

    protocol = legacy_protocol(args.legacy_evaluator)
    if args.validate_only:
        print(json.dumps({
            "validated": True,
            "authorized_calls": len(pending),
            "historical_reuse": len(reused),
            "judge_model": protocol["model_name"],
            "prompt_sha256": protocol["prompt_sha256"],
        }, indent=2))
        return

    groundtruth = read_records(args.groundtruth)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    candidates = read_records(candidates_path)
    if any(str(row["question_id"]) not in gt_by_id for row in candidates):
        raise RuntimeError("missing private reference")

    score_by_key: dict[tuple[str, str], float] = {}
    for row in reused:
        score_by_key[(str(row["question_id"]), str(row["candidate_prediction_sha256"]))] = float(row["score"])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    partial_path = args.output_dir / "api_results_partial.jsonl"
    failure_path = args.output_dir / "api_failures.jsonl"
    completed_keys: set[tuple[str, str]] = set()
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if partial_path.exists():
        for row in read_records(partial_path):
            key = (str(row["question_id"]), str(row["candidate_prediction_sha256"]))
            completed_keys.add(key)
            if row.get("score") in VALID_SCORES:
                score_by_key[key] = float(row["score"])
            for name in usage:
                usage[name] += int(row.get("usage", {}).get(name, 0) or 0)
    if failure_path.exists():
        for row in read_records(failure_path):
            completed_keys.add((str(row["question_id"]), str(row["candidate_prediction_sha256"])))

    pending_by_key = {
        (str(row["question_id"]), str(row["candidate_prediction_sha256"])): row
        for row in pending
    }
    remaining = [row for key, row in pending_by_key.items() if key not in completed_keys]
    if len(completed_keys) + len(remaining) != len(pending):
        raise RuntimeError("checkpoint does not match authorized pending set")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        tree = ast.parse(args.legacy_evaluator.read_text(encoding="utf-8"))
        keys = [
            str(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith("sk-")
            and len(node.value) > 20
        ]
        if len(set(keys)) == 1:
            api_key = keys[0]
    if not api_key:
        raise RuntimeError("DeepSeek API key not found")

    from openai import OpenAI

    prompt_template = protocol["prompt_template"]
    write_lock = threading.Lock()

    def judge(row: dict[str, Any]) -> dict[str, Any]:
        qid = str(row["question_id"])
        gt = gt_by_id[qid]
        prompt = prompt_template.format(
            meta_info=gt.get("meta_info", ""),
            question=gt.get("question", ""),
            golden_answer=gt.get("answer", gt.get("gt_answer", "")),
            response=str(row["candidate_prediction"]),
        )
        client = OpenAI(
            api_key=api_key,
            base_url=protocol["base_url"],
            timeout=60.0,
            max_retries=0,
        )
        try:
            response = client.chat.completions.create(
                model=protocol["model_name"],
                messages=[
                    {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=64,
            )
            output = str(response.choices[0].message.content)
            score = legacy_parse_score(output)
            result = {
                "question_id": qid,
                "candidate_prediction_sha256": row["candidate_prediction_sha256"],
                "owners": row["owners"],
                "score": float(score) if score in VALID_SCORES else None,
                "parse_valid": score in VALID_SCORES,
                "output": output,
                "usage": {
                    "prompt_tokens": int(getattr(response.usage, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(getattr(response.usage, "completion_tokens", 0) or 0),
                    "total_tokens": int(getattr(response.usage, "total_tokens", 0) or 0),
                },
            }
        except Exception as exc:
            result = {
                "question_id": qid,
                "candidate_prediction_sha256": row["candidate_prediction_sha256"],
                "owners": row["owners"],
                "score": None,
                "parse_valid": False,
                "output": f"{type(exc).__name__}: {exc}",
                "usage": {},
            }
        target = partial_path if result["parse_valid"] else failure_path
        with write_lock, target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        return result

    started = time.time()
    fresh_results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(judge, row) for row in remaining]
        for count, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            result = future.result()
            fresh_results.append(result)
            print(f"judge {count}/{len(remaining)} valid={result['parse_valid']}", flush=True)
    for row in fresh_results:
        if row["parse_valid"]:
            key = (str(row["question_id"]), str(row["candidate_prediction_sha256"]))
            score_by_key[key] = float(row["score"])
        for name in usage:
            usage[name] += int(row.get("usage", {}).get(name, 0) or 0)

    scored = []
    for row in candidates:
        qid = str(row["question_id"])
        output = {"question_id": qid}
        for arm in ARMS:
            value = str(row["candidates"][arm])
            key = (qid, answer_hash(value))
            output[arm] = value
            output[f"_score_{arm}"] = score_by_key.get(key)
        scored.append(output)

    dataset_by_id = {str(row["question_id"]): row for row in read_records(args.dataset)}
    if set(dataset_by_id) != {str(row["question_id"]) for row in candidates}:
        raise RuntimeError("dataset and candidate question sets differ")
    rng = np.random.default_rng(20260803)

    def arm_stats(arm: str) -> dict[str, Any]:
        values = [row[f"_score_{arm}"] for row in scored if row[f"_score_{arm}"] is not None]
        return {
            "n": len(values),
            "strict": round(sum(metric(value, False) for value in values) / len(values), 6) if values else None,
            "relaxed": round(sum(metric(value, True) for value in values) / len(values), 6) if values else None,
        }

    def paired(a: str, b: str) -> dict[str, Any]:
        rows = [row for row in scored if row[f"_score_{a}"] is not None and row[f"_score_{b}"] is not None]
        strict_d = [metric(row[f"_score_{a}"], False) - metric(row[f"_score_{b}"], False) for row in rows]
        relaxed_d = [metric(row[f"_score_{a}"], True) - metric(row[f"_score_{b}"], True) for row in rows]
        wins = sum(row[f"_score_{a}"] > row[f"_score_{b}"] for row in rows)
        losses = sum(row[f"_score_{a}"] < row[f"_score_{b}"] for row in rows)
        boot_s, boot_r = [], []
        for _ in range(args.bootstrap_samples):
            sample = rng.integers(0, len(rows), size=len(rows))
            boot_s.append(float(np.mean([strict_d[index] for index in sample])))
            boot_r.append(float(np.mean([relaxed_d[index] for index in sample])))
        return {
            "n": len(rows),
            "wins": wins,
            "ties": len(rows) - wins - losses,
            "losses": losses,
            "strict_delta": round(float(np.mean(strict_d)), 6),
            "relaxed_delta": round(float(np.mean(relaxed_d)), 6),
            "strict_ci95": [round(float(np.percentile(boot_s, 2.5)), 6), round(float(np.percentile(boot_s, 97.5)), 6)],
            "relaxed_ci95": [round(float(np.percentile(boot_r, 2.5)), 6), round(float(np.percentile(boot_r, 97.5)), 6)],
        }

    complete = [row for row in scored if all(row[f"_score_{arm}"] is not None for arm in ARMS)]
    interaction_s = []
    interaction_r = []
    for row in complete:
        interaction_s.append(
            metric(row["_score_crop_on"], False) - metric(row["_score_full_on"], False)
            - metric(row["_score_crop_off"], False) + metric(row["_score_full_off"], False)
        )
        interaction_r.append(
            metric(row["_score_crop_on"], True) - metric(row["_score_full_on"], True)
            - metric(row["_score_crop_off"], True) + metric(row["_score_full_off"], True)
        )
    boot_is, boot_ir = [], []
    if complete:
        for _ in range(args.bootstrap_samples):
            sample = rng.integers(0, len(complete), size=len(complete))
            boot_is.append(float(np.mean([interaction_s[index] for index in sample])))
            boot_ir.append(float(np.mean([interaction_r[index] for index in sample])))

    summary = {
        "schema_version": "ocr_crop_factorial_smoke_judge_v1",
        "not_human_gold": True,
        "question_count": len(candidates),
        "judge_model": protocol["model_name"],
        "prompt_sha256": protocol["prompt_sha256"],
        "authorized_new_api_calls": len(pending),
        "actual_new_api_calls": len(remaining),
        "automatic_retries": 0,
        "historical_reuse_count": len(reused),
        "parse_failure_count": sum(not row["parse_valid"] for row in fresh_results),
        "usage": usage,
        "elapsed_seconds": round(time.time() - started, 3),
        "methods": {arm: arm_stats(arm) for arm in ARMS},
        "comparisons": {f"{a}_vs_{b}": paired(a, b) for a, b in COMPARISONS},
        "interaction": {
            "definition": "(crop_on-full_on)-(crop_off-full_off)",
            "n": len(complete),
            "strict": round(float(np.mean(interaction_s)), 6) if interaction_s else None,
            "relaxed": round(float(np.mean(interaction_r)), 6) if interaction_r else None,
            "strict_ci95": [round(float(np.percentile(boot_is, 2.5)), 6), round(float(np.percentile(boot_is, 97.5)), 6)] if boot_is else None,
            "relaxed_ci95": [round(float(np.percentile(boot_ir, 2.5)), 6), round(float(np.percentile(boot_ir, 97.5)), 6)] if boot_ir else None,
        },
        "video_count": len({str(dataset_by_id[qid]["video_id"]) for qid in dataset_by_id}),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "scored_candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    if fresh_results:
        with (args.output_dir / "api_results.jsonl").open("w", encoding="utf-8") as handle:
            for row in fresh_results:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.output_dir / "JUDGE_COMPLETE").write_text("complete\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
