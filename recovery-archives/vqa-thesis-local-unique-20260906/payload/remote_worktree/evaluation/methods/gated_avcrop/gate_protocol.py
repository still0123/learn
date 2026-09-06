"""Frozen, leakage-safe protocol primitives for Qwen2.5 gated AV crops.

This module deliberately has no torch, model, or evaluator dependency.  It
defines the pre-inference gate and audit contracts shared by RandomCrop8,
CLIPCrop8, and AVCrop8.  The gate can observe only question, ASR, OCR, and AV
response statistics.  It must never receive answers, judge scores, or results.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PROTOCOL_VERSION = "qwen25_gated_avcrop_protocol_v1"
ALLOWED_MODEL_PATH = Path("/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct")
FORBIDDEN_MODEL_MARKER = "qwen2.5-7b-vl-read-r"
RAW_GLOBAL_VIEW_COUNT = 32
RAW40_VIEW_COUNT = 40
APPENDED_LOCAL_VIEW_COUNT = 8

FROZEN_GATE_RULE = {
    "version": "question_type_av_peak_gate_v1",
    "append_local_view_count": APPENDED_LOCAL_VIEW_COUNT,
    "minimum_peak_response": 0.70,
    "minimum_response_concentration": 0.08,
    "minimum_eligible_crop_candidates": APPENDED_LOCAL_VIEW_COUNT,
    "local_crop_scale": 0.60,
    "av_question_weight": 0.60,
    "av_asr_weight": 0.40,
    "question_type_policy": "visual_detail_only_with_audio_narrative_cta_exclusions",
    "threshold_selection": "frozen_before_groupcv_inference_no_validation_or_test_scan",
}


def normalize_gate_rule(gate_rule: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate a rule frozen before applying it to an outer-fold holdout."""
    active = dict(FROZEN_GATE_RULE)
    if gate_rule is not None:
        active.update(dict(gate_rule))
    required = {
        "version",
        "append_local_view_count",
        "minimum_peak_response",
        "minimum_response_concentration",
        "minimum_eligible_crop_candidates",
        "local_crop_scale",
        "av_question_weight",
        "av_asr_weight",
        "question_type_policy",
        "threshold_selection",
    }
    missing = required - set(active)
    if missing:
        raise GateProtocolError(f"gate rule is missing keys: {sorted(missing)}")
    if int(active["append_local_view_count"]) != APPENDED_LOCAL_VIEW_COUNT:
        raise GateProtocolError("only the fixed eight appended local views are allowed")
    for key in (
        "minimum_peak_response",
        "minimum_response_concentration",
        "local_crop_scale",
        "av_question_weight",
        "av_asr_weight",
    ):
        value = float(active[key])
        if not 0.0 <= value <= 1.0:
            raise GateProtocolError(f"gate rule {key} must be in [0, 1]")
    if int(active["minimum_eligible_crop_candidates"]) < APPENDED_LOCAL_VIEW_COUNT:
        raise GateProtocolError("gate rule must require at least eight crop candidates")
    return active


VISUAL_DETAIL_TERMS = (
    "brand",
    "logo",
    "text",
    "word",
    "written",
    "caption",
    "subtitle",
    "sign",
    "label",
    "package",
    "packaging",
    "color",
    "colour",
    "number",
    "price",
    "discount",
    "percentage",
    "url",
    "website",
    "barcode",
)
AUDIO_NARRATIVE_CTA_TERMS = (
    "voiceover",
    "speaker",
    "narrator",
    "spoken",
    "say",
    "said",
    "hear",
    "sound",
    "music",
    "theme",
    "message",
    "emotion",
    "mood",
    "audience",
    "strategy",
    "persuade",
    "campaign",
    "target audience",
    "why",
    "how does",
    "call to action",
    "encourage",
    "invite",
    "urge",
)
FORBIDDEN_GATE_KEY_FRAGMENTS = (
    "answer",
    "ground_truth",
    "groundtruth",
    "reference",
    "judge",
    "evaluation",
    "eval",
    "result",
    "prediction",
    "label",
)


class GateProtocolError(ValueError):
    """Raised when a frozen gate or a protocol invariant is violated."""


def canonical_json_sha256(value: Any) -> str:
    """Hash structured values with a deterministic JSON representation."""
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_content_manifest(model_dir: str | Path) -> dict[str, Any]:
    """Return an auditable content manifest without loading model weights."""
    root = Path(model_dir).expanduser().resolve()
    if not root.is_dir():
        raise GateProtocolError(f"model directory does not exist: {root}")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    rows = [f"{path.relative_to(root)}\t{sha256_file(path)}" for path in files]
    digest_input = ("\n".join(rows) + "\n").encode("utf-8")
    return {
        "path": str(root),
        "file_count": len(rows),
        "config_sha256": sha256_file(root / "config.json"),
        "content_manifest_sha256": hashlib.sha256(digest_input).hexdigest(),
        "content_manifest_method": (
            "sha256 of newline-joined relative_path<TAB>file_sha256 records "
            "sorted by relative path, with trailing newline"
        ),
    }


def validate_clean_model_path(model_dir: str | Path) -> dict[str, Any]:
    """Enforce the single allowed base model and reject every ReAd-R path."""
    raw = str(model_dir)
    normalized = Path(model_dir).expanduser().resolve()
    if FORBIDDEN_MODEL_MARKER in raw.lower() or FORBIDDEN_MODEL_MARKER in str(normalized).lower():
        raise GateProtocolError("ReAd-R is forbidden for this experiment")
    if normalized != ALLOWED_MODEL_PATH.resolve():
        raise GateProtocolError(
            f"only clean Qwen2.5-VL-7B-Instruct is allowed: {ALLOWED_MODEL_PATH}"
        )
    return model_content_manifest(normalized)


def _walk_keys(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            yield child_path, key_text
            yield from _walk_keys(child, child_path)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            yield from _walk_keys(child, f"{path}[{index}]")


def assert_gate_inputs_are_leakage_safe(*values: Any) -> None:
    """Reject answer, judge, and result fields before a gate is materialized.

    Plain ``score`` fields remain allowed because timestamped ASR and OCR
    candidates commonly expose confidence as ``score``.  Judge/evaluation
    scores remain blocked by their field names.
    """
    for value in values:
        for path, key in _walk_keys(value):
            normalized = key.lower().replace("-", "_").replace(" ", "_")
            if any(fragment in normalized for fragment in FORBIDDEN_GATE_KEY_FRAGMENTS):
                raise GateProtocolError(f"forbidden gate input field at {path}")


def _matched_terms(question: str, terms: Sequence[str]) -> list[str]:
    text = " ".join((question or "").lower().split())
    return [term for term in terms if term in text]


def extract_question_text(question: str) -> str:
    """Remove the dataset's ASR prefix before classifying question type.

    AdsQA training rows concatenate ``Voiceover: ...`` and ``Question: ...``.
    Treating that prefix as the question would spuriously route visual-detail
    prompts to the audio exclusion.  The ASR remains a separate gate input.
    """
    if not isinstance(question, str) or not question.strip():
        raise GateProtocolError("gate requires a non-empty question string")
    marker = "question:"
    lower = question.lower()
    index = lower.rfind(marker)
    extracted = question[index + len(marker) :].strip() if index >= 0 else question.strip()
    if not extracted:
        raise GateProtocolError("Question: marker does not contain a question")
    return extracted


def classify_question_type(
    question: str,
    *,
    classifier_version: str = FROZEN_GATE_RULE["version"],
) -> dict[str, Any]:
    """Classify only from question text; no dataset labels or outcomes are read."""
    question_text = extract_question_text(question)
    visual_terms = _matched_terms(question_text, VISUAL_DETAIL_TERMS)
    excluded_terms = _matched_terms(question_text, AUDIO_NARRATIVE_CTA_TERMS)
    is_visual_detail = bool(visual_terms) and not bool(excluded_terms)
    return {
        "classifier_version": classifier_version,
        "question_text_source": "suffix_after_last_Question_marker",
        "raw_question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "question_text_sha256": hashlib.sha256(question_text.encode("utf-8")).hexdigest(),
        "matched_visual_detail_terms": visual_terms,
        "matched_exclusion_terms": excluded_terms,
        "is_visual_detail_question": is_visual_detail,
        "reason": (
            "visual_detail_terms_present_and_no_audio_narrative_cta_exclusion"
            if is_visual_detail
            else "missing_visual_detail_terms"
            if not visual_terms
            else "audio_narrative_cta_exclusion"
        ),
    }


def _bounded_float(stats: Mapping[str, Any], key: str) -> float:
    try:
        value = float(stats[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise GateProtocolError(f"missing or invalid AV response statistic: {key}") from exc
    if not 0.0 <= value <= 1.0:
        raise GateProtocolError(f"AV response statistic outside [0, 1]: {key}={value}")
    return value


def _nonnegative_int(stats: Mapping[str, Any], key: str) -> int:
    try:
        value = int(stats[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise GateProtocolError(f"missing or invalid AV response statistic: {key}") from exc
    if value < 0:
        raise GateProtocolError(f"AV response statistic must be non-negative: {key}={value}")
    return value


def build_gate_decision(
    question: str,
    asr_evidence: Mapping[str, Any] | str | None,
    ocr_candidates: Sequence[Mapping[str, Any]] | None,
    av_response_stats: Mapping[str, Any],
    gate_rule: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze one gate decision from permitted pre-inference evidence only."""
    assert_gate_inputs_are_leakage_safe(asr_evidence, ocr_candidates, av_response_stats)
    active_rule = normalize_gate_rule(gate_rule)
    question_type = classify_question_type(question, classifier_version=str(active_rule["version"]))
    peak_response = _bounded_float(av_response_stats, "peak_response")
    concentration = _bounded_float(av_response_stats, "response_concentration")
    candidate_count = _nonnegative_int(av_response_stats, "eligible_crop_candidate_count")
    asr_present = bool(
        asr_evidence.strip()
        if isinstance(asr_evidence, str)
        else (asr_evidence or {}).get("transcript", "")
    )
    ocr_count = len(ocr_candidates or [])

    criteria = {
        "visual_detail_question": question_type["is_visual_detail_question"],
        "peak_response": peak_response >= float(active_rule["minimum_peak_response"]),
        "response_concentration": concentration >= float(active_rule["minimum_response_concentration"]),
        "eligible_crop_candidates": (
            candidate_count >= int(active_rule["minimum_eligible_crop_candidates"])
        ),
    }
    append_crop8 = all(criteria.values())
    return {
        "protocol_version": PROTOCOL_VERSION,
        "gate_rule": active_rule,
        "question_type": question_type,
        "permitted_evidence_summary": {
            "asr_present": asr_present,
            "ocr_candidate_count": ocr_count,
            "peak_response": peak_response,
            "response_concentration": concentration,
            "eligible_crop_candidate_count": candidate_count,
        },
        "criteria": criteria,
        "append_crop8": append_crop8,
        "local_view_count": APPENDED_LOCAL_VIEW_COUNT if append_crop8 else 0,
        "submitted_view_count": RAW_GLOBAL_VIEW_COUNT + (
            APPENDED_LOCAL_VIEW_COUNT if append_crop8 else 0
        ),
        "decision_reason": "all_frozen_criteria_met" if append_crop8 else "one_or_more_frozen_criteria_failed",
    }


def frozen_group_configs() -> dict[str, dict[str, Any]]:
    """Return immutable group identities for the five required comparisons."""
    common = {
        "protocol_version": PROTOCOL_VERSION,
        "model_policy": "clean_qwen25_only",
        "rag_enabled": False,
        "reflection_enabled": False,
        "answer_rewrite_enabled": False,
        "fine_tuning_enabled": False,
        "secondary_frame_sampling_disabled": True,
        "global_frame_policy": "uniform_complete_frames",
        "raw_global_view_count": RAW_GLOBAL_VIEW_COUNT,
    }
    return {
        "A_Raw32": {
            **common,
            "method": "raw_uniform",
            "submitted_view_count": RAW_GLOBAL_VIEW_COUNT,
            "local_view_count": 0,
            "gate_manifest_required": False,
        },
        "B_Raw40": {
            **common,
            "method": "raw_uniform",
            "submitted_view_count": RAW40_VIEW_COUNT,
            "local_view_count": 0,
            "gate_manifest_required": False,
        },
        "C_Gated_RandomCrop8": {
            **common,
            "method": "gated_random_crop8",
            "submitted_view_count_when_gate_hit": RAW40_VIEW_COUNT,
            "submitted_view_count_when_gate_miss": RAW_GLOBAL_VIEW_COUNT,
            "local_view_count_when_gate_hit": APPENDED_LOCAL_VIEW_COUNT,
            "gate_manifest_required": True,
            "gate_manifest_shared_with": ["D_Gated_CLIPCrop8", "E_Gated_AVCrop8"],
        },
        "D_Gated_CLIPCrop8": {
            **common,
            "method": "gated_clip_crop8",
            "submitted_view_count_when_gate_hit": RAW40_VIEW_COUNT,
            "submitted_view_count_when_gate_miss": RAW_GLOBAL_VIEW_COUNT,
            "local_view_count_when_gate_hit": APPENDED_LOCAL_VIEW_COUNT,
            "gate_manifest_required": True,
            "gate_manifest_shared_with": ["C_Gated_RandomCrop8", "E_Gated_AVCrop8"],
        },
        "E_Gated_AVCrop8": {
            **common,
            "method": "gated_av_crop8",
            "submitted_view_count_when_gate_hit": RAW40_VIEW_COUNT,
            "submitted_view_count_when_gate_miss": RAW_GLOBAL_VIEW_COUNT,
            "local_view_count_when_gate_hit": APPENDED_LOCAL_VIEW_COUNT,
            "gate_manifest_required": True,
            "gate_manifest_shared_with": ["C_Gated_RandomCrop8", "D_Gated_CLIPCrop8"],
        },
    }


@dataclass(frozen=True)
class GateManifestRecord:
    """Minimal immutable record consumed by all gated experimental groups."""

    question_id: str
    video_id: str
    gate_decision: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        decision = dict(self.gate_decision)
        return {
            "question_id": self.question_id,
            "video_id": self.video_id,
            "append_crop8": bool(decision["append_crop8"]),
            "local_view_count": int(decision["local_view_count"]),
            "submitted_view_count": int(decision["submitted_view_count"]),
            "gate_decision": decision,
        }


def build_gate_manifest_record(
    question_id: str | int,
    video_id: str,
    question: str,
    asr_evidence: Mapping[str, Any] | str | None,
    ocr_candidates: Sequence[Mapping[str, Any]] | None,
    av_response_stats: Mapping[str, Any],
    gate_rule: Mapping[str, Any] | None = None,
) -> GateManifestRecord:
    """Create a manifest record without accepting ground truth or predictions."""
    if not str(question_id):
        raise GateProtocolError("question_id is required")
    if not str(video_id):
        raise GateProtocolError("video_id is required")
    return GateManifestRecord(
        question_id=str(question_id),
        video_id=str(video_id),
        gate_decision=build_gate_decision(
            question=question,
            asr_evidence=asr_evidence,
            ocr_candidates=ocr_candidates,
            av_response_stats=av_response_stats,
            gate_rule=gate_rule,
        ),
    )


def validate_shared_gate_manifest(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate that C/D/E consume one immutable, duplicate-free decision list."""
    if not records:
        raise GateProtocolError("gate manifest must contain at least one record")
    seen_questions: set[str] = set()
    gate_hit_count = 0
    expected_view_counts: set[int] = set()
    normalized_records = []
    for raw in records:
        assert_gate_inputs_are_leakage_safe(raw)
        question_id = str(raw.get("question_id", ""))
        if not question_id:
            raise GateProtocolError("gate manifest record has no question_id")
        if question_id in seen_questions:
            raise GateProtocolError(f"duplicate question_id in gate manifest: {question_id}")
        seen_questions.add(question_id)
        append_crop8 = bool(raw.get("append_crop8"))
        local_count = int(raw.get("local_view_count", -1))
        submitted_count = int(raw.get("submitted_view_count", -1))
        expected_local = APPENDED_LOCAL_VIEW_COUNT if append_crop8 else 0
        expected_submitted = RAW_GLOBAL_VIEW_COUNT + expected_local
        if local_count != expected_local or submitted_count != expected_submitted:
            raise GateProtocolError(
                f"gate view invariant failed for {question_id}: "
                f"local={local_count}, submitted={submitted_count}"
            )
        gate_hit_count += int(append_crop8)
        expected_view_counts.add(submitted_count)
        normalized_records.append(
            {
                "question_id": question_id,
                "video_id": str(raw.get("video_id", "")),
                "append_crop8": append_crop8,
                "local_view_count": local_count,
                "submitted_view_count": submitted_count,
                "gate_decision": raw.get("gate_decision", {}),
            }
        )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "record_count": len(normalized_records),
        "gate_hit_count": gate_hit_count,
        "gate_miss_count": len(normalized_records) - gate_hit_count,
        "allowed_submitted_view_counts": sorted(expected_view_counts),
        "manifest_sha256": canonical_json_sha256(normalized_records),
        "shared_by_methods": [
            "C_Gated_RandomCrop8",
            "D_Gated_CLIPCrop8",
            "E_Gated_AVCrop8",
        ],
    }


def audit_group_record_against_manifest(
    method_name: str,
    manifest_record: Mapping[str, Any],
    inference_record: Mapping[str, Any],
) -> None:
    """Check that a single C/D/E result obeyed the frozen gate decision."""
    if method_name not in {
        "C_Gated_RandomCrop8",
        "D_Gated_CLIPCrop8",
        "E_Gated_AVCrop8",
    }:
        raise GateProtocolError(f"not a gated method: {method_name}")
    if str(inference_record.get("question_id", "")) != str(manifest_record.get("question_id", "")):
        raise GateProtocolError("inference record question_id does not match the gate manifest")
    gate_hit = bool(manifest_record.get("append_crop8"))
    expected_local = APPENDED_LOCAL_VIEW_COUNT if gate_hit else 0
    expected_submitted = RAW_GLOBAL_VIEW_COUNT + expected_local
    if int(inference_record.get("local_view_count", -1)) != expected_local:
        raise GateProtocolError("local view count differs from frozen gate decision")
    if int(inference_record.get("submitted_view_count", -1)) != expected_submitted:
        raise GateProtocolError("submitted view count differs from frozen gate decision")
    if gate_hit and int(inference_record.get("crop_count", -1)) != APPENDED_LOCAL_VIEW_COUNT:
        raise GateProtocolError("gate hit must append exactly eight crops")
