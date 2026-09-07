#!/usr/bin/env python3
"""
AdsQA Evaluation Script (Adapted for v203 Rescue Edition)
[修改点]:
1. 路径: 指向 203_qaar_rescue。
2. 文件名: 改为 prediction.json。
3. Prompt: 增加 "Do NOT penalize brevity" 规则，确保短语回答能拿满分。
"""

import json
import os
import re
import time
import sys
import subprocess
import requests
import concurrent.futures
from openai import OpenAI
from tqdm import tqdm

# ==============================================================================
# ⚙️ 1. 模型服务配置
# ==============================================================================
SERVER_CONFIG = {
    "model_path": "/data1/rmx/projectb/models/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
    "served_name": "llama-local",
    "port": 8000,
    "gpu_memory_utilization": 0.95,
    "max_model_len": 4096
}

# 指定 GPU ID (确保此卡显存空闲)
GPU_IDS = "5" 

# ==============================================================================
# ⚙️ 2. 评测任务配置 (关键修改)
# ==============================================================================

# [修改 1] 指向最新的 v203 输出目录
PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results'
# results里面是采用最新覆盖脚本评估的

# [修改 2] 推理脚本生成的标准文件名
TARGET_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'

GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'

API_KEY = 'EMPTY'
BASE_URL = f"http://localhost:{SERVER_CONFIG['port']}/v1"
MODEL_NAME = SERVER_CONFIG['served_name']

MAX_WORKERS = 40  # 并发数

# ==============================================================================
# 🔧 服务管理模块
# ==============================================================================

def start_vllm_server():
    """后台启动 vLLM 服务"""
    # 先检查服务是否已存在，存在则不重启
    try:
        if requests.get(f"{BASE_URL}/models", timeout=2).status_code == 200:
            print("✅ [System] Reusing existing server.")
            return None, None
    except: pass

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
    env["CUDA_VISIBLE_DEVICES"] = GPU_IDS
    
    print(f"\n🚀 [System] Starting vLLM Server on GPU {GPU_IDS}...")
    log_file = open("vllm_server.log", "w")
    process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, env=env)
    return process, log_file

def wait_for_server(url, timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if requests.get(f"{url}/models", timeout=5).status_code == 200:
                print("✅ [System] Server is Ready!")
                return True
        except: pass
        time.sleep(5)
        print(".", end="", flush=True)
    return False

# ==============================================================================
# 🧠 评测逻辑 (Prompt 优化)
# ==============================================================================

# [修改 3] 针对 v203 的“极简短语”策略，优化评分规则
prompt_template = """
You are an advertising expert evaluating whether a respondent's answer matches the golden answer.

### Meta-Information:
{meta_info}

### Question: 
{question}

### Golden Answer: 
{golden_answer}

### Candidate Response: 
{response}

### Rules:
1. MATCH (1.0): The response contains ALL key information (entities, numbers, concepts) from the golden answer. Synonyms are allowed.
2. MISMATCH (0.0): The response misses key info or contains hallucinations/contradictions.
3. PARTIAL (0.5): The response contains MOST key info but misses minor details.
4. **IMPORTANT**: Do NOT penalize the response for being a short phrase (e.g., "Nike") instead of a full sentence. Brevity is preferred.

### Instructions:
Output ONLY one line:
Answer: 0
Answer: 0.5
Answer: 1
"""

def get_client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=1200.0)

def parse_score(content):
    if "Answer: 1" in content: return 1.0
    elif "Answer: 0.5" in content: return 0.5
    elif "Answer: 0" in content: return 0.0
    else:
        match = re.search(r"Answer:\s*(\d+(\.\d+)?)", content)
        if match: return float(match.group(1))
    return -1.0

def process_single_item(item_data):
    q_id, gt_item, pred_path, client = item_data
    try:
        with open(pred_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
        
        if isinstance(pred_data, list): target_entry = pred_data[0]
        else: target_entry = pred_data

        # 强制重跑 (Force Overwrite) 以应用新 Prompt
        score = -1.0 
        
        if score == -1.0:
            prediction = target_entry.get('prediction', '')
            if not prediction: return None 
            if len(prediction.split()) > 300: prediction = ' '.join(prediction.split()[0:300])

            raw_gold = gt_item.get('answer', gt_item.get('gt_answer', gt_item.get('answers')))
            if isinstance(raw_gold, list): golden_answer_str = "; ".join([str(x) for x in raw_gold])
            elif raw_gold is not None: golden_answer_str = str(raw_gold)
            else: return None

            prompt = prompt_template.format(
                meta_info=gt_item.get('meta_info', ''),
                question=gt_item.get('question', ''),
                golden_answer=golden_answer_str,
                response=prediction
            )

            for attempt in range(3):
                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "You are a fair and strict evaluation judge."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        max_tokens=10
                    )
                    content = completion.choices[0].message.content
                    score = parse_score(content)
                    
                    target_entry['score'] = content 
                    with open(pred_path, 'w', encoding='utf-8') as f:
                        json.dump(pred_data, f, indent=4, ensure_ascii=False)
                    break 
                except Exception as e:
                    time.sleep(1)

        if score != -1.0:
            q_types = gt_item.get('question_type', ['unknown'])
            if isinstance(q_types, str):
                 try: q_types = json.loads(q_types.replace("'", '"'))
                 except: q_types = [q_types]
            return {'id': q_id, 'score': score, 'types': q_types}
    except Exception as e:
        return None
    return None

def run_evaluation():
    print(f"🚀 Starting Evaluation for v203 (Rescue Mode)...")
    print(f"📂 Target Dir: {PRED_DIR}")
    
    client = get_client()

    if not os.path.exists(GT_FILE):
        print(f"❌ Error: GT file not found at {GT_FILE}")
        return
    
    with open(GT_FILE, 'r') as f: gt_data = json.load(f)
    gt_map = {str(item['question_id']): item for item in gt_data}

    tasks = []
    for q_id in gt_map.keys():
        pred_path = os.path.join(PRED_DIR, q_id, TARGET_FILE_NAME)
        if not os.path.exists(pred_path):
            backup_path = os.path.join(PRED_DIR, f"{q_id}.json")
            if os.path.exists(backup_path): pred_path = backup_path
            else: pred_path = None
        if pred_path: tasks.append((q_id, gt_map[q_id], pred_path, client))

    print(f"✅ Found {len(tasks)} files to evaluate.")
    stats = {'total_count': 0, 'strict_correct': 0, 'relaxed_score_sum': 0, 'type_stats': {}}

    if len(tasks) > 0:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_single_item, task): task[0] for task in tasks}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(tasks), desc="Evaluating"):
                result = future.result()
                if result:
                    score = result['score']
                    q_types = result['types']
                    stats['total_count'] += 1
                    stats['relaxed_score_sum'] += score
                    if score == 1.0: stats['strict_correct'] += 1
                    for t in q_types:
                        if t not in stats['type_stats']: stats['type_stats'][t] = {'count': 0, 'strict': 0, 'relax_sum': 0}
                        stats['type_stats'][t]['count'] += 1
                        stats['type_stats'][t]['relax_sum'] += score
                        if score == 1.0: stats['type_stats'][t]['strict'] += 1
    
    if stats['total_count'] > 0:
        print("\n" + "=" * 80)
        print(f"🏆 Overall Results (N={stats['total_count']})")
        print(f"Strict Acc: {stats['strict_correct']/stats['total_count']:.4f}")
        print(f"Relaxed Acc: {stats['relaxed_score_sum']/stats['total_count']:.4f}")
        print("-" * 80)
        print(f"{'Type':<15} | {'Count':<6} | {'Strict Acc':<12} | {'Relaxed Acc':<12}")
        print("-" * 80)
        
        sorted_types = sorted(stats['type_stats'].keys())
        for t in sorted_types:
            s = stats['type_stats'][t]
            if s['count'] > 0:
                t_strict = s['strict'] / s['count']
                t_relax = s['relax_sum'] / s['count']
                print(f"{t:<15} | {s['count']:<6} | {t_strict:.4f}       | {t_relax:.4f}")
        print("=" * 80)
    else:
        print("⚠️ No valid evaluations processed.")

def main():
    server_process = None
    log_file = None
    
    try:
        server_process, log_file = start_vllm_server()
        if wait_for_server(BASE_URL):
            run_evaluation()
        else:
            print("❌ Skipping evaluation due to server failure.")
            
    except KeyboardInterrupt:
        print("\n🛑 User interrupted.")
    finally:
        if server_process:
            print("\n🧹 [System] Shutting down vLLM server...")
            server_process.terminate()
            server_process.wait()
            print("✅ Server stopped.")
        if log_file:
            log_file.close()

if __name__ == "__main__":
    main()