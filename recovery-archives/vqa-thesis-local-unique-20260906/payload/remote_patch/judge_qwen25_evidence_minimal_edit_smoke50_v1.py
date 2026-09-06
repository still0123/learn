#!/usr/bin/env python3
"""Judge Qwen2.5 evidence-minimal-edit Smoke-50 with frozen answer-only protocol."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import threading
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def score_summary(
    rows: list[dict[str, Any]], key: str, samples: int
) -> dict[str, Any]:
    scores = [float(row[key]) for row in rows]
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    videos = sorted(by_video)
    rng = random.Random(2026073002)
    strict_samples: list[float] = []
    relaxed_samples: list[float] = []
    for _ in range(samples):
        sampled: list[dict[str, Any]] = []
        for video in rng.choices(videos, k=len(videos)):
            sampled.extend(by_video[video])
        strict_samples.append(
            sum(float(row[key]) == 1.0 for row in sampled) / len(sampled)
        )
        relaxed_samples.append(
            sum(float(row[key]) for row in sampled) / len(sampled)
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


def paired_summary(
    rows: list[dict[str, Any]],
    baseline_key: str,
    candidate_key: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    wins = sum(float(row[candidate_key]) > float(row[baseline_key]) for row in rows)
    losses = sum(
        float(row[candidate_key]) < float(row[baseline_key]) for row in rows
    )
    by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    videos = sorted(by_video)
    rng = random.Random(seed)
    strict_samples: list[float] = []
    relaxed_samples: list[float] = []
    for _ in range(samples):
        sampled: list[dict[str, Any]] = []
        for video in rng.choices(videos, k=len(videos)):
            sampled.extend(by_video[video])
        strict_samples.append(
            sum(
                int(float(row[candidate_key]) == 1.0)
                - int(float(row[baseline_key]) == 1.0)
                for row in sampled
            )
            / len(sampled)
        )
        relaxed_samples.append(
            sum(
                float(row[candidate_key]) - float(row[baseline_key])
                for row in sampled
            )
            / len(sampled)
        )
    return {
        "n": len(rows),
        "wins": wins,
        "ties": len(rows) - wins - losses,
        "losses": losses,
        "wrong_to_right": sum(
            float(row[baseline_key]) == 0.0
            and float(row[candidate_key]) == 1.0
            for row in rows
        ),
        "right_to_wrong": sum(
            float(row[baseline_key]) == 1.0
            and float(row[candidate_key]) < 1.0
            for row in rows
        ),
        "correction_precision": wins / (wins + losses) if wins + losses else None,
        "strict_delta": (
            sum(float(row[candidate_key]) == 1.0 for row in rows)
            - sum(float(row[baseline_key]) == 1.0 for row in rows)
        )
        / len(rows),
        "relaxed_delta": sum(
            float(row[candidate_key]) - float(row[baseline_key]) for row in rows
        )
        / len(rows),
        "video_cluster_bootstrap_ci95": {
            "samples": samples,
            "cluster_count": len(videos),
            "strict_delta": [
                percentile(strict_samples, 0.025),
                percentile(strict_samples, 0.975),
            ],
            "relaxed_delta": [
                percentile(relaxed_samples, 0.025),
                percentile(relaxed_samples, 0.975),
            ],
        },
    }


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(args.project_root / "evaluation/tools"))
    from judge_adsqa_answer_lora_oof_v1 import (  # noqa: PLC0415
        JudgeProtocolError,
        VALID_SCORES,
        extract_answer_section,
        legacy_parse_score,
        legacy_protocol,
        truncate_words,
    )

    preflight = json.loads(
        (args.smoke_root / "judge_preflight_v1/dry_run_audit.json").read_text(
            encoding="utf-8"
        )
    )
    if preflight.get("passed") is not True:
        raise JudgeProtocolError("judge preflight failed")
    if int(preflight.get("new_api_calls", -1)) != 16:
        raise JudgeProtocolError("authorized call count changed")
    if preflight.get("api_called") is not False:
        raise JudgeProtocolError("preflight unexpectedly called API")
    if (args.output_dir / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite completed judge output")

    dataset_rows = load_jsonl(args.smoke_root / "dataset/items_answer_free.jsonl")
    dataset = {str(row["question_id"]): row for row in dataset_rows}
    if len(dataset_rows) != 50 or len(dataset) != 50:
        raise JudgeProtocolError("Smoke dataset must contain 50 unique questions")

    all_gt = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    gt = {
        str(row["question_id"]): row
        for row in all_gt
        if str(row["question_id"]) in dataset
    }
    if set(gt) != set(dataset):
        raise JudgeProtocolError("private references do not cover Smoke-50")

    old_judge_root = args.baseline_root / "judge_deepseek_answeronly_v1"
    old_summary = json.loads(
        (old_judge_root / "summary.json").read_text(encoding="utf-8")
    )
    protocol = legacy_protocol(args.legacy_evaluator)
    old_protocol = old_summary["judge_protocol"]
    if protocol["prompt_sha256"] != preflight["prompt_sha256"]:
        raise JudgeProtocolError("judge prompt changed after preflight")
    if protocol["prompt_sha256"] != old_protocol["prompt_sha256"]:
        raise JudgeProtocolError("judge prompt does not match baseline")
    if protocol["model_name"] != old_protocol["judge_model"]:
        raise JudgeProtocolError("judge model does not match baseline")

    old_expanded = load_jsonl(old_judge_root / "expanded_results2000.jsonl")
    old_scores = {
        (str(row["question_id"]), str(row["method"])): float(row["score"])
        for row in old_expanded
    }
    old_api_rows = load_jsonl(old_judge_root / "api_results_partial.jsonl")
    historical = {
        (str(row["question_id"]), str(row["candidate_prediction"])): row
        for row in old_api_rows
    }

    candidates: dict[str, dict[str, Any]] = {}
    for path in sorted(
        (args.smoke_root / "inference").glob("fold_*/*/a2_prediction.json")
    ):
        item = json.loads(path.read_text(encoding="utf-8"))
        qid = str(item["question_id"])
        answer, found, marker = extract_answer_section(
            str(item["prediction"]).strip()
        )
        answer = truncate_words(answer.strip())
        trace = json.loads(
            (path.parent / "a2_trace.json").read_text(encoding="utf-8")
        )
        candidates[qid] = {
            "prediction": answer,
            "prediction_sha256": sha256_text(answer),
            "answer_extraction_found": found,
            "answer_extraction_marker": marker,
            "changed_from_a0": bool(trace.get("answer_changed_from_a0")),
            "fold": int(dataset[qid]["fold"]),
            "video_id": str(dataset[qid]["video_id"]),
        }
    if set(candidates) != set(dataset):
        raise JudgeProtocolError("new candidates do not cover Smoke-50")

    call_keys = sorted(
        (qid, item["prediction"]) for qid, item in candidates.items()
    )
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    for key in call_keys:
        if key in historical:
            row = dict(historical[key])
            row["score_source"] = "historical_exact_answer_reuse"
            partial[key] = row
    pending = [key for key in call_keys if key not in partial]
    if len(partial) != 34 or len(pending) != 16:
        raise JudgeProtocolError("frozen reuse/call counts changed")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    partial_path = args.output_dir / "api_results_partial.jsonl"
    if partial_path.exists():
        for row in load_jsonl(partial_path):
            key = (str(row["question_id"]), str(row["candidate_prediction"]))
            if key not in set(call_keys):
                raise JudgeProtocolError("partial result outside frozen call set")
            partial[key] = row
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
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": (
                usage.model_dump() if hasattr(usage, "model_dump") else None
            ),
            "score_source": "minimal_edit_smoke50_answer_only_api",
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
                for future in concurrent.futures.as_completed(futures):
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
        if failures:
            write_jsonl(args.output_dir / "api_failures.jsonl", failures)
            raise JudgeProtocolError("API calls failed; automatic retry disabled")
    if set(partial) != set(call_keys):
        raise JudgeProtocolError("judge results do not cover frozen candidates")

    paired: list[dict[str, Any]] = []
    for qid in sorted(dataset):
        candidate = candidates[qid]
        paired.append({
            "question_id": qid,
            "video_id": candidate["video_id"],
            "fold": candidate["fold"],
            "answer_changed_from_a0": candidate["changed_from_a0"],
            "MMR8_score": old_scores[(qid, "MMR8")],
            "Adaptive12_score": old_scores[(qid, "Adaptive12")],
            "MinimalEdit12_score": float(
                partial[(qid, candidate["prediction"])]["score"]
            ),
            "MinimalEdit12_prediction_sha256": candidate["prediction_sha256"],
            "score_source": partial[
                (qid, candidate["prediction"])
            ]["score_source"],
        })
    write_jsonl(args.output_dir / "paired_results50.jsonl", paired)
    changed_rows = [row for row in paired if row["answer_changed_from_a0"]]
    total_usage: Counter[str] = Counter()
    for row in partial.values():
        if row.get("score_source") != "minimal_edit_smoke50_answer_only_api":
            continue
        for key, value in (row.get("judge_usage") or {}).items():
            if isinstance(value, int):
                total_usage[key] += value
    summary = {
        "schema_version": "qwen25_evidence_minimal_edit_smoke50_judge_v1",
        "selection": (
            "per-fold 10 lowest A0-support questions with unique videos; "
            "hard-case directional smoke, not a population estimate"
        ),
        "judge_protocol": {
            "candidate_mode": "answer_only",
            "judge_model": protocol["model_name"],
            "prompt_sha256": protocol["prompt_sha256"],
            "historical_exact_reuses": 34,
            "new_api_calls": 16,
            "failures": 0,
            "automatic_retries": 0,
            "not_human_gold": True,
            "usage": dict(total_usage),
        },
        "methods": {
            "MMR8": score_summary(
                paired, "MMR8_score", args.bootstrap_samples
            ),
            "Adaptive12": score_summary(
                paired, "Adaptive12_score", args.bootstrap_samples
            ),
            "MinimalEdit12": score_summary(
                paired, "MinimalEdit12_score", args.bootstrap_samples
            ),
        },
        "paired_vs_MMR8": paired_summary(
            paired,
            "MMR8_score",
            "MinimalEdit12_score",
            args.bootstrap_samples,
            2026073003,
        ),
        "paired_vs_Adaptive12": paired_summary(
            paired,
            "Adaptive12_score",
            "MinimalEdit12_score",
            args.bootstrap_samples,
            2026073004,
        ),
        "changed_only_vs_MMR8": paired_summary(
            changed_rows,
            "MMR8_score",
            "MinimalEdit12_score",
            args.bootstrap_samples,
            2026073005,
        ),
        "adopted_revision_count": len(changed_rows),
        "trigger_rate": len(changed_rows) / len(paired),
        "passed_smoke_gate": (
            sum(
                row["MinimalEdit12_score"] > row["MMR8_score"] for row in paired
            )
            > sum(
                row["MinimalEdit12_score"] < row["MMR8_score"] for row in paired
            )
            and sum(row["MinimalEdit12_score"] for row in paired)
            >= sum(row["MMR8_score"] for row in paired)
        ),
    }
    write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
