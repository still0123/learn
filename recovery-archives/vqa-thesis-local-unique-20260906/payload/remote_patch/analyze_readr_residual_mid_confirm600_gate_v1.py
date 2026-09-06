#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path("evaluation/runs/readr_increment_confirm600_v1/residual_mid_confirm600_v1")
OLD=Path("evaluation/runs/readr_increment_confirm600_v1/mmr8_verifier_merged/scores_all.jsonl")
TAU=0.9241418242454529; MARGIN=0.0
def load(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def norm(x): return " ".join(str(x).casefold().split())
def digest(x): return hashlib.sha256(x.encode()).hexdigest()
items={str(x["question_id"]):x for x in load(ROOT/"dataset_v1/items_answer_free.jsonl")}
a0={str(x["source_question_id"]):x for x in load(OLD)}
a2={str(x["source_question_id"]):x for x in load(ROOT/"verifier_merged/scores_all.jsonl")}
rows=[]
for qid,item in items.items():
    fold=int(item["fold"]); pred=json.loads((ROOT/"inference"/f"fold_{fold}"/qid/"a2_prediction.json").read_text())["prediction"]
    a0s=float(a0[qid]["support_probability"]); a2s=float(a2[qid]["support_probability"]); changed=norm(pred)!=norm(item["a0_prediction"]); review=a0s<TAU; switch=review and changed and a2s>=a0s+MARGIN
    rows.append({"question_id":qid,"video_id":str(item["video_id"]),"fold":fold,"a0_support":a0s,"a2_support":a2s,"support_delta":a2s-a0s,"answer_changed":changed,"review_triggered":review,"gate_switched":switch,"candidate_prediction":pred,"candidate_prediction_sha256":digest(pred),"a0_prediction":item["a0_prediction"]})
rows.sort(key=lambda x:(x["fold"],x["question_id"]))
out={"schema_version":"readr_residual_mid_confirm600_gate_v1","passed":True,"reference_answers_read":False,"judge_scores_read":False,"rows":len(rows),"video_count":len({x["video_id"] for x in rows}),"tau":TAU,"margin":MARGIN,"review_trigger_count":sum(x["review_triggered"] for x in rows),"switch_count":sum(x["gate_switched"] for x in rows),"answer_change_count":sum(x["answer_changed"] for x in rows),"rows_detail":rows}
(ROOT/"gate_analysis_v1").mkdir(parents=True)
(ROOT/"gate_analysis_v1/summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in out.items() if k!="rows_detail"},ensure_ascii=False,indent=2))
