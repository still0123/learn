#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
GPU_ID="${GPU_ID:-4}"
STAGE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_claim_verifier_v2"
DATA_ROOT="$STAGE_ROOT/smoke30_oracle_protocol_v1"
OUTPUT_ROOT="$STAGE_ROOT/smoke30_qwen_support_v1"

[[ -s "$DATA_ROOT/input.jsonl" ]] || { echo "missing smoke input" >&2; exit 2; }
[[ -s "$DATA_ROOT/oracle_plans.jsonl" ]] || { echo "missing oracle plans" >&2; exit 2; }
mkdir -p "$OUTPUT_ROOT/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/inference_intervention_smoke_v2.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/metrics_v2.py" \
  "$OUTPUT_ROOT/source_snapshot/"

exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/inference_intervention_smoke_v2.py" \
  --gpu-id "$GPU_ID" --input-jsonl "$DATA_ROOT/input.jsonl" \
  --oracle-jsonl "$DATA_ROOT/oracle_plans.jsonl" --output-root "$OUTPUT_ROOT"
