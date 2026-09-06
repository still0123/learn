#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen25_evidence_minimal_edit_smoke50_v1"
BASELINE="${ROOT}/evaluation/runs/qwen25_final_arch_groupcv500_v1"
OUT="${RUN}/judge_deepseek_answeronly_v1"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
GT="${ROOT}/evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/oof500_v1_audit/oof_groundtruth_separate.json"
JUDGE="${ROOT}/evaluation/tools/judge_qwen25_evidence_minimal_edit_smoke50_v1.py"

[[ -f "${RUN}/INFERENCE_COMPLETE_V2" ]]
[[ -f "${RUN}/judge_preflight_v1/dry_run_audit.json" ]]
[[ ! -f "${OUT}/summary.json" ]]

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
trap 'unset DEEPSEEK_API_KEY' EXIT

mkdir -p "${OUT}/source_snapshot"
cp "${JUDGE}" "$0" "${OUT}/source_snapshot/"

"${PY}" "${JUDGE}" \
  --project-root "${ROOT}" \
  --baseline-root "${BASELINE}" \
  --smoke-root "${RUN}" \
  --groundtruth "${GT}" \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${OUT}" \
  --workers 8 \
  --bootstrap-samples 10000

(
  cd "${OUT}"
  sha256sum \
    api_results_partial.jsonl \
    paired_results50.jsonl \
    summary.json \
    source_snapshot/* \
    > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/JUDGE_COMPLETE"
