"""Ablatable fixed-budget temporal selection over precomputed similarities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SelectorWeights:
    question: float = 0.55
    asr: float = 0.20
    scene_change: float = 0.15
    coverage_bonus: float = 0.10
    duplicate_penalty: float = 0.20


def _minmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    span = float(values.max() - values.min()) if values.size else 0.0
    if span <= 1e-12:
        return np.zeros_like(values)
    return (values - values.min()) / span


def _validate_inputs(
    frame_embeddings: np.ndarray,
    question_scores: np.ndarray,
    asr_scores: np.ndarray,
    top_k: int,
    coverage_bins: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    frame_embeddings = np.asarray(frame_embeddings, dtype=np.float64)
    question_scores = np.asarray(question_scores, dtype=np.float64).reshape(-1)
    asr_scores = np.asarray(asr_scores, dtype=np.float64).reshape(-1)
    if frame_embeddings.ndim != 2 or frame_embeddings.shape[0] == 0:
        raise ValueError("frame_embeddings must be a non-empty 2D array")
    count = frame_embeddings.shape[0]
    if question_scores.shape != (count,) or asr_scores.shape != (count,):
        raise ValueError("score arrays must match the candidate count")
    if not 0 < top_k <= count:
        raise ValueError("top_k must be within the candidate count")
    if not 0 < coverage_bins <= top_k:
        raise ValueError("coverage_bins must be within top_k")
    norms = np.linalg.norm(frame_embeddings, axis=1, keepdims=True)
    normalized = frame_embeddings / np.maximum(norms, 1e-12)
    return normalized, question_scores, asr_scores


def select_temporal_evidence(
    frame_embeddings: np.ndarray,
    question_scores: np.ndarray,
    asr_scores: np.ndarray,
    *,
    top_k: int,
    coverage_bins: int = 8,
    question_asr_reliability: float = 1.0,
    weights: SelectorWeights = SelectorWeights(),
) -> tuple[list[int], dict[str, Any]]:
    """Select chronological ranks with coverage anchors and MMR suppression."""
    embeddings, question_scores, asr_scores = _validate_inputs(
        frame_embeddings, question_scores, asr_scores, top_k, coverage_bins
    )
    count = embeddings.shape[0]
    reliability = float(np.clip(question_asr_reliability, 0.0, 1.0))
    question_component = _minmax(question_scores)
    asr_component = _minmax(asr_scores) * reliability

    adjacent_similarity = np.ones(count, dtype=np.float64)
    if count > 1:
        pair_similarity = np.sum(embeddings[1:] * embeddings[:-1], axis=1)
        adjacent_similarity[1:] = pair_similarity
        adjacent_similarity[0] = pair_similarity[0]
    scene_component = _minmax(1.0 - adjacent_similarity)
    base_score = (
        weights.question * question_component
        + weights.asr * asr_component
        + weights.scene_change * scene_component
    )

    bin_ids = np.minimum(
        (np.arange(count, dtype=np.int64) * coverage_bins) // count,
        coverage_bins - 1,
    )
    selected: list[int] = []
    selected_set: set[int] = set()
    bin_counts = np.zeros(coverage_bins, dtype=np.int64)
    decision_trace: list[dict[str, Any]] = []

    # One evidence anchor per temporal bin prevents complete interval collapse.
    for bin_id in range(coverage_bins):
        candidates = np.flatnonzero(bin_ids == bin_id).tolist()
        chosen = max(candidates, key=lambda index: (base_score[index], -index))
        selected.append(chosen)
        selected_set.add(chosen)
        bin_counts[bin_id] += 1
        decision_trace.append({
            "candidate_rank": chosen,
            "stage": "coverage_anchor",
            "utility": float(base_score[chosen]),
            "bin_id": bin_id,
        })

    target_per_bin = float(top_k) / float(coverage_bins)
    while len(selected) < top_k:
        best_index = -1
        best_utility = -float("inf")
        best_duplicate = 0.0
        best_coverage = 0.0
        for index in range(count):
            if index in selected_set:
                continue
            duplicate = float(np.max(embeddings[selected] @ embeddings[index]))
            bin_id = int(bin_ids[index])
            coverage = max(0.0, 1.0 - (float(bin_counts[bin_id]) / target_per_bin))
            utility = (
                float(base_score[index])
                + weights.coverage_bonus * coverage
                - weights.duplicate_penalty * duplicate
            )
            if utility > best_utility or (utility == best_utility and index < best_index):
                best_index = index
                best_utility = utility
                best_duplicate = duplicate
                best_coverage = coverage
        selected.append(best_index)
        selected_set.add(best_index)
        bin_counts[int(bin_ids[best_index])] += 1
        decision_trace.append({
            "candidate_rank": best_index,
            "stage": "mmr_fill",
            "utility": float(best_utility),
            "duplicate_similarity": float(best_duplicate),
            "coverage_deficit": float(best_coverage),
            "bin_id": int(bin_ids[best_index]),
        })

    ranked_selected = sorted(
        selected,
        key=lambda index: (
            -next(entry["utility"] for entry in decision_trace if entry["candidate_rank"] == index),
            index,
        ),
    )
    chronological = sorted(selected)
    trace = {
        "weights": asdict(weights),
        "question_asr_reliability": reliability,
        "question_component": question_component.tolist(),
        "asr_component": asr_component.tolist(),
        "scene_change_component": scene_component.tolist(),
        "base_score": base_score.tolist(),
        "coverage_bins": coverage_bins,
        "bin_counts": bin_counts.tolist(),
        "decision_trace": decision_trace,
        "ranked_selected_candidate_ranks": ranked_selected,
    }
    return chronological, trace


def select_conservative_raw_evidence(
    frame_embeddings: np.ndarray,
    question_scores: np.ndarray,
    asr_scores: np.ndarray,
    *,
    raw_candidate_ranks: list[int],
    top_k: int = 32,
    coverage_bins: int = 8,
    raw_per_bin: int = 3,
    evidence_per_bin: int = 1,
    question_asr_reliability: float = 1.0,
    weights: SelectorWeights = SelectorWeights(),
) -> tuple[list[int], dict[str, Any]]:
    """Keep broad Raw anchors and add one non-Raw evidence frame per bin."""
    embeddings, _, _ = _validate_inputs(
        frame_embeddings, question_scores, asr_scores, top_k, coverage_bins
    )
    count = embeddings.shape[0]
    if raw_per_bin <= 0 or evidence_per_bin <= 0:
        raise ValueError("raw_per_bin and evidence_per_bin must be positive")
    if coverage_bins * (raw_per_bin + evidence_per_bin) != top_k:
        raise ValueError("per-bin allocation must equal top_k")
    if len(raw_candidate_ranks) != coverage_bins * (raw_per_bin + 1):
        raise ValueError("expected four Raw32 candidate ranks per temporal bin")
    if len(set(raw_candidate_ranks)) != len(raw_candidate_ranks):
        raise ValueError("raw_candidate_ranks must be unique")
    if any(rank < 0 or rank >= count for rank in raw_candidate_ranks):
        raise ValueError("raw candidate rank outside candidate range")

    _, score_trace = select_temporal_evidence(
        frame_embeddings,
        question_scores,
        asr_scores,
        top_k=top_k,
        coverage_bins=coverage_bins,
        question_asr_reliability=question_asr_reliability,
        weights=weights,
    )
    base_score = np.asarray(score_trace["base_score"], dtype=np.float64)
    bin_ids = np.minimum(
        (np.arange(count, dtype=np.int64) * coverage_bins) // count,
        coverage_bins - 1,
    )
    raw_set = set(raw_candidate_ranks)
    selected: list[int] = []
    decision_trace: list[dict[str, Any]] = []

    for bin_id in range(coverage_bins):
        bin_raw = [rank for rank in raw_candidate_ranks if int(bin_ids[rank]) == bin_id]
        if len(bin_raw) != raw_per_bin + 1:
            raise ValueError(f"bin {bin_id} does not contain four Raw anchors")
        retained = sorted(
            sorted(bin_raw, key=lambda rank: (-base_score[rank], rank))[:raw_per_bin]
        )
        for rank in retained:
            selected.append(rank)
            decision_trace.append({
                "candidate_rank": rank,
                "stage": "retained_raw_anchor",
                "utility": float(base_score[rank]),
                "bin_id": bin_id,
            })

        non_raw = [
            rank for rank in range(count)
            if int(bin_ids[rank]) == bin_id and rank not in raw_set
        ]
        if len(non_raw) < evidence_per_bin:
            raise ValueError(f"bin {bin_id} has insufficient non-Raw candidates")
        for _ in range(evidence_per_bin):
            best_rank = max(
                non_raw,
                key=lambda rank: (
                    float(base_score[rank])
                    - weights.duplicate_penalty
                    * float(np.max(embeddings[selected] @ embeddings[rank])),
                    -rank,
                ),
            )
            duplicate = float(np.max(embeddings[selected] @ embeddings[best_rank]))
            utility = float(base_score[best_rank]) - weights.duplicate_penalty * duplicate
            selected.append(best_rank)
            non_raw.remove(best_rank)
            decision_trace.append({
                "candidate_rank": best_rank,
                "stage": "non_raw_evidence",
                "utility": utility,
                "duplicate_similarity": duplicate,
                "bin_id": bin_id,
            })

    chronological = sorted(selected)
    if len(chronological) != top_k or len(set(chronological)) != top_k:
        raise RuntimeError("conservative selector did not produce a unique fixed budget")
    ranked_selected = [
        item["candidate_rank"]
        for item in sorted(decision_trace, key=lambda item: (-item["utility"], item["candidate_rank"]))
    ]
    trace = {
        **score_trace,
        "policy": "conservative_raw24_evidence8_v1",
        "raw_candidate_ranks": sorted(raw_candidate_ranks),
        "raw_per_bin": raw_per_bin,
        "evidence_per_bin": evidence_per_bin,
        "replacement_count": len(set(chronological) - raw_set),
        "bin_counts": [raw_per_bin + evidence_per_bin] * coverage_bins,
        "decision_trace": decision_trace,
        "ranked_selected_candidate_ranks": ranked_selected,
    }
    return chronological, trace
