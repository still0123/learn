#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
SOURCE="${ROOT}/evaluation/runs/qwen3_selective_evidence_rewrite_confirmd300_v1"
RUN="${ROOT}/evaluation/runs/qwen3_selective_evidence_rewrite_random30_confirmd300_v1"
GPU_ID="${GPU_ID:-1}"
DATASET="${RUN}/random30_dataset_v1"
REWRITE="${RUN}/rewrite_inference_v1"
A2_INPUTS="${RUN}/a2_verifier_inputs_v1"
A2_SHARDS="${RUN}/a2_verifier_shards_v1"
A2_MERGED="${RUN}/a2_verifier_merged_v1"
CHOICES="${RUN}/frozen_choices_v1"

if [[ -e "${RUN}/LAUNCHED" ]]; then
  echo "refusing duplicate random30 launch" >&2
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

cp evaluation/tools/build_selective_evidence_rewrite_confirmd_random30_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_qwen3_selective_evidence_rewrite_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/merge_selective_rewrite_a2_scores_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py "${RUN}/source_snapshot/"
cp evaluation/scripts/run_qwen3_selective_evidence_rewrite_random30_v1.sh "${RUN}/source_snapshot/"

"${PY}" evaluation/tools/build_selective_evidence_rewrite_confirmd_random30_v1.py \
  --pool-dir "${SOURCE}/a0_pool_v1" \
  --scores "${SOURCE}/a0_verifier_merged_v2_decord/scores_all.jsonl" \
  --av-manifest "${SOURCE}/av_manifest_v1/av_funnel_confirmd300.jsonl" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root data/segmented_asr_innovation1_confirmd300_v1/records \
  --low-support-selection "${SOURCE}/trigger30_dataset_v1/selection_manifest_private_support_only.jsonl" \
  --output-dir "${DATASET}" \
  --trigger-count 30 \
  --seed 20260728 \
  > "${RUN}/logs/build_random30.log" 2>&1
cp \
  "${DATASET}/selection_manifest_random_only.jsonl" \
  "${DATASET}/selection_manifest_private_support_only.jsonl"

for fold in 0 1 2 3 4; do
  "${PY}" evaluation/tools/infer_qwen3_selective_evidence_rewrite_v1.py \
    --gpu-id "${GPU_ID}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${DATASET}/shards/fold_${fold}.jsonl" \
    --output-dir "${REWRITE}/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items 6 \
    > "${RUN}/logs/rewrite_${fold}.log" 2>&1
done

"${PY}" evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py \
  --dataset-dir "${DATASET}" \
  --inference-root "${REWRITE}" \
  --output-dir "${A2_INPUTS}" \
  --expected-count 30 \
  --expected-videos 30 \
  --expected-per-fold 6 \
  > "${RUN}/logs/build_a2_inputs.log" 2>&1

SCORER="${SOURCE}/source_snapshot/score_answer_claims_qwen3_v1_decord_exact_v2.py"
for fold in 0 1 2 3 4; do
  "${PY}" "${SCORER}" \
    --gpu-id "${GPU_ID}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${A2_INPUTS}/shards/fold_${fold}.jsonl" \
    --output-dir "${A2_SHARDS}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    --overwrite \
    > "${RUN}/logs/a2_verifier_${fold}.log" 2>&1
done

"${PY}" evaluation/tools/merge_selective_rewrite_a2_scores_v1.py \
  --shard-root "${A2_SHARDS}" \
  --output-dir "${A2_MERGED}" \
  --expected-count 30 \
  --expected-per-fold 6 \
  > "${RUN}/logs/merge_a2_scores.log" 2>&1

"${PY}" evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py \
  --dataset-dir "${DATASET}" \
  --inference-root "${REWRITE}" \
  --a0-scores "${SOURCE}/a0_verifier_merged_v2_decord/scores_all.jsonl" \
  --a2-scores "${A2_MERGED}/scores_all.jsonl" \
  --output-dir "${CHOICES}" \
  --support-threshold 0.8933094143867493 \
  --minimum-margin 0.25 \
  --expected-count 30 \
  --expected-videos 30 \
  --expected-per-fold 6 \
  > "${RUN}/logs/freeze_choices.log" 2>&1

find "${RUN}" -type f ! -name SHA256SUMS -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${RUN}/SHA256SUMS"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/INFERENCE_AND_SELECTION_COMPLETE"
