#!/usr/bin/env python3
"""Build a leakage-separated 30-item oracle intervention smoke set."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.claim_evidence_verifier.features_v2 import extract_answer_claim
from evaluation.methods.claim_evidence_verifier.protocol_v2 import (
    audit_intervention,
    frame_timestamps,
    plan_asr_target_control,
    plan_visual_target_control,
)


FORBIDDEN_INPUT_KEYS = {"answer", "ground_truth", "reference_answer", "judge_score", "supervision", "evidence_units"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def video_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def stable_rank(seed: int, question_id: str) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def locate_result(root: Path, question_id: str, filename: str) -> Path | None:
    direct = root / question_id / filename
    if direct.is_file():
        return direct
    matches = sorted(root.glob(f"{question_id}*/{filename}"))
    return matches[0] if len(matches) == 1 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--raw-result-root", type=Path, required=True)
    parser.add_argument("--judge-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-type", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    annotations = {str(row["question_id"]): row for row in load_json(args.annotations)}
    reviews = {str(row["question_id"]): row for row in load_jsonl(args.review_queue)}
    judge_rows = [row for row in load_jsonl(args.judge_results) if row.get("method") == "raw_uniform"]
    judges = {str(row["question_id"]): row for row in judge_rows}
    pools: dict[str, list[str]] = defaultdict(list)
    skipped = Counter()
    for qid, annotation in annotations.items():
        review = reviews.get(qid)
        prediction_path = locate_result(args.raw_result_root, qid, "prediction.json")
        evidence_path = locate_result(args.raw_result_root, qid, "evidence.json")
        if annotation.get("review_status") != "AI_REVIEWED":
            skipped["not_reviewed"] += 1
        elif not annotation.get("evidence_units"):
            skipped["no_evidence_units"] += 1
        elif not review:
            skipped["missing_review_row"] += 1
        elif not prediction_path or not evidence_path:
            skipped["missing_raw_result"] += 1
        elif qid not in judges:
            skipped["missing_judge"] += 1
        else:
            pools[str(review.get("primary_type", "unknown"))].append(qid)

    selected = []
    for primary_type in sorted(pools):
        ranked = sorted(pools[primary_type], key=lambda qid: stable_rank(args.seed, qid))
        selected.extend((primary_type, qid) for qid in ranked[: args.per_type])
    expected = args.per_type * 5
    if len(selected) != expected:
        raise RuntimeError(f"expected {expected} stratified rows, got {len(selected)}")

    inputs, oracle, supervision = [], [], []
    audit_errors = []
    valid_plan_count = 0
    for primary_type, qid in selected:
        annotation, review = annotations[qid], reviews[qid]
        prediction_path = locate_result(args.raw_result_root, qid, "prediction.json")
        evidence_path = locate_result(args.raw_result_root, qid, "evidence.json")
        assert prediction_path and evidence_path
        prediction, evidence = load_json(prediction_path), load_json(evidence_path)
        duration = video_duration(Path(evidence["video_path"]))
        timestamps = frame_timestamps(evidence.get("selected_frames", []), duration)
        visual_plan = plan_visual_target_control(timestamps, annotation["evidence_units"])
        asr_plan = plan_asr_target_control(review.get("asr_segments", []), annotation["evidence_units"])
        plans = [plan for plan in (visual_plan, asr_plan) if plan.get("valid")]
        chosen = plans[0] if plans else visual_plan
        errors = audit_intervention(chosen)
        if chosen.get("valid"):
            valid_plan_count += 1
        if errors:
            audit_errors.append({"question_id": qid, "errors": errors})
        input_row = {
            "schema": "adsqa_claim_evidence_smoke_input_v2",
            "question_id": qid,
            "video_id": str(annotation["video_id"]),
            "primary_type": primary_type,
            "question": str(evidence.get("question", review.get("question", ""))),
            "claim": extract_answer_claim(str(prediction.get("prediction", ""))),
            "asr_excerpt": str(evidence.get("asr_excerpt", "")),
            "asr_segments": [
                {"start": row.get("start"), "end": row.get("end"), "text": row.get("text", "")}
                for row in review.get("asr_segments", [])
            ],
            "video_path": str(evidence["video_path"]),
            "evidence_trace_path": str(evidence_path),
            "selected_frame_indices": [int(row["frame_index"]) for row in evidence.get("selected_frames", [])],
            "selected_timestamps_sec": timestamps,
            "duration_sec": duration,
            "intervention_modality": chosen.get("modality"),
        }
        if FORBIDDEN_INPUT_KEYS & set(input_row):
            raise RuntimeError("supervision leaked into smoke input")
        inputs.append(input_row)
        oracle.append({
            "schema": "adsqa_claim_evidence_oracle_plan_v2",
            "question_id": qid,
            "decisive_fact": annotation.get("decisive_fact", ""),
            "evidence_observability": annotation.get("evidence_observability", ""),
            "evidence_units": annotation["evidence_units"],
            "visual_plan": visual_plan,
            "asr_plan": asr_plan,
            "selected_plan": chosen,
        })
        supervision.append({
            "schema": "adsqa_claim_evidence_smoke_supervision_v2",
            "question_id": qid,
            "reference_answer": review.get("reference_answer", ""),
            "raw_judge_score": float(judges[qid]["score"]),
        })

    input_path = args.output_root / "input.jsonl"
    oracle_path = args.output_root / "oracle_plans.jsonl"
    supervision_path = args.output_root / "supervision.jsonl"
    write_jsonl(input_path, inputs)
    write_jsonl(oracle_path, oracle)
    write_jsonl(supervision_path, supervision)
    audit = {
        "schema": "adsqa_claim_evidence_smoke30_audit_v2",
        "selected": len(inputs),
        "unique_questions": len({row["question_id"] for row in inputs}),
        "unique_videos": len({row["video_id"] for row in inputs}),
        "primary_type_counts": dict(Counter(row["primary_type"] for row in inputs)),
        "valid_intervention_plans": valid_plan_count,
        "plan_errors": audit_errors,
        "forbidden_input_keys": sorted(FORBIDDEN_INPUT_KEYS),
        "input_supervision_leakage": False,
        "skipped": dict(skipped),
        "passed": len(inputs) == expected and not audit_errors and valid_plan_count == expected,
    }
    audit_path = args.output_root / "audit.json"
    write_json(audit_path, audit)
    manifest = {
        "schema": "adsqa_claim_evidence_smoke30_manifest_v2",
        "purpose": "oracle target/control protocol smoke; not a trained verifier result",
        "seed": args.seed,
        "per_type": args.per_type,
        "inputs": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "oracle_plans": {"path": str(oracle_path), "sha256": sha256_file(oracle_path)},
        "supervision": {"path": str(supervision_path), "sha256": sha256_file(supervision_path)},
        "audit": {"path": str(audit_path), "sha256": sha256_file(audit_path)},
    }
    write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps({"selected": len(inputs), "valid_plans": valid_plan_count, "passed": audit["passed"]}))


if __name__ == "__main__":
    main()
