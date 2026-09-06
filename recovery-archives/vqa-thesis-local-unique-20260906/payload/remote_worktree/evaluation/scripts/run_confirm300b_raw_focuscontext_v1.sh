#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
FAIR_ENTRY="$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py"
AV_ENTRY="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
FOCUS_CONTEXT="$PROJECT_ROOT/evaluation/methods/av_evidence/focus_context.py"
AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_visual_protocol.py"
FOCUS_AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_focus_context.py"
QUESTION_FILE="$PROJECT_ROOT/data/confirm300b_focuscontext_disjoint_prior_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/confirm300b_focuscontext_disjoint_prior_groundtruth.json"
MANIFEST="$PROJECT_ROOT/data/confirm300b_focuscontext_disjoint_prior_manifest.json"
RUN_ID="${1:-20260712_v1}"
OUTPUT_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300b_focuscontext_${RUN_ID}"
GPU_IDS="${GPU_IDS:-2 3 5}"
START_IDX="${START_IDX:-0}"
END_IDX="${END_IDX:-300}"
OVERWRITE="${OVERWRITE:-0}"

read -r -a gpu_ids <<<"$GPU_IDS"
if [[ "${#gpu_ids[@]}" -eq 0 ]]; then
  echo "GPU_IDS must not be empty" >&2
  exit 2
fi
for gpu_id in "${gpu_ids[@]}"; do
  case "$gpu_id" in
    2|3|5) ;;
    *) echo "Only GPU 2, 3, and 5 are allowed; got $gpu_id" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUTPUT_ROOT/source_snapshot" "$OUTPUT_ROOT/logs"
cp "$MANIFEST" "$OUTPUT_ROOT/confirm_subset_manifest.json"
cp "$0" "$FAIR_ENTRY" "$AV_ENTRY" "$FOCUS_CONTEXT" "$AUDITOR" "$FOCUS_AUDITOR" \
  "$PROJECT_ROOT/evaluation/methods/av_evidence/av_response.py" \
  "$PROJECT_ROOT/evaluation/methods/av_evidence/ocr_response.py" \
  "$PROJECT_ROOT/evaluation/methods/common/qwen_video_budget.py" \
  "$PROJECT_ROOT/evaluation/methods/common/adsqa_prompt.py" \
  "$OUTPUT_ROOT/source_snapshot/"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

assert_count() {
  local method="$1"
  local count
  count="$(find "$OUTPUT_ROOT/$method" -name prediction.json -type f | wc -l)"
  if [[ "$count" != "300" ]]; then
    echo "$method prediction count is $count, expected 300" >&2
    return 1
  fi
}

run_raw() {
  local method="raw_uniform"
  local pids=()
  local status=0
  local num_shards="${#gpu_ids[@]}"
  mkdir -p "$OUTPUT_ROOT/$method"
  for shard_id in "${!gpu_ids[@]}"; do
    local gpu_id="${gpu_ids[$shard_id]}"
    local shard_root="$OUTPUT_ROOT/$method/shard${shard_id}"
    mkdir -p "$shard_root"
    "$PYTHON" "$FAIR_ENTRY" \
      --gpu_id "$gpu_id" --shard_id "$shard_id" --num_shards "$num_shards" \
      --fair_method raw_uniform \
      --question_file "$QUESTION_FILE" --groundtruth_file "$GROUNDTRUTH_FILE" \
      --start_idx "$START_IDX" --end_idx "$END_IDX" \
      --visual_view_budget 32 --max_post_merge_visual_tokens 12000 \
      --oversample_count 32 --top_k_frames 16 \
      --output_dir "$shard_root" "${overwrite_args[@]}" \
      >"$OUTPUT_ROOT/logs/${method}_gpu${gpu_id}_shard${shard_id}.log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then status=1; fi
  done
  return "$status"
}

run_focus() {
  local method="av_v1_focuscontext32_budget8"
  local pids=()
  local status=0
  local num_shards="${#gpu_ids[@]}"
  mkdir -p "$OUTPUT_ROOT/$method"
  for shard_id in "${!gpu_ids[@]}"; do
    local gpu_id="${gpu_ids[$shard_id]}"
    local shard_root="$OUTPUT_ROOT/$method/shard${shard_id}"
    mkdir -p "$shard_root"
    "$PYTHON" "$AV_ENTRY" \
      --gpu_id "$gpu_id" --shard_id "$shard_id" --num_shards "$num_shards" \
      --question_file "$QUESTION_FILE" --groundtruth_file "$GROUNDTRUTH_FILE" \
      --start_idx "$START_IDX" --end_idx "$END_IDX" \
      --oversample_count 32 --top_k_frames 32 --temporal_coverage_bins 0 \
      --visual_image_budget 32 --max_local_views_per_frame 1 \
      --focus_context_budget 8 --focus_context_global_fraction 0.50 \
      --max_post_merge_visual_tokens 12000 \
      --output_dir "$shard_root" "${overwrite_args[@]}" \
      >"$OUTPUT_ROOT/logs/${method}_gpu${gpu_id}_shard${shard_id}.log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then status=1; fi
  done
  return "$status"
}

run_raw
assert_count raw_uniform
run_focus
assert_count av_v1_focuscontext32_budget8

"$PYTHON" "$AUDITOR" \
  --question-file "$QUESTION_FILE" \
  --run raw_uniform "$OUTPUT_ROOT/raw_uniform" \
  --run av_v1_focuscontext32_budget8 "$OUTPUT_ROOT/av_v1_focuscontext32_budget8" \
  --expected-frames 32 --expected-tokens 11664 \
  --output "$OUTPUT_ROOT/audit_visual_protocol.json"

"$PYTHON" "$FOCUS_AUDITOR" \
  --question-file "$QUESTION_FILE" \
  --raw-run "$OUTPUT_ROOT/raw_uniform" \
  --focus-run "$OUTPUT_ROOT/av_v1_focuscontext32_budget8" \
  --expected-frames 32 --expected-focus 8 \
  --output "$OUTPUT_ROOT/audit_focus_context.json"

(
  cd "$OUTPUT_ROOT"
  sha256sum source_snapshot/* confirm_subset_manifest.json > SHA256SUMS
)
echo "confirm300b_raw_focuscontext=complete gpu_ids=$GPU_IDS"
