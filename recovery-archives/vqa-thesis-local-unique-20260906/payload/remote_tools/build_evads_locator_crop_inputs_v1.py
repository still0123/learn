#!/usr/bin/env python3
"""Freeze E-VAds SFT locator-crop screening and confirmation inputs."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from build_evads_mmr_selectrescue_trigger100_v1 import (
    FORBIDDEN,
    load_jsonl,
    parse_events,
    select_text_evidence,
)


VARIANTS = ("anchor_global10", "crop_minimap10", "locator_inset10")
CANDIDATES = VARIANTS[1:]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-dir", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--av-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-questions", type=int, default=500)
    parser.add_argument("--screen-only", action="store_true")
    parser.add_argument("--confirmation-only", action="store_true")
    return parser.parse_args()


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    args = parse_args()
    if (
        args.expected_questions <= 0
        or args.screen_only and args.confirmation_only
        or (
            (args.screen_only or args.confirmation_only)
            and args.expected_questions % 5
        )
    ):
        raise RuntimeError("expected questions must be positive and foldable")
    if args.output_root.exists():
        raise RuntimeError("output root already exists")
    questions = json.loads(args.questions.read_text())
    question_by_id = {str(row["question_id"]): row for row in questions}
    if (
        len(question_by_id) != args.expected_questions
        or any(FORBIDDEN & set(row) for row in questions)
        or args.screen_only
        and any(row.get("dev_stage") != "screen" for row in questions)
        or args.confirmation_only
        and any(row.get("dev_stage") != "confirmation" for row in questions)
    ):
        raise RuntimeError("questions are not the frozen answer-free input")
    pool = {
        str(row["source_question_id"]): row
        for row in load_jsonl(args.pool_dir / "model_inputs_all.jsonl")
    }
    sources = {
        str(row["question_id"]): row
        for row in load_jsonl(args.pool_dir / "source_manifest.jsonl")
    }
    av = {
        str(row["question_id"]): row for row in load_jsonl(args.av_manifest)
    }
    if set(pool) != set(question_by_id) or set(av) != set(question_by_id):
        raise RuntimeError("A0 pool, questions, and AV manifest do not align")

    base_rows = []
    for qid in sorted(question_by_id):
        question = question_by_id[qid]
        source = pool[qid]
        events, _ = parse_events(str(question["multimodal_context"]))
        ocr, asr = select_text_evidence(str(question["question"]), events)
        mid_specs = sorted(
            (
                spec
                for spec in av[qid]["funnel_crop_specs"]
                if str(spec["scale_level"]) == "mid"
            ),
            key=lambda spec: int(spec["anchor_index"]),
        )
        if len(mid_specs) != 2:
            raise RuntimeError(f"missing two mid anchors: {qid}")
        anchors = [{
            "anchor_index": int(spec["anchor_index"]),
            "source_global_rank": int(spec["source_global_rank"]),
            "source_frame_index": int(spec["source_frame_index"]),
            "bbox_norm": [float(value) for value in spec["bbox_norm"]],
            "bbox_source": "siglip_3x3_grid_response",
            "fusion_score": float(spec["fusion_score"]),
            "visual_rank_score": float(spec["visual_rank_score"]),
            "asr_rank_score": float(spec["asr_score"]),
            "ocr_rank_score": float(spec["ocr_score"]),
            "crop_mode": "evads_av_funnel_mid_v1",
        } for spec in mid_specs]
        base_rows.append({
            "question_id": qid,
            "video_id": str(question["video"]),
            "fold": int(question["fold"]),
            "dev_stage": str(question["dev_stage"]),
            "question": str(question["question"]),
            "a0_prediction": str(source["claim"]),
            "a0_asr_excerpt": str(source.get("asr_excerpt", "")),
            "a0_frame_indices": [
                int(value) for value in source["selected_frame_indices"]
            ],
            "video_path": str(source["video_path"]),
            "evidence_anchors": anchors,
            "ocr_evidence": ocr,
            "ocr_quality": {
                "status": "official_time_aligned_text",
                "selected_count": len(ocr),
            },
            "asr_evidence": asr,
            "asr_quality": {
                "status": "official_time_aligned_text",
                "selected_count": len(asr),
            },
            "asr_full_text": str(source.get("asr_excerpt", "")),
            "a0_source_sha256": sources[qid]["a0_prediction_sha256"],
        })

    args.output_root.mkdir(parents=True, exist_ok=False)
    files = {}
    screen = [row for row in base_rows if row["dev_stage"] == "screen"]
    confirmation = [
        row for row in base_rows if row["dev_stage"] == "confirmation"
    ]
    screen_variants = (
        ("anchor_global10",)
        if args.screen_only or args.confirmation_only
        else VARIANTS
    )
    for fold in range(5):
        if args.confirmation_only:
            rows = [
                {**row, "view_variant": "anchor_global10"}
                for row in confirmation
                if int(row["fold"]) == fold
            ]
            path = (
                args.output_root
                / "confirmation"
                / "shards"
                / f"fold_{fold}.jsonl"
            )
            write_jsonl(path, rows)
            files[str(path.relative_to(args.output_root))] = sha256(path)
            continue
        rows = [
            {**row, "view_variant": variant}
            for row in screen
            if int(row["fold"]) == fold
            for variant in screen_variants
        ]
        path = args.output_root / "screen" / "shards" / f"fold_{fold}.jsonl"
        write_jsonl(path, rows)
        files[str(path.relative_to(args.output_root))] = sha256(path)
        if args.screen_only:
            continue
        for candidate in CANDIDATES:
            pair = [
                {**row, "view_variant": variant}
                for row in confirmation
                if int(row["fold"]) == fold
                for variant in ("anchor_global10", candidate)
            ]
            path = (
                args.output_root
                / "confirmation_pairs"
                / candidate
                / f"fold_{fold}.jsonl"
            )
            write_jsonl(path, pair)
            files[str(path.relative_to(args.output_root))] = sha256(path)
    audit = {
        "schema_version": (
            "evads_qwen3_policy_screen_base_inputs_v1"
            if args.screen_only
            else "evads_qwen3_policy_confirmation_base_inputs_v1"
            if args.confirmation_only
            else "evads_qwen3_locator_crop_sftdev500_inputs_v1"
        ),
        "passed": (
            len(base_rows) == args.expected_questions
            and (
                (
                    args.screen_only
                    and len(screen) == args.expected_questions
                    and not confirmation
                    and Counter(int(row["fold"]) for row in screen)
                    == Counter({
                        fold: args.expected_questions // 5
                        for fold in range(5)
                    })
                )
                or (
                    args.confirmation_only
                    and not screen
                    and len(confirmation) == args.expected_questions
                    and Counter(int(row["fold"]) for row in confirmation)
                    == Counter({
                        fold: args.expected_questions // 5
                        for fold in range(5)
                    })
                )
                or (
                    not args.screen_only
                    and len(screen) == 100
                    and len(confirmation) == 400
                    and Counter(int(row["fold"]) for row in screen)
                    == Counter({fold: 20 for fold in range(5)})
                    and Counter(int(row["fold"]) for row in confirmation)
                    == Counter({fold: 80 for fold in range(5)})
                )
            )
        ),
        "question_count": len(base_rows),
        "video_count": len({row["video_id"] for row in base_rows}),
        "screen_question_count": len(screen),
        "confirmation_question_count": len(confirmation),
        "variants": list(screen_variants),
        "screen_rows_per_variant": len(screen),
        "confirmation_rows_per_variant": (
            0 if args.screen_only else len(confirmation)
        ),
        "same_mmr8_a0": True,
        "same_anchor_times": True,
        "same_ocr_asr": True,
        "views": 10,
        "visual_tokens": 2592,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "questions_sha256": sha256(args.questions),
        "pool_sha256": sha256(args.pool_dir / "model_inputs_all.jsonl"),
        "av_manifest_sha256": sha256(args.av_manifest),
        "files_sha256": files,
    }
    (args.output_root / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
