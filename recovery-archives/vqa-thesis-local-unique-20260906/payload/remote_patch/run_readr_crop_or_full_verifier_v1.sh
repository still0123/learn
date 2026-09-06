#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main

ROOT=evaluation/runs/readr_crop_or_full_confirm600_v1
PY=/data1/rmx/ana3/envs/ReadR/bin/python
SCORE=evaluation/tools/score_answer_claims_qwen3_v1.py
MODEL=/data1/qky/Model/Qwen3Vl-8B
ADAPTER=evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter

SHARDS="$ROOT/verifier_shards_v2"
mkdir -p "$SHARDS" "$ROOT/verifier_logs_v2" "$ROOT/verifier_pids_v2"
exec > >(tee -a "$ROOT/verifier_logs/pipeline.log") 2>&1

run_fold() {
  local fold="$1"
  local gpu="$2"
  local expected="$3"
  local input="$ROOT/verifier_inputs/shards/fold_${fold}.jsonl"
  local output="$SHARDS/fold_${fold}"
  if [[ -f "$output/summary.json" ]]; then
    echo "fold_${fold} already complete"
    return
  fi
  if [[ -e "$output" ]] && [[ $(find "$output" -mindepth 1 -maxdepth 1 | wc -l) -gt 0 ]]; then
    echo "incomplete output exists: $output" >&2
    return 1
  fi
  "$PY" "$SCORE" \
    --gpu-id "$gpu" --model-dir "$MODEL" --adapter-dir "$ADAPTER" \
    --input-jsonl "$input" --output-dir "$output" \
    --views 8 --unified-size 448 --max-visual-tokens 4096 \
    >"$ROOT/verifier_logs_v2/fold_${fold}.log" 2>&1
  "$PY" - "$output/scores.jsonl" "$output/summary.json" "$expected" <<'PY'
import json,sys
rows=[json.loads(x) for x in open(sys.argv[1]) if x.strip()]
summary=json.load(open(sys.argv[2]))
expected=int(sys.argv[3])
assert len(rows)==expected, (len(rows),expected)
assert all(int(x['represented_views'])==8 for x in rows)
assert all(not x['secondary_frame_sampling'] for x in rows)
print({'fold_rows':len(rows),'summary':summary})
PY
}

folds=(0 1 2 3 4)
expected=(31 20 30 30 41)
next=0
declare -A running=()
while [[ "$next" -lt 5 ]] || [[ "${#running[@]}" -gt 0 ]]; do
  for gpu in 0 1 2 3 4 5; do
    [[ "$next" -lt 5 ]] || break
    [[ -z "${running[$gpu]:-}" ]] || continue
    free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$gpu" | tr -d ' ')
    if [[ "$free" -lt 38000 ]]; then continue; fi
    fold="${folds[$next]}"
    echo "$(date -Is) launch fold=$fold gpu=$gpu free_mib=$free"
    run_fold "$fold" "$gpu" "${expected[$next]}" &
    pid=$!
    running[$gpu]="$pid"
    printf '%s\n' "$pid" > "$ROOT/verifier_pids_v2/fold_${fold}.pid"
    next=$((next+1))
  done
  for gpu in "${!running[@]}"; do
    pid="${running[$gpu]}"
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid"
      unset 'running[$gpu]'
    fi
  done
  if [[ "$next" -lt 5 ]] || [[ "${#running[@]}" -gt 0 ]]; then sleep 60; fi
done
touch "$ROOT/VERIFIER_INFERENCE_COMPLETE"
echo "$(date -Is) VERIFIER_INFERENCE_COMPLETE"
