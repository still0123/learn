#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/confirm100_v1
mkdir -p "$ROOT/logs" "$ROOT/pids" "$ROOT/inference"

run_arm() {
  local gpu=$1 input=$2 output=$3 count=$4 variant=$5 method=$6
  "$PY" evaluation/tools/infer_qwen25_evidence_minimal_edit_v2.py \
    --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$ROOT/inputs/$input.jsonl" \
    --output-dir "$ROOT/inference/$output" --expected-items "$count" \
    --a2-method "$method" --ablation-variant "$variant" --skip-a1 --max-new-tokens 192
}

test ! -e "$ROOT/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
test ! -e "$ROOT/PIPELINE_FAILED"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT/PIPELINE_FAILED"' ERR

run_arm 0 full_only full_only 79 full_only_minimal_edit ReAdR_FullOnly_MinimalEdit_A2 \
  > "$ROOT/logs/full_only.log" 2>&1 & p0=$!
echo "$p0" > "$ROOT/pids/full_only.pid"

run_arm 1 active_region active_region 53 minimal_edit ReAdR_ActiveRegion_MinimalEdit_A2 \
  > "$ROOT/logs/active_region.log" 2>&1 & p1=$!
echo "$p1" > "$ROOT/pids/active_region.pid"

(
  run_arm 4 active_time active_time 26 full_only_minimal_edit ReAdR_ActiveTime_MinimalEdit_A2 \
    > "$ROOT/logs/active_time.log" 2>&1
  run_arm 4 random_region random_region 34 minimal_edit ReAdR_RandomRegion_MinimalEdit_A2 \
    > "$ROOT/logs/random_region.log" 2>&1
) & p4=$!
echo "$p4" > "$ROOT/pids/gpu4_relay.pid"

run_arm 5 random_time random_time 45 full_only_minimal_edit ReAdR_RandomTime_MinimalEdit_A2 \
  > "$ROOT/logs/random_time.log" 2>&1 & p5=$!
echo "$p5" > "$ROOT/pids/random_time.pid"

wait "$p0" "$p1" "$p4" "$p5"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
