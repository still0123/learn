#!/usr/bin/env python3
"""Run the frozen same-budget ablation with scoped OpenCV decoding recovery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import infer_qwen3_samebudget_ablation_v1 as base


RECOVERY_VIDEO_IDS = {
    "603f96f94cbcf891d8db244c11555214",
    "60d442c42fde20512ca8c0f02ce7123d",
    "611e166ba44c2a31cbf29f62b5986dcc",
}
ORIGINAL_VIDEO_READER = base.VideoReader
AUDIT_ROOT = Path(os.environ["ADSQA_DECODE_AUDIT_ROOT"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class _Frame:
    def __init__(self, array):
        self._array = array

    def asnumpy(self):
        return self._array


class OpenCVReader:
    def __init__(self, path: str):
        import cv2

        self.cv2 = cv2
        self.path = Path(path)
        self.capture = cv2.VideoCapture(str(self.path))
        self.total = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.capture.get(cv2.CAP_PROP_FPS))
        if self.total <= 0:
            self.capture.release()
            raise RuntimeError(f"OpenCV found no frames: {self.path}")

    def __len__(self):
        return self.total

    def get_avg_fps(self):
        return self.fps

    def __getitem__(self, index: int):
        self.capture.set(self.cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = self.capture.read()
        if not ok:
            raise RuntimeError(f"OpenCV recovery failed at frame {index}: {self.path}")
        rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        return _Frame(rgb)

    def __del__(self):
        capture = getattr(self, "capture", None)
        if capture is not None:
            capture.release()


def write_audit(reader: OpenCVReader) -> None:
    path = AUDIT_ROOT / f"{reader.path.stem}.json"
    payload = {
        "schema_version": "adsqa_samebudget_ablation_scoped_decode_recovery_v1",
        "video_id": reader.path.stem,
        "video_sha256": sha256_file(reader.path),
        "original_decoder": "decord",
        "recovery_decoder": "opencv",
        "recovery_reason": "previously confirmed intermittent H.264 failure",
        "source_total_frame_count": reader.total,
        "source_fps": reader.fps,
        "frame_index_policy": "reuse frozen indices from answer-free source inputs",
        "method_or_parameter_changed": False,
    }
    text = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"decode audit changed: {path}")
        return
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def video_reader_with_recovery(path: str, ctx=None):
    video_id = Path(path).stem
    if video_id in RECOVERY_VIDEO_IDS:
        reader = OpenCVReader(path)
        write_audit(reader)
        return reader
    last_error = None
    for _ in range(3):
        try:
            return ORIGINAL_VIDEO_READER(path, ctx=ctx)
        except Exception as error:
            last_error = error
    raise RuntimeError(f"Decord failed three times for non-whitelisted video {video_id}") from last_error


base.VideoReader = video_reader_with_recovery


if __name__ == "__main__":
    base.main()
