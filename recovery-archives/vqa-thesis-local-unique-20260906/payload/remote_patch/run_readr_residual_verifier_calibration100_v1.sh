#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main

ROOT=evaluation/runs/readr_residual_avfunnel_calibration100_v1
DATASET="$ROOT/dataset_v2"
PY=/data1/rmx/ana3/envs/ReadR/bin/python
BUILD=evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py
SCORE=evaluation/tools/score_answer_claims_qwen3_v1.py
MERGE=evaluation/tools/merge_selective_rewrite_a2_scores_v1.py
MODEL=/data1/qky/Model/Qwen3Vl-8B
ADAPTER=evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter

mkdir -p "$ROOT/verifier_logs" "$ROOT/verifier_pids"
exec > >(tee -a "$ROOT/verifier_logs/pipeline.log") 2>&1
echo "$(date -Is) verifier_start"

run_variant() {
  local variant="$1"
  local inputs="$ROOT/${variant}_verifier_inputs"
  local scores="$ROOT/${variant}_verifier_shards"
  local merged="$ROOT/${variant}_verifier_merged"
  if [[ ! -f "$inputs/audit.json" ]]; then
    "$PY" "$BUILD" \
      --dataset-dir "$DATASET/$variant" \
      --inference-root "$ROOT/shards/$variant" \
      --output-dir "$inputs" \
      --expected-count 100 --expected-videos 20 --expected-per-fold 20
  fi
  "$PY" - "$inputs/audit.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); assert a['passed'] and a['row_count']==100
assert a['groundtruth_read'] is False and a['judge_scores_read'] is False
PY
  mkdir -p "$scores"
  local fold=0
  local gpus=(0 5)
  while [[ "$fold" -lt 5 ]]; do
    local pids=()
    for gpu in "${gpus[@]}"; do
      [[ "$fold" -lt 5 ]] || break
      local inp="$inputs/shards/fold_${fold}.jsonl"
      local out="$scores/fold_${fold}"
      if [[ -f "$out/summary.json" ]]; then fold=$((fold+1)); continue; fi
      if [[ -e "$out" ]] && [[ $(find "$out" -mindepth 1 -maxdepth 1 | wc -l) -gt 0 ]]; then
        echo "incomplete verifier output exists: $out" >&2
        exit 1
      fi
      nohup "$PY" "$SCORE" --gpu-id "$gpu" --model-dir "$MODEL" --adapter-dir "$ADAPTER" \
        --input-jsonl "$inp" --output-dir "$out" --views 8 --unified-size 448 --max-visual-tokens 4096 \
        >"$ROOT/verifier_logs/${variant}_fold${fold}.log" 2>&1 &
      local pid=$!
      echo "$pid" > "$ROOT/verifier_pids/${variant}_fold${fold}.pid"
      pids+=("$pid")
      fold=$((fold+1))
    done
    for pid in "${pids[@]}"; do wait "$pid"; done
  done
  if [[ ! -f "$merged/summary.json" ]]; then
    "$PY" "$MERGE" --shard-root "$scores" --output-dir "$merged" --expected-count 100 --expected-per-fold 20
  fi
  test -f "$merged/summary.json"
  touch "$merged/PROTOCOL_AUDIT_COMPLETE"
}

run_variant residual_mid
run_variant residual_avfunnel
touch "$ROOT/VERIFIER_INFERENCE_COMPLETE"
echo "$(date -Is) VERIFIER_INFERENCE_COMPLETE"
