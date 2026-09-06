#!/usr/bin/env python3
"""Align 512-token-budget LoRA MMR8 predictions to frozen judge caches."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"
EXPECTED_METHOD = "AdsSFTLoRA_MMR8_512"
EXPECTED_QUESTIONS = 500
EXPECTED_FOLDS = 5
EXPECTED_VIEWS = 8
EXPECTED_VISUAL_TOKENS = 1296
VALID_SCORES = {0.0, 0.5, 1.0}


class PreflightError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mmr512-run", type=Path, required=True)
    parser.add_argument("--mmr448-run", type=Path, required=True)
    parser.add_argument("--clean-mmr512-root", type=Path, required=True)
    parser.add_argument(
        "--historical-judge-root", type=Path, action="append", required=True
    )
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def extract_answer_section(text: str) -> tuple[str, str | None]:
    markers = (
        "3. [Answer]:",
        "[Answer]:",
        "3. [Answer]",
        "[Answer]",
        "<answer>",
    )
    matches = [(text.find(marker), marker) for marker in markers if marker in text]
    if not matches:
        return text, None
    position, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
    answer = text[position + len(marker) :]
    if marker == "<answer>" and "</answer>" in answer:
        answer = answer.split("</answer>", 1)[0]
    answer = answer.strip()
    return (answer or text), marker if answer else None


def normalized_prediction(path: Path) -> tuple[str, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    prediction = str(payload.get("prediction", "")).strip()
    if not prediction:
        raise PreflightError(f"empty prediction: {path}")
    candidate, marker = extract_answer_section(prediction)
    words = candidate.split()
    if len(words) > 300:
        candidate = " ".join(words[:300])
    return candidate, marker


def load_fold_predictions(
    root: Path,
    fold_prefix: str,
    expected_method: str | None = None,
    audit_visual_protocol: bool = False,
) -> dict[str, str]:
    rows: dict[str, str] = {}
    for fold in range(EXPECTED_FOLDS):
        fold_root = root / f"{fold_prefix}{fold}"
        paths = sorted(fold_root.glob("*/prediction.json"))
        if len(paths) != 100:
            raise PreflightError(
                f"expected 100 predictions in {fold_root}, got {len(paths)}"
            )
        if audit_visual_protocol:
            audit = json.loads(
                (fold_root / "protocol_audit.json").read_text(encoding="utf-8")
            )
            if (
                audit.get("passed") is not True
                or audit.get("completed_count") != 100
                or audit.get("expected_visual_tokens") != EXPECTED_VISUAL_TOKENS
                or audit.get("visual_token_range")
                != [EXPECTED_VISUAL_TOKENS, EXPECTED_VISUAL_TOKENS]
            ):
                raise PreflightError(f"visual protocol audit failed: {fold_root}")
        for path in paths:
            question_id = path.parent.name
            payload = json.loads(path.read_text(encoding="utf-8"))
            if str(payload.get("question_id")) != question_id:
                raise PreflightError(f"question ID mismatch: {path}")
            if expected_method and payload.get("method") != expected_method:
                raise PreflightError(f"method mismatch: {path}")
            if question_id in rows:
                raise PreflightError(f"duplicate question ID: {question_id}")
            rows[question_id] = normalized_prediction(path)[0]
    if len(rows) != EXPECTED_QUESTIONS:
        raise PreflightError(f"expected 500 predictions, got {len(rows)}")
    return rows


def load_judge_cache(
    roots: list[Path],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, int]]:
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    source_counts: dict[str, int] = {}
    for root in roots:
        dry_run_path = root / "dry_run_audit.json"
        partial_path = root / "api_results_partial.jsonl"
        if not dry_run_path.is_file() or not partial_path.is_file():
            raise PreflightError(f"incomplete historical judge root: {root}")
        dry_run = json.loads(dry_run_path.read_text(encoding="utf-8"))
        if dry_run.get("prompt_sha256") != EXPECTED_PROMPT_SHA256:
            raise PreflightError(f"judge prompt mismatch: {root}")
        count = 0
        for line in partial_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (
                str(row.get("question_id", "")),
                str(row.get("candidate_prediction", "")),
            )
            score = float(row.get("score", -1))
            if not all(key) or score not in VALID_SCORES:
                raise PreflightError(f"invalid cache row in {partial_path}")
            if key in cache and float(cache[key]["score"]) != score:
                raise PreflightError(
                    f"conflicting exact-cache scores for question {key[0]}"
                )
            cache.setdefault(key, row)
            count += 1
        source_counts[str(root)] = count
    return cache, source_counts


def main() -> None:
    args = parse_args()
    run = args.mmr512_run.resolve()
    if not (run / "INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION").is_file():
        raise PreflightError("512 inference completion marker is missing")
    protocol = json.loads((run / "protocol_audit.json").read_text(encoding="utf-8"))
    if (
        protocol.get("passed") is not True
        or protocol.get("question_count") != EXPECTED_QUESTIONS
        or protocol.get("method") != EXPECTED_METHOD
        or protocol.get("views") != EXPECTED_VIEWS
        or protocol.get("visual_tokens") != EXPECTED_VISUAL_TOKENS
        or protocol.get("groundtruth_read") is not False
        or protocol.get("judge_scores_read") is not False
    ):
        raise PreflightError("512 run-level protocol audit failed")

    mmr512 = load_fold_predictions(
        run / "oof500",
        "fold_",
        expected_method=EXPECTED_METHOD,
        audit_visual_protocol=True,
    )
    mmr448 = load_fold_predictions(args.mmr448_run.resolve() / "oof500", "fold_")
    clean512 = load_fold_predictions(
        args.clean_mmr512_root.resolve() / "a0_mmr8", "fold_"
    )
    cache, source_counts = load_judge_cache(
        [path.resolve() for path in args.historical_judge_root]
    )

    reuse = 0
    pending: list[dict[str, str]] = []
    extraction_counts: Counter[str] = Counter()
    candidate_hash_rows: list[str] = []
    for fold in range(EXPECTED_FOLDS):
        for path in sorted((run / "oof500" / f"fold_{fold}").glob("*/prediction.json")):
            question_id = path.parent.name
            candidate, marker = normalized_prediction(path)
            extraction_counts[marker or "full_response"] += 1
            candidate_hash = sha256_bytes(candidate.encode("utf-8"))
            candidate_hash_rows.append(f"{question_id}\t{candidate_hash}")
            if (question_id, candidate) in cache:
                reuse += 1
            else:
                pending.append(
                    {
                        "question_id": question_id,
                        "candidate_prediction_sha256": candidate_hash,
                    }
                )

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "pending_requests_answer_free.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in pending:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    audit = {
        "schema_version": "adsqa_sft_lora_mmr8_512_judge_preflight_v1",
        "passed": True,
        "question_count": EXPECTED_QUESTIONS,
        "method": EXPECTED_METHOD,
        "visual_protocol": {
            "views": EXPECTED_VIEWS,
            "unified_size": 512,
            "visual_tokens": EXPECTED_VISUAL_TOKENS,
            "visual_token_budget": 4096,
            "secondary_frame_sampling_disabled": True,
            "answer_or_outcome_fields_used": False,
        },
        "candidate_comparison": {
            "identical_to_lora_mmr448": sum(
                mmr512[qid] == mmr448[qid] for qid in mmr512
            ),
            "changed_from_lora_mmr448": sum(
                mmr512[qid] != mmr448[qid] for qid in mmr512
            ),
            "identical_to_clean_mmr512": sum(
                mmr512[qid] == clean512[qid] for qid in mmr512
            ),
            "changed_from_clean_mmr512": sum(
                mmr512[qid] != clean512[qid] for qid in mmr512
            ),
        },
        "judge_protocol": {
            "candidate_mode": "answer_only",
            "prompt_sha256": EXPECTED_PROMPT_SHA256,
            "historical_cache_unique_record_count": len(cache),
            "historical_cache_source_row_counts": source_counts,
            "exact_cache_reuse_count": reuse,
            "required_new_api_call_count": len(pending),
            "answer_extraction_counts": dict(sorted(extraction_counts.items())),
        },
        "candidate_set_sha256": sha256_bytes(
            ("\n".join(sorted(candidate_hash_rows)) + "\n").encode("utf-8")
        ),
        "inference_sha256s_sha256": sha256_file(run / "INFERENCE_SHA256SUMS"),
        "pending_manifest_contains_candidate_text": False,
        "contains_reference_answers": False,
        "contains_api_key": False,
        "api_called": False,
        "not_human_gold": True,
    }
    (output_root / "dry_run_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
