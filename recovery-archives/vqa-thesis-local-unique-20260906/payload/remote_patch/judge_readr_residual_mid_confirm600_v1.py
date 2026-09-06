#!/usr/bin/env python3
"""Judge the frozen ResidualMid12 gate on the ReAd-R Confirm-600 set."""

from __future__ import annotations

import concurrent.futures
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import threading

import numpy as np

from judge_adsqa_answer_lora_oof_v1 import (
    VALID_SCORES,
    legacy_parse_score,
    legacy_protocol,
)


ROOT = Path("evaluation/runs/readr_increment_confirm600_v1/residual_mid_confirm600_v1")
REFS = Path(
    "evaluation/runs/readr_increment_confirm600_v1/"
    "judge_deepseek_legacy_answeronly_v1/materialized_v1/private_references/"
    "groundtruth_confirm600.json"
)
OLD = Path(
    "evaluation/runs/readr_increment_confirm600_v1/"
    "judge_deepseek_legacy_answeronly_v1/results_v1/"
    "expanded_four_method_scores.jsonl"
)
GATE = ROOT / "gate_analysis_v1/summary.json"
LEGACY = Path(
    "/data1/rmx/backups/AdsQA-main/20260710_before_reorg/"
    "evaluation/evaluate_compare_new.py"
)


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_jsonl(path: Path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows, key):
    scores = np.asarray([float(row[key]) for row in rows], dtype=float)
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


def clustered_ci(rows, selected_key, baseline_key, samples, seed):
    by_video = defaultdict(list)
    for row in rows:
        by_video[str(row["video_id"])].append(row)
    videos = sorted(by_video)
    rng = np.random.default_rng(seed)
    relaxed_sums = np.asarray(
        [sum(float(r[selected_key]) - float(r[baseline_key]) for r in by_video[v]) for v in videos]
    )
    strict_sums = np.asarray(
        [
            sum(
                float(float(r[selected_key]) == 1.0)
                - float(float(r[baseline_key]) == 1.0)
                for r in by_video[v]
            )
            for v in videos
        ]
    )
    counts = np.asarray([len(by_video[v]) for v in videos], dtype=float)
    relaxed = np.empty(samples, dtype=float)
    strict = np.empty(samples, dtype=float)
    for start in range(0, samples, 256):
        stop = min(start + 256, samples)
        indices = rng.integers(0, len(videos), size=(stop - start, len(videos)))
        denominator = counts[indices].sum(axis=1)
        relaxed[start:stop] = relaxed_sums[indices].sum(axis=1) / denominator
        strict[start:stop] = strict_sums[indices].sum(axis=1) / denominator
    return {
        "relaxed_delta": [float(np.quantile(relaxed, 0.025)), float(np.quantile(relaxed, 0.975))],
        "strict_delta": [float(np.quantile(strict, 0.025)), float(np.quantile(strict, 0.975))],
        "samples": samples,
        "seed": seed,
        "cluster_count": len(videos),
    }


def pairwise(rows, selected_key, baseline_key, seed):
    selected = np.asarray([float(r[selected_key]) for r in rows])
    baseline = np.asarray([float(r[baseline_key]) for r in rows])
    delta = selected - baseline
    wrong_to_right = int(np.sum((baseline < 1.0) & (selected == 1.0)))
    right_to_wrong = int(np.sum((baseline == 1.0) & (selected < 1.0)))
    return {
        "rows": len(rows),
        "wins": int(np.sum(delta > 0)),
        "ties": int(np.sum(delta == 0)),
        "losses": int(np.sum(delta < 0)),
        "mean_relaxed_delta": float(np.mean(delta)),
        "mean_strict_delta": float(np.mean((selected == 1.0) - (baseline == 1.0))),
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "correction_precision": (
            wrong_to_right / (wrong_to_right + right_to_wrong)
            if wrong_to_right + right_to_wrong
            else None
        ),
        "video_cluster_bootstrap_ci95": clustered_ci(
            rows, selected_key, baseline_key, 10000, seed
        ),
    }


def main() -> None:
    out = ROOT / "judge_deepseek_residual_mid_v1"
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"refusing to overwrite existing output: {out}")

    refs = {str(row["question_id"]): row for row in load(REFS)}
    old = {str(row["question_id"]): row for row in load(OLD)}
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    rows = gate["rows_detail"]
    switched = [row for row in rows if row.get("gate_switched") is True]
    if len(refs) != 600 or len(old) != 600 or len(rows) != 152 or len(switched) != 22:
        raise RuntimeError("Confirm-600 frozen input counts do not match expected values")

    pending = []
    for row in switched:
        qid = str(row["question_id"])
        candidate = str(row["candidate_prediction"]).strip()
        if qid not in refs or qid not in old or not candidate:
            raise RuntimeError(f"missing judge context for {qid}")
        candidate_hash = sha256_text(candidate)
        if candidate_hash != str(row["candidate_prediction_sha256"]):
            raise RuntimeError(f"candidate hash mismatch for {qid}")
        pending.append({
            "question_id": qid,
            "candidate_prediction_sha256": candidate_hash,
            "owner": "ResidualMid12Gated",
        })
    pending.sort(key=lambda row: row["question_id"])
    pending_keys = {(row["question_id"], row["candidate_prediction_sha256"]) for row in pending}

    out.mkdir(parents=True)
    protocol = legacy_protocol(LEGACY)
    manifest = {
        "schema_version": "readr_residual_mid_confirm600_authorized_call_manifest_v1",
        "authorized_new_calls": 22,
        "question_count": 600,
        "gate_switch_count": 22,
        "generated_answer_change_count": int(sum(row.get("answer_changed") is True for row in rows)),
        "pending_question_hashes": pending,
        "not_human_gold": True,
        "reference_answers_sent_to_judge": True,
        "judge_prompt_sha256": protocol["prompt_sha256"],
        "legacy_evaluator_sha256": protocol["legacy_evaluator_sha256"],
        "parse_score_source_sha256": protocol["parse_score_source_sha256"],
    }
    (out / "authorized_call_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY missing")

    partial_path = out / "api_results_partial.jsonl"
    failure_path = out / "api_failures.jsonl"
    partial = {}
    if partial_path.exists():
        for result in load(partial_path):
            key = (str(result["question_id"]), str(result["candidate_prediction_sha256"]))
            if key not in pending_keys or float(result.get("score", -1)) not in VALID_SCORES:
                raise RuntimeError("partial result is outside the authorized whitelist")
            partial[key] = result

    local = threading.local()

    def judge_one(row):
        qid = row["question_id"]
        reference = refs[qid]
        candidate = str(gate_row_by_id[qid]["candidate_prediction"]).strip()
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=candidate,
        )
        if not hasattr(local, "client"):
            from openai import OpenAI
            local.client = OpenAI(api_key=api_key, base_url=protocol["base_url"], timeout=60.0)
        response = local.client.chat.completions.create(
            model=protocol["model_name"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        text = str(response.choices[0].message.content)
        score = legacy_parse_score(text)
        if score not in VALID_SCORES:
            raise RuntimeError(f"unparsed judge output for {qid}")
        usage = getattr(response, "usage", None)
        return {
            "question_id": qid,
            "candidate_prediction_sha256": row["candidate_prediction_sha256"],
            "owner": row["owner"],
            "score": float(score),
            "judge_output": text,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "score_source": "authorized_readr_residual_mid_confirm600",
        }

    gate_row_by_id = {str(row["question_id"]): row for row in switched}
    failures = []
    remaining = [row for row in pending if (row["question_id"], row["candidate_prediction_sha256"]) not in partial]
    with partial_path.open("a", encoding="utf-8") as handle:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(judge_one, row): row for row in remaining}
            for future in concurrent.futures.as_completed(futures):
                row = futures[future]
                try:
                    result = future.result()
                except Exception as error:
                    failures.append({"question_id": row["question_id"], "error": repr(error)})
                else:
                    key = (result["question_id"], result["candidate_prediction_sha256"])
                    partial[key] = result
                    handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                    handle.flush()
                print(f"completed={len(partial)}/{len(pending)} failures={len(failures)}", flush=True)
    if failures:
        write_jsonl(failure_path, failures)
        raise RuntimeError(f"{len(failures)} calls failed; no automatic retries")
    if set(partial) != pending_keys:
        raise RuntimeError("successful API results do not exactly cover the whitelist")
    write_jsonl(out / "api_results.jsonl", [partial[key] for key in sorted(partial)])
    write_jsonl(failure_path, [])

    api_score = {qid: float(result["score"]) for (qid, _), result in partial.items()}
    expanded = []
    switched_ids = set(gate_row_by_id)
    for qid, old_row in sorted(old.items()):
        mmr = float(old_row["MMR8_score"])
        adaptive = float(old_row["Adaptive12Gated_score"])
        residual = api_score[qid] if qid in switched_ids else mmr
        expanded.append({
            "question_id": qid,
            "video_id": str(old_row["video_id"]),
            "question_type": str(old_row.get("question_type", "unknown")),
            "MMR8_score": mmr,
            "Adaptive12Gated_score": adaptive,
            "ResidualMid12Gated_score": residual,
            "switched": qid in switched_ids,
        })
    write_jsonl(out / "expanded_scores.jsonl", expanded)

    comparisons = {
        "ResidualMid12Gated_vs_MMR8": pairwise(expanded, "ResidualMid12Gated_score", "MMR8_score", 2026073103),
        "ResidualMid12Gated_vs_Adaptive12Gated": pairwise(expanded, "ResidualMid12Gated_score", "Adaptive12Gated_score", 2026073104),
        "Adaptive12Gated_vs_MMR8": pairwise(expanded, "Adaptive12Gated_score", "MMR8_score", 2026073105),
    }
    type_results = {}
    for qtype in sorted({row["question_type"] for row in expanded}):
        subset = [row for row in expanded if row["question_type"] == qtype]
        type_results[qtype] = {
            "MMR8": metrics(subset, "MMR8_score"),
            "Adaptive12Gated": metrics(subset, "Adaptive12Gated_score"),
            "ResidualMid12Gated": metrics(subset, "ResidualMid12Gated_score"),
        }
    usage_totals = {
        key: sum(int((row.get("judge_usage") or {}).get(key) or 0) for row in partial.values())
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary = {
        "schema_version": "readr_residual_mid_confirm600_judge_v1",
        "not_human_gold": True,
        "authorized_new_calls": 22,
        "actual_new_successful_calls": len(partial),
        "automatic_retries": 0,
        "one_shot_failures": 0,
        "historical_exact_reuse_count": 600 - len(partial),
        "generated_answer_change_count": int(sum(row.get("answer_changed") is True for row in rows)),
        "gate_switch_count": len(switched),
        "judge_response_models": sorted({str(row.get("judge_response_model")) for row in partial.values()}),
        "new_api_usage_totals": usage_totals,
        "confirm600": {
            "MMR8": metrics(expanded, "MMR8_score"),
            "Adaptive12Gated": metrics(expanded, "Adaptive12Gated_score"),
            "ResidualMid12Gated": metrics(expanded, "ResidualMid12Gated_score"),
        },
        "complete_comparisons": comparisons,
        "question_type_stratified": type_results,
        "protocol": {
            "reference_answers_read": True,
            "reference_answers_in_model_inputs": False,
            "candidate_mode": "answer_only",
            "legacy_evaluator_sha256": protocol["legacy_evaluator_sha256"],
            "judge_prompt_sha256": protocol["prompt_sha256"],
            "parse_score_source_sha256": protocol["parse_score_source_sha256"],
            "gate_summary_sha256": sha256_file(GATE),
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "JUDGE_COMPLETE").touch()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
