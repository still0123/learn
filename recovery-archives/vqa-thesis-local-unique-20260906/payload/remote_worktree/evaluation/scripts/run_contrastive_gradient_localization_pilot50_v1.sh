#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
ENTRYPOINT="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
EVIDENCE_EVAL="$PROJECT_ROOT/evaluation/eval/build_evidence_recall_annotation_pack.py"
QUESTION_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
MANIFEST="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_manifest.json"
ANNOTATIONS="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_20260711_v1/evidence_recall_annotation_v1/manual_annotations_v1.json"
PATCH_RUN="$PROJECT_ROOT/evaluation/runs/innovation1_framebalanced_pilot50_20260711_v1/av_v1_framecap1"
RUN_ID="${1:-20260712_v1}"
OUTPUT_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_contrastive_gradient_localization_pilot50_${RUN_ID}"
METHOD="av_v1_framecap1_contrastive_gradient"
GPU_IDS="${GPU_IDS:-2 3 5}"
OVERWRITE="${OVERWRITE:-0}"

read -r -a gpu_ids <<<"$GPU_IDS"
for gpu_id in "${gpu_ids[@]}"; do
  case "$gpu_id" in 2|3|5) ;; *) echo "Only GPU 2, 3, and 5 are allowed" >&2; exit 2 ;; esac
done
if [[ "${#gpu_ids[@]}" -eq 0 ]]; then exit 2; fi

mkdir -p "$OUTPUT_ROOT/$METHOD" "$OUTPUT_ROOT/logs" "$OUTPUT_ROOT/source_snapshot"
cp "$0" "$ENTRYPOINT" "$EVIDENCE_EVAL" "$MANIFEST" "$OUTPUT_ROOT/source_snapshot/"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then overwrite_args+=(--overwrite); fi

pids=()
status=0
num_shards="${#gpu_ids[@]}"
for shard_id in "${!gpu_ids[@]}"; do
  gpu_id="${gpu_ids[$shard_id]}"
  shard_root="$OUTPUT_ROOT/$METHOD/shard${shard_id}"
  mkdir -p "$shard_root"
  "$PYTHON" "$ENTRYPOINT" \
    --gpu_id "$gpu_id" --shard_id "$shard_id" --num_shards "$num_shards" \
    --question_file "$QUESTION_FILE" --groundtruth_file "$GROUNDTRUTH_FILE" \
    --start_idx 0 --end_idx 50 \
    --oversample_count 32 --top_k_frames 16 --visual_image_budget 32 \
    --max_local_views_per_frame 1 --spatial_response_mode contrastive_gradient \
    --localization_only --output_dir "$shard_root" "${overwrite_args[@]}" \
    >"$OUTPUT_ROOT/logs/${METHOD}_gpu${gpu_id}_shard${shard_id}.log" 2>&1 &
  pids+=("$!")
done
for pid in "${pids[@]}"; do if ! wait "$pid"; then status=1; fi; done
if [[ "$status" != "0" ]]; then exit "$status"; fi

count="$(find "$OUTPUT_ROOT/$METHOD" -name evidence.json -type f | wc -l)"
if [[ "$count" != "50" ]]; then
  echo "evidence count is $count, expected 50" >&2
  exit 1
fi

"$PYTHON" "$EVIDENCE_EVAL" \
  --question-file "$QUESTION_FILE" --groundtruth-file "$GROUNDTRUTH_FILE" \
  --asr-file "$PROJECT_ROOT/evaluation/asr_set.json" --video-dir "$PROJECT_ROOT/data/videos" \
  --output-dir "$OUTPUT_ROOT/evidence_recall_annotation_v1" \
  --method patch_cosine="$PATCH_RUN" \
  --method contrastive_gradient="$OUTPUT_ROOT/$METHOD" \
  --annotation-overlay "$ANNOTATIONS" --skip-render

(
  cd "$OUTPUT_ROOT"
  sha256sum source_snapshot/* > SHA256SUMS
)
echo "contrastive_gradient_localization=complete evidence=$count"
