"""Metrics for target/control claim-evidence intervention triplets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def intervention_metrics(records: Sequence[Mapping[str, Any]], margin: float = 0.0) -> dict[str, Any]:
    if not records:
        raise ValueError("records must be non-empty")
    rows = []
    for record in records:
        scores = record.get("scores") or {}
        full = float((scores.get("full") or {}).get("supported", 0.0))
        target = float((scores.get("target_removed") or {}).get("supported", 0.0))
        control = float((scores.get("control_removed") or {}).get("supported", 0.0))
        target_drop = full - target
        control_drop = full - control
        rows.append({
            "question_id": str(record.get("question_id", "")),
            "target_drop": target_drop,
            "control_drop": control_drop,
            "necessity_contrast": target_drop - control_drop,
            "strict_pair_correct": target_drop > control_drop + margin,
        })
    return {
        "n": len(rows),
        "margin": margin,
        "mean_target_drop": sum(row["target_drop"] for row in rows) / len(rows),
        "mean_control_drop": sum(row["control_drop"] for row in rows) / len(rows),
        "mean_necessity_contrast": sum(row["necessity_contrast"] for row in rows) / len(rows),
        "strict_pair_accuracy": sum(row["strict_pair_correct"] for row in rows) / len(rows),
        "rows": rows,
    }
