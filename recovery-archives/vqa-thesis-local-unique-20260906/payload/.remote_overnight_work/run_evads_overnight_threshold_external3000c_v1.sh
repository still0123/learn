#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
VIDEO_ROOT="${ROOT}/data/external/evads_v1/videos_unpacked/videos"
INDEX_ROOT="${ROOT}/data/external/evads_v1/cache/video_index64_v1"
SOURCE="${ROOT}/data/external/evads_v1/manifests/evads_test_answer_free_inputs.jsonl"
EXTERNAL500="${ROOT}/data/external/evads_v1/experiments/external500_v1/questions_answer_free.jsonl"
RUN_B="${ROOT}/data/external/evads_v1/experiments/mmr_selectrescue_external1000b_v1"
TRANSFER="${RUN_B}/threshold_transfer_tau_knee_v1"
NIGHT="${ROOT}/data/external/evads_v1/experiments/overnight_20260729_external3000c_v1"
RUN_C="${NIGHT}/external3000c_v1"
TAU_KNEE="0.9195213913917542"
TAU_ACCURACY="0.9602926671504974"
EXPECTED_C=3000
VIDEOS_C=600
PER_FOLD_C=600
VIDEOS_PER_FOLD_C=120

mkdir -p "${NIGHT}/logs" "${NIGHT}/pids" "${NIGHT}/source_snapshot"
RESUME_AFTER_TRANSFER_ADAPTIVE="${RESUME_AFTER_TRANSFER_ADAPTIVE:-0}"
RESUME_AFTER_TRANSFER_COMPLETE="${RESUME_AFTER_TRANSFER_COMPLETE:-0}"
if [[ -e "${NIGHT}/NIGHT_PIPELINE_LAUNCHED" ]]; then
  if [[
    "${RESUME_AFTER_TRANSFER_ADAPTIVE}" != "1"
    && "${RESUME_AFTER_TRANSFER_COMPLETE}" != "1"
  ]]; then
    echo "refusing duplicate overnight pipeline launch" >&2
    exit 1
  fi
  if [[ -e "${NIGHT}/PIPELINE_FAILED" ]]; then
    if [[ -e "${NIGHT}/PIPELINE_FAILED_FIRST" ]]; then
      cp "${NIGHT}/PIPELINE_FAILED" "${NIGHT}/PIPELINE_FAILED_SECOND"
    else
      cp "${NIGHT}/PIPELINE_FAILED" "${NIGHT}/PIPELINE_FAILED_FIRST"
    fi
    rm -f "${NIGHT}/PIPELINE_FAILED"
  fi
  date -u +"%Y-%m-%dT%H:%M:%SZ" \
    > "${NIGHT}/NIGHT_PIPELINE_RECOVERY_LAUNCHED"
else
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/NIGHT_PIPELINE_LAUNCHED"
fi

on_error() {
  status=$?
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    echo "exit_status=${status}"
    echo "line=${BASH_LINENO[0]:-unknown}"
  } > "${NIGHT}/PIPELINE_FAILED"
  exit "${status}"
}
trap on_error ERR

cd "${ROOT}"

cp \
  evaluation/tools/build_evads_answerfree_external_v1.py \
  evaluation/tools/build_evads_siglip_mmr_topk_manifest_v1.py \
  evaluation/tools/merge_evads_siglip_mmr_topk_manifest_v1.py \
  evaluation/tools/materialize_evads_evidence8_manifests_v1.py \
  evaluation/tools/build_evads_a0_verifier_pool_v2.py \
  evaluation/tools/build_evads_threshold_evidence_dataset_v1.py \
  evaluation/tools/audit_evads_threshold_a2_controls_v1.py \
  evaluation/tools/build_evads_a2_verifier_inputs_v2.py \
  evaluation/tools/merge_evads_a2_scores_v2.py \
  evaluation/tools/summarize_evads_threshold_operating_points_v1.py \
  evaluation/tools/build_evads_siglip_mmr8_manifest_v1.py \
  evaluation/tools/infer_evads_qwen3_siglip_mmr8_v1.py \
  evaluation/tools/audit_evads_external1000b_a0_v1.py \
  evaluation/tools/score_answer_claims_qwen3_v1.py \
  evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  evaluation/tools/infer_qwen3_samebudget_ablation_v1.py \
  evaluation/tools/build_evads_mmr_selectrescue_trigger100_v1.py \
  evaluation/scripts/run_evads_overnight_threshold_external3000c_v1.sh \
  "${NIGHT}/source_snapshot/"

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
  local busy
  local gpu
  while :; do
    busy=0
    for gpu in 1 2 3 4 5; do
      if nvidia-smi \
        --id="${gpu}" \
        --query-compute-apps=pid \
        --format=csv,noheader,nounits 2>/dev/null \
        | grep -Eq '[0-9]'; then
        busy=1
      fi
    done
    if [[ "${busy}" -eq 0 ]]; then
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
    mkdir -p "${output_root}" "${NIGHT}/logs" "${NIGHT}/pids"
    nohup "${PY}" evaluation/tools/infer_qwen3_samebudget_ablation_v1.py \
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
      > "${NIGHT}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${NIGHT}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_wave "${label}" "${pids[@]}"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/${label}_COMPLETE"
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
    nohup "${PY}" evaluation/tools/infer_evads_qwen3_siglip_mmr8_v1.py \
      --gpu-id "${gpu}" \
      --questions "${RUN_C}/dataset/shards/fold_${fold}.json" \
      --manifest "${manifest}" \
      --method "${method}" \
      --frame-field "${frame_field}" \
      --video-root "${VIDEO_ROOT}" \
      --output-dir "${output_root}/fold_${fold}" \
      --model-dir "${MODEL}" \
      --unified-size 512 \
      --max-visual-tokens 1024 \
      --max-new-tokens 512 \
      > "${NIGHT}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${NIGHT}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_wave "${label}" "${pids[@]}"
  "${PY}" evaluation/tools/audit_evads_external1000b_a0_v1.py \
    --questions "${RUN_C}/dataset/questions_answer_free.json" \
    --a0-root "${output_root}" \
    --output "${output_root}/protocol_audit.json" \
    --expected-method "${method}" \
    --expected-count "${EXPECTED_C}" \
    --expected-videos "${VIDEOS_C}" \
    --expected-per-fold "${PER_FOLD_C}" \
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
      --model-dir "${MODEL}" \
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

# Stage 1: transfer the frozen OOF Pareto-knee threshold to External-1000B.
if [[ "${RESUME_AFTER_TRANSFER_COMPLETE}" == "1" ]]; then
  "${PY}" -c \
    "import json; from pathlib import Path; p=Path('${TRANSFER}/protocol_audit.json'); a=json.loads(p.read_text()); assert a.get('passed') is True and a.get('question_count') == 384"
elif [[ "${RESUME_AFTER_TRANSFER_ADAPTIVE}" == "1" ]]; then
  adaptive_count="$(
    find "${TRANSFER}/adaptive12" -name a2_prediction.json -type f | wc -l | tr -d ' '
  )"
  adaptive_trace_count="$(
    find "${TRANSFER}/adaptive12" -name a2_trace.json -type f | wc -l | tr -d ' '
  )"
  if [[ "${adaptive_count}" -ne 384 || "${adaptive_trace_count}" -ne 384 ]]; then
    echo "cannot resume: Adaptive384 coverage is incomplete" >&2
    exit 1
  fi
  "${PY}" -c \
    "import json; from pathlib import Path; p=Path('${TRANSFER}/dataset/audit.json'); a=json.loads(p.read_text()); assert a.get('passed') is True and a.get('question_count') == 384"
else
  mkdir -p "${TRANSFER}"
  "${PY}" evaluation/tools/build_evads_threshold_evidence_dataset_v1.py \
    --pool-dir "${RUN_B}/full1000/a0_pool" \
    --scores "${RUN_B}/full1000/a0_verifier_merged/scores_all.jsonl" \
    --questions "${RUN_B}/dataset/questions_answer_free.json" \
    --output-dir "${TRANSFER}/dataset" \
    --support-threshold "${TAU_KNEE}" \
    --expected-source-count 1000 \
    --expected-trigger-count 384 \
    --minimum-trigger-count 384 \
    > "${NIGHT}/logs/transfer_build_dataset.log" 2>&1

  run_threshold_a2_wave \
    "TRANSFER_ADAPTIVE384" \
    "${TRANSFER}/dataset" \
    "${TRANSFER}/adaptive12" \
    "adaptive_scale" \
    "Qwen3_EVAds1000B_TauKnee_AVEvidence12_A2"
fi
if [[ "${RESUME_AFTER_TRANSFER_COMPLETE}" != "1" ]]; then
  run_threshold_a2_wave \
    "TRANSFER_EXTRAGLOBAL384" \
    "${TRANSFER}/dataset" \
    "${TRANSFER}/extra_global12" \
    "extra_global" \
    "Qwen3_EVAds1000B_TauKnee_ExtraGlobal12_A2"
  "${PY}" evaluation/tools/audit_evads_threshold_a2_controls_v1.py \
    --dataset-dir "${TRANSFER}/dataset" \
    --adaptive-root "${TRANSFER}/adaptive12" \
    --extra-global-root "${TRANSFER}/extra_global12" \
    --output "${TRANSFER}/protocol_audit.json" \
    > "${NIGHT}/logs/transfer_protocol_audit.log" 2>&1
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/TRANSFER1000B_COMPLETE"
fi

# Stage 2: freeze External-3000C from entirely unused E-VAds videos.
mkdir -p "${RUN_C}"
"${PY}" evaluation/tools/build_evads_answerfree_external_v1.py \
  --answer-free-source "${SOURCE}" \
  --exclude-questions "${EXTERNAL500}" \
  --exclude-questions "${RUN_B}/dataset/questions_answer_free.json" \
  --video-index-dir "${INDEX_ROOT}" \
  --output-dir "${RUN_C}/dataset" \
  --selection-seed "evads-external3000c-unused-videos-v1" \
  --split-name "evads_external3000c_v1" \
  --selected-videos "${VIDEOS_C}" \
  > "${NIGHT}/logs/build_external3000c.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/EXTERNAL3000C_FROZEN"

# Stage 3: create shared SigLIP MMR8 and TopK8 plans.
wait_for_gpus_1_to_5 "SIGLIP_MANIFEST3000"
pids=()
for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  mkdir -p "${RUN_C}/manifest_shards"
  nohup "${PY}" evaluation/tools/build_evads_siglip_mmr_topk_manifest_v1.py \
    --gpu-id "${gpu}" \
    --questions "${RUN_C}/dataset/shards/fold_${fold}.json" \
    --video-index-dir "${INDEX_ROOT}" \
    --video-root "${VIDEO_ROOT}" \
    --output "${RUN_C}/manifest_shards/fold_${fold}.jsonl" \
    > "${NIGHT}/logs/siglip_manifest_fold_${fold}.log" 2>&1 &
  pid=$!
  echo "${pid}" > "${NIGHT}/pids/siglip_manifest_fold_${fold}.pid"
  pids+=("${pid}")
done
wait_wave "SIGLIP_MANIFEST3000" "${pids[@]}"
"${PY}" evaluation/tools/merge_evads_siglip_mmr_topk_manifest_v1.py \
  --questions "${RUN_C}/dataset/questions_answer_free.json" \
  --shard-dir "${RUN_C}/manifest_shards" \
  --output "${RUN_C}/siglip_mmr_topk_manifest3000.jsonl" \
  --audit-output "${RUN_C}/siglip_mmr_topk_manifest3000.audit.json" \
  --expected-count "${EXPECTED_C}" \
  --expected-videos "${VIDEOS_C}" \
  --expected-per-fold "${PER_FOLD_C}" \
  --expected-videos-per-fold "${VIDEOS_PER_FOLD_C}" \
  > "${NIGHT}/logs/merge_siglip_manifest.log" 2>&1
"${PY}" evaluation/tools/materialize_evads_evidence8_manifests_v1.py \
  --source-manifest "${RUN_C}/siglip_mmr_topk_manifest3000.jsonl" \
  --uniform-output "${RUN_C}/uniform8_manifest3000.jsonl" \
  --topk-alias-output "${RUN_C}/siglip_topk8_compat_manifest3000.jsonl" \
  --audit "${RUN_C}/evidence8_manifest_audit.json" \
  --expected-count "${EXPECTED_C}" \
  --expected-videos "${VIDEOS_C}" \
  --expected-per-fold "${PER_FOLD_C}" \
  > "${NIGHT}/logs/materialize_evidence8.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/EVIDENCE8_MANIFESTS_COMPLETE"

# Stage 4: three same-model, same-budget standard baselines.
run_a0_wave \
  "MMR8_A0_3000" \
  "SigLIPMMR64_8_lambda070" \
  "${RUN_C}/siglip_mmr_topk_manifest3000.jsonl" \
  "siglip_mmr8_frame_indices" \
  "${RUN_C}/a0_mmr8"
run_a0_wave \
  "UNIFORM8_A0_3000" \
  "Uniform64_8" \
  "${RUN_C}/uniform8_manifest3000.jsonl" \
  "uniform8_frame_indices" \
  "${RUN_C}/a0_uniform8"
run_a0_wave \
  "SIGLIP_TOPK8_A0_3000" \
  "SigLIPTopK64_8" \
  "${RUN_C}/siglip_topk8_compat_manifest3000.jsonl" \
  "siglip_mmr8_frame_indices" \
  "${RUN_C}/a0_siglip_topk8"

# Stage 5: answer-free sufficiency scoring and maximum reusable A2 pool.
"${PY}" evaluation/tools/build_evads_a0_verifier_pool_v2.py \
  --questions "${RUN_C}/dataset/questions_answer_free.json" \
  --a0-root "${RUN_C}/a0_mmr8" \
  --video-root "${VIDEO_ROOT}" \
  --output-dir "${RUN_C}/a0_mmr8_pool" \
  --expected-method "SigLIPMMR64_8_lambda070" \
  --candidate-method "CleanQwen3_EvadsSigLIPMMR8_A0" \
  --expected-count "${EXPECTED_C}" \
  --expected-videos "${VIDEOS_C}" \
  --expected-per-fold "${PER_FOLD_C}" \
  > "${NIGHT}/logs/build_a0_mmr8_pool.log" 2>&1
run_verifier_wave \
  "MMR8_A0_VERIFIER_3000" \
  "${RUN_C}/a0_mmr8_pool" \
  "${RUN_C}/a0_mmr8_verifier_shards"
"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  --pool-dir "${RUN_C}/a0_mmr8_pool" \
  --scores-root "${RUN_C}/a0_mmr8_verifier_shards" \
  --output-dir "${RUN_C}/a0_mmr8_verifier_merged" \
  --expected-count "${EXPECTED_C}" \
  --expected-videos "${VIDEOS_C}" \
  --expected-per-fold "${PER_FOLD_C}" \
  > "${NIGHT}/logs/merge_a0_mmr8_verifier.log" 2>&1
"${PY}" evaluation/tools/summarize_evads_threshold_operating_points_v1.py \
  --scores "${RUN_C}/a0_mmr8_verifier_merged/scores_all.jsonl" \
  --pool "${RUN_C}/a0_mmr8_pool/model_inputs_all.jsonl" \
  --output "${RUN_C}/threshold_operating_points.json" \
  --expected-count "${EXPECTED_C}" \
  > "${NIGHT}/logs/threshold_operating_points.log" 2>&1
"${PY}" evaluation/tools/build_evads_threshold_evidence_dataset_v1.py \
  --pool-dir "${RUN_C}/a0_mmr8_pool" \
  --scores "${RUN_C}/a0_mmr8_verifier_merged/scores_all.jsonl" \
  --questions "${RUN_C}/dataset/questions_answer_free.json" \
  --output-dir "${RUN_C}/threshold_max_pool" \
  --support-threshold "${TAU_ACCURACY}" \
  --expected-source-count "${EXPECTED_C}" \
  --minimum-trigger-count 300 \
  > "${NIGHT}/logs/build_threshold_max_pool.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/THRESHOLD_MAX_POOL_FROZEN"

# Stage 6: main evidence rewrite and equal-budget ExtraGlobal control.
run_threshold_a2_wave \
  "EXTERNAL3000C_ADAPTIVE12" \
  "${RUN_C}/threshold_max_pool" \
  "${RUN_C}/adaptive12" \
  "adaptive_scale" \
  "Qwen3_EVAds3000C_AVEvidence12_A2"
run_threshold_a2_wave \
  "EXTERNAL3000C_EXTRAGLOBAL12" \
  "${RUN_C}/threshold_max_pool" \
  "${RUN_C}/extra_global12" \
  "extra_global" \
  "Qwen3_EVAds3000C_ExtraGlobal12_A2"
"${PY}" evaluation/tools/audit_evads_threshold_a2_controls_v1.py \
  --dataset-dir "${RUN_C}/threshold_max_pool" \
  --adaptive-root "${RUN_C}/adaptive12" \
  --extra-global-root "${RUN_C}/extra_global12" \
  --output "${RUN_C}/threshold_a2_controls_protocol_audit.json" \
  > "${NIGHT}/logs/audit_threshold_a2_controls.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/THRESHOLD_A2_CONTROLS_COMPLETE"

# Stage 7: support-score both A2 arms; no reference answers or judge API.
for arm in adaptive extra_global; do
  if [[ "${arm}" == "adaptive" ]]; then
    inference_root="${RUN_C}/adaptive12"
    expected_method="Qwen3_EVAds3000C_AVEvidence12_A2"
    candidate_method="Qwen3_EVAds3000C_AVEvidence12_A2"
  else
    inference_root="${RUN_C}/extra_global12"
    expected_method="Qwen3_EVAds3000C_ExtraGlobal12_A2"
    candidate_method="Qwen3_EVAds3000C_ExtraGlobal12_A2"
  fi
  "${PY}" evaluation/tools/build_evads_a2_verifier_inputs_v2.py \
    --dataset-dir "${RUN_C}/threshold_max_pool" \
    --inference-root "${inference_root}" \
    --output-dir "${RUN_C}/${arm}12_verifier_inputs" \
    --expected-a2-method "${expected_method}" \
    --candidate-method "${candidate_method}" \
    > "${NIGHT}/logs/build_${arm}12_verifier_inputs.log" 2>&1
  run_verifier_wave \
    "EXTERNAL3000C_${arm^^}12_VERIFIER" \
    "${RUN_C}/${arm}12_verifier_inputs" \
    "${RUN_C}/${arm}12_verifier_shards"
  "${PY}" evaluation/tools/merge_evads_a2_scores_v2.py \
    --input-dir "${RUN_C}/${arm}12_verifier_inputs" \
    --shard-root "${RUN_C}/${arm}12_verifier_shards" \
    --output-dir "${RUN_C}/${arm}12_verifier_merged" \
    > "${NIGHT}/logs/merge_${arm}12_verifier.log" 2>&1
done

sha256sum \
  "${RUN_C}/dataset/questions_answer_free.json" \
  "${RUN_C}/dataset/selection_manifest.jsonl" \
  "${RUN_C}/siglip_mmr_topk_manifest3000.jsonl" \
  "${RUN_C}/uniform8_manifest3000.jsonl" \
  "${RUN_C}/siglip_topk8_compat_manifest3000.jsonl" \
  "${RUN_C}/a0_mmr8/protocol_audit.json" \
  "${RUN_C}/a0_uniform8/protocol_audit.json" \
  "${RUN_C}/a0_siglip_topk8/protocol_audit.json" \
  "${RUN_C}/a0_mmr8_verifier_merged/summary.json" \
  "${RUN_C}/threshold_operating_points.json" \
  "${RUN_C}/threshold_max_pool/audit.json" \
  "${RUN_C}/threshold_a2_controls_protocol_audit.json" \
  "${RUN_C}/adaptive12_verifier_merged/summary.json" \
  "${RUN_C}/extra_global12_verifier_merged/summary.json" \
  > "${NIGHT}/INFERENCE_SHA256SUMS"
snapshot_gpus "pipeline_complete"
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${NIGHT}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
rm -f "${NIGHT}/PIPELINE_FAILED"
