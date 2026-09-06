#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
REFERENCE="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/confirm100_v1"
FIRST_CACHE="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/crop_rerunocr_confirm50_v1"
SECOND_CACHE="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/crop_rerunocr_confirm50b_v1"
RUN="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/matched_ocr_confirm100_v1"
TOOLS="$ROOT/evaluation/tools"
export PYTHONPATH="/data1/rmx/tools/adsqa_rapidocr${PYTHONPATH:+:$PYTHONPATH}"
export DISABLE_MODEL_SOURCE_CHECK=True

mkdir -p "$RUN/logs" "$RUN/pids" "$RUN/source_snapshot"
test ! -e "$RUN/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
echo "$$" > "$RUN/pids/driver.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/PIPELINE_FAILED"' ERR
cp "$TOOLS/infer_ocr_crop_factorial_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/match_ocr_count_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/audit_matched_ocr_confirm100_v1.py" "$RUN/source_snapshot/"
cp "$ROOT/evaluation/scripts/run_matched_ocr_confirm100_v1.sh" "$RUN/source_snapshot/"

cp "$REFERENCE/dataset_100.jsonl" "$RUN/dataset_100.jsonl"
"$PY" "$TOOLS/match_ocr_count_v1.py" \
  --crop-cache "$FIRST_CACHE/ocr_cache_crop.jsonl" \
  --full-cache "$FIRST_CACHE/ocr_cache_full.jsonl" \
  --output-crop "$RUN/ocr_cache_crop.jsonl" \
  --output-full "$RUN/ocr_cache_full.jsonl" > "$RUN/logs/match.log" 2>&1

run_arm() {
  local gpu="$1" arm="$2" visual="$3" cache="$4"
  "$PY" "$TOOLS/infer_ocr_crop_factorial_v1.py" \
    --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$RUN/dataset_100.jsonl" \
    --output-dir "$RUN/$arm" --visual-mode "$visual" --ocr-mode rerun \
    --ocr-cache "$cache" --crop-size 896 --crop-side 0.35 \
    --max-visual-tokens 4160 --expected-items 100 --resume-existing
}
run_arm 1 crop_rerunocr crop "$RUN/ocr_cache_crop.jsonl" > "$RUN/logs/crop.log" 2>&1 &
echo "$!" > "$RUN/pids/crop.pid"
run_arm 2 full_rerunocr full "$RUN/ocr_cache_full.jsonl" > "$RUN/logs/full.log" 2>&1 &
echo "$!" > "$RUN/pids/full.pid"
wait

"$PY" "$TOOLS/audit_matched_ocr_confirm100_v1.py" \
  --run-root "$RUN" --reference-root "$REFERENCE" \
  --dataset "$RUN/dataset_100.jsonl" --expected 100 > "$RUN/logs/audit.log" 2>&1
(
  cd "$RUN"
  find source_snapshot dataset_100.jsonl ocr_cache_*.jsonl matched_ocr_audit.json protocol_audit.json -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
