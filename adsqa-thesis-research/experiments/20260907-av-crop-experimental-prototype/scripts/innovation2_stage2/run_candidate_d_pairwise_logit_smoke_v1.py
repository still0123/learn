#!/usr/bin/env python3
"""Probe continuous frozen-Qwen state likelihoods for candidate-D pairwise ranking."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--gpu-id", type=int, required=True)
    parser.add_argument("--goal-start-epoch", type=int, required=True)
    parser.add_argument(
        "--partition",
        choices=("train_fit", "stage2_dev", "all"),
        default="train_fit",
    )
    parser.add_argument(
        "--pair-limit",
        type=int,
        default=20,
        help="Number of pairs to score; use 0 to score every eligible pair.",
    )
    parser.add_argument("--seed", type=int, default=20260718)
    parser.add_argument("--model-dir", type=Path, default=Path("/data1/qky/Model/Qwen3Vl-8B"))
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--unified-size", type=int, default=896)
    return parser.parse_args()


ARGS = parse_args()
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = str(ARGS.gpu_id)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
sys.modules["torchcodec"] = None
ASR_UNAVAILABLE_PREFIX = "[[ASR_UNAVAILABLE:"
ASR_NOT_DETECTED_PREFIX = "[[ASR_AVAILABLE: no matching aligned speech segment detected"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_int(seed: int, value: str) -> int:
    return int(hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()[:16], 16)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def command_output(command: list[str]) -> str:
    return subprocess.run(command, check=False, text=True, capture_output=True).stdout.strip()


def gpu_snapshot(gpu_id: int) -> dict[str, Any]:
    gpu = command_output(
        [
            "nvidia-smi",
            "-i",
            str(gpu_id),
            "--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    processes = command_output(
        [
            "nvidia-smi",
            "-i",
            str(gpu_id),
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    process_rows = []
    for line in processes.splitlines():
        if not line.strip() or line.strip().lower().startswith("no running"):
            continue
        fields = [field.strip() for field in line.split(",", 2)]
        if len(fields) < 3:
            continue
        owner = command_output(["ps", "-o", "user=", "-p", fields[0]]).strip() or "unknown"
        process_rows.append(
            {
                "pid": int(fields[0]),
                "process_name": fields[1],
                "used_memory_mib": int(fields[2]),
                "owner": owner,
            }
        )
    return {"captured_at_epoch": int(time.time()), "gpu": gpu, "compute_processes": process_rows}


def enforce_gpu_policy() -> dict[str, Any]:
    now = int(time.time())
    window_end = ARGS.goal_start_epoch + 21600
    allowed = {1, 2, 4, 5} if now < window_end else {4, 5}
    if ARGS.gpu_id not in allowed:
        raise RuntimeError(
            f"GPU{ARGS.gpu_id} is outside the dynamic policy at {now}; allowed={sorted(allowed)}"
        )
    snapshot = gpu_snapshot(ARGS.gpu_id)
    if snapshot["compute_processes"]:
        raise RuntimeError(f"GPU{ARGS.gpu_id} has active compute processes: {snapshot['compute_processes']}")
    return {
        "goal_start_epoch": ARGS.goal_start_epoch,
        "gpu_window_end_epoch": window_end,
        "launch_epoch": now,
        "allowed_gpu_ids": sorted(allowed),
        "pre_launch_snapshot": snapshot,
    }


def select_pairs(
    pairs: list[dict[str, Any]],
    limit: int,
    seed: int,
    partition: str,
) -> list[dict[str, Any]]:
    by_modality: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        if partition == "all" or pair.get("stage2_partition") == partition:
            by_modality[str(pair.get("required_modality", "visual"))].append(pair)
    eligible_count = sum(len(values) for values in by_modality.values())
    target = eligible_count if limit == 0 else limit
    if target <= 0:
        raise RuntimeError(f"no eligible pairs for partition={partition}")
    for values in by_modality.values():
        values.sort(key=lambda row: stable_int(seed, str(row["pair_id"])))
    selected: list[dict[str, Any]] = []
    while len(selected) < target:
        progressed = False
        for modality in sorted(by_modality):
            if not by_modality[modality]:
                continue
            selected.append(by_modality[modality].pop(0))
            progressed = True
            if len(selected) >= target:
                break
        if not progressed:
            break
    if len(selected) != target:
        raise RuntimeError(
            f"unable to select {target} partition={partition} pairs, got {len(selected)}"
        )
    return selected


def mosaic_region(image: Any, side: int, box_norm: Any) -> Any:
    from PIL import Image

    width, height = image.size
    if not isinstance(box_norm, list) or len(box_norm) != 4:
        box_norm = [0.0, 0.0, 1.0, 1.0]
    left = max(0, min(width - 1, int(float(box_norm[0]) * width)))
    top = max(0, min(height - 1, int(float(box_norm[1]) * height)))
    right = max(left + 1, min(width, int(float(box_norm[2]) * width)))
    bottom = max(top + 1, min(height, int(float(box_norm[3]) * height)))
    box = (left, top, right, bottom)
    patch = image.crop(box)
    low = patch.resize((side, side), Image.Resampling.BILINEAR)
    pixelated = low.resize(patch.size, Image.Resampling.NEAREST)
    changed = image.copy()
    changed.paste(pixelated, box)
    return changed


def decode_frames(video_path: str, frame_indices: list[int], visual_operation: Any) -> tuple[list[Any], dict[str, Any]]:
    from decord import VideoReader, cpu
    from PIL import Image

    reader = VideoReader(video_path, ctx=cpu(0))
    total_frames = len(reader)
    if len(frame_indices) != 32 or len(set(frame_indices)) != 32:
        raise RuntimeError(f"invalid model frame plan: {frame_indices}")
    if min(frame_indices) < 0 or max(frame_indices) >= total_frames:
        raise RuntimeError(f"frame plan outside video range 0..{total_frames - 1}: {frame_indices}")
    frames = [Image.fromarray(frame).convert("RGB") for frame in reader.get_batch(frame_indices).asnumpy()]
    applied = {"operation": "none", "applied": False, "affected_positions": []}
    if isinstance(visual_operation, dict) and visual_operation.get("operation") == "same_area_mosaic":
        positions = [int(position) for position in visual_operation.get("mosaic_positions", [])]
        if not positions or any(position < 0 or position >= len(frames) for position in positions):
            raise RuntimeError(f"invalid mosaic positions: {positions}")
        side = int(visual_operation.get("mosaic_side", 14))
        boxes = visual_operation.get("mosaic_boxes_norm", [])
        for index, position in enumerate(positions):
            box_norm = boxes[index] if index < len(boxes) else [0.0, 0.0, 1.0, 1.0]
            frames[position] = mosaic_region(frames[position], side, box_norm)
        applied = {
            "operation": "same_area_mosaic",
            "applied": True,
            "affected_positions": positions,
            "affected_frame_indices": [frame_indices[position] for position in positions],
            "mosaic_side": side,
            "mosaic_boxes_norm": boxes,
        }
    frames = [
        frame.resize((ARGS.unified_size, ARGS.unified_size), Image.Resampling.BICUBIC)
        for frame in frames
    ]
    return frames, {
        "source_total_frames": total_frames,
        "decoded_frame_indices": frame_indices,
        "visual_intervention": applied,
        "unified_frame_size": [ARGS.unified_size, ARGS.unified_size],
    }


def build_prompt(
    question: str,
    claim: str,
    asr_excerpt: str,
    required_modality: str,
) -> str:
    if required_modality == "asr":
        if asr_excerpt.startswith(ASR_UNAVAILABLE_PREFIX):
            evidence_rule = (
                "The ASR modality is explicitly unavailable because extraction failed. Ignore "
                "all video frames and select state code C."
            )
        elif asr_excerpt.startswith(ASR_NOT_DETECTED_PREFIX):
            evidence_rule = (
                "The ASR modality is available but the aligned target speech segment was not "
                "detected. Ignore all video frames and select state code B unless the "
                "claim is directly contradicted by the supplied ASR state."
            )
        else:
            evidence_rule = (
                "For this ASR claim, score only the supplied ASR excerpt. Ignore all video-frame "
                "content even when it appears relevant. Select code A only for a direct "
                "verbatim match; otherwise select B or D."
            )
    elif required_modality in {"visual", "ocr"}:
        evidence_rule = (
            "For this visual claim, score only the supplied video frames. The ASR excerpt is "
            "withheld from the decision and must not be inferred from. If the fact is not visible "
            "in this current 32-frame evidence view, select code B; do not claim it is absent "
            "from the entire video."
        )
    elif required_modality == "joint":
        evidence_rule = (
            "For this joint claim, require both the supplied video frames and the supplied ASR "
            "excerpt. Select code A only when both modalities are needed and present."
        )
    else:
        raise RuntimeError(f"unsupported required modality: {required_modality}")
    return (
        "You are a strict multimodal evidence verifier. Use only the provided video frames and "
        "the permitted ASR excerpt. Determine whether the atomic claim is supported, contradicted, "
        "or insufficiently supported. Do not use outside knowledge, campaign knowledge, or "
        "unprovided modality evidence. "
        f"{evidence_rule} Select exactly one state code as the next token:\n"
        "A = PRESENT and supported\n"
        "B = NOT_DETECTED in the current evidence view\n"
        "C = MODALITY_UNAVAILABLE\n"
        "D = CONTRADICTED\n\n"
        f"Question context (not evidence):\n{question}\n\nAtomic claim:\n{claim}\n\n"
        f"Required modality:\n{required_modality}\n\n"
        f"ASR excerpt available to this decision:\n{asr_excerpt or '[WITHHELD]'}"
    )


def prompt_hash_material() -> str:
    return json.dumps(
        {
            "base": (
                "strict evidence verifier; no outside or campaign knowledge; question is not evidence; "
                "output one next-token state code for continuous likelihood scoring"
            ),
            "modality_policies": {
                "asr": "ASR only; distinguish available, not detected, and unavailable",
                "ocr": "visual frames only; ASR withheld",
                "visual": "visual frames only; ASR withheld",
                "joint": "visual and ASR jointly required",
            },
        },
        sort_keys=True,
    )


def main() -> None:
    gpu_record = enforce_gpu_policy()
    from evaluation.methods.common.qwen_video_budget import prepare_qwen_video_inputs
    from transformers import AutoModelForVision2Seq, AutoProcessor
    import torch

    dataset_root = ARGS.dataset_root
    manifest = json.loads((dataset_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("not_human_gold") is not True:
        raise RuntimeError("candidate-D data must be explicitly not_human_gold=true")
    manifest_audit = manifest.get("audit", {})
    if not manifest_audit.get("passed", False):
        raise RuntimeError("candidate-D data audit did not pass")
    inputs = {row["input_id"]: row for row in read_jsonl(dataset_root / "model_inputs.jsonl")}
    pairs = select_pairs(
        read_jsonl(dataset_root / "pairs.jsonl"),
        ARGS.pair_limit,
        ARGS.seed,
        ARGS.partition,
    )
    label_rows = {row["input_id"]: row for row in read_jsonl(dataset_root / "labels.jsonl")}
    if set(inputs) != set(label_rows):
        raise RuntimeError("model inputs and separately stored labels do not have identical IDs")
    if any(row.get("not_human_gold") is not True for row in label_rows.values()):
        raise RuntimeError("candidate-D labels must be explicitly not_human_gold=true")
    if ARGS.output_root.exists():
        raise RuntimeError(f"refusing to overwrite smoke output: {ARGS.output_root}")
    ARGS.output_root.mkdir(parents=True)
    write_json(ARGS.output_root / "gpu_preflight.json", gpu_record)

    model = AutoModelForVision2Seq.from_pretrained(
        ARGS.model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    processor = AutoProcessor.from_pretrained(
        ARGS.model_dir,
        min_pixels=256 * 256,
        max_pixels=1280 * 1280,
        trust_remote_code=True,
    )
    state_token_ids: dict[str, int] = {}
    for code in ("A", "B", "C", "D"):
        token_ids = processor.tokenizer.encode(code, add_special_tokens=False)
        if len(token_ids) != 1:
            raise RuntimeError(f"state code {code} is not one tokenizer token: {token_ids}")
        state_token_ids[code] = token_ids[0]
    run_config = {
        "schema": "adsqa_candidate_d_pairwise_logit_smoke_v1",
        "partition": ARGS.partition,
        "pair_limit": ARGS.pair_limit,
        "selected_pair_ids": [row["pair_id"] for row in pairs],
        "model_dir": str(ARGS.model_dir),
        "model_config_sha256": sha256_file(ARGS.model_dir / "config.json"),
        "dataset_manifest_sha256": sha256_file(dataset_root / "manifest.json"),
        "model_inputs_sha256": sha256_file(dataset_root / "model_inputs.jsonl"),
        "pairs_sha256": sha256_file(dataset_root / "pairs.jsonl"),
        "labels_sha256": sha256_file(dataset_root / "labels.jsonl"),
        "visual_view_budget": 32,
        "visual_token_budget": 12000,
        "expected_post_merge_visual_tokens": 11664,
        "unified_frame_size": ARGS.unified_size,
        "secondary_frame_sampling_disabled": True,
        "prompt_sha256": hashlib.sha256(
            prompt_hash_material().encode("utf-8")
        ).hexdigest(),
        "evidence_policy": {
            "asr": "asr_only",
            "ocr": "visual_only",
            "visual": "visual_only",
            "joint": "visual_and_asr_conjunctive",
        },
        "continuous_state_policy": {
            "A": "present_supported",
            "B": "not_detected_current_view",
            "C": "modality_unavailable",
            "D": "contradicted",
        },
        "state_token_ids": state_token_ids,
        "not_human_gold": True,
        "started_at_epoch": int(time.time()),
    }
    write_json(ARGS.output_root / "run_config.json", run_config)

    input_results_path = ARGS.output_root / "input_results.jsonl"
    pair_results_path = ARGS.output_root / "pair_results.jsonl"
    protocol_failures: list[dict[str, Any]] = []
    pairwise_correct = 0
    for pair in pairs:
        pair_outputs: dict[str, dict[str, Any]] = {}
        for branch, input_key in (("positive", "positive_input_id"), ("negative", "negative_input_id")):
            input_id = pair[input_key]
            item = inputs[input_id]
            visual_operation = "none" if branch == "positive" else pair["negative_plan"].get("visual_operation")
            frames, frame_trace = decode_frames(item["video_path"], [int(value) for value in item["frame_indices"]], visual_operation)
            active_asr_excerpt = (
                item["asr_excerpt"]
                if item["required_modality"] in {"asr", "joint"}
                else ""
            )
            prompt = build_prompt(
                item["question"],
                item["atomic_claim"],
                active_asr_excerpt,
                item["required_modality"],
            )
            message = [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": frames, "fps": 1.0},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
            start = time.time()
            model_inputs, processor_trace = prepare_qwen_video_inputs(
                processor=processor,
                text_input=text_input,
                frames=frames,
                device=model.device,
                expected_view_count=32,
                max_post_merge_visual_tokens=12000,
                metadata_fps=1.0,
                frame_indices=item["frame_indices"],
                require_exact_frame_count=True,
            )
            with torch.no_grad():
                forward = model(**model_inputs)
            raw_logits = forward.logits[0, -1]
            state_logits = {
                code: float(raw_logits[token_id].detach().float().cpu())
                for code, token_id in state_token_ids.items()
            }
            state_tensor = torch.tensor(
                [state_logits[code] for code in ("A", "B", "C", "D")],
                dtype=torch.float32,
            )
            state_probabilities = {
                code: float(probability)
                for code, probability in zip(
                    ("A", "B", "C", "D"),
                    torch.softmax(state_tensor, dim=0).tolist(),
                )
            }
            state_code = max(state_probabilities, key=state_probabilities.get)
            modality_state = {
                "A": "PRESENT",
                "B": "NOT_DETECTED",
                "C": "MODALITY_UNAVAILABLE",
                "D": "CONTRADICTED",
            }[state_code]
            support_score = state_probabilities["A"]
            result = {
                "input_id": input_id,
                "pair_id": pair["pair_id"],
                "stage2_partition": pair["stage2_partition"],
                "branch": branch,
                "question_id": item["source_question_id"],
                "video_id": item["video_id"],
                "required_modality": item["required_modality"],
                "active_evidence_modalities": (
                    ["asr"]
                    if item["required_modality"] == "asr"
                    else ["visual"]
                    if item["required_modality"] in {"ocr", "visual"}
                    else ["visual", "asr"]
                ),
                "asr_passed_to_prompt": bool(active_asr_excerpt),
                "model_text": f"STATE_CODE: {state_code}",
                "modality_state": modality_state,
                "state_code": state_code,
                "state_logits": state_logits,
                "state_probabilities": state_probabilities,
                "support_score": support_score,
                "latency_seconds": time.time() - start,
                "frame_trace": frame_trace,
                "processor_trace": processor_trace,
            }
            if (
                processor_trace["submitted_frame_count"] != 32
                or processor_trace["represented_frame_count"] != 32
                or processor_trace["post_merge_visual_token_count"] != 11664
                or not processor_trace["secondary_frame_sampling_disabled"]
            ):
                protocol_failures.append({"input_id": input_id, "processor_trace": processor_trace})
            append_jsonl(input_results_path, result)
            pair_outputs[branch] = result
            torch.cuda.empty_cache()
        relation_correct = pair_outputs["positive"]["support_score"] > pair_outputs["negative"]["support_score"]
        pairwise_correct += int(relation_correct)
        append_jsonl(
            pair_results_path,
            {
                "pair_id": pair["pair_id"],
                "stage2_partition": pair["stage2_partition"],
                "required_modality": pair["required_modality"],
                "positive_input_id": pair["positive_input_id"],
                "negative_input_id": pair["negative_input_id"],
                "positive_score": pair_outputs["positive"]["support_score"],
                "negative_score": pair_outputs["negative"]["support_score"],
                "strict_pairwise_correct": relation_correct,
                "negative_corruption_type": pair["negative_corruption_type"],
                "negative_visual_operation": pair["negative_plan"].get("visual_operation"),
            },
        )

    run_config["ended_at_epoch"] = int(time.time())
    run_config["pairwise_correct_count"] = pairwise_correct
    run_config["pairwise_accuracy"] = pairwise_correct / len(pairs)
    run_config["protocol_failure_count"] = len(protocol_failures)
    run_config["complete"] = True
    run_config["passed"] = not protocol_failures
    write_json(ARGS.output_root / "run_summary.json", run_config)
    write_json(
        ARGS.output_root / "protocol_audit.json",
        {
            "failures": protocol_failures,
            "passed": not protocol_failures,
            "not_human_gold": True,
        },
    )
    gpu_record["post_run_snapshot"] = gpu_snapshot(ARGS.gpu_id)
    gpu_record["ended_at_epoch"] = int(time.time())
    write_json(ARGS.output_root / "gpu_usage.json", gpu_record)
    if protocol_failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
