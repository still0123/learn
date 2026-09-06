#!/usr/bin/env python3
"""FreshQ wrapper around the frozen Qwen2.5 Raw40/CLIPCrop40 runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.fresh_confirm_decode import robust_load_uniform_frames
from evaluation.tools import run_qwen25_gated_avcrop_groupcv_v1 as legacy


def argument_value(name: str) -> str:
    try:
        return sys.argv[sys.argv.index(name) + 1]
    except (ValueError, IndexError):
        return ""


def patch_provenance(output_dir: Path) -> None:
    additions = {
        "entrypoint": "evaluation/tools/run_qwen25_fresh_confirm500_v1.py",
        "decode_policy": "decord_accurate_seek_then_opencv_sequential_fallback_v1",
        "fresh_confirmation_protocol": True,
    }
    for name in ("run_config.json", "run_summary.json"):
        path = output_dir / name
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.update(additions)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    output_value = argument_value("--output-dir")
    if not output_value:
        raise ValueError("FreshQ runs require an explicit --output-dir")
    output_dir = Path(output_value).resolve()
    os.environ["FRESH_DECODE_FALLBACK_LOG"] = str(
        output_dir / "logs/decode_fallback_v1.jsonl"
    )
    legacy.load_uniform_frames = robust_load_uniform_frames
    legacy.main()
    patch_provenance(output_dir)


if __name__ == "__main__":
    main()
