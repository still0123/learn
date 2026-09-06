#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
SOURCE="$ROOT/evaluation/runs/scheme_b_multicenter600_v1/dataset_600.jsonl"
SMOKE="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/smoke20_v2/dataset_20.jsonl"
RUN="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/confirm100_v1"
TOOLS="$ROOT/evaluation/tools"

mkdir -p "$RUN/logs" "$RUN/pids" "$RUN/source_snapshot"
test ! -e "$RUN/CONFIRM100_INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
echo "$$" > "$RUN/pids/driver.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/CONFIRM100_PIPELINE_FAILED"' ERR

if [[ ! -s "$RUN/dataset_100.jsonl" ]]; then
  "$PY" "$TOOLS/build_ocr_crop_factorial_smoke_v1.py" \
    --source "$SOURCE" \
    --output "$RUN/dataset_100.jsonl" \
    --n 100 \
    --exclude-dataset "$SMOKE" \
    --exclude-video-id 603f96f94cbcf891d8db244c11555214 \
    --exclude-video-id 611e166ba44c2a31cbf29f62b5986dcc
fi

cp "$TOOLS/infer_ocr_crop_factorial_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/build_ocr_crop_factorial_smoke_v1.py" "$RUN/source_snapshot/"
cp "$TOOLS/audit_ocr_crop_factorial_v1.py" "$RUN/source_snapshot/"
cp "$ROOT/evaluation/scripts/run_ocr_crop_factorial_confirm100_v1.sh" "$RUN/source_snapshot/"

cat > "$RUN/preregistration.json" <<'JSON'
{
  "schema_version": "ocr_crop_factorial_confirm100_preregistration_v1",
  "sample_size": 100,
  "video_disjoint_from_smoke20": true,
  "selection": "OCR-relevant, deterministic SHA256 order, one question per video",
  "frozen_arms": ["crop_on", "crop_off", "full_on", "full_off"],
  "base_views": "MMR8 at 512",
  "extra_views": "four views at 896 from two frozen evidence moments",
  "visual_token_limit": 4160,
  "crop_side": 0.35,
  "asr": "on for all arms",
  "secondary_sampling": false,
  "primary_comparison": "crop_on vs full_on",
  "secondary_comparisons": ["crop_off vs full_off", "crop_on vs crop_off", "full_on vs full_off"],
  "interaction": "(crop_on-full_on)-(crop_off-full_off)",
  "labels_read_for_selection": false
}
JSON

run_arm() {
  local gpu="$1" arm="$2" visual="$3" ocr="$4"
  "$PY" "$TOOLS/infer_ocr_crop_factorial_v1.py" \
    --gpu-id "$gpu" \
    --model-dir "$MODEL" \
    --input-jsonl "$RUN/dataset_100.jsonl" \
    --output-dir "$RUN/$arm" \
    --visual-mode "$visual" \
    --ocr-mode "$ocr" \
    --crop-size 896 \
    --crop-side 0.35 \
    --max-visual-tokens 4160 \
    --expected-items 100 \
    --resume-existing
}

run_arm 1 crop_on crop on > "$RUN/logs/crop_on.log" 2>&1 &
echo "$!" > "$RUN/pids/crop_on.pid"
run_arm 2 crop_off crop off > "$RUN/logs/crop_off.log" 2>&1 &
echo "$!" > "$RUN/pids/crop_off.pid"
run_arm 3 full_on full on > "$RUN/logs/full_on.log" 2>&1 &
echo "$!" > "$RUN/pids/full_on.pid"
run_arm 4 full_off full off > "$RUN/logs/full_off.log" 2>&1 &
echo "$!" > "$RUN/pids/full_off.pid"
wait

"$PY" "$TOOLS/audit_ocr_crop_factorial_v1.py" \
  --run-root "$RUN" \
  --dataset "$RUN/dataset_100.jsonl" \
  --expected 100 > "$RUN/logs/audit.log" 2>&1

(
  cd "$RUN"
  find source_snapshot dataset_100.jsonl dataset_audit.json preregistration.json protocol_audit.json -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/CONFIRM100_INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
