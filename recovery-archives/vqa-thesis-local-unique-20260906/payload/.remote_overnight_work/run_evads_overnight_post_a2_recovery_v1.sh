#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
NIGHT="${ROOT}/data/external/evads_v1/experiments/overnight_20260729_external3000c_v1"
RUN_C="${NIGHT}/external3000c_v1"

mkdir -p "${NIGHT}/logs" "${NIGHT}/pids" "${NIGHT}/source_snapshot"
if [[ -e "${NIGHT}/POST_A2_RECOVERY_LAUNCHED" ]]; then
  echo "refusing duplicate post-A2 recovery launch" >&2
  exit 1
fi
for marker in \
  MMR8_A0_3000_COMPLETE \
  UNIFORM8_A0_3000_COMPLETE \
  SIGLIP_TOPK8_A0_3000_COMPLETE \
  MMR8_A0_VERIFIER_3000_COMPLETE \
  EXTERNAL3000C_ADAPTIVE12_COMPLETE \
  EXTERNAL3000C_EXTRAGLOBAL12_COMPLETE; do
  [[ -e "${NIGHT}/${marker}" ]] || {
    echo "missing prerequisite marker: ${marker}" >&2
    exit 1
  }
done
if [[ -e "${NIGHT}/PIPELINE_FAILED" ]]; then
  cp "${NIGHT}/PIPELINE_FAILED" "${NIGHT}/PIPELINE_FAILED_THIRD_AUDIT_V1"
  rm -f "${NIGHT}/PIPELINE_FAILED"
fi
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${NIGHT}/POST_A2_RECOVERY_LAUNCHED"

on_error() {
  local status=$?
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    echo "exit_status=${status}"
    echo "line=${BASH_LINENO[0]:-unknown}"
    echo "recovery=post_a2_v1"
  } > "${NIGHT}/PIPELINE_FAILED"
  exit "${status}"
}
trap on_error ERR

cd "${ROOT}"
cp \
  evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
  evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
  evaluation/scripts/run_evads_overnight_post_a2_recovery_v1.sh \
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
  local pid
  local failed=0
  for pid in "$@"; do
    if ! wait "${pid}"; then
      failed=1
    fi
  done
  snapshot_gpus "after_${label}"
  if [[ "${failed}" -ne 0 ]]; then
    echo "wave failed: ${label}" >&2
    return 1
  fi
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

if [[ -e "${RUN_C}/threshold_a2_controls_protocol_audit_v2.json" ]]; then
  "${PY}" -c \
    "import json; p='${RUN_C}/threshold_a2_controls_protocol_audit_v2.json'; d=json.load(open(p)); assert d.get('passed') is True; assert d.get('question_count') == 1645" \
    > "${NIGHT}/logs/audit_threshold_a2_controls_v2_reuse.log" 2>&1
else
  "${PY}" evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
    --dataset-dir "${RUN_C}/threshold_max_pool" \
    --adaptive-root "${RUN_C}/adaptive12" \
    --extra-global-root "${RUN_C}/extra_global12" \
    --output "${RUN_C}/threshold_a2_controls_protocol_audit_v2.json" \
    > "${NIGHT}/logs/audit_threshold_a2_controls_v2.log" 2>&1
fi
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${NIGHT}/THRESHOLD_A2_CONTROLS_V2_COMPLETE"

for arm in adaptive extra_global; do
  if [[ "${arm}" == "adaptive" ]]; then
    inference_root="${RUN_C}/adaptive12"
    expected_method="Qwen3_EVAds3000C_AVEvidence12_A2"
  else
    inference_root="${RUN_C}/extra_global12"
    expected_method="Qwen3_EVAds3000C_ExtraGlobal12_A2"
  fi
  "${PY}" evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
    --dataset-dir "${RUN_C}/threshold_max_pool" \
    --inference-root "${inference_root}" \
    --output-dir "${RUN_C}/${arm}12_verifier_inputs_v3" \
    --expected-a2-method "${expected_method}" \
    --candidate-method "${expected_method}" \
    > "${NIGHT}/logs/build_${arm}12_verifier_inputs_v3.log" 2>&1
  run_verifier_wave \
    "EXTERNAL3000C_${arm^^}12_VERIFIER_V3" \
    "${RUN_C}/${arm}12_verifier_inputs_v3" \
    "${RUN_C}/${arm}12_verifier_shards_v3"
  "${PY}" evaluation/tools/merge_evads_a2_scores_v2.py \
    --input-dir "${RUN_C}/${arm}12_verifier_inputs_v3" \
    --shard-root "${RUN_C}/${arm}12_verifier_shards_v3" \
    --output-dir "${RUN_C}/${arm}12_verifier_merged_v3" \
    > "${NIGHT}/logs/merge_${arm}12_verifier_v3.log" 2>&1
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
  "${RUN_C}/threshold_a2_controls_protocol_audit_v2.json" \
  "${RUN_C}/adaptive12_verifier_merged_v3/summary.json" \
  "${RUN_C}/extra_global12_verifier_merged_v3/summary.json" \
  > "${NIGHT}/INFERENCE_SHA256SUMS_V2"
snapshot_gpus "pipeline_complete_v2"
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${NIGHT}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
rm -f "${NIGHT}/PIPELINE_FAILED"
