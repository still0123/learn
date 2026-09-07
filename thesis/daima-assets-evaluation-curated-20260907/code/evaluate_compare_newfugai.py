#!/usr/bin/env python3
"""
DeepSeek Evaluation Script (Force Re-Evaluation Mode)
[核心修改]:
1. 强制重置分数 (score = -1.0)，确保所有样本都会重新调用 DeepSeek API 进行打分。
2. Prompt 修正：使用通用的、最严格的评分规则。
3. 路径修正：使用最新的 v204 完整句子模式路径进行对比。
"""
import json
import os
import re
import time
import concurrent.futures
from openai import OpenAI
from tqdm import tqdm

# ==============================================================================
# ⚙️ 1. 配置区域
# ==============================================================================

# ⚠️ 评估路径配置 (请根据需要自行调整)
# [当前测试] 您的 V204 完整句子模式输出目录
# PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/204_complete_sentence' 
PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results_cot_reflection' # 如果想重评 Baseline，则使用这个路径

# Ground Truth (标准答案) JSON 文件路径
GT_FILE = '/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json'

# 每个子文件夹中的预测文件名
TARGET_FILE_NAME = 'prediction.json'
# TARGET_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'

# DeepSeek API 配置 (保持不变)
API_KEY = os.environ["DEEPSEEK_API_KEY"]
BASE_URL = "https://api.deepseek.com/v1" # DeepSeek URL 必须带 /v1
MODEL_NAME = "deepseek-chat"

# 并发线程数
MAX_WORKERS = 10 

# ==============================================================================
# 🧠 评测逻辑区域 (强制重评)
# ==============================================================================

# 使用通用的评分模板
prompt_template = """
You are an advertising expert specializing in evaluating whether a respondent's answer after watching a video matches the golden answer.

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
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60.0)

def parse_score(content):
    if "Answer: 1" in content: return 1.0
    elif "Answer: 0.5" in content: return 0.5
    elif "Answer: 0" in content: return 0.0
    match = re.search(r"Answer:\s*(\d+(\.\d+)?)", content)
    return float(match.group(1)) if match else -1.0

def process_single_item(item_data):
    q_id, gt_item, pred_path, client = item_data
    
    try:
        # 1. 读取预测文件
        with open(pred_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
        
        if isinstance(pred_data, list): target_entry = pred_data[0]
        else: target_entry = pred_data

        # 2. [核心修改] 强制分数重置，无论是否有旧分数，都重新打分
        score = -1.0 
        
        # 3. 调用 DeepSeek
        if score == -1.0: # 这一步现在是永远为真
            prediction = target_entry.get('prediction', '')
            if not prediction: return None 

            if len(prediction.split()) > 300: 
                prediction = ' '.join(prediction.split()[0:300])

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

            max_retries = 3
            for attempt in range(max_retries):
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
                    
                    # 4. 将结果写回 JSON
                    target_entry['score'] = content 
                    
                    # 这里必须判断 pred_data 是列表还是字典才能正确写回
                    save_data = [target_entry] if isinstance(pred_data, list) else target_entry
                    with open(pred_path, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, indent=4, ensure_ascii=False)
                    
                    break 
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"\n[Error] Failed to evaluate ID {q_id} after retries: {e}")
                    time.sleep(2) 

        # 5. 返回统计数据
        if score != -1.0:
            q_types = gt_item.get('question_type', ['unknown'])
            if isinstance(q_types, str):
                 try: q_types = json.loads(q_types.replace("'", '"'))
                 except: q_types = [q_types]
            
            return {
                'id': q_id,
                'score': score,
                'types': q_types
            }

    except Exception as e:
        print(f"\n[Fatal Error] Processing {q_id}: {e}")
        return None
    
    return None

def main():
    print(f"🚀 Starting Evaluation Script (DeepSeek API) - FORCE RE-EVALUATION")
    print(f"📂 Predictions Dir: {PRED_DIR}")
    
    client = get_client()

    if not os.path.exists(GT_FILE):
        print(f"❌ Error: GT file not found at {GT_FILE}")
        return
    
    with open(GT_FILE, 'r') as f:
        gt_data = json.load(f)
    gt_map = {str(item['question_id']): item for item in gt_data}

    # 扫描目录寻找待评测文件
    tasks = []
    print(f"Scanning directories...")
    
    for q_id in gt_map.keys():
        pred_path = os.path.join(PRED_DIR, q_id, TARGET_FILE_NAME)
        
        if not os.path.exists(pred_path):
            backup_path = os.path.join(PRED_DIR, f"{q_id}.json")
            if os.path.exists(backup_path): pred_path = backup_path
            else: pred_path = None
        
        if pred_path: tasks.append((q_id, gt_map[q_id], pred_path, client))

    print(f"✅ Found {len(tasks)} files to evaluate.")

    # 统计容器
    stats = {
        'total_count': 0,
        'strict_correct': 0,
        'relaxed_score_sum': 0,
        'type_stats': {}
    }

    # 并发执行
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
    
    # ================= 输出最终报表 =================
    if stats['total_count'] > 0:
        strict_acc = stats['strict_correct'] / stats['total_count']
        relax_acc = stats['relaxed_score_sum'] / stats['total_count']
        
        print("\n" + "=" * 80)
        print(f"🏆 Overall Results (DeepSeek - Evaluated {stats['total_count']} samples)")
        print(f"Strict Accuracy: {strict_acc:.4f}")
        print(f"Relaxed Accuracy: {relax_acc:.4f}")
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

if __name__ == "__main__":
    main()
