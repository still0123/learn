#!/usr/bin/env python3
"""Train a frozen-vision Qwen2.5-VL LoRA claim verifier on audited pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--labels-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("classification", "pairwise"), required=True)
    parser.add_argument("--max-pairs", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--views", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--margin", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=20260721)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ARGS.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import cv2  # noqa: E402
from PIL import Image  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from qwen_vl_utils import process_vision_info  # noqa: E402
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration  # noqa: E402


LABEL_TO_CHOICE = {"supported": "A", "contradicted": "B"}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_key(value: str) -> str:
    return hashlib.sha256(f"{ARGS.seed}:{value}".encode()).hexdigest()


def choose_views(indices: list[int], count: int) -> list[int]:
    if len(indices) < count:
        raise ValueError(f"need at least {count} frame indices, got {len(indices)}")
    if count == 1:
        return [int(indices[len(indices) // 2])]
    positions = [round(i * (len(indices) - 1) / (count - 1)) for i in range(count)]
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
        f"Question: {row['question']}\n"
        f"Atomic claim: {row['claim']}\n"
        f"Transcript: {str(row.get('asr_excerpt', ''))[:1600]}\n"
        "Answer:"
    )


def resolve_choice_ids(tokenizer) -> dict[str, int]:
    ids = {}
    for label, choice in LABEL_TO_CHOICE.items():
        encoded = tokenizer.encode(choice, add_special_tokens=False)
        if len(encoded) != 1:
            raise RuntimeError(f"choice {choice} is not a single token: {encoded}")
        ids[label] = encoded[0]
    if len(set(ids.values())) != 2:
        raise RuntimeError("label token ids are not distinct")
    return ids


def prepare_example(processor, row: dict, label: str, device: torch.device) -> tuple[dict, torch.Tensor, int]:
    frame_indices = choose_views(list(row["selected_frame_indices"]), ARGS.views)
    frames = decode_frames(str(row["video_path"]), frame_indices)
    content = [{"type": "image", "image": image} for image in frames]
    content.append({"type": "text", "text": prompt(row)})
    messages = [
        {"role": "user", "content": content},
        {"role": "assistant", "content": [{"type": "text", "text": LABEL_TO_CHOICE[label]}]},
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}
    target_id = processor.tokenizer.encode(LABEL_TO_CHOICE[label], add_special_tokens=False)[0]
    positions = (inputs["input_ids"][0] == target_id).nonzero(as_tuple=False).flatten().tolist()
    positions = [position for position in positions if position >= inputs["input_ids"].shape[1] - 8]
    if not positions:
        raise RuntimeError(f"cannot locate terminal label token for {row['question_id']}")
    label_position = positions[-1]
    labels = torch.full_like(inputs["input_ids"], -100)
    labels[0, label_position] = target_id
    return inputs, labels, label_position


def forward_one(model, processor, row: dict, label: str, choice_ids: dict[str, int]):
    inputs, labels, position = prepare_example(processor, row, label, model.device)
    outputs = model(**inputs, use_cache=False)
    next_logits = outputs.logits[0, position - 1].float()
    ce = F.cross_entropy(next_logits[[choice_ids["supported"], choice_ids["contradicted"]]],
                         torch.tensor(0 if label == "supported" else 1, device=model.device))
    preference = next_logits[choice_ids["supported"]] - next_logits[choice_ids["contradicted"]]
    del inputs, labels, outputs, next_logits
    return ce, preference


def evaluate(model, processor, pairs: list[dict[str, dict]], choice_ids: dict[str, int]) -> dict:
    rows = []
    model.eval()
    with torch.inference_mode():
        for pair_id, pair in pairs:
            _, positive = forward_one(model, processor, pair["supported"], "supported", choice_ids)
            _, negative = forward_one(model, processor, pair["contradicted"], "contradicted", choice_ids)
            rows.append({"source_question_id": pair_id, "positive_preference": float(positive.cpu()),
                         "negative_preference": float(negative.cpu()),
                         "pair_correct": bool(positive > negative)})
    model.train()
    return {
        "pairs": len(rows),
        "pair_accuracy": sum(row["pair_correct"] for row in rows) / max(len(rows), 1),
        "mean_margin": sum(row["positive_preference"] - row["negative_preference"] for row in rows) / max(len(rows), 1),
        "rows": rows,
    }


def main() -> None:
    if ARGS.output_dir.exists() and any(ARGS.output_dir.iterdir()) and not ARGS.overwrite:
        raise RuntimeError(f"output directory is not empty: {ARGS.output_dir}")
    ARGS.output_dir.mkdir(parents=True, exist_ok=True)
    inputs = load_jsonl(ARGS.input_jsonl)
    labels = {str(row["question_id"]): row for row in load_jsonl(ARGS.labels_jsonl)}
    grouped: dict[str, dict[str, dict]] = {}
    for row in inputs:
        label_row = labels[str(row["question_id"])]
        label = str(label_row["label_name"])
        grouped.setdefault(str(row["source_question_id"]), {})[label] = row
    complete = [(key, value) for key, value in grouped.items() if set(value) == set(LABEL_TO_CHOICE)]
    complete.sort(key=lambda item: stable_key(item[0]))
    if ARGS.max_pairs > 0:
        complete = complete[:ARGS.max_pairs]
    if len(complete) < 5:
        raise RuntimeError("fewer than five complete pairs")
    pairs_by_video: dict[str, list] = {}
    for item in complete:
        pairs_by_video.setdefault(str(item[1]["supported"]["video_id"]), []).append(item)
    validation_target = max(2, round(len(complete) * 0.2))
    validation_videos: set[str] = set()
    validation_size = 0
    for video_id in sorted(pairs_by_video, key=stable_key):
        if validation_size >= validation_target:
            break
        validation_videos.add(video_id)
        validation_size += len(pairs_by_video[video_id])
    validation = [item for item in complete if item[1]["supported"]["video_id"] in validation_videos]
    training = [item for item in complete if item[1]["supported"]["video_id"] not in validation_videos]
    if not validation:
        raise RuntimeError("video-level validation split is empty")
    train_videos = {row["supported"]["video_id"] for _, row in training}
    overlap = train_videos & validation_videos
    if overlap:
        raise RuntimeError(f"video-level split overlap: {sorted(overlap)}")

    config = {
        "schema": "adsqa_realclaim_lora_verifier_config_v1",
        "mode": ARGS.mode,
        "model_dir": str(ARGS.model_dir),
        "model_is_clean_qwen25_instruct": ARGS.model_dir.name == "Qwen2.5-VL-7B-Instruct",
        "input_sha256": sha256_file(ARGS.input_jsonl),
        "labels_sha256": sha256_file(ARGS.labels_jsonl),
        "selected_pairs": len(complete),
        "train_pairs": len(training),
        "validation_pairs": len(validation),
        "video_overlap": [],
        "views": ARGS.views,
        "epochs": ARGS.epochs,
        "learning_rate": ARGS.learning_rate,
        "margin": ARGS.margin if ARGS.mode == "pairwise" else None,
        "seed": ARGS.seed,
        "not_human_gold": True,
        "vision_encoder_frozen": True,
        "lora_target": "language q_proj/v_proj only; visual adapters frozen",
    }
    dump_json(ARGS.output_dir / "config.json", config)
    dump_jsonl(ARGS.output_dir / "train_pairs.jsonl", [{"source_question_id": key, "video_id": row["supported"]["video_id"]} for key, row in training])
    dump_jsonl(ARGS.output_dir / "validation_pairs.jsonl", [{"source_question_id": key, "video_id": row["supported"]["video_id"]} for key, row in validation])

    random.seed(ARGS.seed)
    torch.manual_seed(ARGS.seed)
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir, min_pixels=224 * 224, max_pixels=448 * 448, trust_remote_code=True
    )
    choice_ids = resolve_choice_ids(processor.tokenizer)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        ARGS.model_dir, torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map={"": 0}
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    lora = LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(model, lora)
    for name, parameter in model.named_parameters():
        if "visual" in name:
            parameter.requires_grad = False
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    total = sum(parameter.numel() for parameter in model.parameters())
    config["trainable_parameters"] = trainable
    config["total_parameters"] = total
    config["trainable_fraction"] = trainable / total
    dump_json(ARGS.output_dir / "config.json", config)
    model.train()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=ARGS.learning_rate)

    history = []
    started = time.time()
    for epoch in range(ARGS.epochs):
        shuffled = list(training)
        random.Random(ARGS.seed + epoch).shuffle(shuffled)
        for step, (pair_id, pair) in enumerate(shuffled, 1):
            optimizer.zero_grad(set_to_none=True)
            positive_ce, positive_pref = forward_one(model, processor, pair["supported"], "supported", choice_ids)
            negative_ce, negative_pref = forward_one(model, processor, pair["contradicted"], "contradicted", choice_ids)
            ce = (positive_ce + negative_ce) / 2
            ranking = F.relu(torch.tensor(ARGS.margin, device=model.device) - positive_pref + negative_pref)
            loss = ce if ARGS.mode == "classification" else ce + 0.5 * ranking
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            row = {
                "epoch": epoch + 1, "step": step, "pair_id": pair_id,
                "loss": float(loss.detach().cpu()), "ce": float(ce.detach().cpu()),
                "ranking": float(ranking.detach().cpu()), "elapsed_sec": time.time() - started,
                "gpu_peak_memory_mb": torch.cuda.max_memory_allocated() / 1024 / 1024,
            }
            history.append(row)
            print(json.dumps(row), flush=True)
    model.save_pretrained(ARGS.output_dir / "adapter")
    evaluation = evaluate(model, processor, validation, choice_ids)
    evaluation["elapsed_sec"] = time.time() - started
    evaluation["gpu_peak_memory_mb"] = torch.cuda.max_memory_allocated() / 1024 / 1024
    dump_jsonl(ARGS.output_dir / "history.jsonl", history)
    dump_json(ARGS.output_dir / "validation.json", evaluation)
    dump_json(ARGS.output_dir / "complete.json", {"complete": True, "mode": ARGS.mode, **evaluation})
    print(json.dumps({"complete": True, **evaluation}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
