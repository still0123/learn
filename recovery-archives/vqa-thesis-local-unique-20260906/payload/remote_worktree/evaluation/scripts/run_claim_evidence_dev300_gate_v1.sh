#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/claim_evidence_stage1_v1"
MODEL_ROOT="$RUN_ROOT/model_v1"
DEV_ROOT="$RUN_ROOT/dev300_candidates"
OUTPUT_ROOT="$RUN_ROOT/dev300_gate_v1"
CHECKPOINT="$MODEL_ROOT/checkpoint.json"
APPLIER="$PROJECT_ROOT/evaluation/eval/apply_claim_evidence_verifier_v1.py"
EVALUATOR="$PROJECT_ROOT/evaluation/eval/evaluate_claim_evidence_verifier_v1.py"
RAW_PAIRS="$DEV_ROOT/postprocess/raw_uniform/pairs.jsonl"
MMR_PAIRS="$DEV_ROOT/postprocess/innovation1_mmr32/pairs.jsonl"
THRESHOLD_CONFIG="$OUTPUT_ROOT/dev_selected_threshold.json"

for path in "$CHECKPOINT" "$RAW_PAIRS" "$MMR_PAIRS"; do
  [[ -s "$path" ]] || { echo "missing required Dev input: $path" >&2; exit 2; }
done
mkdir -p "$OUTPUT_ROOT/source_snapshot"
cp "$0" "$APPLIER" "$EVALUATOR" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/features.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/numpy_mlp.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/metrics.py" \
  "$OUTPUT_ROOT/source_snapshot/"

# Threshold selection is preregistered on Raw Dev300 only. The same threshold is
# then frozen for both Raw and MMR32 parents and for Confirm-D300.
"$PYTHON" "$APPLIER" --pair-jsonl "$RAW_PAIRS" --checkpoint "$CHECKPOINT" \
  --output-root "$OUTPUT_ROOT/raw_probe" --method-name raw_learned_verifier_probe_v1
"$PYTHON" "$EVALUATOR" --pair-jsonl "$RAW_PAIRS" \
  --decisions-jsonl "$OUTPUT_ROOT/raw_probe/decisions.jsonl" \
  --output "$OUTPUT_ROOT/raw_dev_threshold_selection.json" \
  --threshold-output "$THRESHOLD_CONFIG" --select-threshold \
  --min-switch-precision 0.70 --bootstrap-samples 10000 --seed 42

for method in raw_uniform innovation1_mmr32; do
  if [[ "$method" == "raw_uniform" ]]; then pairs="$RAW_PAIRS"; else pairs="$MMR_PAIRS"; fi
  "$PYTHON" "$APPLIER" --pair-jsonl "$pairs" --checkpoint "$CHECKPOINT" \
    --threshold-config "$THRESHOLD_CONFIG" --output-root "$OUTPUT_ROOT/$method" \
    --method-name "${method}_learned_verifier_v1"
  "$PYTHON" "$EVALUATOR" --pair-jsonl "$pairs" \
    --decisions-jsonl "$OUTPUT_ROOT/$method/decisions.jsonl" \
    --output "$OUTPUT_ROOT/${method}_fixed_threshold_report.json" \
    --threshold "$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["threshold"])' "$THRESHOLD_CONFIG")" \
    --min-switch-precision 0.70 --bootstrap-samples 10000 --seed 42
done
echo "claim_evidence_dev300_gate=complete"
