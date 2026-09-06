#!/usr/bin/env bash
# Continue the frozen protocol on GPU3/4/5 as soon as all A0 scores are ready.
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
DATA="${ROOT}/data/adsqa_full_valid5320_v1"
RUN="${ROOT}/evaluation/runs/qwen3_full_valid5320_v1"
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
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"

mark() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/$1"
}

line_count() {
  if [[ -f "$1" ]]; then wc -l < "$1"; else echo 0; fi
}

wait_a0_all() {
  local fold
  for fold in 0 1 2 3 4; do
    while [[ "$(line_count "${A0_SHARDS}/fold_${fold}/scores.jsonl")" -lt 1064 ]]; do
      sleep 20
    done
  done
  sleep 30
}

wait_uniform_all() {
  local fold count
  for fold in 0 1 2 3 4; do
    while true; do
      count="$(find "${UNIFORM}/fold_${fold}/base" -name prediction.json -type f 2>/dev/null | wc -l)"
      [[ "${count}" -ge 1064 ]] && break
      sleep 20
    done
  done
  sleep 30
}

run_adaptive() {
  local gpu="$1"
  local split="$2"
  local expected="$3"
  local fold="$4"
  "${PY}" evaluation/tools/infer_qwen3_adaptive_crop_full_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${ARMS}/${split}/adaptive_scale/shards/fold_${fold}.jsonl" \
    --output-dir "${CROP}/${split}/adaptive_scale/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items "${expected}" \
    --a2-method Qwen3_adaptive_scale_AVEvidenceRewrite12_A2 \
    --skip-a1 \
    > "${RUN}/logs/posta0_adaptive_${split}_fold_${fold}.log" 2>&1
}

run_a2_score() {
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
    > "${RUN}/logs/posta0_a2_verifier_fold_${fold}.log" 2>&1
}

# The first handoff has already launched all current workers. Pause only its
# parent coordinator so it cannot recreate post-A0 outputs after this relay.
if [[ -f "${RUN}/pids/handoff_v1_launcher.pid" ]]; then
  handoff_pid="$(cat "${RUN}/pids/handoff_v1_launcher.pid")"
  if kill -0 "${handoff_pid}" 2>/dev/null; then
    kill -STOP "${handoff_pid}"
    echo "${handoff_pid}" > "${RUN}/pids/handoff_v1_paused_by_posta0.pid"
  fi
fi

echo "$$" > "${RUN}/pids/posta0_relay_v1.pid"
cp evaluation/scripts/run_adsqa_full5320_posta0_relay_v1.sh "${RUN}/source_snapshot/"
mark POSTA0_RELAY_V1_LAUNCHED

wait_a0_all

"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_full_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores-root "${A0_SHARDS}" \
  --output-dir "${A0_MERGED}" \
  --expected-count 5320 \
  --expected-videos 1521 \
  --expected-per-fold 1064 \
  > "${RUN}/logs/posta0_merge_a0.log" 2>&1
"${PY}" evaluation/tools/build_selective_evidence_rewrite_full530_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores "${A0_MERGED}/scores_all.jsonl" \
  --av-manifest "${RUN}/av_manifest_v1/av_funnel_full5320.jsonl" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root "${DATA}/asr_union_records" \
  --output-dir "${TRIGGER}" \
  > "${RUN}/logs/posta0_build_trigger530.log" 2>&1
"${PY}" evaluation/tools/build_qwen3_adaptive_crop_full530_arms_v1.py \
  --input-jsonl "${TRIGGER}/items_answer_free.jsonl" \
  --output-root "${ARMS}" \
  --smoke-per-fold 2 \
  > "${RUN}/logs/posta0_build_adaptive_arms.log" 2>&1
mark POSTA0_TRIGGER530_READY

# Smoke remains mandatory. Three cards cover five folds in two waves.
run_adaptive 3 smoke10 2 0 & p0="$!"
run_adaptive 4 smoke10 2 1 & p1="$!"
run_adaptive 5 smoke10 2 2 & p2="$!"
wait "${p0}" "${p1}" "${p2}"
run_adaptive 3 smoke10 2 3 & p3="$!"
run_adaptive 4 smoke10 2 4 & p4="$!"
wait "${p3}" "${p4}"
"${PY}" evaluation/tools/audit_qwen3_adaptive_crop_full_v1.py \
  --dataset-root "${ARMS}" \
  --run-root "${CROP}" \
  --split smoke10 \
  --output "${RUN}/smoke10_adaptive_protocol_audit.json" \
  > "${RUN}/logs/posta0_audit_adaptive_smoke10.log" 2>&1
mark POSTA0_ADAPTIVE_SMOKE_COMPLETE

# Full A2 inference, again using only the newly available GPU3/4/5.
run_adaptive 3 full530 106 0 & p0="$!"
run_adaptive 4 full530 106 1 & p1="$!"
run_adaptive 5 full530 106 2 & p2="$!"
wait "${p0}" "${p1}" "${p2}"
run_adaptive 3 full530 106 3 & p3="$!"
run_adaptive 4 full530 106 4 & p4="$!"
wait "${p3}" "${p4}"
"${PY}" evaluation/tools/audit_qwen3_adaptive_crop_full_v1.py \
  --dataset-root "${ARMS}" \
  --run-root "${CROP}" \
  --split full530 \
  --output "${RUN}/full530_adaptive_protocol_audit.json" \
  > "${RUN}/logs/posta0_audit_adaptive_full530.log" 2>&1
mark POSTA0_ADAPTIVE_FULL530_COMPLETE

"${PY}" evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CROP}/full530/adaptive_scale" \
  --output-dir "${A2_INPUTS}" \
  --expected-count 530 \
  --expected-videos 530 \
  --expected-per-fold 106 \
  > "${RUN}/logs/posta0_build_a2_inputs.log" 2>&1

run_a2_score 3 0 & p0="$!"
run_a2_score 4 1 & p1="$!"
run_a2_score 5 2 & p2="$!"
wait "${p0}" "${p1}" "${p2}"
run_a2_score 3 3 & p3="$!"
run_a2_score 4 4 & p4="$!"
wait "${p3}" "${p4}"

"${PY}" evaluation/tools/merge_selective_rewrite_a2_scores_v1.py \
  --shard-root "${A2_SHARDS}" \
  --output-dir "${A2_MERGED}" \
  --expected-count 530 \
  --expected-per-fold 106 \
  > "${RUN}/logs/posta0_merge_a2.log" 2>&1
"${PY}" evaluation/tools/freeze_mmr_selectrescue_full_v1.py \
  --delegate evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CROP}/full530/adaptive_scale" \
  --a0-scores "${A0_MERGED}/scores_all.jsonl" \
  --a2-scores "${A2_MERGED}/scores_all.jsonl" \
  --output-dir "${CHOICES}" \
  --support-threshold 0.8933094143867493 \
  --minimum-margin 0.25 \
  > "${RUN}/logs/posta0_freeze_choices.log" 2>&1
mark POSTA0_JOINT_CHOICES_FROZEN

wait_uniform_all
for fold in 0 1 2 3 4; do
  "${PY}" evaluation/tools/audit_adsqa_uniform8_full_v1.py \
    --questions "${DATA}/shards/fold_${fold}.json" \
    --inference-root "${UNIFORM}" \
    --output "${UNIFORM}/audits/fold_${fold}.json" \
    --expected-count 1064 \
    > "${RUN}/logs/posta0_audit_uniform_fold_${fold}.log" 2>&1
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
  > "${RUN}/logs/posta0_materialize_candidates.log" 2>&1

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
  > "${RUN}/logs/posta0_judge_preflight.log" 2>&1

(
  cd "${RUN}"
  find FROZEN_PROTOCOL.json selected8_manifest_v1 raw_features_v1 \
    av_manifest_v1 mmr8_full5320_v1 a0_pool_v1 a0_verifier_merged_v1 \
    trigger530_dataset_v1 adaptive_scale_arms_v1 adaptive_scale_inference_v1 \
    a2_verifier_merged_v1 frozen_choices_v1 uniform8_full5320_v1 \
    final_protocol_audit_v1 judge_deepseek_v1/preflight_v1 source_snapshot \
    -type f -print0 | sort -z | xargs -0 sha256sum > INFERENCE_SHA256SUMS
)
mark POSTA0_INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION
