#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
SOURCE="${ROOT}/evaluation/runs/qwen3_threshold_full5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_threshold_samebudget_ablation_full_v1"
ARMS="${RUN}/arms_v1"
INFERENCE="${RUN}/inference_full4905_v1"
AUDIT="${RUN}/protocol_audit_full4905_v1"

cd "${ROOT}"
test ! -e "${RUN}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"
cp evaluation/tools/build_threshold_samebudget_ablation_full_v1.py \
  evaluation/tools/infer_qwen3_samebudget_ablation_v1.py \
  evaluation/tools/audit_threshold_samebudget_ablation_full_v1.py \
  evaluation/scripts/run_threshold_samebudget_ablation_full_v1.sh \
  "${RUN}/source_snapshot/"

"${PY}" evaluation/tools/build_threshold_samebudget_ablation_full_v1.py \
  --input-jsonl "${SOURCE}/trigger4905_dataset_v1/items_answer_free.jsonl" \
  --output-root "${ARMS}" \
  > "${RUN}/logs/build_arms.log" 2>&1

variants=(extra_global no_ocr no_asr)
for variant in "${variants[@]}"; do
  wave_pids=()
  for fold in 0 1 2 3 4 5; do
    expected=818
    if [ "${fold}" -ge 3 ]; then expected=817; fi
    log="${RUN}/logs/${variant}_fold${fold}.log"
    pidfile="${RUN}/pids/${variant}_fold${fold}.pid"
    nohup "${PY}" evaluation/tools/infer_qwen3_samebudget_ablation_v1.py \
      --gpu-id "${fold}" --model-dir "${MODEL}" \
      --input-jsonl "${ARMS}/full4905/${variant}/shards/fold_${fold}.jsonl" \
      --output-dir "${INFERENCE}/${variant}/fold_${fold}" \
      --base-size 512 --crop-size 896 --max-visual-tokens 4096 \
      --max-new-tokens 192 --expected-items "${expected}" \
      --a2-method "Qwen3_${variant}_AVEvidenceRewrite12_A2" \
      --ablation-variant "${variant}" --skip-a1 \
      > "${log}" 2>&1 < /dev/null &
    pid="$!"
    echo "${pid}" > "${pidfile}"
    wave_pids+=("${pid}")
  done
  for pid in "${wave_pids[@]}"; do
    if ! wait "${pid}"; then
      date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_FAILED_${variant}"
      exit 1
    fi
  done
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/WAVE_${variant}_COMPLETE"
done

"${PY}" evaluation/tools/audit_threshold_samebudget_ablation_full_v1.py \
  --dataset-root "${ARMS}" --inference-root "${INFERENCE}" --output-dir "${AUDIT}" \
  > "${RUN}/logs/audit_full4905.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
