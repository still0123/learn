#!/usr/bin/env bash
set -euo pipefail

ROOT=/data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
RUN="$ROOT/evaluation/runs/innovation2_realclaim_lora_verifier_v1"
DATA="$RUN/realclaim_hardneg_replay_v1/dataset"
OUT="$RUN/realclaim_hardneg_replay_v1"
MODEL=/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct

mkdir -p "$OUT/train" "$OUT/calibration240"
"$PY" "$ROOT/evaluation/tools/train_realclaim_weak_lora_v1.py" \
  --gpu-id 2 --model-dir "$MODEL" --inputs "$DATA/inputs.jsonl" --labels "$DATA/labels.jsonl" \
  --output-dir "$OUT/train" --max-rows 1165 --epochs 1 --views 8 --overwrite \
  >"$OUT/train/launcher.log" 2>&1
test -f "$OUT/train/complete.json"

"$PY" "$ROOT/evaluation/tools/evaluate_realclaim_lora_verifier_v1.py" \
  --gpu-id 2 --model-dir "$MODEL" --adapter-dir "$OUT/train/adapter" \
  --input-jsonl "$ROOT/evaluation/runs/innovation2_realclaim300_v2_corrected_frames/inference_inputs.jsonl" \
  --claims-jsonl "$ROOT/evaluation/runs/innovation2_realclaim300_v2_corrected_frames/claims.jsonl" \
  --split calibration --output-dir "$OUT/calibration240" --views 8 --overwrite \
  >"$OUT/calibration240/launcher.log" 2>&1
test -f "$OUT/calibration240/summary.json"
touch "$OUT/COMPLETE"
