#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ID="${1:-20260711_v1}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_${RUN_ID}"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY must be set}"
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

run_judge() {
  local candidate_mode="$1"
  local output_dir="$2"
  "$PYTHON" "$ADAPTER" \
    --run raw_uniform "$RUN_ROOT/raw_uniform" \
    --run clip_singlepeak "$RUN_ROOT/clip_singlepeak" \
    --run adslot_fixed "$RUN_ROOT/adslot_fixed" \
    --run av_v1 "$RUN_ROOT/av_v1" \
    --run av_v2 "$RUN_ROOT/av_v2" \
    --groundtruth-file "$GROUNDTRUTH_FILE" \
    --evaluator "$EVALUATOR" \
    --output-dir "$output_dir" \
    --candidate-mode "$candidate_mode" \
    --max-workers 10 \
    --bootstrap-samples 5000 \
    --overwrite
}

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" "$RUN_ROOT/source_snapshot/$(basename "$0")"
cp "$ADAPTER" "$EVALUATOR" "$RUN_ROOT/source_snapshot/"

run_judge full_response "$RUN_ROOT/judge_deepseek_legacy_full_response_v1"
run_judge answer_only "$RUN_ROOT/judge_deepseek_legacy_answer_only_v1"
echo "validanswer_pilot50_judges=complete"
