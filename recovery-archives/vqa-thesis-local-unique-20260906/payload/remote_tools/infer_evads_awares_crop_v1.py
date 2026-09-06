#!/usr/bin/env python3
"""Generate policy crop and matched global candidates."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-size", type=int, default=512)
    parser.add_argument("--crop-size", type=int, default=896)
    parser.add_argument("--max-visual-tokens", type=int, default=2592)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--expected-items", type=int, default=10)
    parser.add_argument("--skip-a1", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ARGS.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from decord import VideoReader, cpu  # noqa: E402
from PIL import Image  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration  # noqa: E402


FORBIDDEN = {
    "answer",
    "ground_truth",
    "reference_answer",
    "meta_info",
    "judge_score",
    "label",
}
VARIANTS = {
    "anchor_global10",
    "awares_first10",
    "adaptvision_bbox10",
    "deepeyes_firstzoom10",
    "zoomeye_union10",
    "vlmr3_lastbbox10",
    "hide_layout10",
    "qzoom_roi10",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_idle_gpu(gpu_id: str) -> list[str]:
    if gpu_id not in {"0", "1", "2", "3", "4", "5"}:
        raise RuntimeError("only currently reserved GPUs 0,1,2,3,4,5 are allowed")
    snapshot = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = [line.strip() for line in snapshot.stdout.splitlines() if line.strip()]
    matching = [row for row in rows if row.split(",", 1)[0].strip() == gpu_id]
    processes = subprocess.run(
        [
            "nvidia-smi",
            f"--id={gpu_id}",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    active = [line.strip() for line in processes.stdout.splitlines() if line.strip()]
    if len(matching) != 1 or active:
        raise RuntimeError(f"GPU{gpu_id} is not idle: {active}")
    return matching


def decode_frames(
    video_path: str,
    indices: list[int],
    size: int,
) -> tuple[list[Image.Image], int, float]:
    reader = VideoReader(video_path, ctx=cpu(0))
    total = len(reader)
    if total <= 0:
        raise RuntimeError(f"video has no frames: {video_path}")
    if any(index < 0 or index >= total for index in indices):
        raise RuntimeError(f"source frame index outside video: {video_path}")
    fps = float(reader.get_avg_fps() or 0.0)
    frames = [
        Image.fromarray(reader[index].asnumpy()).convert("RGB").resize(
            (size, size), Image.Resampling.BICUBIC
        )
        for index in indices
    ]
    return frames, total, fps


def crop_frame(frame: Image.Image, bbox_norm: list[float], size: int) -> tuple[Image.Image, list[int]]:
    width, height = frame.size
    left, top, right, bottom = [
        max(0.0, min(1.0, float(value))) for value in bbox_norm
    ]
    if right <= left or bottom <= top:
        raise RuntimeError("empty normalized crop")
    box = [
        max(0, min(width - 1, round(left * width))),
        max(0, min(height - 1, round(top * height))),
        max(1, min(width, round(right * width))),
        max(1, min(height, round(bottom * height))),
    ]
    if box[2] <= box[0] or box[3] <= box[1]:
        raise RuntimeError("empty pixel crop")
    crop = frame.crop(tuple(box)).resize((size, size), Image.Resampling.BICUBIC)
    return crop, box


def a1_prompt(row: dict[str, Any]) -> str:
    return (
        "Answer the advertisement-video question by reconsidering the initial answer once. "
        "Use only the same eight chronological video frames and transcript supplied here. "
        "Keep the initial answer unless the supplied evidence gives a decisive reason to revise it. "
        "Return exactly one line beginning with [Answer]: and no analysis.\n"
        f"Question: {row['question']}\n"
        f"Initial answer: {row['a0_prediction']}\n"
        f"Transcript: {str(row.get('a0_asr_excerpt', ''))[:1600]}\n"
    )


def a2_prompt(row: dict[str, Any]) -> str:
    ocr_lines = [
        (
            f"{item['id']} @ {float(item['timestamp_sec']):.2f}s "
            f"(confidence {float(item['confidence']):.2f}): {item['text']}"
        )
        for item in row.get("ocr_evidence", [])
    ]
    asr_lines = [
        (
            f"{item['id']} @ {float(item['start_sec']):.2f}-"
            f"{float(item['end_sec']):.2f}s: {item['text']}"
        )
        for item in row.get("asr_evidence", [])
    ]
    return (
        "Answer the advertisement-video question using all supplied evidence. "
        "Treat the initial answer as a draft, not as authority. "
        "V1-V8 are the original chronological global frames. "
        "Inspect the two high-resolution evidence views V9 and V10 carefully, "
        "and revise the draft whenever the total visual, OCR, or ASR evidence "
        "supports a better answer. OCR and ASR evidence may be missing; "
        "absence is not a contradiction. Use only the supplied advertisement "
        "evidence. Return exactly one line beginning with [Answer]: and no analysis.\n"
        f"Question: {row['question']}\n"
        f"Initial answer: {row['a0_prediction']}\n"
        "OCR evidence:\n"
        + ("\n".join(ocr_lines) if ocr_lines else "[OCR unavailable]")
        + "\nASR evidence:\n"
        + ("\n".join(asr_lines) if asr_lines else "[ASR unavailable]")
        + "\n"
    )


def count_visual_tokens(processor: Any, inputs: dict[str, Any]) -> int:
    visual_token_ids = [
        processor.tokenizer.convert_tokens_to_ids(token)
        for token in ("<|image_pad|>", "<|video_pad|>")
    ]
    count = sum(
        int((inputs["input_ids"] == token_id).sum().item())
        for token_id in visual_token_ids
        if token_id is not None
    )
    if count:
        return count
    total = 0
    for key, processor_name in (
        ("image_grid_thw", "image_processor"),
        ("video_grid_thw", "video_processor"),
    ):
        grids = inputs.get(key)
        if grids is None:
            continue
        merge_size = int(getattr(getattr(processor, processor_name), "merge_size", 2))
        total += int(
            sum(int(grid.prod().item()) // (merge_size * merge_size) for grid in grids)
        )
    if not total:
        raise RuntimeError("processor returned no visual grid")
    return total


def generate(
    processor: Any,
    model: Any,
    base_frames: list[Image.Image],
    extra_frames: list[Image.Image],
    base_frame_indices: list[int],
    prompt: str,
) -> tuple[str, dict[str, Any]]:
    content = [{"type": "video", "video": base_frames, "fps": 1.0}]
    content.extend({"type": "image", "image": frame} for frame in extra_frames)
    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    width, height = base_frames[0].size
    video_metadata = [{
        "total_num_frames": len(base_frames),
        "fps": 1.0,
        "duration": float(max(base_frame_indices)) if base_frame_indices else 0.0,
        "frames_indices": base_frame_indices,
        "width": int(width),
        "height": int(height),
    }]
    inputs = processor(
        text=[text],
        images=extra_frames or None,
        videos=[base_frames],
        video_metadata=video_metadata,
        do_sample_frames=False,
        padding=True,
        return_tensors="pt",
    )
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    visual_tokens = count_visual_tokens(processor, inputs)
    if visual_tokens > ARGS.max_visual_tokens:
        raise RuntimeError(
            f"visual token budget exceeded: {visual_tokens} > {ARGS.max_visual_tokens}"
        )
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=ARGS.max_new_tokens,
        )
    trimmed = [
        output[len(source):] for source, output in zip(inputs["input_ids"], generated)
    ]
    answer = processor.batch_decode(
        trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0].strip()
    image_grids = inputs.get("image_grid_thw")
    video_grids = inputs.get("video_grid_thw")
    temporal_patch_size = int(
        getattr(processor.video_processor, "temporal_patch_size", 2)
    )
    represented_video_frames = (
        sum(int(row[0]) * temporal_patch_size for row in video_grids.detach().cpu().tolist())
        if video_grids is not None
        else 0
    )
    if represented_video_frames != len(base_frames):
        raise RuntimeError(
            "secondary video frame change detected: "
            f"{represented_video_frames} != {len(base_frames)}"
        )
    return answer, {
        "represented_views": represented_video_frames + len(extra_frames),
        "represented_video_frames": represented_video_frames,
        "represented_extra_images": len(extra_frames),
        "visual_tokens": visual_tokens,
        "image_grid_thw": (
            image_grids.detach().cpu().tolist() if image_grids is not None else []
        ),
        "video_grid_thw": (
            video_grids.detach().cpu().tolist() if video_grids is not None else []
        ),
        "secondary_frame_sampling": False,
    }


def extract_answer(text: str, fallback: str) -> tuple[str, bool]:
    match = re.search(r"\[Answer\]\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return fallback, False
    answer = match.group(1).strip().splitlines()[0].strip()
    return (answer or fallback), bool(answer)


def main() -> None:
    if (ARGS.base_size, ARGS.crop_size, ARGS.max_visual_tokens) != (512, 896, 2592):
        raise RuntimeError("frozen protocol requires base=512, detail=896, tokens=2592")
    if (
        ARGS.output_dir.exists()
        and any(ARGS.output_dir.iterdir())
        and not ARGS.resume_existing
    ):
        raise RuntimeError("output directory must be empty")
    rows = load_jsonl(ARGS.input_jsonl)
    if len(rows) != ARGS.expected_items or any(FORBIDDEN & set(row) for row in rows):
        raise RuntimeError(
            f"each frozen shard must contain {ARGS.expected_items} answer-free items"
        )
    if (
        any(str(row.get("view_variant")) not in VARIANTS for row in rows)
        or any(len(row.get("evidence_anchors", [])) != 2 for row in rows)
    ):
        raise RuntimeError("each item must define a valid paired 10-view variant")
    present_variants = sorted({str(row["view_variant"]) for row in rows})
    gpu_snapshot = ensure_idle_gpu(ARGS.gpu_id)
    ARGS.output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "evads_qwen3_policy_crop_inference_v2",
        "gpu_id": ARGS.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "model_dir": str(ARGS.model_dir.resolve()),
        "model_config_sha256": sha256_file(ARGS.model_dir / "config.json"),
        "input_jsonl": str(ARGS.input_jsonl.resolve()),
        "input_sha256": sha256_file(ARGS.input_jsonl),
        "rows": len(rows),
        "a1_views": 8,
        "a2_views": 10,
        "base_size": ARGS.base_size,
        "detail_size": ARGS.crop_size,
        "max_visual_tokens": ARGS.max_visual_tokens,
        "max_new_tokens": ARGS.max_new_tokens,
        "expected_items": ARGS.expected_items,
        "resume_existing": ARGS.resume_existing,
        "view_variants": present_variants,
        "skip_a1": ARGS.skip_a1,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "external_knowledge_used": False,
        "secondary_frame_sampling_disabled": True,
    }
    dump_json(ARGS.output_dir / "run_config.json", config)
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir,
        min_pixels=224 * 224,
        max_pixels=ARGS.crop_size * ARGS.crop_size,
        trust_remote_code=True,
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        ARGS.model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
    )
    if str(model.config.model_type) != "qwen3_vl":
        raise RuntimeError(f"expected qwen3_vl, got {model.config.model_type}")
    model.eval()

    stats = {
        "processed": 0,
        "skipped_existing": 0,
        "errors": 0,
        "a1_parse_failures": 0,
        "a2_parse_failures": 0,
    }
    errors_path = ARGS.output_dir / "logs" / "errors.jsonl"
    for index, row in enumerate(rows, 1):
        qid = str(row["question_id"])
        variant = str(row["view_variant"])
        item_dir = ARGS.output_dir / variant / qid
        started = time.time()
        try:
            if ARGS.resume_existing and item_dir.is_dir():
                prediction_path = item_dir / "a2_prediction.json"
                trace_path = item_dir / "a2_trace.json"
                if prediction_path.is_file() and trace_path.is_file():
                    existing_trace = json.loads(trace_path.read_text(encoding="utf-8"))
                    if existing_trace.get("parse_valid"):
                        stats["skipped_existing"] += 1
                        print(json.dumps({
                            "index": index,
                            "total": len(rows),
                            "question_id": qid,
                            "skipped_existing": True,
                        }), flush=True)
                        continue
                raise RuntimeError(f"incomplete existing output for {qid}")
            base_indices = [int(value) for value in row["a0_frame_indices"]]
            if len(base_indices) != 8:
                raise RuntimeError("A0 does not contain eight frozen source frames")
            base_frames, total_frames, fps = decode_frames(
                str(row["video_path"]), base_indices, ARGS.base_size
            )
            if ARGS.skip_a1:
                a1_raw = ""
                a1_trace = {
                    "skipped": True,
                    "represented_views": 8,
                    "visual_tokens": 1024,
                    "secondary_frame_sampling": False,
                }
                a1_answer = str(row["a0_prediction"])
                a1_valid = True
            else:
                a1_raw, a1_trace = generate(
                    processor,
                    model,
                    base_frames,
                    [],
                    base_indices,
                    a1_prompt(row),
                )
                a1_answer, a1_valid = extract_answer(
                    a1_raw, str(row["a0_prediction"])
                )
                if not a1_valid:
                    stats["a1_parse_failures"] += 1

            reader = VideoReader(str(row["video_path"]), ctx=cpu(0))
            extra_frames: list[Image.Image] = []
            extra_plan: list[dict[str, Any]] = []
            for anchor in row["evidence_anchors"]:
                rank = int(anchor["source_global_rank"])
                if rank not in range(32):
                    raise RuntimeError("invalid frozen 32-frame evidence rank")
                source_index = int(anchor["source_frame_index"])
                if source_index not in range(len(reader)):
                    raise RuntimeError("frozen anchor source frame is invalid")
                source = Image.fromarray(reader[source_index].asnumpy()).convert("RGB")
                plan = {
                    "view_id": f"V{9 + int(anchor['anchor_index'])}",
                    "anchor_index": int(anchor["anchor_index"]),
                    "source_global_rank32": rank,
                    "source_frame_index": source_index,
                }
                bbox_norm = list(anchor["bbox_norm"])
                if variant == "qzoom_roi10":
                    detail_value = anchor.get("detail_image_path")
                    if detail_value:
                        detail_path = Path(str(detail_value))
                        detail_sha256 = sha256_file(detail_path)
                        if detail_sha256 != anchor.get(
                            "detail_image_sha256"
                        ):
                            raise RuntimeError(
                                "Q-Zoom ROI image hash changed"
                            )
                        with Image.open(detail_path) as image:
                            detail_size = list(image.size)
                            detail = image.convert("RGB").resize(
                                (ARGS.crop_size, ARGS.crop_size),
                                Image.Resampling.BICUBIC,
                            )
                        if detail_size != anchor.get("detail_image_size"):
                            raise RuntimeError(
                                "Q-Zoom ROI image size changed"
                            )
                        plan.update({
                            "view_type": "qzoom_roi10_896",
                            "render_mode": "official_qzoom_roi_crop",
                            "detail_image_path": str(
                                detail_path.resolve()
                            ),
                            "detail_image_sha256": detail_sha256,
                            "detail_image_size": detail_size,
                            "bbox_norm": bbox_norm,
                            "bbox_pixel_xyxy": anchor[
                                "qzoom_bbox_pixel_xyxy"
                            ],
                            "bbox_source": anchor["bbox_source"],
                        })
                    else:
                        detail, pixel_box = crop_frame(
                            source,
                            bbox_norm,
                            ARGS.crop_size,
                        )
                        plan.update({
                            "view_type": "qzoom_roi10_896",
                            "render_mode": (
                                "no_roi_fallback_AVFunnel_mid"
                            ),
                            "bbox_norm": bbox_norm,
                            "pixel_box": pixel_box,
                            "bbox_source": anchor["bbox_source"],
                        })
                elif variant == "hide_layout10":
                    detail_value = anchor.get("detail_image_path")
                    if detail_value:
                        detail_path = Path(str(detail_value))
                        detail_sha256 = sha256_file(detail_path)
                        if detail_sha256 != anchor.get(
                            "detail_image_sha256"
                        ):
                            raise RuntimeError(
                                "HiDe compact image hash changed"
                            )
                        with Image.open(detail_path) as image:
                            detail_size = list(image.size)
                            detail = image.convert("RGB").resize(
                                (ARGS.crop_size, ARGS.crop_size),
                                Image.Resampling.BICUBIC,
                            )
                        if detail_size != anchor.get("detail_image_size"):
                            raise RuntimeError(
                                "HiDe compact image size changed"
                            )
                        plan.update({
                            "view_type": "hide_layout10_896",
                            "render_mode": (
                                "layout_preserving_compact"
                            ),
                            "detail_image_path": str(
                                detail_path.resolve()
                            ),
                            "detail_image_sha256": detail_sha256,
                            "detail_image_size": detail_size,
                            "selected_regions_norm": anchor[
                                "hide_selected_regions_norm"
                            ],
                            "selected_region_count": int(
                                anchor[
                                    "hide_selected_region_count"
                                ]
                            ),
                            "bbox_source": anchor["bbox_source"],
                        })
                    else:
                        detail, pixel_box = crop_frame(
                            source,
                            bbox_norm,
                            ARGS.crop_size,
                        )
                        plan.update({
                            "view_type": "hide_layout10_896",
                            "render_mode": (
                                "no_region_fallback_AVFunnel_mid"
                            ),
                            "bbox_norm": bbox_norm,
                            "pixel_box": pixel_box,
                            "bbox_source": anchor["bbox_source"],
                        })
                elif variant in {
                    "awares_first10",
                    "adaptvision_bbox10",
                    "deepeyes_firstzoom10",
                    "zoomeye_union10",
                    "vlmr3_lastbbox10",
                }:
                    detail, pixel_box = crop_frame(
                        source,
                        bbox_norm,
                        ARGS.crop_size,
                    )
                    plan.update({
                        "view_type": f"{variant}_896",
                        "bbox_norm": bbox_norm,
                        "pixel_box": pixel_box,
                        "bbox_source": anchor["bbox_source"],
                    })
                elif variant == "anchor_global10":
                    detail = source.resize(
                        (ARGS.crop_size, ARGS.crop_size),
                        Image.Resampling.BICUBIC,
                    )
                    plan["view_type"] = "same_anchor_full_896"
                else:
                    raise RuntimeError(f"unsupported view variant: {variant}")
                extra_frames.append(detail)
                extra_plan.append(plan)
            if len(extra_frames) != 2:
                raise RuntimeError("A2 must add exactly two evidence views")
            prompt = a2_prompt(row)
            a2_raw, a2_trace = generate(
                processor,
                model,
                base_frames,
                extra_frames,
                base_indices,
                prompt,
            )
            if (
                int(a2_trace["represented_views"]) != 10
                or int(a2_trace["visual_tokens"]) != 2592
            ):
                raise RuntimeError(
                    "paired protocol requires exactly 10 views and 2592 visual tokens"
                )
            a2_answer, a2_valid = extract_answer(
                a2_raw, str(row["a0_prediction"])
            )
            if not a2_valid:
                stats["a2_parse_failures"] += 1

            item_dir.mkdir(parents=True, exist_ok=False)
            dump_json(item_dir / "a1_prediction.json", {
                "question_id": qid,
                "method": "Qwen3_GenericReconsider8_A1",
                "prediction": a1_answer,
            })
            dump_json(item_dir / "a1_trace.json", {
                "question_id": qid,
                "raw_output": a1_raw,
                "parse_valid": a1_valid,
                "fallback_to_a0": not a1_valid,
                "base_source_frame_indices": base_indices,
                "processor_trace": a1_trace,
            })
            dump_json(item_dir / "a2_prediction.json", {
                "question_id": qid,
                "method": f"Qwen3_PolicyCrop_{variant}_A2",
                "prediction": a2_answer,
            })
            dump_json(item_dir / "a2_trace.json", {
                "question_id": qid,
                "raw_output": a2_raw,
                "parse_valid": a2_valid,
                "fallback_to_a0": not a2_valid,
                "answer_changed_from_a0": (
                    " ".join(a2_answer.casefold().split())
                    != " ".join(str(row["a0_prediction"]).casefold().split())
                ),
                "base_source_frame_indices": base_indices,
                "extra_view_plan": extra_plan,
                "view_variant": variant,
                "prompt_sha256": hashlib.sha256(
                    prompt.encode("utf-8")
                ).hexdigest(),
                "video_total_frames": total_frames,
                "video_fps": fps,
                "processor_trace": a2_trace,
                "latency_seconds": time.time() - started,
            })
            stats["processed"] += 1
            print(json.dumps({"index": index, "total": len(rows), "question_id": qid}), flush=True)
        except Exception as error:
            append_jsonl(errors_path, {
                "question_id": qid,
                "error": repr(error),
                "traceback": traceback.format_exc(),
            })
            stats["errors"] += 1
        finally:
            torch.cuda.empty_cache()
            gc.collect()
    config["stats"] = stats
    config["complete"] = (
        stats["processed"] + stats["skipped_existing"] == len(rows)
        and stats["errors"] == 0
    )
    config["gpu_peak_memory_mb"] = torch.cuda.max_memory_allocated() / 1024 / 1024
    dump_json(ARGS.output_dir / "run_summary.json", config)
    if not config["complete"]:
        raise RuntimeError(f"inference incomplete: {stats}")
    print(json.dumps(config, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
