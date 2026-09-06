#!/usr/bin/env python3
"""Build two answer-free verifier shards for Confirm-100 region candidates."""

import argparse
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    items = {str(row["question_id"]): row for row in rows(args.base_root / "inputs" / "active_region.jsonl")}
    result = []
    for path in sorted((args.run_root / "inference").glob("shard*/*/a2_prediction.json")):
        prediction = json.loads(path.read_text())
        qid = str(prediction["question_id"])
        item = items[qid]
        result.append({
            "question_id": f"q{qid}__A2", "source_question_id": qid,
            "video_id": str(item["video_id"]), "video_path": str(item["video_path"]),
            "question": str(item["question"]), "claim": str(prediction["prediction"]),
            "candidate_method": "ReAdR_ActiveRegion_Regenerate_A2",
            "selected_frame_indices": [int(value) for value in item["a0_frame_indices"]],
            "asr_excerpt": str(item.get("a0_asr_excerpt", "")),
        })
    if len(result) != 53:
        raise RuntimeError(f"expected 53 candidates, got {len(result)}")
    args.output_root.mkdir(parents=True, exist_ok=False)
    for index, part in enumerate((result[:27], result[27:])):
        (args.output_root / f"shard{index}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in part)
        )
    audit = {"count": 53, "shard_counts": [27, 26], "groundtruth_read": False, "judge_scores_read": False}
    (args.output_root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
