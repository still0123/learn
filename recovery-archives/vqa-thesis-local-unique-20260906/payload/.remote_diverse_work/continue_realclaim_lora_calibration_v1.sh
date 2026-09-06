#!/usr/bin/env bash
set -euo pipefail

ROOT=/data1/rmx/projectb/AdsQA-main
PY=/data1/rmx/ana3/envs/ReadR/bin/python
RUN="$ROOT/evaluation/runs/innovation2_realclaim_lora_verifier_v1"
TRAIN="$RUN/full156"
CAL="$RUN/calibration240"
MODEL=/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct
INPUT="$ROOT/evaluation/runs/innovation2_realclaim300_v2_corrected_frames/inference_inputs.jsonl"
CLAIMS="$ROOT/evaluation/runs/innovation2_realclaim300_v2_corrected_frames/claims.jsonl"
SCRIPT="$ROOT/evaluation/tools/evaluate_realclaim_lora_verifier_v1.py"

mkdir -p "$CAL"

wait_for_file() {
  local path="$1"
  while [[ ! -f "$path" ]]; do sleep 30; done
}

launch_eval() {
  local gpu="$1" name="$2" adapter="${3:-}"
  local out="$CAL/$name"
  mkdir -p "$out"
  local cmd=("$PY" "$SCRIPT" --gpu-id "$gpu" --model-dir "$MODEL"
    --input-jsonl "$INPUT" --claims-jsonl "$CLAIMS" --split calibration
    --output-dir "$out" --views 8 --overwrite)
  if [[ -n "$adapter" ]]; then cmd+=(--adapter-dir "$adapter"); fi
  nohup "${cmd[@]}" >"$out/launcher.log" 2>&1 < /dev/null &
  echo "$!" >"$out/pid"
}

wait_for_file "$TRAIN/classification/complete.json"
wait_for_file "$TRAIN/pairwise/complete.json"

launch_eval 1 classification "$TRAIN/classification/adapter"
launch_eval 2 pairwise "$TRAIN/pairwise/adapter"
wait_for_file "$CAL/classification/summary.json"
wait_for_file "$CAL/pairwise/summary.json"

launch_eval 1 frozen_base
wait_for_file "$CAL/frozen_base/summary.json"

"$PY" - "$CAL" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
rows = []
for name in ("frozen_base", "classification", "pairwise"):
    value = json.loads((root / name / "summary.json").read_text())
    rows.append({"name": name, **{key: value[key] for key in (
        "rows", "auroc", "auprc_positive", "balanced_accuracy",
        "best_split_threshold", "best_split_balanced_accuracy")}})
winner = max(rows, key=lambda row: (row["auroc"], row["balanced_accuracy"]))
result = {
    "schema": "adsqa_realclaim_lora_calibration_comparison_v1",
    "not_human_gold": True,
    "development_evaluated": False,
    "rows": rows,
    "provisional_winner": winner["name"],
    "frozen_threshold": winner["best_split_threshold"],
}
(root / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
PY

touch "$CAL/COMPLETE"
