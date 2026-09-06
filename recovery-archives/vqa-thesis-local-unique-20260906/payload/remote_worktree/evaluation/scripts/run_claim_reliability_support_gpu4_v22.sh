#!/usr/bin/env bash
set -euo pipefail
ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/innovation2_claim_reliability_v22"
mkdir -p "$RUN/qwen_full_support/source_snapshot"
cp "$0" "$ROOT/evaluation/methods/claim_evidence_verifier/inference_intervention_smoke_v2.py" "$RUN/qwen_full_support/source_snapshot/"
exec "$PYTHON" "$ROOT/evaluation/methods/claim_evidence_verifier/inference_intervention_smoke_v2.py" \
  --gpu-id 4 --input-jsonl "$RUN/dataset/input.jsonl" --oracle-jsonl "$RUN/dataset/input.jsonl" \
  --output-root "$RUN/qwen_full_support" --full-only
