#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
ENTRYPOINT="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_visual_protocol.py"
QUESTION_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
PILOT_MANIFEST="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_manifest.json"
RUN_ID="${1:-20260712_v1}"
OUTPUT_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_budget24g8l_pilot50_${RUN_ID}"
METHOD="av_v1_budget24g8l"
START_IDX="${START_IDX:-0}"
END_IDX="${END_IDX:-50}"
GPU_IDS="${GPU_IDS:-2 3 5}"
OVERWRITE="${OVERWRITE:-0}"
RUN_AUDIT="${RUN_AUDIT:-1}"

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

mkdir -p "$OUTPUT_ROOT/$METHOD" "$OUTPUT_ROOT/logs" "$OUTPUT_ROOT/source_snapshot"
cp "$PILOT_MANIFEST" "$OUTPUT_ROOT/pilot_subset_manifest.json"
cp "$0" "$ENTRYPOINT" "$PROJECT_ROOT/evaluation/methods/av_evidence/av_response.py" \
  "$AUDITOR" "$OUTPUT_ROOT/source_snapshot/"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

pids=()
status=0
num_shards="${#gpu_ids[@]}"
for shard_id in "${!gpu_ids[@]}"; do
  gpu_id="${gpu_ids[$shard_id]}"
  mkdir -p "$OUTPUT_ROOT/$METHOD/shard${shard_id}"
  "$PYTHON" "$ENTRYPOINT" \
    --gpu_id "$gpu_id" \
    --shard_id "$shard_id" \
    --num_shards "$num_shards" \
    --question_file "$QUESTION_FILE" \
    --groundtruth_file "$GROUNDTRUTH_FILE" \
    --start_idx "$START_IDX" \
    --end_idx "$END_IDX" \
    --oversample_count 32 \
    --top_k_frames 24 \
    --temporal_coverage_bins 0 \
    --visual_image_budget 32 \
    --max_local_views_per_frame 1 \
    --max_post_merge_visual_tokens 12000 \
    --output_dir "$OUTPUT_ROOT/$METHOD/shard${shard_id}" \
    "${overwrite_args[@]}" \
    >"$OUTPUT_ROOT/logs/${METHOD}_gpu${gpu_id}_shard${shard_id}.log" 2>&1 &
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

if [[ "$RUN_AUDIT" == "1" ]]; then
  if [[ "$START_IDX" != "0" || "$END_IDX" != "50" ]]; then
    echo "Full audit requires START_IDX=0 and END_IDX=50" >&2
    exit 2
  fi
  "$PYTHON" "$AUDITOR" \
    --question-file "$QUESTION_FILE" \
    --run "$METHOD" "$OUTPUT_ROOT/$METHOD" \
    --expected-frames 32 \
    --expected-tokens 11664 \
    --output "$OUTPUT_ROOT/audit_visual_protocol.json"
fi

(
  cd "$OUTPUT_ROOT"
  sha256sum source_snapshot/* pilot_subset_manifest.json > SHA256SUMS
)
echo "$METHOD=complete start=$START_IDX end=$END_IDX gpu_ids=$GPU_IDS"
