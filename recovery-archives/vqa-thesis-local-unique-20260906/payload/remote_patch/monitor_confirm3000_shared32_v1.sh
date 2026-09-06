#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm3000_shared32_v1"
SELECTION_ROOT="$RUN_ROOT/selection"
SMOKE_ROOT="$SELECTION_ROOT/smoke30"
PYTHON_BIN="/data1/rmx/ana3/envs/ReadR/bin/python"
LOG_FILE="$RUN_ROOT/logs/confirm3000_orchestrator.log"

cd "$PROJECT_ROOT"
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/formal"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "orchestrator_start $(date -Is) pid=$$"

count_predictions() {
    find "$SMOKE_ROOT/inference/$1" -name prediction.json -type f 2>/dev/null | wc -l | tr -d ' '
}

while true; do
    extra_count="$(count_predictions Shared32_ExtraGlobal8)"
    local_count="$(count_predictions Shared32_Local8)"
    echo "smoke_progress $(date -Is) extra=$extra_count local=$local_count"
    if [ "$extra_count" -ge 30 ] && [ "$local_count" -ge 30 ]; then
        break
    fi
    sleep 30
done

SMOKE_AUDIT="$SMOKE_ROOT/twoarm_protocol_audit.json"
if [ ! -f "$SMOKE_AUDIT" ]; then
    echo "smoke_audit_start $(date -Is)"
    "$PYTHON_BIN" "$PROJECT_ROOT/evaluation/tools/audit_qwen25_shared32_twoarm_v1.py" \
        --run-root "$SMOKE_ROOT/inference" \
        --gate-manifest "$SMOKE_ROOT/fixed_local8_manifest.jsonl" \
        --expected-count 30 \
        --output "$SMOKE_AUDIT"
fi

if ! "$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1]))["passed"])' "$SMOKE_AUDIT" | grep -qx True; then
    echo "smoke_audit_failed $(date -Is)"
    touch "$RUN_ROOT/SMOKE_FAILED"
    exit 1
fi
touch "$RUN_ROOT/SMOKE_PASSED"
echo "smoke_audit_passed $(date -Is)"

FULL_FIXED_GATE="$SELECTION_ROOT/fixed_local8_manifest.jsonl"
if [ ! -f "$FULL_FIXED_GATE" ] || [ ! -f "$SELECTION_ROOT/fixed_local8_manifest.audit.json" ]; then
    echo "full_gate_start $(date -Is) gpus=3,4,5"
    "$PROJECT_ROOT/evaluation/scripts/run_confirm3000_parallel_gate_gpu345_v1.sh" \
        > "$RUN_ROOT/logs/parallel_gate.nohup.log" 2>&1
    "$PYTHON_BIN" "$PROJECT_ROOT/evaluation/tools/materialize_confirm3000_fixed_local8_v1.py" \
        --input "$SELECTION_ROOT/full_gate_manifest.jsonl" \
        --output "$FULL_FIXED_GATE"
fi

if [ ! -f "$SELECTION_ROOT/shards/manifest.json" ]; then
    mkdir -p "$SELECTION_ROOT/shards"
    "$PYTHON_BIN" "$PROJECT_ROOT/evaluation/tools/shard_confirm3000_shared32_v1.py" \
        --input "$SELECTION_ROOT/question.json" \
        --output-dir "$SELECTION_ROOT/shards" \
        --shards 3 > "$RUN_ROOT/logs/shard_manifest.log"
fi

for spec in "3 0" "4 1" "5 2"; do
    read -r gpu_id shard_id <<< "$spec"
    marker="$RUN_ROOT/formal/worker_gpu${gpu_id}_shard${shard_id}.complete"
    pid_file="$RUN_ROOT/formal/worker_gpu${gpu_id}_shard${shard_id}.pid"
    if [ ! -f "$marker" ]; then
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo "worker_already_running $(date -Is) gpu=$gpu_id shard=$shard_id pid=$(cat "$pid_file")"
        else
            nohup "$PROJECT_ROOT/evaluation/scripts/run_confirm3000_shared32_worker_v1.sh" "$gpu_id" "$shard_id" \
                > "$RUN_ROOT/logs/worker_gpu${gpu_id}_shard${shard_id}.nohup.log" 2>&1 < /dev/null &
            echo $! > "$pid_file"
            echo "worker_started $(date -Is) gpu=$gpu_id shard=$shard_id pid=$(cat "$pid_file")"
        fi
    fi
done

while true; do
    complete_count=0
    for marker in "$RUN_ROOT"/formal/worker_gpu*_shard*.complete; do
        [ -f "$marker" ] && complete_count=$((complete_count + 1))
    done
    echo "formal_progress $(date -Is) workers_complete=$complete_count/3"
    [ "$complete_count" -eq 3 ] && break
    sleep 60
done

AUDIT="$RUN_ROOT/formal/twoarm_protocol_audit.json"
if [ ! -f "$AUDIT" ]; then
    "$PYTHON_BIN" "$PROJECT_ROOT/evaluation/tools/audit_qwen25_shared32_twoarm_v1.py" \
        --run-root "$RUN_ROOT/formal" \
        --gate-manifest "$FULL_FIXED_GATE" \
        --expected-count 3000 \
        --output "$AUDIT"
fi
if "$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1]))["passed"])' "$AUDIT" | grep -qx True; then
    touch "$RUN_ROOT/FORMAL_PROTOCOL_PASSED"
    echo "formal_protocol_passed $(date -Is)"
else
    touch "$RUN_ROOT/FORMAL_PROTOCOL_FAILED"
    echo "formal_protocol_failed $(date -Is)"
    exit 1
fi

if [ ! -f "$RUN_ROOT/POSTPROCESS_COMPLETE" ]; then
    echo "postprocess_start $(date -Is)"
    nohup "$PROJECT_ROOT/evaluation/scripts/run_confirm3000_shared32_postprocess_v1.sh" \
        > "$RUN_ROOT/logs/postprocess.nohup.log" 2>&1 < /dev/null &
    echo "postprocess_started $(date -Is) pid=$!"
else
    echo "postprocess_already_complete $(date -Is)"
fi
echo "orchestrator_complete_waiting_for_status $(date -Is)"
