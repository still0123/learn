#!/usr/bin/env python3
"""Precompute OCR text and boxes for frames selected by an existing run."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import platform
import time
from typing import Any


_OCR = None
_THREADS_PER_WORKER = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--video-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--threads-per-worker", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.35)
    return parser.parse_args()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_evidence(root: str | Path) -> dict[str, Path]:
    indexed = {}
    for path in Path(root).rglob("evidence.json"):
        try:
            qid = str(json.loads(path.read_text(encoding="utf-8"))["question_id"])
        except (KeyError, json.JSONDecodeError, OSError):
            continue
        indexed[qid] = path
    return indexed


def selected_frames(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    frames = evidence.get("selected_frames")
    if isinstance(frames, list) and frames:
        return [dict(item) for item in frames]
    return [dict(item) for item in evidence.get("visual_plan", []) if item.get("view_type") == "global"]


def init_worker() -> None:
    global _OCR
    threads = max(1, int(_THREADS_PER_WORKER))
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["OPENBLAS_NUM_THREADS"] = str(threads)
    from rapidocr import RapidOCR

    _OCR = RapidOCR(params={
        "Global.use_cls": False,
        "Global.log_level": "error",
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    })


def process_question(task: dict[str, Any]) -> dict[str, Any]:
    import cv2

    capture = cv2.VideoCapture(task["video_path"])
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {task['video_path']}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = []
    try:
        for metadata in task["frames"]:
            frame_index = int(metadata["frame_index"])
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"cannot decode {task['question_id']} frame {frame_index}")
            result = _OCR(image)
            detections = []
            serialized = result.to_json() if result is not None else None
            for detection in serialized or []:
                score = float(detection.get("score", 0.0))
                if score < task["min_score"]:
                    continue
                points = detection.get("box") or []
                if not points:
                    continue
                xs = [float(point[0]) for point in points]
                ys = [float(point[1]) for point in points]
                detections.append({
                    "text": str(detection.get("txt", "")),
                    "score": score,
                    "box": points,
                    "bbox_norm": [min(xs) / width, min(ys) / height, max(xs) / width, max(ys) / height],
                })
            frames.append({
                "sample_rank": int(metadata["sample_rank"]),
                "frame_index": frame_index,
                "timestamp_sec": metadata.get("timestamp_sec"),
                "detections": detections,
            })
    finally:
        capture.release()
    return {
        "question_id": task["question_id"],
        "video_id": task["video_id"],
        "width": width,
        "height": height,
        "frames": frames,
    }


def main() -> None:
    global _THREADS_PER_WORKER
    args = parse_args()
    _THREADS_PER_WORKER = max(1, int(args.threads_per_worker))
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    evidence_by_qid = index_evidence(args.evidence_root)
    tasks = []
    for question in questions:
        qid = str(question["question_id"])
        evidence_path = evidence_by_qid.get(qid)
        if evidence_path is None:
            raise FileNotFoundError(f"missing evidence for {qid}")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        video_id = str(question.get("video", question.get("video_id")))
        frames = selected_frames(evidence)
        if len(frames) == 0:
            raise ValueError(f"no selected global frames for {qid}")
        tasks.append({
            "question_id": qid,
            "video_id": video_id,
            "video_path": str(Path(args.video_root) / f"{video_id}.mp4"),
            "frames": frames,
            "min_score": float(args.min_score),
        })

    started = time.time()
    completed: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=max(1, args.workers), initializer=init_worker) as executor:
        futures = {executor.submit(process_question, task): task["question_id"] for task in tasks}
        for count, future in enumerate(as_completed(futures), start=1):
            item = future.result()
            completed[item["question_id"]] = item
            print(f"ocr {count}/{len(tasks)} {item['question_id']}", flush=True)

    payload = {
        "provenance": {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question_file": str(Path(args.question_file).resolve()),
            "question_file_sha256": sha256_file(args.question_file),
            "evidence_root": str(Path(args.evidence_root).resolve()),
            "video_root": str(Path(args.video_root).resolve()),
            "workers": max(1, args.workers),
            "threads_per_worker": _THREADS_PER_WORKER,
            "min_score": float(args.min_score),
            "python": platform.python_version(),
            "elapsed_seconds": time.time() - started,
        },
        "items": [completed[str(question["question_id"])] for question in questions],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"wrote {output} items={len(payload['items'])}")


if __name__ == "__main__":
    main()
