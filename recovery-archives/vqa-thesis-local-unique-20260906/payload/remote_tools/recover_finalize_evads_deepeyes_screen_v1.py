#!/usr/bin/env python3
"""Recover one authorized judge format failure and finalize DeepEyes screen."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time

from judge_evads_awares_crop_v1 import (
    BASELINE,
    JUDGE_PROMPT,
    clustered_ci,
    dump,
    parse_score,
    passes_metric_gate,
    read_jsonl,
    references,
    sha256_file,
    sha256_text,
    tier,
    write_jsonl,
)


CANDIDATE = "deepeyes_firstzoom10"
VARIANTS = (BASELINE, CANDIDATE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--sft-parquet", type=Path, required=True)
    parser.add_argument("--preflight-dir", type=Path, required=True)
    parser.add_argument("--prior-results-dir", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    return parser.parse_args()


def method_summary(
    rows: list[dict],
    variant: str,
) -> dict:
    values = [float(row[variant]) for row in rows]
    return {
        "rows": len(values),
        "R5": sum(values) / len(values),
        "R3": sum(tier(value, "R3") for value in values) / len(values),
        "R2": sum(tier(value, "R2") for value in values) / len(values),
        "counts": dict(Counter(str(value) for value in values)),
    }


def comparison_summary(
    rows: list[dict],
    draws: int,
) -> dict:
    raw = [
        float(row[CANDIDATE]) - float(row[BASELINE]) for row in rows
    ]
    comparison = {
        "selected": CANDIDATE,
        "baseline": BASELINE,
        "wins": sum(value > 0 for value in raw),
        "ties": sum(value == 0 for value in raw),
        "losses": sum(value < 0 for value in raw),
        "tiers": {},
    }
    for name in ("R5", "R3", "R2"):
        delta = [
            tier(float(row[CANDIDATE]), name)
            - tier(float(row[BASELINE]), name)
            for row in rows
        ]
        comparison["tiers"][name] = {
            "delta": sum(delta) / len(delta),
            "video_cluster_bootstrap_ci95": clustered_ci(
                rows,
                CANDIDATE,
                BASELINE,
                name,
                draws,
            ),
            "bootstrap_draws": draws,
        }
    comparison["wrong_to_right"] = sum(
        tier(float(row[BASELINE]), "R2") == 0.0
        and tier(float(row[CANDIDATE]), "R2") == 1.0
        for row in rows
    )
    comparison["right_to_wrong"] = sum(
        tier(float(row[BASELINE]), "R2") == 1.0
        and tier(float(row[CANDIDATE]), "R2") == 0.0
        for row in rows
    )
    return comparison


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError("recovered output directory already exists")

    authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
    failure_path = args.prior_results_dir / "api_failures.jsonl"
    prior_path = args.prior_results_dir / "api_results.jsonl"
    preflight_path = args.preflight_dir / "audit.json"
    pending_path = args.preflight_dir / "pending_candidates_answer_free.jsonl"
    slots_path = args.preflight_dir / "candidate_slots_answer_free.jsonl"
    source_hashes = {
        "failures": sha256_file(failure_path),
        "prior_results": sha256_file(prior_path),
        "preflight": sha256_file(preflight_path),
        "pending": sha256_file(pending_path),
        "slots": sha256_file(slots_path),
    }
    if (
        int(authorization.get("authorized_unique_calls", -1)) != 1
        or authorization.get("automatic_retries") != 0
        or authorization.get("format_only_recovery") is not True
        or authorization.get("source_hashes") != source_hashes
        or authorization.get("recovery_script_sha256")
        != sha256_file(Path(__file__))
    ):
        raise RuntimeError("recovery authorization or source hashes changed")

    failures = read_jsonl(failure_path)
    prior = read_jsonl(prior_path)
    pending = {
        (str(row["question_id"]), str(row["prediction_sha256"])): row
        for row in read_jsonl(pending_path)
    }
    candidates = [
        pending[(str(row["question_id"]), str(row["prediction_sha256"]))]
        for row in failures
    ]
    authorized_candidate = (
        {
            "question_id": str(candidates[0]["question_id"]),
            "prediction_sha256": str(candidates[0]["prediction_sha256"]),
        }
        if len(candidates) == 1
        else None
    )
    if (
        len(candidates) != 1
        or len(prior) != 126
        or len(pending) != 127
        or authorization.get("authorized_candidate")
        != authorized_candidate
    ):
        raise RuntimeError("partial result counts or candidate changed")

    all_questions = {
        str(row["question_id"]): row
        for row in json.loads(args.questions.read_text(encoding="utf-8"))
    }
    candidate_ids = {str(row["question_id"]) for row in candidates}
    if len(all_questions) != 100 or not candidate_ids.issubset(all_questions):
        raise RuntimeError("frozen question source changed")
    refs = references(args.sft_parquet, candidate_ids)
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=150.0,
        max_retries=0,
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    dump(args.output_dir / "manifest.json", {
        "schema_version": "evads_deepeyes_screen_recovery_manifest_v1",
        "authorized_calls": 1,
        "automatic_retries": 0,
        "explicit_recovery_round": 1,
        "prompt_change": "format_only_single_line_reinforcement",
        "api_key_saved": False,
        "private_references_persisted": False,
        "source_hashes": {
            **source_hashes,
            "script": sha256_file(Path(__file__)),
            "authorization": sha256_file(args.authorization),
            "sft_parquet": sha256_file(args.sft_parquet),
        },
    })
    started = time.time()
    candidate = candidates[0]
    qid = str(candidate["question_id"])
    prediction = str(candidate["prediction"])
    if sha256_text(prediction) != candidate["prediction_sha256"]:
        raise RuntimeError("authorized candidate hash changed")
    ref = refs[qid]
    prompt = JUDGE_PROMPT.format(
        question=all_questions[qid]["question"],
        metadata=ref["metadata"],
        clues=ref["clues"],
        reference=ref["reference_answer"],
        prediction=prediction,
    )
    prompt += (
        "\nFormatting is mandatory: output exactly one line in the form "
        "Answer: X, where X is one allowed numeric score. Output nothing else."
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=16,
    )
    usage = getattr(response, "usage", None)
    recovered = {
        "question_id": qid,
        "prediction_sha256": candidate["prediction_sha256"],
        "score_R5": parse_score(str(response.choices[0].message.content)),
        "judge_model": getattr(response, "model", None),
        "usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
        "not_human_gold": True,
    }
    write_jsonl(
        args.output_dir / "api_results_recovery.jsonl",
        [recovered],
    )

    completed = sorted(
        prior + [recovered],
        key=lambda row: (row["question_id"], row["prediction_sha256"]),
    )
    keys = {
        (str(row["question_id"]), str(row["prediction_sha256"]))
        for row in completed
    }
    if len(completed) != 127 or keys != set(pending):
        raise RuntimeError("recovered score cache is incomplete")
    completed_path = args.output_dir / "api_results.jsonl"
    write_jsonl(completed_path, completed)

    scores = {
        (str(row["question_id"]), str(row["prediction_sha256"])): float(
            row["score_R5"]
        )
        for row in completed
    }
    slots = read_jsonl(slots_path)
    expanded = {}
    for slot in slots:
        slot_qid = str(slot["question_id"])
        expanded.setdefault(slot_qid, {
            "question_id": slot_qid,
            "video_id": str(slot["video_id"]),
        })[slot["variant"]] = scores[
            (slot_qid, slot["prediction_sha256"])
        ]
    rows = [expanded[key] for key in sorted(expanded)]
    if len(rows) != 99 or any(set(VARIANTS) - set(row) for row in rows):
        raise RuntimeError("expanded screen score table is incomplete")
    scores_path = args.output_dir / "scores_screen.jsonl"
    write_jsonl(scores_path, rows)

    methods = {
        variant: method_summary(rows, variant) for variant in VARIANTS
    }
    comparison = comparison_summary(rows, args.bootstrap)
    screen_gate = (
        passes_metric_gate(
            comparison["tiers"]["R5"],
            comparison["tiers"]["R2"],
        )
        and comparison["wrong_to_right"]
        >= comparison["right_to_wrong"]
    )
    successful_usage = {
        name: sum(
            int((row.get("usage") or {}).get(name) or 0)
            for row in completed
        )
        for name in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary = {
        "schema_version": "evads_deepeyes_screen_summary_recovered_v1",
        "not_human_gold": True,
        "analysis_role": "SFT_development_screen",
        "question_count": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "methods": methods,
        "comparisons": {
            f"{CANDIDATE}_vs_{BASELINE}": comparison,
        },
        "screen_selection": {
            "eligible_candidates": [CANDIDATE] if screen_gate else [],
            "selected_candidate": CANDIDATE if screen_gate else None,
        },
        "development_confirmation_gate_passed": None,
        "E_VAds_Test_references_read": False,
        "judge": {
            "model": "deepseek-chat",
            "planned_unique_candidates": 127,
            "initial_api_calls": 127,
            "initial_successes": 126,
            "format_only_recovery_calls_round1": 1,
            "final_successful_candidates": 127,
            "automatic_retries": 0,
            "usage_for_successful_responses": successful_usage,
            "format_only_recovery_elapsed_seconds": time.time() - started,
        },
        "hashes": {
            **source_hashes,
            "api_results": sha256_file(completed_path),
            "scores": sha256_file(scores_path),
        },
    }
    dump(args.output_dir / "summary.json", summary)
    dump(args.output_dir / "SCREEN_SELECTION.json", {
        "selected_candidate": CANDIDATE if screen_gate else None,
        "eligible_candidates": [CANDIDATE] if screen_gate else [],
        "selection_rule_frozen": True,
    })
    dump(args.output_dir / "JUDGE_COMPLETE.json", {
        "unique_candidates": 127,
        "final_successful_candidates": 127,
        "initial_failures": 1,
        "format_only_recovery_calls_round1": 1,
        "automatic_retries": 0,
        "not_human_gold": True,
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
