#!/usr/bin/env python3
"""Create a separate, non-human machine preannotation for Candidate F.

This runner intentionally never writes into the two human-review templates. It
uses only the leak-free fields present in the template and records every output
as ``machine_only=true`` and ``not_human_gold=true``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


ALLOWED_RELATIONS = {
    "claim_absent_from_answer",
    "claim_present_supported",
    "claim_present_refuted",
    "claim_present_insufficient",
}
ALLOWED_MODALITIES = {"asr", "ocr", "visual", "joint"}
PROTECTED_KEYS = {"ground_truth", "label", "reference_answer", "score"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--calibration-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--gpu-id", type=int, required=True)
    parser.add_argument("--goal-start-epoch", type=int, required=True)
    parser.add_argument("--model-dir", type=Path, default=Path("/data1/qky/Model/Qwen3Vl-8B"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--max-image-pixels", type=int, default=1_280 * 1_280)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = str(ARGS.gpu_id)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
sys.modules["torchcodec"] = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def command_output(command: list[str]) -> str:
    return subprocess.run(command, check=False, text=True, capture_output=True).stdout.strip()


def gpu_snapshot(gpu_id: int) -> dict[str, Any]:
    gpu = command_output(
        [
            "nvidia-smi",
            "-i",
            str(gpu_id),
            "--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    processes = command_output(
        [
            "nvidia-smi",
            "-i",
            str(gpu_id),
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    active = []
    for line in processes.splitlines():
        if not line.strip() or line.lower().startswith("no running"):
            continue
        fields = [field.strip() for field in line.split(",", 2)]
        if len(fields) == 3:
            active.append(
                {
                    "pid": int(fields[0]),
                    "process_name": fields[1],
                    "used_memory_mib": int(fields[2]),
                }
            )
    return {"captured_at_epoch": int(time.time()), "gpu": gpu, "compute_processes": active}


def enforce_gpu_policy() -> dict[str, Any]:
    now = int(time.time())
    window_end = ARGS.goal_start_epoch + 21600
    allowed = {1, 2, 4, 5} if now < window_end else {4, 5}
    if ARGS.gpu_id not in allowed:
        raise RuntimeError(f"GPU{ARGS.gpu_id} is outside policy; allowed={sorted(allowed)}")
    snapshot = gpu_snapshot(ARGS.gpu_id)
    if snapshot["compute_processes"]:
        raise RuntimeError(f"GPU{ARGS.gpu_id} is not idle: {snapshot['compute_processes']}")
    return {
        "goal_start_epoch": ARGS.goal_start_epoch,
        "gpu_window_end_epoch": window_end,
        "allowed_gpu_ids": sorted(allowed),
        "pre_launch_snapshot": snapshot,
    }


def prompt_for(row: dict[str, Any]) -> str:
    transcript = str(row.get("transcript", "") or "")
    asr_available = bool(transcript.strip())
    frame_indices = [int(value) for value in row["raw32_frame_indices"]]
    return f"""You are a machine preannotator for a research review. Use ONLY the candidate answer,
atomic claim, transcript, and the supplied 32-frame Raw32 contact sheet. Do not use outside
knowledge, reference answers, prior labels, or historical scores.

Candidate answer:
{row["raw32_candidate_answer"]}

Atomic claim:
{row["atomic_claim"]}

Transcript available: {asr_available}
Transcript:
{transcript if asr_available else "[ASR_UNAVAILABLE]"}

The contact sheet contains Raw32 frames whose allowed original source-frame indices are:
{frame_indices}

Return exactly one compact JSON object and nothing else:
{{
  "relation": "claim_absent_from_answer|claim_present_supported|claim_present_refuted|claim_present_insufficient",
  "modalities": ["asr|ocr|visual|joint"],
  "primary_frame_index": 0,
  "asr_quote": "one exact transcript substring or empty string",
  "ocr_text": "one exact visible string or empty string",
  "confidence": 0.0,
  "rationale": "under 160 characters"
}}

Rules:
- Decide whether the atomic claim is actually stated or entailed by the candidate answer before
  judging its evidence. If absent, set `modalities` to an empty array and leave every evidence field empty.
- For a present claim, list only necessary modalities. If ASR is unavailable, never select asr or joint.
- visual, ocr, and joint require exactly one `primary_frame_index` from the allowed list. ocr additionally
  requires one exact `ocr_text`. asr and joint require one exact `asr_quote` from the supplied transcript.
- For asr-only or absent claims, set `primary_frame_index` to null. Use empty strings for unavailable
  `asr_quote` and `ocr_text`.
- A plausible campaign story is not evidence. When evidence is absent or ambiguous, use
  claim_present_insufficient rather than inventing an anchor.
"""


def extract_json(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
    starts = [match.start() for match in re.finditer(r"\{", candidate)]
    for start in starts:
        try:
            return json.loads(candidate[start:]), None
        except json.JSONDecodeError:
            continue
    return None, "no_parseable_json_object"


def remove_unverified_asr(
    annotation: dict[str, Any],
    modalities: list[Any],
    actions: list[str],
) -> None:
    modality_set = set(modalities)
    if modality_set == {"asr"} or "joint" in modality_set:
        annotation.update(
            {
                "machine_answer_relation": "claim_present_insufficient",
                "machine_required_modalities": [],
                "machine_frame_indices": [],
                "machine_asr_spans": [],
                "machine_ocr_evidence": [],
            }
        )
        actions.append("demoted_to_insufficient_for_unverified_required_asr")
    else:
        annotation["machine_required_modalities"] = [
            modality for modality in modalities if modality != "asr"
        ]
        annotation["machine_asr_spans"] = []
        actions.append("removed_unverified_asr_from_multimodal_annotation")


def canonicalize_annotation(
    annotation: dict[str, Any],
    row: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Canonicalize exact quoted ASR spans without inventing an unquoted anchor."""
    actions: list[str] = []
    if "machine_answer_relation" not in annotation:
        modalities = annotation.get("modalities", [])
        frame = annotation.get("primary_frame_index")
        asr_quote = annotation.get("asr_quote", "")
        ocr_text = annotation.get("ocr_text", "")
        frame_indices = [frame] if isinstance(frame, int) else []
        annotation = {
            "machine_answer_relation": annotation.get("relation"),
            "machine_required_modalities": modalities,
            "machine_frame_indices": frame_indices,
            "machine_asr_spans": (
                [{"start_char": None, "end_char": None, "quote": asr_quote}]
                if isinstance(asr_quote, str) and asr_quote
                else []
            ),
            "machine_ocr_evidence": (
                [{"text": ocr_text, "frame_indices": frame_indices}]
                if isinstance(ocr_text, str) and ocr_text
                else []
            ),
            "machine_confidence": annotation.get("confidence"),
            "machine_rationale": annotation.get("rationale"),
        }
    normalized = dict(annotation)
    modalities = normalized.get("machine_required_modalities")
    if not isinstance(modalities, list):
        return normalized, actions
    modality_set = set(modalities)
    if (
        normalized.get("machine_answer_relation")
        in {"claim_present_supported", "claim_present_refuted"}
        and not modality_set
    ):
        normalized["machine_answer_relation"] = "claim_present_insufficient"
        actions.append("demoted_unsupported_or_unrefuted_claim_to_insufficient")
    if modality_set == {"asr"}:
        normalized["machine_frame_indices"] = []
    normalized.setdefault("machine_asr_spans", [])
    normalized.setdefault("machine_ocr_evidence", [])
    if "ocr" not in modality_set and normalized["machine_ocr_evidence"]:
        normalized["machine_ocr_evidence"] = []
        actions.append("cleared_ocr_evidence_not_declared_as_required_modality")
    transcript = str(row.get("transcript", "") or "")
    spans = normalized.get("machine_asr_spans")
    if not transcript or not isinstance(spans, list):
        if {"asr", "joint"} & modality_set:
            remove_unverified_asr(normalized, modalities, actions)
        return normalized, actions
    canonical_spans = []
    search_from = 0
    unmatched_quote = False
    for span in spans:
        if not isinstance(span, dict) or not isinstance(span.get("quote"), str):
            unmatched_quote = True
            continue
        quote = span["quote"]
        start = transcript.find(quote, search_from)
        if start < 0:
            start = transcript.find(quote)
        if start < 0:
            unmatched_quote = True
            continue
        canonical_spans.append(
            {
                "start_char": start,
                "end_char": start + len(quote),
                "quote": quote,
            }
        )
        search_from = start + len(quote)
    normalized["machine_asr_spans"] = canonical_spans
    if (unmatched_quote or not canonical_spans) and ({"asr", "joint"} & modality_set):
        remove_unverified_asr(normalized, modalities, actions)
    return normalized, actions


def validate_annotation(annotation: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errors = []
    relation = annotation.get("machine_answer_relation")
    modalities = annotation.get("machine_required_modalities")
    frames = annotation.get("machine_frame_indices")
    asr_spans = annotation.get("machine_asr_spans")
    ocr = annotation.get("machine_ocr_evidence")
    confidence = annotation.get("machine_confidence")
    rationale = annotation.get("machine_rationale")
    allowed_frames = set(int(value) for value in row["raw32_frame_indices"])
    if relation not in ALLOWED_RELATIONS:
        errors.append("invalid_answer_relation")
    if not isinstance(modalities, list) or not set(modalities).issubset(ALLOWED_MODALITIES):
        errors.append("invalid_modalities")
    if not isinstance(frames, list) or any(not isinstance(value, int) or value not in allowed_frames for value in frames):
        errors.append("invalid_frame_indices")
    if not isinstance(asr_spans, list):
        errors.append("invalid_asr_spans")
    if not isinstance(ocr, list):
        errors.append("invalid_ocr_evidence")
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        errors.append("invalid_confidence")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("missing_rationale")
    if relation == "claim_absent_from_answer":
        if modalities or frames or asr_spans or ocr:
            errors.append("absent_claim_has_evidence")
        return errors
    if relation == "claim_present_insufficient" and not modalities:
        if frames or asr_spans or ocr:
            errors.append("insufficient_claim_has_unattributed_evidence")
        return errors
    if relation in ALLOWED_RELATIONS:
        if not modalities:
            errors.append("present_claim_missing_modalities")
        modality_set = set(modalities)
        if modality_set & {"visual", "ocr", "joint"} and not frames:
            errors.append("visual_or_ocr_missing_frames")
        if modality_set & {"asr", "joint"}:
            if not str(row.get("transcript", "") or "").strip():
                errors.append("asr_selected_when_unavailable")
            elif not asr_spans:
                errors.append("asr_missing_spans")
            else:
                transcript = str(row["transcript"])
                for span in asr_spans:
                    if not isinstance(span, dict):
                        errors.append("invalid_asr_span_record")
                        continue
                    start = span.get("start_char")
                    end = span.get("end_char")
                    quote = span.get("quote")
                    if (
                        not isinstance(start, int)
                        or not isinstance(end, int)
                        or not isinstance(quote, str)
                        or not 0 <= start < end <= len(transcript)
                        or transcript[start:end] != quote
                    ):
                        errors.append("asr_span_not_exact")
        if "ocr" in modality_set and not ocr:
            errors.append("ocr_missing_text")
        elif "ocr" in modality_set:
            for item in ocr:
                item_frames = item.get("frame_indices") if isinstance(item, dict) else None
                item_text = item.get("text") if isinstance(item, dict) else None
                if (
                    not isinstance(item_text, str)
                    or not item_text.strip()
                    or not isinstance(item_frames, list)
                    or not item_frames
                    or any(
                        not isinstance(value, int) or value not in allowed_frames
                        for value in item_frames
                    )
                ):
                    errors.append("ocr_evidence_not_anchored")
    return errors


def move_inputs(inputs: dict[str, Any], device: Any) -> dict[str, Any]:
    return {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}


def main() -> None:
    rows = read_jsonl(ARGS.template)
    if len(rows) != 240 or len({row.get("claim_id") for row in rows}) != 240:
        raise RuntimeError("machine preannotation requires exactly 240 unique Calibration claim rows")
    if any(PROTECTED_KEYS & set(row) for row in rows):
        raise RuntimeError("template contains protected label, answer, or score fields")
    for row in rows:
        if not (ARGS.calibration_root / row["raw32_contact_sheet"]).is_file():
            raise FileNotFoundError(f"missing contact sheet for {row['claim_id']}")
    if ARGS.output_root.exists() and not ARGS.resume:
        raise RuntimeError(f"refusing to overwrite {ARGS.output_root}")
    ARGS.output_root.mkdir(parents=True, exist_ok=True)
    result_path = ARGS.output_root / "machine_preannotations.jsonl"
    existing: dict[str, dict[str, Any]] = {}
    if result_path.exists():
        for prior in read_jsonl(result_path):
            existing[str(prior["claim_id"])] = prior
    if existing and not ARGS.resume:
        raise RuntimeError("existing output requires --resume")

    selected = sorted(rows, key=lambda row: stable_int(str(row["claim_id"])))
    if ARGS.limit > 0:
        selected = selected[: ARGS.limit]
    selected_ids = {str(row["claim_id"]) for row in selected}
    completed_ids = {
        claim_id
        for claim_id, prior in existing.items()
        if claim_id in selected_ids and not prior.get("validation_errors")
    }
    pending = [row for row in selected if str(row["claim_id"]) not in completed_ids]
    gpu_record = enforce_gpu_policy()
    write_json(
        ARGS.output_root / "run_config.json",
        {
            "schema": "adsqa_candidate_f_machine_preannotation_v1",
            "template": str(ARGS.template),
            "template_sha256": sha256_file(ARGS.template),
            "calibration_root": str(ARGS.calibration_root),
            "model_dir": str(ARGS.model_dir),
            "model_config_sha256": sha256_file(ARGS.model_dir / "config.json"),
            "requested_count": len(selected),
            "already_complete_count": len(completed_ids),
            "pending_count": len(pending),
            "limit": ARGS.limit,
            "max_new_tokens": ARGS.max_new_tokens,
            "max_image_pixels": ARGS.max_image_pixels,
            "machine_only": True,
            "not_human_gold": True,
            "started_at_epoch": int(time.time()),
            "gpu": gpu_record,
        },
    )

    from PIL import Image
    import torch
    from transformers import AutoModelForVision2Seq, AutoProcessor

    model = AutoModelForVision2Seq.from_pretrained(
        ARGS.model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir,
        min_pixels=256 * 256,
        max_pixels=ARGS.max_image_pixels,
        trust_remote_code=True,
    )
    for count, row in enumerate(pending, start=1):
        image_path = ARGS.calibration_root / row["raw32_contact_sheet"]
        image = Image.open(image_path).convert("RGB")
        prompt = prompt_for(row)
        message = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
        start = time.time()
        with torch.inference_mode():
            inputs = processor(
                text=[text_input],
                images=[image],
                padding=True,
                return_tensors="pt",
            )
            inputs = move_inputs(inputs, model.device)
            generated = model.generate(**inputs, do_sample=False, max_new_tokens=ARGS.max_new_tokens)
        input_length = int(inputs["input_ids"].shape[1])
        decoded = processor.batch_decode(
            generated[:, input_length:],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        raw_output = decoded[0].strip() if decoded else ""
        annotation, parse_error = extract_json(raw_output)
        canonicalization_actions: list[str] = []
        if annotation is not None:
            annotation, canonicalization_actions = canonicalize_annotation(annotation, row)
        validation_errors = validate_annotation(annotation, row) if annotation is not None else [parse_error or "unknown_parse_error"]
        output = {
            "schema": "adsqa_candidate_f_machine_preannotation_v1",
            "claim_id": row["claim_id"],
            "source_question_id": row["source_question_id"],
            "review_index": row["review_index"],
            "contact_sheet": row["raw32_contact_sheet"],
            "contact_sheet_sha256": sha256_file(image_path),
            "template_row_sha256": hashlib.sha256(
                json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "machine_annotation": annotation,
            "parse_error": parse_error,
            "validation_errors": validation_errors,
            "canonicalization_actions": canonicalization_actions,
            "raw_model_output": raw_output,
            "latency_seconds": time.time() - start,
            "machine_only": True,
            "not_human_gold": True,
        }
        append_jsonl(result_path, output)
        existing[str(row["claim_id"])] = output
        print(
            f"machine_preannotation {count}/{len(pending)} claim={row['claim_id']} "
            f"valid={not validation_errors}",
            flush=True,
        )
        torch.cuda.empty_cache()
    final_rows = [existing[str(row["claim_id"])] for row in selected]
    write_jsonl(result_path, final_rows)
    config_path = ARGS.output_root / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.update(
        {
            "ended_at_epoch": int(time.time()),
            "result_count": len(final_rows),
            "valid_annotation_count": sum(not row["validation_errors"] for row in final_rows),
            "invalid_annotation_count": sum(bool(row["validation_errors"]) for row in final_rows),
            "complete": len(final_rows) == len(selected),
            "post_run_gpu_snapshot": gpu_snapshot(ARGS.gpu_id),
        }
    )
    write_json(config_path, config)
    write_json(
        ARGS.output_root / "audit.json",
        {
            "schema": "adsqa_candidate_f_machine_preannotation_audit_v1",
            "template_sha256": sha256_file(ARGS.template),
            "result_sha256": sha256_file(result_path),
            "rows": len(final_rows),
            "valid_annotation_count": config["valid_annotation_count"],
            "invalid_annotation_count": config["invalid_annotation_count"],
            "machine_only": True,
            "not_human_gold": True,
            "human_template_modified": False,
            "threshold_calibration_allowed": False,
            "development_evaluation_allowed": False,
            "passed": config["complete"] and config["valid_annotation_count"] == len(selected),
        },
    )
    if config["invalid_annotation_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
