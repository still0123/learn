#!/usr/bin/env python3
"""Explore Raw32 plus eight AV crops on Dev100 with dynamic visual tokens.

This is deliberately an exploratory, non-fixed-token run. It must not be
compared with the fixed 32-view/11,664-token main table.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", type=int, required=True)
    parser.add_argument("--goal-start-epoch", type=int, required=True)
    parser.add_argument("--question-file", type=Path, required=True)
    parser.add_argument("--groundtruth-file", type=Path, required=True)
    parser.add_argument("--asr-file", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, default=Path("/data1/qky/Model/Qwen3Vl-8B"))
    parser.add_argument(
        "--clip-path",
        type=Path,
        default=Path("/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14"),
    )
    parser.add_argument(
        "--video-root",
        type=Path,
        default=Path("/data1/rmx/projectb/AdsQA-main/data/videos"),
    )
    parser.add_argument(
        "--frames-fallback-root",
        type=Path,
        default=Path("/data1/rmx/projectb/AdsQA-main/data/frames_8"),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = str(ARGS.gpu_id)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
sys.modules["torchcodec"] = None
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RAW_GLOBAL_COUNT = 32
AV_CROP_COUNT = 8
INPUT_VIEW_COUNT = RAW_GLOBAL_COUNT + AV_CROP_COUNT


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


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
    raw_processes = command_output(
        [
            "nvidia-smi",
            "-i",
            str(gpu_id),
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    processes = []
    for line in raw_processes.splitlines():
        if not line.strip() or line.lower().startswith("no running"):
            continue
        fields = [field.strip() for field in line.split(",", 2)]
        if len(fields) == 3:
            processes.append(
                {
                    "pid": int(fields[0]),
                    "process_name": fields[1],
                    "used_memory_mib": int(fields[2]),
                }
            )
    return {"captured_at_epoch": int(time.time()), "gpu": gpu, "compute_processes": processes}


def enforce_gpu_policy() -> dict[str, Any]:
    now = int(time.time())
    window_end = ARGS.goal_start_epoch + 21600
    allowed = {1, 2, 4, 5} if now < window_end else {4, 5}
    if ARGS.gpu_id not in allowed:
        raise RuntimeError(f"GPU{ARGS.gpu_id} outside policy; allowed={sorted(allowed)}")
    snapshot = gpu_snapshot(ARGS.gpu_id)
    if snapshot["compute_processes"]:
        raise RuntimeError(f"GPU{ARGS.gpu_id} not idle: {snapshot['compute_processes']}")
    return {
        "goal_start_epoch": ARGS.goal_start_epoch,
        "gpu_window_end_epoch": window_end,
        "allowed_gpu_ids": sorted(allowed),
        "pre_launch_snapshot": snapshot,
    }


def configure_av_module() -> Any:
    """Import AV utilities while explicitly freezing their selection configuration."""
    av_dir = PROJECT_ROOT / "evaluation" / "methods" / "av_evidence"
    if str(av_dir) not in sys.path:
        sys.path.insert(0, str(av_dir))
    saved_argv = list(sys.argv)
    sys.argv = [
        "inference_av_evidence_budget_v1.py",
        "--gpu_id",
        str(ARGS.gpu_id),
        "--question_file",
        str(ARGS.question_file),
        "--groundtruth_file",
        str(ARGS.groundtruth_file),
        "--asr_file",
        str(ARGS.asr_file),
        "--output_dir",
        str(ARGS.output_root),
        "--oversample_count",
        str(RAW_GLOBAL_COUNT),
        "--top_k_frames",
        str(RAW_GLOBAL_COUNT),
        "--visual_image_budget",
        str(INPUT_VIEW_COUNT),
        "--max_post_merge_visual_tokens",
        "0",
        "--ocr_proxy",
        "semantic",
        "--max_local_views_per_frame",
        "1",
    ]
    try:
        from evaluation.methods.av_evidence import inference_av_evidence_budget_v1 as av
    finally:
        sys.argv = saved_argv
    av.args.gpu_id = str(ARGS.gpu_id)
    av.args.oversample_count = RAW_GLOBAL_COUNT
    av.args.top_k_frames = RAW_GLOBAL_COUNT
    av.args.visual_image_budget = INPUT_VIEW_COUNT
    av.args.max_post_merge_visual_tokens = 0
    av.args.ocr_proxy = "semantic"
    av.args.max_local_views_per_frame = 1
    av.args.unified_size = None
    return av


def resolve_video(av: Any, video_id: str) -> str:
    av.args.video_root = str(ARGS.video_root)
    av.args.frames_fallback_root = str(ARGS.frames_fallback_root)
    return av.resolve_video_path(video_id)


def raw32_plus_avcrop8(
    av: Any,
    visual_processor: Any,
    raw_frames: list[Any],
    raw_metadata: list[dict[str, Any]],
    question: str,
    asr_evidence: dict[str, Any],
) -> tuple[list[Any], list[dict[str, Any]], dict[str, Any]]:
    """Retain all Raw32 frames and append exactly eight unresized AV crops."""
    offset_trace = visual_processor.estimate_audio_offset(raw_frames, raw_metadata, asr_evidence)
    selected_frames, selected_metadata = visual_processor.select_frames(
        raw_frames,
        raw_metadata,
        question,
        asr_evidence,
        float(offset_trace.get("offset_seconds", 0.0)),
        RAW_GLOBAL_COUNT,
    )
    if len(selected_frames) != RAW_GLOBAL_COUNT:
        raise RuntimeError(f"Raw32 selection drift: expected 32, got {len(selected_frames)}")
    crop_images: dict[str, Any] = {}
    crop_records: list[dict[str, Any]] = []
    response_traces = []
    for frame_rank, (frame, metadata) in enumerate(zip(selected_frames, selected_metadata)):
        candidates, response_trace = visual_processor.crop_candidates(
            frame,
            question,
            str(metadata.get("audio_window_text", "")),
            str(metadata.get("audio_window_trace", {}).get("mode", "global_fallback")),
            [],
        )
        response_traces.append({"frame_rank": frame_rank, **response_trace})
        for local_rank, (crop, crop_meta) in enumerate(candidates):
            crop_id = f"{frame_rank}:{local_rank}"
            crop_images[crop_id] = crop
            crop_records.append(
                {
                    **crop_meta,
                    "candidate_id": crop_id,
                    "frame_rank": frame_rank,
                    "source_frame_index": int(metadata["frame_index"]),
                    "source_sample_rank": int(metadata["sample_rank"]),
                }
            )
    selected_crops, allocation = av.allocate_local_budget(
        crop_records,
        global_count=RAW_GLOBAL_COUNT,
        visual_budget=INPUT_VIEW_COUNT,
        max_per_frame=1,
    )
    if len(selected_crops) != AV_CROP_COUNT:
        raise RuntimeError(f"AVCrop8 allocation drift: expected 8, got {len(selected_crops)}")
    frames = list(selected_frames)
    visual_plan = [
        {
            "input_index": index,
            "view_type": "raw_global",
            "raw_rank": index,
            "frame_index": int(metadata["frame_index"]),
            "sample_rank": int(metadata["sample_rank"]),
            "timestamp_sec": metadata.get("timestamp_sec"),
        }
        for index, metadata in enumerate(selected_metadata)
    ]
    for crop in sorted(selected_crops, key=lambda item: int(item["budget_rank"])):
        crop_id = str(crop["candidate_id"])
        frames.append(crop_images[crop_id])
        visual_plan.append(
            {
                "input_index": len(frames) - 1,
                "view_type": "av_crop",
                "raw_rank": int(crop["frame_rank"]),
                "frame_index": int(crop["source_frame_index"]),
                "candidate_id": crop_id,
                "bbox": crop.get("bbox"),
                "bbox_norm": crop.get("bbox_norm"),
                "budget_rank": int(crop["budget_rank"]),
                "budget_utility": crop.get("budget_utility"),
                "original_image_size": list(crop_images[crop_id].size),
            }
        )
    if len(frames) != INPUT_VIEW_COUNT:
        raise RuntimeError(f"input count drift: expected 40, got {len(frames)}")
    return frames, visual_plan, {
        "offset_trace": offset_trace,
        "response_traces": response_traces,
        "crop_candidate_count": len(crop_records),
        "selected_crops": selected_crops,
        "allocation": allocation,
        "raw_frame_sizes": [list(frame.size) for frame in selected_frames],
        "crop_frame_sizes": [list(frame.size) for frame in frames[RAW_GLOBAL_COUNT:]],
    }


def standardize_within_video_shape(frames: list[Any]) -> tuple[list[Any], dict[str, Any]]:
    """Use one native canvas per video while preserving cross-video token variation."""
    from PIL import Image

    if not frames:
        raise ValueError("cannot standardize an empty frame list")
    target_size = tuple(int(value) for value in frames[0].size)
    original_sizes = [list(frame.size) for frame in frames]
    converted = [
        frame
        if tuple(frame.size) == target_size
        else frame.resize(target_size, Image.Resampling.BICUBIC)
        for frame in frames
    ]
    return converted, {
        "mode": "per_video_native_canvas",
        "target_size": list(target_size),
        "original_sizes": original_sizes,
        "resized_input_count": sum(size != list(target_size) for size in original_sizes),
        "cross_video_fixed_size": False,
        "fixed_896_resize": False,
    }


def generate_response(
    model: Any,
    processor: Any,
    frames: list[Any],
    prompt: str,
    source_frame_indices: list[int],
) -> tuple[str, dict[str, Any]]:
    from evaluation.methods.common.qwen_video_budget import prepare_qwen_video_inputs
    import torch

    message = [
        {
            "role": "user",
            "content": [
                {"type": "video", "video": frames, "fps": 1.0},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
    inputs, trace = prepare_qwen_video_inputs(
        processor=processor,
        text_input=text_input,
        frames=frames,
        device=model.device,
        expected_view_count=INPUT_VIEW_COUNT,
        max_post_merge_visual_tokens=0,
        metadata_fps=1.0,
        frame_indices=source_frame_indices,
        require_exact_frame_count=True,
    )
    with torch.inference_mode():
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=ARGS.max_new_tokens)
    trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated)]
    decoded = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return (decoded[0].strip() if decoded else ""), trace


def main() -> None:
    if ARGS.output_root.exists() and not ARGS.resume:
        raise RuntimeError(f"refusing to overwrite {ARGS.output_root}")
    questions = read_json(ARGS.question_file)
    groundtruth = {
        str(row["question_id"]): str(row.get("answer", ""))
        for row in read_json(ARGS.groundtruth_file)
    }
    asr_data = read_json(ARGS.asr_file)
    if len(questions) != 100 or len({str(row["question_id"]) for row in questions}) != 100:
        raise RuntimeError("Dev100 question file must contain exactly 100 unique questions")
    if ARGS.limit > 0:
        questions = questions[: ARGS.limit]
    gpu_record = enforce_gpu_policy()
    ARGS.output_root.mkdir(parents=True, exist_ok=True)
    av = configure_av_module()
    write_json(
        ARGS.output_root / "run_config.json",
        {
            "schema": "adsqa_raw32_avcrop8_nonfixedtoken_dev100_v1",
            "experiment_class": "exploratory_nonfixed_token",
            "not_comparable_to_fixed_token_main_table": True,
            "method": "Raw32_plus_AVCrop8",
            "raw_global_count": RAW_GLOBAL_COUNT,
            "av_crop_count": AV_CROP_COUNT,
            "input_view_count": INPUT_VIEW_COUNT,
            "secondary_frame_sampling_disabled": True,
            "max_post_merge_visual_tokens": None,
            "unified_resize": False,
            "rag_enabled": False,
            "reflection_enabled": False,
            "answer_prompt_sha256": av.adsqa_answer_prompt_sha256(),
            "question_file": str(ARGS.question_file),
            "question_file_sha256": sha256_file(ARGS.question_file),
            "groundtruth_file": str(ARGS.groundtruth_file),
            "groundtruth_file_sha256": sha256_file(ARGS.groundtruth_file),
            "asr_file": str(ARGS.asr_file),
            "asr_file_sha256": sha256_file(ARGS.asr_file),
            "model_dir": str(ARGS.model_dir),
            "model_config_sha256": sha256_file(ARGS.model_dir / "config.json"),
            "script_sha256": sha256_file(Path(__file__)),
            "gpu": gpu_record,
            "requested_question_count": len(questions),
            "started_at_epoch": int(time.time()),
        },
    )

    import torch
    from transformers import AutoModelForVision2Seq, AutoProcessor

    visual_processor = av.VisualEvidenceProcessor(device="cuda", clip_path=str(ARGS.clip_path))
    if not visual_processor.valid:
        raise RuntimeError(f"AV response processor unavailable: {visual_processor.error}")
    model = AutoModelForVision2Seq.from_pretrained(
        ARGS.model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir,
        min_pixels=256 * 256,
        max_pixels=1280 * 1280,
        trust_remote_code=True,
    )
    stats = {"processed": 0, "skipped_existing": 0, "errors": 0}
    for global_index, item in enumerate(questions):
        qid = str(item["question_id"])
        q_dir = ARGS.output_root / qid
        prediction_path = q_dir / "prediction.json"
        evidence_path = q_dir / "evidence.json"
        if prediction_path.exists() and evidence_path.exists() and ARGS.resume:
            stats["skipped_existing"] += 1
            continue
        started = time.time()
        try:
            video_id = str(item.get("video", item.get("video_id", qid.split("_")[0])))
            video_path = resolve_video(av, video_id)
            raw_frames, raw_metadata = av.load_frames_oversampled(video_path, RAW_GLOBAL_COUNT)
            if len(raw_frames) != RAW_GLOBAL_COUNT:
                raise RuntimeError(f"expected Raw32, got {len(raw_frames)}")
            raw_asr = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, ""))
            asr_evidence = av.normalize_asr(raw_asr)
            frames, visual_plan, crop_trace = raw32_plus_avcrop8(
                av,
                visual_processor,
                raw_frames,
                raw_metadata,
                str(item["question"]),
                asr_evidence,
            )
            frames, shape_trace = standardize_within_video_shape(frames)
            crop_trace["processor_shape_adapter"] = shape_trace
            source_indices = [int(item["frame_index"]) for item in visual_plan]
            prompt = av.build_adsqa_answer_prompt(
                str(item["question"]),
                str(asr_evidence.get("transcript", "")),
            )
            prediction, processor_trace = generate_response(
                model,
                processor,
                frames,
                prompt,
                source_indices,
            )
            q_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                prediction_path,
                {
                    "question_id": qid,
                    "prediction": prediction,
                    "ground_truth": groundtruth.get(qid, ""),
                    "pipeline": "Raw32_plus_AVCrop8_nonfixedtoken_Qwen3VL",
                    "rag_mode": "none",
                    "reflection_status": "disabled",
                    "score": "",
                },
            )
            write_json(
                evidence_path,
                {
                    "schema": "adsqa_raw32_avcrop8_nonfixedtoken_item_v1",
                    "question_id": qid,
                    "global_index": global_index,
                    "video_id": video_id,
                    "video_path": video_path,
                    "question": item["question"],
                    "raw_asr_mode": asr_evidence.get("mode"),
                    "raw32_frame_count": RAW_GLOBAL_COUNT,
                    "av_crop_count": AV_CROP_COUNT,
                    "input_image_count": len(frames),
                    "visual_plan": visual_plan,
                    "crop_trace": crop_trace,
                    "processor_trace": processor_trace,
                    "dynamic_visual_tokens": processor_trace["post_merge_visual_token_count"],
                    "protocol": {
                        "exploratory_nonfixed_token": True,
                        "not_comparable_to_fixed_token_main_table": True,
                        "secondary_frame_sampling_disabled": True,
                        "rag_enabled": False,
                        "reflection_enabled": False,
                    },
                    "latency_seconds": time.time() - started,
                },
            )
            stats["processed"] += 1
            print(
                f"raw32_avcrop8 {stats['processed'] + stats['skipped_existing']}/{len(questions)} "
                f"{qid} tokens={processor_trace['post_merge_visual_token_count']}",
                flush=True,
            )
        except Exception as error:
            stats["errors"] += 1
            append_jsonl(
                ARGS.output_root / "errors.jsonl",
                {
                    "question_id": qid,
                    "error": repr(error),
                    "traceback": traceback.format_exc(),
                },
            )
            print(f"raw32_avcrop8 error {qid}: {error!r}", flush=True)
        finally:
            torch.cuda.empty_cache()
            gc.collect()
    config_path = ARGS.output_root / "run_config.json"
    config = read_json(config_path)
    config.update(
        {
            "ended_at_epoch": int(time.time()),
            "stats": stats,
            "complete": stats["processed"] + stats["skipped_existing"] == len(questions),
            "post_run_gpu_snapshot": gpu_snapshot(ARGS.gpu_id),
        }
    )
    write_json(config_path, config)
    if stats["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
