#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
STAGE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_claim_verifier_v2"
DATA_ROOT="$STAGE_ROOT/smoke30_oracle_protocol_v1"
RUN_ROOT="$STAGE_ROOT/smoke30_qwen_support_v1"

exec "$PYTHON" "$PROJECT_ROOT/evaluation/eval/analyze_claim_evidence_smoke_v2.py" \
  --scores "$RUN_ROOT/scores.jsonl" --supervision "$DATA_ROOT/supervision.jsonl" \
  --output "$RUN_ROOT/diagnostic_analysis.json"
