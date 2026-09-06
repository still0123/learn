#!/usr/bin/env python3
"""Score claim support under full, target-removed, and control-removed evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--oracle-jsonl", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("/data1/rmx/projectb/AdsQA-main"))
    parser.add_argument("--model-dir", default="/data1/qky/Model/Qwen3Vl-8B")
    parser.add_argument("--start-idx", type=int, default=0)
    parser.add_argument("--end-idx", type=int, default=-1)
    parser.add_argument("--mosaic-side", type=int, default=14)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--full-only", action="store_true")
    return parser.parse_args()


args = parse_args()
if args.gpu_id not in {"2", "3", "4", "5"}:
    raise ValueError("gpu-id must be 2, 3, 4, or 5")
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
PROJECT_ROOT = args.project_root.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configure_fair_module():
    saved_argv = list(sys.argv)
    sys.argv = [
        "inference_fair_baselines_v1.py", "--gpu_id", args.gpu_id,
        "--fair_method", "raw_uniform", "--question_file", str(args.input_jsonl),
        "--groundtruth_file", str(args.input_jsonl), "--asr_file", str(args.input_jsonl),
        "--output_dir", str(args.output_root), "--visual_view_budget", "32",
        "--max_post_merge_visual_tokens", "12000", "--unified_size", "896",
        "--oversample_count", "32", "--disable_reflection",
    ]
    try:
        from evaluation.methods.fair_protocol import inference_fair_baselines_v1 as fair
    finally:
        sys.argv = saved_argv
    fair.args.visual_view_budget = 32
    fair.args.max_post_merge_visual_tokens = 12000
    fair.args.unified_size = 896
    fair.args.disable_reflection = True
    return fair


FAIR = configure_fair_module()
import cv2  # noqa: E402
from PIL import Image  # noqa: E402
import torch  # noqa: E402

from evaluation.methods.claim_evidence_verifier.metrics_v2 import intervention_metrics  # noqa: E402


LOGGER = logging.getLogger("claim_evidence_intervention_smoke_v2")
STATES = ("full", "target_removed", "control_removed")
LABEL_CHOICES = {"supported": "A", "refuted": "B", "insufficient": "C"}


def load_selected_frames(video_path: str, indices: list[int]) -> list[Image.Image]:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    frames = []
    try:
        for frame_index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"cannot decode frame {frame_index}: {video_path}")
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frames.append(FAIR.smart_resize(image, FAIR.args.unified_size))
    finally:
        capture.release()
    if len(frames) != 32:
        raise RuntimeError(f"expected 32 decoded frames, got {len(frames)}")
    return frames


def mosaic_views(frames: list[Image.Image], indices: list[int]) -> list[Image.Image]:
    changed = set(int(value) for value in indices)
    output = []
    for index, frame in enumerate(frames):
        image = frame.convert("RGB")
        if index in changed:
            image = image.resize((args.mosaic_side, args.mosaic_side), Image.Resampling.BILINEAR).resize(
                frame.size, Image.Resampling.NEAREST
            )
        output.append(image)
    return output


def asr_without_indices(segments: list[dict[str, Any]], removed: list[int], fallback: str) -> str:
    if not segments:
        return fallback
    removed_set = set(int(value) for value in removed)
    return " ".join(str(row.get("text", "")).strip() for index, row in enumerate(segments) if index not in removed_set).strip()


def verifier_prompt(question: str, claim: str, asr: str) -> str:
    return (
        "Judge whether the claim is established by the supplied advertisement video and transcript. "
        "Use only supplied evidence. Choose exactly one label: A = supported, B = refuted, "
        "C = insufficient evidence. Do not explain.\n"
        f"Question: {question}\nClaim: {claim}\nTranscript: {asr[:1600]}\nLabel:"
    )


def resolve_label_token_ids(tokenizer) -> dict[str, int]:
    for prefix in ("", " "):
        encoded = {
            label: tokenizer.encode(prefix + choice, add_special_tokens=False)
            for label, choice in LABEL_CHOICES.items()
        }
        if all(len(value) == 1 for value in encoded.values()) and len({value[0] for value in encoded.values()}) == 3:
            return {label: value[0] for label, value in encoded.items()}
    raise RuntimeError("A/B/C labels are not distinct single tokens for this tokenizer")


def score_state(model, processor, token_ids: dict[str, int], frames, prompt: str) -> tuple[dict[str, float], dict[str, Any]]:
    message = [{"role": "user", "content": [
        {"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt},
    ]}]
    text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
    inputs, trace = FAIR.prepare_qwen_video_inputs(
        processor=processor, text_input=text_input, frames=frames, device=model.device,
        expected_view_count=32, max_post_merge_visual_tokens=12000,
        metadata_fps=1.0, require_exact_frame_count=True,
    )
    with torch.inference_mode():
        logits = model(**inputs, use_cache=False).logits[0, -1].float()
    label_logits = torch.stack([logits[token_ids[label]] for label in LABEL_CHOICES])
    probabilities = torch.softmax(label_logits, dim=0).cpu().tolist()
    scores = {label: float(probability) for label, probability in zip(LABEL_CHOICES, probabilities)}
    return scores, {
        "submitted_frame_count": trace.get("submitted_frame_count"),
        "represented_frame_count": trace.get("represented_frame_count"),
        "post_merge_visual_token_count": trace.get("post_merge_visual_token_count"),
        "secondary_frame_sampling_disabled": trace.get("secondary_frame_sampling_disabled"),
    }


def main() -> None:
    args.output_root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(args.output_root / "run.log", encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    inputs = load_jsonl(args.input_jsonl)
    plans = {} if args.full_only else {str(row["question_id"]): row for row in load_jsonl(args.oracle_jsonl)}
    end = len(inputs) if args.end_idx < 0 else min(args.end_idx, len(inputs))
    selected = inputs[args.start_idx:end]
    results_path = args.output_root / "scores.jsonl"
    existing = {} if args.overwrite or not results_path.exists() else {
        str(row["question_id"]): row for row in load_jsonl(results_path)
    }
    config = {
        "schema": "adsqa_claim_evidence_intervention_run_v2",
        "model_dir": args.model_dir, "gpu_id": args.gpu_id,
        "input_jsonl": str(args.input_jsonl), "input_sha256": sha256_file(args.input_jsonl),
        "oracle_jsonl": str(args.oracle_jsonl), "oracle_sha256": sha256_file(args.oracle_jsonl),
        "visual_view_budget": 32, "visual_token_budget": 12000,
        "secondary_frame_sampling_disabled": True, "rag": False, "reflection": False,
        "intervention": "full_evidence_only_v22" if args.full_only else f"equal_cost_target_control_mosaic{args.mosaic_side}_v2",
        "script_sha256": sha256_file(Path(__file__).resolve()),
    }
    dump_json(args.output_root / "run_config.json", config)
    model = FAIR.AutoModelForVision2Seq.from_pretrained(
        args.model_dir, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )
    processor = FAIR.AutoProcessor.from_pretrained(
        args.model_dir, min_pixels=256 * 256, max_pixels=1280 * 1280, trust_remote_code=True
    )
    token_ids = resolve_label_token_ids(processor.tokenizer)
    stats = {"requested": len(selected), "processed": 0, "skipped": 0, "errors": 0}
    for row in selected:
        qid = str(row["question_id"])
        if qid in existing and not args.overwrite:
            stats["skipped"] += 1
            continue
        started = time.time()
        try:
            frames = load_selected_frames(row["video_path"], row["selected_frame_indices"])
            states = ("full",) if args.full_only else STATES
            modality = "none"
            state_frames = {state: frames for state in states}
            state_asr = {state: str(row.get("asr_excerpt", "")) for state in states}
            plan = None
            if not args.full_only:
                oracle = plans[qid]
                plan = oracle["selected_plan"]
                if not plan.get("valid"):
                    raise RuntimeError(f"invalid intervention plan: {plan.get('reason')}")
                modality = str(plan["modality"])
                if modality == "visual":
                    state_frames["target_removed"] = mosaic_views(frames, plan["target_indices"])
                    state_frames["control_removed"] = mosaic_views(frames, plan["control_indices"])
                elif modality == "asr":
                    segments = list(row.get("asr_segments") or [])
                    full_segmented_asr = asr_without_indices(segments, [], state_asr["full"])
                    state_asr = {state: full_segmented_asr for state in STATES}
                    state_asr["target_removed"] = asr_without_indices(segments, plan["target_indices"], state_asr["full"])
                    state_asr["control_removed"] = asr_without_indices(segments, plan["control_indices"], state_asr["full"])
                else:
                    raise RuntimeError(f"unsupported modality: {modality}")
            scores, traces = {}, {}
            for state in states:
                prompt = verifier_prompt(row["question"], row["claim"], state_asr[state])
                scores[state], traces[state] = score_state(model, processor, token_ids, state_frames[state], prompt)
            result = {
                "schema": "adsqa_claim_evidence_intervention_scores_v2",
                "question_id": qid, "video_id": row["video_id"],
                "primary_type": row["primary_type"], "question": row["question"],
                "claim": row["claim"], "asr_excerpt": row.get("asr_excerpt", ""),
                "scores": scores,
                "metadata": {
                    "modality": modality,
                    "target_cost": plan["target_cost"] if plan else 0,
                    "control_cost": plan["control_cost"] if plan else 0,
                    "ocr_present": bool(row.get("ocr_present", False)),
                },
                "processor_traces": traces, "elapsed_sec": time.time() - started,
            }
            append_jsonl(results_path, result)
            stats["processed"] += 1
            LOGGER.info("%s complete (%d/%d)", qid, stats["processed"] + stats["skipped"], len(selected))
        except Exception as error:
            stats["errors"] += 1
            append_jsonl(args.output_root / "errors.jsonl", {
                "question_id": qid, "error": str(error), "traceback": traceback.format_exc(),
            })
            LOGGER.exception("%s failed", qid)
    all_results = load_jsonl(results_path) if results_path.exists() else []
    selected_ids = {str(row["question_id"]) for row in selected}
    aligned = [row for row in all_results if str(row["question_id"]) in selected_ids]
    protocol_errors = []
    for row in aligned:
        for state, trace in row.get("processor_traces", {}).items():
            if trace.get("submitted_frame_count") != 32 or trace.get("represented_frame_count") != 32:
                protocol_errors.append({"question_id": row["question_id"], "state": state, "error": "view_count"})
            if int(trace.get("post_merge_visual_token_count", 999999)) > 12000:
                protocol_errors.append({"question_id": row["question_id"], "state": state, "error": "token_budget"})
            if trace.get("secondary_frame_sampling_disabled") is not True:
                protocol_errors.append({"question_id": row["question_id"], "state": state, "error": "secondary_sampling"})
    summary = {
        "schema": "adsqa_claim_evidence_intervention_summary_v2",
        "stats": stats, "complete": len(aligned) == len(selected) and not stats["errors"],
        "protocol_errors": protocol_errors,
        "protocol_passed": len(aligned) == len(selected) and not protocol_errors,
        "intervention_metrics": intervention_metrics(aligned) if aligned and not args.full_only else None,
    }
    dump_json(args.output_root / "summary.json", summary)
    LOGGER.info("summary: %s", json.dumps(summary["stats"]))
    if stats["errors"] or not summary["protocol_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
