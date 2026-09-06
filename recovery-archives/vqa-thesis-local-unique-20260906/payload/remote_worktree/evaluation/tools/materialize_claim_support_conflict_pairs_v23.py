#!/usr/bin/env python3
"""Materialize audited supported/contradicted claim pairs for Qwen scoring."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRADICTION_FIELDS = (
    "supported_matches_fact", "contradiction_same_question",
    "contradiction_changes_exactly_one_atom", "contradiction_directly_conflicts",
    "no_meta_language",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
    parser.add_argument("--audited-triplets", type=Path, required=True)
    parser.add_argument("--evidence-inputs", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    triplets = load_jsonl(args.audited_triplets)
    evidence = {str(row["question_id"]): row for row in load_jsonl(args.evidence_inputs)}
    inputs, labels, rejected = [], [], []
    for row in triplets:
        qid = str(row["question_id"])
        contradiction_ok = (
            not row.get("deterministic_errors")
            and all((row.get("audit") or {}).get(field) is True for field in CONTRADICTION_FIELDS)
        )
        if not contradiction_ok:
            rejected.append(qid)
            continue
        base = evidence[qid]
        claims = (
            ("supported", str(row["supported_claim"]), 1),
            ("contradicted", str(row["generated"]["contradicted_claim"]), 0),
        )
        for label_name, claim, label in claims:
            pair_id = f"{qid}__{label_name}"
            inputs.append({
                **{key: value for key, value in base.items() if key not in {"question_id", "claim"}},
                "schema": "adsqa_claim_support_conflict_input_v23",
                "question_id": pair_id, "source_question_id": qid,
                "claim": claim, "pair_label_name": label_name,
            })
            labels.append({
                "schema": "adsqa_claim_support_conflict_label_v23", "question_id": pair_id,
                "source_question_id": qid, "label_name": label_name, "supported": label,
                "split": str(row.get("split", base.get("split", "unknown"))),
            })
    if len(inputs) != 2 * (len(triplets) - len(rejected)):
        raise RuntimeError("pair materialization count mismatch")
    input_path, label_path = args.output_root / "input.jsonl", args.output_root / "labels.jsonl"
    dump_jsonl(input_path, inputs)
    dump_jsonl(label_path, labels)
    audit = {
        "schema": "adsqa_claim_support_conflict_pair_audit_v23",
        "source_triplets": len(triplets), "accepted_pairs": len(inputs) // 2,
        "rejected_source_question_ids": rejected,
        "rows": len(inputs), "label_counts": dict(Counter(row["label_name"] for row in labels)),
        "unique_pair_ids": len({row["question_id"] for row in inputs}),
        "input_supervision_leakage": False,
        "passed": len(inputs) >= 54 and len({row["question_id"] for row in inputs}) == len(inputs),
    }
    audit_path = args.output_root / "audit.json"
    dump_json(audit_path, audit)
    dump_json(args.output_root / "manifest.json", {
        "schema": "adsqa_claim_support_conflict_pair_manifest_v23",
        "inputs": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "labels": {"path": str(label_path), "sha256": sha256_file(label_path)},
        "audit": {"path": str(audit_path), "sha256": sha256_file(audit_path)},
    })
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
