#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
MODEL_PATH="${1:-/data1/rmx/projectb/models/Qwen3-32B-AWQ}"
CHECKSUM_FILE="$PROJECT_ROOT/evaluation/configs/qwen3_32b_awq_revision_0499.sha256"
RECEIPT="$MODEL_PATH/VERIFIED_SHA256SUMS"

test -d "$MODEL_PATH"
test -f "$CHECKSUM_FILE"

receipt_valid=0
if [[ -f "$RECEIPT" ]] && cmp --silent "$CHECKSUM_FILE" "$RECEIPT"; then
  receipt_valid=1
  while read -r _ file; do
    if [[ ! "$RECEIPT" -nt "$MODEL_PATH/$file" ]]; then
      receipt_valid=0
      break
    fi
  done <"$CHECKSUM_FILE"
fi

if [[ "$receipt_valid" == "1" ]]; then
  echo "qwen3_32b_awq_model_verification=receipt_valid"
  exit 0
fi

(
  cd "$MODEL_PATH"
  sha256sum --check "$CHECKSUM_FILE"
)

cp "$CHECKSUM_FILE" "$RECEIPT"
touch "$RECEIPT"

echo "qwen3_32b_awq_model_verification=complete"
