"""Leakage-safe features and metrics for the direct claim reliability verifier."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping, Sequence


FEATURE_SCHEMA_VERSION = "adsqa_claim_reliability_features_v22"
PRIMARY_TYPES = tuple(f"Type_{index}" for index in range(1, 6))
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(value: Any) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(str(value or "")) if len(token) > 1}


def _jaccard(left: Any, right: Any) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _stats(values: Sequence[Any]) -> list[float]:
    numbers = [float(value) for value in values]
    if not numbers:
        return [0.0] * 5
    mean = sum(numbers) / len(numbers)
    variance = sum((value - mean) ** 2 for value in numbers) / len(numbers)
    ordered = sorted(numbers, reverse=True)
    return [mean, math.sqrt(variance), min(numbers), max(numbers), sum(ordered[: min(4, len(ordered))]) / min(4, len(ordered))]


def _entropy(probabilities: Sequence[float]) -> float:
    return -sum(value * math.log(max(value, 1e-12)) for value in probabilities)


def feature_names() -> list[str]:
    names = [
        "support_supported", "support_refuted", "support_insufficient", "support_entropy", "support_margin",
        "question_claim_jaccard", "asr_claim_jaccard", "question_asr_jaccard",
        "question_log_length", "claim_log_length", "asr_log_length", "asr_present", "ocr_present",
        "candidate_mean", "candidate_std", "candidate_min", "candidate_max", "candidate_top4_mean",
        "raw_mean", "raw_std", "raw_min", "raw_max", "raw_top4_mean",
        "question_component_mean", "question_component_std", "question_component_min",
        "question_component_max", "question_component_top4_mean",
        "asr_component_mean", "asr_component_std", "asr_component_min", "asr_component_max", "asr_component_top4_mean",
        "question_asr_reliability", "mmr_raw_overlap", "raw_score_range",
    ]
    names.extend(f"primary_type={value}" for value in PRIMARY_TYPES)
    return names


def build_feature_vector(input_row: Mapping[str, Any], support_row: Mapping[str, Any]) -> list[float]:
    scores = (support_row.get("scores") or {}).get("full") or {}
    probabilities = [float(scores.get(key, 0.0)) for key in ("supported", "refuted", "insufficient")]
    if abs(sum(probabilities) - 1.0) > 1e-4:
        raise ValueError("support probabilities must sum to one")
    ordered = sorted(probabilities, reverse=True)
    router = input_row.get("router_inputs") or {}
    candidate_scores = list(router.get("candidate_scores") or [])
    raw_ranks = [int(value) for value in router.get("raw_candidate_ranks") or []]
    raw_scores = [candidate_scores[index] for index in raw_ranks if 0 <= index < len(candidate_scores)]
    trace = router.get("selector_trace") or {}
    question_component = list(trace.get("question_component") or [])
    asr_component = list(trace.get("asr_component") or [])
    mmr = set(int(value) for value in router.get("mmr_selected_candidate_ranks") or [])
    raw = set(raw_ranks)
    question, claim, asr = input_row.get("question", ""), input_row.get("claim", ""), input_row.get("asr_excerpt", "")
    vector = [
        *probabilities, _entropy(probabilities), ordered[0] - ordered[1],
        _jaccard(question, claim), _jaccard(asr, claim), _jaccard(question, asr),
        math.log1p(len(str(question))), math.log1p(len(str(claim))), math.log1p(len(str(asr))),
        float(bool(str(asr).strip())), float(bool(input_row.get("ocr_present"))),
        *_stats(candidate_scores), *_stats(raw_scores), *_stats(question_component), *_stats(asr_component),
        float(trace.get("question_asr_reliability", 0.0) or 0.0),
        len(raw & mmr) / len(raw | mmr) if raw and mmr else 0.0,
        max(raw_scores) - min(raw_scores) if raw_scores else 0.0,
    ]
    primary_type = str(input_row.get("primary_type", ""))
    vector.extend(float(primary_type == value) for value in PRIMARY_TYPES)
    if len(vector) != len(feature_names()):
        raise RuntimeError(f"v2.2 feature schema drift: {len(vector)} != {len(feature_names())}")
    return vector


def feature_schema_sha256() -> str:
    return hashlib.sha256("\n".join([FEATURE_SCHEMA_VERSION, *feature_names()]).encode("utf-8")).hexdigest()


def auroc(labels: Sequence[int], scores: Sequence[float]) -> float:
    positives, negatives = sum(labels), len(labels) - sum(labels)
    if not positives or not negatives:
        return 0.5
    ordered = sorted(zip(scores, labels), key=lambda row: row[0])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        rank_sum += ((index + 1 + end) / 2.0) * sum(label for _, label in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def auprc(labels: Sequence[int], scores: Sequence[float]) -> float:
    positives = sum(labels)
    if not positives:
        return 0.0
    ordered = sorted(zip(scores, labels), reverse=True)
    tp = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ordered, start=1):
        tp += label
        if label:
            precision_sum += tp / rank
    return precision_sum / positives


def ece(labels: Sequence[int], probabilities: Sequence[float], bins: int = 10) -> float:
    total, error = len(labels), 0.0
    for index in range(bins):
        left, right = index / bins, (index + 1) / bins
        members = [(y, p) for y, p in zip(labels, probabilities) if left <= p < right or index == bins - 1 and p == 1.0]
        if members:
            error += len(members) / total * abs(sum(y for y, _ in members) / len(members) - sum(p for _, p in members) / len(members))
    return error


def risk_coverage(labels: Sequence[int], probabilities: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(zip(probabilities, labels), reverse=True)
    points, risks = [], []
    for count in range(1, len(ordered) + 1):
        risk = 1.0 - sum(label for _, label in ordered[:count]) / count
        risks.append(risk)
        points.append({"coverage": count / len(ordered), "risk": risk})
    aurc = sum(risks) / len(risks)
    requested = {}
    for coverage in (0.4, 0.6, 0.8, 1.0):
        count = max(1, math.ceil(len(ordered) * coverage))
        requested[str(coverage)] = 1.0 - sum(label for _, label in ordered[:count]) / count
    return {"aurc": aurc, "risks": requested, "points": points}


def classification_metrics(labels: Sequence[int], probabilities: Sequence[float], threshold: float) -> dict[str, Any]:
    predictions = [int(value >= threshold) for value in probabilities]
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "auroc": auroc(labels, probabilities), "auprc": auprc(labels, probabilities),
        "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "accuracy": sum(y == p for y, p in zip(labels, predictions)) / len(labels),
        "ece_10bin": ece(labels, probabilities), "risk_coverage": risk_coverage(labels, probabilities),
    }
