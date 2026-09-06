#!/usr/bin/env bash
set -euo pipefail
cd /data1/rmx/projectb/AdsQA-main

RUN=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
CF="$RUN/forced_full_cf123_v1"
PY=/data1/rmx/ana3/envs/ReadR/bin/python
exec >>"$CF/logs/relay.log" 2>&1
echo "relay_start=$(date -Is)"

for shard in 0 1 2 3 4 5; do
  pid=$(cat "$CF/pids/infer_shard_${shard}.pid")
  while kill -0 "$pid" 2>/dev/null; do sleep 15; done
  test -s "$CF/inference/shard_${shard}/run_summary.json"
done

cp "$CF/dataset/items_forced_full_answer_free.jsonl" "$CF/dataset/items_answer_free.jsonl"
$PY - <<'PY'
import json
from pathlib import Path
cf=Path("data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1/forced_full_cf123_v1")
items={str(x["question_id"]):int(x["fold"]) for x in map(json.loads,(cf/"dataset/items_answer_free.jsonl").read_text().splitlines())}
dst=cf/"inference_by_fold"; dst.mkdir(exist_ok=True); seen=set()
for d in (cf/"inference").glob("shard_*/*"):
    if not d.is_dir() or d.name not in items: continue
    out=dst/f"fold_{items[d.name]}"/d.name; out.parent.mkdir(parents=True,exist_ok=True)
    if not out.exists(): out.symlink_to(d.resolve(),target_is_directory=True)
    seen.add(d.name)
assert len(seen)==123,len(seen)
print({i:len(list((dst/f"fold_{i}").iterdir())) for i in range(5)})
PY

$PY evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
  --dataset-dir "$CF/dataset" \
  --inference-root "$CF/inference_by_fold" \
  --output-dir "$CF/verifier_pool" \
  --expected-a2-method ReAdR_MMR8_ForcedFullCounterfactual12_V1 \
  --candidate-method ReAdR_ForcedFullCounterfactual12_V1

for fold in 0 1 2 3 4; do
  nohup $PY evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py \
    --gpu-id "$fold" --model-dir /data1/qky/Model/Qwen3Vl-8B \
    --adapter-dir evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter \
    --input-jsonl "$CF/verifier_pool/shards/fold_${fold}.jsonl" \
    --output-dir "$CF/verifier_scores/fold_${fold}" \
    --views 8 --unified-size 448 --max-visual-tokens 4096 \
    >"$CF/logs/verifier_fold_${fold}.log" 2>&1 </dev/null &
  echo $! > "$CF/pids/verifier_fold_${fold}.pid"
done

for fold in 0 1 2 3 4; do
  pid=$(cat "$CF/pids/verifier_fold_${fold}.pid")
  while kill -0 "$pid" 2>/dev/null; do sleep 15; done
  test -s "$CF/verifier_scores/fold_${fold}/scores.jsonl"
done

$PY evaluation/tools/merge_evads_a2_scores_v2.py \
  --input-dir "$CF/verifier_pool" --shard-root "$CF/verifier_scores" \
  --output-dir "$CF/verifier_merged"
touch "$CF/INFERENCE_AND_VERIFIER_COMPLETE"
echo "relay_complete=$(date -Is)"
