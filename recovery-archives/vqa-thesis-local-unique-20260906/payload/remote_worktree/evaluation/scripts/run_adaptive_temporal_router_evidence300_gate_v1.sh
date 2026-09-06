#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/adaptive_temporal_router_evidence300_v1"
DATA_ROOT="$PROJECT_ROOT/data/innovation1_evidence300_v1"
STAGE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_evidence300_stage_v1"
DATASET="$RUN_ROOT/router_dataset.jsonl"

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/tools/build_adaptive_temporal_router_dataset_v1.py" \
  "$PROJECT_ROOT/evaluation/methods/adaptive_temporal_router/features.py" \
  "$PROJECT_ROOT/evaluation/methods/adaptive_temporal_router/metrics.py" \
  "$PROJECT_ROOT/evaluation/methods/adaptive_temporal_router/numpy_model.py" \
  "$PROJECT_ROOT/evaluation/methods/adaptive_temporal_router/train_router_v1.py" \
  "$RUN_ROOT/source_snapshot/"

"$PYTHON" "$PROJECT_ROOT/evaluation/tools/build_adaptive_temporal_router_dataset_v1.py" \
  --question-file "$DATA_ROOT/question.json" \
  --assignments-file "$DATA_ROOT/assignments.json" \
  --judge-results "$STAGE_ROOT/deepseek_judge_v1/results.jsonl" \
  --mmr-cache "$STAGE_ROOT/exploratory_dev200_v1/mmr32_cache/cache.jsonl" \
  --mmr-cache "$STAGE_ROOT/exploratory_tail100_v1/mmr32_cache/cache.jsonl" \
  --asr-file "$PROJECT_ROOT/evaluation/asr_set.json" \
  --output-jsonl "$DATASET" \
  --audit-output "$RUN_ROOT/dataset_audit.json"

"$PYTHON" "$PROJECT_ROOT/evaluation/methods/adaptive_temporal_router/train_router_v1.py" \
  --dataset-jsonl "$DATASET" --output-root "$RUN_ROOT/model_gate_v1" \
  --hash-dim 64 --hidden-dim 16 --epochs 800 --learning-rate 0.01 \
  --l2 0.001 --patience 80 --min-switch-precision 0.70 \
  --bootstrap-samples 10000 --seed 42

echo "adaptive_temporal_router_evidence300_gate=complete"
