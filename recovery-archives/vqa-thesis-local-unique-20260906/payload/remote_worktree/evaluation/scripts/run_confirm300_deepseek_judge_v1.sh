#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ID="${1:-20260711_v1}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300_${RUN_ID}"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_groundtruth.json"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
JUDGE_MODES="${JUDGE_MODES:-answer_only}"
OVERWRITE="${OVERWRITE:-0}"

declare -a runs=(
  "raw_uniform:$RUN_ROOT/raw_uniform"
  "clip_singlepeak:$RUN_ROOT/clip_singlepeak"
  "adslot_fixed:$RUN_ROOT/adslot_fixed"
  "av_v1_framecap1:$RUN_ROOT/av_v1_framecap1"
  "av_v1_framecap1_cachedocr_trainnull:$RUN_ROOT/av_v1_framecap1_cachedocr_trainnull"
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

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" "$ADAPTER" "$EVALUATOR" "$RUN_ROOT/source_snapshot/"

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
    --output-dir "$RUN_ROOT/judge_deepseek_legacy_${mode}_v1" \
    --candidate-mode "$mode" \
    --max-workers "${MAX_WORKERS:-10}" \
    --bootstrap-samples 10000 \
    "${overwrite_args[@]}"
done

(
  cd "$RUN_ROOT"
  sha256sum source_snapshot/run_confirm300_deepseek_judge_v1.sh \
    source_snapshot/evaluate_adsqa_deepseek_legacy_v1.py \
    source_snapshot/evaluate_compare_new.py \
    > DEEPSEEK_JUDGE_SHA256SUMS
)

echo "confirm300_deepseek_judge=complete modes=$JUDGE_MODES"
