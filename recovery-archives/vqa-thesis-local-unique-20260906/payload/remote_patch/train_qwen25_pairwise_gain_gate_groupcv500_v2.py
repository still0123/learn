#!/usr/bin/env python3
"""Train a nested-OOF pairwise gain gate for Qwen2.5 Adaptive12."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sys
from typing import Any

import joblib
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


GAIN_RECALL_TARGET = 0.90
HARM_WEIGHT = 1.5
MIN_CALIBRATION_SWITCHES = 3
MIN_CORRECTION_PRECISION = 0.70
MAX_CALIBRATION_SWITCH_RATE = 0.10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
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
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def numeric_stats(values: list[float], prefix: str) -> dict[str, float]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {
            f"{prefix}_count": 0.0,
            f"{prefix}_mean": 0.0,
            f"{prefix}_max": 0.0,
            f"{prefix}_min": 0.0,
        }
    return {
        f"{prefix}_count": float(len(clean)),
        f"{prefix}_mean": float(sum(clean) / len(clean)),
        f"{prefix}_max": float(max(clean)),
        f"{prefix}_min": float(min(clean)),
    }


def tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", value.lower()))


def numbers(value: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", value.lower()))


def normalize_answer(
    raw: str,
    extract_answer_section: Any,
    truncate_words: Any,
) -> str:
    answer, _, _ = extract_answer_section(raw.strip())
    return truncate_words(answer.strip())


def build_features(
    item: dict[str, Any],
    a0_answer: str,
    a2_answer: str,
    a0_support: float,
    a2_support: float,
) -> dict[str, float]:
    a0_tokens = tokenize(a0_answer)
    a2_tokens = tokenize(a2_answer)
    union = a0_tokens | a2_tokens
    a0_numbers = numbers(a0_answer)
    a2_numbers = numbers(a2_answer)
    question = str(item.get("question", "")).lower()
    features: dict[str, float] = {
        "a0_support": a0_support,
        "a2_support": a2_support,
        "support_delta": a2_support - a0_support,
        "support_abs_delta": abs(a2_support - a0_support),
        "answer_changed": float(a0_answer.strip() != a2_answer.strip()),
        "a0_char_len": float(len(a0_answer)),
        "a2_char_len": float(len(a2_answer)),
        "answer_char_len_delta": float(len(a2_answer) - len(a0_answer)),
        "token_jaccard": (
            float(len(a0_tokens & a2_tokens) / len(union)) if union else 1.0
        ),
        "a0_number_count": float(len(a0_numbers)),
        "a2_number_count": float(len(a2_numbers)),
        "number_added_count": float(len(a2_numbers - a0_numbers)),
        "number_removed_count": float(len(a0_numbers - a2_numbers)),
        "number_changed": float(a0_numbers != a2_numbers),
        "question_what": float("what" in question),
        "question_who": float("who" in question),
        "question_where": float("where" in question),
        "question_when": float("when" in question),
        "question_why": float("why" in question),
        "question_how": float("how" in question),
        "question_brand": float(
            any(term in question for term in ("brand", "company", "product"))
        ),
        "question_text": float(
            any(
                term in question
                for term in ("text", "word", "write", "written", "slogan")
            )
        ),
        "question_numeric": float(
            any(
                term in question
                for term in ("number", "price", "percent", "how many", "year")
            )
        ),
    }
    ocr = [row for row in item.get("ocr_evidence", []) if isinstance(row, dict)]
    asr = [row for row in item.get("asr_evidence", []) if isinstance(row, dict)]
    anchors = [
        row for row in item.get("evidence_anchors", []) if isinstance(row, dict)
    ]
    features.update(
        numeric_stats(
            [float(row.get("confidence", 0.0) or 0.0) for row in ocr],
            "ocr_confidence",
        )
    )
    features.update(
        numeric_stats(
            [float(row.get("question_overlap", 0.0) or 0.0) for row in ocr],
            "ocr_overlap",
        )
    )
    features.update(
        numeric_stats(
            [float(row.get("question_overlap", 0.0) or 0.0) for row in asr],
            "asr_overlap",
        )
    )
    features.update(
        numeric_stats(
            [float(row.get("avg_logprob", 0.0) or 0.0) for row in asr],
            "asr_logprob",
        )
    )
    for field in (
        "fusion_score",
        "entropy_proxy",
        "visual_rank_score",
        "ocr_rank_score",
        "asr_rank_score",
    ):
        features.update(
            numeric_stats(
                [float(row.get(field, 0.0) or 0.0) for row in anchors],
                f"anchor_{field}",
            )
        )
    ocr_quality = item.get("ocr_quality", {})
    asr_quality = item.get("asr_quality", {})
    features.update({
        "ocr_candidate_count": float(ocr_quality.get("candidate_count", 0) or 0),
        "ocr_selected_count": float(ocr_quality.get("selected_count", 0) or 0),
        "asr_segment_count": float(asr_quality.get("segment_count", 0) or 0),
        "asr_selected_count": float(asr_quality.get("selected_count", 0) or 0),
    })
    return features


def make_classifier(seed: int) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        (
            "model",
            LogisticRegression(
                C=0.5,
                class_weight="balanced",
                max_iter=5000,
                solver="liblinear",
                random_state=seed,
            ),
        ),
    ])


def fit_binary(
    x: np.ndarray, y: np.ndarray, seed: int
) -> tuple[Pipeline | None, float]:
    classes = sorted(set(int(value) for value in y))
    if len(classes) == 1:
        return None, float(classes[0])
    model = make_classifier(seed)
    model.fit(x, y)
    return model, -1.0


def predict_binary(
    model: Pipeline | None, constant: float, x: np.ndarray
) -> np.ndarray:
    if model is None:
        return np.full(x.shape[0], constant, dtype=float)
    classes = list(model.named_steps["model"].classes_)
    if 1 not in classes:
        return np.zeros(x.shape[0], dtype=float)
    return model.predict_proba(x)[:, classes.index(1)]


def learn_trigger_threshold(rows: list[dict[str, Any]]) -> float:
    gain_support = sorted(
        float(row["a0_support"]) for row in rows if float(row["gain"]) > 0.0
    )
    if not gain_support:
        return -1.0
    return percentile(gain_support, GAIN_RECALL_TARGET) + 1e-12


def threshold_report(
    rows: list[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if bool(row["triggered"]) and float(row["utility"]) >= threshold
    ]
    wins = sum(float(row["gain"]) > 0.0 for row in selected)
    losses = sum(float(row["gain"]) < 0.0 for row in selected)
    return {
        "threshold": threshold,
        "switches": len(selected),
        "wins": wins,
        "losses": losses,
        "ties": len(selected) - wins - losses,
        "correction_precision": (
            wins / (wins + losses) if wins + losses else None
        ),
        "total_score_gain": sum(float(row["gain"]) for row in selected),
    }


def calibrate_switch_threshold(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = sorted(
        {float(row["utility"]) for row in rows if bool(row["triggered"])},
        reverse=True,
    )
    candidates = [max(eligible, default=0.0) + 1e-9]
    candidates.extend(eligible)
    valid: list[dict[str, Any]] = []
    for threshold in candidates:
        report = threshold_report(rows, threshold)
        precision = report["correction_precision"]
        if (
            report["switches"] >= MIN_CALIBRATION_SWITCHES
            and report["switches"]
            <= math.ceil(MAX_CALIBRATION_SWITCH_RATE * len(rows))
            and report["wins"] > report["losses"]
            and precision is not None
            and precision >= MIN_CORRECTION_PRECISION
            and report["total_score_gain"] > 0.0
        ):
            valid.append(report)
    if not valid:
        return threshold_report(rows, max(eligible, default=0.0) + 1e-9)
    return max(
        valid,
        key=lambda row: (
            float(row["total_score_gain"]),
            int(row["wins"]) - int(row["losses"]),
            -int(row["losses"]),
            float(row["correction_precision"]),
            -int(row["switches"]),
        ),
    )


def evaluate_policy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    switches = [row for row in rows if bool(row["switched"])]
    wins = sum(float(row["policy_score"]) > float(row["a0_score"]) for row in rows)
    losses = sum(
        float(row["policy_score"]) < float(row["a0_score"]) for row in rows
    )
    return {
        "rows": len(rows),
        "triggered": sum(bool(row["triggered"]) for row in rows),
        "trigger_rate": sum(bool(row["triggered"]) for row in rows) / len(rows),
        "switched": len(switches),
        "switch_rate": len(switches) / len(rows),
        "strict": sum(float(row["policy_score"]) == 1.0 for row in rows)
        / len(rows),
        "relaxed": sum(float(row["policy_score"]) for row in rows) / len(rows),
        "baseline_strict": sum(float(row["a0_score"]) == 1.0 for row in rows)
        / len(rows),
        "baseline_relaxed": sum(float(row["a0_score"]) for row in rows)
        / len(rows),
        "wins": wins,
        "ties": len(rows) - wins - losses,
        "losses": losses,
        "wrong_to_right": sum(
            float(row["a0_score"]) == 0.0
            and float(row["policy_score"]) == 1.0
            for row in rows
        ),
        "right_to_wrong": sum(
            float(row["a0_score"]) == 1.0
            and float(row["policy_score"]) < 1.0
            for row in rows
        ),
        "correction_precision": wins / (wins + losses) if wins + losses else None,
    }


def paired_bootstrap(
    rows: list[dict[str, Any]],
    candidate_key: str,
    baseline_key: str,
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
                - int(float(row[baseline_key]) == 1.0)
                for row in sample
            )
            / len(sample)
        )
        relaxed.append(
            sum(
                float(row[candidate_key]) - float(row[baseline_key])
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


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(args.project_root / "evaluation/tools"))
    from judge_adsqa_answer_lora_oof_v1 import (  # noqa: PLC0415
        extract_answer_section,
        truncate_words,
    )

    source_paths = {
        "items": args.run_root
        / "calibration_candidates500/items_answer_free.jsonl",
        "paired": args.run_root
        / "judge_deepseek_answeronly_v1/paired_results500.jsonl",
        "threshold": args.run_root
        / "judge_deepseek_answeronly_v1/threshold_result.json",
    }
    items = {
        str(row["question_id"]): row for row in load_jsonl(source_paths["items"])
    }
    paired = {
        str(row["question_id"]): row for row in load_jsonl(source_paths["paired"])
    }
    if len(items) != 500 or set(items) != set(paired):
        raise RuntimeError("GroupCV-500 inputs do not align")

    rows: list[dict[str, Any]] = []
    feature_names: list[str] | None = None
    for qid in sorted(items):
        row = paired[qid]
        fold = int(row["fold"])
        a0_path = args.run_root / f"a0_mmr8/fold_{fold}/{qid}/prediction.json"
        a2_path = args.run_root / f"adaptive12/fold_{fold}/{qid}/a2_prediction.json"
        a0_raw = json.loads(a0_path.read_text(encoding="utf-8"))["prediction"]
        a2_raw = json.loads(a2_path.read_text(encoding="utf-8"))["prediction"]
        a0_answer = normalize_answer(
            str(a0_raw), extract_answer_section, truncate_words
        )
        a2_answer = normalize_answer(
            str(a2_raw), extract_answer_section, truncate_words
        )
        features = build_features(
            items[qid],
            a0_answer,
            a2_answer,
            float(row["MMR8_support"]),
            float(row["Adaptive12_support"]),
        )
        if feature_names is None:
            feature_names = sorted(features)
        if sorted(features) != feature_names:
            raise RuntimeError("feature schema changed across rows")
        rows.append({
            "question_id": qid,
            "video_id": str(row["video_id"]),
            "fold": fold,
            "features": features,
            "a0_support": float(row["MMR8_support"]),
            "a2_support": float(row["Adaptive12_support"]),
            "a0_score": float(row["MMR8_score"]),
            "a2_score": float(row["Adaptive12_score"]),
            "gain": float(row["Adaptive12_score"]) - float(row["MMR8_score"]),
        })
    assert feature_names is not None

    fold_videos = {
        fold: {
            str(row["video_id"]) for row in rows if int(row["fold"]) == fold
        }
        for fold in range(5)
    }
    leakage = {
        str(fold): sorted(
            fold_videos[fold]
            & set().union(
                *(fold_videos[other] for other in range(5) if other != fold)
            )
        )
        for fold in range(5)
    }
    if any(leakage.values()):
        raise RuntimeError("video leakage across folds")

    x_all = np.asarray(
        [[float(row["features"][name]) for name in feature_names] for row in rows],
        dtype=float,
    )
    y_gain = np.asarray([float(row["gain"]) > 0.0 for row in rows], dtype=int)
    y_harm = np.asarray([float(row["gain"]) < 0.0 for row in rows], dtype=int)

    output_rows: list[dict[str, Any]] = []
    fold_reports: list[dict[str, Any]] = []
    for outer_fold in range(5):
        outer_train = [
            index for index, row in enumerate(rows) if int(row["fold"]) != outer_fold
        ]
        outer_test = [
            index for index, row in enumerate(rows) if int(row["fold"]) == outer_fold
        ]
        inner_predictions: list[dict[str, Any]] = []
        for inner_fold in sorted(
            {int(rows[index]["fold"]) for index in outer_train}
        ):
            inner_train = [
                index
                for index in outer_train
                if int(rows[index]["fold"]) != inner_fold
            ]
            inner_test = [
                index
                for index in outer_train
                if int(rows[index]["fold"]) == inner_fold
            ]
            gain_model, gain_constant = fit_binary(
                x_all[inner_train],
                y_gain[inner_train],
                2026073000 + outer_fold * 10 + inner_fold,
            )
            harm_model, harm_constant = fit_binary(
                x_all[inner_train],
                y_harm[inner_train],
                2026073100 + outer_fold * 10 + inner_fold,
            )
            p_gain = predict_binary(
                gain_model, gain_constant, x_all[inner_test]
            )
            p_harm = predict_binary(
                harm_model, harm_constant, x_all[inner_test]
            )
            trigger_threshold = learn_trigger_threshold(
                [rows[index] for index in inner_train]
            )
            for position, index in enumerate(inner_test):
                inner_predictions.append({
                    "gain": float(rows[index]["gain"]),
                    "triggered": float(rows[index]["a0_support"])
                    < trigger_threshold,
                    "utility": float(p_gain[position] - HARM_WEIGHT * p_harm[position]),
                })
        switch_calibration = calibrate_switch_threshold(inner_predictions)
        trigger_threshold = learn_trigger_threshold(
            [rows[index] for index in outer_train]
        )
        gain_model, gain_constant = fit_binary(
            x_all[outer_train], y_gain[outer_train], 2026073200 + outer_fold
        )
        harm_model, harm_constant = fit_binary(
            x_all[outer_train], y_harm[outer_train], 2026073300 + outer_fold
        )
        p_gain = predict_binary(gain_model, gain_constant, x_all[outer_test])
        p_harm = predict_binary(harm_model, harm_constant, x_all[outer_test])
        fold_dir = args.output_dir / f"fold_{outer_fold}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(gain_model, fold_dir / "gain_model.joblib")
        joblib.dump(harm_model, fold_dir / "harm_model.joblib")
        for position, index in enumerate(outer_test):
            source = rows[index]
            utility = float(p_gain[position] - HARM_WEIGHT * p_harm[position])
            triggered = float(source["a0_support"]) < trigger_threshold
            switched = (
                triggered and utility >= float(switch_calibration["threshold"])
            )
            output_rows.append({
                "question_id": source["question_id"],
                "video_id": source["video_id"],
                "fold": outer_fold,
                "a0_score": source["a0_score"],
                "a2_score": source["a2_score"],
                "gain_label": source["gain"],
                "a0_support": source["a0_support"],
                "a2_support": source["a2_support"],
                "p_gain": float(p_gain[position]),
                "p_harm": float(p_harm[position]),
                "utility": utility,
                "trigger_threshold": trigger_threshold,
                "switch_threshold": float(switch_calibration["threshold"]),
                "triggered": triggered,
                "switched": switched,
                "policy_score": (
                    source["a2_score"] if switched else source["a0_score"]
                ),
            })
        heldout = [row for row in output_rows if int(row["fold"]) == outer_fold]
        fold_reports.append({
            "heldout_fold": outer_fold,
            "train_rows": len(outer_train),
            "heldout_rows": len(outer_test),
            "train_gain_count": int(y_gain[outer_train].sum()),
            "train_harm_count": int(y_harm[outer_train].sum()),
            "trigger_threshold": trigger_threshold,
            "switch_calibration": switch_calibration,
            "heldout_metrics": evaluate_policy(heldout),
        })

    output_rows.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    if len(output_rows) != 500:
        raise RuntimeError("OOF predictions do not cover 500 questions")

    threshold_result = json.loads(
        source_paths["threshold"].read_text(encoding="utf-8")
    )
    frozen_folds = {
        int(row["heldout_fold"]): float(row["learned_threshold"])
        for row in threshold_result["nested_oof"]["accuracy_optimum"]["fold_reports"]
    }
    for row in output_rows:
        frozen_triggered = float(row["a0_support"]) < frozen_folds[int(row["fold"])]
        frozen_switched = (
            frozen_triggered
            and float(row["a2_support"]) >= float(row["a0_support"]) + 0.25
        )
        row["frozen_policy_score"] = (
            float(row["a2_score"]) if frozen_switched else float(row["a0_score"])
        )
        row["frozen_triggered"] = frozen_triggered
        row["frozen_switched"] = frozen_switched

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "oof_predictions500.jsonl", output_rows)
    metrics = evaluate_policy(output_rows)
    frozen_rows = [
        {
            **row,
            "triggered": row["frozen_triggered"],
            "switched": row["frozen_switched"],
            "policy_score": row["frozen_policy_score"],
        }
        for row in output_rows
    ]
    frozen_metrics = evaluate_policy(frozen_rows)
    summary = {
        "schema_version": "qwen25_pairwise_gain_gate_groupcv500_v2",
        "model": "dual_balanced_logistic_regression",
        "gain_recall_target": GAIN_RECALL_TARGET,
        "harm_weight": HARM_WEIGHT,
        "minimum_calibration_switches": MIN_CALIBRATION_SWITCHES,
        "minimum_correction_precision": MIN_CORRECTION_PRECISION,
        "maximum_calibration_switch_rate": MAX_CALIBRATION_SWITCH_RATE,
        "question_count": len(output_rows),
        "video_count": len({row["video_id"] for row in output_rows}),
        "fold_counts": dict(Counter(str(row["fold"]) for row in output_rows)),
        "label_counts": {
            "gain": int(y_gain.sum()),
            "tie": int(len(rows) - y_gain.sum() - y_harm.sum()),
            "harm": int(y_harm.sum()),
        },
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "fold_reports": fold_reports,
        "pairwise_gain_gate": metrics,
        "frozen_tau_margin_gate": frozen_metrics,
        "bootstrap_pairwise_vs_a0": paired_bootstrap(
            output_rows,
            "policy_score",
            "a0_score",
            args.bootstrap_samples,
            2026073401,
        ),
        "bootstrap_pairwise_vs_frozen": paired_bootstrap(
            output_rows,
            "policy_score",
            "frozen_policy_score",
            args.bootstrap_samples,
            2026073402,
        ),
        "protocol_audit": {
            "outer_fold_video_leakage": leakage,
            "features_answer_free": True,
            "reference_answer_text_read": False,
            "judge_scores_used_as_training_labels": True,
            "not_human_gold": True,
            "test_or_confirm_labels_read": False,
            "passed": True,
        },
        "input_sha256": {
            name: sha256_file(path) for name, path in source_paths.items()
        },
    }
    summary["gate_passed"] = (
        metrics["wins"] > metrics["losses"]
        and metrics["correction_precision"] is not None
        and metrics["correction_precision"] >= MIN_CORRECTION_PRECISION
        and metrics["relaxed"] >= frozen_metrics["relaxed"]
    )
    write_json(args.output_dir / "summary.json", summary)
    write_json(
        args.output_dir / "feature_manifest.json",
        {
            "feature_names": feature_names,
            "feature_count": len(feature_names),
            "reference_answer_text_read": False,
            "judge_scores_used_as_training_labels": True,
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
