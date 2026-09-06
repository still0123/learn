#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ID="${1:-20260712_v1}"
BASE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_20260711_v1"
FRAMECAP_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_framebalanced_pilot50_20260711_v1"
BUDGET_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_budget24g8l_pilot50_${RUN_ID}"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
OUTPUT="$BUDGET_ROOT/judge_deepseek_legacy_answer_only_v1"
OVERWRITE="${OVERWRITE:-0}"

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY must be set}"
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

mkdir -p "$BUDGET_ROOT/source_snapshot"
cp "$0" "$ADAPTER" "$EVALUATOR" "$BUDGET_ROOT/source_snapshot/"

"$PYTHON" "$ADAPTER" \
  --run raw_uniform "$BASE_ROOT/raw_uniform" \
  --run av_v1_framecap1 "$FRAMECAP_ROOT/av_v1_framecap1" \
  --run av_v1_budget24g8l "$BUDGET_ROOT/av_v1_budget24g8l" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$OUTPUT" \
  --candidate-mode answer_only \
  --max-workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000 \
  "${overwrite_args[@]}"

(
  cd "$BUDGET_ROOT"
  sha256sum source_snapshot/run_budget24g8l_deepseek_judge_pilot50_v1.sh \
    source_snapshot/evaluate_adsqa_deepseek_legacy_v1.py \
    source_snapshot/evaluate_compare_new.py > DEEPSEEK_JUDGE_SHA256SUMS
)
echo "budget24g8l_deepseek_judge=complete"
