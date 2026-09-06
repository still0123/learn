#!/usr/bin/env python3
"""Materialize a frozen E-VAds Test subset after answer-free inference."""

import argparse
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq

FORBIDDEN={"answer","reference_answer","ground_truth","reward","label","evidence_state","pairwise_target"}

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--questions",type=Path,required=True); p.add_argument("--test-parquet",type=Path,required=True); p.add_argument("--inference-audit",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--audit",type=Path,required=True); p.add_argument("--expected-count",type=int,required=True); a=p.parse_args()
    if a.output.exists() or a.audit.exists(): raise FileExistsError("outputs exist")
    gate=json.loads(a.inference_audit.read_text())
    if gate.get("passed") is not True or int(gate.get("question_count",-1))!=a.expected_count: raise RuntimeError("inference gate failed")
    questions=json.loads(a.questions.read_text()); ids=set()
    for x in questions:
        if not isinstance(x,dict) or FORBIDDEN & set(x) or x.get("answer_free") is not True: raise RuntimeError("questions not answer-free")
        ids.add(str(x["question_id"]))
    if len(ids)!=a.expected_count: raise RuntimeError("question count mismatch")
    parquet=pq.ParquetFile(a.test_parquet); selected={}
    for row in parquet.read(columns=["answer","extra_info"]).to_pylist():
        extra=row.get("extra_info") or {}; qid=str(extra.get("id",""))
        if qid not in ids: continue
        if qid in selected: raise RuntimeError("duplicate reference")
        selected[qid]={"question_id":qid,"reference_answer":str(row.get("answer","")),"judge_clues":str(extra.get("evidence","")),"judge_metadata_ocr_asr":str(extra.get("meta_ocr_asr","")),"reference_source":"evads_test_official"}
    if set(selected)!=ids or any(not x["reference_answer"].strip() for x in selected.values()): raise RuntimeError("reference coverage failed")
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text("".join(json.dumps(selected[q],ensure_ascii=True)+"\n" for q in sorted(selected)))
    audit={"schema_version":"evads_test_private_reference_compat_audit_v1","passed":True,"reference_count":len(selected),"expected_count":a.expected_count,"reference_source":"evads_test_official","metadata_nonempty_count":sum(bool(x["judge_metadata_ocr_asr"].strip()) for x in selected.values()),"clues_nonempty_count":sum(bool(x["judge_clues"].strip()) for x in selected.values()),"public_input_answers_read":False,"inference_audit_sha256":digest(a.inference_audit),"questions_sha256":digest(a.questions),"private_reference_sha256":digest(a.output)}
    a.audit.write_text(json.dumps(audit,indent=2)+"\n"); print(json.dumps(audit,indent=2))

if __name__=="__main__": main()
