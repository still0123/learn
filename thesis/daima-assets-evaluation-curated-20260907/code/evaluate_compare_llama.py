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
    
    # [修改点 1] 显存利用率设为 0.95
    # 因为下面我们禁用了 CUDA Graph，所以这里可以设高一点，让 vLLM 尽可能利用剩下的空间
    "gpu_memory_utilization": 0.95,
    
    "max_model_len": 4096
}

# 指定 GPU ID
GPU_IDS = "2" 

# ==============================================================================
# ⚙️ 2. 评测任务配置
# ==============================================================================

# PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results'
# GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'
# TARGET_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'


PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results'
GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'
TARGET_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'

# PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5_2'
# GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'
# TARGET_FILE_NAME = 'prediction.json'



API_KEY = 'EMPTY'
BASE_URL = f"http://localhost:{SERVER_CONFIG['port']}/v1"
MODEL_NAME = SERVER_CONFIG['served_name']

MAX_WORKERS = 5 

# ==============================================================================
# 🔧 服务管理模块
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
        
        # [修改点 2] 关键救命参数！
        # 强制关闭 CUDA Graph。这会牺牲一点推理速度，但能大幅减少显存占用，
        # 是在 48G 显存上跑 70B 模型的必要手段。
        "--enforce-eager"
    ]
    
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = GPU_IDS
    
    print(f"\n🚀 [System] Starting vLLM Server on GPU {GPU_IDS}...")
    print(f"👉 Command: {' '.join(cmd)}")
    
    log_file = open("vllm_server.log", "w")
    process = subprocess.Popen(
        cmd, 
        stdout=log_file, 
        stderr=subprocess.STDOUT,
        env=env
    )
    return process, log_file

def wait_for_server(url, timeout=600):
    """等待服务就绪"""
    print(f"⏳ [System] Waiting for server to be ready at {url} (Check vllm_server.log for details)...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/models", timeout=5)
            if response.status_code == 200:
                print("✅ [System] Server is Ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            print(f"Wait warning: {e}")
        
        time.sleep(5)
        print(".", end="", flush=True)
    
    print("\n❌ [Error] Server failed to start within timeout.")
    return False

# ==============================================================================
# 🧠 评测逻辑区域
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

def process_single_item(item_data):
    q_id, gt_item, pred_path, client = item_data
    try:
        with open(pred_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
        
        if isinstance(pred_data, list): target_entry = pred_data[0]
        else: target_entry = pred_data

        current_score_str = target_entry.get('score', '')
        score = -1.0
        if current_score_str and isinstance(current_score_str, str) and "Answer:" in current_score_str:
            score = parse_score(current_score_str)
        
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
                            {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        max_tokens=20
                    )
                    content = completion.choices[0].message.content
                    score = parse_score(content)
                    target_entry['score'] = content 
                    with open(pred_path, 'w', encoding='utf-8') as f:
                        json.dump(pred_data, f, indent=4, ensure_ascii=False)
                    break 
                except Exception as e:
                    time.sleep(2)

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
    print(f"🚀 Starting Evaluation Logic...")
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
    
    # [修复] 打印详细表格
    if stats['total_count'] > 0:
        print("\n" + "=" * 80)
        print(f"🏆 Overall Results: Strict Acc: {stats['strict_correct']/stats['total_count']:.4f} | Relaxed Acc: {stats['relaxed_score_sum']/stats['total_count']:.4f}")
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

# ==============================================================================
# 🚀 主程序入口
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
            print("✅ Server stopped.")
        if log_file:
            log_file.close()

if __name__ == "__main__":
    main()