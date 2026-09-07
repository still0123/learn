#!/usr/bin/env python3
import sys
# [关键修正] 显式屏蔽 torchcodec，防止某些环境下的兼容性报错
sys.modules['torchcodec'] = None 

import argparse
import time
import os
import json
import random
import glob
import math
from tqdm import tqdm
from qwen_vl_utils import process_vision_info
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
import torch
import numpy as np

# 显存优化：启用扩展段以减少碎片
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

def read_json(jpath):
    with open(jpath, 'r', encoding='utf-8') as ff:
        data = json.load(ff)
    return data

def get_qwen2vl_response(model, processor, image_inputs, inputs_text):
    inputs = processor(
        text=[inputs_text],
        images=image_inputs,
        videos=None,
        padding=True,
        return_tensors="pt",
    )
    # 这里的 "cuda" 会自动映射到 CUDA_VISIBLE_DEVICES 设置的设备
    inputs = inputs.to("cuda")
    with torch.no_grad():
        generated_ids = model.generate(**inputs,
                                       do_sample=True,
                                       temperature=1,
                                       max_new_tokens=1524)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_text[0].strip()

def set_random_seed(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    random.seed(seed)
    np.random.seed(seed)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # === 路径参数 ===
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    parser.add_argument('--model_dir', type=str, default='/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R')
    parser.add_argument('--model_name', type=str, default='Qwen2.5-7B-VL-ReAd-R')
    parser.add_argument('--result_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/evaluation/results')
    
    # === 运行控制参数 ===
    parser.add_argument('--gpu_id', type=str, default="1", help='指定GPU ID')
    parser.add_argument('--start_idx', type=int, default=0, help='开始索引')
    parser.add_argument('--end_idx', type=int, default=-1, help='结束索引 (-1代表到最后)')
    parser.add_argument('--reverse', action='store_true', help='是否倒序运行')

    args = parser.parse_args()

    # [关键] 设置当前进程可见的 GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    print(f"🚀 Running on GPU {args.gpu_id}")

    set_random_seed(42)

    # 读取数据
    asr_reslts_set = read_json(os.path.join(args.file_dir, 'asr_set.json'))
    raw_test_data = read_json(os.path.join(args.file_dir, 'testset_question.json'))
    
    # 数据切片
    total_len = len(raw_test_data)
    end_idx = args.end_idx if args.end_idx != -1 else total_len
    
    process_data = raw_test_data[args.start_idx : end_idx]
    
    # 倒序处理逻辑
    if args.reverse:
        process_data = process_data[::-1]
        print(f"🔄 Reverse mode ON. Processing from index {end_idx} down to {args.start_idx}")
    else:
        print(f"▶️ Normal mode. Processing from index {args.start_idx} to {end_idx}")

    print(f"📊 Task Load: {len(process_data)} items")

    # 加载模型
    print(f"Loading model from: {args.model_dir}")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            args.model_dir, torch_dtype="auto", device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(args.model_dir)

    if not os.path.exists(args.result_dir):
        os.makedirs(args.result_dir, exist_ok=True)

    # 推理循环
    for ii, item in enumerate(tqdm(process_data)):
        video_name = item['video']
        question = item['question']
        question_id = item['question_id']

        asr = asr_reslts_set.get(video_name + '.mp4', '')
        if asr != '':
            asr = f"Voiceover: {asr}\n"

        output_dir = os.path.join(args.result_dir, question_id)
        output_file = os.path.join(output_dir, f'{args.model_name}.json')
        
        # 断点续传：跳过已存在的结果
        if os.path.exists(output_file):
            continue

        try:
            frame_folder = os.path.join(args.frames_dir, video_name)
            if not os.path.exists(frame_folder):
                continue

            images = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
            if not images:
                continue

            # 均匀采样 8 帧
            total_frames = len(images)
            target_frames = 8
            if total_frames > target_frames:
                indices = np.linspace(0, total_frames - 1, target_frames, dtype=int)
                selected_images = [images[i] for i in indices]
            else:
                selected_images = images

            content_list = []
            for img_path in selected_images:
                content_list.append({
                    "type": "image",
                    "image": img_path,
                    "max_pixels": 360 * 420 * 4, 
                })
            content_list.append({"type": "text", "text": "PLACEHOLDER"})

            messages = [{"role": "user", "content": content_list}]
            image_inputs, video_inputs = process_vision_info(messages)

            input_question = f"{asr}\n\n Question: {question}\n\nYou are permitted to gather any relevant clues, think step by step, to answer this question. Output your thought process (no length limit) and the final answer (using approximately 30 words; longer answers will be truncated) in the following format\n <think>your_thinking</think> <answer>your_answer_within_30_words</answer>"
            
            messages[0]['content'][-1]['text'] = input_question
            
            inputs_text = processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            pred = get_qwen2vl_response(model, processor, image_inputs, inputs_text)

            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            res = [{"prediction": pred, "score": ""}]
            with open(output_file, 'w', encoding='utf-8') as ff:
                json.dump(res, ff, ensure_ascii=False, indent=4)

        except Exception as ex:
            print(f"Error processing {video_name}: {ex}")
            if "out of memory" in str(ex).lower():
                import gc
                gc.collect()
                torch.cuda.empty_cache()