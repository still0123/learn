#!/usr/bin/env python3
"""Execute the frozen incremental judge for three selective-rewrite ablations."""

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


ABLATIONS = ("no_ocr", "no_segmented_asr", "no_local_crop")
AUTHORIZED_CALLS = 81


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--historical-a0-results", type=Path, required=True)
    parser.add_argument("--historical-rewrite-results", type=Path, required=True)
    parser.add_argument("--full-method-results", type=Path, required=True)
    parser.add_argument("--ablation-root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorized-new-calls", type=int, default=0)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def method_metrics(scores: list[float]) -> dict[str, Any]:
    values = np.asarray(scores, dtype=np.float64)
    return {
        "rows": len(scores),
        "strict": float(np.mean(values == 1.0)),
        "relaxed": float(np.mean(values)),
        "counts": {
            "0": int(np.sum(values == 0.0)),
            "0.5": int(np.sum(values == 0.5)),
            "1": int(np.sum(values == 1.0)),
        },
    }


def bootstrap_delta(
    first: np.ndarray,
    second: np.ndarray,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    relaxed = np.empty(samples, dtype=np.float64)
    strict = np.empty(samples, dtype=np.float64)
    count = len(first)
    for index in range(samples):
        sampled = rng.integers(0, count, size=count)
        relaxed[index] = float(np.mean(first[sampled] - second[sampled]))
        strict[index] = float(
            np.mean(first[sampled] == 1.0) - np.mean(second[sampled] == 1.0)
        )
    return {
        "relaxed_delta": float(np.mean(first - second)),
        "relaxed_ci95": [float(np.quantile(relaxed, 0.025)), float(np.quantile(relaxed, 0.975))],
        "strict_delta": float(np.mean(first == 1.0) - np.mean(second == 1.0)),
        "strict_ci95": [float(np.quantile(strict, 0.025)), float(np.quantile(strict, 0.975))],
    }


def load_frozen(args: argparse.Namespace) -> dict[str, Any]:
    if args.authorized_new_calls != AUTHORIZED_CALLS:
        raise JudgeProtocolError(f"this run requires explicit authorization for {AUTHORIZED_CALLS} calls")
    if args.bootstrap_samples != 10000 or args.workers <= 0:
        raise JudgeProtocolError("invalid frozen execution settings")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise JudgeProtocolError("immutable judge output directory is not empty")
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    if (
        preflight.get("passed") is not True
        or preflight.get("api_called") is not False
        or int(preflight.get("required_new_api_call_count", -1)) != AUTHORIZED_CALLS
        or preflight.get("candidate_mode") != "answer_only"
    ):
        raise JudgeProtocolError("frozen preflight is invalid")

    groundtruth = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    if len(gt_by_id) != 500:
        raise JudgeProtocolError("groundtruth is not OOF500")

    existing: dict[tuple[str, str], dict[str, Any]] = {}
    for source in (args.historical_a0_results, args.historical_rewrite_results):
        for row in load_jsonl(source):
            candidate_hash = str(row.get("candidate_prediction_sha256", ""))
            if not candidate_hash:
                candidate = str(row.get("candidate_prediction", row.get("prediction", "")))
                if not candidate:
                    raise JudgeProtocolError("historical row lacks candidate text and hash")
                candidate_hash = sha256_text(candidate)
            key = (str(row["question_id"]), candidate_hash)
            score = float(row["score"])
            if score not in VALID_SCORES:
                raise JudgeProtocolError(f"invalid historical score for {key[0]}")
            if key in existing and float(existing[key]["score"]) != score:
                raise JudgeProtocolError(f"conflicting historical score for {key[0]}")
            existing[key] = row

    choices_by_ablation: dict[str, list[dict[str, Any]]] = {}
    candidates: dict[tuple[str, str], str] = {}
    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for ablation in ABLATIONS:
        choice_path = args.ablation_root / ablation / "frozen_choices_v1" / "frozen_choices_answer_free.jsonl"
        protocol_path = args.ablation_root / ablation / "frozen_choices_v1" / "protocol_audit.json"
        choices = load_jsonl(choice_path)
        audit = json.loads(protocol_path.read_text(encoding="utf-8"))
        if audit.get("passed") is not True or len(choices) != 50:
            raise JudgeProtocolError(f"{ablation} is not a frozen complete run")
        choices_by_ablation[ablation] = choices
        for row in choices:
            qid = str(row["question_id"])
            if qid not in gt_by_id:
                raise JudgeProtocolError(f"unknown question in {ablation}: {qid}")
            for field in ("a0_prediction", "a1_prediction", "a2_prediction"):
                candidate = str(row[field])
                key = (qid, sha256_text(candidate))
                if key in candidates and candidates[key] != candidate:
                    raise JudgeProtocolError("SHA256 collision in candidate set")
                candidates[key] = candidate
                owners[key].append(f"{ablation}:{field}")

    missing = sorted(set(candidates) - set(existing))
    expected_missing = [
        (str(row["question_id"]), str(row["candidate_prediction_sha256"]))
        for row in preflight["new_candidate_key_hashes"]
    ]
    if missing != expected_missing or len(missing) != AUTHORIZED_CALLS:
        raise JudgeProtocolError("candidate set changed after preflight")
    return {
        "preflight": preflight,
        "gt_by_id": gt_by_id,
        "existing": existing,
        "choices_by_ablation": choices_by_ablation,
        "candidates": candidates,
        "owners": owners,
        "missing": missing,
    }


def main() -> None:
    args = parse_args()
    frozen = load_frozen(args)
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    protocol = legacy_protocol(args.legacy_evaluator)
    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, candidate_hash = key
        candidate = frozen["candidates"][key]
        reference = frozen["gt_by_id"][qid]
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
        response = local.client.chat.completions.create(
            model=protocol["model_name"],
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
            "candidate_prediction_sha256": candidate_hash,
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "score_source": "ablation_incremental_deepseek_api",
            "owners": frozen["owners"][key],
        }

    new_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    partial_path = args.output_dir / "new_api_results_partial.jsonl"
    with partial_path.open("x", encoding="utf-8") as handle:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(judge_one, key): key for key in frozen["missing"]}
            for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
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
                    new_rows.append(row)
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                if completed % 10 == 0 or completed == len(frozen["missing"]):
                    print(f"judged={completed}/{len(frozen['missing'])}", flush=True)
    if failures:
        write_jsonl(args.output_dir / "failures.jsonl", failures)
        raise JudgeProtocolError(f"{len(failures)} judge calls failed; refusing analysis")

    scored = dict(frozen["existing"])
    for row in new_rows:
        key = (str(row["question_id"]), str(row["candidate_prediction_sha256"]))
        scored[key] = row
    full_rows = load_jsonl(args.full_method_results)
    full_by_id = {str(row["question_id"]): float(row["a3_score"]) for row in full_rows}
    if len(full_by_id) != 50:
        raise JudgeProtocolError("full-method result is not the frozen selected50 set")

    summary: dict[str, Any] = {
        "schema_version": "qwen3_selective_rewrite_ablation_judge_summary_v1",
        "actual_api_calls": len(new_rows),
        "required_api_calls": AUTHORIZED_CALLS,
        "candidate_mode": "answer_only",
        "bootstrap_samples": args.bootstrap_samples,
        "ablations": {},
    }
    for ablation_index, ablation in enumerate(ABLATIONS):
        result_rows: list[dict[str, Any]] = []
        for choice in frozen["choices_by_ablation"][ablation]:
            qid = str(choice["question_id"])

            def score(field: str) -> float:
                candidate = str(choice[field])
                return float(scored[(qid, sha256_text(candidate))]["score"])

            row = {
                "question_id": qid,
                "video_id": str(choice["video_id"]),
                "fold": int(choice["fold"]),
                "a0_score": score("a0_prediction"),
                "a1_score": score("a1_prediction"),
                "a2_score": score("a2_prediction"),
                "a3_score": score("a2_prediction") if choice["a3_switched"] else score("a0_prediction"),
                "a3_switched": bool(choice["a3_switched"]),
                "full_method_a3_score": full_by_id[qid],
            }
            result_rows.append(row)
        write_jsonl(args.output_dir / f"results_{ablation}.jsonl", result_rows)
        a0 = np.asarray([row["a0_score"] for row in result_rows], dtype=np.float64)
        a1 = np.asarray([row["a1_score"] for row in result_rows], dtype=np.float64)
        a2 = np.asarray([row["a2_score"] for row in result_rows], dtype=np.float64)
        a3 = np.asarray([row["a3_score"] for row in result_rows], dtype=np.float64)
        full = np.asarray([row["full_method_a3_score"] for row in result_rows], dtype=np.float64)
        summary["ablations"][ablation] = {
            "A0": method_metrics(a0.tolist()),
            "A1": method_metrics(a1.tolist()),
            "A2": method_metrics(a2.tolist()),
            "A3": method_metrics(a3.tolist()),
            "full_method_A3": method_metrics(full.tolist()),
            "A3_vs_A0": {
                "win_tie_loss": [
                    int(np.sum(a3 > a0)),
                    int(np.sum(a3 == a0)),
                    int(np.sum(a3 < a0)),
                ],
                **bootstrap_delta(a3, a0, args.bootstrap_samples, 20260727 + ablation_index),
            },
            "full_method_minus_ablation_A3": {
                "win_tie_loss": [
                    int(np.sum(full > a3)),
                    int(np.sum(full == a3)),
                    int(np.sum(full < a3)),
                ],
                **bootstrap_delta(
                    full,
                    a3,
                    args.bootstrap_samples,
                    20260827 + ablation_index,
                ),
            },
            "trigger_count": int(sum(row["a3_switched"] for row in result_rows)),
        }
    usage_rows = [row.get("judge_usage") or {} for row in new_rows]
    summary["judge_usage_totals"] = {
        key: int(sum(int(row.get(key) or 0) for row in usage_rows))
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary["judge_response_models"] = sorted(
        {str(row.get("judge_response_model")) for row in new_rows}
    )
    summary["protocol_hashes"] = {
        "preflight_sha256": sha256_file(args.preflight),
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "historical_a0_results_sha256": sha256_file(args.historical_a0_results),
        "historical_rewrite_results_sha256": sha256_file(args.historical_rewrite_results),
        "full_method_results_sha256": sha256_file(args.full_method_results),
        "legacy_evaluator_sha256": protocol["legacy_evaluator_sha256"],
        "judge_prompt_sha256": protocol["prompt_sha256"],
    }
    dump_json(args.output_dir / "summary.json", summary)
    (args.output_dir / "JUDGE_COMPLETE").touch()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
