#!/usr/bin/env python3
"""Judge the frozen ReAd-R Increment Pilot-300 four-arm experiment."""

from __future__ import annotations

import argparse
from collections import defaultdict
import concurrent.futures
import hashlib
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


METHODS = ("Uniform8", "MMR8", "Adaptive12", "ExtraGlobal12")
EXPECTED_QUESTIONS = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--expected-new-calls", type=int, required=True)
    parser.add_argument("--expected-reused", type=int, required=True)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise JudgeProtocolError(f"expected JSON list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


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


def metrics(rows: list[dict[str, Any]], score_key: str) -> dict[str, Any]:
    scores = np.asarray([float(row[score_key]) for row in rows], dtype=float)
    return {
        "rows": int(scores.size),
        "strict": float(np.mean(scores == 1.0)),
        "relaxed": float(np.mean(scores)),
        "counts": {
            "0": int(np.sum(scores == 0.0)),
            "0.5": int(np.sum(scores == 0.5)),
            "1": int(np.sum(scores == 1.0)),
        },
    }


def clustered_interval(
    rows: list[dict[str, Any]],
    selected_key: str,
    baseline_key: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    by_video: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    video_ids = sorted(by_video)
    relaxed_sum = np.asarray(
        [
            sum(float(row[selected_key]) - float(row[baseline_key])
                for row in by_video[video_id])
            for video_id in video_ids
        ],
        dtype=float,
    )
    strict_sum = np.asarray(
        [
            sum(
                float(float(row[selected_key]) == 1.0)
                - float(float(row[baseline_key]) == 1.0)
                for row in by_video[video_id]
            )
            for video_id in video_ids
        ],
        dtype=float,
    )
    counts = np.asarray(
        [len(by_video[video_id]) for video_id in video_ids], dtype=float
    )
    rng = np.random.default_rng(seed)
    relaxed_bootstrap = np.empty(samples, dtype=float)
    strict_bootstrap = np.empty(samples, dtype=float)
    batch_size = 256
    for start in range(0, samples, batch_size):
        stop = min(start + batch_size, samples)
        indices = rng.integers(
            0, len(video_ids), size=(stop - start, len(video_ids))
        )
        denominators = counts[indices].sum(axis=1)
        relaxed_bootstrap[start:stop] = (
            relaxed_sum[indices].sum(axis=1) / denominators
        )
        strict_bootstrap[start:stop] = (
            strict_sum[indices].sum(axis=1) / denominators
        )
    return {
        "relaxed_delta": [
            float(np.quantile(relaxed_bootstrap, 0.025)),
            float(np.quantile(relaxed_bootstrap, 0.975)),
        ],
        "strict_delta": [
            float(np.quantile(strict_bootstrap, 0.025)),
            float(np.quantile(strict_bootstrap, 0.975)),
        ],
        "samples": samples,
        "seed": seed,
        "cluster_count": len(video_ids),
    }


def pairwise(
    rows: list[dict[str, Any]],
    selected_key: str,
    baseline_key: str,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    selected = np.asarray(
        [float(row[selected_key]) for row in rows], dtype=float
    )
    baseline = np.asarray(
        [float(row[baseline_key]) for row in rows], dtype=float
    )
    delta = selected - baseline
    wrong_to_right = int(np.sum((baseline < 1.0) & (selected == 1.0)))
    right_to_wrong = int(np.sum((baseline == 1.0) & (selected < 1.0)))
    strict_changes = wrong_to_right + right_to_wrong
    return {
        "rows": len(rows),
        "wins": int(np.sum(delta > 0)),
        "ties": int(np.sum(delta == 0)),
        "losses": int(np.sum(delta < 0)),
        "mean_relaxed_delta": float(np.mean(delta)),
        "mean_strict_delta": float(
            np.mean((selected == 1.0).astype(float)
                    - (baseline == 1.0).astype(float))
        ),
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "strict_correction_precision": (
            wrong_to_right / strict_changes if strict_changes else None
        ),
        "video_cluster_bootstrap_ci95": clustered_interval(
            rows,
            selected_key,
            baseline_key,
            bootstrap_samples,
            seed,
        ),
    }


def primary_type(row: dict[str, Any]) -> str:
    value = row.get("question_type", ["unknown"])
    if isinstance(value, list) and value:
        return str(value[0])
    return str(value or "unknown")


def validate_inputs(
    args: argparse.Namespace,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    dict[tuple[str, str], list[str]],
    dict[str, Any],
    dict[str, Any],
]:
    if args.workers <= 0 or args.bootstrap_samples != 10000:
        raise JudgeProtocolError(
            "frozen protocol requires positive workers and 10000 bootstrap samples"
        )
    protocol = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    preflight_path = args.preflight_root / "dry_run_audit.json"
    pending_path = (
        args.preflight_root / "pending_candidates_answer_only.jsonl"
    )
    reused_path = args.preflight_root / "reused_scores.jsonl"
    conflicts_path = args.preflight_root / "cache_conflicts.jsonl"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if (
        protocol.get("passed") is not True
        or int(protocol.get("question_count", -1)) != EXPECTED_QUESTIONS
        or protocol.get("groundtruth_read") is not False
        or protocol.get("judge_scores_read") is not False
        or int(protocol.get("deepseek_calls_made", -1)) != 0
    ):
        raise JudgeProtocolError("answer-free protocol audit did not pass")
    if (
        preflight.get("passed") is not True
        or int(preflight.get("question_count", -1)) != EXPECTED_QUESTIONS
        or int(preflight.get("required_new_api_call_count", -1))
        != args.expected_new_calls
        or int(preflight.get("historical_exact_reuse_count", -1))
        != args.expected_reused
        or int(preflight.get("historical_conflict_count", -1)) != 0
        or preflight.get("candidate_mode") != "answer_only"
        or preflight.get("api_called") is not False
        or preflight.get("contains_api_key") is not False
    ):
        raise JudgeProtocolError("authorized Pilot-300 preflight is invalid")
    if (
        sha256_file(args.groundtruth) != preflight["groundtruth_sha256"]
        or sha256_file(args.candidates) != preflight["candidates_sha256"]
        or sha256_file(args.protocol_audit)
        != preflight["protocol_audit_sha256"]
        or sha256_file(args.legacy_evaluator)
        != preflight["legacy_evaluator_sha256"]
        or sha256_file(pending_path) != preflight["pending_sha256"]
        or sha256_file(reused_path) != preflight["reuse_sha256"]
        or sha256_file(conflicts_path) != preflight["conflicts_sha256"]
    ):
        raise JudgeProtocolError("frozen input hash changed after authorization")

    groundtruth = load_records(args.groundtruth)
    candidates = load_records(args.candidates)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    candidate_by_id = {str(row["question_id"]): row for row in candidates}
    if (
        len(groundtruth) != EXPECTED_QUESTIONS
        or len(gt_by_id) != EXPECTED_QUESTIONS
        or len(candidates) != EXPECTED_QUESTIONS
        or len(candidate_by_id) != EXPECTED_QUESTIONS
        or set(gt_by_id) != set(candidate_by_id)
    ):
        raise JudgeProtocolError("candidate/reference pools do not align")

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    answer_by_key: dict[tuple[str, str], str] = {}
    for qid, row in candidate_by_id.items():
        values = row.get("candidates")
        hashes = row.get("candidate_sha256")
        if (
            row.get("groundtruth_included") is not False
            or not isinstance(values, dict)
            or set(values) != set(METHODS)
            or not isinstance(hashes, dict)
        ):
            raise JudgeProtocolError(f"invalid candidate row: {qid}")
        for method in METHODS:
            answer = str(values[method]).strip()
            answer_hash = sha256_text(answer)
            if answer_hash != str(hashes.get(method, "")):
                raise JudgeProtocolError(
                    f"candidate hash mismatch: {qid}:{method}"
                )
            key = (qid, answer_hash)
            owners[key].append(method)
            answer_by_key[key] = answer

    pending_rows = load_records(pending_path)
    reused_rows = load_records(reused_path)
    pending = {
        (str(row["question_id"]),
         str(row["candidate_prediction_sha256"])): row
        for row in pending_rows
    }
    reused = {
        (str(row["question_id"]),
         str(row["candidate_prediction_sha256"])): row
        for row in reused_rows
    }
    if (
        len(pending_rows) != args.expected_new_calls
        or len(pending) != args.expected_new_calls
        or len(reused_rows) != args.expected_reused
        or len(reused) != args.expected_reused
        or set(pending) & set(reused)
        or set(pending) | set(reused) != set(owners)
    ):
        raise JudgeProtocolError("pending/reused score pools do not partition candidates")
    for key, row in pending.items():
        answer = str(row.get("candidate_prediction", "")).strip()
        if (
            answer != answer_by_key[key]
            or sha256_text(answer) != key[1]
            or sorted(map(str, row.get("owners", [])))
            != sorted(owners[key])
        ):
            raise JudgeProtocolError(f"invalid pending row: {key[0]}")
    for key, row in reused.items():
        if (
            float(row.get("score", -1)) not in VALID_SCORES
            or sorted(map(str, row.get("owners", [])))
            != sorted(owners[key])
        ):
            raise JudgeProtocolError(f"invalid reused row: {key[0]}")
    return (
        gt_by_id,
        candidate_by_id,
        pending,
        reused,
        dict(owners),
        protocol,
        preflight,
    )


def main() -> None:
    args = parse_args()
    if (args.output_dir / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite final Pilot-300 results")
    (
        gt_by_id,
        candidate_by_id,
        pending_manifest,
        reused,
        owners,
        protocol,
        preflight,
    ) = validate_inputs(args)
    validation = {
        "passed": True,
        "question_count": len(gt_by_id),
        "new_call_count": len(pending_manifest),
        "reused_score_count": len(reused),
        "unique_score_count": len(owners),
        "api_called": False,
    }
    if args.validate_only:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    judge_protocol = legacy_protocol(args.legacy_evaluator)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    partial_path = args.output_dir / "api_results_partial.jsonl"
    failures_path = args.output_dir / "api_failures.jsonl"
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists():
        for row in load_records(partial_path):
            key = (
                str(row["question_id"]),
                str(row["candidate_prediction_sha256"]),
            )
            partial[key] = row
    if not set(partial).issubset(pending_manifest):
        raise JudgeProtocolError("partial cache contains an unauthorized candidate")
    for key, row in partial.items():
        if (
            str(row.get("candidate_prediction", "")).strip()
            != str(pending_manifest[key]["candidate_prediction"]).strip()
            or float(row.get("score", -1)) not in VALID_SCORES
        ):
            raise JudgeProtocolError(f"invalid partial result: {key[0]}")
    pending_keys = [
        key for key in sorted(pending_manifest) if key not in partial
    ]
    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, candidate_hash = key
        candidate = str(
            pending_manifest[key]["candidate_prediction"]
        ).strip()
        reference = gt_by_id[qid]
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
                    "content": (
                        "You are a helpful assistant acting as an "
                        "evaluation judge."
                    ),
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
            "candidate_prediction_sha256": candidate_hash,
            "owners": owners[key],
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": (
                usage.model_dump() if hasattr(usage, "model_dump") else None
            ),
            "score_source": "current_readr_increment_pilot300_api",
        }

    failures: list[dict[str, Any]] = []
    if pending_keys:
        with partial_path.open("a", encoding="utf-8") as handle:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers
            ) as executor:
                futures = {
                    executor.submit(judge_one, key): key
                    for key in pending_keys
                }
                for completed, future in enumerate(
                    concurrent.futures.as_completed(futures), start=1
                ):
                    key = futures[future]
                    try:
                        row = future.result()
                    except Exception as error:
                        failures.append(
                            {
                                "question_id": key[0],
                                "candidate_prediction_sha256": key[1],
                                "error": repr(error),
                            }
                        )
                    else:
                        partial[key] = row
                        handle.write(
                            json.dumps(row, ensure_ascii=False) + "\n"
                        )
                        handle.flush()
                    if completed % 50 == 0 or completed == len(pending_keys):
                        print(
                            f"attempted={completed}/{len(pending_keys)} "
                            f"total_succeeded={len(partial)} "
                            f"failures={len(failures)}",
                            flush=True,
                        )
    if failures:
        write_jsonl(failures_path, failures)
        raise JudgeProtocolError(
            f"{len(failures)} one-shot calls failed; no automatic retries"
        )
    if set(partial) != set(pending_manifest):
        raise JudgeProtocolError("API cache does not exactly cover pending calls")

    all_scores = {
        key: float(row["score"]) for key, row in reused.items()
    }
    all_scores.update(
        {key: float(row["score"]) for key, row in partial.items()}
    )

    expanded: list[dict[str, Any]] = []
    for qid, source in sorted(candidate_by_id.items()):
        values = source["candidates"]
        hashes = source["candidate_sha256"]
        row: dict[str, Any] = {
            "question_id": qid,
            "video_id": str(source["video_id"]),
            "question_type": primary_type(source),
            "pilot_partition": str(source["pilot_partition"]),
        }
        for method in METHODS:
            row[f"{method}_score"] = all_scores[
                (qid, str(hashes[method]))
            ]
        expanded.append(row)
    write_jsonl(args.output_dir / "expanded_four_method_scores.jsonl", expanded)

    comparisons_spec = [
        ("MMR8_vs_Uniform8", "MMR8_score", "Uniform8_score"),
        (
            "Adaptive12_vs_Uniform8",
            "Adaptive12_score",
            "Uniform8_score",
        ),
        (
            "ExtraGlobal12_vs_Uniform8",
            "ExtraGlobal12_score",
            "Uniform8_score",
        ),
        (
            "Adaptive12_vs_MMR8",
            "Adaptive12_score",
            "MMR8_score",
        ),
        (
            "ExtraGlobal12_vs_MMR8",
            "ExtraGlobal12_score",
            "MMR8_score",
        ),
        (
            "ExtraGlobal12_vs_Adaptive12",
            "ExtraGlobal12_score",
            "Adaptive12_score",
        ),
    ]

    def comparisons(
        rows: list[dict[str, Any]], seed_base: int
    ) -> dict[str, Any]:
        return {
            name: pairwise(
                rows,
                selected_key,
                baseline_key,
                args.bootstrap_samples,
                seed_base + index,
            )
            for index, (name, selected_key, baseline_key)
            in enumerate(comparisons_spec)
        }

    type_results: dict[str, Any] = {}
    for question_type in sorted(
        {row["question_type"] for row in expanded}
    ):
        subset = [
            row for row in expanded
            if row["question_type"] == question_type
        ]
        type_results[question_type] = {
            method: metrics(subset, f"{method}_score")
            for method in METHODS
        }
    usage_totals = {
        key: sum(
            int((row.get("judge_usage") or {}).get(key) or 0)
            for row in partial.values()
        )
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary = {
        "schema_version": "readr_increment_pilot300_judge_summary_v1",
        "not_human_gold": True,
        "authorized_new_calls": args.expected_new_calls,
        "actual_new_successful_calls": len(partial),
        "historical_exact_reuse_count": len(reused),
        "expanded_record_count": len(expanded) * len(METHODS),
        "one_shot_failures": 0,
        "automatic_retries": 0,
        "judge_response_models": sorted(
            {
                str(row.get("judge_response_model"))
                for row in partial.values()
            }
        ),
        "new_api_usage_totals": usage_totals,
        "pilot300": {
            method: metrics(expanded, f"{method}_score")
            for method in METHODS
        },
        "complete_comparisons": comparisons(expanded, 2026072900),
        "question_type_stratified": type_results,
        "raw_arm_protocol": protocol,
        "protocol_hashes": {
            "groundtruth_sha256": sha256_file(args.groundtruth),
            "candidates_sha256": sha256_file(args.candidates),
            "protocol_audit_sha256": sha256_file(args.protocol_audit),
            "preflight_audit_sha256": sha256_file(
                args.preflight_root / "dry_run_audit.json"
            ),
            "pending_sha256": preflight["pending_sha256"],
            "reuse_sha256": preflight["reuse_sha256"],
            "legacy_evaluator_sha256": (
                judge_protocol["legacy_evaluator_sha256"]
            ),
            "judge_prompt_sha256": judge_protocol["prompt_sha256"],
            "parse_score_source_sha256": (
                judge_protocol["parse_score_source_sha256"]
            ),
        },
    }
    dump_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
