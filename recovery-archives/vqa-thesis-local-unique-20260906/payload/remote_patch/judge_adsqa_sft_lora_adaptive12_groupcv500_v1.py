#!/usr/bin/env python3
"""Judge AdsSFTLoRA MMR8/Adaptive12 controls and calibrate support gates."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
    extract_answer_section,
    legacy_parse_score,
    legacy_protocol,
    truncate_words,
)


METHODS = {
    "MMR8": ("external_mmr", "prediction.json", "AdsSFTLoRA_MMR8"),
    "Adaptive12": (
        "adaptive12",
        "a2_prediction.json",
        "AdsSFTLoRA_Adaptive12_A2",
    ),
    "ExtraGlobal12": (
        "extra_global12",
        "a2_prediction.json",
        "AdsSFTLoRA_ExtraGlobal12_A2",
    ),
}
SUPPORT_FILES = {
    "MMR8": "a0_mmr8_verifier_merged/scores_all.jsonl",
    "Adaptive12": "adaptive12_verifier_merged/scores_all.jsonl",
    "ExtraGlobal12": "extra_global12_verifier_merged/scores_all.jsonl",
}
MARGIN = 0.25
A0_VISUAL_TOKENS = 1024
A2_VISUAL_TOKENS = 3992
EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--mmr-oof-root", type=Path, required=True)
    parser.add_argument(
        "--historical-cache",
        type=Path,
        action="append",
        default=[],
    )
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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
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


def load_historical_caches(
    paths: list[Path],
) -> dict[tuple[str, str], dict[str, Any]]:
    cached: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        audit_path = path.parent / "dry_run_audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if audit.get("prompt_sha256") != EXPECTED_PROMPT_SHA256:
            raise JudgeProtocolError(f"historical cache prompt mismatch: {path}")
        for row in load_jsonl(path):
            key = (
                str(row["question_id"]),
                str(row["candidate_prediction"]),
            )
            score = float(row.get("score", -1))
            if score not in VALID_SCORES:
                raise JudgeProtocolError(f"invalid historical cache score: {key!r}")
            if key in cached and float(cached[key]["score"]) != score:
                raise JudgeProtocolError(f"historical cache disagreement: {key!r}")
            cached[key] = row
    return cached


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def normalize_prediction(raw: str) -> tuple[str, bool, str | None]:
    answer, found, marker = extract_answer_section(raw.strip())
    answer = truncate_words(answer.strip())
    if not answer:
        raise JudgeProtocolError("empty answer after answer-only extraction")
    return answer, found, marker


def load_inputs(args: argparse.Namespace) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, dict[str, Any]]],
    dict[str, dict[str, float]],
    dict[str, int],
    dict[str, str],
]:
    required_markers = [
        args.run_root / "INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION",
        args.run_root / "INFERENCE_SHA256SUMS",
    ]
    if not all(path.is_file() for path in required_markers):
        raise JudgeProtocolError("frozen inference completion markers are missing")

    audits = [
        args.run_root / "a0_mmr8_pool/audit.json",
        args.run_root / "calibration_candidates500/audit.json",
        args.run_root / "a2_controls_protocol_audit.json",
        args.run_root / "adaptive12_verifier_inputs/audit.json",
        args.run_root / "extra_global12_verifier_inputs/audit.json",
    ]
    for path in audits:
        audit = json.loads(path.read_text(encoding="utf-8"))
        if audit.get("passed") is not True:
            raise JudgeProtocolError(f"protocol audit failed: {path}")
        if audit.get("groundtruth_read") is not False:
            raise JudgeProtocolError(f"answer-free audit read ground truth: {path}")
        if audit.get("judge_scores_read") is not False:
            raise JudgeProtocolError(f"answer-free audit read judge scores: {path}")

    groundtruth = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    if len(groundtruth) != 500:
        raise JudgeProtocolError("groundtruth must contain exactly 500 rows")
    gt = {str(row["question_id"]): row for row in groundtruth}
    if len(gt) != 500:
        raise JudgeProtocolError("groundtruth question IDs are not unique")
    folds = {str(row["question_id"]): int(row["fold"]) for row in groundtruth}
    videos = {str(row["question_id"]): str(row["video"]) for row in groundtruth}
    if set(folds.values()) != set(range(5)) or len(set(videos.values())) != 100:
        raise JudgeProtocolError("expected five folds and 100 videos")

    predictions: dict[str, dict[str, dict[str, Any]]] = {}
    for method, (subdir, filename, expected_method) in METHODS.items():
        rows: dict[str, dict[str, Any]] = {}
        method_root = (
            args.mmr_oof_root
            if subdir == "external_mmr"
            else args.run_root / subdir
        )
        paths = sorted(method_root.glob(f"fold_*/*/{filename}"))
        if len(paths) != 500:
            raise JudgeProtocolError(f"{method} has {len(paths)} predictions")
        for path in paths:
            item = json.loads(path.read_text(encoding="utf-8"))
            qid = str(item["question_id"])
            if qid not in gt or qid in rows:
                raise JudgeProtocolError(f"invalid {method} question ID: {qid}")
            if str(item.get("method")) != expected_method:
                raise JudgeProtocolError(f"{method} metadata mismatch for {qid}")
            prediction, found, marker = normalize_prediction(str(item["prediction"]))
            rows[qid] = {
                "prediction": prediction,
                "candidate_prediction_sha256": sha256_text(prediction),
                "answer_extraction_found": found,
                "answer_extraction_marker": marker,
                "source_path": str(path),
            }
        predictions[method] = rows

    support: dict[str, dict[str, float]] = {}
    for method, relative in SUPPORT_FILES.items():
        rows = load_jsonl(args.run_root / relative)
        mapped = {
            str(row["source_question_id"]): float(row["support_probability"])
            for row in rows
        }
        if len(rows) != 500 or set(mapped) != set(gt):
            raise JudgeProtocolError(f"{method} support scores do not align")
        support[method] = mapped
    return groundtruth, predictions, support, folds, videos


def score_summary(rows: list[dict[str, Any]], samples: int) -> dict[str, Any]:
    scores = [float(row["score"]) for row in rows]
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    rng = random.Random(2026073001)
    strict_samples: list[float] = []
    relaxed_samples: list[float] = []
    videos = sorted(by_video)
    for _ in range(samples):
        sample: list[dict[str, Any]] = []
        for video in rng.choices(videos, k=len(videos)):
            sample.extend(by_video[video])
        strict_samples.append(
            sum(float(row["score"]) == 1.0 for row in sample) / len(sample)
        )
        relaxed_samples.append(
            sum(float(row["score"]) for row in sample) / len(sample)
        )
    return {
        "n": len(rows),
        "strict": sum(score == 1.0 for score in scores) / len(scores),
        "relaxed": sum(scores) / len(scores),
        "score_counts": dict(Counter(str(score) for score in scores)),
        "video_cluster_bootstrap_ci95": {
            "samples": samples,
            "cluster_count": len(videos),
            "strict": [
                percentile(strict_samples, 0.025),
                percentile(strict_samples, 0.975),
            ],
            "relaxed": [
                percentile(relaxed_samples, 0.025),
                percentile(relaxed_samples, 0.975),
            ],
        },
    }


def paired_bootstrap(
    rows: list[dict[str, Any]],
    candidate_key: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    videos = sorted(by_video)
    rng = random.Random(seed)
    strict: list[float] = []
    relaxed: list[float] = []
    for _ in range(samples):
        sample: list[dict[str, Any]] = []
        for video in rng.choices(videos, k=len(videos)):
            sample.extend(by_video[video])
        strict.append(
            sum(
                int(float(row[candidate_key]) == 1.0)
                - int(float(row["MMR8_score"]) == 1.0)
                for row in sample
            )
            / len(sample)
        )
        relaxed.append(
            sum(
                float(row[candidate_key]) - float(row["MMR8_score"])
                for row in sample
            )
            / len(sample)
        )
    return {
        "samples": samples,
        "cluster_count": len(videos),
        "strict_delta_ci95": [
            percentile(strict, 0.025),
            percentile(strict, 0.975),
        ],
        "relaxed_delta_ci95": [
            percentile(relaxed, 0.025),
            percentile(relaxed, 0.975),
        ],
    }


def candidate_thresholds(rows: list[dict[str, Any]]) -> list[float]:
    values = sorted({float(row["MMR8_support"]) for row in rows})
    return (
        [values[0] - 1e-9]
        + [(left + right) / 2 for left, right in zip(values, values[1:])]
        + [values[-1] + 1e-9]
    )


def evaluate_policy(
    rows: list[dict[str, Any]],
    threshold: float,
    arm: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evaluated: list[dict[str, Any]] = []
    for row in rows:
        baseline = float(row["MMR8_score"])
        triggered = float(row["MMR8_support"]) < threshold
        margin_passed = (
            float(row[f"{arm}_support"])
            >= float(row["MMR8_support"]) + MARGIN
        )
        switched = triggered and margin_passed
        policy = float(row[f"{arm}_score"]) if switched else baseline
        evaluated.append({
            **row,
            "triggered": triggered,
            "margin_passed": margin_passed,
            "switched": switched,
            "policy_score": policy,
        })
    n = len(evaluated)
    wins = sum(row["policy_score"] > row["MMR8_score"] for row in evaluated)
    losses = sum(row["policy_score"] < row["MMR8_score"] for row in evaluated)
    metrics = {
        "threshold": threshold,
        "margin": MARGIN,
        "rows": n,
        "triggered": sum(bool(row["triggered"]) for row in evaluated),
        "trigger_rate": sum(bool(row["triggered"]) for row in evaluated) / n,
        "switched": sum(bool(row["switched"]) for row in evaluated),
        "switch_rate": sum(bool(row["switched"]) for row in evaluated) / n,
        "strict": sum(row["policy_score"] == 1.0 for row in evaluated) / n,
        "relaxed": sum(float(row["policy_score"]) for row in evaluated) / n,
        "baseline_strict": sum(row["MMR8_score"] == 1.0 for row in evaluated) / n,
        "baseline_relaxed": sum(float(row["MMR8_score"]) for row in evaluated) / n,
        "wins": wins,
        "ties": n - wins - losses,
        "losses": losses,
        "wrong_to_right": sum(
            row["MMR8_score"] == 0.0 and row["policy_score"] == 1.0
            for row in evaluated
        ),
        "right_to_wrong": sum(
            row["MMR8_score"] == 1.0 and row["policy_score"] < 1.0
            for row in evaluated
        ),
        "correction_precision": wins / (wins + losses) if wins + losses else None,
        "average_selected_visual_tokens": (
            (n - sum(bool(row["switched"]) for row in evaluated)) * A0_VISUAL_TOKENS
            + sum(bool(row["switched"]) for row in evaluated) * A2_VISUAL_TOKENS
        )
        / n,
        "average_executed_visual_tokens": (
            n * A0_VISUAL_TOKENS
            + sum(bool(row["triggered"]) for row in evaluated) * A2_VISUAL_TOKENS
        )
        / n,
    }
    return metrics, evaluated


def build_curve(
    rows: list[dict[str, Any]],
    arm: str,
) -> tuple[list[dict[str, Any]], dict[float, list[dict[str, Any]]]]:
    curve = []
    evaluated: dict[float, list[dict[str, Any]]] = {}
    for threshold in candidate_thresholds(rows):
        metrics, policy_rows = evaluate_policy(rows, threshold, arm)
        curve.append(metrics)
        evaluated[threshold] = policy_rows
    return curve, evaluated


def choose_accuracy(curve: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        curve,
        key=lambda row: (
            float(row["relaxed"]),
            float(row["strict"]),
            -int(row["right_to_wrong"]),
            -int(row["switched"]),
            -int(row["triggered"]),
        ),
    )


def choose_cost_aware(curve: list[dict[str, Any]]) -> dict[str, Any]:
    best = float(choose_accuracy(curve)["relaxed"])
    eligible = [row for row in curve if float(row["relaxed"]) >= best - 0.005]
    return min(
        eligible,
        key=lambda row: (
            int(row["triggered"]),
            -float(row["relaxed"]),
            -float(row["strict"]),
            int(row["right_to_wrong"]),
        ),
    )


def choose_knee(curve: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = min(curve, key=lambda row: int(row["triggered"]))
    maximum = max(float(row["relaxed"]) for row in curve)
    span = maximum - float(baseline["relaxed"])
    if span <= 0:
        return baseline
    enriched = []
    for row in curve:
        item = dict(row)
        gain = (float(item["relaxed"]) - float(baseline["relaxed"])) / span
        item["normalized_relaxed_gain"] = gain
        item["knee_score"] = gain - float(item["trigger_rate"])
        enriched.append(item)
    return max(
        enriched,
        key=lambda row: (
            float(row["knee_score"]),
            float(row["relaxed"]),
            float(row["strict"]),
            -int(row["right_to_wrong"]),
            -int(row["triggered"]),
        ),
    )


def nested_operating_point(
    rows: list[dict[str, Any]],
    chooser: Any,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    combined: list[dict[str, Any]] = []
    fold_reports = []
    for fold in range(5):
        train = [row for row in rows if int(row["fold"]) != fold]
        heldout = [row for row in rows if int(row["fold"]) == fold]
        train_curve, _ = build_curve(train, "Adaptive12")
        chosen = chooser(train_curve)
        adaptive_metrics, adaptive_rows = evaluate_policy(
            heldout, float(chosen["threshold"]), "Adaptive12"
        )
        extra_metrics, _ = evaluate_policy(
            heldout, float(chosen["threshold"]), "ExtraGlobal12"
        )
        fold_reports.append({
            "heldout_fold": fold,
            "learned_threshold": float(chosen["threshold"]),
            "train_adaptive_metrics": chosen,
            "heldout_adaptive_metrics": adaptive_metrics,
            "heldout_extra_global_metrics": extra_metrics,
        })
        combined.extend(adaptive_rows)
    n = len(combined)
    metrics = {
        "rows": n,
        "strict": sum(row["policy_score"] == 1.0 for row in combined) / n,
        "relaxed": sum(float(row["policy_score"]) for row in combined) / n,
        "baseline_strict": sum(row["MMR8_score"] == 1.0 for row in combined) / n,
        "baseline_relaxed": sum(float(row["MMR8_score"]) for row in combined) / n,
        "triggered": sum(bool(row["triggered"]) for row in combined),
        "switched": sum(bool(row["switched"]) for row in combined),
        "wins": sum(row["policy_score"] > row["MMR8_score"] for row in combined),
        "losses": sum(row["policy_score"] < row["MMR8_score"] for row in combined),
        "wrong_to_right": sum(
            row["MMR8_score"] == 0.0 and row["policy_score"] == 1.0
            for row in combined
        ),
        "right_to_wrong": sum(
            row["MMR8_score"] == 1.0 and row["policy_score"] < 1.0
            for row in combined
        ),
    }
    for row in combined:
        row["nested_policy_score"] = row["policy_score"]
    metrics["bootstrap_vs_mmr8"] = paired_bootstrap(
        combined, "nested_policy_score", samples, seed
    )
    return {"fold_reports": fold_reports, "metrics": metrics}


def calibrate(
    rows: list[dict[str, Any]],
    samples: int,
) -> dict[str, Any]:
    curve, evaluated = build_curve(rows, "Adaptive12")
    result: dict[str, Any] = {
        "schema_version": "adsqa_sft_lora_adaptive12_groupcv500_threshold_v1",
        "threshold_source": "AdsQA video-disjoint GroupCV-500 only",
        "support_verifier": "frozen Qwen3 RealClaim adapter",
        "fixed_a2_minus_a0_support_margin": MARGIN,
        "operating_points": {},
        "nested_oof": {},
    }
    choosers = {
        "accuracy_optimum": choose_accuracy,
        "cost_aware_within_0.5pp": choose_cost_aware,
        "knee": choose_knee,
    }
    for index, (name, chooser) in enumerate(choosers.items()):
        chosen = chooser(curve)
        threshold = float(chosen["threshold"])
        adaptive_metrics, adaptive_rows = evaluate_policy(
            rows, threshold, "Adaptive12"
        )
        extra_metrics, extra_rows = evaluate_policy(
            rows, threshold, "ExtraGlobal12"
        )
        for row in adaptive_rows:
            row["final_policy_score"] = row["policy_score"]
        for row in extra_rows:
            row["final_policy_score"] = row["policy_score"]
        adaptive_metrics["bootstrap_vs_mmr8"] = paired_bootstrap(
            adaptive_rows, "final_policy_score", samples, 2026073010 + index
        )
        extra_metrics["bootstrap_vs_mmr8"] = paired_bootstrap(
            extra_rows, "final_policy_score", samples, 2026073020 + index
        )
        result["operating_points"][name] = {
            "threshold": threshold,
            "adaptive": adaptive_metrics,
            "extra_global_same_gate_control": extra_metrics,
        }
        result["nested_oof"][name] = nested_operating_point(
            rows, chooser, samples, 2026073030 + index
        )
    write_rows = []
    for row in rows:
        write_rows.append({
            "question_id": row["question_id"],
            "video_id": row["video_id"],
            "fold": row["fold"],
            "MMR8_support": row["MMR8_support"],
            "Adaptive12_support": row["Adaptive12_support"],
            "ExtraGlobal12_support": row["ExtraGlobal12_support"],
        })
    result["support_rows_sha256"] = sha256_text(
        "".join(json.dumps(row, sort_keys=True) for row in write_rows)
    )
    result["test_or_confirm_labels_read"] = False
    return result


def main() -> None:
    args = parse_args()
    if args.workers <= 0 or args.bootstrap_samples != 10000:
        raise JudgeProtocolError("requires positive workers and 10000 bootstrap samples")
    groundtruth, predictions, support, folds, videos = load_inputs(args)
    gt = {str(row["question_id"]): row for row in groundtruth}
    protocol = legacy_protocol(args.legacy_evaluator)

    owners: dict[tuple[str, str], list[str]] = defaultdict(list)
    extraction_counts = Counter()
    for method, method_rows in predictions.items():
        for qid, row in method_rows.items():
            owners[(qid, str(row["prediction"]))].append(method)
            extraction_counts[f"{method}:{bool(row['answer_extraction_found'])}"] += 1
    call_keys = sorted(owners, key=lambda item: (item[0], item[1]))
    historical = load_historical_caches(args.historical_cache)
    reusable_keys = [key for key in call_keys if key in historical]
    pending_keys = [key for key in call_keys if key not in historical]
    dry_run = {
        "schema_version": "adsqa_sft_lora_adaptive12_groupcv500_judge_dry_run_v1",
        "passed": True,
        "question_count": 500,
        "video_count": 100,
        "method_count": len(METHODS),
        "expanded_record_count": 500 * len(METHODS),
        "unique_judge_request_count": len(call_keys),
        "required_new_api_call_count": len(pending_keys),
        "within_run_exact_duplicate_record_count": (
            500 * len(METHODS) - len(call_keys)
        ),
        "historical_exact_reuse_count": len(reusable_keys),
        "candidate_mode": "answer_only",
        "answer_extraction_counts": dict(extraction_counts),
        "legacy_evaluator_sha256": protocol["legacy_evaluator_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "inference_sha256s_sha256": sha256_file(
            args.run_root / "INFERENCE_SHA256SUMS"
        ),
        "historical_cache_sha256": [
            sha256_file(path) for path in args.historical_cache
        ],
        "api_called": False,
        "automatic_retry_allowed": False,
        "contains_api_key": False,
        "not_human_gold": True,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    dry_path = args.output_root / "dry_run_audit.json"
    if args.dry_run:
        write_json(dry_path, dry_run)
        print(json.dumps(dry_run, ensure_ascii=False, indent=2))
        return
    if not dry_path.is_file():
        raise JudgeProtocolError("frozen dry-run audit is missing")
    frozen = json.loads(dry_path.read_text(encoding="utf-8"))
    for key in (
        "required_new_api_call_count",
        "historical_exact_reuse_count",
        "unique_judge_request_count",
        "expanded_record_count",
        "within_run_exact_duplicate_record_count",
        "legacy_evaluator_sha256",
        "prompt_sha256",
        "groundtruth_sha256",
        "inference_sha256s_sha256",
        "historical_cache_sha256",
    ):
        if frozen.get(key) != dry_run.get(key):
            raise JudgeProtocolError(f"dry-run changed after authorization: {key}")
    if (args.output_root / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite completed judge output")

    partial_path = args.output_root / "api_results_partial.jsonl"
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists():
        for row in load_jsonl(partial_path):
            partial[(str(row["question_id"]), str(row["candidate_prediction"]))] = row
    if not set(partial).issubset(set(call_keys)):
        raise JudgeProtocolError("partial file contains an unauthorized candidate")
    cached_to_append: list[dict[str, Any]] = []
    for key in reusable_keys:
        if key not in partial:
            row = {
                **historical[key],
                "score_source": "historical_exact_candidate",
            }
            partial[key] = row
            cached_to_append.append(row)
    if cached_to_append:
        with partial_path.open("a", encoding="utf-8") as handle:
            for row in cached_to_append:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    pending = [key for key in call_keys if key not in partial]
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if pending and not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, candidate = key
        reference = gt[qid]
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
            "candidate_prediction_sha256": sha256_text(candidate),
            "owners": owners[key],
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": (
                usage.model_dump() if hasattr(usage, "model_dump") else None
            ),
            "score_source": "adsqa_sft_lora_groupcv500_answer_only_api",
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
                    if completed % 25 == 0 or completed == len(pending):
                        print(
                            f"attempted={completed}/{len(pending)} "
                            f"succeeded={len(partial)} failures={len(failures)}",
                            flush=True,
                        )
    if failures:
        write_jsonl(args.output_root / "api_failures.jsonl", failures)
        raise JudgeProtocolError("one-shot API calls failed; automatic retry disabled")
    if set(partial) != set(call_keys):
        raise JudgeProtocolError("judge results do not cover frozen call set")

    expanded: list[dict[str, Any]] = []
    by_qid: dict[str, dict[str, Any]] = {}
    for qid in sorted(gt):
        row: dict[str, Any] = {
            "question_id": qid,
            "video_id": videos[qid],
            "fold": folds[qid],
        }
        for method in METHODS:
            candidate = predictions[method][qid]["prediction"]
            score = float(partial[(qid, candidate)]["score"])
            row[f"{method}_score"] = score
            expanded.append({
                "question_id": qid,
                "video_id": videos[qid],
                "fold": folds[qid],
                "method": method,
                "candidate_prediction_sha256": sha256_text(candidate),
                "score": score,
                "score_source": partial[(qid, candidate)].get(
                    "score_source",
                    "historical_exact_candidate",
                ),
            })
        row["MMR8_support"] = support["MMR8"][qid]
        row["Adaptive12_support"] = support["Adaptive12"][qid]
        row["ExtraGlobal12_support"] = support["ExtraGlobal12"][qid]
        by_qid[qid] = row
    write_jsonl(args.output_root / "expanded_results1500.jsonl", expanded)
    paired = [by_qid[qid] for qid in sorted(by_qid)]
    write_jsonl(args.output_root / "paired_results500.jsonl", paired)

    method_summary = {}
    for method in METHODS:
        rows = [
            {
                "question_id": row["question_id"],
                "video_id": row["video_id"],
                "score": row[f"{method}_score"],
            }
            for row in paired
        ]
        method_summary[method] = score_summary(rows, args.bootstrap_samples)
    raw_comparisons = {}
    for index, method in enumerate(("Adaptive12", "ExtraGlobal12")):
        raw_comparisons[f"{method}_vs_MMR8"] = paired_bootstrap(
            paired, f"{method}_score", args.bootstrap_samples, 2026073040 + index
        )
    threshold_result = calibrate(paired, args.bootstrap_samples)
    write_json(args.output_root / "threshold_result.json", threshold_result)
    summary = {
        "schema_version": "adsqa_sft_lora_adaptive12_groupcv500_judge_summary_v1",
        "judge_protocol": {
            "candidate_mode": "answer_only",
            "judge_model": protocol["model_name"],
            "prompt_sha256": protocol["prompt_sha256"],
            "new_api_calls": len(pending_keys),
            "historical_exact_reuses": len(reusable_keys),
            "expanded_records": len(expanded),
            "within_run_exact_duplicate_reuses": (
                len(expanded) - len(call_keys)
            ),
            "failures": 0,
            "automatic_retries": 0,
            "not_human_gold": True,
        },
        "methods": method_summary,
        "raw_paired_comparisons": raw_comparisons,
        "threshold_calibration": threshold_result,
    }
    write_json(args.output_root / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
