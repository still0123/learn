"""Strict offline temporal-index cache loading and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SCHEMA_VERSION = "adsqa_temporal_indices_v1"
CANDIDATE_POLICY = "nested_uniform_raw32_plus_maxgap_v1"


class TemporalCacheError(RuntimeError):
    """Raised when an offline selector cache violates the fair protocol."""


def question_sha256(question: str) -> str:
    return hashlib.sha256(str(question).encode("utf-8")).hexdigest()


def nested_uniform_candidate_indices(
    frame_count: int,
    candidate_count: int = 64,
    baseline_count: int = 32,
) -> list[int]:
    """Build ordered candidates that contain the exact uniform baseline frames."""
    if frame_count <= 0 or not 0 < baseline_count <= candidate_count:
        raise ValueError("invalid frame or candidate counts")
    baseline = np.linspace(0, frame_count - 1, baseline_count, dtype=int).tolist()
    nested_count = min(candidate_count, max(baseline_count, 2 * baseline_count - 1))
    selected = set(np.linspace(0, frame_count - 1, nested_count, dtype=int).tolist())
    selected.update(baseline)
    while len(selected) < candidate_count and len(selected) < frame_count:
        ordered = sorted(selected)
        gaps = [(right - left, left, right) for left, right in zip(ordered, ordered[1:]) if right - left > 1]
        if not gaps:
            break
        _, left, right = max(gaps, key=lambda item: (item[0], -item[1]))
        selected.add((left + right) // 2)
    if len(selected) < candidate_count:
        # Short videos necessarily repeat source frames, matching the historical policy.
        dense = np.linspace(0, frame_count - 1, candidate_count, dtype=int).tolist()
        result = sorted(selected)
        for index in dense:
            if len(result) >= candidate_count:
                break
            result.append(index)
        return sorted(result)
    result = sorted(selected)
    if len(result) != candidate_count or not set(baseline).issubset(result):
        raise RuntimeError("failed to construct nested candidate grid")
    return result


def _iter_cache_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if path.is_dir():
        files = sorted(path.glob("*.jsonl"))
        if not files:
            raise TemporalCacheError(f"no JSONL cache files found in {path}")
        yield from files
        return
    raise TemporalCacheError(f"temporal cache path does not exist: {path}")


def temporal_cache_inventory(path: str | Path) -> list[dict[str, Any]]:
    """Return stable file metadata for run-config provenance."""
    inventory = []
    for cache_file in _iter_cache_files(Path(path)):
        digest = hashlib.sha256()
        with cache_file.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        inventory.append({
            "path": str(cache_file.resolve()),
            "size_bytes": cache_file.stat().st_size,
            "sha256": digest.hexdigest(),
        })
    return inventory


def load_temporal_index_cache(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load one JSONL file or a directory of sharded JSONL files."""
    records: dict[str, dict[str, Any]] = {}
    for cache_file in _iter_cache_files(Path(path)):
        with cache_file.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise TemporalCacheError(
                        f"invalid JSON at {cache_file}:{line_number}: {exc}"
                    ) from exc
                if record.get("schema_version") != SCHEMA_VERSION:
                    raise TemporalCacheError(
                        f"unsupported schema at {cache_file}:{line_number}: "
                        f"{record.get('schema_version')!r}"
                    )
                question_id = str(record.get("question_id", ""))
                if not question_id:
                    raise TemporalCacheError(f"missing question_id at {cache_file}:{line_number}")
                if question_id in records:
                    raise TemporalCacheError(f"duplicate question_id in temporal cache: {question_id}")
                record["_cache_file"] = str(cache_file)
                record["_cache_line"] = line_number
                records[question_id] = record
    if not records:
        raise TemporalCacheError(f"temporal cache is empty: {path}")
    return records


def validate_temporal_record(
    record: dict[str, Any],
    *,
    question_id: str,
    question: str,
    candidate_count: int,
    selected_count: int,
) -> list[int]:
    """Return chronological candidate ranks after strict protocol checks."""
    if str(record.get("question_id")) != str(question_id):
        raise TemporalCacheError(
            f"question_id mismatch: cache={record.get('question_id')} current={question_id}"
        )
    expected_hash = question_sha256(question)
    if record.get("question_sha256") != expected_hash:
        raise TemporalCacheError(f"question hash mismatch for {question_id}")
    if int(record.get("candidate_count", -1)) != int(candidate_count):
        raise TemporalCacheError(
            f"candidate count mismatch for {question_id}: "
            f"cache={record.get('candidate_count')} current={candidate_count}"
        )
    ranks = record.get("selected_candidate_ranks")
    if not isinstance(ranks, list) or len(ranks) != int(selected_count):
        raise TemporalCacheError(
            f"selected rank count mismatch for {question_id}: "
            f"cache={len(ranks) if isinstance(ranks, list) else 'invalid'} expected={selected_count}"
        )
    if any(isinstance(rank, bool) or not isinstance(rank, int) for rank in ranks):
        raise TemporalCacheError(f"non-integer selected rank for {question_id}")
    if len(set(ranks)) != len(ranks):
        raise TemporalCacheError(f"duplicate selected rank for {question_id}")
    if ranks != sorted(ranks):
        raise TemporalCacheError(f"selected ranks are not chronological for {question_id}")
    if any(rank < 0 or rank >= candidate_count for rank in ranks):
        raise TemporalCacheError(f"selected rank outside candidate range for {question_id}")

    ranked = record.get("ranked_candidate_ranks")
    if ranked is not None:
        if not isinstance(ranked, list) or len(ranked) != candidate_count:
            raise TemporalCacheError(f"invalid full ranking for {question_id}")
        if sorted(ranked) != list(range(candidate_count)):
            raise TemporalCacheError(f"full ranking is not a permutation for {question_id}")
        if set(ranks) != set(ranked[:selected_count]):
            raise TemporalCacheError(f"selected ranks disagree with ranking Top-K for {question_id}")
    return ranks
