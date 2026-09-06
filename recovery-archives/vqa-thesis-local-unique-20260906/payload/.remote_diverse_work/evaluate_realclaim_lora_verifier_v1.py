#!/usr/bin/env python3
"""Evaluate a base or LoRA Qwen2.5-VL claim verifier on a frozen split."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--claims-jsonl", type=Path, required=True)
    parser.add_argument("--split", choices=("calibration", "development"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--views", type=int, default=8)
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--limit", type=int, default=-1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ARGS.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import cv2  # noqa: E402
from PIL import Image  # noqa: E402
from peft import PeftModel  # noqa: E402
from qwen_vl_utils import process_vision_info  # noqa: E402
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score  # noqa: E402
import torch  # noqa: E402
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose_views(indices: list[int]) -> list[int]:
    positions = [round(i * (len(indices) - 1) / (ARGS.views - 1)) for i in range(ARGS.views)]
    return [int(indices[position]) for position in positions]


def decode_frames(video_path: str, indices: list[int]) -> list[Image.Image]:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    frames = []
    try:
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"cannot decode frame {index}: {video_path}")
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image.thumbnail((448, 448), Image.Resampling.LANCZOS)
            frames.append(image)
    finally:
        capture.release()
    return frames


def prompt(row: dict) -> str:
    return (
        "Determine whether the atomic claim is supported or contradicted by the supplied "
        "advertisement frames and transcript. Use only supplied evidence. "
        "Answer A for supported or B for contradicted. Do not explain.\n"
        f"Question: {row['question']}\nAtomic claim: {row['claim']}\n"
        f"Transcript: {str(row.get('asr_excerpt', ''))[:1600]}\nAnswer:"
    )


def prepare(processor, row: dict, device: torch.device) -> dict:
    frames = decode_frames(str(row["video_path"]), choose_views(list(row["selected_frame_indices"])))
    content = [{"type": "image", "image": image} for image in frames]
    content.append({"type": "text", "text": prompt(row)})
    messages = [{"role": "user", "content": content}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")
    return {key: value.to(device) for key, value in inputs.items()}


def best_threshold(y_true: list[int], scores: list[float]) -> tuple[float, float]:
    candidates = sorted(set(scores))
    best = (0.5, -1.0)
    for threshold in candidates:
        metric = balanced_accuracy_score(y_true, [int(score >= threshold) for score in scores])
        if metric > best[1]:
            best = (threshold, metric)
    return best


def main() -> None:
    ARGS.output_dir.mkdir(parents=True, exist_ok=True)
    output = ARGS.output_dir / "scores.jsonl"
    if output.exists() and ARGS.overwrite:
        output.unlink()
    existing = {row["question_id"] for row in load_jsonl(output)} if output.exists() else set()
    labels = {str(row["claim_id"]): row for row in load_jsonl(ARGS.claims_jsonl)}
    rows = [row for row in load_jsonl(ARGS.input_jsonl) if row.get("split") == ARGS.split]
    if ARGS.limit > 0:
        rows = rows[:ARGS.limit]
    config = {
        "schema": "adsqa_realclaim_lora_evaluation_config_v1",
        "model_dir": str(ARGS.model_dir), "adapter_dir": str(ARGS.adapter_dir) if ARGS.adapter_dir else None,
        "split": ARGS.split, "rows": len(rows), "views": ARGS.views,
        "input_sha256": sha256_file(ARGS.input_jsonl), "claims_sha256": sha256_file(ARGS.claims_jsonl),
        "model_input_excludes_reference_answer_and_label": True,
        "labels_are_llm_assisted_not_human_gold": True,
    }
    dump_json(ARGS.output_dir / "config.json", config)
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir, min_pixels=224 * 224, max_pixels=448 * 448, trust_remote_code=True
    )
    ids = {}
    for name, choice in (("supported", "A"), ("contradicted", "B")):
        encoded = processor.tokenizer.encode(choice, add_special_tokens=False)
        if len(encoded) != 1:
            raise RuntimeError(f"choice {choice} is not one token")
        ids[name] = encoded[0]
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        ARGS.model_dir, torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map={"": 0}
    )
    if ARGS.adapter_dir:
        model = PeftModel.from_pretrained(model, ARGS.adapter_dir)
    model.eval()
    started = time.time()
    for index, row in enumerate(rows, 1):
        qid = str(row["question_id"])
        if qid in existing:
            continue
        label_row = labels[qid]
        reference_label = str(label_row["label"])
        binary_label = int(reference_label == "supported")
        inputs = prepare(processor, row, model.device)
        with torch.inference_mode():
            logits = model(**inputs, use_cache=False).logits[0, -1].float()
        pair_logits = torch.stack([logits[ids["supported"]], logits[ids["contradicted"]]])
        probability = float(torch.softmax(pair_logits, dim=0)[0].cpu())
        append_jsonl(output, {
            "question_id": qid, "video_id": row["video_id"], "split": ARGS.split,
            "primary_type": row.get("primary_type"), "reference_label": reference_label,
            "binary_label": binary_label, "support_probability": probability,
        })
        print(json.dumps({"index": index, "total": len(rows), "question_id": qid}), flush=True)
    scored = load_jsonl(output)
    y_true = [int(row["binary_label"]) for row in scored]
    scores = [float(row["support_probability"]) for row in scored]
    if len(set(y_true)) < 2:
        raise RuntimeError("evaluation split contains only one binary class")
    fitted_threshold, fitted_balanced = best_threshold(y_true, scores)
    threshold = ARGS.threshold if ARGS.threshold is not None else fitted_threshold
    summary = {
        "schema": "adsqa_realclaim_lora_evaluation_v1", "complete": len(scored) == len(rows),
        "rows": len(scored), "positives": sum(y_true), "negatives": len(y_true) - sum(y_true),
        "auroc": roc_auc_score(y_true, scores), "auprc_positive": average_precision_score(y_true, scores),
        "threshold": threshold,
        "threshold_source": "provided_frozen" if ARGS.threshold is not None else f"fitted_on_{ARGS.split}",
        "balanced_accuracy": balanced_accuracy_score(y_true, [int(score >= threshold) for score in scores]),
        "best_split_threshold": fitted_threshold, "best_split_balanced_accuracy": fitted_balanced,
        "elapsed_sec": time.time() - started,
        "gpu_peak_memory_mb": torch.cuda.max_memory_allocated() / 1024 / 1024,
    }
    dump_json(ARGS.output_dir / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
