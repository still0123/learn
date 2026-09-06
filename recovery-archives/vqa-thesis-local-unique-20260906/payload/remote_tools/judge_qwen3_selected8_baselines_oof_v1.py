#!/usr/bin/env python3
"""Judge three Qwen3 selected-frame baselines against frozen Uniform8 scores."""

from __future__ import annotations

import argparse
from collections import defaultdict
import concurrent.futures
import json
import os
from pathlib import Path
import threading
import time
from typing import Any

from judge_adsqa_answer_lora_oof_v1 import (
    JudgeProtocolError,
    VALID_SCORES,
    cluster_bootstrap_ci,
    extract_answer_section,
    legacy_parse_score,
    legacy_protocol,
    load_groundtruth,
    score_summary,
    sha256_bytes,
    sha256_file,
    truncate_words,
)


UNIFORM = "CleanQwen3_Uniform8"
CLIP = "CleanQwen3_CLIPTopK8"
MMR = "CleanQwen3_MMR8"
VIDEOITG = "CleanQwen3_VideoITG8"
NEW_METHODS = (CLIP, MMR, VIDEOITG)
METHODS = (UNIFORM,) + NEW_METHODS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--selected-root", type=Path, required=True)
    parser.add_argument(
        "--protocol-audit", type=Path, action="append", required=True
    )
    parser.add_argument("--historical-results", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def prediction_path(
    selected_root: Path, method: str, question_id: str
) -> Path:
    subdir = {
        CLIP: "CLIPTopK8",
        MMR: "MMR8",
        VIDEOITG: "VideoITG8",
    }[method]
    root = selected_root / subdir
    direct = root / question_id / "prediction.json"
    if direct.is_file():
        return direct
    matches = sorted(root.glob(f"shard*/{question_id}/prediction.json"))
    if len(matches) != 1:
        raise JudgeProtocolError(
            f"expected one {method} prediction for {question_id}, got {matches}"
        )
    return matches[0]


def load_selected_predictions(
    selected_root: Path, method: str, question_ids: list[str]
) -> dict[str, dict[str, Any]]:
    rows = {}
    for question_id in question_ids:
        path = prediction_path(selected_root, method, question_id)
        item = json.loads(path.read_text(encoding="utf-8"))
        if str(item.get("question_id")) != question_id:
            raise JudgeProtocolError(f"question ID mismatch: {path}")
        raw = str(item.get("prediction", "")).strip()
        if not raw:
            raise JudgeProtocolError(f"empty prediction: {path}")
        candidate, found, marker = extract_answer_section(raw)
        candidate = truncate_words(candidate)
        rows[question_id] = {
            "prediction": candidate,
            "candidate_prediction_sha256": sha256_bytes(
                candidate.encode("utf-8")
            ),
            "source_prediction_sha256": sha256_bytes(raw.encode("utf-8")),
            "answer_extraction_found": found,
            "answer_extraction_marker": marker,
            "path": str(path),
        }
    return rows


def load_historical_uniform(
    path: Path, question_ids: list[str]
) -> dict[str, dict[str, Any]]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("method") != "CleanQwen3_Raw8":
            continue
        question_id = str(row.get("question_id", ""))
        if question_id in rows:
            raise JudgeProtocolError(
                f"duplicate historical Uniform8 score: {question_id}"
            )
        score = float(row.get("score"))
        if score not in VALID_SCORES:
            raise JudgeProtocolError(
                f"invalid historical score for {question_id}: {score}"
            )
        rows[question_id] = row
    if set(rows) != set(question_ids):
        raise JudgeProtocolError(
            "historical Uniform8 scores do not cover frozen GroupCV-500"
        )
    return rows


def pairwise(
    expanded: list[dict[str, Any]],
    challenger: str,
    reference: str,
    samples: int,
) -> dict[str, Any]:
    by_question: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in expanded:
        by_question[str(row["question_id"])][str(row["method"])] = row
    rows = []
    for question_id, methods in by_question.items():
        challenger_score = float(methods[challenger]["score"])
        reference_score = float(methods[reference]["score"])
        rows.append(
            {
                "question_id": question_id,
                "video": str(methods[challenger]["video"]),
                "relaxed_delta": challenger_score - reference_score,
                "strict_delta": float(challenger_score == 1.0)
                - float(reference_score == 1.0),
                "wrong_to_right": (
                    reference_score < 1.0 and challenger_score == 1.0
                ),
                "right_to_wrong": (
                    reference_score == 1.0 and challenger_score < 1.0
                ),
            }
        )
    relaxed = [float(row["relaxed_delta"]) for row in rows]
    strict = [float(row["strict_delta"]) for row in rows]
    wrong_to_right = sum(bool(row["wrong_to_right"]) for row in rows)
    right_to_wrong = sum(bool(row["right_to_wrong"]) for row in rows)
    changed = wrong_to_right + right_to_wrong
    return {
        "shared": len(rows),
        "challenger_wins": sum(value > 0 for value in relaxed),
        "ties": sum(value == 0 for value in relaxed),
        "reference_wins": sum(value < 0 for value in relaxed),
        "mean_relaxed_delta": sum(relaxed) / len(relaxed),
        "mean_strict_delta": sum(strict) / len(strict),
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "strict_correction_precision": (
            wrong_to_right / changed if changed else None
        ),
        "video_cluster_bootstrap_ci95": {
            "relaxed_delta": cluster_bootstrap_ci(
                rows, "relaxed_delta", samples
            ),
            "strict_delta": cluster_bootstrap_ci(
                rows, "strict_delta", samples
            ),
            "samples": samples,
            "seed": 42,
        },
    }


def main() -> None:
    args = parse_args()
    if args.workers <= 0 or args.bootstrap_samples < 0:
        raise JudgeProtocolError("invalid workers or bootstrap count")
    if len(args.protocol_audit) != 4:
        raise JudgeProtocolError("exactly four protocol audits are required")
    audits = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.protocol_audit
    ]
    if any(audit.get("passed") is not True for audit in audits):
        raise JudgeProtocolError("a selected-frame protocol audit failed")
    if sum(int(audit.get("completed_count", -1)) for audit in audits) != 1500:
        raise JudgeProtocolError("protocol audits do not cover 1500 records")

    groundtruth = load_groundtruth(args.groundtruth)
    if len(groundtruth) != 500:
        raise JudgeProtocolError("judge requires frozen GroupCV-500")
    question_ids = [str(row["question_id"]) for row in groundtruth]
    by_question = {str(row["question_id"]): row for row in groundtruth}
    historical = load_historical_uniform(
        args.historical_results, question_ids
    )
    protocol = legacy_protocol(args.legacy_evaluator)
    predictions = {
        method: load_selected_predictions(
            args.selected_root, method, question_ids
        )
        for method in NEW_METHODS
    }

    historical_by_hash = {
        (question_id, str(row["candidate_prediction_sha256"])): row
        for question_id, row in historical.items()
    }
    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    candidates_by_key: dict[tuple[str, str], str] = {}
    for method, rows in predictions.items():
        for question_id, row in rows.items():
            key = (
                question_id,
                str(row["candidate_prediction_sha256"]),
            )
            owners[key].append(method)
            candidates_by_key[key] = str(row["prediction"])

    all_keys = sorted(owners)
    reused_keys = {
        key: historical_by_hash[key]
        for key in all_keys
        if key in historical_by_hash
    }
    call_keys = [key for key in all_keys if key not in reused_keys]
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    dry_run = {
        "schema_version": "adsqa_qwen3_selected8_judge_dry_run_v1",
        "passed": True,
        "question_count": len(question_ids),
        "new_method_count": len(NEW_METHODS),
        "expanded_new_record_count": len(question_ids) * len(NEW_METHODS),
        "required_api_call_count": len(call_keys),
        "historical_uniform_reuse_count": len(reused_keys),
        "cross_new_duplicate_record_count": sum(
            max(0, len(methods) - 1) for methods in owners.values()
        ),
        "methods": list(METHODS),
        "candidate_mode": "answer_only",
        "legacy_evaluator_sha256": protocol["legacy_evaluator_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "parse_score_source_sha256": protocol[
            "parse_score_source_sha256"
        ],
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "historical_results_sha256": sha256_file(
            args.historical_results
        ),
        "protocol_audit_sha256": {
            str(path): sha256_file(path) for path in args.protocol_audit
        },
        "submitted_fields": [
            "meta_info",
            "question",
            "golden_answer",
            "candidate_answer",
        ],
        "video_or_cache_submitted": False,
        "contains_api_key": False,
        "not_human_gold": True,
    }
    (output_root / "dry_run_audit.json").write_text(
        json.dumps(dry_run, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(dry_run, ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    results_path = output_root / "results.jsonl"
    partial_path = output_root / "api_results_partial.jsonl"
    if results_path.exists():
        raise JudgeProtocolError(
            f"refusing to overwrite final results: {results_path}"
        )
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists():
        for line in partial_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (
                str(row["question_id"]),
                str(row["candidate_prediction_sha256"]),
            )
            partial[key] = row
    if not set(partial).issubset(set(call_keys)):
        raise JudgeProtocolError("partial cache contains non-frozen candidates")

    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        question_id, candidate_hash = key
        candidate = candidates_by_key[key]
        reference = by_question[question_id]
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=candidate,
        )
        if not hasattr(local, "client"):
            from openai import OpenAI

            local.client = OpenAI(
                api_key=api_key,
                base_url=protocol["base_url"],
                timeout=60.0,
            )
        last_error = ""
        for attempt in range(3):
            try:
                response = local.client.chat.completions.create(
                    model=protocol["model_name"],
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
                judge_output = str(response.choices[0].message.content)
                score = legacy_parse_score(judge_output)
                if score not in VALID_SCORES:
                    raise JudgeProtocolError(
                        f"unparsed output for {question_id}: "
                        f"{judge_output!r}"
                    )
                usage = getattr(response, "usage", None)
                return {
                    "question_id": question_id,
                    "candidate_prediction": candidate,
                    "candidate_prediction_sha256": candidate_hash,
                    "score": score,
                    "judge_output": judge_output,
                    "judge_response_model": getattr(
                        response, "model", None
                    ),
                    "judge_usage": (
                        usage.model_dump()
                        if hasattr(usage, "model_dump") else None
                    ),
                    "attempt_count": attempt + 1,
                    "retry_count": attempt,
                    "score_source": "current_batch_api",
                }
            except Exception as error:
                last_error = repr(error)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise JudgeProtocolError(
            f"judge failed after retries for {question_id}: {last_error}"
        )

    pending = [key for key in call_keys if key not in partial]
    if pending:
        with partial_path.open("a", encoding="utf-8") as handle:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers
            ) as executor:
                futures = {
                    executor.submit(judge_one, key): key for key in pending
                }
                for count, future in enumerate(
                    concurrent.futures.as_completed(futures), start=1
                ):
                    row = future.result()
                    key = (
                        str(row["question_id"]),
                        str(row["candidate_prediction_sha256"]),
                    )
                    partial[key] = row
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                    if count % 25 == 0 or count == len(pending):
                        print(f"judged={count}/{len(pending)}", flush=True)
    if set(partial) != set(call_keys):
        raise JudgeProtocolError("API cache does not cover frozen candidates")

    expanded = []
    for question_id in question_ids:
        historical_row = historical[question_id]
        expanded.append(
            {
                "method": UNIFORM,
                "question_id": question_id,
                "video": str(by_question[question_id]["video"]),
                "score": float(historical_row["score"]),
                "judge_output": historical_row.get("judge_output"),
                "judge_response_model": historical_row.get(
                    "judge_response_model"
                ),
                "judge_usage": historical_row.get("judge_usage"),
                "candidate_prediction_sha256": historical_row[
                    "candidate_prediction_sha256"
                ],
                "source_prediction_sha256": historical_row[
                    "source_prediction_sha256"
                ],
                "answer_extraction_found": historical_row[
                    "answer_extraction_found"
                ],
                "answer_extraction_marker": historical_row[
                    "answer_extraction_marker"
                ],
                "score_source": "frozen_historical_current_batch",
            }
        )
    for method in NEW_METHODS:
        for question_id in question_ids:
            candidate = predictions[method][question_id]
            key = (
                question_id,
                str(candidate["candidate_prediction_sha256"]),
            )
            source = reused_keys.get(key) or partial[key]
            expanded.append(
                {
                    "method": method,
                    "question_id": question_id,
                    "video": str(by_question[question_id]["video"]),
                    "score": float(source["score"]),
                    "judge_output": source.get("judge_output"),
                    "judge_response_model": source.get(
                        "judge_response_model"
                    ),
                    "judge_usage": source.get("judge_usage"),
                    "candidate_prediction_sha256": candidate[
                        "candidate_prediction_sha256"
                    ],
                    "source_prediction_sha256": candidate[
                        "source_prediction_sha256"
                    ],
                    "answer_extraction_found": candidate[
                        "answer_extraction_found"
                    ],
                    "answer_extraction_marker": candidate[
                        "answer_extraction_marker"
                    ],
                    "score_source": (
                        "frozen_uniform_exact_duplicate"
                        if key in reused_keys
                        else "current_batch_api"
                    ),
                }
            )
    with results_path.open("w", encoding="utf-8") as handle:
        for row in expanded:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in expanded:
        grouped[str(row["method"])].append(row)
    comparisons = [
        (challenger, UNIFORM) for challenger in NEW_METHODS
    ] + [
        (MMR, CLIP),
        (VIDEOITG, CLIP),
        (VIDEOITG, MMR),
    ]
    pairwise_results = {
        f"{challenger}__vs__{reference}": pairwise(
            expanded,
            challenger,
            reference,
            args.bootstrap_samples,
        )
        for challenger, reference in comparisons
    }
    usage = [
        row.get("judge_usage")
        for row in partial.values()
        if isinstance(row.get("judge_usage"), dict)
    ]
    summary = {
        "schema_version": "adsqa_qwen3_selected8_judge_summary_v1",
        "not_human_gold": True,
        "methods": {
            method: score_summary(
                grouped[method], args.bootstrap_samples
            )
            for method in METHODS
        },
        "pairwise": pairwise_results,
        "best_point_estimate": {
            "strict": max(
                METHODS,
                key=lambda method: sum(
                    float(row["score"] == 1.0)
                    for row in grouped[method]
                ),
            ),
            "relaxed": max(
                METHODS,
                key=lambda method: sum(
                    float(row["score"]) for row in grouped[method]
                ),
            ),
        },
        "api": {
            "authorized_call_count": len(call_keys),
            "unique_call_count": len(partial),
            "new_call_count_this_run": len(pending),
            "historical_uniform_reuse_count": len(reused_keys),
            "retry_count": sum(
                int(row.get("retry_count") or 0) for row in partial.values()
            ),
            "final_failure_count": 0,
            "usage": {
                key: sum(int(value.get(key) or 0) for value in usage)
                for key in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                )
            },
            "monetary_cost_reported": False,
        },
        "protocol": dry_run,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
