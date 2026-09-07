#!/usr/bin/env python3
import sys
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
from qwen_vl_utils import process_vision_info
from transformers import AutoModelForVision2Seq, AutoProcessor
import torch
import numpy as np

# [显存优化] 虽然显存够，但开启这个能防碎片化
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

def setup_logger(save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
    time_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(save_dir, f'retry_full_{time_str}.log')
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
    with open(jpath, 'r', encoding='utf-8') as ff:
        return json.load(ff)

def get_qwen2vl_response(model, processor, image_inputs, video_inputs, inputs_text, video_kwargs):
    inputs = processor(
        text=[inputs_text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
        **video_kwargs,
    )
    inputs = inputs.to("cuda")
    with torch.no_grad():
        generated_ids = model.generate(**inputs, do_sample=True, temperature=0.7, max_new_tokens=1524)
    
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
    return seed

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    
    # 路径参数
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    parser.add_argument('--model_dir', type=str, default='/data1/qky/Model/QWen3VL')
    parser.add_argument('--model_name', type=str, default='Qwen3-VL-Instruct')
    parser.add_argument('--result_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_baseline')
    
    # 重跑专用参数
    parser.add_argument('--retry_file', type=str, default='retry_list.json', help='指定要重跑的列表文件')
    
    # 控制参数
    parser.add_argument('--gpu_id', type=str, default="0")
    parser.add_argument('--shard_id', type=int, default=0)
    parser.add_argument('--num_shards', type=int, default=1)
    parser.add_argument('--start_idx', type=int, default=0)
    parser.add_argument('--end_idx', type=int, default=-1)

    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    
    if not os.path.exists(args.result_dir):
        os.makedirs(args.result_dir, exist_ok=True)
    logger, log_file_path = setup_logger(args.result_dir)

    logger.info("="*50)
    logger.info(f"🚀 全量帧重跑模式 (无降采样) | GPU: {args.gpu_id}")
    set_random_seed(42)

    # 读取辅助数据
    asr_reslts_set = read_json(os.path.join(args.file_dir, 'asr_set.json'))

    # [逻辑修改] 读取重跑列表
    if os.path.exists(args.retry_file):
        logger.info(f"📂 读取重跑列表: {args.retry_file}")
        process_data = read_json(args.retry_file)
    else:
        logger.warning("⚠️ 找不到重跑列表，将读取全量数据！")
        process_data = read_json(os.path.join(args.file_dir, 'testset_question.json'))

    # 如果需要切片
    total_len = len(process_data)
    if args.end_idx != -1:
        process_data = process_data[args.start_idx : args.end_idx]
    
    logger.info(f"📊 任务数量: {len(process_data)} (分片: {args.shard_id}/{args.num_shards})")

    logger.info(f"加载模型... {args.model_dir}")
    try:
        model = AutoModelForVision2Seq.from_pretrained(
            args.model_dir, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
        )
        processor = AutoProcessor.from_pretrained(args.model_dir, trust_remote_code=True)
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}"); exit(1)

    last_video_name = ""
    cached_vision_info = None
    success_count = 0
    error_count = 0

    pbar = tqdm(process_data)
    for i, item in enumerate(pbar):
        # 分片逻辑
        if i % args.num_shards != args.shard_id: continue

        video_name = item['video']
        question = item['question']
        question_id = item['question_id']
        pbar.set_description(f"Retrying {video_name[:10]}...")

        asr = asr_reslts_set.get(video_name + '.mp4', '')
        if asr: asr = f"Voiceover: {asr}\n"

        output_dir = os.path.join(args.result_dir, question_id)
        output_file = os.path.join(output_dir, f'{args.model_name}.json')

        try:
            frame_folder = os.path.join(args.frames_dir, video_name)
            if not os.path.exists(frame_folder):
                error_count += 1; continue

            if last_video_name != video_name:
                images = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
                if not images: error_count += 1; continue
                
                # [关键] 这里没有任何降采样逻辑，直接全部塞入
                content_list = []
                for img_path in images:
                    content_list.append({"type": "image", "image": img_path})
                content_list.append({"type": "text", "text": "PLACEHOLDER"})
                
                messages = [{"role": "user", "content": content_list}]
                cached_vision_info = process_vision_info(messages)
                last_video_name = video_name

            image_inputs, video_inputs = cached_vision_info
            
            input_question = f"{asr}\n\nBy watching the video, you are required to answer a question within 30 words: Question: {question}"
            current_messages = [
                {
                    "role": "user",
                    "content": [{"type": "image", "image": "placeholder"} for _ in range(len(image_inputs))] + [{"type": "text", "text": input_question}]
                }
            ]
            
            inputs_text = processor.apply_chat_template(current_messages, tokenize=False, add_generation_prompt=True)
            
            start_time = time.time()
            # 推理
            pred = get_qwen2vl_response(model, processor, image_inputs, video_inputs, inputs_text, {})
            duration = time.time() - start_time

            if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as ff:
                json.dump([{"prediction": pred, "score": ""}], ff, ensure_ascii=False, indent=4)
            
            success_count += 1
            logger.info(f"✅ 完成: {question_id} | 耗时: {duration:.2f}s")

        except Exception as ex:
            error_count += 1
            logger.error(f"❌ 异常 {question_id}: {str(ex)}")
            if "out of memory" in str(ex).lower():
                import gc; gc.collect(); torch.cuda.empty_cache()

    logger.info(f"🎉 结束 | 成功: {success_count} | 失败: {error_count}")