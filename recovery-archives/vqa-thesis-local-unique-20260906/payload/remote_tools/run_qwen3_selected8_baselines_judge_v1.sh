#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/qwen3_selected8_baselines_groupcv500_v1"
SELECTED_ROOT="$RUN_ROOT/full500"
JUDGE_ROOT="$RUN_ROOT/judge_deepseek_answeronly_v1"
GROUNDTRUTH="$PROJECT_ROOT/evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/oof500_v1_audit/oof_groundtruth_separate.json"
HISTORICAL="$PROJECT_ROOT/evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/judge_deepseek_current_batch_v1/results.jsonl"
LEGACY_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
KEY_WRAPPER="$PROJECT_ROOT/evaluation/tools/run_with_backup_api_key_v1.py"
JUDGE="$PROJECT_ROOT/evaluation/tools/judge_qwen3_selected8_baselines_oof_v1.py"

AUDITS=(
  "$SELECTED_ROOT/CLIPTopK8/protocol_audit.json"
  "$SELECTED_ROOT/MMR8/protocol_audit.json"
  "$SELECTED_ROOT/VideoITG8/shard0/protocol_audit.json"
  "$SELECTED_ROOT/VideoITG8/shard1/protocol_audit.json"
)
COMMON_ARGS=(
  --groundtruth "$GROUNDTRUTH"
  --selected-root "$SELECTED_ROOT"
  --historical-results "$HISTORICAL"
  --legacy-evaluator "$LEGACY_EVALUATOR"
  --output-root "$JUDGE_ROOT"
  --workers 10
  --bootstrap-samples 10000
)
for audit in "${AUDITS[@]}"; do
  COMMON_ARGS+=(--protocol-audit "$audit")
done

mkdir -p "$JUDGE_ROOT/source_snapshot"
echo "$$" > "$JUDGE_ROOT/run.pid"
exec >>"$JUDGE_ROOT/controller.log" 2>&1
cd "$PROJECT_ROOT"

"$PYTHON" - "$JUDGE_ROOT/dry_run_audit.json" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
checks = {
    "passed": audit.get("passed") is True,
    "authorized_calls": audit.get("required_api_call_count") == 1499,
    "questions": audit.get("question_count") == 500,
    "new_methods": audit.get("new_method_count") == 3,
    "records": audit.get("expanded_new_record_count") == 1500,
    "reuse": audit.get("historical_uniform_reuse_count") == 1,
    "answer_only": audit.get("candidate_mode") == "answer_only",
    "no_key": audit.get("contains_api_key") is False,
}
if not all(checks.values()):
    raise SystemExit(f"frozen dry-run failed: {checks}")
PY

if [[ -f "$JUDGE_ROOT/summary.json" ]]; then
  echo "final summary already exists; refusing to overwrite" >&2
  exit 3
fi

cp "$0" "$JUDGE" "$JUDGE_ROOT/source_snapshot/"
{
  sha256sum \
    "$GROUNDTRUTH" \
    "$HISTORICAL" \
    "$LEGACY_EVALUATOR" \
    "$KEY_WRAPPER" \
    "$JUDGE" \
    "${AUDITS[@]}"
  find "$SELECTED_ROOT/CLIPTopK8" \
       "$SELECTED_ROOT/MMR8" \
       "$SELECTED_ROOT/VideoITG8" \
    -type f -name prediction.json -print0 \
    | sort -z \
    | xargs -0 sha256sum
} > "$JUDGE_ROOT/frozen_inputs_sha256.txt"

"$PYTHON" "$KEY_WRAPPER" \
  --backup-script "$LEGACY_EVALUATOR" \
  -- "$PYTHON" "$JUDGE" "${COMMON_ARGS[@]}"

(
  cd "$JUDGE_ROOT"
  sha256sum \
    source_snapshot/* \
    frozen_inputs_sha256.txt \
    dry_run_audit.json \
    api_results_partial.jsonl \
    results.jsonl \
    summary.json \
    > SHA256SUMS
)
touch "$JUDGE_ROOT/JUDGE_COMPLETE"
echo "[$(date -Is)] selected8 baseline judge complete"
