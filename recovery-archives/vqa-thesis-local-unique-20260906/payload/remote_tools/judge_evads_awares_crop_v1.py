#!/usr/bin/env python3
"""Preflight and judge E-VAds policy crop screening."""

from __future__ import annotations

import argparse
import concurrent.futures
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import re
import time
from typing import Any

import pyarrow.parquet as pq


ALLOWED_VARIANTS = {
    "anchor_global10",
    "awares_first10",
    "adaptvision_bbox10",
    "deepeyes_firstzoom10",
    "zoomeye_union10",
    "vlmr3_lastbbox10",
    "hide_layout10",
    "qzoom_roi10",
}
BASELINE = "anchor_global10"
VALID_SCORES = {0.0, 0.25, 0.5, 0.75, 1.0}
FORBIDDEN_INPUT_KEYS = {
    "answer",
    "reference_answer",
    "ground_truth",
    "label",
    "reward",
    "evidence_state",
    "pairwise_target",
}
JUDGE_PROMPT = """# Role
You are a professional E-commerce Content Analyst and Senior Evaluator. Objectively assess the model answer using the question, reference answer, evidence clues, and time-aligned OCR/ASR metadata.

# Scoring tiers
- 1.0: completely accurate, covers all key points, and uses evidence consistently.
- 0.75: core answer is accurate and complete but generic or lacks deeper business logic.
- 0.5: partially correct, with important information missing.
- 0.25: conclusion or cited evidence is materially misaligned, including hallucinated evidence.
- 0.0: incorrect, contradictory, non-responsive, or severely hallucinated.

# Input
[Question]
{question}

[Metadata (OCR/ASR)]
{metadata}

[Clues]
{clues}

[Reference Answer]
{reference}

[Model Output]
{prediction}

Return exactly one line: Answer: <0, 0.25, 0.5, 0.75, or 1.0>
"""
FOOTER = "\n\nYou are permitted to gather any relevant clues"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "judge"), required=True)
    parser.add_argument(
        "--stage",
        choices=("screen", "confirmation"),
        required=True,
    )
    parser.add_argument("--variants", nargs="+", required=True)
    parser.add_argument("--expected-questions", type=int, required=True)
    parser.add_argument("--source-question-count", type=int, default=100)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--inference-audit", type=Path, required=True)
    parser.add_argument("--preflight-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorized-call-limit", type=int, required=True)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--sft-parquet", type=Path)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap", type=int, default=10000)
    return parser.parse_args()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def answer_only(value):
    text = str(value).strip()
    match = re.search(
        r"\[Answer\]\s*:\s*(.+)",
        text,
        flags=re.I | re.S,
    )
    if match:
        return match.group(1).strip().splitlines()[0].strip()
    match = re.search(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
    return " ".join((match.group(1) if match else text).split())


def tier(score, name):
    if name == "R5":
        return score
    if name == "R3":
        return 0.0 if score == 0.25 else 0.5 if score == 0.75 else score
    if name == "R2":
        return 1.0 if score == 1.0 else 0.0
    raise ValueError(name)


def passes_metric_gate(r5, r2, require_ci=False):
    def positive(metric):
        return (
            metric["video_cluster_bootstrap_ci95"][0] > 0
            if require_ci
            else metric["delta"] > 0
        )

    return (
        positive(r5) and r2["delta"] >= 0
    ) or (
        positive(r2) and r5["delta"] >= 0
    )


def self_check():
    assert passes_metric_gate({"delta": 0.1}, {"delta": 0.0})
    assert passes_metric_gate({"delta": 0.0}, {"delta": 0.1})
    assert not passes_metric_gate({"delta": 0.1}, {"delta": -0.1})
    assert passes_metric_gate(
        {"delta": 0.1, "video_cluster_bootstrap_ci95": [0.01, 0.2]},
        {"delta": 0.0, "video_cluster_bootstrap_ci95": [-0.1, 0.1]},
        require_ci=True,
    )


def clustered_ci(rows, selected, baseline, name, draws):
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row["video_id"])].append(
            tier(float(row[selected]), name) - tier(float(row[baseline]), name)
        )
    videos = sorted(grouped)
    rng = random.Random(2026080901)
    samples = []
    for _ in range(draws):
        selected_videos = [videos[rng.randrange(len(videos))] for _ in videos]
        values = [
            value
            for video in selected_videos
            for value in grouped[video]
        ]
        samples.append(sum(values) / len(values))
    samples.sort()
    return [
        samples[int((draws - 1) * 0.025)],
        samples[int((draws - 1) * 0.975)],
    ]


def preflight(args):
    if args.preflight_dir.exists():
        raise RuntimeError("preflight directory already exists")
    audit = json.loads(args.inference_audit.read_text())
    all_questions = {
        str(row["question_id"]): row
        for row in json.loads(args.questions.read_text())
    }
    if (
        audit.get("passed") is not True
        or set(audit.get("variants", [])) != set(args.variants)
        or int(audit.get("paired_question_count", -1))
        != args.expected_questions
        or len(all_questions) != args.source_question_count
        or any(
            FORBIDDEN_INPUT_KEYS & set(row)
            for row in all_questions.values()
        )
    ):
        raise RuntimeError("inference audit or questions are incomplete")
    predictions = defaultdict(dict)
    for prediction_path in sorted(
        args.inference_root.glob("fold_*/*/*/a2_prediction.json")
    ):
        row = json.loads(prediction_path.read_text())
        qid = str(row["question_id"])
        variant = prediction_path.parents[1].name
        if variant not in args.variants or variant in predictions[qid]:
            raise RuntimeError(f"invalid prediction path: {prediction_path}")
        prediction = answer_only(str(row["prediction"]))
        if not prediction:
            raise RuntimeError(f"empty prediction: {prediction_path}")
        predictions[qid][variant] = prediction
    if (
        len(predictions) != args.expected_questions
        or any(
            set(values) != set(args.variants)
            for values in predictions.values()
        )
    ):
        raise RuntimeError("paired predictions are incomplete")
    if not set(predictions).issubset(all_questions):
        raise RuntimeError("predictions are outside the frozen screen")
    questions = {qid: all_questions[qid] for qid in predictions}

    slots = []
    candidates = {}
    for qid in sorted(predictions):
        video_id = str(questions[qid]["video"])
        for variant in args.variants:
            prediction = predictions[qid][variant]
            prediction_hash = sha256_text(prediction)
            slots.append({
                "question_id": qid,
                "video_id": video_id,
                "variant": variant,
                "prediction": prediction,
                "prediction_sha256": prediction_hash,
            })
            key = (qid, prediction_hash)
            candidates.setdefault(key, {
                "question_id": qid,
                "video_id": video_id,
                "prediction": prediction,
                "prediction_sha256": prediction_hash,
                "variants": [],
            })["variants"].append(variant)
    pending = sorted(
        candidates.values(),
        key=lambda row: (row["question_id"], row["prediction_sha256"]),
    )
    args.preflight_dir.mkdir(parents=True, exist_ok=False)
    slots_path = args.preflight_dir / "candidate_slots_answer_free.jsonl"
    pending_path = args.preflight_dir / "pending_candidates_answer_free.jsonl"
    write_jsonl(slots_path, slots)
    write_jsonl(pending_path, pending)
    result = {
        "schema_version": "evads_policy_crop_judge_preflight_v2",
        "passed": 0 < len(pending) <= args.authorized_call_limit,
        "stage": args.stage,
        "question_count": args.expected_questions,
        "video_count": len({
            str(row["video"]) for row in questions.values()
        }),
        "variants": list(args.variants),
        "candidate_slot_count": len(slots),
        "unique_question_answer_calls": len(pending),
        "authorized_call_limit": args.authorized_call_limit,
        "groundtruth_read": False,
        "api_called": False,
        "not_human_gold": True,
        "questions_sha256": sha256_file(args.questions),
        "inference_audit_sha256": sha256_file(args.inference_audit),
        "slots_sha256": sha256_file(slots_path),
        "pending_sha256": sha256_file(pending_path),
    }
    dump(args.preflight_dir / "audit.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise RuntimeError("preflight did not pass")


def references(sft_parquet, ids):
    parquet = pq.ParquetFile(sft_parquet)
    selected = {}
    for row in parquet.read(
        columns=["answer", "prompt", "extra_info"]
    ).to_pylist():
        extra = row.get("extra_info") or {}
        qid = str(extra.get("id", ""))
        if qid in ids:
            prompt = row.get("prompt")
            if (
                not isinstance(prompt, list)
                or len(prompt) != 1
                or FOOTER not in str(prompt[0].get("content", ""))
            ):
                raise RuntimeError(f"malformed SFT prompt: {qid}")
            body = str(prompt[0]["content"]).split(FOOTER, 1)[0].rstrip()
            question = body.rsplit("\n", 1)[-1].strip()
            if not body.endswith(question):
                raise RuntimeError(f"could not isolate SFT question: {qid}")
            selected[qid] = {
                "reference_answer": str(row.get("answer", "")),
                "metadata": body[: body.rfind(question)].rstrip(),
                "clues": "",
            }
    if set(selected) != ids:
        raise RuntimeError("official SFT references do not cover development set")
    return selected


def parse_score(text):
    match = re.search(
        r"Answer:\s*(0(?:\.0+|\.25|\.5|\.75)?|1(?:\.0+)?)\b",
        text,
        flags=re.I,
    )
    if not match:
        raise RuntimeError("judge output has no valid score")
    score = float(match.group(1))
    if score not in VALID_SCORES:
        raise RuntimeError(f"invalid score: {score}")
    return score


def judge(args):
    if args.sft_parquet is None or args.authorization is None:
        raise RuntimeError("--sft-parquet and --authorization are required")
    if args.output_dir.exists():
        raise RuntimeError("judge output already exists")
    audit = json.loads((args.preflight_dir / "audit.json").read_text())
    authorization = json.loads(args.authorization.read_text())
    slots = read_jsonl(args.preflight_dir / "candidate_slots_answer_free.jsonl")
    pending = read_jsonl(args.preflight_dir / "pending_candidates_answer_free.jsonl")
    all_questions = {
        str(row["question_id"]): row
        for row in json.loads(args.questions.read_text())
    }
    slot_question_ids = {str(row["question_id"]) for row in slots}
    if (
        len(all_questions) != args.source_question_count
        or len(slot_question_ids) != args.expected_questions
        or not slot_question_ids.issubset(all_questions)
    ):
        raise RuntimeError("frozen screen question source changed")
    questions = {
        qid: all_questions[qid] for qid in slot_question_ids
    }
    if (
        audit.get("passed") is not True
        or audit.get("stage") != args.stage
        or audit.get("variants") != list(args.variants)
        or int(audit.get("question_count", -1))
        != args.expected_questions
        or len(pending) != int(audit["unique_question_answer_calls"])
        or len(pending) != args.authorized_call_limit
        or int(authorization.get("authorized_unique_calls", -1)) != len(pending)
        or authorization.get("preflight_audit_sha256")
        != sha256_file(args.preflight_dir / "audit.json")
        or authorization.get("pending_sha256")
        != sha256_file(args.preflight_dir / "pending_candidates_answer_free.jsonl")
        or authorization.get("slots_sha256")
        != sha256_file(args.preflight_dir / "candidate_slots_answer_free.jsonl")
        or audit.get("questions_sha256") != sha256_file(args.questions)
        or audit.get("inference_audit_sha256") != sha256_file(args.inference_audit)
    ):
        raise RuntimeError("judge preflight or authorization changed")
    refs = references(args.sft_parquet, set(questions))
    api_key = __import__("os").environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=150.0,
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    dump(args.output_dir / "manifest.json", {
        "schema_version": "evads_policy_crop_judge_manifest_v2",
        "stage": args.stage,
        "variants": list(args.variants),
        "authorized_call_limit": args.authorized_call_limit,
        "planned_calls": len(pending),
        "candidate_slot_count": len(slots),
        "model": "deepseek-chat",
        "automatic_retries": 0,
        "api_key_saved": False,
        "private_references_persisted": False,
        "not_human_gold": True,
        "source_hashes": {
            "script": sha256_file(Path(__file__)),
            "authorization": sha256_file(args.authorization),
            "preflight": sha256_file(args.preflight_dir / "audit.json"),
            "sft_parquet": sha256_file(args.sft_parquet),
        },
    })
    started = time.time()

    def score(candidate):
        qid = str(candidate["question_id"])
        if sha256_text(str(candidate["prediction"])) != candidate["prediction_sha256"]:
            raise RuntimeError(f"candidate hash changed: {qid}")
        ref = refs[qid]
        prompt = JUDGE_PROMPT.format(
            question=questions[qid]["question"],
            metadata=ref["metadata"],
            clues=ref["clues"],
            reference=ref["reference_answer"],
            prediction=candidate["prediction"],
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16,
        )
        usage = getattr(response, "usage", None)
        return {
            "question_id": qid,
            "prediction_sha256": candidate["prediction_sha256"],
            "score_R5": parse_score(str(response.choices[0].message.content)),
            "judge_model": getattr(response, "model", None),
            "usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "not_human_gold": True,
        }

    completed = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(score, row): row for row in pending}
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                completed.append(future.result())
            except Exception as error:
                failures.append({
                    "question_id": source["question_id"],
                    "prediction_sha256": source["prediction_sha256"],
                    "error": repr(error),
                })
    completed.sort(key=lambda row: (row["question_id"], row["prediction_sha256"]))
    failures.sort(key=lambda row: (row["question_id"], row["prediction_sha256"]))
    write_jsonl(args.output_dir / "api_results.jsonl", completed)
    if failures:
        write_jsonl(args.output_dir / "api_failures.jsonl", failures)
        dump(args.output_dir / "JUDGE_PARTIAL_AWAITING_RETRY_AUTHORIZATION.json", {
            "planned_calls": len(pending),
            "successful_calls": len(completed),
            "failed_calls": len(failures),
            "automatic_retries": 0,
        })
        raise RuntimeError(f"{len(failures)} authorized calls failed")

    scores = {
        (row["question_id"], row["prediction_sha256"]): float(row["score_R5"])
        for row in completed
    }
    expanded = {}
    for slot in slots:
        qid = str(slot["question_id"])
        expanded.setdefault(qid, {
            "question_id": qid,
            "video_id": str(slot["video_id"]),
        })[slot["variant"]] = scores[(qid, slot["prediction_sha256"])]
    rows = [expanded[qid] for qid in sorted(expanded)]
    if (
        len(rows) != args.expected_questions
        or any(set(args.variants) - set(row) for row in rows)
    ):
        raise RuntimeError("expanded score table is incomplete")
    scores_path = args.output_dir / f"scores_{args.stage}.jsonl"
    write_jsonl(scores_path, rows)

    methods = {}
    for variant in args.variants:
        values = [float(row[variant]) for row in rows]
        methods[variant] = {
            "rows": len(values),
            "R5": sum(values) / len(values),
            "R3": sum(tier(value, "R3") for value in values) / len(values),
            "R2": sum(tier(value, "R2") for value in values) / len(values),
            "counts": dict(Counter(str(value) for value in values)),
        }
    comparisons = {}
    for candidate in args.variants:
        if candidate == BASELINE:
            continue
        raw = [
            float(row[candidate]) - float(row[BASELINE])
            for row in rows
        ]
        comparison = {
            "selected": candidate,
            "baseline": BASELINE,
            "wins": sum(value > 0 for value in raw),
            "ties": sum(value == 0 for value in raw),
            "losses": sum(value < 0 for value in raw),
            "tiers": {},
        }
        for name in ("R5", "R3", "R2"):
            delta = [
                tier(float(row[candidate]), name)
                - tier(float(row[BASELINE]), name)
                for row in rows
            ]
            comparison["tiers"][name] = {
                "delta": sum(delta) / len(delta),
                "video_cluster_bootstrap_ci95": clustered_ci(
                    rows,
                    candidate,
                    BASELINE,
                    name,
                    args.bootstrap,
                ),
                "bootstrap_draws": args.bootstrap,
            }
        comparison["wrong_to_right"] = sum(
            tier(float(row[BASELINE]), "R2") == 0.0
            and tier(float(row[candidate]), "R2") == 1.0
            for row in rows
        )
        comparison["right_to_wrong"] = sum(
            tier(float(row[BASELINE]), "R2") == 1.0
            and tier(float(row[candidate]), "R2") == 0.0
            for row in rows
        )
        comparisons[f"{candidate}_vs_{BASELINE}"] = comparison

    eligible = [
        comparison
        for comparison in comparisons.values()
        if passes_metric_gate(
            comparison["tiers"]["R5"],
            comparison["tiers"]["R2"],
        )
        and comparison["wrong_to_right"] >= comparison["right_to_wrong"]
    ]
    selected_candidate = (
        max(
            eligible,
            key=lambda comparison: (
                comparison["tiers"]["R5"]["delta"],
                comparison["tiers"]["R2"]["delta"],
                comparison["wins"] - comparison["losses"],
                comparison["selected"],
            ),
        )["selected"]
        if args.stage == "screen" and eligible
        else None
    )
    confirmation_gate = None
    if args.stage == "confirmation":
        if len(comparisons) != 1:
            raise RuntimeError("confirmation requires one candidate and baseline")
        comparison = next(iter(comparisons.values()))
        r5 = comparison["tiers"]["R5"]
        r2 = comparison["tiers"]["R2"]
        confirmation_gate = passes_metric_gate(r5, r2, require_ci=True)
    usage = {
        name: sum(
            int((row.get("usage") or {}).get(name) or 0)
            for row in completed
        )
        for name in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary = {
        "schema_version": "evads_policy_crop_judge_summary_v2",
        "not_human_gold": True,
        "analysis_role": f"SFT_development_{args.stage}",
        "question_count": len(rows),
        "video_count": len({row["video_id"] for row in rows}),
        "methods": methods,
        "comparisons": comparisons,
        "screen_selection": {
            "eligible_candidates": [
                comparison["selected"] for comparison in eligible
            ],
            "selected_candidate": selected_candidate,
        } if args.stage == "screen" else None,
        "development_confirmation_gate_passed": confirmation_gate,
        "E_VAds_Test_references_read": False,
        "judge": {
            "model": "deepseek-chat",
            "planned_calls": len(pending),
            "successful_calls": len(completed),
            "failures": 0,
            "automatic_retries": 0,
            "usage": usage,
            "elapsed_seconds": time.time() - started,
        },
        "hashes": {
            "preflight": sha256_file(args.preflight_dir / "audit.json"),
            "sft_parquet": sha256_file(args.sft_parquet),
            "api_results": sha256_file(args.output_dir / "api_results.jsonl"),
            "scores": sha256_file(scores_path),
        },
    }
    dump(args.output_dir / "summary.json", summary)
    if args.stage == "screen":
        dump(args.output_dir / "SCREEN_SELECTION.json", {
            "selected_candidate": selected_candidate,
            "eligible_candidates": [
                comparison["selected"] for comparison in eligible
            ],
            "selection_rule_frozen": True,
        })
    dump(args.output_dir / "JUDGE_COMPLETE.json", {
        "planned_calls": len(pending),
        "actual_calls": len(completed),
        "failures": 0,
        "automatic_retries": 0,
        "not_human_gold": True,
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    self_check()
    args = parse_args()
    allowed_pairs = {
        ("anchor_global10", "awares_first10"),
        ("anchor_global10", "adaptvision_bbox10"),
        ("anchor_global10", "deepeyes_firstzoom10"),
        ("anchor_global10", "zoomeye_union10"),
        ("anchor_global10", "vlmr3_lastbbox10"),
        ("anchor_global10", "hide_layout10"),
        ("anchor_global10", "qzoom_roi10"),
    }
    if (
        args.stage not in {"screen", "confirmation"}
        or not 1 <= args.expected_questions <= args.source_question_count
        or args.source_question_count not in {100, 400}
        or tuple(args.variants) not in allowed_pairs
        or args.authorized_call_limit <= 0
    ):
        raise RuntimeError("arguments do not match the frozen stage protocol")
    if args.mode == "preflight":
        preflight(args)
    else:
        judge(args)


if __name__ == "__main__":
    main()
