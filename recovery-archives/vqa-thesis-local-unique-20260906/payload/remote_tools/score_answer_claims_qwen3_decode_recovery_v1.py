#!/usr/bin/env python3
"""Run frozen claim scoring with scoped OpenCV recovery for audited videos."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import score_answer_claims_qwen3_v1 as base


RECOVERY_VIDEO_IDS = {
    "603f96f94cbcf891d8db244c11555214",
    "60d442c42fde20512ca8c0f02ce7123d",
    "611e166ba44c2a31cbf29f62b5986dcc",
}
ORIGINAL_DECODE_FRAMES = base.decode_frames
ORIGINAL_DUMP_JSON = base.dump_json


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_frames_with_scoped_recovery(
    video_path: str,
    indices: list[int],
) -> list[base.Image.Image]:
    path = Path(video_path)
    video_id = path.stem
    if video_id not in RECOVERY_VIDEO_IDS:
        return ORIGINAL_DECODE_FRAMES(video_path, indices)

    import cv2

    capture = cv2.VideoCapture(video_path)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if total <= 0 or any(index < 0 or index >= total for index in indices):
        capture.release()
        raise RuntimeError(f"OpenCV verifier index outside [0, {total}): {video_path}")
    frames = []
    for frame_index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(
                f"OpenCV verifier recovery failed for {video_id} at frame {frame_index}"
            )
        image = base.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGB")
        image.thumbnail(
            (base.ARGS.unified_size, base.ARGS.unified_size),
            base.Image.Resampling.LANCZOS,
        )
        frames.append(image)
    capture.release()

    recovery_dir = Path(base.__file__).resolve().parents[1] / "runs/qwen3_joint_confirm1000_v1/decode_recovery_v1"
    recovery_dir.mkdir(parents=True, exist_ok=True)
    audit_path = recovery_dir / f"{video_id}_verifier.json"
    audit = {
        "schema_version": "adsqa_scoped_verifier_decode_recovery_v1",
        "video_id": video_id,
        "video_path": str(path.resolve()),
        "video_sha256": sha256_file(path),
        "original_decoder": "decord",
        "recovery_decoder": "opencv",
        "view_count": len(indices),
        "unified_size": base.ARGS.unified_size,
        "source_total_frame_count": total,
        "source_fps": fps,
        "source_frame_indices": indices,
        "decoded_view_count": len(frames),
        "method_or_parameter_changed": False,
    }
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return frames


def dump_json_with_recovery_metadata(path: Path, value) -> None:
    if isinstance(value, dict) and value.get("schema") == "adsqa_answer_claim_qwen3_scoring_config_v1":
        value = dict(value)
        value["decode_backend"] = "decord_exact_index_with_scoped_opencv_recovery_v1"
        value["decode_recovery_video_ids"] = sorted(RECOVERY_VIDEO_IDS)
    ORIGINAL_DUMP_JSON(path, value)


base.decode_frames = decode_frames_with_scoped_recovery
base.dump_json = dump_json_with_recovery_metadata


if __name__ == "__main__":
    base.main()
