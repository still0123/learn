#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
ROOT=evaluation/runs/qwen25_active_evidence_look_v1/region_gate_confirm100_v1
PREFLIGHT="$ROOT/judge_preflight_v1"
OUTPUT="$ROOT/judge_results_v1"
GROUNDTRUTH=data/testset_groundtruth.json
LEGACY=/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py
mkdir -p "$OUTPUT"

DEEPSEEK_API_KEY="$($PY - "$LEGACY" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "API_KEY" for target in node.targets) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        print(node.value.value, end="")
        break
else:
    raise SystemExit("API_KEY literal missing")
PY
)"
export DEEPSEEK_API_KEY
trap 'unset DEEPSEEK_API_KEY' EXIT

$PY evaluation/tools/judge_qwen25_region_gate_confirm100_v1.py \
  --project-root . --preflight-root "$PREFLIGHT" --groundtruth "$GROUNDTRUTH" \
  --legacy-evaluator "$LEGACY" --output-root "$OUTPUT"
