#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 5 ]]; then
  echo "usage: $0 GPU_ID SHARD_ID NUM_SHARDS INPUT_DIR OUTPUT_DIR" >&2
  exit 2
fi

GPU_ID="$1"
SHARD_ID="$2"
NUM_SHARDS="$3"
INPUT_DIR="$4"
OUTPUT_DIR="$5"
ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_joint_confirm1000_v1"
PREP="${RUN}/prepared_answer_free_v1"

mkdir -p "${OUTPUT_DIR}"
cd "${ROOT}"

mapfile -t files < <(find "${INPUT_DIR}" -maxdepth 1 -type f -name "*.json" | sort)
for ((index=SHARD_ID; index<${#files[@]}; index+=NUM_SHARDS)); do
  input="${files[index]}"
  stem="$(basename "${input}" .json)"
  output="${OUTPUT_DIR}/${stem}.jsonl"
  if [[ -f "${output}" && "$(wc -l < "${output}")" -eq 1 ]]; then
    continue
  fi
  "${PY}" evaluation/tools/build_diverse_local8_manifest_decode_recovery_v1.py \
    --gpu-id "${GPU_ID}" \
    --questions "${input}" \
    --segmented-asr-root "${PREP}/asr_union_records" \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --clip-path models/clip-vit-large-patch14 \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output "${output}"
done
