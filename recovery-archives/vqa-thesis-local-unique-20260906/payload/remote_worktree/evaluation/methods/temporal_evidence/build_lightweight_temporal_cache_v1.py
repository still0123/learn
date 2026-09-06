#!/usr/bin/env python3
"""Build AdsQA caches with the lightweight question/ASR/scene/MMR selector."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline lightweight AdsQA temporal selector")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--gpu_id", default="")
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=-1)
    parser.add_argument("--candidate_count", type=int, default=64)
    parser.add_argument("--top_k", type=int, default=32)
    parser.add_argument("--coverage_bins", type=int, default=8)
    parser.add_argument("--question_weight", type=float, default=0.55)
    parser.add_argument("--asr_weight", type=float, default=0.20)
    parser.add_argument("--scene_change_weight", type=float, default=0.15)
    parser.add_argument("--coverage_bonus", type=float, default=0.10)
    parser.add_argument("--duplicate_penalty", type=float, default=0.20)
    parser.add_argument(
        "--selection_policy",
        choices=["mmr32", "conservative_raw24_evidence8_v1"],
        default="mmr32",
    )
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--asr_file", required=True)
    parser.add_argument("--video_root", required=True)
    parser.add_argument("--clip_path", required=True)
    parser.add_argument("--output_jsonl", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


args = parse_args()
if args.candidate_count < args.top_k or args.top_k <= 0:
    raise ValueError("require candidate_count >= top_k > 0")
if args.num_shards <= 0 or not 0 <= args.shard_id < args.num_shards:
    raise ValueError("invalid shard configuration")
if args.device == "cuda" and args.gpu_id not in {"2", "3", "4", "5"}:
    raise ValueError("CUDA runs require --gpu_id 2, 3, 4, or 5")
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
if args.device == "cuda":
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch
import torch.nn.functional as F
from decord import VideoReader, cpu
from PIL import Image
from transformers import (
    CLIPTextModelWithProjection,
    CLIPTokenizer,
    CLIPVisionModelWithProjection,
)
from torchvision.transforms import Normalize, ToTensor

from lightweight_selector import (
    SelectorWeights,
    select_conservative_raw_evidence,
    select_temporal_evidence,
)
from temporal_cache import CANDIDATE_POLICY, SCHEMA_VERSION, nested_uniform_candidate_indices, question_sha256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_video(video_root: str, video_id: str) -> Path:
    candidates = [
        Path(video_root) / f"{video_id}.mp4",
        Path(video_root) / video_id,
        Path(video_root) / f"{video_id}.webm",
        Path(video_root) / f"{video_id}.mov",
    ]
    return next((path for path in candidates if path.is_file()), candidates[0])


def existing_question_ids(path: Path) -> set[str]:
    if not path.exists() or args.overwrite:
        return set()
    with path.open("r", encoding="utf-8") as handle:
        return {
            str(json.loads(line)["question_id"])
            for line in handle
            if line.strip()
        }


def map_source_indices_to_candidate_ranks(
    candidate_indices: list[int], source_indices: list[int]
) -> list[int]:
    available: dict[int, list[int]] = {}
    for rank, source_index in enumerate(candidate_indices):
        available.setdefault(int(source_index), []).append(rank)
    mapped = []
    for source_index in source_indices:
        ranks = available.get(int(source_index), [])
        if not ranks:
            raise ValueError(f"Raw source frame {source_index} missing from nested candidates")
        mapped.append(ranks.pop(0))
    return mapped


class ClipTemporalEncoder:
    def __init__(self, model_path: str, device: str):
        self.device = torch.device(device)
        kwargs = {"local_files_only": True, "ignore_mismatched_sizes": True}
        self.vision = CLIPVisionModelWithProjection.from_pretrained(model_path, **kwargs).to(self.device).eval()
        self.text = CLIPTextModelWithProjection.from_pretrained(model_path, **kwargs).to(self.device).eval()
        self.tokenizer = CLIPTokenizer.from_pretrained(model_path, local_files_only=True)
        self.to_tensor = ToTensor()
        self.normalize = Normalize(
            (0.48145466, 0.4578275, 0.40821073),
            (0.26862954, 0.26130258, 0.27577711),
        )

    def encode_text(self, text: str) -> torch.Tensor:
        tokens = self.tokenizer(
            [str(text)[:300] or "video evidence"],
            padding=True,
            truncation=True,
            max_length=77,
            return_tensors="pt",
        ).to(self.device)
        with torch.inference_mode():
            return F.normalize(self.text(**tokens).text_embeds, dim=-1)

    def encode_frames(self, frames: list[Image.Image]) -> torch.Tensor:
        tensors = [
            self.normalize(self.to_tensor(frame.convert("RGB").resize((224, 224), Image.BICUBIC)))
            for frame in frames
        ]
        with torch.inference_mode():
            return F.normalize(self.vision(torch.stack(tensors).to(self.device)).image_embeds, dim=-1)


def main() -> None:
    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite and output_path.exists():
        output_path.unlink()
    completed = existing_question_ids(output_path)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    asr_data = json.loads(Path(args.asr_file).read_text(encoding="utf-8"))
    end_idx = len(questions) if args.end_idx < 0 else min(args.end_idx, len(questions))
    selected_items = [
        (index, item)
        for index, item in enumerate(questions[args.start_idx:end_idx], start=args.start_idx)
        if index % args.num_shards == args.shard_id
    ]
    weights = SelectorWeights(
        question=args.question_weight,
        asr=args.asr_weight,
        scene_change=args.scene_change_weight,
        coverage_bonus=args.coverage_bonus,
        duplicate_penalty=args.duplicate_penalty,
    )
    encoder = ClipTemporalEncoder(args.clip_path, args.device)
    run_config = {
        **vars(args),
        "schema_version": SCHEMA_VERSION,
        "selector": (
            "ads_temporal_conservative24e8_v1"
            if args.selection_policy == "conservative_raw24_evidence8_v1"
            else "ads_temporal_mmr_v1"
        ),
        "script_sha256": sha256_file(Path(__file__)),
        "selector_module_sha256": sha256_file(Path(__file__).with_name("lightweight_selector.py")),
        "question_file_sha256": sha256_file(Path(args.question_file)),
        "asr_file_sha256": sha256_file(Path(args.asr_file)),
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (output_path.parent / f"run_config_shard{args.shard_id}.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with output_path.open("a", encoding="utf-8") as handle:
        for global_idx, item in selected_items:
            question_id = str(item["question_id"])
            if question_id in completed:
                continue
            video_id = str(item.get("video", item.get("video_id", question_id.split("_")[0])))
            video_path = resolve_video(args.video_root, video_id)
            reader = VideoReader(str(video_path), ctx=cpu(0), num_threads=4)
            source_indices = nested_uniform_candidate_indices(
                len(reader), args.candidate_count, args.top_k
            )
            frames = [
                Image.fromarray(frame).convert("RGB")
                for frame in reader.get_batch(source_indices).asnumpy()
            ]
            question = str(item.get("question", ""))
            asr_text = str(asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, "")) or "")
            frame_embeddings = encoder.encode_frames(frames)
            question_embedding = encoder.encode_text(question)
            asr_embedding = encoder.encode_text(asr_text or "video evidence")
            question_scores = (frame_embeddings @ question_embedding.T).view(-1)
            asr_scores = (frame_embeddings @ asr_embedding.T).view(-1)
            question_asr_reliability = float(
                torch.clamp(question_embedding @ asr_embedding.T, min=0.0, max=1.0).item()
            ) if asr_text else 0.0
            selector_kwargs = dict(
                top_k=args.top_k,
                coverage_bins=args.coverage_bins,
                question_asr_reliability=question_asr_reliability,
                weights=weights,
            )
            if args.selection_policy == "conservative_raw24_evidence8_v1":
                raw_sources = np.linspace(0, len(reader) - 1, args.top_k, dtype=int).tolist()
                raw_ranks = map_source_indices_to_candidate_ranks(source_indices, raw_sources)
                chosen, trace = select_conservative_raw_evidence(
                    frame_embeddings.float().cpu().numpy(),
                    question_scores.float().cpu().numpy(),
                    asr_scores.float().cpu().numpy(),
                    raw_candidate_ranks=raw_ranks,
                    **selector_kwargs,
                )
            else:
                chosen, trace = select_temporal_evidence(
                    frame_embeddings.float().cpu().numpy(),
                    question_scores.float().cpu().numpy(),
                    asr_scores.float().cpu().numpy(),
                    **selector_kwargs,
                )
            selected_ranked = trace["ranked_selected_candidate_ranks"]
            unselected = sorted(
                set(range(args.candidate_count)) - set(chosen),
                key=lambda rank: (-trace["base_score"][rank], rank),
            )
            record = {
                "schema_version": SCHEMA_VERSION,
                "selector": run_config["selector"],
                "question_id": question_id,
                "question_sha256": question_sha256(question),
                "global_idx": global_idx,
                "video_id": video_id,
                "video_path": str(video_path),
                "candidate_count": args.candidate_count,
                "candidate_sampling_policy": CANDIDATE_POLICY,
                "candidate_frame_indices": source_indices,
                "candidate_scores": trace["base_score"],
                "ranked_candidate_ranks": selected_ranked + unselected,
                "selected_candidate_ranks": chosen,
                "selected_frame_indices": [source_indices[rank] for rank in chosen],
                "selector_trace": trace,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            print(f"[{global_idx}] {question_id}: selected={chosen}", flush=True)


if __name__ == "__main__":
    main()
