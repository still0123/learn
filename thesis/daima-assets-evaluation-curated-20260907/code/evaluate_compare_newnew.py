#!/usr/bin/env python3
"""
DeepSeek Comparative Evaluation Script (Comprehensive Edition)
[功能]: 同时评估 Method A 和 Method B，生成包含 Strict 和 Relaxed 准确率的详细对比报表。
[新增]: "TYPE BREAKDOWN" 增加 Relaxed Accuracy 对比。
"""

import json
import os
import re
import time
import datetime
import asyncio
import httpx
from tqdm.asyncio import tqdm_asyncio
import logging
import sys

# ==============================================================================
# ⚙️ 1. 配置区域
# ==============================================================================

GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'

# Method A (New)上面是当前结果最好的一次，推理文件163qwen3
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5_qwen3_pure'
# 下面是改进了音频热力图融合的版本
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v10_14_patent_hybrid'

# 努力改进宽松中，但是精度下降10%
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/163qwen3relax2'
# CURRENT_FILE_NAME = 'prediction.json'


CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results222_fixed'
CURRENT_FILE_NAME = 'Qwen2.5-VL-7B-Instruct.json'


# ==========================================================================================


# 我的版本+6.78宽松-2.02
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/163qwen3_rich_prompt'
# CURRENT_FILE_NAME = 'prediction.json'

# qwen3 baseline 版本精度各提升3%
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_baseline'
# CURRENT_FILE_NAME = 'Qwen3-VL-Instruct.json'

#llava-onevision
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results_llava_ov'
# CURRENT_FILE_NAME = 'llava-onevision-qwen2-7b-ov-hf.json'

# #MiniCPM
# CURRENT_PRED_DIR = '//data1/rmx/projectb/AdsQA-main/evaluation/results_minicpm'
# CURRENT_FILE_NAME = 'MiniCPM-V-2_6.json'

# # Qwen2-VL-7B
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen2vl'
# CURRENT_FILE_NAME = 'Qwen2-VL-7B-Instruct.json'

# # Qwen2.5-VL-7B
# CURRENT_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results222'
# CURRENT_FILE_NAME = 'Qwen2.5-VL-7B-Instruct.json'

# Method B (Base)Qwen2.5-7B-VL-ReAd-R
BASELINE_PRED_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results'
BASELINE_FILE_NAME = 'Qwen2.5-7B-VL-ReAd-R.json'

API_KEY = os.environ["DEEPSEEK_API_KEY"]
BASE_URL = "https://api.deepseek.com/v1" 
MODEL_NAME = "deepseek-chat"

# 强制将日志保存在脚本所在的目录下
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "evaluation_history.txt")

SAMPLE_LIMIT = 1000
CONCURRENCY = 10 

# ==============================================================================
# 🧩 日志初始化
# ==============================================================================
def setup_logging():
    log_formatter = logging.Formatter('%(message)s') 
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('tqdm').setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 评测核心逻辑
# ==============================================================================

JUDGE_PROMPT = """
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

def parse_score(content):
    if "Answer: 1" in content: return 1.0
    elif "Answer: 0.5" in content: return 0.5
    elif "Answer: 0" in content: return 0.0
    match = re.search(r"Answer:\s*(\d+(\.\d+)?)", content)
    return float(match.group(1)) if match else -1.0

async def evaluate_single(client, text_prompt, target_entry, pred_path, sem):
    current_score_str = target_entry.get('score', '')
    if current_score_str and isinstance(current_score_str, str) and "Answer:" in current_score_str:
        return parse_score(current_score_str)

    async with sem:
        for attempt in range(3): 
            try:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    json={
                        "model": MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": "You are a fair and strict evaluation judge."},
                            {"role": "user", "content": text_prompt}
                        ],
                        "temperature": 0.0,
                        "max_tokens": 20
                    },
                    timeout=90.0
                )
                
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content']
                    score = parse_score(content)
                    if score != -1.0:
                        target_entry['score'] = content
                        with open(pred_path, 'w', encoding='utf-8') as f:
                            json.dump(target_entry, f, indent=4, ensure_ascii=False)
                        return score
                else:
                    if 'Insufficient Balance' in response.text: return -1.0
            except Exception: pass
            await asyncio.sleep(2 ** attempt)
        return -1.0

async def process_comparison_item(item_data, client, sem):
    q_id, gt_item, curr_path, base_path = item_data
    
    def load_pred_file(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data[0] if isinstance(data, list) else data
        except: return None

    curr_entry = load_pred_file(curr_path)
    base_entry = load_pred_file(base_path)

    if not curr_entry or not base_entry: return {'valid': False}

    raw_gold = gt_item.get('answer', gt_item.get('gt_answer', gt_item.get('answers')))
    if isinstance(raw_gold, list): gold_str = "; ".join(map(str, raw_gold))
    elif raw_gold is not None: gold_str = str(raw_gold)
    else: return {'valid': False}

    meta_info = gt_item.get('meta_info', '')
    question = gt_item.get('question', '')
    
    # 评估
    prompt_curr = JUDGE_PROMPT.format(meta_info=meta_info, question=question, golden_answer=gold_str, response=curr_entry.get('prediction', '')[:3000])
    score_curr = await evaluate_single(client, prompt_curr, curr_entry, curr_path, sem)

    prompt_base = JUDGE_PROMPT.format(meta_info=meta_info, question=question, golden_answer=gold_str, response=base_entry.get('prediction', '')[:3000])
    score_base = await evaluate_single(client, prompt_base, base_entry, base_path, sem)

    q_types = gt_item.get('question_type', ['unknown'])
    if isinstance(q_types, str): 
        try: q_types = json.loads(q_types.replace("'", '"'))
        except: q_types = [q_types]

    return {
        'valid': (score_curr != -1.0 and score_base != -1.0),
        'score_curr': max(0.0, score_curr),
        'score_base': max(0.0, score_base),
        'types': q_types
    }

async def run_async_evaluation():
    start_time = datetime.datetime.now()
    start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"🚀 Evaluation Started at {start_str}")
    print(f"🔹 Method A: {CURRENT_PRED_DIR}")
    print(f"🔸 Method B: {BASELINE_PRED_DIR}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        if not os.path.exists(GT_FILE): return

        with open(GT_FILE, 'r') as f: gt_map = {str(i['question_id']): i for i in json.load(f)}
        
        tasks = []
        for qid in gt_map:
            c_p = os.path.join(CURRENT_PRED_DIR, qid, CURRENT_FILE_NAME)
            b_p = os.path.join(BASELINE_PRED_DIR, qid, BASELINE_FILE_NAME)
            
            # 路径兼容
            if not os.path.exists(c_p): c_p = os.path.join(CURRENT_PRED_DIR, qid, os.path.basename(CURRENT_PRED_DIR) + ".json")
            if not os.path.exists(b_p): b_p = os.path.join(BASELINE_PRED_DIR, qid, os.path.basename(BASELINE_PRED_DIR) + ".json")

            if os.path.exists(c_p) and os.path.exists(b_p):
                tasks.append((qid, gt_map[qid], c_p, b_p))
                if SAMPLE_LIMIT and len(tasks) >= SAMPLE_LIMIT: break
        
        print(f"✅ Pairs found: {len(tasks)}")
        
        sem = asyncio.Semaphore(CONCURRENCY)
        results = await tqdm_asyncio.gather(*[process_comparison_item(t, client, sem) for t in tasks], desc="Judging")
        
        # --- 统计 ---
        stats = {'count': 0, 'c_strict': 0, 'c_relax': 0, 'b_strict': 0, 'b_relax': 0}
        type_stats = {}

        for res in results:
            if not res or not res['valid']: continue
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

        end_time = datetime.datetime.now()
        duration = end_time - start_time
        
        if stats['count'] > 0:
            total = stats['count']
            c_s_acc = stats['c_strict']/total
            b_s_acc = stats['b_strict']/total
            
            report = [
                "\n" + "="*80,
                f"📝 EVALUATION REPORT | {start_str} -> {end_time.strftime('%H:%M:%S')} (Duration: {duration})",
                f"📂 Method A (New):  {CURRENT_PRED_DIR}",
                f"📂 Method B (Base): {BASELINE_PRED_DIR}",
                "-"*80,
                f"{'Metric':<10} | {'Method A':<10} | {'Method B':<10} | {'Diff':<10}",
                "-"*60,
                f"{'Strict':<10} | {c_s_acc:.4f}     | {b_s_acc:.4f}     | {(c_s_acc-b_s_acc)*100:+.2f}%",
                f"{'Relaxed':<10} | {stats['c_relax']/total:.4f}     | {stats['b_relax']/total:.4f}     | {(stats['c_relax']-stats['b_relax'])*100/total:+.2f}%",
                "="*80,
            ]

            # --- 严格准确率 (Strict Accuracy) ---
            report.append("📂 TYPE BREAKDOWN (Strict Acc)")
            report.append(f"{'Type':<30} | {'Cnt':<5} | {'Curr':<6} | {'Base':<6} | {'Diff'}")
            sorted_keys = sorted(type_stats.keys())
            
            for t in sorted_keys:
                s = type_stats[t]
                if s['cnt'] == 0: continue
                c_acc = s['c_s']/s['cnt']
                b_acc = s['b_s']/s['cnt']
                report.append(f"{t[:30]:<30} | {s['cnt']:<5} | {c_acc:.3f}  | {b_acc:.3f}  | {(c_acc-b_acc)*100:+.1f}%")
            
            report.append("-" * 80)

            # --- 宽松准确率 (Relaxed Accuracy) ---
            report.append("📂 TYPE BREAKDOWN (Relaxed Acc) - [New]")
            report.append(f"{'Type':<30} | {'Cnt':<5} | {'Curr':<6} | {'Base':<6} | {'Diff'}")
            
            for t in sorted_keys:
                s = type_stats[t]
                if s['cnt'] == 0: continue
                c_acc = s['c_r']/s['cnt']
                b_acc = s['b_r']/s['cnt']
                report.append(f"{t[:30]:<30} | {s['cnt']:<5} | {c_acc:.3f}  | {b_acc:.3f}  | {(c_acc-b_acc)*100:+.1f}%")

            report.append("="*80 + "\n")
            
            final_log = "\n".join(report)
            print(final_log)
            logger.info(final_log) 

def main():
    try:
        asyncio.run(run_async_evaluation())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
