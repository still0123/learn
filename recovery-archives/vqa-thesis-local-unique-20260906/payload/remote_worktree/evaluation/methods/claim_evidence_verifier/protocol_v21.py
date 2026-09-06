"""Single preregistered correction for target/control intervention construction."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

from .protocol_v2 import canonical_modality, required_intervals, timestamp_in_intervals


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _union_coverage(intervals: Sequence[tuple[float, float]], duration: float) -> float:
    clipped = sorted((max(0.0, left), min(duration, right)) for left, right in intervals if right > 0 and left < duration)
    if not clipped or duration <= 0:
        return 0.0
    total = 0.0
    start, end = clipped[0]
    for left, right in clipped[1:]:
        if left <= end:
            end = max(end, right)
        else:
            total += end - start
            start, end = left, right
    return (total + end - start) / duration


def _distance_to_intervals(timestamp: float, intervals: Sequence[tuple[float, float]]) -> float:
    if timestamp_in_intervals(timestamp, intervals):
        return 0.0
    return min((min(abs(timestamp - left), abs(timestamp - right)) for left, right in intervals), default=float("inf"))


def _quartile(timestamp: float, duration: float) -> int:
    return min(3, max(0, int(4.0 * timestamp / max(duration, 1e-8))))


def _select_cross_bin_low_relevance(
    candidates: Sequence[int], timestamps: Sequence[float], relevance: Sequence[float], count: int, duration: float
) -> list[int]:
    by_bin: dict[int, list[int]] = {index: [] for index in range(4)}
    for index in candidates:
        by_bin[_quartile(float(timestamps[index]), duration)].append(index)
    for values in by_bin.values():
        values.sort(key=lambda index: (float(relevance[index]), index))
    selected = []
    for bin_index in sorted(by_bin, key=lambda value: (float(relevance[by_bin[value][0]]) if by_bin[value] else float("inf"), value)):
        if by_bin[bin_index] and len(selected) < count:
            selected.append(by_bin[bin_index][0])
    remaining = sorted(set(candidates) - set(selected), key=lambda index: (float(relevance[index]), index))
    selected.extend(remaining[: max(0, count - len(selected))])
    return sorted(selected)


def plan_visual_target_control_v21(
    timestamps_sec: Sequence[float],
    relevance_scores: Sequence[float],
    evidence_units: Sequence[Mapping[str, Any]],
    duration_sec: float,
    max_target_count: int = 4,
    max_evidence_coverage: float = 0.70,
    endpoint_guard_fraction: float = 0.05,
    boundary_guard_fraction: float = 0.02,
    min_control_pool: int = 6,
) -> dict[str, Any]:
    if len(timestamps_sec) != len(relevance_scores):
        raise ValueError("timestamps and relevance scores must align")
    intervals = required_intervals(evidence_units, {"visual", "ocr"})
    coverage = _union_coverage(intervals, duration_sec)
    endpoint_guard = duration_sec * endpoint_guard_fraction
    boundary_guard = duration_sec * boundary_guard_fraction
    targets = [index for index, timestamp in enumerate(timestamps_sec) if timestamp_in_intervals(float(timestamp), intervals)]
    controls = [
        index for index, timestamp in enumerate(timestamps_sec)
        if not timestamp_in_intervals(float(timestamp), intervals)
        and endpoint_guard <= float(timestamp) <= duration_sec - endpoint_guard
        and _distance_to_intervals(float(timestamp), intervals) >= boundary_guard
    ]
    if not intervals:
        reason = "no_required_visual_interval"
    elif coverage > max_evidence_coverage:
        reason = "distributed_visual_evidence_no_safe_control"
    elif not targets:
        reason = "no_raw_view_hits_visual_interval"
    elif len(controls) < min_control_pool:
        reason = "insufficient_guarded_control_pool"
    else:
        reason = "ok"
    count = min(max_target_count, len(targets), len(controls))
    target = sorted(sorted(targets, key=lambda index: (-float(relevance_scores[index]), index))[:count]) if count else []
    control = _select_cross_bin_low_relevance(controls, timestamps_sec, relevance_scores, count, duration_sec) if count else []
    control_bins = sorted({_quartile(float(timestamps_sec[index]), duration_sec) for index in control})
    valid = reason == "ok" and bool(target) and len(target) == len(control) and len(control_bins) >= 2
    if reason == "ok" and not valid:
        reason = "control_not_cross_temporal_bins"
    return {
        "protocol": "guarded_low_relevance_cross_bin_v21",
        "modality": "visual", "valid": valid, "reason": reason,
        "target_indices": target, "control_indices": control,
        "target_timestamps_sec": [float(timestamps_sec[index]) for index in target],
        "control_timestamps_sec": [float(timestamps_sec[index]) for index in control],
        "target_relevance": [float(relevance_scores[index]) for index in target],
        "control_relevance": [float(relevance_scores[index]) for index in control],
        "target_cost": len(target), "control_cost": len(control), "cost_unit": "views",
        "evidence_coverage_fraction": coverage,
        "control_candidate_count": len(controls), "control_temporal_bins": control_bins,
        "endpoint_guard_fraction": endpoint_guard_fraction,
        "boundary_guard_fraction": boundary_guard_fraction,
        "max_evidence_coverage": max_evidence_coverage,
        "required_intervals_sec": [[left, right] for left, right in intervals],
    }


def _tokens(text: Any) -> set[str]:
    return {value.lower() for value in _TOKEN_RE.findall(str(text or "")) if len(value) > 1}


def _jaccard(left: Any, right: Any) -> float:
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _overlap(start: float, end: float, intervals: Sequence[tuple[float, float]]) -> float:
    return sum(max(0.0, min(end, right) - max(start, left)) for left, right in intervals)


def plan_asr_target_control_v21(
    segments: Sequence[Mapping[str, Any]],
    evidence_units: Sequence[Mapping[str, Any]],
    query_text: str,
    duration_tolerance: float = 0.35,
) -> dict[str, Any]:
    intervals = required_intervals(evidence_units, {"asr"})
    parsed = []
    for index, segment in enumerate(segments):
        start, end = float(segment.get("start", 0.0)), float(segment.get("end", 0.0))
        if end > start:
            overlap = _overlap(start, end, intervals)
            parsed.append({
                "index": index, "start": start, "end": end, "duration": end - start,
                "overlap": overlap, "overlap_ratio": overlap / (end - start),
                "query_relevance": _jaccard(query_text, segment.get("text", "")),
            })
    targets = [row for row in parsed if row["overlap"] > 0]
    controls = [row for row in parsed if row["overlap"] == 0]
    if not intervals:
        reason = "no_required_asr_interval"
    elif not targets:
        reason = "no_asr_segment_hits_interval"
    elif not controls:
        reason = "no_non_evidence_asr_control"
    else:
        reason = "ok"
    if reason != "ok":
        return {
            "protocol": "duration_matched_low_relevance_asr_v21", "modality": "asr",
            "valid": False, "reason": reason, "target_indices": [], "control_indices": [],
            "target_cost": 0.0, "control_cost": 0.0, "cost_unit": "seconds",
            "required_intervals_sec": [[left, right] for left, right in intervals],
        }
    target = max(targets, key=lambda row: (row["overlap_ratio"], row["overlap"], -row["duration"], -row["index"]))
    matched = [row for row in controls if abs(row["duration"] - target["duration"]) / target["duration"] <= duration_tolerance]
    if not matched:
        return {
            "protocol": "duration_matched_low_relevance_asr_v21", "modality": "asr",
            "valid": False, "reason": "no_duration_matched_asr_control",
            "target_indices": [target["index"]], "control_indices": [],
            "target_cost": target["duration"], "control_cost": 0.0, "cost_unit": "seconds",
            "required_intervals_sec": [[left, right] for left, right in intervals],
        }
    control = min(matched, key=lambda row: (row["query_relevance"], abs(row["duration"] - target["duration"]), row["index"]))
    return {
        "protocol": "duration_matched_low_relevance_asr_v21", "modality": "asr",
        "valid": True, "reason": "ok", "target_indices": [target["index"]],
        "control_indices": [control["index"]], "target_cost": target["duration"],
        "control_cost": control["duration"], "cost_unit": "seconds",
        "target_query_relevance": target["query_relevance"],
        "control_query_relevance": control["query_relevance"],
        "duration_tolerance": duration_tolerance,
        "required_intervals_sec": [[left, right] for left, right in intervals],
    }


def raw32_relevance_from_nested_cache(
    selected_frame_indices: Sequence[int], cache_row: Mapping[str, Any]
) -> list[float]:
    candidates = [int(value) for value in cache_row.get("candidate_frame_indices", [])]
    scores = [float(value) for value in cache_row.get("candidate_scores", [])]
    if len(candidates) != len(scores):
        raise ValueError("temporal cache candidates and scores do not align")
    score_by_frame = dict(zip(candidates, scores))
    missing = [int(value) for value in selected_frame_indices if int(value) not in score_by_frame]
    if missing:
        raise ValueError(f"Raw32 is not nested in temporal cache: {missing[:5]}")
    return [score_by_frame[int(value)] for value in selected_frame_indices]
