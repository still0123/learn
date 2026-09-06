#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
POOL="${RUN}/a0_pool_v1"
SCORES="${RUN}/a0_verifier_shards_v1"

cd "${ROOT}"
mkdir -p "${RUN}/logs" "${RUN}/pids"

score_count() {
  local path="${SCORES}/fold_$1/scores.jsonl"
  if [[ -f "${path}" ]]; then
    wc -l < "${path}"
  else
    echo 0
  fi
}

wait_score_count() {
  local fold="$1"
  while [[ "$(score_count "${fold}")" -lt 1064 ]]; do
    sleep 15
  done
  sleep 30
}

run_score() {
  local gpu="$1"
  local fold="$2"
  "${PY}" evaluation/tools/score_answer_claims_qwen3_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${POOL}/shards/fold_${fold}.jsonl" \
    --output-dir "${SCORES}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096
}

echo "$$" > "${RUN}/pids/gpu34_a0_relay_v1.pid"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/GPU34_A0_RELAY_LAUNCHED"

(
  wait_score_count 0
  run_score 3 2 > "${RUN}/logs/gpu3_a0_relay_fold2.log" 2>&1
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/GPU3_A0_FOLD2_RELAY_COMPLETE"
) &
gpu3_relay="$!"

(
  wait_score_count 1
  run_score 4 4 > "${RUN}/logs/gpu4_a0_relay_fold4.log" 2>&1
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/GPU4_A0_FOLD4_RELAY_COMPLETE"
) &
gpu4_relay="$!"

wait "${gpu3_relay}" "${gpu4_relay}"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/GPU34_A0_RELAY_COMPLETE"
