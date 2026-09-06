#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
SOURCE_RUN="${ROOT}/evaluation/runs/qwen3_selective_evidence_rewrite_smoke50_v1"
DATASET="${SOURCE_RUN}/dataset_v1"
REFERENCE_INFERENCE="${SOURCE_RUN}/rewrite_inference_v1"
A0_SCORES="${SOURCE_RUN}/a0_verifier_merged_v1/scores_all.jsonl"
RUN="${ROOT}/evaluation/runs/qwen3_selective_evidence_rewrite_ablation_oof50_v1"
INFER="${ROOT}/evaluation/tools/infer_qwen3_selective_evidence_rewrite_ablation_v1.py"
BUILD_VERIFIER="${ROOT}/evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py"
SCORE="${ROOT}/evaluation/tools/score_answer_claims_qwen3_v1.py"
FREEZE="${ROOT}/evaluation/tools/freeze_selective_evidence_rewrite_ablation_choices_v1.py"

for required in \
  "${SOURCE_RUN}/INFERENCE_AND_SELECTION_COMPLETE" \
  "${DATASET}/audit.json" \
  "${DATASET}/items_answer_free.jsonl" \
  "${REFERENCE_INFERENCE}" \
  "${A0_SCORES}" \
  "${MODEL}/config.json" \
  "${ADAPTER}" \
  "${INFER}" \
  "${BUILD_VERIFIER}" \
  "${SCORE}" \
  "${FREEZE}"; do
  [[ -e "${required}" ]] || {
    echo "missing frozen input: ${required}" >&2
    exit 1
  }
done
if [[ -e "${RUN}/LAUNCHED" ]]; then
  echo "refusing duplicate ablation launch" >&2
  exit 2
fi

mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
cp "${INFER}" "${BUILD_VERIFIER}" "${SCORE}" "${FREEZE}" "$0" \
  "${RUN}/source_snapshot/"
{
  sha256sum \
    "${DATASET}/audit.json" \
    "${DATASET}/items_answer_free.jsonl" \
    "${A0_SCORES}" \
    "${MODEL}/config.json" \
    "${INFER}" \
    "${BUILD_VERIFIER}" \
    "${SCORE}" \
    "${FREEZE}"
} > "${RUN}/frozen_inputs_sha256.txt"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/LAUNCHED"

run_arm() {
  local ablation="$1"
  local gpu="$2"
  local arm="${RUN}/${ablation}"
  local inference="${arm}/rewrite_inference_v1"
  local verifier_inputs="${arm}/a2_verifier_inputs_v1"
  local verifier_scores="${arm}/a2_verifier_scores_v1"
  local choices="${arm}/frozen_choices_v1"

  mkdir -p "${arm}/logs"
  "${PY}" "${INFER}" \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${DATASET}/items_answer_free.jsonl" \
    --output-dir "${inference}" \
    --ablation "${ablation}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items 50 \
    > "${arm}/logs/inference.log" 2>&1

  "${PY}" "${BUILD_VERIFIER}" \
    --dataset-dir "${DATASET}" \
    --inference-root "${inference}" \
    --output-dir "${verifier_inputs}" \
    --expected-count 50 \
    --expected-videos 50 \
    --expected-per-fold 10 \
    > "${arm}/logs/build_verifier_inputs.log" 2>&1

  "${PY}" "${SCORE}" \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${verifier_inputs}/model_inputs_all.jsonl" \
    --output-dir "${verifier_scores}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    --overwrite \
    > "${arm}/logs/verifier.log" 2>&1

  "${PY}" "${FREEZE}" \
    --dataset-dir "${DATASET}" \
    --inference-root "${inference}" \
    --reference-inference-root "${REFERENCE_INFERENCE}" \
    --ablation "${ablation}" \
    --a0-scores "${A0_SCORES}" \
    --a2-scores "${verifier_scores}/scores.jsonl" \
    --output-dir "${choices}" \
    --support-threshold 0.8933094143867493 \
    --minimum-margin 0.25 \
    --expected-count 50 \
    --expected-videos 50 \
    --expected-per-fold 10 \
    > "${arm}/logs/freeze.log" 2>&1

  (
    cd "${arm}"
    find . -type f ! -name SHA256SUMS -print0 \
      | sort -z \
      | xargs -0 sha256sum \
      > SHA256SUMS
  )
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${arm}/COMPLETE"
}

run_arm no_ocr 1 &
pid_no_ocr="$!"
echo "${pid_no_ocr}" > "${RUN}/pids/no_ocr.pid"
run_arm no_segmented_asr 2 &
pid_no_asr="$!"
echo "${pid_no_asr}" > "${RUN}/pids/no_segmented_asr.pid"
run_arm no_local_crop 3 &
pid_no_crop="$!"
echo "${pid_no_crop}" > "${RUN}/pids/no_local_crop.pid"

status=0
for pid in "${pid_no_ocr}" "${pid_no_asr}" "${pid_no_crop}"; do
  if ! wait "${pid}"; then
    status=1
  fi
done
if [[ "${status}" -ne 0 ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FAILED"
  exit 1
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/COMPLETE"
