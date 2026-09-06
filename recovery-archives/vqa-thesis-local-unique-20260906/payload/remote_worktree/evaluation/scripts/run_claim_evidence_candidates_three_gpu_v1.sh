#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
WORKER="$PROJECT_ROOT/evaluation/scripts/run_claim_evidence_candidates_worker_v1.sh"
METHOD="${METHOD:?set METHOD to raw_uniform or innovation1_mmr32}"
QUESTION_FILE="${QUESTION_FILE:?set QUESTION_FILE}"
GROUNDTRUTH_FILE="${GROUNDTRUTH_FILE:?set GROUNDTRUTH_FILE}"
RUN_ROOT="${RUN_ROOT:?set RUN_ROOT}"
END_IDX="${END_IDX:?set END_IDX}"
OVERWRITE="${OVERWRITE:-0}"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"
TEMPORAL_CACHE="${TEMPORAL_CACHE:-}"
GPUS=(2 3 4)

for gpu in "${GPUS[@]}"; do
  pids="$(nvidia-smi --id="$gpu" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null | sed '/^[[:space:]]*$/d' || true)"
  used="$(nvidia-smi --id="$gpu" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
  if [[ -n "$pids" ]] || (( used > FREE_MAX_MIB )); then
    echo "GPU $gpu is not truly idle: memory=${used}MiB compute_pids=${pids:-none}" >&2
    exit 3
  fi
done

launcher_dir="$RUN_ROOT/$METHOD/launcher_logs"
mkdir -p "$launcher_dir" "$RUN_ROOT/source_snapshot"
cp "$0" "$WORKER" "$RUN_ROOT/source_snapshot/"
pids=()
for shard in 0 1 2; do
  gpu="${GPUS[$shard]}"
  log="$launcher_dir/gpu${gpu}_shard${shard}of3.log"
  env GPU_ID="$gpu" METHOD="$METHOD" QUESTION_FILE="$QUESTION_FILE" \
    GROUNDTRUTH_FILE="$GROUNDTRUTH_FILE" RUN_ROOT="$RUN_ROOT" END_IDX="$END_IDX" \
    SHARD_ID="$shard" NUM_SHARDS=3 OVERWRITE="$OVERWRITE" FREE_MAX_MIB="$FREE_MAX_MIB" \
    TEMPORAL_CACHE="$TEMPORAL_CACHE" bash "$WORKER" >"$log" 2>&1 &
  pids+=("$!")
  echo "started gpu=$gpu shard=$shard pid=${pids[-1]} log=$log"
done
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup INT TERM
status=0
for pid in "${pids[@]}"; do if ! wait "$pid"; then status=1; fi; done
trap - INT TERM
exit "$status"
