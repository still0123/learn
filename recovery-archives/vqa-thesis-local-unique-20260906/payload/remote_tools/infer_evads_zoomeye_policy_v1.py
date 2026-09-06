#!/usr/bin/env python3
"""Run answer-free ZoomEye tree search on frozen E-VAds anchor images."""

from __future__ import annotations

import argparse
from collections import Counter
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


SOURCE_REPOSITORY = "https://github.com/om-ai-lab/ZoomEye"
SOURCE_COMMIT = "6762d79f3153552d03b49a2d5c07caaa44fac375"
MODEL_REPOSITORY = "Qwen/Qwen2.5-VL-7B-Instruct"
DECOMPOSED_QUESTION_TEMPLATE = "What is the appearance of the {}?"
MAX_TARGETS = 3
SPLIT_NUM = 4
PATCH_SCALE = 1.2
BIAS_VALUE = 0.6
ANSWERING_CONFIDENCE_LOWER = 0.0
ANSWERING_CONFIDENCE_UPPER = 0.95
VISUAL_CUE_THRESHOLD = 0.6
THRESHOLD_DECREASE = [0.05, 0.1, 0.2]
ADSQA_CUE_PROMPT = """Select visual evidence for the advertisement-video question below. Do not answer the question.
Return a JSON array containing 1 to 3 short strings. Each string must name a concrete visible entity, person, product, action, on-screen text region, or scene region whose appearance should be inspected. Avoid abstract concepts and explanations.
Question: {question}
JSON array:"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--ic-examples", type=Path, required=True)
    parser.add_argument(
        "--cue-mode",
        choices=("official_ic", "adsqa_json"),
        required=True,
    )
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


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


def normalize_xyxy(
    bbox: list[float],
    width: int,
    height: int,
) -> list[float]:
    left, top, right, bottom = bbox
    normalized = [
        max(0.0, min(1.0, left / width)),
        max(0.0, min(1.0, top / height)),
        max(0.0, min(1.0, right / width)),
        max(0.0, min(1.0, bottom / height)),
    ]
    if normalized[2] <= normalized[0] or normalized[3] <= normalized[1]:
        raise RuntimeError(f"empty union bbox: {bbox}")
    return normalized


def self_check() -> None:
    assert normalize_xyxy([0, 20, 100, 220], 200, 400) == [
        0.0,
        0.05,
        0.5,
        0.55,
    ]
    assert parse_json_cues('["product", "on-screen text"]') == (
        ["product", "on-screen text"],
        True,
    )
    assert parse_json_cues("not json") == ([], False)


def parse_json_cues(text: str) -> tuple[list[str], bool]:
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return [], False
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], False
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= MAX_TARGETS
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        return [], False
    return [item.strip() for item in value], True


def generate_adsqa_cues(
    zoom_model: Any,
    question: str,
) -> tuple[list[str], bool, str]:
    messages = [{
        "role": "user",
        "content": [{
            "type": "text",
            "text": ADSQA_CUE_PROMPT.format(question=question),
        }],
    }]
    text = zoom_model.processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = zoom_model.processor(
        text=[text],
        images=None,
        return_tensors="pt",
        padding=True,
        padding_side="left",
        add_special_tokens=False,
    ).to(zoom_model.device)
    generated = zoom_model.model.generate(
        **inputs,
        use_cache=True,
        max_new_tokens=128,
        do_sample=False,
    )
    trimmed = [
        output[len(source) :]
        for source, output in zip(inputs.input_ids, generated)
    ]
    response = zoom_model.processor.batch_decode(
        trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    cues, valid = parse_json_cues(response)
    return cues, valid, response


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
    sys.path.insert(0, str(args.adapter_root.resolve()))

    import torch
    from PIL import Image
    import transformers
    from ZoomEye.tree import ImageTree
    from ZoomEye.utils import (
        include_pronouns,
        merge_bbox_list,
        union_all_bboxes,
    )
    from ZoomEye.zoom_eye import (
        zoom_eye_search_type1,
        zoom_eye_search_type2,
    )
    from ZoomEye.zoom_model_qwenvl import ZoomModelQwenVL

    ic_examples = json.loads(args.ic_examples.read_text(encoding="utf-8"))
    config = {
        "schema_version": "evads_zoomeye_policy_inference_v1",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "model_repository": MODEL_REPOSITORY,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "model_dir": str(args.model_dir.resolve()),
        "model_config_sha256": sha256(args.model_dir / "config.json"),
        "model_index_sha256": sha256(
            args.model_dir / "model.safetensors.index.json"
        ),
        "adapter_files_sha256": {
            name: sha256(args.adapter_root / "ZoomEye" / name)
            for name in (
                "tree.py",
                "utils.py",
                "zoom_eye.py",
                "zoom_model_qwenvl.py",
            )
        },
        "ic_examples_sha256": sha256(args.ic_examples),
        "cue_mode": args.cue_mode,
        "adsqa_cue_prompt_sha256": (
            hashlib.sha256(ADSQA_CUE_PROMPT.encode("utf-8")).hexdigest()
            if args.cue_mode == "adsqa_json"
            else None
        ),
        "requests_sha256": sha256(args.requests),
        "expected_items": args.expected_items,
        "gpu_id": args.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "split_num": SPLIT_NUM,
        "patch_scale": PATCH_SCALE,
        "bias_value": BIAS_VALUE,
        "maximum_visual_cues": MAX_TARGETS,
        "answering_confidence_lower": ANSWERING_CONFIDENCE_LOWER,
        "answering_confidence_upper": ANSWERING_CONFIDENCE_UPPER,
        "visual_cue_threshold": VISUAL_CUE_THRESHOLD,
        "threshold_decrease": THRESHOLD_DECREASE,
        "pop_limit": "max_tree_depth * 3 per visual cue",
        "selected_bbox_rule": (
            "union of official context-expanded patches for all selected nodes"
        ),
        "reference_answers_used": False,
        "judge_scores_used": False,
        "automatic_retry": False,
    }
    dump(args.output_dir / "run_config.json", config)

    zoom_model = ZoomModelQwenVL(
        model_path=str(args.model_dir),
        device="cuda:0",
        torch_dtype=torch.bfloat16,
        patch_scale=PATCH_SCALE,
        bias_value=BIAS_VALUE,
    )
    stats = Counter()
    result_path = args.output_dir / "policy_results.jsonl"
    error_path = args.output_dir / "errors.jsonl"
    for index, row in enumerate(rows, 1):
        started = time.time()
        key = (str(row["question_id"]), int(row["anchor_index"]))
        try:
            original = Image.open(str(row["image_path"])).convert("RGB")
            tree = ImageTree(
                image_path=str(row["image_path"]),
                patch_size=zoom_model.input_size[0],
                split_num=SPLIT_NUM,
            )
            if args.cue_mode == "official_ic":
                raw_targets = zoom_model.generate_visual_cues_using_ic(
                    ic_examples,
                    str(row["question"]),
                )
                cue_parse_valid = True
                cue_response_sha256 = None
            else:
                raw_targets, cue_parse_valid, cue_response = (
                    generate_adsqa_cues(
                        zoom_model,
                        str(row["question"]),
                    )
                )
                cue_response_sha256 = hashlib.sha256(
                    cue_response.encode("utf-8")
                ).hexdigest()
            filtered_targets = [
                target for target in raw_targets if not include_pronouns(target)
            ][:MAX_TARGETS]
            targets = zoom_model.filter_visual_cues(
                original,
                filtered_targets,
                tree.root,
                DECOMPOSED_QUESTION_TEMPLATE,
                ANSWERING_CONFIDENCE_UPPER,
            )
            one_target_search = (
                len(targets) == 1 and not targets[0].startswith("all ")
            )
            selected_nodes = []
            search_trace = []
            for target in targets:
                target_tree = ImageTree(
                    image_path=str(row["image_path"]),
                    patch_size=zoom_model.input_size[0],
                    split_num=SPLIT_NUM,
                )
                if not target.startswith("all "):
                    candidates, pops, zoom_in, zoom_out = (
                        zoom_eye_search_type1(
                            zoom_model=zoom_model,
                            pop_limit=lambda depth: depth * 3,
                            num_intervel=2,
                            threshold_descrease=THRESHOLD_DECREASE,
                            depth_limit=5,
                            question=(
                                str(row["question"])
                                if one_target_search
                                else DECOMPOSED_QUESTION_TEMPLATE.format(target)
                            ),
                            visual_cue=target,
                            answering_confidence_threshold_lower=(
                                ANSWERING_CONFIDENCE_LOWER
                            ),
                            answering_confidence_threshold_upper=(
                                ANSWERING_CONFIDENCE_UPPER
                            ),
                            image_pil=original,
                            image_tree=target_tree,
                            force_no_root=False,
                            force_visit_bottom=not one_target_search,
                        )
                    )
                    candidates.sort(key=lambda node: node.depth, reverse=True)
                    chosen = candidates[:1]
                    search_trace.append({
                        "target": target,
                        "search_type": "type1",
                        "num_pop": pops,
                        "num_zoom_in": zoom_in,
                        "num_zoom_out": zoom_out,
                        "candidate_count": len(candidates),
                        "selected": [
                            {
                                "depth": node.depth,
                                "bbox_xywh": list(node.state.bbox),
                                "answering_confidence": (
                                    node.answering_confidence
                                ),
                                "fast_confidence": node.fast_confidence,
                                "fast_confidence_details": (
                                    node.fast_confidence_details
                                ),
                            }
                            for node in chosen
                        ],
                    })
                    selected_nodes.extend(chosen)
                else:
                    singular_target = target[4:]
                    if singular_target.endswith("s"):
                        singular_target = singular_target[:-1]
                    candidates = zoom_eye_search_type2(
                        depth_limit=2,
                        image_tree=target_tree,
                        visual_cue=singular_target,
                        zoom_model=zoom_model,
                        visual_cue_threshold=VISUAL_CUE_THRESHOLD,
                        image_pil=original,
                    )
                    search_trace.append({
                        "target": target,
                        "search_type": "type2",
                        "candidate_count": len(candidates),
                        "selected": [
                            {
                                "depth": node.depth,
                                "bbox_xywh": list(node.state.bbox),
                                "fast_confidence": node.fast_confidence,
                            }
                            for node in candidates
                        ],
                    })
                    selected_nodes.extend(candidates)

            union_bbox = None
            if selected_nodes:
                expanded = [
                    zoom_model.get_patch(
                        node.state.bbox,
                        original.width,
                        original.height,
                        patch_size=zoom_model.input_size[0],
                        patch_scale=PATCH_SCALE,
                    )
                    for node in selected_nodes
                ]
                union_bbox = list(union_all_bboxes(
                    merge_bbox_list(expanded, threshold=0)
                ))
            bbox_norm = (
                normalize_xyxy(union_bbox, original.width, original.height)
                if union_bbox
                else None
            )
            area = (
                (bbox_norm[2] - bbox_norm[0])
                * (bbox_norm[3] - bbox_norm[1])
                if bbox_norm
                else None
            )
            result = {
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
                "raw_visual_cues": raw_targets,
                "cue_mode": args.cue_mode,
                "cue_parse_valid": cue_parse_valid,
                "cue_response_sha256": cue_response_sha256,
                "filtered_visual_cues": filtered_targets,
                "searched_visual_cues": targets,
                "search_trace": search_trace,
                "selected_node_count": len(selected_nodes),
                "bbox_pixel_original": union_bbox,
                "bbox_norm": bbox_norm,
                "bbox_area_ratio": area,
                "selected_bbox_rule": (
                    "context_expanded_selected_node_union"
                    if bbox_norm
                    else None
                ),
                "parse_valid": True,
                "latency_seconds": time.time() - started,
                "reference_answer_used": False,
            }
            append_jsonl(result_path, result)
            stats["processed"] += 1
            stats["triggered_anchors"] += int(bbox_norm is not None)
            stats["selected_nodes"] += len(selected_nodes)
            stats["raw_visual_cues"] += len(raw_targets)
            stats["searched_visual_cues"] += len(targets)
            stats["cue_parse_failures"] += int(not cue_parse_valid)
            stats["exact_full_bbox_anchors"] += int(area == 1.0)
            print(json.dumps({
                "index": index,
                "total": len(rows),
                "question_id": key[0],
                "raw_visual_cues": raw_targets,
                "searched_visual_cues": targets,
                "selected_node_count": len(selected_nodes),
                "bbox_norm": bbox_norm,
            }, ensure_ascii=False), flush=True)
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
    config["stats"] = dict(stats)
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
        raise RuntimeError(f"ZoomEye policy inference incomplete: {stats}")


if __name__ == "__main__":
    main()
