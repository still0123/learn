#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
BASE="${ROOT}/evaluation/runs/innovation2_realclaim_lora_verifier_v1"
ORIGINAL="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1"
INPUTS="${BASE}/realclaim_train_v1/inputs.jsonl"
LABELS="${BASE}/realclaim_train_v1/labels.jsonl"
CAL_INPUTS="${ROOT}/evaluation/runs/innovation2_realclaim300_v2_corrected_frames/inference_inputs.jsonl"
CAL_LABELS="${ROOT}/evaluation/runs/innovation2_realclaim300_v2_corrected_frames/claims.jsonl"
Q25_SCORES="${BASE}/realclaim_weak_full985_calibration240_v1/direct/scores.jsonl"
GPU_ID="${GPU_ID:?GPU_ID is required}"
SEED="${SEED:?SEED is required}"
RUN="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_stability_v1/seed_${SEED}"

if [[ -e "${RUN}/LAUNCHED" ]]; then
  echo "refusing duplicate seed launch: ${RUN}" >&2
  exit 1
fi
active="$(nvidia-smi --id="${GPU_ID}" --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits)"
if [[ -n "${active}" ]]; then
  echo "GPU${GPU_ID} is not idle: ${active}" >&2
  exit 1
fi
mkdir -p "${RUN}/logs" "${RUN}/source_snapshot"
echo "$$" > "${RUN}/controller.pid"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/LAUNCHED"
cd "${ROOT}"

cp evaluation/tools/train_realclaim_weak_lora_qwen3_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/evaluate_realclaim_lora_qwen3_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/audit_qwen3_realclaim_smoke_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/analyze_qwen3_realclaim985_calibration_v1.py "${RUN}/source_snapshot/"
cp evaluation/scripts/run_qwen3_realclaim985_seed_v1.sh "${RUN}/source_snapshot/"
sha256sum \
  "${INPUTS}" "${LABELS}" "${CAL_INPUTS}" "${CAL_LABELS}" "${Q25_SCORES}" \
  "${MODEL}/config.json" "${RUN}"/source_snapshot/* \
  > "${RUN}/SHA256SUMS.before"

"${PY}" evaluation/tools/train_realclaim_weak_lora_qwen3_v1.py \
  --gpu-id "${GPU_ID}" \
  --model-dir "${MODEL}" \
  --inputs "${INPUTS}" \
  --labels "${LABELS}" \
  --output-dir "${RUN}/train" \
  --epochs 1 \
  --views 8 \
  --unified-size 448 \
  --max-visual-tokens 4096 \
  --learning-rate 1e-4 \
  --seed "${SEED}" \
  > "${RUN}/logs/train.log" 2>&1

"${PY}" evaluation/tools/evaluate_realclaim_lora_qwen3_v1.py \
  --gpu-id "${GPU_ID}" \
  --model-dir "${MODEL}" \
  --adapter-dir "${RUN}/train/adapter" \
  --input-jsonl "${CAL_INPUTS}" \
  --claims-jsonl "${CAL_LABELS}" \
  --split calibration \
  --output-dir "${RUN}/lora_calibration240" \
  --views 8 \
  --unified-size 448 \
  --max-visual-tokens 4096 \
  > "${RUN}/logs/lora_calibration240.log" 2>&1

"${PY}" evaluation/tools/audit_qwen3_realclaim_smoke_v1.py \
  --train-dir "${RUN}/train" \
  --base-dir "${ORIGINAL}/base_calibration240" \
  --lora-dir "${RUN}/lora_calibration240" \
  --expected-input-sha256 78789c288138235a7026d916775e74bbb7d05714f5647f19c8ba71d4526d85ac \
  --expected-labels-sha256 58bda82a11b3e4c21a6801e1f977fc1ce45a36ddce422a86634c5f32872444d4 \
  --output "${RUN}/protocol_audit.json" \
  > "${RUN}/logs/audit.log" 2>&1

"${PY}" evaluation/tools/analyze_qwen3_realclaim985_calibration_v1.py \
  --qwen3-base "${ORIGINAL}/base_calibration240/scores.jsonl" \
  --qwen3-lora "${RUN}/lora_calibration240/scores.jsonl" \
  --qwen25-incumbent "${Q25_SCORES}" \
  --calibration-inputs "${CAL_INPUTS}" \
  --output "${RUN}/calibration_analysis.json" \
  --bootstrap 10000 \
  --seed "${SEED}" \
  > "${RUN}/logs/analysis.log" 2>&1

find "${RUN}" -type f ! -name SHA256SUMS.final -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${RUN}/SHA256SUMS.final"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/COMPLETE"
