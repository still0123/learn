#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_joint_confirm1000_v1"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
INPUT="${RUN}/a0_pool_v1/shards/fold_3.jsonl"
OUTPUT="${RUN}/a0_verifier_shards_v1/fold_3"

cd "${ROOT}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
cp evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/scripts/run_confirm1000_a0_verifier_fold3_repair_v1.sh "${RUN}/source_snapshot/"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A0_VERIFIER_FOLD3_REPAIR_FAILED"' ERR

test "$(wc -l < "${INPUT}")" -eq 200
test "$(wc -l < "${OUTPUT}/scores.jsonl")" -eq 78

"${PY}" evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py \
  --gpu-id 4 \
  --model-dir "${MODEL}" \
  --adapter-dir "${ADAPTER}" \
  --input-jsonl "${INPUT}" \
  --output-dir "${OUTPUT}" \
  --views 8 \
  --unified-size 448 \
  --max-visual-tokens 4096 \
  > "${RUN}/logs/a0_verifier_3_repair.log" 2>&1

test "$(wc -l < "${OUTPUT}/scores.jsonl")" -eq 200
"${PY}" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["complete"] and x["rows"]==200' "${OUTPUT}/summary.json"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A0_VERIFIER_FOLD3_REPAIR_COMPLETE"

exec env RESUME_AFTER_A0_VERIFIER_REPAIR=1 bash evaluation/scripts/run_qwen3_joint_confirm1000_v1.sh
