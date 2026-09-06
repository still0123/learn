#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
METHOD="${METHOD:?set METHOD to raw_uniform or innovation1_mmr32}"
OVERWRITE="${OVERWRITE:-0}"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_counterfactual_dev100_v1"
GPUS=(2 3 4)

case "$METHOD" in raw_uniform|innovation1_mmr32) ;; *) echo "invalid METHOD=$METHOD" >&2; exit 2 ;; esac
for gpu in "${GPUS[@]}"; do
  used_mib="$(nvidia-smi --id="$gpu" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
  if (( used_mib > FREE_MAX_MIB )); then
    echo "GPU $gpu is not free: ${used_mib} MiB used (limit ${FREE_MAX_MIB})" >&2
    exit 3
  fi
done

launcher_dir="$RUN_ROOT/$METHOD/launcher_logs"
mkdir -p "$launcher_dir"
pids=()
for shard in 0 1 2; do
  gpu="${GPUS[$shard]}"
  log="$launcher_dir/gpu${gpu}_shard${shard}of3.log"
  env GPU_ID="$gpu" METHOD="$METHOD" SHARD_ID="$shard" NUM_SHARDS=3 START_IDX=0 END_IDX=100 \
    OVERWRITE="$OVERWRITE" FREE_MAX_MIB="$FREE_MAX_MIB" \
    bash "$PROJECT_ROOT/evaluation/scripts/run_counterfactual_sufficiency_worker_v1.sh" >"$log" 2>&1 &
  pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    status=1
  fi
done
exit "$status"
