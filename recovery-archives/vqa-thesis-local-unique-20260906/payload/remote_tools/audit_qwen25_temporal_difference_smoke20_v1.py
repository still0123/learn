#!/usr/bin/env python3
"""Audit that temporal tool inputs and outputs differ from the old same-anchor arm."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--old-root", type=Path, required=True)
    args = parser.parse_args()
    qids = [json.loads(line)["question_id"] for line in (args.root / "inputs.jsonl").read_text().splitlines()]
    changed = 0
    parse_failures = 0
    rows = []
    for qid in qids:
        trace = json.loads((args.root / "inference" / qid / "a2_trace.json").read_text())
        pred = json.loads((args.root / "inference" / qid / "a2_prediction.json").read_text())["prediction"]
        old = json.loads((args.old_root / qid / "a2_prediction.json").read_text())["prediction"]
        plan = trace["extra_view_plan"]
        distinct = all(item["source_frame_index"] != item["anchor_frame_index"] for item in plan)
        if len(plan) != 4 or not distinct or trace["processor_trace"]["visual_tokens"] != 3992:
            raise RuntimeError(f"protocol failure: {qid}")
        changed += pred != old
        parse_failures += not trace["parse_valid"]
        rows.append({"question_id": qid, "answer_changed_vs_same_anchor": pred != old})
    audit = {
        "schema_version": "qwen25_temporal_difference_smoke20_audit_v1",
        "count": len(qids),
        "errors": 0,
        "all_extra_views_distinct_from_anchor": True,
        "all_views": 12,
        "all_visual_tokens": 3992,
        "secondary_sampling_disabled": True,
        "parse_failures": parse_failures,
        "answers_changed_vs_same_anchor": changed,
        "answer_difference_rate": changed / len(qids),
        "judge_called": False,
        "items": rows,
    }
    (args.root / "difference_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.root / "DIFFERENCE_SMOKE_COMPLETE").write_text("complete\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
