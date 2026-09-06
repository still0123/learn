#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ID="${1:-20260711_v1}"
BASE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_${RUN_ID}"
FRAME_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_cachedocr_framebalanced_pilot50_${RUN_ID}"
VIDEO_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_cachedocr_videorelevance_pilot50_${RUN_ID}"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
OUTPUT="$VIDEO_ROOT/judge_deepseek_legacy_answer_only_v1"
OVERWRITE="${OVERWRITE:-0}"

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY must be set}"
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

mkdir -p "$VIDEO_ROOT/source_snapshot"
cp "$0" "$ADAPTER" "$EVALUATOR" "$VIDEO_ROOT/source_snapshot/"

"$PYTHON" "$ADAPTER" \
  --run adslot_fixed "$BASE_ROOT/adslot_fixed" \
  --run av_v1_framecap1_cachedocr "$FRAME_ROOT/av_v1_framecap1_cachedocr" \
  --run av_v1_framecap1_cachedocr_videorelevance "$VIDEO_ROOT/av_v1_framecap1_cachedocr_videorelevance" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$OUTPUT" \
  --candidate-mode answer_only \
  --max-workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 5000 \
  "${overwrite_args[@]}"

echo "cachedocr_videorelevance_deepseek_judge=complete"
