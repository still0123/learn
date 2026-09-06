#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_qwen25_temporal_diverse_local8_groupcv500_v1"
GROUNDTRUTH_FILE="$PROJECT_ROOT/evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1/groupcv5/oof_groundtruth_v1.json"
PROTOCOL_AUDIT="$RUN_ROOT/formal/protocol_audit_v1.json"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
BACKUP_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
ANALYZER="$PROJECT_ROOT/evaluation/tools/analyze_qwen25_diverse_local8_v1.py"
JUDGE_OUTPUT="$RUN_ROOT/judge_deepseek_answer_only_v1"
ANALYSIS_OUTPUT="$RUN_ROOT/analysis_diverse_local8_v1"
LOG="$RUN_ROOT/diverse_local8_postprocess.log"
INPUT_ROOT="$RUN_ROOT/judge_inputs"
OLD_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_qwen25_shared32_isolation_groupcv500_v1"
OVERWRITE="${OVERWRITE:-0}"

exec >>"$LOG" 2>&1
echo "[$(date -Is)] Shared32 postprocess started"

"$PYTHON" - "$PROTOCOL_AUDIT" "$GROUNDTRUTH_FILE" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
groundtruth = json.load(open(sys.argv[2], encoding="utf-8"))
if audit.get("passed") is not True:
    raise SystemExit("Shared32 protocol audit failed; judge blocked")
if len(groundtruth) != 500 or len({str(row["question_id"]) for row in groundtruth}) != 500:
    raise SystemExit("Shared32 groundtruth must contain 500 unique questions")
PY

if [[ -f "$JUDGE_OUTPUT/summary.json" && "$OVERWRITE" != "1" ]]; then
  echo "[$(date -Is)] judge summary already exists; refusing to overwrite"
  exit 0
fi

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" "$ANALYZER" "$ADAPTER" "$EVALUATOR" "$PROTOCOL_AUDIT" "$RUN_ROOT/source_snapshot/"

mkdir -p "$INPUT_ROOT/Shared32_Local8" "$INPUT_ROOT/Shared32_DiverseLocal8"
for fold in 0 1 2 3 4; do
  if [[ ! -e "$INPUT_ROOT/Shared32_Local8/fold_${fold}" ]]; then
    cp -al "$RUN_ROOT/formal/fold_${fold}/Shared32_Local8" "$INPUT_ROOT/Shared32_Local8/fold_${fold}"
  fi
  if [[ ! -e "$INPUT_ROOT/Shared32_DiverseLocal8/fold_${fold}" ]]; then
    cp -al "$RUN_ROOT/formal/fold_${fold}/Shared32_DiverseLocal8" "$INPUT_ROOT/Shared32_DiverseLocal8/fold_${fold}"
  fi
done

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  [[ -r "$BACKUP_EVALUATOR" ]] || {
    echo "missing read-only legacy evaluator backup; refusing to call judge" >&2
    exit 4
  }
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
    raise SystemExit("API_KEY literal missing from legacy evaluator backup")
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

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

echo "[$(date -Is)] visual audit passed; starting frozen answer-only DeepSeek judge"
"$PYTHON" "$ADAPTER" \
  --run Shared32_Local8 "$INPUT_ROOT/Shared32_Local8" \
  --run Shared32_DiverseLocal8 "$INPUT_ROOT/Shared32_DiverseLocal8" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$JUDGE_OUTPUT" \
  --candidate-mode answer_only \
  --max-workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000 \
  "${overwrite_args[@]}"

echo "[$(date -Is)] running video-cluster bootstrap analysis"
"$PYTHON" "$ANALYZER" \
  --groundtruth "$GROUNDTRUTH_FILE" \
  --judge-results "$JUDGE_OUTPUT/results.jsonl" \
  --protocol-audit "$PROTOCOL_AUDIT" \
  --output-dir "$ANALYSIS_OUTPUT" \
  --samples 10000 \
  --seed 42

unset DEEPSEEK_API_KEY
(
  cd "$RUN_ROOT"
  sha256sum source_snapshot/* > POSTPROCESS_SHA256SUMS
)
echo "[$(date -Is)] Shared32 postprocess complete"
