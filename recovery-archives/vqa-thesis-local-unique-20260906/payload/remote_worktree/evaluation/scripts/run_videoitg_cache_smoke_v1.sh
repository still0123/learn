#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
VIDEOITG_SOURCE="$PROJECT_ROOT/external/VideoITG_official_main"
VIDEOITG_DEPS="$PROJECT_ROOT/external/videoitg_pydeps"
MODEL_PATH="/data1/rmx/projectb/models/VideoITG-8B"
VISION_TOWER_PATH="/data1/rmx/projectb/models/siglip-so400m-patch14-384"
QUESTION_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json"
OUTPUT_DIR="$PROJECT_ROOT/evaluation/runs/videoitg_cache_smoke_v1"

export PYTHONPATH="$VIDEOITG_DEPS:$VIDEOITG_SOURCE:$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export HF_ENDPOINT="https://hf-mirror.com"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_DEVICE_ORDER="PCI_BUS_ID"

GPU_ID="${GPU_ID:-2}"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
case "$GPU_ID" in
  2|3|5) ;;
  *) echo "GPU_ID must be one of 2, 3, 5" >&2; exit 2 ;;
esac
used_mib="$(nvidia-smi --id="$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
if (( used_mib > FREE_MAX_MIB )); then
  echo "GPU $GPU_ID is not free: ${used_mib} MiB used (limit ${FREE_MAX_MIB})" >&2
  exit 3
fi

mkdir -p "$OUTPUT_DIR"
overwrite_args=()
if [[ "${OVERWRITE:-0}" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi
"$PYTHON" "$PROJECT_ROOT/evaluation/methods/temporal_evidence/build_videoitg_cache_v1.py" \
  --gpu_id "$GPU_ID" \
  --shard_id 0 \
  --num_shards 1 \
  --start_idx 0 \
  --end_idx "${END_IDX:-1}" \
  --candidate_count 64 \
  --top_k 32 \
  --question_file "$QUESTION_FILE" \
  --video_root "$PROJECT_ROOT/data/videos" \
  --model_path "$MODEL_PATH" \
  --vision_tower_path "$VISION_TOWER_PATH" \
  --videoitg_source "$VIDEOITG_SOURCE" \
  --output_jsonl "$OUTPUT_DIR/cache_shard0.jsonl" \
  "${overwrite_args[@]}"
