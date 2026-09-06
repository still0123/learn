#!/usr/bin/env python3
"""Run Qwen2.5 same-budget A2 inference with scoped AdsQA decode recovery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import infer_qwen25_residual_avfunnel_v1 as base


RECOVERY_VIDEO_IDS = {
    "603f96f94cbcf891d8db244c11555214",
    "60d442c42fde20512ca8c0f02ce7123d",
    "611e166ba44c2a31cbf29f62b5986dcc",
}
ORIGINAL_VIDEO_READER = base.VideoReader


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArrayFrame:
    def __init__(self, value: Any) -> None:
        self.value = value

    def asnumpy(self) -> Any:
        return self.value


class OpenCVVideoReader:
    def __init__(self, path: str) -> None:
        import cv2

        self.cv2 = cv2
        self.path = Path(path)
        self.capture = cv2.VideoCapture(str(self.path))
        self.total = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.capture.get(cv2.CAP_PROP_FPS))
        if self.total <= 0:
            self.capture.release()
            raise RuntimeError(f"OpenCV cannot inspect {path}")
        root = Path(os.environ["ADSQA_DECODE_RECOVERY_ROOT"])
        root.mkdir(parents=True, exist_ok=True)
        audit = root / f"{self.path.stem}_qwen25_a2.json"
        if not audit.exists():
            audit.write_text(
                json.dumps(
                    {
                        "schema_version": "adsqa_qwen25_a2_decode_recovery_v1",
                        "video_id": self.path.stem,
                        "video_path": str(self.path.resolve()),
                        "video_sha256": sha256_file(self.path),
                        "original_decoder": "decord",
                        "recovery_decoder": "opencv",
                        "source_total_frame_count": self.total,
                        "source_fps": self.fps,
                        "method_or_parameter_changed": False,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    def __len__(self) -> int:
        return self.total

    def get_avg_fps(self) -> float:
        return self.fps

    def __getitem__(self, index: int) -> ArrayFrame:
        if index < 0 or index >= self.total:
            raise IndexError(index)
        self.capture.set(self.cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self.capture.read()
        if not ok:
            raise RuntimeError(
                f"OpenCV recovery failed for {self.path.stem} at {index}"
            )
        return ArrayFrame(self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB))

    def __del__(self) -> None:
        capture = getattr(self, "capture", None)
        if capture is not None:
            capture.release()


def scoped_video_reader(path: str, ctx: Any = None) -> Any:
    if Path(path).stem in RECOVERY_VIDEO_IDS:
        return OpenCVVideoReader(path)
    errors: list[Exception] = []
    for _ in range(3):
        try:
            return ORIGINAL_VIDEO_READER(path, ctx=ctx)
        except Exception as error:  # pragma: no cover - remote codec behavior
            errors.append(error)
    raise RuntimeError(
        f"Decord failed three times for non-whitelisted video {Path(path).stem}"
    ) from errors[-1]


base.VideoReader = scoped_video_reader


if __name__ == "__main__":
    base.main()
