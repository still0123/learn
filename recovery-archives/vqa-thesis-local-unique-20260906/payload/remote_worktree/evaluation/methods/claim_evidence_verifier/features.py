"""Deterministic, leakage-safe features for paired AdsQA candidate answers.

Ground-truth answers and judge scores live under ``supervision`` in a pair record.
This module deliberately never reads that field. At inference time it consumes
only the question, ASR excerpt, two generated answers, and frozen trace scores.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Iterable, Mapping, Sequence


FEATURE_SCHEMA_VERSION = "adsqa_claim_evidence_features_v1"
DEFAULT_HASH_DIM = 256
CATEGORIES = (
    "brand",
    "cta",
    "narrative_other",
    "ocr_text",
    "price_promo",
    "speech_audio",
    "visual_detail",
)
SOURCES = ("raw_uniform", "innovation1_mmr32")

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.'%-][a-z0-9]+)?", re.IGNORECASE)
_ANSWER_RE = re.compile(r"(?:^|\n)\s*(?:3\s*[.)]\s*)?\[?answer\]?\s*:\s*", re.IGNORECASE)
_CRITICAL_RE = re.compile(r"(?:[$£€]\s*\d+(?:[.,]\d+)?)|(?:\b\d+(?:[.,]\d+)?%?\b)", re.IGNORECASE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "what", "when", "which", "who", "why", "with",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def extract_answer_claim(answer: str) -> str:
    """Return the final answer claim, excluding verbose observation/reasoning text."""
    text = str(answer or "").strip()
    matches = list(_ANSWER_RE.finditer(text))
    if matches:
        return text[matches[-1].end():].strip()
    nonempty = [line.strip() for line in text.splitlines() if line.strip()]
    return nonempty[-1] if nonempty else text


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_RE.findall(str(text or ""))
        if len(token) > 1 and token.lower() not in _STOPWORDS
    ]


def _token_set(text: str) -> set[str]:
    return set(_tokens(text))


def _overlap(left: str, right: str) -> tuple[float, float, float]:
    a, b = _token_set(left), _token_set(right)
    if not a or not b:
        return 0.0, 0.0, 0.0
    shared = len(a & b)
    return shared / len(a | b), shared / len(a), shared / len(b)


def _critical_recall(candidate: str, evidence: str) -> float:
    candidate_values = {value.replace(" ", "").lower() for value in _CRITICAL_RE.findall(candidate)}
    if not candidate_values:
        return 1.0
    evidence_values = {value.replace(" ", "").lower() for value in _CRITICAL_RE.findall(evidence)}
    return len(candidate_values & evidence_values) / len(candidate_values)


def _moments(values: Sequence[Any]) -> tuple[float, float, float, float, float]:
    numbers = [_safe_float(value) for value in values]
    if not numbers:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    mean = sum(numbers) / len(numbers)
    variance = sum((value - mean) ** 2 for value in numbers) / len(numbers)
    ordered = sorted(numbers, reverse=True)
    top_count = min(4, len(ordered))
    return mean, math.sqrt(variance), min(numbers), max(numbers), sum(ordered[:top_count]) / top_count


def _hash_slot(value: str, dimension: int) -> tuple[int, float]:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    slot = int.from_bytes(digest[:8], "big") % dimension
    sign = 1.0 if digest[8] & 1 else -1.0
    return slot, sign


def _candidate_hash_features(
    candidate: str,
    question_tokens: set[str],
    evidence_tokens: set[str],
    dimension: int,
) -> list[float]:
    vector = [0.0] * dimension
    tokens = _tokens(candidate)
    for token in tokens:
        keys = [f"claim={token}"]
        if token in question_tokens:
            keys.append(f"question_claim={token}")
        if token in evidence_tokens:
            keys.append(f"evidence_claim={token}")
        for key in keys:
            slot, sign = _hash_slot(key, dimension)
            vector[slot] += sign
    for left, right in zip(tokens, tokens[1:]):
        slot, sign = _hash_slot(f"claim_bigram={left}_{right}", dimension)
        vector[slot] += 0.5 * sign
    scale = max(1.0, math.sqrt(len(tokens)))
    return [value / scale for value in vector]


def _numeric_feature_names() -> list[str]:
    names = [
        "support_initial_positive", "support_initial_counterfactual", "support_delta",
        "support_initial_rescue", "support_rescue_rescue", "support_gain",
        "support_gain_abs", "counterfactual_delta_abs",
        "relevance_mean", "relevance_std", "relevance_min", "relevance_max", "relevance_top4_mean",
        "destroy_fraction", "asr_present", "asr_log_length", "question_log_length",
        "initial_claim_log_length", "rescue_claim_log_length", "claim_length_delta",
        "claim_jaccard", "claim_initial_containment", "claim_rescue_containment",
        "question_initial_jaccard", "question_rescue_jaccard", "question_overlap_delta",
        "asr_initial_jaccard", "asr_rescue_jaccard", "asr_overlap_delta",
        "initial_critical_recall", "rescue_critical_recall", "critical_recall_delta",
        "claims_identical", "reason_low_positive_support", "reason_counterfactual_insensitive",
    ]
    names.extend(f"category={category}" for category in CATEGORIES)
    names.extend(f"source={source}" for source in SOURCES)
    return names


def feature_names(hash_dim: int = DEFAULT_HASH_DIM) -> list[str]:
    if hash_dim <= 0:
        raise ValueError("hash_dim must be positive")
    return _numeric_feature_names() + [f"claim_hash_delta_{index:04d}" for index in range(hash_dim)]


def build_feature_vector(record: Mapping[str, Any], hash_dim: int = DEFAULT_HASH_DIM) -> list[float]:
    """Build an ordered feature vector without consulting supervision fields."""
    question = str(record.get("question", ""))
    asr = str(record.get("asr_excerpt", ""))
    initial_claim = extract_answer_claim(str(record.get("initial_answer", "")))
    rescue_claim = extract_answer_claim(str(record.get("rescue_answer", "")))
    support = record.get("support") or {}
    initial_positive = _safe_float(support.get("initial_on_positive"))
    initial_counterfactual = _safe_float(support.get("initial_on_counterfactual"))
    initial_rescue = _safe_float(support.get("initial_on_rescue"))
    rescue_rescue = _safe_float(support.get("rescue_on_rescue"))
    support_delta = initial_positive - initial_counterfactual
    support_gain = rescue_rescue - initial_rescue
    relevance = record.get("relevance_scores") or []
    relevance_stats = _moments(relevance)
    counterfactual = record.get("counterfactual") or {}
    destroyed = counterfactual.get("destroyed_input_indices") or []
    view_count = max(1, int(_safe_float(counterfactual.get("view_count_before"), len(relevance) or 1)))
    rescue = record.get("rescue") or {}
    reasons = {str(value) for value in rescue.get("reasons", [])}

    claim_overlap = _overlap(initial_claim, rescue_claim)
    q_initial = _overlap(question, initial_claim)[0]
    q_rescue = _overlap(question, rescue_claim)[0]
    asr_initial = _overlap(asr, initial_claim)[0]
    asr_rescue = _overlap(asr, rescue_claim)[0]
    critical_initial = _critical_recall(initial_claim, asr)
    critical_rescue = _critical_recall(rescue_claim, asr)
    numeric = [
        initial_positive, initial_counterfactual, support_delta,
        initial_rescue, rescue_rescue, support_gain,
        abs(support_gain), abs(support_delta),
        *relevance_stats,
        len(destroyed) / view_count,
        float(bool(asr.strip())), math.log1p(len(asr)), math.log1p(len(question)),
        math.log1p(len(initial_claim)), math.log1p(len(rescue_claim)),
        math.log1p(len(rescue_claim)) - math.log1p(len(initial_claim)),
        *claim_overlap,
        q_initial, q_rescue, q_rescue - q_initial,
        asr_initial, asr_rescue, asr_rescue - asr_initial,
        critical_initial, critical_rescue, critical_rescue - critical_initial,
        float(initial_claim.casefold() == rescue_claim.casefold()),
        float("low_positive_support" in reasons),
        float("counterfactual_insensitive" in reasons),
    ]
    category = str(record.get("category", "narrative_other"))
    source = str(record.get("source_method", "raw_uniform"))
    numeric.extend(float(category == value) for value in CATEGORIES)
    numeric.extend(float(source == value) for value in SOURCES)

    question_tokens = _token_set(question)
    evidence_tokens = _token_set(asr)
    initial_hash = _candidate_hash_features(initial_claim, question_tokens, evidence_tokens, hash_dim)
    rescue_hash = _candidate_hash_features(rescue_claim, question_tokens, evidence_tokens, hash_dim)
    vector = numeric + [right - left for left, right in zip(initial_hash, rescue_hash)]
    expected = len(feature_names(hash_dim))
    if len(vector) != expected:
        raise RuntimeError(f"feature schema drift: {len(vector)} != {expected}")
    return vector


def feature_schema_sha256(hash_dim: int = DEFAULT_HASH_DIM) -> str:
    payload = "\n".join([FEATURE_SCHEMA_VERSION, *feature_names(hash_dim)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
