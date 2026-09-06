#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np

ROOT=Path("evaluation/runs/readr_residual_avfunnel_calibration100_v1")
OLD_ROOT=Path("evaluation/runs/readr_increment_pilot300_v1")
def load(path):
    text=path.read_text()
    return json.loads(text) if text.lstrip().startswith("[") else [json.loads(x) for x in text.splitlines() if x.strip()]
def digest(x):
    import hashlib
    return hashlib.sha256(x.encode()).hexdigest()
def bootstrap(rows,selected,baseline,seed):
    groups={}
    for row in rows: groups.setdefault(row["video_id"],[]).append(row)
    vids=sorted(groups); rng=np.random.default_rng(seed); values=[]
    for _ in range(10000):
        chosen=rng.choice(vids,size=len(vids),replace=True)
        chosen_rows=[row for v in chosen for row in groups[v]]
        values.append(np.mean([row[selected]-row[baseline] for row in chosen_rows]))
    return [float(np.quantile(values,.025)),float(np.quantile(values,.975))]

gate=json.loads((ROOT/"residual_gate_analysis_v1/summary.json").read_text())
api=load(ROOT/"residual_judge_v1/api_results.jsonl")
assert len(api)==5
by_key={(x["question_id"],x["candidate_hash"]):float(x["score"]) for x in api}
old={str(x["question_id"]):x for x in load(OLD_ROOT/"judge_deepseek_legacy_answeronly_v1/results_v1/expanded_four_method_scores.jsonl")}
items={}
for variant in ("residual_mid","residual_avfunnel"):
    for x in load(ROOT/"dataset_v2"/variant/"items_answer_free.jsonl"): items[str(x["question_id"])]=x
summary={"schema_version":"readr_residual_gate_calibration100_judge_v1","not_human_gold":True,"authorized_new_calls":5,"actual_new_successful_calls":5,"automatic_retries":0,"api_failures":0,"variants":{}}
for variant in ("residual_mid","residual_avfunnel"):
    rows=[]
    for base in gate["candidates"][variant]["rows_detail"]:
        qid=str(base["question_id"]); item=items[qid]; a0=float(old[qid]["MMR8_score"]); fold=int(item["fold"])
        pred=json.loads((ROOT/"shards"/variant/("fold_"+str(fold))/qid/"a2_prediction.json").read_text())["prediction"]
        selected=a0
        if base["gate_switched"]: selected=by_key[(qid,digest(pred))]
        rows.append({"question_id":qid,"video_id":str(item["video_id"]),"MMR8_score":a0,"Gated_score":selected,"switched":bool(base["gate_switched"])})
    s=np.asarray([r["Gated_score"] for r in rows]); b=np.asarray([r["MMR8_score"] for r in rows]); d=s-b
    wr=int(np.sum((b<1)&(s==1))); rw=int(np.sum((b==1)&(s<1)))
    summary["variants"][variant]={"rows":100,"trigger_count":26,"switch_count":sum(r["switched"] for r in rows),"strict":float(np.mean(s==1)),"relaxed":float(np.mean(s)),"mmr8_strict":float(np.mean(b==1)),"mmr8_relaxed":float(np.mean(b)),"wins":int(np.sum(d>0)),"ties":int(np.sum(d==0)),"losses":int(np.sum(d<0)),"wrong_to_right":wr,"right_to_wrong":rw,"correction_precision":wr/(wr+rw) if wr+rw else None,"relaxed_delta":float(np.mean(d)),"strict_delta":float(np.mean((s==1).astype(float)-(b==1).astype(float))),"video_cluster_bootstrap_relaxed_ci95":bootstrap(rows,"Gated_score","MMR8_score",2026073101 if variant=="residual_mid" else 2026073102)}
(ROOT/"residual_judge_v1/summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
