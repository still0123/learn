#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main

ROOT=evaluation/runs/readr_ocrbox_routed_confirm_v1
INPUT="$ROOT/dataset/items_answer_free.jsonl"
MODEL=/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R
PY=/data1/rmx/ana3/envs/ReadR/bin/python
INFER=evaluation/tools/infer_qwen25_ocrbox_routed_v1.py

mkdir -p "$ROOT/logs" "$ROOT/pids" "$ROOT/locks"
exec > >(tee -a "$ROOT/logs/pipeline.log") 2>&1

is_idle() {
  local gpu="$1" free util procs
  free=$(nvidia-smi --id="$gpu" --query-gpu=memory.free --format=csv,noheader,nounits | tr -d ' ')
  util=$(nvidia-smi --id="$gpu" --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d ' ')
  procs=$(nvidia-smi --id="$gpu" --query-compute-apps=pid --format=csv,noheader,nounits | sed '/^[[:space:]]*$/d' | wc -l)
  [[ "$free" -ge 26000 && "$util" -le 5 && "$procs" -eq 0 ]]
}

acquire_gpu() {
  local arm="$1"
  while true; do
    for gpu in 0 1 2 3 4 5; do
      if is_idle "$gpu" && mkdir "$ROOT/locks/gpu_${gpu}" 2>/dev/null; then
        echo "$gpu"
        return
      fi
    done
    echo "$(date -Is) $arm waiting_for_idle_gpu" >&2
    sleep 300
  done
}

run_arm() {
  local arm="$1" variant="$2" method="$3" gpu
  gpu=$(acquire_gpu "$arm")
  echo "$gpu" > "$ROOT/pids/${arm}.gpu"
  echo "$(date -Is) start $arm gpu=$gpu"
  set +e
  "$PY" "$INFER" \
    --gpu-id "$gpu" --model-dir "$MODEL" --input-jsonl "$INPUT" \
    --output-dir "$ROOT/$arm" --base-size 512 --crop-size 896 \
    --max-visual-tokens 4096 --max-new-tokens 192 --expected-items 38 \
    --a2-method "$method" --ablation-variant "$variant" --skip-a1 \
    > "$ROOT/logs/${arm}.log" 2>&1
  status=$?
  set -e
  rmdir "$ROOT/locks/gpu_${gpu}" || true
  if [[ "$status" -ne 0 ]]; then
    touch "$ROOT/${arm}_FAILED"
    return "$status"
  fi
  touch "$ROOT/${arm}_COMPLETE"
}

run_arm ocr_box_crop ocr_box_crop ReAdR_OCRBoxCrop12_A2 &
crop_pid=$!
echo "$crop_pid" > "$ROOT/pids/ocr_box_crop.scheduler.pid"
sleep 5
run_arm ocr_box_full ocr_box_full ReAdR_OCRMomentFull12_Control &
full_pid=$!
echo "$full_pid" > "$ROOT/pids/ocr_box_full.scheduler.pid"

wait "$crop_pid"
wait "$full_pid"

"$PY" - "$ROOT" <<'PY'
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
arms = {
    "ocr_box_crop": "ReAdR_OCRBoxCrop12_A2",
    "ocr_box_full": "ReAdR_OCRMomentFull12_Control",
}
traces = {}
for arm, method in arms.items():
    summary = json.load(open(root / arm / "run_summary.json"))
    assert summary["complete"] and summary["stats"]["errors"] == 0
    items = [path for path in (root / arm).iterdir() if path.is_dir() and path.name != "logs"]
    assert len(items) == 38
    traces[arm] = {}
    for item in items:
        pred = json.load(open(item / "a2_prediction.json"))
        trace = json.load(open(item / "a2_trace.json"))
        assert pred["method"] == method
        assert trace["processor_trace"]["represented_views"] == 12
        assert trace["processor_trace"]["visual_tokens"] <= 4096
        assert len(trace["extra_view_plan"]) == 4
        traces[arm][item.name] = trace

assert set(traces["ocr_box_crop"]) == set(traces["ocr_box_full"])
for qid in traces["ocr_box_crop"]:
    crop = traces["ocr_box_crop"][qid]
    full = traces["ocr_box_full"][qid]
    assert crop["base_source_frame_indices"] == full["base_source_frame_indices"]
    assert [x["source_frame_index"] for x in crop["extra_view_plan"]] == [
        x["source_frame_index"] for x in full["extra_view_plan"]
    ]
    assert crop["processor_trace"]["visual_tokens"] == full["processor_trace"]["visual_tokens"]

audit = {
    "schema_version": "readr_ocrbox_routed_confirm38_protocol_v1",
    "passed": True,
    "question_count": 38,
    "paired_same_base_frames": True,
    "paired_same_extra_moments": True,
    "paired_equal_visual_tokens": True,
    "views": 12,
    "max_visual_tokens": 4096,
    "answers_read": False,
    "judge_called": False,
}
(root / "protocol_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
print(json.dumps(audit, indent=2))
PY

touch "$ROOT/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
echo "$(date -Is) inference_complete_awaiting_judge_authorization"
