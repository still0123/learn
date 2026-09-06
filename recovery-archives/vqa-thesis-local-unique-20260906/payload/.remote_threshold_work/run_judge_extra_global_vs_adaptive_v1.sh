#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/qwen3_threshold_samebudget_ablation_full_v1"
JUDGE_ROOT="$RUN/judge_extraglobal_vs_adaptive_v1"
PREFLIGHT="$JUDGE_ROOT/preflight_v1"
RESULTS="$JUDGE_ROOT/results_v1"
AUTH="$JUDGE_ROOT/authorization_manifest_v1.json"
GROUNDTRUTH="$ROOT/data/adsqa_full_valid5320_v1/private_references/groundtruth.json"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="$ROOT/evaluation/tools/judge_extra_global_vs_adaptive_v1.py"

cd "$ROOT"
test -f "$PREFLIGHT/dry_run_audit.json"
test ! -e "$RUN/JUDGE_EXTRAGLOBAL_ADAPTIVE_COMPLETE"
test ! -e "$RUN/JUDGE_EXTRAGLOBAL_ADAPTIVE_LAUNCHED"
mkdir -p "$RESULTS/source_snapshot" "$RUN/pids"
cp "$JUDGE" evaluation/scripts/run_judge_extra_global_vs_adaptive_v1.sh "$RESULTS/source_snapshot/"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/JUDGE_EXTRAGLOBAL_ADAPTIVE_LAUNCHED"
echo "$$" > "$RUN/pids/judge_extraglobal_vs_adaptive_v1.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/JUDGE_EXTRAGLOBAL_ADAPTIVE_FAILED"' ERR

"$PY" - "$AUTH" "$GROUNDTRUTH" "$PREFLIGHT/candidates_answer_free.jsonl" +  "$PREFLIGHT/dry_run_audit.json" "$PREFLIGHT/pending_candidates_answer_only.jsonl" +  "$PREFLIGHT/reused_scores.jsonl" "$PREFLIGHT/cache_conflicts.jsonl" "$LEGACY" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

names = (
    "groundtruth_sha256",
    "candidates_sha256",
    "preflight_sha256",
    "pending_sha256",
    "reuse_sha256",
    "conflicts_sha256",
    "legacy_evaluator_sha256",
)
paths = [Path(value) for value in sys.argv[2:]]
def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()
payload = {
    "schema_version": "adsqa_extra_global_vs_adaptive_authorization_v1",
    "authorized_new_api_call_count": 2804,
    "automatic_retries": 0,
    "input_sha256": dict(zip(names, (digest(path) for path in paths))),
}
target = Path(sys.argv[1])
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

"$PY" "$JUDGE" +  --groundtruth "$GROUNDTRUTH" +  --candidates "$PREFLIGHT/candidates_answer_free.jsonl" +  --preflight-root "$PREFLIGHT" +  --authorization-manifest "$AUTH" +  --legacy-evaluator "$LEGACY" +  --output-dir "$RESULTS" +  --workers 10 +  --bootstrap-samples 10000 +  --validate-only

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  DEEPSEEK_API_KEY="$("$PY" - "$LEGACY" <<'PY'
import ast
import sys

tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
keys = [
    node.value
    for node in ast.walk(tree)
    if isinstance(node, ast.Constant)
    and isinstance(node.value, str)
    and node.value.startswith("sk-")
    and len(node.value) > 20
]
if len(set(keys)) != 1:
    raise SystemExit("expected exactly one embedded DeepSeek key")
print(keys[0], end="")
PY
  )"
  export DEEPSEEK_API_KEY
fi
[[ -n "${DEEPSEEK_API_KEY:-}" ]]
trap 'unset DEEPSEEK_API_KEY' EXIT

"$PY" "$JUDGE" +  --groundtruth "$GROUNDTRUTH" +  --candidates "$PREFLIGHT/candidates_answer_free.jsonl" +  --preflight-root "$PREFLIGHT" +  --authorization-manifest "$AUTH" +  --legacy-evaluator "$LEGACY" +  --output-dir "$RESULTS" +  --workers 10 +  --bootstrap-samples 10000

(
  cd "$JUDGE_ROOT"
  find preflight_v1 results_v1 authorization_manifest_v1.json -type f -print0 +    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/JUDGE_EXTRAGLOBAL_ADAPTIVE_COMPLETE"
