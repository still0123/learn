from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def inspect_experiment(output_dir: str | Path, *, repeat: int | None = None) -> dict[str, Any]:
    """Load a completed experiment into a concise, evidence-oriented view."""
    root = Path(output_dir).resolve()
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"experiment summary not found: {summary_path}")
    summary = _read_json(summary_path)
    manifest = summary.get("manifest") or _read_json(root / "manifest.json")
    repeats = summary.get("repeats")
    if not isinstance(repeats, list):
        raise ValueError("experiment summary is missing repeats")
    if repeat is not None and repeat < 1:
        raise ValueError("repeat must be at least 1")

    selected = [item for item in repeats if repeat is None or item.get("repeat") == repeat]
    if not selected:
        raise ValueError(f"repeat {repeat} was not found in {root}")
    details = [_inspect_repeat(root, item) for item in selected]
    return {
        "experiment_dir": str(root),
        "experiment_id": summary.get("experiment_id"),
        "report_path": str(root / "report.md"),
        "runtime": manifest.get("runtime", {}),
        "conditions": summary.get("conditions", {}),
        "paired_statistics": summary.get("paired_statistics", {}),
        "evolution": summary.get("evolution", {}),
        "repeats": details,
    }


def render_inspection(view: dict[str, Any]) -> str:
    lines = [
        f"# Experiment Inspect: {view.get('experiment_id', 'unknown')}",
        "",
        f"- Evidence directory: `{view['experiment_dir']}`",
        f"- Report: `{view['report_path']}`",
        f"- Runtime: `{view.get('runtime', {}).get('runtime', 'unknown')}` / "
        f"`{view.get('runtime', {}).get('model', 'unknown')}`",
        "",
        "## Three-condition Test summary",
        "",
        "| Condition | Mean score |",
        "|---|---:|",
    ]
    for name in ("no_skill", "seed_skill", "evolved_skill"):
        item = view.get("conditions", {}).get(name, {})
        lines.append(f"| {name} | {_score(item.get('mean_score'))} |")

    lines.extend([
        "",
        "## Paired statistics",
        "",
        "| Comparison | Delta | 95% CI | p-value | Significant |",
        "|---|---:|---:|---:|---|",
    ])
    for name, item in view.get("paired_statistics", {}).items():
        lines.append(
            f"| {name} | {_score(item.get('observed_delta'))} | "
            f"[{_score(item.get('ci_low'))}, {_score(item.get('ci_high'))}] | "
            f"{_score(item.get('p_value'))} | {item.get('significant_improvement', False)} |"
        )

    lines.extend(["", "## Candidate decisions"])
    for repeat in view["repeats"]:
        lines.extend([
            "",
            f"### Repeat {repeat['repeat']}",
            "",
            f"- Final Skill version: v{repeat['final_version']:03d}",
            f"- Final Validation: {_score(repeat.get('final_validation_score'))}",
        ])
        candidates = repeat["candidates"]
        if not candidates:
            lines.append("- No candidate-impact event was recorded.")
            continue
        lines.extend([
            "",
            "| Candidate | Decision | Validation | Diff lines | Reason |",
            "|---|---|---:|---:|---|",
        ])
        for item in candidates:
            reason = str(item.get("reason", "")).replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {item.get('candidate_id', '-')} | {item.get('decision', 'unknown')} | "
                f"{_score(item.get('candidate'))} | {item.get('diff_lines', 0)} | {reason} |"
            )
            path = item.get("candidate_path")
            if path:
                lines.append(f"| ↳ `{path}` |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def _inspect_repeat(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    index = int(item["repeat"])
    workspace = root / f"repeat-{index:03d}" / "workspace"
    state = _read_json(workspace / "state.json")
    impacts = _read_jsonl(workspace / "events" / "skill-impact.jsonl")
    candidates = []
    for event in impacts:
        proposal = event.get("proposal") or {}
        candidates.append({
            "candidate_id": event.get("candidate_id") or "candidate-01",
            "candidate_path": event.get("candidate_path"),
            "candidate_sha256": event.get("candidate_sha256"),
            "decision": event.get("decision"),
            "baseline": event.get("baseline"),
            "candidate": event.get("candidate"),
            "reason": event.get("reason"),
            "summary": event.get("summary"),
            "pattern_ids": proposal.get("pattern_ids", []),
            "evidence_ids": proposal.get("evidence_ids", []),
            "diff_lines": len(str(event.get("diff", "")).splitlines()),
        })
    return {
        "repeat": index,
        "final_version": int(state["version"]),
        "final_validation_score": state.get("best_validation_score"),
        "candidates": candidates,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required experiment file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected an object in {path}")
    return data


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"expected an object on line {number} in {path}")
        rows.append(item)
    return rows


def _score(value: Any) -> str:
    return "—" if value is None else f"{float(value):.4f}"
