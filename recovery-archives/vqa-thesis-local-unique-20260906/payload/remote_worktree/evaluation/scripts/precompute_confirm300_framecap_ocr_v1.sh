#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RAPIDOCR_SITE="/data1/rmx/tools/adsqa_rapidocr"
TOOL="$PROJECT_ROOT/evaluation/tools/precompute_ocr_evidence.py"
QUESTION_FILE="$PROJECT_ROOT/data/confirm300_validanswer_disjoint_pilot50_question.json"
RUN_ID="${1:-20260711_v1}"
EVIDENCE_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300_${RUN_ID}/av_v1_framecap1"
OUTPUT="$PROJECT_ROOT/evaluation/cache/ocr/confirm300_framecap1_rapidocr_v1.json"
LOG="$PROJECT_ROOT/evaluation/runs/innovation1_confirm300_${RUN_ID}/logs/precompute_confirm300_ocr.log"

test -d "$RAPIDOCR_SITE/rapidocr"
test -d "$EVIDENCE_ROOT"
mkdir -p "$(dirname "$OUTPUT")" "$(dirname "$LOG")"

PYTHONPATH="$RAPIDOCR_SITE${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$TOOL" \
  --question-file "$QUESTION_FILE" \
  --evidence-root "$EVIDENCE_ROOT" \
  --video-root "$PROJECT_ROOT/data/videos" \
  --output "$OUTPUT" \
  --workers 8 \
  --threads-per-worker 4 \
  --min-score 0.35 \
  2>&1 | tee "$LOG"

sha256sum "$OUTPUT" > "$OUTPUT.sha256"
echo "confirm300_framecap_ocr=complete"
