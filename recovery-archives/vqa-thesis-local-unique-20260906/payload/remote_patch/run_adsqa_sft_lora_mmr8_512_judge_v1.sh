#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
BASE_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_groupcv500_v1"
MMR448_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_mmr8_groupcv500_v1"
MMR512_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_mmr8_512_groupcv500_v1"
CLEAN_RUN="${ROOT}/evaluation/runs/qwen25_final_arch_groupcv500_v1"
ADAPTIVE_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_adaptive12_groupcv500_v1"
OUTPUT="${MMR512_RUN}/judge_deepseek_legacy_answer_only_v1/results_v1"
PREFLIGHT="${MMR512_RUN}/judge_deepseek_legacy_answer_only_v1/preflight_v1/dry_run_audit.json"
GROUNDTRUTH="${BASE_RUN}/oof500_v2_audit/oof_groundtruth_separate.json"
CACHE_CLEAN="${CLEAN_RUN}/judge_deepseek_answeronly_v1/api_results_partial.jsonl"
CACHE_RAW="${BASE_RUN}/judge_deepseek_legacy_answer_only_v1/api_results_partial.jsonl"
CACHE_MMR="${MMR448_RUN}/judge_deepseek_legacy_answer_only_v1/results_v1/api_results_partial.jsonl"
CACHE_ADAPTIVE="${ADAPTIVE_RUN}/judge_deepseek_answeronly_v1/results_v1/api_results_partial.jsonl"
LEGACY_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="${ROOT}/evaluation/tools/judge_adsqa_sft_lora_mmr8_512_v1.py"

mkdir -p "${OUTPUT}/source_snapshot"
exec >>"${OUTPUT}/judge.log" 2>&1
echo "[$(date -Is)] AdsSFTLoRA MMR8 448/512 paired judge started"

"${PY}" - "${PREFLIGHT}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("passed") is not True:
    raise SystemExit("cache preflight did not pass")
if payload["judge_protocol"]["required_new_api_call_count"] != 294:
    raise SystemExit("authorized API call count changed")
if payload["judge_protocol"]["exact_cache_reuse_count"] != 206:
    raise SystemExit("historical cache reuse count changed")
if payload["judge_protocol"]["prompt_sha256"] != "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19":
    raise SystemExit("judge prompt hash changed")
PY

if [[ -f "${OUTPUT}/summary.json" ]]; then
  echo "[$(date -Is)] summary already exists; refusing to overwrite"
  exit 0
fi
[[ -r "$LEGACY_EVALUATOR" ]] || { echo "missing legacy evaluator" >&2; exit 4; }
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  DEEPSEEK_API_KEY="$("${PY}" - "$LEGACY_EVALUATOR" <<'PY'
import ast
import sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "API_KEY" for target in node.targets
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

cp "$0" "${JUDGE}" \
  "${ROOT}/evaluation/tools/preflight_adsqa_sft_lora_mmr8_512_judge_v1.py" \
  "${OUTPUT}/source_snapshot/"
sha256sum \
  "${PREFLIGHT}" \
  "${GROUNDTRUTH}" \
  "${CACHE_CLEAN}" \
  "${CACHE_RAW}" \
  "${CACHE_MMR}" \
  "${CACHE_ADAPTIVE}" \
  "${LEGACY_EVALUATOR}" \
  > "${OUTPUT}/frozen_inputs_sha256.txt"

"${PY}" "${JUDGE}" \
  --groundtruth "${GROUNDTRUTH}" \
  --protocol-audit "${PREFLIGHT}" \
  --mmr448-oof-root "${MMR448_RUN}/oof500" \
  --mmr512-oof-root "${MMR512_RUN}/oof500" \
  --historical-cache "${CACHE_CLEAN}" \
  --historical-cache "${CACHE_RAW}" \
  --historical-cache "${CACHE_MMR}" \
  --historical-cache "${CACHE_ADAPTIVE}" \
  --legacy-evaluator "${LEGACY_EVALUATOR}" \
  --output-root "${OUTPUT}" \
  --workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000

(
  cd "${OUTPUT}"
  sha256sum source_snapshot/* frozen_inputs_sha256.txt dry_run_audit.json \
    api_results_partial.jsonl results.jsonl summary.json > SHA256SUMS
)
touch "${OUTPUT}/JUDGE_COMPLETE"
echo "[$(date -Is)] AdsSFTLoRA MMR8 448/512 paired judge complete"
