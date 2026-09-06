#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/venvs/adsqa_asr_v1/bin/python"
MODEL="/data1/rmx/models/Whisper-large-v3-turbo-modelscope/large-v3-turbo.pt"
RUN="${ROOT}/evaluation/runs/qwen3_joint_confirm1000_v1/asr_supplement_v1"
QUESTIONS="${ROOT}/data/qwen3_joint_confirm1000_v1/questions_answer_free.json"
EXISTING="${ROOT}/data/segmented_asr_pilot_train_confirm_v1/records"
SELECTION="${RUN}/selection/missing_videos_answer_free.json"
SMOKE_SELECTION="${RUN}/selection/smoke_videos_answer_free.json"
RECORDS="${RUN}/records"
GPU_ID="${GPU_ID:-1}"
MODE="${MODE:-smoke}"

test -x "${PYTHON}"
test -f "${MODEL}"
test -f "${QUESTIONS}"
test -f "${SELECTION}"
test -f "${SMOKE_SELECTION}"
mkdir -p "${RECORDS}" "${RUN}/logs" "${RUN}/audit"
cd "${ROOT}"

if [[ "${MODE}" == "smoke" ]]; then
  "${PYTHON}" preprocess/build_segmented_asr_cache_v1.py \
    --index_dir data/video_index_v1 \
    --selection_files "${SMOKE_SELECTION}" \
    --model_path "${MODEL}" \
    --output_dir "${RECORDS}" \
    --gpu_id "${GPU_ID}" \
    2>&1 | tee "${RUN}/logs/smoke_build.log"
  "${PYTHON}" preprocess/audit_segmented_asr_cache_v1.py \
    --index_dir data/video_index_v1 \
    --selection_files "${SMOKE_SELECTION}" \
    --asr_dir "${RECORDS}" \
    --output_json "${RUN}/audit/smoke_audit.json" \
    2>&1 | tee "${RUN}/logs/smoke_audit.log"
  touch "${RUN}/SMOKE_COMPLETE"
elif [[ "${MODE}" == "full" ]]; then
  test -f "${RUN}/SMOKE_COMPLETE"
  "${PYTHON}" preprocess/build_segmented_asr_cache_v1.py \
    --index_dir data/video_index_v1 \
    --selection_files "${SELECTION}" \
    --model_path "${MODEL}" \
    --output_dir "${RECORDS}" \
    --gpu_id "${GPU_ID}" \
    2>&1 | tee "${RUN}/logs/full_build.log"
  "${PYTHON}" preprocess/audit_segmented_asr_cache_v1.py \
    --index_dir data/video_index_v1 \
    --selection_files "${SELECTION}" \
    --asr_dir "${RECORDS}" \
    --output_json "${RUN}/audit/supplement_audit.json" \
    2>&1 | tee "${RUN}/logs/supplement_audit.log"
  "${PYTHON}" evaluation/tools/audit_confirm1000_asr_union_v1.py \
    --questions "${QUESTIONS}" \
    --index-dir data/video_index_v1 \
    --asr-dir "${EXISTING}" \
    --asr-dir "${RECORDS}" \
    --output-json "${RUN}/audit/union_audit.json" \
    2>&1 | tee "${RUN}/logs/union_audit.log"
  touch "${RUN}/COMPLETE"
else
  echo "MODE must be smoke or full, got: ${MODE}" >&2
  exit 2
fi
