#!/usr/bin/env python3
"""Materialize leakage-separated Evidence-300 inputs and reliability labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from evaluation.methods.claim_evidence_verifier.features_v2 import extract_answer_claim


FORBIDDEN = {"answer", "ground_truth", "reference_answer", "judge_score", "supervision", "reliable"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def locate(root: Path, qid: str, filename: str) -> Path:
    direct = root / qid / filename
    if direct.is_file():
        return direct
    matches = sorted(root.glob(f"{qid}*/{filename}"))
    if len(matches) != 1:
        raise RuntimeError(f"cannot uniquely locate {filename} for {qid}")
    return matches[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--router-dataset", type=Path, required=True)
    parser.add_argument("--raw-result-root", type=Path, required=True)
    parser.add_argument("--judge-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    router = load_jsonl(args.router_dataset)
    judges = {
        str(row["question_id"]): float(row["score"])
        for row in load_jsonl(args.judge_results) if row.get("method") == "raw_uniform"
    }
    inputs, labels = [], []
    split_counts, split_positives = {}, {}
    videos_by_split: dict[str, set[str]] = {}
    for record in router:
        qid, split = str(record["question_id"]), str(record["split"])
        prediction_path = locate(args.raw_result_root, qid, "prediction.json")
        evidence_path = locate(args.raw_result_root, qid, "evidence.json")
        prediction, evidence = load_json(prediction_path), load_json(evidence_path)
        selected = list(evidence.get("selected_frames") or [])
        input_row = {
            "schema": "adsqa_claim_reliability_input_v22",
            "question_id": qid, "video_id": str(record["video_id"]), "split": split,
            "primary_type": str(record["primary_type"]), "question": str(record["question"]),
            "claim": extract_answer_claim(prediction.get("prediction", "")),
            "asr_excerpt": str(evidence.get("asr_excerpt", "")),
            "video_path": str(evidence["video_path"]),
            "selected_frame_indices": [int(row["frame_index"]) for row in selected],
            "router_inputs": record["router_inputs"],
            "ocr_present": any(bool(row.get("ocr_texts")) for row in evidence.get("image_records", [])),
        }
        if FORBIDDEN & set(input_row):
            raise RuntimeError("label leakage into v2.2 input")
        score = judges[qid]
        label_row = {
            "schema": "adsqa_claim_reliability_label_v22", "question_id": qid,
            "split": split, "judge_score": score, "reliable": int(score == 1.0),
        }
        inputs.append(input_row)
        labels.append(label_row)
        split_counts[split] = split_counts.get(split, 0) + 1
        split_positives[split] = split_positives.get(split, 0) + label_row["reliable"]
        videos_by_split.setdefault(split, set()).add(input_row["video_id"])
    if len(inputs) != 300 or len({row["question_id"] for row in inputs}) != 300:
        raise RuntimeError("v2.2 requires 300 unique questions")
    split_names = sorted(videos_by_split)
    overlaps = {
        f"{left}:{right}": len(videos_by_split[left] & videos_by_split[right])
        for index, left in enumerate(split_names) for right in split_names[index + 1:]
    }
    if any(overlaps.values()):
        raise RuntimeError(f"video leakage across splits: {overlaps}")
    input_path, label_path = args.output_root / "input.jsonl", args.output_root / "labels.jsonl"
    dump_jsonl(input_path, inputs)
    dump_jsonl(label_path, labels)
    audit = {
        "schema": "adsqa_claim_reliability_dataset_audit_v22", "count": len(inputs),
        "split_counts": split_counts, "split_positive_counts": split_positives,
        "cross_split_video_overlap": overlaps, "input_label_leakage": False, "passed": True,
    }
    audit_path = args.output_root / "audit.json"
    dump_json(audit_path, audit)
    dump_json(args.output_root / "manifest.json", {
        "schema": "adsqa_claim_reliability_manifest_v22",
        "inputs": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "labels": {"path": str(label_path), "sha256": sha256_file(label_path)},
        "audit": {"path": str(audit_path), "sha256": sha256_file(audit_path)},
    })
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
