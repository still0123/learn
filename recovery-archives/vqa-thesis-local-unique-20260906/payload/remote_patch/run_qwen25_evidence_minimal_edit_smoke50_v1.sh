#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct"
RUN="${ROOT}/evaluation/runs/qwen25_evidence_minimal_edit_smoke50_v1"
DATASET="${RUN}/dataset"

mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
if [[ -e "${RUN}/PIPELINE_LAUNCHED" ]]; then
  echo "refusing duplicate minimal-edit Smoke-50 launch" >&2
  exit 1
fi
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"

on_error() {
  local status=$?
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    echo "exit_status=${status}"
    echo "line=${BASH_LINENO[0]:-unknown}"
  } > "${RUN}/PIPELINE_FAILED"
  exit "${status}"
}
trap on_error ERR

cd "${ROOT}"
cp \
  evaluation/tools/build_qwen25_evidence_minimal_edit_smoke50_v1.py \
  evaluation/tools/infer_qwen25_evidence_minimal_edit_v1.py \
  evaluation/tools/audit_qwen25_evidence_minimal_edit_smoke50_v1.py \
  evaluation/scripts/run_qwen25_evidence_minimal_edit_smoke50_v1.sh \
  "${RUN}/source_snapshot/"

for gpu in 1 2 3 4 5; do
  active="$(
    nvidia-smi \
      --id="${gpu}" \
      --query-compute-apps=pid \
      --format=csv,noheader,nounits 2>/dev/null \
      | tr -d '[:space:]'
  )"
  free_memory="$(
    nvidia-smi \
      --id="${gpu}" \
      --query-gpu=memory.free \
      --format=csv,noheader,nounits 2>/dev/null \
      | tr -d '[:space:]'
  )"
  if [[ -n "${active}" || "${free_memory}" -lt 26000 ]]; then
    echo "GPU${gpu} is not safely available" >&2
    exit 1
  fi
done

{
  date -u +"%Y-%m-%dT%H:%M:%SZ"
  nvidia-smi \
    --query-gpu=index,memory.used,memory.free,memory.total,utilization.gpu \
    --format=csv,noheader,nounits
  nvidia-smi \
    --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
    --format=csv,noheader,nounits || true
} > "${RUN}/logs/gpu_before_inference.log"

worker_pids=()
for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  nohup "${PY}" evaluation/tools/infer_qwen25_evidence_minimal_edit_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${DATASET}/shards/fold_${fold}.jsonl" \
    --output-dir "${RUN}/inference/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items 10 \
    --a2-method "CleanQwen25_AdsQA_EvidenceMinimalEdit12_A2" \
    --ablation-variant minimal_edit \
    --skip-a1 \
    > "${RUN}/logs/inference_fold_${fold}.log" 2>&1 &
  pid=$!
  echo "${pid}" > "${RUN}/pids/inference_fold_${fold}.pid"
  worker_pids+=("${pid}")
done
for pid in "${worker_pids[@]}"; do
  wait "${pid}"
done

"${PY}" evaluation/tools/audit_qwen25_evidence_minimal_edit_smoke50_v1.py \
  --dataset-dir "${DATASET}" \
  --inference-root "${RUN}/inference" \
  --output-dir "${RUN}/protocol_audit_v1" \
  > "${RUN}/logs/protocol_audit.log" 2>&1

sha256sum \
  "${DATASET}/audit.json" \
  "${RUN}/protocol_audit_v1/audit.json" \
  "${RUN}/protocol_audit_v1/manifest.jsonl" \
  > "${RUN}/INFERENCE_SHA256SUMS"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/INFERENCE_COMPLETE"
