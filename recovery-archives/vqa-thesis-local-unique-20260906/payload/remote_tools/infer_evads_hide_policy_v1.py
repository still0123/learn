#!/usr/bin/env python3
"""Run answer-free HiDe compact-region decisions on E-VAds anchors."""

from __future__ import annotations

import argparse
import ast
import base64
from io import BytesIO
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


SOURCE_REPOSITORY = "https://github.com/Tennine2077/HiDe"
SOURCE_COMMIT = "c7d211641ecb9e2824fdc50f6c574e8cb5813f08"
SIGMA = 3
ATTENTION_THRESHOLD = 0.7
MIN_PIXELS = 256 * 32 * 32
MAX_PIXELS = 16384 * 32 * 32
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
    rows = [line.strip() for line in snapshot.stdout.splitlines() if line.strip()]
    selected = [row for row in rows if row.split(",", 1)[0].strip() == gpu_id]
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
    if len(selected) != 1 or active:
        raise RuntimeError(f"GPU{gpu_id} is not idle: {active}")
    return selected


def extract_official_entity_prompt(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for function in tree.body:
        if isinstance(function, ast.FunctionDef) and function.name == "once_infer":
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name)
                        and target.id == "prompt_ques"
                        for target in node.targets
                    )
                ):
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str) and "{input_text}" in value:
                        return value
    raise RuntimeError("official HiDe entity prompt was not found")


def parse_entities(text: str) -> tuple[str, bool]:
    match = re.search(
        r"<FINAL_OUTPUT>\s*(.*?)\s*</FINAL_OUTPUT>",
        text,
        flags=re.DOTALL,
    )
    if match:
        return match.group(1).strip(), True
    return "", False


def validate_bboxes(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        raise RuntimeError("HiDe bounding boxes are not a list")
    result = []
    for bbox in value:
        normalized = [float(item) for item in bbox]
        if (
            len(normalized) != 4
            or not all(0.0 <= item <= 1.0 for item in normalized)
            or normalized[2] <= normalized[0]
            or normalized[3] <= normalized[1]
        ):
            raise RuntimeError(f"invalid HiDe bbox: {normalized}")
        result.append(normalized)
    return result


def decode_layout(value: str) -> Any:
    from PIL import Image

    payload = value.split(",", 1)[1] if "," in value else value
    return Image.open(BytesIO(base64.b64decode(payload))).convert("RGBA")


def self_check(source_dir: Path) -> None:
    prompt = extract_official_entity_prompt(source_dir / "official_inference.py")
    assert "{input_text}" in prompt
    assert parse_entities("<FINAL_OUTPUT>logo, bottle</FINAL_OUTPUT>") == (
        "logo, bottle",
        True,
    )
    assert parse_entities("<FINAL_OUTPUT></FINAL_OUTPUT>") == ("", True)
    assert validate_bboxes([[0, 0.1, 0.8, 1]]) == [[0.0, 0.1, 0.8, 1.0]]


def main() -> None:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    self_check(source_dir)
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
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    sys.path.insert(0, str(source_dir))

    import torch
    import transformers
    from PIL import Image
    from transformers import AutoProcessor
    from Get_box import (
        from_img_and_att_get_cropbox,
        get_inputs,
        messages2att,
        messages2out,
    )
    from modeling_qwen3_vl_re_infer import (
        Qwen3VLForConditionalGeneration,
    )

    entity_prompt = extract_official_entity_prompt(
        source_dir / "official_inference.py"
    )
    config = {
        "schema_version": "evads_hide_policy_inference_v1",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
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
        "entity_prompt_sha256": hashlib.sha256(
            entity_prompt.encode("utf-8")
        ).hexdigest(),
        "gaussian_sigma": SIGMA,
        "attention_threshold": ATTENTION_THRESHOLD,
        "min_pixels": MIN_PIXELS,
        "max_pixels": MAX_PIXELS,
        "attention_implementation": "eager",
        "connected_components": "scipy_ndimage_8_connected",
        "diagnostic_image_side_effects": False,
        "reference_answers_used": False,
        "judge_scores_used": False,
        "automatic_retry": False,
    }
    dump(args.output_dir / "run_config.json", config)
    processor = AutoProcessor.from_pretrained(
        args.model_dir,
        use_fast=True,
        min_pixels=MIN_PIXELS,
        max_pixels=MAX_PIXELS,
        local_files_only=True,
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        device_map={"": 0},
        local_files_only=True,
    ).eval()

    stats = {
        "processed": 0,
        "errors": 0,
        "entity_parse_failures": 0,
        "layout_anchors": 0,
        "no_region_anchors": 0,
        "selected_regions": 0,
    }
    result_path = args.output_dir / "policy_results.jsonl"
    error_path = args.output_dir / "errors.jsonl"
    layout_dir = args.output_dir / "compact_images"
    for index, row in enumerate(rows, 1):
        key = (str(row["question_id"]), int(row["anchor_index"]))
        started = time.time()
        try:
            image_path = Path(str(row["image_path"])).resolve()
            if not image_path.is_file():
                raise RuntimeError(f"missing anchor image: {image_path}")
            entity_messages = [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": entity_prompt.format(
                        input_text=str(row["question"])
                    ),
                }],
            }]
            _, _, _, entity_inputs, _ = get_inputs(
                entity_messages,
                processor,
                model,
            )
            entity_outputs, _ = messages2out(
                model,
                processor,
                entity_inputs,
            )
            entity_raw = str(entity_outputs[0])
            entities, entity_valid = parse_entities(entity_raw)
            search_target = entities or str(row["question"])
            search_messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {
                        "type": "text",
                        "text": "Search the following entities in the images: "
                        + search_target,
                    },
                ],
            }]
            _, _, _, search_inputs, _ = get_inputs(
                search_messages,
                processor,
                model,
            )
            attention, token_map, image_start, image_end = messages2att(
                model,
                processor,
                search_inputs,
            )
            result = from_img_and_att_get_cropbox(
                search_inputs,
                attention,
                token_map,
                [str(image_path)],
                image_start,
                image_end,
                [SIGMA],
                [ATTENTION_THRESHOLD],
            )[str(SIGMA)][str(ATTENTION_THRESHOLD)]
            _, _, _, layouts, bbox_by_image = result
            if len(layouts) > 1:
                raise RuntimeError("one anchor produced multiple compact images")
            bboxes = validate_bboxes(bbox_by_image.get(0, []))
            layout_path = None
            layout_size = None
            if layouts:
                if not bboxes:
                    raise RuntimeError("compact image has no source regions")
                layout = decode_layout(str(layouts[0]))
                layout_dir.mkdir(parents=True, exist_ok=True)
                layout_path = (
                    layout_dir / f"{key[0]}_anchor{key[1]}.png"
                )
                layout.save(layout_path, format="PNG")
                layout_size = list(layout.size)
                stats["layout_anchors"] += 1
                stats["selected_regions"] += len(bboxes)
            else:
                if bboxes:
                    raise RuntimeError("source regions have no compact image")
                stats["no_region_anchors"] += 1
            stats["entity_parse_failures"] += int(not entity_valid)
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
                "entity_response_sha256": hashlib.sha256(
                    entity_raw.encode("utf-8")
                ).hexdigest(),
                "entity_response": entity_raw,
                "entity_parse_valid": entity_valid,
                "search_target": search_target,
                "search_target_sha256": hashlib.sha256(
                    search_target.encode("utf-8")
                ).hexdigest(),
                "selected_regions_norm": bboxes,
                "selected_region_count": len(bboxes),
                "compact_image_path": (
                    str(layout_path.resolve()) if layout_path else None
                ),
                "compact_image_sha256": (
                    sha256(layout_path) if layout_path else None
                ),
                "compact_image_size": layout_size,
                "parse_valid": True,
                "latency_seconds": time.time() - started,
                "reference_answer_used": False,
            })
            stats["processed"] += 1
            print(json.dumps({
                "index": index,
                "total": len(rows),
                "question_id": key[0],
                "entity_parse_valid": entity_valid,
                "selected_region_count": len(bboxes),
                "compact_image_size": layout_size,
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
        raise RuntimeError(f"HiDe policy inference incomplete: {stats}")


if __name__ == "__main__":
    main()
