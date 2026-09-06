#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
SELECTED="${RUN}/selected8_manifest_v1"
RAW="${RUN}/raw_features_v1"
AV="${RUN}/av_manifest_v1"
MMR_SMOKE="${RUN}/mmr8_smoke10_v1"
MMR="${RUN}/mmr8_full5320_v1"
UNIFORM_SMOKE="${RUN}/uniform8_smoke10_v1"
UNIFORM="${RUN}/uniform8_full5320_v1"
A0_POOL="${RUN}/a0_pool_v1"
A0_SHARDS="${RUN}/a0_verifier_shards_v1"
A0_MERGED="${RUN}/a0_verifier_merged_v1"
TRIGGER="${RUN}/trigger530_dataset_v1"
ARMS="${RUN}/adaptive_scale_arms_v1"
CROP="${RUN}/adaptive_scale_inference_v1"
A2_INPUTS="${RUN}/a2_verifier_inputs_v1"
A2_SHARDS="${RUN}/a2_verifier_shards_v1"
A2_MERGED="${RUN}/a2_verifier_merged_v1"
CHOICES="${RUN}/frozen_choices_v1"
FINAL="${RUN}/final_protocol_audit_v1"
PREFLIGHT="${RUN}/judge_deepseek_v1/preflight_v1"
GPUS=(1 2 3 4 5)

mark() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/$1"
}

wait_idle() {
  local gpu="$1"
  while [[ -n "$(nvidia-smi --id="${gpu}" \
    --query-compute-apps=pid --format=csv,noheader,nounits)" ]]; do
    sleep 30
  done
}

wait_external() {
  local pid_file="$1"
  local pid
  pid="$(cat "${pid_file}")"
  while kill -0 "${pid}" 2>/dev/null; do
    sleep 30
  done
}

wait_jobs() {
  local failed=0
  local pid
  for pid in "$@"; do
    if ! wait "${pid}"; then
      failed=1
    fi
  done
  [[ "${failed}" -eq 0 ]]
}

run_selected() {
  local label="$1"
  local question_root="$2"
  local output_root="$3"
  local expected="$4"
  local pids=()
  local fold gpu
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    wait_idle "${gpu}"
    nohup "${PY}" \
      evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --method CLIPMMR64_8_lambda070 \
      --question-file "${question_root}/fold_${fold}.json" \
      --selection-manifest "${SELECTED}/mmr8.jsonl" \
      --asr-file "${DATA}/asr_combined_answer_free.json" \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output-dir "${output_root}/fold_${fold}" \
      --views 8 \
      --unified-size 512 \
      --max-visual-tokens 4096 \
      --max-new-tokens 256 \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 < /dev/null &
    pids+=("$!")
    echo "$!" > "${RUN}/pids/${label}_fold_${fold}.pid"
  done
  wait_jobs "${pids[@]}"
  mkdir -p "${output_root}/audits"
  for fold in 0 1 2 3 4; do
    "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
      --questions "${question_root}/fold_${fold}.json" \
      --selection-manifest "${SELECTED}/mmr8.jsonl" \
      --inference-dir "${output_root}/fold_${fold}" \
      --output "${output_root}/audits/fold_${fold}.json" \
      --expected-count "${expected}" \
      > "${RUN}/logs/audit_${label}_fold_${fold}.log" 2>&1
  done
}

run_uniform() {
  local label="$1"
  local question_root="$2"
  local output_root="$3"
  local expected="$4"
  local pids=()
  local fold gpu
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    wait_idle "${gpu}"
    nohup "${PY}" \
      evaluation/tools/infer_adsqa_answer_lora_qwen3_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --method CleanQwen3_Raw8 \
      --question-file "${question_root}/fold_${fold}.json" \
      --asr-file "${DATA}/asr_combined_answer_free.json" \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output-dir "${output_root}/fold_${fold}/base" \
      --views 8 \
      --unified-size 512 \
      --max-visual-tokens 4096 \
      --max-new-tokens 256 \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 < /dev/null &
    pids+=("$!")
    echo "$!" > "${RUN}/pids/${label}_fold_${fold}.pid"
  done
  wait_jobs "${pids[@]}"
  mkdir -p "${output_root}/audits"
  for fold in 0 1 2 3 4; do
    "${PY}" evaluation/tools/audit_adsqa_uniform8_full_v1.py \
      --questions "${question_root}/fold_${fold}.json" \
      --inference-root "${output_root}" \
      --output "${output_root}/audits/fold_${fold}.json" \
      --expected-count "${expected}" \
      > "${RUN}/logs/audit_${label}_fold_${fold}.log" 2>&1
  done
}

run_verifier() {
  local label="$1"
  local input_root="$2"
  local output_root="$3"
  local pids=()
  local fold gpu
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    wait_idle "${gpu}"
    nohup "${PY}" \
      evaluation/tools/score_answer_claims_qwen3_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --adapter-dir "${ADAPTER}" \
      --input-jsonl "${input_root}/shards/fold_${fold}.jsonl" \
      --output-dir "${output_root}/fold_${fold}" \
      --views 8 \
      --unified-size 448 \
      --max-visual-tokens 4096 \
      > "${RUN}/logs/${label}_fold_${fold}.log" 2>&1 < /dev/null &
    pids+=("$!")
    echo "$!" > "${RUN}/pids/${label}_fold_${fold}.pid"
  done
  wait_jobs "${pids[@]}"
}

run_adaptive() {
  local split="$1"
  local expected="$2"
  local pids=()
  local fold gpu output
  for fold in 0 1 2 3 4; do
    gpu="${GPUS[$fold]}"
    wait_idle "${gpu}"
    output="${CROP}/${split}/adaptive_scale/fold_${fold}"
    nohup "${PY}" \
      evaluation/tools/infer_qwen3_adaptive_crop_full_decode_recovery_v1.py \
      --gpu-id "${gpu}" \
      --model-dir "${MODEL}" \
      --input-jsonl "${ARMS}/${split}/adaptive_scale/shards/fold_${fold}.jsonl" \
      --output-dir "${output}" \
      --base-size 512 \
      --crop-size 896 \
      --max-visual-tokens 4096 \
      --max-new-tokens 192 \
      --expected-items "${expected}" \
      --a2-method Qwen3_adaptive_scale_AVEvidenceRewrite12_A2 \
      --skip-a1 \
      > "${RUN}/logs/adaptive_${split}_fold_${fold}.log" 2>&1 < /dev/null &
    pids+=("$!")
    echo "$!" > "${RUN}/pids/adaptive_${split}_fold_${fold}.pid"
  done
  wait_jobs "${pids[@]}"
  "${PY}" evaluation/tools/audit_qwen3_adaptive_crop_full_v1.py \
    --dataset-root "${ARMS}" \
    --run-root "${CROP}" \
    --split "${split}" \
    --output "${RUN}/${split}_adaptive_protocol_audit.json" \
    > "${RUN}/logs/audit_adaptive_${split}.log" 2>&1
}

cd "${ROOT}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
if [[ -e "${RUN}/FULL_PIPELINE_LAUNCHED" ]] && [[ "${RESUME_FULL_PIPELINE:-0}" != "1" ]]; then
  echo "refusing duplicate full5320 pipeline launch" >&2
  exit 1
fi
echo "$$" > "${RUN}/pids/full_pipeline.pid"
mark FULL_PIPELINE_LAUNCHED
trap 'mark FULL_PIPELINE_FAILED' ERR

for file in \
  build_adsqa_full_valid_v1.py \
  build_diverse_local8_manifest_full_decode_recovery_v1.py \
  merge_qwen3_a0_verifier_pool_full_v1.py \
  build_selective_evidence_rewrite_full530_v1.py \
  build_qwen3_adaptive_crop_full530_arms_v1.py \
  infer_qwen3_adaptive_crop_full_decode_recovery_v1.py \
  audit_qwen3_adaptive_crop_full_v1.py \
  freeze_mmr_selectrescue_full_v1.py \
  audit_adsqa_uniform8_full_v1.py \
  materialize_adsqa_full5320_candidates_v1.py \
  preflight_adsqa_full5320_judge_reuse_v1.py \
  infer_adsqa_answer_lora_qwen3_selected8_full_decode_recovery_v1.py \
  infer_adsqa_answer_lora_qwen3_full_decode_recovery_v1.py \
  score_answer_claims_qwen3_full_decode_recovery_v1.py; do
  cp "evaluation/tools/${file}" "${RUN}/source_snapshot/"
done
cp evaluation/scripts/run_adsqa_full5320_pipeline_v1.sh \
  "${RUN}/source_snapshot/"

# Finish the interrupted precompute without changing any data or method.
if [[ ! -e "${RUN}/EVIDENCE_MANIFESTS_COMPLETE" ]]; then
  for fold in 0 2 3; do
    wait_external "${RUN}/pids/raw_features_${fold}.pid"
  done
  wait_external "${RUN}/pids/raw_features_1_recovery_gpu1.pid"
  for fold in 0 1 2 3; do
    test "$(wc -l < "${RAW}/shard_${fold}.jsonl")" -eq 1064
  done
  if [[ ! -f "${RAW}/shard_4.jsonl" ]] ||
     [[ "$(wc -l < "${RAW}/shard_4.jsonl")" -ne 1064 ]]; then
    wait_idle 3
    "${PY}" evaluation/tools/build_diverse_local8_manifest_full_decode_recovery_v1.py \
      --gpu-id 3 \
      --questions "${DATA}/shards/fold_4.json" \
      --segmented-asr-root "${DATA}/asr_union_records" \
      --ocr-root data/candidate_cache_full_v1/ocr \
      --clip-path models/clip-vit-large-patch14 \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output "${RAW}/shard_4.jsonl" \
      > "${RUN}/logs/raw_features_4_continuation.log" 2>&1
  fi
  "${PY}" evaluation/tools/merge_answer_free_raw_features_v1.py \
    --questions "${DATA}/questions_answer_free.json" \
    --input "${RAW}/shard_0.jsonl" \
    --input "${RAW}/shard_1.jsonl" \
    --input "${RAW}/shard_2.jsonl" \
    --input "${RAW}/shard_3.jsonl" \
    --input "${RAW}/shard_4.jsonl" \
    --output "${RAW}/raw_features_all.jsonl" \
    --audit "${RAW}/merge_audit.json" \
    --expected-count 5320 \
    > "${RUN}/logs/merge_raw_features_continuation.log" 2>&1
  "${PY}" evaluation/tools/build_avfunnel8_manifest_v1.py \
    --questions "${DATA}/questions_answer_free.json" \
    --raw-features "${RAW}/raw_features_all.jsonl" \
    --output "${AV}/av_funnel_full5320.jsonl" \
    --audit "${AV}/audit.json" \
    > "${RUN}/logs/build_av_manifest_continuation.log" 2>&1
  mark EVIDENCE_MANIFESTS_COMPLETE
fi

"${PY}" - "${DATA}" "${RUN}" "${SELECTED}" "${AV}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
data, run, selected, av = map(Path, sys.argv[1:])
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for path in (data / "audit.json", selected / "audit.json", av / "audit.json"):
    if json.load(open(path, encoding="utf-8")).get("passed") is not True:
        raise SystemExit(f"failed prerequisite audit: {path}")
protocol = {
    "schema_version": "adsqa_qwen3_full_valid5320_frozen_protocol_v1",
    "questions": 5320,
    "videos": 1521,
    "fold_counts": [1064] * 5,
    "base_model": "/data1/qky/Model/Qwen3Vl-8B",
    "uniform_method": "CleanQwen3_Raw8",
    "mmr_method": "CLIPMMR64_8_lambda070",
    "trigger": "530 lowest-support per-video minima, 106 per runtime fold",
    "trigger_count": 530,
    "adaptive_variant": "response center plus entropy scale",
    "a0_views": 8,
    "a0_visual_tokens": 1024,
    "a2_views": 12,
    "a2_visual_tokens": 3104,
    "secondary_sampling": False,
    "support_threshold": 0.8933094143867493,
    "minimum_margin": 0.25,
    "groundtruth_read": False,
    "judge_scores_read": False,
    "dataset_manifest_sha256": digest(data / "manifest.json"),
    "mmr_manifest_sha256": digest(selected / "mmr8.jsonl"),
    "av_manifest_sha256": digest(av / "av_funnel_full5320.jsonl"),
}
path = run / "FROZEN_PROTOCOL.json"
if path.exists():
    raise SystemExit("refusing to overwrite frozen protocol")
path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
PY
mark PROTOCOL_FROZEN

run_selected mmr_smoke "${DATA}/smoke_shards" "${MMR_SMOKE}" 2
run_uniform uniform_smoke "${DATA}/smoke_shards" "${UNIFORM_SMOKE}" 2
mark A0_SMOKE_COMPLETE

run_selected mmr_full "${DATA}/shards" "${MMR}" 1064
mark MMR8_FULL_COMPLETE

"${PY}" evaluation/tools/build_qwen3_mmr_a0_verifier_pool_fresh499_v1.py \
  --questions "${DATA}/questions_answer_free.json" \
  --mmr-root "${MMR}" \
  --video-root data/videos \
  --output-dir "${A0_POOL}" \
  --expected-count 5320 \
  --expected-videos 1521 \
  > "${RUN}/logs/build_a0_pool.log" 2>&1
run_verifier a0_verifier "${A0_POOL}" "${A0_SHARDS}"
"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_full_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores-root "${A0_SHARDS}" \
  --output-dir "${A0_MERGED}" \
  --expected-count 5320 \
  --expected-videos 1521 \
  --expected-per-fold 1064 \
  > "${RUN}/logs/merge_a0_verifier.log" 2>&1
mark A0_VERIFIER_COMPLETE

"${PY}" evaluation/tools/build_selective_evidence_rewrite_full530_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores "${A0_MERGED}/scores_all.jsonl" \
  --av-manifest "${AV}/av_funnel_full5320.jsonl" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root "${DATA}/asr_union_records" \
  --output-dir "${TRIGGER}" \
  > "${RUN}/logs/build_trigger530.log" 2>&1
"${PY}" evaluation/tools/build_qwen3_adaptive_crop_full530_arms_v1.py \
  --input-jsonl "${TRIGGER}/items_answer_free.jsonl" \
  --output-root "${ARMS}" \
  --smoke-per-fold 2 \
  > "${RUN}/logs/build_adaptive_arms.log" 2>&1
mark TRIGGER530_AND_ARMS_FROZEN

run_adaptive smoke10 2
mark ADAPTIVE_SMOKE_COMPLETE
run_adaptive full530 106
mark ADAPTIVE_FULL530_COMPLETE

"${PY}" evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CROP}/full530/adaptive_scale" \
  --output-dir "${A2_INPUTS}" \
  --expected-count 530 \
  --expected-videos 530 \
  --expected-per-fold 106 \
  > "${RUN}/logs/build_a2_inputs.log" 2>&1
run_verifier a2_verifier "${A2_INPUTS}" "${A2_SHARDS}"
"${PY}" evaluation/tools/merge_selective_rewrite_a2_scores_v1.py \
  --shard-root "${A2_SHARDS}" \
  --output-dir "${A2_MERGED}" \
  --expected-count 530 \
  --expected-per-fold 106 \
  > "${RUN}/logs/merge_a2_verifier.log" 2>&1
"${PY}" evaluation/tools/freeze_mmr_selectrescue_full_v1.py \
  --delegate evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CROP}/full530/adaptive_scale" \
  --a0-scores "${A0_MERGED}/scores_all.jsonl" \
  --a2-scores "${A2_MERGED}/scores_all.jsonl" \
  --output-dir "${CHOICES}" \
  --support-threshold 0.8933094143867493 \
  --minimum-margin 0.25 \
  > "${RUN}/logs/freeze_choices.log" 2>&1
mark JOINT_CHOICES_FROZEN

run_uniform uniform_full "${DATA}/shards" "${UNIFORM}" 1064
mark UNIFORM8_FULL_COMPLETE

"${PY}" evaluation/tools/materialize_adsqa_full5320_candidates_v1.py \
  --questions "${DATA}/questions_answer_free.json" \
  --uniform-root "${UNIFORM}" \
  --uniform-audit-root "${UNIFORM}/audits" \
  --mmr-root "${MMR}" \
  --mmr-audit-root "${MMR}/audits" \
  --trigger-dataset "${TRIGGER}" \
  --crop-audit "${RUN}/full530_adaptive_protocol_audit.json" \
  --choices-dir "${CHOICES}" \
  --output-dir "${FINAL}" \
  > "${RUN}/logs/materialize_final_candidates.log" 2>&1

LEGACY="/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py"
"${PY}" evaluation/tools/preflight_adsqa_full5320_judge_reuse_v1.py \
  --groundtruth "${DATA}/private_references/groundtruth.json" \
  --candidates "${FINAL}/candidates_answer_free.jsonl" \
  --protocol-audit "${FINAL}/protocol_audit.json" \
  --cache evaluation/runs/qwen3_joint_confirm1000_v1/judge_deepseek_v1/api_results_partial.jsonl \
  --cache evaluation/runs/qwen3_adaptive_crop_fresh499_v1/judge_deepseek_v1/results_v1/api_results_partial.jsonl \
  --cache evaluation/runs/qwen3_selected8_baselines_groupcv500_v1/judge_deepseek_answeronly_v1/results.jsonl \
  --cache evaluation/runs/qwen3_mmr_selectrescue_oof500_v1/judge_deepseek_v1/api_results_partial.jsonl \
  --cache evaluation/runs/qwen3_adaptive_crop_ablation_groupcv50_v1/judge_deepseek_v1/api_results_partial.jsonl \
  --cache evaluation/runs/qwen3_selective_evidence_rewrite_confirmd300_v1/judge_deepseek_v1/api_results_partial.jsonl \
  --legacy-evaluator "${LEGACY}" \
  --output-dir "${PREFLIGHT}" \
  > "${RUN}/logs/judge_reuse_preflight.log" 2>&1

(
  cd "${RUN}"
  find FROZEN_PROTOCOL.json selected8_manifest_v1 raw_features_v1 \
    av_manifest_v1 mmr8_full5320_v1 a0_pool_v1 \
    a0_verifier_merged_v1 trigger530_dataset_v1 adaptive_scale_arms_v1 \
    adaptive_scale_inference_v1 a2_verifier_merged_v1 frozen_choices_v1 \
    uniform8_full5320_v1 final_protocol_audit_v1 \
    judge_deepseek_v1/preflight_v1 source_snapshot -type f -print0 \
    | sort -z | xargs -0 sha256sum > INFERENCE_SHA256SUMS
)
mark INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION
