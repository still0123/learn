#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct"
ADAPTER_ROOT="${ROOT}/evaluation/runs/adsqa_sft_lora_groupcv500_v1/oof500_v2"
MMR_RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_mmr8_groupcv500_v1"
RUN="${ROOT}/evaluation/runs/adsqa_sft_lora_adaptive12_groupcv500_v1"
QUESTIONS="${ROOT}/evaluation/runs/qwen25_final_arch_groupcv500_v1/inputs_v1/questions_answer_free.json"
VIDEO_ROOT="${ROOT}/data/videos"
VERIFIER_MODEL="/data1/qky/Model/Qwen3Vl-8B"
VERIFIER_ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
AV_MANIFEST="${ROOT}/evaluation/runs/innovation1_avfunnel8_groupcv500_v1/manifest/av_funnel_oof500_v2.jsonl"
INFER="${ROOT}/evaluation/tools/infer_adsqa_sft_lora_qwen25_samebudget_v1.py"
EXPECTED=500
VIDEOS=100
PER_FOLD=100

mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
if [[ -e "${RUN}/PIPELINE_LAUNCHED" ]]; then
  echo "refusing duplicate AdsSFTLoRA Adaptive12 launch" >&2
  exit 1
fi
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/PIPELINE_LAUNCHED"

on_error() {
  local status=$?
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    echo "exit_status=${status}"
    echo "line=${BASH_LINENO[0]:-unknown}"
  } > "${RUN}/PIPELINE_FAILED"
  exit "${status}"
}
trap on_error ERR

cd "${ROOT}"
cp \
  evaluation/tools/build_evads_a0_verifier_pool_v2.py \
  evaluation/tools/score_answer_claims_qwen3_v1.py \
  evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  evaluation/tools/build_selective_evidence_rewrite_calibration500_v1.py \
  evaluation/tools/infer_adsqa_sft_lora_qwen25_samebudget_v1.py \
  evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
  evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
  evaluation/tools/merge_evads_a2_scores_v2.py \
  evaluation/scripts/run_adsqa_sft_lora_adaptive12_groupcv500_v1.sh \
  "${RUN}/source_snapshot/"

"${PY}" - "${MMR_RUN}/judge_deepseek_legacy_answer_only_v1/results_v1/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf-8"))
pair = summary["pairwise"]["AdsSFTLoRA_MMR8__vs__AdsSFTLoRA_Raw8"]
if pair["mean_relaxed_delta_mmr_minus_raw"] <= 0:
    raise SystemExit("MMR8 direction gate is not positive")
if summary["judge_execution"]["failure_count"] != 0:
    raise SystemExit("MMR8 judge has failures")
PY

assert_gpus_idle() {
  local gpu
  local active
  for gpu in 1 2 3 4 5; do
    active="$(
      nvidia-smi \
        --id="${gpu}" \
        --query-compute-apps=pid \
        --format=csv,noheader,nounits 2>/dev/null \
        | tr -d '[:space:]'
    )"
    if [[ -n "${active}" ]]; then
      echo "GPU${gpu} is not idle" >&2
      return 1
    fi
  done
}

snapshot_gpus() {
  local label="$1"
  {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
    nvidia-smi \
      --query-gpu=index,memory.used,memory.free,memory.total,utilization.gpu \
      --format=csv,noheader,nounits
    nvidia-smi \
      --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
      --format=csv,noheader,nounits || true
  } > "${RUN}/logs/gpu_${label}.log"
}

"${PY}" evaluation/tools/build_evads_a0_verifier_pool_v2.py \
  --questions "${QUESTIONS}" \
  --a0-root "${MMR_RUN}/oof500" \
  --video-root "${VIDEO_ROOT}" \
  --output-dir "${RUN}/a0_mmr8_pool" \
  --expected-method "AdsSFTLoRA_MMR8" \
  --candidate-method "AdsSFTLoRA_MMR8_A0" \
  --expected-count "${EXPECTED}" \
  --expected-videos "${VIDEOS}" \
  --expected-per-fold "${PER_FOLD}" \
  --expected-visual-tokens 1024 \
  > "${RUN}/logs/build_a0_pool.log" 2>&1

run_verifier_wave() {
  local label="$1"
  local input_root="$2"
  local output_root="$3"
  local -a pids=()
  local fold
  local gpu
  assert_gpus_idle
  for fold in 0 1 2 3 4; do
    gpu="$((fold + 1))"
    mkdir -p "${output_root}/fold_${fold}"
    nohup "${PY}" evaluation/tools/score_answer_claims_qwen3_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${VERIFIER_MODEL}" \
      --adapter-dir "${VERIFIER_ADAPTER}" \
      --input-jsonl "${input_root}/shards/fold_${fold}.jsonl" \
      --output-dir "${output_root}/fold_${fold}" \
      --views 8 \
      --unified-size 448 \
      --max-visual-tokens 4096 \
      --overwrite \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  for pid in "${pids[@]}"; do
    wait "${pid}"
  done
}

snapshot_gpus "before_a0_verifier"
run_verifier_wave \
  "a0_verifier" \
  "${RUN}/a0_mmr8_pool" \
  "${RUN}/a0_mmr8_verifier_shards"
"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  --pool-dir "${RUN}/a0_mmr8_pool" \
  --scores-root "${RUN}/a0_mmr8_verifier_shards" \
  --output-dir "${RUN}/a0_mmr8_verifier_merged" \
  --expected-count "${EXPECTED}" \
  --expected-videos "${VIDEOS}" \
  --expected-per-fold "${PER_FOLD}" \
  > "${RUN}/logs/merge_a0_verifier.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A0_VERIFIER_COMPLETE"

"${PY}" evaluation/tools/build_selective_evidence_rewrite_calibration500_v1.py \
  --pool-dir "${RUN}/a0_mmr8_pool" \
  --scores "${RUN}/a0_mmr8_verifier_merged/scores_all.jsonl" \
  --av-manifest "${AV_MANIFEST}" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root data/segmented_asr_pilot_train_confirm_v1/records \
  --output-dir "${RUN}/calibration_candidates500" \
  > "${RUN}/logs/build_calibration_candidates500.log" 2>&1

"${PY}" - "${RUN}/calibration_candidates500" "${RUN}/smoke_inputs" <<'PY'
import json
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
for fold in range(5):
    rows = [
        json.loads(line)
        for line in (source / "shards" / f"fold_{fold}.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    output = target / "shards" / f"fold_{fold}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(rows[0], ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
PY

run_a2_wave() {
  local label="$1"
  local variant="$2"
  local method="$3"
  local input_root="$4"
  local expected_items="$5"
  local output_root="$6"
  local -a pids=()
  local fold
  local gpu
  assert_gpus_idle
  for fold in 0 1 2 3 4; do
    gpu="$((fold + 1))"
    nohup "${PY}" "${INFER}" \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --adapter-dir "${ADAPTER_ROOT}/fold_${fold}/train/adapter" \
      --input-jsonl "${input_root}/shards/fold_${fold}.jsonl" \
      --output-dir "${output_root}/fold_${fold}" \
      --base-size 512 \
      --crop-size 896 \
      --max-visual-tokens 4096 \
      --max-new-tokens 192 \
      --expected-items "${expected_items}" \
      --a2-method "${method}" \
      --ablation-variant "${variant}" \
      --skip-a1 \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 &
    pid=$!
    echo "${pid}" > "${RUN}/pids/${label}_fold_${fold}.pid"
    pids+=("${pid}")
  done
  for pid in "${pids[@]}"; do
    wait "${pid}"
  done
}

snapshot_gpus "before_smoke5"
run_a2_wave \
  "smoke5_adaptive12" \
  "adaptive_scale" \
  "AdsSFTLoRA_Adaptive12_A2" \
  "${RUN}/smoke_inputs" \
  1 \
  "${RUN}/smoke5_adaptive12"
"${PY}" - "${RUN}/smoke5_adaptive12" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
traces = sorted(root.glob("fold_*/*/a2_trace.json"))
if len(traces) != 5:
    raise SystemExit(f"expected 5 smoke traces, got {len(traces)}")
for path in traces:
    row = json.load(open(path, encoding="utf-8"))
    trace = row["processor_trace"]
    if (
        trace["represented_views"] != 12
        or trace["visual_tokens"] != 3992
        or trace["secondary_frame_sampling"] is not False
    ):
        raise SystemExit(f"smoke protocol mismatch: {path}")
PY
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/SMOKE5_COMPLETE"

snapshot_gpus "before_a2_full500"
run_a2_wave \
  "adaptive12" \
  "adaptive_scale" \
  "AdsSFTLoRA_Adaptive12_A2" \
  "${RUN}/calibration_candidates500" \
  100 \
  "${RUN}/adaptive12"
run_a2_wave \
  "extra_global12" \
  "extra_global" \
  "AdsSFTLoRA_ExtraGlobal12_A2" \
  "${RUN}/calibration_candidates500" \
  100 \
  "${RUN}/extra_global12"

"${PY}" evaluation/tools/audit_evads_threshold_a2_controls_v2.py \
  --dataset-dir "${RUN}/calibration_candidates500" \
  --adaptive-root "${RUN}/adaptive12" \
  --extra-global-root "${RUN}/extra_global12" \
  --expected-visual-tokens 3992 \
  --output "${RUN}/a2_controls_protocol_audit.json" \
  > "${RUN}/logs/audit_a2_controls.log" 2>&1
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/A2_ARMS_COMPLETE"

for arm in adaptive12 extra_global12; do
  if [[ "${arm}" == "adaptive12" ]]; then
    a2_method="AdsSFTLoRA_Adaptive12_A2"
  else
    a2_method="AdsSFTLoRA_ExtraGlobal12_A2"
  fi
  "${PY}" evaluation/tools/build_evads_a2_verifier_inputs_v3.py \
    --dataset-dir "${RUN}/calibration_candidates500" \
    --inference-root "${RUN}/${arm}" \
    --output-dir "${RUN}/${arm}_verifier_inputs" \
    --expected-a2-method "${a2_method}" \
    --candidate-method "${a2_method}" \
    > "${RUN}/logs/build_${arm}_verifier_inputs.log" 2>&1
  run_verifier_wave \
    "${arm}_verifier" \
    "${RUN}/${arm}_verifier_inputs" \
    "${RUN}/${arm}_verifier_shards"
  "${PY}" evaluation/tools/merge_evads_a2_scores_v2.py \
    --input-dir "${RUN}/${arm}_verifier_inputs" \
    --shard-root "${RUN}/${arm}_verifier_shards" \
    --output-dir "${RUN}/${arm}_verifier_merged" \
    > "${RUN}/logs/merge_${arm}_verifier.log" 2>&1
done

sha256sum \
  "${RUN}/a0_mmr8_pool/audit.json" \
  "${RUN}/a0_mmr8_verifier_merged/summary.json" \
  "${RUN}/calibration_candidates500/audit.json" \
  "${RUN}/a2_controls_protocol_audit.json" \
  "${RUN}/adaptive12_verifier_merged/summary.json" \
  "${RUN}/extra_global12_verifier_merged/summary.json" \
  > "${RUN}/INFERENCE_SHA256SUMS"
snapshot_gpus "pipeline_complete"
date -u +"%Y-%m-%dT%H:%M:%SZ" \
  > "${RUN}/INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION"
rm -f "${RUN}/PIPELINE_FAILED"
