#!/usr/bin/env bash
set -euo pipefail

GPU_ID="${1:?GPU id required}"
SHARD_ID="${2:?shard id required}"
PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm3000_shared32_v1"
QUESTION_FILE="$RUN_ROOT/selection/shards/shard_${SHARD_ID}.json"
GATE_MANIFEST="$RUN_ROOT/selection/fixed_local8_manifest.jsonl"
PYTHON_BIN="/data1/rmx/ana3/envs/ReadR/bin/python"
LOG_FILE="$RUN_ROOT/logs/worker_gpu${GPU_ID}_shard${SHARD_ID}.log"
VIDEO_ROOT="${VIDEO_ROOT:-$RUN_ROOT/selection/video_overlay_v1}"
FRAMES_ROOT="${FRAMES_ROOT:-$PROJECT_ROOT/data/frames_8}"

mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/formal"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "worker_start $(date -Is) gpu=$GPU_ID shard=$SHARD_ID"
echo "question_file=$QUESTION_FILE"
echo "gate_manifest=$GATE_MANIFEST"
echo "video_root=$VIDEO_ROOT"
echo "frames_root=$FRAMES_ROOT"

for METHOD in Shared32_ExtraGlobal8 Shared32_Local8; do
    OUTPUT_DIR="$RUN_ROOT/formal/$METHOD/shard_${SHARD_ID}"
    mkdir -p "$OUTPUT_DIR"
    echo "method_start $(date -Is) method=$METHOD"
    "$PYTHON_BIN" "$PROJECT_ROOT/evaluation/tools/run_qwen25_shared32_confirm3000_v1.py" \
        --gpu-id "$GPU_ID" \
        --fold 0 \
        --method "$METHOD" \
        --question-file "$QUESTION_FILE" \
        --gate-manifest "$GATE_MANIFEST" \
        --model-dir /data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct \
        --video-root "$VIDEO_ROOT" \
        --frames-fallback-root "$FRAMES_ROOT" \
        --output-dir "$OUTPUT_DIR"
    echo "method_end $(date -Is) method=$METHOD"
done

date -Is > "$RUN_ROOT/formal/worker_gpu${GPU_ID}_shard${SHARD_ID}.complete"
echo "worker_complete $(date -Is) gpu=$GPU_ID shard=$SHARD_ID"
