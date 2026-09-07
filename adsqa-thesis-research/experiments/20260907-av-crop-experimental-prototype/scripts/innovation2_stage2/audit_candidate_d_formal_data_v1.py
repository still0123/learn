#!/usr/bin/env python3
"""Audit candidate-D formal data, including real OCR mosaic pixel changes."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
from typing import Any


FORBIDDEN_INPUT_KEYS = {
    "evidence_state",
    "label",
    "label_provenance",
    "not_human_gold",
    "pairwise_target",
    "reference_answer",
    "role",
    "source_label",
    "source_label_policy",
    "visual_operation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mosaic_patch_changed(task: dict[str, Any]) -> dict[str, Any]:
    from decord import VideoReader, cpu
    from PIL import Image
    import numpy as np

    operation = task["operation"]
    positions = [int(value) for value in operation["mosaic_positions"]]
    boxes = operation["mosaic_boxes_norm"]
    frame_indices = task["frame_indices"]
    reader = VideoReader(task["video_path"], ctx=cpu(0), num_threads=1)
    changed_count = 0
    unchanged_positions: list[int] = []
    for position, box_norm in zip(positions, boxes):
        image = Image.fromarray(
            reader.get_batch([int(frame_indices[position])]).asnumpy()[0]
        ).convert("RGB")
        width, height = image.size
        left = max(0, min(width - 1, int(float(box_norm[0]) * width)))
        top = max(0, min(height - 1, int(float(box_norm[1]) * height)))
        right = max(left + 1, min(width, int(float(box_norm[2]) * width)))
        bottom = max(top + 1, min(height, int(float(box_norm[3]) * height)))
        original = image.crop((left, top, right, bottom))
        reduced = original.resize((1, 1), Image.Resampling.BILINEAR)
        mosaic = reduced.resize(original.size, Image.Resampling.NEAREST)
        if not np.array_equal(np.asarray(original), np.asarray(mosaic)):
            changed_count += 1
        else:
            unchanged_positions.append(position)
    return {
        "pair_id": task["pair_id"],
        "checked_box_count": len(positions),
        "changed_box_count": changed_count,
        "unchanged_positions": unchanged_positions,
        "changed": changed_count > 0,
    }


def main() -> None:
    args = parse_args()
    root = args.dataset_root
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    sources = read_jsonl(root / "source_claims.jsonl")
    inputs = read_jsonl(root / "model_inputs.jsonl")
    pairs = read_jsonl(root / "pairs.jsonl")
    labels = read_jsonl(root / "labels.jsonl")
    inputs_by_id = {row["input_id"]: row for row in inputs}
    tasks: list[dict[str, Any]] = []
    invalid_operations: list[str] = []
    for pair in pairs:
        if pair["required_modality"] != "ocr":
            continue
        operation = pair["negative_plan"].get("visual_operation")
        positions = operation.get("mosaic_positions", []) if isinstance(operation, dict) else []
        boxes = operation.get("mosaic_boxes_norm", []) if isinstance(operation, dict) else []
        negative = inputs_by_id[pair["negative_input_id"]]
        positive = inputs_by_id[pair["positive_input_id"]]
        if (
            not isinstance(operation, dict)
            or operation.get("operation") != "same_area_mosaic"
            or not operation.get("valid")
            or not positions
            or len(positions) != len(boxes)
            or any(not 0 <= int(position) < 32 for position in positions)
            or negative["frame_indices"] != positive["frame_indices"]
        ):
            invalid_operations.append(pair["pair_id"])
            continue
        tasks.append(
            {
                "pair_id": pair["pair_id"],
                "video_path": negative["video_path"],
                "frame_indices": negative["frame_indices"],
                "operation": operation,
            }
        )
    pixel_results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(mosaic_patch_changed, task) for task in tasks]
        for future in as_completed(futures):
            pixel_results.append(future.result())
    pixel_results.sort(key=lambda row: row["pair_id"])
    unchanged_pairs = [row["pair_id"] for row in pixel_results if not row["changed"]]
    forbidden_input_paths = [
        f"model_inputs.jsonl[{index}].{key}"
        for index, row in enumerate(inputs)
        for key in FORBIDDEN_INPUT_KEYS
        if key in row
    ]
    audit = {
        "schema": "adsqa_candidate_d_formal_pixel_audit_v1",
        "source_count": len(sources),
        "pair_count": len(pairs),
        "model_input_count": len(inputs),
        "label_count": len(labels),
        "ocr_pair_count": len(tasks),
        "ocr_pixel_changed_pair_count": sum(row["changed"] for row in pixel_results),
        "ocr_pixel_unchanged_pairs": unchanged_pairs,
        "invalid_ocr_operations": invalid_operations,
        "forbidden_input_paths": forbidden_input_paths,
        "source_not_human_gold": all(row.get("not_human_gold") is True for row in sources),
        "pair_not_human_gold": all(row.get("not_human_gold") is True for row in pairs),
        "label_not_human_gold": all(row.get("not_human_gold") is True for row in labels),
        "manifest_not_human_gold": manifest.get("not_human_gold") is True,
        "manifest_audit_passed": bool(manifest.get("audit", {}).get("passed")),
        "file_sha256": {
            name: sha256_file(root / name)
            for name in (
                "source_claims.jsonl",
                "model_inputs.jsonl",
                "pairs.jsonl",
                "labels.jsonl",
                "manifest.json",
            )
        },
    }
    audit["passed"] = (
        audit["source_count"] == 500
        and audit["pair_count"] == 1000
        and audit["model_input_count"] == 2000
        and audit["label_count"] == 2000
        and audit["ocr_pair_count"] == 500
        and audit["ocr_pixel_changed_pair_count"] == 500
        and not invalid_operations
        and not forbidden_input_paths
        and audit["source_not_human_gold"]
        and audit["pair_not_human_gold"]
        and audit["label_not_human_gold"]
        and audit["manifest_not_human_gold"]
        and audit["manifest_audit_passed"]
    )
    write_json(args.output, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if not audit["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
