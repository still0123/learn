#!/usr/bin/env python3
"""Freeze the existing audited Raw32 draft and evidence for reflection intervention."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    question_file = Path(args.question_file)
    questions = json.loads(question_file.read_text(encoding="utf-8"))
    if len(questions) != 100:
        raise RuntimeError(f"expected Dev100, got {len(questions)}")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for global_idx, item in enumerate(questions):
        qid = str(item["question_id"])
        matches = sorted(Path(args.raw_root).glob(f"shard*of3/initial/{qid}/prediction.json"))
        if len(matches) != 1:
            raise RuntimeError(f"expected one baseline prediction for {qid}, got {len(matches)}")
        prediction_path = matches[0]
        evidence_path = prediction_path.parent / "evidence.json"
        if not evidence_path.exists():
            raise RuntimeError(f"missing baseline evidence for {qid}")
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        protocol = evidence.get("fair_protocol", {})
        trace = evidence.get("processor_trace", {})
        plan = evidence.get("visual_plan", [])
        if str(prediction.get("question_id")) != qid or str(evidence.get("question_id")) != qid:
            raise RuntimeError(f"question id mismatch for {qid}")
        if protocol.get("method") != "raw_uniform" or len(plan) != 32:
            raise RuntimeError(f"baseline is not audited Raw32 for {qid}")
        if int(evidence.get("input_image_count", 0)) != 32:
            raise RuntimeError(f"baseline view count mismatch for {qid}")
        if int(trace.get("post_merge_visual_token_count", 0)) != 11664:
            raise RuntimeError(f"baseline visual token mismatch for {qid}")
        if trace.get("secondary_frame_sampling_disabled") is not True:
            raise RuntimeError(f"baseline secondary sampling was not disabled for {qid}")
        if qid in seen:
            raise RuntimeError(f"duplicate qid {qid}")
        seen.add(qid)
        records.append({
            "global_idx": global_idx,
            "question_id": qid,
            "video": str(item.get("video", item.get("video_id", ""))),
            "prediction_path": str(prediction_path),
            "evidence_path": str(evidence_path),
            "prediction_sha256": sha256_file(prediction_path),
            "evidence_sha256": sha256_file(evidence_path),
            "draft_prediction": str(prediction.get("prediction", "")),
            "visual_plan": plan,
            "processor_trace": {
                "post_merge_visual_token_count": trace.get("post_merge_visual_token_count"),
                "represented_frame_count": trace.get("represented_frame_count"),
                "submitted_frame_count": trace.get("submitted_frame_count"),
                "secondary_frame_sampling_disabled": trace.get("secondary_frame_sampling_disabled"),
            },
        })
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "adsqa_evidence_reflection_dev100_freeze_v1",
        "protocol": "evidence_reflection_fixed_raw32_v1",
        "question_file": str(question_file),
        "question_file_sha256": sha256_file(question_file),
        "raw_root": str(Path(args.raw_root)),
        "expected_count": 100,
        "records": records,
        "formal_testset_mutation_allowed": False,
        "groundtruth_loaded_by_inference": False,
    }
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "count": len(records), "sha256": sha256_file(output)}, indent=2))


if __name__ == "__main__":
    main()
