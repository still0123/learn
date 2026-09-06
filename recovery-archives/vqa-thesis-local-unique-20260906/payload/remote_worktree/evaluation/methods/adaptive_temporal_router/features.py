"""Leakage-safe, pre-answer features for Raw32/MMR32 routing."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping, Sequence


FEATURE_SCHEMA_VERSION = "adsqa_adaptive_temporal_router_features_v1"
DEFAULT_HASH_DIM = 64
PRIMARY_TYPES = ("Type_1", "Type_2", "Type_3", "Type_4", "Type_5")
INTENT_PATTERNS = {
    "emotion": r"\b(emotion|emotional|feel|feeling|mood|evoke)\b",
    "target_audience": r"\b(target|audience|viewer|consumer|beneficiar)\w*\b",
    "cta": r"\b(call.to.action|encourage|participat|join|visit|buy|purchase)\w*\b",
    "visual_detail": r"\b(visual|image|object|element|component|design|appearance)\w*\b",
    "metaphor": r"\b(metaphor|symbol|symbolize|represent|imagery)\w*\b",
    "narrative": r"\b(story|storyline|narrative|journey|theme|plot)\w*\b",
    "product": r"\b(product|feature|brand|service|campaign|advertis)\w*\b",
    "speech_audio": r"\b(say|says|said|voice|audio|music|sound|dialogue|narrat)\w*\b",
    "text_ocr": r"\b(text|word|caption|logo|price|discount|offer|slogan)\w*\b",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.'%-][a-z0-9]+)?", re.IGNORECASE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "what", "when", "which", "who", "why", "with",
}


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_RE.findall(str(text or ""))
        if len(token) > 1 and token.lower() not in _STOPWORDS
    ]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _moments(values: Sequence[Any]) -> list[float]:
    numbers = [_safe_float(value) for value in values]
    if not numbers:
        return [0.0] * 7
    mean = sum(numbers) / len(numbers)
    variance = sum((value - mean) ** 2 for value in numbers) / len(numbers)
    ordered = sorted(numbers, reverse=True)
    shifted = [value - min(numbers) + 1e-8 for value in numbers]
    total = sum(shifted)
    probabilities = [value / total for value in shifted]
    entropy = -sum(value * math.log(value) for value in probabilities)
    concentration = 1.0 - entropy / math.log(len(numbers)) if len(numbers) > 1 else 1.0
    margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]
    return [
        mean,
        math.sqrt(variance),
        min(numbers),
        max(numbers),
        sum(ordered[: min(4, len(ordered))]) / min(4, len(ordered)),
        concentration,
        margin,
    ]


def _selected(values: Sequence[Any], ranks: Sequence[int]) -> list[float]:
    numbers = [_safe_float(value) for value in values]
    chosen = [numbers[index] for index in ranks if 0 <= int(index) < len(numbers)]
    return _moments(chosen)


def _hash_features(question: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    tokens = _tokens(question)
    keys = [f"token={token}" for token in tokens]
    keys.extend(f"bigram={left}_{right}" for left, right in zip(tokens, tokens[1:]))
    for key in keys:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        slot = int.from_bytes(digest[:8], "big") % dimension
        vector[slot] += 1.0 if digest[8] & 1 else -1.0
    scale = max(1.0, math.sqrt(len(keys)))
    return [value / scale for value in vector]


def _rank_distance(left: Sequence[int], right: Sequence[int], count: int) -> float:
    if not left or not right:
        return 0.0
    return sum(min(abs(int(value) - int(other)) for other in right) for value in left) / (
        len(left) * max(1, count - 1)
    )


def _gap_features(ranks: Sequence[int], count: int) -> list[float]:
    ordered = sorted(int(value) for value in ranks)
    if not ordered or count <= 1:
        return [0.0, 0.0]
    boundaries = [0, *ordered, count - 1]
    gaps = [right - left for left, right in zip(boundaries, boundaries[1:])]
    mean = sum(gaps) / len(gaps)
    variance = sum((value - mean) ** 2 for value in gaps) / len(gaps)
    return [max(gaps) / (count - 1), math.sqrt(variance) / (count - 1)]


def _numeric_feature_names() -> list[str]:
    names = [
        "question_log_length", "question_log_token_count", "asr_present", "asr_log_length",
        "question_asr_reliability", "raw_mmr_overlap", "replacement_fraction",
        "mmr_to_raw_rank_distance", "raw_to_mmr_rank_distance",
        "mmr_max_gap", "mmr_gap_std", "raw_max_gap", "raw_gap_std",
        "bin_count_std", "bin_count_min", "bin_count_max",
        "duplicate_similarity_mean", "duplicate_similarity_max",
        "coverage_deficit_mean", "coverage_deficit_max",
    ]
    moment_names = ("mean", "std", "min", "max", "top4_mean", "concentration", "top_margin")
    for component in ("question", "asr", "scene", "base"):
        names.extend(f"{component}_all_{name}" for name in moment_names)
        names.extend(f"{component}_mmr_{name}" for name in moment_names)
        names.extend(f"{component}_raw_{name}" for name in moment_names)
        names.extend(f"{component}_mmr_minus_raw_{name}" for name in moment_names)
    names.extend(f"primary_type={value}" for value in PRIMARY_TYPES)
    names.extend(f"intent={value}" for value in INTENT_PATTERNS)
    return names


def feature_names(hash_dim: int = DEFAULT_HASH_DIM) -> list[str]:
    if hash_dim <= 0:
        raise ValueError("hash_dim must be positive")
    return _numeric_feature_names() + [f"question_hash_{index:03d}" for index in range(hash_dim)]


def build_feature_vector(record: Mapping[str, Any], hash_dim: int = DEFAULT_HASH_DIM) -> list[float]:
    """Build features without consulting the record's supervision section."""
    question = str(record.get("question", ""))
    primary_type = str(record.get("primary_type", ""))
    inputs = record.get("router_inputs") or {}
    trace = inputs.get("selector_trace") or {}
    selected = [int(value) for value in inputs.get("mmr_selected_candidate_ranks") or []]
    raw = [int(value) for value in inputs.get("raw_candidate_ranks") or []]
    candidate_count = int(_safe_float(inputs.get("candidate_count"), 64))
    overlap = len(set(selected) & set(raw)) / max(1, len(set(raw)))
    bin_counts = [_safe_float(value) for value in trace.get("bin_counts") or []]
    bin_mean = sum(bin_counts) / len(bin_counts) if bin_counts else 0.0
    duplicate = [
        _safe_float(row.get("duplicate_similarity"))
        for row in trace.get("decision_trace") or []
        if row.get("duplicate_similarity") is not None
    ]
    coverage = [
        _safe_float(row.get("coverage_deficit"))
        for row in trace.get("decision_trace") or []
        if row.get("coverage_deficit") is not None
    ]
    tokens = _tokens(question)
    numeric = [
        math.log1p(len(question)), math.log1p(len(tokens)),
        float(bool(inputs.get("asr_present"))), math.log1p(int(_safe_float(inputs.get("asr_length")))),
        _safe_float(trace.get("question_asr_reliability")), overlap, 1.0 - overlap,
        _rank_distance(selected, raw, candidate_count), _rank_distance(raw, selected, candidate_count),
        *_gap_features(selected, candidate_count), *_gap_features(raw, candidate_count),
        math.sqrt(sum((value - bin_mean) ** 2 for value in bin_counts) / len(bin_counts)) if bin_counts else 0.0,
        min(bin_counts) if bin_counts else 0.0, max(bin_counts) if bin_counts else 0.0,
        sum(duplicate) / len(duplicate) if duplicate else 0.0, max(duplicate) if duplicate else 0.0,
        sum(coverage) / len(coverage) if coverage else 0.0, max(coverage) if coverage else 0.0,
    ]
    components = (
        trace.get("question_component") or [],
        trace.get("asr_component") or [],
        trace.get("scene_change_component") or [],
        trace.get("base_score") or inputs.get("candidate_scores") or [],
    )
    for values in components:
        all_stats = _moments(values)
        mmr_stats = _selected(values, selected)
        raw_stats = _selected(values, raw)
        numeric.extend(all_stats)
        numeric.extend(mmr_stats)
        numeric.extend(raw_stats)
        numeric.extend(right - left for left, right in zip(raw_stats, mmr_stats))
    numeric.extend(float(primary_type == value) for value in PRIMARY_TYPES)
    numeric.extend(float(bool(re.search(pattern, question, re.IGNORECASE))) for pattern in INTENT_PATTERNS.values())
    vector = numeric + _hash_features(question, hash_dim)
    expected = len(feature_names(hash_dim))
    if len(vector) != expected or any(not math.isfinite(value) for value in vector):
        raise RuntimeError(f"invalid feature vector: size={len(vector)} expected={expected}")
    return vector


def feature_schema_sha256(hash_dim: int = DEFAULT_HASH_DIM) -> str:
    payload = "\n".join([FEATURE_SCHEMA_VERSION, *feature_names(hash_dim)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

