"""Leakage-safe features for claim evidence intervention triplets."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping


FEATURE_SCHEMA_VERSION = "adsqa_claim_evidence_features_v2"
STATES = ("full", "target_removed", "control_removed")
LABELS = ("supported", "refuted", "insufficient")
MODALITIES = ("visual", "asr", "ocr")
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_ANSWER_RE = re.compile(r"(?:^|\n)\s*(?:3\s*[.)]\s*)?\[?answer\]?\s*:\s*", re.IGNORECASE)


def extract_answer_claim(answer: Any) -> str:
    text = str(answer or "").strip()
    matches = list(_ANSWER_RE.finditer(text))
    if matches:
        return text[matches[-1].end():].strip()
    nonempty = [line.strip() for line in text.splitlines() if line.strip()]
    return nonempty[-1] if nonempty else text


def _safe_probability(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) and 0.0 <= number <= 1.0 else 0.0


def _tokens(value: Any) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(str(value or "")) if len(token) > 1}


def _jaccard(left: Any, right: Any) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def feature_names() -> list[str]:
    names = []
    for state in STATES:
        names.extend(f"{state}_{label}" for label in LABELS)
    names.extend([
        "target_support_drop", "control_support_drop", "necessity_contrast",
        "target_insufficient_gain", "control_insufficient_gain",
        "question_claim_jaccard", "asr_claim_jaccard",
        "question_log_length", "claim_log_length", "asr_log_length",
        "intervention_cost", "cost_ratio", "asr_present", "ocr_present",
    ])
    names.extend(f"modality={modality}" for modality in MODALITIES)
    return names


def build_feature_vector(record: Mapping[str, Any]) -> list[float]:
    """Build features without reading oracle annotations or supervision."""
    scores = record.get("scores") or {}
    values = []
    for state in STATES:
        state_scores = scores.get(state) or {}
        values.extend(_safe_probability(state_scores.get(label)) for label in LABELS)
    full = scores.get("full") or {}
    target = scores.get("target_removed") or {}
    control = scores.get("control_removed") or {}
    full_support = _safe_probability(full.get("supported"))
    target_support = _safe_probability(target.get("supported"))
    control_support = _safe_probability(control.get("supported"))
    full_insufficient = _safe_probability(full.get("insufficient"))
    target_insufficient = _safe_probability(target.get("insufficient"))
    control_insufficient = _safe_probability(control.get("insufficient"))
    metadata = record.get("metadata") or {}
    target_cost = max(0.0, float(metadata.get("target_cost", 0.0) or 0.0))
    control_cost = max(0.0, float(metadata.get("control_cost", 0.0) or 0.0))
    question = str(record.get("question", ""))
    claim = str(record.get("claim", ""))
    asr = str(record.get("asr_excerpt", ""))
    values.extend([
        full_support - target_support,
        full_support - control_support,
        control_support - target_support,
        target_insufficient - full_insufficient,
        control_insufficient - full_insufficient,
        _jaccard(question, claim),
        _jaccard(asr, claim),
        math.log1p(len(question)), math.log1p(len(claim)), math.log1p(len(asr)),
        target_cost,
        control_cost / target_cost if target_cost else 0.0,
        float(bool(asr.strip())),
        float(bool(metadata.get("ocr_present"))),
    ])
    modality = str(metadata.get("modality", "visual"))
    values.extend(float(modality == value) for value in MODALITIES)
    if len(values) != len(feature_names()):
        raise RuntimeError("v2 feature schema drift")
    return values


def feature_schema_sha256() -> str:
    payload = "\n".join([FEATURE_SCHEMA_VERSION, *feature_names()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
