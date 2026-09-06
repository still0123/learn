#!/usr/bin/env bash
set -euo pipefail
ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/innovation2_claim_support_conflict_v23"
$PYTHON "$ROOT/evaluation/tools/materialize_claim_support_conflict_pairs_v23.py" \
  --audited-triplets "$RUN/smoke30/triplets_audited.jsonl" \
  --evidence-inputs "$ROOT/evaluation/runs/innovation2_claim_reliability_v22/dataset/input.jsonl" \
  --output-root "$RUN/pair_smoke29"
$PYTHON "$ROOT/evaluation/methods/claim_evidence_verifier/inference_intervention_smoke_v2.py" \
  --gpu-id 4 --input-jsonl "$RUN/pair_smoke29/input.jsonl" \
  --oracle-jsonl "$RUN/pair_smoke29/input.jsonl" --output-root "$RUN/pair_smoke29/qwen_support" --full-only
$PYTHON "$ROOT/evaluation/eval/evaluate_claim_support_conflict_pairs_v23.py" \
  --scores "$RUN/pair_smoke29/qwen_support/scores.jsonl" --labels "$RUN/pair_smoke29/labels.jsonl" \
  --output "$RUN/pair_smoke29/evaluation.json"
