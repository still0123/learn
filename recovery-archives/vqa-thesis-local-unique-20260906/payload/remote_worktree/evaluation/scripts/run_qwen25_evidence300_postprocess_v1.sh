#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/qwen25_evidence300_afternoon_v1"
QUESTION_FILE="$PROJECT_ROOT/data/innovation1_evidence300_v1/question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/innovation1_evidence300_v1/groundtruth.json"
AUDIT_RAW="$RUN_ROOT/formal_raw_uniform_v1/audit_qwen25_fair_run_v1.json"
AUDIT_ADSLOT="$RUN_ROOT/formal_adslot_fixed_v1/audit_qwen25_fair_run_v1.json"
AUDIT_MARKER="$RUN_ROOT/qwen25_fair_audit_ready.marker"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
BACKUP_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE_OUTPUT="$RUN_ROOT/judge_deepseek_full_response_v1"
LOG="$RUN_ROOT/qwen25_fair_postprocess.log"
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

mkdir -p "$RUN_ROOT"
exec >>"$LOG" 2>&1
echo "[$(date -Is)] qwen25 postprocess watcher started"

while true; do
  if [[ -f "$AUDIT_MARKER" && -f "$AUDIT_RAW" && -f "$AUDIT_ADSLOT" ]]; then
    break
  fi
  echo "[$(date -Is)] waiting for raw/adslot fair audits"
  sleep 60
done

"$PYTHON" - "$AUDIT_RAW" "$AUDIT_ADSLOT" <<'PY'
import json
import sys

for path in sys.argv[1:]:
    audit = json.load(open(path, encoding="utf-8"))
    if audit.get("complete") is not True or audit.get("passed") is not True:
        raise SystemExit(f"audit failed: {path}")
    if audit.get("expected_count") != 300 or audit.get("observed_count") != 300:
        raise SystemExit(f"audit incomplete: {path}")
    if audit.get("failures"):
        raise SystemExit(f"audit has failures: {path}")
    if audit.get("model_label") != "Qwen2.5-VL-7B-Instruct":
        raise SystemExit(f"unexpected model label: {path}")
    if audit.get("expected_visual_tokens") != 16384:
        raise SystemExit(f"unexpected token budget: {path}")
print("qwen25_fair_audits=pass")
PY

if [[ -f "$JUDGE_OUTPUT/summary.json" ]]; then
  echo "[$(date -Is)] judge summary already exists; refusing to overwrite"
  exit 0
fi

[[ -r "$BACKUP_EVALUATOR" ]] || {
  echo "missing read-only legacy evaluator backup; refusing to call judge" >&2
  exit 4
}

mkdir -p "$RUN_ROOT/qwen25_postprocess_source_snapshot"
cp "$SCRIPT_PATH" "$ADAPTER" "$EVALUATOR" \
  "$PROJECT_ROOT/evaluation/tools/audit_qwen25_fair_run_v1.py" \
  "$RUN_ROOT/qwen25_postprocess_source_snapshot/"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  DEEPSEEK_API_KEY="$($PYTHON - "$BACKUP_EVALUATOR" <<'PY'
import ast
import sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "API_KEY" for target in node.targets
    ):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            print(node.value.value, end="")
            break
else:
    raise SystemExit("API_KEY literal missing from legacy evaluator")
PY
  )"
  export DEEPSEEK_API_KEY
fi
[[ -n "${DEEPSEEK_API_KEY:-}" ]] || {
  echo "empty temporary DeepSeek key; refusing to call judge" >&2
  exit 5
}
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

echo "[$(date -Is)] audits passed; starting frozen Qwen2.5 full-response DeepSeek judge"
"$PYTHON" "$ADAPTER" \
  --run raw_uniform "$RUN_ROOT/formal_raw_uniform_v1" \
  --run adslot_fixed "$RUN_ROOT/formal_adslot_fixed_v1" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$JUDGE_OUTPUT" \
  --candidate-mode full_response \
  --max-workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000

unset DEEPSEEK_API_KEY
(
  cd "$RUN_ROOT"
  sha256sum qwen25_postprocess_source_snapshot/* > QWEN25_POSTPROCESS_SHA256SUMS
)
echo "[$(date -Is)] qwen25 fair postprocess complete"
