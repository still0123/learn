#!/usr/bin/env bash
set -euo pipefail

cd /data1/rmx/projectb/AdsQA-main
RUN=data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1
LOG="$RUN/logs/a2_verifier_merge_v2.log"
exec >>"$LOG" 2>&1
echo "merge_relay_start=$(date -Is)"

for fold in 0 1 2 3 4; do
  pid=$(cat "$RUN/pids/a2_verifier_v2_fold_${fold}.pid")
  while kill -0 "$pid" 2>/dev/null; do sleep 20; done
  test -s "$RUN/a2_verifier_scores_v2/fold_${fold}/scores.jsonl"
done

rm -rf "$RUN/a2_verifier_merged_v2"
python3 evaluation/tools/merge_evads_a2_scores_v2.py \
  --input-dir "$RUN/a2_verifier_pool_v2" \
  --shard-root "$RUN/a2_verifier_scores_v2" \
  --output-dir "$RUN/a2_verifier_merged_v2"

python3 - <<'PY'
import hashlib
import json
from collections import Counter
from pathlib import Path

run = Path("data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1")
data = run / "threshold_crop_or_full_pool_v2"
items = {str(x["question_id"]): x for x in map(json.loads, (data / "items_answer_free.jsonl").read_text().splitlines())}
a0 = {str(x["source_question_id"]): x for x in map(json.loads, (run / "a0_verifier_merged/scores_all.jsonl").read_text().splitlines())}
a2 = {str(x["source_question_id"]): x for x in map(json.loads, (run / "a2_verifier_merged_v2/scores_all.jsonl").read_text().splitlines())}
threshold = 0.9241418242454529
rows=[]
for qid,item in items.items():
    fold=int(item["fold"])
    d=run / "a2_crop_or_full_v2_by_fold" / f"fold_{fold}" / qid
    pred=json.loads((d / "a2_prediction.json").read_text())
    trace=json.loads((d / "a2_trace.json").read_text())
    p0=float(a0[qid]["support_probability"]); p2=float(a2[qid]["support_probability"])
    switch=(p2 >= threshold and p2 > p0 and trace.get("parse_valid") is True)
    a0_text=str(item["a0_prediction"]); a2_text=str(pred["prediction"])
    rows.append({
      "schema_version":"readr_crop_or_full_frozen_choice_v2",
      "question_id":qid,"video_id":str(item["video_id"]),"fold":fold,
      "a0_prediction":a0_text,"a2_prediction":a2_text,
      "final_prediction":a2_text if switch else a0_text,
      "switched":switch,
      "answer_changed":switch and " ".join(a0_text.casefold().split()) != " ".join(a2_text.casefold().split()),
      "a0_support_probability":p0,"a2_support_probability":p2,
      "support_difference_a2_minus_a0":p2-p0,
      "support_threshold":threshold,"minimum_margin":0.0,
      "a2_parse_valid":trace.get("parse_valid") is True,
      "route_crop_anchor_count":sum(x.get("view_type")=="crop_or_full_router_crop" for x in trace.get("extra_view_plan",[])),
      "groundtruth_read":False,"judge_scores_read":False,
    })
rows.sort(key=lambda x:(x["fold"],x["question_id"]))
out=run / "frozen_choices_crop_or_full_v2"
out.mkdir(exist_ok=False)
p=out / "frozen_choices_answer_free.jsonl"
p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
audit={
 "schema_version":"readr_crop_or_full_gate_audit_v2","passed":len(rows)==257 and set(items)==set(a2),
 "rows":len(rows),"videos":len({x["video_id"] for x in rows}),"fold_counts":dict(Counter(str(x["fold"]) for x in rows)),
 "switches":sum(x["switched"] for x in rows),"actual_answer_changes":sum(x["answer_changed"] for x in rows),
 "parse_valid":sum(x["a2_parse_valid"] for x in rows),"parse_fallback":sum(not x["a2_parse_valid"] for x in rows),
 "crop_anchor_distribution":dict(Counter(str(x["route_crop_anchor_count"]) for x in rows)),
 "support_threshold":threshold,"minimum_margin":0.0,"groundtruth_read":False,"judge_scores_read":False,
 "choices_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
}
(out / "protocol_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(audit,ensure_ascii=False,indent=2))
PY

touch "$RUN/FINAL_CHOICES_READY_AWAITING_JUDGE_AUTHORIZATION"
echo "merge_relay_complete=$(date -Is)"
