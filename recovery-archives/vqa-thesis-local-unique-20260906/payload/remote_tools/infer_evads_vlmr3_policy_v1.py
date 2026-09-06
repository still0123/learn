#!/usr/bin/env python3
"""Run answer-free VLM-R3 interleaved crop decisions on E-VAds anchors."""

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


SOURCE_REPOSITORY = "https://github.com/0001Henry/VLM-R3"
SOURCE_COMMIT = "5e8fb0b581a310b8e1dfc9e5c4746ab503e2e6a3"
MODEL_REPOSITORY = "LittleHenry/VLM-R3-7b-rl-v1"
MODEL_REVISION = "bc34d281c27ee245676e2a869abd0699ebd61ef6"
POLICY_PROMPT = """\nYou need to first think about the reasoning process in your mind, and then provide the answer. When thinking, you should call the "crop" tool (format: {"bbox_2d": [x1, y1, x2, y2]}) to focus on the key areas in the image. The reasoning process and the answer are included in the <think> </think> and <answer> </answer> tags respectively."""
JSON_PATTERN = re.compile(r"\{.*?\}", re.DOTALL)
ANSWER_PATTERN = re.compile(r"<answer>.*?</answer>", re.DOTALL)
MIN_PIXELS = 32 * 28 * 28
MAX_PIXELS = 8192 * 28 * 28
CROP_MIN_PIXELS = 32 * 28 * 28
CROP_MAX_PIXELS = 4096 * 28 * 28
MAX_ITERATIONS = 8
MAX_NEW_TOKENS = 2048
STOP_STRINGS = ["]}", "]\n}", "] }", "</answer>"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-items", type=int, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_idle_gpu(gpu_id: str) -> list[str]:
    if gpu_id not in {"0", "1", "2", "3", "4", "5"}:
        raise RuntimeError("GPU id is outside the reserved host")
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


def has_answer(text: str) -> bool:
    return bool(ANSWER_PATTERN.search(text))


def parse_bbox(
    text: str,
    processed_size: tuple[int, int],
    original_size: tuple[int, int],
) -> tuple[dict[str, Any] | None, bool, bool]:
    bbox_called = "bbox_2d" in text
    candidates = JSON_PATTERN.findall(text)
    if bbox_called and not candidates:
        repaired = text + (
            "]}" if not text.rstrip().endswith("]}") else ""
        )
        candidates = JSON_PATTERN.findall(repaired)
    payload = None
    for candidate in reversed(candidates):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "bbox_2d" in value:
            payload = value
            break
    if payload is None:
        return None, bbox_called, not bbox_called
    bbox = payload["bbox_2d"]
    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            for value in bbox
        )
    ):
        return None, True, False
    processed_width, processed_height = processed_size
    original_width, original_height = original_size
    x0, y0, x1, y1 = map(float, bbox)
    clamped = [
        max(0.0, min(x0, float(processed_width))),
        max(0.0, min(y0, float(processed_height))),
        max(0.0, min(x1, float(processed_width))),
        max(0.0, min(y1, float(processed_height))),
    ]
    if clamped[2] <= clamped[0] or clamped[3] <= clamped[1]:
        return None, True, False
    original_bbox = [
        clamped[0] * original_width / processed_width,
        clamped[1] * original_height / processed_height,
        clamped[2] * original_width / processed_width,
        clamped[3] * original_height / processed_height,
    ]
    normalized = [
        original_bbox[0] / original_width,
        original_bbox[1] / original_height,
        original_bbox[2] / original_width,
        original_bbox[3] / original_height,
    ]
    return {
        "bbox_pixel_processed": clamped,
        "bbox_pixel_original": original_bbox,
        "bbox_norm": normalized,
        "bbox_area_ratio": (
            (normalized[2] - normalized[0])
            * (normalized[3] - normalized[1])
        ),
    }, True, True


def self_check() -> None:
    call, called, valid = parse_bbox(
        '<think>x</think>{"bbox_2d":[10,20,110,220]}',
        (200, 400),
        (400, 800),
    )
    assert called and valid
    assert call == {
        "bbox_pixel_processed": [10.0, 20.0, 110.0, 220.0],
        "bbox_pixel_original": [20.0, 40.0, 220.0, 440.0],
        "bbox_norm": [0.05, 0.05, 0.55, 0.55],
        "bbox_area_ratio": 0.25,
    }
    assert parse_bbox("<answer>blue</answer>", (200, 400), (400, 800)) == (
        None,
        False,
        True,
    )
    assert has_answer("<answer>blue</answer>")


def crop_for_context(
    original: Any,
    call: dict[str, Any],
    smart_resize: Any,
) -> Any:
    from PIL import Image

    left, top, right, bottom = call["bbox_pixel_original"]
    crop = original.crop((left, top, right, bottom))
    width, height = crop.size
    ratio = (width * height) / (original.width * original.height)
    if ratio < 0.125:
        scale = 2.0
    elif ratio >= 0.5:
        scale = 1.0
    else:
        scale = 2.0 - (ratio - 0.125) / 0.375
    resized_height, resized_width = smart_resize(
        int(scale * height),
        int(scale * width),
        factor=28,
        min_pixels=CROP_MIN_PIXELS,
        max_pixels=CROP_MAX_PIXELS,
    )
    return crop.resize(
        (resized_width, resized_height),
        Image.Resampling.LANCZOS,
    )


def main() -> None:
    self_check()
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError("output directory already exists")
    rows = read_jsonl(args.requests)
    required = {
        "question_id",
        "video_id",
        "anchor_index",
        "source_frame_index",
        "image_path",
        "question",
    }
    if (
        len(rows) != args.expected_items
        or any(not required.issubset(row) for row in rows)
        or any("answer" in row or "reference_answer" in row for row in rows)
    ):
        raise RuntimeError("requests are not answer-free policy inputs")
    keys = {
        (str(row["question_id"]), int(row["anchor_index"])) for row in rows
    }
    if len(keys) != len(rows):
        raise RuntimeError("request keys are not unique")

    gpu_snapshot = ensure_idle_gpu(args.gpu_id)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch
    from PIL import Image
    import transformers
    from qwen_vl_utils import smart_resize
    from transformers import (
        AutoProcessor,
        Qwen2_5_VLForConditionalGeneration,
    )

    config = {
        "schema_version": "evads_vlmr3_policy_inference_v1",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "model_dir": str(args.model_dir.resolve()),
        "model_config_sha256": sha256(args.model_dir / "config.json"),
        "model_index_sha256": sha256(
            args.model_dir / "model.safetensors.index.json"
        ),
        "requests_sha256": sha256(args.requests),
        "expected_items": args.expected_items,
        "gpu_id": args.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "policy_prompt_sha256": hashlib.sha256(
            POLICY_PROMPT.encode("utf-8")
        ).hexdigest(),
        "min_pixels": MIN_PIXELS,
        "max_pixels": MAX_PIXELS,
        "crop_min_pixels": CROP_MIN_PIXELS,
        "crop_max_pixels": CROP_MAX_PIXELS,
        "max_iterations": MAX_ITERATIONS,
        "max_new_tokens_per_iteration": MAX_NEW_TOKENS,
        "temperature": 0,
        "stop_strings": STOP_STRINGS,
        "selected_bbox_rule": "last executed bbox in original coordinates",
        "reference_answers_used": False,
        "judge_scores_used": False,
        "automatic_retry": False,
    }
    dump(args.output_dir / "run_config.json", config)
    processor = AutoProcessor.from_pretrained(
        args.model_dir,
        min_pixels=MIN_PIXELS,
        max_pixels=MAX_PIXELS,
        local_files_only=True,
        use_fast=False,
    )
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
    ).eval()

    stats = {
        "processed": 0,
        "errors": 0,
        "bbox_responses": 0,
        "valid_bbox_calls": 0,
        "triggered_anchors": 0,
        "parse_failures": 0,
        "max_iterations_reached": 0,
        "answer_responses": 0,
    }
    result_path = args.output_dir / "policy_results.jsonl"
    error_path = args.output_dir / "errors.jsonl"
    for index, row in enumerate(rows, 1):
        key = (str(row["question_id"]), int(row["anchor_index"]))
        started = time.time()
        try:
            original = Image.open(str(row["image_path"])).convert("RGB")
            resized_height, resized_width = smart_resize(
                original.height,
                original.width,
                factor=28,
                min_pixels=MIN_PIXELS,
                max_pixels=MAX_PIXELS,
            )
            processed_size = (resized_width, resized_height)
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": original},
                    {
                        "type": "text",
                        "text": str(row["question"]) + POLICY_PROMPT,
                    },
                ],
            }]
            images = [original]
            trace = []
            bbox_calls = []
            parse_valid = True
            answer_present = False
            for turn_index in range(MAX_ITERATIONS):
                text = processor.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=len(messages) == 1,
                )
                if text.endswith("<|im_end|>\n"):
                    text = text[: -len("<|im_end|>\n")] + "\n"
                inputs = processor(
                    text=[text],
                    images=images,
                    return_tensors="pt",
                    padding=True,
                    padding_side="left",
                    add_special_tokens=False,
                ).to(model.device)
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        do_sample=False,
                        max_new_tokens=MAX_NEW_TOKENS,
                        stop_strings=STOP_STRINGS,
                        tokenizer=processor.tokenizer,
                    )
                trimmed = [
                    output[len(source) :]
                    for source, output in zip(inputs.input_ids, generated)
                ]
                response = processor.batch_decode(
                    trimmed,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )[0]
                state_response = response
                if "<answer>" in state_response and "</answer>" not in state_response:
                    state_response += "</answer>\n"
                call, bbox_called, parsed = parse_bbox(
                    state_response,
                    processed_size,
                    original.size,
                )
                if (
                    call is not None
                    and not JSON_PATTERN.findall(state_response)
                ):
                    state_response += "]}\n"
                answer_present = has_answer(state_response)
                parse_valid = parse_valid and parsed
                trace.append({
                    "turn_index": turn_index,
                    "response": state_response,
                    "response_sha256": hashlib.sha256(
                        state_response.encode("utf-8")
                    ).hexdigest(),
                    "answer_present": answer_present,
                    "bbox_called": bbox_called,
                    "valid_call": call,
                })
                stats["bbox_responses"] += int(bbox_called)
                stats["answer_responses"] += int(answer_present)
                if answer_present:
                    break
                if call is None:
                    if bbox_called:
                        stats["parse_failures"] += 1
                    break
                bbox_calls.append(call)
                stats["valid_bbox_calls"] += 1
                crop = crop_for_context(original, call, smart_resize)
                if len(messages) == 1:
                    messages.append({
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": state_response},
                            {"type": "image", "image": crop},
                        ],
                    })
                else:
                    messages[-1]["content"].extend([
                        {"type": "text", "text": state_response},
                        {"type": "image", "image": crop},
                    ])
                images.append(crop)
            else:
                stats["max_iterations_reached"] += 1

            selected = bbox_calls[-1] if bbox_calls else None
            append_jsonl(result_path, {
                "question_id": key[0],
                "video_id": str(row["video_id"]),
                "fold": int(row.get("fold", -1)),
                "anchor_index": key[1],
                "source_frame_index": int(row["source_frame_index"]),
                "image_sha256": sha256(Path(row["image_path"])),
                "question_sha256": hashlib.sha256(
                    str(row["question"]).encode("utf-8")
                ).hexdigest(),
                "original_image_size": list(original.size),
                "processed_image_size": list(processed_size),
                "trace": trace,
                "bbox_call_count": len(bbox_calls),
                "bbox_calls": bbox_calls,
                "bbox_norm": selected["bbox_norm"] if selected else None,
                "bbox_pixel_original": (
                    selected["bbox_pixel_original"] if selected else None
                ),
                "bbox_area_ratio": (
                    selected["bbox_area_ratio"] if selected else None
                ),
                "selected_bbox_rule": (
                    "last_executed_original_coordinate_bbox"
                    if selected
                    else None
                ),
                "parse_valid": parse_valid,
                "answer_present": answer_present,
                "latency_seconds": time.time() - started,
                "reference_answer_used": False,
            })
            stats["processed"] += 1
            stats["triggered_anchors"] += int(selected is not None)
            print(json.dumps({
                "index": index,
                "total": len(rows),
                "question_id": key[0],
                "bbox_call_count": len(bbox_calls),
                "bbox_norm": selected["bbox_norm"] if selected else None,
                "answer_present": answer_present,
            }), flush=True)
        except Exception as error:
            append_jsonl(error_path, {
                "question_id": key[0],
                "anchor_index": key[1],
                "error": repr(error),
                "traceback": traceback.format_exc(),
            })
            stats["errors"] += 1
        finally:
            gc.collect()
            torch.cuda.empty_cache()

    final_rows = read_jsonl(result_path) if result_path.exists() else []
    config["stats"] = stats
    config["result_count"] = len(final_rows)
    config["complete"] = (
        len(final_rows) == args.expected_items
        and stats["errors"] == 0
        and len({
            (str(row["question_id"]), int(row["anchor_index"]))
            for row in final_rows
        }) == args.expected_items
    )
    config["results_sha256"] = (
        sha256(result_path) if result_path.exists() else None
    )
    config["gpu_peak_memory_mb"] = (
        torch.cuda.max_memory_allocated() / 1024 / 1024
    )
    dump(args.output_dir / "run_summary.json", config)
    if not config["complete"]:
        raise RuntimeError(f"VLM-R3 policy inference incomplete: {stats}")


if __name__ == "__main__":
    main()
