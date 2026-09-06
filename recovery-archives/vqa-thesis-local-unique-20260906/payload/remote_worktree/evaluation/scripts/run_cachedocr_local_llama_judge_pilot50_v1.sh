#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ID="${1:-20260711_v1}"
BASE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_${RUN_ID}"
F1_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_framebalanced_pilot50_${RUN_ID}"
C80_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_framebalanced_cov80_pilot50_${RUN_ID}"
OCR_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_cachedocr_framebalanced_pilot50_${RUN_ID}"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
OUTPUT="$OCR_ROOT/judge_local_llama31_70b_answer_only_v1"

export DEEPSEEK_API_KEY="EMPTY_LOCAL_VLLM"
export DEEPSEEK_BASE_URL="${LOCAL_LLAMA_BASE_URL:-http://127.0.0.1:18000/v1}"
export DEEPSEEK_MODEL="${LOCAL_LLAMA_MODEL:-llama-local}"

curl --fail --silent --max-time 10 "$DEEPSEEK_BASE_URL/models" >/dev/null
mkdir -p "$OCR_ROOT/source_snapshot"
cp "$0" "$ADAPTER" "$EVALUATOR" "$OCR_ROOT/source_snapshot/"

"$PYTHON" "$ADAPTER" \
  --run adslot_fixed "$BASE_ROOT/adslot_fixed" \
  --run av_v1_framecap1 "$F1_ROOT/av_v1_framecap1" \
  --run av_v1_framecap1_cov80 "$C80_ROOT/av_v1_framecap1_cov80" \
  --run av_v1_framecap1_cachedocr "$OCR_ROOT/av_v1_framecap1_cachedocr" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$OUTPUT" \
  --candidate-mode answer_only \
  --max-workers 5 \
  --bootstrap-samples 5000 \
  --overwrite

echo "cachedocr_local_llama_judge=complete"
