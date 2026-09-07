#!/usr/bin/env python3
"""
DeepSeek Multi-Model Evaluation (Strict Mode + Pivot Table Report + CSV Export)
[功能]: 
  1. 同时评估 7 个模型在同一批 Question ID 上的表现。
  2. 极速模式：优先读取本地 score，跳过 API。
  3. [核心更新]：输出横向对比表格 + 自动导出 CSV + 提供 Excel 粘贴格式。
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
import csv  # 新增引用

# ================= 1. 配置区域 =================
GT_FILE = '/data1/rmx/projectb/AdsQA-main/evaluation/testset_groundtruth.json'

MODELS_CONFIG = [
    {
        "name": "Ours (Rich)", 
        "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163qwen3_rich_prompt",
        "file": "prediction.json"
    },
    {
        "name": "Qwen3-Base", 
        "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_baseline",
        "file": "Qwen3-VL-Instruct.json"
    },
    {
        "name": "LLaVA-OV", 
        "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/results_llava_ov",
        "file": "llava-onevision-qwen2-7b-ov-hf.json"
    },
    {
        "name": "MiniCPM-V", 
        "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/results_minicpm",
        "file": "MiniCPM-V-2_6.json"
    },
    {
        "name": "Qwen2-VL", 
        "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen2vl",
        "file": "Qwen2-VL-7B-Instruct.json"
    },
    # {
    #     "name": "Qwen2.5-VL", 
    #     "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/results222_fixed",
    #     "file": "Qwen2.5-VL-7B-Instruct.json"
    # },
    {
        "name": "Qwen2.5-ReAd", 
        "dir": "/data1/rmx/projectb/AdsQA-main/evaluation/results",
        "file": "Qwen2.5-7B-VL-ReAd-R.json"
    }
]

API_KEY = os.environ["DEEPSEEK_API_KEY"]
BASE_URL = "https://api.deepseek.com/v1" 
MODEL_NAME = "deepseek-chat"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "evaluation_table_history.txt")
SAMPLE_LIMIT = None
CONCURRENCY = 50

# ================= 2. 基础函数 =================
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
                    timeout=60.0
                )
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content']
                    score = parse_score(content)
                    if score != -1.0:
                        target_entry['score'] = content
                        with open(pred_path, 'w', encoding='utf-8') as f:
                            json.dump(target_entry, f, indent=4, ensure_ascii=False)
                        return score
            except: pass
            await asyncio.sleep(1)
        return -1.0

async def process_multi_model_item(item_data, client, sem):
    q_id, gt_item, model_file_paths = item_data
    model_entries = {}
    for m_name, path in model_file_paths.items():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                model_entries[m_name] = data[0] if isinstance(data, list) else data
        except: return {'valid': False}

    raw_gold = gt_item.get('answer', gt_item.get('gt_answer', gt_item.get('answers')))
    if isinstance(raw_gold, list): gold_str = "; ".join(map(str, raw_gold))
    elif raw_gold is not None: gold_str = str(raw_gold)
    else: return {'valid': False}

    prompt_base = JUDGE_PROMPT.format(meta_info=gt_item.get('meta_info',''), question=gt_item.get('question',''), golden_answer=gold_str, response="{}")
    
    q_types = gt_item.get('question_type', ['unknown'])
    if isinstance(q_types, str): 
        try: q_types = json.loads(q_types.replace("'", '"'))
        except: q_types = [q_types]

    eval_tasks = []
    model_names_order = list(model_entries.keys())
    for m_name in model_names_order:
        entry = model_entries[m_name]
        path = model_file_paths[m_name]
        prompt = prompt_base.format(entry.get('prediction', '')[:3000])
        eval_tasks.append(evaluate_single(client, prompt, entry, path, sem))

    scores = await asyncio.gather(*eval_tasks)
    
    result_dict = {'valid': True, 'scores': {}, 'types': q_types}
    for idx, score in enumerate(scores):
        if score == -1.0: return {'valid': False}
        result_dict['scores'][model_names_order[idx]] = max(0.0, score)
    return result_dict

# ================= 3. 报表生成核心 (已修改) =================
async def run_async_evaluation():
    start_time = datetime.datetime.now()
    print(f"🚀 Evaluation Started at {start_time.strftime('%H:%M:%S')}")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        if not os.path.exists(GT_FILE): return
        with open(GT_FILE, 'r') as f: gt_map = {str(i['question_id']): i for i in json.load(f)}
        
        tasks = []
        for qid in gt_map:
            model_paths = {}
            all_exist = True
            for m_cfg in MODELS_CONFIG:
                p1 = os.path.join(m_cfg['dir'], qid, m_cfg['file'])
                p2 = os.path.join(m_cfg['dir'], qid, os.path.basename(m_cfg['dir']) + ".json")
                if os.path.exists(p1): model_paths[m_cfg['name']] = p1
                elif os.path.exists(p2): model_paths[m_cfg['name']] = p2
                else: all_exist = False; break
            if all_exist:
                tasks.append((qid, gt_map[qid], model_paths))
                if SAMPLE_LIMIT and len(tasks) >= SAMPLE_LIMIT: break
        
        print(f"✅ Processing {len(tasks)} items...")
        sem = asyncio.Semaphore(CONCURRENCY)
        results = await tqdm_asyncio.gather(*[process_multi_model_item(t, client, sem) for t in tasks], desc="Evaluating")
        
        # --- 数据统计 ---
        global_stats = {m['name']: 0 for m in MODELS_CONFIG}
        type_stats = {}
        total_valid = 0
        
        for res in results:
            if not res or not res['valid']: continue
            total_valid += 1
            scores = res['scores']
            
            # Update Global
            for m, s in scores.items():
                if s == 1.0: global_stats[m] += 1
            
            # Update Types
            for t_raw in res['types']:
                t = str(t_raw)
                if t not in type_stats: type_stats[t] = {'count': 0, 'scores': {m:0 for m in scores}}
                type_stats[t]['count'] += 1
                for m, s in scores.items():
                    if s == 1.0: type_stats[t]['scores'][m] += 1

        if total_valid == 0: return

        # --- 生成横向表格 & CSV 数据 ---
        # 1. 确定模型列顺序（按 Strict Acc 降序）
        sorted_models = sorted(MODELS_CONFIG, key=lambda m: global_stats[m['name']], reverse=True)
        model_cols = [m['name'] for m in sorted_models]
        
        # 准备 CSV 数据容器
        csv_data = []
        
        # 表头
        csv_header = ['Category (Count)'] + model_cols
        csv_data.append(csv_header)
        
        # 终端显示缩略名
        def short_name(n): return n.replace("Qwen", "Qw").replace("LLaVA", "LV")[:10]
        col_headers_console = [short_name(n) for n in model_cols]

        report = []
        report.append("\n" + "="*120)
        report.append(f"🏆 STRICT ACCURACY TABLE (Winner-Takes-All) | Samples: {total_valid}")
        report.append("-" * 120)
        
        # 控制台表头
        header_row = f"{'Category (Count)':<25} | " + " | ".join([f"{h:<10}" for h in col_headers_console])
        report.append(header_row)
        report.append("-" * 120)
        
        # 第一行: Overall
        overall_vals = []
        for m in model_cols:
            acc = global_stats[m] / total_valid
            overall_vals.append(f"{acc:.1%}")
        
        overall_label = f"OVERALL (n={total_valid})"
        
        # 添加到 CSV
        csv_data.append([overall_label] + overall_vals)
        # 添加到 Report
        report.append(f"{overall_label:<25} | " + " | ".join([f"{v:<10}" for v in overall_vals]))
        report.append("-" * 120)
        
        # 后续行: 各类别
        sorted_types = sorted(type_stats.keys())
        for t in sorted_types:
            info = type_stats[t]
            cnt = info['count']
            if cnt == 0: continue
            
            row_vals = []
            for m in model_cols:
                acc = info['scores'][m] / cnt
                row_vals.append(f"{acc:.1%}")
            
            t_label = f"{t} (n={cnt})"
            
            # 添加到 CSV
            csv_data.append([t_label] + row_vals)
            
            # 控制台截断显示
            t_label_short = t_label
            if len(t_label_short) > 25: t_label_short = t_label_short[:22] + "..."
            report.append(f"{t_label_short:<25} | " + " | ".join([f"{v:<10}" for v in row_vals]))

        report.append("="*120 + "\n")
        
        final_log = "\n".join(report)
        print(final_log)
        logger.info(final_log)
        
        # === 导出 CSV 文件 ===
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"evaluation_report_{timestamp}.csv"
        csv_path = os.path.join(SCRIPT_DIR, csv_filename)
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(csv_data)
            print(f"💾 CSV Report Saved to: {csv_path}")
        except Exception as e:
            print(f"❌ Failed to save CSV: {e}")

        # === 打印 TAB 分隔的文本 (方便直接复制到 Excel) ===
        print("\n" + "="*30 + " COPY BELOW TO EXCEL " + "="*30)
        for row in csv_data:
            print("\t".join(row))
        print("="*80 + "\n")

def main():
    try:
        asyncio.run(run_async_evaluation())
    except KeyboardInterrupt: print("\n🛑 Interrupted.")
    except Exception as e: print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
