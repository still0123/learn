#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_counterfactual_dev100_v1"
DATA_DIR="$PROJECT_ROOT/data/counterfactual_dev100_v1"
RAW_ROOT="$RUN_ROOT/raw_uniform"
MMR_ROOT="$RUN_ROOT/innovation1_mmr32"
CACHE="$RUN_ROOT/innovation1_mmr32_cache/cache_shard0.jsonl"
AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_counterfactual_sufficiency_v1.py"
COLLECTOR="$PROJECT_ROOT/evaluation/eval/collect_counterfactual_judge_inputs_v1.py"
ANALYZER="$PROJECT_ROOT/evaluation/eval/analyze_counterfactual_dev100_v1.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
BACKUP_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE_INPUT="$RUN_ROOT/judge_inputs_legacy_answer_only_v1"
JUDGE_OUTPUT="$RUN_ROOT/judge_deepseek_legacy_answer_only_v1"
OVERWRITE="${OVERWRITE:-0}"

mkdir -p "$RUN_ROOT/source_snapshot"
cp "$0" "$AUDITOR" "$COLLECTOR" "$ANALYZER" "$ADAPTER" "$EVALUATOR" "$RUN_ROOT/source_snapshot/"

"$PYTHON" "$AUDITOR" --question_file "$DATA_DIR/question.json" --run_root "$RAW_ROOT" \
  --output "$RAW_ROOT/audit_complete.json" --require_complete
"$PYTHON" "$AUDITOR" --question_file "$DATA_DIR/question.json" --run_root "$MMR_ROOT" \
  --cache "$CACHE" --output "$MMR_ROOT/audit_complete.json" --require_complete

overwrite_args=(); if [[ "$OVERWRITE" == "1" ]]; then overwrite_args+=(--overwrite); fi
"$PYTHON" "$COLLECTOR" --question_file "$DATA_DIR/question.json" --raw_root "$RAW_ROOT" \
  --mmr_root "$MMR_ROOT" --output_root "$JUDGE_INPUT" "${overwrite_args[@]}"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  [[ -r "$BACKUP_EVALUATOR" ]] || { echo "missing read-only legacy evaluator backup" >&2; exit 4; }
  DEEPSEEK_API_KEY="$($PYTHON - "$BACKUP_EVALUATOR" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding='utf-8').read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'API_KEY' for t in node.targets):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
            print(node.value.value, end='')
            break
else:
    raise SystemExit('API_KEY literal missing from legacy evaluator')
PY
)"
  export DEEPSEEK_API_KEY
fi
[[ -n "$DEEPSEEK_API_KEY" ]] || { echo "empty temporary DeepSeek key" >&2; exit 5; }
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"
"$PYTHON" "$ADAPTER" \
  --run raw_uniform "$JUDGE_INPUT/raw_uniform" \
  --run raw_plus_counterfactual2 "$JUDGE_INPUT/raw_plus_counterfactual2" \
  --run innovation1_mmr32 "$JUDGE_INPUT/innovation1_mmr32" \
  --run innovation1_mmr32_plus_counterfactual2 "$JUDGE_INPUT/innovation1_mmr32_plus_counterfactual2" \
  --groundtruth-file "$DATA_DIR/groundtruth.json" --evaluator "$EVALUATOR" --output-dir "$JUDGE_OUTPUT" \
  --candidate-mode answer_only --max-workers "${MAX_WORKERS:-10}" --bootstrap-samples 10000 "${overwrite_args[@]}"
"$PYTHON" "$ANALYZER" --groundtruth_file "$DATA_DIR/groundtruth.json" \
  --results_jsonl "$JUDGE_OUTPUT/results.jsonl" --raw_trace_root "$RAW_ROOT" \
  --mmr_trace_root "$MMR_ROOT" --output_dir "$JUDGE_OUTPUT"
unset DEEPSEEK_API_KEY
(cd "$RUN_ROOT" && sha256sum source_snapshot/* > COUNTERFACTUAL_POSTPROCESS_SHA256SUMS)
echo "counterfactual_dev100_postprocess=complete"
