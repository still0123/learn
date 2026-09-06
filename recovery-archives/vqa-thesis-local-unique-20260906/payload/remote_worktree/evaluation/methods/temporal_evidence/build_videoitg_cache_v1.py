#!/usr/bin/env python3
"""Build AdsQA 64-candidate VideoITG frame-ranking caches offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline VideoITG temporal cache builder")
    parser.add_argument("--gpu_id", required=True)
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=-1)
    parser.add_argument("--candidate_count", type=int, default=64)
    parser.add_argument("--top_k", type=int, default=32)
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--video_root", required=True)
    parser.add_argument("--model_path", default="nvidia/VideoITG-8B")
    parser.add_argument(
        "--vision_tower_path",
        default="/data1/rmx/projectb/models/siglip-so400m-patch14-384",
    )
    parser.add_argument(
        "--videoitg_source",
        default="/data1/rmx/projectb/AdsQA-main/external/VideoITG_official_main",
    )
    parser.add_argument(
        "--videoitg_revision",
        default="50a60a822c0e362bfd8747c45ba34e66e9c9d650",
    )
    parser.add_argument("--output_jsonl", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


args = parse_args()
if args.candidate_count < args.top_k or args.top_k <= 0:
    raise ValueError("require candidate_count >= top_k > 0")
if args.num_shards <= 0 or not 0 <= args.shard_id < args.num_shards:
    raise ValueError("invalid shard configuration")
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)

sys.path.insert(0, str(Path(args.videoitg_source)))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch
from decord import VideoReader, cpu
from eagle.constants import DEFAULT_IMAGE_TOKEN, IMAGE_TOKEN_INDEX
from eagle.mm_utils import get_model_name_from_path, tokenizer_image_token
from eagle.model.builder import load_pretrained_model
from transformers import AutoConfig

from temporal_cache import CANDIDATE_POLICY, SCHEMA_VERSION, nested_uniform_candidate_indices, question_sha256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_inventory(model_path: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(model_path.glob("*")):
        if path.is_file():
            files.append(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return files


def resolve_video(video_root: str, video_id: str) -> Path:
    candidates = [
        Path(video_root) / f"{video_id}.mp4",
        Path(video_root) / video_id,
        Path(video_root) / f"{video_id}.webm",
        Path(video_root) / f"{video_id}.mov",
    ]
    return next((path for path in candidates if path.is_file()), candidates[0])


def pad_sequence(tokenizer, input_ids):
    if tokenizer.padding_side == "left":
        input_ids = [torch.flip(ids, [0]) for ids in input_ids]
    padded = torch.nn.utils.rnn.pad_sequence(
        input_ids,
        batch_first=True,
        padding_value=(
            tokenizer.pad_token_id
            if tokenizer.pad_token_id is not None
            else tokenizer.eos_token_id
        ),
    )
    return torch.flip(padded, [1]) if tokenizer.padding_side == "left" else padded


def existing_question_ids(path: Path) -> set[str]:
    if not path.exists() or args.overwrite:
        return set()
    result = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                result.add(str(json.loads(line)["question_id"]))
    return result


def score_candidates(
    model: Any,
    tokenizer: Any,
    image_processor: Any,
    question: str,
    video_path: Path,
) -> tuple[list[int], list[float], list[int], list[int]]:
    reader = VideoReader(str(video_path), ctx=cpu(0), num_threads=4)
    total_frames = len(reader)
    if total_frames <= 0:
        raise RuntimeError(f"empty video: {video_path}")
    source_indices = nested_uniform_candidate_indices(total_frames, args.candidate_count, args.top_k)
    pixels = image_processor.preprocess(
        reader.get_batch(source_indices).asnumpy(), return_tensors="pt"
    )["pixel_values"].half().to("cuda")
    prompt = DEFAULT_IMAGE_TOKEN + str(question) + "\n"
    input_ids = tokenizer_image_token(
        prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt"
    )
    input_ids = pad_sequence(tokenizer, [input_ids]).to("cuda")
    pad_token_id = (
        tokenizer.pad_token_id
        if tokenizer.pad_token_id is not None
        else tokenizer.eos_token_id
    )
    attention_mask = input_ids.ne(pad_token_id).to("cuda")
    with torch.inference_mode():
        response = model(input_ids, attention_mask=attention_mask, images=[pixels])
        logits = response.logits[0].sigmoid().view(-1)
    if logits.numel() != args.candidate_count:
        raise RuntimeError(
            f"VideoITG score count mismatch: {logits.numel()} != {args.candidate_count}"
        )
    scores = [float(value) for value in logits.detach().cpu().tolist()]
    ranked = sorted(range(args.candidate_count), key=lambda rank: (-scores[rank], rank))
    selected = sorted(ranked[: args.top_k])
    return source_indices, scores, ranked, selected


def main() -> None:
    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite and output_path.exists():
        output_path.unlink()
    completed = existing_question_ids(output_path)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    end_idx = len(questions) if args.end_idx < 0 else min(args.end_idx, len(questions))
    selected_items = [
        (index, item)
        for index, item in enumerate(questions[args.start_idx:end_idx], start=args.start_idx)
        if index % args.num_shards == args.shard_id
    ]

    source_infer = Path(args.videoitg_source) / "infer.py"
    builder_path = Path(__file__).resolve()
    model_path = Path(args.model_path)
    vision_tower_path = Path(args.vision_tower_path)
    if not vision_tower_path.is_dir():
        raise FileNotFoundError(f"missing local vision tower: {vision_tower_path}")
    error_path = output_path.parent / f"errors_shard{args.shard_id}.jsonl"
    summary_path = output_path.parent / f"run_summary_shard{args.shard_id}.json"
    if args.overwrite and error_path.exists():
        error_path.unlink()
    run_metadata = {
        "schema_version": SCHEMA_VERSION,
        "selector": "videoitg_8b",
        "candidate_count": args.candidate_count,
        "top_k": args.top_k,
        "model_path": args.model_path,
        "videoitg_source": args.videoitg_source,
        "videoitg_revision": args.videoitg_revision,
        "attention_backend": "flash_attention_2",
        "official_infer_sha256": sha256_file(source_infer),
        "cache_builder": str(builder_path),
        "cache_builder_sha256": sha256_file(builder_path),
        "model_inventory": model_inventory(model_path),
        "vision_tower_path": str(vision_tower_path.resolve()),
        "vision_tower_inventory": model_inventory(vision_tower_path),
        "question_file": args.question_file,
        "question_file_sha256": sha256_file(Path(args.question_file)),
        "shard_id": args.shard_id,
        "num_shards": args.num_shards,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (output_path.parent / f"run_config_shard{args.shard_id}.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    model_config = AutoConfig.from_pretrained(args.model_path, local_files_only=True)
    model_config.mm_vision_tower = str(vision_tower_path.resolve())
    tokenizer, model, image_processor, _ = load_pretrained_model(
        args.model_path,
        None,
        get_model_name_from_path(args.model_path),
        device_map="cuda:0",
        use_flash_attn=True,
        config=model_config,
        local_files_only=True,
    )
    model.half().eval().to("cuda")

    succeeded = 0
    skipped = 0
    failed = 0
    with output_path.open("a", encoding="utf-8") as handle, error_path.open(
        "a", encoding="utf-8"
    ) as error_handle:
        for global_idx, item in selected_items:
            question_id = str(item["question_id"])
            if question_id in completed:
                skipped += 1
                continue
            video_id = str(item.get("video", item.get("video_id", question_id.split("_")[0])))
            video_path = resolve_video(args.video_root, video_id)
            try:
                source_indices, scores, ranked, selected = score_candidates(
                    model,
                    tokenizer,
                    image_processor,
                    str(item.get("question", "")),
                    video_path,
                )
            except Exception as exc:
                failed += 1
                error_record = {
                    "global_idx": global_idx,
                    "question_id": question_id,
                    "video_id": video_id,
                    "video_path": str(video_path),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                error_handle.write(json.dumps(error_record, ensure_ascii=False) + "\n")
                error_handle.flush()
                print(f"[{global_idx}] {question_id}: ERROR {exc}", flush=True)
                continue
            record = {
                "schema_version": SCHEMA_VERSION,
                "selector": "videoitg_8b",
                "question_id": question_id,
                "question_sha256": question_sha256(str(item.get("question", ""))),
                "global_idx": global_idx,
                "video_id": video_id,
                "video_path": str(video_path),
                "candidate_count": args.candidate_count,
                "candidate_sampling_policy": CANDIDATE_POLICY,
                "candidate_frame_indices": source_indices,
                "candidate_scores": scores,
                "ranked_candidate_ranks": ranked,
                "selected_candidate_ranks": selected,
                "selected_frame_indices": [source_indices[rank] for rank in selected],
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            succeeded += 1
            print(f"[{global_idx}] {question_id}: selected={selected}", flush=True)

    summary = {
        **run_metadata,
        "end_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "requested_items": len(selected_items),
        "succeeded_this_run": succeeded,
        "skipped_existing": skipped,
        "failed_this_run": failed,
        "output_jsonl": str(output_path),
        "output_sha256": sha256_file(output_path) if output_path.exists() else None,
        "error_jsonl": str(error_path),
        "error_sha256": sha256_file(error_path) if error_path.exists() else None,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if failed:
        raise RuntimeError(f"VideoITG cache completed with {failed} failed item(s)")


if __name__ == "__main__":
    main()
