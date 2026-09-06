#!/usr/bin/env python3
"""Build the frozen 32-global plus 8 CLIP-local plan for Fresh Confirm-500."""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any

sys.modules["torchcodec"] = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    PROTOCOL_VERSION,
    RAW_GLOBAL_VIEW_COUNT,
    canonical_json_sha256,
    sha256_file,
    validate_shared_gate_manifest,
)
from evaluation.tools.build_qwen25_modality_active_manifest_v1 import Planner  # noqa: E402
from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import (  # noqa: E402
    ensure_idle_allowed_gpu,
    load_answer_free_questions,
    resolve_video_path,
)
from evaluation.tools.fresh_confirm_decode import (  # noqa: E402
    FALLBACK_EVENTS,
    robust_load_uniform_frames,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", required=True, choices=["4"])
    parser.add_argument("--questions", required=True)
    parser.add_argument("--clip-path", default=str(PROJECT_ROOT / "models/clip-vit-large-patch14"))
    parser.add_argument("--video-root", default=str(PROJECT_ROOT / "data/videos"))
    parser.add_argument("--frames-fallback-root", default=str(PROJECT_ROOT / "data/frames_8"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-items", type=int, default=-1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    questions_path = Path(args.questions).resolve()
    output_path = Path(args.output).resolve()
    if output_path.exists() and not args.overwrite:
        raise ValueError(f"output exists: {output_path}")
    questions = load_answer_free_questions(questions_path)
    if args.max_items > 0:
        questions = questions[: args.max_items]
    if not questions:
        raise ValueError("no questions selected")

    gpu_snapshot = ensure_idle_allowed_gpu(args.gpu_id)
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = output_path.parent / "logs/build_clip_manifest_gpu4.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logger = logging.getLogger("fresh_confirm500_clip_manifest")
    planner = Planner(args.clip_path, "cuda")
    video_root = Path(args.video_root)
    fallback_root = Path(args.frames_fallback_root)
    records: list[dict[str, Any]] = []
    started = time.time()

    for index, item in enumerate(questions, start=1):
        question_id = str(item["question_id"])
        video = str(item["video"])
        frames, frame_metadata = robust_load_uniform_frames(
            resolve_video_path(video, video_root, fallback_root),
            RAW_GLOBAL_VIEW_COUNT,
        )
        plan = planner.plan(
            frames,
            frame_metadata,
            str(item["question"]),
            [],
            [],
        )
        clip_specs = plan["clip_crop_specs"]
        if len(clip_specs) != APPENDED_LOCAL_VIEW_COUNT:
            raise ValueError(f"question {question_id} does not have eight CLIP crops")
        gate_decision = {
            "protocol_version": PROTOCOL_VERSION,
            "gate_rule": {
                "version": "fresh_confirm500_always_clip_local8_v1",
                "fit_scope": "none_frozen_before_confirmation_inference",
            },
            "modality_route": "clip_question_patch_response",
            "modality_active": False,
            "criteria": {
                "fixed_global_context": True,
                "fixed_local_budget": True,
                "question_conditioned_visual_plan": True,
            },
            "append_crop8": True,
            "local_view_count": APPENDED_LOCAL_VIEW_COUNT,
            "submitted_view_count": RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT,
            "decision_reason": "frozen_confirmation_method",
        }
        record = {
            "schema_version": "fresh_confirm500_clipcrop40_manifest_v1",
            "question_id": question_id,
            "video_id": video,
            "fold": int(item.get("fold", 0)),
            "append_crop8": True,
            "local_view_count": APPENDED_LOCAL_VIEW_COUNT,
            "submitted_view_count": RAW_GLOBAL_VIEW_COUNT + APPENDED_LOCAL_VIEW_COUNT,
            "gate_decision": gate_decision,
            "clip_crop_specs": clip_specs,
            "av_crop_specs": clip_specs,
            "raw_feature_sha256": canonical_json_sha256(
                {
                    "question_id": question_id,
                    "video_id": video,
                    "query_text_sha256": plan["query_text_sha256"],
                    "clip_crop_specs": clip_specs,
                }
            ),
            "manifest_inputs": {
                "questions_sha256": sha256_file(questions_path),
                "clip_path": str(Path(args.clip_path).resolve()),
            },
        }
        records.append(record)
        if index % 25 == 0:
            logger.info("processed=%d/%d elapsed=%.1f", index, len(questions), time.time() - started)
        gc.collect()
        planner.torch.cuda.empty_cache()

    records.sort(key=lambda row: str(row["question_id"]))
    manifest_audit = validate_shared_gate_manifest(records)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in records),
        encoding="utf-8",
    )
    temporary.replace(output_path)
    audit = {
        "schema_version": "fresh_confirm500_clipcrop40_manifest_audit_v1",
        "passed": (
            len(records) == len(questions)
            and manifest_audit["record_count"] == len(questions)
            and manifest_audit["gate_hit_count"] == len(questions)
        ),
        "record_count": len(records),
        "video_count": len({row["video_id"] for row in records}),
        "manifest_audit": manifest_audit,
        "gpu_snapshot_before_load": gpu_snapshot,
        "questions_sha256": sha256_file(questions_path),
        "output_manifest_sha256": sha256_file(output_path),
        "groundtruth_read": False,
        "outcome_fields_used": False,
        "decode_fallback_count": len(FALLBACK_EVENTS),
        "decode_fallback_video_paths": sorted(
            {str(row["video_path"]) for row in FALLBACK_EVENTS}
        ),
        "elapsed_seconds": time.time() - started,
    }
    audit_path = output_path.with_suffix(".audit.json")
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=True, indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
