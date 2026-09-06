#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_threshold_calibration500_v1"
SOURCE="${ROOT}/evaluation/runs/qwen3_mmr_selectrescue_oof500_v1"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
POOL="${SOURCE}/a0_pool_v1"
SCORES="${SOURCE}/a0_verifier_merged_v1/scores_all.jsonl"
AV_MANIFEST="${ROOT}/evaluation/runs/innovation1_avfunnel8_groupcv500_v1/manifest/av_funnel_oof500_v2.jsonl"
DATASET="${RUN}/dataset_v1"
INFERENCE="${RUN}/a2_inference_v1"
AUDIT="${RUN}/a2_protocol_audit_v1"

if [[ -e "${RUN}/PIPELINE_LAUNCHED" ]]; then
  echo "refusing duplicate threshold-calibration launch" >&2
  exit 1
fi
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"
cd "${ROOT}"

cp evaluation/tools/build_selective_evidence_rewrite_calibration500_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_qwen3_selective_evidence_rewrite_calibration_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/audit_threshold_calibration_a2_v1.py "${RUN}/source_snapshot/"
cp evaluation/scripts/run_qwen3_threshold_calibration500_v1.sh "${RUN}/source_snapshot/"

"${PY}" evaluation/tools/build_selective_evidence_rewrite_calibration500_v1.py \
  --pool-dir "${POOL}" \
  --scores "${SCORES}" \
  --av-manifest "${AV_MANIFEST}" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root data/segmented_asr_pilot_train_confirm_v1/records \
  --output-dir "${DATASET}" \
  > "${RUN}/logs/build_dataset.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/DATASET_COMPLETE"

for fold in 0 1 2 3 4; do
  mkdir -p "${INFERENCE}/fold_${fold}"
  for source_dir in "${SOURCE}/rewrite_inference_v1/fold_${fold}"/*; do
    [[ -d "${source_dir}" ]] || continue
    qid="$(basename "${source_dir}")"
    cp -a "${source_dir}" "${INFERENCE}/fold_${fold}/${qid}"
  done
done

run_fold() {
  local fold="$1"
  local gpu="$2"
  nohup "${PY}" evaluation/tools/infer_qwen3_selective_evidence_rewrite_calibration_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${DATASET}/shards/fold_${fold}.jsonl" \
    --output-dir "${INFERENCE}/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items 100 \
    --a2-only \
    --resume-existing \
    > "${RUN}/logs/a2_fold_${fold}.log" 2>&1
}

worker() {
  local gpu="$1"
  shift
  for fold in "$@"; do
    run_fold "${fold}" "${gpu}"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_FOLD_${fold}_COMPLETE"
  done
}

worker 0 0 3 &
pid0="$!"
echo "${pid0}" > "${RUN}/pids/worker_gpu0.pid"
worker 1 1 4 &
pid1="$!"
echo "${pid1}" > "${RUN}/pids/worker_gpu1.pid"
worker 2 2 &
pid2="$!"
echo "${pid2}" > "${RUN}/pids/worker_gpu2.pid"

status=0
wait "${pid0}" || status=1
wait "${pid1}" || status=1
wait "${pid2}" || status=1
if [[ "${status}" -ne 0 ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_INFERENCE_FAILED"
  exit 1
fi

"${PY}" evaluation/tools/audit_threshold_calibration_a2_v1.py \
  --dataset "${DATASET}/items_answer_free.jsonl" \
  --inference-root "${INFERENCE}" \
  --reused-root "${SOURCE}/rewrite_inference_v1" \
  --output-dir "${AUDIT}" \
  > "${RUN}/logs/audit_a2.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_INFERENCE_COMPLETE_AWAITING_JUDGE_PREFLIGHT"

sha256sum \
  "${DATASET}/audit.json" \
  "${AUDIT}/audit.json" \
  "${AUDIT}/manifest.jsonl" \
  > "${RUN}/INFERENCE_SHA256SUMS"
