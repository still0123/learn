#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_uncertainty_gated_local8_groupcv500_v1"
MANIFEST="${RUN_ROOT}/manifest/uncertainty_gated_local8_oof_v1.jsonl"
QUESTION_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1/groupcv5"
OLD_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_shared32_isolation_groupcv500_v1"
RUNNER="${PROJECT_ROOT}/evaluation/tools/run_qwen25_shared32_uncertainty_gated_v1.py"
AUDITOR="${PROJECT_ROOT}/evaluation/tools/audit_qwen25_shared32_uncertainty_gated_v1.py"
SMOKE_ROOT="${RUN_ROOT}/smoke20"
FORMAL_ROOT="${RUN_ROOT}/formal"
LOG_ROOT="${RUN_ROOT}/logs"

cd "${PROJECT_ROOT}"
mkdir -p "${LOG_ROOT}"

while true; do
  if [[ -f "${SMOKE_ROOT}/Shared32_UncertaintyGatedLocal8/run_summary.json" ]]; then
    break
  fi
  if ! pgrep -f 'run_qwen25_shared32_uncertainty_gated_v1.py.*Shared32_UncertaintyGatedLocal8.*--max-items 20' >/dev/null 2>&1; then
    printf '%s\n' 'smoke process stopped before run_summary.json' >&2
    exit 1
  fi
  sleep 30
done

"${PYTHON}" "${AUDITOR}" \
  --run-root "${SMOKE_ROOT}" \
  --gate-manifest "${MANIFEST}" \
  --expected-count 20 \
  --folds 0 \
  --output "${SMOKE_ROOT}/protocol_audit_v1.json" \
  > "${LOG_ROOT}/smoke_audit.log" 2>&1
date -Is > "${SMOKE_ROOT}/SMOKE20_COMPLETE"

mkdir -p "${FORMAL_ROOT}"
for fold in 0 1 2 3 4; do
  mkdir -p "${FORMAL_ROOT}/fold_${fold}"
  if [[ ! -e "${FORMAL_ROOT}/fold_${fold}/Shared32_Local8" ]]; then
    cp -al "${OLD_ROOT}/formal/Shared32_Local8/fold_${fold}" "${FORMAL_ROOT}/fold_${fold}/Shared32_Local8"
  fi
done

wait_gpu_idle() {
  local gpu_id="$1"
  while true; do
    if [[ -z "$(nvidia-smi --id="${gpu_id}" --query-compute-apps=pid --format=csv,noheader,nounits | sed '/^[[:space:]]*$/d')" ]]; then
      return 0
    fi
    sleep 60
  done
}

run_fold() {
  local gpu_id="$1"
  local fold="$2"
  local output_dir="${FORMAL_ROOT}/fold_${fold}/Shared32_UncertaintyGatedLocal8"
  if [[ -f "${output_dir}/run_summary.json" ]]; then
    return 0
  fi
  wait_gpu_idle "${gpu_id}"
  nvidia-smi --id="${gpu_id}" --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits >> "${LOG_ROOT}/formal_gpu${gpu_id}.log"
  "${PYTHON}" "${RUNNER}" \
    --gpu-id "${gpu_id}" \
    --fold "${fold}" \
    --method Shared32_UncertaintyGatedLocal8 \
    --question-file "${QUESTION_ROOT}/fold_${fold}/validation_questions_v1.json" \
    --gate-manifest "${MANIFEST}" \
    --output-dir "${output_dir}" \
    >> "${LOG_ROOT}/formal_gpu${gpu_id}.log" 2>&1
}

run_folds() {
  local gpu_id="$1"
  shift
  for fold in "$@"; do
    run_fold "${gpu_id}" "${fold}"
  done
}

run_folds 1 0 2 4 > "${LOG_ROOT}/formal_gpu1.log" 2>&1 & pid1=$!
run_folds 2 1 3 > "${LOG_ROOT}/formal_gpu2.log" 2>&1 & pid2=$!
wait "${pid1}" "${pid2}"

"${PYTHON}" "${AUDITOR}" \
  --run-root "${FORMAL_ROOT}" \
  --gate-manifest "${MANIFEST}" \
  --expected-count 500 \
  --folds 0,1,2,3,4 \
  --output "${FORMAL_ROOT}/protocol_audit_v1.json" \
  > "${LOG_ROOT}/formal_audit.log" 2>&1
date -Is > "${FORMAL_ROOT}/FORMAL_INFERENCE_COMPLETE"
