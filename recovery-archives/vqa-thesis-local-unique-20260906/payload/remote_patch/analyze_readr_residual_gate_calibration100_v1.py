#!/usr/bin/env python3
"""Answer-free gate analysis for residual A2 candidates; no reference labels."""
import hashlib
import json
from pathlib import Path

ROOT=Path("evaluation/runs/readr_residual_avfunnel_calibration100_v1")
DATA=ROOT/"dataset_v2"
OLD=Path("evaluation/runs/readr_increment_pilot300_v1/mmr8_verifier_merged/scores_all.jsonl")
TAU=0.9241418242454529
MARGIN=0.0

def load(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def norm(x):
    return " ".join(str(x).casefold().split())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

old={str(x["source_question_id"]):x for x in load(OLD)}
out={}
for variant in ("residual_mid","residual_avfunnel"):
    items={str(x["question_id"]):x for x in load(DATA/variant/"items_answer_free.jsonl")}
    scores={str(x["source_question_id"]):x for x in load(ROOT/f"{variant}_verifier_merged/scores_all.jsonl")}
    rows=[]
    for qid,item in items.items():
        a0=float(old[qid]["support_probability"])
        a2=float(scores[qid]["support_probability"])
        pred_path=ROOT/"shards"/variant/f"fold_{int(item['fold'])}"/qid/"a2_prediction.json"
        pred=json.loads(pred_path.read_text())["prediction"]
        changed=norm(pred)!=norm(item["a0_prediction"])
        review=a0<TAU
        switch=review and changed and a2>=a0+MARGIN
        rows.append({"question_id":qid,"video_id":str(item["video_id"]),"a0_support":a0,"a2_support":a2,"support_delta":a2-a0,"answer_changed":changed,"review_triggered":review,"gate_switched":switch})
    def mean(key):
        return sum(float(x[key]) for x in rows)/len(rows)
    out[variant]={
        "rows":len(rows),"review_trigger_count":sum(x["review_triggered"] for x in rows),
        "review_trigger_rate":mean("review_triggered"),"switch_count":sum(x["gate_switched"] for x in rows),
        "switch_rate":mean("gate_switched"),"answer_change_count":sum(x["answer_changed"] for x in rows),
        "mean_a0_support":mean("a0_support"),"mean_a2_support":mean("a2_support"),"mean_support_delta":mean("support_delta"),
        "min_support_delta":min(x["support_delta"] for x in rows),"max_support_delta":max(x["support_delta"] for x in rows),
        "rows_detail":rows,
    }
output={"schema_version":"readr_residual_gate_analysis_calibration100_v1","reference_answers_read":False,"judge_scores_read":False,"tau":TAU,"margin":MARGIN,"source_a0_scores_sha256":sha(OLD),"candidates":out}
outdir=ROOT/"residual_gate_analysis_v1"
outdir.mkdir(parents=False,exist_ok=False)
(outdir/"summary.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:{x:y for x,y in v.items() if x!="rows_detail"} for k,v in out.items()},ensure_ascii=False,indent=2))
