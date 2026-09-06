#!/usr/bin/env python3
"""Prepare frozen answer-free inputs for the Qwen3 joint Confirm-1000 run."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any


FORBIDDEN = {
    "answer",
    "ground_truth",
    "reference_answer",
    "meta_info",
    "judge_score",
    "prediction",
    "label",
    "score",
}
ALLOWED_ASR_STATUS = {
    "success",
    "no_audio",
    "no_speech",
    "transcription_failed",
}
EXPECTED_MANIFEST_SHA256 = (
    "ac3cd2978c5003ffdb1f10dc83db4ef2db4c9d7be3f6c766349419e7bd8e951a"
)
EXPECTED_QUESTIONS_SHA256 = (
    "87344f000942eba1c9c03d0b43ef70a82e30c809a52ac4ebfed26c8377e5050a"
)
EXPECTED_ASR_AGGREGATE_SHA256 = (
    "084446e1f685647d402115d3284ab368c95b121387ae7880d41b07024e9ebbd6"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--confirm-manifest", type=Path, required=True)
    parser.add_argument("--frozen-marker", type=Path, required=True)
    parser.add_argument("--asr-union-audit", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--ocr-root", type=Path, required=True)
    parser.add_argument("--clip-cache-root", type=Path, required=True)
    parser.add_argument("--asr-root", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def resolve_asr(video_id: str, roots: list[Path]) -> Path:
    matches = [
        root / f"{video_id}.json"
        for root in roots
        if (root / f"{video_id}.json").is_file()
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one ASR record for {video_id}, found {len(matches)}"
        )
    return matches[0]


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    if sha256_file(args.confirm_manifest) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("Confirm-1000 manifest hash changed")
    if args.frozen_marker.read_text(encoding="utf-8").strip() != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("Confirm-1000 FROZEN marker mismatch")
    if sha256_file(args.questions) != EXPECTED_QUESTIONS_SHA256:
        raise RuntimeError("Confirm-1000 questions hash changed")

    union_audit = json.loads(args.asr_union_audit.read_text(encoding="utf-8"))
    if (
        union_audit.get("passed") is not True
        or int(union_audit.get("record_count", -1)) != 1000
        or union_audit.get("aggregate_sha256") != EXPECTED_ASR_AGGREGATE_SHA256
    ):
        raise RuntimeError("segmented-ASR union audit is not the frozen 1000-video asset")

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    required = {
        "question_id",
        "video",
        "question",
        "question_type",
        "primary_type",
        "confirm_shard",
    }
    if (
        not isinstance(questions, list)
        or len(questions) != 1000
        or any(not required.issubset(row) for row in questions)
        or any(FORBIDDEN & set(row) for row in questions)
    ):
        raise RuntimeError("invalid frozen answer-free Confirm-1000 schema")

    prepared = []
    for row in questions:
        fold = int(row["confirm_shard"])
        primary_type = str(row["primary_type"])
        if fold not in range(5) or primary_type not in {
            f"Type_{index}" for index in range(1, 6)
        }:
            raise RuntimeError("invalid frozen shard or primary type")
        prepared.append(
            {
                "question_id": str(row["question_id"]),
                "video": str(row["video"]),
                "question": str(row["question"]),
                "question_type": [primary_type],
                "primary_type": primary_type,
                "fold": fold,
                "source_split": "qwen3_joint_confirm1000_v1_method_level_confirm",
            }
        )
    prepared.sort(key=lambda row: (int(row["fold"]), str(row["question_id"])))
    videos = {str(row["video"]) for row in prepared}
    if len(videos) != 1000:
        raise RuntimeError("Confirm-1000 is not unique-video")
    fold_counts = Counter(int(row["fold"]) for row in prepared)
    fold_type_counts = {
        str(fold): dict(
            Counter(
                row["primary_type"]
                for row in prepared
                if int(row["fold"]) == fold
            )
        )
        for fold in range(5)
    }
    if fold_counts != Counter({fold: 200 for fold in range(5)}):
        raise RuntimeError(f"runtime shard balance failed: {fold_counts}")
    expected_types = {f"Type_{index}": 40 for index in range(1, 6)}
    if any(counts != expected_types for counts in fold_type_counts.values()):
        raise RuntimeError(f"runtime type balance failed: {fold_type_counts}")

    coverage = Counter()
    asr_status = Counter()
    asr_combined: dict[str, Any] = {}
    inventory = []
    union_root = args.output_dir / "asr_union_records"
    union_root.mkdir(parents=True, exist_ok=False)
    for row in prepared:
        video_id = str(row["video"])
        video_path = args.video_root / f"{video_id}.mp4"
        ocr_path = args.ocr_root / f"{video_id}.json"
        clip_path = args.clip_cache_root / f"{video_id}.npz"
        asr_path = resolve_asr(video_id, args.asr_root)
        for key, path in (
            ("video", video_path),
            ("ocr", ocr_path),
            ("clip", clip_path),
            ("asr", asr_path),
        ):
            coverage[key] += int(path.is_file())
        if not all(
            path.is_file()
            for path in (video_path, ocr_path, clip_path, asr_path)
        ):
            raise RuntimeError(f"missing frozen cache for {video_id}")
        asr_payload = json.loads(asr_path.read_text(encoding="utf-8"))
        status = str(asr_payload.get("status"))
        if status not in ALLOWED_ASR_STATUS:
            raise RuntimeError(f"invalid ASR status for {video_id}: {status}")
        asr_status[status] += 1
        asr_combined[video_id] = {
            "transcript": str(asr_payload.get("text") or ""),
            "status": status,
        }
        link_path = union_root / f"{video_id}.json"
        os.symlink(asr_path.resolve(), link_path)
        inventory.append(
            {
                "question_id": str(row["question_id"]),
                "video_id": video_id,
                "fold": int(row["fold"]),
                "primary_type": row["primary_type"],
                "video_path": str(video_path.resolve()),
                "ocr_path": str(ocr_path.resolve()),
                "clip_path": str(clip_path.resolve()),
                "asr_path": str(asr_path.resolve()),
                "ocr_sha256": sha256_file(ocr_path),
                "clip_sha256": sha256_file(clip_path),
                "asr_sha256": sha256_file(asr_path),
                "asr_status": status,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    questions_path = args.output_dir / "questions_answer_free.json"
    dump_json(questions_path, prepared)
    dump_json(args.output_dir / "asr_combined_answer_free.json", asr_combined)
    for fold in range(5):
        shard = [row for row in prepared if int(row["fold"]) == fold]
        dump_json(args.output_dir / "a0_shards" / f"fold_{fold}.json", shard)
        dump_json(
            args.output_dir / "raw_feature_shards" / f"shard_{fold}.json",
            shard,
        )
    inventory_path = args.output_dir / "cache_inventory.jsonl"
    inventory_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in inventory
        ),
        encoding="utf-8",
    )
    audit = {
        "schema_version": "qwen3_selective_rewrite_confirm1000_prepare_audit_v1",
        "question_count": len(prepared),
        "video_count": len(videos),
        "type_counts": dict(Counter(row["primary_type"] for row in prepared)),
        "runtime_fold_counts": {
            str(key): value for key, value in sorted(fold_counts.items())
        },
        "runtime_fold_type_counts": fold_type_counts,
        "cache_coverage": dict(coverage),
        "asr_status_counts": dict(asr_status),
        "answer_free": True,
        "groundtruth_read": False,
        "judge_scores_read": False,
        "independence_scope": "method_level_confirm_not_global_blind",
        "source_questions_sha256": sha256_file(args.questions),
        "source_manifest_sha256": sha256_file(args.confirm_manifest),
        "asr_union_audit_sha256": sha256_file(args.asr_union_audit),
        "asr_union_aggregate_sha256": union_audit["aggregate_sha256"],
        "prepared_questions_sha256": sha256_file(questions_path),
        "cache_inventory_sha256": sha256_file(inventory_path),
        "passed": (
            len(prepared) == 1000
            and len(videos) == 1000
            and all(coverage[key] == 1000 for key in ("video", "ocr", "clip", "asr"))
        ),
    }
    dump_json(args.output_dir / "audit.json", audit)
    if not audit["passed"]:
        raise RuntimeError("Confirm-1000 preparation audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
