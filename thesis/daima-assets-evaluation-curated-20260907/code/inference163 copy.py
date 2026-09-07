#!/usr/bin/env python3
"""
AdsQA A6000 终极补全版 (V5 Supplement - Dual GPU Ready)
功能：
1. 自动检查旧结果文件夹，不重复跑已完成的任务。
2. 支持双卡并行 (GPU 0 和 GPU 1 同时跑)。
3. 新生成的结果存入 supplement 文件夹。
"""

import os
import argparse

# ================= 命令行参数解析 (最优先) =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="指定使用的GPU ID (例如 0 或 1)")
parser.add_argument("--shard_id", type=int, required=True, help="当前分片ID (0 或 1)")
parser.add_argument("--num_shards", type=int, default=2, help="总分片数 (通常为2)")
args = parser.parse_args()

# [关键] 必须在 import torch 之前设置 CUDA_VISIBLE_DEVICES
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id

import json
import torch
import logging
import numpy as np
import traceback
from pathlib import Path
from typing import List
from tqdm import tqdm
from PIL import Image, ImageFile
import torch.nn.functional as F

# ================= 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",          
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    # [关键配置 1] 旧结果路径 (用来检查是否跑过)
    "previous_output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5",

    # [关键配置 2] 新结果路径 (新跑的数据存这里)
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5_supplement",
    
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

# 日志 (区分 GPU)
log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/supplement_gpu{args.gpu_id}.log'
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

# [修复] 逐帧读取
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

class RAGRetriever:
    def __init__(self, kb_path, model_path, device='cuda'):
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

class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr, rag):
        rag_text = f"\n[Expert Context]\n{rag}" if rag else ""
        return f"""Analyze the video content (Global views + Local details) and audio.

Question: {question}
Audio Transcript: {asr}
{rag_text}

Instructions:
1. [Visual Observation]: Describe the scene, characters, and visible text. Prioritize visuals over rules.
2. [Reasoning]: Connect visuals to the question. **Cite Expert Context ONLY IF it fits visually.**
3. [Answer]: Concise, direct answer.
"""

    @staticmethod
    def reflection_prompt(question, initial_ans):
        return f"""Role: Fact-Checker.
        
Question: {question}
Draft: "{initial_ans}"

Task: Verify the Draft against the video.
- **KEEP** if the answer is subjective (emotions, style) or visually supported.
- **CORRECT** only if you find a factual error (wrong text, wrong object).

Output: [KEEP] or [Final Answer]: ...
"""

def main():
    logger.info(f"🚀 Starting process on GPU {args.gpu_id} (Shard {args.shard_id}/{args.num_shards})")

    retriever = RAGRetriever(CONFIG["kb_file"], CONFIG["rag_model_path"])
    s23_processor = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info(f"Loading Qwen from {CONFIG['model_dir']}...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(CONFIG["model_dir"], torch_dtype=torch.float16, device_map="auto")
    processor = AutoProcessor.from_pretrained(CONFIG["model_dir"], min_pixels=256*256, max_pixels=1280*1280)
    logger.info("✅ Model loaded.")
    
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    
    # 确保输出文件夹存在
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    TRIGGERS = ["text", "say", "number", "logo", "url", "why", "reason", "logic", "how does"]

    logger.info(f"Checking Previous: {CONFIG['previous_output_dir']}")
    logger.info(f"Saving New to:     {CONFIG['output_dir']}")

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        # [分片逻辑] 根据索引取模，分配任务
        if i % args.num_shards != args.shard_id: 
            continue
        
        qid = item['question_id']
        
        # =======================================================
        # [智能跳过逻辑]
        # =======================================================
        prev_save_path = Path(CONFIG["previous_output_dir"]) / qid / "prediction.json"
        curr_save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        
        # 如果旧文件夹里已经跑成功了 -> 跳过
        if prev_save_path.exists():
            continue
            
        # 如果新文件夹里已经跑成功了 (断点续传) -> 跳过
        if curr_save_path.exists():
            continue
            
        save_path = curr_save_path
        # =======================================================
        
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        selected_frames = s23_processor.select_top_frames(raw_frames, item['question'], asr_text[:100], CONFIG["top_k_frames"])
        
        final_input_frames = []
        for f in selected_frames:
            local = s23_processor.smart_crop(f, item['question'], asr_text[:100])
            global_view = f
            
            # [升级] 分辨率统一
            local = smart_resize(local, CONFIG["unified_size"])
            global_view = smart_resize(global_view, CONFIG["unified_size"])
            
            final_input_frames.extend([global_view, local])
        
        rag_ctx = retriever.retrieve(f"{item['question']} {asr_text[:100]}", top_k=3)
        
        try:
            # Round 1
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text, rag_ctx)
            msg_1 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames, "fps": 1.0}, {"type": "text", "text": text_1}]}]
            in_1 = processor(text=[processor.apply_chat_template(msg_1, tokenize=False, add_generation_prompt=True)], videos=[final_input_frames], padding=True, return_tensors="pt").to("cuda")
            with torch.no_grad(): gen_1 = model.generate(**in_1, do_sample=False, max_new_tokens=512)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()

            # Gate
            q_lower = item['question'].lower()
            needs_reflect = any(t in q_lower for t in TRIGGERS)
            if any(t in q_lower for t in ["what color", "who is", "where is", "what object"]): needs_reflect = False
            
            final_ans = ans_1
            status = "Skipped"

            if needs_reflect:
                text_2 = CoTReflectionPrompts.reflection_prompt(item['question'], ans_1)
                msg_2 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames, "fps": 1.0}, {"type": "text", "text": text_2}]}]
                in_2 = processor(text=[processor.apply_chat_template(msg_2, tokenize=False, add_generation_prompt=True)], videos=[final_input_frames], padding=True, return_tensors="pt").to("cuda")
                with torch.no_grad(): gen_2 = model.generate(**in_2, do_sample=False, max_new_tokens=512)
                res_2 = processor.batch_decode(gen_2, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                
                if "[Final Answer]:" in res_2:
                    final_ans = res_2.split("[Final Answer]:")[-1].strip()
                    status = "Corrected"
                elif "[KEEP]" in res_2:
                    status = "Verified"
                else:
                    if len(res_2) > 20: final_ans = res_2

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "initial_reasoning": ans_1,
                    "pipeline": "A6000_Ultimate_V5_Supplement",
                    "reflection_status": status,
                    "rag_context": rag_ctx
                }, f, ensure_ascii=False, indent=2)
            
            torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Inference failed {qid}: {e}")

    logger.info("Done.")

if __name__ == "__main__":
    main()