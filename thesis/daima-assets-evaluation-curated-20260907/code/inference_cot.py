#!/usr/bin/env python3
"""
AdsQA CoT + Reflection Inference (Adapted for Multi-GPU & MP4)
[修改点]:
1. 增加 Sharding (分片) 逻辑，支持双卡并行。
2. 增加 VideoReader 支持，直接读取 .mp4 文件。
3. 适配 Qwen2.5-VL 的 Processor 调用方式。
"""

import os
import sys
import json
import torch
import logging
import argparse
import numpy as np
from pathlib import Path
from tqdm import tqdm
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

# 显存优化补丁
sys.modules['torchcodec'] = None 
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except: 
    DECORD_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [CoT-Reflect] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class CoTReflectionPrompts:
    """CoT推理 + 反思提示模板"""
    
    @staticmethod
    def initial_reasoning_prompt(question: str) -> str:
        return f"""请仔细观察视频内容，并对以下问题进行详细的逐步推理。

问题：{question}

请按照以下步骤进行推理：

【步骤1：观察】
描述你在视频中观察到的关键视觉元素、场景、人物、文字等。

【步骤2：分析】
分析这些视觉元素如何与问题相关，它们传达了什么信息。

【步骤3：推理】
基于观察和分析，进行逻辑推理，说明你的思考过程。

【步骤4：答案】
给出对问题的最终答案。

请用中文回答，保持简洁清晰。"""
    
    @staticmethod
    def reflection_prompt(question: str, initial_answer: str) -> str:
        return f"""请评估并改进以下回答。

原始问题：{question}

初始回答：
{initial_answer}

请进行反思：
1. 这个回答是否完整回答了问题？
2. 推理过程是否有逻辑漏洞？
3. 是否遗漏了重要的视觉信息？
4. 答案是否准确且有说服力？

如果发现问题，请给出改进后的回答。如果初始回答已经很好，请直接确认。

请按以下格式输出：

【评估】
对初始回答的评价（优点和不足）

【改进回答】
如果需要改进，给出更好的回答；否则确认原回答。

请用中文回答。"""

def load_frames_from_video(video_path, max_frames=8):
    """从 MP4 视频中直接读取帧"""
    if not os.path.exists(video_path):
        return []
    
    frames = []
    if DECORD_AVAILABLE:
        try:
            vr = VideoReader(video_path, ctx=cpu(0))
            total_frames = len(vr)
            if total_frames > max_frames:
                indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            else:
                indices = np.arange(total_frames)
            
            frames = [Image.fromarray(vr[i].asnumpy()).convert("RGB") for i in indices]
        except Exception as e:
            logger.error(f"Decord read error: {e}")
    return frames

def generate_with_model(model, processor, frames, prompt, device="cuda", max_new_tokens=512):
    """使用模型生成回答"""
    try:
        # 构造 Video 输入消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "video", "video": frames},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # 处理输入
        inputs = processor(
            text=[text],
            videos=[frames], # Qwen2.5-VL 推荐传入 list of PIL images 作为 video
            padding=True,
            return_tensors="pt",
        ).to(device)
        
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=max_new_tokens,
            )
        
        trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated)]
        output_text = processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]
        
        return output_text.strip()
    
    except Exception as e:
        logger.error(f"生成失败: {e}")
        return ""

def cot_reflection_inference(model, processor, frames, question, device="cuda"):
    prompts = CoTReflectionPrompts()
    
    # 1. 初始推理
    # logger.info("  [Step 1] Initial CoT...")
    initial_prompt = prompts.initial_reasoning_prompt(question)
    initial_reasoning = generate_with_model(model, processor, frames, initial_prompt, device, 512)
    
    if not initial_reasoning:
        return {'final_answer': '', 'initial_reasoning': '', 'reflection': ''}
    
    # 2. 反思
    # logger.info("  [Step 2] Reflection...")
    reflection_prompt = prompts.reflection_prompt(question, initial_reasoning)
    reflection_output = generate_with_model(model, processor, frames, reflection_prompt, device, 512)
    
    # 3. 提取
    final_answer = initial_reasoning
    if "【改进回答】" in reflection_output:
        parts = reflection_output.split("【改进回答】")
        if len(parts) > 1:
            candidate = parts[1].strip()
            # 如果改进回答不是空的，就采纳
            if len(candidate) > 5: 
                final_answer = candidate

    return {
        'initial_reasoning': initial_reasoning,
        'reflection': reflection_output,
        'final_answer': final_answer
    }

def main():
    parser = argparse.ArgumentParser()
    # 路径配置 (已填入默认值)
    parser.add_argument("--video_root", type=str, default="/data1/rmx/projectb/AdsQA-main/data/videos")
    parser.add_argument("--question_file", type=str, default="/data1/rmx/projectb/AdsQA-main/data/testset_question.json")
    parser.add_argument("--model_dir", type=str, default="/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R")
    parser.add_argument("--output_dir", type=str, default="/data1/rmx/projectb/AdsQA-main/evaluation/results_cot_reflection")
    parser.add_argument("--max_frames", type=int, default=16) # 提高一点帧数配合CoT
    
    # 分片参数
    parser.add_argument("--gpu_id", type=str, required=True) # 仅用于日志，实际控制靠 CUDA_VISIBLE_DEVICES
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    
    args = parser.parse_args()
    
    # 1. 加载模型
    logger.info(f"🔄 Loading Model on GPU (Logical: 0)...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    # 适当限制像素防止 OOM
    processor = AutoProcessor.from_pretrained(args.model_dir, min_pixels=256*256, max_pixels=1008*1008)
    
    # 2. 加载问题 & 分片
    with open(args.question_file, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)
    
    # ⚠️ 快速验证模式 (跑 1/30 数据)，如果想跑全量请注释下面这行
    all_questions = all_questions[::30]

    # 分片逻辑
    questions = [q for i, q in enumerate(all_questions) if i % args.num_shards == args.shard_id]
    logger.info(f"📊 Shard {args.shard_id}/{args.num_shards}: Processing {len(questions)} samples.")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. 推理循环
    for item in tqdm(questions, desc=f"Shard {args.shard_id}"):
        qid = item["question_id"]
        vid = item.get("video", item.get("video_id", qid.split('_')[0]))
        
        save_path = output_dir / qid / "prediction.json"
        if save_path.exists(): continue
        
        # 寻找视频文件
        vpath = os.path.join(args.video_root, f"{vid}.mp4")
        if not os.path.exists(vpath): 
            vpath = os.path.join(args.video_root, vid)
        
        # 加载帧
        frames = load_frames_from_video(vpath, args.max_frames)
        if not frames: continue
        
        try:
            # 执行 CoT + Reflection
            res = cot_reflection_inference(model, processor, frames, item["question"])
            
            # 保存
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": res['final_answer'],
                    "initial_reasoning": res['initial_reasoning'],
                    "reflection": res['reflection'],
                    "pipeline": "CoT_Reflection"
                }, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error {qid}: {e}")

if __name__ == "__main__":
    main()