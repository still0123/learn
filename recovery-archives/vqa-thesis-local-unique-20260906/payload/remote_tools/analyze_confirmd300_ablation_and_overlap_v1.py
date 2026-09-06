#!/usr/bin/env python3
"""Build full Confirm-D300 ablations and audit video-level isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260728)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def dump_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def score_metrics(rows: list[dict], field: str) -> dict:
    values = [float(row[field]) for row in rows]
    counts = {str(value): values.count(value) for value in (0.0, 0.5, 1.0)}
    return {
        "rows": len(rows),
        "strict": sum(value == 1.0 for value in values) / len(values),
        "relaxed": sum(values) / len(values),
        "counts": counts,
    }


def paired_metrics(rows: list[dict], base_field: str, candidate_field: str) -> dict:
    pairs = [
        (float(row[base_field]), float(row[candidate_field]))
        for row in rows
    ]
    wins = sum(candidate > base for base, candidate in pairs)
    losses = sum(candidate < base for base, candidate in pairs)
    return {
        "rows": len(rows),
        "wins": wins,
        "ties": len(rows) - wins - losses,
        "losses": losses,
        "relaxed_delta": sum(candidate - base for base, candidate in pairs) / len(pairs),
        "strict_delta": (
            sum(candidate == 1.0 for _, candidate in pairs)
            - sum(base == 1.0 for base, _ in pairs)
        )
        / len(pairs),
        "wrong_to_right": sum(base < 1.0 and candidate == 1.0 for base, candidate in pairs),
        "right_to_wrong": sum(base == 1.0 and candidate < 1.0 for base, candidate in pairs),
    }


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap(
    rows: list[dict],
    base_field: str,
    candidate_field: str,
    samples: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    relaxed, strict = [], []
    for _ in range(samples):
        selected = [rows[rng.randrange(len(rows))] for _ in rows]
        base = [float(row[base_field]) for row in selected]
        candidate = [float(row[candidate_field]) for row in selected]
        relaxed.append(
            sum(cand - old for old, cand in zip(base, candidate)) / len(selected)
        )
        strict.append(
            (
                sum(value == 1.0 for value in candidate)
                - sum(value == 1.0 for value in base)
            )
            / len(selected)
        )
    return {
        "samples": samples,
        "seed": seed,
        "relaxed_delta_ci95": [percentile(relaxed, 0.025), percentile(relaxed, 0.975)],
        "strict_delta_ci95": [percentile(strict, 0.025), percentile(strict, 0.975)],
    }


def ids(rows: list[dict], field: str) -> set[str]:
    return {str(row[field]) for row in rows if row.get(field) not in (None, "")}


def pairwise_overlap(named_sets: dict[str, set[str]]) -> dict:
    output = {}
    names = list(named_sets)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            values = sorted(named_sets[left] & named_sets[right])
            output[f"{left}__{right}"] = {
                "count": len(values),
                "examples": values[:20],
            }
    return output


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    run = root / "evaluation/runs/qwen3_selective_evidence_rewrite_confirmd300_v1"
    trigger_path = run / "judge_deepseek_v1/results_trigger30.jsonl"
    complete_path = run / "judge_deepseek_v1/complete_confirmd300_policy_rows.jsonl"
    trigger_rows = load_jsonl(trigger_path)
    complete_rows = load_jsonl(complete_path)
    if len(trigger_rows) != 30 or len(complete_rows) != 300:
        raise RuntimeError("expected 30 trigger rows and 300 complete rows")

    trigger_by_qid = {str(row["question_id"]): row for row in trigger_rows}
    if len(trigger_by_qid) != 30:
        raise RuntimeError("trigger question IDs are not unique")
    policy_rows = []
    for row in complete_rows:
        qid = str(row["question_id"])
        trigger = trigger_by_qid.get(qid)
        policy_rows.append({
            "question_id": qid,
            "video_id": str(row["video_id"]),
            "question_type": str(row["question_type"]),
            "triggered": trigger is not None,
            "a0_score": float(row["a0_score"]),
            "a1_policy_score": (
                float(trigger["a1_score"]) if trigger else float(row["a0_score"])
            ),
            "a2_policy_score": (
                float(trigger["a2_score"]) if trigger else float(row["a0_score"])
            ),
            "a3_policy_score": float(row["a3_score"]),
        })

    comparisons = {}
    for offset, field in enumerate(
        ("a1_policy_score", "a2_policy_score", "a3_policy_score"), start=1
    ):
        comparisons[field] = {
            "candidate": score_metrics(policy_rows, field),
            "vs_a0": paired_metrics(policy_rows, "a0_score", field),
            "bootstrap": bootstrap(
                policy_rows,
                "a0_score",
                field,
                args.bootstrap,
                args.seed + offset,
            ),
        }
    ablation = {
        "schema_version": "confirmd300_full_policy_ablation_v1",
        "baseline": score_metrics(policy_rows, "a0_score"),
        "comparisons": comparisons,
        "trigger_count": sum(row["triggered"] for row in policy_rows),
        "score_source": "existing_deepseek_v4_flash_answer_only_results",
        "new_api_calls": 0,
        "not_human_gold": True,
        "input_hashes": {
            "trigger_rows": sha256_file(trigger_path),
            "complete_rows": sha256_file(complete_path),
        },
    }

    realclaim_path = (
        root
        / "evaluation/runs/innovation2_realclaim_lora_verifier_v1/"
        "realclaim_train_v1/inputs.jsonl"
    )
    oof_path = (
        root
        / "evaluation/runs/qwen3_selective_evidence_rewrite_smoke50_v1/"
        "a0_pool_v1/model_inputs_all.jsonl"
    )
    confirm_path = (
        run / "a0_pool_v1/model_inputs_all.jsonl"
    )
    calibration_path = (
        root
        / "evaluation/runs/innovation2_realclaim300_v2_corrected_frames/"
        "inference_inputs.jsonl"
    )
    paths = {
        "realclaim985_train": realclaim_path,
        "oof500": oof_path,
        "confirmd300": confirm_path,
        "calibration240": calibration_path,
    }
    datasets = {name: load_jsonl(path) for name, path in paths.items()}
    datasets["calibration240"] = [
        row for row in datasets["calibration240"]
        if str(row.get("split")) == "calibration"
    ]
    if len(datasets["calibration240"]) != 240:
        raise RuntimeError(
            "expected exactly 240 rows after filtering split=calibration, got "
            f"{len(datasets['calibration240'])}"
        )
    video_sets = {name: ids(rows, "video_id") for name, rows in datasets.items()}
    question_sets = {
        name: ids(rows, "source_question_id") | ids(rows, "question_id")
        for name, rows in datasets.items()
    }
    video_overlap = pairwise_overlap(video_sets)
    question_overlap = pairwise_overlap(question_sets)
    critical_pairs = (
        "realclaim985_train__calibration240",
        "realclaim985_train__confirmd300",
        "oof500__confirmd300",
        "confirmd300__calibration240",
    )
    isolation = {
        "schema_version": "adsqa_final_training_confirm_isolation_audit_v1",
        "datasets": {
            name: {
                "rows": len(datasets[name]),
                "videos": len(video_sets[name]),
                "questions": len(question_sets[name]),
                "path": str(paths[name]),
                "sha256": sha256_file(paths[name]),
            }
            for name in paths
        },
        "video_overlap": video_overlap,
        "question_overlap": question_overlap,
        "critical_zero_overlap_pairs": list(critical_pairs),
        "passed": all(video_overlap[pair]["count"] == 0 for pair in critical_pairs),
    }

    args.output_dir.mkdir(parents=True, exist_ok=False)
    dump_jsonl(args.output_dir / "full_policy_rows.jsonl", policy_rows)
    dump_json(args.output_dir / "full_policy_ablation.json", ablation)
    dump_json(args.output_dir / "isolation_audit.json", isolation)
    hashes = {}
    for path in sorted(args.output_dir.iterdir()):
        if path.is_file():
            hashes[path.name] = sha256_file(path)
    dump_json(args.output_dir / "manifest.json", {
        "schema_version": "adsqa_final_cpu_audit_manifest_v1",
        "files": hashes,
        "passed": isolation["passed"],
    })
    print(json.dumps(
        {"ablation": ablation, "isolation": isolation},
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
