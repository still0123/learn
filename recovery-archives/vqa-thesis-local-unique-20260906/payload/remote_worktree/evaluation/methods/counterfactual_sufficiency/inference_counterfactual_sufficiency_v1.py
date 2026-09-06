#!/usr/bin/env python3
"""Fixed-budget counterfactual evidence sufficiency inference for AdsQA.

For one frozen evidence construction method, this entrypoint writes two aligned
prediction groups: the initial answer (the method-only ablation) and a single
counterfactual-gated rescue answer (method + innovation-2). Every Qwen call sees
exactly 32 visual views. The trace makes the additional verification passes and
their latency explicit instead of treating them as free computation.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AdsQA counterfactual sufficiency inference V1")
    parser.add_argument("--gpu_id", required=True)
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=-1)
    parser.add_argument("--project_root", default="/data1/rmx/projectb/AdsQA-main")
    parser.add_argument("--model_dir", default="/data1/qky/Model/Qwen3Vl-8B")
    parser.add_argument("--clip_path", default="/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14")
    parser.add_argument("--video_root", default="/data1/rmx/projectb/AdsQA-main/data/videos")
    parser.add_argument("--frames_fallback_root", default="/data1/rmx/projectb/AdsQA-main/data/frames_8")
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--groundtruth_file", required=True)
    parser.add_argument("--asr_file", required=True)
    parser.add_argument("--evidence_method", choices=["raw_uniform", "innovation1_mmr32"], required=True)
    parser.add_argument("--temporal_index_cache", default="")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--visual_view_budget", type=int, default=32)
    parser.add_argument("--max_post_merge_visual_tokens", type=int, default=12000)
    parser.add_argument("--unified_size", type=int, default=896)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--destroy_count", type=int, default=4)
    parser.add_argument("--local_count", type=int, default=8)
    parser.add_argument("--support_threshold", type=float, default=-6.00)
    parser.add_argument("--sensitivity_margin", type=float, default=0.02)
    parser.add_argument("--switch_margin", type=float, default=0.05)
    parser.add_argument(
        "--force_rescue_all",
        action="store_true",
        help="Generate the frozen rescue candidate for every item; selection remains a separate postprocess.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    return parser.parse_args()


args = parse_args()
if args.gpu_id not in {"2", "3", "4", "5"}:
    raise ValueError("gpu_id must be one of 2, 3, 4, or 5")
if args.evidence_method == "innovation1_mmr32" and not args.temporal_index_cache:
    raise ValueError("innovation1_mmr32 requires --temporal_index_cache")
if args.visual_view_budget != 32:
    raise ValueError("V1 is intentionally frozen to 32 visual views")
if not 0 < args.destroy_count < args.visual_view_budget:
    raise ValueError("destroy_count must be in (0, visual_view_budget)")
if not 0 < args.local_count < args.visual_view_budget:
    raise ValueError("local_count must be in (0, visual_view_budget)")
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
PROJECT_ROOT = Path(args.project_root).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def configure_fair_module():
    """Import the frozen fair protocol without running its main function."""
    saved_argv = list(sys.argv)
    fair_method = "raw_uniform" if args.evidence_method == "raw_uniform" else "external_temporal"
    sys.argv = [
        "inference_fair_baselines_v1.py", "--gpu_id", args.gpu_id,
        "--fair_method", fair_method,
        "--question_file", args.question_file,
        "--groundtruth_file", args.groundtruth_file,
        "--asr_file", args.asr_file,
        "--output_dir", args.output_dir,
        "--visual_view_budget", str(args.visual_view_budget),
        "--max_post_merge_visual_tokens", str(args.max_post_merge_visual_tokens),
        "--unified_size", str(args.unified_size),
        "--disable_reflection",
    ]
    if fair_method == "external_temporal":
        sys.argv.extend(["--temporal_index_cache", args.temporal_index_cache, "--oversample_count", "64"])
    else:
        sys.argv.extend(["--oversample_count", "32"])
    try:
        from evaluation.methods.fair_protocol import inference_fair_baselines_v1 as fair
    finally:
        sys.argv = saved_argv
    fair.args.fair_method = fair_method
    fair.args.temporal_index_cache = args.temporal_index_cache
    fair.args.visual_view_budget = args.visual_view_budget
    fair.args.max_post_merge_visual_tokens = args.max_post_merge_visual_tokens
    fair.args.unified_size = args.unified_size
    fair.args.disable_reflection = True
    fair.args.rag_mode = "none"
    fair.args.oversample_count = 64 if fair_method == "external_temporal" else 32
    return fair


FAIR = configure_fair_module()
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

from evaluation.methods.common.adsqa_prompt import build_adsqa_answer_prompt  # noqa: E402
from evaluation.methods.counterfactual_sufficiency.counterfactual import (  # noqa: E402
    build_rescue_sequence,
    categorize_question,
    choose_corrected_answer,
    make_visual_counterfactual,
    question_stem,
    select_asr_excerpt,
    should_rescue,
)
from evaluation.methods.temporal_evidence.temporal_cache import load_temporal_index_cache  # noqa: E402


LOGGER = logging.getLogger("adsqa_counterfactual_sufficiency_v1")


def setup_logging(output_dir: Path) -> None:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"inference_gpu{args.gpu_id}_shard{args.shard_id}of{args.num_shards}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(path, mode="a", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        force=True,
    )


def load_groundtruth_map(path: str) -> Dict[str, str]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(row["question_id"]): str(row.get("answer", "")) for row in rows}


def score_frame_relevance(visual_processor, frames, question: str, asr_text: str) -> List[float]:
    """CLIP relevance is used only to decide the minimal perturbation/rescue slots."""
    processed = [visual_processor._safe_preprocess(frame) for frame in frames]
    if any(item is None for item in processed):
        return [float(index) for index in range(len(frames))]
    with torch.inference_mode():
        embeddings = F.normalize(visual_processor.vision(torch.stack(processed).to("cuda")).image_embeds, dim=-1)
        question_embedding = visual_processor._encode_text(question)
        asr_embedding = visual_processor._encode_text(asr_text or "video evidence")
        scores = torch.matmul(embeddings, question_embedding.T).view(-1) * 0.70
        if asr_embedding is not None:
            scores = scores + torch.matmul(embeddings, asr_embedding.T).view(-1) * 0.30
    return [float(value) for value in scores.detach().cpu().tolist()]


def candidate_mean_logprob(model, processor, frames, prompt: str, candidate_answer: str) -> Tuple[float, Dict[str, Any]]:
    """Score a candidate answer by its evidence-conditioned mean token log-likelihood.

    Unlike a Yes/No self-critique, this is computed from the frozen answer model's
    actual conditional distribution and cannot collapse into a prompt-induced Yes
    prior. Scores are only compared among the paired evidence variants of one item.
    """
    message = [{"role": "user", "content": [{"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt}]}]
    text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
    inputs, processor_trace = FAIR.prepare_qwen_video_inputs(
        processor=processor,
        text_input=text_input,
        frames=frames,
        device=model.device,
        expected_view_count=args.visual_view_budget,
        max_post_merge_visual_tokens=args.max_post_merge_visual_tokens,
        metadata_fps=1.0,
        require_exact_frame_count=True,
    )
    answer_ids = processor.tokenizer.encode(str(candidate_answer).strip(), add_special_tokens=False)
    if not answer_ids:
        raise ValueError("cannot score an empty candidate answer")
    answer_tensor = torch.tensor([answer_ids], dtype=inputs.input_ids.dtype, device=inputs.input_ids.device)
    base_length = int(inputs.input_ids.shape[1])
    inputs["input_ids"] = torch.cat([inputs.input_ids, answer_tensor], dim=1)
    inputs["attention_mask"] = torch.cat(
        [inputs.attention_mask, torch.ones_like(answer_tensor, dtype=inputs.attention_mask.dtype)], dim=1
    )
    with torch.inference_mode():
        logits = model(**inputs, use_cache=False).logits[0, base_length - 1: base_length - 1 + len(answer_ids)].float()
        token_logprobs = torch.log_softmax(logits, dim=-1).gather(
            1, torch.tensor(answer_ids, device=logits.device).unsqueeze(1)
        ).squeeze(1)
        score = float(token_logprobs.mean().item())
    return score, {
        "scoring": "qwen_candidate_mean_logprob_v1",
        "answer_token_count": len(answer_ids),
        "answer_token_logprob_sum": float(token_logprobs.sum().item()),
        "processor_trace": processor_trace,
    }


def prediction_record(qid: str, answer: str, gt_map: Dict[str, str], pipeline: str) -> Dict[str, Any]:
    return {
        "question_id": qid,
        "prediction": answer,
        "ground_truth": gt_map.get(qid, "N/A"),
        "initial_reasoning": answer,
        "pipeline": pipeline,
        "reflection_status": "disabled_counterfactual_sufficiency_v1",
        "rag_mode": "none",
        "score": "",
    }


def main() -> None:
    output_dir = Path(args.output_dir)
    setup_logging(output_dir)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    asr_data = json.loads(Path(args.asr_file).read_text(encoding="utf-8"))
    gt_map = load_groundtruth_map(args.groundtruth_file)
    end_idx = len(questions) if args.end_idx < 0 else min(args.end_idx, len(questions))
    items = [
        (index, item)
        for index, item in enumerate(questions[args.start_idx:end_idx], start=args.start_idx)
        if index % args.num_shards == args.shard_id
    ]
    temporal_cache = None
    if args.evidence_method == "innovation1_mmr32":
        temporal_cache = load_temporal_index_cache(args.temporal_index_cache)
        if len(temporal_cache) < len(questions):
            raise RuntimeError("temporal cache does not cover the complete question file")
    script_path = Path(__file__).resolve()
    config = {
        **vars(args),
        "script_sha256": sha256_file(script_path),
        "fair_protocol_script": str(Path(FAIR.__file__).resolve()),
        "fair_protocol_script_sha256": sha256_file(Path(FAIR.__file__).resolve()),
        "protocol": "counterfactual_sufficiency_fixed32_v1",
        "initial_group": args.evidence_method,
        "final_group": f"{args.evidence_method}_plus_counterfactual2",
        "fair_method": "raw_uniform" if args.evidence_method == "raw_uniform" else "external_temporal",
        "answer_prompt_template_sha256": FAIR.adsqa_answer_prompt_sha256(),
        "answer_prompt_version": FAIR.ADSQA_ANSWER_PROMPT_VERSION,
        "secondary_frame_sampling_disabled": True,
        "rag_enabled": False,
        "reflection_enabled": False,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    dump_json(output_dir / "run_config.json", config)
    if args.dry_run:
        dump_json(output_dir / "dry_run_preview.json", [{"global_idx": index, "question_id": str(item["question_id"]), "video": item.get("video")} for index, item in items[:10]])
        LOGGER.info("Dry run complete for %d shard items", len(items))
        return

    visual_processor = FAIR.S23VisualProcessor(device="cuda", clip_path=args.clip_path, cfg=FAIR.args)
    if not visual_processor.valid:
        raise RuntimeError(f"CLIP evidence processor unavailable: {visual_processor.error}")
    model = FAIR.AutoModelForVision2Seq.from_pretrained(
        args.model_dir, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )
    processor = FAIR.AutoProcessor.from_pretrained(
        args.model_dir, min_pixels=256 * 256, max_pixels=1280 * 1280, trust_remote_code=True
    )
    stats = {"processed": 0, "skipped_existing": 0, "errors": 0, "rescued": 0, "switched": 0}
    errors_path = output_dir / "logs" / f"errors_gpu{args.gpu_id}_shard{args.shard_id}.jsonl"
    for global_idx, item in items:
        started = time.time()
        qid = str(item["question_id"])
        initial_path = output_dir / "initial" / qid / "prediction.json"
        final_path = output_dir / "final" / qid / "prediction.json"
        trace_path = output_dir / "trace" / qid / "evidence.json"
        if initial_path.exists() and final_path.exists() and trace_path.exists() and not args.overwrite:
            stats["skipped_existing"] += 1
            continue
        try:
            video_id = str(item.get("video", item.get("video_id", qid.split("_")[0])))
            video_path = FAIR.resolve_video_path(args.video_root, video_id, args.frames_fallback_root)
            raw_frames, raw_meta = FAIR.load_frames_oversampled(
                video_path,
                FAIR.args.oversample_count,
                args.visual_view_budget if args.evidence_method == "innovation1_mmr32" else 0,
            )
            if len(raw_frames) != FAIR.args.oversample_count:
                raise RuntimeError(f"expected {FAIR.args.oversample_count} raw frames, got {len(raw_frames)}")
            asr_text = str(asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, "")) or "")
            selected_frames, selected_meta, input_frames, crop_metas, visual_plan, route, fair_trace = FAIR.build_fair_visual_sequence(
                None,
                raw_frames,
                raw_meta,
                item,
                asr_text,
                temporal_cache,
            )
            if len(input_frames) != args.visual_view_budget:
                raise RuntimeError("initial visual budget drift")
            question = question_stem(str(item.get("question", "")))
            category = categorize_question(question)
            prompt = build_adsqa_answer_prompt(question, asr_text, "")
            initial_answer, initial_processor_trace = FAIR.generate_response(
                model, processor, input_frames, prompt, args.max_new_tokens
            )
            relevance_scores = score_frame_relevance(visual_processor, input_frames, question, asr_text)
            support_plus, support_plus_trace = candidate_mean_logprob(
                model, processor, input_frames, prompt, initial_answer
            )
            if category == "speech_audio":
                counterfactual_frames = list(input_frames)
                counterfactual_asr = ""
                counterfactual_trace = {
                    "perturbation": "asr_withheld_for_audio_question_v1",
                    "destroyed_input_indices": [],
                    "view_count_before": len(input_frames),
                    "view_count_after": len(counterfactual_frames),
                }
            else:
                counterfactual_frames, counterfactual_trace = make_visual_counterfactual(
                    input_frames, relevance_scores, destroy_count=args.destroy_count
                )
                counterfactual_asr = asr_text
            counterfactual_prompt = build_adsqa_answer_prompt(question, counterfactual_asr, "")
            support_minus, support_minus_trace = candidate_mean_logprob(
                model, processor, counterfactual_frames, counterfactual_prompt, initial_answer
            )
            rescue_needed, rescue_reasons = should_rescue(
                support_plus, support_minus, args.support_threshold, args.sensitivity_margin
            )
            if args.force_rescue_all:
                rescue_needed = True
                rescue_reasons = [*rescue_reasons, "forced_candidate_pair_generation"]
            final_answer = initial_answer
            rescue_trace: Dict[str, Any] = {"triggered": False, "reasons": rescue_reasons}
            final_processor_trace = initial_processor_trace
            if rescue_needed:
                def cropper(frame, source_index):
                    crop, crop_meta = visual_processor.smart_crop(frame, question, select_asr_excerpt(asr_text, question))
                    return FAIR.smart_resize(crop, args.unified_size), crop_meta

                rescue_frames, rescue_plan = build_rescue_sequence(
                    input_frames, relevance_scores, cropper, local_count=args.local_count
                )
                rescue_asr = select_asr_excerpt(asr_text, question)
                rescue_prompt = build_adsqa_answer_prompt(question, rescue_asr, "")
                rescue_answer, rescue_processor_trace = FAIR.generate_response(
                    model, processor, rescue_frames, rescue_prompt, args.max_new_tokens
                )
                initial_support_on_rescue, initial_rescue_trace = candidate_mean_logprob(
                    model, processor, rescue_frames, rescue_prompt, initial_answer
                )
                rescue_support_on_rescue, rescue_support_trace = candidate_mean_logprob(
                    model, processor, rescue_frames, rescue_prompt, rescue_answer
                )
                final_answer, decision_trace = choose_corrected_answer(
                    initial_answer,
                    rescue_answer,
                    initial_support_on_rescue,
                    rescue_support_on_rescue,
                    switch_margin=args.switch_margin,
                )
                final_processor_trace = rescue_processor_trace if decision_trace["switched"] else initial_processor_trace
                rescue_trace = {
                    "triggered": True,
                    "reasons": rescue_reasons,
                    "rescue_asr": rescue_asr,
                    "rescue_plan": rescue_plan,
                    "rescue_answer": rescue_answer,
                    "initial_support_on_rescue": initial_support_on_rescue,
                    "rescue_support_on_rescue": rescue_support_on_rescue,
                    "initial_support_trace": initial_rescue_trace,
                    "rescue_support_trace": rescue_support_trace,
                    "decision": decision_trace,
                    "rescue_processor_trace": rescue_processor_trace,
                }
                stats["rescued"] += 1
                stats["switched"] += int(decision_trace["switched"])
            initial_record = prediction_record(qid, initial_answer, gt_map, f"{args.evidence_method}_Qwen3VL")
            final_record = prediction_record(qid, final_answer, gt_map, f"{args.evidence_method}_plus_counterfactual2_Qwen3VL")
            dump_json(initial_path, initial_record)
            dump_json(final_path, final_record)
            base_evidence = {
                "question_id": qid,
                "global_idx": global_idx,
                "video_id": video_id,
                "video_path": video_path,
                "question": question,
                "asr_excerpt": asr_text[:1000],
                "raw_sample_count": len(raw_frames),
                "selected_count": len(selected_frames),
                "input_image_count": len(input_frames),
                "fair_protocol": fair_trace,
                "visual_plan": visual_plan,
                "selected_frames": selected_meta,
                "crop_metas": crop_metas,
                "config_subset": {
                    "evidence_method": args.evidence_method,
                    "visual_view_budget": args.visual_view_budget,
                    "max_post_merge_visual_tokens": args.max_post_merge_visual_tokens,
                    "secondary_frame_sampling_disabled": True,
                },
            }
            dump_json(output_dir / "initial" / qid / "evidence.json", {**base_evidence, "processor_trace": initial_processor_trace})
            final_evidence = {**base_evidence, "processor_trace": final_processor_trace}
            if rescue_trace.get("decision", {}).get("switched"):
                rescue_plan_for_audit = rescue_trace["rescue_plan"]
                final_evidence.update({
                    "input_image_count": args.visual_view_budget,
                    "visual_plan": rescue_plan_for_audit["visual_plan"],
                    "fair_protocol": {
                        **fair_trace,
                        "method": f"{args.evidence_method}_plus_counterfactual2",
                        "global_count": rescue_plan_for_audit["context_count"],
                        "local_count": rescue_plan_for_audit["local_count"],
                        "selection": "counterfactual_gated_fixed_budget_rescue",
                    },
                })
            dump_json(output_dir / "final" / qid / "evidence.json", final_evidence)
            dump_json(trace_path, {
                **base_evidence,
                "initial_answer": initial_answer,
                "final_answer": final_answer,
                "category": category,
                "relevance_scores": relevance_scores,
                "support_plus": support_plus,
                "support_minus": support_minus,
                "support_delta": support_plus - support_minus,
                "support_plus_trace": support_plus_trace,
                "support_minus_trace": support_minus_trace,
                "counterfactual": counterfactual_trace,
                "rescue": rescue_trace,
                "latency_seconds": time.time() - started,
                "qwen_visual_forward_passes": 2 + (3 if rescue_needed else 0),
                "visual_views_per_forward_pass": args.visual_view_budget,
                "note": "The final answer remains 32-view fixed-budget; verification/rescue compute is reported separately.",
            })
            stats["processed"] += 1
            if stats["processed"] % 5 == 0:
                LOGGER.info("Progress %s", stats)
        except Exception as exc:
            stats["errors"] += 1
            LOGGER.exception("Failed qid=%s", qid)
            append_jsonl(errors_path, {"question_id": qid, "global_idx": global_idx, "error": repr(exc), "traceback": traceback.format_exc()})
        finally:
            torch.cuda.empty_cache()
            gc.collect()
    config["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    config["stats"] = stats
    dump_json(output_dir / f"run_summary_gpu{args.gpu_id}_shard{args.shard_id}.json", config)
    LOGGER.info("Done %s", stats)


if __name__ == "__main__":
    main()
