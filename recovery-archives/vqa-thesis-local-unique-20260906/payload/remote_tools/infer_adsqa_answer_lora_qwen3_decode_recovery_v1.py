#!/usr/bin/env python3
"""Run frozen Uniform8 inference with one scoped OpenCV decode recovery."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import infer_adsqa_answer_lora_qwen3_v1 as base
from adsqa_sft_lora_common_v1 import uniform_indices


RECOVERY_VIDEO_IDS = {
    "603f96f94cbcf891d8db244c11555214",
    "60d442c42fde20512ca8c0f02ce7123d",
    "611e166ba44c2a31cbf29f62b5986dcc",
}
ORIGINAL_LOAD_UNIFORM_FRAMES = base.load_uniform_frames


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_uniform_frames_with_scoped_recovery(
    video_path: Path,
    view_count: int,
    unified_size: int,
) -> tuple[list[Any], list[dict[str, Any]]]:
    video_id = video_path.stem
    if video_id not in RECOVERY_VIDEO_IDS or not video_path.is_file():
        errors = []
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                result = ORIGINAL_LOAD_UNIFORM_FRAMES(video_path, view_count, unified_size)
                if attempt > 1:
                    recovery_dir = Path(base.__file__).resolve().parents[1] / "runs/qwen3_joint_confirm1000_v1/decode_recovery_v1"
                    recovery_dir.mkdir(parents=True, exist_ok=True)
                    audit_path = recovery_dir / f"{video_id}_uniform8_decord_retry.json"
                    retry_audit = {
                        "schema_version": "adsqa_decord_retry_audit_v1",
                        "video_id": video_id,
                        "video_path": str(video_path.resolve()),
                        "decoder": "decord",
                        "attempts": attempt,
                        "prior_errors": errors,
                        "fallback_decoder_used": False,
                        "method_or_parameter_changed": False,
                    }
                    audit_path.write_text(
                        json.dumps(retry_audit, ensure_ascii=True, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    logging.getLogger(__name__).warning(
                        "Decord Uniform8 retry succeeded video_id=%s attempts=%d audit=%s",
                        video_id,
                        attempt,
                        audit_path,
                    )
                return result
            except Exception as error:
                last_error = error
                errors.append({"type": type(error).__name__, "message": str(error)})
        raise RuntimeError(
            f"Decord failed three times for non-whitelisted video {video_id}"
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
                f"OpenCV recovery failed for {video_id} at frame {frame_index}"
            )
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGB")
        frames.append(image.resize((unified_size, unified_size), Image.Resampling.BICUBIC))
    capture.release()

    metadata = [
        {
            "input_index": rank,
            "source_frame_index": int(frame_index),
            "source_total_frame_count": total,
            "source_timestamp_sec": float(frame_index / fps) if fps > 0 else None,
            "view_type": "uniform_global",
        }
        for rank, frame_index in enumerate(indices)
    ]
    recovery_dir = Path(base.__file__).resolve().parents[1] / "runs/qwen3_joint_confirm1000_v1/decode_recovery_v1"
    recovery_dir.mkdir(parents=True, exist_ok=True)
    audit_path = recovery_dir / f"{video_id}_uniform8.json"
    audit = {
        "schema_version": "adsqa_scoped_decode_recovery_v1",
        "video_id": video_id,
        "video_path": str(video_path.resolve()),
        "video_sha256": sha256_file(video_path),
        "original_decoder": "decord",
        "recovery_decoder": "opencv",
        "recovery_reason": "confirmed intermittent Decord H.264 NAL/filter-graph failure",
        "view_count": view_count,
        "unified_size": unified_size,
        "source_total_frame_count": total,
        "source_fps": fps,
        "source_frame_indices": indices,
        "decoded_view_count": len(frames),
        "method_or_parameter_changed": False,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    logging.getLogger(__name__).warning(
        "scoped OpenCV Uniform8 recovery video_id=%s audit=%s",
        video_id,
        audit_path,
    )
    return frames, metadata


base.load_uniform_frames = load_uniform_frames_with_scoped_recovery


if __name__ == "__main__":
    base.main()
