#!/usr/bin/env python3
"""Train a confidence-weighted RealClaim LoRA verifier with video-level holdout."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import time


def args_parser() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--gpu-id", required=True)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--init-adapter", type=Path)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--max-rows", type=int, default=-1)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--views", type=int, default=8)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--soft-labels", action="store_true")
    p.add_argument("--seed", type=int, default=2026072102)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


ARGS = args_parser()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = ARGS.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import cv2  # noqa: E402
from PIL import Image  # noqa: E402
from peft import LoraConfig, PeftModel, get_peft_model  # noqa: E402
from qwen_vl_utils import process_vision_info  # noqa: E402
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def stable(value: str) -> str:
    return hashlib.sha256(f"{ARGS.seed}:{value}".encode()).hexdigest()


def choose_views(indices: list[int]) -> list[int]:
    positions = [round(i * (len(indices) - 1) / (ARGS.views - 1)) for i in range(ARGS.views)]
    return [int(indices[position]) for position in positions]


def frames(video_path: str, indices: list[int]) -> list[Image.Image]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")
    output = []
    try:
        for index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"cannot decode frame {index}")
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image.thumbnail((448, 448), Image.Resampling.LANCZOS)
            output.append(image)
    finally:
        cap.release()
    return output


def prompt(row: dict) -> str:
    return (
        "Determine whether the atomic claim is supported or not supported by the supplied "
        "advertisement frames and transcript. Use only supplied evidence. "
        "Answer A for supported or B for not supported. Do not explain.\n"
        f"Question: {row['question']}\nAtomic claim: {row['claim']}\n"
        f"Transcript: {str(row.get('asr_excerpt', ''))[:1600]}\nAnswer:"
    )


def prepare(processor, row: dict, target: str, device: torch.device):
    images = frames(row["video_path"], choose_views(row["selected_frame_indices"]))
    content = [{"type": "image", "image": image} for image in images]
    content.append({"type": "text", "text": prompt(row)})
    messages = [{"role": "user", "content": content}, {"role": "assistant", "content": target}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    image_inputs, video_inputs = process_vision_info(messages)
    values = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")
    values = {key: value.to(device) for key, value in values.items()}
    target_id = processor.tokenizer.encode(target, add_special_tokens=False)[0]
    positions = (values["input_ids"][0] == target_id).nonzero(as_tuple=False).flatten().tolist()
    positions = [position for position in positions if position >= values["input_ids"].shape[1] - 8]
    if not positions:
        raise RuntimeError(f"terminal target token missing for {row['question_id']}")
    return values, positions[-1]


def score(model, processor, row: dict, truth: int, token_ids: list[int], target_support: float | None = None):
    values, position = prepare(processor, row, "A" if truth else "B", model.device)
    output = model(**values, use_cache=False)
    logits = output.logits[0, position - 1].float()[token_ids]
    if target_support is None:
        loss = F.cross_entropy(logits.unsqueeze(0), torch.tensor([0 if truth else 1], device=model.device))
    else:
        target = torch.tensor([target_support, 1.0 - target_support], device=model.device)
        loss = -(target * F.log_softmax(logits, dim=0)).sum()
    probability = torch.softmax(logits, dim=0)[0]
    return loss, probability


def metrics(rows: list[dict]) -> dict:
    y = [row["label"] for row in rows]
    scores = [row["probability"] for row in rows]
    return {
        "rows": len(rows), "positives": sum(y), "negatives": len(y) - sum(y),
        "auroc": roc_auc_score(y, scores), "auprc": average_precision_score(y, scores),
        "balanced_accuracy_05": balanced_accuracy_score(y, [int(value >= 0.5) for value in scores]),
    }


def main() -> None:
    ARGS.output_dir.mkdir(parents=True, exist_ok=True)
    if any(ARGS.output_dir.iterdir()) and not ARGS.overwrite:
        raise RuntimeError(f"output directory not empty: {ARGS.output_dir}")
    inputs = load_jsonl(ARGS.inputs)
    label_map = {row["question_id"]: row for row in load_jsonl(ARGS.labels)}
    rows = [(row, label_map[row["question_id"]]) for row in inputs]
    rows.sort(key=lambda pair: stable(pair[0]["question_id"]))
    if ARGS.max_rows > 0:
        rows = rows[:ARGS.max_rows]
    by_video: dict[str, list] = {}
    for pair in rows:
        by_video.setdefault(pair[0]["video_id"], []).append(pair)
    target = max(10, round(len(rows) * 0.2))
    validation_videos, count = set(), 0
    for video in sorted(by_video, key=stable):
        if count >= target:
            break
        validation_videos.add(video)
        count += len(by_video[video])
    train = [pair for pair in rows if pair[0]["video_id"] not in validation_videos]
    validation = [pair for pair in rows if pair[0]["video_id"] in validation_videos]
    counts = Counter(int(label["binary_label"]) for _, label in train)
    class_weight = {key: len(train) / (2 * value) for key, value in counts.items()}
    config = {
        "schema": "adsqa_realclaim_weak_lora_config_v1", "rows": len(rows),
        "train_rows": len(train), "validation_rows": len(validation),
        "train_videos": len({row["video_id"] for row, _ in train}),
        "validation_videos": len(validation_videos), "video_overlap": [],
        "init_adapter": str(ARGS.init_adapter) if ARGS.init_adapter else None,
        "epochs": ARGS.epochs, "views": ARGS.views, "learning_rate": ARGS.learning_rate,
        "class_weight": class_weight, "confidence_weighted": True,
        "soft_labels": ARGS.soft_labels,
        "soft_label_policy": "p(observed_label)=annotation_confidence" if ARGS.soft_labels else None,
        "not_human_gold": True,
    }
    dump_json(ARGS.output_dir / "config.json", config)
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir, min_pixels=224 * 224, max_pixels=448 * 448, trust_remote_code=True
    )
    token_ids = [processor.tokenizer.encode(value, add_special_tokens=False)[0] for value in ("A", "B")]
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        ARGS.model_dir, torch_dtype=torch.bfloat16, attn_implementation="sdpa", device_map={"": 0}
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    if ARGS.init_adapter:
        model = PeftModel.from_pretrained(model, ARGS.init_adapter, is_trainable=True)
    else:
        model = get_peft_model(model, LoraConfig(
            r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj"],
        ))
    for name, parameter in model.named_parameters():
        if "visual" in name:
            parameter.requires_grad = False
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=ARGS.learning_rate)
    history, started = [], time.time()
    model.train()
    for epoch in range(ARGS.epochs):
        shuffled = list(train)
        random.Random(ARGS.seed + epoch).shuffle(shuffled)
        for step, (row, label) in enumerate(shuffled, 1):
            optimizer.zero_grad(set_to_none=True)
            truth = int(label["binary_label"])
            confidence = max(0.0, min(1.0, float(label["annotation_confidence"])))
            target_support = (confidence if truth else 1.0 - confidence) if ARGS.soft_labels else None
            loss, probability = score(model, processor, row, truth, token_ids, target_support)
            sample_weight = max(0.3, float(label["annotation_confidence"])) * class_weight[truth]
            weighted = loss * sample_weight
            weighted.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            item = {"epoch": epoch + 1, "step": step, "loss": float(loss.detach().cpu()),
                    "weighted_loss": float(weighted.detach().cpu()), "elapsed_sec": time.time() - started}
            history.append(item)
            print(json.dumps(item), flush=True)
    model.save_pretrained(ARGS.output_dir / "adapter")
    model.eval()
    scored = []
    with torch.inference_mode():
        for row, label in validation:
            truth = int(label["binary_label"])
            _, probability = score(model, processor, row, truth, token_ids)
            scored.append({"question_id": row["question_id"], "video_id": row["video_id"],
                           "label": truth, "probability": float(probability.cpu()),
                           "claim_type": row["claim_type"], "primary_type": row["primary_type"]})
    result = {"complete": True, **metrics(scored), "elapsed_sec": time.time() - started,
              "gpu_peak_memory_mb": torch.cuda.max_memory_allocated() / 1024 / 1024}
    dump_jsonl(ARGS.output_dir / "history.jsonl", history)
    dump_jsonl(ARGS.output_dir / "validation_scores.jsonl", scored)
    dump_json(ARGS.output_dir / "complete.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
