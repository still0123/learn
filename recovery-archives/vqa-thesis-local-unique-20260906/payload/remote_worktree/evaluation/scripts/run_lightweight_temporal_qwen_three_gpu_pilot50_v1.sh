#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
WORKER="$PROJECT_ROOT/evaluation/scripts/run_lightweight_temporal_qwen_pilot50_v1.sh"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/lightweight_temporal_qwen_nested_pilot50_v1"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
OVERWRITE="${OVERWRITE:-0}"
GPUS=(2 3 5)

for gpu in "${GPUS[@]}"; do
  used_mib="$(nvidia-smi --id="$gpu" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
  if (( used_mib > FREE_MAX_MIB )); then
    echo "GPU $gpu is not free: ${used_mib} MiB used (limit ${FREE_MAX_MIB}); nothing started" >&2
    exit 3
  fi
done

mkdir -p "$RUN_ROOT/launcher_logs" "$RUN_ROOT/source_snapshot"
cp "$0" "$WORKER" "$RUN_ROOT/source_snapshot/"

pids=()
for shard in 0 1 2; do
  gpu="${GPUS[$shard]}"
  log="$RUN_ROOT/launcher_logs/gpu${gpu}_shard${shard}of3.log"
  GPU_ID="$gpu" SHARD_ID="$shard" NUM_SHARDS=3 \
    FREE_MAX_MIB="$FREE_MAX_MIB" OVERWRITE="$OVERWRITE" \
    bash "$WORKER" >"$log" 2>&1 &
  pids+=("$!")
  echo "started gpu=$gpu shard=$shard pid=${pids[-1]} log=$log"
done

cleanup() {
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup INT TERM

status=0
for index in 0 1 2; do
  if ! wait "${pids[$index]}"; then
    echo "worker failed: gpu=${GPUS[$index]} shard=$index" >&2
    status=1
  fi
done
trap - INT TERM

if (( status != 0 )); then
  exit "$status"
fi
echo "lightweight_temporal_qwen_three_gpu=complete"
