#!/usr/bin/env python3
"""Judge Fresh-500 A0/A2/final candidates with the official E-VAds rubric."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time

VALID = {0.0, 0.25, 0.5, 0.75, 1.0}
PROMPT = """# Role
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


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def write_jsonl(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))


def r3(x):
    return 0.5 if x == 0.75 else 0.0 if x == 0.25 else x


def r2(x):
    return 1.0 if x == 1.0 else 0.0


def metrics(rows, key):
    vals=[float(x[key]) for x in rows]
    return {"rows":len(vals),"R5":sum(vals)/len(vals),"R3":sum(map(r3,vals))/len(vals),"R2":sum(map(r2,vals))/len(vals),"counts":dict(Counter(str(x) for x in vals))}


def paired(rows, left, right, seed):
    by_video={}
    for x in rows: by_video.setdefault(str(x["video_id"]),[]).append(x)
    diffs=[float(x[right])-float(x[left]) for x in rows]
    rng=random.Random(seed); boots=[]; vids=sorted(by_video)
    for _ in range(10000):
        draw=[x for v in (rng.choice(vids) for _ in vids) for x in by_video[v]]
        boots.append(sum(float(x[right])-float(x[left]) for x in draw)/len(draw))
    boots.sort()
    return {"rows":len(rows),"wins":sum(x>0 for x in diffs),"ties":sum(x==0 for x in diffs),"losses":sum(x<0 for x in diffs),"R5_delta":sum(diffs)/len(diffs),"video_bootstrap_ci95":[boots[250],boots[9750]],"cluster_count":len(vids)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--questions",type=Path,required=True); p.add_argument("--references",type=Path,required=True)
    p.add_argument("--preflight",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--authorized-limit",type=int,required=True); p.add_argument("--max-retries",type=int,default=8)
    a=p.parse_args()
    pre=json.loads((a.preflight/"dry_run_audit.json").read_text())
    if not pre["passed"] or pre["authorized_call_limit"]!=a.authorized_limit: raise RuntimeError("authorization mismatch")
    questions={str(x["question_id"]):x for x in json.loads(a.questions.read_text())}
    refs={str(x["question_id"]):x for x in load_jsonl(a.references)}
    candidates=load_jsonl(a.preflight/"candidates_answer_free.jsonl"); slots=load_jsonl(a.preflight/"candidate_slots_answer_free.jsonl")
    if len(questions)!=500 or len(refs)!=500 or len(candidates)>a.authorized_limit or len(slots)!=500: raise RuntimeError("coverage mismatch")
    key=os.environ.get("DEEPSEEK_API_KEY");
    if not key: raise RuntimeError("DEEPSEEK_API_KEY missing")
    from openai import OpenAI
    client=OpenAI(api_key=key,base_url="https://api.deepseek.com")
    a.output_dir.mkdir(parents=True,exist_ok=True); cache_path=a.output_dir/"api_results_partial.jsonl"
    cache={(str(x["question_id"]),str(x["prediction_sha256"])):float(x["score_R5"]) for x in (load_jsonl(cache_path) if cache_path.exists() else [])}
    usage=Counter(); retries=0; started=time.time(); new=0
    for i,c in enumerate(candidates,1):
        k=(str(c["question_id"]),str(c["prediction_sha256"]))
        if k in cache: continue
        ref=refs[k[0]]; score=None; last=None; attempts=0; u={}
        prompt=PROMPT.format(question=questions[k[0]]["question"],metadata=ref["judge_metadata_ocr_asr"],clues=ref["judge_clues"],reference=ref["reference_answer"],prediction=c["prediction"])
        for n in range(a.max_retries):
            attempts+=1
            try:
                res=client.chat.completions.create(model="deepseek-chat",messages=[{"role":"user","content":prompt}],temperature=0,max_tokens=32,timeout=150)
                m=re.search(r"Answer:\s*(0(?:\.0+|\.25|\.5|\.75)?|1(?:\.0+)?)",str(res.choices[0].message.content))
                if not m or float(m.group(1)) not in VALID: raise ValueError("invalid judge output")
                score=float(m.group(1)); ru=getattr(res,"usage",None)
                u={x:int(getattr(ru,x,0) or 0) for x in ("prompt_tokens","completion_tokens","total_tokens")} if ru else {}
                break
            except Exception as e:
                last=repr(e)
                if n+1<a.max_retries: retries+=1; time.sleep(min(30,2**n))
        if score is None: raise RuntimeError(f"judge failed {k[0]}: {last}")
        row={"question_id":k[0],"prediction_sha256":k[1],"score_R5":score,"attempts":attempts,"usage":u,"judge_model":"deepseek-chat","not_human_gold":True}
        with cache_path.open("a") as f: f.write(json.dumps(row)+"\n")
        cache[k]=score; usage.update(u); new+=1
        if new%25==0: print(f"new_calls={new}/{len(candidates)}",flush=True)
    rows=[]
    for s in slots:
        q=str(s["question_id"]); get=lambda h:cache[(q,str(h))]
        row={**s,"A0_score":get(s["A0"]),"FINAL_score":get(s["FINAL"])}
        if "A2" in s: row["A2_score"]=get(s["A2"])
        rows.append(row)
    write_jsonl(a.output_dir/"scores_fresh500.jsonl",rows)
    triggered=[x for x in rows if x["triggered"]]; switched=[x for x in rows if x["switched"]]
    summary={"schema_version":"readr_crop_or_full_fresh500_judge_v1","not_human_gold":True,"judge_rubric":"official_evads_R5_R3_R2","authorized_limit":a.authorized_limit,"actual_unique_calls":len(cache),"new_calls_this_run":new,"retry_count":retries,"usage":dict(usage),"elapsed_seconds":time.time()-started,"protocol":{"rows":500,"videos":100,"trigger_count":len(triggered),"switch_count":len(switched),"crop_trigger_count":sum(x["crop_anchor_count"]>0 for x in triggered),"visual_tokens_triggered":3992,"visual_tokens_A0":1296},"methods":{"A0_MMR8":metrics(rows,"A0_score"),"CropOrFull12_Gated":metrics(rows,"FINAL_score"),"A2_trigger_subset":metrics(triggered,"A2_score")},"comparisons":{"Gated_vs_A0":paired(rows,"A0_score","FINAL_score",2026080301),"A2_vs_A0_on_triggered":paired(triggered,"A0_score","A2_score",2026080302),"Gated_vs_A0_on_switched":paired(switched,"A0_score","FINAL_score",2026080303) if switched else None}}
    (a.output_dir/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    (a.output_dir/"JUDGE_COMPLETE").touch(); print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
