#!/usr/bin/env python3
"""Build answer-free residual-mid inputs for the frozen Confirm-600 trigger pool."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
from typing import Any
import cv2
from build_avfunnel8_manifest_v1 import build_candidates, select_temporally_diverse_anchors
from build_readr_residual_avfunnel_calibration100_v1 import center_of, hierarchical_sides, square_box, uncertainty_proxy

def load_jsonl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def uniform(total,count=32): return [round(i*(total-1)/(count-1)) for i in range(count)] if total>1 else [0]*count
def frame_count(path,cache):
    if path in cache: return cache[path]
    c=cv2.VideoCapture(path); n=int(c.get(cv2.CAP_PROP_FRAME_COUNT)); c.release()
    if n<=0: raise RuntimeError(f"cannot inspect video: {path}")
    cache[path]=n; return n
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source-items",type=Path,required=True); ap.add_argument("--raw-features",type=Path,action="append",required=True); ap.add_argument("--output-root",type=Path,required=True); args=ap.parse_args()
    if args.output_root.exists(): raise RuntimeError("output root already exists")
    source=load_jsonl(args.source_items); raw=[]
    for p in args.raw_features: raw += load_jsonl(p)
    raw_by={str(x["question_id"]):x for x in raw}; cache={}; rows=[]; source_hashes={}
    for item in source:
        qid=str(item["question_id"]); assert qid in raw_by and len(item["a0_frame_indices"])==8
        total=frame_count(str(item["video_path"]),cache); plan=uniform(total); a0={int(x) for x in item["a0_frame_indices"]}
        candidates=[c for c in build_candidates(raw_by[qid]) if plan[int(c["source_global_rank"])] not in a0]
        if len(candidates)<2: raise RuntimeError(f"not enough residual candidates: {qid}")
        selected,gap=select_temporally_diverse_anchors(candidates); assert len(selected)==2
        out=json.loads(json.dumps(item)); out["crop_ablation_variant"]="residual_mid"; out["residual_anchor_selection"]={"rule":"exclude_a0_source_frame_then_fixed_av_fusion_v1","a0_frame_indices":sorted(a0),"candidate_count_after_exclusion":len(candidates),"temporal_gap_satisfied":gap,"source_total_frames":total}
        anchors=[]
        for ai,c in enumerate(selected):
            e=uncertainty_proxy(float(c["response_concentration"])); cx,cy=center_of(c["bbox_norm"]); box=square_box(cx,cy,hierarchical_sides(c["bbox_norm"],e)["mid"])
            anchors.append({"anchor_index":ai,"source_global_rank":int(c["source_global_rank"]),"bbox_norm":box,"bbox_source":str(c["bbox_source"]),"fusion_score":float(c["fusion_score"]),"visual_rank_score":float(c["visual_rank_score"]),"asr_rank_score":float(c["asr_rank_score"]),"ocr_rank_score":float(c["ocr_rank_score"]),"entropy_proxy":e,"scale_level":"mid","crop_mode":"residual_mid_v1","residual_selection":"excluded_a0_frame_indices_then_av_fusion_v1"})
        assert not ({plan[int(x["source_global_rank"])] for x in anchors}&a0); out["evidence_anchors"]=anchors; rows.append(out)
    rows.sort(key=lambda x:(int(x["fold"]),str(x["question_id"]))); args.output_root.mkdir(parents=True)
    (args.output_root/"items_answer_free.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
    for f in range(5):
        sub=[x for x in rows if int(x["fold"])==f]; d=args.output_root/"shards"; d.mkdir(exist_ok=True); (d/f"fold_{f}.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in sub))
    audit={"schema_version":"readr_residual_mid_confirm600_dataset_v1","passed":True,"development_only":False,"question_count":len(rows),"video_count":len({str(x["video_id"]) for x in rows}),"fold_counts":dict(Counter(str(x["fold"]) for x in rows)),"groundtruth_read":False,"judge_scores_read":False,"external_knowledge_used":False,"source_hash":sha(args.source_items),"raw_features_sha256":[sha(p) for p in args.raw_features],"items_sha256":sha(args.output_root/"items_answer_free.jsonl")}
    (args.output_root/"dataset_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n"); print(json.dumps(audit,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
