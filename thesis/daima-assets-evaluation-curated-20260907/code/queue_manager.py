import time
import subprocess
import os
import datetime

# === 配置区域 ===
# 1. 正在运行的脚本名 (等待它结束)
WAIT_FOR_SCRIPT = "eval_adQA_qwen2vl-7b.py"

# 2. 接下来要运行的脚本 (Qwen3)
NEXT_SCRIPT_PATH = "/data1/rmx/projectb/AdsQA-main/evaluation/inference_163qwen3xiugairelax2.py"

def is_process_running(script_name):
    """检查指定脚本是否还在运行"""
    try:
        # 使用 pgrep -f 查找包含脚本名的进程
        subprocess.check_output(f"pgrep -f {script_name}", shell=True)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print(f"[{datetime.datetime.now()}] 👀 守夜模式 (无锁版) 开启...")
    print(f"🎯 目标: 等待 {WAIT_FOR_SCRIPT} 结束 -> 启动 Qwen3 任务")
    
    # === 1. 循环等待 ===
    while is_process_running(WAIT_FOR_SCRIPT):
        print(f"[{datetime.datetime.now()}] ⏳ 正在等待当前任务结束...", flush=True)
        time.sleep(60) # 每分钟检查一次
        
    print(f"[{datetime.datetime.now()}] ✨ 前序任务已结束！")
    print(f"🚀 正在启动下一轮任务: {NEXT_SCRIPT_PATH}")
    
    # === 2. 启动 GPU 2 任务 (Shard 0) ===
    cmd_gpu2 = (
        f"CUDA_VISIBLE_DEVICES=2 nohup python3 {NEXT_SCRIPT_PATH} "
        f"--gpu_id 2 --shard_id 0 --num_shards 2 --start_idx 0 --end_idx -1 "
        f"> logs/auto_relax2_gpu2.log 2>&1 &"
    )
    print(f"执行 GPU 2: {cmd_gpu2}")
    os.system(cmd_gpu2)

    # === 3. 启动 GPU 3 任务 (Shard 1) ===
    cmd_gpu3 = (
        f"CUDA_VISIBLE_DEVICES=3 nohup python3 {NEXT_SCRIPT_PATH} "
        f"--gpu_id 3 --shard_id 1 --num_shards 2 --start_idx 0 --end_idx -1 "
        f"> logs/auto_relax2_gpu3.log 2>&1 &"
    )
    print(f"执行 GPU 3: {cmd_gpu3}")
    os.system(cmd_gpu3)

    print(f"[{datetime.datetime.now()}] ✅ 所有任务已自动挂起。")

if __name__ == "__main__":
    main()