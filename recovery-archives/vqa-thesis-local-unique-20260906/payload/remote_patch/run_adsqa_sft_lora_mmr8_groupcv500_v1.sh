#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct"
BASE="${ROOT}/evaluation/runs/adsqa_sft_lora_groupcv500_v1"
RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_mmr8_groupcv500_v1"
INPUTS="${RUN}/inputs_v1"
MANIFEST="${INPUTS}/mmr8_manifest.jsonl"
INFER="${ROOT}/evaluation/tools/infer_adsqa_answer_lora_qwen25_selected8_v1.py"
AUDIT="${ROOT}/evaluation/tools/audit_adsqa_selected8_inference_v1.py"

mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
cp "$0" "${INFER}" "${AUDIT}" \
  "${ROOT}/evaluation/tools/prepare_adsqa_sft_lora_mmr8_groupcv500_v1.py" \
  "${RUN}/source_snapshot/"

if [[ ! -f "${INPUTS}/audit.json" ]]; then
  "${PY}" "${ROOT}/evaluation/tools/prepare_adsqa_sft_lora_mmr8_groupcv500_v1.py" \
    --splits-root "${BASE}/splits_v2" \
    --source-manifest "${ROOT}/evaluation/runs/qwen25_final_arch_groupcv500_v1/inputs_v1/mmr8_manifest.jsonl" \
    --output-dir "${INPUTS}"
fi

"${PY}" - "${INPUTS}/audit.json" <<'PY'
import json
import sys
audit = json.load(open(sys.argv[1], encoding="utf-8"))
if audit.get("passed") is not True or audit.get("answer_or_outcome_fields_used") is not False:
    raise SystemExit("MMR8 input audit failed")
PY

run_fold() {
  local fold="$1"
  local gpu="$2"
  local questions="$3"
  local output="$4"
  local expected="$5"
  local adapter="${BASE}/oof500_v2/fold_${fold}/train/adapter"
  "${PY}" "${INFER}" \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${adapter}" \
    --method "AdsSFTLoRA_MMR8" \
    --question-file "${questions}" \
    --selection-manifest "${MANIFEST}" \
    --asr-file "${ROOT}/evaluation/asr_set.json" \
    --video-root "${ROOT}/data/videos" \
    --frames-fallback-root "${ROOT}/data/frames_8" \
    --output-dir "${output}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256
  "${PY}" "${AUDIT}" \
    --questions "${questions}" \
    --selection-manifest "${MANIFEST}" \
    --inference-dir "${output}" \
    --output "${output}/protocol_audit.json" \
    --expected-count "${expected}"
}

declare -a smoke_pids=()
for fold in 0 1 2 3 4; do
  gpu=$((fold + 1))
  run_fold "${fold}" "${gpu}" \
    "${INPUTS}/fold_${fold}/smoke5_questions.json" \
    "${RUN}/smoke5/fold_${fold}" 5 \
    >"${RUN}/logs/smoke_fold_${fold}.log" 2>&1 &
  smoke_pids+=("$!")
done
for pid in "${smoke_pids[@]}"; do
  wait "${pid}"
done
touch "${RUN}/SMOKE5_COMPLETE"

declare -a full_pids=()
for fold in 0 1 2 3 4; do
  gpu=$((fold + 1))
  run_fold "${fold}" "${gpu}" \
    "${INPUTS}/fold_${fold}/questions100.json" \
    "${RUN}/oof500/fold_${fold}" 100 \
    >"${RUN}/logs/full_fold_${fold}.log" 2>&1 &
  full_pids+=("$!")
done
for pid in "${full_pids[@]}"; do
  wait "${pid}"
done

"${PY}" - "${RUN}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
audits = []
for fold in range(5):
    path = root / f"oof500/fold_{fold}/protocol_audit.json"
    audit = json.load(open(path, encoding="utf-8"))
    if audit.get("passed") is not True or int(audit.get("completed_count", -1)) != 100:
        raise SystemExit(f"fold {fold} audit failed")
    audits.append(audit)
summary = {
    "schema_version": "adsqa_sft_lora_mmr8_groupcv500_protocol_v1",
    "passed": True,
    "question_count": 500,
    "fold_counts": {str(fold): 100 for fold in range(5)},
    "method": "AdsSFTLoRA_MMR8",
    "views": 8,
    "unified_size": 448,
    "visual_tokens": 1024,
    "secondary_frame_sampling_disabled": True,
    "groundtruth_read": False,
    "judge_scores_read": False,
}
(root / "protocol_audit.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
PY

(
  cd "${RUN}"
  sha256sum inputs_v1/audit.json inputs_v1/mmr8_manifest.jsonl \
    protocol_audit.json oof500/fold_*/protocol_audit.json \
    source_snapshot/* > INFERENCE_SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
