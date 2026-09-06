#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
STAGE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation2_claim_verifier_v2"
EVIDENCE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_evidence300_stage_v1"
OUTPUT_ROOT="$STAGE_ROOT/smoke30_oracle_protocol_v1"

mkdir -p "$OUTPUT_ROOT/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/tools/build_claim_evidence_smoke30_v2.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/protocol_v2.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/features_v2.py" \
  "$PROJECT_ROOT/evaluation/methods/claim_evidence_verifier/metrics_v2.py" \
  "$OUTPUT_ROOT/source_snapshot/"

exec "$PYTHON" "$PROJECT_ROOT/evaluation/tools/build_claim_evidence_smoke30_v2.py" \
  --annotations "$EVIDENCE_ROOT/ai_review_audit/ai_reviews_merged.json" \
  --review-queue "$EVIDENCE_ROOT/review_materials/review_queue.jsonl" \
  --raw-result-root "$EVIDENCE_ROOT/formal_raw_uniform_v1" \
  --judge-results "$EVIDENCE_ROOT/deepseek_judge_v1/results.jsonl" \
  --output-root "$OUTPUT_ROOT" --per-type 6 --seed 20260716
