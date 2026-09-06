#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
ROOT=evaluation/runs/qwen25_active_evidence_look_v1
LOGIC="$ROOT/logic_trees_pilot300_v1"
OUT="$ROOT/smoke20_reuse_v1"

while [[ ! -f "$LOGIC/LOGIC_TREES_QWEN3_COMPLETE" ]]; do
  if [[ -f "$LOGIC/summary.json" ]] && ! kill -0 "$(cat "$LOGIC/run.pid")" 2>/dev/null; then
    rows=$(wc -l < "$LOGIC/logic_trees.jsonl")
    if [[ "$rows" -ge 299 ]]; then
      echo "accepting audited partial logic-tree coverage: $rows/300"
      break
    fi
    echo "logic-tree coverage below smoke gate: $rows/300" >&2
    exit 1
  fi
  sleep 60
done

/data1/rmx/ana3/envs/ReadR/bin/python evaluation/tools/build_qwen25_active_evidence_look_smoke_v1.py \
  --logic-trees "$LOGIC/logic_trees.jsonl" \
  --items evaluation/runs/readr_increment_pilot300_v1/all_candidates_for_calibration/items_answer_free.jsonl \
  --verifier-scores evaluation/runs/readr_increment_pilot300_v1/mmr8_verifier_merged/scores_all.jsonl \
  --adaptive-root evaluation/runs/readr_increment_pilot300_v1/adaptive12 \
  --extra-root evaluation/runs/readr_increment_pilot300_v1/extra_global12 \
  --judge-scores evaluation/runs/readr_increment_pilot300_v1/judge_deepseek_legacy_answeronly_v1/results_v1/expanded_four_method_scores.jsonl \
  --output-root "$OUT"
