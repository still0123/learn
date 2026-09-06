#!/usr/bin/env bash
set -euo pipefail

ROOT="/data1/rmx/projectb/AdsQA-main"
PY="/data1/rmx/ana3/envs/ReadR/bin/python"
RUN="${ROOT}/evaluation/runs/qwen3_joint_confirm1000_v1"
MODEL="/data1/qky/Model/Qwen3Vl-8B"
ADAPTER="${ROOT}/evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter"
PREP="${RUN}/prepared_answer_free_v1"
RAW="${RUN}/raw_features_v1"
AV="${RUN}/av_manifest_v1"
SELECTED="${RUN}/selected8_manifest_v1"
A0="${RUN}/a0_inference_v1"
A0_POOL="${RUN}/a0_pool_v1"
A0_SCORE_SHARDS="${RUN}/a0_verifier_shards_v1"
A0_SCORES="${RUN}/a0_verifier_merged_v1"
TRIGGER="${RUN}/trigger100_dataset_v1"
FULL_REWRITE="${RUN}/full_rewrite_inference_v1"
CONTROL_REWRITE="${RUN}/extraglobal_control_inference_v1"
FULL_A2_INPUTS="${RUN}/full_a2_verifier_inputs_v1"
CONTROL_A2_INPUTS="${RUN}/control_a2_verifier_inputs_v1"
FULL_A2_SHARDS="${RUN}/full_a2_verifier_shards_v1"
CONTROL_A2_SHARDS="${RUN}/control_a2_verifier_shards_v1"
FULL_A2_SCORES="${RUN}/full_a2_verifier_merged_v1"
CONTROL_A2_SCORES="${RUN}/control_a2_verifier_merged_v1"
FULL_CHOICES="${RUN}/full_frozen_choices_v1"
CONTROL_CHOICES="${RUN}/control_frozen_choices_v1"
MMR="${RUN}/mmr8_inference_v1"
FINAL="${RUN}/final_protocol_audit_v1"
RESUME_DECODE_RECOVERY="${RESUME_DECODE_RECOVERY:-0}"
RESUME_AFTER_A0_REPAIR="${RESUME_AFTER_A0_REPAIR:-0}"
RESUME_AFTER_A0_VERIFIER_REPAIR="${RESUME_AFTER_A0_VERIFIER_REPAIR:-0}"

assert_idle() {
  local gpu="$1"
  local active
  active="$(nvidia-smi --id="${gpu}" --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits)"
  if [[ -n "${active}" ]]; then
    echo "GPU${gpu} is not idle: ${active}" >&2
    return 1
  fi
}

wait_pid_files() {
  local prefix="$1"
  local count="$2"
  local status=0
  local index pid
  for ((index=0; index<count; index++)); do
    pid="$(<"${RUN}/pids/${prefix}_${index}.pid")"
    if ! wait "${pid}"; then
      status=1
    fi
  done
  return "${status}"
}

mark() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${RUN}/$1"
}

if [[ -e "${RUN}/PIPELINE_LAUNCHED" && "${RESUME_DECODE_RECOVERY}" != "1" && "${RESUME_AFTER_A0_REPAIR}" != "1" && "${RESUME_AFTER_A0_VERIFIER_REPAIR}" != "1" ]]; then
  echo "refusing duplicate Confirm-1000 pipeline launch" >&2
  exit 1
fi
test -f "${RUN}/FROZEN_PROTOCOL"
test -f "${PREP}/audit.json"
test -f "${RUN}/asr_supplement_v1/COMPLETE"
mkdir -p "${RUN}/logs" "${RUN}/pids" "${RUN}/source_snapshot"
if [[ "${RESUME_AFTER_A0_VERIFIER_REPAIR}" == "1" ]]; then
  test -f "${RUN}/PIPELINE_A0_REPAIR_CONTINUATION_FAILED"
  trap 'mark PIPELINE_A0_VERIFIER_REPAIR_CONTINUATION_FAILED' ERR
  mark PIPELINE_A0_VERIFIER_REPAIR_CONTINUATION_LAUNCHED
elif [[ "${RESUME_AFTER_A0_REPAIR}" == "1" ]]; then
  test -f "${RUN}/PIPELINE_RECOVERY_FAILED"
  trap 'mark PIPELINE_A0_REPAIR_CONTINUATION_FAILED' ERR
  mark PIPELINE_A0_REPAIR_CONTINUATION_LAUNCHED
elif [[ "${RESUME_DECODE_RECOVERY}" == "1" ]]; then
  test -f "${RUN}/PIPELINE_FAILED"
  trap 'mark PIPELINE_RECOVERY_FAILED' ERR
  mark PIPELINE_RECOVERY_LAUNCHED
else
  trap 'mark PIPELINE_FAILED' ERR
  mark PIPELINE_LAUNCHED
fi
cd "${ROOT}"

cp evaluation/tools/prepare_qwen3_selective_rewrite_confirm1000_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/build_selective_evidence_rewrite_confirm100_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/build_adsqa_clip_mmr8_manifest_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/build_diverse_local8_manifest_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/build_avfunnel8_manifest_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_adsqa_answer_lora_qwen3_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/score_answer_claims_qwen3_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_qwen3_selective_evidence_rewrite_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_qwen3_selective_evidence_rewrite_ablation_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/freeze_selective_evidence_rewrite_ablation_choices_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/audit_and_materialize_qwen3_joint_confirm1000_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/build_diverse_local8_manifest_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_adsqa_answer_lora_qwen3_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py "${RUN}/source_snapshot/"
cp evaluation/scripts/run_qwen3_joint_confirm1000_v1.sh "${RUN}/source_snapshot/"

# Build answer-free visual evidence features and the frozen MMR manifest.
if [[ "${RESUME_AFTER_A0_REPAIR}" != "1" && "${RESUME_AFTER_A0_VERIFIER_REPAIR}" != "1" ]]; then
mkdir -p "${RAW}" "${SELECTED}"
if [[ "${RESUME_DECODE_RECOVERY}" == "1" ]]; then
  for shard in 0 1 2; do
    test "$(wc -l < "${RAW}/shard_${shard}.jsonl")" -eq 200
  done
  test "$(wc -l < "${SELECTED}/mmr8.jsonl")" -eq 1000
  recovery_count=0
  if [[ ! -f "${RAW}/shard_3.jsonl" || "$(wc -l < "${RAW}/shard_3.jsonl")" -ne 200 ]]; then
    assert_idle 5
    nohup "${PY}" evaluation/tools/build_diverse_local8_manifest_decode_recovery_v1.py \
      --gpu-id 5 \
      --questions "${PREP}/raw_feature_shards/shard_3.json" \
      --segmented-asr-root "${PREP}/asr_union_records" \
      --ocr-root data/candidate_cache_full_v1/ocr \
      --clip-path models/clip-vit-large-patch14 \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output "${RAW}/shard_3.jsonl" \
      > "${RUN}/logs/raw_features_3_recovery.log" 2>&1 &
    echo "$!" > "${RUN}/pids/raw_recovery_${recovery_count}.pid"
    recovery_count=$((recovery_count + 1))
  fi
  if [[ ! -f "${RAW}/shard_4.jsonl" || "$(wc -l < "${RAW}/shard_4.jsonl")" -ne 200 ]]; then
    assert_idle 1
    nohup "${PY}" evaluation/tools/build_diverse_local8_manifest_v1.py \
      --gpu-id 1 \
      --questions "${PREP}/raw_feature_shards/shard_4.json" \
      --segmented-asr-root "${PREP}/asr_union_records" \
      --ocr-root data/candidate_cache_full_v1/ocr \
      --clip-path models/clip-vit-large-patch14 \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output "${RAW}/shard_4.jsonl" \
      > "${RUN}/logs/raw_features_4.log" 2>&1 &
    echo "$!" > "${RUN}/pids/raw_recovery_${recovery_count}.pid"
    recovery_count=$((recovery_count + 1))
  fi
  if [[ "${recovery_count}" -gt 0 ]]; then
    wait_pid_files raw_recovery "${recovery_count}"
  fi
  mark DECODE_RECOVERY_COMPLETE
else
  for gpu in 1 2 3 4 5; do
    assert_idle "${gpu}"
  done
  raw_gpus=(1 2 4 5)
  for shard in 0 1 2 3; do
    gpu="${raw_gpus[shard]}"
    nohup "${PY}" evaluation/tools/build_diverse_local8_manifest_v1.py \
      --gpu-id "${gpu}" \
      --questions "${PREP}/raw_feature_shards/shard_${shard}.json" \
      --segmented-asr-root "${PREP}/asr_union_records" \
      --ocr-root data/candidate_cache_full_v1/ocr \
      --clip-path models/clip-vit-large-patch14 \
      --video-root data/videos \
      --frames-fallback-root data/frames_8 \
      --output "${RAW}/shard_${shard}.jsonl" \
      > "${RUN}/logs/raw_features_${shard}.log" 2>&1 &
    echo "$!" > "${RUN}/pids/raw_first_${shard}.pid"
  done
  nohup "${PY}" evaluation/tools/build_adsqa_clip_mmr8_manifest_v1.py \
    --gpu-id 3 \
    --questions "${PREP}/questions_answer_free.json" \
    --clip-cache-root data/candidate_cache_full_v1/clip \
    --clip-model models/clip-vit-large-patch14 \
    --clip-output "${SELECTED}/clip_topk8.jsonl" \
    --mmr-output "${SELECTED}/mmr8.jsonl" \
    --audit-output "${SELECTED}/audit.json" \
    > "${RUN}/logs/mmr_manifest.log" 2>&1 &
  echo "$!" > "${RUN}/pids/mmr_manifest_0.pid"
  wait_pid_files raw_first 4
  wait_pid_files mmr_manifest 1

  assert_idle 1
  "${PY}" evaluation/tools/build_diverse_local8_manifest_v1.py \
    --gpu-id 1 \
    --questions "${PREP}/raw_feature_shards/shard_4.json" \
    --segmented-asr-root "${PREP}/asr_union_records" \
    --ocr-root data/candidate_cache_full_v1/ocr \
    --clip-path models/clip-vit-large-patch14 \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output "${RAW}/shard_4.jsonl" \
    > "${RUN}/logs/raw_features_4.log" 2>&1
fi

"${PY}" evaluation/tools/merge_answer_free_raw_features_v1.py \
  --questions "${PREP}/questions_answer_free.json" \
  --input "${RAW}/shard_0.jsonl" \
  --input "${RAW}/shard_1.jsonl" \
  --input "${RAW}/shard_2.jsonl" \
  --input "${RAW}/shard_3.jsonl" \
  --input "${RAW}/shard_4.jsonl" \
  --output "${RAW}/raw_features_all.jsonl" \
  --audit "${RAW}/merge_audit.json" \
  --expected-count 1000 \
  > "${RUN}/logs/merge_raw_features.log" 2>&1

"${PY}" evaluation/tools/build_avfunnel8_manifest_v1.py \
  --questions "${PREP}/questions_answer_free.json" \
  --raw-features "${RAW}/raw_features_all.jsonl" \
  --output "${AV}/av_funnel_confirm1000.jsonl" \
  --audit "${AV}/audit.json" \
  > "${RUN}/logs/build_av_manifest.log" 2>&1
mark EVIDENCE_MANIFESTS_COMPLETE

# Generate the Uniform8 A0 answers.
for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  assert_idle "${gpu}"
  nohup "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --method CleanQwen3_Raw8 \
    --question-file "${PREP}/a0_shards/fold_${fold}.json" \
    --asr-file "${PREP}/asr_combined_answer_free.json" \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output-dir "${A0}/fold_${fold}/base" \
    --views 8 \
    --unified-size 512 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256 \
    > "${RUN}/logs/a0_fold_${fold}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/a0_${fold}.pid"
done
wait_pid_files a0 5
mark A0_INFERENCE_COMPLETE
else
  test -f "${RUN}/EVIDENCE_MANIFESTS_COMPLETE"
  test "$(wc -l < "${RAW}/raw_features_all.jsonl")" -eq 1000
  test "$(wc -l < "${AV}/av_funnel_confirm1000.jsonl")" -eq 1000
  test "$(wc -l < "${SELECTED}/mmr8.jsonl")" -eq 1000
  for fold in 0 1 2 3 4; do
    test "$(find "${A0}/fold_${fold}/base" -mindepth 2 -maxdepth 2 -type f -name prediction.json | wc -l)" -eq 200
  done
  mark A0_REPAIR_VALIDATED
fi

if [[ "${RESUME_AFTER_A0_VERIFIER_REPAIR}" != "1" ]]; then
"${PY}" evaluation/tools/build_qwen3_a0_verifier_pool_v1.py \
  --questions "${PREP}/questions_answer_free.json" \
  --qwen3-oof-root "${A0}" \
  --video-root data/videos \
  --output-dir "${A0_POOL}" \
  --expected-count 1000 \
  --expected-videos 1000 \
  --expected-per-fold 200 \
  > "${RUN}/logs/build_a0_pool.log" 2>&1

# Score every A0 answer and freeze the lowest-support 10%.
for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  assert_idle "${gpu}"
  nohup "${PY}" evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${A0_POOL}/shards/fold_${fold}.jsonl" \
    --output-dir "${A0_SCORE_SHARDS}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    --overwrite \
    > "${RUN}/logs/a0_verifier_${fold}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/a0v_${fold}.pid"
done
wait_pid_files a0v 5
else
  for fold in 0 1 2 3 4; do
    test "$(wc -l < "${A0_POOL}/shards/fold_${fold}.jsonl")" -eq 200
    test "$(wc -l < "${A0_SCORE_SHARDS}/fold_${fold}/scores.jsonl")" -eq 200
  done
  mark A0_VERIFIER_REPAIR_VALIDATED
fi

"${PY}" evaluation/tools/merge_qwen3_a0_verifier_pool_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores-root "${A0_SCORE_SHARDS}" \
  --output-dir "${A0_SCORES}" \
  --expected-count 1000 \
  --expected-videos 1000 \
  --expected-per-fold 200 \
  > "${RUN}/logs/merge_a0_verifier.log" 2>&1

"${PY}" evaluation/tools/build_selective_evidence_rewrite_confirm100_v1.py \
  --pool-dir "${A0_POOL}" \
  --scores "${A0_SCORES}/scores_all.jsonl" \
  --av-manifest "${AV}/av_funnel_confirm1000.jsonl" \
  --ocr-root data/candidate_cache_full_v1/ocr \
  --asr-root "${PREP}/asr_union_records" \
  --output-dir "${TRIGGER}" \
  --trigger-count 100 \
  > "${RUN}/logs/build_trigger100.log" 2>&1
mark TRIGGER100_FROZEN

# Run the full local-evidence rewrites in five balanced shards.
for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  assert_idle "${gpu}"
  nohup "${PY}" evaluation/tools/infer_qwen3_selective_evidence_rewrite_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --input-jsonl "${TRIGGER}/shards/fold_${fold}.jsonl" \
    --output-dir "${FULL_REWRITE}/fold_${fold}" \
    --base-size 512 \
    --crop-size 896 \
    --max-visual-tokens 4096 \
    --max-new-tokens 192 \
    --expected-items 20 \
    > "${RUN}/logs/full_rewrite_${fold}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/full_rewrite_${fold}.pid"
done
wait_pid_files full_rewrite 5
mark FULL_REWRITE_COMPLETE

# Run the same-trigger/same-token high-resolution full-frame control.
assert_idle 1
"${PY}" evaluation/tools/infer_qwen3_selective_evidence_rewrite_ablation_v1.py \
  --gpu-id 1 \
  --model-dir "${MODEL}" \
  --input-jsonl "${TRIGGER}/items_answer_free.jsonl" \
  --output-dir "${CONTROL_REWRITE}" \
  --ablation no_local_crop \
  --base-size 512 \
  --crop-size 896 \
  --max-visual-tokens 4096 \
  --max-new-tokens 192 \
  --expected-items 100 \
  > "${RUN}/logs/control_rewrite.log" 2>&1
mark CONTROL_REWRITE_COMPLETE

"${PY}" evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${FULL_REWRITE}" \
  --output-dir "${FULL_A2_INPUTS}" \
  --expected-count 100 \
  --expected-videos 100 \
  --expected-per-fold 20 \
  > "${RUN}/logs/build_full_a2_inputs.log" 2>&1

"${PY}" evaluation/tools/build_selective_rewrite_a2_verifier_inputs_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CONTROL_REWRITE}" \
  --output-dir "${CONTROL_A2_INPUTS}" \
  --expected-count 100 \
  --expected-videos 100 \
  --expected-per-fold 20 \
  > "${RUN}/logs/build_control_a2_inputs.log" 2>&1

for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  assert_idle "${gpu}"
  nohup "${PY}" evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${FULL_A2_INPUTS}/shards/fold_${fold}.jsonl" \
    --output-dir "${FULL_A2_SHARDS}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    --overwrite \
    > "${RUN}/logs/full_a2_verifier_${fold}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/full_a2v_${fold}.pid"
done
wait_pid_files full_a2v 5

for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  assert_idle "${gpu}"
  nohup "${PY}" evaluation/tools/score_answer_claims_qwen3_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --adapter-dir "${ADAPTER}" \
    --input-jsonl "${CONTROL_A2_INPUTS}/shards/fold_${fold}.jsonl" \
    --output-dir "${CONTROL_A2_SHARDS}/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    --overwrite \
    > "${RUN}/logs/control_a2_verifier_${fold}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/control_a2v_${fold}.pid"
done
wait_pid_files control_a2v 5

"${PY}" evaluation/tools/merge_selective_rewrite_a2_scores_v1.py \
  --shard-root "${FULL_A2_SHARDS}" \
  --output-dir "${FULL_A2_SCORES}" \
  --expected-count 100 \
  --expected-per-fold 20 \
  > "${RUN}/logs/merge_full_a2_scores.log" 2>&1

"${PY}" evaluation/tools/merge_selective_rewrite_a2_scores_v1.py \
  --shard-root "${CONTROL_A2_SHARDS}" \
  --output-dir "${CONTROL_A2_SCORES}" \
  --expected-count 100 \
  --expected-per-fold 20 \
  > "${RUN}/logs/merge_control_a2_scores.log" 2>&1

"${PY}" evaluation/tools/freeze_selective_evidence_rewrite_choices_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${FULL_REWRITE}" \
  --a0-scores "${A0_SCORES}/scores_all.jsonl" \
  --a2-scores "${FULL_A2_SCORES}/scores_all.jsonl" \
  --output-dir "${FULL_CHOICES}" \
  --support-threshold 0.8933094143867493 \
  --minimum-margin 0.25 \
  --expected-count 100 \
  --expected-videos 100 \
  --expected-per-fold 20 \
  > "${RUN}/logs/freeze_full_choices.log" 2>&1

"${PY}" evaluation/tools/freeze_selective_evidence_rewrite_ablation_choices_v1.py \
  --dataset-dir "${TRIGGER}" \
  --inference-root "${CONTROL_REWRITE}" \
  --reference-inference-root "${FULL_REWRITE}" \
  --ablation no_local_crop \
  --a0-scores "${A0_SCORES}/scores_all.jsonl" \
  --a2-scores "${CONTROL_A2_SCORES}/scores_all.jsonl" \
  --output-dir "${CONTROL_CHOICES}" \
  --support-threshold 0.8933094143867493 \
  --minimum-margin 0.25 \
  --expected-count 100 \
  --expected-videos 100 \
  --expected-per-fold 20 \
  > "${RUN}/logs/freeze_control_choices.log" 2>&1
mark JOINT_CHOICES_FROZEN

# Run the static MMR8 baseline in five disjoint frozen shards.
for fold in 0 1 2 3 4; do
  gpu="$((fold + 1))"
  assert_idle "${gpu}"
  nohup "${PY}" evaluation/tools/infer_adsqa_answer_lora_qwen3_selected8_decode_recovery_v1.py \
    --gpu-id "${gpu}" \
    --model-dir "${MODEL}" \
    --method CLIPMMR64_8_lambda070 \
    --question-file "${PREP}/a0_shards/fold_${fold}.json" \
    --selection-manifest "${SELECTED}/mmr8.jsonl" \
    --asr-file "${PREP}/asr_combined_answer_free.json" \
    --video-root data/videos \
    --frames-fallback-root data/frames_8 \
    --output-dir "${MMR}/fold_${fold}" \
    --views 8 \
    --unified-size 512 \
    --max-visual-tokens 4096 \
    --max-new-tokens 256 \
    > "${RUN}/logs/mmr8_fold_${fold}.log" 2>&1 &
  echo "$!" > "${RUN}/pids/mmr8_${fold}.pid"
done
wait_pid_files mmr8 5

mkdir -p "${MMR}/audits"
for fold in 0 1 2 3 4; do
  "${PY}" evaluation/tools/audit_adsqa_selected8_inference_v1.py \
    --questions "${PREP}/a0_shards/fold_${fold}.json" \
    --selection-manifest "${SELECTED}/mmr8.jsonl" \
    --inference-dir "${MMR}/fold_${fold}" \
    --output "${MMR}/audits/fold_${fold}.json" \
    --expected-count 200 \
    > "${RUN}/logs/mmr8_audit_${fold}.log" 2>&1
done
mark MMR8_COMPLETE

"${PY}" evaluation/tools/audit_and_materialize_qwen3_joint_confirm1000_v1.py \
  --protocol "${RUN}/PREREGISTERED_PROTOCOL.json" \
  --protocol-marker "${RUN}/FROZEN_PROTOCOL" \
  --questions "${PREP}/questions_answer_free.json" \
  --a0-root "${A0}" \
  --a0-pool "${A0_POOL}" \
  --mmr-root "${MMR}" \
  --mmr-audit-root "${MMR}/audits" \
  --trigger-dataset "${TRIGGER}" \
  --full-inference "${FULL_REWRITE}" \
  --full-choices "${FULL_CHOICES}" \
  --control-inference "${CONTROL_REWRITE}" \
  --control-choices "${CONTROL_CHOICES}" \
  --output-dir "${FINAL}" \
  > "${RUN}/logs/final_protocol_audit.log" 2>&1

find "${RUN}" -type f ! -path '*/pids/*' ! -name SHA256SUMS -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > "${RUN}/SHA256SUMS"
mark INFERENCE_COMPLETE_AWAITING_JUDGE_AUTHORIZATION
