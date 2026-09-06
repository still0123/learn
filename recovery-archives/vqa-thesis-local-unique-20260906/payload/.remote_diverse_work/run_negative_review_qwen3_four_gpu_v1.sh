#!/usr/bin/env bash
set -euo pipefail

ROOT=/data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
RUN="$ROOT/evaluation/runs/innovation2_realclaim_lora_verifier_v1/negative_review_qwen3_v1"
INPUT="$RUN/dataset/review_inputs.jsonl"
SCRIPT="$ROOT/evaluation/methods/claim_evidence_verifier/inference_intervention_smoke_v2.py"
MODEL=/data1/qky/Model/Qwen3Vl-8B

mkdir -p "$RUN/shards"
starts=(0 86 172 258)
ends=(86 172 258 343)
gpus=(2 3 4 5)
for i in 0 1 2 3; do
  out="$RUN/shards/shard_$i"
  mkdir -p "$out"
  nohup "$PY" "$SCRIPT" \
    --gpu-id "${gpus[$i]}" --model-dir "$MODEL" \
    --input-jsonl "$INPUT" --oracle-jsonl "$INPUT" --output-root "$out" \
    --start-idx "${starts[$i]}" --end-idx "${ends[$i]}" --full-only --overwrite \
    >"$out/launcher.log" 2>&1 < /dev/null &
  echo "$!" >"$out/pid"
done
printf 'pids=%s,%s,%s,%s\n' \
  "$(cat "$RUN/shards/shard_0/pid")" "$(cat "$RUN/shards/shard_1/pid")" \
  "$(cat "$RUN/shards/shard_2/pid")" "$(cat "$RUN/shards/shard_3/pid")"
