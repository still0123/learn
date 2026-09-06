#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_joint_confirm1000_v1"
PREP="${RUN}/prepared_answer_free_v1"
RAW="${RUN}/raw_features_v1"
SPLIT="${RUN}/decode_recovery_v1/shard3_split"
AFTER_SPLIT="${SPLIT}/after_split"
SINGLETON_INPUTS="${AFTER_SPLIT}/singleton_inputs"
SINGLETON_OUTPUTS="${AFTER_SPLIT}/singleton_outputs"

assert_idle() {
  local gpu="$1"
  local active
  active="$(nvidia-smi --id="${gpu}" --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits)"
  if [[ -n "${active}" ]]; then
    echo "GPU${gpu} is not idle: ${active}" >&2
    return 1
  fi
}

wait_all() {
  local status=0
  local pid
  for pid in "$@"; do
    if ! wait "${pid}"; then
      status=1
    fi
  done
  return "${status}"
}

cd "${ROOT}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot" "${SPLIT}"
cp evaluation/tools/split_answer_free_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/split_answer_free_singletons_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/merge_answer_free_raw_feature_singletons_v1.py "${RUN}/source_snapshot/"
cp evaluation/scripts/run_raw_feature_singleton_worker_v1.sh "${RUN}/source_snapshot/"
cp evaluation/scripts/run_confirm1000_decode_recovery_split_v1.sh "${RUN}/source_snapshot/"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/DECODE_SPLIT_RECOVERY_FAILED"' ERR

if [[ ! -f "${SPLIT}/audit.json" ]]; then
  "${PY}" evaluation/tools/split_answer_free_decode_recovery_v1.py \
    --input "${PREP}/raw_feature_shards/shard_3.json" \
    --video-id 603f96f94cbcf891d8db244c11555214 \
    --output-dir "${SPLIT}" \
    > "${RUN}/logs/split_decode_recovery.log" 2>&1
fi
if [[ ! -f "${AFTER_SPLIT}/audit.json" ]]; then
  "${PY}" evaluation/tools/split_answer_free_decode_recovery_v1.py \
    --input "${SPLIT}/after.json" \
    --video-id 60d442c42fde20512ca8c0f02ce7123d \
    --output-dir "${AFTER_SPLIT}" \
    > "${RUN}/logs/split_decode_recovery_after.log" 2>&1
fi
if [[ ! -f "${AFTER_SPLIT}/singleton_split_audit.json" ]]; then
  "${PY}" evaluation/tools/split_answer_free_singletons_v1.py \
    --input "${AFTER_SPLIT}/after.json" \
    --output-dir "${SINGLETON_INPUTS}" \
    > "${RUN}/logs/split_decode_recovery_singletons.log" 2>&1
fi

test ! -e "${RAW}/shard_3.jsonl"
pids=()
if [[ ! -f "${SPLIT}/before.jsonl" || "$(wc -l < "${SPLIT}/before.jsonl")" -ne 75 ]]; then
  assert_idle 1
  nohup "${PY}" evaluation/tools/build_diverse_local8_manifest_v1.py \
    --gpu-id 1 \
    --questions "${SPLIT}/before.json" \
    --segmented-asr-root "${PREP}/asr_union_records" \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --clip-path models/clip-vit-large-patch14 \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output "${SPLIT}/before.jsonl" \
    > "${RUN}/logs/raw_features_3_before.log" 2>&1 &
  pids+=("$!")
  echo "${pids[-1]}" > "${RUN}/pids/decode_split_before.pid"
fi

if [[ ! -f "${SPLIT}/recovery.jsonl" || "$(wc -l < "${SPLIT}/recovery.jsonl")" -ne 1 ]]; then
  assert_idle 2
  nohup "${PY}" evaluation/tools/build_diverse_local8_manifest_decode_recovery_v1.py \
    --gpu-id 2 \
    --questions "${SPLIT}/recovery.json" \
    --segmented-asr-root "${PREP}/asr_union_records" \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --clip-path models/clip-vit-large-patch14 \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output "${SPLIT}/recovery.jsonl" \
    > "${RUN}/logs/raw_features_3_single_recovery.log" 2>&1 &
  pids+=("$!")
  echo "${pids[-1]}" > "${RUN}/pids/decode_split_recovery.pid"
fi

if [[ ! -f "${AFTER_SPLIT}/recovery.jsonl" || "$(wc -l < "${AFTER_SPLIT}/recovery.jsonl")" -ne 1 ]]; then
  assert_idle 2
  nohup "${PY}" evaluation/tools/build_diverse_local8_manifest_decode_recovery_v1.py \
    --gpu-id 2 \
    --questions "${AFTER_SPLIT}/recovery.json" \
    --segmented-asr-root "${PREP}/asr_union_records" \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --clip-path models/clip-vit-large-patch14 \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output "${AFTER_SPLIT}/recovery.jsonl" \
    > "${RUN}/logs/raw_features_3_second_recovery.log" 2>&1 &
  pids+=("$!")
  echo "${pids[-1]}" > "${RUN}/pids/decode_split_second_recovery.pid"
fi

if [[ ! -f "${AFTER_SPLIT}/after.jsonl" || "$(wc -l < "${AFTER_SPLIT}/after.jsonl")" -ne 123 ]]; then
  worker_gpus=(1 2 4 5)
  for worker in 0 1 2 3; do
    gpu="${worker_gpus[worker]}"
    assert_idle "${gpu}"
    nohup bash evaluation/scripts/run_raw_feature_singleton_worker_v1.sh \
      "${gpu}" "${worker}" 4 "${SINGLETON_INPUTS}" "${SINGLETON_OUTPUTS}" \
      > "${RUN}/logs/raw_features_3_singleton_worker_${worker}.log" 2>&1 &
    pids+=("$!")
    echo "${pids[-1]}" > "${RUN}/pids/decode_singleton_worker_${worker}.pid"
  done
fi

if [[ "${#pids[@]}" -gt 0 ]]; then
  wait_all "${pids[@]}"
fi

if [[ ! -f "${AFTER_SPLIT}/after.jsonl" ]]; then
  "${PY}" evaluation/tools/merge_answer_free_raw_feature_singletons_v1.py \
    --questions "${AFTER_SPLIT}/after.json" \
    --input-dir "${SINGLETON_OUTPUTS}" \
    --output "${AFTER_SPLIT}/after.jsonl" \
    --audit "${AFTER_SPLIT}/singleton_merge_audit.json" \
    --expected-count 123 \
    > "${RUN}/logs/merge_decode_recovery_singletons.log" 2>&1
fi

if [[ ! -f "${SPLIT}/after.jsonl" ]]; then
  "${PY}" evaluation/tools/merge_answer_free_raw_features_v1.py \
    --questions "${SPLIT}/after.json" \
    --input "${AFTER_SPLIT}/recovery.jsonl" \
    --input "${AFTER_SPLIT}/after.jsonl" \
    --output "${SPLIT}/after.jsonl" \
    --audit "${AFTER_SPLIT}/merge_audit.json" \
    --expected-count 124 \
    > "${RUN}/logs/merge_decode_recovery_after.log" 2>&1
fi

"${PY}" evaluation/tools/merge_answer_free_raw_features_v1.py \
  --questions "${PREP}/raw_feature_shards/shard_3.json" \
  --input "${SPLIT}/before.jsonl" \
  --input "${SPLIT}/recovery.jsonl" \
  --input "${SPLIT}/after.jsonl" \
  --output "${RAW}/shard_3.jsonl" \
  --audit "${SPLIT}/merge_audit.json" \
  --expected-count 200 \
  > "${RUN}/logs/merge_decode_recovery_shard3.log" 2>&1

test "$(wc -l < "${RAW}/shard_3.jsonl")" -eq 200
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/DECODE_SPLIT_RECOVERY_COMPLETE"

exec env RESUME_DECODE_RECOVERY=1 bash evaluation/scripts/run_qwen3_joint_confirm1000_v1.sh
