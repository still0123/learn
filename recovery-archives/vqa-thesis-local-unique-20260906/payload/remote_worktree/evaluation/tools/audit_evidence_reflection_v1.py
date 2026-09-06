#!/usr/bin/env python3
"""Audit fixed-input reflection outputs against the frozen Raw32 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/data1/rmx/projectb/AdsQA-main")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from evaluation.methods.evidence_reflection.reflection_protocol import visual_plan_sha256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-count", type=int, default=100)
    args = parser.parse_args()
    freeze_path = Path(args.freeze_manifest)
    run_dir = Path(args.run_dir)
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    records = freeze.get("records", [])
    expected = {str(row["question_id"]): row for row in records}
    errors: list[dict[str, Any]] = []
    observed: set[str] = set()
    parsed = 0
    fallback = 0
    for qid, frozen in sorted(expected.items()):
        prediction_path = run_dir / qid / "prediction.json"
        reflection_path = run_dir / qid / "reflection.json"
        if not prediction_path.exists() or not reflection_path.exists():
            errors.append({"question_id": qid, "error": "missing_prediction_or_trace"})
            continue
        try:
            prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
            trace = json.loads(reflection_path.read_text(encoding="utf-8"))
            observed.add(qid)
            if str(prediction.get("question_id")) != qid or str(trace.get("question_id")) != qid:
                errors.append({"question_id": qid, "error": "question_id_mismatch"})
            if int(trace.get("input_image_count", 32)) != 32:
                errors.append({"question_id": qid, "error": "view_count_mismatch"})
            processor = trace.get("processor_trace", {})
            if int(processor.get("post_merge_visual_token_count", 0)) != 11664:
                errors.append({"question_id": qid, "error": "visual_token_mismatch", "value": processor.get("post_merge_visual_token_count")})
            if processor.get("secondary_frame_sampling_disabled") is not True:
                errors.append({"question_id": qid, "error": "secondary_sampling_not_disabled"})
            if trace.get("rag_enabled") is not False or trace.get("new_visual_sampling") is not False:
                errors.append({"question_id": qid, "error": "protocol_feature_enabled"})
            if trace.get("groundtruth_loaded_by_inference") is not False:
                errors.append({"question_id": qid, "error": "groundtruth_loaded"})
            expected_plan_hash = visual_plan_sha256(frozen.get("visual_plan", []))
            if trace.get("visual_plan_sha256") != expected_plan_hash:
                errors.append({"question_id": qid, "error": "visual_plan_drift"})
            if not str(trace.get("visual_input_sha256", "")):
                errors.append({"question_id": qid, "error": "missing_visual_input_hash"})
            parse_status = str(trace.get("reflection_parsed", {}).get("parse_status", ""))
            if parse_status == "unparsed":
                fallback += 1
            else:
                parsed += 1
            if not str(prediction.get("prediction", "")).strip():
                errors.append({"question_id": qid, "error": "empty_final_answer"})
        except Exception as exc:
            errors.append({"question_id": qid, "error": repr(exc)})
    extra = sorted(set(p.parent.name for p in run_dir.glob("*/prediction.json")) - set(expected))
    payload = {
        "schema": "adsqa_evidence_reflection_audit_v1",
        "freeze_manifest": str(freeze_path),
        "freeze_manifest_sha256": sha256_file(freeze_path),
        "run_dir": str(run_dir),
        "expected_count": int(args.expected_count),
        "observed_count": len(observed),
        "parsed_count": parsed,
        "fallback_keep_count": fallback,
        "extra_qids": extra,
        "errors": errors,
        "complete": len(observed) == int(args.expected_count),
        "passed": len(observed) == int(args.expected_count) and not errors and not extra,
    }
    dump_json(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
