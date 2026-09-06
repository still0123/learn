#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_threshold_calibration500_v1"
OUT="${RUN}/judge_and_threshold_v1"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="${ROOT}/evaluation/tools/judge_and_learn_threshold_calibration500_v1.py"

[[ -f "${RUN}/A2_INFERENCE_COMPLETE_AWAITING_JUDGE_PREFLIGHT" ]] || {
  echo "A2 inference is incomplete" >&2
  exit 1
}
"${PY}" - "${OUT}/dry_run_audit.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
if audit.get("passed") is not True:
    raise SystemExit("judge dry-run did not pass")
if int(audit.get("required_api_call_count", -1)) != 432:
    raise SystemExit("API call count is not the separately authorized 432")
if int(audit.get("historical_a0_score_reuse_count", -1)) != 500:
    raise SystemExit("historical A0 reuse count changed")
if int(audit.get("historical_a2_score_reuse_count", -1)) != 48:
    raise SystemExit("historical A2 reuse count changed")
if int(audit.get("a2_equals_a0_count", -1)) != 20:
    raise SystemExit("A2 duplicate count changed")
if audit.get("candidate_mode") != "answer_only":
    raise SystemExit("candidate mode is not answer_only")
if audit.get("api_called") is not False:
    raise SystemExit("dry-run claims an API call")
if audit.get("automatic_retry_allowed") is not False:
    raise SystemExit("automatic retries are not disabled")
PY
[[ ! -f "${OUT}/threshold_result.json" ]] || {
  echo "threshold result already exists; refusing overwrite" >&2
  exit 2
}

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

mkdir -p "${OUT}/source_snapshot"
cp "${JUDGE}" "$0" "${OUT}/source_snapshot/"

"${PY}" "${JUDGE}" \
  --groundtruth "${ROOT}/evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/oof500_v1_audit/oof_groundtruth_separate.json" \
  --dataset "${RUN}/dataset_v1/items_answer_free.jsonl" \
  --inference-root "${RUN}/a2_inference_v1" \
  --protocol-audit "${RUN}/a2_protocol_audit_v1/audit.json" \
  --a0-scores "${ROOT}/evaluation/runs/qwen3_mmr_selectrescue_oof500_v1/a0_verifier_merged_v1/scores_all.jsonl" \
  --historical-a0-results "${ROOT}/evaluation/runs/qwen3_selected8_baselines_groupcv500_v1/judge_deepseek_answeronly_v1/results.jsonl" \
  --historical-a2-api-results "${ROOT}/evaluation/runs/qwen3_mmr_selectrescue_oof500_v1/judge_deepseek_v1/api_results_partial.jsonl" \
  --legacy-evaluator "${LEGACY}" \
  --output-root "${OUT}" \
  --workers 10 \
  --bootstrap-samples 10000

(
  cd "${OUT}"
  sha256sum \
    dry_run_audit.json \
    api_results_partial.jsonl \
    paired_results500.jsonl \
    threshold_result.json \
    source_snapshot/* \
    > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/THRESHOLD_CALIBRATION_COMPLETE"
