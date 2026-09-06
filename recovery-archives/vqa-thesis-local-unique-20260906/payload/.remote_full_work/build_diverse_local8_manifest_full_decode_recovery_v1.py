#!/usr/bin/env python3
"""Run raw-feature construction with scoped, audited decode recovery."""

from __future__ import annotations

import hashlib
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
from typing import Any

import build_diverse_local8_manifest_v1 as base
from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import uniform_indices


RECOVERY_VIDEO_IDS = {
    "603f96f94cbcf891d8db244c11555214",
    "60d442c42fde20512ca8c0f02ce7123d",
    "611e166ba44c2a31cbf29f62b5986dcc",
}
ORIGINAL_LOAD_UNIFORM_FRAMES = base.load_uniform_frames
AUDIT_ROOT = Path(
    os.environ.get(
        "ADSQA_DECODE_AUDIT_ROOT",
        "/data1/rmx/projectb/AdsQA-main/evaluation/runs/"
        "qwen3_full_valid5320_v1/decode_recovery_v1/raw_features",
    )
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=True, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise RuntimeError(f"decode audit changed across calls: {path}")
        return
    temporary = path.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def load_uniform_frames_with_scoped_recovery(
    video_path: Path,
    view_count: int,
) -> tuple[list[Any], list[dict[str, Any]]]:
    video = video_path.stem
    if video not in RECOVERY_VIDEO_IDS:
        last_error: Exception | None = None
        errors = []
        for attempt in range(1, 4):
            try:
                frames, metadata = ORIGINAL_LOAD_UNIFORM_FRAMES(
                    video_path, view_count
                )
                if attempt > 1:
                    write_once(
                        AUDIT_ROOT / f"{video}_decord_retry.json",
                        {
                            "schema_version": "adsqa_full_decord_retry_v1",
                            "video_id": video,
                            "video_sha256": sha256_file(video_path),
                            "decoder": "decord",
                            "attempts": attempt,
                            "prior_errors": errors,
                            "fallback_decoder_used": False,
                            "method_or_parameter_changed": False,
                        },
                    )
                return frames, metadata
            except Exception as error:
                last_error = error
                errors.append(
                    {"type": type(error).__name__, "message": str(error)}
                )
        raise RuntimeError(
            f"Decord failed three times for non-whitelisted video {video}"
        ) from last_error

    import cv2
    from PIL import Image

    capture = cv2.VideoCapture(str(video_path))
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    indices = uniform_indices(total, view_count)
    frames = []
    for frame_index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(
                f"OpenCV recovery failed for {video} at frame {frame_index}"
            )
        frames.append(
            Image.fromarray(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ).convert("RGB")
        )
    capture.release()
    metadata = [
        {
            "global_rank": rank,
            "source_frame_index": int(frame_index),
            "source_total_frame_count": total,
            "source_timestamp_sec": (
                float(frame_index / fps) if fps > 0 else None
            ),
        }
        for rank, frame_index in enumerate(indices)
    ]
    write_once(
        AUDIT_ROOT / f"{video}.json",
        {
            "schema_version": "adsqa_full_scoped_decode_recovery_v1",
            "video_id": video,
            "video_sha256": sha256_file(video_path),
            "original_decoder": "decord",
            "recovery_decoder": "opencv",
            "recovery_reason": "previously confirmed intermittent H.264 failure",
            "view_count": view_count,
            "source_total_frame_count": total,
            "source_fps": fps,
            "source_frame_indices": indices,
            "decoded_view_count": len(frames),
            "method_or_parameter_changed": False,
        },
    )
    logging.getLogger("modality_manifest").warning(
        "scoped OpenCV recovery video_id=%s views=%d", video, len(frames)
    )
    return frames, metadata


base.load_uniform_frames = load_uniform_frames_with_scoped_recovery


def parse_args_all_idle_gpus() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=[str(i) for i in range(6)])
    parser.add_argument("--questions", required=True)
    parser.add_argument("--segmented-asr-root", required=True)
    parser.add_argument("--ocr-root", required=True)
    parser.add_argument("--clip-path", default=str(base.PROJECT_ROOT / "models/clip-vit-large-patch14"))
    parser.add_argument("--video-root", default=str(base.PROJECT_ROOT / "data/videos"))
    parser.add_argument("--frames-fallback-root", default=str(base.PROJECT_ROOT / "data/frames_8"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-items", type=int, default=-1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def ensure_idle_visible_gpu(gpu_id: str) -> list[str]:
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
        raise RuntimeError(f"GPU {gpu_id} is not visible")
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
        raise RuntimeError(f"GPU {gpu_id} is not idle: {active_apps}")
    return matching


base.parse_args = parse_args_all_idle_gpus
base.ensure_idle_allowed_gpu = ensure_idle_visible_gpu


if __name__ == "__main__":
    base.main()
