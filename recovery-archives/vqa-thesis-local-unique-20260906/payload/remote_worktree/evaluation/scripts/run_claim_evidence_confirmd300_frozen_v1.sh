#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/claim_evidence_stage1_v1"
MODEL_ROOT="$RUN_ROOT/model_v1"
DEV_GATE_ROOT="$RUN_ROOT/dev300_gate_v1"
CONFIRM_ROOT="$RUN_ROOT/confirmd300_candidates"
OUTPUT_ROOT="$RUN_ROOT/confirmd300_frozen_v1"
CHECKPOINT="$MODEL_ROOT/checkpoint.json"
THRESHOLD_CONFIG="$DEV_GATE_ROOT/dev_selected_threshold.json"
DEV_REPORT="$DEV_GATE_ROOT/raw_dev_threshold_selection.json"
APPLIER="$PROJECT_ROOT/evaluation/eval/apply_claim_evidence_verifier_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_claim_evidence_verifier_v1.py"

for path in "$CHECKPOINT" "$THRESHOLD_CONFIG" "$DEV_REPORT"; do
  [[ -s "$path" ]] || { echo "missing frozen prerequisite: $path" >&2; exit 2; }
done
"$PYTHON" - "$DEV_REPORT" <<'PY'
import json, sys
report = json.load(open(sys.argv[1], encoding="utf-8"))
if not report.get("selection", {}).get("gate", {}).get("passed"):
    raise SystemExit("Dev300 gate did not pass; Confirm-D300 is forbidden")
PY
if [[ -e "$OUTPUT_ROOT/CONFIRM_COMPLETE" && "${OVERWRITE:-0}" != "1" ]]; then
  echo "Confirm-D300 already completed; rerun is forbidden without explicit OVERWRITE=1" >&2
  exit 3
fi
threshold="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["threshold"])' "$THRESHOLD_CONFIG")"
mkdir -p "$OUTPUT_ROOT/source_snapshot"
cp "$0" "$APPLIER" "$EVALUATOR" "$OUTPUT_ROOT/source_snapshot/"
for method in raw_uniform innovation1_mmr32; do
  pairs="$CONFIRM_ROOT/postprocess/$method/pairs.jsonl"
  [[ -s "$pairs" ]] || { echo "missing Confirm-D candidate pairs: $pairs" >&2; exit 4; }
  "$PYTHON" "$APPLIER" --pair-jsonl "$pairs" --checkpoint "$CHECKPOINT" \
    --threshold-config "$THRESHOLD_CONFIG" --output-root "$OUTPUT_ROOT/$method" \
    --method-name "${method}_learned_verifier_confirmd_v1"
  "$PYTHON" "$EVALUATOR" --pair-jsonl "$pairs" \
    --decisions-jsonl "$OUTPUT_ROOT/$method/decisions.jsonl" \
    --output "$OUTPUT_ROOT/${method}_confirmd_report.json" --threshold "$threshold" \
    --min-switch-precision 0.70 --bootstrap-samples 10000 --seed 42
done
"$PYTHON" - "$OUTPUT_ROOT/CONFIRM_COMPLETE" "$CHECKPOINT" "$THRESHOLD_CONFIG" "$DEV_REPORT" <<'PY'
import hashlib, json, pathlib, sys
output = pathlib.Path(sys.argv[1])
def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
payload = {
    "schema": "adsqa_claim_evidence_confirmd_completion_v1",
    "checkpoint_sha256": sha(sys.argv[2]),
    "threshold_config_sha256": sha(sys.argv[3]),
    "dev_report_sha256": sha(sys.argv[4]),
    "policy": "single frozen Confirm-D300 run; no tuning",
}
output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
echo "claim_evidence_confirmd300=complete"
