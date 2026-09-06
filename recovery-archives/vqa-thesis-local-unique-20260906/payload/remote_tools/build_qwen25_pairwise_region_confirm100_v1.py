#!/usr/bin/env python3
"""Build answer-free changed-candidate inputs for symmetric pairwise election."""

import hashlib
import json
from pathlib import Path
import re


ROOT = Path("evaluation/runs/qwen25_active_evidence_look_v1")
SOURCE = ROOT / "confirm100_v1/inputs/active_region.jsonl"
CANDIDATES = ROOT / "region_gate_confirm100_v1/inference"
OUT = ROOT / "pairwise_region_confirm100_v1/inputs"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


rows = read_jsonl(SOURCE)
predictions = {}
for path in CANDIDATES.glob("shard*/*/a2_prediction.json"):
    item = json.loads(path.read_text())
    predictions[str(item["question_id"])] = item

changed = []
for row in rows:
    qid = str(row["question_id"])
    candidate = predictions[qid]["prediction"]
    if norm(candidate) == norm(row["a0_prediction"]):
        continue
    changed.append({
        **row,
        "candidate_prediction": candidate,
        "candidate_method": predictions[qid]["method"],
    })

assert len(rows) == len(predictions) == 53
assert len(changed) == 49
assert len({row["question_id"] for row in changed}) == len(changed)
assert not any(
    {"answer", "ground_truth", "reference_answer", "meta_info", "judge_score", "label"}
    & set(row)
    for row in changed
)

OUT.mkdir(parents=True, exist_ok=True)
data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in changed)
(OUT / "changed49.jsonl").write_text(data)
(OUT / "audit.json").write_text(json.dumps({
    "source_count": len(rows),
    "candidate_count": len(predictions),
    "changed_count": len(changed),
    "question_ids_sha256": hashlib.sha256(
        "\n".join(row["question_id"] for row in changed).encode()
    ).hexdigest(),
    "groundtruth_read": False,
    "judge_scores_read": False,
    "not_human_gold": True,
}, indent=2) + "\n")
print(json.dumps({"changed_count": len(changed), "output": str(OUT)}))
