#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$ROOT/evaluation/runs/innovation1_qwen25_clipcrop_freshq500_v1"
QUESTIONS="$ROOT/data/freshq_confirm500_qwen25_clipcrop_v2/question.json"
GROUNDTRUTH="$ROOT/data/freshq_confirm500_qwen25_clipcrop_v2/groundtruth.json"
SELECTION_AUDIT="$ROOT/data/freshq_confirm500_qwen25_clipcrop_v2/audit.json"
GATE="$RUN_ROOT/manifests/clipcrop40_manifest_v1.jsonl"
PROTOCOL="$RUN_ROOT/protocol"
SMOKE="$RUN_ROOT/smoke10"
FORMAL="$RUN_ROOT/formal"
JUDGE="$RUN_ROOT/judge_deepseek_answer_only_v1"
LEGACY_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"

cd "$ROOT"

"$PYTHON" evaluation/tools/prepare_fresh_confirm500_protocol_v1.py \
  --questions "$QUESTIONS" \
  --gate-manifest "$GATE" \
  --output-dir "$PROTOCOL"

"$PYTHON" evaluation/tools/run_qwen25_fresh_confirm500_v1.py \
  --gpu-id 4 \
  --fold 0 \
  --method B_Raw40 \
  --question-file "$PROTOCOL/smoke10_question.json" \
  --output-dir "$SMOKE/B_Raw40"

"$PYTHON" evaluation/tools/run_qwen25_fresh_confirm500_v1.py \
  --gpu-id 4 \
  --fold 0 \
  --method D_Gated_CLIPCrop8 \
  --question-file "$PROTOCOL/smoke10_question.json" \
  --gate-manifest "$PROTOCOL/smoke10_gate_manifest.jsonl" \
  --output-dir "$SMOKE/D_CLIPCrop40"

"$PYTHON" evaluation/tools/audit_fresh_confirm500_qwen25_v1.py \
  --questions "$PROTOCOL/smoke10_question.json" \
  --selection-audit "$SELECTION_AUDIT" \
  --gate-manifest "$PROTOCOL/smoke10_gate_manifest.jsonl" \
  --raw-root "$SMOKE/B_Raw40" \
  --crop-root "$SMOKE/D_CLIPCrop40" \
  --expected-count 10 \
  --output "$SMOKE/protocol_audit_v1.json"
touch "$SMOKE/SMOKE_COMPLETE"

"$PYTHON" evaluation/tools/run_qwen25_fresh_confirm500_v1.py \
  --gpu-id 4 \
  --fold 0 \
  --method B_Raw40 \
  --question-file "$QUESTIONS" \
  --output-dir "$FORMAL/B_Raw40"

"$PYTHON" evaluation/tools/run_qwen25_fresh_confirm500_v1.py \
  --gpu-id 4 \
  --fold 0 \
  --method D_Gated_CLIPCrop8 \
  --question-file "$QUESTIONS" \
  --gate-manifest "$GATE" \
  --output-dir "$FORMAL/D_CLIPCrop40"

"$PYTHON" evaluation/tools/audit_fresh_confirm500_qwen25_v1.py \
  --questions "$QUESTIONS" \
  --selection-audit "$SELECTION_AUDIT" \
  --gate-manifest "$GATE" \
  --raw-root "$FORMAL/B_Raw40" \
  --crop-root "$FORMAL/D_CLIPCrop40" \
  --expected-count 500 \
  --output "$FORMAL/protocol_audit_v1.json"
touch "$FORMAL/FORMAL_INFERENCE_COMPLETE"

"$PYTHON" evaluation/tools/judge_qwen25_clipcrop_freshq500_v1.py \
  --groundtruth "$GROUNDTRUTH" \
  --protocol-audit "$FORMAL/protocol_audit_v1.json" \
  --raw-root "$FORMAL/B_Raw40" \
  --crop-root "$FORMAL/D_CLIPCrop40" \
  --legacy-evaluator "$LEGACY_EVALUATOR" \
  --output-root "$JUDGE" \
  --workers 10 \
  --dry-run

"$PYTHON" evaluation/tools/judge_qwen25_clipcrop_freshq500_v1.py \
  --groundtruth "$GROUNDTRUTH" \
  --protocol-audit "$FORMAL/protocol_audit_v1.json" \
  --raw-root "$FORMAL/B_Raw40" \
  --crop-root "$FORMAL/D_CLIPCrop40" \
  --legacy-evaluator "$LEGACY_EVALUATOR" \
  --output-root "$JUDGE" \
  --workers 10

"$PYTHON" evaluation/tools/analyze_qwen25_clipcrop_freshq500_v1.py \
  --judge-results "$JUDGE/results.jsonl" \
  --groundtruth "$GROUNDTRUTH" \
  --protocol-audit "$FORMAL/protocol_audit_v1.json" \
  --output-dir "$JUDGE/analysis_v1" \
  --samples 10000 \
  --seed 42
touch "$RUN_ROOT/FRESHQ500_COMPLETE"
