#!/usr/bin/env bash
set -euo pipefail
ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/innovation2_claim_reliability_v22"
[[ $(wc -l <"$RUN/qwen_full_support/scores.jsonl") -eq 300 ]] || { echo "support scores incomplete" >&2; exit 2; }
mkdir -p "$RUN/model_gate/source_snapshot"
cp "$0" "$ROOT/evaluation/methods/claim_evidence_verifier/reliability_v22.py" \
  "$ROOT/evaluation/methods/claim_evidence_verifier/train_reliability_v22.py" "$RUN/model_gate/source_snapshot/"
exec "$PYTHON" "$ROOT/evaluation/methods/claim_evidence_verifier/train_reliability_v22.py" \
  --inputs "$RUN/dataset/input.jsonl" --labels "$RUN/dataset/labels.jsonl" \
  --support-scores "$RUN/qwen_full_support/scores.jsonl" --output-root "$RUN/model_gate"
