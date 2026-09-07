#!/usr/bin/env python3
import sys
# [关键修复1] 显式屏蔽 flash_attn，防止触发 GLIBC 错误
sys.modules['flash_attn'] = None 
# [关键修复2] 屏蔽 torchcodec
sys.modules['torchcodec'] = None 

import argparse
import time
import os
import json
import random
import glob
import logging
from datetime import datetime
from tqdm import tqdm
import torch
import numpy as np
from PIL import Image
from transformers import AutoModel, AutoTokenizer

# [显存优化]
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# === 日志配置 ===
def setup_logger(save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
    time_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(save_dir, f'inference_minicpm_{time_str}.log')
    logger = logging.getLogger("Inference")
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger, log_file

def read_json(jpath):
    with open(jpath, 'r', encoding='utf-8') as ff: return json.load(ff)

def get_minicpm_response(model, tokenizer, frames, prompt_text):
    content = frames + [prompt_text]
    msgs = [{'role': 'user', 'content': content}]
    
    # 显存保护：适当减少 max_new_tokens 或调整 max_slice_nums
    res = model.chat(
        image=None,
        msgs=msgs,
        tokenizer=tokenizer,
        sampling=True, 
        temperature=0.7,
        max_new_tokens=512,
        max_slice_nums=1 # 设为1最安全，防止OOM
    )
    return res

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    
    # [正确路径] 指向最里层包含 config.json 的目录
    parser.add_argument('--model_dir', type=str, default='/data1/rmx/projectb/models/MiniCPM-V-2_6/OpenBMB/MiniCPM-V-2_6')
    parser.add_argument('--model_name', type=str, default='MiniCPM-V-2_6')
    parser.add_argument('--result_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/evaluation/results_minicpm')
    
    parser.add_argument('--gpu_id', type=str, default="0")
    parser.add_argument('--shard_id', type=int, default=0)
    parser.add_argument('--num_shards', type=int, default=1)
    parser.add_argument('--start_idx', type=int, default=0)
    parser.add_argument('--end_idx', type=int, default=-1)

    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    
    if not os.path.exists(args.result_dir): os.makedirs(args.result_dir, exist_ok=True)
    logger, log_file_path = setup_logger(args.result_dir)

    logger.info(f"🚀 修正版 MiniCPM 启动 | GPU: {args.gpu_id}")
    logger.info(f"读取模型: {args.model_dir}")

    # 数据准备
    asr_reslts_set = read_json(os.path.join(args.file_dir, 'asr_set.json'))
    raw_test_data = read_json(os.path.join(args.file_dir, 'testset_question.json'))
    
    process_data = raw_test_data[args.start_idx : args.end_idx] if args.end_idx != -1 else raw_test_data[args.start_idx:]
    logger.info(f"📊 任务量: {len(process_data)} (Shard {args.shard_id}/{args.num_shards})")

    # === 模型加载 (GLIBC 修复核心) ===
    try:
        model = AutoModel.from_pretrained(
            args.model_dir, 
            trust_remote_code=True,
            # [修改] 改为 'eager' 以避免调用 flash_attn
            attn_implementation='eager', 
            torch_dtype=torch.bfloat16
        )
        model = model.eval().cuda()
        tokenizer = AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=True)
        logger.info("✅ 模型加载成功 (Eager Mode)")
    except Exception as e:
        logger.error(f"❌ 加载崩溃: {e}")
        exit(1)

    success_count = 0
    error_count = 0

    pbar = tqdm(process_data)
    for i, item in enumerate(pbar):
        if i % args.num_shards != args.shard_id: continue

        video_name = item['video']
        question = item['question']
        question_id = item['question_id']
        pbar.set_description(f"Processing {video_name[:10]}...")

        output_dir = os.path.join(args.result_dir, question_id)
        output_file = os.path.join(output_dir, f'{args.model_name}.json')
        if os.path.exists(output_file): continue # 简单跳过

        try:
            frame_folder = os.path.join(args.frames_dir, video_name)
            if not os.path.exists(frame_folder):
                error_count += 1; continue

            images_paths = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
            if not images_paths: error_count += 1; continue
            
            frames = []
            for img_p in images_paths:
                try: frames.append(Image.open(img_p).convert("RGB"))
                except: continue
            
            if not frames: continue

            asr = asr_reslts_set.get(video_name + '.mp4', '')
            input_prompt = f"{'Voiceover: '+asr if asr else ''}\n\nBy watching the video, you are required to answer a question within 30 words: Question: {question}"
            
            start_time = time.time()
            pred = get_minicpm_response(model, tokenizer, frames, input_prompt)
            duration = time.time() - start_time

            if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as ff:
                json.dump([{"prediction": pred, "score": ""}], ff, ensure_ascii=False, indent=4)
            
            success_count += 1
            logger.info(f"✅ 完成: {question_id} | 耗时: {duration:.2f}s")

        except Exception as ex:
            error_count += 1
            logger.error(f"❌ 异常 {question_id}: {str(ex)}")
            torch.cuda.empty_cache()

    logger.info(f"🎉 结束 | 成功: {success_count} | 失败: {error_count}")