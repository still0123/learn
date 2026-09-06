#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_temporal_diverse_local8_groupcv500_v1"
MANIFEST_ROOT="${RUN_ROOT}/manifest"
RAW_FEATURES="${MANIFEST_ROOT}/raw_features_oof_v1.jsonl"
BASE_GATE="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_modality_active_avcrop_groupcv_v1/gate_manifest/modality_active_gate_oof_v1.jsonl"
DIVERSE_GATE="${MANIFEST_ROOT}/diverse_local8_gate_oof_v1.jsonl"
QUESTION_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1/groupcv5"
OLD_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_shared32_isolation_groupcv500_v1"
RUNNER="${PROJECT_ROOT}/evaluation/tools/run_qwen25_shared32_diverse_v1.py"
AUDITOR="${PROJECT_ROOT}/evaluation/tools/audit_qwen25_shared32_diverse_v1.py"
LOG_ROOT="${RUN_ROOT}/orchestrator_logs"

mkdir -p "${LOG_ROOT}"
cd "${PROJECT_ROOT}"

while [[ ! -f "${RAW_FEATURES}.audit.json" ]]; do
  if ! pgrep -f 'build_diverse_local8_manifest_v1.py' >/dev/null 2>&1; then
    printf '%s\n' 'candidate manifest builder stopped before producing its audit' >&2
    exit 1
  fi
  sleep 15
done

"${PYTHON}" evaluation/tools/materialize_diverse_local8_manifest_v1.py \
  --base-manifest "${BASE_GATE}" \
  --candidate-manifest "${RAW_FEATURES}" \
  --output "${DIVERSE_GATE}" \
  --overwrite \
  > "${LOG_ROOT}/materialize.log" 2>&1

SMOKE_ROOT="${RUN_ROOT}/smoke20"
mkdir -p "${SMOKE_ROOT}"
if [[ ! -e "${SMOKE_ROOT}/Shared32_Local8" ]]; then
  cp -al "${OLD_ROOT}/smoke20/Shared32_Local8" "${SMOKE_ROOT}/Shared32_Local8"
fi
"${PYTHON}" "${RUNNER}" \
  --gpu-id 1 \
  --fold 0 \
  --method Shared32_DiverseLocal8 \
  --question-file "${QUESTION_ROOT}/fold_0/validation_questions_v1.json" \
  --gate-manifest "${DIVERSE_GATE}" \
  --output-dir "${SMOKE_ROOT}/Shared32_DiverseLocal8" \
  --max-items 20 \
  > "${LOG_ROOT}/smoke_gpu1.log" 2>&1

"${PYTHON}" "${AUDITOR}" \
  --run-root "${SMOKE_ROOT}" \
  --gate-manifest "${DIVERSE_GATE}" \
  --expected-count 20 \
  --folds 0 \
  --output "${SMOKE_ROOT}/protocol_audit_v1.json" \
  > "${LOG_ROOT}/smoke_audit.log" 2>&1

date -Is > "${SMOKE_ROOT}/SMOKE20_COMPLETE"

FORMAL_ROOT="${RUN_ROOT}/formal"
mkdir -p "${FORMAL_ROOT}"
for fold in 0 1 2 3 4; do
  mkdir -p "${FORMAL_ROOT}/fold_${fold}"
  if [[ ! -e "${FORMAL_ROOT}/fold_${fold}/Shared32_Local8" ]]; then
    cp -al "${OLD_ROOT}/formal/Shared32_Local8/fold_${fold}" "${FORMAL_ROOT}/fold_${fold}/Shared32_Local8"
  fi
done

run_folds() {
  local gpu_id="$1"
  local folds="$2"
  IFS=',' read -r -a fold_list <<< "${folds}"
  for fold in "${fold_list[@]}"; do
    "${PYTHON}" "${RUNNER}" \
      --gpu-id "${gpu_id}" \
      --fold "${fold}" \
      --method Shared32_DiverseLocal8 \
      --question-file "${QUESTION_ROOT}/fold_${fold}/validation_questions_v1.json" \
      --gate-manifest "${DIVERSE_GATE}" \
      --output-dir "${FORMAL_ROOT}/fold_${fold}/Shared32_DiverseLocal8"
  done
}

run_folds 1 "0,2,4" > "${LOG_ROOT}/formal_gpu1.log" 2>&1 &
pid1=$!
run_folds 2 "1,3" > "${LOG_ROOT}/formal_gpu2.log" 2>&1 &
pid2=$!
wait "${pid1}"
wait "${pid2}"

"${PYTHON}" "${AUDITOR}" \
  --run-root "${FORMAL_ROOT}" \
  --gate-manifest "${DIVERSE_GATE}" \
  --expected-count 500 \
  --folds 0,1,2,3,4 \
  --output "${FORMAL_ROOT}/protocol_audit_v1.json" \
  > "${LOG_ROOT}/formal_audit.log" 2>&1

date -Is > "${FORMAL_ROOT}/FORMAL_INFERENCE_COMPLETE"
