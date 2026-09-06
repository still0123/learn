#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="$ROOT/evaluation/runs/ocr_crop_factorial_confirm600_v1/crop_rerunocr_confirm50_v1"
PREFLIGHT="$RUN/judge_preflight_v1"
RESULTS="$RUN/judge_results_v1"
AUTH="$RUN/judge_authorization_v1.json"
GT="$ROOT/data/adsqa_full_valid5320_v1/private_references/groundtruth.json"
DATASET="$RUN/dataset_50.jsonl"
LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
JUDGE="$ROOT/evaluation/tools/judge_ocr_crop_factorial_smoke_v1.py"

test -f "$RUN/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
test ! -e "$RESULTS/JUDGE_COMPLETE"
mkdir -p "$RESULTS/source_snapshot" "$RUN/pids"
echo "$$" > "$RUN/pids/judge.pid"
trap 'date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/JUDGE_FAILED"' ERR
cp "$JUDGE" "$RESULTS/source_snapshot/"
cp "$ROOT/evaluation/scripts/run_crop_rerunocr_confirm50_judge_v1.sh" "$RESULTS/source_snapshot/"

"$PY" - "$AUTH" "$GT" "$DATASET" "$PREFLIGHT/preflight_audit.json" "$PREFLIGHT/pending_candidates_answer_only.jsonl" "$LEGACY" <<'PY'
import hashlib, json, sys
from pathlib import Path
def digest(path):
    value=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""): value.update(block)
    return value.hexdigest()
output,gt,dataset,preflight,pending,legacy=map(Path,sys.argv[1:])
payload={"schema_version":"crop_rerunocr_confirm50_authorization_v1",
         "authorized_new_api_call_count":70,"automatic_retries":0,
         "input_sha256":{"groundtruth":digest(gt),"dataset":digest(dataset),
                         "preflight":digest(preflight),"pending":digest(pending),
                         "legacy_evaluator":digest(legacy)}}
output.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
PY

COMMON=(--groundtruth "$GT" --dataset "$DATASET" --preflight-root "$PREFLIGHT"
        --authorization-manifest "$AUTH" --legacy-evaluator "$LEGACY"
        --output-dir "$RESULTS" --workers 5 --bootstrap-samples 10000)
"$PY" "$JUDGE" "${COMMON[@]}" --validate-only
"$PY" "$JUDGE" "${COMMON[@]}"
(
  cd "$RUN"
  find judge_preflight_v1 judge_results_v1 judge_authorization_v1.json -type f -print0 \
    | sort -z | xargs -0 sha256sum > JUDGE_SHA256SUMS
)
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN/JUDGE_PIPELINE_COMPLETE"
