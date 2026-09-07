import json
import os
from pathlib import Path

# === 配置: 请确认路径正确 ===
RESULT_DIR = '/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_baseline'
QUESTION_FILE = '/data1/rmx/projectb/AdsQA-main/data/testset_question.json'
SAVE_FILE = os.path.abspath("retry_list.json") # 生成绝对路径
# ===========================

def main():
    print("正在扫描失败样本...")
    with open(QUESTION_FILE, 'r') as f:
        all_data = json.load(f)
    
    retry_list = []
    for item in all_data:
        qid = item['question_id']
        # 检查结果文件是否存在且有内容
        fpath = Path(RESULT_DIR) / qid / 'Qwen3-VL-Instruct.json'
        if not (fpath.exists() and fpath.stat().st_size > 10):
            retry_list.append(item)

    print(f"❌ 需要重跑的数量: {len(retry_list)}")
    
    if len(retry_list) > 0:
        with open(SAVE_FILE, 'w') as f:
            json.dump(retry_list, f, indent=2)
        print(f"✅ 列表已保存至绝对路径: {SAVE_FILE}")
    else:
        print("🎉 没有需要重跑的样本！")

if __name__ == "__main__":
    main()