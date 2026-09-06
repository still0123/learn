#!/usr/bin/env python3
"""Compute clustered OOF statistics and gate-specific failure attribution."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from statistics import mean
from typing import Any, Callable, Iterable, Mapping, Sequence


METHODS = (
    "A_Raw32",
    "B_Raw40",
    "C_Gated_RandomCrop8",
    "D_Gated_CLIPCrop8",
    "E_Gated_AVCrop8",
)
VALID_SCORES = frozenset((0.0, 0.5, 1.0))
BOOTSTRAP_SAMPLES = 10_000
SEED = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--judge-results", required=True)
    parser.add_argument("--judge-provenance", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"JSONL row {line_number} is not an object")
            rows.append(row)
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{hashlib.sha256(str(path).encode()).hexdigest()[:12]}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_markdown_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{hashlib.sha256(str(path).encode()).hexdigest()[:12]}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot calculate percentile of an empty sample")
    index = min(len(sorted_values) - 1, max(0, int(probability * len(sorted_values)) - 1))
    return float(sorted_values[index])


def video_cluster_bootstrap(
    cluster_values: Mapping[str, float],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = SEED,
) -> dict[str, Any]:
    video_ids = sorted(cluster_values)
    if not video_ids:
        return {"cluster_count": 0, "samples": samples, "seed": seed, "ci95": None}
    values = [float(cluster_values[video_id]) for video_id in video_ids]
    rng = random.Random(seed)
    statistics = []
    count = len(values)
    for _ in range(samples):
        statistics.append(sum(values[rng.randrange(count)] for _ in range(count)) / count)
    statistics.sort()
    return {
        "cluster_count": count,
        "samples": samples,
        "seed": seed,
        "ci95": [percentile(statistics, 0.025), percentile(statistics, 0.975)],
    }


def compact_scores(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scores = [float(row["score"]) for row in rows]
    counts = Counter(str(score) for score in scores)
    return {
        "n": len(scores),
        "score_counts": {"0": counts.get("0.0", 0), "0.5": counts.get("0.5", 0), "1": counts.get("1.0", 0)},
        "strict": sum(score == 1.0 for score in scores) / len(scores) if scores else 0.0,
        "relaxed": mean(scores) if scores else 0.0,
    }


def grouped_scores(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    groups: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key, "unknown"))].append(row)
    return {name: compact_scores(group) for name, group in sorted(groups.items())}


def video_metric(rows: Sequence[Mapping[str, Any]], metric: Callable[[Mapping[str, Any]], float]) -> dict[str, float]:
    grouped: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["video"])].append(metric(row))
    return {video: mean(values) for video, values in grouped.items()}


def pairwise_summary(
    first: str,
    second: str,
    scores: Mapping[str, Mapping[str, float]],
    metadata: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    shared_ids = sorted(set(scores[first]) & set(scores[second]), key=lambda value: int(value))
    paired = [
        (question_id, float(scores[first][question_id]), float(scores[second][question_id]))
        for question_id in shared_ids
    ]
    relaxed_deltas_by_video: defaultdict[str, list[float]] = defaultdict(list)
    strict_deltas_by_video: defaultdict[str, list[float]] = defaultdict(list)
    for question_id, first_score, second_score in paired:
        video = str(metadata[question_id]["video"])
        relaxed_deltas_by_video[video].append(second_score - first_score)
        strict_deltas_by_video[video].append(
            float(second_score == 1.0) - float(first_score == 1.0)
        )
    relaxed_cluster_deltas = {
        video: mean(values) for video, values in relaxed_deltas_by_video.items()
    }
    strict_cluster_deltas = {
        video: mean(values) for video, values in strict_deltas_by_video.items()
    }
    second_improved = [item for item in paired if item[2] > item[1]]
    second_harmed = [item for item in paired if item[2] < item[1]]
    second_wrong_to_right = [item for item in paired if item[1] < 1.0 and item[2] == 1.0]
    second_right_to_wrong = [item for item in paired if item[1] == 1.0 and item[2] < 1.0]
    return {
        "first_method": first,
        "second_method": second,
        "score_direction": "second_minus_first",
        "shared_questions": len(paired),
        "first_wins": sum(first_score > second_score for _, first_score, second_score in paired),
        "ties": sum(first_score == second_score for _, first_score, second_score in paired),
        "second_wins": sum(first_score < second_score for _, first_score, second_score in paired),
        "mean_score_delta_second_minus_first": mean(
            [second_score - first_score for _, first_score, second_score in paired]
        )
        if paired
        else 0.0,
        "mean_strict_delta_second_minus_first": mean(
            [
                float(second_score == 1.0) - float(first_score == 1.0)
                for _, first_score, second_score in paired
            ]
        )
        if paired
        else 0.0,
        "video_clustered_bootstrap": video_cluster_bootstrap(relaxed_cluster_deltas),
        "relaxed_video_clustered_bootstrap": video_cluster_bootstrap(relaxed_cluster_deltas),
        "strict_video_clustered_bootstrap": video_cluster_bootstrap(strict_cluster_deltas),
        "second_relaxed_improved": len(second_improved),
        "second_relaxed_harmed": len(second_harmed),
        "second_wrong_to_right": len(second_wrong_to_right),
        "second_right_to_wrong": len(second_right_to_wrong),
        "second_correction_precision": (
            len(second_wrong_to_right) / (len(second_wrong_to_right) + len(second_right_to_wrong))
            if (second_wrong_to_right or second_right_to_wrong)
            else None
        ),
    }


def subtype_from_terms(gate_record: Mapping[str, Any]) -> str:
    question_type = gate_record.get("question_type", {})
    terms = set(question_type.get("matched_visual_detail_terms", [])) if isinstance(question_type, Mapping) else set()
    if {"brand", "logo"} & terms:
        return "brand_or_logo"
    if {"price", "discount", "percentage", "number"} & terms:
        return "price_or_numeric_text"
    if terms:
        return "ocr_or_visual_text"
    return "other_visual_detail"


def main() -> int:
    args = parse_args()
    run_root = Path(args.run_root).resolve()
    judge_results_path = Path(args.judge_results).resolve()
    provenance_path = Path(args.judge_provenance).resolve()
    output_dir = Path(args.output_dir).resolve()
    errors: list[str] = []

    merge_manifest_path = run_root / "oof_merge_manifest_v1.json"
    protocol_audit_path = run_root / "oof_protocol_audit_v1.json"
    if not merge_manifest_path.exists() or not protocol_audit_path.exists():
        raise RuntimeError("merged OOF audit artifacts are required before judge analysis")
    protocol_audit = load_json(protocol_audit_path)
    if not protocol_audit.get("passed"):
        raise RuntimeError("joint OOF protocol audit did not pass")
    merge_manifest = load_json(merge_manifest_path)
    if int(merge_manifest.get("total_records", -1)) != 2500:
        raise RuntimeError("merge manifest does not contain 2,500 records")

    merged: dict[str, dict[str, dict[str, Any]]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for method in METHODS:
        path = run_root / f"oof_predictions_{method}.jsonl"
        rows = load_jsonl(path)
        if len(rows) != 500:
            errors.append(f"{method} merged rows={len(rows)}, expected=500")
        by_id = {str(row["question_id"]): row for row in rows}
        if len(by_id) != 500:
            errors.append(f"{method} merged question IDs are not unique")
        merged[method] = by_id
        if method == "A_Raw32":
            metadata = {
                question_id: {
                    "video": str(row["video"]),
                    "fold": int(row["fold"]),
                    "question_type": str(row.get("question_type", "unknown")),
                }
                for question_id, row in by_id.items()
            }
        elif set(by_id) != set(metadata):
            errors.append(f"{method} question IDs do not align with A_Raw32")

    judge_rows = load_jsonl(judge_results_path)
    scores: dict[str, dict[str, float]] = {method: {} for method in METHODS}
    for row in judge_rows:
        method = str(row.get("method", ""))
        question_id = str(row.get("question_id", ""))
        score = row.get("score")
        if method not in scores or question_id not in metadata or score not in VALID_SCORES:
            errors.append(f"invalid or unparsed judge row for method={method}, question_id={question_id}")
            continue
        if question_id in scores[method]:
            errors.append(f"duplicate judge score for {method}/{question_id}")
            continue
        scores[method][question_id] = float(score)
    for method in METHODS:
        if set(scores[method]) != set(metadata):
            errors.append(f"{method} does not have 500 valid judge scores")

    if errors:
        report = {
            "schema_version": "qwen25_gated_avcrop_oof_clustered_judge_analysis_v1",
            "passed": False,
            "failures": errors,
        }
        write_json_atomic(output_dir / "oof_judge_clustered_analysis_v1.json", report)
        return 1

    method_reports: dict[str, Any] = {}
    for method in METHODS:
        records = [
            {
                **metadata[question_id],
                **merged[method][question_id],
                "score": scores[method][question_id],
            }
            for question_id in sorted(metadata, key=lambda value: int(value))
        ]
        token_values = [float(row["post_merge_visual_token_count"]) for row in records]
        latency_values = [float(row["latency_seconds"]) for row in records]
        method_reports[method] = {
            "overall": compact_scores(records),
            "video_clustered_bootstrap": {
                "strict": video_cluster_bootstrap(video_metric(records, lambda row: float(row["score"] == 1.0))),
                "relaxed": video_cluster_bootstrap(video_metric(records, lambda row: float(row["score"]))),
            },
            "by_fold": grouped_scores(records, "fold"),
            "by_question_type": grouped_scores(records, "question_type"),
            "average_visual_tokens": mean(token_values),
            "average_inference_latency_seconds": mean(latency_values),
        }

    pairwise = {
        f"{first}__vs__{second}": pairwise_summary(first, second, scores, metadata)
        for index, first in enumerate(METHODS)
        for second in METHODS[index + 1 :]
    }

    gate_path = run_root / "gate_manifest" / "gate_manifest_oof_foldfrozen_v2.jsonl"
    gate_by_id = {
        str(row["question_id"]): row
        for row in load_jsonl(gate_path)
    }
    gate_ids = sorted(
        (question_id for question_id, row in gate_by_id.items() if bool(row.get("append_crop8"))),
        key=lambda value: int(value),
    )
    if len(gate_ids) != 7:
        raise RuntimeError(f"frozen gate coverage is {len(gate_ids)}/500, expected 7/500")

    gate_rows = []
    for question_id in gate_ids:
        per_method = {
            method: {
                "prediction": merged[method][question_id]["prediction"],
                "score": scores[method][question_id],
                "score_delta_vs_A": scores[method][question_id] - scores["A_Raw32"][question_id],
            }
            for method in METHODS
        }
        gate_rows.append(
            {
                "question_id": question_id,
                "video": metadata[question_id]["video"],
                "fold": metadata[question_id]["fold"],
                "question_type": metadata[question_id]["question_type"],
                "gate_subtype": subtype_from_terms(gate_by_id[question_id]),
                "matched_visual_detail_terms": gate_by_id[question_id]
                .get("question_type", {})
                .get("matched_visual_detail_terms", []),
                "methods": per_method,
            }
        )
    non_gate_ids = sorted(set(metadata) - set(gate_ids), key=lambda value: int(value))
    non_gate_identity = {}
    for method in METHODS[2:]:
        mismatch_ids = [
            question_id
            for question_id in non_gate_ids
            if merged[method][question_id]["prediction"] != merged["A_Raw32"][question_id]["prediction"]
        ]
        non_gate_identity[method] = {
            "expected_non_gate_questions": len(non_gate_ids),
            "exact_prediction_match_count": len(non_gate_ids) - len(mismatch_ids),
            "mismatch_count": len(mismatch_ids),
            "mismatch_question_ids": mismatch_ids,
        }

    def gate_delta(method: str, question_ids: Iterable[str]) -> float:
        values = [scores[method][question_id] - scores["A_Raw32"][question_id] for question_id in question_ids]
        return mean(values) if values else 0.0

    d_overall_delta = gate_delta("D_Gated_CLIPCrop8", metadata)
    d_gate_delta = gate_delta("D_Gated_CLIPCrop8", gate_ids)
    e_overall_delta = gate_delta("E_Gated_AVCrop8", metadata)
    e_gate_delta = gate_delta("E_Gated_AVCrop8", gate_ids)

    modality_activation = []
    for question_id in gate_ids:
        gate_record = gate_by_id[question_id]
        permitted = gate_record.get("gate_decision", {}).get("permitted_evidence_summary", {})

        def crop_signature(key: str) -> list[tuple[Any, Any]]:
            return [
                (item.get("source_global_rank"), item.get("bbox_norm"))
                for item in gate_record.get(key, [])
            ]

        modality_activation.append(
            {
                "question_id": question_id,
                "asr_present": bool(permitted.get("asr_present")),
                "ocr_candidate_count": int(permitted.get("ocr_candidate_count", 0) or 0),
                "clip_av_crop_specs_identical": (
                    crop_signature("clip_crop_specs") == crop_signature("av_crop_specs")
                ),
                "D_E_predictions_identical": (
                    merged["D_Gated_CLIPCrop8"][question_id]["prediction"]
                    == merged["E_Gated_AVCrop8"][question_id]["prediction"]
                ),
            }
        )
    av_degenerated_to_clip = bool(modality_activation) and all(
        not row["asr_present"]
        and row["ocr_candidate_count"] == 0
        and row["clip_av_crop_specs_identical"]
        and row["D_E_predictions_identical"]
        for row in modality_activation
    )

    if av_degenerated_to_clip:
        decision = "candidate_failed_av_degenerated_to_clip"
        failure_reason = (
            "all gated samples lack usable ASR and OCR candidates; E uses the same crops "
            "and produces the same answers as D, so no audiovisual contribution was tested"
        )
    elif e_overall_delta > 0.0 and e_gate_delta > 0.0:
        decision = "directionally_positive_but_underpowered"
        failure_reason = "not_a_failure_label; gate coverage remains only 7/500"
    elif e_gate_delta > 0.0:
        decision = "candidate_failed_undercoverage"
        failure_reason = "gate subset is directionally positive but does not yield an overall positive OOF trend"
    else:
        decision = "candidate_failed_crop_effect"
        failure_reason = "E has no positive trend on the gated subset, so the current crop evidence is unsupported"

    theoretical_headroom = sum(1.0 - scores["A_Raw32"][question_id] for question_id in gate_ids) / 500.0
    gate_analysis = {
        "gate_coverage": {"hit": len(gate_ids), "total": 500, "fraction": len(gate_ids) / 500.0},
        "gate_question_ids": gate_ids,
        "gate_question_details": gate_rows,
        "non_gate_prediction_identity_vs_A": non_gate_identity,
        "theoretical_max_relaxed_gain_if_all_gate_items_reach_one": theoretical_headroom,
        "absolute_max_affected_question_fraction": len(gate_ids) / 500.0,
        "modality_activation_audit": modality_activation,
        "av_degenerated_to_clip": av_degenerated_to_clip,
        "D_minus_A": {
            "overall_mean_score_delta": d_overall_delta,
            "gate_subset_mean_score_delta": d_gate_delta,
        },
        "E_minus_A": {
            "overall_mean_score_delta": e_overall_delta,
            "gate_subset_mean_score_delta": e_gate_delta,
        },
        "candidate_decision": decision,
        "failure_reason": failure_reason,
    }

    report = {
        "schema_version": "qwen25_gated_avcrop_oof_clustered_judge_analysis_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": True,
        "bootstrap": {"unit": "video_cluster", "samples": BOOTSTRAP_SAMPLES, "seed": SEED},
        "judge_results_sha256": sha256_file(judge_results_path),
        "judge_provenance_sha256": sha256_file(provenance_path),
        "method_reports": method_reports,
        "pairwise": pairwise,
        "gate_analysis": gate_analysis,
    }
    write_json_atomic(output_dir / "oof_judge_clustered_analysis_v1.json", report)
    failure = {
        "schema_version": "qwen25_gated_avcrop_failure_attribution_v1",
        "candidate": "E_Gated_AVCrop8",
        "decision": decision,
        "e_overall_delta": e_overall_delta,
        "e_gate_subset_delta": e_gate_delta,
        "d_overall_delta": d_overall_delta,
        "d_gate_subset_delta": d_gate_delta,
        "av_degenerated_to_clip": av_degenerated_to_clip,
        "gate_coverage": f"{len(gate_ids)}/500",
        "reason": failure_reason,
        "no_threshold_or_crop_parameter_retuning_on_this_oof": True,
        "fresh81_confirm_run": False,
    }
    write_json_atomic(output_dir / "failure_attribution.json", failure)
    markdown = "\n".join(
        [
            "# Qwen2.5 Gate Crop Failure Attribution",
            "",
            f"- Decision: `{decision}`",
            f"- Gate coverage: `{len(gate_ids)}/500`",
            f"- E minus A, overall mean score: `{e_overall_delta:.6f}`",
            f"- E minus A, gate subset mean score: `{e_gate_delta:.6f}`",
            f"- D minus A, overall mean score: `{d_overall_delta:.6f}`",
            f"- D minus A, gate subset mean score: `{d_gate_delta:.6f}`",
            f"- AV degenerated to CLIP: `{str(av_degenerated_to_clip).lower()}`",
            f"- Interpretation: {failure_reason}",
            "- No gate threshold, crop count, crop scale, prompt, or test-set decision was changed from these OOF results.",
            "- Fresh81 confirmation was not run.",
            "",
        ]
    )
    write_markdown_atomic(output_dir / "failure_attribution.md", markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
