#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main

PY=/data1/rmx/ana3/envs/ReadR/bin/python
LEGACY=/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py
ROOT=evaluation/runs/readr_crop_or_full_confirm600_v1

test -f "$ROOT/VERIFIER_INFERENCE_COMPLETE"
test -f "$ROOT/gate_analysis_v1/summary.json"
test ! -e "$ROOT/judge_deepseek_v1"

DEEPSEEK_API_KEY="$($PY - "$LEGACY" <<'PY'
import ast,sys
tree=ast.parse(open(sys.argv[1],encoding="utf-8").read())
keys=[node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith("sk-") and len(node.value)>20]
if len(set(keys)) != 1: raise SystemExit("expected exactly one embedded DeepSeek key")
print(keys[0],end="")
PY
)"
export DEEPSEEK_API_KEY
trap 'unset DEEPSEEK_API_KEY' EXIT

$PY evaluation/tools/judge_readr_crop_or_full_confirm600_v1.py
(
  cd "$ROOT"
  find dataset verifier_inputs verifier_shards_v2 gate_analysis_v1 judge_deepseek_v1 -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
