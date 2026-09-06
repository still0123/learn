#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
MMR_PID_FILE="${RUN}/pids/early_mmr_full_fold_3.pid"
MMR_OUTPUT="${RUN}/mmr8_full5320_v1/fold_3"
UNIFORM_OUTPUT="${RUN}/uniform8_full5320_v1/fold_2/base"

cd "${ROOT}"
mkdir -p "${RUN}/mmr8_full5320_v1/audits" "${RUN}/logs" "${RUN}/pids"
mmr_pid="$(cat "${MMR_PID_FILE}")"
while kill -0 "${mmr_pid}" 2>/dev/null; do
  sleep 5
done

mmr_count="$(find "${MMR_OUTPUT}" -name prediction.json | wc -l | tr -d ' ')"
if [[ "${mmr_count}" -ne 1064 ]]; then
  echo "MMR Fold 3 stopped at ${mmr_count}/1064; refusing GPU5 handoff" >&2
  exit 1
fi

"${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
  --questions "${DATA}/shards/fold_3.json" \
  --selection-manifest "${RUN}/selected8_manifest_v1/mmr8.jsonl" \
  --inference-dir "${MMR_OUTPUT}" \
  --output "${RUN}/mmr8_full5320_v1/audits/fold_3.json" \
  --expected-count 1064
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/EARLY_MMR_FOLD3_COMPLETE"

while [[ -n "$(nvidia-smi --id=5 --query-compute-apps=pid \
  --format=csv,noheader,nounits)" ]]; do
  sleep 1
done

echo "$$" > "${RUN}/pids/early_uniform_full_fold2_gpu5.pid"
exec "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_full_decode_recovery_v1.py \
  --gpu-id 5 \
  --model-dir "${MODEL}" \
  --method CleanQwen3_Raw8 \
  --question-file "${DATA}/shards/fold_2.json" \
  --asr-file "${DATA}/asr_combined_answer_free.json" \
  --video-root data/videos \
  --frames-fallback-root data/frames_8 \
  --output-dir "${UNIFORM_OUTPUT}" \
  --views 8 \
  --unified-size 512 \
  --max-visual-tokens 4096 \
  --max-new-tokens 256
