#!/usr/bin/env python3
"""Judge five authorized residual gate candidates and summarize against frozen MMR8."""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import threading
import numpy as np

from judge_adsqa_answer_lora_oof_v1 import legacy_parse_score, legacy_protocol, VALID_SCORES

ROOT=Path("evaluation/runs/readr_residual_avfunnel_calibration100_v1")
OLD_ROOT=Path("evaluation/runs/readr_increment_pilot300_v1")
REFS=OLD_ROOT/"judge_deepseek_legacy_answeronly_v1/materialized_v1/private_references/groundtruth_pilot300.json"
OLD_EXP=OLD_ROOT/"judge_deepseek_legacy_answeronly_v1/results_v1/expanded_four_method_scores.jsonl"
LEGACY=Path("/data1/rmx/backups/AdsQA-main/20260710_before_reorg/evaluation/evaluate_compare_new.py")
OUT=ROOT/"residual_judge_v1"

def load(path):
    text=path.read_text()
    if text.lstrip().startswith("["):
        return json.loads(text)
    return [json.loads(x) for x in text.splitlines() if x.strip()]
def norm(x): return " ".join(str(x).casefold().split())
def digest(x): return hashlib.sha256(x.encode()).hexdigest()

gate=json.loads((ROOT/"residual_gate_analysis_v1/summary.json").read_text())
refs={str(x["question_id"]):x for x in load(REFS)}
old={str(x["question_id"]):x for x in load(OLD_EXP)}
items={}
for variant in ("residual_mid","residual_avfunnel"):
    for x in load(ROOT/"dataset_v2"/variant/"items_answer_free.jsonl"):
        items[str(x["question_id"])] = x

pending=[]
owners={}
for variant in ("residual_mid","residual_avfunnel"):
    for row in gate["candidates"][variant]["rows_detail"]:
        if not row["gate_switched"]: continue
        qid=str(row["question_id"]); item=items[qid]
        fold=int(item["fold"])
        pred=json.loads((ROOT/"shards"/variant/f"fold_{fold}"/qid/"a2_prediction.json").read_text())["prediction"]
        key=(qid,digest(pred))
        owners.setdefault(key,[]).append(variant)
        if key not in {(x["question_id"],x["candidate_hash"]) for x in pending}:
            pending.append({"question_id":qid,"candidate_hash":digest(pred),"candidate":pred,"variant":variant})
if len(pending)!=5: raise RuntimeError(f"expected 5 authorized calls, got {len(pending)}")
if (OUT/"api_results.jsonl").exists() or (OUT/"summary.json").exists():
    raise RuntimeError("judge output already exists; refusing to overwrite")
OUT.mkdir(parents=False,exist_ok=True)
(OUT/"authorized_call_manifest.json").write_text(json.dumps({"authorized_new_calls":5,"rows":pending,"not_human_gold":True},ensure_ascii=False,indent=2)+"\n")
api_key=os.environ.get("DEEPSEEK_API_KEY")
if not api_key: raise RuntimeError("DEEPSEEK_API_KEY missing")
protocol=legacy_protocol(LEGACY)
local=threading.local()

def judge(row):
    qid=row["question_id"]; ref=refs[qid]
    prompt=protocol["prompt_template"].format(meta_info=ref["meta_info"],question=ref["question"],golden_answer=ref["answer"],response=row["candidate"])
    if not hasattr(local,"client"):
        from openai import OpenAI
        local.client=OpenAI(api_key=api_key,base_url=protocol["base_url"],timeout=60.0)
    response=local.client.chat.completions.create(model=protocol["model_name"],messages=[{"role":"system","content":"You are a helpful assistant acting as an evaluation judge."},{"role":"user","content":prompt}],temperature=0.0,max_tokens=20)
    text=str(response.choices[0].message.content); score=legacy_parse_score(text)
    if score not in VALID_SCORES: raise RuntimeError(f"unparsed score for {qid}")
    usage=getattr(response,"usage",None)
    return {**row,"score":score,"judge_output":text,"judge_response_model":getattr(response,"model",None),"judge_usage":usage.model_dump() if hasattr(usage,"model_dump") else None,"score_source":"authorized_residual_gate_calibration100"}

results=[]; failures=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    fs=[ex.submit(judge,x) for x in pending]
    for f in fs:
        try: results.append(f.result())
        except Exception as e: failures.append({"error":repr(e)})
if failures: (OUT/"api_failures.jsonl").write_text("".join(json.dumps(x)+"\n" for x in failures)); raise RuntimeError(f"judge failures: {len(failures)}")
(OUT/"api_results.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in results))
by_key={(x["question_id"],x["candidate_hash"]):float(x["score"]) for x in results}

def bootstrap(rows, selected, baseline, seed):
    by_video={}
    for r in rows: by_video.setdefault(r["video_id"],[]).append(r)
    vids=sorted(by_video); rng=np.random.default_rng(seed); vals=[]
    for _ in range(10000):
        chosen=rng.choice(vids,size=len(vids),replace=True); chosen_rows=[r for v in chosen for r in by_video[v]]
        vals.append(np.mean([r[selected]-r[baseline] for r in chosen_rows]))
    return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]

summary={"schema_version":"readr_residual_gate_calibration100_judge_v1","not_human_gold":True,"authorized_new_calls":5,"actual_successful_calls":len(results),"automatic_retries":0,"reference_answers_read_for_prompt":True,"variants":{}}
for variant in ("residual_mid","residual_avfunnel"):
    rows=[]
    for base in gate["candidates"][variant]["rows_detail"]:
        qid=str(base["question_id"]); item=items[qid]; oldrow=old[qid]; a0=float(oldrow["MMR8_score"])
        fold=int(item["fold"]); pred=json.loads((ROOT/"shards"/variant/f"fold_{fold}"/qid/"a2_prediction.json").read_text())["prediction"]
        val=a0
        if base["gate_switched"]: val=by_key[(qid,digest(pred))]
        rows.append({"question_id":qid,"video_id":str(item["video_id"]),"MMR8_score":a0,"Gated_score":val,"switched":bool(base["gate_switched"])})
    s=np.asarray([r["Gated_score"] for r in rows]); b=np.asarray([r["MMR8_score"] for r in rows]); d=s-b
    wr=int(np.sum((b<1)&(s==1))); rw=int(np.sum((b==1)&(s<1)))
    summary["variants"][variant]={"rows":100,"trigger_count":26,"switch_count":sum(r["switched"] for r in rows),"strict":float(np.mean(s==1)),"relaxed":float(np.mean(s)),"mmr8_strict":float(np.mean(b==1)),"mmr8_relaxed":float(np.mean(b)),"wins":int(np.sum(d>0)),"ties":int(np.sum(d==0)),"losses":int(np.sum(d<0)),"wrong_to_right":wr,"right_to_wrong":rw,"correction_precision":wr/(wr+rw) if wr+rw else None,"relaxed_delta":float(np.mean(d)),"strict_delta":float(np.mean((s==1)-(b==1))),"video_cluster_bootstrap_relaxed_ci95":bootstrap(rows,"Gated_score","MMR8_score",2026073101 if variant=="residual_mid" else 2026073102)}
(OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
