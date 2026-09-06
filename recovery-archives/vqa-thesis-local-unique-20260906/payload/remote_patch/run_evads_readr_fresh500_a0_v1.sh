#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
run=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
readr_python=/data1/rmx/ana3/envs/ReadR/bin/python
questions="$run/dataset/questions_answer_free.json"
mmr_manifest="$run/siglip_mmr8_manifest500.jsonl"
a0_dir="$run/a0_mmr8"

mkdir -p "$run/logs" "$run/pids"
while true; do
  gpu=""
  for candidate in 1 2 3 4 5; do
    active=$(nvidia-smi -i "$candidate" --query-compute-apps=pid --format=csv,noheader,nounits | sed '/^[[:space:]]*$/d' | wc -l)
    free=$(nvidia-smi -i "$candidate" --query-gpu=memory.free --format=csv,noheader,nounits | tr -dc '0-9')
    if [[ "$active" -eq 0 && "$free" -ge 26000 ]]; then
      gpu="$candidate"
      break
    fi
  done
  if [[ -n "$gpu" ]]; then
    break
  fi
  sleep 30
done
printf '%s\n' "$gpu" > "$run/pids/a0_gpu.txt"

if [[ ! -f "$run/MMR8_MANIFEST_COMPLETE" ]]; then
  python3 evaluation/tools/build_evads_siglip_mmr8_manifest_compat_v1.py \
    --gpu-id "$gpu" \
    --questions "$questions" \
    --video-index-dir data/external/evads_v1/cache/video_index64_v1 \
    --video-root data/external/evads_v1/videos_unpacked/videos \
    --output "$mmr_manifest"
  touch "$run/MMR8_MANIFEST_COMPLETE"
fi

"$readr_python" evaluation/tools/infer_evads_qwen25_evidence8_v2.py \
  --gpu-id "$gpu" \
  --questions "$questions" \
  --manifest "$mmr_manifest" \
  --method ReAdR_EVAdsFresh500_MMR8 \
  --frame-field siglip_mmr8_frame_indices \
  --video-root data/external/evads_v1/videos_unpacked/videos \
  --output-dir "$a0_dir" \
  --model-dir /data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R \
  --unified-size 512 \
  --max-visual-tokens 1296 \
  --max-new-tokens 512 \
  --min-free-memory-mib 26000
touch "$run/A0_MMR8_INFERENCE_COMPLETE"
