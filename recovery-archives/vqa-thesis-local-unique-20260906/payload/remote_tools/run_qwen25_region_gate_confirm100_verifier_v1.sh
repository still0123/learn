#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
BASE=evaluation/runs/qwen25_active_evidence_look_v1/confirm100_v1
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/region_gate_confirm100_v1
MODEL=/data1/qky/Model/Qwen3Vl-8B
ADAPTER=evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter

$PY evaluation/tools/build_qwen25_region_gate_confirm100_verifier_inputs_v1.py \
  --base-root "$BASE" --run-root "$ROOT" --output-root "$ROOT/verifier_inputs_v1"

score() {
  local gpu="$1" shard="$2"
  $PY evaluation/tools/score_answer_claims_qwen3_v1.py \
    --gpu-id "$gpu" --model-dir "$MODEL" --adapter-dir "$ADAPTER" \
    --input-jsonl "$ROOT/verifier_inputs_v1/shard${shard}.jsonl" \
    --output-dir "$ROOT/verifier_scores_v1/shard${shard}" \
    --views 8 --unified-size 448 --max-visual-tokens 4096 \
    > "$ROOT/verifier_shard${shard}.log" 2>&1
}
score 0 0 & p0=$!
score 1 1 & p1=$!
wait "$p0" "$p1"
cat "$ROOT/verifier_scores_v1/shard0/scores.jsonl" "$ROOT/verifier_scores_v1/shard1/scores.jsonl" \
  > "$ROOT/verifier_scores_v1/scores_all.jsonl"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT/VERIFIER_COMPLETE"
