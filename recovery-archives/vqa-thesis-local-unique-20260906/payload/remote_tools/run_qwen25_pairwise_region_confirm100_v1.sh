#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
root=evaluation/runs/qwen25_active_evidence_look_v1/pairwise_region_confirm100_v1
model=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
input="$root/inputs/changed49.jsonl"
py=/data1/rmx/ana3/envs/ReadR/bin/python

$py evaluation/tools/build_qwen25_pairwise_region_confirm100_v1.py

run_arm() {
  local gpu=$1 order=$2
  CUDA_VISIBLE_DEVICES="$gpu" $py evaluation/tools/infer_qwen25_evidence_regenerate_v2.py \
    --gpu-id "$gpu" --model-dir "$model" --input-jsonl "$input" \
    --output-dir "$root/inference/$order" --expected-items 49 \
    --base-size 512 --crop-size 896 --max-visual-tokens 4096 --max-new-tokens 16 \
    --a2-method "ReAdR_PairwiseRegion_${order}" --ablation-variant region_regenerate \
    --pairwise-order "$order" --skip-a1
}

mkdir -p "$root/logs" "$root/pids"
run_arm 0 a0_first >"$root/logs/a0_first.log" 2>&1 & p0=$!
run_arm 1 a2_first >"$root/logs/a2_first.log" 2>&1 & p1=$!
printf '%s\n' "$p0" >"$root/pids/a0_first.pid"
printf '%s\n' "$p1" >"$root/pids/a2_first.pid"
wait "$p0"; wait "$p1"
touch "$root/PAIRWISE_INFERENCE_COMPLETE"
