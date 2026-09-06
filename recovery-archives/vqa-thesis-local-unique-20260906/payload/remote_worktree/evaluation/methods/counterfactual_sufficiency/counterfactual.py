"""Pure counterfactual and fixed-budget rescue operations.

The functions in this module deliberately avoid model-specific state. This keeps
the evidence perturbation, rescue budget, and decision policy independently
testable from Qwen inference.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Sequence, Tuple

from PIL import Image


CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "ocr_text": (
        "text", "word", "written", "displayed", "caption", "subtitle",
        "screen", "number", "url", "website", "small print", "disclaimer",
    ),
    "cta": (
        "call to action", "buy", "purchase", "download", "install", "order",
        "subscribe", "sign up", "visit", "scan", "click",
    ),
    "price_promo": (
        "price", "discount", "offer", "deal", "sale", "promotion", "cost",
        "free", "percent", "%", "$", "£", "€",
    ),
    "brand": ("brand", "logo", "product name", "company", "packaging", "package"),
    "speech_audio": (
        "voiceover", "narrator", "say", "says", "said", "spoken", "audio",
        "sound", "music", "hear", "heard",
    ),
    "visual_detail": (
        "visual", "shown", "image", "scene", "color", "object", "symbol",
        "appearance", "look", "depict",
    ),
}

_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def question_stem(question: str) -> str:
    """Strip the legacy training-set Voiceover prefix from a question."""
    text = str(question or "").strip()
    if "Question:" in text:
        text = text.split("Question:", 1)[1].strip()
    return text


def categorize_question(question: str) -> str:
    """Assign one deterministic evidence-oriented category."""
    stem = question_stem(question).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in stem for keyword in keywords):
            return category
    return "narrative_other"


def _tokens(text: str) -> set[str]:
    stop = {
        "a", "an", "and", "are", "as", "at", "be", "by", "does", "for",
        "from", "how", "in", "is", "it", "of", "on", "the", "this", "to",
        "what", "which", "who", "why", "with",
    }
    return {token for token in _WORD_RE.findall(str(text).lower()) if len(token) > 2 and token not in stop}


def select_asr_excerpt(asr_text: str, question: str, max_chars: int = 600) -> str:
    """Select a deterministic question-relevant ASR excerpt without an LLM."""
    text = str(asr_text or "").strip()
    if len(text) <= max_chars:
        return text
    query_tokens = _tokens(question)
    # AdsQA often asks with a paraphrase (for example, "discount") while the
    # spoken evidence uses a concrete realization (for example, "percent").
    # Category terms supply a compact, deterministic synonym bridge.
    query_tokens.update(_tokens(" ".join(CATEGORY_KEYWORDS.get(categorize_question(question), ()))))
    segments = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()]
    if not segments:
        return text[:max_chars]
    ranked = sorted(
        enumerate(segments),
        key=lambda row: (-len(_tokens(row[1]) & query_tokens), row[0]),
    )
    chosen: List[Tuple[int, str]] = []
    used = 0
    for index, segment in ranked:
        extra = len(segment) + (1 if chosen else 0)
        if chosen and used + extra > max_chars:
            continue
        chosen.append((index, segment))
        used += extra
        if used >= max_chars or len(chosen) >= 4:
            break
    if not chosen:
        return text[:max_chars]
    return " ".join(segment for _, segment in sorted(chosen))[:max_chars]


def _rank_indices(scores: Sequence[float], count: int, reverse: bool = True) -> List[int]:
    if count < 0 or count > len(scores):
        raise ValueError(f"invalid rank count {count} for {len(scores)} scores")
    return sorted(range(len(scores)), key=lambda index: (float(scores[index]), -index), reverse=reverse)[:count]


def make_visual_counterfactual(
    frames: Sequence[Image.Image],
    relevance_scores: Sequence[float],
    destroy_count: int = 4,
    mosaic_side: int = 14,
) -> Tuple[List[Image.Image], Dict[str, Any]]:
    """Remove fine evidence from the most relevant views while preserving layout."""
    if len(frames) != len(relevance_scores):
        raise ValueError("frames and relevance_scores must have equal length")
    if not 0 < destroy_count < len(frames):
        raise ValueError("destroy_count must be between 1 and len(frames)-1")
    destroyed = sorted(_rank_indices(relevance_scores, destroy_count))
    destroyed_set = set(destroyed)
    output: List[Image.Image] = []
    for index, frame in enumerate(frames):
        image = frame.convert("RGB")
        if index in destroyed_set:
            image = image.resize((mosaic_side, mosaic_side), Image.Resampling.BILINEAR).resize(
                frame.size, Image.Resampling.NEAREST
            )
        output.append(image)
    return output, {
        "perturbation": "top_relevance_mosaic_v1",
        "destroyed_input_indices": destroyed,
        "destroy_count": destroy_count,
        "mosaic_side": mosaic_side,
        "view_count_before": len(frames),
        "view_count_after": len(output),
    }


def build_rescue_sequence(
    frames: Sequence[Image.Image],
    relevance_scores: Sequence[float],
    cropper: Callable[[Image.Image, int], Tuple[Image.Image, Dict[str, Any]]],
    local_count: int = 8,
) -> Tuple[List[Image.Image], Dict[str, Any]]:
    """Build 24 context + 8 local evidence views under a fixed 32-view budget."""
    if len(frames) != len(relevance_scores):
        raise ValueError("frames and relevance_scores must have equal length")
    if not 0 < local_count < len(frames):
        raise ValueError("local_count must be between 1 and len(frames)-1")
    evidence_indices = sorted(_rank_indices(relevance_scores, local_count))
    dropped_indices = sorted(_rank_indices(relevance_scores, local_count, reverse=False))
    evidence_set = set(evidence_indices)
    dropped_set = set(dropped_indices)
    output: List[Image.Image] = []
    plan: List[Dict[str, Any]] = []
    crop_records: List[Dict[str, Any]] = []
    for index, frame in enumerate(frames):
        if index not in dropped_set:
            output.append(frame.convert("RGB"))
            plan.append({"input_index": len(output) - 1, "view_type": "context", "source_input_index": index})
        if index in evidence_set:
            crop, crop_meta = cropper(frame.convert("RGB"), index)
            output.append(crop.convert("RGB"))
            plan.append({"input_index": len(output) - 1, "view_type": "local_rescue", "source_input_index": index})
            crop_records.append({"source_input_index": index, **crop_meta})
    if len(output) != len(frames):
        raise RuntimeError(f"rescue budget drift: {len(output)} != {len(frames)}")
    return output, {
        "policy": "fixed_budget_context24_local8_v1",
        "view_budget": len(frames),
        "context_count": len(frames) - local_count,
        "local_count": local_count,
        "evidence_indices": evidence_indices,
        "dropped_indices": dropped_indices,
        "visual_plan": plan,
        "crop_records": crop_records,
    }


def should_rescue(
    support_plus: float,
    support_minus: float,
    support_threshold: float = 0.60,
    sensitivity_margin: float = 0.08,
) -> Tuple[bool, List[str]]:
    """Decide whether the initial evidence-answer pair requires one rescue."""
    reasons: List[str] = []
    if support_plus < support_threshold:
        reasons.append("low_positive_support")
    if support_plus - support_minus < sensitivity_margin:
        reasons.append("counterfactual_insensitive")
    return bool(reasons), reasons


def choose_corrected_answer(
    initial_answer: str,
    rescue_answer: str,
    initial_support_on_rescue: float,
    rescue_support_on_rescue: float,
    switch_margin: float = 0.05,
) -> Tuple[str, Dict[str, Any]]:
    """Switch only when the rescue answer has a clear evidence-support advantage."""
    gain = float(rescue_support_on_rescue) - float(initial_support_on_rescue)
    switched = bool(str(rescue_answer).strip()) and gain >= switch_margin
    return (rescue_answer if switched else initial_answer), {
        "switched": switched,
        "support_gain": gain,
        "switch_margin": switch_margin,
    }
