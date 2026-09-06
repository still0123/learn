#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
PYTHON="/data1/rmx/ana3/envs/ReadR/bin/python"
WORKER="$PROJECT_ROOT/evaluation/scripts/run_claim_evidence_mmr_cache_worker_v1.sh"
QUESTION_FILE="${QUESTION_FILE:?set QUESTION_FILE}"
RUN_ROOT="${RUN_ROOT:?set RUN_ROOT}"
END_IDX="${END_IDX:?set END_IDX}"
OVERWRITE="${OVERWRITE:-0}"
NUM_SHARDS=3

mkdir -p "$RUN_ROOT/launcher_logs" "$RUN_ROOT/source_snapshot"
cp "$0" "$WORKER" "$RUN_ROOT/source_snapshot/"
pids=()
for shard in 0 1 2; do
  log="$RUN_ROOT/launcher_logs/cpu_shard${shard}of${NUM_SHARDS}.log"
  nice -n 10 env QUESTION_FILE="$QUESTION_FILE" RUN_ROOT="$RUN_ROOT" END_IDX="$END_IDX" \
    SHARD_ID="$shard" NUM_SHARDS="$NUM_SHARDS" OVERWRITE="$OVERWRITE" \
    OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}" \
    bash "$WORKER" >"$log" 2>&1 &
  pids+=("$!")
  echo "started cache shard=$shard pid=${pids[-1]} log=$log"
done
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup INT TERM
status=0
for pid in "${pids[@]}"; do if ! wait "$pid"; then status=1; fi; done
trap - INT TERM
(( status == 0 )) || exit "$status"

"$PYTHON" - "$QUESTION_FILE" "$RUN_ROOT" "$NUM_SHARDS" <<'PY'
import json, pathlib, sys
question_file, run_root, num_shards = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
questions = json.loads(question_file.read_text(encoding="utf-8"))
by_id = {}
for shard in range(num_shards):
    path = run_root / f"cache_shard{shard}of{num_shards}.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        qid = str(row["question_id"])
        if qid in by_id:
            raise SystemExit(f"duplicate cache question_id: {qid}")
        by_id[qid] = row
expected = [str(row["question_id"]) for row in questions]
missing = [qid for qid in expected if qid not in by_id]
extra = sorted(set(by_id) - set(expected))
if missing or extra:
    raise SystemExit(f"cache merge mismatch: missing={len(missing)} extra={len(extra)}")
output = run_root / "cache_shard0.jsonl"
with output.open("w", encoding="utf-8") as handle:
    for qid in expected:
        handle.write(json.dumps(by_id[qid], ensure_ascii=False) + "\n")
print(f"merged={len(expected)} output={output}")
PY
echo "claim_evidence_mmr_cache=complete"
