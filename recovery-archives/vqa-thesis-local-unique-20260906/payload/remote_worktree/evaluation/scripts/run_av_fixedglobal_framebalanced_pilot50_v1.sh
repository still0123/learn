#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
ENTRYPOINT="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
QUESTION_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
PILOT_MANIFEST="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_manifest.json"
RUN_ID="${1:-20260711_v1}"
OUTPUT_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_fixedglobal_framebalanced_pilot50_${RUN_ID}"
METHOD="av_v1_fixedglobal_framecap1"
START_IDX="${START_IDX:-0}"
END_IDX="${END_IDX:-50}"
OVERWRITE="${OVERWRITE:-0}"

mkdir -p "$OUTPUT_ROOT/$METHOD" "$OUTPUT_ROOT/logs" "$OUTPUT_ROOT/source_snapshot"
cp "$PILOT_MANIFEST" "$OUTPUT_ROOT/pilot_subset_manifest.json"
cp "$0" "$ENTRYPOINT" "$PROJECT_ROOT/evaluation/methods/av_evidence/av_response.py" "$OUTPUT_ROOT/source_snapshot/"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

pids=()
status=0
for spec in "0:2" "1:3" "2:5"; do
  shard_id="${spec%%:*}"
  gpu_id="${spec##*:}"
  mkdir -p "$OUTPUT_ROOT/$METHOD/shard${shard_id}"
  "$PYTHON" "$ENTRYPOINT" \
    --gpu_id "$gpu_id" \
    --shard_id "$shard_id" \
    --num_shards 3 \
    --question_file "$QUESTION_FILE" \
    --groundtruth_file "$GROUNDTRUTH_FILE" \
    --start_idx "$START_IDX" \
    --end_idx "$END_IDX" \
    --oversample_count 32 \
    --top_k_frames 16 \
    --global_question_weight 0.6 \
    --global_audio_weight 0.4 \
    --temporal_coverage_bins 0 \
    --visual_image_budget 32 \
    --max_local_views_per_frame 1 \
    --max_post_merge_visual_tokens 12000 \
    --output_dir "$OUTPUT_ROOT/$METHOD/shard${shard_id}" \
    "${overwrite_args[@]}" \
    >"$OUTPUT_ROOT/logs/${METHOD}_shard${shard_id}.log" 2>&1 &
  pids+=("$!")
done

for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    status=1
  fi
done
if [[ "$status" != "0" ]]; then
  exit "$status"
fi

(
  cd "$OUTPUT_ROOT"
  sha256sum source_snapshot/* pilot_subset_manifest.json > SHA256SUMS
)
echo "av_v1_fixedglobal_framecap1=complete"
