#!/usr/bin/env python3
"""Paired legacy-DeepSeek judge for AdsSFTLoRA Raw8 versus MMR8."""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import re
import threading
import time
from typing import Any


RAW_METHOD = "AdsSFTLoRA_Raw8"
MMR_METHOD = "AdsSFTLoRA_MMR8"
EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"
EXPECTED_PARSE_SCORE_SOURCE_SHA256 = "fe42aa06105c2559ca32cf6073dd738478466888e6f480edcf6a2350398c9716"
VALID_SCORES = {0.0, 0.5, 1.0}


class JudgeProtocolError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--protocol-audit", type=Path, required=True)
    parser.add_argument("--baseline-oof-root", type=Path, required=True)
    parser.add_argument("--mmr-oof-root", type=Path, required=True)
    parser.add_argument("--historical-cache", type=Path, required=True)
    parser.add_argument("--legacy-evaluator", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def legacy_protocol(path: Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    prompt = None
    base_url = None
    model_name = None
    parse_source = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "prompt_template" in targets and isinstance(node.value, ast.Constant):
                prompt = str(node.value.value)
            if "BASE_URL" in targets and isinstance(node.value, ast.Constant):
                base_url = str(node.value.value)
            if "MODEL_NAME" in targets and isinstance(node.value, ast.Constant):
                model_name = str(node.value.value)
        elif isinstance(node, ast.FunctionDef) and node.name == "parse_score":
            parse_source = ast.get_source_segment(source, node)
    if not all((prompt, base_url, model_name, parse_source)):
        raise JudgeProtocolError("legacy evaluator is missing frozen judge protocol fields")
    protocol = {
        "legacy_evaluator_sha256": sha256_bytes(source.encode("utf-8")),
        "prompt_template": prompt,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "base_url": base_url,
        "model_name": model_name,
        "parse_score_source_sha256": sha256_bytes(parse_source.encode("utf-8")),
    }
    if protocol["prompt_sha256"] != EXPECTED_PROMPT_SHA256:
        raise JudgeProtocolError("legacy judge prompt hash mismatch")
    if protocol["parse_score_source_sha256"] != EXPECTED_PARSE_SCORE_SOURCE_SHA256:
        raise JudgeProtocolError("legacy judge parse_score hash mismatch")
    return protocol


def legacy_parse_score(content: Any) -> float | None:
    text = str(content or "")
    if "Answer: 1" in text:
        return 1.0
    if "Answer: 0.5" in text:
        return 0.5
    if "Answer: 0" in text:
        return 0.0
    match = re.search(r"Answer:\s*(\d+(\.\d+)?)", text)
    if match:
        value = float(match.group(1))
    else:
        repaired = re.fullmatch(r"\s*:\s*(0(?:\.0)?|0\.5|1(?:\.0)?)\s*", text)
        value = float(repaired.group(1)) if repaired else -1.0
    return value if value in VALID_SCORES else None


def extract_answer_section(text: str) -> tuple[str, bool, str | None]:
    markers = ("3. [Answer]:", "[Answer]:", "3. [Answer]", "[Answer]")
    matches = [(text.find(marker), marker) for marker in markers if text.find(marker) >= 0]
    if not matches:
        return text, False, None
    position, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
    answer = text[position + len(marker):].strip()
    return (answer or text), bool(answer), marker


def truncate_words(text: str) -> str:
    words = text.split()
    return " ".join(words[:300]) if len(words) > 300 else text


def load_groundtruth(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise JudgeProtocolError("groundtruth must be a nonempty list")
    seen: set[str] = set()
    for row in rows:
        question_id = str(row.get("question_id", ""))
        if not question_id or question_id in seen:
            raise JudgeProtocolError(f"invalid or duplicate groundtruth question ID: {question_id!r}")
        if not all(key in row for key in ("video", "question", "meta_info", "answer")):
            raise JudgeProtocolError(f"groundtruth row lacks judge context: {question_id}")
        seen.add(question_id)
    return rows


def find_prediction(root: Path, artifact_subdir: str, question_id: str) -> Path:
    direct = root / question_id / "prediction.json"
    if direct.is_file():
        return direct
    matches = sorted(root.glob(f"fold_*/{artifact_subdir}/{question_id}/prediction.json"))
    if len(matches) != 1:
        raise JudgeProtocolError(
            f"expected exactly one prediction for {question_id} under {root}/{artifact_subdir}, got {matches}"
        )
    return matches[0]


def load_predictions(root: Path, artifact_subdir: str, question_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for question_id in question_ids:
        path = find_prediction(root, artifact_subdir, question_id)
        item = json.loads(path.read_text(encoding="utf-8"))
        if str(item.get("question_id")) != question_id:
            raise JudgeProtocolError(f"prediction question ID mismatch: {path}")
        prediction = str(item.get("prediction", "")).strip()
        if not prediction:
            raise JudgeProtocolError(f"empty prediction: {path}")
        candidate, extraction_found, extraction_marker = extract_answer_section(prediction)
        rows[question_id] = {
            "prediction": truncate_words(candidate),
            "source_prediction_sha256": sha256_bytes(prediction.encode("utf-8")),
            "answer_extraction_found": extraction_found,
            "answer_extraction_marker": extraction_marker,
            "path": str(path),
        }
    return rows


def load_mmr_predictions(root: Path, question_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for question_id in question_ids:
        matches = sorted(root.glob(f"fold_*/{question_id}/prediction.json"))
        if len(matches) != 1:
            raise JudgeProtocolError(
                f"expected exactly one MMR8 prediction for {question_id}, got {matches}"
            )
        path = matches[0]
        item = json.loads(path.read_text(encoding="utf-8"))
        if str(item.get("question_id")) != question_id or item.get("method") != MMR_METHOD:
            raise JudgeProtocolError(f"MMR8 prediction identity mismatch: {path}")
        prediction = str(item.get("prediction", "")).strip()
        if not prediction:
            raise JudgeProtocolError(f"empty prediction: {path}")
        candidate, extraction_found, extraction_marker = extract_answer_section(prediction)
        rows[question_id] = {
            "prediction": truncate_words(candidate),
            "source_prediction_sha256": sha256_bytes(prediction.encode("utf-8")),
            "answer_extraction_found": extraction_found,
            "answer_extraction_marker": extraction_marker,
            "path": str(path),
        }
    return rows


def load_cache(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["question_id"]), str(row["candidate_prediction"]))
        if key in rows:
            raise JudgeProtocolError(f"duplicate cache key: {key!r}")
        if float(row.get("score", -1)) not in VALID_SCORES:
            raise JudgeProtocolError(f"invalid cached score: {key!r}")
        rows[key] = row
    return rows


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    return values[round((len(values) - 1) * fraction)]


def cluster_bootstrap_ci(rows: list[dict[str, Any]], value_key: str, samples: int, seed: int = 42) -> list[float] | None:
    by_video: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_video[str(row["video"])].append(float(row[value_key]))
    videos = sorted(by_video)
    if not videos or samples <= 0:
        return None
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(samples):
        sample: list[float] = []
        for _ in videos:
            sample.extend(by_video[videos[rng.randrange(len(videos))]])
        values.append(sum(sample) / len(sample))
    values.sort()
    return [quantile(values, 0.025), quantile(values, 0.975)]


def score_summary(rows: list[dict[str, Any]], samples: int) -> dict[str, Any]:
    scores = [float(row["score"]) for row in rows]
    strict_rows = [{**row, "strict": float(row["score"] == 1.0)} for row in rows]
    return {
        "n": len(rows),
        "strict": sum(score == 1.0 for score in scores) / len(scores),
        "relaxed": sum(scores) / len(scores),
        "score_counts": dict(sorted(Counter(str(score) for score in scores).items())),
        "video_cluster_bootstrap_ci95": {
            "strict": cluster_bootstrap_ci(strict_rows, "strict", samples),
            "relaxed": cluster_bootstrap_ci(rows, "score", samples),
            "samples": samples,
            "seed": 42,
        },
    }


def main() -> None:
    args = parse_args()
    if args.workers <= 0 or args.bootstrap_samples < 0:
        raise JudgeProtocolError("workers and bootstrap-samples are invalid")
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    audit = json.loads(args.protocol_audit.read_text(encoding="utf-8"))
    if audit.get("passed") is not True:
        raise JudgeProtocolError("OOF protocol audit did not pass")
    groundtruth = load_groundtruth(args.groundtruth)
    protocol = legacy_protocol(args.legacy_evaluator)
    question_ids = [str(row["question_id"]) for row in groundtruth]
    by_question = {str(row["question_id"]): row for row in groundtruth}
    predictions = {
        RAW_METHOD: load_predictions(args.baseline_oof_root, "lora_raw8", question_ids),
        MMR_METHOD: load_mmr_predictions(args.mmr_oof_root, question_ids),
    }
    owners: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for method, rows in predictions.items():
        for question_id, row in rows.items():
            owners[(question_id, str(row["prediction"]))].append(method)
    call_keys = sorted(owners, key=lambda value: (value[0], value[1]))
    historical_cache = load_cache(args.historical_cache)
    reusable_keys = [key for key in call_keys if key in historical_cache]
    new_call_keys = [key for key in call_keys if key not in historical_cache]
    dry_run = {
        "schema_version": "adsqa_sft_lora_mmr8_legacy_judge_dry_run_v1",
        "passed": True,
        "question_count": len(question_ids),
        "expanded_record_count": len(question_ids) * 2,
        "unique_judge_request_count": len(call_keys),
        "historical_cache_reuse_count": len(reusable_keys),
        "required_new_api_call_count": len(new_call_keys),
        "cross_method_duplicate_record_count": sum(max(0, len(value) - 1) for value in owners.values()),
        "candidate_mode": "answer_only",
        "legacy_evaluator_sha256": protocol["legacy_evaluator_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "parse_score_source_sha256": protocol["parse_score_source_sha256"],
        "oof_protocol_audit_sha256": sha256_file(args.protocol_audit),
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "historical_cache_sha256": sha256_file(args.historical_cache),
        "contains_api_key": False,
        "not_human_gold": True,
    }
    (output_root / "dry_run_audit.json").write_text(
        json.dumps(dry_run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(dry_run, ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise JudgeProtocolError("DEEPSEEK_API_KEY is required for the actual judge")
    results_path = output_root / "results.jsonl"
    partial_path = output_root / "api_results_partial.jsonl"
    failures_path = output_root / "api_failures.jsonl"
    if results_path.exists():
        raise JudgeProtocolError(f"refusing to overwrite final results: {results_path}")
    partial: dict[tuple[str, str], dict[str, Any]] = {}
    if partial_path.exists():
        for line in partial_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                partial[(str(row["question_id"]), str(row["candidate_prediction"]))] = row
    cached_to_append: list[dict[str, Any]] = []
    for key in reusable_keys:
        if key not in partial:
            row = {**historical_cache[key], "cache_source": "historical_exact_candidate"}
            partial[key] = row
            cached_to_append.append(row)
    if cached_to_append:
        with partial_path.open("a", encoding="utf-8") as handle:
            for row in cached_to_append:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    from openai import OpenAI

    local = threading.local()

    def judge_one(key: tuple[str, str]) -> dict[str, Any]:
        question_id, candidate_prediction = key
        reference = by_question[question_id]
        prompt = protocol["prompt_template"].format(
            meta_info=reference["meta_info"],
            question=reference["question"],
            golden_answer=reference["answer"],
            response=candidate_prediction,
        )
        if not hasattr(local, "client"):
            local.client = OpenAI(api_key=api_key, base_url=protocol["base_url"], timeout=60.0)
        last_error = ""
        for attempt in range(3):
            try:
                completion = local.client.chat.completions.create(
                    model=protocol["model_name"],
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=20,
                )
                output = str(completion.choices[0].message.content)
                score = legacy_parse_score(output)
                if score not in VALID_SCORES:
                    raise JudgeProtocolError(f"unparsed legacy judge output for {question_id}: {output!r}")
                usage = getattr(completion, "usage", None)
                return {
                    "question_id": question_id,
                    "candidate_prediction": candidate_prediction,
                    "candidate_prediction_sha256": sha256_bytes(candidate_prediction.encode("utf-8")),
                    "score": score,
                    "judge_output": output,
                    "judge_response_model": getattr(completion, "model", None),
                    "judge_usage": usage.model_dump() if hasattr(usage, "model_dump") else None,
                }
            except Exception as error:
                last_error = repr(error)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        raise JudgeProtocolError(f"judge failed after retries for {question_id}: {last_error}")

    pending = [key for key in call_keys if key not in partial]
    if pending:
        with partial_path.open("a", encoding="utf-8") as handle:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(judge_one, key): key for key in pending}
                for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                    key = futures[future]
                    try:
                        row = future.result()
                    except Exception as error:
                        with failures_path.open("a", encoding="utf-8") as failure_handle:
                            failure_handle.write(json.dumps({
                                "question_id": key[0],
                                "candidate_prediction_sha256": sha256_bytes(key[1].encode("utf-8")),
                                "error": repr(error),
                            }, ensure_ascii=False) + "\n")
                        raise
                    row["cache_source"] = "new_api_call"
                    partial[key] = row
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                    if completed % 25 == 0 or completed == len(pending):
                        print(f"judged={completed}/{len(pending)}", flush=True)
    if set(partial) != set(call_keys):
        raise JudgeProtocolError("partial cache does not cover all unique judge requests")

    expanded: list[dict[str, Any]] = []
    for method in (RAW_METHOD, MMR_METHOD):
        for question_id in question_ids:
            candidate = predictions[method][question_id]
            source = partial[(question_id, candidate["prediction"])]
            expanded.append({
                "method": method,
                "question_id": question_id,
                "video": str(by_question[question_id]["video"]),
                "score": source["score"],
                "judge_output": source["judge_output"],
                "judge_response_model": source["judge_response_model"],
                "judge_usage": source["judge_usage"],
                "candidate_prediction_sha256": source["candidate_prediction_sha256"],
                "source_prediction_sha256": candidate["source_prediction_sha256"],
                "answer_extraction_found": candidate["answer_extraction_found"],
                "answer_extraction_marker": candidate["answer_extraction_marker"],
                "cache_source": source.get("cache_source", "historical_exact_candidate"),
            })
    with results_path.open("w", encoding="utf-8") as handle:
        for row in expanded:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    by_method: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    by_pair: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in expanded:
        by_method[row["method"]].append(row)
        by_pair[row["question_id"]][row["method"]] = row
    pair_rows: list[dict[str, Any]] = []
    for question_id in question_ids:
        raw = by_pair[question_id][RAW_METHOD]
        mmr = by_pair[question_id][MMR_METHOD]
        pair_rows.append({
            "question_id": question_id,
            "video": raw["video"],
            "relaxed_delta_mmr_minus_raw": float(mmr["score"]) - float(raw["score"]),
            "strict_delta_mmr_minus_raw": float(mmr["score"] == 1.0) - float(raw["score"] == 1.0),
        })
    relaxed_deltas = [row["relaxed_delta_mmr_minus_raw"] for row in pair_rows]
    strict_deltas = [row["strict_delta_mmr_minus_raw"] for row in pair_rows]
    relaxed_wins = sum(value > 0 for value in relaxed_deltas)
    relaxed_losses = sum(value < 0 for value in relaxed_deltas)
    summary = {
        "schema_version": "adsqa_sft_lora_mmr8_legacy_judge_summary_v1",
        "not_human_gold": True,
        "methods": {
            method: score_summary(by_method[method], args.bootstrap_samples)
            for method in (RAW_METHOD, MMR_METHOD)
        },
        "pairwise": {
            "AdsSFTLoRA_MMR8__vs__AdsSFTLoRA_Raw8": {
                "shared": len(pair_rows),
                "mmr_wins": relaxed_wins,
                "ties": sum(value == 0 for value in relaxed_deltas),
                "raw_wins": relaxed_losses,
                "correction_precision": (
                    relaxed_wins / (relaxed_wins + relaxed_losses)
                    if relaxed_wins + relaxed_losses else None
                ),
                "mean_relaxed_delta_mmr_minus_raw": sum(relaxed_deltas) / len(relaxed_deltas),
                "mean_strict_delta_mmr_minus_raw": sum(strict_deltas) / len(strict_deltas),
                "video_cluster_count": len({row["video"] for row in pair_rows}),
                "video_cluster_bootstrap_ci95": {
                    "relaxed_delta": cluster_bootstrap_ci(
                        pair_rows, "relaxed_delta_mmr_minus_raw", args.bootstrap_samples
                    ),
                    "strict_delta": cluster_bootstrap_ci(
                        pair_rows, "strict_delta_mmr_minus_raw", args.bootstrap_samples
                    ),
                    "samples": args.bootstrap_samples,
                    "seed": 42,
                },
            }
        },
        "judge_execution": {
            "historical_cache_reuse_count": len(reusable_keys),
            "new_api_call_count": len(new_call_keys),
            "failure_count": (
                sum(1 for line in failures_path.read_text(encoding="utf-8").splitlines() if line.strip())
                if failures_path.exists() else 0
            ),
        },
        "protocol": dry_run,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
