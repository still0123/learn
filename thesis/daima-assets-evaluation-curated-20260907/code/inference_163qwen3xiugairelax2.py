#!/usr/bin/env python3
"""
AdsQA Patent Edition (S5 Chain-of-Verification)
实现功能：
1. S4: 营销专家思维链 (观察-分析-推理-答案) -> 提升 Relaxed
2. S5: 批评家反思机制 (Critic -> Revision) -> 巩固 Strict
3. S2/S23: 视听协同与动态锚框 (保留)
"""

import os
import argparse
import sys
import json
import logging
import numpy as np
import traceback
import re
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile
import torch
import torch.nn.functional as F

# 显存优化
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
ImageFile.LOAD_TRUNCATED_IMAGES = True

# ================= 命令行参数 =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="Target GPU ID")
parser.add_argument("--shard_id", type=int, default=0)
parser.add_argument("--num_shards", type=int, default=1)
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

# [强硬锁卡]
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
print(f"🔒 [System] Hard-locked process to Physical GPU: {args.gpu_id}")

from transformers import AutoModelForVision2Seq, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except ImportError:
    DECORD_AVAILABLE = False

# ================= 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/qky/Model/QWen3VL",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",          
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "groundtruth_file": "/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    
    # [输出目录] 
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163qwen3relax2",
    
    # [参数]
    "oversample_count": 32,
    "top_k_frames": 16, 
    "unified_size": (896, 896), 
}

# 日志
log_dir = '/data1/rmx/projectb/AdsQA-main/evaluation/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'qwen3_s5_gpu{args.gpu_id}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# [图像处理辅助函数]
def smart_resize(img, target_size): return img.resize(target_size, Image.BICUBIC)

def load_frames_oversampled(video_path, sample_count=32):
    if not os.path.exists(video_path): return []
    frames = []
    try:
        if DECORD_AVAILABLE:
            vr = VideoReader(video_path, ctx=cpu(0))
            if len(vr) > 0:
                indices = np.linspace(0, len(vr)-1, sample_count, dtype=int)
                for idx in indices:
                    frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
                if frames: return frames
    except: pass
    if not frames and os.path.isdir(video_path):
        files = sorted(Path(video_path).glob("*.jpg")) + sorted(Path(video_path).glob("*.png"))
        if files:
            idx = np.linspace(0, len(files)-1, sample_count, dtype=int)
            for i in idx:
                try: frames.append(Image.open(files[i]).convert("RGB"))
                except: continue
    return frames

# [保留专利 S23 特征提取]
class S23VisualProcessor:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device 
        self.valid = False
        if not clip_path: return
        try:
            kwargs = {"local_files_only": True, "ignore_mismatched_sizes": True}
            self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, **kwargs).to(device).eval()
            self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path, **kwargs).to(device).eval()
            self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
            from torchvision.transforms import ToTensor, Normalize
            self.normalize = Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))
            self.to_tensor = ToTensor()
            self.valid = True
        except: pass

    def _encode_text(self, text):
        tokens = self.tokenizer([text[:77]], padding=True, return_tensors="pt").to(self.device)
        return F.normalize(self.text_enc(**tokens).text_embeds, dim=-1)

    def _safe_preprocess(self, image):
        try:
            if image.mode != 'RGB': image = image.convert('RGB')
            image = image.resize((224, 224), Image.BICUBIC)
            tensor = self.to_tensor(image)
            if tensor.shape[0] == 1: tensor = tensor.repeat(3, 1, 1)
            elif tensor.shape[0] == 4: tensor = tensor[:3]
            return self.normalize(tensor) if tensor.shape[0]==3 else None
        except: return None

    def select_and_crop(self, frames, question, audio, top_k=8):
        """同时执行筛选(S21)和动态裁剪(S23)"""
        if not self.valid or not frames: return frames[:top_k]
        try:
            # 1. Select
            with torch.no_grad():
                processed, valid_idx = [], []
                for i, f in enumerate(frames):
                    t = self._safe_preprocess(f)
                    if t: processed.append(t); valid_idx.append(i)
                if not processed: return frames[:top_k]
                
                imgs_ts = torch.stack(processed).to(self.device)
                img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                q_emb = self._encode_text(question)
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                top_idx = sorted(np.argsort(scores.cpu().numpy())[-top_k:])
                selected = [frames[valid_idx[i]] for i in top_idx]

                # 2. Crop (简化版 S23)
                final_frames = []
                for f in selected:
                    final_frames.append(f) # 全图
                    # 这里为了速度，简单取中心裁切作为 Anchor 示意，完整 S23 逻辑见上个版本
                    # 如果需要极高精度，请把上个版本的 smart_crop 复制回来
                    w, h = f.size
                    final_frames.append(f.crop((w*0.1, h*0.1, w*0.9, h*0.9))) 
                return final_frames
        except: return frames[:top_k]

# ================= 核心：Prompt 模板 (S4 & S5) =================
class PatentPrompts:
    @staticmethod
    def expert_prompt(question, asr):
        """步骤 S4: 营销专家思维链"""
        return f"""Role: You are a Senior Advertising Marketing Expert.
Task: Answer the question based on the video visual content and audio transcript.

Context Information:
- Question: {question}
- Audio Transcript: {asr}

Requirement: Strictly follow the format below.
1. [Observation]: List key visual elements (colors, texts, objects, actions) and audio cues.
2. [Analysis]: Analyze the marketing intent or scene context.
3. [Reasoning]: Logically connect the evidence to the question.
4. [Answer]: Provide the final answer concisely.
"""

    @staticmethod
    def critic_prompt(question, draft_answer):
        """步骤 S51: 批评家反思"""
        return f"""Role: Critical Reviewer.
Task: Check the answer below for hallucinations or logic errors based on the video.

Question: {question}
Draft Answer: {draft_answer}

Instruction:
- Is the answer supported by the visual/audio evidence?
- Is the logic sound?

Output Format (JSON only):
{{
    "status": "pass" OR "fail",
    "suggestion": "If fail, provide specific correction instructions here. If pass, leave empty."
}}
"""

    @staticmethod
    def revision_prompt(question, old_answer, suggestion):
        """步骤 S52: 迭代修正"""
        return f"""Role: Expert.
The previous answer was rejected.
Question: {question}
Previous Answer: {old_answer}
Critique: {suggestion}

Task: Regenerate the [Answer] section ONLY, strictly following the critique.
"""

def main():
    logger.info(f"🚀 S5 Patent Process started on GPU: {args.gpu_id}")
    
    s23 = S23VisualProcessor(CONFIG["model_dir"], CONFIG["clip_path"])
    
    # 模型加载
    model = AutoModelForVision2Seq.from_pretrained(CONFIG["model_dir"], torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(CONFIG["model_dir"], min_pixels=256*256, max_pixels=1280*1280, trust_remote_code=True)
    
    # 数据加载
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    questions = questions[args.start_idx : args.end_idx] if args.end_idx != -1 else questions[args.start_idx:]

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        torch.cuda.empty_cache()
        qid = item['question_id']
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        if save_path.exists(): continue

        # 1. 视频加载与 S23 处理
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "")
        # 获取处理后的帧 (Top-K + Crop)
        frames = s23.select_and_crop(raw_frames, item['question'], asr_text, CONFIG["top_k_frames"])
        
        # 统一尺寸
        frames = [smart_resize(f, CONFIG["unified_size"]) for f in frames]

        try:
            # === Round 1: S4 营销专家推理 ===
            prompt_1 = PatentPrompts.expert_prompt(item['question'], asr_text)
            msg_1 = [{"role": "user", "content": [{"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt_1}]}]
            text_1 = processor.apply_chat_template(msg_1, tokenize=False, add_generation_prompt=True)
            inputs_1 = processor(text=[text_1], videos=[frames], padding=True, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                gen_1 = model.generate(**inputs_1, do_sample=False, max_new_tokens=512)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()
            
            final_ans = ans_1
            final_status = "Direct"

            # === Round 2: S5 链式校验 (仅针对长难句或推理题触发，或全量触发) ===
            # 这里设为全量触发，因为你的目标是修正 Relaxed
            
            prompt_critic = PatentPrompts.critic_prompt(item['question'], ans_1)
            # Critic 也是基于视频看的
            msg_critic = [{"role": "user", "content": [{"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt_critic}]}]
            text_critic = processor.apply_chat_template(msg_critic, tokenize=False, add_generation_prompt=True)
            inputs_critic = processor(text=[text_critic], videos=[frames], padding=True, return_tensors="pt").to(model.device)
            
            with torch.no_grad():
                gen_critic = model.generate(**inputs_critic, do_sample=False, max_new_tokens=256)
            critic_res = processor.batch_decode(gen_critic, skip_special_tokens=True)[0].split("assistant")[-1].strip()

            # 解析 JSON
            is_fail = False
            suggestion = ""
            try:
                # 简单提取 json 部分，防止 markdown 干扰
                json_str = critic_res
                if "```json" in critic_res:
                    json_str = critic_res.split("```json")[1].split("```")[0]
                elif "```" in critic_res:
                    json_str = critic_res.split("```")[1].split("```")[0]
                
                critic_json = json.loads(json_str)
                if critic_json.get("status", "").lower() == "fail":
                    is_fail = True
                    suggestion = critic_json.get("suggestion", "")
            except:
                # 如果 JSON 解析失败但含有 fail 关键字，也视为失败
                if "fail" in critic_res.lower():
                    is_fail = True
                    suggestion = critic_res

            # === Round 3: S52 迭代修正 ===
            if is_fail:
                prompt_rev = PatentPrompts.revision_prompt(item['question'], ans_1, suggestion)
                msg_rev = [{"role": "user", "content": [{"type": "video", "video": frames, "fps": 1.0}, {"type": "text", "text": prompt_rev}]}]
                text_rev = processor.apply_chat_template(msg_rev, tokenize=False, add_generation_prompt=True)
                inputs_rev = processor(text=[text_rev], videos=[frames], padding=True, return_tensors="pt").to(model.device)
                
                with torch.no_grad():
                    gen_rev = model.generate(**inputs_rev, do_sample=False, max_new_tokens=512)
                ans_rev = processor.batch_decode(gen_rev, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                
                final_ans = ans_rev
                final_status = "Corrected"

            # 保存
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "initial_draft": ans_1,
                    "critic_feedback": critic_res,
                    "pipeline_status": final_status
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error {qid}: {e}")
            torch.cuda.empty_cache()

if __name__ == "__main__":
    main()