#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_selected8_baselines_groupcv500_v1"
CACHE="${RUN}/videoitg_cache_top8"
MANIFEST="${RUN}/manifest/videoitg_top8_oof500.jsonl"
QUESTIONS="${ROOT}/evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/oof500_v1_audit/oof_questions_answer_free.json"

while [[ ! -f "${CACHE}/run_summary_shard0.json" || ! -f "${CACHE}/run_summary_shard1.json" ]]; do
  sleep 60
done

"${PY}" - "${CACHE}" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for shard in (0, 1):
    summary = json.load(open(root / f"run_summary_shard{shard}.json", encoding="utf-8"))
    if int(summary.get("requested_items", -1)) != 250:
        raise SystemExit(f"VideoITG shard {shard} requested count mismatch")
    if int(summary.get("failed_this_run", -1)) != 0:
        raise SystemExit(f"VideoITG shard {shard} contains failures")
    if int(summary.get("succeeded_this_run", 0)) + int(summary.get("skipped_existing", 0)) != 250:
        raise SystemExit(f"VideoITG shard {shard} is incomplete")
PY

"${PY}" "${ROOT}/evaluation/tools/merge_videoitg_top8_manifest_v1.py" \
  --questions "${QUESTIONS}" \
  --cache-shard "${CACHE}/cache_shard0.jsonl" \
  --cache-shard "${CACHE}/cache_shard1.jsonl" \
  --output "${MANIFEST}" \
  --audit "${RUN}/manifest/videoitg_top8_audit.json" \
  > "${RUN}/logs/videoitg_merge.log" 2>&1

while nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader \
  | grep -q .; do
  if ! nvidia-smi --id=1,2 --query-compute-apps=pid --format=csv,noheader \
    | grep -q '[0-9]'; then
    break
  fi
  sleep 10
done

for shard in 0 1; do
  gpu=$((shard + 1))
  out="${RUN}/full500/VideoITG8/shard${shard}"
  mkdir -p "${out}"
  nohup "${PY}" "${ROOT}/evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_v1.py" \
    --gpu-id "${gpu}" \
    --model-dir /data1/qky/Model/Qwen3Vl-8B \
    --method VideoITG8 \
    --question-file "${QUESTIONS}" \
    --selection-manifest "${MANIFEST}" \
    --asr-file "${ROOT}/evaluation/asr_set.json" \
    --video-root "${ROOT}/data/videos" \
    --frames-fallback-root "${ROOT}/data/frames_8" \
    --output-dir "${out}" \
    --views 8 \
    --unified-size 512 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256 \
    --shard-id "${shard}" \
    --num-shards 2 \
    > "${RUN}/logs/videoitg_qwen3_shard${shard}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/videoitg_qwen3_shard${shard}.pid"
done

wait

for shard in 0 1; do
  "${PY}" "${ROOT}/evaluation/tools/audit_adsqa_selected8_inference_v1.py" \
    --questions "${QUESTIONS}" \
    --selection-manifest "${MANIFEST}" \
    --inference-dir "${RUN}/full500/VideoITG8/shard${shard}" \
    --output "${RUN}/full500/VideoITG8/shard${shard}/protocol_audit.json" \
    --expected-count 250 \
    --shard-id "${shard}" \
    --num-shards 2 \
    > "${RUN}/logs/videoitg_audit_shard${shard}.log" 2>&1
done

touch "${RUN}/full500/VideoITG8/COMPLETE"
