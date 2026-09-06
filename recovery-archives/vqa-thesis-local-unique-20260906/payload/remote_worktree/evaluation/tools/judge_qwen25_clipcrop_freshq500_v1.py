#!/usr/bin/env python3
"""Run the frozen answer-only judge for FreshQ-500 Raw40 and CLIPCrop40."""

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
METHOD_CROP = "D_CLIPCrop40"
METHODS = (METHOD_RAW, METHOD_CROP)
EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"


class JudgeProtocolError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", required=True)
    parser.add_argument("--protocol-audit", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--crop-root", required=True)
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
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_predictions(root: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    for path in root.rglob("prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row["question_id"])
        prediction = str(row.get("prediction", "")).strip()
        if not prediction:
            raise JudgeProtocolError(f"empty prediction for {qid} under {root}")
        if qid in rows:
            raise JudgeProtocolError(f"duplicate prediction for {qid} under {root}")
        rows[qid] = {**row, "prediction": prediction}
    return rows


def extract_legacy_constants(path: Path, include_key: bool) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    wanted = {"prompt_template", "BASE_URL", "MODEL_NAME"}
    if include_key:
        wanted.add("API_KEY")
    values = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in wanted:
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values[target.id] = node.value.value
    if set(values) != wanted:
        raise JudgeProtocolError(f"legacy evaluator is missing constants: {sorted(wanted - set(values))}")
    return values


def parse_score(content: str) -> tuple[float | None, bool]:
    normalized = str(content).strip()
    match = re.search(
        r"Answer\s*:\s*(1(?:\.0)?|0\.5|0(?:\.0)?)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        return float(match.group(1)), False
    repaired = re.search(r"^\s*:\s*(1(?:\.0)?|0\.5|0(?:\.0)?)\s*$", normalized)
    return (float(repaired.group(1)), True) if repaired else (None, False)


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


def result_summary(rows: list[Mapping[str, Any]], question_ids: list[str]) -> dict[str, Any]:
    methods = {}
    score_map = {
        (str(row["method"]), str(row["question_id"])): float(row["score"])
        for row in rows
    }
    for method in METHODS:
        scores = [score_map[(method, qid)] for qid in question_ids]
        methods[method] = {
            "n": len(scores),
            "strict": sum(score == 1.0 for score in scores) / len(scores),
            "relaxed": sum(scores) / len(scores),
            "score_counts": dict(sorted(Counter(str(score) for score in scores).items())),
        }
    deltas = [score_map[(METHOD_CROP, qid)] - score_map[(METHOD_RAW, qid)] for qid in question_ids]
    return {
        "methods": methods,
        "pairwise": {
            "D_CLIPCrop40__vs__B_Raw40": {
                "shared": len(deltas),
                "crop_wins": sum(delta > 0 for delta in deltas),
                "ties": sum(delta == 0 for delta in deltas),
                "raw_wins": sum(delta < 0 for delta in deltas),
                "mean_score_delta_crop_minus_raw": sum(deltas) / len(deltas),
            }
        },
    }


def main() -> None:
    args = parse_args()
    groundtruth_path = Path(args.groundtruth).resolve()
    protocol_audit_path = Path(args.protocol_audit).resolve()
    evaluator_path = Path(args.legacy_evaluator).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    protocol_audit = json.loads(protocol_audit_path.read_text(encoding="utf-8"))
    if protocol_audit.get("passed") is not True:
        raise JudgeProtocolError("formal visual protocol audit did not pass")

    legacy = extract_legacy_constants(evaluator_path, include_key=not args.dry_run)
    prompt_template = legacy["prompt_template"]
    if sha256_text(prompt_template) != EXPECTED_PROMPT_SHA256:
        raise JudgeProtocolError("judge prompt hash differs from the frozen protocol")
    groundtruth_rows = json.loads(groundtruth_path.read_text(encoding="utf-8"))
    groundtruth = {str(row["question_id"]): row for row in groundtruth_rows}
    if len(groundtruth) != 500:
        raise JudgeProtocolError("FreshQ groundtruth must contain 500 unique questions")
    method_predictions = {
        METHOD_RAW: load_predictions(Path(args.raw_root).resolve()),
        METHOD_CROP: load_predictions(Path(args.crop_root).resolve()),
    }
    if any(set(rows) != set(groundtruth) for rows in method_predictions.values()):
        raise JudgeProtocolError("prediction and groundtruth question IDs differ")

    owners: dict[tuple[str, str], list[str]] = {}
    for method, rows in method_predictions.items():
        for qid, row in rows.items():
            owners.setdefault((qid, row["prediction"]), []).append(method)
    api_keys = sorted(owners, key=lambda item: (item[0], item[1]))
    audit = {
        "schema_version": "qwen25_clipcrop_freshq500_judge_dry_run_v1",
        "passed": sum(len(methods) for methods in owners.values()) == 1000,
        "expanded_record_count": 1000,
        "unique_question_prediction_count": len(owners),
        "required_api_call_count": len(api_keys),
        "cross_method_duplicate_record_count": sum(
            max(0, len(methods) - 1) for methods in owners.values()
        ),
        "prompt_sha256": sha256_text(prompt_template),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "protocol_audit_sha256": sha256_file(protocol_audit_path),
        "contains_api_key": False,
    }
    (output_root / "dry_run_audit.json").write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if args.dry_run:
        return

    results_path = output_root / "results.jsonl"
    if results_path.exists() and not args.overwrite:
        raise JudgeProtocolError(f"final judge results already exist: {results_path}")
    partial_path = output_root / "api_results_partial.jsonl"
    partial = {}
    if partial_path.exists() and not args.overwrite:
        for row in load_jsonl(partial_path):
            partial[(str(row["question_id"]), str(row["prediction"]))] = row
    elif args.overwrite and partial_path.exists():
        partial_path.unlink()

    from openai import OpenAI

    thread_local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        qid, prediction = key
        gt = groundtruth[qid]
        raw_gold = gt.get("answer", gt.get("gt_answer", gt.get("answers")))
        golden = "; ".join(str(value) for value in raw_gold) if isinstance(raw_gold, list) else str(raw_gold)
        prompt = prompt_template.format(
            meta_info=gt.get("meta_info", ""),
            question=gt.get("question", ""),
            golden_answer=golden,
            response=truncated_prediction(prediction),
        )
        if not hasattr(thread_local, "client"):
            thread_local.client = OpenAI(
                api_key=legacy["API_KEY"],
                base_url=legacy["BASE_URL"],
                timeout=60.0,
            )
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
                    raise JudgeProtocolError(f"unparsed judge output for {qid}: {content!r}")
                return {
                    "question_id": qid,
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
        raise JudgeProtocolError(f"judge failed after retries for {qid}: {last_error}")

    pending = [key for key in api_keys if key not in partial]
    if pending:
        with partial_path.open("a", encoding="utf-8") as handle:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(judge_one, key): key for key in pending}
                for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                    row = future.result()
                    key = futures[future]
                    partial[key] = row
                    handle.write(json.dumps(row, ensure_ascii=True) + "\n")
                    handle.flush()
                    if completed % 25 == 0:
                        print(f"judged={completed}/{len(pending)}", flush=True)
    if set(partial) != set(api_keys):
        raise JudgeProtocolError("partial judge cache does not cover all unique predictions")

    expanded = []
    first_owner = {}
    question_ids = sorted(groundtruth)
    for method in METHODS:
        for qid in question_ids:
            prediction = method_predictions[method][qid]["prediction"]
            key = (qid, prediction)
            first_owner.setdefault(key, method)
            source = partial[key]
            expanded.append(
                {
                    "method": method,
                    "question_id": qid,
                    "score": float(source["score"]),
                    "judge_output": source.get("judge_output"),
                    "judge_response_model": source.get("judge_response_model"),
                    "judge_usage": source.get("judge_usage"),
                    "score_parse_repaired": bool(source.get("score_parse_repaired", False)),
                    "score_reused_for_identical_prediction": method != first_owner[key],
                    "score_source_method": first_owner[key],
                    "prediction_sha256": sha256_text(prediction),
                }
            )
    temporary = results_path.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in expanded),
        encoding="utf-8",
    )
    temporary.replace(results_path)
    summary = result_summary(expanded, question_ids)
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    provenance = {
        "schema_version": "qwen25_clipcrop_freshq500_judge_provenance_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "judge_protocol": "legacy_evaluate_compare_new",
        "candidate_mode": "answer_only",
        "judge_model": legacy["MODEL_NAME"],
        "base_url": legacy["BASE_URL"],
        "prompt_sha256": sha256_text(prompt_template),
        "groundtruth_sha256": sha256_file(groundtruth_path),
        "protocol_audit_sha256": sha256_file(protocol_audit_path),
        "legacy_evaluator_sha256": sha256_file(evaluator_path),
        "deduplication_policy": "judge each unique question_id and full prediction once",
        "required_api_call_count": len(api_keys),
        "expanded_record_count": len(expanded),
        "results_sha256": sha256_file(results_path),
        "contains_api_key": False,
    }
    (output_root / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"summary": summary, "provenance": provenance}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
