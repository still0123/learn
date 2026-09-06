#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data1/rmx/projectb/AdsQA-main"
RUN_ROOT="$PROJECT_ROOT/evaluation/runs/innovation1_confirm3000_shared32_v1"
SELECTION_ROOT="$RUN_ROOT/selection"
QUESTION_FILE="$SELECTION_ROOT/question.json"
PARALLEL_ROOT="$SELECTION_ROOT/parallel_gate_gpu345_v1"
QUESTION_ROOT="$PARALLEL_ROOT/questions"
OUTPUT_ROOT="$PARALLEL_ROOT/manifests"
LOG_ROOT="$PARALLEL_ROOT/logs"
FINAL_RAW="$SELECTION_ROOT/full_gate_manifest.jsonl"
FINAL_AUDIT="$SELECTION_ROOT/full_gate_manifest.audit.json"
OVERLAY_ROOT="$SELECTION_ROOT/video_overlay_v1"
OVERLAY_AUDIT="$SELECTION_ROOT/video_overlay_v1.json"
PYTHON_BIN="/data1/rmx/ana3/envs/ReadR/bin/python"
OVERLAY_BUILDER="$PROJECT_ROOT/evaluation/tools/prepare_confirm3000_video_overlay_v1.py"
BUILDER="$PROJECT_ROOT/evaluation/tools/build_qwen25_av_gate_manifest_v1.py"
GPU_IDS=(3 4 5)
SHARD_COUNT=3

cd "$PROJECT_ROOT"
mkdir -p "$QUESTION_ROOT" "$OUTPUT_ROOT" "$LOG_ROOT"

if [[ ! -f "$OVERLAY_AUDIT" ]]; then
  "$PYTHON_BIN" "$OVERLAY_BUILDER" \
    --question-file "$QUESTION_FILE" \
    --original-root "$PROJECT_ROOT/data/videos" \
    --repair-root "$PROJECT_ROOT/data/video_repair_cache_v1" \
    --frames-root "$PROJECT_ROOT/data/frames_8" \
    --output-root "$OVERLAY_ROOT" \
    --manifest "$OVERLAY_AUDIT"
fi

echo "parallel_gate_gpu345_start $(date -Is) gpus=${GPU_IDS[*]}"

"$PYTHON_BIN" - "$QUESTION_FILE" "$QUESTION_ROOT" "$PARALLEL_ROOT/shard_manifest.json" "$SHARD_COUNT" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
out_dir = Path(sys.argv[2]).resolve()
manifest_path = Path(sys.argv[3]).resolve()
shard_count = int(sys.argv[4])
items = json.loads(source.read_text(encoding="utf-8"))
if not isinstance(items, list) or not items:
    raise SystemExit("question file must contain a non-empty JSON list")
ids = [str(item.get("question_id", "")) for item in items]
if any(not item_id for item_id in ids) or len(set(ids)) != len(ids):
    raise SystemExit("question IDs must be present and unique")
out_dir.mkdir(parents=True, exist_ok=True)
count = len(items)
shards = []
for shard_id in range(shard_count):
    start = shard_id * count // shard_count
    end = (shard_id + 1) * count // shard_count
    shard_items = items[start:end]
    path = out_dir / f"shard_{shard_id}.json"
    path.write_text(json.dumps(shard_items, ensure_ascii=True), encoding="utf-8")
    shards.append({
        "shard_id": shard_id,
        "start_index": start,
        "end_index": end,
        "question_count": len(shard_items),
        "question_ids": [str(item["question_id"]) for item in shard_items],
        "question_file": str(path),
    })
manifest_path.write_text(json.dumps({
    "schema_version": "confirm3000_parallel_gate_gpu345_v1",
    "source_question_file": str(source),
    "source_question_count": count,
    "source_question_ids": ids,
    "shards": shards,
    "gpu_ids": [3, 4, 5],
    "groundtruth_read": False,
    "answer_content_used_for_partition": False,
    "not_human_gold": True,
}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"question_count": count, "shard_counts": [row["question_count"] for row in shards]}))
PY

wait_for_idle() {
  local all_idle=1
  local gpu apps memory
  for gpu in "${GPU_IDS[@]}"; do
    apps="$(nvidia-smi --id="$gpu" --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null | sed '/^[[:space:]]*$/d')"
    memory="$(nvidia-smi --id="$gpu" --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d ' ')"
    if [[ -n "$apps" || "${memory:-999999}" -gt 256 ]]; then
      echo "waiting_gate_gpu $(date -Is) gpu=$gpu apps=${apps:-none} memory=${memory:-unknown}"
      all_idle=0
    fi
  done
  [[ "$all_idle" -eq 1 ]]
}

while ! wait_for_idle; do
  sleep 30
done

declare -a PIDS=()
for shard_id in 0 1 2; do
  gpu_id="${GPU_IDS[$shard_id]}"
  question_path="$QUESTION_ROOT/shard_${shard_id}.json"
  output_path="$OUTPUT_ROOT/gate_manifest_gpu${gpu_id}_shard${shard_id}.jsonl"
  log_path="$LOG_ROOT/gate_gpu${gpu_id}_shard${shard_id}.log"
  nohup env CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES="$gpu_id" \
    "$PYTHON_BIN" "$BUILDER" \
    --gpu-id "$gpu_id" \
    --question-file "$question_path" \
    --output "$output_path" \
    --video-root "$OVERLAY_ROOT" \
    --frames-fallback-root "$PROJECT_ROOT/data/frames_8" \
    --overwrite > "$log_path" 2>&1 < /dev/null &
  PIDS[$shard_id]=$!
  echo "gate_shard_started $(date -Is) gpu=$gpu_id shard=$shard_id pid=${PIDS[$shard_id]}"
done

failed=0
for shard_id in 0 1 2; do
  if wait "${PIDS[$shard_id]}"; then
    echo "gate_shard_finished $(date -Is) shard=$shard_id"
  else
    echo "gate_shard_failed $(date -Is) shard=$shard_id"
    failed=1
  fi
done
if [[ "$failed" -ne 0 ]]; then
  exit 1
fi

"$PYTHON_BIN" - "$QUESTION_FILE" "$OUTPUT_ROOT" "$FINAL_RAW" "$FINAL_AUDIT" "$PARALLEL_ROOT/shard_manifest.json" "$OVERLAY_AUDIT" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

question_path = Path(sys.argv[1]).resolve()
output_root = Path(sys.argv[2]).resolve()
final_path = Path(sys.argv[3]).resolve()
audit_path = Path(sys.argv[4]).resolve()
shard_manifest_path = Path(sys.argv[5]).resolve()
overlay_audit_path = Path(sys.argv[6]).resolve()

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

questions = json.loads(question_path.read_text(encoding="utf-8"))
expected_ids = [str(item["question_id"]) for item in questions]
expected_set = set(expected_ids)
by_id = {}
shard_rows = []
for path in sorted(output_root.glob("gate_manifest_gpu*_shard*.jsonl")):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    shard_ids = []
    for row in rows:
        question_id = str(row.get("question_id", ""))
        if not question_id or question_id in by_id:
            raise SystemExit(f"duplicate or missing question_id in shards: {question_id}")
        by_id[question_id] = row
        shard_ids.append(question_id)
    shard_rows.append({
        "path": str(path),
        "sha256": sha256(path),
        "question_count": len(rows),
        "question_ids": shard_ids,
    })
missing = [question_id for question_id in expected_ids if question_id not in by_id]
extra = [question_id for question_id in by_id if question_id not in expected_set]
if missing or extra or len(by_id) != len(expected_ids):
    raise SystemExit(json.dumps({"missing": missing[:10], "extra": extra[:10], "merged": len(by_id), "expected": len(expected_ids)}))
merged = [by_id[question_id] for question_id in expected_ids]
temp_path = final_path.with_suffix(final_path.suffix + ".tmp")
temp_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in merged), encoding="utf-8")
os.replace(temp_path, final_path)
audit = {
    "schema_version": "qwen25_confirm3000_parallel_gate_gpu345_merge_audit_v1",
    "passed": True,
    "source_question_file": str(question_path),
    "source_question_sha256": sha256(question_path),
    "source_question_count": len(expected_ids),
    "merged_manifest": str(final_path),
    "merged_manifest_sha256": sha256(final_path),
    "merged_question_count": len(merged),
    "shard_count": len(shard_rows),
    "gpu_ids": [3, 4, 5],
    "shards": shard_rows,
    "shard_manifest": str(shard_manifest_path),
    "video_overlay_manifest": str(overlay_audit_path),
    "video_overlay_manifest_sha256": sha256(overlay_audit_path),
    "question_ids_unique": len(set(expected_ids)) == len(expected_ids),
    "question_ids_ordered_to_source": True,
    "groundtruth_read": False,
    "answer_content_used_for_partition": False,
    "not_human_gold": True,
}
audit_path.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, ensure_ascii=True, indent=2))
PY

echo "parallel_gate_gpu345_complete $(date -Is) output=$FINAL_RAW"
