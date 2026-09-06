#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
RAW="${RUN}/raw_features_v1"
AV="${RUN}/av_manifest_v1"
GPUS=(2 3 4 5)

mark() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/$1"
}

assert_idle() {
  local gpu="$1"
  local active
  active="$(nvidia-smi --id="${gpu}" \
    --query-compute-apps=pid,process_name,used_memory \
    --format=csv,noheader,nounits)"
  if [[ -n "${active}" ]]; then
    echo "GPU${gpu} is not idle: ${active}" >&2
    return 1
  fi
}

cd "${ROOT}"
mkdir -p "${RAW}" "${AV}" "${RUN}/logs" "${RUN}/pids" \
  "${RUN}/source_snapshot"
if [[ -e "${RUN}/PRECOMPUTE_LAUNCHED" ]]; then
  echo "refusing duplicate full5320 precompute launch" >&2
  exit 1
fi
"${PY}" - "${DATA}/audit.json" <<'PY'
import json
import sys
audit = json.load(open(sys.argv[1], encoding="utf-8"))
if audit.get("passed") is not True or int(audit.get("question_count", -1)) != 5320:
    raise SystemExit("full5320 data audit failed")
PY

cp evaluation/tools/build_diverse_local8_manifest_full_decode_recovery_v1.py \
  "${RUN}/source_snapshot/"
cp evaluation/tools/build_diverse_local8_manifest_v1.py \
  "${RUN}/source_snapshot/"
cp evaluation/tools/merge_answer_free_raw_features_v1.py \
  "${RUN}/source_snapshot/"
cp evaluation/tools/build_avfunnel8_manifest_v1.py \
  "${RUN}/source_snapshot/"
echo "$$" > "${RUN}/pids/precompute.pid"
mark PRECOMPUTE_LAUNCHED
trap 'mark PRECOMPUTE_FAILED' ERR

pids=()
for fold in 0 1 2 3; do
  gpu="${GPUS[$fold]}"
  assert_idle "${gpu}"
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
    > "${RUN}/logs/raw_features_${fold}.log" 2>&1 < /dev/null &
  pids+=("$!")
  echo "$!" > "${RUN}/pids/raw_features_${fold}.pid"
done
for pid in "${pids[@]}"; do
  wait "${pid}"
done

assert_idle 2
"${PY}" evaluation/tools/build_diverse_local8_manifest_full_decode_recovery_v1.py \
  --gpu-id 2 \
  --questions "${DATA}/shards/fold_4.json" \
  --segmented-asr-root "${DATA}/asr_union_records" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --clip-path models/clip-vit-large-patch14 \
  --video-root data/videos \
  --frames-fallback-root data/frames_8 \
  --output "${RAW}/shard_4.jsonl" \
  > "${RUN}/logs/raw_features_4.log" 2>&1

"${PY}" evaluation/tools/merge_answer_free_raw_features_v1.py \
  --questions "${DATA}/questions_answer_free.json" \
  --input "${RAW}/shard_0.jsonl" \
  --input "${RAW}/shard_1.jsonl" \
  --input "${RAW}/shard_2.jsonl" \
  --input "${RAW}/shard_3.jsonl" \
  --input "${RAW}/shard_4.jsonl" \
  --output "${RAW}/raw_features_all.jsonl" \
  --audit "${RAW}/merge_audit.json" \
  --expected-count 5320 \
  > "${RUN}/logs/merge_raw_features.log" 2>&1

"${PY}" evaluation/tools/build_avfunnel8_manifest_v1.py \
  --questions "${DATA}/questions_answer_free.json" \
  --raw-features "${RAW}/raw_features_all.jsonl" \
  --output "${AV}/av_funnel_full5320.jsonl" \
  --audit "${AV}/audit.json" \
  > "${RUN}/logs/build_av_manifest.log" 2>&1

mark EVIDENCE_MANIFESTS_COMPLETE
