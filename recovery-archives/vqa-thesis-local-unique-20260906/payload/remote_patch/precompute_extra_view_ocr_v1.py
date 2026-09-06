#!/usr/bin/env python3
"""Run the same local RapidOCR engine on frozen crop or full extra views."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any


_OCR = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--visual-mode", choices=("crop", "full"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.35)
    parser.add_argument("--size", type=int, default=896)
    return parser.parse_args()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def init_worker() -> None:
    global _OCR
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["OPENBLAS_NUM_THREADS"] = "2"
    from rapidocr import RapidOCR
    _OCR = RapidOCR(params={
        "Global.use_cls": False,
        "Global.log_level": "error",
        "EngineConfig.onnxruntime.intra_op_num_threads": 2,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    })


def process(task: dict[str, Any]) -> dict[str, Any]:
    import cv2

    capture = cv2.VideoCapture(task["video_path"])
    if not capture.isOpened():
        raise RuntimeError("video open failed")
    detections = []
    view_audit = []
    try:
        for view in task["plan"]:
            frame_index = int(view["source_frame_index"])
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, image = capture.read()
            if not ok:
                raise RuntimeError(f"decode failed frame={frame_index}")
            if task["visual_mode"] == "crop":
                x1, y1, x2, y2 = [int(value) for value in view["pixel_box"]]
                image = image[y1:y2, x1:x2]
                if image.size == 0:
                    raise RuntimeError("empty crop")
            image = cv2.resize(image, (task["size"], task["size"]), interpolation=cv2.INTER_CUBIC)
            result = _OCR(image)
            serialized = result.to_json() if result is not None else []
            kept = 0
            for detection in serialized or []:
                score = float(detection.get("score", 0.0))
                text = str(detection.get("txt", "")).strip()
                if score < task["min_score"] or not text:
                    continue
                points = detection.get("box") or []
                xs = [float(point[0]) for point in points]
                ys = [float(point[1]) for point in points]
                bbox = ([min(xs) / task["size"], min(ys) / task["size"],
                         max(xs) / task["size"], max(ys) / task["size"]] if points else None)
                detections.append({
                    "view_id": str(view["view_id"]),
                    "source_frame_index": frame_index,
                    "text": text,
                    "score": score,
                    "bbox_norm_in_view": bbox,
                })
                kept += 1
            view_audit.append({
                "view_id": str(view["view_id"]),
                "source_frame_index": frame_index,
                "detection_count": kept,
                "input_size": [task["size"], task["size"]],
            })
    finally:
        capture.release()
    return {
        "question_id": task["question_id"],
        "video_id": task["video_id"],
        "visual_mode": task["visual_mode"],
        "detections": detections,
        "views": view_audit,
        "answer_fields_read": False,
    }


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite {args.output}")
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    forbidden = {"answer", "answers", "ground_truth", "reference_answer", "meta_info", "label", "judge_score"}
    if any(forbidden & set(row) for row in rows):
        raise RuntimeError("supervision fields found in dataset")
    tasks = []
    for row in rows:
        path = args.plan_root / str(row["question_id"]) / "a2_prediction.json"
        plan_row = json.loads(path.read_text(encoding="utf-8"))
        if plan_row.get("visual_mode") != args.visual_mode or len(plan_row.get("extra_plan", [])) != 4:
            raise RuntimeError(f"invalid frozen plan: {path}")
        tasks.append({
            "question_id": str(row["question_id"]),
            "video_id": str(row["video_id"]),
            "video_path": str(row["video_path"]),
            "visual_mode": args.visual_mode,
            "plan": plan_row["extra_plan"],
            "size": args.size,
            "min_score": args.min_score,
        })
    started = time.time()
    completed = {}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker) as executor:
        futures = {executor.submit(process, task): task["question_id"] for task in tasks}
        for count, future in enumerate(as_completed(futures), 1):
            item = future.result()
            completed[item["question_id"]] = item
            print(f"ocr {args.visual_mode} {count}/{len(tasks)}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ordered = [completed[str(row["question_id"])] for row in rows]
    args.output.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in ordered), encoding="utf-8")
    audit = {
        "schema_version": "extra_view_ocr_cache_v1",
        "visual_mode": args.visual_mode,
        "question_count": len(ordered),
        "view_count": sum(len(row["views"]) for row in ordered),
        "detection_count": sum(len(row["detections"]) for row in ordered),
        "empty_question_count": sum(not row["detections"] for row in ordered),
        "workers": args.workers,
        "min_score": args.min_score,
        "size": args.size,
        "answer_fields_read": False,
        "dataset_sha256": digest(args.dataset),
        "output_sha256": digest(args.output),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    args.output.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
