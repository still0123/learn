#!/usr/bin/env python3
"""Build a disjoint Smoke30 using the single guarded v2.1 intervention correction."""

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
from evaluation.methods.claim_evidence_verifier.protocol_v2 import audit_intervention, frame_timestamps
from evaluation.methods.claim_evidence_verifier.protocol_v21 import (
    plan_asr_target_control_v21,
    plan_visual_target_control_v21,
    raw32_relevance_from_nested_cache,
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
    parser.add_argument("--temporal-cache", type=Path, action="append", required=True)
    parser.add_argument("--exclude-input-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-type", type=int, default=6)
    parser.add_argument("--seed", type=int, default=2026071602)
    args = parser.parse_args()

    annotations = {str(row["question_id"]): row for row in load_json(args.annotations)}
    reviews = {str(row["question_id"]): row for row in load_jsonl(args.review_queue)}
    judges = {
        str(row["question_id"]): row for row in load_jsonl(args.judge_results)
        if row.get("method") == "raw_uniform"
    }
    caches = {}
    for path in args.temporal_cache:
        for row in load_jsonl(path):
            qid = str(row["question_id"])
            if qid in caches:
                raise RuntimeError(f"duplicate temporal cache row: {qid}")
            caches[qid] = row
    excluded_qids, excluded_videos = set(), set()
    exclusions = []
    for path in args.exclude_input_jsonl:
        rows = load_jsonl(path)
        excluded_qids.update(str(row["question_id"]) for row in rows)
        excluded_videos.update(str(row["video_id"]) for row in rows)
        exclusions.append({"path": str(path), "sha256": sha256_file(path), "rows": len(rows)})

    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped = Counter()
    plan_reason_counts = Counter()
    for qid, annotation in annotations.items():
        review = reviews.get(qid)
        if qid in excluded_qids or str(annotation.get("video_id")) in excluded_videos:
            skipped["excluded_prior_smoke"] += 1
            continue
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
        elif qid not in caches:
            skipped["missing_temporal_cache"] += 1
        else:
            prediction, evidence = load_json(prediction_path), load_json(evidence_path)
            claim = extract_answer_claim(str(prediction.get("prediction", "")))
            duration = video_duration(Path(evidence["video_path"]))
            selected_frames = list(evidence.get("selected_frames") or [])
            selected_indices = [int(row["frame_index"]) for row in selected_frames]
            timestamps = frame_timestamps(selected_frames, duration)
            try:
                relevance = raw32_relevance_from_nested_cache(selected_indices, caches[qid])
            except ValueError:
                skipped["raw32_cache_not_nested"] += 1
                continue
            visual_plan = plan_visual_target_control_v21(
                timestamps, relevance, annotation["evidence_units"], duration
            )
            asr_plan = plan_asr_target_control_v21(
                review.get("asr_segments", []), annotation["evidence_units"],
                f"{evidence.get('question', review.get('question', ''))} {claim}",
            )
            # Timed speech is less ambiguous than broad visual intervals, so it is preferred when valid.
            chosen = asr_plan if asr_plan.get("valid") else visual_plan
            plan_reason_counts[f"asr:{asr_plan.get('reason')}"] += 1
            plan_reason_counts[f"visual:{visual_plan.get('reason')}"] += 1
            errors = audit_intervention(chosen)
            if not chosen.get("valid") or errors:
                skipped["no_safe_intervention"] += 1
                continue
            input_row = {
                "schema": "adsqa_claim_evidence_smoke_input_v21",
                "question_id": qid, "video_id": str(annotation["video_id"]),
                "primary_type": str(review.get("primary_type", "unknown")),
                "question": str(evidence.get("question", review.get("question", ""))),
                "claim": claim, "asr_excerpt": str(evidence.get("asr_excerpt", "")),
                "asr_segments": [
                    {"start": row.get("start"), "end": row.get("end"), "text": row.get("text", "")}
                    for row in review.get("asr_segments", [])
                ],
                "video_path": str(evidence["video_path"]), "evidence_trace_path": str(evidence_path),
                "selected_frame_indices": selected_indices, "selected_timestamps_sec": timestamps,
                "raw32_relevance_scores": relevance, "duration_sec": duration,
                "intervention_modality": chosen["modality"],
            }
            if FORBIDDEN_INPUT_KEYS & set(input_row):
                raise RuntimeError("supervision leaked into v2.1 smoke input")
            pools[input_row["primary_type"]].append({
                "input": input_row,
                "oracle": {
                    "schema": "adsqa_claim_evidence_oracle_plan_v21", "question_id": qid,
                    "decisive_fact": annotation.get("decisive_fact", ""),
                    "evidence_observability": annotation.get("evidence_observability", ""),
                    "evidence_units": annotation["evidence_units"],
                    "visual_plan": visual_plan, "asr_plan": asr_plan, "selected_plan": chosen,
                },
                "supervision": {
                    "schema": "adsqa_claim_evidence_smoke_supervision_v21", "question_id": qid,
                    "reference_answer": review.get("reference_answer", ""),
                    "raw_judge_score": float(judges[qid]["score"]),
                },
            })

    expected = args.per_type * 5
    eligibility = {key: len(value) for key, value in sorted(pools.items())}
    shortage = {f"Type_{index}": eligibility.get(f"Type_{index}", 0) for index in range(1, 6) if eligibility.get(f"Type_{index}", 0) < args.per_type}
    if shortage:
        write_json(args.output_root / "eligibility_failure.json", {
            "eligible_by_type": eligibility, "shortage": shortage,
            "skipped": dict(skipped), "plan_reason_counts": dict(plan_reason_counts),
        })
        raise RuntimeError(f"insufficient safe v2.1 samples: {shortage}")
    primary_types = [f"Type_{index}" for index in range(1, 6)]
    ranked_pools = {
        primary_type: sorted(
            pools[primary_type], key=lambda row: stable_rank(args.seed, row["input"]["question_id"])
        )
        for primary_type in primary_types
    }
    pointers = {primary_type: 0 for primary_type in primary_types}
    selected, selected_videos = [], set()
    for _ in range(args.per_type):
        for primary_type in primary_types:
            chosen = None
            while pointers[primary_type] < len(ranked_pools[primary_type]):
                candidate = ranked_pools[primary_type][pointers[primary_type]]
                pointers[primary_type] += 1
                video_id = candidate["input"]["video_id"]
                if video_id not in selected_videos:
                    chosen = candidate
                    break
            if chosen is None:
                write_json(args.output_root / "unique_video_selection_failure.json", {
                    "primary_type": primary_type, "selected": len(selected),
                    "selected_videos": len(selected_videos), "eligible_by_type": eligibility,
                })
                raise RuntimeError(f"insufficient globally unique videos for {primary_type}")
            selected.append(chosen)
            selected_videos.add(chosen["input"]["video_id"])
    inputs = [row["input"] for row in selected]
    oracle = [row["oracle"] for row in selected]
    supervision = [row["supervision"] for row in selected]
    if len(inputs) != expected or len({row["video_id"] for row in inputs}) != expected:
        raise RuntimeError("v2.1 selection count or unique-video audit failed")

    input_path, oracle_path = args.output_root / "input.jsonl", args.output_root / "oracle_plans.jsonl"
    supervision_path, audit_path = args.output_root / "supervision.jsonl", args.output_root / "audit.json"
    write_jsonl(input_path, inputs)
    write_jsonl(oracle_path, oracle)
    write_jsonl(supervision_path, supervision)
    modality_counts = Counter(row["selected_plan"]["modality"] for row in oracle)
    audit = {
        "schema": "adsqa_claim_evidence_smoke30_audit_v21",
        "selected": len(inputs), "unique_questions": len({row["question_id"] for row in inputs}),
        "unique_videos": len({row["video_id"] for row in inputs}),
        "primary_type_counts": dict(Counter(row["primary_type"] for row in inputs)),
        "modality_counts": dict(modality_counts), "eligible_by_type": eligibility,
        "excluded_prior_question_overlap": len({row["question_id"] for row in inputs} & excluded_qids),
        "excluded_prior_video_overlap": len({row["video_id"] for row in inputs} & excluded_videos),
        "input_supervision_leakage": False, "skipped": dict(skipped),
        "plan_reason_counts": dict(plan_reason_counts), "passed": True,
    }
    write_json(audit_path, audit)
    write_json(args.output_root / "manifest.json", {
        "schema": "adsqa_claim_evidence_smoke30_manifest_v21",
        "purpose": "single guarded target/control correction; no parameter scan",
        "seed": args.seed, "per_type": args.per_type, "exclusions": exclusions,
        "temporal_caches": [{"path": str(path), "sha256": sha256_file(path)} for path in args.temporal_cache],
        "inputs": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "oracle_plans": {"path": str(oracle_path), "sha256": sha256_file(oracle_path)},
        "supervision": {"path": str(supervision_path), "sha256": sha256_file(supervision_path)},
        "audit": {"path": str(audit_path), "sha256": sha256_file(audit_path)},
    })
    print(json.dumps({"selected": len(inputs), "eligible_by_type": eligibility, "modality_counts": dict(modality_counts), "passed": True}))


if __name__ == "__main__":
    main()
