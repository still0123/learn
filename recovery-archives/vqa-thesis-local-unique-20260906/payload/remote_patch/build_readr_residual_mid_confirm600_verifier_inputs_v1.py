#!/usr/bin/env python3
"""Build answer-free variable-fold Qwen3 verifier inputs for Confirm-600."""
import argparse, hashlib, json
from pathlib import Path
from collections import Counter

def load(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dataset-dir",type=Path,required=True); ap.add_argument("--inference-root",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True); args=ap.parse_args()
    if args.output_dir.exists(): raise RuntimeError("output exists")
    rows=[]
    for item in load(args.dataset_dir/"items_answer_free.jsonl"):
        qid=str(item["question_id"]); fold=int(item["fold"]); d=args.inference_root/f"fold_{fold}"/qid
        pred=json.loads((d/"a2_prediction.json").read_text()); trace=json.loads((d/"a2_trace.json").read_text())
        if not trace.get("parse_valid"): raise RuntimeError(f"parse failed: {qid}")
        rows.append({"question_id":f"q{qid}__A2","source_question_id":qid,"video_id":str(item["video_id"]),"video_path":str(item["video_path"]),"question":str(item["question"]),"claim":str(pred["prediction"]),"candidate_method":"ReAdR_ResidualMid12_A2","selected_frame_indices":[int(x) for x in item["a0_frame_indices"]],"asr_excerpt":str(item.get("a0_asr_excerpt","")),"fold":fold})
    rows.sort(key=lambda x:(int(x["fold"]),str(x["source_question_id"]))); args.output_dir.mkdir(parents=True); allp=args.output_dir/"model_inputs_all.jsonl"; allp.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
    sh=args.output_dir/"shards"; sh.mkdir()
    for f in range(5): (sh/f"fold_{f}.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows if int(x["fold"])==f))
    audit={"schema_version":"qwen3_residual_mid_confirm600_verifier_input_v1","passed":True,"row_count":len(rows),"video_count":len({x["video_id"] for x in rows}),"fold_counts":dict(Counter(str(x["fold"]) for x in rows)),"groundtruth_read":False,"judge_scores_read":False,"labels_in_model_inputs":False,"model_inputs_sha256":sha(allp)}
    (args.output_dir/"audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n"); print(json.dumps(audit,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
