#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
RUN=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
PY=/data1/rmx/ana3/envs/ReadR/bin/python
SIG_PID="$RUN/pids/siglip_entropy_full500_v2.pid"
LOG="$RUN/logs/crop_or_full_v2_relay.log"

exec >>"$LOG" 2>&1
echo "relay_start=$(date -Is)"

while kill -0 "$(cat "$SIG_PID")" 2>/dev/null; do sleep 30; done
test -s "$RUN/siglip_manifest_entropy500_v2.jsonl"
test -s "$RUN/siglip_manifest_entropy500_v2.audit.json"

$PY evaluation/tools/build_evads_avfunnel_manifest_entropy_v1.py \
  --questions "$RUN/dataset/questions_answer_free.json" \
  --siglip-manifest "$RUN/siglip_manifest_entropy500_v2.jsonl" \
  --video-index-dir data/external/evads_v1/cache/video_index64_v1 \
  --output "$RUN/avfunnel_manifest_entropy500_v2.jsonl" \
  --audit "$RUN/avfunnel_manifest_entropy500_v2.audit.json" \
  --overwrite

$PY evaluation/tools/build_evads_threshold_crop_or_full_dataset_v1.py \
  --pool-dir "$RUN/a0_verifier_pool" \
  --scores "$RUN/a0_verifier_merged/scores_all.jsonl" \
  --questions "$RUN/dataset/questions_answer_free.json" \
  --av-manifest "$RUN/avfunnel_manifest_entropy500_v2.jsonl" \
  --output-dir "$RUN/threshold_crop_or_full_pool_v2" \
  --support-threshold 0.9241418242454529 \
  --expected-source-count 500 \
  --expected-trigger-count 257 \
  --minimum-trigger-count 257

$PY evaluation/tools/build_readr_crop_or_full_router_v1.py \
  --input-jsonl "$RUN/threshold_crop_or_full_pool_v2/items_answer_free.jsonl" \
  --output-jsonl "$RUN/threshold_crop_or_full_pool_v2/items_routed_answer_free.jsonl" \
  --audit-json "$RUN/threshold_crop_or_full_pool_v2/router_audit.json" \
  --expected-items 257 \
  --full-denominator 500

$PY - <<'PY'
import json
from pathlib import Path

root = Path("data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1/threshold_crop_or_full_pool_v2")
audit = json.loads((root / "router_audit.json").read_text())
rate = float(audit["crop_anchor_rate"])
if not audit.get("passed") or not 0.10 <= rate <= 0.90:
    raise SystemExit(f"unsafe crop route rate: {rate}")
rows = [json.loads(x) for x in (root / "items_routed_answer_free.jsonl").read_text().splitlines() if x.strip()]
shards = [[], []]
for i, row in enumerate(rows):
    shards[i % 2].append(row)
for i, part in enumerate(shards):
    p = root / "inference_shards" / f"shard_{i}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in part))
(root / "ROUTER_V2_COMPLETE").write_text(json.dumps({"counts": [len(x) for x in shards], "crop_anchor_rate": rate}) + "\n")
PY

run_a2() {
  local gpu="$1" shard="$2" count="$3"
  $PY evaluation/tools/infer_qwen25_ocrbox_routed_v1.py \
    --gpu-id "$gpu" \
    --model-dir /data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R \
    --input-jsonl "$RUN/threshold_crop_or_full_pool_v2/inference_shards/shard_${shard}.jsonl" \
    --output-dir "$RUN/a2_crop_or_full_v2/shard_${shard}" \
    --base-size 512 --crop-size 896 \
    --max-visual-tokens 4096 --max-new-tokens 512 \
    --expected-items "$count" \
    --a2-method ReAdR_MMR8_CropOrFull12_EntropyScaledV2 \
    --ablation-variant crop_or_full --skip-a1 --resume-existing
}

run_a2 0 0 129 & p0=$!
run_a2 1 1 128 & p1=$!
wait "$p0"
wait "$p1"

touch "$RUN/A2_CROP_OR_FULL_V2_COMPLETE"
echo "relay_complete=$(date -Is)"
