#!/usr/bin/env python3
"""Audit AdsSFTLoRA MMR8 predictions and align them to the frozen judge cache."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_PROMPT_SHA256 = "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19"
EXPECTED_METHOD = "AdsSFTLoRA_MMR8"
EXPECTED_QUESTIONS = 500
EXPECTED_FOLDS = 5
EXPECTED_VIEWS = 8
EXPECTED_VISUAL_TOKENS = 1024


class PreflightError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mmr-run", type=Path, required=True)
    parser.add_argument("--historical-oof-root", type=Path, required=True)
    parser.add_argument("--historical-judge-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def extract_answer_section(text: str) -> tuple[str, bool, str | None]:
    markers = (
        "3. [Answer]:",
        "[Answer]:",
        "3. [Answer]",
        "[Answer]",
        "<answer>",
    )
    matches = [(text.find(marker), marker) for marker in markers if text.find(marker) >= 0]
    if not matches:
        return text, False, None
    position, marker = min(matches, key=lambda item: (item[0], -len(item[1])))
    answer = text[position + len(marker):]
    if marker == "<answer>" and "</answer>" in answer:
        answer = answer.split("</answer>", 1)[0]
    answer = answer.strip()
    return (answer or text), bool(answer), marker


def truncate_words(text: str) -> str:
    words = text.split()
    return " ".join(words[:300]) if len(words) > 300 else text


def normalized_prediction(path: Path) -> tuple[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    prediction = str(payload.get("prediction", "")).strip()
    if not prediction:
        raise PreflightError(f"empty prediction: {path}")
    candidate, found, marker = extract_answer_section(prediction)
    return truncate_words(candidate), {
        "source_sha256": sha256_bytes(prediction.encode("utf-8")),
        "answer_extraction_found": found,
        "answer_extraction_marker": marker,
    }


def load_historical_candidates(root: Path) -> dict[tuple[str, str], set[str]]:
    owners: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for fold in range(EXPECTED_FOLDS):
        fold_root = root / f"fold_{fold}"
        for artifact, method in (
            ("base_raw8", "BaseRaw8"),
            ("lora_raw8", "AdsSFTLoRA_Raw8"),
        ):
            paths = sorted((fold_root / artifact).glob("*/prediction.json"))
            if len(paths) != 100:
                raise PreflightError(
                    f"expected 100 historical {method} predictions in fold {fold}, got {len(paths)}"
                )
            for path in paths:
                question_id = path.parent.name
                candidate, _ = normalized_prediction(path)
                owners[(question_id, candidate)].add(method)
    return dict(owners)


def load_historical_cache(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    dry_run_path = root / "dry_run_audit.json"
    partial_path = root / "api_results_partial.jsonl"
    if not (root / "JUDGE_COMPLETE").is_file():
        raise PreflightError("historical judge is not complete")
    dry_run = json.loads(dry_run_path.read_text(encoding="utf-8"))
    if dry_run.get("prompt_sha256") != EXPECTED_PROMPT_SHA256:
        raise PreflightError("historical prompt hash mismatch")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for line in partial_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        question_id = str(row.get("question_id", ""))
        candidate = str(row.get("candidate_prediction", ""))
        key = (question_id, candidate)
        if not question_id or not candidate or key in rows:
            raise PreflightError(f"invalid or duplicate historical cache key: {key!r}")
        if float(row.get("score", -1)) not in {0.0, 0.5, 1.0}:
            raise PreflightError(f"invalid historical score: {key!r}")
        rows[key] = row
    if len(rows) != int(dry_run.get("required_api_call_count", -1)):
        raise PreflightError("historical cache count does not match its dry-run audit")
    return rows


def load_mmr_predictions(root: Path) -> dict[str, dict[str, Any]]:
    if not (root / "INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION").is_file():
        raise PreflightError("MMR8 inference completion marker is missing")
    rows: dict[str, dict[str, Any]] = {}
    for fold in range(EXPECTED_FOLDS):
        fold_root = root / "oof500" / f"fold_{fold}"
        prediction_paths = sorted(fold_root.glob("*/prediction.json"))
        if len(prediction_paths) != 100:
            raise PreflightError(f"expected 100 MMR8 predictions in fold {fold}, got {len(prediction_paths)}")
        for prediction_path in prediction_paths:
            question_id = prediction_path.parent.name
            if question_id in rows:
                raise PreflightError(f"duplicate MMR8 question ID: {question_id}")
            payload = json.loads(prediction_path.read_text(encoding="utf-8"))
            if str(payload.get("question_id")) != question_id:
                raise PreflightError(f"question ID mismatch: {prediction_path}")
            if payload.get("method") != EXPECTED_METHOD:
                raise PreflightError(f"method mismatch: {prediction_path}")
            evidence_path = prediction_path.with_name("evidence.json")
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            trace = evidence.get("processor_trace", {})
            if evidence.get("input_image_count") != EXPECTED_VIEWS:
                raise PreflightError(f"view-count mismatch: {evidence_path}")
            if trace.get("submitted_frame_count") != EXPECTED_VIEWS:
                raise PreflightError(f"submitted-frame mismatch: {evidence_path}")
            if trace.get("represented_frame_count") != EXPECTED_VIEWS:
                raise PreflightError(f"represented-frame mismatch: {evidence_path}")
            if trace.get("secondary_frame_sampling_disabled") is not True:
                raise PreflightError(f"secondary sampling is not disabled: {evidence_path}")
            if trace.get("post_merge_visual_token_count") != EXPECTED_VISUAL_TOKENS:
                raise PreflightError(f"visual-token mismatch: {evidence_path}")
            provenance = evidence.get("selection_provenance", {})
            if provenance.get("answer_or_outcome_fields_used") is not False:
                raise PreflightError(f"answer/outcome leakage flag is not false: {evidence_path}")
            candidate, extraction = normalized_prediction(prediction_path)
            rows[question_id] = {
                "fold": fold,
                "candidate": candidate,
                "candidate_sha256": sha256_bytes(candidate.encode("utf-8")),
                **extraction,
            }
    if len(rows) != EXPECTED_QUESTIONS:
        raise PreflightError(f"expected {EXPECTED_QUESTIONS} MMR8 predictions, got {len(rows)}")
    return rows


def main() -> None:
    args = parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    historical_owners = load_historical_candidates(args.historical_oof_root.resolve())
    historical_cache = load_historical_cache(args.historical_judge_root.resolve())
    mmr = load_mmr_predictions(args.mmr_run.resolve())

    cache_owner_counts: Counter[str] = Counter()
    extraction_counts: Counter[str] = Counter()
    reusable_keys: list[tuple[str, str]] = []
    pending_keys: list[tuple[str, str]] = []
    candidate_hash_rows: list[str] = []
    for question_id in sorted(mmr):
        row = mmr[question_id]
        key = (question_id, str(row["candidate"]))
        candidate_hash_rows.append(f"{question_id}\t{row['candidate_sha256']}")
        extraction_counts[str(row["answer_extraction_marker"] or "full_response")] += 1
        owners = historical_owners.get(key, set())
        if key in historical_cache:
            reusable_keys.append(key)
            cache_owner_counts["+".join(sorted(owners)) or "cache_only"] += 1
        else:
            pending_keys.append(key)

    pending_manifest_path = output_root / "pending_requests_answer_free.jsonl"
    with pending_manifest_path.open("w", encoding="utf-8") as handle:
        for question_id, candidate in pending_keys:
            handle.write(json.dumps({
                "question_id": question_id,
                "candidate_prediction_sha256": sha256_bytes(candidate.encode("utf-8")),
            }, ensure_ascii=False) + "\n")

    audit = {
        "schema_version": "adsqa_sft_lora_mmr8_judge_cache_preflight_v1",
        "passed": True,
        "method": EXPECTED_METHOD,
        "question_count": len(mmr),
        "fold_count": EXPECTED_FOLDS,
        "visual_protocol": {
            "views_per_question": EXPECTED_VIEWS,
            "visual_tokens_per_question": EXPECTED_VISUAL_TOKENS,
            "secondary_frame_sampling_disabled": True,
            "answer_or_outcome_fields_used": False,
        },
        "judge_protocol": {
            "candidate_mode": "answer_only",
            "prompt_sha256": EXPECTED_PROMPT_SHA256,
            "historical_cache_record_count": len(historical_cache),
            "exact_cache_reuse_count": len(reusable_keys),
            "required_new_api_call_count": len(pending_keys),
            "cache_reuse_owner_counts": dict(sorted(cache_owner_counts.items())),
            "answer_extraction_counts": dict(sorted(extraction_counts.items())),
        },
        "candidate_set_sha256": sha256_bytes(
            ("\n".join(candidate_hash_rows) + "\n").encode("utf-8")
        ),
        "inputs": {
            "mmr_inference_sha256s": sha256_file(args.mmr_run / "INFERENCE_SHA256SUMS"),
            "historical_judge_dry_run_sha256": sha256_file(
                args.historical_judge_root / "dry_run_audit.json"
            ),
            "historical_judge_partial_sha256": sha256_file(
                args.historical_judge_root / "api_results_partial.jsonl"
            ),
        },
        "pending_manifest_contains_candidate_text": False,
        "contains_reference_answers": False,
        "contains_api_key": False,
        "api_called": False,
        "not_human_gold": True,
    }
    audit_path = output_root / "dry_run_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
