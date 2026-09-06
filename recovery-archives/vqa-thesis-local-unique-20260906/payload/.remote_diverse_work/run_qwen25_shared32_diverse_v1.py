#!/usr/bin/env python3
"""Run the fixed-40-view Shared32 causal-isolation arms for one fold."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any, Mapping, Sequence

sys.modules["torchcodec"] = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.common.adsqa_prompt import (  # noqa: E402
    ADSQA_ANSWER_PROMPT_VERSION,
    adsqa_answer_prompt_sha256,
    build_adsqa_answer_prompt,
)
from evaluation.methods.common.qwen_video_budget import (  # noqa: E402
    VideoBudgetError,
    prepare_qwen_video_inputs,
)
from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    RAW_GLOBAL_VIEW_COUNT,
    sha256_file,
    validate_clean_model_path,
    validate_shared_gate_manifest,
)


METHODS = {
    "Shared32_ExtraGlobal8",
    "Shared32_Local8",
    "Shared32_RandomLocal8",
    "Shared32_DiverseLocal8",
}
SPLIT_ROOT = PROJECT_ROOT / "evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"
DEFAULT_RUN_ROOT = (
    PROJECT_ROOT / "evaluation/runs/innovation1_qwen25_modality_active_avcrop_groupcv_v1"
)


class InferenceProtocolError(RuntimeError):
    """Raised when an inference request violates the frozen protocol."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["1", "2", "4", "5"])
    parser.add_argument("--fold", required=True, type=int, choices=range(5))
    parser.add_argument("--method", required=True, choices=sorted(METHODS))
    parser.add_argument(
        "--question-file",
        default="",
        help="Answer-free validation question file; defaults to the selected fold.",
    )
    parser.add_argument(
        "--asr-file",
        default=str(PROJECT_ROOT / "evaluation/asr_set.json"),
    )
    parser.add_argument(
        "--gate-manifest",
        default="",
        help="Required immutable JSONL manifest shared by both fixed-40 methods.",
    )
    parser.add_argument(
        "--model-dir",
        default="/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct",
    )
    parser.add_argument(
        "--video-root",
        default=str(PROJECT_ROOT / "data/videos"),
    )
    parser.add_argument(
        "--frames-fallback-root",
        default=str(PROJECT_ROOT / "data/frames_8"),
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Defaults to the selected method/fold under the run root.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--unified-size", type=int, default=896)
    parser.add_argument("--metadata-fps", type=float, default=1.0)
    parser.add_argument("--max-items", type=int, default=-1, help="Smoke limit; -1 means all.")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def default_question_file(fold: int) -> Path:
    return SPLIT_ROOT / "groupcv5" / f"fold_{fold}" / "validation_questions_v1.json"


def default_output_dir(method: str, fold: int) -> Path:
    return DEFAULT_RUN_ROOT / "groupcv5" / "inference" / method / f"fold_{fold}"


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=True) + "\n")


def load_answer_free_questions(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise InferenceProtocolError("question file must be a JSON list")
    required = {"question_id", "video", "question"}
    forbidden = {"answer", "ground_truth", "reference_answer", "judge_score", "prediction"}
    for row in rows:
        if not isinstance(row, dict) or not required.issubset(row):
            raise InferenceProtocolError("question file row lacks question_id/video/question")
        if forbidden & set(row):
            raise InferenceProtocolError("question file contains answer-side or outcome fields")
    return rows


def load_asr(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise InferenceProtocolError("ASR file must contain an object")
    return payload


def load_gate_manifest(path: Path, question_ids: set[str]) -> dict[str, dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InferenceProtocolError(f"invalid gate JSONL at line {line_number}") from exc
        if not isinstance(record, dict):
            raise InferenceProtocolError("gate manifest row must be an object")
        records.append(record)
    validate_shared_gate_manifest(records)
    by_question = {str(record["question_id"]): record for record in records}
    missing = question_ids - set(by_question)
    if missing:
        raise InferenceProtocolError(
            f"gate manifest misses {len(missing)} requested questions"
        )
    return by_question


def ensure_idle_allowed_gpu(gpu_id: str) -> list[str]:
    """Reject unavailable, busy, or disallowed GPUs before importing torch."""
    if gpu_id not in {"1", "2", "4", "5"}:
        raise InferenceProtocolError("this experiment is frozen to GPU1/GPU2/GPU4/GPU5")
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
    matching = [line for line in rows if line.split(",", 1)[0].strip() == gpu_id]
    if len(matching) != 1:
        raise InferenceProtocolError(f"GPU {gpu_id} is not visible in nvidia-smi")
    apps = subprocess.run(
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
    active_apps = [line.strip() for line in apps.stdout.splitlines() if line.strip()]
    if active_apps:
        raise InferenceProtocolError(
            f"GPU {gpu_id} is not idle; existing processes: {active_apps}"
        )
    return matching


def uniform_indices(frame_count: int, view_count: int) -> list[int]:
    if frame_count <= 0 or view_count <= 0:
        raise InferenceProtocolError("positive frame and view counts are required")
    if frame_count == 1:
        return [0] * view_count
    return [round(index * (frame_count - 1) / (view_count - 1)) for index in range(view_count)]


def resolve_video_path(video_id: str, video_root: Path, fallback_root: Path) -> Path:
    candidates = [
        video_root / f"{video_id}.mp4",
        video_root / video_id,
        video_root / f"{video_id}.webm",
        video_root / f"{video_id}.mov",
        fallback_root / video_id,
    ]
    return next((path for path in candidates if path.exists()), candidates[0])


def load_frames_by_indices(
    video_path: Path,
    indices: Sequence[int],
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Decode an explicit frame-index list using CPU video decoding."""
    import numpy as np
    from PIL import Image

    try:
        from decord import VideoReader, cpu
    except Exception:
        VideoReader = None
        cpu = None
    if VideoReader is not None and video_path.is_file():
        reader = VideoReader(str(video_path), ctx=cpu(0))
        total = len(reader)
        if total:
            fps = float(reader.get_avg_fps()) if reader.get_avg_fps() else 0.0
            safe_indices = [max(0, min(int(index), total - 1)) for index in indices]
            frames = [Image.fromarray(reader[index].asnumpy()).convert("RGB") for index in safe_indices]
            metadata = [
                {
                    "global_rank": rank,
                    "source_frame_index": int(index),
                    "source_total_frame_count": total,
                    "source_timestamp_sec": float(index / fps) if fps > 0 else None,
                }
                for rank, index in enumerate(safe_indices)
            ]
            return frames, metadata
    if video_path.is_dir():
        images = sorted(video_path.glob("*.jpg")) + sorted(video_path.glob("*.png"))
        if images:
            safe_indices = [max(0, min(int(index), len(images) - 1)) for index in indices]
            frames = [Image.open(images[index]).convert("RGB") for index in safe_indices]
            metadata = [
                {
                    "global_rank": rank,
                    "source_frame_index": int(index),
                    "source_total_frame_count": len(images),
                    "source_timestamp_sec": None,
                }
                for rank, index in enumerate(safe_indices)
            ]
            return frames, metadata
    raise InferenceProtocolError(f"unable to decode video or fallback frames: {video_path}")


def load_uniform_frames(
    video_path: Path,
    view_count: int,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Decode exactly ``view_count`` uniform global views."""
    if view_count <= 0:
        raise InferenceProtocolError("view_count must be positive")
    if video_path.is_file():
        try:
            from decord import VideoReader, cpu
            reader = VideoReader(str(video_path), ctx=cpu(0))
            total = len(reader)
        except Exception:
            total = 0
    elif video_path.is_dir():
        total = len(sorted(video_path.glob("*.jpg")) + sorted(video_path.glob("*.png")))
    else:
        total = 0
    if total <= 0:
        raise InferenceProtocolError(f"unable to count video frames: {video_path}")
    return load_frames_by_indices(video_path, uniform_indices(total, view_count))


def extra_global_indices(total: int) -> list[int]:
    """Select deterministic midpoints between the shared 32 global anchors."""
    if total <= 0:
        raise InferenceProtocolError("positive frame count required")
    shared = set(uniform_indices(total, RAW_GLOBAL_VIEW_COUNT))
    candidates = [round((2 * index + 1) * (total - 1) / 16) for index in range(8)]
    result = []
    for candidate in candidates:
        value = int(max(0, min(candidate, total - 1)))
        if value in shared:
            for offset in range(1, total):
                alternatives = [value - offset, value + offset]
                value = next((item for item in alternatives if 0 <= item < total and item not in shared), value)
                if value not in shared:
                    break
        result.append(value)
    return result


def deterministic_random_crop_specs(question_id: str) -> list[dict[str, Any]]:
    """Create eight question-independent spatial controls from a stable hash."""
    specs = []
    for rank in range(APPENDED_LOCAL_VIEW_COUNT):
        digest = hashlib.sha256(f"shared32-random-control-v1:{question_id}:{rank}".encode("utf-8")).digest()
        source_rank = int.from_bytes(digest[:4], "big") % RAW_GLOBAL_VIEW_COUNT
        left = 0.05 + (digest[4] / 255.0) * 0.30
        top = 0.05 + (digest[5] / 255.0) * 0.30
        width = 0.60
        specs.append(
            {
                "source_global_rank": source_rank,
                "bbox_norm": [left, top, left + width, top + width],
                "crop_mode": "deterministic_random_control_v1",
            }
        )
    return specs


def resize_frame(frame: Any, unified_size: int) -> Any:
    from PIL import Image

    return frame.resize((unified_size, unified_size), Image.Resampling.BICUBIC)


def crop_from_normalized_box(frame: Any, bbox_norm: Sequence[float]) -> Any:
    if len(bbox_norm) != 4:
        raise InferenceProtocolError("crop bbox_norm must contain four values")
    left, top, right, bottom = [float(value) for value in bbox_norm]
    if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
        raise InferenceProtocolError(f"invalid normalized crop box: {bbox_norm}")
    width, height = frame.size
    box = (
        int(left * width),
        int(top * height),
        max(int(right * width), int(left * width) + 1),
        max(int(bottom * height), int(top * height) + 1),
    )
    return frame.crop(box)


def validate_crop_specs(specs: Sequence[Mapping[str, Any]], key: str) -> list[Mapping[str, Any]]:
    if len(specs) != APPENDED_LOCAL_VIEW_COUNT:
        raise InferenceProtocolError(f"{key} must contain exactly eight crop specs")
    validated = []
    for spec in specs:
        rank = int(spec.get("source_global_rank", -1))
        if not 0 <= rank < RAW_GLOBAL_VIEW_COUNT:
            raise InferenceProtocolError(f"{key} has invalid source_global_rank={rank}")
        bbox = spec.get("bbox_norm")
        if (
            not isinstance(bbox, Sequence)
            or isinstance(bbox, (str, bytes))
            or len(bbox) != 4
        ):
            raise InferenceProtocolError(f"{key} has no bbox_norm")
        try:
            left, top, right, bottom = [float(value) for value in bbox]
        except (TypeError, ValueError) as exc:
            raise InferenceProtocolError(f"{key} has non-numeric bbox_norm") from exc
        if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
            raise InferenceProtocolError(f"{key} has invalid bbox_norm")
        validated.append(spec)
    return validated


def construct_input_views(
    *,
    method: str,
    question_id: str,
    global_frames: Sequence[Any],
    global_metadata: Sequence[Mapping[str, Any]],
    video_path: Path,
    unified_size: int,
    gate_record: Mapping[str, Any] | None,
) -> tuple[list[Any], list[dict[str, Any]], dict[str, Any] | None]:
    """Construct the shared 32 anchors plus one frozen 8-view intervention."""
    if len(global_frames) != RAW_GLOBAL_VIEW_COUNT:
        raise InferenceProtocolError("gated methods require exactly 32 Raw global frames")
    frames, metadata = load_uniform_frames_placeholder(global_frames, global_metadata, unified_size)
    if method == "Shared32_ExtraGlobal8":
        total = int(global_metadata[0].get("source_total_frame_count", 0))
        indices = extra_global_indices(total)
        extra_frames, extra_metadata = load_frames_by_indices(video_path, indices)
        for rank, (frame, source) in enumerate(zip(extra_frames, extra_metadata)):
            frames.append(resize_frame(frame, unified_size))
            metadata.append(
                {
                    "input_index": len(metadata),
                    "view_type": "extra_global",
                    "extra_global_rank": rank,
                    "source_frame_index": source.get("source_frame_index"),
                    "source_total_frame_count": source.get("source_total_frame_count"),
                }
            )
        return frames, metadata, {"control": "extra_global_midpoints_v1", "extra_global_indices": indices}

    if gate_record is None:
        raise InferenceProtocolError("local intervention requires a frozen gate record")
    if not bool(gate_record.get("append_crop8")) or int(gate_record.get("local_view_count", -1)) != 8:
        raise InferenceProtocolError("gate manifest must request exactly eight local views")
    if method in {"Shared32_Local8", "Shared32_DiverseLocal8"}:
        specs = validate_crop_specs(gate_record.get("clip_crop_specs", []), "clip_crop_specs")
    elif method == "Shared32_RandomLocal8":
        specs = deterministic_random_crop_specs(question_id)
        specs = validate_crop_specs(specs, "random_control_crop_specs")
    else:
        raise InferenceProtocolError(f"unsupported method: {method}")

    for local_rank, spec in enumerate(specs):
        source_rank = int(spec["source_global_rank"])
        source_metadata = global_metadata[source_rank]
        local = crop_from_normalized_box(global_frames[source_rank], spec["bbox_norm"])
        frames.append(resize_frame(local, unified_size))
        metadata.append(
            {
                "input_index": len(metadata),
                "view_type": "local",
                "local_rank": local_rank,
                "source_global_rank": source_rank,
                "source_frame_index": source_metadata.get("source_frame_index"),
                "bbox_norm": list(spec["bbox_norm"]),
                "crop_mode": spec.get("crop_mode", method),
            }
        )
    if len(frames) != RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT:
        raise InferenceProtocolError("gate hit did not append exactly eight local views")
    return frames, metadata, {
        "control": (
            "question_conditioned_local_v1"
            if method == "Shared32_Local8"
            else "question_conditioned_temporal_diverse_local_v1"
            if method == "Shared32_DiverseLocal8"
            else "deterministic_random_local_control_v1"
        ),
        "gate_record": dict(gate_record),
        "crop_specs": [dict(spec) for spec in specs],
    }


def load_uniform_frames_placeholder(
    frames: Sequence[Any],
    metadata: Sequence[Mapping[str, Any]],
    unified_size: int,
) -> tuple[list[Any], list[dict[str, Any]]]:
    if len(frames) != len(metadata):
        raise InferenceProtocolError("frame/metadata length mismatch")
    resized = [resize_frame(frame, unified_size) for frame in frames]
    plan = [
        {
            "input_index": index,
            "view_type": "global",
            "global_rank": int(source.get("global_rank", index)),
            "source_frame_index": source.get("source_frame_index"),
        }
        for index, source in enumerate(metadata)
    ]
    return resized, plan


def setup_logging(output_dir: Path, gpu_id: str) -> logging.Logger:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"inference_gpu{gpu_id}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return logging.getLogger("qwen25_gated_avcrop_groupcv")


def main() -> None:
    args = parse_args()
    question_path = Path(args.question_file) if args.question_file else default_question_file(args.fold)
    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir(args.method, args.fold)
    output_dir = output_dir.resolve()
    questions = load_answer_free_questions(question_path.resolve())
    if args.max_items > 0:
        questions = questions[: args.max_items]
    if not questions:
        raise InferenceProtocolError("no questions selected")

    gpu_snapshot = ensure_idle_allowed_gpu(args.gpu_id)
    model_identity = validate_clean_model_path(args.model_dir)
    if not args.gate_manifest:
        raise InferenceProtocolError("both fixed-40 methods require --gate-manifest")
    gate_manifest_path = Path(args.gate_manifest).resolve()
    gate_by_question = load_gate_manifest(
        gate_manifest_path,
        {str(item["question_id"]) for item in questions},
    )
    gate_manifest_sha256 = sha256_file(gate_manifest_path)

    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch
    import transformers
    from transformers import AutoModelForVision2Seq, AutoProcessor

    logger = setup_logging(output_dir, args.gpu_id)
    run_config = {
        "schema_version": "qwen25_shared32_isolation_inference_v1",
        "fold": args.fold,
        "method": args.method,
        "causal_isolation_protocol": "same_shared32_plus_one_of_three_eight_view_controls",
        "question_file": str(question_path.resolve()),
        "question_file_sha256": sha256_file(question_path),
        "question_count": len(questions),
        "groundtruth_file_read": False,
        "testset_answers_read": False,
        "model_identity": model_identity,
        "gpu_snapshot_before_load": gpu_snapshot,
        "gpu_id": args.gpu_id,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "transformers_version": transformers.__version__,
        "rag_enabled": False,
        "reflection_enabled": False,
        "answer_rewrite_enabled": False,
        "secondary_frame_sampling_disabled": True,
        "answer_prompt_version": ADSQA_ANSWER_PROMPT_VERSION,
        "answer_prompt_sha256": adsqa_answer_prompt_sha256(),
        "gate_manifest_sha256": gate_manifest_sha256,
        "raw_global_view_count": RAW_GLOBAL_VIEW_COUNT,
        "appended_local_view_count": APPENDED_LOCAL_VIEW_COUNT,
        "submitted_view_count": RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT,
        "shared_global_view_count": RAW_GLOBAL_VIEW_COUNT,
        "segmented_asr_used_for_selection_only": True,
        "answer_model_asr_source_unchanged_from_prior_oof": True,
        "unified_size": args.unified_size,
        "max_new_tokens": args.max_new_tokens,
    }
    dump_json(output_dir / "run_config.json", run_config)

    logger.info("Loading clean Qwen2.5 model for method=%s fold=%d", args.method, args.fold)
    model = AutoModelForVision2Seq.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    processor = AutoProcessor.from_pretrained(
        args.model_dir,
        min_pixels=256 * 256,
        max_pixels=args.unified_size * args.unified_size,
        trust_remote_code=True,
    )
    asr_data = load_asr(Path(args.asr_file))
    video_root = Path(args.video_root)
    fallback_root = Path(args.frames_fallback_root)
    stats = {"processed": 0, "skipped_existing": 0, "errors": 0}
    errors_path = output_dir / "logs/errors.jsonl"

    for item in questions:
        question_id = str(item["question_id"])
        question_dir = output_dir / question_id
        prediction_path = question_dir / "prediction.json"
        evidence_path = question_dir / "evidence.json"
        if prediction_path.exists() and not args.overwrite:
            stats["skipped_existing"] += 1
            continue
        started = time.time()
        try:
            video_id = str(item["video"])
            video_path = resolve_video_path(video_id, video_root, fallback_root)
            global_frames, global_metadata = load_uniform_frames(
                video_path,
                RAW_GLOBAL_VIEW_COUNT,
            )
            gate_record = gate_by_question.get(question_id)
            input_frames, visual_plan, gate_evidence = construct_input_views(
                method=args.method,
                question_id=question_id,
                global_frames=global_frames,
                global_metadata=global_metadata,
                video_path=video_path,
                unified_size=args.unified_size,
                gate_record=gate_record,
            )
            expected_view_count = len(input_frames)
            if expected_view_count != RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT:
                raise InferenceProtocolError("both methods must submit exactly 40 views")

            asr = asr_data.get(f"{video_id}.mp4", asr_data.get(video_id, ""))
            asr_text = str(asr.get("transcript", asr.get("text", ""))) if isinstance(asr, dict) else str(asr or "")
            prompt = build_adsqa_answer_prompt(str(item["question"]), asr_text)
            message = [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": input_frames, "fps": args.metadata_fps},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            text_input = processor.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
            processor_inputs, processor_trace = prepare_qwen_video_inputs(
                processor=processor,
                text_input=text_input,
                frames=input_frames,
                device=model.device,
                expected_view_count=expected_view_count,
                max_post_merge_visual_tokens=20480,
                metadata_fps=args.metadata_fps,
                frame_indices=[
                    int(plan.get("source_frame_index", index) or index)
                    for index, plan in enumerate(visual_plan)
                ],
                require_exact_frame_count=True,
            )
            with torch.no_grad():
                generated = model.generate(
                    **processor_inputs,
                    do_sample=False,
                    max_new_tokens=args.max_new_tokens,
                )
            trimmed = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(processor_inputs.input_ids, generated)
            ]
            prediction = processor.batch_decode(
                trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()

            if str(gate_record.get("question_id")) != question_id:
                raise InferenceProtocolError("question and gate record are misaligned")
            if expected_view_count - RAW_GLOBAL_VIEW_COUNT != APPENDED_LOCAL_VIEW_COUNT:
                raise InferenceProtocolError("fixed local-view budget was violated")
            question_dir.mkdir(parents=True, exist_ok=True)
            dump_json(
                prediction_path,
                {
                    "question_id": question_id,
                    "video": video_id,
                    "prediction": prediction,
                    "pipeline": args.method,
                    "model_path": model_identity["path"],
                },
            )
            dump_json(
                evidence_path,
                {
                    "question_id": question_id,
                    "video": video_id,
                    "question": item["question"],
                    "asr_excerpt": asr_text[:1000],
                    "input_image_count": expected_view_count,
                    "visual_plan": visual_plan,
                    "intervention_record": gate_evidence,
                    "processor_trace": processor_trace,
                    "latency_seconds": time.time() - started,
                },
            )
            stats["processed"] += 1
        except Exception as exc:
            logger.exception("inference failure for %s", question_id)
            append_jsonl(
                errors_path,
                {
                    "question_id": question_id,
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            stats["errors"] += 1
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    run_config["stats"] = stats
    dump_json(output_dir / "run_summary.json", run_config)
    logger.info("Finished %s", stats)


if __name__ == "__main__":
    main()
