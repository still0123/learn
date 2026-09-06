#!/usr/bin/env python3
"""Evaluate AdsQA runs with the immutable legacy DeepSeek judge protocol."""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
from typing import Any


EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"
EXPECTED_PARSE_SCORE_SOURCE_SHA256 = "fe42aa06105c2559ca32cf6073dd738478466888e6f480edcf6a2350398c9716"
VALID_SCORES = {0.0, 0.5, 1.0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", nargs=2, metavar=("NAME", "DIR"), required=True)
    parser.add_argument("--groundtruth-file", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-workers", type=int, default=10)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument(
        "--candidate-mode",
        choices=["full_response", "answer_only"],
        default="full_response",
        help="Keep the legacy full response or diagnose only the explicit answer section",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"expected a list of objects: {path}")
    return data


def evaluator_protocol(evaluator: Path) -> dict[str, str]:
    source = evaluator.read_text(encoding="utf-8")
    tree = ast.parse(source)
    prompt = None
    parse_score_source = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "prompt_template" in targets and isinstance(node.value, ast.Constant):
                prompt = str(node.value.value)
        elif isinstance(node, ast.FunctionDef) and node.name == "parse_score":
            parse_score_source = ast.get_source_segment(source, node)

    if prompt is None or parse_score_source is None:
        raise RuntimeError(f"legacy judge protocol not found in {evaluator}")

    protocol = {
        "evaluator_sha256": sha256_bytes(source.encode("utf-8")),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "parse_score_source_sha256": sha256_bytes(parse_score_source.encode("utf-8")),
    }
    if protocol["prompt_sha256"] != EXPECTED_PROMPT_SHA256:
        raise RuntimeError("legacy DeepSeek prompt hash mismatch")
    if protocol["parse_score_source_sha256"] != EXPECTED_PARSE_SCORE_SOURCE_SHA256:
        raise RuntimeError("legacy parse_score hash mismatch")
    return protocol


def find_prediction(run_dir: Path, question_id: str) -> Path | None:
    direct = run_dir / question_id / "prediction.json"
    if direct.exists():
        return direct
    matches = sorted(run_dir.glob(f"*/{question_id}/prediction.json"))
    if len(matches) > 1:
        raise RuntimeError(f"multiple predictions for {question_id} under {run_dir}: {matches}")
    return matches[0] if matches else None


def prediction_entry(data: Any) -> dict[str, Any]:
    entry = data[0] if isinstance(data, list) and data else data
    if not isinstance(entry, dict):
        raise ValueError("prediction JSON must contain an object")
    return entry


def extract_answer_section(text: str) -> tuple[str, bool, str | None]:
    markers = ("3. [Answer]:", "[Answer]:", "3. [Answer]", "[Answer]")
    matches = [(text.find(marker), marker) for marker in markers if text.find(marker) >= 0]
    if not matches:
        return text, False, None
    position, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
    answer = text[position + len(marker):].strip()
    return (answer or text), bool(answer), marker


def prepare_scored_copy(
    source: Path,
    destination: Path,
    overwrite: bool,
    candidate_mode: str,
) -> None:
    if destination.exists() and not overwrite:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    data = json.loads(destination.read_text(encoding="utf-8"))
    entry = prediction_entry(data)
    entry["score"] = ""
    source_prediction = str(entry.get("prediction", ""))
    extraction_found = True
    extraction_marker = None
    if candidate_mode == "answer_only":
        candidate, extraction_found, extraction_marker = extract_answer_section(source_prediction)
        entry["prediction"] = candidate
    entry["_legacy_judge_candidate"] = {
        "mode": candidate_mode,
        "source_prediction_sha256": sha256_bytes(source_prediction.encode("utf-8")),
        "answer_extraction_found": extraction_found,
        "answer_extraction_marker": extraction_marker,
    }
    destination.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


def run_legacy_evaluator(
    name: str,
    evaluator: Path,
    groundtruth_file: Path,
    prediction_dir: Path,
    log_file: Path,
    max_workers: int,
) -> None:
    env = os.environ.copy()
    env.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    env.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
    command = [
        sys.executable,
        str(evaluator),
        "--pred-dir",
        str(prediction_dir),
        "--gt-file",
        str(groundtruth_file),
        "--target-file",
        "prediction.json",
        "--max-workers",
        str(max_workers),
    ]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            print(f"[{name}] {line}", end="")
        return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"legacy evaluator failed for {name}; see {log_file}")


def parse_legacy_score(content: Any) -> float | None:
    text = str(content or "")
    if "Answer: 1" in text:
        return 1.0
    if "Answer: 0.5" in text:
        return 0.5
    if "Answer: 0" in text:
        return 0.0
    repaired = re.fullmatch(r"\s*:\s*(0(?:\.0)?|0\.5|1(?:\.0)?)\s*", text)
    if repaired:
        return float(repaired.group(1))
    return None


def normalize_types(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(value) for value in raw] or ["unknown"]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw.replace("'", '"'))
        except json.JSONDecodeError:
            return [raw]
        return normalize_types(parsed)
    return ["unknown"]


def bootstrap_mean_ci(values: list[float], samples: int, seed: int = 42) -> list[float] | None:
    if not values or samples <= 0:
        return None
    rng = random.Random(seed)
    size = len(values)
    means = sorted(
        sum(values[rng.randrange(size)] for _ in range(size)) / size
        for _ in range(samples)
    )
    return [means[max(0, int(0.025 * samples) - 1)], means[min(samples - 1, int(0.975 * samples))]]


def compact_scores(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "strict": sum(value == 1.0 for value in values) / len(values) if values else 0.0,
        "relaxed": sum(values) / len(values) if values else 0.0,
        "score_counts": dict(sorted(Counter(str(value) for value in values).items())),
    }


def summarize(
    methods: list[str],
    groundtruth: list[dict[str, Any]],
    results: dict[tuple[str, str], dict[str, Any]],
    missing: dict[str, list[str]],
    bootstrap_samples: int,
) -> dict[str, Any]:
    by_id = {str(item["question_id"]): item for item in groundtruth}
    summary: dict[str, Any] = {"methods": {}, "pairwise": {}}
    for method in methods:
        records = [
            results[(method, str(item["question_id"]))]
            for item in groundtruth
            if (method, str(item["question_id"])) in results
        ]
        parsed = [record for record in records if record["score"] in VALID_SCORES]
        values = [float(record["score"]) for record in parsed]
        by_primary: defaultdict[str, list[float]] = defaultdict(list)
        by_membership: defaultdict[str, list[float]] = defaultdict(list)
        for record in parsed:
            types = normalize_types(by_id[record["question_id"]].get("question_type"))
            by_primary[types[0]].append(float(record["score"]))
            for type_name in types:
                by_membership[type_name].append(float(record["score"]))
        summary["methods"][method] = {
            "expected": len(groundtruth),
            "prediction_missing": len(missing[method]),
            "parsed": len(parsed),
            "unparsed": len(records) - len(parsed),
            "evaluated": compact_scores(values),
            "ci95": {
                "strict": bootstrap_mean_ci(
                    [1.0 if value == 1.0 else 0.0 for value in values], bootstrap_samples
                ),
                "relaxed": bootstrap_mean_ci(values, bootstrap_samples),
                "bootstrap_samples": bootstrap_samples,
                "seed": 42,
            },
            "by_primary_type": {
                key: compact_scores(items) for key, items in sorted(by_primary.items())
            },
            "by_type_membership": {
                key: compact_scores(items) for key, items in sorted(by_membership.items())
            },
        }

    for first, second in itertools.combinations(methods, 2):
        shared = []
        for item in groundtruth:
            question_id = str(item["question_id"])
            first_score = results.get((first, question_id), {}).get("score")
            second_score = results.get((second, question_id), {}).get("score")
            if first_score in VALID_SCORES and second_score in VALID_SCORES:
                shared.append((float(first_score), float(second_score)))
        deltas = [first_score - second_score for first_score, second_score in shared]
        summary["pairwise"][f"{first}__vs__{second}"] = {
            "shared": len(shared),
            "first_wins": sum(first_score > second_score for first_score, second_score in shared),
            "ties": sum(first_score == second_score for first_score, second_score in shared),
            "second_wins": sum(first_score < second_score for first_score, second_score in shared),
            "mean_score_delta_first_minus_second": sum(deltas) / len(deltas) if deltas else 0.0,
            "mean_score_delta_ci95": bootstrap_mean_ci(deltas, bootstrap_samples),
            "bootstrap_samples": bootstrap_samples,
            "seed": 42,
        }
    return summary


def main() -> None:
    args = parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    evaluator = Path(args.evaluator).resolve()
    groundtruth_file = Path(args.groundtruth_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    protocol = evaluator_protocol(evaluator)
    groundtruth = load_records(groundtruth_file)
    question_ids = [str(item["question_id"]) for item in groundtruth]
    runs = [(name, Path(path).resolve()) for name, path in args.run]

    scored_root = output_dir / "scored_predictions"
    missing: dict[str, list[str]] = {}
    for name, run_dir in runs:
        missing[name] = []
        for question_id in question_ids:
            source = find_prediction(run_dir, question_id)
            if source is None:
                missing[name].append(question_id)
                continue
            prepare_scored_copy(
                source,
                scored_root / name / question_id / "prediction.json",
                args.overwrite,
                args.candidate_mode,
            )
        run_legacy_evaluator(
            name,
            evaluator,
            groundtruth_file,
            scored_root / name,
            output_dir / "logs" / f"{name}.log",
            args.max_workers,
        )

    results: dict[tuple[str, str], dict[str, Any]] = {}
    rows = []
    for name, _ in runs:
        for question_id in question_ids:
            path = scored_root / name / question_id / "prediction.json"
            if not path.exists():
                continue
            entry = prediction_entry(json.loads(path.read_text(encoding="utf-8")))
            judge_output = entry.get("score", "")
            score = parse_legacy_score(judge_output)
            row = {
                "method": name,
                "question_id": question_id,
                "score": score,
                "judge_output": judge_output,
                "judge_response_model": (
                    entry.get("_judge_api_response", {}).get("model")
                    if isinstance(entry.get("_judge_api_response"), dict)
                    else None
                ),
                "judge_usage": (
                    entry.get("_judge_api_response", {}).get("usage")
                    if isinstance(entry.get("_judge_api_response"), dict)
                    else None
                ),
                "score_parse_repaired": bool(
                    score is not None
                    and re.fullmatch(r"\s*:\s*(0(?:\.0)?|0\.5|1(?:\.0)?)\s*", str(judge_output))
                ),
            }
            rows.append(row)
            results[(name, question_id)] = row

    methods = [name for name, _ in runs]
    summary = summarize(methods, groundtruth, results, missing, args.bootstrap_samples)
    provenance = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "judge_protocol": "legacy_evaluate_compare_new",
        "candidate_mode": args.candidate_mode,
        "adapter_score_repair": "leading-colon numeric-only outputs",
        "judge_model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "judge_response_models": dict(sorted(Counter(
            str(row["judge_response_model"] or "unknown") for row in rows
        ).items())),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "groundtruth_file": str(groundtruth_file),
        "groundtruth_sha256": sha256_bytes(groundtruth_file.read_bytes()),
        "source_runs": {name: str(path) for name, path in runs},
        **protocol,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
