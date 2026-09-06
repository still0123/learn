#!/usr/bin/env python3
"""Build answer-free RealClaim verifier inputs for Confirm-60B active candidates."""

import argparse
import hashlib
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    master = {str(row["question_id"]): row for row in rows(args.root / "master_answer_free.jsonl")}
    items = {str(row["question_id"]): row for row in rows(args.items)}
    result = []
    for action, arm in (("LOOK_TIME", "time"), ("LOOK_REGION", "region")):
        for path in sorted((args.root / "inference" / arm).glob("*/a2_prediction.json")):
            prediction = json.loads(path.read_text())
            qid = str(prediction["question_id"])
            if master[qid]["action"] != action:
                raise RuntimeError(f"action mismatch: {qid}")
            item = items[qid]
            result.append({
                "question_id": f"q{qid}__A2",
                "source_question_id": qid,
                "video_id": str(item["video_id"]),
                "video_path": str(item["video_path"]),
                "question": str(item["question"]),
                "claim": str(prediction["prediction"]),
                "candidate_method": f"ReAdR_Active_{action}_Regenerate_A2",
                "selected_frame_indices": [int(value) for value in item["a0_frame_indices"]],
                "asr_excerpt": str(item.get("a0_asr_excerpt", "")),
            })
    if len(result) != 50 or len({row["source_question_id"] for row in result}) != 50:
        raise RuntimeError("expected 50 unique triggered candidates")
    args.output_root.mkdir(parents=True, exist_ok=False)
    output = args.output_root / "model_inputs_all.jsonl"
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in result))
    audit = {
        "schema_version": "qwen25_active_confirm60b_verifier_inputs_v1",
        "count": 50, "video_count": len({row["video_id"] for row in result}),
        "groundtruth_read": False, "judge_scores_read": False,
        "labels_in_model_inputs": False,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (args.output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
