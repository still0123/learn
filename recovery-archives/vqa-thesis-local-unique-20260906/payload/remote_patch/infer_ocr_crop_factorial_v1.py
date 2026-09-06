#!/usr/bin/env python3
"""Factorial OCR x spatial-focus A2 inference with frozen Qwen3-VL-8B.

All arms share V1-V8 (MMR8, 512), two evidence moments, four 896 extra
views, ASR, prompt template, and generation settings.  The only factors are:

* visual_mode=crop: two deterministic crops from each evidence moment.
* visual_mode=full: the same evidence frame repeated for the two slots.
* ocr_mode=on/off: include or remove the same cached OCR text.

The full-frame arm deliberately repeats the anchor frame because the crop arm
uses two regions from that exact frame.  This keeps temporal evidence fixed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

# ---- deterministic random center (mirror of av_funnel8 frozen generator) ----
import hashlib


def deterministic_random_center(
    question_id: str,
    anchor_index: int,
    broad_side: float,
    evidence_center: tuple[float, float],
) -> tuple[float, float]:
    digest = hashlib.sha256(
        f"av-funnel8-random-center-v2:{question_id}:{anchor_index}".encode("utf-8")
    ).digest()
    low = broad_side / 2.0
    span = 1.0 - broad_side
    center_x = low + (digest[0] / 255.0) * span
    center_y = low + (digest[1] / 255.0) * span
    evidence_x, evidence_y = evidence_center
    if abs(center_x - evidence_x) + abs(center_y - evidence_y) < max(1e-7, span * 0.05):
        center_x = low + ((digest[2] / 255.0 + 0.37) % 1.0) * span
        center_y = low + ((digest[3] / 255.0 + 0.61) % 1.0) * span
    return center_x, center_y


def square_box(center_x: float, center_y: float, side: float) -> list[float]:
    left = min(max(center_x - side / 2.0, 0.0), 1.0 - side)
    top = min(max(center_y - side / 2.0, 0.0), 1.0 - side)
    return [left, top, left + side, top + side]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["0", "1", "2", "3", "4", "5"])
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-size", type=int, default=512)
    parser.add_argument("--crop-size", type=int, default=896)
    parser.add_argument("--max-visual-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--visual-mode", choices=("crop", "full"), required=True)
    parser.add_argument("--ocr-mode", choices=("on", "off", "rerun"), required=True)
    parser.add_argument("--ocr-cache", type=Path)
    parser.add_argument("--crop-side", type=float, default=0.35)
    parser.add_argument("--expected-items", type=int, default=600)
    parser.add_argument("--resume-existing", action="store_true")
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ARGS.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from decord import VideoReader, cpu  # noqa: E402
from PIL import Image  # noqa: E402
import torch  # noqa: E402
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration  # noqa: E402


OCR_BY_QID: dict[str, dict[str, Any]] = {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def visual_grid_area(inputs: Any) -> int:
    total = 0
    for key in ("image_grid_thw", "video_grid_thw"):
        for grid in inputs.get(key, []):
            total += int(grid[0]) * int(grid[1]) * int(grid[2])
    return total


def count_visual_tokens(processor: Any, inputs: Any) -> int:
    """Count the actual expanded image/video placeholder tokens."""
    input_ids = inputs["input_ids"]
    token_ids = {
        int(processor.tokenizer.convert_tokens_to_ids("<|image_pad|>")),
        int(processor.tokenizer.convert_tokens_to_ids("<|video_pad|>")),
    }
    return sum(int((input_ids == token_id).sum().item()) for token_id in token_ids)


def crop_frame(frame: Image.Image, bbox_norm: list[float], size: int) -> tuple[Image.Image, list[int]]:
    width, height = frame.size
    left, top, right, bottom = [max(0.0, min(1.0, float(v))) for v in bbox_norm]
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


def decode_frames(video_path: str, indices: list[int], size: int) -> tuple[list[Image.Image], int, float]:
    reader = VideoReader(video_path, ctx=cpu(0))
    frames = []
    for idx in indices:
        frames.append(Image.fromarray(reader[idx].asnumpy()).convert("RGB").resize((size, size), Image.Resampling.BICUBIC))
    return frames, len(reader), float(reader.get_avg_fps())


def uniform_indices(total: int, n: int) -> list[int]:
    if n <= 0 or total <= 0:
        return []
    if n == 1:
        return [0]
    return [round(i * (total - 1) / (n - 1)) for i in range(n)]


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
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
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
    grid_area = visual_grid_area(inputs)
    if visual_tokens > ARGS.max_visual_tokens:
        raise RuntimeError(f"visual token budget exceeded: {visual_tokens} > {ARGS.max_visual_tokens}")
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=ARGS.max_new_tokens, do_sample=False)
    generated = generated[:, inputs["input_ids"].shape[1]:]
    output = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
    return output, {"visual_tokens": visual_tokens, "visual_grid_area": grid_area}


def extract_answer(raw: str, fallback: str) -> tuple[str, bool]:
    match = re.search(r"\[Answer\]\s*:?\s*(.+)", raw, re.IGNORECASE)
    if match:
        return match.group(1).strip(), True
    return fallback, False


def a2_prompt(row: dict[str, Any]) -> str:
    if ARGS.visual_mode == "crop":
        view_description = (
            f"V9 and V10 are two {ARGS.crop_size} crops of evidence moment 1 (response center and an "
            f"independent offset center). V11 and V12 are the two corresponding crops of "
            f"evidence moment 2. "
        )
    else:
        view_description = (
            f"V9 and V10 are two {ARGS.crop_size} full-frame views of the same evidence moment 1. "
            f"V11 and V12 are the two corresponding full-frame views of evidence moment 2. "
        )
    ocr_lines = []
    if ARGS.ocr_mode == "on":
        ocr_lines = [
            f"{item['id']} @ {float(item['timestamp_sec']):.2f}s "
            f"(confidence {float(item['confidence']):.2f}): {item['text']}"
            for item in row.get("ocr_evidence", [])
        ]
    elif ARGS.ocr_mode == "rerun":
        cache = OCR_BY_QID[str(row["question_id"])]
        ocr_lines = [
            f"{item['view_id']} (confidence {float(item['score']):.2f}): {item['text']}"
            for item in cache.get("detections", [])
        ]
    asr_lines = [
        f"{item['id']} @ {float(item['start_sec']):.2f}-{float(item['end_sec']):.2f}s: {item['text']}"
        for item in row.get("asr_evidence", [])
    ]
    return (
        "Verify and, only when necessary, revise the initial answer using only the supplied "
        "advertisement evidence. V1-V8 are the original chronological global frames. "
        + view_description
        + (
            ("Cached OCR text is supplied below. " if ARGS.ocr_mode == "on" else
             "OCR text re-recognized only from V9-V12 is supplied below. ")
            if ARGS.ocr_mode in ("on", "rerun")
            else "OCR text is intentionally unavailable in this protocol arm. "
        )
        + "ASR evidence may be missing; absence is not a contradiction. "
        + "Keep the initial answer unless the supplied evidence gives a decisive reason to revise it. "
        + "Return exactly one line beginning with [Answer]: and no analysis.\n"
        f"Question: {row['question']}\n"
        f"Initial answer: {row['a0_prediction']}\n"
        f"OCR: {' '.join(ocr_lines) if ocr_lines else ('none' if ARGS.ocr_mode in ('on', 'rerun') else 'disabled')}\n"
        f"ASR: {' '.join(asr_lines) if asr_lines else 'none'}\n"
    )


def main() -> None:
    global OCR_BY_QID
    rows = load_jsonl(ARGS.input_jsonl)
    if len(rows) != ARGS.expected_items:
        raise RuntimeError(f"expected {ARGS.expected_items} rows, got {len(rows)}")
    if any(k in row for k in ("answer", "ground_truth", "reference_answer", "meta_info", "judge_score", "label") for row in rows if k in row):
        # forbid leaked answer fields in any row
        bad = [k for row in rows for k in ("answer", "ground_truth", "reference_answer", "meta_info", "judge_score", "label") if k in row]
        if bad:
            raise RuntimeError(f"forbidden fields present: {set(bad)}")

    if ARGS.ocr_mode == "rerun":
        if ARGS.ocr_cache is None:
            raise RuntimeError("--ocr-cache is required for rerun mode")
        OCR_BY_QID = {str(item["question_id"]): item for item in load_jsonl(ARGS.ocr_cache)}
        expected_qids = {str(row["question_id"]) for row in rows}
        if set(OCR_BY_QID) != expected_qids:
            raise RuntimeError("OCR cache and input question sets differ")
        if any(item.get("visual_mode") != ARGS.visual_mode for item in OCR_BY_QID.values()):
            raise RuntimeError("OCR cache visual mode mismatch")
    elif ARGS.ocr_cache is not None:
        raise RuntimeError("--ocr-cache is only valid in rerun mode")

    output_root = Path(ARGS.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        str(ARGS.model_dir), torch_dtype=torch.bfloat16, device_map="cuda:0"
    )
    processor = AutoProcessor.from_pretrained(str(ARGS.model_dir))

    stats = {"done": 0, "errors": 0, "a2_parse_failures": 0}
    start = time.time()

    for row in rows:
        qid = row["question_id"]
        item_dir = output_root / qid
        out_file = item_dir / "a2_prediction.json"
        if ARGS.resume_existing and out_file.exists():
            stats["done"] += 1
            continue
        try:
            base_indices = [int(v) for v in row["a0_frame_indices"]]
            if len(base_indices) != 8:
                raise RuntimeError(f"A0 does not contain eight frames: {qid}")
            base_frames, total_frames, fps = decode_frames(
                str(row["video_path"]), base_indices, ARGS.base_size
            )
            reader = VideoReader(str(row["video_path"]), ctx=cpu(0))
            plan32 = uniform_indices(len(reader), 32)
            extra_frames: list[Image.Image] = []
            extra_plan: list[dict[str, Any]] = []

            anchors = row["evidence_anchors"]
            if len(anchors) != 2:
                raise RuntimeError(f"expected 2 anchors, got {len(anchors)}: {qid}")

            for anchor in anchors:
                rank = int(anchor["source_global_rank"])
                if rank not in range(32):
                    raise RuntimeError(f"invalid anchor rank {rank}")
                source_index = int(plan32[rank])
                source = Image.fromarray(reader[source_index].asnumpy()).convert("RGB")

                if ARGS.visual_mode == "crop":
                    # center 1: response center (anchor bbox center), small focused box
                    bbox1 = [float(v) for v in anchor["bbox_norm"]]
                    center1 = ((bbox1[0] + bbox1[2]) / 2.0, (bbox1[1] + bbox1[3]) / 2.0)
                    side = ARGS.crop_side
                    box1 = square_box(center1[0], center1[1], side)
                    # center 2: deterministic random center (frozen av_funnel8 rule)
                    c2x, c2y = deterministic_random_center(qid, int(anchor["anchor_index"]), side, center1)
                    box2 = square_box(c2x, c2y, side)
                    crop1, px1 = crop_frame(source, box1, ARGS.crop_size)
                    crop2, px2 = crop_frame(source, box2, ARGS.crop_size)
                    extra_frames.extend([crop1, crop2])
                    extra_plan.extend([
                        {"view_id": f"V{9 + 2 * int(anchor['anchor_index'])}", "anchor_index": int(anchor["anchor_index"]), "view_type": "evidence_crop_center1", "bbox_norm": box1, "pixel_box": px1, "bbox_source": "response_center", "size": ARGS.crop_size, "crop_side": side, "source_global_rank32": rank, "source_frame_index": source_index},
                        {"view_id": f"V{10 + 2 * int(anchor['anchor_index'])}", "anchor_index": int(anchor["anchor_index"]), "view_type": "evidence_crop_center2", "bbox_norm": box2, "pixel_box": px2, "bbox_source": "deterministic_random_center", "size": ARGS.crop_size, "crop_side": side, "source_global_rank32": rank, "source_frame_index": source_index},
                    ])
                else:
                    # Pure spatial control: duplicate the exact anchor frame for both slots.
                    full896 = source.resize((ARGS.crop_size, ARGS.crop_size), Image.Resampling.BICUBIC)
                    extra_frames.extend([full896, full896.copy()])
                    extra_plan.extend([
                        {"view_id": f"V{9 + 2 * int(anchor['anchor_index'])}", "anchor_index": int(anchor["anchor_index"]), "view_type": "evidence_full_same_frame_1", "bbox_norm": [0.0, 0.0, 1.0, 1.0], "bbox_source": "same_anchor_full_control", "size": ARGS.crop_size, "source_global_rank32": rank, "source_frame_index": source_index},
                        {"view_id": f"V{10 + 2 * int(anchor['anchor_index'])}", "anchor_index": int(anchor["anchor_index"]), "view_type": "evidence_full_same_frame_2", "bbox_norm": [0.0, 0.0, 1.0, 1.0], "bbox_source": "same_anchor_full_control", "size": ARGS.crop_size, "source_global_rank32": rank, "source_frame_index": source_index},
                    ])

            if len(extra_frames) != 4:
                raise RuntimeError(f"expected 4 extra views, got {len(extra_frames)}")

            a2_raw, a2_trace = generate(
                processor, model, base_frames, extra_frames, base_indices, a2_prompt(row)
            )
            a2_answer, a2_valid = extract_answer(a2_raw, str(row["a0_prediction"]))
            if not a2_valid:
                stats["a2_parse_failures"] += 1

            item_dir.mkdir(parents=True, exist_ok=False)
            (item_dir / "a2_prediction.json").write_text(
                json.dumps({
                    "question_id": qid,
                    "method": f"Qwen3_OCRCropFactorial_{ARGS.visual_mode}_{ARGS.ocr_mode}",
                    "prediction": a2_answer,
                    "a2_raw": a2_raw,
                    "parse_valid": a2_valid,
                    "visual_tokens": a2_trace["visual_tokens"],
                    "visual_grid_area": a2_trace["visual_grid_area"],
                    "visual_mode": ARGS.visual_mode,
                    "ocr_mode": ARGS.ocr_mode,
                    "ocr_evidence_in_prompt": ARGS.ocr_mode in ("on", "rerun"),
                    "ocr_source": (
                        "cached_global" if ARGS.ocr_mode == "on" else
                        "rerun_extra_views" if ARGS.ocr_mode == "rerun" else
                        "disabled"
                    ),
                    "ocr_cache_sha256": sha256_file(ARGS.ocr_cache) if ARGS.ocr_cache else None,
                    "asr_evidence_in_prompt": True,
                    "extra_plan": extra_plan,
                }, ensure_ascii=True, indent=2) + "\n",
                encoding="utf-8",
            )
            stats["done"] += 1
            if stats["done"] % 20 == 0:
                elapsed = time.time() - start
                print(json.dumps({"done": stats["done"], "elapsed_s": round(elapsed, 1), "per_item_s": round(elapsed / stats["done"], 2)}), flush=True)
        except Exception as exc:
            stats["errors"] += 1
            print(f"ERROR {qid}: {type(exc).__name__}: {exc}", flush=True)

    summary = {
        "schema_version": "ocr_crop_factorial_a2_summary_v1",
        "visual_mode": ARGS.visual_mode,
        "ocr_mode": ARGS.ocr_mode,
        "expected": ARGS.expected_items,
        "done": stats["done"],
        "errors": stats["errors"],
        "a2_parse_failures": stats["a2_parse_failures"],
        "elapsed_s": round(time.time() - start, 1),
        "model_dir": str(ARGS.model_dir),
        "crop_size": ARGS.crop_size,
        "max_visual_tokens": ARGS.max_visual_tokens,
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("SUMMARY:", json.dumps(summary))


if __name__ == "__main__":
    main()
