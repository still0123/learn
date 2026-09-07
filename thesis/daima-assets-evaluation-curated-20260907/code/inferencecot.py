import sys
sys.modules['torchcodec'] = None 

import os
import argparse
import time
import json
import random
import glob
import math
import gc
import torch
import numpy as np
from tqdm import tqdm
from qwen_vl_utils import process_vision_info
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

def read_json(jpath):
    with open(jpath, 'r', encoding='utf-8') as ff:
        data = json.load(ff)
    return data

def get_qwen2vl_response(model, processor, inputs):
    inputs = inputs.to("cuda")
    with torch.no_grad():
        generated_ids = model.generate(**inputs,
                                       do_sample=True,
                                       temperature=1.0,
                                       # [修改点1] CoT 需要更长的生成长度来容纳思考过程
                                       max_new_tokens=2048) 
    
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
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    
    # 模型路径 (保持不变)
    parser.add_argument('--model_dir', type=str, default='/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct')
    parser.add_argument('--model_name', type=str, default='Qwen2.5-VL-7B-Instruct')
    
    # [修改点2] 输出目录改为 CoT 结果目录
    parser.add_argument('--result_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/evaluation/results_cot_baseline')
    
    parser.add_argument("--rank", type=int, default=0)
    parser.add_argument("--world_size", type=int, default=1)
    
    args = parser.parse_args()
    set_random_seed(42)
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    asr_path = os.path.join(args.file_dir, 'asr_set.json')
    question_path = os.path.join(args.file_dir, 'testset_question.json')
    asr_reslts_set = read_json(asr_path)
    full_test_data = read_json(question_path)
    
    # 切分逻辑
    total_len = len(full_test_data)
    chunk_size = math.ceil(total_len / args.world_size)
    start_idx = args.rank * chunk_size
    end_idx = min(start_idx + chunk_size, total_len)
    my_test_data = full_test_data[start_idx:end_idx]
    
    print(f"[Rank {args.rank}] Loading Model for CoT Baseline...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            args.model_dir, torch_dtype="auto", device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(args.model_dir)

    if not os.path.exists(args.result_dir):
        os.makedirs(args.result_dir, exist_ok=True)

    # [修改点3] 定义 CoT Prompt 模板 (参考论文 Table 8)
    # 强制模型分两步走：1. <think>思考, 2. <answer>回答
    cot_instruction = (
        "Analyze the provided video and voiceover (if present) to perform step-by-step reasoning. "
        "Structure your output as follows:\n"
        "1. Chain-of-Thought (CoT): Enclose detailed reasoning in <think> tags, covering key visual/audio cues, logical connections, and deductions.\n"
        "2. Final Answer: Provide a concise answer which answers the given question (less than 30 words) in <answer> tags."
    )

    for ii, item in enumerate(tqdm(my_test_data, desc=f"Rank {args.rank}")):
        video_name = item['video']
        question = item['question']
        question_id = item['question_id']

        # 检查是否已跑过
        output_file_path = os.path.join(args.result_dir, question_id, f'{args.model_name}.json')
        if os.path.exists(output_file_path):
            continue

        asr = asr_reslts_set.get(video_name + '.mp4', '')
        if asr: asr = f"Voiceover: {asr}\n"

        try:
            frame_folder = os.path.join(args.frames_dir, video_name)
            if not os.path.exists(frame_folder):
                alt_folder = os.path.join(args.frames_dir, video_name.replace('.mp4', ''))
                if os.path.exists(alt_folder): frame_folder = alt_folder
                else: continue

            image_paths = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))[:8]
            if not image_paths: continue

            content_list = []
            for img_path in image_paths:
                content_list.append({"type": "image", "image": img_path, "max_pixels": 360*420*4})
            
            content_list.append({"type": "text", "text": "PLACEHOLDER"})
            messages = [{"role": "user", "content": content_list}]
            image_inputs, video_inputs = process_vision_info(messages)
            
            # [修改点4] 组装 CoT Prompt
            full_prompt = f"{asr}\n{cot_instruction}\n\nQuestion: {question}"
            messages[0]['content'][-1]['text'] = full_prompt

            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")

            pred = get_qwen2vl_response(model, processor, inputs)

            # 保存
            save_dir = os.path.join(args.result_dir, question_id)
            os.makedirs(save_dir, exist_ok=True)
            
            # 保存完整结果 (包含 think 和 answer)
            res = [{"prediction": pred, "type": "CoT"}]
            with open(output_file_path, 'w', encoding='utf-8') as ff:
                json.dump(res, ff, ensure_ascii=False, indent=4)

        except Exception as ex:
            print(f"Error {video_name}: {ex}")
            if "out of memory" in str(ex).lower():
                gc.collect(); torch.cuda.empty_cache()