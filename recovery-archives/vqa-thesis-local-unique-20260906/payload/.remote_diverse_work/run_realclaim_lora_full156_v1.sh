#!/usr/bin/env bash
set -euo pipefail

ROOT=/data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
RUN_ROOT="$ROOT/evaluation/runs/innovation2_realclaim_lora_verifier_v1/full156"
INPUT="$ROOT/evaluation/runs/innovation2_claim_support_conflict_v23/full_pairs_train/input.jsonl"
LABELS="$ROOT/evaluation/runs/innovation2_claim_support_conflict_v23/full_pairs_train/labels.jsonl"
MODEL=/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct
SCRIPT="$ROOT/evaluation/tools/train_realclaim_lora_verifier_v1.py"

mkdir -p "$RUN_ROOT"

launch() {
  local gpu="$1" mode="$2"
  local out="$RUN_ROOT/$mode"
  mkdir -p "$out"
  nohup "$PY" "$SCRIPT" \
    --gpu-id "$gpu" \
    --model-dir "$MODEL" \
    --input-jsonl "$INPUT" \
    --labels-jsonl "$LABELS" \
    --output-dir "$out" \
    --mode "$mode" \
    --max-pairs 156 \
    --epochs 2 \
    --views 8 \
    --overwrite \
    >"$out/launcher.log" 2>&1 < /dev/null &
  echo "$!" >"$out/pid"
}

launch 1 classification
launch 2 pairwise
printf 'classification_pid=%s pairwise_pid=%s\n' \
  "$(cat "$RUN_ROOT/classification/pid")" "$(cat "$RUN_ROOT/pairwise/pid")"
