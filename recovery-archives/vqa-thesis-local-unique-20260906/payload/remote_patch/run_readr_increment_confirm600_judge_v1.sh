#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/readr_increment_confirm600_v1"
JROOT="${RUN}/judge_deepseek_legacy_answeronly_v1"
MATERIALIZED="${JROOT}/materialized_v1"
PREFLIGHT="${JROOT}/preflight_v1"
RESULTS="${JROOT}/results_v1"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
CACHE="${ROOT}/evaluation/runs/qwen25_adsqa_full7846_v1/judge_deepseek_v1/api_results_partial.jsonl"
EXPECTED_NEW=1232
EXPECTED_REUSED=0

cd "${ROOT}"
test -f "${RUN}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
test -f "${MATERIALIZED}/protocol_audit.json"
test -f "${PREFLIGHT}/dry_run_audit.json"
test ! -f "${JROOT}/JUDGE_COMPLETE"
test ! -f "${JROOT}/JUDGE_RUNNING"
test ! -f "${JROOT}/JUDGE_FAILED"
mkdir -p "${RESULTS}/source_snapshot" "${RUN}/pids"
echo "$$" > "${RUN}/pids/readr_increment_confirm600_judge_v1.pid"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JROOT}/JUDGE_RUNNING"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JROOT}/JUDGE_FAILED"; rm -f "${JROOT}/JUDGE_RUNNING"' ERR

cp evaluation/tools/preflight_readr_increment_confirm600_judge_v1.py \
  evaluation/tools/judge_readr_increment_confirm600_v1.py \
  evaluation/scripts/run_readr_increment_confirm600_judge_v1.sh \
  "${RESULTS}/source_snapshot/"

"${PY}" evaluation/tools/judge_readr_increment_confirm600_v1.py \
  --groundtruth "${MATERIALIZED}/private_references/groundtruth_confirm600.json" \
  --candidates "${MATERIALIZED}/candidates_answer_free.jsonl" \
  --protocol-audit "${MATERIALIZED}/protocol_audit.json" \
  --preflight-root "${PREFLIGHT}" \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${RESULTS}" \
  --workers 10 \
  --bootstrap-samples 10000 \
  --expected-new-calls "${EXPECTED_NEW}" \
  --expected-reused "${EXPECTED_REUSED}" \
  --validate-only

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
[[ -n "${DEEPSEEK_API_KEY}" ]]
trap 'unset DEEPSEEK_API_KEY; rm -f "${JROOT}/JUDGE_RUNNING"' EXIT

"${PY}" evaluation/tools/judge_readr_increment_confirm600_v1.py \
  --groundtruth "${MATERIALIZED}/private_references/groundtruth_confirm600.json" \
  --candidates "${MATERIALIZED}/candidates_answer_free.jsonl" \
  --protocol-audit "${MATERIALIZED}/protocol_audit.json" \
  --preflight-root "${PREFLIGHT}" \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${RESULTS}" \
  --workers 10 \
  --bootstrap-samples 10000 \
  --expected-new-calls "${EXPECTED_NEW}" \
  --expected-reused "${EXPECTED_REUSED}"

(
  cd "${JROOT}"
  find materialized_v1 preflight_v1 results_v1 -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JROOT}/JUDGE_COMPLETE"
rm -f "${JROOT}/JUDGE_RUNNING"
