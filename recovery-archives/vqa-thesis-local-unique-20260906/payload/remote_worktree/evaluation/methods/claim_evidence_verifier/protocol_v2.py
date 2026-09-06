"""Pure protocol utilities for claim-level target/control interventions.

Human evidence annotations are used only to construct and audit the oracle
diagnostic triplets. They are never part of the verifier feature record.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any


MODALITY_ALIASES = {
    "audio": "asr",
    "speech": "asr",
    "voiceover": "asr",
    "text": "ocr",
}
VISUAL_MODALITIES = {"visual", "ocr"}


def canonical_modality(value: Any) -> str:
    modality = str(value or "").strip().lower()
    return MODALITY_ALIASES.get(modality, modality)


def required_intervals(
    evidence_units: Sequence[Mapping[str, Any]], modalities: set[str]
) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    for unit in evidence_units:
        if not bool(unit.get("required", True)):
            continue
        unit_modalities = {canonical_modality(value) for value in unit.get("modalities", [])}
        if not unit_modalities & modalities:
            continue
        for value in unit.get("intervals_sec", []):
            if not isinstance(value, Sequence) or len(value) != 2:
                continue
            start, end = float(value[0]), float(value[1])
            if math.isfinite(start) and math.isfinite(end) and 0.0 <= start <= end:
                intervals.append((start, end))
    return sorted(intervals)


def timestamp_in_intervals(timestamp: float, intervals: Sequence[tuple[float, float]]) -> bool:
    return any(start <= timestamp <= end for start, end in intervals)


def frame_timestamps(selected_frames: Sequence[Mapping[str, Any]], duration_sec: float) -> list[float]:
    if not math.isfinite(duration_sec) or duration_sec <= 0:
        raise ValueError("duration_sec must be positive and finite")
    timestamps = []
    for frame in selected_frames:
        frame_index = max(0, int(frame.get("frame_index", 0)))
        total_frames = max(1, int(frame.get("total_frames", 1)))
        timestamps.append(duration_sec * frame_index / max(1, total_frames - 1))
    return timestamps


def _spread(indices: Sequence[int], count: int) -> list[int]:
    values = sorted(set(int(value) for value in indices))
    if count >= len(values):
        return values
    if count == 1:
        return [values[len(values) // 2]]
    positions = [round(index * (len(values) - 1) / (count - 1)) for index in range(count)]
    return [values[position] for position in positions]


def plan_visual_target_control(
    timestamps_sec: Sequence[float],
    evidence_units: Sequence[Mapping[str, Any]],
    max_target_count: int = 4,
) -> dict[str, Any]:
    """Choose equal-count visual target and non-evidence control views."""
    if max_target_count <= 0:
        raise ValueError("max_target_count must be positive")
    intervals = required_intervals(evidence_units, VISUAL_MODALITIES)
    target_candidates = [
        index for index, timestamp in enumerate(timestamps_sec)
        if timestamp_in_intervals(float(timestamp), intervals)
    ]
    control_candidates = [
        index for index, timestamp in enumerate(timestamps_sec)
        if not timestamp_in_intervals(float(timestamp), intervals)
    ]
    count = min(max_target_count, len(target_candidates), len(control_candidates))
    if not intervals:
        reason = "no_required_visual_interval"
    elif not target_candidates:
        reason = "no_selected_view_hits_visual_interval"
    elif not control_candidates:
        reason = "no_non_evidence_control_view"
    else:
        reason = "ok"
    target = _spread(target_candidates, count) if count else []
    # Match controls to target timestamps while keeping a one-to-one assignment.
    remaining = set(control_candidates)
    control = []
    for target_index in target:
        chosen = min(
            remaining,
            key=lambda index: (abs(float(timestamps_sec[index]) - float(timestamps_sec[target_index])), index),
        )
        control.append(chosen)
        remaining.remove(chosen)
    return {
        "modality": "visual",
        "valid": bool(target and len(target) == len(control)),
        "reason": reason,
        "target_indices": target,
        "control_indices": control,
        "target_timestamps_sec": [float(timestamps_sec[index]) for index in target],
        "control_timestamps_sec": [float(timestamps_sec[index]) for index in control],
        "target_cost": len(target),
        "control_cost": len(control),
        "cost_unit": "views",
        "required_intervals_sec": [[start, end] for start, end in intervals],
    }


def _overlap_duration(start: float, end: float, intervals: Sequence[tuple[float, float]]) -> float:
    return sum(max(0.0, min(end, right) - max(start, left)) for left, right in intervals)


def plan_asr_target_control(
    segments: Sequence[Mapping[str, Any]], evidence_units: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Choose one supporting ASR segment and a duration-matched control segment."""
    intervals = required_intervals(evidence_units, {"asr"})
    parsed = []
    for index, segment in enumerate(segments):
        start, end = float(segment.get("start", 0.0)), float(segment.get("end", 0.0))
        if end > start:
            parsed.append((index, start, end, _overlap_duration(start, end, intervals)))
    targets = [row for row in parsed if row[3] > 0]
    controls = [row for row in parsed if row[3] == 0]
    if not intervals:
        reason = "no_required_asr_interval"
    elif not targets:
        reason = "no_asr_segment_hits_interval"
    elif not controls:
        reason = "no_non_evidence_asr_control"
    else:
        reason = "ok"
    if not targets or not controls:
        return {
            "modality": "asr", "valid": False, "reason": reason,
            "target_indices": [], "control_indices": [],
            "target_cost": 0.0, "control_cost": 0.0, "cost_unit": "seconds",
            "required_intervals_sec": [[start, end] for start, end in intervals],
        }
    target = max(targets, key=lambda row: (row[3], -(row[2] - row[1]), -row[0]))
    target_duration = target[2] - target[1]
    control = min(controls, key=lambda row: (abs((row[2] - row[1]) - target_duration), row[0]))
    return {
        "modality": "asr",
        "valid": True,
        "reason": reason,
        "target_indices": [target[0]],
        "control_indices": [control[0]],
        "target_cost": target_duration,
        "control_cost": control[2] - control[1],
        "cost_unit": "seconds",
        "required_intervals_sec": [[start, end] for start, end in intervals],
    }


def audit_intervention(plan: Mapping[str, Any], duration_tolerance: float = 0.35) -> list[str]:
    errors = []
    target = list(plan.get("target_indices") or [])
    control = list(plan.get("control_indices") or [])
    if bool(plan.get("valid")) and (not target or not control):
        errors.append("valid_plan_has_empty_side")
    if set(target) & set(control):
        errors.append("target_control_overlap")
    if plan.get("cost_unit") == "views" and plan.get("target_cost") != plan.get("control_cost"):
        errors.append("view_cost_mismatch")
    if plan.get("cost_unit") == "seconds" and plan.get("valid"):
        target_cost = float(plan.get("target_cost", 0.0))
        control_cost = float(plan.get("control_cost", 0.0))
        if target_cost <= 0 or abs(target_cost - control_cost) / target_cost > duration_tolerance:
            errors.append("duration_cost_mismatch")
    return errors
