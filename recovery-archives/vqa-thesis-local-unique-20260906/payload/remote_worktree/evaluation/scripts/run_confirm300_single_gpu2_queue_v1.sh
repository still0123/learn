#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
FAIR_ENTRY="$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py"
AV_ENTRY="$PROJECT_ROOT/evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py"
AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_visual_protocol.py"
QUESTION_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_groundtruth.json"
MANIFEST="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_manifest.json"
NULL_QUESTIONS="$PROJECT_ROOT/data/train.json"
OCR_CACHE="$PROJECT_ROOT/evaluation/cache/ocr/confirm300_framecap1_rapidocr_v1.json"
RUN_ID="${1:-20260711_v1}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300_${RUN_ID}"
WAIT_PID="${WAIT_PID:-}"

mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/source_snapshot"
cp "$0" "$FAIR_ENTRY" "$AV_ENTRY" "$AUDITOR" \
  "$PROJECT_ROOT/evaluation/methods/av_evidence/av_response.py" \
  "$PROJECT_ROOT/evaluation/methods/av_evidence/ocr_response.py" \
  "$PROJECT_ROOT/evaluation/methods/common/qwen_video_budget.py" \
  "$PROJECT_ROOT/evaluation/methods/common/adsqa_prompt.py" "$RUN_ROOT/source_snapshot/"
cp "$MANIFEST" "$RUN_ROOT/confirm_subset_manifest.json"

if [[ -n "$WAIT_PID" ]]; then
  while kill -0 "$WAIT_PID" 2>/dev/null; do
    sleep 30
  done
fi

run_fair() {
  local method="$1"
  local output="$RUN_ROOT/$method"
  mkdir -p "$output"
  "$PYTHON" "$FAIR_ENTRY" \
    --gpu_id 2 \
    --fair_method "$method" \
    --question_file "$QUESTION_FILE" \
    --groundtruth_file "$GROUNDTRUTH_FILE" \
    --start_idx 0 \
    --end_idx 300 \
    --visual_view_budget 32 \
    --max_post_merge_visual_tokens 12000 \
    --oversample_count 32 \
    --top_k_frames 16 \
    --output_dir "$output" \
    >"$RUN_ROOT/logs/${method}_gpu2_resume.log" 2>&1
}

assert_prediction_count() {
  local method="$1"
  local count
  count="$(find "$RUN_ROOT/$method" -name prediction.json -type f | wc -l)"
  if [[ "$count" != "300" ]]; then
    echo "$method prediction coverage is $count/300" >&2
    exit 1
  fi
}

# CLIP is completed by the process named in WAIT_PID. The remaining baselines
# resume from their existing successful question directories.
assert_prediction_count clip_singlepeak
run_fair raw_uniform
assert_prediction_count raw_uniform
run_fair adslot_fixed
assert_prediction_count adslot_fixed

mkdir -p "$RUN_ROOT/av_v1_framecap1/shard0"
"$PYTHON" "$AV_ENTRY" \
  --gpu_id 2 \
  --shard_id 0 \
  --num_shards 1 \
  --question_file "$QUESTION_FILE" \
  --groundtruth_file "$GROUNDTRUTH_FILE" \
  --start_idx 0 \
  --end_idx 300 \
  --oversample_count 32 \
  --top_k_frames 16 \
  --temporal_coverage_bins 0 \
  --visual_image_budget 32 \
  --max_local_views_per_frame 1 \
  --max_post_merge_visual_tokens 12000 \
  --output_dir "$RUN_ROOT/av_v1_framecap1/shard0" \
  >"$RUN_ROOT/logs/av_v1_framecap1_gpu2.log" 2>&1
assert_prediction_count av_v1_framecap1

bash "$PROJECT_ROOT/evaluation/scripts/precompute_confirm300_framecap_ocr_v1.sh" "$RUN_ID"
test -f "$OCR_CACHE"

mkdir -p "$RUN_ROOT/av_v1_framecap1_cachedocr_trainnull/shard0"
"$PYTHON" "$AV_ENTRY" \
  --gpu_id 2 \
  --shard_id 0 \
  --num_shards 1 \
  --question_file "$QUESTION_FILE" \
  --groundtruth_file "$GROUNDTRUTH_FILE" \
  --start_idx 0 \
  --end_idx 300 \
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
  --output_dir "$RUN_ROOT/av_v1_framecap1_cachedocr_trainnull/shard0" \
  >"$RUN_ROOT/logs/av_v1_framecap1_cachedocr_trainnull_gpu2.log" 2>&1
assert_prediction_count av_v1_framecap1_cachedocr_trainnull

"$PYTHON" "$AUDITOR" \
  --question-file "$QUESTION_FILE" \
  --run raw_uniform "$RUN_ROOT/raw_uniform" \
  --run clip_singlepeak "$RUN_ROOT/clip_singlepeak" \
  --run adslot_fixed "$RUN_ROOT/adslot_fixed" \
  --run av_v1_framecap1 "$RUN_ROOT/av_v1_framecap1" \
  --run av_v1_framecap1_cachedocr_trainnull "$RUN_ROOT/av_v1_framecap1_cachedocr_trainnull" \
  --output "$RUN_ROOT/audit_visual_protocol.json" \
  >"$RUN_ROOT/logs/audit_visual_protocol.log"

"$PYTHON" - "$RUN_ROOT/audit_visual_protocol.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if not payload["all_valid"]:
    raise SystemExit("visual protocol audit failed")
PY

(
  cd "$RUN_ROOT"
  sha256sum source_snapshot/* confirm_subset_manifest.json > SHA256SUMS
)
echo "confirm300_single_gpu2_queue=complete"
