#!/usr/bin/env python3
"""
AdsQA Evaluation Script for v203 (Rescue Edition)
[修改点]:
1. 路径指向: 203_qaar_rescue (这是您刚才跑的新结果)。
2. Judge Prompt: 明确允许 "Concise Phrase" (短语) 作为答案，防止误判。
3. 架构: 异步高并发，速度更快。
"""

import json
import os
import re
import time
import sys
import subprocess
import requests
import datetime
import asyncio
import httpx
from tqdm.asyncio import tqdm_asyncio

# ==============================================================================
# ⚙️ 1. 配置区域
# ==============================================================================
SERVER_CONFIG = {
    "model_path": "/data1/rmx/projectb/models/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
    "served_name": "llama-local",
    "port": 8000,
    "gpu_memory_utilization": 0.95,
    "max_model_len": 4096,
    "gpu_ids": "5"  # 保持您原来的 GPU 设置
}

# [配置 1] Ground Truth
GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'

# [配置 2] Method A (您刚才跑的最强版本)
# ⚠️ 必须指向 203，否则您评估的还是旧的垃圾结果
CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/201_segment_avam'
CURRENT_FILE_NAME = 'prediction.json'

# [配置 3] Method B (Baseline)
BASELINE_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results'
BASELINE_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'

LOG_FILE_PATH = "evaluation_log_203.txt"
SAMPLE_LIMIT = None 
CONCURRENCY = 30     

# ==============================================================================
# 🔧 智能服务管理
# ==============================================================================
def is_server_running(url):
    try:
        resp = requests.get(f"{url}/models", timeout=2)
        return resp.status_code == 200
    except:
        return False

def start_vllm_server():
    base_url = f"http://localhost:{SERVER_CONFIG['port']}/v1"
    if is_server_running(base_url):
        print(f"✅ [Smart] Reusing existing vLLM server on port {SERVER_CONFIG['port']}")
        return None, None

    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", SERVER_CONFIG["model_path"],
        "--served-model-name", SERVER_CONFIG["served_name"],
        "--port", str(SERVER_CONFIG["port"]),
        "--gpu-memory-utilization", str(SERVER_CONFIG["gpu_memory_utilization"]),
        "--max-model-len", str(SERVER_CONFIG["max_model_len"]),
        "--trust-remote-code",
        "--enforce-eager"
    ]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = SERVER_CONFIG["gpu_ids"]
    
    print(f"\n🚀 [System] Starting vLLM on GPU {SERVER_CONFIG['gpu_ids']}...")
    log_file = open("vllm_server.log", "w")
    process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, env=env)
    
    # Wait loop
    print("⏳ Waiting for server...")
    start_time = time.time()
    while time.time() - start_time < 600:
        if is_server_running(base_url):
            print("✅ Server Ready!")
            return process, log_file
        time.sleep(5)
        print(".", end="", flush=True)
    raise RuntimeError("Server start timeout")

# ==============================================================================
# 🧠 评测核心 (适配 v203 简洁风格)
# ==============================================================================
# [修改点]: 增加 Rules 第 5 条，明确告诉 Judge 不要因为短而扣分
JUDGE_PROMPT = """
You are an advertising expert evaluating whether a Response matches the Golden Answer.

### Meta-Information:
{meta_info}

### Question: 
{question}

### Golden Answer: 
{golden_answer}

### Response to be judged: 
{response}

### Rules:
1. MATCH (1.0): Response contains ALL key information. Synonyms are allowed.
2. MISMATCH (0.0): Response misses key info OR contradicts Meta-Info.
3. PARTIAL (0.5): Response contains MOST key info.
4. **FORMAT NOTE**: Do NOT penalize the response for being a concise phrase (e.g., "Nike") instead of a full sentence. Brevity is preferred.

### Output:
Output ONLY one line: "Answer: 1", "Answer: 0.5", or "Answer: 0".
"""

def parse_score(content):
    if "Answer: 1" in content: return 1.0
    elif "Answer: 0.5" in content: return 0.5
    elif "Answer: 0" in content: return 0.0
    match = re.search(r"Answer:\s*(\d+(\.\d+)?)", content)
    return float(match.group(1)) if match else -1.0

async def evaluate_single(client, text_prompt):
    for _ in range(3): 
        try:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": SERVER_CONFIG["served_name"],
                    "messages": [
                        {"role": "system", "content": "You are a fair and strict evaluation judge."},
                        {"role": "user", "content": text_prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 10
                },
                timeout=60.0
            )
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return parse_score(content)
        except:
            await asyncio.sleep(1)
    return -1.0

async def process_item(item_data, client, sem):
    q_id, gt_item, curr_path, base_path = item_data
    
    async with sem:
        # Evaluate Current
        score_curr = -1.0
        try:
            with open(curr_path, 'r') as f: curr_json = json.load(f)
            curr_entry = curr_json[0] if isinstance(curr_json, list) else curr_json
            
            # 如果已经打过分，直接跳过 (节省时间)
            if 'score' in curr_entry and "Answer:" in str(curr_entry.get('score', '')):
                 score_curr = parse_score(str(curr_entry['score']))
            else:
                raw_gold = gt_item.get('answer', gt_item.get('gt_answer', ''))
                if isinstance(raw_gold, list): gold_str = "; ".join(map(str, raw_gold))
                else: gold_str = str(raw_gold)
                
                prompt = JUDGE_PROMPT.format(
                    meta_info=gt_item.get('meta_info', ''),
                    question=gt_item.get('question', ''),
                    golden_answer=gold_str,
                    response=curr_entry.get('prediction', '')[:1000]
                )
                score_curr = await evaluate_single(client, prompt)
                
                if score_curr != -1.0:
                    curr_entry['score'] = f"Answer: {score_curr}"
                    with open(curr_path, 'w') as f: json.dump(curr_entry, f, indent=2, ensure_ascii=False)
        except: pass

        # Evaluate Baseline
        score_base = -1.0
        try:
            with open(base_path, 'r') as f: base_json = json.load(f)
            base_entry = base_json[0] if isinstance(base_json, list) else base_json
            
            if 'score' in base_entry and "Answer:" in str(base_entry.get('score', '')):
                 score_base = parse_score(str(base_entry['score']))
            else:
                raw_gold = gt_item.get('answer', gt_item.get('gt_answer', ''))
                if isinstance(raw_gold, list): gold_str = "; ".join(map(str, raw_gold))
                else: gold_str = str(raw_gold)
                
                prompt = JUDGE_PROMPT.format(
                    meta_info=gt_item.get('meta_info', ''),
                    question=gt_item.get('question', ''),
                    golden_answer=gold_str,
                    response=base_entry.get('prediction', '')[:1000]
                )
                score_base = await evaluate_single(client, prompt)
                
                if score_base != -1.0:
                    base_entry['score'] = f"Answer: {score_base}"
                    with open(base_path, 'w') as f: json.dump(base_entry, f, indent=2, ensure_ascii=False)
        except: pass

    q_types = gt_item.get('question_type', ['unknown'])
    if isinstance(q_types, str): q_types = [q_types]
    
    return {
        'valid': (score_curr != -1.0 and score_base != -1.0),
        'score_curr': max(0.0, score_curr),
        'score_base': max(0.0, score_base),
        'types': q_types
    }

async def run_async_evaluation():
    base_url = f"http://localhost:{SERVER_CONFIG['port']}/v1"
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        
        # 1. Scan Files
        with open(GT_FILE, 'r') as f: gt_map = {str(i['question_id']): i for i in json.load(f)}
        
        tasks = []
        for qid in gt_map:
            c_p = os.path.join(CURRENT_PRED_DIR, qid, CURRENT_FILE_NAME)
            b_p = os.path.join(BASELINE_PRED_DIR, qid, BASELINE_FILE_NAME)
            if os.path.exists(c_p) and os.path.exists(b_p):
                tasks.append((qid, gt_map[qid], c_p, b_p))
                if SAMPLE_LIMIT and len(tasks) >= SAMPLE_LIMIT: break
        
        print(f"✅ Found {len(tasks)} comparison pairs.")
        
        # 2. Run
        sem = asyncio.Semaphore(CONCURRENCY)
        coroutines = [process_item(t, client, sem) for t in tasks]
        results = await tqdm_asyncio.gather(*coroutines, desc="Evaluating")
        
        # 3. Stats
        stats = {'count': 0, 'c_strict': 0, 'c_relax': 0, 'b_strict': 0, 'b_relax': 0}
        type_stats = {}

        for res in results:
            if not res['valid']: continue
            stats['count'] += 1
            stats['c_relax'] += res['score_curr']
            stats['b_relax'] += res['score_base']
            if res['score_curr'] == 1.0: stats['c_strict'] += 1
            if res['score_base'] == 1.0: stats['b_strict'] += 1
            
            for t in res['types']:
                t = str(t)
                if t not in type_stats: type_stats[t] = {'cnt':0, 'c_r':0, 'b_r':0, 'c_s':0, 'b_s':0}
                type_stats[t]['cnt'] += 1
                type_stats[t]['c_r'] += res['score_curr']
                type_stats[t]['b_r'] += res['score_base']
                if res['score_curr'] == 1.0: type_stats[t]['c_s'] += 1
                if res['score_base'] == 1.0: type_stats[t]['b_s'] += 1

        # 4. Report
        if stats['count'] > 0:
            total = stats['count']
            c_s_acc = stats['c_strict']/total
            b_s_acc = stats['b_strict']/total
            diff = (c_s_acc - b_s_acc) * 100
            
            report = [
                "\n" + "="*80,
                f"📊 FINAL REPORT (v203 Rescue) | N={total}",
                f"📂 Method A: {CURRENT_PRED_DIR}",
                "-"*80,
                f"{'Metric':<10} | {'Method A':<10} | {'Method B':<10} | {'Diff':<10}",
                "-"*60,
                f"{'Strict':<10} | {c_s_acc:.4f}     | {b_s_acc:.4f}     | {diff:+.2f}%",
                f"{'Relaxed':<10} | {stats['c_relax']/total:.4f}     | {stats['b_relax']/total:.4f}     | {(stats['c_relax']-stats['b_relax'])*100/total:+.2f}%",
                "="*80,
                "📂 TYPE BREAKDOWN (Strict Acc)",
                f"{'Type':<30} | {'Cnt':<5} | {'Curr':<6} | {'Base':<6} | {'Diff'}"
            ]
            
            for t in sorted(type_stats.keys()):
                s = type_stats[t]
                if s['cnt'] == 0: continue
                c_acc = s['c_s']/s['cnt']
                b_acc = s['b_s']/s['cnt']
                report.append(f"{t[:30]:<30} | {s['cnt']:<5} | {c_acc:.3f}  | {b_acc:.3f}  | {(c_acc-b_acc)*100:+.1f}%")
            
            final_log = "\n".join(report)
            print(final_log)
            with open(LOG_FILE_PATH, 'a') as f: f.write(final_log + "\n")

def main():
    proc, logf = start_vllm_server()
    try:
        asyncio.run(run_async_evaluation())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
    finally:
        if proc:
            print("🧹 Stopping server...")
            proc.terminate()
            if logf: logf.close()

if __name__ == "__main__":
    main()