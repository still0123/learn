#!/usr/bin/env python3
"""Run fixed-input generic or evidence-structured reflection on audited Raw32 drafts."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--variant", choices=["generic", "structured", "conservative"], required=True)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--asr-file", required=True)
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-dir", default="/data1/qky/Model/Qwen3Vl-8B")
    parser.add_argument("--project-root", default="/data1/rmx/projectb/AdsQA-main")
    parser.add_argument("--video-root", default="/data1/rmx/projectb/AdsQA-main/data/videos")
    parser.add_argument("--frames-fallback-root", default="/data1/rmx/projectb/AdsQA-main/data/frames_8")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--start-idx", type=int, default=0)
    parser.add_argument("--end-idx", type=int, default=-1)
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


args = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
PROJECT_ROOT = Path(args.project_root)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.evidence_reflection.reflection_protocol import (  # noqa: E402
    PROTOCOL_VERSION,
    build_reflection_prompt,
    extract_answer_section,
    parse_reflection_output,
    sha256_text,
    visual_input_sha256,
    visual_plan_sha256,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def import_fair_module():
    saved_argv = list(sys.argv)
    sys.argv = [
        "inference_fair_baselines_v1.py",
        "--gpu_id", str(args.gpu_id),
        "--fair_method", "raw_uniform",
        "--question_file", str(args.question_file),
        "--groundtruth_file", str(Path(args.project_root) / "data" / "counterfactual_dev100_v1" / "groundtruth.json"),
        "--asr_file", str(args.asr_file),
        "--output_dir", str(args.output_dir),
        "--visual_view_budget", "32",
        "--max_post_merge_visual_tokens", "12000",
        "--unified_size", "896",
        "--oversample_count", "32",
        "--disable_reflection",
    ]
    try:
        from evaluation.methods.fair_protocol import inference_fair_baselines_v1 as fair
    finally:
        sys.argv = saved_argv
    fair.args.fair_method = "raw_uniform"
    fair.args.visual_view_budget = 32
    fair.args.max_post_merge_visual_tokens = 12000
    fair.args.oversample_count = 32
    fair.args.disable_reflection = True
    return fair


def setup_logging(output_dir: Path) -> logging.Logger:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"evidence_reflection_{args.variant}_{args.gpu_id}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_dir / f"inference_gpu{args.gpu_id}.log", encoding="utf-8")
    stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    stream.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(stream)
    return logger


def load_freeze(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if payload.get("schema") != "adsqa_evidence_reflection_dev100_freeze_v1" or len(records) != 100:
        raise RuntimeError("invalid or incomplete reflection freeze manifest")
    return {str(row["question_id"]): row for row in records}


def generate_with_trace(fair, model, processor, frames, prompt: str) -> tuple[str, dict[str, Any]]:
    import torch

    message = [{"role": "user", "content": [
        {"type": "video", "video": frames, "fps": 1.0},
        {"type": "text", "text": prompt},
    ]}]
    text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
    inputs, processor_trace = fair.prepare_qwen_video_inputs(
        processor=processor,
        text_input=text_input,
        frames=frames,
        device=model.device,
        expected_view_count=32,
        max_post_merge_visual_tokens=12000,
        metadata_fps=1.0,
        require_exact_frame_count=True,
    )
    with torch.inference_mode():
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=args.max_new_tokens)
    trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated)]
    decoded = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    output = decoded[0].strip() if decoded else ""
    processor_trace = {
        **processor_trace,
        "input_token_count": int(inputs.input_ids.shape[1]),
        "output_token_count": int(trimmed[0].shape[0]) if trimmed else 0,
        "max_new_tokens": int(args.max_new_tokens),
    }
    return output, processor_trace


def resolve_video(fair, video_root: str, video_id: str, fallback_root: str) -> str:
    return fair.resolve_video_path(video_root, video_id, fallback_root)


def main() -> None:
    output_dir = Path(args.output_dir)
    logger = setup_logging(output_dir)
    freeze_path = Path(args.freeze_manifest)
    freeze_hash = sha256_file(freeze_path)
    freeze = load_freeze(freeze_path)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    asr_data = json.loads(Path(args.asr_file).read_text(encoding="utf-8"))
    if len(questions) != 100:
        raise RuntimeError("reflection runner requires exactly Dev100")
    selected = [(idx, item) for idx, item in enumerate(questions)
                if args.start_idx <= idx < (len(questions) if args.end_idx < 0 else args.end_idx)
                and idx % args.num_shards == args.shard_id]
    for idx, item in selected:
        if str(item["question_id"]) not in freeze:
            raise RuntimeError(f"question missing from freeze manifest: {item['question_id']}")

    config = {
        "schema": "adsqa_evidence_reflection_run_v1",
        "protocol": PROTOCOL_VERSION,
        "variant": args.variant,
        "gpu_id": str(args.gpu_id),
        "model_dir": args.model_dir,
        "question_file": str(Path(args.question_file)),
        "question_file_sha256": sha256_file(Path(args.question_file)),
        "asr_file": str(Path(args.asr_file)),
        "asr_file_sha256": sha256_file(Path(args.asr_file)),
        "freeze_manifest": str(freeze_path),
        "freeze_manifest_sha256": freeze_hash,
        "visual_view_budget": 32,
        "max_post_merge_visual_tokens": 12000,
        "same_raw32_input": True,
        "secondary_frame_sampling_disabled": True,
        "rag_enabled": False,
        "new_visual_sampling": False,
        "groundtruth_loaded_by_inference": False,
        "selected_count": len(selected),
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    dump_json(output_dir / "run_config.json", config)
    if args.dry_run:
        dump_json(output_dir / "dry_run_preview.json", [
            {"global_idx": idx, "question_id": str(item["question_id"]), "video": item.get("video")}
            for idx, item in selected[:10]
        ])
        logger.info("Dry run complete: %d items", len(selected))
        return

    fair = import_fair_module()
    import torch
    from transformers import AutoModelForVision2Seq, AutoProcessor

    logger.info("Loading Qwen3-VL from %s on GPU %s", args.model_dir, args.gpu_id)
    model = AutoModelForVision2Seq.from_pretrained(
        args.model_dir, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )
    processor = AutoProcessor.from_pretrained(
        args.model_dir, min_pixels=256 * 256, max_pixels=1280 * 1280, trust_remote_code=True
    )
    stats = {"processed": 0, "skipped_existing": 0, "errors": 0, "parsed": 0, "fallback_keep": 0}
    errors_path = output_dir / "logs" / f"errors_gpu{args.gpu_id}.jsonl"
    for global_idx, item in selected:
        qid = str(item["question_id"])
        q_dir = output_dir / qid
        pred_path = q_dir / "prediction.json"
        trace_path = q_dir / "reflection.json"
        if pred_path.exists() and trace_path.exists() and not args.overwrite:
            stats["skipped_existing"] += 1
            continue
        started = time.time()
        try:
            frozen = freeze[qid]
            baseline_evidence = json.loads(Path(frozen["evidence_path"]).read_text(encoding="utf-8"))
            video_id = str(item.get("video", item.get("video_id", "")))
            video_path = resolve_video(fair, args.video_root, video_id, args.frames_fallback_root)
            raw_frames, raw_meta = fair.load_frames_oversampled(video_path, 32, 0)
            if len(raw_frames) != 32:
                raise RuntimeError(f"expected 32 raw frames, got {len(raw_frames)}")
            asr_text = str(asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, "")) or "")
            selected_frames, selected_meta, input_frames, crop_metas, visual_plan, route, fair_trace = fair.build_fair_visual_sequence(
                None, raw_frames, raw_meta, item, asr_text, None
            )
            current_plan_hash = visual_plan_sha256(visual_plan)
            frozen_plan_hash = visual_plan_sha256(baseline_evidence.get("visual_plan", []))
            if current_plan_hash != frozen_plan_hash:
                raise RuntimeError(f"Raw32 visual plan drift for {qid}: {current_plan_hash} != {frozen_plan_hash}")
            if len(input_frames) != 32:
                raise RuntimeError("reflection input view budget drift")
            input_hash = visual_input_sha256(input_frames)
            draft = str(frozen["draft_prediction"])
            prompt = build_reflection_prompt(args.variant, str(item["question"]), asr_text, draft)
            raw_output, processor_trace = generate_with_trace(fair, model, processor, input_frames, prompt)
            parsed = parse_reflection_output(args.variant, raw_output, draft)
            draft_answer = extract_answer_section(draft).strip()
            parsed_answer = str(parsed.get("final_answer", "")).strip()
            allow_revision = (
                parsed.get("parse_status") != "unparsed"
                and str(parsed.get("decision", "keep")).lower() == "revise"
                and bool(parsed_answer)
            )
            final_answer = parsed_answer if allow_revision else draft_answer
            if not allow_revision:
                stats["fallback_keep"] += 1
            if parsed.get("parse_status") != "unparsed":
                stats["parsed"] += 1
            prediction = {
                "question_id": qid,
                "prediction": final_answer,
                "draft_prediction": draft,
                "pipeline": f"Raw32_plus_{args.variant}_evidence_reflection_Qwen3VL",
                "reflection_status": parsed.get("parse_status"),
                "reflection_decision": parsed.get("decision"),
                "reflection_variant": args.variant,
                "score": "",
            }
            evidence = {
                "schema": "adsqa_evidence_reflection_item_v1",
                "question_id": qid,
                "global_idx": global_idx,
                "video_id": video_id,
                "video_path": video_path,
                "question": str(item["question"]),
                "asr_excerpt": asr_text[:1000],
                "visual_plan": visual_plan,
                "selected_frames": selected_meta,
                "fair_protocol": fair_trace,
                "processor_trace": processor_trace,
                "visual_input_sha256": input_hash,
                "visual_plan_sha256": current_plan_hash,
                "frozen_baseline_prediction_sha256": frozen["prediction_sha256"],
                "frozen_baseline_evidence_sha256": frozen["evidence_sha256"],
                "draft_answer": draft,
                "reflection_prompt": prompt,
                "reflection_prompt_sha256": sha256_text(prompt),
                "reflection_raw_output": raw_output,
                "reflection_parsed": parsed,
                "effective_final_answer": final_answer,
                "effective_policy": {
                    "name": "keep_on_non_revise_v1",
                    "allow_revision": allow_revision,
                    "status": "revised" if allow_revision else "kept_draft",
                },
                "new_visual_sampling": False,
                "rag_enabled": False,
                "groundtruth_loaded_by_inference": False,
                "latency_seconds": time.time() - started,
            }
            dump_json(pred_path, prediction)
            dump_json(trace_path, evidence)
            stats["processed"] += 1
            if stats["processed"] % 5 == 0:
                logger.info("Progress: %s", stats)
        except Exception as exc:
            stats["errors"] += 1
            logger.exception("Inference failed qid=%s", qid)
            append_jsonl(errors_path, {
                "question_id": qid,
                "global_idx": global_idx,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            })
        finally:
            try:
                torch.cuda.empty_cache()
                gc.collect()
            except Exception:
                pass
    config["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    config["stats"] = stats
    dump_json(output_dir / f"run_summary_gpu{args.gpu_id}.json", config)
    logger.info("Done: %s", stats)


if __name__ == "__main__":
    main()
