#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
REFERENCE="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/confirm100_v1"
FIRST_HALF="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/crop_rerunocr_confirm50_v1/dataset_50.jsonl"
RUN="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/crop_rerunocr_confirm50b_v1"
TOOLS="$ROOT/evaluation/tools"
export PYTHONPATH="/data1/rmx/tools/adsqa_rapidocr${PYTHONPATH:+:$PYTHONPATH}"
export DISABLE_MODEL_SOURCE_CHECK=True

mkdir -p "$RUN/logs" "$RUN/pids" "$RUN/source_snapshot"
test ! -e "$RUN/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
echo "$$" > "$RUN/pids/driver.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/PIPELINE_FAILED"' ERR

if [[ ! -s "$RUN/dataset_50.jsonl" ]]; then
  "$PY" "$TOOLS/build_ocr_crop_factorial_smoke_v1.py" \
    --source "$REFERENCE/dataset_100.jsonl" --output "$RUN/dataset_50.jsonl" \
    --n 50 --exclude-dataset "$FIRST_HALF"
fi

cp "$TOOLS/infer_ocr_crop_factorial_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/precompute_extra_view_ocr_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/audit_crop_rerunocr_confirm50_v1.py" "$RUN/source_snapshot/"
cp "$ROOT/evaluation/scripts/run_crop_rerunocr_confirm50b_v1.sh" "$RUN/source_snapshot/"

"$PY" "$TOOLS/precompute_extra_view_ocr_v1.py" \
  --dataset "$RUN/dataset_50.jsonl" --plan-root "$REFERENCE/crop_on" \
  --visual-mode crop --output "$RUN/ocr_cache_crop.jsonl" --workers 4 \
  > "$RUN/logs/ocr_crop.log" 2>&1 &
echo "$!" > "$RUN/pids/ocr_crop.pid"
"$PY" "$TOOLS/precompute_extra_view_ocr_v1.py" \
  --dataset "$RUN/dataset_50.jsonl" --plan-root "$REFERENCE/full_on" \
  --visual-mode full --output "$RUN/ocr_cache_full.jsonl" --workers 4 \
  > "$RUN/logs/ocr_full.log" 2>&1 &
echo "$!" > "$RUN/pids/ocr_full.pid"
wait

run_arm() {
  local gpu="$1" arm="$2" visual="$3" cache="$4"
  "$PY" "$TOOLS/infer_ocr_crop_factorial_v1.py" \
    --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$RUN/dataset_50.jsonl" \
    --output-dir "$RUN/$arm" --visual-mode "$visual" --ocr-mode rerun \
    --ocr-cache "$cache" --crop-size 896 --crop-side 0.35 \
    --max-visual-tokens 4160 --expected-items 50 --resume-existing
}

run_arm 1 crop_rerunocr crop "$RUN/ocr_cache_crop.jsonl" > "$RUN/logs/crop_rerunocr.log" 2>&1 &
echo "$!" > "$RUN/pids/crop_rerunocr.pid"
run_arm 2 full_rerunocr full "$RUN/ocr_cache_full.jsonl" > "$RUN/logs/full_rerunocr.log" 2>&1 &
echo "$!" > "$RUN/pids/full_rerunocr.pid"
wait

"$PY" "$TOOLS/audit_crop_rerunocr_confirm50_v1.py" \
  --run-root "$RUN" --dataset "$RUN/dataset_50.jsonl" \
  --reference-root "$REFERENCE" --expected 50 > "$RUN/logs/audit.log" 2>&1
(
  cd "$RUN"
  find source_snapshot dataset_50.jsonl dataset_audit.json ocr_cache_*.jsonl ocr_cache_*.audit.json protocol_audit.json -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
