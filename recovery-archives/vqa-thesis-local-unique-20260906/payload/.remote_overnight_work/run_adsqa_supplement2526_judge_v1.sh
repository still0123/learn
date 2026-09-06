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
MATERIALIZE="${ROOT}/evaluation/tools/materialize_adsqa_supplement2526_private_refs_v1.py"
PREFLIGHT_TOOL="${ROOT}/evaluation/tools/preflight_adsqa_supplement2526_judge_v1.py"
JUDGE="${ROOT}/evaluation/tools/judge_adsqa_supplement2526_v1.py"
CANDIDATES="${RUN}/final_candidates_v1/candidates_answer_free.jsonl"
PROTOCOL="${RUN}/final_candidates_v1/protocol_audit.json"

cd "${ROOT}"
test -f "${RUN}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
test ! -f "${JUDGE_ROOT}/JUDGE_COMPLETE"
test ! -e "${JUDGE_ROOT}"
mkdir -p "${PRIVATE}" "${RESULTS}/source_snapshot" "${RUN}/pids"
echo "$$" > "${RUN}/pids/judge_adsqa_supplement2526_v1.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_FAILED"' ERR

cp "${MATERIALIZE}" "${PREFLIGHT_TOOL}" "${JUDGE}" \
  evaluation/scripts/run_adsqa_supplement2526_judge_v1.sh \
  "${RESULTS}/source_snapshot/"

"${PY}" "${MATERIALIZE}" \
  --questions data/adsqa_supplement2526_v1/questions_answer_free.json \
  --private-answers data/adsqa_supplement2526_v1/private_references/groundtruth.json \
  --raw-groundtruth data/testset_groundtruth.json \
  --output "${PRIVATE}/groundtruth_private.jsonl" \
  --audit "${PRIVATE}/audit.json"

"${PY}" "${PREFLIGHT_TOOL}" \
  --groundtruth "${PRIVATE}/groundtruth_private.jsonl" \
  --candidates "${CANDIDATES}" \
  --protocol-audit "${PROTOCOL}" \
  --legacy-evaluator "${LEGACY}" \
  --cache-root evaluation/runs \
  --output-dir "${PREFLIGHT}"

"${PY}" - "${PREFLIGHT}/dry_run_audit.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
if (
    audit.get("passed") is not True
    or audit.get("required_new_api_call_count") != 9807
    or audit.get("historical_exact_reuse_count") != 0
    or audit.get("historical_conflict_count") != 0
):
    raise SystemExit("authorized 9807-call preflight changed")
PY
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_AUTHORIZED_9807"

"${PY}" "${JUDGE}" \
  --groundtruth "${PRIVATE}/groundtruth_private.jsonl" \
  --candidates "${PREFLIGHT}/candidates_answer_free.jsonl" \
  --protocol-audit "${PROTOCOL}" \
  --preflight-root "${PREFLIGHT}" \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${RESULTS}" \
  --workers 10 \
  --bootstrap-samples 10000 \
  --validate-only

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
trap 'unset DEEPSEEK_API_KEY' EXIT

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
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_COMPLETE"
