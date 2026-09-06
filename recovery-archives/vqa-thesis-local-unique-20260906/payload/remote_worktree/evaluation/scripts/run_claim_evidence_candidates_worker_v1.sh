#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
GPU_ID="${GPU_ID:?set GPU_ID to 2, 3, or 4}"
METHOD="${METHOD:?set METHOD to raw_uniform or innovation1_mmr32}"
QUESTION_FILE="${QUESTION_FILE:?set QUESTION_FILE}"
GROUNDTRUTH_FILE="${GROUNDTRUTH_FILE:?set GROUNDTRUTH_FILE}"
RUN_ROOT="${RUN_ROOT:?set RUN_ROOT}"
END_IDX="${END_IDX:?set END_IDX}"
SHARD_ID="${SHARD_ID:-0}"
NUM_SHARDS="${NUM_SHARDS:-1}"
START_IDX="${START_IDX:-0}"
OVERWRITE="${OVERWRITE:-0}"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
TEMPORAL_CACHE="${TEMPORAL_CACHE:-}"

case "$GPU_ID" in 2|3|4) ;; *) echo "GPU_ID must be 2, 3, or 4" >&2; exit 2 ;; esac
case "$METHOD" in raw_uniform|innovation1_mmr32) ;; *) echo "invalid METHOD=$METHOD" >&2; exit 2 ;; esac
[[ -s "$QUESTION_FILE" && -s "$GROUNDTRUTH_FILE" ]] || { echo "missing question/groundtruth input" >&2; exit 3; }
if [[ "$METHOD" == "innovation1_mmr32" && ! -s "$TEMPORAL_CACHE" ]]; then
  echo "innovation1_mmr32 requires a complete TEMPORAL_CACHE" >&2
  exit 4
fi
compute_pids="$(nvidia-smi --id="$GPU_ID" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null | sed '/^[[:space:]]*$/d' || true)"
used_mib="$(nvidia-smi --id="$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
if [[ -n "$compute_pids" ]] || (( used_mib > FREE_MAX_MIB )); then
  echo "GPU $GPU_ID is not truly idle: memory=${used_mib}MiB compute_pids=${compute_pids:-none}" >&2
  exit 5
fi

OUT_DIR="$RUN_ROOT/$METHOD/shard${SHARD_ID}of${NUM_SHARDS}"
mkdir -p "$OUT_DIR/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/methods/counterfactual_sufficiency/inference_counterfactual_sufficiency_v1.py" \
  "$PROJECT_ROOT/evaluation/methods/counterfactual_sufficiency/counterfactual.py" \
  "$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py" \
  "$OUT_DIR/source_snapshot/"
overwrite_args=(); if [[ "$OVERWRITE" == "1" ]]; then overwrite_args+=(--overwrite); fi
cache_args=(); if [[ "$METHOD" == "innovation1_mmr32" ]]; then cache_args+=(--temporal_index_cache "$TEMPORAL_CACHE"); fi

exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/counterfactual_sufficiency/inference_counterfactual_sufficiency_v1.py" \
  --gpu_id "$GPU_ID" --shard_id "$SHARD_ID" --num_shards "$NUM_SHARDS" \
  --start_idx "$START_IDX" --end_idx "$END_IDX" \
  --project_root "$PROJECT_ROOT" --model_dir /data1/qky/Model/Qwen3Vl-8B \
  --clip_path "$PROJECT_ROOT/models/clip-vit-large-patch14" \
  --video_root "$PROJECT_ROOT/data/videos" \
  --question_file "$QUESTION_FILE" --groundtruth_file "$GROUNDTRUTH_FILE" \
  --asr_file "$PROJECT_ROOT/evaluation/asr_set.json" --evidence_method "$METHOD" \
  --output_dir "$OUT_DIR" --visual_view_budget 32 --max_post_merge_visual_tokens 12000 \
  --unified_size 896 --destroy_count 4 --local_count 8 \
  --support_threshold -6.00 --sensitivity_margin 0.02 --switch_margin 0.05 \
  --force_rescue_all "${cache_args[@]}" "${overwrite_args[@]}"
