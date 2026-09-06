#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
LEGACY=/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py
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
$PY /tmp/judge_forced_full_cf123_v1.py
