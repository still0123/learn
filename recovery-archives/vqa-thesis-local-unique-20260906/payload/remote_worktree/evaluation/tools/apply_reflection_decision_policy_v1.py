#!/usr/bin/env python3
"""Apply the declared KEEP/REVISE policy without changing visual inference."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
import sys

PROJECT_ROOT = Path("/data1/rmx/projectb/AdsQA-main")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from evaluation.methods.evidence_reflection.reflection_protocol import extract_answer_section


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--variants", nargs="+", default=["generic", "structured", "conservative"])
    args = parser.parse_args()
    root = Path(args.run_root)
    report = {"schema": "adsqa_reflection_decision_policy_audit_v1", "variants": {}}
    for variant in args.variants:
        counters = Counter()
        changed = 0
        for trace_path in sorted((root / variant).glob("*/reflection.json")):
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            prediction_path = trace_path.parent / "prediction.json"
            prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
            parsed = trace.get("reflection_parsed", {})
            draft_answer = extract_answer_section(str(trace.get("draft_answer", ""))).strip()
            parsed_answer = str(parsed.get("final_answer", "")).strip()
            decision = str(parsed.get("decision", "keep")).lower()
            parse_status = str(parsed.get("parse_status", "unparsed"))
            allow_revision = parse_status != "unparsed" and decision == "revise" and bool(parsed_answer)
            effective = parsed_answer if allow_revision else draft_answer
            policy_status = "revised" if allow_revision else "kept_draft"
            if effective != str(prediction.get("prediction", "")).strip():
                changed += 1
            prediction["prediction"] = effective
            prediction["reflection_policy"] = "keep_on_non_revise_v1"
            prediction["reflection_policy_status"] = policy_status
            dump_json(prediction_path, prediction)
            trace["effective_final_answer"] = effective
            trace["effective_policy"] = {
                "name": "keep_on_non_revise_v1",
                "allow_revision": allow_revision,
                "status": policy_status,
                "draft_answer_sha256": __import__("hashlib").sha256(draft_answer.encode()).hexdigest(),
            }
            dump_json(trace_path, trace)
            counters[policy_status] += 1
        report["variants"][variant] = {
            "items": sum(counters.values()),
            "policy_counts": dict(sorted(counters.items())),
            "prediction_files_changed": changed,
        }
    out = root / "reflection_decision_policy_audit_v1.json"
    dump_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
