#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
SELECTED="${RUN}/selected8_manifest_v1"
SMOKE="${RUN}/mmr8_smoke10_v1"
FULL="${RUN}/mmr8_full5320_v1"
GPUS=(1 2 4 5)

cd "${ROOT}"
mkdir -p "${SMOKE}/audits" "${FULL}/audits" "${RUN}/logs" "${RUN}/pids"

run_fold() {
  local fold="$1"
  local gpu="$2"
  local questions="$3"
  local output="$4"
  local label="$5"
  "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --method CLIPMMR64_8_lambda070 \
    --question-file "${questions}" \
    --selection-manifest "${SELECTED}/mmr8.jsonl" \
    --asr-file "${DATA}/asr_combined_answer_free.json" \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output-dir "${output}" \
    --views 8 \
    --unified-size 512 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256 \
    > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1
}

pids=()
for index in 0 1 2 3; do
  run_fold "${index}" "${GPUS[$index]}" \
    "${DATA}/smoke_shards/fold_${index}.json" \
    "${SMOKE}/fold_${index}" "early_mmr_smoke" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do
  wait "${pid}"
done

run_fold 4 1 "${DATA}/smoke_shards/fold_4.json" \
  "${SMOKE}/fold_4" "early_mmr_smoke"

for fold in 0 1 2 3 4; do
  "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
    --questions "${DATA}/smoke_shards/fold_${fold}.json" \
    --selection-manifest "${SELECTED}/mmr8.jsonl" \
    --inference-dir "${SMOKE}/fold_${fold}" \
    --output "${SMOKE}/audits/fold_${fold}.json" \
    --expected-count 2 \
    > "${RUN}/logs/audit_early_mmr_smoke_fold_${fold}.log" 2>&1
done
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/EARLY_MMR_SMOKE_COMPLETE"

pids=()
for index in 0 1 2 3; do
  run_fold "${index}" "${GPUS[$index]}" \
    "${DATA}/shards/fold_${index}.json" \
    "${FULL}/fold_${index}" "early_mmr_full" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do
  wait "${pid}"
done

for fold in 0 1 2 3; do
  "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
    --questions "${DATA}/shards/fold_${fold}.json" \
    --selection-manifest "${SELECTED}/mmr8.jsonl" \
    --inference-dir "${FULL}/fold_${fold}" \
    --output "${FULL}/audits/fold_${fold}.json" \
    --expected-count 1064 \
    > "${RUN}/logs/audit_early_mmr_full_fold_${fold}.log" 2>&1
done
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/EARLY_MMR_FOLDS_0_3_COMPLETE"
