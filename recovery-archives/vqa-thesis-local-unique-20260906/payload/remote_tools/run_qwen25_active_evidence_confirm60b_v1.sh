#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/confirm60b_v1
mkdir -p "$ROOT/logs" "$ROOT/pids"
test ! -e "$ROOT/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"

$PY evaluation/tools/build_qwen25_active_evidence_confirm60b_v1.py \
  --items evaluation/runs/readr_increment_pilot300_v1/all_candidates_for_calibration/items_answer_free.jsonl \
  --logic-trees evaluation/runs/qwen25_active_evidence_look_v1/logic_trees_pilot300_v1/logic_trees.jsonl \
  --scores evaluation/runs/readr_increment_pilot300_v1/mmr8_verifier_merged/scores_all.jsonl \
  --smoke evaluation/runs/qwen25_active_evidence_look_v1/smoke20_reuse_v1/trajectories_answer_free.jsonl \
  --confirm100 evaluation/runs/qwen25_active_evidence_look_v1/confirm100_v1/confirm100_master_answer_free.jsonl \
  --output-root "$ROOT"

$PY evaluation/tools/infer_qwen25_evidence_regenerate_v2.py \
  --gpu-id 0 --model-dir "$MODEL" --input-jsonl "$ROOT/inputs/time.jsonl" \
  --output-dir "$ROOT/inference/time" --expected-items 13 --skip-a1 \
  --a2-method ReAdR_ActiveASRTemporal_Regenerate_A2 \
  --ablation-variant temporal_asr_regenerate --max-new-tokens 128 \
  > "$ROOT/logs/time.log" 2>&1 & p0=$!
echo "$p0" > "$ROOT/pids/time.pid"

$PY evaluation/tools/infer_qwen25_evidence_regenerate_v2.py \
  --gpu-id 1 --model-dir "$MODEL" --input-jsonl "$ROOT/inputs/region.jsonl" \
  --output-dir "$ROOT/inference/region" --expected-items 37 --skip-a1 \
  --a2-method ReAdR_ActiveRegion_Regenerate_A2 \
  --ablation-variant region_regenerate --max-new-tokens 128 \
  > "$ROOT/logs/region.log" 2>&1 & p1=$!
echo "$p1" > "$ROOT/pids/region.pid"

wait "$p0" "$p1"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
