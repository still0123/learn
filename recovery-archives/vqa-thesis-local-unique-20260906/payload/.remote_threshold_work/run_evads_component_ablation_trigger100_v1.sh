#!/usr/bin/env bash
set -euo pipefail

PROJECT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
BASE="${PROJECT}/data/external/evads_v1/experiments/mmr_selectrescue_external1000b_v1"
DATASET="${BASE}/full1000/trigger100_dataset"
RUN="${BASE}/component_ablation_trigger100_v1"
TOOL="${PROJECT}/evaluation/tools/infer_qwen3_samebudget_ablation_v1.py"

cd "${PROJECT}"
if [[ -e "${RUN}/FULL100_LAUNCHED" || -e "${RUN}/FULL100_COMPLETE" ]]; then
  echo "refusing duplicate full100 launch" >&2
  exit 1
fi
mkdir -p "${RUN}/full100" "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
cp "${TOOL}" "${RUN}/source_snapshot/"
sha256sum "${TOOL}" "${DATASET}"/shards/fold_*.jsonl \
  > "${RUN}/source_snapshot/INPUT_SHA256SUMS"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FULL100_LAUNCHED"

run_wave() {
  local arm="$1"
  local variant="$2"
  local method="$3"
  local status=0

  for fold in 0 1 2 3 4; do
    local gpu="$((fold + 1))"
    local output="${RUN}/full100/${arm}/fold_${fold}"
    if [[ -e "${output}" ]]; then
      echo "refusing existing output: ${output}" >&2
      return 1
    fi
    nohup "${PY}" "${TOOL}" \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --input-jsonl "${DATASET}/shards/fold_${fold}.jsonl" \
      --output-dir "${output}" \
      --base-size 512 \
      --crop-size 896 \
      --max-visual-tokens 4096 \
      --max-new-tokens 192 \
      --expected-items 20 \
      --a2-method "${method}" \
      --ablation-variant "${variant}" \
      --skip-a1 \
      > "${RUN}/logs/full100_${arm}_fold_${fold}.log" 2>&1 &
    echo "$!" > "${RUN}/pids/full100_${arm}_fold_${fold}.pid"
  done

  for fold in 0 1 2 3 4; do
    local pid
    pid="$(<"${RUN}/pids/full100_${arm}_fold_${fold}.pid")"
    if ! wait "${pid}"; then
      status=1
    fi
  done
  if [[ "${status}" -ne 0 ]]; then
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FULL100_${arm}_FAILED"
    return 1
  fi
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FULL100_${arm}_COMPLETE"
}

run_wave "ExtraGlobal12" "extra_global" "Qwen3_EVAds_ExtraGlobal12_A2"
run_wave "NoOCR12" "no_ocr" "Qwen3_EVAds_NoOCR12_A2"
run_wave "NoASR12" "no_asr" "Qwen3_EVAds_NoASR12_A2"

"${PY}" - "${RUN}" <<'PY'
import glob
import json
import os
import sys

root = sys.argv[1]
arms = {
    "ExtraGlobal12": "extra_global",
    "NoOCR12": "no_ocr",
    "NoASR12": "no_asr",
}
report = {
    "schema_version": "evads_component_ablation_trigger100_protocol_audit_v1",
    "passed": True,
    "groundtruth_read": False,
    "judge_scores_read": False,
    "arms": {},
}
base_signatures = {}
for arm, variant in arms.items():
    traces = sorted(glob.glob(f"{root}/full100/{arm}/fold_*/ques_*/a2_trace.json"))
    predictions = sorted(
        glob.glob(f"{root}/full100/{arm}/fold_*/ques_*/a2_prediction.json")
    )
    errors = []
    token_values = []
    fold_counts = {}
    for path in traces:
        trace = json.load(open(path, encoding="utf-8"))
        question_id = os.path.basename(os.path.dirname(path))
        fold = os.path.basename(os.path.dirname(os.path.dirname(path)))
        fold_counts[fold] = fold_counts.get(fold, 0) + 1
        processor = trace["processor_trace"]
        if processor.get("represented_views") != 12:
            errors.append(f"{question_id}:represented_views")
        if processor.get("secondary_frame_sampling") is not False:
            errors.append(f"{question_id}:secondary_sampling")
        token_count = int(processor.get("visual_tokens", -1))
        token_values.append(token_count)
        if token_count != 3104:
            errors.append(f"{question_id}:visual_tokens={token_count}")
        if trace.get("crop_ablation_variant") != variant:
            errors.append(f"{question_id}:variant")
        signature = tuple(trace.get("base_source_frame_indices", []))
        if question_id in base_signatures and base_signatures[question_id] != signature:
            errors.append(f"{question_id}:base_frame_mismatch")
        base_signatures[question_id] = signature
    report["arms"][arm] = {
        "trace_rows": len(traces),
        "prediction_rows": len(predictions),
        "fold_counts": fold_counts,
        "visual_token_min": min(token_values) if token_values else None,
        "visual_token_max": max(token_values) if token_values else None,
        "errors": errors,
    }
    if (
        len(traces) != 100
        or len(predictions) != 100
        or sorted(fold_counts.values()) != [20, 20, 20, 20, 20]
        or errors
    ):
        report["passed"] = False

output = f"{root}/full100_protocol_audit.json"
with open(output, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
if not report["passed"]:
    raise SystemExit(1)
PY

find "${RUN}/full100" -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > "${RUN}/FULL100_SHA256SUMS"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FULL100_COMPLETE"
