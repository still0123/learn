#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="${ROOT}/evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"
RUNNER="${ROOT}/evaluation/tools/run_qwen25_gated_avcrop_groupcv_v1.py"
GATE_MANIFEST="${RUN_ROOT}/gate_manifest/gate_manifest_oof_foldfrozen_v2.jsonl"
GPU_ID="4"

mkdir -p "${RUN_ROOT}/oof_orchestrator"
LOG_FILE="${RUN_ROOT}/oof_orchestrator/launcher.log"
FAILED_FILE="${RUN_ROOT}/oof_orchestrator/FAILED"
COMPLETE_FILE="${RUN_ROOT}/oof_orchestrator/COMPLETE"

rm -f "${FAILED_FILE}" "${COMPLETE_FILE}"

check_gpu_idle() {
  local apps
  apps="$(nvidia-smi --id="${GPU_ID}" --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits)"
  if [[ -n "${apps//[[:space:]]/}" ]]; then
    echo "GPU${GPU_ID} is not idle: ${apps}" >&2
    return 1
  fi
}

trap 'printf "failed_at=%s\n" "$(date -u +%FT%TZ)" > "${FAILED_FILE}"' ERR

{
  echo "started_at=$(date -u +%FT%TZ)"
  echo "python=$(${PYTHON} -c 'import sys; print(sys.executable)')"
  echo "transformers=$(${PYTHON} -c 'import transformers; print(transformers.__version__)')"
  echo "gpu=${GPU_ID}"
  echo "gate_manifest_sha256=$(sha256sum "${GATE_MANIFEST}" | awk '{print $1}')"

  for method in A_Raw32 B_Raw40 C_Gated_RandomCrop8 D_Gated_CLIPCrop8 E_Gated_AVCrop8; do
    for fold in 0 1 2 3 4; do
      check_gpu_idle
      echo "starting method=${method} fold=${fold} at $(date -u +%FT%TZ)"
      args=(
        "${RUNNER}"
        --gpu-id "${GPU_ID}"
        --fold "${fold}"
        --method "${method}"
      )
      if [[ "${method}" == C_Gated_RandomCrop8 || "${method}" == D_Gated_CLIPCrop8 || "${method}" == E_Gated_AVCrop8 ]]; then
        args+=(--gate-manifest "${GATE_MANIFEST}")
      fi
      "${PYTHON}" "${args[@]}"
      echo "completed method=${method} fold=${fold} at $(date -u +%FT%TZ)"
    done
  done

  echo "completed_at=$(date -u +%FT%TZ)"
  touch "${COMPLETE_FILE}"
} >> "${LOG_FILE}" 2>&1
