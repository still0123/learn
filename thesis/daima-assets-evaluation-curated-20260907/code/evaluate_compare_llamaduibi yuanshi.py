#!/usr/bin/env python3
import json
import os
import re
import time
import sys
import subprocess
import requests
import concurrent.futures
import datetime
from openai import OpenAI
from tqdm import tqdm

# ==============================================================================
# ⚙️ 1. 模型服务配置 (Judge Model: Llama-3-70B)
# ==============================================================================
SERVER_CONFIG = {
    "model_path": "/data1/rmx/projectb/models/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
    "served_name": "llama-local",
    "port": 8000,
    "gpu_memory_utilization": 0.95,
    "max_model_len": 4096
}

# 指定用于跑打分模型(Llama)的显卡ID
GPU_IDS = "5" 

# [新增] 日志保存路径
LOG_FILE_PATH = "evaluation_log.txt"

# ==============================================================================
# ⚙️ 2. 评测任务配置 (A vs B 对比模式)
# ==============================================================================

# [配置 1] Ground Truth 文件路径
GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'

# [配置 2] 方法 A (Current / 新方法)
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/164'
# CURRENT_FILE_NAME = 'prediction.json'

# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results222'
# CURRENT_FILE_NAME = 'Qwen2.5-VL-7B-Instruct.json'

CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/202_qaar_new'
CURRENT_FILE_NAME = 'prediction.json'

# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results_cot_reflection'
# CURRENT_FILE_NAME = 'prediction.json'

# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/165_rl2'
# CURRENT_FILE_NAME = 'prediction.json'

# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/165_rl_3'
# CURRENT_FILE_NAME = 'prediction.json'

# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/165_quanjudaojubu_base'
# CURRENT_FILE_NAME = 'prediction.json'

# [配置 3] 方法 B (Baseline / 旧方法)
BASELINE_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results'
BASELINE_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'


# [配置 4] 采样数量限制 (None 表示跑全部)
SAMPLE_LIMIT = None 

# ------------------------------------------------------------------------------
# API 连接配置
API_KEY = 'EMPTY'
BASE_URL = f"http://localhost:{SERVER_CONFIG['port']}/v1"
MODEL_NAME = SERVER_CONFIG['served_name']
MAX_WORKERS = 8  # 并发线程数

# ==============================================================================
# 🔧 VLLM 服务管理模块
# ==============================================================================

def start_vllm_server():
    """后台启动 vLLM 服务"""
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
    
    print(f"\n🚀 [System] Starting vLLM Judge Server on GPU {GPU_IDS}...")
    log_file = open("vllm_server.log", "w")
    process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, env=env)
    return process, log_file

def wait_for_server(url, timeout=600):
    print(f"⏳ [System] Waiting for server at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if requests.get(f"{url}/models", timeout=5).status_code == 200:
                print("✅ [System] Judge Server is Ready!")
                return True
        except: pass
        time.sleep(5)
        print(".", end="", flush=True)
    print("\n❌ Server start timeout.")
    return False

# ==============================================================================
# 🧠 评测核心逻辑 (Prompt & Scoring)
# ==============================================================================

prompt_template = """
You are an advertising expert specializing in evaluating whether a respondent's answer after watching a video matches the golden answer. We will provide the video's Meta-Information, Question, Golden Answer, and the Response to be judged below.

###The meta-information includes the advertisement video's theme, creative points, and a brief content description, which can be regarded as ground-truth information, as follows::
{meta_info}

###Question: 
{question}

###Golden Answer: 
{golden_answer}

###Rule:
1. If the response to be judged contains ALL key information of the golden answer or expresses the same meaning using other sentences or synonyms, it is considered a match with the golden answer, and the output is 1.
2. If the response to be judged does NOT contain the key information from the golden answer, it is considered a mismatch, and the output is 0.
3. The response to be judged should NOT contain any content that is contradictory, conflicting, or unreasonable when inferred from the meta-information. If such content exist, it is considered a mismatch, and the output is 0.
4. If the response to be judged contains the MOST of key information of the golden answer and, do NOT contain any information that is contradictory, conflicting, or unreasonable when inferred from the meta-information, it is considered a partial match, and the output is 0.5.

###Response to be judged: 
{response}

###Instructions:
Follow the format below and do not give any extra outputs:
Answer: 0 (if the response does not match)
Answer: 0.5 (if the response partially match)
Answer: 1 (if the response matches)
"""

def get_client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=600.0)

def parse_score(content):
    if "Answer: 1" in content: return 1.0
    elif "Answer: 0.5" in content: return 0.5
    elif "Answer: 0" in content: return 0.0
    else:
        match = re.search(r"Answer:\s*(\d+(\.\d+)?)", content)
        if match: return float(match.group(1))
    return -1.0

def evaluate_one_file(pred_path, gt_item, client):
    if not pred_path or not os.path.exists(pred_path):
        return -1.0, False 

    try:
        with open(pred_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
        
        if isinstance(pred_data, list): 
            if not pred_data: return -1.0, False
            target_entry = pred_data[0]
            is_list = True
        else: 
            target_entry = pred_data
            is_list = False

        current_score_str = target_entry.get('score', '')
        score = -1.0
        if current_score_str and isinstance(current_score_str, str) and "Answer:" in current_score_str:
            score = parse_score(current_score_str)
        
        if score == -1.0:
            prediction = target_entry.get('prediction', '')
            if not prediction: return 0.0, True 
            
            if len(prediction.split()) > 300: prediction = ' '.join(prediction.split()[0:300])

            raw_gold = gt_item.get('answer', gt_item.get('gt_answer', gt_item.get('answers')))
            if isinstance(raw_gold, list): golden_answer_str = "; ".join([str(x) for x in raw_gold])
            elif raw_gold is not None: golden_answer_str = str(raw_gold)
            else: return -1.0, False 

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
                            {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        max_tokens=20
                    )
                    content = completion.choices[0].message.content
                    score = parse_score(content)
                    
                    target_entry['score'] = content 
                    save_data = [target_entry] if is_list else target_entry
                    with open(pred_path, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, indent=4, ensure_ascii=False)
                    break 
                except Exception as e:
                    time.sleep(1)
        
        if score != -1.0:
            return score, True
        return 0.0, True
        
    except Exception as e:
        return -1.0, False

def process_comparison_item(item_data):
    """线程工作单元：同时评测 A 和 B"""
    q_id, gt_item, current_path, baseline_path, client = item_data
    
    # 获取问题类型
    q_types = gt_item.get('question_type', ['unknown'])
    if isinstance(q_types, str):
        # 处理某些数据集中 question_type 可能是字符串的情况
        q_types = [q_types]
    
    score_curr, valid_curr = evaluate_one_file(current_path, gt_item, client)
    score_base, valid_base = evaluate_one_file(baseline_path, gt_item, client)
    
    return {
        'id': q_id,
        'types': q_types, # 返回类型信息
        'valid': valid_curr and valid_base,
        'score_curr': score_curr,
        'score_base': score_base
    }

def save_log_to_file(content):
    """将结果保存到日志文件"""
    try:
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(content + "\n")
        print(f"📝 Log saved to {LOG_FILE_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to save log: {e}")

def run_evaluation():
    print(f"\n🚀 Starting STRICT COMPARATIVE Evaluation (With Category Breakdown)...")
    print(f"🔹 Method A (Current): {CURRENT_PRED_DIR}")
    print(f"🔸 Method B (Baseline): {BASELINE_PRED_DIR}")
    
    client = get_client()

    if not os.path.exists(GT_FILE):
        print(f"❌ Error: GT file not found at {GT_FILE}")
        return
    
    with open(GT_FILE, 'r') as f: gt_data = json.load(f)
    gt_map = {str(item['question_id']): item for item in gt_data}

    # --- 1. 扫描任务 ---
    tasks = []
    found_count = 0
    
    print("🔍 Scanning for intersecting samples...")
    for q_id in gt_map.keys():
        curr_path = os.path.join(CURRENT_PRED_DIR, q_id, CURRENT_FILE_NAME)
        if not os.path.exists(curr_path):
            backup = os.path.join(CURRENT_PRED_DIR, f"{q_id}.json")
            if os.path.exists(backup): curr_path = backup
            else: curr_path = None
        
        base_path = os.path.join(BASELINE_PRED_DIR, q_id, BASELINE_FILE_NAME)
        if not os.path.exists(base_path):
            backup = os.path.join(BASELINE_PRED_DIR, f"{q_id}.json")
            if os.path.exists(backup): base_path = backup
            else: base_path = None 

        if curr_path and base_path:
            tasks.append((q_id, gt_map[q_id], curr_path, base_path, client))
            found_count += 1
            if SAMPLE_LIMIT and found_count >= SAMPLE_LIMIT:
                break
    
    print(f"✅ Found {len(tasks)} intersecting samples.")

    # --- 2. 并行执行评测与统计 ---
    # 初始化总统计
    stats_overall = {
        'count': 0,
        'curr_strict': 0, 'curr_relax': 0,
        'base_strict': 0, 'base_relax': 0
    }
    # 初始化分类统计
    stats_by_type = {}

    if len(tasks) > 0:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_comparison_item, task): task[0] for task in tasks}
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(tasks), desc="Evaluating"):
                res = future.result()
                
                if res['valid']:
                    # 1. 更新总榜
                    stats_overall['count'] += 1
                    stats_overall['curr_relax'] += res['score_curr']
                    if res['score_curr'] == 1.0: stats_overall['curr_strict'] += 1
                    stats_overall['base_relax'] += res['score_base']
                    if res['score_base'] == 1.0: stats_overall['base_strict'] += 1

                    # 2. 更新分类榜
                    for t in res['types']:
                        t = str(t) # 确保是字符串作为key
                        if t not in stats_by_type:
                            stats_by_type[t] = {
                                'count': 0,
                                'curr_strict': 0, 'curr_relax': 0,
                                'base_strict': 0, 'base_relax': 0
                            }
                        stats_by_type[t]['count'] += 1
                        stats_by_type[t]['curr_relax'] += res['score_curr']
                        if res['score_curr'] == 1.0: stats_by_type[t]['curr_strict'] += 1
                        stats_by_type[t]['base_relax'] += res['score_base']
                        if res['score_base'] == 1.0: stats_by_type[t]['base_strict'] += 1

    # --- 3. 生成详细对比报表 & 保存日志 ---
    if stats_overall['count'] > 0:
        total = stats_overall['count']
        
        # 准备日志内容字符串
        log_content = []
        log_content.append(f"\n==========================================================================================")
        log_content.append(f"📅 Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_content.append(f"📂 Method A (Curr): {CURRENT_PRED_DIR}")
        log_content.append(f"📂 Method B (Base): {BASELINE_PRED_DIR}")
        log_content.append(f"==========================================================================================")
        log_content.append(f"📊 OVERALL REPORT (N={total})")
        log_content.append("-" * 80)
        
        # 计算总体
        c_s = stats_overall['curr_strict'] / total
        c_r = stats_overall['curr_relax'] / total
        b_s = stats_overall['base_strict'] / total
        b_r = stats_overall['base_relax'] / total
        d_s = (c_s - b_s) * 100
        d_r = (c_r - b_r) * 100
        
        log_content.append(f"{'Metric':<15} | {'Curr Acc':<10} | {'Base Acc':<10} | {'Diff':<15}")
        log_content.append("-" * 60)
        log_content.append(f"{'Strict':<15} | {c_s:.4f}     | {b_s:.4f}     | {'+' if d_s>=0 else ''}{d_s:.2f}%")
        log_content.append(f"{'Relaxed':<15} | {c_r:.4f}     | {b_r:.4f}     | {'+' if d_r>=0 else ''}{d_r:.2f}%")

        # --- 生成分类详细表格 ---
        log_content.append("\n📑 DETAILED BREAKDOWN BY QUESTION TYPE")
        log_content.append("-" * 120)
        # 表头
        log_content.append(f"{'Type':<35} | {'Cnt':<5} | {'Curr(S)':<8} | {'Base(S)':<8} | {'Diff(S)':<9} | {'Curr(R)':<8} | {'Base(R)':<8} | {'Diff(R)':<9}")
        log_content.append("-" * 120)
        
        sorted_types = sorted(stats_by_type.keys())
        for t in sorted_types:
            s = stats_by_type[t]
            cnt = s['count']
            if cnt == 0: continue
            
            # 计算各项指标
            curr_strict_acc = s['curr_strict'] / cnt
            base_strict_acc = s['base_strict'] / cnt
            diff_strict = (curr_strict_acc - base_strict_acc) * 100
            
            curr_relax_acc = s['curr_relax'] / cnt
            base_relax_acc = s['base_relax'] / cnt
            diff_relax = (curr_relax_acc - base_relax_acc) * 100
            
            # 格式化输出
            type_str = t[:33] + ".." if len(t) > 33 else t
            ds_icon = "+" if diff_strict >= 0 else ""
            dr_icon = "+" if diff_relax >= 0 else ""
            
            log_content.append(f"{type_str:<35} | {cnt:<5} | {curr_strict_acc:.3f}    | {base_strict_acc:.3f}    | {ds_icon}{diff_strict:>5.1f}%   | {curr_relax_acc:.3f}    | {base_relax_acc:.3f}    | {dr_icon}{diff_relax:>5.1f}%")
            
        log_content.append("=" * 120 + "\n")
        
        # 打印到屏幕
        final_output = "\n".join(log_content)
        print(final_output)
        
        # 保存到文件
        save_log_to_file(final_output)
        
    else:
        print("⚠️ No valid comparison samples found.")

# ==============================================================================
# 🚀 主程序
# ==============================================================================
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
            if log_file: log_file.close()
            print("✅ Server stopped.")

if __name__ == "__main__":
    main()