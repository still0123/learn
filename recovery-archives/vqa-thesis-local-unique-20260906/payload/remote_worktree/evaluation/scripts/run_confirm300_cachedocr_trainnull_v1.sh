#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
ENTRYPOINT="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
OCR_RESPONSE="$PROJECT_ROOT/evaluation/methods/av_evidence/ocr_response.py"
OCR_PRECOMPUTE="$PROJECT_ROOT/evaluation/tools/precompute_ocr_evidence.py"
OCR_CACHE="$PROJECT_ROOT/evaluation/cache/ocr/confirm300_framecap1_rapidocr_v1.json"
NULL_QUESTIONS="$PROJECT_ROOT/data/train.json"
QUESTION_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_groundtruth.json"
MANIFEST="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_manifest.json"
RUN_ID="${1:-20260711_v1}"
OUTPUT_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300_${RUN_ID}"
METHOD="av_v1_framecap1_cachedocr_trainnull"
START_IDX="${START_IDX:-0}"
END_IDX="${END_IDX:-300}"
OVERWRITE="${OVERWRITE:-0}"

test -f "$OCR_CACHE"
test -f "$NULL_QUESTIONS"
mkdir -p "$OUTPUT_ROOT/$METHOD" "$OUTPUT_ROOT/logs" "$OUTPUT_ROOT/source_snapshot"
cp "$MANIFEST" "$OUTPUT_ROOT/confirm_subset_manifest.json"
cp "$0" "$ENTRYPOINT" "$OCR_RESPONSE" "$OCR_PRECOMPUTE" \
  "$PROJECT_ROOT/evaluation/methods/av_evidence/av_response.py" "$OUTPUT_ROOT/source_snapshot/"
cp "$OCR_CACHE.sha256" "$OUTPUT_ROOT/source_snapshot/confirm300_framecap1_rapidocr_v1.sha256"

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
    --temporal_coverage_bins 0 \
    --visual_image_budget 32 \
    --max_local_views_per_frame 1 \
    --ocr_proxy cache \
    --ocr_proxy_reliability 0.80 \
    --ocr_min_confidence 0.50 \
    --ocr_relevance_scope train_null \
    --ocr_null_question_file "$NULL_QUESTIONS" \
    --ocr_cache_file "$OCR_CACHE" \
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
  sha256sum source_snapshot/* confirm_subset_manifest.json > SHA256SUMS
)
echo "confirm300_cachedocr_trainnull=complete"
