#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
SOURCE="$ROOT/evaluation/runs/qwen3_threshold_full5320_v1"
ADAPTIVE="$SOURCE/adaptive_scale_inference_v1"
RUN="$ROOT/evaluation/runs/qwen3_threshold_response_center68_full_v1"
DATA="$RUN/dataset_v1"
FULL="$RUN/inference_full4905_v1"
RECOVERY="$RUN/decode_recovery_v1"

cd "$ROOT"
test -f "$RUN/PIPELINE_FAILED"
test -f "$RUN/DATASET_COMPLETE"
test -f "$RUN/SMOKE_AUDIT_COMPLETE"
test ! -e "$RUN/RECOVERY_V1_LAUNCHED"
for fold in 0 1 2 3 4 5; do
  test ! -e "$FULL/fold_$fold"
done
mkdir -p "$RUN/source_snapshot_recovery_v1"
cp \
  evaluation/tools/infer_qwen3_response_center68_full_v1.py \
  evaluation/tools/infer_qwen3_response_center68_full_decode_recovery_v1.py \
  evaluation/tools/audit_threshold_response_center68_full_v1.py \
  evaluation/scripts/run_threshold_response_center68_full_recovery_v1.sh \
  "$RUN/source_snapshot_recovery_v1/"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/RECOVERY_V1_LAUNCHED"
echo "$$" > "$RUN/pids/recovery_v1.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/RECOVERY_V1_FAILED"' ERR

"$PY" evaluation/tools/audit_threshold_response_center68_full_v1.py \
  --dataset-root "$DATA" --inference-root "$RUN/smoke1_v1" \
  --adaptive-root "$ADAPTIVE" --mode smoke \
  --output-dir "$RUN/protocol_audit_smoke1_recovery_v1" \
  > "$RUN/logs/audit_smoke1_recovery_v1.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/SMOKE_RECOVERY_AUDIT_COMPLETE"

pids=""
for fold in 0 1 2 3 4 5; do
  expected=818
  if [ "$fold" -ge 3 ]; then expected=817; fi
  log="$RUN/logs/full_fold${fold}_recovery_v1.log"
  pidfile="$RUN/pids/full_fold${fold}_recovery_v1.pid"
  ADSQA_DECODE_AUDIT_ROOT="$RECOVERY/full4905/fold_$fold" \
    nohup "$PY" evaluation/tools/infer_qwen3_response_center68_full_decode_recovery_v1.py \
    --gpu-id "$fold" --model-dir "$MODEL" \
    --input-jsonl "$DATA/full4905/shards/fold_${fold}.jsonl" \
    --output-dir "$FULL/fold_${fold}" \
    --base-size 512 --crop-size 896 --max-visual-tokens 4096 \
    --max-new-tokens 192 --expected-items "$expected" \
    --a2-method "Qwen3_ResponseCenter68_AVEvidenceRewrite12_A2" \
    --ablation-variant response_center68 --skip-a1 \
    > "$log" 2>&1 < /dev/null &
  pid="$!"
  echo "$pid" > "$pidfile"
  pids="$pids $pid"
done

for pid in $pids; do
  wait "$pid"
done
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/INFERENCE_COMPLETE"

"$PY" evaluation/tools/audit_threshold_response_center68_full_v1.py \
  --dataset-root "$DATA" --inference-root "$FULL" \
  --adaptive-root "$ADAPTIVE" --mode full \
  --output-dir "$RUN/protocol_audit_full4905_v1" \
  > "$RUN/logs/audit_full4905.log" 2>&1

(
  cd "$RUN"
  find dataset_v1 smoke1_v1 inference_full4905_v1 \
    protocol_audit_smoke1_v1 protocol_audit_smoke1_recovery_v1 \
    protocol_audit_full4905_v1 source_snapshot source_snapshot_recovery_v1 \
    decode_recovery_v1 -type f -print0 \
    | sort -z | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
