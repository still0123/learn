#!/usr/bin/env python3
"""
AdsQA A6000 AVAM专利增强版 (V7 Patent Implementation)
核心技术：基于视听锚点(AVAM)与动态微观重采样(IVR)的认知推理架构。

[专利模块映射]:
1. [AVAM Selection]: 融合 "语义相关性(CLIP)" + "视觉信息熵(Entropy)" 进行关键帧锚定。
2. [Dynamic IVR]: 针对不同任务类型，自适应切换 "全局宏观流" 与 "局部微观流" 的混合比例。
3. [Cognitive Loop]: 保留 RAG(先验知识) + CoT(层级推理) + Reflection(对抗校验)。
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
from PIL import Image, ImageFile, ImageFilter # [新增] ImageFilter用于计算熵
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
print(f"🚀 AVAM-System initialized on GPU {args.gpu_id} | Shard {args.shard_id}/{args.num_shards}")

# 显存优化
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
sys.modules['torchcodec'] = None 

# ================= 3. 配置区域 ================= 
CONFIG = {
    # [建议] 使用 Qwen2.5-VL-7B-Instruct 基座，因为我们的 AVAM 模块负责了特征增强
    # "model_dir": "/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct", # 或者换回 Instruct 基座
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R", 
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    # [修改] 输出路径 V7
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/165_quanjudaojubu_base",
    
    # [专利点] 大幅增加过采样 (96帧)，为熵减压缩提供足够的候选池
    "oversample_count": 96, 
    
    # 最终输入给大模型的帧数
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
log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/run_avam_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def smart_resize(img, target_size):
    return img.resize(target_size, Image.BICUBIC)

def load_frames_oversampled(video_path: str, sample_count: int = 96) -> List[Image.Image]:
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
                        frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
                    except: continue
                if len(frames) > 0: return frames
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
        self.kb_path = kb_path
        self.use_rag = False
        if not SENTENCE_RAG_AVAILABLE: return
        try:
            self.model = SentenceTransformer(model_path, device=device)
            self.use_rag = True
            with open(self.kb_path, 'r') as f: self.rules = json.load(f)
            self.corpus = [f"Triggers: {','.join(r.get('trigger_features',[]))}. Logic: {r.get('marketing_logic','')}" for r in self.rules]
            self.index_embeddings = self.model.encode(self.corpus, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
        except: self.use_rag = False

    def retrieve(self, query, top_k=3):
        if not self.use_rag: return ""
        try:
            q_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            scores = np.dot(q_vec, self.index_embeddings.T)[0]
            top_ids = np.argsort(scores)[::-1][:top_k]
            return "\n".join([f"- Rule {i+1}: {self.rules[idx].get('marketing_logic','')}" for i, idx in enumerate(top_ids)])
        except: return ""

# ==============================================================================
# 🧠 核心改造：S23VisualProcessor (AVAM Implementation)
# ==============================================================================
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

    # [专利模块 1] 信息熵计算 (Entropy Calculation)
    # 作用：量化图像的"信息密度"。文字、复杂纹理的熵值高；纯色背景熵值低。
    def calculate_entropy_score(self, image):
        try:
            # 转灰度 -> 边缘检测 -> 计算方差 (方差越大，边缘越密集，信息量越大)
            gray = image.convert('L').resize((224, 224))
            edges = gray.filter(ImageFilter.FIND_EDGES)
            return np.var(np.array(edges))
        except: return 0.0

    # [专利模块 2] AVAM 锚点筛选 (Audio-Visual Anchoring Selection)
    def select_avam_frames(self, frames, question, audio_text, total_k=16):
        if not frames: return []
        if not self.valid: 
            # 降级策略：均匀采样
            indices = np.linspace(0, len(frames)-1, total_k, dtype=int)
            return [frames[i] for i in indices]

        try:
            # 1. 计算三维评分 (Semantic + Entropy)
            semantic_scores = []
            entropy_scores = []
            
            processed, valid_idx = [], []
            
            for i, f in enumerate(frames):
                # A. 计算熵分 (保 OCR)
                entropy_scores.append(self.calculate_entropy_score(f))
                
                t = self._safe_preprocess(f)
                if t is not None:
                    processed.append(t)
                    valid_idx.append(i)
                else:
                    semantic_scores.append(0.0)

            # B. 计算语义分 (保 Reasoning)
            if processed:
                with torch.no_grad():
                    imgs_ts = torch.stack(processed).to(self.device)
                    # Vision Encoder
                    img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                    q_emb = self._encode_text(question)
                    a_emb = self._encode_text(audio_text)
                    
                    # 融合：70% 问题相关 + 30% 音频相关
                    sim = torch.matmul(img_emb, q_emb.T).view(-1)
                    if a_emb is not None:
                        sim = (sim * 0.7) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.3)
                    
                    sim_np = sim.cpu().numpy()
                    
                    # 映射回去
                    full_sem_scores = np.zeros(len(frames))
                    for idx, val in zip(valid_idx, sim_np):
                        full_sem_scores[idx] = val
            else:
                full_sem_scores = np.zeros(len(frames))

            # 2. 归一化
            def normalize(arr):
                arr = np.array(arr)
                if arr.max() == arr.min(): return arr
                return (arr - arr.min()) / (arr.max() - arr.min())

            norm_sem = normalize(full_sem_scores)
            norm_ent = normalize(entropy_scores)

            # 3. 专利融合公式 (Fusion Formula)
            # 0.5 语义(Reasoning) + 0.3 熵(OCR) + 0.2 均匀偏置(Action)
            # 均匀偏置是为了防止帧过于集中
            batch_size = len(frames)
            # 简单的"距离惩罚"作为均匀偏置的替代，或者直接加随机噪声，这里简化处理
            # 实际上，保留熵高的帧通常就能覆盖到文字帧
            
            final_scores = 0.5 * norm_sem + 0.3 * norm_ent

            # 4. 排序与筛选 (带最小距离约束，防止连选相似帧)
            selected_indices = []
            sorted_idx = np.argsort(final_scores)[::-1] # 降序
            
            min_dist = max(1, batch_size // (total_k * 3)) # 动态距离
            
            # 第一轮：选 Top
            for idx in sorted_idx:
                if len(selected_indices) >= total_k: break
                
                # 检查距离
                is_far = True
                for sel in selected_indices:
                    if abs(sel - idx) < min_dist:
                        is_far = False
                        break
                
                if is_far:
                    selected_indices.append(idx)
            
            # 第二轮：如果没选够，补齐剩下的最高分
            if len(selected_indices) < total_k:
                remaining = [i for i in sorted_idx if i not in selected_indices]
                selected_indices.extend(remaining[:total_k - len(selected_indices)])

            # 按时间排序 (时序重构)
            final_indices = sorted(selected_indices)
            return [frames[i] for i in final_indices]

        except Exception as e:
            logger.error(f"AVAM Select error: {e}")
            return frames[:total_k]

    # [专利模块 3] 熵感知的智能裁剪 (Entropy-Aware Crop)
    def smart_crop_avam(self, frame, question):
        if not self.valid: return frame
        try:
            with torch.no_grad():
                t = self._safe_preprocess(frame)
                if t is None: return frame
                
                # 计算 CLIP Attention
                img_ts = t.unsqueeze(0).to(self.device)
                vis_out = self.vision(img_ts)
                last_hidden = vis_out.last_hidden_state[:, 1:]
                if hasattr(self.vision, 'visual_projection'): last_hidden = self.vision.visual_projection(last_hidden)
                patch_emb = F.normalize(last_hidden, dim=-1)
                q_emb = self._encode_text(question)
                hm = torch.matmul(patch_emb, q_emb.T).view(-1) # [256]
                
                # 转为 16x16 Heatmap
                side = int(hm.shape[0]**0.5)
                hm = hm.view(side, side).cpu().numpy()
                hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
                
                # 计算重心
                h, w = hm.shape
                y, x = np.indices((h, w))
                tot = hm.sum() + 1e-8
                cy, cx = np.sum(y * hm) / tot, np.sum(x * hm) / tot
                
                ow, oh = frame.size
                ctx, cty = int((cx/w)*ow), int((cy/h)*oh)
                
                # 裁剪框大小 (0.6倍，保证视野)
                crop_ratio = 0.6
                cw, ch = int(ow * crop_ratio), int(oh * crop_ratio)
                
                l = max(0, min(ow - cw, ctx - cw//2))
                t = max(0, min(oh - ch, cty - ch//2))
                
                return frame.crop((l, t, l+cw, t+ch))
        except: return frame

class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr, rag):
        rag_text = f"\n[Marketing Knowledge]\n{rag}" if rag else ""
        return f"""Analyze the video visually and aurally.

Question: {question}
Audio: {asr}
{rag_text}

Steps:
1. **Perception**: List key visual elements (Text, Objects, Actions, Colors).
2. **Analysis**: Connect elements to the question. Use Marketing Knowledge if relevant.
3. **Answer**: Provide a direct, factual, and comprehensive answer.
"""

    @staticmethod
    def reflection_prompt(question, initial_ans):
        return f"""Role: QC Editor.
Question: {question}
Draft Answer: "{initial_ans}"

Task: Check for MISSING DETAILS or HALLUCINATIONS.
- If the Draft is sufficient and correct -> Output: [KEEP]
- If the Draft missed visible text or key action -> Output: [Final Answer]: (Refined Answer)
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
    
    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
    # 复杂推理题触发词
    COMPLEX_TRIGGERS = ["why", "reason", "logic", "how", "implied", "theme", "purpose", "suggest"]

    logger.info(f"Saving New results to: {CONFIG['output_dir']}")

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        qid = item['question_id']
        curr_save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        if curr_save_path.exists(): continue
        
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        # 1. 广域读取 (Wide Reading)
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        # 2. [专利核心] AVAM 筛选 (Semantic + Entropy)
        # 从96帧里精选16帧，兼顾了文字清晰度(熵)和语义相关性(CLIP)
        selected_frames = s23_processor.select_avam_frames(raw_frames, item['question'], asr_text[:100], CONFIG["top_k_frames"])
        
        # 3. [专利核心] 动态 IVR 输入构建 (Dynamic Input Construction)
        q_lower = item['question'].lower()
        is_complex = any(t in q_lower for t in COMPLEX_TRIGGERS)
        
        final_input_frames = []
        if is_complex:
            # === 复杂推理题 ===
            # 策略：全图 + 局部高清图 (Global + Local)
            # 全图提供上下文，局部图(Crop)提供细节供推理
            for f in selected_frames:
                # 添加全图
                final_input_frames.append(smart_resize(f, CONFIG["unified_size"]))
                # 隔帧添加局部图 (节省显存)
                if len(final_input_frames) % 4 == 0: 
                    local = s23_processor.smart_crop_avam(f, item['question'])
                    final_input_frames.append(smart_resize(local, CONFIG["unified_size"]))
        else:
            # === 简单感知题 (OCR, Action, Color) ===
            # 策略：仅全图 (Global Only)
            # 坚决不切图！防止切断文字或割裂动作。Qwen2.5-VL 足够看清 Resize 后的文字。
            final_input_frames = [smart_resize(f, CONFIG["unified_size"]) for f in selected_frames]

        # 4. 知识增强 (RAG) - 仅在复杂题启用，避免干扰简单题
        rag_ctx = retriever.retrieve(f"{item['question']} {asr_text[:100]}", top_k=2) # if is_complex else ""
        # 实际上 RAG 几乎没有副作用，可以全开，或者只对复杂题开。这里全开以利用“规则”。
        
        try:
            # === Round 1: Chain of Thought ===
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text, rag_ctx)
            msg_1 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames, "fps": 1.0}, {"type": "text", "text": text_1}]}]
            
            in_1 = processor(text=[processor.apply_chat_template(msg_1, tokenize=False, add_generation_prompt=True)], 
                             videos=[final_input_frames], 
                             padding=True, return_tensors="pt").to("cuda")
            
            with torch.no_grad(): gen_1 = model.generate(**in_1, do_sample=False, max_new_tokens=512)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()

            final_ans = ans_1
            status = "Skipped"

            # === Round 2: Reflection (闭环修正) ===
            # 仅当问题复杂或回答过短（可能没看清）时触发
            if is_complex or len(ans_1) < 20:
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
                    # 如果没有按格式输出，但输出了长文本，可能是在修正
                    if len(res_2) > len(ans_1): final_ans = res_2

            # 保存结果
            curr_save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(curr_save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "initial_reasoning": ans_1,
                    "pipeline": "A6000_AVAM_Patent_V7",
                    "reflection_status": status,
                    "rag_context": rag_ctx
                }, f, ensure_ascii=False, indent=2)
            
            torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Inference failed {qid}: {e}")

    logger.info("Done.")

if __name__ == "__main__":
    main()