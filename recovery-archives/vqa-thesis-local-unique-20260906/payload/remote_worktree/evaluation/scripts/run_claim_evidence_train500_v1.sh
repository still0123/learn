#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/claim_evidence_stage1_v1"
RAW_PAIRS="$RUN_ROOT/train500_candidates/postprocess/raw_uniform/pairs.jsonl"
MMR_PAIRS="$RUN_ROOT/train500_candidates/postprocess/innovation1_mmr32/pairs.jsonl"
MODEL_ROOT="$RUN_ROOT/model_v1"

[[ -s "$RAW_PAIRS" ]] || { echo "missing Raw Train500 pairs: $RAW_PAIRS" >&2; exit 2; }
pair_args=(--pair-jsonl "$RAW_PAIRS")
if [[ -s "$MMR_PAIRS" ]]; then pair_args+=(--pair-jsonl "$MMR_PAIRS"); fi
mkdir -p "$MODEL_ROOT/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/features.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/numpy_mlp.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/metrics.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/train_verifier_v1.py" \
  "$MODEL_ROOT/source_snapshot/"
exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/train_verifier_v1.py" \
  "${pair_args[@]}" --checkpoint-output "$MODEL_ROOT/checkpoint.json" \
  --report-output "$MODEL_ROOT/training_report.json" --hash-dim 256 --hidden-dim 64 \
  --epochs 800 --learning-rate 0.01 --l2 0.0001 --patience 80 \
  --calibration-fraction 0.20 --seed 42
