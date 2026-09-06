import argparse
import json
import os
import re
import time
import concurrent.futures
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

# ==============================================================================
# ⚙️ 配置区域 (DeepSeek 版本)
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# These globals are populated from explicit CLI arguments in main(). They remain
# module-level because worker functions use them during concurrent evaluation.
PRED_DIR = ""
GT_FILE = str(PROJECT_ROOT / "data/testset_groundtruth.json")


# 3. 每个子文件夹中的预测文件名
TARGET_FILE_NAME = 'prediction.json'
# TARGET_FILE_NAME = 'Qwen2.5-VL-7B-Instruct.json'
# TARGET_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'

# 4. DeepSeek API 配置
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DISABLE_THINKING = os.environ.get("JUDGE_DISABLE_THINKING", "0") == "1"

# 5. 并发线程数
# DeepSeek 服务端并发能力较强，10 是比较安全的数值
MAX_WORKERS = 10 

# ==============================================================================
# 核心逻辑区域
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
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required to run API evaluation")
    # 增加超时设置，防止网络波动卡死
    return OpenAI(api_key=api_key, base_url=BASE_URL, timeout=60.0)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate AdsQA predictions with DeepSeek")
    parser.add_argument("--pred-dir", required=True, help="Run directory containing prediction files")
    parser.add_argument("--gt-file", default=GT_FILE, help="Ground-truth JSON file")
    parser.add_argument("--target-file", default=TARGET_FILE_NAME, help="Prediction filename in each question directory")
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    return parser.parse_args()

def parse_score(content):
    """解析模型输出，提取分数"""
    if "Answer: 1" in content:
        return 1.0
    elif "Answer: 0.5" in content:
        return 0.5
    elif "Answer: 0" in content:
        return 0.0
    else:
        # 尝试正则提取数字
        match = re.search(r"Answer:\s*(\d+(\.\d+)?)", content)
        if match:
            return float(match.group(1))
    return -1.0

def process_single_item(item_data):
    """
    单个样本的处理逻辑
    """
    q_id, gt_item, pred_path, client = item_data
    
    try:
        # 1. 读取预测文件
        with open(pred_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
        
        # 兼容列表或字典格式
        if isinstance(pred_data, list):
            target_entry = pred_data[0]
        else:
            target_entry = pred_data

        # 2. 检查是否已经评分 (断点续评)
        current_score_str = target_entry.get('score', '')
        score = -1.0
        
        if current_score_str and isinstance(current_score_str, str) and "Answer:" in current_score_str:
            score = parse_score(current_score_str)
        
        # 3. 如果没有分数，调用 DeepSeek
        if score == -1.0:
            prediction = target_entry.get('prediction', '')
            if not prediction:
                return None 

            if len(prediction.split()) > 300: 
                prediction = ' '.join(prediction.split()[0:300])

            # === [核心修复] 智能获取 Golden Answer ===
            # 优先找 'answer'，如果报错找不到，尝试找 'gt_answer' (针对 modify 类题目)，再找 'answers'
            raw_gold = gt_item.get('answer', gt_item.get('gt_answer', gt_item.get('answers')))
            
            # 如果答案是列表，转为字符串，避免报错
            if isinstance(raw_gold, list):
                golden_answer_str = "; ".join([str(x) for x in raw_gold])
            elif raw_gold is not None:
                golden_answer_str = str(raw_gold)
            else:
                # 实在找不到答案，打印警告并跳过，防止程序崩溃
                print(f"\n[Warning] ID {q_id} skipped: No answer found in GT keys: {list(gt_item.keys())}")
                return None

            prompt = prompt_template.format(
                meta_info=gt_item.get('meta_info', ''),
                question=gt_item.get('question', ''),
                golden_answer=golden_answer_str,
                response=prediction
            )

            # API 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    request_kwargs = {}
                    if DISABLE_THINKING:
                        request_kwargs["extra_body"] = {
                            "chat_template_kwargs": {"enable_thinking": False}
                        }
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant acting as an evaluation judge."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        max_tokens=20,
                        **request_kwargs,
                    )
                    content = completion.choices[0].message.content
                    score = parse_score(content)
                    
                    # 4. 将结果写回 JSON
                    target_entry['score'] = content 
                    target_entry['_judge_api_response'] = {
                        'model': completion.model,
                        'usage': completion.usage.model_dump() if completion.usage else None,
                    }
                    
                    with open(pred_path, 'w', encoding='utf-8') as f:
                        json.dump(pred_data, f, indent=4, ensure_ascii=False)
                    
                    break 
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"\n[Error] Failed to evaluate ID {q_id} after retries: {e}")
                    time.sleep(2) 

        # 5. 返回统计数据
        if score != -1.0:
            q_types = gt_item.get('question_type', ['unknown'])
            # 处理字符串格式的列表 "[...]"
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
    global PRED_DIR, GT_FILE, TARGET_FILE_NAME, MAX_WORKERS

    args = parse_args()
    PRED_DIR = args.pred_dir
    GT_FILE = args.gt_file
    TARGET_FILE_NAME = args.target_file
    MAX_WORKERS = args.max_workers

    print(f"🚀 Starting Evaluation Script (DeepSeek API)")
    print(f"📂 Predictions Dir: {PRED_DIR}")
    print(f"📄 Ground Truth:   {GT_FILE}")
    print("-" * 60)

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
            if os.path.exists(backup_path):
                pred_path = backup_path
            else:
                pred_path = None
        
        if pred_path:
            tasks.append((q_id, gt_map[q_id], pred_path, client))

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
                    if score == 1.0:
                        stats['strict_correct'] += 1
                    
                    # 分类统计
                    for t in q_types:
                        if t not in stats['type_stats']:
                            stats['type_stats'][t] = {'count': 0, 'strict': 0, 'relax_sum': 0}
                        stats['type_stats'][t]['count'] += 1
                        stats['type_stats'][t]['relax_sum'] += score
                        if score == 1.0:
                            stats['type_stats'][t]['strict'] += 1
    
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
