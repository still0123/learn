"""Pure utilities for dynamic audio-visual response and budgeted crops.

This module deliberately has no torch/transformers dependency. The inference
entrypoint supplies model response maps; these functions normalize, fuse, decode,
and allocate them under a fixed visual-image budget.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


EPS = 1e-8


@dataclass(frozen=True)
class ASRSegment:
    start: float
    end: float
    text: str
    confidence: float = 1.0

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2.0


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_asr(raw: Any) -> dict[str, Any]:
    """Normalize string or timestamped ASR into a stable evidence structure."""
    if isinstance(raw, str):
        text = raw.strip()
        return {
            "transcript": text,
            "segments": [],
            "has_timestamps": False,
            "mode": "global_text" if text else "missing",
        }

    source_segments: Iterable[Any] = []
    transcript = ""
    if isinstance(raw, Mapping):
        transcript = str(raw.get("text", raw.get("transcript", "")) or "").strip()
        candidate = raw.get("segments", raw.get("chunks", []))
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            source_segments = candidate
        elif any(key in raw for key in ("start", "start_time", "begin")):
            source_segments = [raw]
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        source_segments = raw

    segments: list[ASRSegment] = []
    for item in source_segments:
        if not isinstance(item, Mapping):
            continue
        start = _number(item.get("start", item.get("start_time", item.get("begin"))))
        end = _number(item.get("end", item.get("end_time", item.get("finish"))))
        text = str(item.get("text", item.get("transcript", item.get("word", ""))) or "").strip()
        confidence = _number(item.get("confidence", item.get("score", 1.0)), 1.0) or 0.0
        if start is None or end is None or end < start or not text:
            continue
        segments.append(ASRSegment(start=start, end=end, text=text, confidence=max(0.0, confidence)))

    segments.sort(key=lambda segment: (segment.start, segment.end))
    if not transcript:
        transcript = " ".join(segment.text for segment in segments).strip()
    return {
        "transcript": transcript,
        "segments": [asdict(segment) for segment in segments],
        "has_timestamps": bool(segments),
        "mode": "timestamped_segments" if segments else "missing",
    }


def windowed_asr_text(
    evidence: Mapping[str, Any],
    frame_time: float | None,
    radius: float,
    offset: float = 0.0,
) -> tuple[str, dict[str, Any]]:
    """Return ASR near a frame; fall back explicitly when timestamps are absent."""
    transcript = str(evidence.get("transcript", "") or "")
    segments = evidence.get("segments", []) or []
    if frame_time is None or not segments:
        return transcript, {
            "mode": "global_fallback",
            "frame_time": frame_time,
            "offset": float(offset),
            "segment_indices": [],
        }

    radius = max(float(radius), 0.0)
    selected: list[tuple[int, Mapping[str, Any], float]] = []
    for index, segment in enumerate(segments):
        start = _number(segment.get("start"), 0.0) or 0.0
        end = _number(segment.get("end"), start) or start
        midpoint = (start + end) / 2.0 + float(offset)
        distance = abs(float(frame_time) - midpoint)
        if distance <= radius:
            selected.append((index, segment, distance))

    if not selected and segments:
        nearest = min(
            enumerate(segments),
            key=lambda pair: abs(
                float(frame_time)
                - (((_number(pair[1].get("start"), 0.0) or 0.0) + (_number(pair[1].get("end"), 0.0) or 0.0)) / 2.0 + float(offset))
            ),
        )
        segment = nearest[1]
        midpoint = ((_number(segment.get("start"), 0.0) or 0.0) + (_number(segment.get("end"), 0.0) or 0.0)) / 2.0 + float(offset)
        if abs(float(frame_time) - midpoint) <= max(2.0 * radius, 1.0):
            selected = [(nearest[0], segment, abs(float(frame_time) - midpoint))]

    text = " ".join(str(segment.get("text", "")) for _, segment, _ in selected).strip()
    return text, {
        "mode": "timestamp_window",
        "frame_time": float(frame_time),
        "offset": float(offset),
        "radius": radius,
        "segment_indices": [index for index, _, _ in selected],
        "distances": [round(distance, 4) for _, _, distance in selected],
    }


def select_topk_with_temporal_coverage(
    score_values: Sequence[float],
    top_k: int,
    coverage_bins: int,
) -> tuple[list[int], dict[str, Any]]:
    """Select high-scoring rows while reserving one anchor per temporal bin."""
    scores = [float(value) for value in score_values]
    count = len(scores)
    if count == 0:
        return [], {"mode": "empty", "coverage_bins": 0, "anchor_rows": []}

    requested_top_k = min(max(int(top_k), 1), count)
    requested_bins = min(max(int(coverage_bins), 0), requested_top_k, count)
    score_order = sorted(range(count), key=lambda row: (scores[row], row), reverse=True)
    if requested_bins == 0 or requested_top_k == count:
        selected = sorted(score_order[:requested_top_k])
        return selected, {
            "mode": "score_topk",
            "coverage_bins": 0,
            "anchor_rows": [],
            "selected_rows": selected,
        }

    rows_by_bin: list[list[int]] = [[] for _ in range(requested_bins)]
    for row in range(count):
        bin_index = min(requested_bins - 1, row * requested_bins // count)
        rows_by_bin[bin_index].append(row)

    anchor_rows = [
        max(rows, key=lambda row: (scores[row], row))
        for rows in rows_by_bin
        if rows
    ]
    selected_set = set(anchor_rows)
    for row in score_order:
        if len(selected_set) >= requested_top_k:
            break
        selected_set.add(row)
    selected = sorted(selected_set)
    return selected, {
        "mode": "score_topk_temporal_coverage",
        "coverage_bins": requested_bins,
        "anchor_rows": sorted(anchor_rows),
        "selected_rows": selected,
    }


def question_modality_priors(question: str) -> dict[str, float]:
    """Return compact question-conditioned priors for visual/audio/text evidence."""
    text = (question or "").lower()
    scores = {"question": 0.60, "audio": 0.25, "ocr": 0.15}
    audio_terms = ("say", "said", "voice", "voiceover", "narrator", "spoken", "hear", "audio", "sound", "music")
    ocr_terms = ("text", "word", "written", "caption", "subtitle", "logo", "brand", "price", "discount", "number", "url", "website", "disclaimer", "cta")
    context_terms = ("emotion", "mood", "audience", "message", "theme", "strategy", "metaphor", "portray", "visual")
    if any(term in text for term in audio_terms):
        scores["audio"] += 0.45
    if any(term in text for term in ocr_terms):
        scores["ocr"] += 0.50
    if any(term in text for term in context_terms):
        scores["question"] += 0.25
    total = sum(scores.values()) or 1.0
    return {key: value / total for key, value in scores.items()}


def normalize_response(response: np.ndarray | Sequence[float]) -> np.ndarray:
    array = np.asarray(response, dtype=np.float32)
    if array.size == 0:
        return array
    minimum = float(np.nanmin(array))
    maximum = float(np.nanmax(array))
    if not math.isfinite(minimum) or not math.isfinite(maximum) or maximum - minimum <= EPS:
        return np.zeros_like(array, dtype=np.float32)
    return np.nan_to_num((array - minimum) / (maximum - minimum + EPS), nan=0.0, posinf=1.0, neginf=0.0)


def response_concentration(response: np.ndarray | Sequence[float]) -> float:
    array = normalize_response(response).reshape(-1)
    if array.size <= 1 or float(array.sum()) <= EPS:
        return 0.0
    probability = array / (float(array.sum()) + EPS)
    entropy = -float(np.sum(probability * np.log(probability + EPS)))
    return float(np.clip(1.0 - entropy / math.log(array.size), 0.0, 1.0))


def fuse_dynamic_responses(
    question: str,
    responses: Mapping[str, np.ndarray | Sequence[float] | None],
    reliabilities: Mapping[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fuse modality maps using question prior, map concentration, and reliability."""
    priors = question_modality_priors(question)
    reliabilities = dict(reliabilities or {})
    normalized: dict[str, np.ndarray] = {}
    concentrations: dict[str, float] = {}
    logits: dict[str, float] = {}
    shape: tuple[int, ...] | None = None

    for name in ("question", "audio", "ocr"):
        raw = responses.get(name)
        if raw is None:
            continue
        array = normalize_response(raw)
        if array.size == 0:
            continue
        if shape is None:
            shape = array.shape
        if array.shape != shape:
            raise ValueError(f"response shape mismatch: expected {shape}, got {array.shape} for {name}")
        reliability = float(np.clip(reliabilities.get(name, 1.0), 0.0, 1.0))
        if reliability <= 0.0:
            continue
        concentration = response_concentration(array)
        normalized[name] = array
        concentrations[name] = concentration
        logits[name] = math.log(max(priors.get(name, EPS), EPS)) + 1.5 * concentration + math.log(max(reliability, EPS))

    if not normalized or shape is None:
        raise ValueError("at least one available response map is required")
    maximum = max(logits.values())
    exponentials = {name: math.exp(value - maximum) for name, value in logits.items()}
    denominator = sum(exponentials.values()) or 1.0
    weights = {name: value / denominator for name, value in exponentials.items()}
    fused = np.zeros(shape, dtype=np.float32)
    for name, array in normalized.items():
        fused += float(weights[name]) * array
    fused = normalize_response(fused)
    return fused, {
        "priors": priors,
        "reliabilities": {name: float(reliabilities.get(name, 1.0)) for name in normalized},
        "concentrations": concentrations,
        "weights": weights,
    }


def fuse_consistency_calibrated_responses(
    question: str,
    response_variants: Mapping[str, Sequence[np.ndarray | Sequence[float]] | np.ndarray | None],
    source_reliabilities: Mapping[str, float] | None = None,
    uncertainty_temperature: float = 0.50,
    refinement_weight: float = 0.25,
    reliability_floor: float = 0.35,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, Any]]:
    """Fuse response ensembles with local consistency and bounded refinement.

    Each modality supplies spatially aligned response maps from deterministic
    observations of the same frame. Variance controls a local reliability map;
    high-response uncertain regions retain a small refinement bonus so fragile
    text or logos are inspected rather than silently discarded.
    """
    priors = question_modality_priors(question)
    source_reliabilities = dict(source_reliabilities or {})
    temperature = max(float(uncertainty_temperature), EPS)
    refine_weight = max(float(refinement_weight), 0.0)
    floor = float(np.clip(reliability_floor, 0.0, 1.0))

    means: dict[str, np.ndarray] = {}
    uncertainties: dict[str, np.ndarray] = {}
    reliability_maps: dict[str, np.ndarray] = {}
    concentrations: dict[str, float] = {}
    consistency_scores: dict[str, float] = {}
    effective_reliabilities: dict[str, float] = {}
    modality_stats: dict[str, dict[str, Any]] = {}
    logits: dict[str, float] = {}
    shape: tuple[int, ...] | None = None

    for name in ("question", "audio", "ocr"):
        raw_variants = response_variants.get(name)
        if raw_variants is None:
            continue
        if isinstance(raw_variants, np.ndarray):
            variants = [raw_variants] if raw_variants.ndim == 2 else list(raw_variants)
        else:
            variants = list(raw_variants)
        normalized_variants = [normalize_response(value) for value in variants if np.asarray(value).size]
        if not normalized_variants:
            continue
        for array in normalized_variants:
            if array.ndim != 2:
                raise ValueError(f"response variants must be 2-D for {name}, got {array.shape}")
            if shape is None:
                shape = array.shape
            if array.shape != shape:
                raise ValueError(f"response shape mismatch: expected {shape}, got {array.shape} for {name}")

        source_reliability = float(np.clip(source_reliabilities.get(name, 1.0), 0.0, 1.0))
        if source_reliability <= 0.0:
            continue
        stack = np.stack(normalized_variants).astype(np.float32)
        mean_map = stack.mean(axis=0)
        variance_map = np.mean((stack - mean_map) ** 2, axis=0)
        positive_variance = variance_map[variance_map > EPS]
        variance_scale = float(np.quantile(positive_variance, 0.90)) if positive_variance.size else 0.0
        uncertainty_map = (
            np.clip(variance_map / (variance_scale + EPS), 0.0, 1.0).astype(np.float32)
            if variance_scale > EPS
            else np.zeros_like(mean_map, dtype=np.float32)
        )
        reliability_map = floor + (1.0 - floor) * np.exp(-uncertainty_map / temperature)
        reliability_map = reliability_map.astype(np.float32)
        response_mass = float(mean_map.sum())
        consistency = (
            float(np.sum(mean_map * reliability_map) / (response_mass + EPS))
            if response_mass > EPS
            else float(reliability_map.mean())
        )
        concentration = response_concentration(mean_map)
        effective_reliability = source_reliability * consistency

        means[name] = mean_map
        uncertainties[name] = uncertainty_map
        reliability_maps[name] = reliability_map
        concentrations[name] = concentration
        consistency_scores[name] = consistency
        effective_reliabilities[name] = effective_reliability
        logits[name] = (
            math.log(max(priors.get(name, EPS), EPS))
            + 1.5 * concentration
            + math.log(max(effective_reliability, EPS))
        )
        modality_stats[name] = {
            "variant_count": len(normalized_variants),
            "source_reliability": source_reliability,
            "effective_reliability": effective_reliability,
            "consistency_score": consistency,
            "variance_scale_p90": variance_scale,
            "variance_mean": float(variance_map.mean()),
            "variance_max": float(variance_map.max()),
            "uncertainty_mean": float(uncertainty_map.mean()),
            "uncertainty_max": float(uncertainty_map.max()),
            "local_reliability_mean": float(reliability_map.mean()),
            "local_reliability_min": float(reliability_map.min()),
        }

    if not means or shape is None:
        raise ValueError("at least one available response ensemble is required")

    maximum = max(logits.values())
    exponentials = {name: math.exp(value - maximum) for name, value in logits.items()}
    denominator = sum(exponentials.values()) or 1.0
    weights = {name: value / denominator for name, value in exponentials.items()}

    local_weight_sum = np.zeros(shape, dtype=np.float32)
    reliable_numerator = np.zeros(shape, dtype=np.float32)
    fused_mean = np.zeros(shape, dtype=np.float32)
    fused_uncertainty = np.zeros(shape, dtype=np.float32)
    for name, weight in weights.items():
        local_weight = float(weight) * reliability_maps[name]
        local_weight_sum += local_weight
        reliable_numerator += local_weight * means[name]
        fused_mean += float(weight) * means[name]
        fused_uncertainty += float(weight) * uncertainties[name]

    fused_reliable = reliable_numerator / (local_weight_sum + EPS)
    refinement_priority = normalize_response(fused_mean * fused_uncertainty)
    crop_response = normalize_response(fused_reliable + refine_weight * refinement_priority)
    auxiliary_maps = {
        "fused_mean": normalize_response(fused_mean),
        "fused_reliable": normalize_response(fused_reliable),
        "fused_uncertainty": np.clip(fused_uncertainty, 0.0, 1.0).astype(np.float32),
        "refinement_priority": refinement_priority,
    }
    return crop_response, auxiliary_maps, {
        "mode": "consistency_calibrated",
        "priors": priors,
        "source_reliabilities": {
            name: float(source_reliabilities.get(name, 1.0)) for name in means
        },
        "effective_reliabilities": effective_reliabilities,
        "concentrations": concentrations,
        "consistency_scores": consistency_scores,
        "weights": weights,
        "uncertainty_temperature": temperature,
        "refinement_weight": refine_weight,
        "reliability_floor": floor,
        "modality_stats": modality_stats,
        "fused_stats": {
            "uncertainty_mean": float(auxiliary_maps["fused_uncertainty"].mean()),
            "uncertainty_max": float(auxiliary_maps["fused_uncertainty"].max()),
            "refinement_priority_mean": float(refinement_priority.mean()),
            "refinement_priority_max": float(refinement_priority.max()),
        },
    }


def response_region_statistics(
    response: np.ndarray | Sequence[float],
    bbox_norm: Sequence[float],
) -> dict[str, float]:
    """Summarize a normalized response inside a normalized crop box."""
    heatmap = np.asarray(response, dtype=np.float32)
    if heatmap.ndim != 2 or heatmap.size == 0:
        raise ValueError("response must be a non-empty 2-D array")
    if len(bbox_norm) != 4:
        raise ValueError("bbox_norm must contain four values")
    left, top, right, bottom = [float(np.clip(value, 0.0, 1.0)) for value in bbox_norm]
    if right <= left or bottom <= top:
        raise ValueError(f"invalid normalized box: {bbox_norm}")
    height, width = heatmap.shape
    x1 = min(width - 1, max(0, int(math.floor(left * width))))
    y1 = min(height - 1, max(0, int(math.floor(top * height))))
    x2 = min(width, max(x1 + 1, int(math.ceil(right * width))))
    y2 = min(height, max(y1 + 1, int(math.ceil(bottom * height))))
    region = heatmap[y1:y2, x1:x2]
    return {
        "mean": float(region.mean()),
        "max": float(region.max()),
        "p90": float(np.quantile(region, 0.90)),
    }


def _box_iou(first: Sequence[int], second: Sequence[int]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    first_area = max(0, first[2] - first[0]) * max(0, first[3] - first[1])
    second_area = max(0, second[2] - second[0]) * max(0, second[3] - second[1])
    return intersection / (first_area + second_area - intersection + EPS)


def _peak_coordinates(response: np.ndarray, max_peaks: int, min_distance: int) -> list[tuple[int, int, float]]:
    height, width = response.shape
    chosen: list[tuple[int, int, float]] = []
    for flat_index in np.argsort(response.reshape(-1))[::-1].tolist():
        y, x = divmod(int(flat_index), width)
        if any((y - py) ** 2 + (x - px) ** 2 < max(min_distance, 1) ** 2 for py, px, _ in chosen):
            continue
        chosen.append((y, x, float(response[y, x])))
        if len(chosen) >= max(max_peaks, 1):
            break
    return chosen


def generate_multipeak_candidates(
    response: np.ndarray | Sequence[float],
    image_size: tuple[int, int],
    scales: Sequence[float] = (0.50, 0.70, 0.85),
    coverage_target: float = 0.60,
    max_peaks: int = 4,
    min_peak_distance: int = 2,
    nms_iou: float = 0.65,
    max_candidates: int = 6,
) -> list[dict[str, Any]]:
    """Decode a 2-D response map into diverse multi-scale crop candidates."""
    heatmap = normalize_response(np.asarray(response, dtype=np.float32))
    if heatmap.ndim != 2 or heatmap.size == 0:
        raise ValueError("response must be a non-empty 2-D array")
    image_width, image_height = image_size
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_size must be positive")
    grid_height, grid_width = heatmap.shape
    total_energy = float(heatmap.sum()) + EPS
    coverage_target = float(np.clip(coverage_target, EPS, 1.0))
    candidates: list[dict[str, Any]] = []
    peaks = _peak_coordinates(heatmap, max_peaks=max_peaks, min_distance=min_peak_distance)

    for peak_rank, (grid_y, grid_x, peak_value) in enumerate(peaks):
        center_x = int(round((grid_x + 0.5) / grid_width * image_width))
        center_y = int(round((grid_y + 0.5) / grid_height * image_height))
        for raw_scale in scales:
            scale = float(np.clip(raw_scale, 0.10, 1.0))
            crop_width = max(1, int(round(image_width * scale)))
            crop_height = max(1, int(round(image_height * scale)))
            left = min(max(0, center_x - crop_width // 2), max(0, image_width - crop_width))
            top = min(max(0, center_y - crop_height // 2), max(0, image_height - crop_height))
            right = min(image_width, left + crop_width)
            bottom = min(image_height, top + crop_height)
            grid_left = max(0, int(math.floor(left / image_width * grid_width)))
            grid_right = min(grid_width, max(grid_left + 1, int(math.ceil(right / image_width * grid_width))))
            grid_top = max(0, int(math.floor(top / image_height * grid_height)))
            grid_bottom = min(grid_height, max(grid_top + 1, int(math.ceil(bottom / image_height * grid_height))))
            region = heatmap[grid_top:grid_bottom, grid_left:grid_right]
            energy = float(region.sum())
            density = float(region.mean()) if region.size else 0.0
            coverage = energy / total_energy
            coverage_satisfaction = min(coverage / coverage_target, 1.0)
            zoom_gain = 1.0 - scale
            score = (
                0.30 * density
                + 0.30 * coverage_satisfaction
                + 0.20 * peak_value
                + 0.20 * zoom_gain
            )
            candidates.append({
                "peak_rank": peak_rank,
                "grid_peak": [grid_x, grid_y],
                "center_xy": [center_x, center_y],
                "scale": scale,
                "bbox": [left, top, right, bottom],
                "bbox_norm": [left / image_width, top / image_height, right / image_width, bottom / image_height],
                "crop_score": float(score),
                "density": density,
                "coverage": coverage,
                "coverage_target": coverage_target,
                "coverage_satisfaction": coverage_satisfaction,
                "zoom_gain": zoom_gain,
                "peak_value": peak_value,
            })

    kept: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: item["crop_score"], reverse=True):
        if any(_box_iou(candidate["bbox"], previous["bbox"]) > float(nms_iou) for previous in kept):
            continue
        kept.append(candidate)
        if len(kept) >= max(max_candidates, 1):
            break
    for rank, candidate in enumerate(kept):
        candidate["candidate_rank"] = rank
    return kept


def allocate_local_budget(
    candidates: Sequence[Mapping[str, Any]],
    global_count: int,
    visual_budget: int,
    max_per_frame: int = 2,
    selection_weight: float = 0.15,
    same_frame_penalty: float = 0.12,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select local views without exceeding the total global+local budget."""
    global_count = max(int(global_count), 0)
    visual_budget = max(int(visual_budget), 0)
    local_budget = max(0, visual_budget - global_count)
    records = [dict(candidate) for candidate in candidates]
    selection_values = [float(record.get("selection_score", 0.0) or 0.0) for record in records]
    low = min(selection_values) if selection_values else 0.0
    high = max(selection_values) if selection_values else 0.0

    for record, selection_score in zip(records, selection_values):
        record["selection_score_norm"] = (selection_score - low) / (high - low + EPS) if high > low else 0.5

    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    per_frame: dict[int, int] = {}
    while len(selected) < local_budget:
        best: tuple[float, dict[str, Any]] | None = None
        for index, record in enumerate(records):
            candidate_id = str(record.get("candidate_id", index))
            frame_rank = int(record.get("frame_rank", -1))
            if candidate_id in used_ids or per_frame.get(frame_rank, 0) >= max(max_per_frame, 1):
                continue
            utility = (
                float(record.get("crop_score", 0.0) or 0.0)
                + float(selection_weight) * float(record["selection_score_norm"])
                - float(same_frame_penalty) * per_frame.get(frame_rank, 0)
            )
            if best is None or utility > best[0]:
                best = (utility, record)
        if best is None:
            break
        utility, record = best
        candidate_id = str(record.get("candidate_id", len(selected)))
        frame_rank = int(record.get("frame_rank", -1))
        chosen = dict(record)
        chosen["budget_rank"] = len(selected)
        chosen["budget_utility"] = float(utility)
        selected.append(chosen)
        used_ids.add(candidate_id)
        per_frame[frame_rank] = per_frame.get(frame_rank, 0) + 1

    return selected, {
        "visual_budget": visual_budget,
        "global_count": global_count,
        "local_budget": local_budget,
        "selected_local_count": len(selected),
        "unused_budget": max(0, local_budget - len(selected)),
        "max_per_frame": max(max_per_frame, 1),
    }


def summarize_video_grid(
    grid_rows: Sequence[Sequence[int]],
    submitted_frame_count: int,
    spatial_merge_size: int,
    temporal_patch_size: int,
    token_budget: int,
) -> dict[str, Any]:
    """Audit Qwen video-grid coverage and its exact post-merge token count."""
    rows: list[list[int]] = []
    for row in grid_rows:
        values = [int(value) for value in row]
        if len(values) != 3 or any(value < 0 for value in values):
            raise ValueError(f"invalid video grid row: {values}")
        rows.append(values)

    merge_size = max(int(spatial_merge_size), 1)
    temporal_size = max(int(temporal_patch_size), 1)
    submitted = max(int(submitted_frame_count), 0)
    budget = int(token_budget)
    token_count = sum((time * height * width) // (merge_size**2) for time, height, width in rows)
    represented_frames = sum(time * temporal_size for time, _, _ in rows)
    budget_respected = budget <= 0 or token_count <= budget
    return {
        "spatial_merge_size": merge_size,
        "temporal_patch_size": temporal_size,
        "represented_frame_count": represented_frames,
        "all_submitted_frames_represented": represented_frames >= submitted,
        "post_merge_visual_token_count": token_count,
        "post_merge_visual_token_budget": budget,
        "visual_token_budget_respected": budget_respected,
    }
