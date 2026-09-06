#!/usr/bin/env python3
"""Run clean Qwen3-VL on frozen E-VAds SigLIP-MMR8 evidence."""

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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.common.qwen_video_budget import (  # noqa: E402
    prepare_qwen_video_inputs,
)


METHOD = "SigLIPMMR64_8_lambda070"
FORBIDDEN_KEYS = {
    "answer",
    "reference_answer",
    "ground_truth",
    "reward",
    "label",
    "evidence_state",
    "pairwise_target",
}


class ProtocolError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["0", "1", "2", "3", "4", "5"])
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--method", default=METHOD)
    parser.add_argument(
        "--frame-field",
        default="siglip_mmr8_frame_indices",
        choices=["siglip_mmr8_frame_indices", "uniform8_frame_indices"],
    )
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("/data1/qky/Model/Qwen3Vl-8B"),
    )
    parser.add_argument("--unified-size", type=int, default=512)
    parser.add_argument("--max-visual-tokens", type=int, default=1024)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def ensure_idle_gpu(gpu_id: str) -> list[str]:
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
    matching = [
        row for row in rows if row.split(",", 1)[0].strip() == gpu_id
    ]
    if len(matching) != 1 or active:
        raise ProtocolError(f"GPU{gpu_id} is not idle: {active}")
    return matching


def load_questions(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "question_id",
        "video",
        "question",
        "official_prompt_text",
        "fold",
        "answer_free",
    }
    if not isinstance(rows, list) or not rows:
        raise ProtocolError("question shard must be a non-empty list")
    if any(not required.issubset(row) for row in rows):
        raise ProtocolError("question shard misses required fields")
    if any(FORBIDDEN_KEYS & set(row) for row in rows):
        raise ProtocolError("question shard contains supervision fields")
    if any(row.get("answer_free") is not True for row in rows):
        raise ProtocolError("question shard is not answer-free")
    return rows


def load_manifest(
    path: Path,
    frame_field: str,
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        qid = str(row["question_id"])
        if qid in records:
            raise ProtocolError(f"duplicate manifest question: {qid}")
        if row.get("answer_or_outcome_fields_used") is not False:
            raise ProtocolError("manifest is not answer-free")
        indices = [int(value) for value in row[frame_field]]
        if (
            len(indices) != 8
            or len(set(indices)) != 8
            or indices != sorted(indices)
        ):
            raise ProtocolError(f"invalid MMR8 indices for {qid}")
        row["_selected_frame_indices"] = indices
        records[qid] = row
    return records


def decode_frames(
    video_path: Path,
    indices: list[int],
    size: int,
) -> tuple[list[Any], list[dict[str, Any]]]:
    from decord import VideoReader, cpu
    from PIL import Image

    reader = VideoReader(str(video_path), ctx=cpu(0))
    total = len(reader)
    if total <= 0 or any(index < 0 or index >= total for index in indices):
        raise ProtocolError(f"frame selection exceeds video: {video_path}")
    fps = float(reader.get_avg_fps() or 0.0)
    frames = [
        Image.fromarray(reader[index].asnumpy()).convert("RGB").resize(
            (size, size), Image.Resampling.BICUBIC
        )
        for index in indices
    ]
    plan = [
        {
            "input_index": rank,
            "view_type": "siglip_mmr_selected_global",
            "source_frame_index": index,
            "source_timestamp_sec": float(index / fps) if fps > 0 else None,
            "source_total_frame_count": total,
        }
        for rank, index in enumerate(indices)
    ]
    return frames, plan


def main() -> None:
    args = parse_args()
    if (
        args.unified_size != 512
        or args.max_visual_tokens != 1024
        or args.max_new_tokens != 512
    ):
        raise ProtocolError("frozen A0 protocol requires 8x512, 1024 tokens")
    question_path = args.questions.resolve()
    manifest_path = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    questions = load_questions(question_path)
    manifest = load_manifest(manifest_path, args.frame_field)
    missing = {
        str(row["question_id"]) for row in questions
    } - set(manifest)
    if missing:
        raise ProtocolError(f"manifest misses questions: {sorted(missing)[:5]}")
    gpu_snapshot = ensure_idle_gpu(args.gpu_id)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": "evads_qwen3_siglip_mmr8_inference_v1",
        "method": args.method,
        "frame_field": args.frame_field,
        "model_family": "qwen3_vl",
        "gpu_id": args.gpu_id,
        "gpu_snapshot_before_load": gpu_snapshot,
        "model_dir": str(args.model_dir.resolve()),
        "model_config_sha256": sha256_file(args.model_dir / "config.json"),
        "question_file": str(question_path),
        "question_file_sha256": sha256_file(question_path),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "question_count": len(questions),
        "views": 8,
        "unified_size": args.unified_size,
        "max_visual_tokens": args.max_visual_tokens,
        "max_new_tokens": args.max_new_tokens,
        "official_evads_prompt_used": True,
        "metadata_ocr_asr_given_to_a0": False,
        "groundtruth_file_read": False,
        "testset_answers_read": False,
        "secondary_frame_sampling_disabled": True,
    }
    dump_json(output_dir / "run_config.json", config)
    processor = AutoProcessor.from_pretrained(
        args.model_dir,
        min_pixels=args.unified_size * args.unified_size,
        max_pixels=args.unified_size * args.unified_size,
        trust_remote_code=True,
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map={"": 0},
    )
    if str(model.config.model_type) != "qwen3_vl":
        raise ProtocolError(f"expected qwen3_vl, got {model.config.model_type}")
    model.eval()

    stats = {"processed": 0, "skipped_existing": 0, "errors": 0}
    errors_path = output_dir / "logs" / "errors.jsonl"
    for item in questions:
        qid = str(item["question_id"])
        item_dir = output_dir / qid
        prediction_path = item_dir / "prediction.json"
        evidence_path = item_dir / "evidence.json"
        if prediction_path.exists() and evidence_path.exists() and not args.overwrite:
            stats["skipped_existing"] += 1
            continue
        started = time.time()
        try:
            plan = manifest[qid]
            video_id = str(item["video"])
            if str(plan["video_id"]) != video_id:
                raise ProtocolError(f"manifest video mismatch for {qid}")
            frames, visual_plan = decode_frames(
                args.video_root.resolve() / f"{video_id}.mp4",
                plan["_selected_frame_indices"],
                args.unified_size,
            )
            prompt = str(item["official_prompt_text"]).replace(
                "<video>", ""
            ).strip()
            messages = [{
                "role": "user",
                "content": [
                    {"type": "video", "video": frames, "fps": 1.0},
                    {"type": "text", "text": prompt},
                ],
            }]
            text = processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs, trace = prepare_qwen_video_inputs(
                processor=processor,
                text_input=text,
                frames=frames,
                device=model.device,
                expected_view_count=8,
                max_post_merge_visual_tokens=1024,
                metadata_fps=1.0,
                frame_indices=plan["_selected_frame_indices"],
                require_exact_frame_count=True,
            )
            with torch.inference_mode():
                generated = model.generate(
                    **inputs,
                    do_sample=False,
                    max_new_tokens=args.max_new_tokens,
                )
            trimmed = [
                output[len(source) :]
                for source, output in zip(inputs.input_ids, generated)
            ]
            prediction = processor.batch_decode(
                trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()
            item_dir.mkdir(parents=True, exist_ok=True)
            dump_json(prediction_path, {
                "question_id": qid,
                "video_id": video_id,
                "method": args.method,
                "prediction": prediction,
                "model_path": str(args.model_dir.resolve()),
            })
            dump_json(evidence_path, {
                "question_id": qid,
                "video_id": video_id,
                "question": str(item["question"]),
                "input_image_count": len(frames),
                "visual_plan": visual_plan,
                "processor_trace": trace,
                "latency_seconds": time.time() - started,
                "metadata_ocr_asr_given_to_a0": False,
            })
            stats["processed"] += 1
        except Exception as error:
            append_jsonl(errors_path, {
                "question_id": qid,
                "error": repr(error),
                "traceback": traceback.format_exc(),
            })
            stats["errors"] += 1
        finally:
            gc.collect()
            torch.cuda.empty_cache()
    config["stats"] = stats
    dump_json(output_dir / "run_summary.json", config)
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
