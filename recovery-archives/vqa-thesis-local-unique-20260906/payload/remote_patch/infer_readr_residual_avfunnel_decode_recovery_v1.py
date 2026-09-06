#!/usr/bin/env python3
"""Run ReAd-R residual AV-Funnel12 A2 inference with tolerant extraction."""

from __future__ import annotations

import re

import infer_qwen25_residual_avfunnel_decode_recovery_v1 as recovery


def extract_readr_answer(text: str, fallback: str) -> tuple[str, bool]:
    patterns = [
        r"\[Answer\]\s*:\s*(.+?)(?=\n\s*\[[A-Za-z ]+\]\s*:|\Z)",
        r"<answer>\s*(.*?)\s*</answer>",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip().splitlines()[0].strip()
            if answer:
                return answer, True
    stripped = text.strip()
    if stripped and "\n" not in stripped and len(stripped) <= 800:
        return stripped, True
    return fallback, False


recovery.base.extract_answer = extract_readr_answer


if __name__ == "__main__":
    recovery.base.main()
