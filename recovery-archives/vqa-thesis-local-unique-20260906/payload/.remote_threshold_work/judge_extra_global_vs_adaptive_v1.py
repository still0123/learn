#!/usr/bin/env python3
"""Paired answer-only judge for the frozen AdaptiveScale12 and ExtraGlobal12 arms."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any

from judge_adsqa_answer_lora_oof_v1 import JudgeProtocolError, VALID_SCORES, legacy_parse_score, legacy_protocol
from judge_adsqa_full5320_v1 import metrics, pairwise, primary_type


METHODS = ("AdaptiveScale12", "ExtraGlobal12")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--authorization-manifest", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise JudgeProtocolError(f"expected JSON list: {path}")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


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


def validate_inputs(args: argparse.Namespace):
    if args.workers <= 0 or args.bootstrap_samples != 10000:
        raise JudgeProtocolError("frozen judge requires positive workers and 10000 bootstrap samples")
    if (args.output_dir / "summary.json").exists():
        raise JudgeProtocolError("refusing to overwrite completed judge output")
    preflight_path = args.preflight_root / "dry_run_audit.json"
    pending_path = args.preflight_root / "pending_candidates_answer_only.jsonl"
    reuse_path = args.preflight_root / "reused_scores.jsonl"
    conflicts_path = args.preflight_root / "cache_conflicts.jsonl"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    manifest = json.loads(args.authorization_manifest.read_text(encoding="utf-8"))
    required_hashes = {
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "candidates_sha256": sha256_file(args.candidates),
        "preflight_sha256": sha256_file(preflight_path),
        "pending_sha256": sha256_file(pending_path),
        "reuse_sha256": sha256_file(reuse_path),
        "conflicts_sha256": sha256_file(conflicts_path),
        "legacy_evaluator_sha256": sha256_file(args.legacy_evaluator),
    }
    if (
        manifest.get("authorized_new_api_call_count") != 2804
        or manifest.get("automatic_retries") != 0
        or manifest.get("input_sha256") != required_hashes
    ):
        raise JudgeProtocolError("authorization manifest does not match the frozen inputs")
    if (
        preflight.get("passed") is not True
        or preflight.get("analysis_role") != "posthoc_mechanism_attribution"
        or int(preflight.get("question_count", -1)) != 4905
        or preflight.get("methods") != list(METHODS)
        or int(preflight.get("required_new_api_call_count", -1)) != 2804
        or int(preflight.get("historical_conflict_count", -1)) != 0
        or preflight.get("api_called") is not False
        or preflight.get("candidates_sha256") != required_hashes["candidates_sha256"]
        or preflight.get("pending_sha256") != required_hashes["pending_sha256"]
        or preflight.get("reuse_sha256") != required_hashes["reuse_sha256"]
        or preflight.get("conflicts_sha256") != required_hashes["conflicts_sha256"]
    ):
        raise JudgeProtocolError("preflight is not frozen or does not match authorization")

    groundtruth = load_records(args.groundtruth)
    gt_by_id = {str(row["question_id"]): row for row in groundtruth}
    candidates = load_records(args.candidates)
    candidate_by_id = {str(row["question_id"]): row for row in candidates}
    if len(gt_by_id) != 5320 or len(candidate_by_id) != 4905 or not set(candidate_by_id).issubset(gt_by_id):
        raise JudgeProtocolError("reference or candidate pools do not align")

    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    answers: dict[tuple[str, str], str] = {}
    for qid, row in candidate_by_id.items():
        values = row.get("candidates")
        hashes = row.get("candidate_sha256")
        if row.get("groundtruth_included") is not False or not isinstance(values, dict) or set(values) != set(METHODS):
            raise JudgeProtocolError(f"invalid candidate row: {qid}")
        for method in METHODS:
            answer = str(values[method]).strip()
            candidate_hash = str(hashes.get(method, ""))
            if not answer or candidate_hash != sha256_text(answer):
                raise JudgeProtocolError(f"candidate hash mismatch: {qid}:{method}")
            key = (qid, candidate_hash)
            owners[key].append(method)
            answers[key] = answer

    pending_rows = load_records(pending_path)
    reused_rows = load_records(reuse_path)
    pending = {(str(row["question_id"]), str(row["candidate_prediction_sha256"])): row for row in pending_rows}
    reused = {(str(row["question_id"]), str(row["candidate_prediction_sha256"])): row for row in reused_rows}
    if (
        len(pending) != 2804
        or len(reused) != 4911
        or set(pending) & set(reused)
        or set(pending) | set(reused) != set(owners)
    ):
        raise JudgeProtocolError("pending/reuse manifests do not partition candidate answers")
    for key, row in pending.items():
        if str(row.get("candidate_prediction", "")).strip() != answers[key] or sorted(row.get("owners", [])) != sorted(owners[key]):
            raise JudgeProtocolError(f"invalid pending manifest row: {key[0]}")
    for key, row in reused.items():
        if float(row.get("score", -1)) not in VALID_SCORES or sorted(row.get("owners", [])) != sorted(owners[key]):
            raise JudgeProtocolError(f"invalid reused score row: {key[0]}")
    return gt_by_id, candidate_by_id, owners, pending, reused, preflight


def main() -> None:
    args = parse_args()
    gt_by_id, candidate_by_id, owners, pending_manifest, reused, preflight = validate_inputs(args)
    if args.validate_only:
        print(json.dumps({
            "passed": True,
            "question_count": len(candidate_by_id),
            "new_call_count": len(pending_manifest),
            "reused_score_count": len(reused),
            "api_called": False,
        }, ensure_ascii=False, indent=2))
        return

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required")
    judge_protocol = legacy_protocol(args.legacy_evaluator)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    partial_path = args.output_dir / "api_results_partial.jsonl"
    failures_path = args.output_dir / "api_failures.jsonl"
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists():
        for row in load_records(partial_path):
            key = (str(row["question_id"]), str(row["candidate_prediction_sha256"]))
            partial[key] = row
    if not set(partial).issubset(pending_manifest):
        raise JudgeProtocolError("partial results are outside the authorized manifest")
    if partial:
        raise JudgeProtocolError("this one-shot evaluation does not allow implicit resume or retry")

    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, candidate_hash = key
        candidate = str(pending_manifest[key]["candidate_prediction"]).strip()
        reference = gt_by_id[qid]
        prompt = judge_protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=candidate,
        )
        if not hasattr(local, "client"):
            from openai import OpenAI

            local.client = OpenAI(api_key=api_key, base_url=judge_protocol["base_url"], timeout=60.0)
        response = local.client.chat.completions.create(
            model=judge_protocol["model_name"],
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
            raise JudgeProtocolError(f"unparsed judge output for {qid}")
        usage = getattr(response, "usage", None)
        return {
            "question_id": qid,
            "candidate_prediction": candidate,
            "candidate_prediction_sha256": candidate_hash,
            "owners": owners[key],
            "score": score,
            "judge_output": output,
            "judge_response_model": getattr(response, "model", None),
            "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
            "score_source": "extra_global_vs_adaptive_api",
        }

    failures = []
    with partial_path.open("a", encoding="utf-8") as handle:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(judge_one, key): key for key in sorted(pending_manifest)}
            for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                key = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    failures.append({
                        "question_id": key[0],
                        "candidate_prediction_sha256": key[1],
                        "error": repr(error),
                    })
                else:
                    partial[key] = row
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                if completed % 50 == 0 or completed == len(pending_manifest):
                    print(f"attempted={completed}/{len(pending_manifest)} succeeded={len(partial)} failures={len(failures)}", flush=True)
    if failures:
        write_jsonl(failures_path, failures)
        raise JudgeProtocolError(f"{len(failures)} authorized one-shot calls failed; no automatic retries")
    if set(partial) != set(pending_manifest):
        raise JudgeProtocolError("API results do not cover the frozen pending manifest")

    scores = {key: float(row["score"]) for key, row in reused.items()}
    scores.update({key: float(row["score"]) for key, row in partial.items()})
    expanded = []
    for qid, candidate in sorted(candidate_by_id.items()):
        reference = gt_by_id[qid]
        row = {
            "question_id": qid,
            "video_id": str(reference["video"]),
            "question_type": primary_type(reference),
        }
        for method in METHODS:
            row[f"{method}_score"] = scores[(qid, str(candidate["candidate_sha256"][method]))]
        expanded.append(row)
    write_jsonl(args.output_dir / "expanded_scores.jsonl", expanded)
    comparison = pairwise(expanded, "ExtraGlobal12_score", "AdaptiveScale12_score", args.bootstrap_samples, 2026072904)
    usage_totals = {
        key: sum(int((row.get("judge_usage") or {}).get(key) or 0) for row in partial.values())
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    summary = {
        "schema_version": "adsqa_extra_global_vs_adaptive_judge_v1",
        "analysis_role": "posthoc_mechanism_attribution",
        "not_human_gold": True,
        "authorized_initial_calls": 2804,
        "automatic_retries": 0,
        "actual_new_successful_calls": len(partial),
        "historical_exact_reuse_count": len(reused),
        "new_api_usage_totals": usage_totals,
        "judge_response_models": sorted({str(row.get("judge_response_model")) for row in partial.values()}),
        "triggered4905": {method: metrics(expanded, f"{method}_score") for method in METHODS},
        "ExtraGlobal12_vs_AdaptiveScale12": comparison,
        "exact_same_answer_count": int(preflight["exact_same_answer_count"]),
        "protocol": {
            "same_trigger_set": True,
            "same_base_frames": True,
            "same_evidence_moments": True,
            "same_visual_tokens": 3104,
            "adaptive_detail_view_type": "evidence_mid_crop",
            "control_detail_view_type": "evidence_full_highres",
        },
        "input_hashes": json.loads(args.authorization_manifest.read_text(encoding="utf-8"))["input_sha256"],
    }
    dump_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
