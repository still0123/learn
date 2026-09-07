#!/usr/bin/env python3
"""
AdsQA A6000 V10 Patent Edition (Smart & Light - Fixed)
[修复日志]:
1. 修复了 AttributeError: 'Namespace' object has no attribute 'end_idx' 报错。
2. 包含完整的专利逻辑：AVAM时序压缩 + 隐式CoT + 门控反思。
"""

import os
import argparse
import sys
import json
import torch
import logging
import numpy as np
import traceback
import re
from pathlib import Path
from typing import List
from tqdm import tqdm
from PIL import Image, ImageFile, ImageFilter
import torch.nn.functional as F

# ================= 1. Setup =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="GPU ID (e.g., 0)")
parser.add_argument("--shard_id", type=int, required=True, help="Shard ID (0, 1, 2...)")
parser.add_argument("--num_shards", type=int, default=3, help="Total number of shards")
# [修复] 补回了这两个缺失的参数
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)

args = parser.parse_args()

os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
print(f"🚀 V10 Patent-Light System initialized on GPU {args.gpu_id}")

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
sys.modules['torchcodec'] = None 

# ================= 2. Config ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    # 输出目录
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/165_rl_3",
    
    # 策略配置
    "oversample_count": 96, # 广撒网
    "top_k_frames": 16,     # 精选16帧 (即Token压缩)
}

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except: DECORD_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_RAG_AVAILABLE = True
except: SENTENCE_RAG_AVAILABLE = False

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/run_v10_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# [无需 Resize] 原生加载
def load_frames_oversampled(video_path: str, sample_count: int = 96) -> List[Image.Image]:
    if not os.path.exists(video_path): return []
    frames = []
    try:
        if DECORD_AVAILABLE:
            vr = VideoReader(video_path, ctx=cpu(0))
            if len(vr) > 0:
                indices = np.linspace(0, len(vr)-1, sample_count, dtype=int)
                for idx in indices:
                    try:
                        frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
                    except: continue
    except: pass

    if not frames and os.path.isdir(video_path):
        files = sorted(Path(video_path).glob("*.jpg")) + sorted(Path(video_path).glob("*.png"))
        if files:
            idx = np.linspace(0, len(files)-1, sample_count, dtype=int)
            for i in idx:
                try:
                    frames.append(Image.open(files[i]).convert("RGB"))
                except: continue
    return frames

class RAGRetriever:
    def __init__(self, kb_path, model_path, device='cuda'):
        self.use_rag = False
        if SENTENCE_RAG_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_path, device=device)
                with open(kb_path, 'r') as f: self.rules = json.load(f)
                self.corpus = [r.get('marketing_logic','') for r in self.rules]
                self.index_embeddings = self.model.encode(self.corpus, normalize_embeddings=True)
                self.use_rag = True
            except: pass

    def retrieve(self, query, top_k=2):
        if not self.use_rag: return ""
        try:
            q_vec = self.model.encode([query], normalize_embeddings=True)
            scores = np.dot(q_vec, self.index_embeddings.T)[0]
            top_ids = np.argsort(scores)[::-1][:top_k]
            return "\n".join([f"- Hint: {self.rules[idx].get('marketing_logic','')}" for idx in top_ids])
        except: return ""

class S23VisualProcessor:
    def __init__(self, device="cuda", clip_path=None):
        self.valid = False
        try:
            self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path).to(device).eval()
            self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path).to(device).eval()
            self.tokenizer = CLIPTokenizer.from_pretrained(clip_path)
            from torchvision.transforms import ToTensor, Normalize
            self.normalize = Normalize((0.481, 0.457, 0.408), (0.268, 0.261, 0.275))
            self.to_tensor = ToTensor()
            self.valid = True
            self.device = device
        except: pass

    def _safe_preprocess_clip(self, image):
        try:
            img = image.resize((224, 224), Image.BICUBIC)
            t = self.to_tensor(img)
            return self.normalize(t) if t.shape[0]==3 else None
        except: return None

    # [专利核心 1] AVAM 混合骨架采样 (Entropy + Semantic)
    def select_avam_frames(self, frames, question, total_k=16):
        if not frames: return []
        if not self.valid: 
            idx = np.linspace(0, len(frames)-1, total_k, dtype=int)
            return [frames[i] for i in idx]

        try:
            # 1. 计算 AVAM 分数
            scores = []
            for f in frames:
                # 熵分 (OCR)
                gray = f.convert('L').resize((224,224))
                ent = np.var(np.array(gray.filter(ImageFilter.FIND_EDGES)))
                scores.append(ent)
            
            # 归一化
            s_min, s_max = min(scores), max(scores)
            norm_scores = [(s - s_min)/(s_max - s_min + 1e-6) for s in scores]

            # 2. 混合选择
            # A. 骨架 (8帧) - 保时序
            n_skel = total_k // 2
            skel_idx = np.linspace(0, len(frames)-1, n_skel, dtype=int).tolist()
            
            # B. 血肉 (8帧) - 保细节 (选熵最高的)
            selected = set(skel_idx)
            sorted_idx = np.argsort(norm_scores)[::-1]
            
            for i in sorted_idx:
                if len(selected) >= total_k: break
                selected.add(i)
                
            final_idx = sorted(list(selected))
            return [frames[i] for i in final_idx]
        except: return frames[:total_k]

# [专利核心 2] 隐式思维链 Prompt
class PatentPrompts:
    @staticmethod
    def implicit_cot(question, asr, rag):
        rag_section = f"\n[Expert Knowledge]\n{rag}" if rag else ""
        return f"""Task: Video Question Answering.
Question: {question}
Audio Transcript: {asr}
{rag_section}

Instruction: 
1. Carefully observe the video for text, actions, and visual details.
2. If available, use the [Expert Knowledge] to interpret the marketing intent.
3. Answer the question directly and concisely.
"""

    @staticmethod
    def reflection_check(question, ans):
        # [专利核心 3] 反思触发器
        return f"""Review Task.
Question: {question}
Draft Answer: "{ans}"

Check if the draft answer missed any specific visual details (like text on screen) or audio cues.
If the draft is correct, output: [KEEP]
If there is a factual error or missing detail, provide the corrected answer directly.
"""

def main():
    retriever = RAGRetriever(CONFIG["kb_file"], CONFIG["rag_model_path"])
    s23 = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info(f"Loading Model: {CONFIG['model_dir']}")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(CONFIG["model_dir"], torch_dtype=torch.float16, device_map="auto")
    processor = AutoProcessor.from_pretrained(CONFIG["model_dir"], min_pixels=256*256, max_pixels=1280*1280)
    logger.info("✅ Model loaded.")
    
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
    COMPLEX_TRIGGERS = ["why", "reason", "logic", "how", "implied", "theme", "purpose"]
    
    logger.info(f"Saving New results to: {CONFIG['output_dir']}")

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        qid = item['question_id']
        save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        if save_path.exists(): continue
        
        # 1. 读视频
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        # 2. AVAM 采样 (Token压缩)
        final_frames = s23.select_avam_frames(raw_frames, item['question'], CONFIG["top_k_frames"])
        
        # 3. RAG & Prompt
        asr = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        is_complex = any(t in item['question'].lower() for t in COMPLEX_TRIGGERS)
        rag_ctx = retriever.retrieve(f"{item['question']} {asr[:50]}") if is_complex else ""
        
        try:
            # === Round 1: Implicit CoT ===
            text_1 = PatentPrompts.implicit_cot(item['question'], asr, rag_ctx)
            msg_1 = [{"role": "user", "content": [{"type": "video", "video": final_frames}, {"type": "text", "text": text_1}]}]
            
            in_1 = processor(text=[processor.apply_chat_template(msg_1, tokenize=False, add_generation_prompt=True)],
                             videos=[final_frames], padding=True, return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                gen_1 = model.generate(**in_1, do_sample=False, max_new_tokens=256)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()
            
            final_ans = ans_1
            status = "Skipped"

            # === Round 2: Reflection (Gate) ===
            if is_complex or len(ans_1) < 15:
                text_2 = PatentPrompts.reflection_check(item['question'], ans_1)
                msg_2 = [{"role": "user", "content": [{"type": "video", "video": final_frames}, {"type": "text", "text": text_2}]}]
                in_2 = processor(text=[processor.apply_chat_template(msg_2, tokenize=False, add_generation_prompt=True)],
                                 videos=[final_frames], padding=True, return_tensors="pt").to("cuda")
                with torch.no_grad():
                    gen_2 = model.generate(**in_2, do_sample=False, max_new_tokens=256)
                res_2 = processor.batch_decode(gen_2, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                
                if "[KEEP]" not in res_2 and len(res_2) > len(ans_1):
                    final_ans = res_2
                    status = "Refined"
                else:
                    status = "Verified"

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "pipeline": "V10_Patent_Light",
                    "reflection": status,
                    "rag": rag_ctx
                }, f, indent=2)
            
            torch.cuda.empty_cache()
                
        except Exception as e:
            logger.error(f"Err {qid}: {e}")

    logger.info("Done.")

if __name__ == "__main__":
    main()