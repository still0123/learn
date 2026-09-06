#!/usr/bin/env python3
"""Materialize four auditable judge inputs from counterfactual run shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_group(source_root: Path, phase: str, expected_ids: list[str], destination: Path, overwrite: bool) -> dict[str, Any]:
    source_by_id: dict[str, Path] = {}
    duplicates: dict[str, list[str]] = {}
    for path in source_root.glob(f"shard*of3/{phase}/*/prediction.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        qid = str(row.get("question_id"))
        if qid in source_by_id:
            duplicates.setdefault(qid, [str(source_by_id[qid])]).append(str(path))
        source_by_id[qid] = path
    missing = sorted(set(expected_ids) - set(source_by_id))
    extra = sorted(set(source_by_id) - set(expected_ids))
    if duplicates or missing or extra:
        raise RuntimeError(f"cannot collect {destination.name}: duplicates={len(duplicates)} missing={len(missing)} extra={len(extra)}")
    records = []
    for qid in expected_ids:
        source = source_by_id[qid]
        target = destination / qid / "prediction.json"
        if target.exists() and not overwrite:
            if sha256_file(target) != sha256_file(source):
                raise RuntimeError(f"existing staged prediction drifted for {destination.name}/{qid}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        records.append({"question_id": qid, "source": str(source), "sha256": sha256_file(source)})
    manifest = {
        "schema": "adsqa_counterfactual_judge_input_v1",
        "source_root": str(source_root),
        "phase": phase,
        "count": len(records),
        "records": records,
    }
    dump_json(destination / "manifest.json", manifest)
    return {"group": destination.name, "count": len(records), "manifest": str(destination / "manifest.json")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question_file", required=True)
    parser.add_argument("--raw_root", required=True)
    parser.add_argument("--mmr_root", required=True)
    parser.add_argument("--output_root", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    expected_ids = [str(row["question_id"]) for row in json.loads(Path(args.question_file).read_text(encoding="utf-8"))]
    if len(expected_ids) != len(set(expected_ids)):
        raise RuntimeError("duplicate question ids in question_file")
    output_root = Path(args.output_root)
    groups = [
        ("raw_uniform", Path(args.raw_root), "initial"),
        ("raw_plus_counterfactual2", Path(args.raw_root), "final"),
        ("innovation1_mmr32", Path(args.mmr_root), "initial"),
        ("innovation1_mmr32_plus_counterfactual2", Path(args.mmr_root), "final"),
    ]
    summary = [collect_group(root, phase, expected_ids, output_root / name, args.overwrite) for name, root, phase in groups]
    payload = {"schema": "adsqa_counterfactual_judge_input_collection_v1", "question_count": len(expected_ids), "groups": summary}
    dump_json(output_root / "collection_manifest.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
