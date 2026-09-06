#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
PARENT="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
MANIFEST="${PARENT}/selected8_manifest_v1/clip_topk8.jsonl"
RUN="${PARENT}/cliptopk8_full5320_v1"

cd "${ROOT}"
mkdir -p "${RUN}/audits" "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
cp evaluation/scripts/run_adsqa_full5320_cliptopk8_three_gpu_v1.sh "${RUN}/source_snapshot/"
cp evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_full_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/audit_adsqa_selected8_inference_v1.py "${RUN}/source_snapshot/"

run_fold() {
  local gpu="$1"
  local fold="$2"
  local output="${RUN}/fold_${fold}"
  echo "$$" > "${RUN}/pids/fold_${fold}.pid"
  "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --method CleanQwen3_CLIPTopK8 \
    --question-file "${DATA}/shards/fold_${fold}.json" \
    --selection-manifest "${MANIFEST}" \
    --asr-file "${DATA}/asr_combined_answer_free.json" \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output-dir "${output}" \
    --views 8 \
    --unified-size 512 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256 \
    > "${RUN}/logs/fold_${fold}.log" 2>&1
  "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
    --questions "${DATA}/shards/fold_${fold}.json" \
    --selection-manifest "${MANIFEST}" \
    --inference-dir "${output}" \
    --output "${RUN}/audits/fold_${fold}.json" \
    --expected-count 1064 \
    > "${RUN}/logs/audit_fold_${fold}.log" 2>&1
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/FOLD_${fold}_COMPLETE"
}

echo "$$" > "${RUN}/pids/orchestrator.pid"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/CLIPTOPK8_LAUNCHED"

(
  run_fold 3 0
  run_fold 3 3
) > "${RUN}/logs/gpu3_chain.log" 2>&1 &
gpu3_chain="$!"

(
  run_fold 4 1
  run_fold 4 4
) > "${RUN}/logs/gpu4_chain.log" 2>&1 &
gpu4_chain="$!"

(
  run_fold 5 2
) > "${RUN}/logs/gpu5_chain.log" 2>&1 &
gpu5_chain="$!"

failed=0
for pid in "${gpu3_chain}" "${gpu4_chain}" "${gpu5_chain}"; do
  if ! wait "${pid}"; then failed=1; fi
done
if [[ "${failed}" -ne 0 ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/CLIPTOPK8_FAILED"
  exit 1
fi

"${PY}" - "${RUN}" "${MANIFEST}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
manifest = Path(sys.argv[2])
audits = [json.loads((run / "audits" / f"fold_{fold}.json").read_text()) for fold in range(5)]
summary = {
    "schema_version": "adsqa_full5320_cliptopk8_summary_v1",
    "method": "CleanQwen3_CLIPTopK8",
    "question_count": sum(int(row["completed_count"]) for row in audits),
    "fold_counts": [int(row["completed_count"]) for row in audits],
    "all_fold_audits_passed": all(row.get("passed") is True for row in audits),
    "views": 8,
    "visual_tokens": 1024,
    "visual_token_budget": 4096,
    "secondary_frame_sampling": False,
    "groundtruth_read": False,
    "judge_outputs_read": False,
    "selection_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
}
if summary["question_count"] != 5320 or not summary["all_fold_audits_passed"]:
    raise SystemExit("CLIPTopK8 full audit failed")
(run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
PY

(
  cd "${RUN}"
  find fold_0 fold_1 fold_2 fold_3 fold_4 audits source_snapshot summary.json \
    -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/CLIPTOPK8_FULL_COMPLETE"
