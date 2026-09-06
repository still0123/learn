#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
FOLD0_PID_FILE="${RUN}/pids/early_uniform_full_fold0_gpu0.pid"
FOLD0_OUTPUT="${RUN}/uniform8_full5320_v1/fold_0"
FOLD1_OUTPUT="${RUN}/uniform8_full5320_v1/fold_1/base"

cd "${ROOT}"
mkdir -p "${RUN}/uniform8_full5320_v1/audits" "${RUN}/logs" "${RUN}/pids"
fold0_pid="$(cat "${FOLD0_PID_FILE}")"
while kill -0 "${fold0_pid}" 2>/dev/null; do
  sleep 5
done

fold0_count="$(find "${FOLD0_OUTPUT}" -name prediction.json | wc -l | tr -d ' ')"
if [[ "${fold0_count}" -ne 1064 ]]; then
  echo "Uniform Fold 0 stopped at ${fold0_count}/1064; refusing handoff" >&2
  exit 1
fi

"${PY}" evaluation/tools/audit_adsqa_uniform8_full_v1.py \
  --questions "${DATA}/shards/fold_0.json" \
  --inference-root "${RUN}/uniform8_full5320_v1" \
  --output "${RUN}/uniform8_full5320_v1/audits/fold_0.json" \
  --expected-count 1064
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/EARLY_UNIFORM_FOLD0_COMPLETE"

while [[ -n "$(nvidia-smi --id=0 --query-compute-apps=pid \
  --format=csv,noheader,nounits)" ]]; do
  sleep 1
done

echo "$$" > "${RUN}/pids/early_uniform_full_fold1_gpu0.pid"
exec "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_full_decode_recovery_v1.py \
  --gpu-id 0 \
  --model-dir "${MODEL}" \
  --method CleanQwen3_Raw8 \
  --question-file "${DATA}/shards/fold_1.json" \
  --asr-file "${DATA}/asr_combined_answer_free.json" \
  --video-root data/videos \
  --frames-fallback-root data/frames_8 \
  --output-dir "${FOLD1_OUTPUT}" \
  --views 8 \
  --unified-size 512 \
  --max-visual-tokens 4096 \
  --max-new-tokens 256
