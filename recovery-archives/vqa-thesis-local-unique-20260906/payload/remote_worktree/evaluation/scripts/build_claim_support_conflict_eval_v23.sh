#!/usr/bin/env bash
set -euo pipefail
ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/innovation2_claim_support_conflict_v23/eval_audited"
mkdir -p "$RUN/source_snapshot"
cp "$0" "$ROOT/evaluation/tools/build_claim_support_conflict_smoke_v23.py" "$RUN/source_snapshot/"
exec "$PYTHON" "$ROOT/evaluation/tools/build_claim_support_conflict_smoke_v23.py" \
  --annotations "$ROOT/evaluation/runs/innovation1_evidence300_stage_v1/ai_review_audit/ai_reviews_merged.json" \
  --router-dataset "$ROOT/evaluation/runs/adaptive_temporal_router_evidence300_v1/router_dataset.jsonl" \
  --output-root "$RUN" --seed 2026071603 --max-workers 10 --all-eligible \
  --include-split calibration --include-split development
