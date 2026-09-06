#!/usr/bin/env python3
"""Audit the five explicit-status ASR shards for AdsQA supplement."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ALLOWED = {"success", "no_speech", "no_audio", "transcription_failed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prep-root", type=Path, required=True)
    parser.add_argument("--asr-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    expected: dict[str, int] = {}
    for fold in range(5):
        path = args.prep_root / "selection_shards" / f"fold_{fold}.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        if len(rows) != 55:
            raise RuntimeError(f"ASR selection fold {fold} is not 55 videos")
        for row in rows:
            video = str(row["video"])
            if video in expected:
                raise RuntimeError(f"duplicate ASR selection video: {video}")
            expected[video] = fold
    if len(expected) != 275:
        raise RuntimeError("expected exactly 275 ASR supplement videos")

    failures: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    fold_counts: Counter[str] = Counter()
    records = []
    for video, fold in sorted(expected.items()):
        matches = [
            root / f"{video}.json"
            for root in args.asr_root
            if (root / f"{video}.json").is_file()
        ]
        if len(matches) != 1:
            failures.append(
                {"video_id": video, "reason": f"record_matches={len(matches)}"}
            )
            continue
        path = matches[0]
        try:
            row: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            status = str(row["status"])
            if str(row["video_id"]) != video or status not in ALLOWED:
                raise RuntimeError("identity or status mismatch")
            if status == "success":
                if not str(row.get("text") or "").strip() or not row.get("segments"):
                    raise RuntimeError("success without text/segments")
                previous = -1.0
                for segment in row["segments"]:
                    start = float(segment["start"])
                    end = float(segment["end"])
                    if (
                        not math.isfinite(start)
                        or not math.isfinite(end)
                        or start < previous
                        or end < start
                    ):
                        raise RuntimeError("invalid segment timestamps")
                    previous = start
            elif status in {"no_audio", "no_speech"}:
                if row.get("text") is not None or row.get("segments"):
                    raise RuntimeError(f"{status} must have empty evidence")
            elif not row.get("error"):
                raise RuntimeError("transcription_failed lacks explicit error")
            status_counts[status] += 1
            fold_counts[str(fold)] += 1
            records.append(
                {
                    "video_id": video,
                    "fold": fold,
                    "status": status,
                    "path": str(path.resolve()),
                    "sha256": sha256_file(path),
                }
            )
        except Exception as exc:
            failures.append({"video_id": video, "reason": str(exc)})

    audit = {
        "schema_version": "adsqa_supplement2526_asr_audit_v1",
        "passed": not failures and len(records) == 275,
        "expected_videos": 275,
        "record_count": len(records),
        "fold_counts": dict(fold_counts),
        "status_counts": dict(status_counts),
        "explicit_failure_state_allowed": True,
        "failures": failures,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in audit.items() if key != "records"},
            ensure_ascii=False,
            indent=2,
        )
    )
    if not audit["passed"]:
        raise RuntimeError("supplement ASR audit failed")


if __name__ == "__main__":
    main()
