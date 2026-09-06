#!/usr/bin/env python3
"""Audit a Qwen2.5 fair-budget run and emit per-question input-plan hashes."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--question-file", required=True)
    parser.add_argument("--expected-visual-tokens", type=int, required=True)
    parser.add_argument("--model-label", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    questions = json.loads(Path(args.question_file).read_text(encoding="utf-8"))
    expected = {str(item["question_id"]) for item in questions}
    observed = set()
    records: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for qdir in sorted(p for p in run_dir.iterdir() if p.is_dir() and p.name != "logs"):
        qid = qdir.name
        pred_path = qdir / "prediction.json"
        evidence_path = qdir / "evidence.json"
        observed.add(qid)
        if not pred_path.exists() or not evidence_path.exists():
            failures.append({"question_id": qid, "error": "missing_prediction_or_evidence"})
            continue
        try:
            pred = load_json(pred_path)
            evidence = load_json(evidence_path)
            trace = evidence.get("processor_trace", {})
            checks = {
                "question_id_match": str(evidence.get("question_id")) == qid,
                "model_label_present": args.model_label in str(pred.get("pipeline", "")),
                "input_image_count_32": evidence.get("input_image_count") == 32,
                "submitted_frame_count_32": trace.get("submitted_frame_count") == 32,
                "represented_frame_count_32": trace.get("represented_frame_count") == 32,
                "secondary_sampling_disabled": trace.get("secondary_frame_sampling_disabled") is True,
                "visual_token_budget": trace.get("post_merge_visual_token_count") == args.expected_visual_tokens,
                "visual_token_budget_respected": trace.get("visual_token_budget_respected") is True,
                "no_temporal_padding": trace.get("temporal_padding_frame_count") == 0,
            }
            plan = {
                "video_id": evidence.get("video_id"),
                "video_path": evidence.get("video_path"),
                "fair_protocol": evidence.get("fair_protocol"),
                "visual_plan": evidence.get("visual_plan"),
                "processor_trace": {
                    "frame_indices": trace.get("frame_indices"),
                    "video_grid_thw": trace.get("video_grid_thw"),
                    "represented_frame_count": trace.get("represented_frame_count"),
                    "submitted_frame_count": trace.get("submitted_frame_count"),
                    "post_merge_visual_token_count": trace.get("post_merge_visual_token_count"),
                    "secondary_frame_sampling_disabled": trace.get("secondary_frame_sampling_disabled"),
                },
            }
            plan_hash = canonical_sha256(plan)
            record = {"question_id": qid, "input_plan_sha256": plan_hash, "checks": checks}
            records.append(record)
            for name, passed in checks.items():
                if not passed:
                    failures.append({"question_id": qid, "error": name})
        except Exception as exc:
            failures.append({"question_id": qid, "error": repr(exc)})

    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    for qid in missing:
        failures.append({"question_id": qid, "error": "missing_question_output"})
    for qid in extra:
        failures.append({"question_id": qid, "error": "extra_question_output"})

    result = {
        "schema": "adsqa_qwen25_fair_run_audit_v1",
        "run_dir": str(run_dir),
        "question_file": args.question_file,
        "expected_count": len(expected),
        "observed_count": len(observed),
        "audited_count": len(records),
        "missing_qids": missing,
        "extra_qids": extra,
        "failure_count": len(failures),
        "failures": failures,
        "complete": len(expected) == len(observed) and not missing and not extra,
        "passed": not failures and len(records) == len(expected),
        "expected_visual_tokens": args.expected_visual_tokens,
        "model_label": args.model_label,
        "records": records,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("expected_count", "observed_count", "audited_count", "failure_count", "complete", "passed")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
