#!/usr/bin/env python3
"""Run clean Qwen3-VL on an answer-free, preselected eight-frame manifest."""

from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Mapping

from adsqa_sft_lora_common_v1 import (
    append_jsonl,
    asr_text,
    dump_json,
    ensure_idle_gpu,
    load_asr,
    resolve_video_path,
    sha256_file,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path)
    parser.add_argument("--method", required=True)
    parser.add_argument("--question-file", type=Path, required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--asr-file", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--frames-fallback-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--views", type=int, default=8)
    parser.add_argument("--unified-size", type=int, default=448)
    parser.add_argument("--max-visual-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--max-items", type=int, default=-1)
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_questions(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    required = {"question_id", "video", "question", "fold", "source_split"}
    forbidden = {"answer", "ground_truth", "reference_answer", "judge_score", "prediction"}
    if not isinstance(rows, list) or any(not required.issubset(row) for row in rows):
        raise RuntimeError("question file does not satisfy answer-free SFT inference schema")
    if any(forbidden & set(row) for row in rows):
        raise RuntimeError("answer-free inference file contains a forbidden outcome field")
    return rows


def load_selection_manifest(path: Path, expected_views: int) -> dict[str, dict[str, Any]]:
    forbidden = {"answer", "ground_truth", "reference_answer", "judge_score", "prediction"}
    rows: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or forbidden & set(row):
            raise RuntimeError(f"invalid answer-free selection row at line {line_number}")
        question_id = str(row.get("question_id", ""))
        indices = row.get("selected_frame_indices")
        if not question_id or question_id in rows:
            raise RuntimeError(f"duplicate or missing selection question_id at line {line_number}")
        if not isinstance(indices, list) or len(indices) != expected_views:
            raise RuntimeError(f"selection {question_id} does not contain {expected_views} frames")
        normalized = [int(value) for value in indices]
        if normalized != sorted(normalized) or len(set(normalized)) != expected_views:
            raise RuntimeError(f"selection {question_id} is not unique chronological evidence")
        row["selected_frame_indices"] = normalized
        rows[question_id] = row
    return rows


def load_selected_frames(
    video_path: Path,
    indices: list[int],
    unified_size: int,
    selection_method: str,
) -> tuple[list[Any], list[dict[str, Any]]]:
    from decord import VideoReader, cpu
    from PIL import Image

    if video_path.is_file():
        reader = VideoReader(str(video_path), ctx=cpu(0))
        total = len(reader)
        if total <= 0 or any(index < 0 or index >= total for index in indices):
            raise RuntimeError(f"selection exceeds video frame range: {video_path}")
        fps = float(reader.get_avg_fps() or 0.0)
        frames = [
            Image.fromarray(reader[index].asnumpy()).convert("RGB").resize(
                (unified_size, unified_size), Image.Resampling.BICUBIC
            )
            for index in indices
        ]
        metadata = [
            {
                "input_index": rank,
                "source_frame_index": int(index),
                "source_total_frame_count": int(total),
                "source_timestamp_sec": float(index / fps) if fps > 0 else None,
                "view_type": selection_method,
            }
            for rank, index in enumerate(indices)
        ]
        return frames, metadata
    if video_path.is_dir():
        images = sorted(video_path.glob("*.jpg")) + sorted(video_path.glob("*.png"))
        if not images or any(index < 0 or index >= len(images) for index in indices):
            raise RuntimeError(f"selection exceeds frame fallback range: {video_path}")
        frames = [
            Image.open(images[index]).convert("RGB").resize(
                (unified_size, unified_size), Image.Resampling.BICUBIC
            )
            for index in indices
        ]
        metadata = [
            {
                "input_index": rank,
                "source_frame_index": int(index),
                "source_total_frame_count": int(len(images)),
                "source_timestamp_sec": None,
                "view_type": selection_method,
            }
            for rank, index in enumerate(indices)
        ]
        return frames, metadata
    raise RuntimeError(f"cannot resolve video or frame fallback: {video_path}")


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and args.overwrite:
        raise RuntimeError("overwrite is intentionally unsupported for this immutable inference run")
    questions = load_questions(args.question_file)
    if args.max_items > 0:
        questions = questions[: args.max_items]
    if args.num_shards <= 0 or not 0 <= args.shard_id < args.num_shards:
        raise RuntimeError("invalid shard configuration")
    questions = [
        row
        for index, row in enumerate(questions)
        if index % args.num_shards == args.shard_id
    ]
    if not questions:
        raise RuntimeError("no questions requested")
    selections = load_selection_manifest(args.selection_manifest, args.views)
    question_ids = {str(row["question_id"]) for row in questions}
    requested_selections = {
        question_id: selections[question_id]
        for question_id in question_ids
        if question_id in selections
    }
    if set(requested_selections) != question_ids:
        missing = sorted(question_ids - set(selections))
        raise RuntimeError(f"selection/question mismatch: missing={missing[:5]}")
    selections = requested_selections
    gpu_snapshot = ensure_idle_gpu(args.gpu_id)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch
    from peft import PeftModel
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    from evaluation.methods.common.adsqa_prompt import (
        ADSQA_ANSWER_PROMPT_VERSION,
        adsqa_answer_prompt_sha256,
        build_adsqa_answer_prompt,
    )
    from evaluation.methods.common.qwen_video_budget import prepare_qwen_video_inputs

    args.output_dir.mkdir(parents=True, exist_ok=True)
    asr = load_asr(args.asr_file)
    config = {
        "schema_version": "adsqa_qwen3_selected8_inference_v1",
        "model_family": "qwen3_vl",
        "method": args.method,
        "gpu_id": args.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "model_dir": str(args.model_dir.resolve()),
        "model_config_sha256": sha256_file(args.model_dir / "config.json"),
        "adapter_dir": str(args.adapter_dir.resolve()) if args.adapter_dir else None,
        "adapter_config_sha256": sha256_file(args.adapter_dir / "adapter_config.json") if args.adapter_dir else None,
        "question_file": str(args.question_file.resolve()),
        "question_file_sha256": sha256_file(args.question_file),
        "selection_manifest": str(args.selection_manifest.resolve()),
        "selection_manifest_sha256": sha256_file(args.selection_manifest),
        "question_count": len(questions),
        "shard_id": args.shard_id,
        "num_shards": args.num_shards,
        "asr_file_sha256": sha256_file(args.asr_file),
        "views": args.views,
        "unified_size": args.unified_size,
        "max_visual_tokens": args.max_visual_tokens,
        "max_new_tokens": args.max_new_tokens,
        "answer_prompt_version": ADSQA_ANSWER_PROMPT_VERSION,
        "answer_prompt_sha256": adsqa_answer_prompt_sha256(),
        "groundtruth_file_read": False,
        "testset_read": False,
        "secondary_frame_sampling_disabled": True,
    }
    dump_json(args.output_dir / "run_config.json", config)
    processor = AutoProcessor.from_pretrained(
        args.model_dir,
        min_pixels=args.unified_size * args.unified_size,
        max_pixels=args.unified_size * args.unified_size,
        trust_remote_code=True,
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
    )
    if str(model.config.model_type) != "qwen3_vl":
        raise RuntimeError(
            f"expected qwen3_vl, got {model.config.model_type}"
        )
    if args.adapter_dir:
        model = PeftModel.from_pretrained(model, args.adapter_dir)
    model.eval()
    errors_path = args.output_dir / "logs" / "errors.jsonl"
    stats = {"processed": 0, "skipped_existing": 0, "errors": 0}
    for row in questions:
        question_id = str(row["question_id"])
        item_dir = args.output_dir / question_id
        prediction_path = item_dir / "prediction.json"
        evidence_path = item_dir / "evidence.json"
        if prediction_path.exists() and evidence_path.exists():
            stats["skipped_existing"] += 1
            continue
        started = time.time()
        try:
            video_id = str(row["video"])
            selection = selections[question_id]
            if str(selection.get("video_id", "")) != video_id:
                raise RuntimeError(f"selection video mismatch for {question_id}")
            video_path = resolve_video_path(video_id, args.video_root, args.frames_fallback_root)
            frames, visual_plan = load_selected_frames(
                video_path,
                selection["selected_frame_indices"],
                args.unified_size,
                str(selection.get("selection_method", args.method)),
            )
            transcript = asr_text(asr, video_id)[:1600]
            prompt = build_adsqa_answer_prompt(str(row["question"]), transcript)
            message = [{
                "role": "user",
                "content": [
                    {"type": "video", "video": frames, "fps": 1.0},
                    {"type": "text", "text": prompt},
                ],
            }]
            text = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
            inputs, trace = prepare_qwen_video_inputs(
                processor=processor,
                text_input=text,
                frames=frames,
                device=model.device,
                expected_view_count=args.views,
                max_post_merge_visual_tokens=args.max_visual_tokens,
                metadata_fps=1.0,
                frame_indices=[int(item["source_frame_index"]) for item in visual_plan],
                require_exact_frame_count=True,
            )
            with torch.inference_mode():
                generated = model.generate(**inputs, do_sample=False, max_new_tokens=args.max_new_tokens)
            trimmed = [output[len(source):] for source, output in zip(inputs.input_ids, generated)]
            prediction = processor.batch_decode(
                trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0].strip()
            item_dir.mkdir(parents=True, exist_ok=True)
            dump_json(prediction_path, {
                "question_id": question_id,
                "video": video_id,
                "prediction": prediction,
                "method": args.method,
            })
            dump_json(evidence_path, {
                "question_id": question_id,
                "video": video_id,
                "question": row["question"],
                "asr_excerpt": transcript,
                "selection_provenance": selection,
                "input_image_count": len(frames),
                "visual_plan": visual_plan,
                "processor_trace": trace,
                "latency_seconds": time.time() - started,
            })
            stats["processed"] += 1
        except Exception as error:
            append_jsonl(errors_path, {
                "question_id": question_id,
                "error": repr(error),
                "traceback": traceback.format_exc(),
            })
            stats["errors"] += 1
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
    config["stats"] = stats
    dump_json(args.output_dir / "run_summary.json", config)
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
