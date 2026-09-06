#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_uncertainty_gated_local8_groupcv500_v1"
SCRIPT="${PROJECT_ROOT}/evaluation/tools/audit_uncertainty_gate_paired_judge_v1.py"
QUESTION_ROOT="${PROJECT_ROOT}/evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1/groupcv5"
GROUNDTRUTH="${QUESTION_ROOT}/oof_groundtruth_v1.json"
OUTPUT="${RUN_ROOT}/judge_identity_dedup_paired_v1"
BACKUP_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
LOG="${RUN_ROOT}/identity_dedup_paired_judge_v1.log"

exec >>"${LOG}" 2>&1
cd "${PROJECT_ROOT}"

"${PYTHON}" - "${RUN_ROOT}/formal/protocol_audit_v1.json" <<'PY'
import json
import sys
if json.load(open(sys.argv[1], encoding="utf-8")).get("passed") is not True:
    raise SystemExit("formal protocol audit failed; paired judge blocked")
PY

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  [[ -r "${BACKUP_EVALUATOR}" ]] || exit 4
  DEEPSEEK_API_KEY="$(${PYTHON} - "${BACKUP_EVALUATOR}" <<'PY'
import ast
import sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "API_KEY" for target in node.targets):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            print(node.value.value, end="")
            break
else:
    raise SystemExit("API_KEY literal missing")
PY
  )"
  export DEEPSEEK_API_KEY
fi

export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

"${PYTHON}" "${SCRIPT}" \
  --run-root "${RUN_ROOT}" \
  --question-root "${QUESTION_ROOT}" \
  --groundtruth "${GROUNDTRUTH}" \
  --output-dir "${OUTPUT}" \
  --samples 10000 \
  --seed 42

unset DEEPSEEK_API_KEY
