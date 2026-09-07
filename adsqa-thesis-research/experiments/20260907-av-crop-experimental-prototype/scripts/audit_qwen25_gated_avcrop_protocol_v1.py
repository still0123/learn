#!/usr/bin/env python3
"""CPU-only preflight audit for the frozen Qwen2.5 gated-AVCrop protocol."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.common.adsqa_prompt import (  # noqa: E402
    ADSQA_ANSWER_PROMPT_VERSION,
    adsqa_answer_prompt_sha256,
)
from evaluation.methods.gated_avcrop import gate_protocol  # noqa: E402
from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    ALLOWED_MODEL_PATH,
    FROZEN_GATE_RULE,
    PROTOCOL_VERSION,
    canonical_json_sha256,
    frozen_group_configs,
    sha256_file,
    validate_clean_model_path,
    validate_shared_gate_manifest,
)


DEFAULT_RUN_DIR = (
    PROJECT_ROOT / "evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CPU-only audit for frozen Qwen2.5 gated AV Crop protocol"
    )
    parser.add_argument("--model-dir", default=str(ALLOWED_MODEL_PATH))
    parser.add_argument(
        "--data-audit",
        default=str(DEFAULT_RUN_DIR / "preflight/groupcv_and_fresh_confirm_audit_v1.json"),
    )
    parser.add_argument(
        "--gate-manifest",
        default="",
        help="Optional pre-inference JSONL manifest shared by C/D/E.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_RUN_DIR / "preflight/protocol_cpu_audit_groupcv_v2.json"),
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL record must be an object at {path}:{line_number}")
        records.append(value)
    return records


def load_data_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "status": "missing",
            "allows_inference": False,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    is_groupcv_ready = bool(payload.get("audit_passed", False))
    status = (
        "groupcv_data_ready"
        if is_groupcv_ready
        else str(payload.get("status", "unknown"))
    )
    return {
        "path": str(path.resolve()),
        "exists": True,
        "sha256": sha256_file(path),
        "status": status,
        "allows_inference": is_groupcv_ready,
        "groupcv_fold_count": payload.get("groupcv", {}).get("fold_count"),
        "groupcv_validation_video_count_per_fold": payload.get("groupcv", {}).get(
            "validation_video_count_per_fold"
        ),
    }


def main() -> None:
    args = parse_args()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model_identity = validate_clean_model_path(args.model_dir)
    groups = frozen_group_configs()
    data_audit = load_data_audit(Path(args.data_audit))

    if args.gate_manifest:
        manifest_path = Path(args.gate_manifest).resolve()
        records = read_jsonl(manifest_path)
        manifest_audit = {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            "status": "validated",
            **validate_shared_gate_manifest(records),
        }
    else:
        manifest_audit = {
            "status": "not_constructed",
            "reason": "per-fold shared gate manifest is not constructed",
        }

    result = {
        "schema_version": "qwen25_gated_avcrop_cpu_audit_groupcv_v2",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cpu_only": True,
        "gpu_inference_started": False,
        "protocol_version": PROTOCOL_VERSION,
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "gate_protocol_module": str(Path(gate_protocol.__file__).resolve()),
        "gate_protocol_module_sha256": sha256_file(Path(gate_protocol.__file__).resolve()),
        "model_identity": model_identity,
        "forbidden_model_policy": "any ReAd-R model path exits before inference",
        "answer_prompt": {
            "version": ADSQA_ANSWER_PROMPT_VERSION,
            "sha256": adsqa_answer_prompt_sha256(),
        },
        "frozen_gate_rule": FROZEN_GATE_RULE,
        "frozen_gate_rule_sha256": canonical_json_sha256(FROZEN_GATE_RULE),
        "groups": groups,
        "groups_sha256": canonical_json_sha256(groups),
        "shared_gate_manifest": manifest_audit,
        "data_gate": data_audit,
        "runnable_for_inference": bool(
            data_audit["allows_inference"]
            and manifest_audit["status"] == "validated"
        ),
        "inference_block_reason": (
            ""
            if data_audit["allows_inference"] and manifest_audit["status"] == "validated"
            else "GateDev200 source data and frozen shared gate manifest are both required."
        ),
    }
    output_path.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "runnable_for_inference": result["runnable_for_inference"],
                "data_gate_status": data_audit["status"],
                "manifest_status": manifest_audit["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
