#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
ASR_PY="/data1/rmx/venvs/adsqa_asr_v1/bin/python"
ASR_MODEL="/data1/rmx/models/Whisper-large-v3-turbo-modelscope/large-v3-turbo.pt"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
EVADS="${ROOT}/data/external/evads_v1/experiments/overnight_20260729_external3000c_qwen25_v1/native1296_v1"
PREP="${ROOT}/data/adsqa_supplement2526_prep_v1"
ASR="${ROOT}/data/segmented_asr_supplement2526_v1"
DATA="${ROOT}/data/adsqa_supplement2526_v1"
RUN="${ROOT}/evaluation/runs/qwen3_adsqa_supplement2526_v1"
SELECTED="${RUN}/selected8_manifest_v1"
RAW="${RUN}/raw_features_v1"
AV="${RUN}/av_manifest_v1"
MMR="${RUN}/mmr8_v1"
UNIFORM="${RUN}/uniform8_v1"
CLIP="${RUN}/cliptopk8_v1"
A0_POOL="${RUN}/a0_pool_v1"
A0_SHARDS="${RUN}/a0_verifier_shards_v1"
A0_MERGED="${RUN}/a0_verifier_merged_v1"
TRIGGER="${RUN}/threshold_trigger_v1"
ARMS="${RUN}/adaptive_scale_arms_v1"
ADAPTIVE="${RUN}/adaptive_scale_inference_v1"
ADAPTIVE_AUDIT="${RUN}/adaptive_scale_protocol_audit_v1"
FINAL="${RUN}/final_candidates_v1"
TAU="0.9602926671504974"
EXPECTED=2526
VIDEOS=1258
GPUS=(1 2 3 4 5)

mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
if [[ -e "${RUN}/RELAY_LAUNCHED" && "${RESUME_SUPPLEMENT:-0}" != "1" ]]; then
  echo "refusing duplicate AdsQA supplement relay" >&2
  exit 1
fi
if [[ ! -e "${RUN}/RELAY_LAUNCHED" ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/RELAY_LAUNCHED"
else
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/RELAY_RESUMED"
fi

mark() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/$1"
}

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
  } > "${RUN}/logs/gpu_${label}.log"
}

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

wait_all_idle() {
  local label="$1"
  local gpu
  local busy
  while :; do
    busy=0
    for gpu in "${GPUS[@]}"; do
      if nvidia-smi --id="${gpu}" --query-compute-apps=pid \
        --format=csv,noheader,nounits 2>/dev/null | grep -Eq '[0-9]'; then
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

wait_jobs() {
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
    mark "${label}_FAILED"
    return 1
  fi
}

json_count() {
  "${PY}" -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$1"
}

run_selected_wave() {
  local label="$1"
  local method="$2"
  local manifest="$3"
  local output_root="$4"
  local marker="$5"
  local fold gpu expected pid
  local -a pids=()
  [[ -e "${RUN}/${marker}" ]] && return
  wait_all_idle "${label}"
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    expected="$(json_count "${DATA}/shards/fold_${fold}.json")"
    nohup "${PY}" \
      evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --method "${method}" \
      --question-file "${DATA}/shards/fold_${fold}.json" \
      --selection-manifest "${manifest}" \
      --asr-file "${DATA}/asr_combined_answer_free.json" \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output-dir "${output_root}/fold_${fold}" \
      --views 8 \
      --unified-size 512 \
      --max-visual-tokens 4096 \
      --max-new-tokens 256 \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_jobs "${label}" "${pids[@]}"
  mkdir -p "${output_root}/audits"
  for fold in 0 1 2 3 4; do
    expected="$(json_count "${DATA}/shards/fold_${fold}.json")"
    "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
      --questions "${DATA}/shards/fold_${fold}.json" \
      --selection-manifest "${manifest}" \
      --inference-dir "${output_root}/fold_${fold}" \
      --output "${output_root}/audits/fold_${fold}.json" \
      --expected-count "${expected}" \
      > "${RUN}/logs/audit_${label}_fold_${fold}.log" 2>&1
  done
  mark "${marker}"
}

run_uniform_wave() {
  local label="$1"
  local output_root="$2"
  local marker="$3"
  local fold gpu expected pid
  local -a pids=()
  [[ -e "${RUN}/${marker}" ]] && return
  wait_all_idle "${label}"
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    expected="$(json_count "${DATA}/shards/fold_${fold}.json")"
    nohup "${PY}" \
      evaluation/tools/infer_adsqa_answer_lora_qwen3_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --method CleanQwen3_Raw8 \
      --question-file "${DATA}/shards/fold_${fold}.json" \
      --asr-file "${DATA}/asr_combined_answer_free.json" \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output-dir "${output_root}/fold_${fold}/base" \
      --views 8 \
      --unified-size 512 \
      --max-visual-tokens 4096 \
      --max-new-tokens 256 \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  wait_jobs "${label}" "${pids[@]}"
  mkdir -p "${output_root}/audits"
  for fold in 0 1 2 3 4; do
    expected="$(json_count "${DATA}/shards/fold_${fold}.json")"
    "${PY}" evaluation/tools/audit_adsqa_uniform8_full_v1.py \
      --questions "${DATA}/shards/fold_${fold}.json" \
      --inference-root "${output_root}" \
      --output "${output_root}/audits/fold_${fold}.json" \
      --expected-count "${expected}" \
      > "${RUN}/logs/audit_${label}_fold_${fold}.log" 2>&1
  done
  mark "${marker}"
}

cd "${ROOT}"
echo "$$" > "${RUN}/pids/relay.pid"

# The current E-VAds reproduction owns GPU1-5. Relay only after its full audit.
while [[ ! -e "${EVADS}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION" ]]; do
  if [[ -e "${EVADS}/PIPELINE_FAILED" ]]; then
    evads_pid="$(cat "${EVADS}/pids/driver.pid" 2>/dev/null || true)"
    if [[ -z "${evads_pid}" ]] || ! kill -0 "${evads_pid}" 2>/dev/null; then
      mark EVADS_PREREQUISITE_FAILED
      exit 1
    fi
  fi
  sleep 60
done
mark EVADS_PREREQUISITE_COMPLETE

for file in \
  prepare_adsqa_supplement2526_asr_v1.py \
  audit_adsqa_supplement2526_asr_v1.py \
  build_adsqa_full7846_supplement_v1.py \
  build_selective_evidence_rewrite_supplement_threshold_v1.py \
  build_qwen3_adaptive_crop_supplement_threshold_arms_v1.py \
  audit_threshold_supplement_adaptive_a2_v1.py \
  merge_qwen3_a0_verifier_pool_supplement_v1.py \
  materialize_adsqa_supplement2526_candidates_v1.py; do
  cp "evaluation/tools/${file}" "${RUN}/source_snapshot/"
done
cp evaluation/scripts/run_adsqa_supplement2526_relay_v1.sh \
  "${RUN}/source_snapshot/"

if [[ ! -e "${RUN}/ASR_SUPPLEMENT_COMPLETE" ]]; then
  wait_all_idle asr_supplement
  asr_pids=()
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    mkdir -p "${ASR}/shard_${fold}"
    nohup "${ASR_PY}" preprocess/build_segmented_asr_cache_v1.py \
      --index_dir data/video_index_v1 \
      --selection_files "${PREP}/selection_shards/fold_${fold}.json" \
      --model_path "${ASR_MODEL}" \
      --output_dir "${ASR}/shard_${fold}" \
      --gpu_id "${gpu}" \
      > "${RUN}/logs/asr_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/asr_fold_${fold}.pid"
    asr_pids+=("${pid}")
  done
  wait_jobs asr_supplement "${asr_pids[@]}"
  "${PY}" evaluation/tools/audit_adsqa_supplement2526_asr_v1.py \
    --prep-root "${PREP}" \
    --asr-root "${ASR}/shard_0" \
    --asr-root "${ASR}/shard_1" \
    --asr-root "${ASR}/shard_2" \
    --asr-root "${ASR}/shard_3" \
    --asr-root "${ASR}/shard_4" \
    --output "${ASR}/audit.json" \
    > "${RUN}/logs/audit_asr.log" 2>&1
  mark ASR_SUPPLEMENT_COMPLETE
fi

if [[ ! -e "${DATA}/FROZEN" ]]; then
  "${PY}" evaluation/tools/build_adsqa_full7846_supplement_v1.py \
    --questions data/testset_question.json \
    --groundtruth data/testset_groundtruth.json \
    --video-root data/videos \
    --clip-root data/candidate_cache_full_v1/clip \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --asr-root data/segmented_asr_pilot_train_confirm_v1/records \
    --asr-root data/segmented_asr_innovation1_confirmd300_v1/records \
    --asr-root "${ASR}/shard_0" \
    --asr-root "${ASR}/shard_1" \
    --asr-root "${ASR}/shard_2" \
    --asr-root "${ASR}/shard_3" \
    --asr-root "${ASR}/shard_4" \
    --output-root "${DATA}" \
    > "${RUN}/logs/build_dataset.log" 2>&1
fi
mark DATASET_FROZEN

if [[ ! -e "${RUN}/SELECTED8_MANIFESTS_COMPLETE" ]]; then
  wait_all_idle selected8_manifests
  "${PY}" evaluation/tools/build_adsqa_clip_mmr8_manifest_v1.py \
    --gpu-id 1 \
    --questions "${DATA}/questions_answer_free.json" \
    --clip-cache-root data/candidate_cache_full_v1/clip \
    --clip-model models/clip-vit-large-patch14 \
    --clip-output "${SELECTED}/clip_topk8.jsonl" \
    --mmr-output "${SELECTED}/mmr8.jsonl" \
    --audit-output "${SELECTED}/audit.json" \
    > "${RUN}/logs/build_selected8.log" 2>&1
  mark SELECTED8_MANIFESTS_COMPLETE
fi

if [[ ! -e "${RUN}/AV_FEATURES_COMPLETE" ]]; then
  wait_all_idle av_raw_features
  raw_pids=()
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    expected="$(json_count "${DATA}/shards/fold_${fold}.json")"
    overwrite=()
    if [[ -e "${RAW}/shard_${fold}.jsonl" ]] \
      && [[ "$(wc -l < "${RAW}/shard_${fold}.jsonl")" -ne "${expected}" ]]; then
      overwrite+=(--overwrite)
    fi
    if [[ ! -e "${RAW}/shard_${fold}.jsonl" ]] \
      || [[ "$(wc -l < "${RAW}/shard_${fold}.jsonl")" -ne "${expected}" ]]; then
      nohup "${PY}" \
        evaluation/tools/build_diverse_local8_manifest_full_decode_recovery_v1.py \
        --gpu-id "${gpu}" \
        --questions "${DATA}/shards/fold_${fold}.json" \
        --segmented-asr-root "${DATA}/asr_union_records" \
        --ocr-root data/candidate_cache_full_v1/ocr \
        --clip-path models/clip-vit-large-patch14 \
        --video-root data/videos \
        --frames-fallback-root data/frames_8 \
        --output "${RAW}/shard_${fold}.jsonl" \
        "${overwrite[@]}" \
        > "${RUN}/logs/raw_features_fold_${fold}.log" 2>&1 &
      pid=$!
      echo "${pid}" > "${RUN}/pids/raw_features_fold_${fold}.pid"
      raw_pids+=("${pid}")
    fi
  done
  if [[ "${#raw_pids[@]}" -gt 0 ]]; then
    wait_jobs av_raw_features "${raw_pids[@]}"
  fi
  merge_args=()
  for fold in 0 1 2 3 4; do
    merge_args+=(--input "${RAW}/shard_${fold}.jsonl")
  done
  "${PY}" evaluation/tools/merge_answer_free_raw_features_v1.py \
    --questions "${DATA}/questions_answer_free.json" \
    "${merge_args[@]}" \
    --output "${RAW}/raw_features_all.jsonl" \
    --audit "${RAW}/merge_audit.json" \
    --expected-count "${EXPECTED}" \
    > "${RUN}/logs/merge_raw_features.log" 2>&1
  "${PY}" evaluation/tools/build_avfunnel8_manifest_v1.py \
    --questions "${DATA}/questions_answer_free.json" \
    --raw-features "${RAW}/raw_features_all.jsonl" \
    --output "${AV}/av_funnel_supplement2526.jsonl" \
    --audit "${AV}/audit.json" \
    > "${RUN}/logs/build_av_manifest.log" 2>&1
  mark AV_FEATURES_COMPLETE
fi

run_selected_wave \
  mmr8 CLIPMMR64_8_lambda070 "${SELECTED}/mmr8.jsonl" \
  "${MMR}" MMR8_COMPLETE
run_uniform_wave uniform8 "${UNIFORM}" UNIFORM8_COMPLETE
run_selected_wave \
  cliptopk8 CleanQwen3_CLIPTopK8 "${SELECTED}/clip_topk8.jsonl" \
  "${CLIP}" CLIPTOPK8_COMPLETE

if [[ ! -e "${RUN}/A0_VERIFIER_COMPLETE" ]]; then
  if [[ ! -e "${A0_POOL}/audit.json" ]]; then
    "${PY}" evaluation/tools/build_qwen3_mmr_a0_verifier_pool_fresh499_v1.py \
      --questions "${DATA}/questions_answer_free.json" \
      --mmr-root "${MMR}" \
      --video-root data/videos \
      --output-dir "${A0_POOL}" \
      --expected-count "${EXPECTED}" \
      --expected-videos "${VIDEOS}" \
      > "${RUN}/logs/build_a0_pool.log" 2>&1
  fi
  wait_all_idle a0_verifier
  verifier_pids=()
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    nohup "${PY}" \
      evaluation/tools/score_answer_claims_qwen3_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --adapter-dir "${ADAPTER}" \
      --input-jsonl "${A0_POOL}/shards/fold_${fold}.jsonl" \
      --output-dir "${A0_SHARDS}/fold_${fold}" \
      --views 8 \
      --unified-size 448 \
      --max-visual-tokens 4096 \
      > "${RUN}/logs/a0_verifier_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/a0_verifier_fold_${fold}.pid"
    verifier_pids+=("${pid}")
  done
  wait_jobs a0_verifier "${verifier_pids[@]}"
  "${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_supplement_v1.py \
    --pool-dir "${A0_POOL}" \
    --scores-root "${A0_SHARDS}" \
    --output-dir "${A0_MERGED}" \
    --expected-count "${EXPECTED}" \
    --expected-videos "${VIDEOS}" \
    > "${RUN}/logs/merge_a0_verifier.log" 2>&1
  mark A0_VERIFIER_COMPLETE
fi

if [[ ! -e "${RUN}/THRESHOLD_DATASET_COMPLETE" ]]; then
  trigger_count="$("${PY}" - "${A0_MERGED}/scores_all.jsonl" "${TAU}" <<'PY'
import json
import sys
threshold = float(sys.argv[2])
print(sum(
    float(json.loads(line)["support_probability"]) < threshold
    for line in open(sys.argv[1], encoding="utf-8")
    if line.strip()
))
PY
  )"
  "${PY}" evaluation/tools/build_selective_evidence_rewrite_supplement_threshold_v1.py \
    --pool-dir "${A0_POOL}" \
    --scores "${A0_MERGED}/scores_all.jsonl" \
    --av-manifest "${AV}/av_funnel_supplement2526.jsonl" \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --asr-root "${DATA}/asr_union_records" \
    --output-dir "${TRIGGER}" \
    --expected-count "${EXPECTED}" \
    --trigger-count "${trigger_count}" \
    --support-threshold "${TAU}" \
    --runtime-folds 5 \
    > "${RUN}/logs/build_threshold_trigger.log" 2>&1
  "${PY}" evaluation/tools/build_qwen3_adaptive_crop_supplement_threshold_arms_v1.py \
    --input-jsonl "${TRIGGER}/items_answer_free.jsonl" \
    --output-root "${ARMS}" \
    --expected-count "${trigger_count}" \
    --runtime-folds 5 \
    --smoke-per-fold 2 \
    > "${RUN}/logs/build_adaptive_arms.log" 2>&1
  echo "${trigger_count}" > "${RUN}/TRIGGER_COUNT"
  mark THRESHOLD_DATASET_COMPLETE
fi

if [[ ! -e "${RUN}/ADAPTIVE_SCALE_COMPLETE" ]]; then
  wait_all_idle adaptive_scale
  adaptive_pids=()
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    shard="${ARMS}/full_triggered/adaptive_scale/shards/fold_${fold}.jsonl"
    expected="$(wc -l < "${shard}" | tr -d ' ')"
    nohup "${PY}" \
      evaluation/tools/infer_qwen3_adaptive_crop_threshold_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --input-jsonl "${shard}" \
      --output-dir "${ADAPTIVE}/fold_${fold}" \
      --base-size 512 \
      --crop-size 896 \
      --max-visual-tokens 4096 \
      --max-new-tokens 192 \
      --expected-items "${expected}" \
      --a2-method Qwen3_adaptive_scale_AVEvidenceRewrite12_A2 \
      --skip-a1 \
      --resume-existing \
      > "${RUN}/logs/adaptive_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/adaptive_fold_${fold}.pid"
    adaptive_pids+=("${pid}")
  done
  wait_jobs adaptive_scale "${adaptive_pids[@]}"
  trigger_count="$(cat "${RUN}/TRIGGER_COUNT")"
  "${PY}" evaluation/tools/audit_threshold_supplement_adaptive_a2_v1.py \
    --dataset-root "${ARMS}" \
    --run-root "${ADAPTIVE}" \
    --expected-count "${trigger_count}" \
    --runtime-folds 5 \
    --output-dir "${ADAPTIVE_AUDIT}" \
    > "${RUN}/logs/audit_adaptive.log" 2>&1
  mark ADAPTIVE_SCALE_COMPLETE
fi

if [[ ! -e "${RUN}/FINAL_CANDIDATES_COMPLETE" ]]; then
  "${PY}" evaluation/tools/materialize_adsqa_supplement2526_candidates_v1.py \
    --questions "${DATA}/questions_answer_free.json" \
    --uniform-root "${UNIFORM}" \
    --uniform-audit-root "${UNIFORM}/audits" \
    --clip-root "${CLIP}" \
    --clip-audit-root "${CLIP}/audits" \
    --mmr-root "${MMR}" \
    --mmr-audit-root "${MMR}/audits" \
    --trigger-dataset "${TRIGGER}" \
    --adaptive-root "${ADAPTIVE}" \
    --crop-audit "${ADAPTIVE_AUDIT}/audit.json" \
    --output-dir "${FINAL}" \
    > "${RUN}/logs/materialize_candidates.log" 2>&1
  mark FINAL_CANDIDATES_COMPLETE
fi

sha256sum \
  "${PREP}/preflight.json" \
  "${ASR}/audit.json" \
  "${DATA}/manifest.json" \
  "${SELECTED}/audit.json" \
  "${RAW}/merge_audit.json" \
  "${AV}/audit.json" \
  "${A0_POOL}/audit.json" \
  "${A0_MERGED}/summary.json" \
  "${TRIGGER}/audit.json" \
  "${ARMS}/dataset_audit.json" \
  "${ADAPTIVE_AUDIT}/audit.json" \
  "${FINAL}/protocol_audit.json" \
  > "${RUN}/INFERENCE_SHA256SUMS"
snapshot_gpus pipeline_complete
mark INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION
rm -f "${RUN}/PIPELINE_FAILED"
