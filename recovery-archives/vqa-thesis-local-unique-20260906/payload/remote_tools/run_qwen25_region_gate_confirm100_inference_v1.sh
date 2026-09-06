#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
BASE=evaluation/runs/qwen25_active_evidence_look_v1/confirm100_v1
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/region_gate_confirm100_v1
mkdir -p "$ROOT/logs" "$ROOT/pids"

$PY evaluation/tools/build_qwen25_region_gate_confirm100_inputs_v1.py \
  --source "$BASE/inputs/active_region.jsonl" --output-root "$ROOT/inputs"

run_shard() {
  local gpu="$1" shard="$2" count="$3"
  $PY evaluation/tools/infer_qwen25_evidence_regenerate_v2.py \
    --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$ROOT/inputs/shard${shard}.jsonl" \
    --output-dir "$ROOT/inference/shard${shard}" --expected-items "$count" --skip-a1 \
    --a2-method ReAdR_ActiveRegion_Regenerate_A2 \
    --ablation-variant region_regenerate --max-new-tokens 128 \
    > "$ROOT/logs/shard${shard}.log" 2>&1
}

run_shard 0 0 27 & p0=$!; echo "$p0" > "$ROOT/pids/shard0.pid"
run_shard 1 1 26 & p1=$!; echo "$p1" > "$ROOT/pids/shard1.pid"
wait "$p0" "$p1"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT/INFERENCE_COMPLETE"
