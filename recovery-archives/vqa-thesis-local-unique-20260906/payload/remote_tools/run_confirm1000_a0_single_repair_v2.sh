#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_joint_confirm1000_v1"
QID="611e166ba44c2a31cbf29f62b5986dcc_6"
QUESTION="${RUN}/decode_recovery_v1/shard3_split/after_split/singleton_inputs/0001.json"
REPAIR="${RUN}/a0_single_repair_v2"
TARGET="${RUN}/a0_inference_v1/fold_3/base"
WRONG_TARGET="${TARGET}/${QID}"
WRONG_ARCHIVE="${RUN}/a0_single_repair_v1/incorrect_method_materialized/${QID}"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
PREP="${RUN}/prepared_answer_free_v1"

cd "${ROOT}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
cp evaluation/scripts/run_confirm1000_a0_single_repair_v2.sh "${RUN}/source_snapshot/"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A0_SINGLE_REPAIR_V2_FAILED"' ERR

"${PY}" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["question_id"]==sys.argv[2] and x["method"]=="CleanQwen3_Raw8_A0SingleRepair"' "${WRONG_TARGET}/prediction.json" "${QID}"
test ! -e "${WRONG_ARCHIVE}"
mkdir -p "$(dirname "${WRONG_ARCHIVE}")"
mv "${WRONG_TARGET}" "${WRONG_ARCHIVE}"

"${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_decode_recovery_v1.py \
  --gpu-id 1 \
  --model-dir "${MODEL}" \
  --method CleanQwen3_Raw8 \
  --question-file "${QUESTION}" \
  --asr-file "${PREP}/asr_combined_answer_free.json" \
  --video-root data/videos \
  --frames-fallback-root data/frames_8 \
  --output-dir "${REPAIR}" \
  --views 8 \
  --unified-size 512 \
  --max-visual-tokens 4096 \
  --max-new-tokens 256 \
  > "${RUN}/logs/a0_single_repair_v2.log" 2>&1

"${PY}" evaluation/tools/materialize_a0_single_repair_v1.py \
  --question-file "${QUESTION}" \
  --repair-root "${REPAIR}" \
  --target-root "${TARGET}" \
  --expected-question-id "${QID}" \
  --audit "${REPAIR}/materialization_audit.json" \
  > "${RUN}/logs/materialize_a0_single_repair_v2.log" 2>&1

"${PY}" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["question_id"]==sys.argv[2] and x["method"]=="CleanQwen3_Raw8"' "${TARGET}/${QID}/prediction.json" "${QID}"
test "$(find "${TARGET}" -mindepth 2 -maxdepth 2 -type f -name prediction.json | wc -l)" -eq 200
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A0_SINGLE_REPAIR_V2_COMPLETE"

exec env RESUME_AFTER_A0_REPAIR=1 bash evaluation/scripts/run_qwen3_joint_confirm1000_v1.sh
