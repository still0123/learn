"""Deterministic video decoding fallback used only by FreshQ confirmation."""

from __future__ import annotations

from collections import defaultdict
import json
import os
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import (
    load_uniform_frames as decord_load_uniform_frames,
    uniform_indices,
)


FALLBACK_EVENTS: list[dict[str, Any]] = []


def _append_event(event: dict[str, Any]) -> None:
    FALLBACK_EVENTS.append(event)
    log_path = os.environ.get("FRESH_DECODE_FALLBACK_LOG", "")
    if not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")


def _opencv_uniform_frames(video_path: Path, view_count: int):
    import cv2
    from PIL import Image

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV cannot open {video_path}")
    total = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if total <= 0:
        capture.release()
        raise RuntimeError(f"OpenCV reports no frames for {video_path}")
    indices = uniform_indices(total, view_count)
    ranks_by_index: dict[int, list[int]] = defaultdict(list)
    for rank, frame_index in enumerate(indices):
        ranks_by_index[int(frame_index)].append(rank)
    selected: dict[int, Any] = {}
    frame_index = 0
    maximum = max(ranks_by_index)
    while frame_index <= maximum:
        ok, frame = capture.read()
        if not ok:
            break
        for rank in ranks_by_index.get(frame_index, []):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            selected[rank] = Image.fromarray(rgb).convert("RGB")
        frame_index += 1
    capture.release()
    if len(selected) != view_count:
        raise RuntimeError(
            f"OpenCV decoded {len(selected)}/{view_count} requested frames from {video_path}"
        )
    frames = [selected[rank] for rank in range(view_count)]
    metadata = [
        {
            "global_rank": rank,
            "source_frame_index": int(frame_index),
            "source_total_frame_count": total,
            "source_timestamp_sec": float(frame_index / fps) if fps > 0 else None,
            "decode_backend": "opencv_sequential_fallback_v1",
        }
        for rank, frame_index in enumerate(indices)
    ]
    return frames, metadata


def robust_load_uniform_frames(video_path: Path, view_count: int):
    try:
        return decord_load_uniform_frames(video_path, view_count)
    except Exception as exc:
        frames, metadata = _opencv_uniform_frames(video_path, view_count)
        _append_event(
            {
                "schema_version": "fresh_confirm_decode_fallback_event_v1",
                "video_path": str(video_path.resolve()),
                "view_count": view_count,
                "primary_backend": "decord_accurate_seek",
                "fallback_backend": "opencv_sequential_fallback_v1",
                "primary_error_type": type(exc).__name__,
                "frame_count": len(frames),
            }
        )
        return frames, metadata
