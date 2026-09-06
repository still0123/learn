#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
OUTPUT_ROOT="$PROJECT_ROOT/data/claim_evidence_stage1_v1"

mkdir -p "$OUTPUT_ROOT/source_snapshot"
cp "$0" \
  "$PROJECT_ROOT/evaluation/tools/build_claim_evidence_stage1_splits_v1.py" \
  "$OUTPUT_ROOT/source_snapshot/"

exec "$PYTHON" "$PROJECT_ROOT/evaluation/tools/build_claim_evidence_stage1_splits_v1.py" \
  --question-source "$PROJECT_ROOT/data/testset_question.json" \
  --groundtruth-source "$PROJECT_ROOT/data/testset_groundtruth.json" \
  --video-root "$PROJECT_ROOT/data/videos" \
  --exclude-question-file "$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json" \
  --exclude-question-file "$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_question.json" \
  --exclude-question-file "$PROJECT_ROOT/data/confirm300b_focuscontext_disjoint_prior_question.json" \
  --exclude-question-file "$PROJECT_ROOT/data/confirm300c_temporal_disjoint_prior_question.json" \
  --output-root "$OUTPUT_ROOT" --per-type-per-split 60 --seed 20260713
