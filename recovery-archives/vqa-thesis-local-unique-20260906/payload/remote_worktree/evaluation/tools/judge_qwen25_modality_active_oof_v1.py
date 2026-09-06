#!/usr/bin/env python3
"""Judge Raw40, CLIPCrop40, and effective modality-active AVCrop40 outputs."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from typing import Any, Mapping


METHOD_RAW = "B_Raw40"
METHOD_CLIP = "D_CLIPCrop40"
METHOD_AV = "E_ModalityActiveAVCrop40"
METHODS = (METHOD_RAW, METHOD_CLIP, METHOD_AV)
EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"
OLD_METHODS = (
    "A_Raw32",
    "B_Raw40",
    "C_Gated_RandomCrop8",
    "D_Gated_CLIPCrop8",
    "E_Gated_AVCrop8",
)


class JudgeProtocolError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--gate-manifest", required=True)
    parser.add_argument("--raw40-root", required=True)
    parser.add_argument("--clip-root", required=True)
    parser.add_argument("--av-active-root", required=True)
    parser.add_argument("--old-run-root", required=True)
    parser.add_argument("--old-judge-results", required=True)
    parser.add_argument("--legacy-evaluator", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_predictions(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in root.rglob("prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        question_id = str(row["question_id"])
        prediction = str(row.get("prediction", "")).strip()
        if not prediction:
            raise JudgeProtocolError(f"empty prediction for {question_id} under {root}")
        if question_id in rows:
            raise JudgeProtocolError(f"duplicate prediction for {question_id} under {root}")
        rows[question_id] = {**row, "prediction": prediction, "source_path": str(path)}
    return rows


def extract_legacy_constants(path: Path, include_key: bool) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"prompt_template", "BASE_URL", "MODEL_NAME"}
    if include_key:
        wanted.add("API_KEY")
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if name in wanted and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values[name] = node.value.value
    if set(values) != wanted:
        raise JudgeProtocolError(f"legacy evaluator is missing constants: {sorted(wanted - set(values))}")
    return values


def parse_score(content: str) -> tuple[float | None, bool]:
    normalized = str(content).strip()
    match = re.search(r"Answer\s*:\s*(1(?:\.0)?|0\.5|0(?:\.0)?)\b", normalized, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"^\s*:\s*(1(?:\.0)?|0\.5|0(?:\.0)?)\s*$", normalized)
        if not match:
            return None, False
        return float(match.group(1)), True
    return float(match.group(1)), False


def truncated_prediction(prediction: str) -> str:
    words = prediction.split()
    return " ".join(words[:300]) if len(words) > 300 else prediction


def usage_dict(completion: Any) -> dict[str, Any] | None:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def prediction_key(question_id: str, prediction: str) -> tuple[str, str]:
    return question_id, prediction


def load_old_score_cache(old_results_path: Path, old_run_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    predictions = {
        method: load_predictions(old_run_root / "groupcv5/inference" / method)
        for method in OLD_METHODS
    }
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    for row in load_jsonl(old_results_path):
        method = str(row["method"])
        question_id = str(row["question_id"])
        if method not in predictions or question_id not in predictions[method]:
            raise JudgeProtocolError(f"old result cannot be traced to prediction: {method}/{question_id}")
        key = prediction_key(question_id, predictions[method][question_id]["prediction"])
        candidate = {
            "score": float(row["score"]),
            "judge_output": row.get("judge_output"),
            "judge_response_model": row.get("judge_response_model"),
            "judge_usage": row.get("judge_usage"),
            "score_parse_repaired": bool(row.get("score_parse_repaired", False)),
            "source_method": method,
        }
        if key in cache and cache[key]["score"] != candidate["score"]:
            raise JudgeProtocolError(f"conflicting old scores for exact prediction: {question_id}")
        cache.setdefault(key, candidate)
    return cache


def make_effective_predictions(
    gate_rows: Mapping[str, Mapping[str, Any]],
    raw_rows: Mapping[str, Mapping[str, Any]],
    clip_rows: Mapping[str, Mapping[str, Any]],
    av_active_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    expected_ids = set(gate_rows)
    if len(expected_ids) != 500 or set(raw_rows) != expected_ids or set(clip_rows) != expected_ids:
        raise JudgeProtocolError("Raw40, CLIPCrop40, and gate manifest must contain the same 500 questions")
    active_ids = {question_id for question_id, row in gate_rows.items() if row["gate_decision"]["modality_active"]}
    if set(av_active_rows) != active_ids:
        raise JudgeProtocolError("AV active outputs do not exactly match the frozen active question set")
    effective_av = {
        question_id: (av_active_rows[question_id] if question_id in active_ids else clip_rows[question_id])
        for question_id in expected_ids
    }
    return {METHOD_RAW: dict(raw_rows), METHOD_CLIP: dict(clip_rows), METHOD_AV: effective_av}


def result_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    by_method: dict[str, Any] = {}
    for method in METHODS:
        scores = [float(row["score"]) for row in rows if row["method"] == method]
        by_method[method] = {
            "n": len(scores),
            "strict": sum(score == 1.0 for score in scores) / len(scores),
            "relaxed": sum(scores) / len(scores),
            "score_counts": dict(sorted(Counter(str(score) for score in scores).items())),
        }
    pairwise: dict[str, Any] = {}
    score_map = {(str(row["method"]), str(row["question_id"])): float(row["score"]) for row in rows}
    for first, second in ((METHOD_RAW, METHOD_CLIP), (METHOD_RAW, METHOD_AV), (METHOD_CLIP, METHOD_AV)):
        deltas = [score_map[(first, str(index))] - score_map[(second, str(index))] for index in range(1, 501)]
        pairwise[f"{first}__vs__{second}"] = {
            "shared": len(deltas),
            "first_wins": sum(delta > 0 for delta in deltas),
            "ties": sum(delta == 0 for delta in deltas),
            "second_wins": sum(delta < 0 for delta in deltas),
            "mean_score_delta_first_minus_second": sum(deltas) / len(deltas),
        }
    return {"methods": by_method, "pairwise": pairwise}


def main() -> None:
    args = parse_args()
    groundtruth_path = Path(args.groundtruth).resolve()
    gate_path = Path(args.gate_manifest).resolve()
    old_results_path = Path(args.old_judge_results).resolve()
    old_run_root = Path(args.old_run_root).resolve()
    evaluator_path = Path(args.legacy_evaluator).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    legacy = extract_legacy_constants(evaluator_path, include_key=not args.dry_run)
    prompt_template = legacy["prompt_template"]
    if sha256_text(prompt_template) != EXPECTED_PROMPT_SHA256:
        raise JudgeProtocolError("legacy judge prompt hash does not match the frozen OOF protocol")
    groundtruth = {str(row["question_id"]): row for row in json.loads(groundtruth_path.read_text(encoding="utf-8"))}
    gates = {str(row["question_id"]): row for row in load_jsonl(gate_path)}
    method_predictions = make_effective_predictions(
        gates,
        load_predictions(Path(args.raw40_root).resolve()),
        load_predictions(Path(args.clip_root).resolve()),
        load_predictions(Path(args.av_active_root).resolve()),
    )
    if set(groundtruth) != set(gates):
        raise JudgeProtocolError("groundtruth and OOF question IDs differ")
    old_cache = load_old_score_cache(old_results_path, old_run_root)

    owners: dict[tuple[str, str], list[str]] = {}
    reused: dict[tuple[str, str], dict[str, Any]] = {}
    for method, rows in method_predictions.items():
        for question_id, row in rows.items():
            key = prediction_key(question_id, row["prediction"])
            owners.setdefault(key, []).append(method)
            if key in old_cache:
                reused[key] = old_cache[key]
    api_keys = sorted(set(owners) - set(reused), key=lambda item: (int(item[0]), item[1]))
    audit = {
        "schema_version": "qwen25_modality_active_judge_dry_run_v1",
        "passed": len(owners) == len(reused) + len(api_keys),
        "expanded_record_count": sum(len(methods) for methods in owners.values()),
        "unique_question_prediction_count": len(owners),
        "old_exact_score_reuse_count": len(reused),
        "required_api_call_count": len(api_keys),
        "cross_method_duplicate_record_count": sum(max(0, len(methods) - 1) for methods in owners.values()),
        "method_exact_old_reuse_counts": {
            method: sum(
                prediction_key(question_id, row["prediction"]) in reused
                for question_id, row in method_predictions[method].items()
            )
            for method in METHODS
        },
        "active_question_count": sum(row["gate_decision"]["modality_active"] for row in gates.values()),
        "fallback_question_count": sum(not row["gate_decision"]["modality_active"] for row in gates.values()),
        "prompt_sha256": sha256_text(prompt_template),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "gate_manifest_sha256": sha256_file(gate_path),
        "old_judge_results_sha256": sha256_file(old_results_path),
        "contains_api_key": False,
    }
    dry_run_path = output_root / "dry_run_audit.json"
    dry_run_path.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if args.dry_run:
        return

    results_path = output_root / "results.jsonl"
    if results_path.exists() and not args.overwrite:
        raise JudgeProtocolError(f"final results already exist: {results_path}")
    partial_path = output_root / "api_results_partial.jsonl"
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists() and not args.overwrite:
        for row in load_jsonl(partial_path):
            partial[(str(row["question_id"]), str(row["prediction"]))] = row
    elif args.overwrite and partial_path.exists():
        partial_path.unlink()

    from openai import OpenAI

    thread_local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        question_id, prediction = key
        gt = groundtruth[question_id]
        raw_gold = gt.get("answer", gt.get("gt_answer", gt.get("answers")))
        golden_answer = "; ".join(str(value) for value in raw_gold) if isinstance(raw_gold, list) else str(raw_gold)
        prompt = prompt_template.format(
            meta_info=gt.get("meta_info", ""),
            question=gt.get("question", ""),
            golden_answer=golden_answer,
            response=truncated_prediction(prediction),
        )
        if not hasattr(thread_local, "client"):
            thread_local.client = OpenAI(api_key=legacy["API_KEY"], base_url=legacy["BASE_URL"], timeout=60.0)
        last_error = ""
        for attempt in range(3):
            try:
                completion = thread_local.client.chat.completions.create(
                    model=legacy["MODEL_NAME"],
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=20,
                )
                content = str(completion.choices[0].message.content)
                score, repaired = parse_score(content)
                if score not in {0.0, 0.5, 1.0}:
                    raise JudgeProtocolError(f"unparsed judge output for {question_id}: {content!r}")
                return {
                    "question_id": question_id,
                    "prediction": prediction,
                    "prediction_sha256": sha256_text(prediction),
                    "score": score,
                    "judge_output": content,
                    "judge_response_model": getattr(completion, "model", None),
                    "judge_usage": usage_dict(completion),
                    "score_parse_repaired": repaired,
                }
            except Exception as exc:
                last_error = repr(exc)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise JudgeProtocolError(f"judge failed after retries for {question_id}: {last_error}")

    pending_keys = [key for key in api_keys if key not in partial]
    if pending_keys:
        with partial_path.open("a", encoding="utf-8") as handle:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                future_map = {executor.submit(judge_one, key): key for key in pending_keys}
                for completed, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
                    row = future.result()
                    key = future_map[future]
                    partial[key] = row
                    handle.write(json.dumps(row, ensure_ascii=True) + "\n")
                    handle.flush()
                    if completed % 25 == 0:
                        print(f"judged={completed}/{len(pending_keys)}", flush=True)
    if set(partial) != set(api_keys):
        raise JudgeProtocolError("partial API results do not exactly cover required calls")

    expanded = []
    first_owner: dict[tuple[str, str], str] = {}
    for method in METHODS:
        for question_id in sorted(method_predictions[method], key=int):
            prediction = method_predictions[method][question_id]["prediction"]
            key = prediction_key(question_id, prediction)
            first_owner.setdefault(key, method)
            if key in reused:
                source = reused[key]
                score_source_method = source["source_method"]
                reused_flag = True
            else:
                source = partial[key]
                score_source_method = first_owner[key]
                reused_flag = method != first_owner[key]
            expanded.append(
                {
                    "method": method,
                    "question_id": question_id,
                    "score": float(source["score"]),
                    "judge_output": source.get("judge_output"),
                    "judge_response_model": source.get("judge_response_model"),
                    "judge_usage": source.get("judge_usage"),
                    "score_parse_repaired": bool(source.get("score_parse_repaired", False)),
                    "score_reused_for_identical_prediction": reused_flag,
                    "score_source_method": score_source_method,
                    "prediction_sha256": sha256_text(prediction),
                }
            )
    temporary = results_path.with_suffix(".jsonl.tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in expanded), encoding="utf-8")
    temporary.replace(results_path)
    summary = result_summary(expanded)
    (output_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "schema_version": "qwen25_modality_active_deduplicated_judge_provenance_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "judge_protocol": "legacy_evaluate_compare_new",
        "candidate_mode": "answer_only",
        "judge_model": legacy["MODEL_NAME"],
        "base_url": legacy["BASE_URL"],
        "prompt_sha256": sha256_text(prompt_template),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "gate_manifest_sha256": sha256_file(gate_path),
        "legacy_evaluator_sha256": sha256_file(evaluator_path),
        "old_judge_results_sha256": sha256_file(old_results_path),
        "deduplication_policy": "reuse only for exact question_id and full prediction text",
        "required_api_call_count": len(api_keys),
        "expanded_record_count": len(expanded),
        "results_sha256": sha256_file(results_path),
        "contains_api_key": False,
    }
    (output_root / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "provenance": provenance}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
