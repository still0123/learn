#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
BASE_RUN="$PROJECT_ROOT/evaluation/runs/adsqa_sft_lora_groupcv500_v1"
MMR_RUN="$PROJECT_ROOT/evaluation/runs/adsqa_sft_lora_mmr8_groupcv500_v1"
OUTPUT_ROOT="$MMR_RUN/judge_deepseek_legacy_answer_only_v1/results_v1"
PREFLIGHT="$MMR_RUN/judge_deepseek_legacy_answer_only_v1/preflight_v1/dry_run_audit.json"
GROUNDTRUTH="$BASE_RUN/oof500_v2_audit/oof_groundtruth_separate.json"
BASELINE_OOF="$BASE_RUN/oof500_v2"
MMR_OOF="$MMR_RUN/oof500"
HISTORICAL_CACHE="$BASE_RUN/judge_deepseek_legacy_answer_only_v1/api_results_partial.jsonl"
LEGACY_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="$PROJECT_ROOT/evaluation/tools/judge_adsqa_sft_lora_mmr8_v1.py"

mkdir -p "$OUTPUT_ROOT/source_snapshot"
exec >>"$OUTPUT_ROOT/judge.log" 2>&1
echo "[$(date -Is)] AdsSFTLoRA Raw8/MMR8 paired judge started"

"$PYTHON" - "$PREFLIGHT" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("passed") is not True:
    raise SystemExit("cache preflight did not pass")
if payload["judge_protocol"]["required_new_api_call_count"] != 436:
    raise SystemExit("authorized API call count changed")
if payload["judge_protocol"]["prompt_sha256"] != "898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19":
    raise SystemExit("judge prompt hash changed")
PY

if [[ -f "$OUTPUT_ROOT/summary.json" ]]; then
  echo "[$(date -Is)] summary already exists; refusing to overwrite"
  exit 0
fi
[[ -r "$LEGACY_EVALUATOR" ]] || { echo "missing legacy evaluator" >&2; exit 4; }
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  DEEPSEEK_API_KEY="$("$PYTHON" - "$LEGACY_EVALUATOR" <<'PY'
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

cp "$0" "$JUDGE" "$PROJECT_ROOT/evaluation/tools/preflight_adsqa_sft_lora_mmr8_judge_v1.py" \
  "$OUTPUT_ROOT/source_snapshot/"
sha256sum "$PREFLIGHT" "$GROUNDTRUTH" "$HISTORICAL_CACHE" "$LEGACY_EVALUATOR" \
  > "$OUTPUT_ROOT/frozen_inputs_sha256.txt"

"$PYTHON" "$JUDGE" \
  --groundtruth "$GROUNDTRUTH" \
  --protocol-audit "$PREFLIGHT" \
  --baseline-oof-root "$BASELINE_OOF" \
  --mmr-oof-root "$MMR_OOF" \
  --historical-cache "$HISTORICAL_CACHE" \
  --legacy-evaluator "$LEGACY_EVALUATOR" \
  --output-root "$OUTPUT_ROOT" \
  --workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000

(
  cd "$OUTPUT_ROOT"
  sha256sum source_snapshot/* frozen_inputs_sha256.txt dry_run_audit.json \
    api_results_partial.jsonl results.jsonl summary.json > SHA256SUMS
)
touch "$OUTPUT_ROOT/JUDGE_COMPLETE"
echo "[$(date -Is)] AdsSFTLoRA Raw8/MMR8 paired judge complete"
