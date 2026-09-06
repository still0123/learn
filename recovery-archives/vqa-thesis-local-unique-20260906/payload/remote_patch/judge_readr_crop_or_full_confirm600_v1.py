#!/usr/bin/env python3
"""Judge the ten authorized CropOrFull12 cache misses and finalize Confirm-600."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np

from judge_adsqa_answer_lora_oof_v1 import VALID_SCORES, legacy_parse_score, legacy_protocol


ROOT = Path("evaluation/runs/readr_crop_or_full_confirm600_v1")
BASE_ROOT = Path("evaluation/runs/readr_increment_confirm600_v1")
REFS = BASE_ROOT / (
    "judge_deepseek_legacy_answeronly_v1/materialized_v1/"
    "private_references/groundtruth_confirm600.json"
)
BASE_SCORES = BASE_ROOT / (
    "judge_deepseek_legacy_answeronly_v1/results_v1/expanded_four_method_scores.jsonl"
)
MAIN_CACHE = BASE_ROOT / (
    "judge_deepseek_legacy_answeronly_v1/results_v1/api_results_partial.jsonl"
)
SUPPLEMENTAL_CACHES = [
    BASE_ROOT / "residual_mid_confirm600_v1/judge_deepseek_residual_mid_v1/api_results.jsonl",
    Path("evaluation/runs/readr_ocrbox_routed_confirm_v2/judge_deepseek_v1/api_results.jsonl"),
]
LEGACY = Path(
    "/data1/rmx/backups/AdsQA-main/20260710_before_reorg/"
    "evaluation/evaluate_compare_new.py"
)
OUT = ROOT / "judge_deepseek_v1"
AUTHORIZED_NEW_CALLS = 10


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def digest(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def dump_jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def metrics(rows, key):
    values = np.asarray([row[key] for row in rows], dtype=float)
    return {
        "rows": len(rows),
        "strict": float(np.mean(values == 1.0)),
        "relaxed": float(np.mean(values)),
        "counts": {str(v): int(np.sum(values == v)) for v in (0.0, 0.5, 1.0)},
    }


def paired(rows, selected, baseline, seed):
    left = np.asarray([row[selected] for row in rows], dtype=float)
    right = np.asarray([row[baseline] for row in rows], dtype=float)
    delta = left - right
    strict_delta = (left == 1.0).astype(float) - (right == 1.0).astype(float)
    by_video = {}
    for index, row in enumerate(rows):
        by_video.setdefault(str(row["video_id"]), []).append(index)
    videos = sorted(by_video)
    rng = np.random.default_rng(seed)
    relaxed_bootstrap = []
    strict_bootstrap = []
    for _ in range(10000):
        selected_videos = rng.choice(videos, size=len(videos), replace=True)
        indices = [index for video in selected_videos for index in by_video[video]]
        relaxed_bootstrap.append(float(np.mean(delta[indices])))
        strict_bootstrap.append(float(np.mean(strict_delta[indices])))
    wrong_to_right = int(np.sum((right < 1.0) & (left == 1.0)))
    right_to_wrong = int(np.sum((right == 1.0) & (left < 1.0)))
    return {
        "rows": len(rows),
        "wins": int(np.sum(delta > 0)),
        "ties": int(np.sum(delta == 0)),
        "losses": int(np.sum(delta < 0)),
        "relaxed_delta": float(np.mean(delta)),
        "strict_delta": float(np.mean(strict_delta)),
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "strict_correction_precision": (
            wrong_to_right / (wrong_to_right + right_to_wrong)
            if wrong_to_right + right_to_wrong
            else None
        ),
        "video_cluster_bootstrap_ci95": {
            "relaxed_delta": [
                float(x) for x in np.quantile(relaxed_bootstrap, [0.025, 0.975])
            ],
            "strict_delta": [
                float(x) for x in np.quantile(strict_bootstrap, [0.025, 0.975])
            ],
            "samples": 10000,
            "cluster_count": len(videos),
            "seed": seed,
        },
    }


def main():
    if (OUT / "JUDGE_COMPLETE").exists():
        raise RuntimeError("judge already complete")
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError("judge output exists; refusing to overwrite")

    refs = {str(row["question_id"]): row for row in load(REFS)}
    base = {str(row["question_id"]): row for row in load(BASE_SCORES)}
    gate = json.loads((ROOT / "gate_analysis_v1/summary.json").read_text())
    switched = [row for row in gate["rows_detail"] if row["gate_switched"]]
    if len(switched) != 22:
        raise RuntimeError("expected 22 frozen gate switches")

    # The original Confirm-600 batch is authoritative. Later caches only fill misses.
    score_cache = {}
    cache_source = {}
    cache_conflicts = []
    for path in [MAIN_CACHE] + SUPPLEMENTAL_CACHES:
        for row in load(path):
            qid = str(row.get("question_id", ""))
            candidate_hash = row.get("candidate_prediction_sha256")
            score = row.get("score")
            if not qid or not candidate_hash or score not in VALID_SCORES:
                continue
            key = (qid, candidate_hash)
            if key in score_cache and score_cache[key] != float(score):
                cache_conflicts.append(
                    {
                        "question_id": qid,
                        "candidate_prediction_sha256": candidate_hash,
                        "kept_score": score_cache[key],
                        "ignored_score": float(score),
                        "kept_source": cache_source[key],
                        "ignored_source": str(path),
                    }
                )
                continue
            if key not in score_cache:
                score_cache[key] = float(score)
                cache_source[key] = str(path)

    reused = []
    pending = []
    for row in switched:
        key = (str(row["question_id"]), row["candidate_prediction_sha256"])
        if key in score_cache:
            reused.append(row)
        else:
            pending.append(row)
    if len(pending) != AUTHORIZED_NEW_CALLS:
        raise RuntimeError(
            f"authorization permits {AUTHORIZED_NEW_CALLS} calls, found {len(pending)}"
        )

    OUT.mkdir(parents=True)
    protocol = legacy_protocol(LEGACY)
    manifest = {
        "schema_version": "readr_crop_or_full_confirm600_authorization_v1",
        "authorized_new_calls": AUTHORIZED_NEW_CALLS,
        "gate_switch_count": len(switched),
        "exact_cache_reuse_count": len(reused),
        "cache_conflict_count": len(cache_conflicts),
        "cache_conflict_policy": "original_confirm600_batch_precedence",
        "pending": [
            {
                "question_id": row["question_id"],
                "candidate_prediction_sha256": row["candidate_prediction_sha256"],
            }
            for row in pending
        ],
        "not_human_gold": True,
        "reference_answers_sent_to_judge": True,
        "judge_prompt_sha256": protocol["prompt_sha256"],
    }
    dump_json(OUT / "authorized_call_manifest.json", manifest)
    dump_jsonl(OUT / "cache_conflicts.jsonl", cache_conflicts)

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY missing")

    def judge(row):
        from openai import OpenAI

        qid = str(row["question_id"])
        reference = refs[qid]
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=row["candidate_prediction"],
        )
        client = OpenAI(api_key=api_key, base_url=protocol["base_url"], timeout=60.0)
        response = client.chat.completions.create(
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
            raise RuntimeError(f"unparsed output for {qid}")
        usage = getattr(response, "usage", None)
        return {
            "question_id": qid,
            "candidate_prediction_sha256": row["candidate_prediction_sha256"],
            "score": float(score),
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "score_source": "authorized_readr_crop_or_full_confirm600_v1",
        }

    failures = []
    api_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(judge, row) for row in pending]
        for future in futures:
            try:
                api_results.append(future.result())
            except Exception as error:
                failures.append({"error": repr(error)})
    if failures:
        dump_jsonl(OUT / "api_failures.jsonl", failures)
        raise RuntimeError(f"judge failures: {len(failures)}")
    dump_jsonl(OUT / "api_results.jsonl", api_results)
    for row in api_results:
        score_cache[(row["question_id"], row["candidate_prediction_sha256"])] = float(
            row["score"]
        )

    switched_by_qid = {str(row["question_id"]): row for row in switched}
    details = []
    for qid, base_row in sorted(base.items()):
        selected_score = float(base_row["MMR8_score"])
        gate_row = switched_by_qid.get(qid)
        if gate_row:
            selected_score = score_cache[(qid, gate_row["candidate_prediction_sha256"])]
        details.append(
            {
                "question_id": qid,
                "video_id": str(base_row["video_id"]),
                "MMR8_score": float(base_row["MMR8_score"]),
                "Adaptive12Gated_score": float(base_row["Adaptive12Gated_score"]),
                "ExtraGlobal12Gated_score": float(base_row["ExtraGlobal12Gated_score"]),
                "CropOrFull12Gated_score": selected_score,
                "gate_switched": gate_row is not None,
                "crop_anchor_count": int(gate_row["crop_anchor_count"]) if gate_row else 0,
            }
        )
    if len(details) != 600:
        raise RuntimeError("final coverage mismatch")
    dump_jsonl(OUT / "scores_confirm600.jsonl", details)

    switched_details = [row for row in details if row["gate_switched"]]
    crop_switched = [row for row in switched_details if row["crop_anchor_count"] > 0]
    full_switched = [row for row in switched_details if row["crop_anchor_count"] == 0]
    usage_totals = Counter()
    for row in api_results:
        for key, value in (row.get("judge_usage") or {}).items():
            if isinstance(value, (int, float)):
                usage_totals[key] += value
    summary = {
        "schema_version": "readr_crop_or_full_confirm600_judge_v1",
        "not_human_gold": True,
        "judge_model": protocol["model_name"],
        "authorized_new_calls": AUTHORIZED_NEW_CALLS,
        "actual_new_successful_calls": len(api_results),
        "automatic_retries": 0,
        "exact_cache_reuse_count": len(reused),
        "cache_conflict_count": len(cache_conflicts),
        "new_api_usage_totals": dict(usage_totals),
        "protocol": {
            "rows": 600,
            "trigger_count": 152,
            "trigger_rate": 152 / 600,
            "switch_count": len(switched),
            "crop_routed_trigger_count": 88,
            "crop_routed_dataset_rate": 88 / 600,
            "crop_switch_count": len(crop_switched),
            "visual_views_on_trigger": 12,
            "visual_tokens_on_trigger": 3992,
            "average_answer_visual_tokens": (448 * 1296 + 152 * 3992) / 600,
            "tau": gate["tau"],
            "margin": gate["margin"],
        },
        "methods": {
            "MMR8": metrics(details, "MMR8_score"),
            "Adaptive12Gated": metrics(details, "Adaptive12Gated_score"),
            "ExtraGlobal12Gated": metrics(details, "ExtraGlobal12Gated_score"),
            "CropOrFull12Gated": metrics(details, "CropOrFull12Gated_score"),
        },
        "comparisons": {
            "CropOrFull12Gated_vs_MMR8": paired(
                details, "CropOrFull12Gated_score", "MMR8_score", 2026080301
            ),
            "CropOrFull12Gated_vs_Adaptive12Gated": paired(
                details,
                "CropOrFull12Gated_score",
                "Adaptive12Gated_score",
                2026080302,
            ),
            "CropOrFull12Gated_vs_ExtraGlobal12Gated": paired(
                details,
                "CropOrFull12Gated_score",
                "ExtraGlobal12Gated_score",
                2026080303,
            ),
        },
        "switched_subgroups": {
            "all": paired(switched_details, "CropOrFull12Gated_score", "MMR8_score", 2026080311),
            "used_crop": paired(crop_switched, "CropOrFull12Gated_score", "MMR8_score", 2026080312),
            "used_full": paired(full_switched, "CropOrFull12Gated_score", "MMR8_score", 2026080313),
        },
    }
    dump_json(OUT / "summary.json", summary)
    (OUT / "JUDGE_COMPLETE").touch()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
