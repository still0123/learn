#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
SOURCE="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
CALIBRATION="${ROOT}/evaluation/runs/qwen3_threshold_calibration500_v1"
RUN="${ROOT}/evaluation/runs/qwen3_threshold_full5320_v1"
DATASET="${RUN}/trigger4905_dataset_v1"
ARMS="${RUN}/adaptive_scale_arms_v1"
INFERENCE="${RUN}/adaptive_scale_inference_v1"
AUDIT="${RUN}/adaptive_scale_protocol_audit_v1"
TAU="0.9602926671504974"

if [[ -e "${RUN}/PIPELINE_LAUNCHED" ]]; then
  echo "refusing duplicate threshold Full-5320 launch" >&2
  exit 1
fi
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"
cd "${ROOT}"

for file in \
  build_selective_evidence_rewrite_full_threshold_v1.py \
  build_qwen3_adaptive_crop_full_threshold_arms_v1.py \
  materialize_threshold_full_reuse_v1.py \
  infer_qwen3_adaptive_crop_threshold_full_v1.py \
  infer_qwen3_adaptive_crop_threshold_full_decode_recovery_v1.py \
  audit_threshold_full_adaptive_a2_v1.py; do
  cp "evaluation/tools/${file}" "${RUN}/source_snapshot/"
done
cp evaluation/scripts/run_qwen3_threshold_full5320_a2_v1.sh \
  "${RUN}/source_snapshot/"
cp "${CALIBRATION}/judge_and_threshold_v1/threshold_result.json" \
  "${RUN}/FROZEN_THRESHOLD_SOURCE.json"

"${PY}" evaluation/tools/build_selective_evidence_rewrite_full_threshold_v1.py \
  --pool-dir "${SOURCE}/a0_pool_v1" \
  --scores "${SOURCE}/a0_verifier_merged_v1/scores_all.jsonl" \
  --av-manifest "${SOURCE}/av_manifest_v1/av_funnel_full5320.jsonl" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root data/adsqa_full_valid5320_v1/asr_union_records \
  --output-dir "${DATASET}" \
  --expected-count 5320 \
  --trigger-count 4905 \
  --support-threshold "${TAU}" \
  --runtime-folds 6 \
  > "${RUN}/logs/build_trigger4905.log" 2>&1

"${PY}" evaluation/tools/build_qwen3_adaptive_crop_full_threshold_arms_v1.py \
  --input-jsonl "${DATASET}/items_answer_free.jsonl" \
  --output-root "${ARMS}" \
  --smoke-per-fold 2 \
  > "${RUN}/logs/build_adaptive_arms.log" 2>&1

"${PY}" evaluation/tools/materialize_threshold_full_reuse_v1.py \
  --dataset "${DATASET}/items_answer_free.jsonl" \
  --source-root "${SOURCE}/adaptive_scale_inference_v1/full530/adaptive_scale" \
  --output-root "${INFERENCE}" \
  --audit "${RUN}/reuse_full530_v1/audit.json" \
  > "${RUN}/logs/materialize_reuse.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/TRIGGER_AND_REUSE_COMPLETE"

status=0
for fold in 0 1 2 3 4 5; do
  expected=817
  [[ "${fold}" -lt 3 ]] && expected=818
  nohup "${PY}" \
    evaluation/tools/infer_qwen3_adaptive_crop_threshold_full_decode_recovery_v1.py \
    --gpu-id "${fold}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${ARMS}/full4905/adaptive_scale/shards/fold_${fold}.jsonl" \
    --output-dir "${INFERENCE}/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items "${expected}" \
    --a2-method Qwen3_adaptive_scale_AVEvidenceRewrite12_A2 \
    --skip-a1 \
    --resume-existing \
    > "${RUN}/logs/adaptive_fold_${fold}.log" 2>&1 < /dev/null &
  echo "$!" > "${RUN}/pids/adaptive_fold_${fold}.pid"
done

for fold in 0 1 2 3 4 5; do
  pid="$(<"${RUN}/pids/adaptive_fold_${fold}.pid")"
  if ! wait "${pid}"; then
    status=1
  else
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_FOLD_${fold}_COMPLETE"
  fi
done
if [[ "${status}" -ne 0 ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_INFERENCE_FAILED"
  exit 1
fi

"${PY}" evaluation/tools/audit_threshold_full_adaptive_a2_v1.py \
  --dataset-root "${ARMS}" \
  --run-root "${INFERENCE}" \
  --reuse-manifest "${RUN}/reuse_full530_v1/reuse_manifest.jsonl" \
  --output-dir "${AUDIT}" \
  > "${RUN}/logs/audit_adaptive_a2.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_INFERENCE_COMPLETE_AWAITING_JUDGE_PREFLIGHT"

sha256sum \
  "${RUN}/FROZEN_THRESHOLD_SOURCE.json" \
  "${DATASET}/audit.json" \
  "${ARMS}/dataset_audit.json" \
  "${RUN}/reuse_full530_v1/audit.json" \
  "${AUDIT}/audit.json" \
  "${AUDIT}/manifest.jsonl" \
  > "${RUN}/INFERENCE_SHA256SUMS"
