#!/usr/bin/env python3
"""Run answer-free Q-Zoom ROI decisions on frozen E-VAds anchors."""

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


SOURCE_REPOSITORY = "https://github.com/YuHengsss/Q-Zoom"
SOURCE_COMMIT = "f062af77ac598c2ca48ef90a58c9973c9b227421"
MODEL_REPOSITORY = "YuhengSSS/Q-Zoom-Qwen3VL-4B"
MODEL_REVISION = "75ad1edb070c04d2a4e40a93235c4a1d904eec16"
ROI_CONFIDENCE = 0.10
MIN_PIXELS = 512 * 32 * 32
MAX_PIXELS = 4096 * 32 * 32
POLICY_SUFFIX = "\nAnswer the question using a single word or phrase."
FORBIDDEN = {
    "answer",
    "reference_answer",
    "ground_truth",
    "label",
    "reward",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
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
    rows = [
        line.strip()
        for line in snapshot.stdout.splitlines()
        if line.strip()
    ]
    selected = [
        row for row in rows if row.split(",", 1)[0].strip() == gpu_id
    ]
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
    active = [
        line.strip()
        for line in processes.stdout.splitlines()
        if line.strip()
    ]
    if len(selected) != 1 or active:
        raise RuntimeError(f"GPU{gpu_id} is not idle: {active}")
    return selected


def normalize_bbox(
    bbox: list[int],
    width: int,
    height: int,
) -> list[float]:
    if (
        len(bbox) != 4
        or width <= 0
        or height <= 0
        or bbox[0] < 0
        or bbox[1] < 0
        or bbox[2] > width
        or bbox[3] > height
        or bbox[2] <= bbox[0]
        or bbox[3] <= bbox[1]
    ):
        raise RuntimeError(f"invalid pixel bbox: {bbox}")
    return [
        bbox[0] / width,
        bbox[1] / height,
        bbox[2] / width,
        bbox[3] / height,
    ]


def self_check() -> None:
    assert normalize_bbox([10, 20, 50, 80], 100, 100) == [
        0.1,
        0.2,
        0.5,
        0.8,
    ]
    try:
        normalize_bbox([50, 20, 10, 80], 100, 100)
    except RuntimeError:
        return
    raise AssertionError("invalid bbox was accepted")


def main() -> None:
    self_check()
    args = parse_args()
    source_dir = args.source_dir.resolve()
    model_dir = args.model_dir.resolve()
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
        or any(FORBIDDEN & set(row) for row in rows)
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
    os.environ.setdefault(
        "PYTORCH_CUDA_ALLOC_CONF",
        "expandable_segments:True",
    )
    sys.path.insert(0, str(source_dir))

    import torch
    import transformers
    from PIL import Image
    from transformers import AutoProcessor
    from qwen_src.ana_utils import get_bbox4src
    from qwen_src.qwen3_vl.modeling_qwen3_vl import (
        Qwen3VLForConditionalGeneration,
    )

    source_model = (
        source_dir / "qwen_src" / "qwen3_vl" / "modeling_qwen3_vl.py"
    )
    source_roi = source_dir / "qwen_src" / "mm_utils.py"
    source_analysis = source_dir / "qwen_src" / "ana_utils.py"
    config = {
        "schema_version": "evads_qzoom_roi_policy_inference_v1",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "source_model_sha256": sha256(source_model),
        "source_roi_utils_sha256": sha256(source_roi),
        "source_analysis_utils_sha256": sha256(source_analysis),
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "model_dir": str(model_dir),
        "model_config_sha256": sha256(model_dir / "config.json"),
        "model_index_sha256": sha256(
            model_dir / "model.safetensors.index.json"
        ),
        "requests_sha256": sha256(args.requests),
        "expected_items": args.expected_items,
        "gpu_id": args.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "roi_confidence": ROI_CONFIDENCE,
        "min_pixels": MIN_PIXELS,
        "max_pixels": MAX_PIXELS,
        "policy_prompt_suffix": POLICY_SUFFIX,
        "attention_implementation": "sdpa",
        "dynamic_gate_ignored": True,
        "roi_forced": True,
        "answer_generation_executed": False,
        "reference_answers_used": False,
        "judge_scores_used": False,
        "automatic_retry": False,
    }
    dump(args.output_dir / "run_config.json", config)

    processor = AutoProcessor.from_pretrained(
        model_dir,
        use_fast=True,
        min_pixels=MIN_PIXELS,
        max_pixels=MAX_PIXELS,
        local_files_only=True,
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
    ).eval()
    language_model = model.model.language_model
    language_model.enable_twig = True
    language_model.roi_enable2stage = True
    language_model.enable_high_res = False
    language_model.roi_conf_thresh = ROI_CONFIDENCE
    language_model.is_debug = False

    stats = {
        "processed": 0,
        "errors": 0,
        "roi_anchors": 0,
        "no_roi_anchors": 0,
    }
    result_path = args.output_dir / "policy_results.jsonl"
    error_path = args.output_dir / "errors.jsonl"
    crop_dir = args.output_dir / "roi_images"
    for index, row in enumerate(rows, 1):
        key = (str(row["question_id"]), int(row["anchor_index"]))
        started = time.time()
        try:
            image_path = Path(str(row["image_path"])).resolve()
            if not image_path.is_file():
                raise RuntimeError(f"missing anchor image: {image_path}")
            image = Image.open(image_path).convert("RGB")
            prompt = str(row["question"]).strip() + POLICY_SUFFIX
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                },
            ]
            text = processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = processor(
                text=[text],
                images=[image],
                padding=True,
                return_tensors="pt",
            ).to(model.device)
            language_model.roi_surrounding_bbox = None
            language_model.bbox_img = None
            language_model.high_res_pred = None
            with torch.inference_mode():
                model(
                    **inputs,
                    src_images=[image],
                    processor=processor,
                    use_cache=False,
                    logits_to_keep=1,
                )

            boxes = language_model.roi_surrounding_bbox
            official_crop = language_model.bbox_img
            bbox_feature = None
            bbox_pixel = None
            bbox_norm = None
            crop_path = None
            if boxes and boxes[0] is not None:
                if len(boxes) != 1 or official_crop is None:
                    raise RuntimeError("Q-Zoom ROI artifacts are incomplete")
                feature_box = boxes[0].detach().cpu()
                if feature_box.shape != (1, 4):
                    raise RuntimeError(
                        f"unexpected Q-Zoom feature bbox: "
                        f"{feature_box.shape}"
                    )
                bbox_feature = [
                    int(value) for value in feature_box[0].tolist()
                ]
                grid = inputs["image_grid_thw"][0].detach().cpu()
                feature_height = int(grid[1]) // 2
                feature_width = int(grid[2]) // 2
                pixel_box = get_bbox4src(
                    feature_box,
                    image,
                    feat_size=(feature_height, feature_width),
                    img_size=(
                        feature_height * 32,
                        feature_width * 32,
                    ),
                )[0]
                bbox_pixel = [int(value) for value in pixel_box.tolist()]
                bbox_norm = normalize_bbox(
                    bbox_pixel,
                    image.width,
                    image.height,
                )
                exact_crop = image.crop(tuple(bbox_pixel))
                if (
                    exact_crop.size != official_crop.size
                    or exact_crop.mode != official_crop.mode
                    or exact_crop.tobytes() != official_crop.tobytes()
                ):
                    raise RuntimeError(
                        "reconstructed ROI differs from official Q-Zoom crop"
                    )
                crop_dir.mkdir(parents=True, exist_ok=True)
                crop_path = crop_dir / f"{key[0]}_anchor{key[1]}.png"
                official_crop.save(crop_path, format="PNG")
                stats["roi_anchors"] += 1
            else:
                if official_crop is not None:
                    raise RuntimeError("Q-Zoom crop has no feature bbox")
                stats["no_roi_anchors"] += 1

            append_jsonl(result_path, {
                "question_id": key[0],
                "video_id": str(row["video_id"]),
                "fold": int(row.get("fold", -1)),
                "anchor_index": key[1],
                "source_frame_index": int(row["source_frame_index"]),
                "image_sha256": sha256(image_path),
                "question_sha256": hashlib.sha256(
                    str(row["question"]).encode("utf-8")
                ).hexdigest(),
                "policy_prompt_sha256": hashlib.sha256(
                    prompt.encode("utf-8")
                ).hexdigest(),
                "image_grid_thw": inputs[
                    "image_grid_thw"
                ].detach().cpu().tolist(),
                "bbox_feature_xyxy": bbox_feature,
                "bbox_pixel_xyxy": bbox_pixel,
                "bbox_norm": bbox_norm,
                "roi_image_path": (
                    str(crop_path.resolve()) if crop_path else None
                ),
                "roi_image_sha256": (
                    sha256(crop_path) if crop_path else None
                ),
                "roi_image_size": (
                    list(official_crop.size) if crop_path else None
                ),
                "parse_valid": True,
                "latency_seconds": time.time() - started,
                "answer_generation_executed": False,
                "reference_answer_used": False,
            })
            stats["processed"] += 1
            print(json.dumps({
                "index": index,
                "total": len(rows),
                "question_id": key[0],
                "bbox_norm": bbox_norm,
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
        raise RuntimeError(f"Q-Zoom policy inference incomplete: {stats}")


if __name__ == "__main__":
    main()
