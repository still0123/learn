#!/usr/bin/env python3
"""Verify that every frozen FreshQ video can supply 32 and 40 decoded views."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.fresh_confirm_decode import (
    FALLBACK_EVENTS,
    robust_load_uniform_frames,
)
from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import resolve_video_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--video-root", required=True)
    parser.add_argument("--frames-fallback-root", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    question_path = Path(args.questions).resolve()
    video_root = Path(args.video_root).resolve()
    fallback_root = Path(args.frames_fallback_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    questions = json.loads(question_path.read_text(encoding="utf-8"))
    failures = []
    started = time.time()
    for index, row in enumerate(questions, start=1):
        video = str(row["video"])
        path = resolve_video_path(video, video_root, fallback_root)
        try:
            frames32, _ = robust_load_uniform_frames(path, 32)
            frames40, _ = robust_load_uniform_frames(path, 40)
            if len(frames32) != 32 or len(frames40) != 40:
                raise RuntimeError("decoded frame count differs from the requested count")
        except Exception as exc:
            failures.append(
                {
                    "question_id": str(row["question_id"]),
                    "video": video,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                }
            )
        if index % 25 == 0:
            print(
                f"checked={index}/{len(questions)} failures={len(failures)} "
                f"elapsed={time.time() - started:.1f}",
                flush=True,
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    failures_path = output_dir / "failed_videos.json"
    failures_path.write_text(
        json.dumps(failures, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    audit = {
        "schema_version": "fresh_confirm500_decode_preflight_audit_v1",
        "passed": len(questions) == 500 and not failures,
        "question_count": len(questions),
        "video_count": len({str(row["video"]) for row in questions}),
        "failure_count": len(failures),
        "failed_video_count": len({row["video"] for row in failures}),
        "fallback_event_count": len(FALLBACK_EVENTS),
        "fallback_video_count": len(
            {Path(str(row["video_path"])).stem for row in FALLBACK_EVENTS}
        ),
        "questions_sha256": sha256_file(question_path),
        "failed_videos_sha256": sha256_file(failures_path),
        "elapsed_seconds": time.time() - started,
    }
    (output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
