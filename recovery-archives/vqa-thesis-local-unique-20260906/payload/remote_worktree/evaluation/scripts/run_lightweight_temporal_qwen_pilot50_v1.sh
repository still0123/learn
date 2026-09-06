#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
GPU_ID="${GPU_ID:?set GPU_ID to 2, 3, or 5}"
SHARD_ID="${SHARD_ID:?set SHARD_ID to 0, 1, or 2}"
NUM_SHARDS="${NUM_SHARDS:-3}"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
OVERWRITE="${OVERWRITE:-0}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/lightweight_temporal_qwen_nested_pilot50_v1"
OUTPUT_DIR="$RUN_ROOT/shards/shard${SHARD_ID}of${NUM_SHARDS}"
CACHE="$PROJECT_ROOT/evaluation/runs/lightweight_temporal_cache_nested_pilot50_v1/cache_shard0.jsonl"

case "$GPU_ID" in
  2|3|5) ;;
  *) echo "GPU_ID must be one of 2, 3, 5" >&2; exit 2 ;;
esac
if (( SHARD_ID < 0 || SHARD_ID >= NUM_SHARDS )); then
  echo "invalid SHARD_ID=$SHARD_ID for NUM_SHARDS=$NUM_SHARDS" >&2
  exit 2
fi
used_mib="$(nvidia-smi --id="$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
if (( used_mib > FREE_MAX_MIB )); then
  echo "GPU $GPU_ID is not free: ${used_mib} MiB used (limit ${FREE_MAX_MIB})" >&2
  exit 3
fi

mkdir -p "$OUTPUT_DIR/source_snapshot"
cp "$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py" "$OUTPUT_DIR/source_snapshot/"
cp "$PROJECT_ROOT/evaluation/methods/temporal_evidence/temporal_cache.py" "$OUTPUT_DIR/source_snapshot/"
cp "$PROJECT_ROOT/evaluation/methods/temporal_evidence/lightweight_selector.py" "$OUTPUT_DIR/source_snapshot/"
cp "$0" "$OUTPUT_DIR/source_snapshot/"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py" \
  --gpu_id "$GPU_ID" \
  --shard_id "$SHARD_ID" \
  --num_shards "$NUM_SHARDS" \
  --start_idx 0 \
  --end_idx 50 \
  --project_root "$PROJECT_ROOT" \
  --model_dir /data1/qky/Model/Qwen3Vl-8B \
  --video_root "$PROJECT_ROOT/data/videos" \
  --question_file "$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json" \
  --groundtruth_file "$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json" \
  --asr_file "$PROJECT_ROOT/evaluation/asr_set.json" \
  --output_dir "$OUTPUT_DIR" \
  --fair_method external_temporal \
  --temporal_index_cache "$CACHE" \
  --oversample_count 64 \
  --visual_view_budget 32 \
  --max_post_merge_visual_tokens 12000 \
  --unified_size 896 \
  --rag_mode none \
  --disable_reflection \
  "${overwrite_args[@]}"
