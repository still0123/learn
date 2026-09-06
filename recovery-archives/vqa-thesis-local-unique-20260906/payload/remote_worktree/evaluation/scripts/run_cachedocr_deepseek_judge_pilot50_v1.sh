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
JUDGE_MODES="${JUDGE_MODES:-answer_only}"
OVERWRITE="${OVERWRITE:-0}"

declare -a runs=(
  "adslot_fixed:$BASE_ROOT/adslot_fixed"
  "av_v1_framecap1:$F1_ROOT/av_v1_framecap1"
  "av_v1_framecap1_cov80:$C80_ROOT/av_v1_framecap1_cov80"
  "av_v1_framecap1_cachedocr:$OCR_ROOT/av_v1_framecap1_cachedocr"
)

test -f "$GROUNDTRUTH_FILE"
test -f "$EVALUATOR"
test -f "$ADAPTER"
for spec in "${runs[@]}"; do
  test -d "${spec#*:}"
done

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY must be set}"
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

adapter_runs=()
for spec in "${runs[@]}"; do
  adapter_runs+=(--run "${spec%%:*}" "${spec#*:}")
done

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

mkdir -p "$OCR_ROOT/source_snapshot"
cp "$0" "$ADAPTER" "$EVALUATOR" "$OCR_ROOT/source_snapshot/"

for mode in $JUDGE_MODES; do
  case "$mode" in
    answer_only|full_response) ;;
    *)
      echo "Unsupported JUDGE_MODES entry: $mode" >&2
      exit 2
      ;;
  esac

  "$PYTHON" "$ADAPTER" \
    "${adapter_runs[@]}" \
    --groundtruth-file "$GROUNDTRUTH_FILE" \
    --evaluator "$EVALUATOR" \
    --output-dir "$OCR_ROOT/judge_deepseek_legacy_${mode}_v1" \
    --candidate-mode "$mode" \
    --max-workers "${MAX_WORKERS:-10}" \
    --bootstrap-samples 5000 \
    "${overwrite_args[@]}"
done

(
  cd "$OCR_ROOT"
  sha256sum source_snapshot/run_cachedocr_deepseek_judge_pilot50_v1.sh \
    source_snapshot/evaluate_adsqa_deepseek_legacy_v1.py \
    source_snapshot/evaluate_compare_new.py \
    > DEEPSEEK_JUDGE_SHA256SUMS
)

echo "cachedocr_deepseek_judge=complete modes=$JUDGE_MODES"
