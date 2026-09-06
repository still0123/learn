#!/usr/bin/env python3
"""Judge the paired ReAd-R OCR-box crop/full Confirm-35 experiment."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from judge_adsqa_answer_lora_oof_v1 import VALID_SCORES, legacy_parse_score, legacy_protocol


ROOT = Path("evaluation/runs/readr_ocrbox_routed_confirm_v2")
REFS = Path(
    "evaluation/runs/readr_increment_confirm600_v1/judge_deepseek_legacy_answeronly_v1/"
    "materialized_v1/private_references/groundtruth_confirm600.json"
)
CACHE_ROOT = Path(
    "evaluation/runs/readr_increment_confirm600_v1/judge_deepseek_legacy_answeronly_v1"
)
LEGACY = Path(
    "/data1/rmx/backups/AdsQA-main/20260710_before_reorg/"
    "evaluation/evaluate_compare_new.py"
)
OUT = ROOT / "judge_deepseek_v1"
ARMS = {
    "ocr_box_crop": "ReAdR_OCRBoxCrop12_A2",
    "ocr_box_full": "ReAdR_OCRMomentFull12_Control",
}


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def norm(text: str) -> str:
    return " ".join(str(text).casefold().split())


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def metrics(rows, key):
    values = np.asarray([row[key] for row in rows], dtype=float)
    return {
        "n": len(rows),
        "strict": float(np.mean(values == 1.0)),
        "relaxed": float(np.mean(values)),
        "counts": {str(score): int(np.sum(values == score)) for score in (0.0, 0.5, 1.0)},
    }


def paired(rows, selected, baseline):
    left = np.asarray([row[selected] for row in rows], dtype=float)
    right = np.asarray([row[baseline] for row in rows], dtype=float)
    delta = left - right
    rng = np.random.default_rng(20260803)
    indices = rng.integers(0, len(rows), size=(10000, len(rows)))
    relaxed = delta[indices].mean(axis=1)
    strict_delta = ((left == 1.0).astype(float) - (right == 1.0).astype(float))[indices].mean(axis=1)
    return {
        "n": len(rows),
        "wins": int(np.sum(delta > 0)),
        "ties": int(np.sum(delta == 0)),
        "losses": int(np.sum(delta < 0)),
        "relaxed_delta": float(np.mean(delta)),
        "strict_delta": float(np.mean((left == 1.0).astype(float) - (right == 1.0).astype(float))),
        "relaxed_ci95": [float(x) for x in np.quantile(relaxed, [0.025, 0.975])],
        "strict_ci95": [float(x) for x in np.quantile(strict_delta, [0.025, 0.975])],
        "bootstrap_samples": 10000,
        "cluster_unit": "video (one question per video)",
    }


def main() -> None:
    resume_results = OUT / "api_results.jsonl"
    if (OUT / "JUDGE_COMPLETE").exists():
        raise RuntimeError(f"judge already complete: {OUT}")
    if OUT.exists() and any(OUT.iterdir()) and not resume_results.exists():
        raise RuntimeError(f"incomplete output cannot be resumed safely: {OUT}")
    refs = {str(row["question_id"]): row for row in load(REFS)}
    protocol = legacy_protocol(LEGACY)

    candidates = {}
    by_arm = {}
    for arm, method in ARMS.items():
        by_arm[arm] = {}
        for path in (ROOT / arm).glob("*/a2_prediction.json"):
            row = json.load(open(path))
            if row["method"] != method:
                raise RuntimeError("method mismatch")
            qid = str(row["question_id"])
            prediction = str(row["prediction"]).strip()
            key = (qid, norm(prediction))
            candidates[key] = {"question_id": qid, "candidate_prediction": prediction}
            by_arm[arm][qid] = key
    if any(len(rows) != 35 for rows in by_arm.values()):
        raise RuntimeError("expected 35 predictions per arm")
    if set(by_arm["ocr_box_crop"]) != set(by_arm["ocr_box_full"]):
        raise RuntimeError("paired question mismatch")

    cache = {}
    for path in CACHE_ROOT.rglob("*.jsonl"):
        try:
            rows = load(path)
        except Exception:
            continue
        for row in rows:
            qid = row.get("question_id")
            prediction = row.get("candidate_prediction") or row.get("prediction")
            score = row.get("score")
            if qid and prediction is not None and score in VALID_SCORES:
                cache[(str(qid), norm(str(prediction)))] = float(score)

    reused = {key: cache[key] for key in candidates if key in cache}
    pending = [candidates[key] for key in sorted(candidates) if key not in cache]
    if len(pending) != 4:
        raise RuntimeError(f"authorization permits exactly 4 new calls, found {len(pending)}")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "readr_ocrbox_routed_confirm35_authorization_v1",
        "authorized_new_calls": 4,
        "actual_candidate_arms": 70,
        "reused_arm_scores": 66,
        "unique_candidate_count": len(candidates),
        "pending": [
            {"question_id": row["question_id"], "candidate_sha256": digest(row["candidate_prediction"])}
            for row in pending
        ],
        "reference_answers_sent_to_judge": True,
        "not_human_gold": True,
        "judge_prompt_sha256": protocol["prompt_sha256"],
    }
    if not (OUT / "authorized_call_manifest.json").exists():
        dump_json(OUT / "authorized_call_manifest.json", manifest)

    api_key = os.environ.get("DEEPSEEK_API_KEY")

    def judge(row):
        from openai import OpenAI

        qid = row["question_id"]
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
                {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
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
            "candidate_prediction": row["candidate_prediction"],
            "candidate_prediction_sha256": digest(row["candidate_prediction"]),
            "score": float(score),
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "score_source": "authorized_readr_ocrbox_confirm35_v1",
        }

    if resume_results.exists():
        api_results = load(resume_results)
        expected = {(row["question_id"], digest(row["candidate_prediction"])) for row in pending}
        actual = {(row["question_id"], row["candidate_prediction_sha256"]) for row in api_results}
        if len(api_results) != 4 or actual != expected:
            raise RuntimeError("saved API results do not match the authorized pending set")
    else:
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY missing")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            api_results = list(executor.map(judge, pending))
        dump_jsonl(resume_results, api_results)
    scores = dict(reused)
    for row in api_results:
        scores[(row["question_id"], norm(row["candidate_prediction"]))] = row["score"]

    detail = []
    for qid in sorted(by_arm["ocr_box_crop"]):
        detail.append({
            "question_id": qid,
            "video_id": qid.split("_", 1)[0],
            "ocr_box_crop_score": scores[by_arm["ocr_box_crop"][qid]],
            "ocr_box_full_score": scores[by_arm["ocr_box_full"][qid]],
        })
    dump_jsonl(OUT / "scores_paired.jsonl", detail)
    summary = {
        "schema_version": "readr_ocrbox_routed_confirm35_judge_v1",
        "not_human_gold": True,
        "judge_model": protocol["model_name"],
        "actual_new_api_calls": len(api_results),
        "reused_arm_scores": 66,
        "methods": {
            "ocr_box_crop": metrics(detail, "ocr_box_crop_score"),
            "ocr_box_full": metrics(detail, "ocr_box_full_score"),
        },
        "crop_vs_full": paired(detail, "ocr_box_crop_score", "ocr_box_full_score"),
    }
    dump_json(OUT / "summary.json", summary)
    (OUT / "JUDGE_COMPLETE").touch()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
