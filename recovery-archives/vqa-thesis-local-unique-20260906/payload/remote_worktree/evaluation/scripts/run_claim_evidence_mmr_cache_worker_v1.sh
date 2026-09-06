#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
QUESTION_FILE="${QUESTION_FILE:?set QUESTION_FILE}"
RUN_ROOT="${RUN_ROOT:?set RUN_ROOT}"
END_IDX="${END_IDX:?set END_IDX}"
SHARD_ID="${SHARD_ID:-0}"
NUM_SHARDS="${NUM_SHARDS:-1}"
OVERWRITE="${OVERWRITE:-0}"
OUTPUT="$RUN_ROOT/cache_shard${SHARD_ID}of${NUM_SHARDS}.jsonl"

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/methods/temporal_evidence/build_lightweight_temporal_cache_v1.py" \
  "$PROJECT_ROOT/evaluation/methods/temporal_evidence/lightweight_selector.py" \
  "$PROJECT_ROOT/evaluation/methods/temporal_evidence/temporal_cache.py" \
  "$RUN_ROOT/source_snapshot/"
overwrite_args=(); if [[ "$OVERWRITE" == "1" ]]; then overwrite_args+=(--overwrite); fi
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/temporal_evidence/build_lightweight_temporal_cache_v1.py" \
  --device cpu --shard_id "$SHARD_ID" --num_shards "$NUM_SHARDS" --start_idx 0 --end_idx "$END_IDX" \
  --candidate_count 64 --top_k 32 --coverage_bins 8 \
  --question_weight 0.55 --asr_weight 0.20 --scene_change_weight 0.15 \
  --coverage_bonus 0.10 --duplicate_penalty 0.20 \
  --question_file "$QUESTION_FILE" --asr_file "$PROJECT_ROOT/evaluation/asr_set.json" \
  --video_root "$PROJECT_ROOT/data/videos" \
  --clip_path "$PROJECT_ROOT/models/clip-vit-large-patch14" \
  --output_jsonl "$OUTPUT" "${overwrite_args[@]}"
