#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
OUT_DIR="$PROJECT_ROOT/data/counterfactual_dev100_v1"
mkdir -p "$OUT_DIR"

exec "$PYTHON" "$PROJECT_ROOT/evaluation/tools/build_counterfactual_dev100_v1.py" \
  --train_file "$PROJECT_ROOT/data/train.json" \
  --video_root "$PROJECT_ROOT/data/videos" \
  --question_output "$OUT_DIR/question.json" \
  --groundtruth_output "$OUT_DIR/groundtruth.json" \
  --manifest_output "$OUT_DIR/manifest.json" \
  --exclude_question_files \
    "$PROJECT_ROOT/data/pilot50_validanswer_balanced5x10_seed42_uniquevideo_question.json" \
    "$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_question.json" \
    "$PROJECT_ROOT/data/confirm300b_focuscontext_disjoint_prior_question.json" \
    "$PROJECT_ROOT/data/confirm300c_temporal_disjoint_prior_question.json" \
    "$PROJECT_ROOT/data/testset_question.json" \
  --expected_count 100
