#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct"
VERIFIER_MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
VIDEO_ROOT="${ROOT}/data/external/evads_v1/videos_unpacked/videos"
PRIMARY="${ROOT}/data/external/evads_v1/experiments/overnight_20260729_external3000c_v1"
RUN_C="${PRIMARY}/external3000c_v1"
NIGHT="${ROOT}/data/external/evads_v1/experiments/overnight_20260729_external3000c_qwen25_v1/native1296_v1"
TAU_ACCURACY="0.9602926671504974"
EXPECTED=3000
VIDEOS=600
PER_FOLD=600

mkdir -p "${NIGHT}/logs" "${NIGHT}/pids" "${NIGHT}/source_snapshot"
if [[ -e "${NIGHT}/RELAY_LAUNCHED" && "${RESUME_SHARED_GPU:-0}" != "1" ]]; then
  echo "refusing duplicate Qwen2.5 native1296 launch" >&2
  exit 1
fi
if [[ ! -e "${NIGHT}/RELAY_LAUNCHED" ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/RELAY_LAUNCHED"
else
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/RELAY_RESUMED_SHARED_GPU"
fi

on_error() {
  local status=$?
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    echo "exit_status=${status}"
    echo "line=${BASH_LINENO[0]:-unknown}"
  } > "${NIGHT}/PIPELINE_FAILED"
  exit "${status}"
}
trap on_error ERR

# Do not compete with the primary job. Start only after its full answer-free audit.
while [[ ! -e "${PRIMARY}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION" ]]; do
  if [[ -e "${PRIMARY}/PIPELINE_FAILED" ]]; then
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/PRIMARY_PIPELINE_FAILED_NO_RELAY"
    exit 1
  fi
  sleep 60
done

cd "${ROOT}"
cp \
  evaluation/tools/infer_evads_qwen25_evidence8_v2.py \
  evaluation/tools/infer_qwen25_samebudget_ablation_v1.py \
  evaluation/tools/audit_evads_a0_native_tokens_v2.py \
  evaluation/tools/build_evads_a0_verifier_pool_v2.py \
  evaluation/tools/score_answer_claims_qwen3_v1.py \
  evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  evaluation/tools/summarize_evads_threshold_operating_points_v1.py \
  evaluation/tools/build_evads_threshold_evidence_dataset_v1.py \
  evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
  evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
  evaluation/tools/merge_evads_a2_scores_v2.py \
  evaluation/scripts/run_evads_external3000c_qwen25_native1296_v1.sh \
  "${NIGHT}/source_snapshot/"

"${PY}" -c \
  "from evaluation.methods.gated_avcrop.gate_protocol import validate_clean_model_path; import json; print(json.dumps(validate_clean_model_path('${MODEL}'), indent=2))" \
  > "${NIGHT}/clean_model_identity.json"

snapshot_gpus() {
  local label="$1"
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    nvidia-smi \
      --query-gpu=index,memory.used,memory.total,utilization.gpu \
      --format=csv,noheader,nounits
    nvidia-smi \
      --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
      --format=csv,noheader,nounits || true
  } > "${NIGHT}/logs/gpu_${label}.log"
}

wait_for_gpus_1_to_5() {
  local label="$1"
  local ready
  local free_mib
  local gpu
  local min_free_mib=26000
  while :; do
    ready=1
    for gpu in 1 2 3 4 5; do
      free_mib="$(
        nvidia-smi \
        --id="${gpu}" \
        --query-gpu=memory.free \
        --format=csv,noheader,nounits 2>/dev/null \
        | tr -d '[:space:]'
      )"
      if [[ ! "${free_mib}" =~ ^[0-9]+$ ]] \
        || (( free_mib < min_free_mib )); then
        ready=0
      fi
    done
    if [[ "${ready}" -eq 1 ]]; then
      snapshot_gpus "before_${label}"
      return
    fi
    sleep 60
  done
}

wait_wave() {
  local label="$1"
  shift
  local failed=0
  local pid
  for pid in "$@"; do
    if ! wait "${pid}"; then
      failed=1
    fi
  done
  snapshot_gpus "after_${label}"
  if [[ "${failed}" -ne 0 ]]; then
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/${label}_FAILED"
    return 1
  fi
}

run_a0_wave() {
  local label="$1"
  local method="$2"
  local manifest="$3"
  local frame_field="$4"
  local output_root="$5"
  local fold
  local gpu
  local pid
  local -a pids
  wait_for_gpus_1_to_5 "${label}"
  pids=()
  for fold in 0 1 2 3 4; do
    gpu="$((fold + 1))"
    nohup "${PY}" evaluation/tools/infer_evads_qwen25_evidence8_v2.py \
      --gpu-id "${gpu}" \
      --questions "${RUN_C}/dataset/shards/fold_${fold}.json" \
      --manifest "${manifest}" \
      --method "${method}" \
      --frame-field "${frame_field}" \
      --video-root "${VIDEO_ROOT}" \
      --output-dir "${output_root}/fold_${fold}" \
      --model-dir "${MODEL}" \
      --unified-size 512 \
      --max-visual-tokens 1296 \
      --max-new-tokens 512 \
      --allow-shared-gpu \
      --min-free-memory-mib 26000 \
      > "${NIGHT}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${NIGHT}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_wave "${label}" "${pids[@]}"
  "${PY}" evaluation/tools/audit_evads_a0_native_tokens_v2.py \
    --questions "${RUN_C}/dataset/questions_answer_free.json" \
    --a0-root "${output_root}" \
    --output "${output_root}/protocol_audit.json" \
    --expected-method "${method}" \
    --expected-count "${EXPECTED}" \
    --expected-videos "${VIDEOS}" \
    --expected-per-fold "${PER_FOLD}" \
    --expected-visual-tokens 1296 \
    > "${NIGHT}/logs/${label}_audit.log" 2>&1
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/${label}_COMPLETE"
}

run_verifier_wave() {
  local label="$1"
  local input_root="$2"
  local output_root="$3"
  local fold
  local gpu
  local pid
  local -a pids
  wait_for_gpus_1_to_5 "${label}"
  pids=()
  for fold in 0 1 2 3 4; do
    gpu="$((fold + 1))"
    mkdir -p "${output_root}/fold_${fold}"
    nohup "${PY}" evaluation/tools/score_answer_claims_qwen3_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${VERIFIER_MODEL}" \
      --adapter-dir "${ADAPTER}" \
      --input-jsonl "${input_root}/shards/fold_${fold}.jsonl" \
      --output-dir "${output_root}/fold_${fold}" \
      --views 8 \
      --unified-size 448 \
      --max-visual-tokens 4096 \
      --overwrite \
      > "${NIGHT}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${NIGHT}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_wave "${label}" "${pids[@]}"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/${label}_COMPLETE"
}

run_threshold_a2_wave() {
  local label="$1"
  local dataset="$2"
  local output_root="$3"
  local variant="$4"
  local method="$5"
  local fold
  local gpu
  local shard
  local count
  local pid
  local -a pids
  wait_for_gpus_1_to_5 "${label}"
  pids=()
  for fold in 0 1 2 3 4; do
    gpu="$((fold + 1))"
    shard="${dataset}/shards/fold_${fold}.jsonl"
    count="$(wc -l < "${shard}" | tr -d ' ')"
    if [[ "${count}" -le 0 ]]; then
      echo "empty threshold shard for fold ${fold}" >&2
      return 1
    fi
    nohup "${PY}" evaluation/tools/infer_qwen25_samebudget_ablation_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --input-jsonl "${shard}" \
      --output-dir "${output_root}/fold_${fold}" \
      --base-size 512 \
      --crop-size 896 \
      --max-visual-tokens 4096 \
      --max-new-tokens 192 \
      --expected-items "${count}" \
      --a2-method "${method}" \
      --ablation-variant "${variant}" \
      --skip-a1 \
      --resume-existing \
      --allow-shared-gpu \
      --min-free-memory-mib 26000 \
      > "${NIGHT}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${NIGHT}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_wave "${label}" "${pids[@]}"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/${label}_COMPLETE"
}

run_a0_wave \
  "QWEN25_MMR8_A0_3000" \
  "Qwen25_SigLIPMMR64_8_lambda070" \
  "${RUN_C}/siglip_mmr_topk_manifest3000.jsonl" \
  "siglip_mmr8_frame_indices" \
  "${NIGHT}/a0_mmr8"
run_a0_wave \
  "QWEN25_UNIFORM8_A0_3000" \
  "Qwen25_Uniform64_8" \
  "${RUN_C}/uniform8_manifest3000.jsonl" \
  "uniform8_frame_indices" \
  "${NIGHT}/a0_uniform8"
run_a0_wave \
  "QWEN25_SIGLIP_TOPK8_A0_3000" \
  "Qwen25_SigLIPTopK64_8" \
  "${RUN_C}/siglip_topk8_compat_manifest3000.jsonl" \
  "siglip_mmr8_frame_indices" \
  "${NIGHT}/a0_siglip_topk8"

"${PY}" evaluation/tools/build_evads_a0_verifier_pool_v2.py \
  --questions "${RUN_C}/dataset/questions_answer_free.json" \
  --a0-root "${NIGHT}/a0_mmr8" \
  --video-root "${VIDEO_ROOT}" \
  --output-dir "${NIGHT}/a0_mmr8_pool" \
  --expected-method "Qwen25_SigLIPMMR64_8_lambda070" \
  --candidate-method "CleanQwen25_EvadsSigLIPMMR8_A0" \
  --expected-count "${EXPECTED}" \
  --expected-videos "${VIDEOS}" \
  --expected-per-fold "${PER_FOLD}" \
  --expected-visual-tokens 1296 \
  > "${NIGHT}/logs/build_a0_pool.log" 2>&1
run_verifier_wave \
  "QWEN25_MMR8_A0_VERIFIER_3000" \
  "${NIGHT}/a0_mmr8_pool" \
  "${NIGHT}/a0_mmr8_verifier_shards"
"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  --pool-dir "${NIGHT}/a0_mmr8_pool" \
  --scores-root "${NIGHT}/a0_mmr8_verifier_shards" \
  --output-dir "${NIGHT}/a0_mmr8_verifier_merged" \
  --expected-count "${EXPECTED}" \
  --expected-videos "${VIDEOS}" \
  --expected-per-fold "${PER_FOLD}" \
  > "${NIGHT}/logs/merge_a0_verifier.log" 2>&1
"${PY}" evaluation/tools/summarize_evads_threshold_operating_points_v1.py \
  --scores "${NIGHT}/a0_mmr8_verifier_merged/scores_all.jsonl" \
  --pool "${NIGHT}/a0_mmr8_pool/model_inputs_all.jsonl" \
  --output "${NIGHT}/threshold_operating_points.json" \
  --expected-count "${EXPECTED}" \
  > "${NIGHT}/logs/threshold_operating_points.log" 2>&1
"${PY}" evaluation/tools/build_evads_threshold_evidence_dataset_v1.py \
  --pool-dir "${NIGHT}/a0_mmr8_pool" \
  --scores "${NIGHT}/a0_mmr8_verifier_merged/scores_all.jsonl" \
  --questions "${RUN_C}/dataset/questions_answer_free.json" \
  --output-dir "${NIGHT}/threshold_max_pool" \
  --support-threshold "${TAU_ACCURACY}" \
  --expected-source-count "${EXPECTED}" \
  --minimum-trigger-count 300 \
  > "${NIGHT}/logs/build_threshold_max_pool.log" 2>&1

run_threshold_a2_wave \
  "QWEN25_ADAPTIVE12_3000" \
  "${NIGHT}/threshold_max_pool" \
  "${NIGHT}/adaptive12" \
  "adaptive_scale" \
  "Qwen25_EVAds3000C_AVEvidence12_A2"
run_threshold_a2_wave \
  "QWEN25_EXTRAGLOBAL12_3000" \
  "${NIGHT}/threshold_max_pool" \
  "${NIGHT}/extra_global12" \
  "extra_global" \
  "Qwen25_EVAds3000C_ExtraGlobal12_A2"
"${PY}" evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
  --dataset-dir "${NIGHT}/threshold_max_pool" \
  --adaptive-root "${NIGHT}/adaptive12" \
  --extra-global-root "${NIGHT}/extra_global12" \
  --expected-visual-tokens 3992 \
  --output "${NIGHT}/threshold_a2_controls_protocol_audit.json" \
  > "${NIGHT}/logs/audit_threshold_a2_controls.log" 2>&1

for arm in adaptive extra_global; do
  if [[ "${arm}" == "adaptive" ]]; then
    expected_method="Qwen25_EVAds3000C_AVEvidence12_A2"
  else
    expected_method="Qwen25_EVAds3000C_ExtraGlobal12_A2"
  fi
  "${PY}" evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
    --dataset-dir "${NIGHT}/threshold_max_pool" \
    --inference-root "${NIGHT}/${arm}12" \
    --output-dir "${NIGHT}/${arm}12_verifier_inputs" \
    --expected-a2-method "${expected_method}" \
    --candidate-method "${expected_method}" \
    > "${NIGHT}/logs/build_${arm}12_verifier_inputs.log" 2>&1
  run_verifier_wave \
    "QWEN25_${arm^^}12_VERIFIER_3000" \
    "${NIGHT}/${arm}12_verifier_inputs" \
    "${NIGHT}/${arm}12_verifier_shards"
  "${PY}" evaluation/tools/merge_evads_a2_scores_v2.py \
    --input-dir "${NIGHT}/${arm}12_verifier_inputs" \
    --shard-root "${NIGHT}/${arm}12_verifier_shards" \
    --output-dir "${NIGHT}/${arm}12_verifier_merged" \
    > "${NIGHT}/logs/merge_${arm}12_verifier.log" 2>&1
done

sha256sum \
  "${NIGHT}/clean_model_identity.json" \
  "${NIGHT}/a0_mmr8/protocol_audit.json" \
  "${NIGHT}/a0_uniform8/protocol_audit.json" \
  "${NIGHT}/a0_siglip_topk8/protocol_audit.json" \
  "${NIGHT}/a0_mmr8_verifier_merged/summary.json" \
  "${NIGHT}/threshold_operating_points.json" \
  "${NIGHT}/threshold_max_pool/audit.json" \
  "${NIGHT}/threshold_a2_controls_protocol_audit.json" \
  "${NIGHT}/adaptive12_verifier_merged/summary.json" \
  "${NIGHT}/extra_global12_verifier_merged/summary.json" \
  > "${NIGHT}/INFERENCE_SHA256SUMS"
snapshot_gpus "pipeline_complete"
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${NIGHT}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
rm -f "${NIGHT}/PIPELINE_FAILED"
