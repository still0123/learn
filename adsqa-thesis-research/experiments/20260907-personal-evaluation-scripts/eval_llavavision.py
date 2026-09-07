#!/usr/bin/env python3
import sys
# [兼容性修复] 显式屏蔽 torchcodec
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

# [模型适配] 引入 LLaVA-OneVision 相关的 Auto 类
from transformers import AutoProcessor, LlavaOnevisionForConditionalGeneration

# [显存优化]
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# === 日志配置 ===
def setup_logger(save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
    
    time_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(save_dir, f'inference_run_{time_str}.log')

    logger = logging.getLogger("Inference")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger, log_file

def read_json(jpath):
    with open(jpath, 'r', encoding='utf-8') as ff:
        data = json.load(ff)
    return data

def set_random_seed(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    random.seed(seed)
    np.random.seed(seed)
    return seed

# === 推理核心函数 (适配 LLaVA-OneVision) ===
def get_llava_response(model, processor, frames, prompt_text):
    # LLaVA-OneVision HF 格式：
    # conversation = [{"role": "user", "content": [{"type": "video"}, {"type": "text", "text": "..."}]}]
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "video"},
                {"type": "text", "text": prompt_text},
            ],
        },
    ]

    # 应用 Chat Template
    text_prompt = processor.apply_chat_template(conversation, add_generation_prompt=True)

    # 预处理
    # LLaVA-OneVision 处理视频时，直接传入 PIL Image 列表给 videos 参数
    inputs = processor(
        videos=[frames],  # 注意这里需要包一层 list，表示 batch_size=1 的视频
        text=text_prompt,
        padding=True,
        return_tensors="pt"
    )

    inputs = inputs.to("cuda")

    # 生成
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            do_sample=True,
            temperature=0.7, 
            top_p=0.9,
            max_new_tokens=512  # LLaVA 回答通常较短，视情况调整
        )

    # 解码
    # generated_ids 包含了 input_ids，需要截断
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    
    return output_text[0].strip()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    # === 关键路径 ===
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8', help='视频帧文件夹路径')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    
    # [修改] 默认路径指向 LLaVA-OneVision
    parser.add_argument('--model_dir', type=str, default='/data1/rmx/projectb/models/llava-onevision-qwen2-7b-ov-hf')
    parser.add_argument('--model_name', type=str, default='llava-onevision-qwen2-7b-ov-hf')
    
    parser.add_argument('--result_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/evaluation/results_llava_ov')
    
    # === 运行控制 ===
    parser.add_argument('--gpu_id', type=str, default="0")
    parser.add_argument('--start_idx', type=int, default=0)
    parser.add_argument('--end_idx', type=int, default=-1)
    parser.add_argument('--shard_id', type=int, default=0)
    parser.add_argument('--num_shards', type=int, default=1)
    parser.add_argument('--reverse', action='store_true')

    args = parser.parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    
    if not os.path.exists(args.result_dir):
        os.makedirs(args.result_dir, exist_ok=True)
    logger, log_file_path = setup_logger(args.result_dir)

    logger.info("="*50)
    logger.info(f"🚀 LLaVA-OneVision 推理启动 | GPU: {args.gpu_id}")
    logger.info(f"模型路径: {args.model_dir}")
    
    set_random_seed(42)

    # 读取数据
    asr_path = os.path.join(args.file_dir, 'asr_set.json')
    question_path = os.path.join(args.file_dir, 'testset_question.json')
    
    if not os.path.exists(question_path):
        logger.error(f"❌ 找不到文件: {question_path}")
        exit(1)

    asr_reslts_set = read_json(asr_path)
    raw_test_data = read_json(question_path)

    # 数据切片
    total_len = len(raw_test_data)
    end_idx = args.end_idx if args.end_idx != -1 else total_len
    process_data = raw_test_data[args.start_idx : end_idx]
    
    logger.info(f"📊 任务范围: {args.start_idx} -> {end_idx} (Total: {total_len})")

    # === 模型加载 ===
    logger.info(f"加载模型中... {args.model_dir}")
    try:
        # 使用 LlavaOnevisionForConditionalGeneration 加载
        model = LlavaOnevisionForConditionalGeneration.from_pretrained(
            args.model_dir, 
            torch_dtype=torch.bfloat16, 
            device_map="auto",
            attn_implementation="flash_attention_2" # 推荐开启
        )
        processor = AutoProcessor.from_pretrained(args.model_dir)
        logger.info("✅ LLaVA-OneVision 模型加载成功")
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        logger.warning("尝试回退 Eager Attention...")
        try:
             model = LlavaOnevisionForConditionalGeneration.from_pretrained(
                args.model_dir, 
                torch_dtype=torch.bfloat16, 
                device_map="auto"
            )
             processor = AutoProcessor.from_pretrained(args.model_dir)
        except Exception as e2:
             logger.error(f"❌ 重试失败: {e2}")
             exit(1)

    success_count = 0
    error_count = 0

    pbar = tqdm(process_data)
    for i, item in enumerate(pbar):
        # 分片逻辑
        if i % args.num_shards != args.shard_id:
            continue

        video_name = item['video']
        question = item['question']
        question_id = item['question_id']

        pbar.set_description(f"Processing {video_name[:10]}...")

        asr = asr_reslts_set.get(video_name + '.mp4', '')
        if asr != '':
            asr = f"Voiceover: {asr}\n"

        output_dir = os.path.join(args.result_dir, question_id)
        output_file = os.path.join(output_dir, f'{args.model_name}.json')

        try:
            # === 读取视频帧 (PIL Image) ===
            frame_folder = os.path.join(args.frames_dir, video_name)
            
            if not os.path.exists(frame_folder):
                error_count += 1
                continue

            images_paths = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
            
            if not images_paths:
                error_count += 1
                continue
            
            # LLaVA-OV 需要 PIL Image 对象列表
            frames = []
            for img_p in images_paths:
                try:
                    frames.append(Image.open(img_p).convert("RGB"))
                except:
                    continue
            
            if not frames:
                continue

            # === 构造 Prompt ===
            input_question = f"{asr}\n\nBy watching the video, you are required to answer a question within 30 words: Question: {question}"
            
            start_time = time.time()
            
            # 推理
            pred = get_llava_response(model, processor, frames, input_question)
            
            duration = time.time() - start_time

            # 保存
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            res = [{"prediction": pred, "score": ""}]
            with open(output_file, 'w', encoding='utf-8') as ff:
                json.dump(res, ff, ensure_ascii=False, indent=4)
            
            success_count += 1
            logger.info(f"✅ 完成: {question_id} | 耗时: {duration:.2f}s")

        except Exception as ex:
            error_count += 1
            logger.error(f"❌ 异常 {question_id}: {str(ex)}")
            if "out of memory" in str(ex).lower():
                import gc
                gc.collect()
                torch.cuda.empty_cache()

    logger.info("="*50)
    logger.info(f"🎉 任务结束 | 成功: {success_count} | 失败: {error_count}")
    logger.info(f"📄 日志: {log_file_path}")