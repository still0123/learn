#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ID="${1:-20260711_v1}"
FRAME_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_framebalanced_pilot50_${RUN_ID}"
DEEPSEEK="$FRAME_ROOT/judge_deepseek_legacy_answer_only_v1/results.jsonl"
QWEN="$FRAME_ROOT/judge_local_qwen3_32b_awq_answer_only_calibration_v1/results.jsonl"
OUTPUT="$FRAME_ROOT/judge_local_qwen3_32b_awq_answer_only_calibration_v1/agreement_vs_historical_deepseek.json"
SOURCE_SNAPSHOT="$FRAME_ROOT/judge_local_qwen3_32b_awq_answer_only_calibration_v1/source_snapshot"

mkdir -p "$SOURCE_SNAPSHOT"
cp "$0" "$PROJECT_ROOT/evaluation/eval/analyze_judge_agreement.py" "$SOURCE_SNAPSHOT/"

"$PYTHON" "$PROJECT_ROOT/evaluation/eval/analyze_judge_agreement.py" \
  --left "$DEEPSEEK" \
  --right "$QWEN" \
  --left-name historical_deepseek \
  --right-name local_qwen3_32b_awq \
  --method adslot_fixed \
  --method av_v1_framecap1 \
  --pair adslot_fixed av_v1_framecap1 \
  --min-pooled-exact-rate 0.80 \
  --max-pooled-mad 0.10 \
  --require-pair-mean-sign-match \
  --output "$OUTPUT"

echo "qwen3_32b_judge_calibration_analysis=complete"
