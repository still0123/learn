#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/lightweight_temporal_qwen_nested_pilot50_v1"
SHARD_ROOT="$RUN_ROOT/shards"
RAW_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_validanswer_pilot50_20260711_v1/raw_uniform"
QUESTION_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json"
GROUNDTRUTH_FILE="$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_groundtruth.json"
AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_visual_protocol.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
AUDIT_OUTPUT="$RUN_ROOT/audit_visual_protocol.json"
JUDGE_OUTPUT="$RUN_ROOT/judge_deepseek_legacy_answer_only_v1"
OVERWRITE="${OVERWRITE:-0}"

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" "$AUDITOR" "$ADAPTER" "$EVALUATOR" "$RUN_ROOT/source_snapshot/"

"$PYTHON" "$AUDITOR" \
  --question-file "$QUESTION_FILE" \
  --run raw_uniform "$RAW_ROOT" \
  --run lightweight_nested "$SHARD_ROOT" \
  --expected-frames 32 \
  --expected-tokens 11664 \
  --output "$AUDIT_OUTPUT"

"$PYTHON" - "$AUDIT_OUTPUT" <<'PY'
import json
import sys

audit = json.load(open(sys.argv[1], encoding="utf-8"))
if not audit.get("all_valid"):
    raise SystemExit("visual protocol audit failed; DeepSeek judge is blocked")
PY

KEY_FILE="${DEEPSEEK_API_KEY_FILE:-$HOME/.config/adsqa/deepseek_api_key}"
if [[ -z "${DEEPSEEK_API_KEY:-}" && -f "$KEY_FILE" ]]; then
  key_mode="$(stat -c '%a' "$KEY_FILE")"
  if [[ "$key_mode" != "600" && "$key_mode" != "400" ]]; then
    echo "Refusing insecure DeepSeek key file mode $key_mode: $KEY_FILE" >&2
    exit 4
  fi
  IFS= read -r DEEPSEEK_API_KEY <"$KEY_FILE"
  export DEEPSEEK_API_KEY
fi
: "${DEEPSEEK_API_KEY:?set DEEPSEEK_API_KEY or create mode-600 $KEY_FILE after visual audit passes}"
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"

overwrite_args=()
if [[ "$OVERWRITE" == "1" ]]; then
  overwrite_args+=(--overwrite)
fi

"$PYTHON" "$ADAPTER" \
  --run raw_uniform "$RAW_ROOT" \
  --run lightweight_nested "$SHARD_ROOT" \
  --groundtruth-file "$GROUNDTRUTH_FILE" \
  --evaluator "$EVALUATOR" \
  --output-dir "$JUDGE_OUTPUT" \
  --candidate-mode answer_only \
  --max-workers "${MAX_WORKERS:-10}" \
  --bootstrap-samples 10000 \
  "${overwrite_args[@]}"

(
  cd "$RUN_ROOT"
  sha256sum source_snapshot/* > POSTPROCESS_SHA256SUMS
)
echo "lightweight_temporal_postprocess=complete"
