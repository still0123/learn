#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
SOURCE="${ROOT}/evaluation/runs/qwen3_threshold_full5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_threshold_samebudget_ablation_v1"
ARMS="${RUN}/arms_v1"
INFERENCE="${RUN}/inference_smoke24_v1"
AUDIT="${RUN}/protocol_audit_smoke24_v1"

cd "${ROOT}"
test ! -e "${RUN}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"
cp evaluation/tools/build_threshold_samebudget_ablation_v1.py \
  evaluation/tools/infer_qwen3_samebudget_ablation_v1.py \
  evaluation/tools/audit_threshold_samebudget_ablation_smoke_v1.py \
  evaluation/scripts/run_threshold_samebudget_ablation_smoke_v1.sh \
  "${RUN}/source_snapshot/"

"${PY}" evaluation/tools/build_threshold_samebudget_ablation_v1.py \
  --input-jsonl "${SOURCE}/trigger4905_dataset_v1/items_answer_free.jsonl" \
  --output-root "${ARMS}" \
  --smoke-per-fold 4 \
  > "${RUN}/logs/build_arms.log" 2>&1

variants=(extra_global no_ocr no_asr)
gpus=(0 1 2)
for index in 0 1 2; do
  variant="${variants[$index]}"
  gpu="${gpus[$index]}"
  nohup "${PY}" evaluation/tools/infer_qwen3_samebudget_ablation_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${ARMS}/smoke24/${variant}/items.jsonl" \
    --output-dir "${INFERENCE}/${variant}" \
    --base-size 512 --crop-size 896 --max-visual-tokens 4096 \
    --max-new-tokens 192 --expected-items 24 \
    --a2-method "Qwen3_${variant}_AVEvidenceRewrite12_A2" \
    --ablation-variant "${variant}" --skip-a1 \
    > "${RUN}/logs/${variant}.log" 2>&1 < /dev/null &
  echo "$!" > "${RUN}/pids/${variant}.pid"
done
for index in 0 1 2; do
  variant="${variants[$index]}"
  if ! wait "$(<"${RUN}/pids/${variant}.pid")"; then
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/SMOKE_FAILED"
    exit 1
  fi
done

"${PY}" evaluation/tools/audit_threshold_samebudget_ablation_smoke_v1.py \
  --dataset-root "${ARMS}" \
  --inference-root "${INFERENCE}" \
  --output-dir "${AUDIT}" \
  > "${RUN}/logs/audit_smoke24.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/SMOKE24_PROTOCOL_COMPLETE_AWAITING_FULL"
