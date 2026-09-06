#!/usr/bin/env python3
"""Freeze Confirm-100 region-only choices without reading judge scores."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.95)
    parser.add_argument("--margin", type=float, default=0.03)
    args = parser.parse_args()
    master = {str(row["question_id"]): row for row in rows(args.base_root / "confirm100_master_answer_free.jsonl")}
    items = {str(row["question_id"]): row for row in rows(args.items)}
    candidate = {}
    for path in (args.run_root / "inference").glob("shard*/*/a2_prediction.json"):
        row = json.loads(path.read_text())
        candidate[str(row["question_id"])] = str(row["prediction"])
    support = {str(row["source_question_id"]): float(row["support_probability"]) for row in rows(args.run_root / "verifier_scores_v1" / "scores_all.jsonl")}
    choices = []
    for qid, row in sorted(master.items()):
        a0 = str(items[qid]["a0_prediction"])
        a2 = candidate.get(qid, a0)
        p0 = float(row["support_probability"])
        p2 = support.get(qid, p0)
        changed = norm(a2) != norm(a0)
        switch = row["action"] == "LOOK_REGION" and changed and p2 >= args.threshold and p2 - p0 >= args.margin
        final = a2 if switch else a0
        choices.append({
            "question_id": qid, "video_id": row["video_id"], "action": row["action"],
            "a0_prediction": a0, "candidate_prediction": a2,
            "final_prediction": final, "switched": switch,
            "p0": p0, "p2": p2, "support_margin": p2 - p0,
            "threshold": args.threshold, "minimum_margin": args.margin,
            "final_sha256": hashlib.sha256(norm(final).encode()).hexdigest(),
            "answer_free": True, "not_human_gold": True,
        })
    if len(choices) != 100:
        raise RuntimeError("Confirm-100 population changed")
    args.output_root.mkdir(parents=True, exist_ok=False)
    (args.output_root / "choices_answer_free.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in choices))
    audit = {
        "schema_version": "qwen25_region_gate_confirm100_choices_v1",
        "count": 100, "switched": sum(row["switched"] for row in choices),
        "threshold": args.threshold, "minimum_margin": args.margin,
        "gate_source": "Confirm60B coarse calibration; p2>=0.95 and margin>=0.03; REGION only",
        "judge_scores_read": False, "groundtruth_read": False,
    }
    (args.output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output_root / "CHOICES_FROZEN").write_text("complete\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
