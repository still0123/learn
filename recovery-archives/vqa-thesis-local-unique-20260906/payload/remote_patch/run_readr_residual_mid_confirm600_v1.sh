#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main

ROOT=evaluation/runs/readr_increment_confirm600_v1/residual_mid_confirm600_v1
DATASET="$ROOT/dataset_v1"
PY=/data1/rmx/ana3/envs/ReadR/bin/python
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
Q3MODEL=/data1/qky/Model/Qwen3Vl-8B
ADAPTER=evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter
BUILD=evaluation/tools/build_readr_residual_mid_confirm600_v1.py
INFER=evaluation/tools/infer_readr_residual_avfunnel_decode_recovery_v1.py
BUILDV=evaluation/tools/build_readr_residual_mid_confirm600_verifier_inputs_v1.py
SCORE=evaluation/tools/score_answer_claims_qwen3_v1.py
MERGE=evaluation/tools/merge_readr_residual_mid_confirm600_scores_v1.py
GATE=evaluation/tools/analyze_readr_residual_mid_confirm600_gate_v1.py
SOURCE=evaluation/runs/readr_increment_confirm600_v1/frozen_triggered_candidates/items_answer_free.jsonl
RAW1=evaluation/runs/qwen3_full_valid5320_v1/raw_features_v1/raw_features_all.jsonl
RAW2=evaluation/runs/qwen3_adsqa_supplement2526_v1/raw_features_v1/raw_features_all.jsonl

mkdir -p "$ROOT/logs" "$ROOT/pids"
exec > >(tee -a "$ROOT/logs/pipeline.log") 2>&1
echo "$(date -Is) confirm600_residual_start"

if [[ ! -f "$DATASET/dataset_audit.json" ]]; then
  if [[ -e "$DATASET" ]]; then echo "incomplete dataset exists; preserve and stop" >&2; exit 1; fi
  "$PY" "$BUILD" --source-items "$SOURCE" --raw-features "$RAW1" --raw-features "$RAW2" --output-root "$DATASET"
fi

run_inference_batch() {
  local first="$1" second="$2" stage="$3"
  local pids=()
  local folds=("$first")
  [[ "$second" != "$first" ]] && folds+=("$second")
  for fold in "${folds[@]}"; do
    local inp="$DATASET/shards/fold_${fold}.jsonl" out="$ROOT/inference/fold_${fold}" expected
    expected=$(wc -l < "$inp" | tr -d ' ')
    [[ "$expected" -gt 0 ]] || continue
    if [[ -f "$out/run_summary.json" ]]; then continue; fi
    if [[ -e "$out" ]] && [[ $(find "$out" -mindepth 1 -maxdepth 1 | wc -l) -gt 0 ]]; then echo "incomplete output exists: $out" >&2; exit 1; fi
    mkdir -p "$out"
    gpu=$((fold==first ? 0 : 5))
    ADSQA_DECODE_RECOVERY_ROOT="$ROOT/decode_recovery_v1" nohup "$PY" "$INFER" --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$inp" --output-dir "$out" --base-size 512 --crop-size 896 --max-visual-tokens 4096 --max-new-tokens 192 --expected-items "$expected" --a2-method ReAdR_ResidualMid12_A2 --ablation-variant residual_mid --skip-a1 >"$ROOT/logs/${stage}_fold${fold}.log" 2>&1 &
    pid=$!; echo "$pid" > "$ROOT/pids/${stage}_fold${fold}.pid"; pids+=("$pid")
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
}

run_inference_batch 0 1 infer_a
run_inference_batch 2 3 infer_b
run_inference_batch 4 4 infer_c
touch "$ROOT/INFERENCE_COMPLETE"

if [[ ! -f "$ROOT/verifier_inputs/audit.json" ]]; then
  "$PY" "$BUILDV" --dataset-dir "$DATASET" --inference-root "$ROOT/inference" --output-dir "$ROOT/verifier_inputs"
fi

run_score_batch() {
  local first="$1" second="$2" stage="$3"; local pids=()
  local folds=("$first")
  [[ "$second" != "$first" ]] && folds+=("$second")
  for fold in "${folds[@]}"; do
    local inp="$ROOT/verifier_inputs/shards/fold_${fold}.jsonl" out="$ROOT/verifier_shards/fold_${fold}" expected
    expected=$(wc -l < "$inp" | tr -d ' '); [[ "$expected" -gt 0 ]] || continue
    if [[ -f "$out/summary.json" ]]; then continue; fi
    if [[ -e "$out" ]] && [[ $(find "$out" -mindepth 1 -maxdepth 1 | wc -l) -gt 0 ]]; then echo "incomplete score output exists: $out" >&2; exit 1; fi
    mkdir -p "$out"
    gpu=$((fold==first ? 0 : 5))
    nohup "$PY" "$SCORE" --gpu-id "$gpu" --model-dir "$Q3MODEL" --adapter-dir "$ADAPTER" --input-jsonl "$inp" --output-dir "$out" --views 8 --unified-size 448 --max-visual-tokens 4096 >"$ROOT/logs/${stage}_fold${fold}.log" 2>&1 &
    pid=$!; echo "$pid" > "$ROOT/pids/${stage}_fold${fold}.pid"; pids+=("$pid")
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
}

run_score_batch 0 1 score_a
run_score_batch 2 3 score_b
run_score_batch 4 4 score_c
"$PY" "$MERGE" --shard-root "$ROOT/verifier_shards" --output-dir "$ROOT/verifier_merged"
"$PY" "$GATE"
touch "$ROOT/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
echo "$(date -Is) INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
