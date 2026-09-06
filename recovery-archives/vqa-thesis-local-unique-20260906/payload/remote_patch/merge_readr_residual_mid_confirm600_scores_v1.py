#!/usr/bin/env python3
import argparse, json, hashlib
from pathlib import Path
from collections import Counter
def load(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--shard-root",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True); args=ap.parse_args()
    if args.output_dir.exists(): raise RuntimeError("output exists")
    rows=[]; hashes={}
    for f in range(5):
        p=args.shard_root/f"fold_{f}"/"scores.jsonl"; part=load(p); rows += [{**x,"fold":f} for x in part]; hashes[str(f)]=sha(p)
    rows.sort(key=lambda x:(int(x["fold"]),str(x["source_question_id"]))); args.output_dir.mkdir(parents=True); out=args.output_dir/"scores_all.jsonl"; out.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
    s=[float(x["support_probability"]) for x in rows]; summary={"schema_version":"qwen3_residual_mid_confirm600_score_merge_v1","passed":len(rows)==152,"row_count":len(rows),"fold_counts":dict(Counter(str(x["fold"]) for x in rows)),"support_probability":{"min":min(s),"mean":sum(s)/len(s),"max":max(s)},"all_have_eight_verifier_views":all(int(x["represented_views"])==8 for x in rows),"secondary_frame_sampling_disabled":all(not x["secondary_frame_sampling"] for x in rows),"groundtruth_read":False,"judge_scores_read":False,"shard_sha256":hashes,"scores_all_sha256":sha(out)}
    (args.output_dir/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n"); print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
