#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R"
VERIFIER_MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
RUN="${ROOT}/evaluation/runs/readr_increment_confirm1000_v2"
INPUTS="${RUN}/inputs_v1"
FULL_INPUTS="${ROOT}/evaluation/runs/qwen25_adsqa_full7846_v1/inputs_v1"
VIDEO_ROOT="${ROOT}/data/videos"
EXPECTED=1000
EXPECTED_VIDEOS=200
GPUS=(0 1 2 3 4)

mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
if [[ -e "${RUN}/PIPELINE_LAUNCHED" ]]; then
  echo "refusing duplicate Confirm-1000 launch" >&2
  exit 1
fi
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"

on_error() {
  local status=$?
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    echo "exit_status=${status}"
    echo "line=${BASH_LINENO[0]:-unknown}"
  } > "${RUN}/PIPELINE_FAILED"
  exit "${status}"
}
trap on_error ERR

cd "${ROOT}"
cp \
  evaluation/tools/prepare_readr_increment_confirm1000_v2.py \
  evaluation/tools/normalize_readr_predictions_v1.py \
  evaluation/tools/infer_readr_samebudget_decode_recovery_v1.py \
  evaluation/tools/infer_adsqa_qwen25_evidence8_decode_recovery_v1.py \
  evaluation/tools/infer_qwen25_samebudget_ablation_decode_recovery_v1.py \
  evaluation/tools/infer_qwen25_samebudget_ablation_v1.py \
  evaluation/tools/score_answer_claims_qwen3_full7846_decode_recovery_v1.py \
  evaluation/tools/score_answer_claims_qwen3_v1.py \
  evaluation/tools/adsqa_qwen25_full7846_protocol_v1.py \
  evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
  evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
  evaluation/tools/merge_evads_a2_scores_v2.py \
  evaluation/tools/merge_qwen3_a0_verifier_pool_supplement_v1.py \
  evaluation/scripts/run_readr_increment_confirm1000_v2.sh \
  "${RUN}/source_snapshot/"

"${PY}" evaluation/tools/prepare_readr_increment_confirm1000_v2.py \
  --questions "${FULL_INPUTS}/questions_answer_free.json" \
  --mmr-manifest "${FULL_INPUTS}/mmr8_manifest.jsonl" \
  --av-manifest "${FULL_INPUTS}/av_manifest.jsonl" \
  --exclude "${ROOT}/data/train.json" \
  --exclude "${ROOT}/evaluation/runs/innovation1_dualconsensus_confirmd300_v1/dataset_v3/confirmd_questions_answer_free.json" \
  --exclude "${ROOT}/data/confirm300_validanswer_disjoint_pilot50_question.json" \
  --exclude "${ROOT}/data/confirm300b_focuscontext_disjoint_prior_question.json" \
  --exclude "${ROOT}/data/confirm300c_temporal_disjoint_prior_question.json" \
  --exclude "${ROOT}/evaluation/runs/readr_increment_pilot300_v1/inputs_v1/questions_answer_free.json" \
  --seed "readr_increment_confirm1000_v2" \
  --calibration-videos 0 \
  --confirm-videos 200 \
  --output-dir "${INPUTS}" \
  > "${RUN}/logs/prepare.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/INPUTS_COMPLETE"

python3 - <<PY
import hashlib, json
from pathlib import Path
model = Path("${MODEL}")
payload = {
    "schema_version": "readr_checkpoint_identity_v1",
    "model_dir": str(model.resolve()),
    "config_sha256": hashlib.sha256((model / "config.json").read_bytes()).hexdigest(),
    "checkpoint_role": "common_answer_backbone_for_all_confirm1000_arms",
    "is_clean_qwen25": False,
    "is_readr_grpo_checkpoint": True,
}
Path("${RUN}/model_identity.json").write_text(
    json.dumps(payload, indent=2) + "\\n", encoding="utf-8"
)
PY

snapshot_gpus() {
  local label="$1"
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    nvidia-smi \
      --query-gpu=index,memory.used,memory.free,memory.total,utilization.gpu \
      --format=csv,noheader,nounits
    nvidia-smi \
      --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
      --format=csv,noheader,nounits || true
  } > "${RUN}/logs/gpu_${label}.log"
}

wait_gpu_idle() {
  local gpu="$1"
  while nvidia-smi --id="${gpu}" --query-compute-apps=pid \
      --format=csv,noheader,nounits 2>/dev/null | grep -Eq '^[[:space:]]*[0-9]+'; do
    sleep 60
  done
}

run_a0_shards() {
  local label="$1"
  local frame_field="$2"
  local raw_method="$3"
  local output_root="$4"
  local manifest="${INPUTS}/mmr8_manifest.jsonl"
  if [[ "${frame_field}" == "uniform8_frame_indices" ]]; then
    manifest="${FULL_INPUTS}/uniform8_manifest.jsonl"
  fi
  local -a pids=()
  local fold gpu pid
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    wait_gpu_idle "${gpu}"
    nohup bash -c \
      "cd '${ROOT}' && ADSQA_DECODE_RECOVERY_ROOT='${RUN}/decode_recovery_v1/${label}' '${PY}' evaluation/tools/infer_adsqa_qwen25_evidence8_decode_recovery_v1.py --gpu-id '${gpu}' --questions '${INPUTS}/shards/fold_${fold}.json' --manifest '${manifest}' --method '${raw_method}' --frame-field '${frame_field}' --video-root '${VIDEO_ROOT}' --output-dir '${output_root}/fold_${fold}' --model-dir '${MODEL}' --unified-size 512 --max-visual-tokens 1296 --max-new-tokens 512" \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  for pid in "${pids[@]}"; do
    wait "${pid}"
  done
}

normalize_a0() {
  local raw_root="$1"
  local output_root="$2"
  local raw_method="$3"
  local normalized_method="$4"
  "${PY}" evaluation/tools/normalize_readr_predictions_v1.py \
    --questions "${INPUTS}/questions_answer_free.json" \
    --raw-root "${raw_root}" \
    --output-root "${output_root}" \
    --raw-method "${raw_method}" \
    --normalized-method "${normalized_method}" \
    > "${RUN}/logs/normalize_${normalized_method}.log" 2>&1
  "${PY}" evaluation/tools/adsqa_qwen25_full7846_protocol_v1.py audit-a0 \
    --questions "${INPUTS}/questions_answer_free.json" \
    --a0-root "${output_root}" \
    --output "${output_root}/protocol_audit.json" \
    --expected-method "${normalized_method}" \
    --expected-count "${EXPECTED}" \
    --expected-visual-tokens 1296 \
    > "${RUN}/logs/audit_${normalized_method}.log" 2>&1
}

snapshot_gpus "before_a0"
run_a0_shards \
  "uniform8_raw" \
  "uniform8_frame_indices" \
  "ReAdR_Uniform8_Raw" \
  "${RUN}/uniform8_raw"
normalize_a0 \
  "${RUN}/uniform8_raw" \
  "${RUN}/uniform8" \
  "ReAdR_Uniform8_Raw" \
  "ReAdR_Uniform8"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/UNIFORM8_COMPLETE"

run_a0_shards \
  "mmr8_raw" \
  "siglip_mmr8_frame_indices" \
  "ReAdR_MMR8_Raw" \
  "${RUN}/mmr8_raw"
normalize_a0 \
  "${RUN}/mmr8_raw" \
  "${RUN}/mmr8" \
  "ReAdR_MMR8_Raw" \
  "ReAdR_MMR8"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/MMR8_COMPLETE"

"${PY}" evaluation/tools/adsqa_qwen25_full7846_protocol_v1.py build-pool \
  --questions "${INPUTS}/questions_answer_free.json" \
  --a0-root "${RUN}/mmr8" \
  --video-root "${VIDEO_ROOT}" \
  --output-dir "${RUN}/mmr8_pool" \
  --expected-method "ReAdR_MMR8" \
  --candidate-method "ReAdR_MMR8_A0" \
  --expected-count "${EXPECTED}" \
  --expected-videos "${EXPECTED_VIDEOS}" \
  --expected-visual-tokens 1296 \
  > "${RUN}/logs/build_mmr8_pool.log" 2>&1

run_verifier_wave() {
  local label="$1"
  local input_root="$2"
  local output_root="$3"
  local -a pids=()
  local fold gpu pid
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    wait_gpu_idle "${gpu}"
    mkdir -p "${output_root}/fold_${fold}"
    nohup bash -c \
      "cd '${ROOT}' && ADSQA_DECODE_RECOVERY_ROOT='${RUN}/decode_recovery_v1/${label}' '${PY}' evaluation/tools/score_answer_claims_qwen3_full7846_decode_recovery_v1.py --gpu-id '${gpu}' --model-dir '${VERIFIER_MODEL}' --adapter-dir '${ADAPTER}' --input-jsonl '${input_root}/shards/fold_${fold}.jsonl' --output-dir '${output_root}/fold_${fold}' --views 8 --unified-size 448 --max-visual-tokens 4096 --overwrite" \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  for pid in "${pids[@]}"; do
    wait "${pid}"
  done
}

run_verifier_wave \
  "mmr8_verifier" \
  "${RUN}/mmr8_pool" \
  "${RUN}/mmr8_verifier_shards"
"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_supplement_v1.py \
  --pool-dir "${RUN}/mmr8_pool" \
  --scores-root "${RUN}/mmr8_verifier_shards" \
  --output-dir "${RUN}/mmr8_verifier_merged" \
  --expected-count "${EXPECTED}" \
  --expected-videos "${EXPECTED_VIDEOS}" \
  > "${RUN}/logs/merge_mmr8_verifier.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/MMR8_VERIFIER_COMPLETE"

# The Pilot-300 deployment threshold is frozen before Confirm-1000 inference.
"${PY}" evaluation/tools/adsqa_qwen25_full7846_protocol_v1.py build-trigger \
  --pool-dir "${RUN}/mmr8_pool" \
  --scores "${RUN}/mmr8_verifier_merged/scores_all.jsonl" \
  --av-manifest "${INPUTS}/av_manifest.jsonl" \
  --ocr-root "${ROOT}/data/candidate_cache_full_v1/ocr" \
  --asr-root "${FULL_INPUTS}/segmented_asr_records" \
  --output-dir "${RUN}/frozen_triggered_candidates" \
  --threshold 0.9241418242454529 \
  --expected-count "${EXPECTED}" \
  > "${RUN}/logs/build_frozen_triggered_candidates.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FROZEN_TRIGGERED_COMPLETE"

run_a2_wave() {
  local label="$1"
  local variant="$2"
  local method="$3"
  local output_root="$4"
  local -a pids=()
  local fold gpu pid expected_items
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    expected_items="$(wc -l < "${RUN}/frozen_triggered_candidates/shards/fold_${fold}.jsonl" | tr -d ' ')"
    wait_gpu_idle "${gpu}"
    nohup bash -c \
      "cd '${ROOT}' && ADSQA_DECODE_RECOVERY_ROOT='${RUN}/decode_recovery_v1/${label}' '${PY}' evaluation/tools/infer_readr_samebudget_decode_recovery_v1.py --gpu-id '${gpu}' --model-dir '${MODEL}' --input-jsonl '${RUN}/frozen_triggered_candidates/shards/fold_${fold}.jsonl' --output-dir '${output_root}/fold_${fold}' --base-size 512 --crop-size 896 --max-visual-tokens 4096 --max-new-tokens 192 --expected-items '${expected_items}' --a2-method '${method}' --ablation-variant '${variant}' --skip-a1" \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  for pid in "${pids[@]}"; do
    wait "${pid}"
  done
}

run_a2_wave \
  "adaptive12" \
  "adaptive_scale" \
  "ReAdR_Adaptive12_A2" \
  "${RUN}/adaptive12"
"${PY}" evaluation/tools/adsqa_qwen25_full7846_protocol_v1.py audit-a2 \
  --dataset-dir "${RUN}/frozen_triggered_candidates" \
  --inference-root "${RUN}/adaptive12" \
  --expected-variant "adaptive_scale" \
  --expected-visual-tokens 3992 \
  --output "${RUN}/adaptive12_protocol_audit.json" \
  > "${RUN}/logs/audit_adaptive12.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/ADAPTIVE12_COMPLETE"

run_a2_wave \
  "extra_global12" \
  "extra_global" \
  "ReAdR_ExtraGlobal12_A2" \
  "${RUN}/extra_global12"
"${PY}" evaluation/tools/adsqa_qwen25_full7846_protocol_v1.py audit-a2 \
  --dataset-dir "${RUN}/frozen_triggered_candidates" \
  --inference-root "${RUN}/extra_global12" \
  --expected-variant "extra_global" \
  --expected-visual-tokens 3992 \
  --output "${RUN}/extra_global12_protocol_audit.json" \
  > "${RUN}/logs/audit_extra_global12.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/EXTRAGLOBAL12_COMPLETE"

build_and_score_a2() {
  local label="$1"
  local method="$2"
  local inference_root="$3"
  "${PY}" evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
    --dataset-dir "${RUN}/frozen_triggered_candidates" \
    --inference-root "${inference_root}" \
    --output-dir "${RUN}/${label}_verifier_inputs" \
    --expected-a2-method "${method}" \
    --candidate-method "${method}" \
    > "${RUN}/logs/build_${label}_verifier_inputs.log" 2>&1
  run_verifier_wave \
    "${label}_verifier" \
    "${RUN}/${label}_verifier_inputs" \
    "${RUN}/${label}_verifier_shards"
  "${PY}" evaluation/tools/merge_evads_a2_scores_v2.py \
    --input-dir "${RUN}/${label}_verifier_inputs" \
    --shard-root "${RUN}/${label}_verifier_shards" \
    --output-dir "${RUN}/${label}_verifier_merged" \
    > "${RUN}/logs/merge_${label}_verifier.log" 2>&1
}

build_and_score_a2 \
  "adaptive12" \
  "ReAdR_Adaptive12_A2" \
  "${RUN}/adaptive12"
build_and_score_a2 \
  "extra_global12" \
  "ReAdR_ExtraGlobal12_A2" \
  "${RUN}/extra_global12"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_VERIFIERS_COMPLETE"

sha256sum \
  "${RUN}/model_identity.json" \
  "${INPUTS}/audit.json" \
  "${RUN}/uniform8/protocol_audit.json" \
  "${RUN}/mmr8/protocol_audit.json" \
  "${RUN}/mmr8_verifier_merged/summary.json" \
  "${RUN}/frozen_triggered_candidates/audit.json" \
  "${RUN}/adaptive12_protocol_audit.json" \
  "${RUN}/extra_global12_protocol_audit.json" \
  "${RUN}/adaptive12_verifier_merged/summary.json" \
  "${RUN}/extra_global12_verifier_merged/summary.json" \
  > "${RUN}/INFERENCE_SHA256SUMS"
snapshot_gpus "complete"
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${RUN}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
rm -f "${RUN}/PIPELINE_FAILED"
