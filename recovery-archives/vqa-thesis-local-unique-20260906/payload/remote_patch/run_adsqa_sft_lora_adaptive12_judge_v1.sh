#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_adaptive12_groupcv500_v1"
MMR_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_mmr8_groupcv500_v1"
BASE_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_groupcv500_v1"
CLEAN_RUN="${ROOT}/evaluation/runs/qwen25_final_arch_groupcv500_v1"
OUTPUT="${RUN}/judge_deepseek_answeronly_v1/results_v1"
JUDGE="${ROOT}/evaluation/tools/judge_adsqa_sft_lora_adaptive12_groupcv500_v1.py"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
GROUNDTRUTH="${BASE_RUN}/oof500_v2_audit/oof_groundtruth_separate.json"
MMR_CACHE="${MMR_RUN}/judge_deepseek_legacy_answer_only_v1/results_v1/api_results_partial.jsonl"
CLEAN_CACHE="${CLEAN_RUN}/judge_deepseek_answeronly_v1/api_results_partial.jsonl"

mkdir -p "${OUTPUT}/source_snapshot"
exec >>"${OUTPUT}/judge.log" 2>&1
echo "[$(date -Is)] AdsSFTLoRA Adaptive12 judge started"

"${PY}" - "${OUTPUT}/dry_run_audit.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("passed") is not True:
    raise SystemExit("dry-run audit did not pass")
if payload.get("required_new_api_call_count") != 208:
    raise SystemExit("authorized API call count changed")
if payload.get("historical_exact_reuse_count") != 500:
    raise SystemExit("historical reuse count changed")
if payload.get("prompt_sha256") != "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19":
    raise SystemExit("judge prompt hash changed")
PY

if [[ -f "${OUTPUT}/summary.json" ]]; then
  echo "[$(date -Is)] summary already exists; refusing to overwrite"
  exit 0
fi
[[ -r "${LEGACY}" ]] || { echo "missing legacy evaluator" >&2; exit 4; }
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
    raise SystemExit("API_KEY literal missing from legacy evaluator backup")
PY
  )"
  export DEEPSEEK_API_KEY
fi
[[ -n "${DEEPSEEK_API_KEY:-}" ]] || { echo "empty temporary DeepSeek key" >&2; exit 5; }
trap 'unset DEEPSEEK_API_KEY' EXIT

cp "$0" "${JUDGE}" "${OUTPUT}/source_snapshot/"
sha256sum \
  "${RUN}/INFERENCE_SHA256SUMS" \
  "${GROUNDTRUTH}" \
  "${MMR_CACHE}" \
  "${CLEAN_CACHE}" \
  "${LEGACY}" \
  > "${OUTPUT}/frozen_inputs_sha256.txt"

"${PY}" "${JUDGE}" \
  --groundtruth "${GROUNDTRUTH}" \
  --run-root "${RUN}" \
  --mmr-oof-root "${MMR_RUN}/oof500" \
  --historical-cache "${MMR_CACHE}" \
  --historical-cache "${CLEAN_CACHE}" \
  --legacy-evaluator "${LEGACY}" \
  --output-root "${OUTPUT}" \
  --workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000

(
  cd "${OUTPUT}"
  sha256sum \
    source_snapshot/* \
    frozen_inputs_sha256.txt \
    dry_run_audit.json \
    api_results_partial.jsonl \
    expanded_results1500.jsonl \
    paired_results500.jsonl \
    threshold_result.json \
    summary.json \
    > SHA256SUMS
)
touch "${OUTPUT}/JUDGE_COMPLETE"
echo "[$(date -Is)] AdsSFTLoRA Adaptive12 judge complete"
