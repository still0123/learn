#!/usr/bin/env python3
"""Judge the 28 ForcedFull cache misses and compare paired Crop vs Full."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time

RUN=Path("data/external/evads_v1/experiments/readr_crop_or_full_fresh500_v1")
CF=RUN/"forced_full_cf123_v1"
OUT=CF/"judge_deepseek_official_v1"
AUTHORIZED=28
VALID={0.0,0.25,0.5,0.75,1.0}
PROMPT="""# Role
You are a professional E-commerce Content Analyst and Senior Evaluator. Objectively assess the model answer using the question, reference answer, evidence clues, and time-aligned OCR/ASR metadata.

# Scoring tiers
- 1.0: completely accurate, covers all key points, and uses evidence consistently.
- 0.75: core answer is accurate and complete but generic or lacks deeper business logic.
- 0.5: partially correct, with important information missing.
- 0.25: conclusion or cited evidence is materially misaligned, including hallucinated evidence.
- 0.0: incorrect, contradictory, non-responsive, or severely hallucinated.

[Question]
{question}

[Metadata (OCR/ASR)]
{metadata}

[Clues]
{clues}

[Reference Answer]
{reference}

[Model Output]
{prediction}

Return exactly one line: Answer: <0, 0.25, 0.5, 0.75, or 1.0>
"""

def load(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def sha(x): return hashlib.sha256(str(x).encode()).hexdigest()
def r3(x): return .5 if x==.75 else 0.0 if x==.25 else x
def r2(x): return 1.0 if x==1.0 else 0.0
def metrics(rows,key):
    v=[float(x[key]) for x in rows]
    return {"rows":len(v),"R5":sum(v)/len(v),"R3":sum(map(r3,v))/len(v),"R2":sum(map(r2,v))/len(v),"counts":dict(Counter(str(x) for x in v))}
def paired(rows,left,right,seed):
    d=[float(x[left])-float(x[right]) for x in rows]; by={}
    for x in rows: by.setdefault(str(x["video_id"]),[]).append(x)
    vids=sorted(by); rng=random.Random(seed); boots=[]
    for _ in range(10000):
        draw=[x for v in (rng.choice(vids) for _ in vids) for x in by[v]]
        boots.append(sum(float(x[left])-float(x[right]) for x in draw)/len(draw))
    boots.sort()
    return {"rows":len(rows),"crop_wins":sum(x>0 for x in d),"ties":sum(x==0 for x in d),"crop_losses":sum(x<0 for x in d),"crop_minus_full_R5":sum(d)/len(d),"video_bootstrap_ci95":[boots[250],boots[9750]],"cluster_count":len(vids)}

def main():
    if (OUT/"JUDGE_COMPLETE").exists(): raise RuntimeError("already complete")
    questions={str(x["question_id"]):x for x in json.loads((RUN/"dataset/questions_answer_free.json").read_text())}
    refs={str(x["question_id"]):x for x in load(RUN/"judge_deepseek_official_v1/private_references.jsonl")}
    old=load(RUN/"judge_deepseek_official_v1/results_v1/api_results_partial.jsonl")
    cache={(str(x["question_id"]),str(x["prediction_sha256"])):float(x["score_R5"]) for x in old}
    old_rows={str(x["question_id"]):x for x in load(RUN/"judge_deepseek_official_v1/results_v1/scores_fresh500.jsonl")}
    items={str(x["question_id"]):x for x in load(CF/"dataset/items_answer_free.jsonl")}
    a0p={str(x["source_question_id"]):float(x["support_probability"]) for x in load(RUN/"a0_verifier_merged/scores_all.jsonl")}
    fp={str(x["source_question_id"]):float(x["support_probability"]) for x in load(CF/"verifier_merged/scores_all.jsonl")}
    preds={}; traces={}
    for p in (CF/"inference_by_fold").glob("fold_*/*/a2_prediction.json"):
        q=p.parent.name; preds[q]=json.loads(p.read_text()); traces[q]=json.loads((p.parent/"a2_trace.json").read_text())
    missing=[]
    for q,p in preds.items():
        h=sha(p["prediction"])
        if (q,h) not in cache: missing.append({"question_id":q,"prediction_sha256":h,"prediction":str(p["prediction"])})
    if len(missing)!=AUTHORIZED: raise RuntimeError(f"expected {AUTHORIZED} calls, found {len(missing)}")
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/"authorized_call_manifest.json").write_text(json.dumps({"authorized_new_calls":AUTHORIZED,"actual_pending_calls":len(missing),"judge_rubric":"official_evads_R5_R3_R2","not_human_gold":True,"groundtruth_read_after_inference_only":True},indent=2)+"\n")
    key=os.environ.get("DEEPSEEK_API_KEY");
    if not key: raise RuntimeError("DEEPSEEK_API_KEY missing")
    from openai import OpenAI
    client=OpenAI(api_key=key,base_url="https://api.deepseek.com"); usage=Counter(); results=[]; retries=0; started=time.time()
    for i,c in enumerate(missing,1):
        q=c["question_id"]; ref=refs[q]; prompt=PROMPT.format(question=questions[q]["question"],metadata=ref["judge_metadata_ocr_asr"],clues=ref["judge_clues"],reference=ref["reference_answer"],prediction=c["prediction"])
        score=None; attempts=0; last=None; u={}
        for n in range(8):
            attempts+=1
            try:
                res=client.chat.completions.create(model="deepseek-chat",messages=[{"role":"user","content":prompt}],temperature=0,max_tokens=32,timeout=150)
                m=re.search(r"Answer:\s*(0(?:\.0+|\.25|\.5|\.75)?|1(?:\.0+)?)",str(res.choices[0].message.content))
                if not m or float(m.group(1)) not in VALID: raise ValueError("invalid judge output")
                score=float(m.group(1)); ru=getattr(res,"usage",None); u={x:int(getattr(ru,x,0) or 0) for x in ("prompt_tokens","completion_tokens","total_tokens")} if ru else {}; break
            except Exception as e:
                last=repr(e)
                if n<7: retries+=1; time.sleep(min(30,2**n))
        if score is None: raise RuntimeError(f"judge failed {q}: {last}")
        row={"question_id":q,"prediction_sha256":c["prediction_sha256"],"score_R5":score,"attempts":attempts,"usage":u,"not_human_gold":True}
        results.append(row); cache[(q,c["prediction_sha256"])]=score; usage.update(u)
        with (OUT/"api_results.jsonl").open("a") as f: f.write(json.dumps(row)+"\n")
    tau=.9241418242454529; rows=[]
    for q,item in items.items():
        full_text=str(preds[q]["prediction"]); full_score=cache[(q,sha(full_text))]
        crop_score=float(old_rows[q]["A2_score"]); a0_score=float(old_rows[q]["A0_score"])
        full_switch=traces[q].get("parse_valid") is True and fp[q]>=tau and fp[q]>a0p[q]
        crop_switch=bool(old_rows[q]["switched"])
        rows.append({"question_id":q,"video_id":str(item["video_id"]),"crop_anchor_count":int(item["crop_or_full_route"]["original_crop_anchor_count"]),"A0_score":a0_score,"Crop_A2_score":crop_score,"Full_A2_score":full_score,"Crop_Gated_score":crop_score if crop_switch else a0_score,"Full_Gated_score":full_score if full_switch else a0_score,"crop_switched":crop_switch,"full_switched":full_switch})
    (OUT/"paired_scores123.jsonl").write_text("".join(json.dumps(x)+"\n" for x in rows))
    summary={"schema_version":"readr_crop_vs_forcedfull_cf123_judge_v1","judge_rubric":"official_evads_R5_R3_R2","not_human_gold":True,"authorized_calls":AUTHORIZED,"actual_calls":len(results),"retry_count":retries,"usage":dict(usage),"elapsed_seconds":time.time()-started,"protocol":{"rows":123,"videos":75,"only_intervention":"routed_crop_to_same_anchor_896_full","views":12,"visual_tokens":3992,"crop_gate_switches":sum(x["crop_switched"] for x in rows),"full_gate_switches":sum(x["full_switched"] for x in rows)},"methods":{"Crop_A2":metrics(rows,"Crop_A2_score"),"ForcedFull_A2":metrics(rows,"Full_A2_score"),"Crop_Gated":metrics(rows,"Crop_Gated_score"),"ForcedFull_Gated":metrics(rows,"Full_Gated_score")},"comparisons":{"Crop_vs_Full_A2":paired(rows,"Crop_A2_score","Full_A2_score",2026080401),"Crop_vs_Full_Gated":paired(rows,"Crop_Gated_score","Full_Gated_score",2026080402)}}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n"); (OUT/"JUDGE_COMPLETE").touch(); print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
