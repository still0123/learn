#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_threshold_full5320_v1"
PREFLIGHT="${RUN}/judge_deepseek_v1/preflight_v1"
RESULTS="${RUN}/judge_deepseek_v1/results_v1"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="${ROOT}/evaluation/tools/judge_threshold_full5320_v1.py"

cd "${ROOT}"
test -f "${RUN}/JUDGE_AUTHORIZED_4304"
test -f "${RUN}/JUDGE_RETRY_AUTHORIZED_1"
test -f "${RUN}/JUDGE_FAILED"
test ! -f "${RUN}/JUDGE_COMPLETE"
test "$(wc -l < "${RESULTS}/api_results_partial.jsonl")" -eq 4303
test "$(wc -l < "${RESULTS}/api_failures.jsonl")" -eq 1
mkdir -p "${RESULTS}/source_snapshot" "${RUN}/pids"
echo "$$" > "${RUN}/pids/judge_threshold_full5320_retry1_v1.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/JUDGE_RETRY1_FAILED"' ERR

cp "${JUDGE}" evaluation/scripts/run_qwen3_threshold_full5320_retry1_v1.sh \
  "${RESULTS}/source_snapshot/"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  DEEPSEEK_API_KEY="$("${PY}" - "${LEGACY}" <<'PY'
import ast
import sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
keys = [
    node.value
    for node in ast.walk(tree)
    if isinstance(node, ast.Constant)
    and isinstance(node.value, str)
    and node.value.startswith("sk-")
    and len(node.value) > 20
]
if len(set(keys)) != 1:
    raise SystemExit("expected exactly one embedded DeepSeek key")
print(keys[0], end="")
PY
  )"
  export DEEPSEEK_API_KEY
fi
export AUTHORIZED_SINGLE_RETRY=1
trap 'unset DEEPSEEK_API_KEY AUTHORIZED_SINGLE_RETRY' EXIT

"${PY}" "${JUDGE}" \
  --groundtruth data/adsqa_full_valid5320_v1/private_references/groundtruth.json \
  --candidates "${PREFLIGHT}/candidates_answer_free.jsonl" \
  --protocol-audit "${RUN}/adaptive_scale_protocol_audit_v1/audit.json" \
  --preflight-root "${PREFLIGHT}" \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${RESULTS}" \
  --workers 1 \
  --bootstrap-samples 10000

(
  cd "${RUN}/judge_deepseek_v1"
  find preflight_v1 results_v1 -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/JUDGE_COMPLETE"
