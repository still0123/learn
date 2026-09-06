#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
run=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
questions="$run/dataset/questions_answer_free.json"
siglip_manifest="$run/smoke20/siglip_manifest_entropy20.jsonl"
av_manifest="$run/smoke20/avfunnel_manifest_entropy20.jsonl"
full_siglip_manifest="$run/siglip_manifest_entropy500.jsonl"
full_av_manifest="$run/avfunnel_manifest_entropy500.jsonl"

mkdir -p "$run/smoke20" "$run/logs" "$run/pids"

while true; do
  selected=$(nvidia-smi --query-gpu=index,memory.free,utilization.gpu --format=csv,noheader,nounits \
    | awk -F, '$1 >= 1 && $1 <= 5 && $2 + 0 >= 12000 {gsub(/ /,"",$1); gsub(/ /,"",$3); print $1, $3}' \
    | sort -k2,2n | head -n1 | awk '{print $1}')
  if [[ -n "$selected" ]]; then
    break
  fi
  sleep 60
done

printf '%s\n' "$selected" > "$run/pids/preflight_gpu.txt"
python3 evaluation/tools/build_evads_siglip_manifest_entropy_v1.py \
  --gpu-id "$selected" \
  --questions "$questions" \
  --video-index-dir data/external/evads_v1/cache/video_index64_v1 \
  --video-root data/external/evads_v1/videos_unpacked/videos \
  --output "$siglip_manifest" \
  --max-items 20 \
  --allow-shared-gpu \
  --min-free-memory-mib 12000

python3 evaluation/tools/build_evads_avfunnel_manifest_entropy_v1.py \
  --questions "$questions" \
  --siglip-manifest "$siglip_manifest" \
  --video-index-dir data/external/evads_v1/cache/video_index64_v1 \
  --output "$av_manifest" \
  --audit "$run/smoke20/avfunnel_manifest_entropy20.audit.json" \
  --max-items 20

touch "$run/SMOKE20_SPATIAL_MANIFEST_COMPLETE"

python3 evaluation/tools/build_evads_siglip_manifest_entropy_v1.py \
  --gpu-id "$selected" \
  --questions "$questions" \
  --video-index-dir data/external/evads_v1/cache/video_index64_v1 \
  --video-root data/external/evads_v1/videos_unpacked/videos \
  --output "$full_siglip_manifest" \
  --allow-shared-gpu \
  --min-free-memory-mib 12000

python3 evaluation/tools/build_evads_avfunnel_manifest_entropy_v1.py \
  --questions "$questions" \
  --siglip-manifest "$full_siglip_manifest" \
  --video-index-dir data/external/evads_v1/cache/video_index64_v1 \
  --output "$full_av_manifest" \
  --audit "$run/avfunnel_manifest_entropy500.audit.json"

touch "$run/FULL500_SPATIAL_MANIFEST_COMPLETE"
