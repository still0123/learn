#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main

RUN=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
PY=/data1/rmx/ana3/envs/ReadR/bin/python
LEGACY=/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py

test -f "$RUN/FINAL_CHOICES_READY_AWAITING_JUDGE_AUTHORIZATION"
test -f "$RUN/judge_deepseek_official_v1/preflight/dry_run_audit.json"
test -f "$RUN/judge_deepseek_official_v1/private_references_audit.json"

DEEPSEEK_API_KEY="$($PY - "$LEGACY" <<'PY'
import ast,sys
tree=ast.parse(open(sys.argv[1],encoding="utf-8").read())
keys=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith("sk-") and len(n.value)>20]
if len(set(keys)) != 1: raise SystemExit("expected one embedded key")
print(keys[0],end="")
PY
)"
export DEEPSEEK_API_KEY
trap 'unset DEEPSEEK_API_KEY' EXIT

$PY /tmp/judge_readr_crop_or_full_fresh500_v1.py \
  --questions "$RUN/dataset/questions_answer_free.json" \
  --references "$RUN/judge_deepseek_official_v1/private_references.jsonl" \
  --preflight "$RUN/judge_deepseek_official_v1/preflight" \
  --output-dir "$RUN/judge_deepseek_official_v1/results_v1" \
  --authorized-limit 757
