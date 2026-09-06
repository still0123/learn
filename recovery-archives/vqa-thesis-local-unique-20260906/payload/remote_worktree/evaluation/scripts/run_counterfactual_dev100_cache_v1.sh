#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
GPU_ID="${GPU_ID:?set GPU_ID to an allowed empty GPU}"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_counterfactual_dev100_v1"
DATA_DIR="$PROJECT_ROOT/data/counterfactual_dev100_v1"
OUT_DIR="$RUN_ROOT/innovation1_mmr32_cache"
OUT_JSONL="$OUT_DIR/cache_shard0.jsonl"

case "$GPU_ID" in 2|3|4|5) ;; *) echo "GPU_ID must be 2, 3, 4, or 5" >&2; exit 2 ;; esac
used_mib="$(nvidia-smi --id="$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
if (( used_mib > FREE_MAX_MIB )); then
  echo "GPU $GPU_ID is not free: ${used_mib} MiB used (limit ${FREE_MAX_MIB})" >&2
  exit 3
fi
if [[ ! -s "$DATA_DIR/manifest.json" ]]; then
  echo "missing dev100 manifest" >&2
  exit 4
fi
mkdir -p "$OUT_DIR"
cp "$0" "$PROJECT_ROOT/evaluation/methods/temporal_evidence/build_lightweight_temporal_cache_v1.py" \
  "$PROJECT_ROOT/evaluation/methods/temporal_evidence/lightweight_selector.py" "$OUT_DIR/"

exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/temporal_evidence/build_lightweight_temporal_cache_v1.py" \
  --device cuda --gpu_id "$GPU_ID" --candidate_count 64 --top_k 32 --coverage_bins 8 \
  --question_weight 0.55 --asr_weight 0.20 --scene_change_weight 0.15 --coverage_bonus 0.10 --duplicate_penalty 0.20 \
  --selection_policy mmr32 --question_file "$DATA_DIR/question.json" \
  --asr_file "$PROJECT_ROOT/evaluation/asr_set.json" --video_root "$PROJECT_ROOT/data/videos" \
  --clip_path "$PROJECT_ROOT/models/clip-vit-large-patch14" --output_jsonl "$OUT_JSONL"
