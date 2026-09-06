#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
FAIR_ENTRY="$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py"
AV_ENTRY="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
QUESTION_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_groundtruth.json"
MANIFEST="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_manifest.json"
RUN_ID="${1:-20260711_v1}"
OUTPUT_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300_${RUN_ID}"
START_IDX="${START_IDX:-0}"
END_IDX="${END_IDX:-300}"
OVERWRITE="${OVERWRITE:-0}"

mkdir -p "$OUTPUT_ROOT/source_snapshot" "$OUTPUT_ROOT/logs"
cp "$MANIFEST" "$OUTPUT_ROOT/confirm_subset_manifest.json"
cp "$0" "$FAIR_ENTRY" "$AV_ENTRY" "$PROJECT_ROOT/evaluation/methods/av_evidence/av_response.py" \
  "$PROJECT_ROOT/evaluation/methods/av_evidence/ocr_response.py" \
  "$PROJECT_ROOT/evaluation/methods/common/qwen_video_budget.py" \
  "$PROJECT_ROOT/evaluation/methods/common/adsqa_prompt.py" "$OUTPUT_ROOT/source_snapshot/"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

run_baseline() {
  local method="$1"
  local gpu="$2"
  mkdir -p "$OUTPUT_ROOT/$method"
  "$PYTHON" "$FAIR_ENTRY" \
    --gpu_id "$gpu" \
    --fair_method "$method" \
    --question_file "$QUESTION_FILE" \
    --groundtruth_file "$GROUNDTRUTH_FILE" \
    --start_idx "$START_IDX" \
    --end_idx "$END_IDX" \
    --visual_view_budget 32 \
    --max_post_merge_visual_tokens 12000 \
    --oversample_count 32 \
    --top_k_frames 16 \
    --output_dir "$OUTPUT_ROOT/$method" \
    "${overwrite_args[@]}" \
    >"$OUTPUT_ROOT/logs/${method}.log" 2>&1
}

run_framecap() {
  local pids=()
  local status=0
  local method="av_v1_framecap1"
  mkdir -p "$OUTPUT_ROOT/$method"
  for spec in "0:2" "1:3" "2:5"; do
    local shard_id="${spec%%:*}"
    local gpu_id="${spec##*:}"
    mkdir -p "$OUTPUT_ROOT/$method/shard${shard_id}"
    "$PYTHON" "$AV_ENTRY" \
      --gpu_id "$gpu_id" \
      --shard_id "$shard_id" \
      --num_shards 3 \
      --question_file "$QUESTION_FILE" \
      --groundtruth_file "$GROUNDTRUTH_FILE" \
      --start_idx "$START_IDX" \
      --end_idx "$END_IDX" \
      --oversample_count 32 \
      --top_k_frames 16 \
      --temporal_coverage_bins 0 \
      --visual_image_budget 32 \
      --max_local_views_per_frame 1 \
      --max_post_merge_visual_tokens 12000 \
      --output_dir "$OUTPUT_ROOT/$method/shard${shard_id}" \
      "${overwrite_args[@]}" \
      >"$OUTPUT_ROOT/logs/${method}_shard${shard_id}.log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      status=1
    fi
  done
  return "$status"
}

# One fair baseline per allowed GPU; GPU 1 remains untouched.
pids=()
run_baseline raw_uniform 5 & pids+=("$!")
run_baseline clip_singlepeak 2 & pids+=("$!")
run_baseline adslot_fixed 3 & pids+=("$!")
status=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    status=1
  fi
done
if [[ "$status" != "0" ]]; then
  exit "$status"
fi

run_framecap

(
  cd "$OUTPUT_ROOT"
  sha256sum source_snapshot/* confirm_subset_manifest.json > SHA256SUMS
)
echo "confirm300_baselines_framecap=complete"
