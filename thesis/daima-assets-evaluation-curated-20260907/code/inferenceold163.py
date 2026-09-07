#!/usr/bin/env python3
"""
AdsQA A6000 终极补全版 (Patent Aligned Version v205 - Device Fixed)
功能：
1. [强制绑定] 修复 GPU 跑偏问题，显式绑定模型到当前可见设备。
2. [专利对齐] 严格执行 S4 权利要求的四步思维链。
3. [智能补全] 自动跳过已跑完的数据。
"""

import os
import argparse
import sys
import torch # 在设置 CUDA 变量之后 import

# ================= 命令行参数解析 =================
parser = argparse.ArgumentParser()
# [Fix 1] gpu_id 改为 int 接收，与 shard_id 保持一致，方便后续逻辑处理
parser.add_argument("--gpu_id", type=int, required=True, help="逻辑GPU ID (0, 1, 2) - 必须提供") 
parser.add_argument("--shard_id", type=int, required=True, help="当前分片ID")
parser.add_argument("--num_shards", type=int, default=3, help="总分片数") # 默认改为 3
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

# [关键] 必须在 import torch 之前设置 CUDA_VISIBLE_DEVICES
# ⚠️ 注意：这里我们使用 shell 外部的 CUDA_VISIBLE_DEVICES 来隔离，
# 脚本内部的 args.gpu_id 只是用于逻辑标识和日志记录。
# os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id) # 外部已经设置，这里不需要重复设置，否则会覆盖外部配置。

import json
import logging
import numpy as np
import traceback
from pathlib import Path
from typing import List
from tqdm import tqdm
from PIL import Image, ImageFile
import torch.nn.functional as F
import gc 

# ================= 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",              
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    # 路径配置
    "previous_output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5",
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/old163", # 更新为 V205 目录
    
    # 视觉参数
    "oversample_count": 32,
    "top_k_frames": 16, 
    "crop_ratio": 0.75,
    "unified_size": (896, 896), 
}
# ============================================

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except ImportError:
    DECORD_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_RAG_AVAILABLE = True
except ImportError:
    SENTENCE_RAG_AVAILABLE = False

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

# 日志
log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/v205_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# [辅助] 智能缩放
def smart_resize(img, target_size):
    return img.resize(target_size, Image.BICUBIC)

# [专利步骤 S1] 多模态数据获取
def load_frames_oversampled(video_path: str, sample_count: int = 32) -> List[Image.Image]:
    if not os.path.exists(video_path): return []
    frames = []
    try:
        if DECORD_AVAILABLE:
            vr = VideoReader(video_path, ctx=cpu(0))
            total = len(vr)
            if total > 0:
                indices = np.linspace(0, total-1, sample_count, dtype=int)
                for idx in indices:
                    try:
                        frame_arr = vr[idx].asnumpy()
                        img = Image.fromarray(frame_arr).convert("RGB")
                        frames.append(img)
                    except Exception: continue
                if len(frames) > 0: return frames
    except Exception: pass

    if not frames and os.path.isdir(video_path):
        files = sorted(Path(video_path).glob("*.jpg")) + sorted(Path(video_path).glob("*.png"))
        if files:
            idx = np.linspace(0, len(files)-1, sample_count, dtype=int)
            for i in idx:
                try:
                    img = Image.open(files[i]).convert("RGB")
                    frames.append(img)
                except Exception: continue
    return frames

# [专利步骤 S3] 知识库检索
class RAGRetriever:
    def __init__(self, kb_path, model_path, device):
        self.kb_path = kb_path
        self.use_rag = False
        if not SENTENCE_RAG_AVAILABLE: return
        try:
            self.model = SentenceTransformer(model_path, device=device)
            self.use_rag = True
            with open(self.kb_path, 'r') as f: self.rules = json.load(f)
            self.corpus = [f"Triggers: {','.join(r.get('trigger_features',[]))}. Logic: {r.get('marketing_logic','')}" for r in self.rules]
            self.index_embeddings = self.model.encode(self.corpus, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
        except Exception: self.use_rag = False

    def retrieve(self, query, top_k=3):
        if not self.use_rag: return ""
        try:
            q_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            scores = np.dot(q_vec, self.index_embeddings.T)[0]
            top_ids = np.argsort(scores)[::-1][:top_k]
            return "\n".join([f"- Rule {i+1}: {self.rules[idx].get('marketing_logic','')}" for i, idx in enumerate(top_ids)])
        except Exception: return ""

# [专利步骤 S2] 视觉压缩与锚框生成
class S23VisualProcessor:
    def __init__(self, device, clip_path=None):
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
        except Exception: pass

    def _encode_text(self, text):
        if not text: return None
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

    def select_top_frames(self, frames, question, audio_text, top_k=8):
        if not self.valid or not frames: return frames[:top_k]
        # 保持原逻辑 (已修复)
        try:
            with torch.no_grad():
                processed, valid_idx = [], []
                for i, f in enumerate(frames):
                    t = self._safe_preprocess(f)
                    if t is not None:
                        processed.append(t)
                        valid_idx.append(i)
                        
                if not processed: return frames[:top_k]
                
                imgs_ts = torch.stack(processed).to(self.device)
                vis_out = self.vision(imgs_ts)
                img_emb = F.normalize(vis_out.image_embeds, dim=-1)
                
                q_emb = self._encode_text(question)
                a_emb = self._encode_text(audio_text)
                
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                if a_emb is not None:
                    scores = (scores * 0.7) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.3)
                
                scores = scores.cpu().numpy()
                if len(scores) <= top_k: return [frames[i] for i in valid_idx]
                
                top_idx = sorted(np.argsort(scores)[-top_k:])
                return [frames[valid_idx[i]] for i in top_idx]
        except Exception as e:
            logger.error(f"Select error: {e}")
            return frames[:top_k]

    def smart_crop(self, frame, question, audio_text):
        if not self.valid: return frame
        # 保持原逻辑 (已修复)
        try:
            with torch.no_grad():
                t = self._safe_preprocess(frame)
                if t is None: return frame
                
                img_ts = t.unsqueeze(0).to(self.device)
                vis_out = self.vision(img_ts)
                last_hidden = vis_out.last_hidden_state[:, 1:]
                if hasattr(self.vision, 'visual_projection'): last_hidden = self.vision.visual_projection(last_hidden)
                patch_emb = F.normalize(last_hidden, dim=-1)
                
                q_emb = self._encode_text(question)
                hm_q = torch.matmul(patch_emb, q_emb.T).view(-1)
                
                ocr_tokens = self.tokenizer(["text", "logo"], padding=True, return_tensors="pt").to(self.device)
                ocr_emb = F.normalize(self.text_enc(**ocr_tokens).text_embeds, dim=-1)
                hm_ocr = torch.matmul(patch_emb, ocr_emb.T).max(dim=1).values.squeeze()
                
                fused = (hm_q * 0.6) + (hm_ocr * 0.4)
                
                side = int(fused.shape[0]**0.5)
                hm = fused.view(side, side).cpu().numpy()
                hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
                h, w = hm.shape
                y, x = np.indices((h, w))
                tot = hm.sum() + 1e-8
                cy, cx = np.sum(y * hm) / tot, np.sum(x * hm) / tot
                
                ow, oh = frame.size
                ctx, cty = int((cx/w)*ow), int((cy/h)*oh)
                cw, ch = int(ow * CONFIG["crop_ratio"]), int(oh * CONFIG["crop_ratio"])
                l, t = max(0, ctx - cw//2), max(0, cty - ch//2)
                r, b = min(ow, l+cw), min(oh, t+ch)
                if r-l < cw: l = max(0, r-cw)
                if b-t < ch: t = max(0, b-ch)
                return frame.crop((l, t, r, b))
        except: return frame

# [专利步骤 S4 & S5] 核心 Prompt 类
class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr, rag):
        rag_text = f"\n[Expert Context (Marketing Knowledge)]\n{rag}" if rag else ""
        # 保持 [Answer] 格式简洁，但 Reasoning 保持详细
        return f"""Analyze the video content (Global views + Local details) and audio to answer the question following the strict 4-step logic.

Question: {question}
Audio Transcript: {asr}
{rag_text}

Instructions:
1. [Observation]: Objectively describe the key visual scenes, characters, actions, and auditory information. (Patent S42)
2. [Analysis]: Analyze the metaphors, persuasion strategies, or marketing logic behind these elements, referring to the Expert Context if applicable. (Patent S43)
3. [Reasoning]: Synthesize the observation and analysis to logically deduce the answer to the user's question. (Patent S44)
4. [Answer]: Provide the final concise answer.

Output format:
[Observation]: ...
[Analysis]: ...
[Reasoning]: ...
[Answer]: ...
"""

    @staticmethod
    def reflection_prompt(question, initial_ans):
        # 保持原逻辑
        return f"""Role: Marketing Logic Checker.
        
Question: {question}
Draft Answer: "{initial_ans}"

Task: Evaluate the draft based on Accuracy, Logic, and Completeness.
- Check if the [Analysis] aligns with actual marketing concepts.
- Check if the [Observation] matches the video facts (No Hallucination).

Output: 
If the draft is correct, output: [KEEP]
If there are errors, output: [Final Answer]: (The corrected answer)
"""

def main():
    # [Fix 2] 显式定义当前进程使用的设备
    device = torch.device(f"cuda:0" if torch.cuda.is_available() else "cpu")
    logger.info(f"🚀 Starting process on LOGICAL GPU {args.gpu_id} (Shard {args.shard_id}/{args.num_shards}) using PHYSICAL device {device}")

    # 初始化 RAG/CLIP 处理器，并传入正确的设备
    retriever = RAGRetriever(CONFIG["kb_file"], CONFIG["rag_model_path"], device=device)
    s23_processor = S23VisualProcessor(device=device, clip_path=CONFIG["clip_path"])
    
    logger.info(f"Loading Qwen from {CONFIG['model_dir']}...")
    
    # [Fix 3] 模型加载：直接加载到当前可见的 GPU 上，不使用 device_map="auto" 或 "cuda"
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        CONFIG["model_dir"], 
        torch_dtype=torch.float16, 
        device_map=device # 显式传入 device 对象或 "auto"
    )
    processor = AutoProcessor.from_pretrained(CONFIG["model_dir"], min_pixels=256*256, max_pixels=1280*1280)
    logger.info(f"✅ Model loaded. Model device: {model.device}")
    
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    # 手动范围切片 (如果指定)
    if args.end_idx == -1:
        args.end_idx = len(questions)
    
    logger.info(f"🔥 Processing Range: {args.start_idx} to {args.end_idx}")
    questions = questions[args.start_idx : args.end_idx]
    
    TRIGGERS = ["text", "say", "number", "logo", "url", "why", "reason", "logic", "how does"]

    logger.info(f"Checking Previous: {CONFIG['previous_output_dir']}")
    logger.info(f"Saving New to:     {CONFIG['output_dir']}")

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        # [分片逻辑]
        if i % args.num_shards != args.shard_id: 
            continue
        
        qid = item['question_id']
        
        # [智能跳过]
        prev_save_path = Path(CONFIG["previous_output_dir"]) / qid / "prediction.json"
        curr_save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        
        if prev_save_path.exists(): continue
        if curr_save_path.exists(): continue
        
        save_path = curr_save_path
        
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        # S2: CLIP 智能选帧
        selected_frames = s23_processor.select_top_frames(raw_frames, item['question'], asr_text[:100], CONFIG["top_k_frames"])
        
        final_input_frames = []
        for f in selected_frames:
            # S23 Local + S24 Global 双流
            local = s23_processor.smart_crop(f, item['question'], asr_text[:100])
            global_view = f
            local = smart_resize(local, CONFIG["unified_size"])
            global_view = smart_resize(global_view, CONFIG["unified_size"])
            final_input_frames.extend([global_view, local])
        
        # RAG 检索
        rag_ctx = retriever.retrieve(f"{item['question']} {asr_text[:100]}", top_k=3)
        
        try:
            # Round 1: Chain of Thought Generation
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text, rag_ctx)
            msg_1 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames}, {"type": "text", "text": text_1}]}]
            
            in_1 = processor(text=[processor.apply_chat_template(msg_1, tokenize=False, add_generation_prompt=True)], videos=[final_input_frames], padding=True, return_tensors="pt").to(device)
            
            with torch.no_grad(): gen_1 = model.generate(**in_1, do_sample=False, max_new_tokens=768)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()

            # 提取 [Answer] 部分
            final_ans = ans_1
            if "[Answer]:" in ans_1:
                final_ans = ans_1.split("[Answer]:")[-1].strip()
            
            status = "Initial"

            # Round 2: Reflection (Patent S5)
            q_lower = item['question'].lower()
            needs_reflect = any(t in q_lower for t in TRIGGERS)
            if any(t in q_lower for t in ["what color", "who is", "where is", "what object"]): needs_reflect = False
            
            if needs_reflect:
                text_2 = CoTReflectionPrompts.reflection_prompt(item['question'], ans_1)
                msg_2 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames}, {"type": "text", "text": text_2}]}]
                
                in_2 = processor(text=[processor.apply_chat_template(msg_2, tokenize=False, add_generation_prompt=True)], videos=[final_input_frames], padding=True, return_tensors="pt").to(device)
                
                with torch.no_grad(): gen_2 = model.generate(**in_2, do_sample=False, max_new_tokens=512)
                res_2 = processor.batch_decode(gen_2, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                
                if "[Final Answer]:" in res_2:
                    final_ans = res_2.split("[Final Answer]:")[-1].strip()
                    status = "Corrected"
                elif "[KEEP]" in res_2:
                    status = "Verified"
                else:
                    if len(res_2.split()) > 5: final_ans = res_2
                    status = "Fallthrough"


            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "initial_reasoning": ans_1,
                    "pipeline": "A6000_Ultimate_V5_Patent",
                    "reflection_status": status,
                    "rag_context": rag_ctx
                }, f, ensure_ascii=False, indent=2)
            
            torch.cuda.empty_cache()
            gc.collect() 
            
        except Exception as e:
            logger.error(f"Inference failed {qid}: {e}")
            if "out of memory" in str(e):
                logger.error("OOM detected, clearing cache...")
                torch.cuda.empty_cache()
                gc.collect()

    logger.info("Done.")

if __name__ == "__main__":
    main()