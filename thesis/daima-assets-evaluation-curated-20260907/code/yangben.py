import json
import os
import pandas as pd
import re
import random
from collections import Counter

# ================= 配置区域 =================

# 1. GT 文件路径
GT_FILE_PATH = "/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json"

# 2. 模型结果路径
MODEL_PATHS = {
    "SOTA": "/data1/rmx/projectb/AdsQA-main/evaluation/results",
    "Ours": "/data1/rmx/projectb/AdsQA-main/evaluation/163qwen3_rich_prompt",
    "LLaVA-OV": "/data1/rmx/projectb/AdsQA-main/evaluation/results_llava_ov",
    "MiniCPM": "/data1/rmx/projectb/AdsQA-main/evaluation/results_minicpm",
    "Qwen3-Base": "/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_baseline",
}

# 3. 输出文件
OUTPUT_FILE = "score1_cleaned_comparison.xlsx"

# 4. 采样数量
NUM_SAMPLES = 50       

# ================= 核心逻辑 (已针对您的格式修改) =================

def parse_prediction(text):
    """
    智能解析函数：
    1. 支持 <think>...</answer> 标签格式
    2. 支持 [Observation]... [Answer]: 结构化格式 (您的新格式)
    """
    if not isinstance(text, str): return "", str(text)
    
    # --- 情况 A: 包含 [Answer]: 的结构化格式 (您提供的例子) ---
    # 查找 [Answer]: (不区分大小写)
    if "[Answer]:" in text or "[answer]:" in text:
        # 使用正则找到 [Answer]: 的位置
        match = re.search(r"\[Answer\]:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        if match:
            ans_content = match.group(1).strip()
            # [Answer] 之前的内容归为 Think (包含 Observation 和 Reasoning)
            think_content = text[:match.start()].strip()
            return think_content, ans_content

    # --- 情况 B: 标准 XML 标签格式 ---
    if "<answer>" in text or "<think>" in text:
        think_match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        answer_match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)
        think = think_match.group(1).strip() if think_match else ""
        ans = answer_match.group(1).strip() if answer_match else text.replace("Answer:", "").strip()
        return think, ans.replace("\n", " ").strip()
    
    # --- 情况 C: 兜底 (没有标签) ---
    # 尝试移除 "Answer:" 前缀
    return "", text.replace("Answer:", "").strip()

def parse_score(score_raw):
    """解析分数，返回 0 或 1"""
    if isinstance(score_raw, int): return score_raw
    text = str(score_raw)
    match = re.search(r'\b(0|1)\b', text)
    return int(match.group(1)) if match else 0

def load_json_map(path, key_field="question_id"):
    """智能加载: 兼容文件和目录扫描"""
    result_map = {}
    if not os.path.exists(path): return {}

    if os.path.isdir(path):
        print(f"   📂 扫描目录: {path} ...")
        for folder_name in os.listdir(path):
            sub_folder = os.path.join(path, folder_name)
            if os.path.isdir(sub_folder):
                for filename in os.listdir(sub_folder):
                    if filename.endswith(".json"):
                        try:
                            with open(os.path.join(sub_folder, filename), 'r', encoding='utf-8') as f:
                                raw = json.load(f)
                                # 处理 list 或 dict
                                item = raw[0] if isinstance(raw, list) and raw else raw if isinstance(raw, dict) else {}
                                if not item: continue
                                qid = str(item.get(key_field, folder_name))
                                result_map[qid] = item
                                break # 找到一个就行
                        except: continue
    elif os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if str(item.get(key_field, "")): result_map[str(item[key_field])] = item
            elif isinstance(data, dict):
                for k, v in data.items():
                    result_map[str(k)] = v
        except: pass
    
    return result_map

def main():
    print(f"📖 读取 GT: {GT_FILE_PATH}")
    gt_map = load_json_map(GT_FILE_PATH)
    all_qids = list(gt_map.keys())
    
    # 加载模型数据
    models_data = {}
    for name, path in MODEL_PATHS.items():
        print(f"🔹 加载模型: {name}...")
        models_data[name] = load_json_map(path)

    if "Ours" not in models_data:
        print("❌ 错误: MODEL_PATHS 中必须包含 'Ours'！")
        return

    # --- 筛选逻辑: Ours Score=1 ---
    print("🔍 正在筛选 Ours 回答正确 (Score=1) 的样本...")
    valid_qids = []
    ours_data = models_data["Ours"]
    
    for qid in all_qids:
        item = ours_data.get(qid, {})
        # 获取 score (兼容字段名: score, rating)
        raw_score = item.get("score", item.get("rating", 0))
        
        if parse_score(raw_score) == 1:
            valid_qids.append(qid)
            
    print(f"   ✨ 找到 {len(valid_qids)} 个满分样本。")

    # --- 排序逻辑: 按视频聚合 ---
    qid_to_vid = {}
    video_counter = Counter()
    for qid in valid_qids:
        gt_item = gt_map.get(qid, {})
        vid = gt_item.get("video", gt_item.get("video_id", "unknown"))
        qid_to_vid[qid] = vid
        video_counter[vid] += 1
        
    # 优先展示问题多的视频 (Cluster Size)
    sorted_qids = sorted(valid_qids, key=lambda q: (-video_counter[qid_to_vid[q]], qid_to_vid[q], q))
    target_qids = sorted_qids[:NUM_SAMPLES]

    # --- 导出 ---
    rows = []
    print("⚙️ 生成表格...")
    
    for qid in target_qids:
        gt_item = gt_map[qid]
        vid = gt_item.get("video", gt_item.get("video_id", ""))
        
        row = {
            "Cluster Size": video_counter[vid],
            "Question ID": qid,
            "Video": vid,
            "Question": gt_item.get("question", ""),
            "Ground Truth": gt_item.get("answer", gt_item.get("gt_answer", ""))
        }
        
        # 记录 Ours 分数
        ours_item = models_data["Ours"].get(qid, {})
        row["Ours Score"] = str(ours_item.get("score", ""))

        for model_name, m_data in models_data.items():
            val = m_data.get(qid, {})
            raw = val.get("prediction", "") if isinstance(val, dict) else str(val)
            if not raw and val and isinstance(val, str): raw = val
            if not raw: raw = "N/A"

            # 解析 Think 和 Ans
            think, ans = parse_prediction(raw)
            row[f"{model_name} (Think)"] = think
            row[f"{model_name} (Ans)"] = ans
        
        rows.append(row)

    df = pd.DataFrame(rows)
    try:
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"\n✨ 成功！已保存至: {OUTPUT_FILE}")
        print("   ✅ Ours (Ans) 列现在只包含 [Answer]: 之后的内容。")
        print("   ✅ 之前的 Observation/Reasoning 已移动到 Ours (Think) 列。")
    except:
        csv_file = OUTPUT_FILE.replace("xlsx", "csv")
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"⚠️ 保存为 CSV: {csv_file}")

if __name__ == "__main__":
    main()