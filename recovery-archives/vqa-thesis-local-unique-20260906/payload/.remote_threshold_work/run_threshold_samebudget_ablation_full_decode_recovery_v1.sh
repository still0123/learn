#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
RUN="$ROOT/evaluation/runs/qwen3_threshold_samebudget_ablation_full_v1"
ARMS="$RUN/arms_v1"
INFERENCE="$RUN/inference_full4905_v1"
AUDIT="$RUN/protocol_audit_full4905_v1"
RECOVERY_AUDIT="$RUN/decode_recovery_v1"
HISTORY="$RUN/recovery_history_v1"

cd "$ROOT"
test -f "$RUN/PIPELINE_FAILED_extra_global"
test ! -e "$RUN/RECOVERY_PIPELINE_LAUNCHED"
mkdir -p "$RUN/source_snapshot_decode_recovery" "$HISTORY"
cp evaluation/tools/infer_qwen3_samebudget_ablation_decode_recovery_v1.py \
  evaluation/scripts/run_threshold_samebudget_ablation_full_decode_recovery_v1.sh \
  "$RUN/source_snapshot_decode_recovery/"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/RECOVERY_PIPELINE_LAUNCHED"

for fold in 0 1 2 3 4 5; do
  output="$INFERENCE/extra_global/fold_$fold"
  history="$HISTORY/extra_global/fold_$fold"
  mkdir -p "$history"
  for name in run_config.json run_summary.json; do
    if [ -f "$output/$name" ]; then
      cp "$output/$name" "$history/$name.pre_recovery"
    fi
  done
  if [ -f "$output/logs/errors.jsonl" ]; then
    mv "$output/logs/errors.jsonl" "$history/errors_initial_decord_failure.jsonl"
  fi
done

run_wave() {
  variant="$1"
  resume="$2"
  pids=""
  for fold in 0 1 2 3 4 5; do
    expected=818
    if [ "$fold" -ge 3 ]; then expected=817; fi
    output="$INFERENCE/$variant/fold_$fold"
    log="$RUN/logs/$variant-fold$fold-decode-recovery.log"
    pidfile="$RUN/pids/$variant-fold$fold-decode-recovery.pid"
    resume_arg=""
    if [ "$resume" = "true" ]; then resume_arg="--resume-existing"; fi
    ADSQA_DECODE_AUDIT_ROOT="$RECOVERY_AUDIT/$variant/fold_$fold" \
      nohup "$PY" evaluation/tools/infer_qwen3_samebudget_ablation_decode_recovery_v1.py \
        --gpu-id "$fold" --model-dir "$MODEL" \
        --input-jsonl "$ARMS/full4905/$variant/shards/fold_$fold.jsonl" \
        --output-dir "$output" \
        --base-size 512 --crop-size 896 --max-visual-tokens 4096 \
        --max-new-tokens 192 --expected-items "$expected" \
        --a2-method "Qwen3_$variant_AVEvidenceRewrite12_A2" \
        --ablation-variant "$variant" --skip-a1 $resume_arg \
        > "$log" 2>&1 < /dev/null &
    pid="$!"
    echo "$pid" > "$pidfile"
    pids="$pids $pid"
  done
  for pid in $pids; do
    if ! wait "$pid"; then
      date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/RECOVERY_PIPELINE_FAILED_$variant"
      exit 1
    fi
  done
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/WAVE-$variant-COMPLETE"
}

run_wave extra_global true
run_wave no_ocr false
run_wave no_asr false

"$PY" evaluation/tools/audit_threshold_samebudget_ablation_full_v1.py \
  --dataset-root "$ARMS" --inference-root "$INFERENCE" --output-dir "$AUDIT" \
  > "$RUN/logs/audit_full4905.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
