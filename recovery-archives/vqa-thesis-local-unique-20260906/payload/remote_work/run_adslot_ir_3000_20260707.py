#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import shlex
import subprocess
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path("/data1/rmx/projectb/AdsQA-main")
PYTHON = "/data1/rmx/ana3/envs/ReadR/bin/python"
FULL_Q = ROOT / "data/testset_question.json"
FULL_GT = ROOT / "data/testset_groundtruth.json"
QUESTION = ROOT / "data/balanced600_by_primary_type_seed42_question.json"
GT = ROOT / "data/balanced600_by_primary_type_seed42_groundtruth.json"
ASR = ROOT / "evaluation/asr_set.json"
MODEL = "/data1/qky/Model/Qwen3Vl-8B"
SCRIPT_EVID = ROOT / "evaluation/inference_ours_param_evidence.py"
SCRIPT_ADSLOT = ROOT / "evaluation/inference_adslot_ir_20260707.py"
SCRIPT_RAW = ROOT / "evaluation/inference_qwen3_raw_uniform_20260629.py"
LOG = ROOT / "evaluation/runs/adslot_ir_3000_20260707.log"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: str, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("RUN " + cmd)
    p = subprocess.run(
        cmd,
        shell=True,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if p.stdout:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(p.stdout[-30000:] + "\n")
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed rc={p.returncode}: {cmd}\n{p.stdout[-4000:]}")
    return p


def primary_type(item: dict) -> str:
    q_types = item.get("question_type") or ["unknown"]
    if isinstance(q_types, str):
        try:
            q_types = json.loads(q_types.replace("'", '"'))
        except Exception:
            q_types = [q_types]
    if not isinstance(q_types, list):
        q_types = [str(q_types)]
    return str(q_types[0]) if q_types else "unknown"


def ensure_balanced3000() -> None:
    if QUESTION.exists() and GT.exists():
        q = json.load(open(QUESTION, encoding="utf-8"))
        g = json.load(open(GT, encoding="utf-8"))
        if len(q) == 3000 and len(g) == 3000:
            log(f"Balanced3000 exists: {QUESTION}")
            return

    questions = json.load(open(FULL_Q, encoding="utf-8"))
    gt_list = json.load(open(FULL_GT, encoding="utf-8"))
    gt_by_id = {str(x["question_id"]): x for x in gt_list}
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in questions:
        buckets[primary_type(item)].append(item)

    rng = random.Random(42)
    selected: list[dict] = []
    manifest = {}
    for t in sorted(buckets):
        arr = list(buckets[t])
        rng.shuffle(arr)
        take = arr[:600] if len(arr) >= 600 else arr
        manifest[t] = {"available": len(arr), "selected": len(take)}
        selected.extend(take)

    if len(selected) < 3000:
        selected_ids = {str(x["question_id"]) for x in selected}
        rest = [x for x in questions if str(x["question_id"]) not in selected_ids]
        rng.shuffle(rest)
        selected.extend(rest[: 3000 - len(selected)])
    selected = selected[:3000]
    selected_ids = [str(x["question_id"]) for x in selected]
    selected_gt = [gt_by_id[qid] for qid in selected_ids if qid in gt_by_id]
    if len(selected_gt) != len(selected):
        missing = sorted(set(selected_ids) - set(gt_by_id))
        raise RuntimeError(f"Missing GT for {len(missing)} questions, first={missing[:5]}")

    QUESTION.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    GT.write_text(json.dumps(selected_gt, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "data/balanced600_by_primary_type_seed42_manifest.json").write_text(
        json.dumps({"target": 3000, "seed": 42, "by_primary_type": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"Wrote balanced3000: q={QUESTION} gt={GT} manifest={manifest}")


def count_pred_files(out: Path) -> int:
    return len(list(out.glob("*/prediction.json")))


def count_covered_rows(out: Path) -> int:
    """Count covered question rows, not unique prediction files.

    The balanced3000 file can contain duplicate question_id rows. Since outputs
    are stored by question_id directory, a duplicate row legitimately maps to the
    same prediction.json. The run is complete when every row can resolve to a
    prediction, even if the number of unique prediction files is slightly lower.
    """
    if not QUESTION.exists():
        return count_pred_files(out)
    questions = json.load(open(QUESTION, encoding="utf-8"))
    covered = 0
    for item in questions:
        qid = str(item["question_id"])
        if (out / qid / "prediction.json").exists():
            covered += 1
    return covered


def free_gpus() -> list[int]:
    p = run(
        "nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits",
        check=False,
    )
    gpus = []
    for line in p.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) >= 3:
            try:
                if int(parts[1]) < 1000 and int(parts[2]) < 15:
                    gpus.append(int(parts[0]))
            except Exception:
                pass
    return gpus


def wait_for_gpus() -> list[int]:
    while True:
        g = free_gpus()
        if g:
            return g
        log("No free GPUs, waiting 5 min")
        time.sleep(300)


def launch_sharded(run_id: str, script: Path, cli: str) -> Path:
    out = ROOT / "evaluation/runs" / run_id
    out.mkdir(parents=True, exist_ok=True)
    if count_covered_rows(out) >= 3000:
        log(f"{run_id} already covers 3000 question rows unique_files={count_pred_files(out)}")
        return out

    p = run(f"pgrep -af {shlex.quote(run_id)}", check=False)
    if p.returncode != 0 or "inference_" not in p.stdout:
        gpus = wait_for_gpus()
        n = len(gpus)
        log(f"Launching {run_id}: script={script.name} GPUs={gpus}")
        for shard, gpu in enumerate(gpus):
            logf = out / f"launch_gpu{gpu}_shard{shard}.log"
            cmd = (
                f"nohup {shlex.quote(PYTHON)} {shlex.quote(str(script))} "
                f"--gpu_id {gpu} --shard_id {shard} --num_shards {n} --start_idx 0 --end_idx -1 "
                f"--question_file {shlex.quote(str(QUESTION))} "
                f"--groundtruth_file {shlex.quote(str(GT))} "
                f"--asr_file {shlex.quote(str(ASR))} "
                f"--model_dir {shlex.quote(MODEL)} "
                f"--output_dir {shlex.quote(str(out))} --save_prompts "
                f"{cli} > {shlex.quote(str(logf))} 2>&1 & echo $!"
            )
            pid = run(cmd).stdout.strip()
            log(f"{run_id} launched gpu={gpu} shard={shard}/{n} pid={pid}")

    while True:
        c = count_covered_rows(out)
        files = count_pred_files(out)
        p = run(f"pgrep -af {shlex.quote(run_id)}", check=False)
        alive = p.returncode == 0 and "inference_" in p.stdout
        log(f"{run_id} progress covered_rows={c}/3000 unique_files={files} alive={alive}")
        if c >= 3000:
            break
        if not alive:
            log(f"{run_id} incomplete and not alive; relaunching")
            return launch_sharded(run_id, script, cli)
        time.sleep(300)
    return out


def score_run(out: Path, name: str) -> None:
    run(
        f"python3 evaluation/eval/collect_predictions.py "
        f"--run_dir {shlex.quote(str(out))} --question_file {shlex.quote(str(QUESTION))} "
        f"--gt_file {shlex.quote(str(GT))} --out {shlex.quote(str(out/'collect_summary.json'))}",
        timeout=300,
    )
    code = f"""
import importlib.util
path='/data1/rmx/projectb/AdsQA-main/evaluation/evaluate_compare_new.py'
spec=importlib.util.spec_from_file_location('eval_{name}', path)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.PRED_DIR={str(out)!r}
mod.GT_FILE={str(GT)!r}
mod.TARGET_FILE_NAME='prediction.json'
mod.MAX_WORKERS=10
mod.main()
"""
    run(f"{shlex.quote(PYTHON)} - <<'EOF'\n{code}\nEOF", timeout=3600)
    run(
        f"python3 evaluation/eval/collect_predictions.py "
        f"--run_dir {shlex.quote(str(out))} --question_file {shlex.quote(str(QUESTION))} "
        f"--gt_file {shlex.quote(str(GT))} --out {shlex.quote(str(out/'collect_summary.json'))}",
        timeout=300,
    )


def main() -> None:
    log("AdSlot-IR 3000 experiment start")
    ensure_balanced3000()
    raw = launch_sharded(
        "qwen3_raw_uniform_norag_bal3000_20260707",
        SCRIPT_RAW,
        "--rag_mode none --oversample_count 8 --top_k_frames 8",
    )
    score_run(raw, "qwen3_raw_uniform_3000")
    evid = launch_sharded(
        "qwen3_evidence_norag_bal3000_20260707",
        SCRIPT_EVID,
        "--rag_mode none --oversample_count 32 --top_k_frames 16",
    )
    score_run(evid, "qwen3_evidence_norag_3000")
    adslot = launch_sharded(
        "adslot_ir_norag_bal3000_20260707",
        SCRIPT_ADSLOT,
        "--rag_mode none --oversample_count 32 --top_k_frames 16 --adslot_mode on --adslot_min_top_k 8 --adslot_max_top_k 20",
    )
    score_run(adslot, "adslot_ir_3000")
    log("AdSlot-IR 3000 experiment complete")


if __name__ == "__main__":
    main()
