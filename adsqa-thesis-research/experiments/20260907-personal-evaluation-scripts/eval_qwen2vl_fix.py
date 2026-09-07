#!/usr/bin/env python3
import sys
# [关键修复] 强行屏蔽 flash_attn，防止 GLIBC 报错
sys.modules['flash_attn'] = None 
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

from qwen_vl_utils import process_vision_info
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

# [显存优化]
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# === 日志配置 ===
def setup_logger(save_dir):
    if not os.path.exists(save_dir): os.makedirs(save_dir, exist_ok=True)
    time_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(save_dir, f'inference_qwen2vl_{time_str}.log')

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    
    # 指向您截图中的正确路径
    parser.add_argument('--model_dir', type=str, default='/data1/rmx/projectb/models/Qwen2-VL-7B-Instruct')
    parser.add_argument('--model_name', type=str, default='Qwen2-VL-7B-Instruct')
    parser.add_argument('--result_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen2vl')
    
    parser.add_argument('--gpu_id', type=str, default="0")
    parser.add_argument('--start_idx', type=int, default=0)
    parser.add_argument('--end_idx', type=int, default=-1)
    parser.add_argument('--shard_id', type=int, default=0)
    parser.add_argument('--num_shards', type=int, default=1)

    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    
    if not os.path.exists(args.result_dir): os.makedirs(args.result_dir, exist_ok=True)
    logger, log_file_path = setup_logger(args.result_dir)

    logger.info(f"🚀 Qwen2-VL-7B (Eager Mode) 启动 | GPU: {args.gpu_id}")
    
    # 读取数据
    asr_reslts_set = read_json(os.path.join(args.file_dir, 'asr_set.json'))
    raw_test_data = read_json(os.path.join(args.file_dir, 'testset_question.json'))
    
    # 简单的任务范围计算
    process_data = raw_test_data[args.start_idx : args.end_idx] if args.end_idx != -1 else raw_test_data[args.start_idx:]
    logger.info(f"📊 任务量: {len(process_data)} (Shard {args.shard_id}/{args.num_shards})")

    # === 加载模型 (核心修复) ===
    try:
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            args.model_dir, 
            torch_dtype="auto", 
            device_map="auto",
            # [强制修改] 使用 eager 模式，避开 GLIBC 问题
            attn_implementation="eager" 
        )
        # 显式指定像素限制
        processor = AutoProcessor.from_pretrained(args.model_dir, min_pixels=256*28*28, max_pixels=1280*28*28)
        logger.info("✅ Qwen2-VL 模型加载成功")
    except Exception as e:
        logger.error(f"❌ 加载失败: {e}")
        exit(1)

    cached_vision_info = None
    last_video_name = ""
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
        if os.path.exists(output_file): continue

        try:
            frame_folder = os.path.join(args.frames_dir, video_name)
            if not os.path.exists(frame_folder):
                error_count += 1; continue

            if last_video_name != video_name:
                images = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
                if not images: error_count += 1; continue
                
                content_list = [{"type": "image", "image": img} for img in images]
                content_list.append({"type": "text", "text": "PLACEHOLDER"})
                
                messages = [{"role": "user", "content": content_list}]
                cached_vision_info = process_vision_info(messages)
                last_video_name = video_name
            
            image_inputs, video_inputs = cached_vision_info
            
            asr = asr_reslts_set.get(video_name + '.mp4', '')
            input_prompt = f"{'Voiceover: '+asr if asr else ''}\nBy watching the video, answer the question within 30 words: {question}"
            
            current_messages = [
                {
                    "role": "user",
                    "content": [{"type": "image", "image": "placeholder"} for _ in range(len(image_inputs))] + [{"type": "text", "text": input_prompt}]
                }
            ]
            inputs_text = processor.apply_chat_template(current_messages, tokenize=False, add_generation_prompt=True)

            inputs = processor(
                text=[inputs_text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
            ).to(model.device)

            with torch.no_grad():
                generated_ids = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.7)
            
            generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
            pred = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

            if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as ff:
                json.dump([{"prediction": pred, "score": ""}], ff, indent=4)
            
            success_count += 1
            logger.info(f"✅ 完成: {question_id}")

        except Exception as ex:
            error_count += 1
            logger.error(f"❌ 异常 {question_id}: {ex}")
            torch.cuda.empty_cache()

    logger.info(f"🎉 结束 | 成功: {success_count} | 失败: {error_count}")