#!/usr/bin/env python3
"""Generate Qwen2.5 evidence-constrained edits, including ASR-aligned temporal tools."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
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
    parser.add_argument("--max-visual-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--expected-items", type=int, default=10)
    parser.add_argument("--a2-method", required=True)
    parser.add_argument(
        "--ablation-variant",
        choices=(
            "minimal_edit",
            "full_only_minimal_edit",
            "temporal_neighbor_minimal_edit",
            "temporal_asr_minimal_edit",
        ),
        required=True,
    )
    parser.add_argument("--skip-a1", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--allow-shared-gpu", action="store_true")
    parser.add_argument("--min-free-memory-mib", type=int, default=26000)
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ARGS.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from decord import VideoReader, cpu  # noqa: E402
from PIL import Image  # noqa: E402
import torch  # noqa: E402
from transformers import AutoModelForVision2Seq, AutoProcessor  # noqa: E402


FORBIDDEN = {
    "answer",
    "ground_truth",
    "reference_answer",
    "meta_info",
    "judge_score",
    "label",
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


def inspect_gpu(gpu_id: str) -> dict[str, Any]:
    if gpu_id not in {"0", "1", "2", "3", "4", "5"}:
        raise RuntimeError("GPU ID must be between 0 and 5")
    snapshot = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.used,memory.free,memory.total,utilization.gpu",
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
    if len(matching) != 1:
        raise RuntimeError(f"GPU{gpu_id} snapshot is unavailable")
    free_memory_mib = int(matching[0].split(",")[3].strip())
    if active and not ARGS.allow_shared_gpu:
        raise RuntimeError(f"GPU{gpu_id} is not idle: {active}")
    if free_memory_mib < ARGS.min_free_memory_mib:
        raise RuntimeError(
            f"GPU{gpu_id} has only {free_memory_mib} MiB free; "
            f"requires {ARGS.min_free_memory_mib} MiB"
        )
    return {
        "gpu_row": matching[0],
        "active_processes_before_load": active,
        "allow_shared_gpu": ARGS.allow_shared_gpu,
        "min_free_memory_mib": ARGS.min_free_memory_mib,
    }


def uniform_indices(total: int, count: int) -> list[int]:
    if total <= 0 or count <= 0:
        raise RuntimeError("invalid frame count")
    if total == 1:
        return [0] * count
    return [round(index * (total - 1) / (count - 1)) for index in range(count)]


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


def temporal_neighbors(source_index: int, total_frames: int) -> tuple[int, int]:
    """Return two nearby frames that are distinct from the frozen anchor."""
    step = max(1, round(total_frames / 32))
    candidates = [
        source_index - step,
        source_index + step,
        source_index - 2 * step,
        source_index + 2 * step,
    ]
    valid = []
    for index in candidates:
        index = max(0, min(total_frames - 1, index))
        if index != source_index and index not in valid:
            valid.append(index)
    if len(valid) < 2:
        raise RuntimeError("video is too short for two distinct temporal neighbors")
    return valid[0], valid[1]


def asr_segment_indices(
    segment: dict[str, Any], fps: float, total_frames: int, anchor_index: int
) -> tuple[int, int]:
    start = max(0, min(total_frames - 1, round(float(segment["start_sec"]) * fps)))
    end = max(0, min(total_frames - 1, round(float(segment["end_sec"]) * fps) - 1))
    if end == start:
        end = min(total_frames - 1, start + 1)
    if start == anchor_index:
        start = max(0, start - 1) if start else min(total_frames - 1, start + 1)
    if end == anchor_index or end == start:
        end = min(total_frames - 1, end + 1) if end + 1 < total_frames else max(0, end - 1)
    if start == end:
        raise RuntimeError("ASR segment cannot provide two distinct temporal frames")
    return start, end


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
    if ARGS.ablation_variant == "temporal_asr_minimal_edit":
        view_description = (
            "V9 and V10 are the start and end frames of the most question-relevant ASR segment. "
            "V11 and V12 are the corresponding frames for the second ASR segment. "
        )
    elif ARGS.ablation_variant == "temporal_neighbor_minimal_edit":
        view_description = (
            "V9 and V10 are new nearby temporal frames around evidence moment 1. "
            "V11 and V12 are new nearby temporal frames around evidence moment 2. "
        )
    elif ARGS.ablation_variant == "full_only_minimal_edit":
        view_description = (
            "V9 and V10 are 512 and 896 full-frame views for evidence moment 1. "
            "V11 and V12 are the corresponding full-frame views for evidence moment 2. "
        )
    else:
        view_description = (
            "V9 and V10 are a full frame and its independent mid-scale crop for evidence moment 1. "
            "V11 and V12 are the corresponding views for evidence moment 2. "
        )
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
        "Perform a minimal evidence correction of the initial answer. Do not paraphrase or "
        "rewrite it merely for style. V1-V8 are the original chronological global frames. "
        + view_description
        + "OCR and ASR evidence may be missing; absence is not a contradiction. Revise only "
        + "when a cited visual, OCR, or ASR item directly contradicts the initial answer or "
        + "supplies a decisive missing fact needed by the question. Otherwise KEEP it exactly. "
        + "Use only evidence IDs that appear here: V1-V12, O-items, and S-items. "
        + "Return exactly three lines and no other analysis:\n"
        + "[Decision]: KEEP or REVISE\n"
        + "[Evidence]: NONE for KEEP; otherwise comma-separated evidence IDs\n"
        + "[Answer]: the exact initial answer for KEEP; otherwise one concise corrected answer\n"
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


def extract_minimal_edit(
    text: str,
    row: dict[str, Any],
) -> tuple[str, bool, str, list[str], dict[str, Any]]:
    fallback = str(row["a0_prediction"]).strip()
    decision_match = re.search(
        r"^\[Decision\]\s*:\s*(KEEP|REVISE)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    evidence_match = re.search(
        r"^\[Evidence\]\s*:\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    answer_match = re.search(
        r"^\[Answer\]\s*:\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not decision_match or not evidence_match or not answer_match:
        return fallback, False, "PARSE_FALLBACK", [], {
            "reason": "missing_required_line",
        }
    decision = decision_match.group(1).upper()
    evidence_text = evidence_match.group(1).strip()
    raw_answer = answer_match.group(1).strip()
    evidence_ids = sorted(set(re.findall(
        r"\b(?:V(?:[1-9]|1[0-2])|O\d+|S\d+)\b",
        evidence_text,
        flags=re.IGNORECASE,
    )))
    evidence_ids = [value.upper() for value in evidence_ids]
    allowed_ids = {f"V{index}" for index in range(1, 13)}
    allowed_ids.update(
        str(item["id"]).upper() for item in row.get("ocr_evidence", [])
    )
    allowed_ids.update(
        str(item["id"]).upper() for item in row.get("asr_evidence", [])
    )
    invalid_ids = sorted(set(evidence_ids) - allowed_ids)
    if decision == "KEEP":
        valid = evidence_text.casefold() == "none"
        return fallback, valid, decision, [], {
            "reason": "valid_keep" if valid else "keep_requires_none",
            "raw_answer_matches_a0": (
                " ".join(raw_answer.casefold().split())
                == " ".join(fallback.casefold().split())
            ),
            "invalid_evidence_ids": invalid_ids,
        }
    changed = (
        " ".join(raw_answer.casefold().split())
        != " ".join(fallback.casefold().split())
    )
    valid = bool(raw_answer and evidence_ids and not invalid_ids and changed)
    return (raw_answer if valid else fallback), valid, decision, evidence_ids, {
        "reason": "valid_revise" if valid else "invalid_revise_contract",
        "raw_answer_matches_a0": not changed,
        "invalid_evidence_ids": invalid_ids,
    }


def main() -> None:
    if (ARGS.base_size, ARGS.crop_size, ARGS.max_visual_tokens) != (512, 896, 4096):
        raise RuntimeError("frozen protocol requires base=512, crop=896, token cap=4096")
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
    gpu_snapshot = inspect_gpu(ARGS.gpu_id)
    ARGS.output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "qwen25_evidence_minimal_edit_inference_v4",
        "gpu_id": ARGS.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "allow_shared_gpu": ARGS.allow_shared_gpu,
        "min_free_memory_mib": ARGS.min_free_memory_mib,
        "model_dir": str(ARGS.model_dir.resolve()),
        "model_config_sha256": sha256_file(ARGS.model_dir / "config.json"),
        "input_jsonl": str(ARGS.input_jsonl.resolve()),
        "input_sha256": sha256_file(ARGS.input_jsonl),
        "rows": len(rows),
        "a1_views": 8,
        "a2_views": 12,
        "base_size": ARGS.base_size,
        "crop_size": ARGS.crop_size,
        "max_visual_tokens": ARGS.max_visual_tokens,
        "max_new_tokens": ARGS.max_new_tokens,
        "expected_items": ARGS.expected_items,
        "resume_existing": ARGS.resume_existing,
        "a2_method": ARGS.a2_method,
        "ablation_variant": ARGS.ablation_variant,
        "ocr_evidence_in_prompt": True,
        "asr_evidence_in_prompt": True,
        "minimal_edit_contract": {
            "decisions": ["KEEP", "REVISE"],
            "revise_requires_evidence_id": True,
            "invalid_output_falls_back_to_a0": True,
        },
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
    model = AutoModelForVision2Seq.from_pretrained(
        ARGS.model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
    )
    if str(model.config.model_type) != "qwen2_5_vl":
        raise RuntimeError(f"expected qwen2_5_vl, got {model.config.model_type}")
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
        item_dir = ARGS.output_dir / qid
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
            plan32 = uniform_indices(len(reader), 32)
            asr_segments = list(row.get("asr_evidence", []))[:2]
            if ARGS.ablation_variant == "temporal_asr_minimal_edit" and len(asr_segments) < 2:
                raise RuntimeError("ASR-aligned temporal tool requires two timestamped segments")
            extra_frames: list[Image.Image] = []
            extra_plan: list[dict[str, Any]] = []
            for anchor in row["evidence_anchors"]:
                rank = int(anchor["source_global_rank"])
                if rank not in range(32):
                    raise RuntimeError("invalid frozen 32-frame evidence rank")
                source_index = int(plan32[rank])
                source = Image.fromarray(reader[source_index].asnumpy()).convert("RGB")
                if ARGS.ablation_variant == "temporal_asr_minimal_edit":
                    segment = asr_segments[int(anchor["anchor_index"])]
                    before_index, after_index = asr_segment_indices(
                        segment, float(reader.get_avg_fps()), len(reader), source_index
                    )
                    full = Image.fromarray(reader[before_index].asnumpy()).convert("RGB").resize(
                        (ARGS.base_size, ARGS.base_size), Image.Resampling.BICUBIC
                    )
                    detail = Image.fromarray(reader[after_index].asnumpy()).convert("RGB").resize(
                        (ARGS.crop_size, ARGS.crop_size), Image.Resampling.BICUBIC
                    )
                    full_plan = {
                        "view_type": "asr_segment_start",
                        "source_frame_index": before_index,
                        "asr_id": segment["id"],
                    }
                    detail_plan = {
                        "view_type": "asr_segment_end",
                        "source_frame_index": after_index,
                        "asr_id": segment["id"],
                    }
                elif ARGS.ablation_variant == "temporal_neighbor_minimal_edit":
                    before_index, after_index = temporal_neighbors(source_index, len(reader))
                    full = Image.fromarray(reader[before_index].asnumpy()).convert("RGB").resize(
                        (ARGS.base_size, ARGS.base_size), Image.Resampling.BICUBIC
                    )
                    detail = Image.fromarray(reader[after_index].asnumpy()).convert("RGB").resize(
                        (ARGS.crop_size, ARGS.crop_size), Image.Resampling.BICUBIC
                    )
                    full_plan = {
                        "view_type": "temporal_neighbor_before",
                        "source_frame_index": before_index,
                    }
                    detail_plan = {
                        "view_type": "temporal_neighbor_after",
                        "source_frame_index": after_index,
                    }
                else:
                    full = source.resize(
                        (ARGS.base_size, ARGS.base_size), Image.Resampling.BICUBIC
                    )
                    full_plan = {
                        "view_type": "evidence_full",
                        "source_frame_index": source_index,
                    }
                if ARGS.ablation_variant in {
                    "temporal_neighbor_minimal_edit",
                    "temporal_asr_minimal_edit",
                }:
                    pass
                elif ARGS.ablation_variant == "full_only_minimal_edit":
                    detail = source.resize(
                        (ARGS.crop_size, ARGS.crop_size), Image.Resampling.BICUBIC
                    )
                    detail_plan = {"view_type": "evidence_full_highres"}
                else:
                    detail, pixel_box = crop_frame(
                        source, list(anchor["bbox_norm"]), ARGS.crop_size
                    )
                    detail_plan = {
                        "view_type": "evidence_mid_crop",
                        "bbox_norm": anchor["bbox_norm"],
                        "pixel_box": pixel_box,
                        "bbox_source": anchor["bbox_source"],
                    }
                extra_frames.extend([full, detail])
                extra_plan.extend([
                    {
                        "view_id": f"V{9 + 2 * int(anchor['anchor_index'])}",
                        "anchor_index": int(anchor["anchor_index"]),
                        **full_plan,
                        "source_global_rank32": rank,
                        "anchor_frame_index": source_index,
                    },
                    {
                        "view_id": f"V{10 + 2 * int(anchor['anchor_index'])}",
                        "anchor_index": int(anchor["anchor_index"]),
                        **detail_plan,
                        "source_global_rank32": rank,
                        "anchor_frame_index": source_index,
                    },
                ])
            if len(extra_frames) != 4:
                raise RuntimeError("A2 must add four independent evidence views")
            a2_raw, a2_trace = generate(
                processor,
                model,
                base_frames,
                extra_frames,
                base_indices,
                a2_prompt(row),
            )
            (
                a2_answer,
                a2_valid,
                a2_decision,
                cited_evidence_ids,
                contract_audit,
            ) = extract_minimal_edit(a2_raw, row)
            if not a2_valid:
                stats["a2_parse_failures"] += 1

            item_dir.mkdir(parents=True, exist_ok=False)
            dump_json(item_dir / "a1_prediction.json", {
                "question_id": qid,
                "method": "Qwen25_GenericReconsider8_A1",
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
                "method": ARGS.a2_method,
                "prediction": a2_answer,
            })
            dump_json(item_dir / "a2_trace.json", {
                "question_id": qid,
                "raw_output": a2_raw,
                "parse_valid": a2_valid,
                "fallback_to_a0": not a2_valid,
                "decision": a2_decision,
                "cited_evidence_ids": cited_evidence_ids,
                "contract_audit": contract_audit,
                "answer_changed_from_a0": (
                    " ".join(a2_answer.casefold().split())
                    != " ".join(str(row["a0_prediction"]).casefold().split())
                ),
                "base_source_frame_indices": base_indices,
                "extra_view_plan": extra_plan,
                "crop_ablation_variant": ARGS.ablation_variant,
                "ocr_evidence_in_prompt": True,
                "asr_evidence_in_prompt": True,
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
