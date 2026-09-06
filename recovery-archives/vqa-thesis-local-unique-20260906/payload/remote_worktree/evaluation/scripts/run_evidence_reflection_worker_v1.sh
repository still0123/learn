#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
GPU_ID="${GPU_ID:?set GPU_ID to a permitted idle GPU}"
VARIANT="${VARIANT:?set VARIANT to generic, structured, or conservative}"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_evidence_reflection_dev100_v1"
DATA_DIR="$PROJECT_ROOT/data/counterfactual_dev100_v1"
FREE_MAX_MIB="${FREE_MAX_MIB:-1024}"

case "$GPU_ID" in 1|4) ;; *) echo "This stage allows only GPU 1 or 4" >&2; exit 2 ;; esac
case "$VARIANT" in generic|structured|conservative) ;; *) echo "invalid VARIANT" >&2; exit 2 ;; esac
used_mib="$(nvidia-smi --id="$GPU_ID" --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
if (( used_mib > FREE_MAX_MIB )); then
  echo "GPU $GPU_ID is not idle: ${used_mib} MiB used" >&2
  exit 3
fi

FREEZE="$RUN_ROOT/frozen_dev100_manifest_v1.json"
if [[ ! -s "$FREEZE" ]]; then
  "$PYTHON" "$PROJECT_ROOT/evaluation/tools/freeze_evidence_reflection_dev100_v1.py" \
    --question-file "$DATA_DIR/question.json" \
    --raw-root "$PROJECT_ROOT/evaluation/runs/innovation2_counterfactual_dev100_v1/raw_uniform" \
    --output "$FREEZE"
fi

OUT_DIR="$RUN_ROOT/$VARIANT"
mkdir -p "$OUT_DIR/source_snapshot"
cp "$0" "$PROJECT_ROOT/evaluation/methods/evidence_reflection/inference_evidence_reflection_v1.py" \
  "$PROJECT_ROOT/evaluation/methods/evidence_reflection/reflection_protocol.py" \
  "$PROJECT_ROOT/evaluation/methods/fair_protocol/inference_fair_baselines_v1.py" \
  "$OUT_DIR/source_snapshot/"

overwrite_args=()
if [[ "${OVERWRITE:-0}" == "1" ]]; then overwrite_args+=(--overwrite); fi
range_args=(--start-idx "${START_IDX:-0}" --end-idx "${END_IDX:--1}" --shard-id "${SHARD_ID:-0}" --num-shards "${NUM_SHARDS:-1}")

exec "$PYTHON" "$PROJECT_ROOT/evaluation/methods/evidence_reflection/inference_evidence_reflection_v1.py" \
  --gpu-id "$GPU_ID" \
  --variant "$VARIANT" \
  --question-file "$DATA_DIR/question.json" \
  --asr-file "$PROJECT_ROOT/evaluation/asr_set.json" \
  --freeze-manifest "$FREEZE" \
  --output-dir "$OUT_DIR" \
  --model-dir /data1/qky/Model/Qwen3Vl-8B \
  --project-root "$PROJECT_ROOT" \
  --video-root "$PROJECT_ROOT/data/videos" \
  --frames-fallback-root "$PROJECT_ROOT/data/frames_8" \
  --max-new-tokens 768 \
  "${range_args[@]}" \
  "${overwrite_args[@]}"
