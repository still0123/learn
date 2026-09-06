#!/usr/bin/env bash
set -euo pipefail
ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/innovation2_claim_reliability_v22"
E1="$ROOT/evaluation/runs/innovation1_evidence300_stage_v1"
mkdir -p "$RUN/dataset/source_snapshot"
cp "$0" "$ROOT/evaluation/tools/build_claim_reliability_inputs_v22.py" "$RUN/dataset/source_snapshot/"
exec "$PYTHON" "$ROOT/evaluation/tools/build_claim_reliability_inputs_v22.py" \
  --router-dataset "$ROOT/evaluation/runs/adaptive_temporal_router_evidence300_v1/router_dataset.jsonl" \
  --raw-result-root "$E1/formal_raw_uniform_v1" \
  --judge-results "$E1/deepseek_judge_v1/results.jsonl" --output-root "$RUN/dataset"
