#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
run=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
py=/data1/rmx/ana3/envs/ReadR/bin/python
model=/data1/qky/Model/Qwen3Vl-8B
adapter=evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/train/adapter
pool="$run/a0_verifier_pool"
scores="$run/a0_verifier_shards"

mkdir -p "$run/logs" "$run/pids" "$run/a0_mmr8_by_fold"
"$py" - "$run/dataset/questions_answer_free.json" "$run/a0_mmr8" "$run/a0_mmr8_by_fold" <<'PY'
import json, os, pathlib, sys
questions = json.load(open(sys.argv[1], encoding="utf-8"))
source = pathlib.Path(sys.argv[2]).resolve()
target = pathlib.Path(sys.argv[3])
for row in questions:
    fold = int(row["fold"])
    qid = str(row["question_id"])
    item = source / qid
    if not (item / "prediction.json").is_file() or not (item / "evidence.json").is_file():
        raise RuntimeError(f"missing source artifacts for {qid}")
    fold_dir = target / f"fold_{fold}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    link = fold_dir / qid
    if link.is_symlink():
        if link.resolve() != item:
            raise RuntimeError(f"stale link for {qid}")
    elif link.exists():
        raise RuntimeError(f"non-link target exists for {qid}")
    else:
        link.symlink_to(item, target_is_directory=True)
PY

if [[ ! -f "$run/A0_VERIFIER_POOL_COMPLETE" ]]; then
  "$py" evaluation/tools/build_evads_a0_verifier_pool_v2.py \
    --questions "$run/dataset/questions_answer_free.json" \
    --a0-root "$run/a0_mmr8_by_fold" \
    --video-root data/external/evads_v1/videos_unpacked/videos \
    --output-dir "$pool" \
    --expected-method ReAdR_EVAdsFresh500_MMR8 \
    --candidate-method ReAdR_EVAdsFresh500_MMR8_A0 \
    --expected-count 500 \
    --expected-videos 100 \
    --expected-per-fold 100 \
    --expected-visual-tokens 1296
  touch "$run/A0_VERIFIER_POOL_COMPLETE"
fi

run_fold() {
  local fold=$1
  local gpu=$2
  "$py" evaluation/tools/score_answer_claims_qwen3_v1.py \
    --gpu-id "$gpu" \
    --model-dir "$model" \
    --adapter-dir "$adapter" \
    --input-jsonl "$pool/shards/fold_${fold}.jsonl" \
    --output-dir "$scores/fold_${fold}" \
    --views 8 \
    --unified-size 448 \
    --max-visual-tokens 4096 \
    > "$run/logs/a0_verifier_fold_${fold}.log" 2>&1
}

run_fold 0 0 & p0=$!
run_fold 1 1 & p1=$!
wait "$p0" "$p1"
run_fold 2 0 & p2=$!
run_fold 3 1 & p3=$!
wait "$p2" "$p3"
run_fold 4 0
touch "$run/A0_VERIFIER_SHARDS_COMPLETE"
