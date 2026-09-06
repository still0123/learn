#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
OLD_RUN_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1"
RUN_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_modality_active_avcrop_groupcv_v1"
GATE="${RUN_ROOT}/gate_manifest/modality_active_gate_oof_v1.jsonl"
RUNNER="${PROJECT_ROOT}/evaluation/tools/run_qwen25_modality_active_groupcv_v1.py"

cd "${PROJECT_ROOT}"

for fold in 0 1 2 3 4; do
  "${PYTHON}" "${RUNNER}" \
    --gpu-id 4 \
    --fold "${fold}" \
    --method D_CLIPCrop40 \
    --question-file "${OLD_RUN_ROOT}/groupcv5/fold_${fold}/validation_questions_v1.json" \
    --gate-manifest "${GATE}" \
    --output-dir "${RUN_ROOT}/formal/D_CLIPCrop40/fold_${fold}"

  "${PYTHON}" "${RUNNER}" \
    --gpu-id 4 \
    --fold "${fold}" \
    --method E_ModalityActiveAVCrop40 \
    --question-file "${RUN_ROOT}/formal/subsets/fold_${fold}/active_questions_v1.json" \
    --gate-manifest "${GATE}" \
    --output-dir "${RUN_ROOT}/formal/E_ModalityActiveAVCrop40_active_only/fold_${fold}"
done

"${PYTHON}" evaluation/tools/audit_qwen25_modality_active_outputs_v1.py \
  --clip-root "${RUN_ROOT}/formal/D_CLIPCrop40" \
  --av-root "${RUN_ROOT}/formal/E_ModalityActiveAVCrop40_active_only" \
  --gate-manifest "${GATE}" \
  --expected-count 500 \
  --output "${RUN_ROOT}/formal/protocol_audit_v1.json"

date -Is > "${RUN_ROOT}/formal/FORMAL_INFERENCE_COMPLETE"
