#!/usr/bin/env python3
"""Judge OOF-500 A2 answers and learn a video-disjoint trigger threshold."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import threading
from typing import Any

from judge_adsqa_answer_lora_oof_v1 import (
    JudgeProtocolError,
    VALID_SCORES,
    legacy_parse_score,
    legacy_protocol,
)


HISTORICAL_METHOD = "CleanQwen3_MMR8"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--a0-scores", type=Path, required=True)
    parser.add_argument("--historical-a0-results", type=Path, required=True)
    parser.add_argument("--historical-a2-api-results", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_inputs(args: argparse.Namespace) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
]:
    audit = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    if (
        audit.get("passed") is not True
        or int(audit.get("question_count", -1)) != 500
        or int(audit.get("video_count", -1)) != 100
        or audit.get("groundtruth_read") is not False
        or audit.get("judge_scores_read") is not False
    ):
        raise JudgeProtocolError("A2 answer-free protocol audit is invalid")

    groundtruth = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    gt = {str(row["question_id"]): row for row in groundtruth}
    dataset = load_jsonl(args.dataset)
    if len(gt) != 500 or len(dataset) != 500:
        raise JudgeProtocolError("calibration set must contain exactly 500 questions")

    historical_rows = [
        row
        for row in load_jsonl(args.historical_a0_results)
        if str(row.get("method")) == HISTORICAL_METHOD
    ]
    historical = {str(row["question_id"]): row for row in historical_rows}
    if len(historical_rows) != 500 or set(historical) != set(gt):
        raise JudgeProtocolError("historical MMR8 scores do not align with OOF-500")

    support_rows = load_jsonl(args.a0_scores)
    support = {
        str(row["source_question_id"]): row for row in support_rows
    }
    if len(support) != 500 or set(support) != set(gt):
        raise JudgeProtocolError("A0 support scores do not align with OOF-500")

    candidates: dict[str, dict[str, Any]] = {}
    for row in dataset:
        qid = str(row["question_id"])
        fold = int(row["fold"])
        prediction_path = (
            args.inference_root / f"fold_{fold}" / qid / "a2_prediction.json"
        )
        trace_path = args.inference_root / f"fold_{fold}" / qid / "a2_trace.json"
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if (
            trace.get("parse_valid") is not True
            or prediction.get("method") != "Qwen3_AVEvidenceRewrite12_A2"
        ):
            raise JudgeProtocolError(f"invalid A2 prediction for {qid}")
        candidates[qid] = {
            "question_id": qid,
            "video_id": str(row["video_id"]),
            "fold": fold,
            "a0_prediction": str(row["a0_prediction"]),
            "a2_prediction": str(prediction["prediction"]),
            "a0_support_probability": float(support[qid]["support_probability"]),
        }
        if sha256_text(str(row["a0_prediction"])) != str(
            historical[qid]["candidate_prediction_sha256"]
        ):
            raise JudgeProtocolError(f"A0 candidate hash mismatch for {qid}")
    if set(candidates) != set(gt):
        raise JudgeProtocolError("A2 predictions do not cover OOF-500")

    historical_a2: dict[tuple[str, str], dict[str, Any]] = {}
    for row in load_jsonl(args.historical_a2_api_results):
        qid = str(row["question_id"])
        candidate = str(row["candidate_prediction"])
        owners = {str(value) for value in row.get("owners", [])}
        if "Qwen3_MMRAVEvidenceRewrite12_A2" in owners:
            historical_a2[(qid, candidate)] = row
    return groundtruth, candidates, historical, historical_a2


def candidate_thresholds(rows: list[dict[str, Any]]) -> list[float]:
    values = sorted({float(row["a0_support_probability"]) for row in rows})
    return (
        [values[0] - 1e-9]
        + [(left + right) / 2 for left, right in zip(values, values[1:])]
        + [values[-1] + 1e-9]
    )


def evaluate_policy(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    policy_scores: list[float] = []
    triggered = 0
    wins = ties = losses = wrong_to_right = right_to_wrong = 0
    for row in rows:
        use_a2 = float(row["a0_support_probability"]) < threshold
        baseline = float(row["a0_score"])
        policy = float(row["a2_score"]) if use_a2 else baseline
        policy_scores.append(policy)
        triggered += int(use_a2)
        wins += int(policy > baseline)
        ties += int(policy == baseline)
        losses += int(policy < baseline)
        wrong_to_right += int(baseline == 0 and policy == 1)
        right_to_wrong += int(baseline == 1 and policy < 1)
    return {
        "rows": len(rows),
        "threshold": threshold,
        "triggered": triggered,
        "trigger_rate": triggered / len(rows),
        "strict": sum(score == 1 for score in policy_scores) / len(rows),
        "relaxed": sum(policy_scores) / len(rows),
        "baseline_strict": sum(float(row["a0_score"]) == 1 for row in rows) / len(rows),
        "baseline_relaxed": sum(float(row["a0_score"]) for row in rows) / len(rows),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
    }


def choose_threshold(rows: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    candidates = [
        (threshold, evaluate_policy(rows, threshold))
        for threshold in candidate_thresholds(rows)
    ]
    threshold, metrics = max(
        candidates,
        key=lambda item: (
            float(item[1]["relaxed"]),
            float(item[1]["strict"]),
            -int(item[1]["right_to_wrong"]),
            -int(item[1]["triggered"]),
        ),
    )
    return threshold, metrics


def bootstrap_delta(
    rows: list[dict[str, Any]],
    policy_key: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    by_video: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_video.setdefault(str(row["video_id"]), []).append(row)
    video_ids = sorted(by_video)
    rng = random.Random(seed)
    relaxed: list[float] = []
    strict: list[float] = []
    for _ in range(samples):
        sampled: list[dict[str, Any]] = []
        for video_id in rng.choices(video_ids, k=len(video_ids)):
            sampled.extend(by_video[video_id])
        relaxed.append(
            sum(float(row[policy_key]) - float(row["a0_score"]) for row in sampled)
            / len(sampled)
        )
        strict.append(
            sum(
                int(float(row[policy_key]) == 1)
                - int(float(row["a0_score"]) == 1)
                for row in sampled
            )
            / len(sampled)
        )
    relaxed.sort()
    strict.sort()
    low = int(0.025 * samples)
    high = min(samples - 1, int(0.975 * samples))
    return {
        "samples": samples,
        "seed": seed,
        "relaxed_delta_ci95": [relaxed[low], relaxed[high]],
        "strict_delta_ci95": [strict[low], strict[high]],
    }


def learn_threshold(
    rows: list[dict[str, Any]],
    bootstrap_samples: int,
) -> dict[str, Any]:
    nested_rows: list[dict[str, Any]] = []
    fold_reports: list[dict[str, Any]] = []
    for fold in range(5):
        train = [row for row in rows if int(row["fold"]) != fold]
        heldout = [row for row in rows if int(row["fold"]) == fold]
        threshold, train_metrics = choose_threshold(train)
        heldout_metrics = evaluate_policy(heldout, threshold)
        fold_reports.append({
            "heldout_fold": fold,
            "learned_threshold": threshold,
            "train_metrics": train_metrics,
            "heldout_metrics": heldout_metrics,
        })
        for row in heldout:
            triggered = float(row["a0_support_probability"]) < threshold
            policy = (
                float(row["a2_score"]) if triggered else float(row["a0_score"])
            )
            nested_rows.append({
                **row,
                "nested_triggered": triggered,
                "nested_policy_score": policy,
            })

    nested_metrics = {
        "rows": len(nested_rows),
        "strict": sum(row["nested_policy_score"] == 1 for row in nested_rows)
        / len(nested_rows),
        "relaxed": sum(row["nested_policy_score"] for row in nested_rows)
        / len(nested_rows),
        "baseline_strict": sum(row["a0_score"] == 1 for row in nested_rows)
        / len(nested_rows),
        "baseline_relaxed": sum(row["a0_score"] for row in nested_rows)
        / len(nested_rows),
        "triggered": sum(bool(row["nested_triggered"]) for row in nested_rows),
        "wins": sum(row["nested_policy_score"] > row["a0_score"] for row in nested_rows),
        "ties": sum(row["nested_policy_score"] == row["a0_score"] for row in nested_rows),
        "losses": sum(row["nested_policy_score"] < row["a0_score"] for row in nested_rows),
        "wrong_to_right": sum(
            row["a0_score"] == 0 and row["nested_policy_score"] == 1
            for row in nested_rows
        ),
        "right_to_wrong": sum(
            row["a0_score"] == 1 and row["nested_policy_score"] < 1
            for row in nested_rows
        ),
    }
    nested_metrics["bootstrap"] = bootstrap_delta(
        nested_rows,
        "nested_policy_score",
        bootstrap_samples,
        2026072901,
    )
    nested_gate = (
        nested_metrics["relaxed"] >= nested_metrics["baseline_relaxed"]
        and nested_metrics["wrong_to_right"] >= nested_metrics["right_to_wrong"]
    )

    final_threshold, final_metrics = choose_threshold(rows)
    for row in rows:
        row["final_policy_score"] = (
            float(row["a2_score"])
            if float(row["a0_support_probability"]) < final_threshold
            else float(row["a0_score"])
        )
    final_metrics["bootstrap"] = bootstrap_delta(
        rows,
        "final_policy_score",
        bootstrap_samples,
        2026072902,
    )

    all_thresholds = candidate_thresholds(rows)
    chosen_index = min(
        range(len(all_thresholds)),
        key=lambda index: abs(all_thresholds[index] - final_threshold),
    )
    sensitivity_indices = sorted({
        max(0, chosen_index - 50),
        max(0, chosen_index - 25),
        chosen_index,
        min(len(all_thresholds) - 1, chosen_index + 25),
        min(len(all_thresholds) - 1, chosen_index + 50),
    })
    return {
        "schema_version": "qwen3_threshold_calibration500_result_v1",
        "selection_objectives_in_order": [
            "maximum_relaxed",
            "maximum_strict",
            "minimum_right_to_wrong",
            "minimum_trigger_rate",
        ],
        "nested_fold_reports": fold_reports,
        "nested_oof_metrics": nested_metrics,
        "nested_gate_passed": nested_gate,
        "final_threshold": final_threshold if nested_gate else None,
        "final_fit_metrics": final_metrics,
        "sensitivity": [
            evaluate_policy(rows, all_thresholds[index])
            for index in sensitivity_indices
        ],
        "full_valid5320_labels_read": False,
    }


def main() -> None:
    args = parse_args()
    if args.workers <= 0 or args.bootstrap_samples != 10000:
        raise JudgeProtocolError("requires positive workers and 10000 bootstrap samples")
    groundtruth, candidates, historical, historical_a2 = load_inputs(args)
    gt = {str(row["question_id"]): row for row in groundtruth}
    judge_protocol = legacy_protocol(args.legacy_evaluator)

    call_keys: list[tuple[str, str]] = []
    reused_a2: dict[tuple[str, str], dict[str, Any]] = {}
    a2_equals_a0 = 0
    for qid, row in candidates.items():
        key = (qid, str(row["a2_prediction"]))
        if row["a2_prediction"] == row["a0_prediction"]:
            a2_equals_a0 += 1
        elif key in historical_a2:
            reused_a2[key] = historical_a2[key]
        else:
            call_keys.append(key)
    call_keys.sort()

    dry_run = {
        "schema_version": "qwen3_threshold_calibration500_judge_dry_run_v1",
        "passed": True,
        "question_count": 500,
        "video_count": 100,
        "historical_a0_score_reuse_count": 500,
        "historical_a2_score_reuse_count": len(reused_a2),
        "a2_equals_a0_count": a2_equals_a0,
        "required_api_call_count": len(call_keys),
        "candidate_mode": "answer_only",
        "legacy_evaluator_sha256": judge_protocol["legacy_evaluator_sha256"],
        "prompt_sha256": judge_protocol["prompt_sha256"],
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "dataset_sha256": sha256_file(args.dataset),
        "protocol_audit_sha256": sha256_file(args.protocol_audit),
        "a0_scores_sha256": sha256_file(args.a0_scores),
        "historical_a0_results_sha256": sha256_file(args.historical_a0_results),
        "historical_a2_api_results_sha256": sha256_file(
            args.historical_a2_api_results
        ),
        "api_called": False,
        "automatic_retry_allowed": False,
        "contains_api_key": False,
        "not_human_gold": True,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    dry_run_path = args.output_root / "dry_run_audit.json"
    if args.dry_run:
        dump_json(dry_run_path, dry_run)
        print(json.dumps(dry_run, ensure_ascii=False, indent=2))
        return

    if not dry_run_path.is_file():
        raise JudgeProtocolError("authorized dry-run audit is missing")
    frozen = json.loads(dry_run_path.read_text(encoding="utf-8"))
    for key in (
        "required_api_call_count",
        "groundtruth_sha256",
        "dataset_sha256",
        "protocol_audit_sha256",
        "a0_scores_sha256",
        "historical_a0_results_sha256",
        "historical_a2_api_results_sha256",
        "legacy_evaluator_sha256",
        "prompt_sha256",
    ):
        if frozen.get(key) != dry_run.get(key):
            raise JudgeProtocolError(f"dry-run changed after authorization: {key}")
    if (args.output_root / "threshold_result.json").exists():
        raise JudgeProtocolError("refusing to overwrite final threshold result")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    partial_path = args.output_root / "api_results_partial.jsonl"
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists():
        for row in load_jsonl(partial_path):
            partial[(str(row["question_id"]), str(row["candidate_prediction"]))] = row
    if not set(partial).issubset(set(call_keys)):
        raise JudgeProtocolError("partial cache contains an unauthorized candidate")
    pending = [key for key in call_keys if key not in partial]
    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, candidate = key
        reference = gt[qid]
        prompt = judge_protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=candidate,
        )
        if not hasattr(local, "client"):
            from openai import OpenAI

            local.client = OpenAI(
                api_key=api_key,
                base_url=judge_protocol["base_url"],
                timeout=60.0,
            )
        response = local.client.chat.completions.create(
            model=judge_protocol["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant acting as an evaluation judge.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        output = str(response.choices[0].message.content)
        score = legacy_parse_score(output)
        if score not in VALID_SCORES:
            raise JudgeProtocolError(f"unparsed judge output for {qid}")
        usage = getattr(response, "usage", None)
        return {
            "question_id": qid,
            "candidate_prediction": candidate,
            "candidate_prediction_sha256": sha256_text(candidate),
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": (
                usage.model_dump() if hasattr(usage, "model_dump") else None
            ),
            "score_source": "threshold_calibration500_api",
        }

    failures: list[dict[str, Any]] = []
    if pending:
        with partial_path.open("a", encoding="utf-8") as handle:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers
            ) as executor:
                futures = {
                    executor.submit(judge_one, key): key for key in pending
                }
                for completed, future in enumerate(
                    concurrent.futures.as_completed(futures), start=1
                ):
                    key = futures[future]
                    try:
                        row = future.result()
                    except Exception as error:
                        failures.append({
                            "question_id": key[0],
                            "candidate_prediction_sha256": sha256_text(key[1]),
                            "error": repr(error),
                        })
                    else:
                        partial[key] = row
                        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                        handle.flush()
                    if completed % 20 == 0 or completed == len(pending):
                        print(
                            f"attempted={completed}/{len(pending)} "
                            f"succeeded={len(partial)} failures={len(failures)}",
                            flush=True,
                        )
    if failures:
        write_jsonl(args.output_root / "api_failures.jsonl", failures)
        raise JudgeProtocolError("one-shot API calls failed; no automatic retries")
    if set(partial) != set(call_keys):
        raise JudgeProtocolError("API results do not cover the frozen call set")

    paired_rows: list[dict[str, Any]] = []
    for qid, candidate in candidates.items():
        a0 = float(historical[qid]["score"])
        key = (qid, str(candidate["a2_prediction"]))
        if candidate["a2_prediction"] == candidate["a0_prediction"]:
            a2 = a0
            source = "historical_a0_exact_duplicate"
        elif key in reused_a2:
            a2 = float(reused_a2[key]["score"])
            source = "historical_a2_exact_reuse"
        else:
            a2 = float(partial[key]["score"])
            source = "threshold_calibration500_api"
        paired_rows.append({
            **candidate,
            "a0_score": a0,
            "a2_score": a2,
            "a2_score_source": source,
        })
    paired_rows.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    write_jsonl(args.output_root / "paired_results500.jsonl", paired_rows)
    result = learn_threshold(paired_rows, args.bootstrap_samples)
    result["judge"] = {
        "actual_new_api_calls": len(partial),
        "historical_a0_score_reuse_count": 500,
        "historical_a2_score_reuse_count": len(reused_a2),
        "a2_equals_a0_count": a2_equals_a0,
    }
    result["input_hashes"] = {
        "paired_results500_sha256": sha256_file(
            args.output_root / "paired_results500.jsonl"
        ),
        "dry_run_audit_sha256": sha256_file(dry_run_path),
    }
    dump_json(args.output_root / "threshold_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
