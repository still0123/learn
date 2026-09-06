#!/usr/bin/env python3
"""Freeze 530 MMR-SelectRescue decisions with the existing audited gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delegate", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--inference-root", type=Path, required=True)
    parser.add_argument("--a0-scores", type=Path, required=True)
    parser.add_argument("--a2-scores", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--support-threshold", type=float, required=True)
    parser.add_argument("--minimum-margin", type=float, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("output directory must be empty")
    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mmr_selectrescue_full_freeze_",
        dir=args.output_dir.parent,
    ) as temporary:
        delegated = Path(temporary) / "delegated"
        subprocess.run(
            [
                sys.executable,
                str(args.delegate),
                "--dataset-dir",
                str(args.dataset_dir),
                "--inference-root",
                str(args.inference_root),
                "--a0-scores",
                str(args.a0_scores),
                "--a2-scores",
                str(args.a2_scores),
                "--output-dir",
                str(delegated),
                "--support-threshold",
                str(args.support_threshold),
                "--minimum-margin",
                str(args.minimum_margin),
                "--expected-count",
                "530",
                "--expected-videos",
                "530",
                "--expected-per-fold",
                "106",
            ],
            check=True,
        )
        args.output_dir.mkdir(parents=True, exist_ok=False)
        shutil.copy2(
            delegated / "protocol_rows.jsonl",
            args.output_dir / "protocol_rows.jsonl",
        )
        choices = []
        for line in (
            delegated / "frozen_choices_answer_free.jsonl"
        ).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["a3_selected_method"] == "CleanQwen3_Raw8_A0":
                row["a3_selected_method"] = "CleanQwen3_MMR8_A0"
            row["schema_version"] = "qwen3_mmr_selectrescue_full_choice_v1"
            choices.append(row)
        choices_path = args.output_dir / "frozen_choices_answer_free.jsonl"
        choices_path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in choices
            ),
            encoding="utf-8",
        )
        audit = json.loads(
            (delegated / "protocol_audit.json").read_text(encoding="utf-8")
        )
        audit["schema_version"] = (
            "qwen3_mmr_selectrescue_full_protocol_audit_v1"
        )
        audit["a0_method"] = "CleanQwen3_MMR8_A0"
        audit["choices_sha256"] = sha256_file(choices_path)
        audit["delegate_sha256"] = sha256_file(args.delegate)
        (args.output_dir / "protocol_audit.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if (
        audit.get("passed") is not True
        or int(audit.get("rows", -1)) != 530
    ):
        raise RuntimeError("full gate audit failed")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
