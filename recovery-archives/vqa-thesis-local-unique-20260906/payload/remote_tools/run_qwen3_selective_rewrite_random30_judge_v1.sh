#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RANDOM_RUN="${ROOT}/evaluation/runs/qwen3_selective_evidence_rewrite_random30_confirmd300_v1"
TARGETED_RUN="${ROOT}/evaluation/runs/qwen3_selective_evidence_rewrite_confirmd300_v1"
JUDGE_ROOT="${RANDOM_RUN}/judge_deepseek_incremental_v1"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="${ROOT}/evaluation/tools/judge_qwen3_selective_rewrite_random30_incremental_v1.py"
GROUNDTRUTH="${ROOT}/data/innovation1_confirmd300_v1/groundtruth.json"
A0_POOL="${TARGETED_RUN}/a0_pool_v1/model_inputs_all.jsonl"
CHOICES="${RANDOM_RUN}/frozen_choices_v2_recovered/frozen_choices_answer_free.jsonl"
AUDIT="${RANDOM_RUN}/frozen_choices_v2_recovered/protocol_audit.json"
EXISTING_CACHE="${TARGETED_RUN}/judge_deepseek_v1/api_results_partial.jsonl"
TARGETED_ROWS="${TARGETED_RUN}/judge_deepseek_v1/complete_confirmd300_policy_rows.jsonl"

for required in \
  "${RANDOM_RUN}/INFERENCE_AND_SELECTION_COMPLETE" \
  "${GROUNDTRUTH}" \
  "${A0_POOL}" \
  "${CHOICES}" \
  "${AUDIT}" \
  "${EXISTING_CACHE}" \
  "${TARGETED_ROWS}" \
  "${LEGACY}" \
  "${JUDGE}"; do
  [[ -e "${required}" ]] || {
    echo "missing required frozen input: ${required}" >&2
    exit 1
  }
done
if [[ -f "${JUDGE_ROOT}/summary.json" ]]; then
  echo "random-trigger judge summary already exists; refusing overwrite" >&2
  exit 2
fi

mkdir -p "${JUDGE_ROOT}/source_snapshot"
cp "${JUDGE}" "$0" "${JUDGE_ROOT}/source_snapshot/"

COMMON_ARGS=(
  --groundtruth "${GROUNDTRUTH}"
  --a0-pool "${A0_POOL}"
  --choices "${CHOICES}"
  --protocol-audit "${AUDIT}"
  --existing-api-cache "${EXISTING_CACHE}"
  --targeted-policy-rows "${TARGETED_ROWS}"
  --legacy-evaluator "${LEGACY}"
  --output-dir "${JUDGE_ROOT}"
  --authorized-new-calls 50
  --workers 10
  --bootstrap-samples 10000
)

env -u DEEPSEEK_API_KEY "${PY}" "${JUDGE}" \
  --mode preflight \
  "${COMMON_ARGS[@]}"

"${PY}" - "${JUDGE_ROOT}/preflight_audit.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
checks = [
    audit.get("passed") is True,
    audit.get("api_called") is False,
    audit.get("contains_api_key") is False,
    int(audit.get("authorized_max_new_call_count", -1)) == 50,
    int(audit.get("required_new_api_call_count", -1)) == 49,
    int(audit.get("exact_historical_reuse_count", -1)) == 307,
    int(audit.get("reconstructed_unique_candidate_count", -1)) == 356,
]
if not all(checks):
    raise SystemExit("incremental 50-call preflight failed")
PY

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  DEEPSEEK_API_KEY="$("${PY}" - "${LEGACY}" <<'PY'
import ast
import sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "API_KEY"
        for target in node.targets
    ) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        print(node.value.value, end="")
        break
else:
    raise SystemExit("API_KEY literal missing from read-only legacy evaluator")
PY
  )"
  export DEEPSEEK_API_KEY
fi
[[ -n "${DEEPSEEK_API_KEY:-}" ]] || {
  echo "empty temporary key" >&2
  exit 3
}
trap 'unset DEEPSEEK_API_KEY' EXIT

"${PY}" "${JUDGE}" \
  --mode execute \
  "${COMMON_ARGS[@]}"

{
  sha256sum \
    "${GROUNDTRUTH}" \
    "${A0_POOL}" \
    "${CHOICES}" \
    "${AUDIT}" \
    "${EXISTING_CACHE}" \
    "${TARGETED_ROWS}" \
    "${LEGACY}" \
    "${JUDGE}"
} > "${JUDGE_ROOT}/frozen_inputs_sha256.txt"
(
  cd "${JUDGE_ROOT}"
  find . -type f ! -name SHA256SUMS -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${JUDGE_ROOT}/JUDGE_COMPLETE"
