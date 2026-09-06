#!/usr/bin/env python3
"""Identity-deduplicated paired adjudication for UncertaintyGatedLocal8."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import re
import statistics
import time
from typing import Any

from openai import OpenAI


BASELINE = "Shared32_Local8"
CANDIDATE = "Shared32_UncertaintyGatedLocal8"
VALID_SCORES = {0.0, 0.5, 1.0}
ROUNDS = 3


PROMPT = """You are evaluating two answers to the same advertising-video question.

Question:
{question}

Reference answer:
{reference}

Anonymous answer A:
{answer_a}

Anonymous answer B:
{answer_b}

Score each answer independently:
- 1: contains all key information in the reference and has no contradiction.
- 0.5: contains most or part of the key information and has no contradiction.
- 0: misses the key information or contradicts it.

Return one JSON object only:
{{"score_a": 0|0.5|1, "score_b": 0|0.5|1, "reason": "brief comparison"}}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--question-root", required=True)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def extract_answer(text: str) -> str:
    markers = ("3. [Answer]:", "[Answer]:", "3. [Answer]", "[Answer]")
    matches = [(text.find(marker), marker) for marker in markers if text.find(marker) >= 0]
    if not matches:
        return text.strip()
    position, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
    answer = text[position + len(marker):].strip()
    return answer or text.strip()


def prediction(run_root: Path, method: str, question_id: str) -> str:
    matches = sorted((run_root / "judge_inputs" / method).glob(f"*/{question_id}/prediction.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one prediction for {method}/{question_id}, found {len(matches)}")
    payload = json.loads(matches[0].read_text(encoding="utf-8"))
    row = payload[0] if isinstance(payload, list) else payload
    return extract_answer(str(row.get("prediction", "")))


def load_questions(root: Path) -> dict[str, str]:
    questions: dict[str, str] = {}
    for path in sorted(root.glob("fold_*/validation_questions_v1.json")):
        for row in json.loads(path.read_text(encoding="utf-8")):
            question_id = str(row["question_id"])
            if question_id in questions:
                raise ValueError(f"duplicate question ID {question_id}")
            questions[question_id] = str(row["question"])
    return questions


def parse_response(content: str) -> dict[str, Any]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        object_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not object_match:
            raise ValueError(f"judge returned no JSON object: {text[:200]}")
        payload = json.loads(object_match.group(0))
    score_a = float(payload["score_a"])
    score_b = float(payload["score_b"])
    if score_a not in VALID_SCORES or score_b not in VALID_SCORES:
        raise ValueError(f"invalid paired scores: {score_a}, {score_b}")
    return {"score_a": score_a, "score_b": score_b, "reason": str(payload.get("reason", ""))}


def judge_once(client: OpenAI, prompt: str, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a strict, impartial advertising QA evaluator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            content = str(response.choices[0].message.content or "")
            parsed = parse_response(content)
            metadata = {
                "model": response.model,
                "usage": response.usage.model_dump() if response.usage else None,
                "raw_response": content,
            }
            return parsed, metadata
        except Exception as exc:  # API and parse failures share the same bounded retry.
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"paired judge failed after retries: {last_error}")


def mode_or_median(values: list[float]) -> float:
    counts = Counter(values)
    highest = max(counts.values())
    modes = sorted(value for value, count in counts.items() if count == highest)
    return modes[len(modes) // 2] if len(modes) == 1 else float(statistics.median(values))


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def clustered_bootstrap(
    qids_by_video: dict[str, list[str]],
    baseline_scores: dict[str, float],
    candidate_scores: dict[str, float],
    samples: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    videos = sorted(qids_by_video)
    relaxed_samples = []
    strict_samples = []
    for _ in range(samples):
        sampled_videos = [rng.choice(videos) for _ in videos]
        sampled_qids = [qid for video in sampled_videos for qid in qids_by_video[video]]
        relaxed = [candidate_scores[qid] - baseline_scores[qid] for qid in sampled_qids]
        strict = [
            float(candidate_scores[qid] == 1.0) - float(baseline_scores[qid] == 1.0)
            for qid in sampled_qids
        ]
        relaxed_samples.append(sum(relaxed) / len(relaxed))
        strict_samples.append(sum(strict) / len(strict))
    return {
        "samples": samples,
        "seed": seed,
        "relaxed_ci95": [percentile(relaxed_samples, 0.025), percentile(relaxed_samples, 0.975)],
        "strict_ci95": [percentile(strict_samples, 0.025), percentile(strict_samples, 0.975)],
    }


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root).resolve()
    question_root = Path(args.question_root).resolve()
    groundtruth_path = Path(args.groundtruth).resolve()
    output_dir = Path(args.output_dir).resolve()
    summary_path = output_dir / "summary.json"
    if summary_path.exists() and not args.overwrite:
        raise SystemExit(f"summary exists: {summary_path}")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=90.0)

    protocol_audit = json.loads((run_root / "formal/protocol_audit_v1.json").read_text(encoding="utf-8"))
    if protocol_audit.get("passed") is not True:
        raise ValueError("formal visual protocol audit did not pass")
    groundtruth_rows = json.loads(groundtruth_path.read_text(encoding="utf-8"))
    groundtruth = {str(row["question_id"]): row for row in groundtruth_rows}
    questions = load_questions(question_root)
    manifest = jsonl(run_root / "manifest/uncertainty_gated_local8_oof_v1.jsonl")
    changed_qids = sorted(
        (
            str(row["question_id"])
            for row in manifest
            if row["uncertainty_selection"]["baseline_ranks"]
            != row["uncertainty_selection"]["selected_ranks"]
        ),
        key=int,
    )
    all_qids = sorted(groundtruth, key=int)
    answers = {
        method: {qid: prediction(run_root, method, qid) for qid in all_qids}
        for method in (BASELINE, CANDIDATE)
    }
    actual_changed = [qid for qid in all_qids if answers[BASELINE][qid] != answers[CANDIDATE][qid]]
    if actual_changed != changed_qids:
        raise ValueError("answer changes do not exactly match visual gate changes")

    output_dir.mkdir(parents=True, exist_ok=True)
    round_rows = []
    adjudicated = {}
    for qid in changed_qids:
        method_scores: dict[str, list[float]] = {BASELINE: [], CANDIDATE: []}
        pair_votes = []
        for round_index in range(ROUNDS):
            baseline_first = round_index == 0 or (round_index == 2 and int(qid) % 2 == 0)
            order = [BASELINE, CANDIDATE] if baseline_first else [CANDIDATE, BASELINE]
            prompt = PROMPT.format(
                question=questions[qid][:4000],
                reference=str(groundtruth[qid]["answer"]),
                answer_a=answers[order[0]][qid][:2000],
                answer_b=answers[order[1]][qid][:2000],
            )
            parsed, metadata = judge_once(client, prompt, model)
            mapped = {order[0]: parsed["score_a"], order[1]: parsed["score_b"]}
            for method in mapped:
                method_scores[method].append(mapped[method])
            vote = "candidate" if mapped[CANDIDATE] > mapped[BASELINE] else "baseline" if mapped[CANDIDATE] < mapped[BASELINE] else "tie"
            pair_votes.append(vote)
            round_rows.append({
                "question_id": qid,
                "round": round_index + 1,
                "anonymous_order": {"A": order[0], "B": order[1]},
                "answer_hashes": {method: sha256_text(answers[method][qid]) for method in order},
                "scores": mapped,
                "vote": vote,
                "reason": parsed["reason"],
                "judge": metadata,
                "not_human_gold": True,
            })
        vote_counts = Counter(pair_votes)
        majority = max(("candidate", "baseline", "tie"), key=lambda item: (vote_counts[item], item == "tie"))
        adjudicated[qid] = {
            "question_id": qid,
            "reference_answer": str(groundtruth[qid]["answer"]),
            "answer_hashes": {method: sha256_text(answers[method][qid]) for method in (BASELINE, CANDIDATE)},
            "round_scores": method_scores,
            "consensus_scores": {method: mode_or_median(method_scores[method]) for method in method_scores},
            "vote_counts": dict(vote_counts),
            "majority": majority,
            "not_human_gold": True,
        }

    legacy_rows = jsonl(run_root / "judge_deepseek_answer_only_v1/results.jsonl")
    legacy = {(str(row["method"]), str(row["question_id"])): float(row["score"]) for row in legacy_rows}
    baseline_scores = {qid: legacy[(BASELINE, qid)] for qid in all_qids}
    candidate_scores = {}
    for qid in all_qids:
        if qid in adjudicated:
            baseline_scores[qid] = adjudicated[qid]["consensus_scores"][BASELINE]
            candidate_scores[qid] = adjudicated[qid]["consensus_scores"][CANDIDATE]
        else:
            candidate_scores[qid] = baseline_scores[qid]

    qids_by_video: dict[str, list[str]] = defaultdict(list)
    for qid in all_qids:
        qids_by_video[str(groundtruth[qid]["video"])].append(qid)
    relaxed_deltas = [candidate_scores[qid] - baseline_scores[qid] for qid in all_qids]
    strict_deltas = [
        float(candidate_scores[qid] == 1.0) - float(baseline_scores[qid] == 1.0)
        for qid in all_qids
    ]
    bootstrap = clustered_bootstrap(qids_by_video, baseline_scores, candidate_scores, args.samples, args.seed)

    def metrics(scores: dict[str, float]) -> dict[str, Any]:
        values = [scores[qid] for qid in all_qids]
        return {
            "n": len(values),
            "strict": sum(value == 1.0 for value in values) / len(values),
            "relaxed": sum(values) / len(values),
            "score_counts": dict(sorted(Counter(str(value) for value in values).items())),
        }

    summary = {
        "schema_version": "uncertainty_gated_local8_identity_dedup_paired_judge_v1",
        "passed": True,
        "question_count": len(all_qids),
        "video_count": len(qids_by_video),
        "visual_and_answer_changed_count": len(changed_qids),
        "identity_reused_count": len(all_qids) - len(changed_qids),
        "paired_judge_rounds_per_changed_answer": ROUNDS,
        "methods": {BASELINE: metrics(baseline_scores), CANDIDATE: metrics(candidate_scores)},
        "pairwise": {
            "candidate_wins": sum(delta > 0 for delta in relaxed_deltas),
            "ties": sum(delta == 0 for delta in relaxed_deltas),
            "baseline_wins": sum(delta < 0 for delta in relaxed_deltas),
            "relaxed_delta_candidate_minus_baseline": sum(relaxed_deltas) / len(relaxed_deltas),
            "strict_delta_candidate_minus_baseline": sum(strict_deltas) / len(strict_deltas),
            "video_cluster_bootstrap": bootstrap,
        },
        "changed_subset": {
            "question_ids": changed_qids,
            "candidate_majority_wins": sum(row["majority"] == "candidate" for row in adjudicated.values()),
            "ties": sum(row["majority"] == "tie" for row in adjudicated.values()),
            "baseline_majority_wins": sum(row["majority"] == "baseline" for row in adjudicated.values()),
        },
        "provenance": {
            "model_requested": model,
            "groundtruth_sha256": sha256_file(groundtruth_path),
            "manifest_sha256": sha256_file(run_root / "manifest/uncertainty_gated_local8_oof_v1.jsonl"),
            "formal_audit_sha256": sha256_file(run_root / "formal/protocol_audit_v1.json"),
            "legacy_results_sha256": sha256_file(run_root / "judge_deepseek_answer_only_v1/results.jsonl"),
            "prompt_sha256": sha256_text(PROMPT),
            "api_key_stored": False,
        },
        "not_human_gold": True,
    }
    (output_dir / "rounds.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in round_rows), encoding="utf-8")
    (output_dir / "adjudicated_changed11.jsonl").write_text("".join(json.dumps(adjudicated[qid], ensure_ascii=True) + "\n" for qid in changed_qids), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
