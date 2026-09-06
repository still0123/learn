#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_adsqa_supplement2526_v1"
JUDGE_ROOT="${RUN}/judge_deepseek_v1/supplement2526_v1"
PRIVATE="${JUDGE_ROOT}/private_references"
PREFLIGHT="${JUDGE_ROOT}/preflight_v1"
RESULTS="${JUDGE_ROOT}/results_v1"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="${ROOT}/evaluation/tools/judge_adsqa_supplement2526_v1.py"
PROTOCOL="${RUN}/final_candidates_v1/protocol_audit.json"

cd "${ROOT}"
test -f "${JUDGE_ROOT}/JUDGE_AUTHORIZED_9807"
test -f "${JUDGE_ROOT}/JUDGE_FAILED"
test -f "${RESULTS}/api_failures.jsonl"
test ! -f "${JUDGE_ROOT}/JUDGE_COMPLETE"
test ! -f "${JUDGE_ROOT}/JUDGE_RETRY1_COMPLETE"
test ! -f "${RESULTS}/api_failures_retry1.jsonl"

FAILURES="$(wc -l < "${RESULTS}/api_failures.jsonl")"
PARTIAL="$(wc -l < "${RESULTS}/api_results_partial.jsonl")"
[[ "${FAILURES}" == "3950" ]]
[[ "${PARTIAL}" == "5857" ]]
[[ $((FAILURES + PARTIAL)) == 9807 ]]

mkdir -p "${RESULTS}/source_snapshot" "${RUN}/pids"
cp "${JUDGE}" evaluation/scripts/retry_adsqa_supplement2526_judge_v1.sh \
  "${RESULTS}/source_snapshot/"
echo "$$" > "${RUN}/pids/judge_adsqa_supplement2526_retry1_v1.pid"
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${JUDGE_ROOT}/JUDGE_RETRY1_AUTHORIZED_3950"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_RETRY1_FAILED"' ERR

export AUTHORIZED_FAILED_RETRY_COUNT=3950
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
[[ -n "${DEEPSEEK_API_KEY:-}" ]]
trap 'unset DEEPSEEK_API_KEY AUTHORIZED_FAILED_RETRY_COUNT' EXIT

"${PY}" "${JUDGE}" \
  --groundtruth "${PRIVATE}/groundtruth_private.jsonl" \
  --candidates "${PREFLIGHT}/candidates_answer_free.jsonl" \
  --protocol-audit "${PROTOCOL}" \
  --preflight-root "${PREFLIGHT}" \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${RESULTS}" \
  --workers 10 \
  --bootstrap-samples 10000

(
  cd "${JUDGE_ROOT}"
  find private_references preflight_v1 results_v1 -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_RETRY1_COMPLETE"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_COMPLETE"
