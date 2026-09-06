#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
SOURCE="${1:-/data1/rmx/projectb/models/.Qwen3-32B-AWQ-modelscope-probe}"
TARGET="${2:-/data1/rmx/projectb/models/Qwen3-32B-AWQ}"
VERIFY="$PROJECT_ROOT/evaluation/scripts/verify_qwen3_32b_awq_model.sh"

"$VERIFY" "$SOURCE"

for shard in \
  model-00001-of-00004.safetensors \
  model-00002-of-00004.safetensors \
  model-00003-of-00004.safetensors \
  model-00004-of-00004.safetensors; do
  mv -- "$SOURCE/$shard" "$TARGET/$shard"
done

rm -f -- "$TARGET"/model-*.safetensors.aria2
"$VERIFY" "$TARGET"

echo "qwen3_32b_awq_verified_install=complete"
