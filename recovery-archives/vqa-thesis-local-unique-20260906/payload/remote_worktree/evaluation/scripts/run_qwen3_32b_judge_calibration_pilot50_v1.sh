#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL_PATH="/data1/rmx/projectb/models/Qwen3-32B-AWQ"
MODEL_REVISION="0499c3ac83fdef8810b907a23894ba91e95eddd8"
MODEL_CHECKSUM_FILE="$PROJECT_ROOT/evaluation/configs/qwen3_32b_awq_revision_0499.sha256"
RUN_ID="${1:-20260711_v1}"
BASE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_${RUN_ID}"
FRAME_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_framebalanced_pilot50_${RUN_ID}"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
OUTPUT="$FRAME_ROOT/judge_local_qwen3_32b_awq_answer_only_calibration_v1"
SOURCE_SNAPSHOT="$OUTPUT/source_snapshot"
SERVER_LOG="$OUTPUT/server.log"
PORT="${QWEN_JUDGE_PORT:-18001}"
MODEL_NAME="qwen3-32b-awq-judge"

mkdir -p "$OUTPUT" "$SOURCE_SNAPSHOT"
cp \
  "$0" \
  "$ADAPTER" \
  "$EVALUATOR" \
  "$PROJECT_ROOT/evaluation/scripts/verify_qwen3_32b_awq_model.sh" \
  "$MODEL_CHECKSUM_FILE" \
  "$SOURCE_SNAPSHOT/"

"$PROJECT_ROOT/evaluation/scripts/verify_qwen3_32b_awq_model.sh" "$MODEL_PATH"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

CUDA_VISIBLE_DEVICES=2 "$PYTHON" -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --served-model-name "$MODEL_NAME" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype auto \
  --quantization awq_marlin \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.75 \
  --enforce-eager \
  >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 180); do
  if curl --fail --silent --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    tail -n 100 "$SERVER_LOG"
    exit 1
  fi
  sleep 2
done
curl --fail --silent --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null

export DEEPSEEK_API_KEY="EMPTY_LOCAL_VLLM"
export DEEPSEEK_BASE_URL="http://127.0.0.1:$PORT/v1"
export DEEPSEEK_MODEL="$MODEL_NAME"
export JUDGE_DISABLE_THINKING=1

"$PYTHON" "$ADAPTER" \
  --run adslot_fixed "$BASE_ROOT/adslot_fixed" \
  --run av_v1_framecap1 "$FRAME_ROOT/av_v1_framecap1" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$OUTPUT" \
  --candidate-mode answer_only \
  --max-workers 5 \
  --bootstrap-samples 5000 \
  --overwrite

cat >"$OUTPUT/server_config.json" <<JSON
{
  "model_path": "$MODEL_PATH",
  "model_revision": "$MODEL_REVISION",
  "model_checksum_file": "$MODEL_CHECKSUM_FILE",
  "served_model_name": "$MODEL_NAME",
  "gpu": 2,
  "gpu_memory_utilization": 0.75,
  "max_model_len": 4096,
  "quantization": "awq_marlin",
  "enforce_eager": true,
  "thinking_enabled": false
}
JSON

echo "qwen3_32b_judge_calibration=complete"
