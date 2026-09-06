#!/usr/bin/env python3
"""Incrementally judge the frozen random-trigger Confirm-D300 control."""

from __future__ import annotations

import argparse
from collections import defaultdict
import concurrent.futures
import json
import os
from pathlib import Path
import threading
from typing import Any

import numpy as np

from judge_adsqa_answer_lora_oof_v1 import (
    JudgeProtocolError,
    VALID_SCORES,
    legacy_parse_score,
    legacy_protocol,
)
from judge_qwen3_selective_rewrite_confirmd300_v1 import (
    METHOD_A0,
    METHOD_A1,
    METHOD_A2,
    METHOD_A3,
    dump_json,
    load_jsonl,
    metrics,
    normalize,
    pairwise,
    primary_type,
    sha256_file,
    sha256_text,
    write_jsonl,
)


METHOD_RANDOM_A3 = "Qwen3_RandomTriggerSelectiveRewrite_A3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "execute"), required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--a0-pool", type=Path, required=True)
    parser.add_argument("--choices", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--existing-api-cache", type=Path, required=True)
    parser.add_argument("--targeted-policy-rows", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorized-new-calls", type=int, default=50)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


def load_inputs(args: argparse.Namespace) -> dict[str, Any]:
    if args.authorized_new_calls != 50:
        raise JudgeProtocolError("this frozen control authorizes exactly 50 new calls")
    if args.workers <= 0 or args.bootstrap_samples != 10000:
        raise JudgeProtocolError("invalid frozen execution settings")
    if (args.output_dir / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite completed random-trigger results")

    protocol_audit = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    if protocol_audit.get("passed") is not True:
        raise JudgeProtocolError("random-trigger answer-free protocol audit did not pass")
    if int(protocol_audit.get("rows", -1)) != 30:
        raise JudgeProtocolError("random-trigger protocol audit is not Trigger-30")

    groundtruth = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    if not isinstance(groundtruth, list) or len(groundtruth) != 300:
        raise JudgeProtocolError("groundtruth is not Confirm-D300")
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    if len(gt_by_id) != 300:
        raise JudgeProtocolError("groundtruth question IDs are not unique")

    pool = load_jsonl(args.a0_pool)
    a0_by_id = {
        str(row["source_question_id"]): str(row["claim"]) for row in pool
    }
    if len(a0_by_id) != 300 or set(a0_by_id) != set(gt_by_id):
        raise JudgeProtocolError("A0 pool and Confirm-D300 do not align")

    choices = load_jsonl(args.choices)
    choice_by_id = {str(row["question_id"]): row for row in choices}
    if len(choice_by_id) != 30 or len(choices) != len(choice_by_id):
        raise JudgeProtocolError("random choices are not 30 unique questions")
    for qid, choice in choice_by_id.items():
        if qid not in gt_by_id:
            raise JudgeProtocolError(f"unknown random-trigger question: {qid}")
        if normalize(choice["a0_prediction"]) != normalize(a0_by_id[qid]):
            raise JudgeProtocolError(f"A0 choice mismatch: {qid}")

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for qid, answer in a0_by_id.items():
        owners[(qid, answer)].append(METHOD_A0)
    for qid, choice in choice_by_id.items():
        owners[(qid, str(choice["a1_prediction"]))].append(METHOD_A1)
        owners[(qid, str(choice["a2_prediction"]))].append(METHOD_A2)
    call_keys = set(owners)

    existing_rows = load_jsonl(args.existing_api_cache)
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    for row in existing_rows:
        key = (str(row["question_id"]), str(row["candidate_prediction"]))
        if key in existing and float(existing[key]["score"]) != float(row["score"]):
            raise JudgeProtocolError(f"conflicting cached score: {key[0]}")
        if float(row["score"]) not in VALID_SCORES:
            raise JudgeProtocolError(f"invalid cached score: {key[0]}")
        existing[key] = row
    reused = {key: existing[key] for key in call_keys if key in existing}
    missing = sorted(call_keys - set(reused))

    if len(call_keys) != 356:
        raise JudgeProtocolError(
            f"random-trigger unique candidate count is {len(call_keys)}, expected 356"
        )
    if len(reused) != 307:
        raise JudgeProtocolError(
            f"exact historical reuse count is {len(reused)}, expected 307"
        )
    if len(missing) != 49 or len(missing) > args.authorized_new_calls:
        raise JudgeProtocolError(
            f"new call count is {len(missing)}, expected 49 and no more than "
            f"the authorized ceiling {args.authorized_new_calls}"
        )

    targeted_rows = load_jsonl(args.targeted_policy_rows)
    targeted_by_id = {str(row["question_id"]): row for row in targeted_rows}
    if len(targeted_by_id) != 300 or set(targeted_by_id) != set(gt_by_id):
        raise JudgeProtocolError("targeted policy rows do not align with Confirm-D300")

    return {
        "protocol_audit": protocol_audit,
        "groundtruth": groundtruth,
        "gt_by_id": gt_by_id,
        "a0_by_id": a0_by_id,
        "choices": choices,
        "choice_by_id": choice_by_id,
        "call_keys": call_keys,
        "reused": reused,
        "missing": missing,
        "targeted_by_id": targeted_by_id,
    }


def protocol_hashes(args: argparse.Namespace) -> dict[str, str]:
    judge = legacy_protocol(args.legacy_evaluator)
    return {
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "a0_pool_sha256": sha256_file(args.a0_pool),
        "choices_sha256": sha256_file(args.choices),
        "protocol_audit_sha256": sha256_file(args.protocol_audit),
        "existing_api_cache_sha256": sha256_file(args.existing_api_cache),
        "targeted_policy_rows_sha256": sha256_file(args.targeted_policy_rows),
        "legacy_evaluator_sha256": judge["legacy_evaluator_sha256"],
        "judge_prompt_sha256": judge["prompt_sha256"],
        "parse_score_source_sha256": judge["parse_score_source_sha256"],
    }


def run_preflight(args: argparse.Namespace, data: dict[str, Any]) -> None:
    if (args.output_dir / "new_api_results_partial.jsonl").exists():
        raise JudgeProtocolError("new-call partial exists; refusing to reset preflight")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit = {
        "schema_version": "random30_incremental_judge_preflight_v1",
        "passed": True,
        "candidate_mode": "answer_only",
        "api_called": False,
        "contains_api_key": False,
        "authorized_max_new_call_count": args.authorized_new_calls,
        "reconstructed_unique_candidate_count": len(data["call_keys"]),
        "exact_historical_reuse_count": len(data["reused"]),
        "required_new_api_call_count": len(data["missing"]),
        "random_trigger_question_count": len(data["choice_by_id"]),
        "complete_policy_question_count": len(data["gt_by_id"]),
        "new_candidate_key_hashes": [
            {
                "question_id": qid,
                "candidate_prediction_sha256": sha256_text(answer),
            }
            for qid, answer in data["missing"]
        ],
        "protocol_hashes": protocol_hashes(args),
    }
    dump_json(args.output_dir / "preflight_audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


def assert_frozen_preflight(
    args: argparse.Namespace,
    data: dict[str, Any],
) -> dict[str, Any]:
    path = args.output_dir / "preflight_audit.json"
    if not path.exists():
        raise JudgeProtocolError("preflight audit is missing")
    audit = json.loads(path.read_text(encoding="utf-8"))
    expected_hashes = protocol_hashes(args)
    checks = [
        audit.get("passed") is True,
        audit.get("api_called") is False,
        audit.get("contains_api_key") is False,
        int(audit.get("authorized_max_new_call_count", -1)) == 50,
        int(audit.get("required_new_api_call_count", -1)) == 49,
        int(audit.get("exact_historical_reuse_count", -1)) == 307,
        int(audit.get("reconstructed_unique_candidate_count", -1)) == 356,
        audit.get("protocol_hashes") == expected_hashes,
    ]
    if not all(checks):
        raise JudgeProtocolError("frozen incremental preflight is invalid or changed")
    expected_missing = [
        {
            "question_id": qid,
            "candidate_prediction_sha256": sha256_text(answer),
        }
        for qid, answer in data["missing"]
    ]
    if audit.get("new_candidate_key_hashes") != expected_missing:
        raise JudgeProtocolError("authorized new candidate set changed after preflight")
    return audit


def score_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return metrics(rows, key)


def run_execute(args: argparse.Namespace, data: dict[str, Any]) -> None:
    preflight = assert_frozen_preflight(args, data)
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    new_partial_path = args.output_dir / "new_api_results_partial.jsonl"
    failures_path = args.output_dir / "new_api_failures.jsonl"
    if new_partial_path.exists() or failures_path.exists():
        raise JudgeProtocolError(
            "one-shot output already exists; refusing automatic retry"
        )

    judge_protocol = legacy_protocol(args.legacy_evaluator)
    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, candidate = key
        reference = data["gt_by_id"][qid]
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
            "score_source": "random30_incremental_deepseek_api",
        }

    new_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with new_partial_path.open("x", encoding="utf-8") as handle:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.workers
        ) as executor:
            futures = {
                executor.submit(judge_one, key): key for key in data["missing"]
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
                    new_rows.append(row)
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                if completed % 10 == 0 or completed == len(data["missing"]):
                    print(
                        f"attempted={completed}/{len(data['missing'])} "
                        f"succeeded={len(new_rows)} failures={len(failures)}",
                        flush=True,
                    )
    if failures:
        write_jsonl(failures_path, failures)
        raise JudgeProtocolError(
            f"{len(failures)} one-shot calls failed; no retries performed"
        )
    if len(new_rows) != len(data["missing"]):
        raise JudgeProtocolError("successful new call count does not cover the 49 missing candidates")

    merged = dict(data["reused"])
    for row in new_rows:
        key = (str(row["question_id"]), str(row["candidate_prediction"]))
        if key in merged:
            raise JudgeProtocolError("new API result duplicates historical reuse")
        merged[key] = row
    if set(merged) != data["call_keys"] or len(merged) != 356:
        raise JudgeProtocolError("merged score map does not cover frozen candidates")
    write_jsonl(
        args.output_dir / "merged_exact_candidate_scores.jsonl",
        [merged[key] for key in sorted(merged)],
    )

    def score(qid: str, answer: str) -> float:
        return float(merged[(qid, answer)]["score"])

    trigger_rows: list[dict[str, Any]] = []
    for qid, choice in sorted(data["choice_by_id"].items()):
        a0_score = score(qid, str(choice["a0_prediction"]))
        a1_score = score(qid, str(choice["a1_prediction"]))
        a2_score = score(qid, str(choice["a2_prediction"]))
        a3_score = a2_score if bool(choice["a3_switched"]) else a0_score
        trigger_rows.append({
            "question_id": qid,
            "video_id": str(choice["video_id"]),
            "question_type": primary_type(data["gt_by_id"][qid]),
            "a0_score": a0_score,
            "a1_score": a1_score,
            "a2_score": a2_score,
            "a3_score": a3_score,
            "a3_switched": bool(choice["a3_switched"]),
            "a3_answer_changed": bool(choice["a3_answer_changed"]),
        })
    write_jsonl(args.output_dir / "results_random_trigger30.jsonl", trigger_rows)
    trigger_by_id = {row["question_id"]: row for row in trigger_rows}

    complete_rows: list[dict[str, Any]] = []
    for qid, reference in sorted(data["gt_by_id"].items()):
        a0_score = score(qid, data["a0_by_id"][qid])
        trigger = trigger_by_id.get(qid)
        targeted = data["targeted_by_id"][qid]
        complete_rows.append({
            "question_id": qid,
            "video_id": str(reference["video"]),
            "question_type": primary_type(reference),
            "a0_score": a0_score,
            "random_a1_score": (
                float(trigger["a1_score"]) if trigger else a0_score
            ),
            "random_a2_score": (
                float(trigger["a2_score"]) if trigger else a0_score
            ),
            "random_a3_score": (
                float(trigger["a3_score"]) if trigger else a0_score
            ),
            "targeted_a3_score": float(targeted["a3_score"]),
            "random_triggered": trigger is not None,
            "random_switched": bool(trigger["a3_switched"]) if trigger else False,
            "targeted_triggered": bool(targeted["triggered"]),
            "targeted_switched": bool(targeted["switched"]),
        })
    write_jsonl(
        args.output_dir / "complete_confirmd300_random_policy_rows.jsonl",
        complete_rows,
    )

    trigger_comparisons = {
        "A1_vs_A0": pairwise(
            trigger_rows, "a1_score", "a0_score", 10000, 2026072811
        ),
        "A2_vs_A0": pairwise(
            trigger_rows, "a2_score", "a0_score", 10000, 2026072812
        ),
        "A3_vs_A0": pairwise(
            trigger_rows, "a3_score", "a0_score", 10000, 2026072813
        ),
        "A2_vs_A1": pairwise(
            trigger_rows, "a2_score", "a1_score", 10000, 2026072814
        ),
    }
    full_comparisons = {
        "RandomA1_vs_A0": pairwise(
            complete_rows, "random_a1_score", "a0_score", 10000, 2026072821
        ),
        "RandomA2_vs_A0": pairwise(
            complete_rows, "random_a2_score", "a0_score", 10000, 2026072822
        ),
        "RandomA3_vs_A0": pairwise(
            complete_rows, "random_a3_score", "a0_score", 10000, 2026072823
        ),
        "TargetedA3_vs_RandomA3": pairwise(
            complete_rows,
            "targeted_a3_score",
            "random_a3_score",
            10000,
            2026072824,
        ),
    }

    type_results: dict[str, Any] = {}
    for index, question_type in enumerate(
        sorted({row["question_type"] for row in complete_rows}), start=1
    ):
        subset = [
            row for row in complete_rows
            if row["question_type"] == question_type
        ]
        type_results[question_type] = {
            METHOD_A0: score_metrics(subset, "a0_score"),
            METHOD_RANDOM_A3: score_metrics(subset, "random_a3_score"),
            "RandomA3_vs_A0": pairwise(
                subset,
                "random_a3_score",
                "a0_score",
                10000,
                2026072900 + index,
            ),
        }

    new_usage = {
        key: sum(
            int((row.get("judge_usage") or {}).get(key) or 0)
            for row in new_rows
        )
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    random_vs_a0 = full_comparisons["RandomA3_vs_A0"]
    targeted_vs_random = full_comparisons["TargetedA3_vs_RandomA3"]
    summary = {
        "schema_version": "random30_incremental_judge_summary_v1",
        "not_human_gold": True,
        "candidate_mode": "answer_only",
        "authorized_max_new_calls": 50,
        "actual_new_successful_calls": len(new_rows),
        "exact_historical_reuse_count": len(data["reused"]),
        "merged_unique_candidate_count": len(merged),
        "one_shot_failures": 0,
        "unauthorized_retries": 0,
        "estimated_cost_usd": None,
        "estimated_cost_note": "Provider billing price was not encoded in the frozen evaluator.",
        "judge_response_models_new_calls": sorted({
            str(row.get("judge_response_model")) for row in new_rows
        }),
        "new_call_usage_totals": new_usage,
        "random_trigger30": {
            METHOD_A0: score_metrics(trigger_rows, "a0_score"),
            METHOD_A1: score_metrics(trigger_rows, "a1_score"),
            METHOD_A2: score_metrics(trigger_rows, "a2_score"),
            METHOD_RANDOM_A3: score_metrics(trigger_rows, "a3_score"),
            "comparisons": trigger_comparisons,
        },
        "complete_confirmd300": {
            METHOD_A0: score_metrics(complete_rows, "a0_score"),
            "RandomTrigger_A1": score_metrics(
                complete_rows, "random_a1_score"
            ),
            "RandomTrigger_A2": score_metrics(
                complete_rows, "random_a2_score"
            ),
            METHOD_RANDOM_A3: score_metrics(
                complete_rows, "random_a3_score"
            ),
            METHOD_A3: score_metrics(complete_rows, "targeted_a3_score"),
            "comparisons": full_comparisons,
        },
        "question_type_stratified_random_a3": type_results,
        "deployment": {
            "random_triggered_questions": len(trigger_rows),
            "random_actual_switches": sum(
                bool(row["a3_switched"]) for row in trigger_rows
            ),
            "random_trigger_rate": len(trigger_rows) / len(complete_rows),
            "random_switch_rate": sum(
                bool(row["a3_switched"]) for row in trigger_rows
            ) / len(complete_rows),
        },
        "control_conclusion": {
            "random_a3_relaxed_delta": random_vs_a0["mean_relaxed_delta"],
            "random_a3_strict_delta": random_vs_a0["mean_strict_delta"],
            "random_a3_wrong_to_right": random_vs_a0["wrong_to_right"],
            "random_a3_right_to_wrong": random_vs_a0["right_to_wrong"],
            "targeted_minus_random_relaxed_delta": (
                targeted_vs_random["mean_relaxed_delta"]
            ),
            "targeted_minus_random_strict_delta": (
                targeted_vs_random["mean_strict_delta"]
            ),
            "targeted_trigger_has_positive_increment_over_random": (
                targeted_vs_random["mean_relaxed_delta"] > 0.0
                and targeted_vs_random["mean_strict_delta"] >= 0.0
            ),
        },
        "protocol_hashes": {
            **preflight["protocol_hashes"],
            "preflight_audit_sha256": sha256_file(
                args.output_dir / "preflight_audit.json"
            ),
        },
    }
    dump_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    data = load_inputs(args)
    if args.mode == "preflight":
        run_preflight(args, data)
    else:
        run_execute(args, data)


if __name__ == "__main__":
    main()
