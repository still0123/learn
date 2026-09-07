#!/usr/bin/env python3
"""
AdsQA A6000 混合采样增强版 (V6 Hybrid Strategy)
策略升级：
1. [混合采样] 50% 均匀帧 (保全局叙事/宽松分) + 50% CLIP Top-K (保关键细节/严格分)。
2. [提示增强] 要求答案 "Comprehensive" 而非仅 "Concise"，防止遗漏关键点。
3. [反思升级] Fact-Checker 增加 "补全遗漏信息" 的职能。
"""

import os
import argparse
import sys
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

# ================= 1. 优先解析参数 & 设置 GPU =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="指定使用的GPU ID (例如 0, 1, 2)")
parser.add_argument("--shard_id", type=int, required=True, help="分片ID (0, 1, 2)")
parser.add_argument("--num_shards", type=int, default=3, help="总分片数")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)

args = parser.parse_args()

# [关键] 设置显卡
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
print(f"🚀 Process initialized on GPU {args.gpu_id} | Shard {args.shard_id}/{args.num_shards}")

# 显存优化
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
sys.modules['torchcodec'] = None 

# ================= 3. 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    # [修改] 输出路径 V6
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/164",
    
    # [升级] 增加采样密度，让 CLIP 有更多选择
    "oversample_count": 64, 
    
    # [保持] 16帧对 7B 模型是最佳平衡点
    "top_k_frames": 16, 
    
    "crop_ratio": 0.75,
    "unified_size": (896, 896), 
}

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
log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/run_v6_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def smart_resize(img, target_size):
    return img.resize(target_size, Image.BICUBIC)

def load_frames_oversampled(video_path: str, sample_count: int = 64) -> List[Image.Image]:
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

    # [策略升级] 混合帧选择：50% 均匀 + 50% TopK
    def select_hybrid_frames(self, frames, question, audio_text, total_k=16):
        if not frames: return []
        
        # 1. 均匀采样 (Global Context) - 取一半
        n_uniform = total_k // 2
        uniform_indices = np.linspace(0, len(frames)-1, n_uniform, dtype=int).tolist()
        
        # 如果 CLIP 不可用，直接返回均匀采样拉伸
        if not self.valid: 
            full_indices = np.linspace(0, len(frames)-1, total_k, dtype=int)
            return [frames[i] for i in full_indices]

        try:
            # 2. CLIP 评分 (Relevance)
            with torch.no_grad():
                processed, valid_idx = [], []
                for i, f in enumerate(frames):
                    t = self._safe_preprocess(f)
                    if t is not None:
                        processed.append(t)
                        valid_idx.append(i)
                
                if not processed: return [frames[i] for i in uniform_indices]

                imgs_ts = torch.stack(processed).to(self.device)
                vis_out = self.vision(imgs_ts)
                img_emb = F.normalize(vis_out.image_embeds, dim=-1)
                
                q_emb = self._encode_text(question)
                a_emb = self._encode_text(audio_text)
                
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                if a_emb is not None:
                    scores = (scores * 0.7) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.3)
                
                scores = scores.cpu().numpy()
                
                # 3. 选取 Top-K (排除掉已经被均匀采样选中的)
                sorted_score_idx = np.argsort(scores)[::-1] # 降序
                
                selected_indices = set(uniform_indices)
                count_needed = total_k - len(selected_indices)
                
                for idx in sorted_score_idx:
                    real_idx = valid_idx[idx]
                    if real_idx not in selected_indices:
                        selected_indices.add(real_idx)
                        count_needed -= 1
                    if count_needed <= 0: break
                
                # 4. 按时间顺序排序返回
                final_indices = sorted(list(selected_indices))
                return [frames[i] for i in final_indices]

        except Exception as e:
            logger.error(f"Select error: {e}")
            return frames[:total_k]

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
1. [Visual Observation]: Describe the scene, characters, visible text, and actions relevant to the question.
2. [Reasoning]: Connect visuals to the question. Cite Expert Context only if it fits.
3. [Answer]: Provide a **comprehensive and precise** answer. Ensure all key details are included.
"""

    @staticmethod
    def reflection_prompt(question, initial_ans):
        return f"""Role: Fact-Checker & Completeness-Checker.
        
Question: {question}
Draft: "{initial_ans}"

Task: Verify the Draft against the video.
1. **CHECK FOR ERRORS**: Are there factual mistakes? (Wrong color, wrong object).
2. **CHECK FOR OMISSIONS**: Did the draft miss any key information visible in the video or heard in the audio?

Output:
- If perfect: [KEEP]
- If errors or omissions found: [Final Answer]: (The corrected and complete answer)
"""

def main():
    retriever = RAGRetriever(CONFIG["kb_file"], CONFIG["rag_model_path"])
    s23_processor = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info(f"Loading Qwen from {CONFIG['model_dir']}...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(CONFIG["model_dir"], torch_dtype=torch.float16, device_map="auto")
    processor = AutoProcessor.from_pretrained(CONFIG["model_dir"], min_pixels=256*256, max_pixels=1280*1280)
    logger.info("✅ Model loaded.")
    
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    if args.end_idx != -1:
        questions = questions[args.start_idx : args.end_idx]
    
    TRIGGERS = ["text", "say", "number", "logo", "url", "why", "reason", "logic", "how does", "describe", "what happens"]

    logger.info(f"Saving New results to: {CONFIG['output_dir']}")

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        qid = item['question_id']
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        
        curr_save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        if curr_save_path.exists(): continue
        save_path = curr_save_path
        
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        # [修改] 读取更多候选帧 (64帧) 以便混合采样
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        # [修改] 使用混合采样 (Hybrid Selection)
        selected_frames = s23_processor.select_hybrid_frames(raw_frames, item['question'], asr_text[:100], CONFIG["top_k_frames"])
        
        final_input_frames = []
        for f in selected_frames:
            local = s23_processor.smart_crop(f, item['question'], asr_text[:100])
            global_view = f
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
                    "pipeline": "A6000_Hybrid_V6",
                    "reflection_status": status,
                    "rag_context": rag_ctx
                }, f, ensure_ascii=False, indent=2)
            
            torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Inference failed {qid}: {e}")

    logger.info("Done.")

if __name__ == "__main__":
    main()