#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_selected8_baselines_groupcv500_v1"
QUESTIONS="${ROOT}/evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/oof500_v1_audit/oof_questions_answer_free.json"

for method in CLIPTopK8 MMR8; do
  while [[ ! -f "${RUN}/full500/${method}/run_summary.json" ]]; do
    sleep 60
  done
done

"${PY}" - "${RUN}" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for method in ("CLIPTopK8", "MMR8"):
    summary = json.load(open(root / "full500" / method / "run_summary.json", encoding="utf-8"))
    stats = summary.get("stats", {})
    if int(stats.get("processed", 0)) + int(stats.get("skipped_existing", 0)) != 500:
        raise SystemExit(f"{method} is incomplete: {stats}")
    if int(stats.get("errors", -1)) != 0:
        raise SystemExit(f"{method} contains inference errors: {stats}")
PY

"${PY}" "${ROOT}/evaluation/tools/audit_adsqa_selected8_inference_v1.py" \
  --questions "${QUESTIONS}" \
  --selection-manifest "${RUN}/manifest/clip_topk8_oof500.jsonl" \
  --inference-dir "${RUN}/full500/CLIPTopK8" \
  --output "${RUN}/full500/CLIPTopK8/protocol_audit.json" \
  --expected-count 500 \
  > "${RUN}/logs/clip_topk8_full_audit.log" 2>&1

"${PY}" "${ROOT}/evaluation/tools/audit_adsqa_selected8_inference_v1.py" \
  --questions "${QUESTIONS}" \
  --selection-manifest "${RUN}/manifest/mmr8_oof500.jsonl" \
  --inference-dir "${RUN}/full500/MMR8" \
  --output "${RUN}/full500/MMR8/protocol_audit.json" \
  --expected-count 500 \
  > "${RUN}/logs/mmr8_full_audit.log" 2>&1

touch "${RUN}/full500/CLIP_MMR_PROTOCOL_COMPLETE"
