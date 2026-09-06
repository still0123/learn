#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/confirm60b_v1
MODEL=/data1/qky/Model/Qwen3Vl-8B
ADAPTER=evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter

$PY evaluation/tools/build_qwen25_active_confirm60b_verifier_inputs_v1.py \
  --root "$ROOT" \
  --items evaluation/runs/readr_increment_pilot300_v1/all_candidates_for_calibration/items_answer_free.jsonl \
  --output-root "$ROOT/verifier_inputs_v1"

$PY evaluation/tools/score_answer_claims_qwen3_v1.py \
  --gpu-id 0 --model-dir "$MODEL" --adapter-dir "$ADAPTER" \
  --input-jsonl "$ROOT/verifier_inputs_v1/model_inputs_all.jsonl" \
  --output-dir "$ROOT/verifier_scores_v1" --views 8 --unified-size 448 \
  --max-visual-tokens 4096 > "$ROOT/verifier.log" 2>&1

$PY evaluation/tools/evaluate_qwen25_active_confirm60b_gate_v1.py \
  --root "$ROOT" --candidate-scores "$ROOT/verifier_scores_v1/scores.jsonl" \
  --candidates "$ROOT/judge_preflight_v1/candidates_answer_free.jsonl" \
  --output-root "$ROOT/frozen_gate_v1"
