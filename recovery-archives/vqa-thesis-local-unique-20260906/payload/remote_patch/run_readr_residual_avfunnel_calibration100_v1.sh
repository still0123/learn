#!/usr/bin/env bash
# Answer-free GPU pipeline: residual evidence before multi-scale crop comparison.
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main

ROOT=evaluation/runs/readr_residual_avfunnel_calibration100_v1
DATASET="$ROOT/dataset_v2"
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
PY=/data1/rmx/ana3/envs/ReadR/bin/python
INFER=evaluation/tools/infer_readr_residual_avfunnel_decode_recovery_v1.py
BUILD=evaluation/tools/build_readr_residual_avfunnel_calibration100_v1.py
CALIB=evaluation/runs/readr_increment_pilot300_v1/inputs_v1/calibration100_questions_answer_free.json
SOURCE=evaluation/runs/readr_increment_pilot300_v1/all_candidates_for_calibration/items_answer_free.jsonl
RAW_FULL=evaluation/runs/qwen3_full_valid5320_v1/raw_features_v1/raw_features_all.jsonl
RAW_SUP=evaluation/runs/qwen3_adsqa_supplement2526_v1/raw_features_v1/raw_features_all.jsonl

mkdir -p "$ROOT/logs" "$ROOT/pids"
exec > >(tee -a "$ROOT/logs/pipeline.log") 2>&1
echo "$(date -Is) pipeline_start"

if [[ ! -f "$DATASET/dataset_audit.json" ]]; then
  if [[ -e "$DATASET" ]]; then
    echo "incomplete dataset directory exists; preserve it and stop" >&2
    exit 1
  fi
  "$PY" "$BUILD" \
    --calibration-questions "$CALIB" \
    --a2-source-items "$SOURCE" \
    --raw-features "$RAW_FULL" \
    --raw-features "$RAW_SUP" \
    --output-root "$DATASET" \
    --smoke-per-fold 5
fi

"$PY" - "$DATASET/dataset_audit.json" <<'PY'
import json, sys
a=json.load(open(sys.argv[1]))
assert a['passed'] and a['question_count']==100
assert a['development_only'] is True
assert set(a['variants']) == {'residual_mid', 'residual_avfunnel'}
print('DATASET_AUDIT_COMPLETE')
PY
touch "$ROOT/DATASET_AUDIT_COMPLETE"

run_batch() {
  local variant="$1" stage="$2" expected="$3" method="$4"
  local out="$ROOT/$stage/$variant"
  local input_dir="$DATASET/$variant/$stage"
  mkdir -p "$out" "$ROOT/pids/$stage-$variant"
  local pids=()
  for gpu in 0 1 2 3 4; do
    local shard="$input_dir/fold_${gpu}.jsonl"
    local shard_out="$out/fold_${gpu}"
    if [[ -f "$shard_out/run_summary.json" ]] && "$PY" - "$shard_out/run_summary.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))['complete']
PY
    then
      continue
    fi
    if [[ -e "$shard_out" ]] && [[ $(find "$shard_out" -mindepth 1 -maxdepth 1 | wc -l) -gt 0 ]]; then
      echo "incomplete output exists: $shard_out" >&2
      exit 1
    fi
    ADSQA_DECODE_RECOVERY_ROOT="$ROOT/decode_recovery_v1" \
    nohup "$PY" "$INFER" \
      --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$shard" --output-dir "$shard_out" \
      --base-size 512 --crop-size 896 --max-visual-tokens 4096 --max-new-tokens 192 \
      --expected-items "$expected" --a2-method "$method" --ablation-variant "$variant" --skip-a1 \
      >"$ROOT/logs/${stage}_${variant}_fold${gpu}.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$ROOT/pids/$stage-$variant/fold_${gpu}.pid"
    pids+=("$pid")
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
  "$PY" - "$out" "$expected" "$method" "$variant" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1]); expected=int(sys.argv[2]); method=sys.argv[3]; variant=sys.argv[4]
for fold in range(5):
    d=root/f'fold_{fold}'
    summary=json.load(open(d/'run_summary.json'))
    assert summary['complete'] and summary['stats']['errors']==0
    assert summary['a2_views']==12 and summary['max_visual_tokens']==4096
    assert summary['ablation_variant']==variant
    dirs=[p for p in d.iterdir() if p.is_dir() and p.name!='logs']
    assert len(dirs)==expected
    for p in dirs:
        pred=json.load(open(p/'a2_prediction.json'))
        trace=json.load(open(p/'a2_trace.json'))
        assert pred['method']==method and trace['crop_ablation_variant']==variant
        assert trace['processor_trace']['visual_tokens'] <= 4096
        assert len(trace['extra_view_plan'])==4
print(f'{root}: PROTOCOL_AUDIT_COMPLETE')
PY
  touch "$out/PROTOCOL_AUDIT_COMPLETE"
}

run_batch residual_mid smoke 5 ReAdR_ResidualMid12_A2
run_batch residual_avfunnel smoke 5 ReAdR_ResidualAVFunnel12_A2
touch "$ROOT/SMOKE_PROTOCOL_AUDIT_COMPLETE"

run_batch residual_mid shards 20 ReAdR_ResidualMid12_A2
run_batch residual_avfunnel shards 20 ReAdR_ResidualAVFunnel12_A2
touch "$ROOT/INFERENCE_COMPLETE_AWAITING_VERIFIER"
echo "$(date -Is) INFERENCE_COMPLETE_AWAITING_VERIFIER"
