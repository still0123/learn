#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
BASE=evaluation/runs/qwen25_active_evidence_look_v1/confirm100_v1
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/temporal_difference_smoke20_v1
mkdir -p "$ROOT"
test ! -e "$ROOT/DIFFERENCE_SMOKE_COMPLETE"

$PY evaluation/tools/build_qwen25_temporal_difference_smoke20_v1.py \
  --source "$BASE/inputs/active_time.jsonl" --output-root "$ROOT"
$PY evaluation/tools/infer_qwen25_evidence_minimal_edit_v3.py \
  --gpu-id 0 --model-dir "$MODEL" --input-jsonl "$ROOT/inputs.jsonl" \
  --output-dir "$ROOT/inference" --expected-items 20 --skip-a1 \
  --a2-method ReAdR_ActiveTemporalNeighbor_MinimalEdit_A2 \
  --ablation-variant temporal_neighbor_minimal_edit --max-new-tokens 192
$PY evaluation/tools/audit_qwen25_temporal_difference_smoke20_v1.py \
  --root "$ROOT" --old-root "$BASE/inference/active_time"
