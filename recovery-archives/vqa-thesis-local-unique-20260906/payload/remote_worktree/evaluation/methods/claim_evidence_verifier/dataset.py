"""Pair-record construction shared by training and inference tools."""

from __future__ import annotations

from typing import Any, Mapping


def pair_record_from_trace(
    trace: Mapping[str, Any],
    source_method: str,
    groundtruth_row: Mapping[str, Any] | None = None,
    initial_score: float | None = None,
    rescue_score: float | None = None,
) -> dict[str, Any]:
    rescue = trace.get("rescue") or {}
    rescue_answer = str(rescue.get("rescue_answer", "")).strip()
    if not rescue.get("triggered") or not rescue_answer:
        raise ValueError(f"trace has no rescue candidate: {trace.get('question_id')}")
    initial_answer = str(trace.get("initial_answer", "")).strip()
    if not initial_answer:
        raise ValueError(f"trace has no initial candidate: {trace.get('question_id')}")
    record: dict[str, Any] = {
        "schema": "adsqa_claim_evidence_pair_v1",
        "question_id": str(trace.get("question_id")),
        "video_id": str(trace.get("video_id", "")),
        "source_method": source_method,
        "category": str(trace.get("category", "narrative_other")),
        "question": str(trace.get("question", "")),
        "asr_excerpt": str(trace.get("asr_excerpt", "")),
        "initial_answer": initial_answer,
        "rescue_answer": rescue_answer,
        "support": {
            "initial_on_positive": trace.get("support_plus"),
            "initial_on_counterfactual": trace.get("support_minus"),
            "initial_on_rescue": rescue.get("initial_support_on_rescue"),
            "rescue_on_rescue": rescue.get("rescue_support_on_rescue"),
        },
        "relevance_scores": list(trace.get("relevance_scores") or []),
        "counterfactual": dict(trace.get("counterfactual") or {}),
        "rescue": {
            "reasons": list(rescue.get("reasons") or []),
            "rescue_plan": dict(rescue.get("rescue_plan") or {}),
        },
    }
    if initial_score is not None and rescue_score is not None:
        delta = float(rescue_score) - float(initial_score)
        record["supervision"] = {
            "initial_score": float(initial_score),
            "rescue_score": float(rescue_score),
            "score_delta": delta,
            "rescue_better": int(delta > 0),
            "initial_better": int(delta < 0),
            "tie": int(delta == 0),
            "ground_truth": str((groundtruth_row or {}).get("answer", "")),
        }
    return record
