#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
METHOD="${METHOD:?set METHOD to raw_uniform or innovation1_mmr32}"
QUESTION_FILE="${QUESTION_FILE:?set QUESTION_FILE}"
GROUNDTRUTH_FILE="${GROUNDTRUTH_FILE:?set GROUNDTRUTH_FILE}"
RUN_ROOT="${RUN_ROOT:?set RUN_ROOT}"
EXPECTED_COUNT="${EXPECTED_COUNT:?set EXPECTED_COUNT}"
TEMPORAL_CACHE="${TEMPORAL_CACHE:-}"
OVERWRITE="${OVERWRITE:-0}"
TRACE_ROOT="$RUN_ROOT/$METHOD"
POST_ROOT="$RUN_ROOT/postprocess/$METHOD"
JUDGE_INPUT="$POST_ROOT/judge_inputs"
JUDGE_OUTPUT="$POST_ROOT/judge_deepseek_legacy_answer_only_v1"
AUDITOR="$PROJECT_ROOT/evaluation/eval/audit_counterfactual_sufficiency_v1.py"
MATERIALIZER="$PROJECT_ROOT/evaluation/eval/materialize_claim_evidence_candidates_v1.py"
ADAPTER="$PROJECT_ROOT/evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_compare_new.py"
PAIR_BUILDER="$PROJECT_ROOT/evaluation/tools/build_claim_evidence_pairs_v1.py"
BACKUP_EVALUATOR="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"

case "$METHOD" in raw_uniform|innovation1_mmr32) ;; *) echo "invalid METHOD=$METHOD" >&2; exit 2 ;; esac
mkdir -p "$POST_ROOT/source_snapshot"
cp "$0" "$AUDITOR" "$MATERIALIZER" "$ADAPTER" "$EVALUATOR" "$PAIR_BUILDER" "$POST_ROOT/source_snapshot/"
cache_args=(); if [[ "$METHOD" == "innovation1_mmr32" ]]; then cache_args+=(--cache "$TEMPORAL_CACHE"); fi
"$PYTHON" "$AUDITOR" --question_file "$QUESTION_FILE" --run_root "$TRACE_ROOT" \
  --output "$POST_ROOT/audit_complete.json" --require_complete "${cache_args[@]}"
overwrite_args=(); if [[ "$OVERWRITE" == "1" ]]; then overwrite_args+=(--overwrite); fi
"$PYTHON" "$MATERIALIZER" --trace-root "$TRACE_ROOT" --groundtruth-file "$GROUNDTRUTH_FILE" \
  --output-root "$JUDGE_INPUT" --source-method "$METHOD" --expected-count "$EXPECTED_COUNT"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  [[ -r "$BACKUP_EVALUATOR" ]] || { echo "missing read-only legacy evaluator backup" >&2; exit 4; }
  DEEPSEEK_API_KEY="$($PYTHON - "$BACKUP_EVALUATOR" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "API_KEY" for target in node.targets):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
            print(node.value.value, end="")
            break
else:
    raise SystemExit("API_KEY literal missing from legacy evaluator")
PY
)"
  export DEEPSEEK_API_KEY
fi
[[ -n "$DEEPSEEK_API_KEY" ]] || { echo "empty temporary DeepSeek key" >&2; exit 5; }
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
export DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-chat}"
"$PYTHON" "$ADAPTER" \
  --run "${METHOD}_initial_candidate" "$JUDGE_INPUT/${METHOD}_initial_candidate" \
  --run "${METHOD}_rescue_candidate" "$JUDGE_INPUT/${METHOD}_rescue_candidate" \
  --run "${METHOD}_conditional_selector" "$JUDGE_INPUT/${METHOD}_conditional_selector" \
  --groundtruth-file "$GROUNDTRUTH_FILE" --evaluator "$EVALUATOR" --output-dir "$JUDGE_OUTPUT" \
  --candidate-mode answer_only --max-workers "${MAX_WORKERS:-10}" --bootstrap-samples 10000 "${overwrite_args[@]}"
unset DEEPSEEK_API_KEY

"$PYTHON" "$PAIR_BUILDER" --trace-root "$TRACE_ROOT" --groundtruth-file "$GROUNDTRUTH_FILE" \
  --judge-results-jsonl "$JUDGE_OUTPUT/results.jsonl" --source-method "$METHOD" \
  --initial-judge-method "${METHOD}_initial_candidate" --rescue-judge-method "${METHOD}_rescue_candidate" \
  --output-jsonl "$POST_ROOT/pairs.jsonl" --manifest-output "$POST_ROOT/pair_manifest.json" \
  --expected-count "$EXPECTED_COUNT"
echo "claim_evidence_judge_and_pairs=complete method=$METHOD"
