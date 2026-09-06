#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
SOURCE="$ROOT/evaluation/runs/scheme_b_multicenter600_v1/dataset_600.jsonl"
RUN="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/smoke20_v2"
TOOLS="$ROOT/evaluation/tools"

mkdir -p "$RUN/logs" "$RUN/pids" "$RUN/source_snapshot"
test ! -e "$RUN/SMOKE_INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
echo "$$" > "$RUN/pids/driver.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/SMOKE_PIPELINE_FAILED"' ERR

if [[ ! -s "$RUN/dataset_20.jsonl" ]]; then
  "$PY" "$TOOLS/build_ocr_crop_factorial_smoke_v1.py" \
    --source "$SOURCE" \
    --output "$RUN/dataset_20.jsonl" \
    --n 20 \
    --exclude-video-id 603f96f94cbcf891d8db244c11555214 \
    --exclude-video-id 611e166ba44c2a31cbf29f62b5986dcc
fi

cp "$TOOLS/infer_ocr_crop_factorial_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/build_ocr_crop_factorial_smoke_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/audit_ocr_crop_factorial_v1.py" "$RUN/source_snapshot/"
cp "$ROOT/evaluation/scripts/run_ocr_crop_factorial_smoke20_v2.sh" "$RUN/source_snapshot/"

run_arm() {
  local gpu="$1" arm="$2" visual="$3" ocr="$4"
  "$PY" "$TOOLS/infer_ocr_crop_factorial_v1.py" \
    --gpu-id "$gpu" \
    --model-dir "$MODEL" \
    --input-jsonl "$RUN/dataset_20.jsonl" \
    --output-dir "$RUN/$arm" \
    --visual-mode "$visual" \
    --ocr-mode "$ocr" \
    --crop-size 896 \
    --crop-side 0.35 \
    --max-visual-tokens 4160 \
    --expected-items 20 \
    --resume-existing
}

run_arm 0 crop_on crop on > "$RUN/logs/crop_on.log" 2>&1 &
echo "$!" > "$RUN/pids/crop_on.pid"
run_arm 1 crop_off crop off > "$RUN/logs/crop_off.log" 2>&1 &
echo "$!" > "$RUN/pids/crop_off.pid"
run_arm 2 full_on full on > "$RUN/logs/full_on.log" 2>&1 &
echo "$!" > "$RUN/pids/full_on.pid"
run_arm 3 full_off full off > "$RUN/logs/full_off.log" 2>&1 &
echo "$!" > "$RUN/pids/full_off.pid"
wait

"$PY" "$TOOLS/audit_ocr_crop_factorial_v1.py" \
  --run-root "$RUN" \
  --dataset "$RUN/dataset_20.jsonl" \
  --expected 20 > "$RUN/logs/audit.log" 2>&1

(
  cd "$RUN"
  find source_snapshot dataset_20.jsonl dataset_audit.json protocol_audit.json -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/SMOKE_PIPELINE_COMPLETE"
