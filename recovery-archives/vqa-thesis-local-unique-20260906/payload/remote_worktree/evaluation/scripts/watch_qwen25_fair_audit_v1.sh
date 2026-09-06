#!/usr/bin/env bash
set -euo pipefail

project_root="/data1/rmx/projectb/AdsQA-main"
run_root="$project_root/evaluation/runs/qwen25_evidence300_afternoon_v1"
question_file="$project_root/data/innovation1_evidence300_v1/question.json"
python_bin="/data1/rmx/ana3/envs/ReadR/bin/python"
log_file="$run_root/qwen25_fair_audit_watcher.log"

mkdir -p "$run_root"
exec >> "$log_file" 2>&1
echo "watcher_started $(date -Is)"

while true; do
  raw_count=$(find "$run_root/formal_raw_uniform_v1" -name prediction.json -type f 2>/dev/null | wc -l | tr -d ' ')
  adslot_count=$(find "$run_root/formal_adslot_fixed_v1" -name prediction.json -type f 2>/dev/null | wc -l | tr -d ' ')
  raw_pid=$(pgrep -f "inference_fair_baselines_v1.py.*formal_raw_uniform_v1" || true)
  adslot_pid=$(pgrep -f "inference_fair_baselines_v1.py.*formal_adslot_fixed_v1" || true)
  echo "$(date -Is) raw=$raw_count adslot=$adslot_count raw_pid=${raw_pid:-none} adslot_pid=${adslot_pid:-none}"

  if [[ "$raw_count" == "300" && "$adslot_count" == "300" && -z "$raw_pid" && -z "$adslot_pid" ]]; then
    "$python_bin" "$project_root/evaluation/tools/audit_qwen25_fair_run_v1.py" \
      --run-dir "$run_root/formal_raw_uniform_v1" \
      --question-file "$question_file" \
      --expected-visual-tokens 16384 \
      --model-label Qwen2.5-VL-7B-Instruct \
      --output "$run_root/formal_raw_uniform_v1/audit_qwen25_fair_run_v1.json"
    "$python_bin" "$project_root/evaluation/tools/audit_qwen25_fair_run_v1.py" \
      --run-dir "$run_root/formal_adslot_fixed_v1" \
      --question-file "$question_file" \
      --expected-visual-tokens 16384 \
      --model-label Qwen2.5-VL-7B-Instruct \
      --output "$run_root/formal_adslot_fixed_v1/audit_qwen25_fair_run_v1.json"
    date -Is > "$run_root/qwen25_fair_audit_ready.marker"
    echo "audits_completed $(date -Is)"
    exit 0
  fi
  sleep 60
done
