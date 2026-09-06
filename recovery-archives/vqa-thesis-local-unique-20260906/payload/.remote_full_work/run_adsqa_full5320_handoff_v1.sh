#!/usr/bin/env bash
# Continue the frozen full-5,320 protocol without leaving a completed GPU idle.
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
SELECTED="${RUN}/selected8_manifest_v1"
MMR="${RUN}/mmr8_full5320_v1"
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

cd "${ROOT}"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/handoff_v1"

mark() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/$1"
}

count_predictions() {
  find "$1" -name prediction.json -type f 2>/dev/null | wc -l
}

wait_prediction_count() {
  local dir="$1"
  local expected="$2"
  while [[ "$(count_predictions "${dir}")" -lt "${expected}" ]]; do
    sleep 20
  done
  # Let the worker flush its run summary before reusing the same card.
  sleep 30
}

run_uniform_fold() {
  local gpu="$1"
  local fold="$2"
  local out="${UNIFORM}/fold_${fold}/base"
  "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --method CleanQwen3_Raw8 \
    --question-file "${DATA}/shards/fold_${fold}.json" \
    --asr-file "${DATA}/asr_combined_answer_free.json" \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output-dir "${out}" \
    --views 8 \
    --unified-size 512 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256 \
    > "${RUN}/logs/handoff_uniform_fold_${fold}.log" 2>&1
  "${PY}" evaluation/tools/audit_adsqa_uniform8_full_v1.py \
    --questions "${DATA}/shards/fold_${fold}.json" \
    --inference-root "${UNIFORM}" \
    --output "${UNIFORM}/audits/fold_${fold}.json" \
    --expected-count 1064 \
    > "${RUN}/logs/handoff_audit_uniform_fold_${fold}.log" 2>&1
}

run_a0_fold() {
  local gpu="$1"
  local fold="$2"
  "${PY}" evaluation/tools/score_answer_claims_qwen3_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${A0_POOL}/shards/fold_${fold}.jsonl" \
    --output-dir "${A0_SHARDS}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    > "${RUN}/logs/handoff_a0_verifier_fold_${fold}.log" 2>&1
}

run_adaptive_fold() {
  local gpu="$1"
  local fold="$2"
  "${PY}" evaluation/tools/infer_qwen3_adaptive_crop_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${ARMS}/full530/adaptive_scale/shards/fold_${fold}.jsonl" \
    --output-dir "${CROP}/full530/adaptive_scale/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items 106 \
    --a2-method Qwen3_adaptive_scale_AVEvidenceRewrite12_A2 \
    --skip-a1 \
    > "${RUN}/logs/handoff_adaptive_fold_${fold}.log" 2>&1
}

run_a2_fold() {
  local gpu="$1"
  local fold="$2"
  "${PY}" evaluation/tools/score_answer_claims_qwen3_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${A2_INPUTS}/shards/fold_${fold}.jsonl" \
    --output-dir "${A2_SHARDS}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    > "${RUN}/logs/handoff_a2_verifier_fold_${fold}.log" 2>&1
}

wait_a0_pool() {
  while [[ ! -f "${RUN}/HANDOFF_A0_POOL_READY" ]]; do
    sleep 20
  done
}

# The original coordinator waits for absolutely idle GPUs and is therefore
# blocked by a separate VLLM job. Pause it reversibly so it cannot relaunch
# completed folds while this resumable handoff owns the remaining stages.
if [[ -f "${RUN}/pids/full_pipeline.pid" ]]; then
  pipeline_pid="$(cat "${RUN}/pids/full_pipeline.pid")"
  if kill -0 "${pipeline_pid}" 2>/dev/null; then
    kill -STOP "${pipeline_pid}"
    echo "${pipeline_pid}" > "${RUN}/handoff_v1/paused_full_pipeline.pid"
  fi
fi
echo "$$" > "${RUN}/pids/handoff_v1.pid"
mark HANDOFF_V1_LAUNCHED

# GPU1/GPU2 take independent Uniform folds immediately after their MMR fold.
(
  wait_prediction_count "${MMR}/fold_0" 1064
  run_uniform_fold 1 3
  wait_a0_pool
  run_a0_fold 1 4
) > "${RUN}/logs/handoff_gpu1_chain.log" 2>&1 &
gpu1_chain="$!"

(
  wait_prediction_count "${MMR}/fold_1" 1064
  run_uniform_fold 2 4
) > "${RUN}/logs/handoff_gpu2_chain.log" 2>&1 &
gpu2_chain="$!"

# Build the answer-free A0 pool only after all frozen MMR outputs are complete.
(
  for fold in 0 1 2 3 4; do
    wait_prediction_count "${MMR}/fold_${fold}" 1064
    "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
      --questions "${DATA}/shards/fold_${fold}.json" \
      --selection-manifest "${SELECTED}/mmr8.jsonl" \
      --inference-dir "${MMR}/fold_${fold}" \
      --output "${MMR}/audits/fold_${fold}.json" \
      --expected-count 1064 \
      > "${RUN}/logs/handoff_audit_mmr_fold_${fold}.log" 2>&1
  done
  "${PY}" evaluation/tools/build_qwen3_mmr_a0_verifier_pool_fresh499_v1.py \
    --questions "${DATA}/questions_answer_free.json" \
    --mmr-root "${MMR}" \
    --video-root data/videos \
    --output-dir "${A0_POOL}" \
    --expected-count 5320 \
    --expected-videos 1521 \
    > "${RUN}/logs/handoff_build_a0_pool.log" 2>&1
  mark HANDOFF_A0_POOL_READY
) > "${RUN}/logs/handoff_pool_builder.log" 2>&1 &
pool_builder="$!"

# GPU3/GPU4 become verifier workers as soon as their MMR work and the shared
# answer-free input pool are ready. They retain their assigned cards.
(
  wait_prediction_count "${MMR}/fold_4" 1064
  wait_a0_pool
  run_a0_fold 3 0
) > "${RUN}/logs/handoff_gpu3_chain.log" 2>&1 &
gpu3_chain="$!"

(
  wait_prediction_count "${MMR}/fold_2" 1064
  wait_a0_pool
  run_a0_fold 4 1
) > "${RUN}/logs/handoff_gpu4_chain.log" 2>&1 &
gpu4_chain="$!"

# Existing GPU0/GPU5 Uniform chains are reused; each takes an A0 verifier fold
# after its current real inference finishes. No reservation-only process is used.
(
  wait_prediction_count "${UNIFORM}/fold_1/base" 1064
  wait_a0_pool
  run_a0_fold 0 2
) > "${RUN}/logs/handoff_gpu0_chain.log" 2>&1 &
gpu0_chain="$!"

(
  wait_prediction_count "${UNIFORM}/fold_2/base" 1064
  wait_a0_pool
  run_a0_fold 5 3
) > "${RUN}/logs/handoff_gpu5_chain.log" 2>&1 &
gpu5_chain="$!"

wait "${pool_builder}" "${gpu0_chain}" "${gpu1_chain}" "${gpu2_chain}" \
  "${gpu3_chain}" "${gpu4_chain}" "${gpu5_chain}"

"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_full_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores-root "${A0_SHARDS}" \
  --output-dir "${A0_MERGED}" \
  --expected-count 5320 \
  --expected-videos 1521 \
  --expected-per-fold 1064 \
  > "${RUN}/logs/handoff_merge_a0_verifier.log" 2>&1
mark HANDOFF_A0_VERIFIER_COMPLETE

"${PY}" evaluation/tools/build_selective_evidence_rewrite_full530_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores "${A0_MERGED}/scores_all.jsonl" \
  --av-manifest "${RUN}/av_manifest_v1/av_funnel_full5320.jsonl" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root "${DATA}/asr_union_records" \
  --output-dir "${TRIGGER}" \
  > "${RUN}/logs/handoff_build_trigger530.log" 2>&1
"${PY}" evaluation/tools/build_qwen3_adaptive_crop_full530_arms_v1.py \
  --input-jsonl "${TRIGGER}/items_answer_free.jsonl" \
  --output-root "${ARMS}" \
  --smoke-per-fold 2 \
  > "${RUN}/logs/handoff_build_adaptive_arms.log" 2>&1
mark HANDOFF_TRIGGER530_AND_ARMS_READY

pids=()
for fold in 0 1 2 3 4; do
  gpu=$((fold + 1))
  run_adaptive_fold "${gpu}" "${fold}" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "${pid}"; done
"${PY}" evaluation/tools/audit_qwen3_adaptive_crop_full_v1.py \
  --dataset-root "${ARMS}" \
  --run-root "${CROP}" \
  --split full530 \
  --output "${RUN}/full530_adaptive_protocol_audit.json" \
  > "${RUN}/logs/handoff_audit_adaptive_full530.log" 2>&1
mark HANDOFF_ADAPTIVE_FULL530_COMPLETE

"${PY}" evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CROP}/full530/adaptive_scale" \
  --output-dir "${A2_INPUTS}" \
  --expected-count 530 \
  --expected-videos 530 \
  --expected-per-fold 106 \
  > "${RUN}/logs/handoff_build_a2_inputs.log" 2>&1

pids=()
for fold in 0 1 2 3 4; do
  gpu=$((fold + 1))
  run_a2_fold "${gpu}" "${fold}" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "${pid}"; done
"${PY}" evaluation/tools/merge_selective_rewrite_a2_scores_v1.py \
  --shard-root "${A2_SHARDS}" \
  --output-dir "${A2_MERGED}" \
  --expected-count 530 \
  --expected-per-fold 106 \
  > "${RUN}/logs/handoff_merge_a2_verifier.log" 2>&1
"${PY}" evaluation/tools/freeze_mmr_selectrescue_full_v1.py \
  --delegate evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CROP}/full530/adaptive_scale" \
  --a0-scores "${A0_MERGED}/scores_all.jsonl" \
  --a2-scores "${A2_MERGED}/scores_all.jsonl" \
  --output-dir "${CHOICES}" \
  --support-threshold 0.8933094143867493 \
  --minimum-margin 0.25 \
  > "${RUN}/logs/handoff_freeze_choices.log" 2>&1
mark HANDOFF_JOINT_CHOICES_FROZEN

for fold in 0 1 2 3 4; do
  "${PY}" evaluation/tools/audit_adsqa_uniform8_full_v1.py \
    --questions "${DATA}/shards/fold_${fold}.json" \
    --inference-root "${UNIFORM}" \
    --output "${UNIFORM}/audits/fold_${fold}.json" \
    --expected-count 1064 \
    > "${RUN}/logs/handoff_final_audit_uniform_fold_${fold}.log" 2>&1
done

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
  > "${RUN}/logs/handoff_materialize_final_candidates.log" 2>&1

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
  > "${RUN}/logs/handoff_judge_reuse_preflight.log" 2>&1
mark HANDOFF_INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION
