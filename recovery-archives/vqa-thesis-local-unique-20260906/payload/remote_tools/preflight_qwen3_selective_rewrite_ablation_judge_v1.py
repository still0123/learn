#!/usr/bin/env python3
"""Count exact new answer-only judge calls for frozen rewrite ablations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ABLATIONS = ("no_ocr", "no_segmented_asr", "no_local_crop")
VALID_SCORES = {0.0, 0.5, 1.0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groundtruth", type=Path, required=True)
    parser.add_argument("--historical-a0-results", type=Path, required=True)
    parser.add_argument("--historical-rewrite-results", type=Path, required=True)
    parser.add_argument("--ablation-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise RuntimeError("immutable preflight output already exists")
    groundtruth = json.loads(args.groundtruth.read_text(encoding="utf-8"))
    gt_ids = {str(row["question_id"]) for row in groundtruth}
    if len(gt_ids) != 500:
        raise RuntimeError("groundtruth is not the frozen OOF500 reference")

    existing: dict[tuple[str, str], dict[str, Any]] = {}
    for source in (args.historical_a0_results, args.historical_rewrite_results):
        for row in load_jsonl(source):
            candidate = str(row.get("candidate_prediction", row.get("prediction", "")))
            candidate_hash = str(row.get("candidate_prediction_sha256", ""))
            if not candidate_hash:
                if not candidate:
                    raise RuntimeError("historical result lacks candidate text and hash")
                candidate_hash = sha256_text(candidate)
            key = (str(row["question_id"]), candidate_hash)
            score = float(row["score"])
            if score not in VALID_SCORES:
                raise RuntimeError(f"invalid historical score for {key[0]}")
            if key in existing and float(existing[key]["score"]) != score:
                raise RuntimeError(f"conflicting historical score for {key[0]}")
            existing[key] = row

    required: dict[tuple[str, str], list[str]] = {}
    choice_hashes: dict[str, str] = {}
    protocol_hashes: dict[str, str] = {}
    per_ablation: dict[str, dict[str, int]] = {}
    for ablation in ABLATIONS:
        choice_path = (
            args.ablation_root
            / ablation
            / "frozen_choices_v1"
            / "frozen_choices_answer_free.jsonl"
        )
        protocol_path = args.ablation_root / ablation / "frozen_choices_v1" / "protocol_audit.json"
        audit = json.loads(protocol_path.read_text(encoding="utf-8"))
        choices = load_jsonl(choice_path)
        if audit.get("passed") is not True or len(choices) != 50:
            raise RuntimeError(f"{ablation} is not a complete frozen 50-question run")
        if {str(row["question_id"]) for row in choices} - gt_ids:
            raise RuntimeError(f"{ablation} contains unknown questions")
        local_keys: set[tuple[str, str]] = set()
        for row in choices:
            qid = str(row["question_id"])
            for field in ("a0_prediction", "a1_prediction", "a2_prediction"):
                key = (qid, sha256_text(str(row[field])))
                required.setdefault(key, []).append(f"{ablation}:{field}")
                local_keys.add(key)
        per_ablation[ablation] = {
            "question_count": len(choices),
            "unique_candidate_count": len(local_keys),
        }
        choice_hashes[ablation] = sha256_file(choice_path)
        protocol_hashes[ablation] = sha256_file(protocol_path)

    missing = sorted(set(required) - set(existing))
    reused = sorted(set(required) & set(existing))
    for ablation in ABLATIONS:
        owners = {
            key
            for key, values in required.items()
            if any(value.startswith(f"{ablation}:") for value in values)
        }
        per_ablation[ablation].update(
            {
                "exact_historical_reuse_count": len(owners & set(existing)),
                "required_new_call_count_before_cross_ablation_dedup": len(owners - set(existing)),
            }
        )
    output = {
        "schema_version": "qwen3_selective_rewrite_ablation_judge_preflight_v1",
        "passed": True,
        "api_called": False,
        "contains_api_key": False,
        "candidate_mode": "answer_only",
        "ablations": list(ABLATIONS),
        "per_ablation": per_ablation,
        "combined_unique_candidate_count": len(required),
        "exact_historical_reuse_count": len(reused),
        "required_new_api_call_count": len(missing),
        "cross_ablation_new_candidate_dedup_count": (
            sum(value["required_new_call_count_before_cross_ablation_dedup"] for value in per_ablation.values())
            - len(missing)
        ),
        "new_candidate_key_hashes": [
            {
                "question_id": qid,
                "candidate_prediction_sha256": candidate_hash,
                "owners": required[(qid, candidate_hash)],
            }
            for qid, candidate_hash in missing
        ],
        "groundtruth_sha256": sha256_file(args.groundtruth),
        "historical_a0_results_sha256": sha256_file(args.historical_a0_results),
        "historical_rewrite_results_sha256": sha256_file(args.historical_rewrite_results),
        "choice_hashes": choice_hashes,
        "protocol_hashes": protocol_hashes,
        "submitted_fields_if_authorized": [
            "meta_info",
            "question",
            "golden_answer",
            "candidate_answer",
        ],
        "video_or_cache_would_be_submitted": False,
        "not_human_gold": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in output.items() if key != "new_candidate_key_hashes"}, indent=2))


if __name__ == "__main__":
    main()
