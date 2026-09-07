#!/usr/bin/env python3
"""
AdsQA Patent Final Attempt (Segment-based Adaptive Selection)
文件名: inference_188.py

[核心策略]: "分段自适应选帧" + "全量原图" + "全量音频"
1. S2 AVAM (修正版): 
   - 之前: 算热力图 -> 裁剪 -> 导致文字丢失 (Fail).
   - 现在: 算热力图 -> 在时间段内优选最佳帧 -> 保留原图 (Success).
   - 数量: 32 帧 (A6000 显存足够，直接拉满).
2. Input: 纯原图序列输入 (保留 Native 分辨率).
3. Prompt: 极简模式，去除干扰，强音频注入.
"""

import sys
import os
import argparse
import json
import torch
import numpy as np
import logging
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFilter
import torch.nn.functional as F

# ================= 显存优化 =================
sys.modules['torchcodec'] = None 
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# ================= 导入依赖 =================
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except: DECORD_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except: RAG_AVAILABLE = False

# ================= 日志配置 =================
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [Final188] %(message)s', 
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧩 模块 S2: 分段自适应选帧 (Segment-based Adaptive Selection)
# ==============================================================================
class AVAM_Selector:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path:
            try:
                # 仅用于打分选帧
                self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.tokenizer = CLIPTokenizer.from_pretrained(clip_path)
                
                from torchvision.transforms import ToTensor, Normalize, Resize, Compose
                self.preprocess = Compose([
                    Resize((224, 224), interpolation=Image.BICUBIC), # CLIP 打分仅需 224
                    ToTensor(),
                    Normalize((0.481, 0.457, 0.408), (0.268, 0.261, 0.275))
                ])
                self.valid = True
            except Exception as e:
                logger.error(f"⚠️ [S2] Init Failed: {e}")

    def select_frames(self, frames, question, asr_text, target_k=32):
        """
        专利核心逻辑 S2 (修正版):
        将视频划分为 target_k 个时间段。
        在每个时间段内，寻找 (CLIP相关性 + 视觉清晰度) 最高的帧。
        返回: 原图列表 (不裁剪!)
        """
        total_frames = len(frames)
        # 如果帧数不足，直接返回所有
        if total_frames <= target_k:
            return frames
        
        # 如果模块未加载，回退到均匀采样
        if not self.valid:
            idx = np.linspace(0, total_frames-1, target_k, dtype=int)
            return [frames[i] for i in idx]

        try:
            # 1. 准备文本特征 (Question + Audio Summary)
            text_input = f"{question} {asr_text[:200]}"
            tk = self.tokenizer([text_input], padding=True, truncation=True, max_length=77, return_tensors="pt").to(self.device)
            with torch.no_grad():
                text_emb = F.normalize(self.text_enc(**tk).text_embeds[0].unsqueeze(0), dim=-1)

            # 2. 将视频切分为片段 (Segments)
            segments = np.array_split(np.arange(total_frames), target_k)
            selected_indices = []

            # 3. 遍历片段，段内优选
            for seg_indices in segments:
                if len(seg_indices) == 0: continue
                
                # 策略: 默认选中中间那一帧 (保底)
                best_idx = seg_indices[len(seg_indices)//2]
                best_score = -999.0

                # 为了速度，如果片段太长，只检查首尾和中间
                check_indices = seg_indices
                if len(seg_indices) > 5:
                     # 取样 5 帧进行检查
                     check_indices = np.linspace(seg_indices[0], seg_indices[-1], 5, dtype=int)

                for idx in check_indices:
                    frame = frames[idx]
                    
                    # A. 视觉信息熵 (清晰度/细节丰富度) - 快速计算
                    # resize 小一点加快速度
                    gray = frame.convert("L").resize((112, 112))
                    entropy = np.var(np.array(gray)) 
                    
                    # B. 语义相关性 (CLIP)
                    img_tensor = self.preprocess(frame).to(self.device)
                    with torch.no_grad():
                        vis_out = self.vision(img_tensor.unsqueeze(0))
                        img_emb = F.normalize(vis_out.image_embeds, dim=-1)
                        clip_score = torch.matmul(img_emb, text_emb.T).item()
                    
                    # 综合分: 相关性为主，清晰度为辅
                    # entropy通常在几百到几千，除以 2000 归一化
                    score = clip_score * 0.8 + (entropy / 2000.0) * 0.2
                    
                    if score > best_score:
                        best_score = score
                        best_idx = idx
                
                selected_indices.append(best_idx)
            
            # 确保按时间顺序返回
            selected_indices = sorted(list(set(selected_indices)))
            return [frames[i] for i in selected_indices]

        except Exception as e:
            logger.error(f"S2 Selection Error: {e}")
            # 出错则均匀采样
            idx = np.linspace(0, total_frames-1, target_k, dtype=int)
            return [frames[i] for i in idx]

# ==============================================================================
# 🧩 模块 S3: RAG (知识库增强)
# ==============================================================================
class MarketingRAG:
    def __init__(self, kb_path, model_path, device='cuda'):
        self.active = False
        if RAG_AVAILABLE and os.path.exists(kb_path):
            try:
                self.model = SentenceTransformer(model_path, device=device)
                with open(kb_path, 'r') as f: self.kb = json.load(f)
                self.corpus = [e['marketing_logic'] for e in self.kb]
                self.embeddings = self.model.encode(self.corpus, normalize_embeddings=True)
                self.active = True
            except: pass

    def search(self, query, k=1):
        if not self.active: return ""
        try:
            q_vec = self.model.encode([query], normalize_embeddings=True)
            scores = np.dot(q_vec, self.embeddings.T)[0]
            top_idx = np.argsort(scores)[::-1][:k]
            # 标记为 Reference，防止模型过度依赖
            return f"Reference Concept: {self.kb[top_idx[0]]['marketing_logic']}"
        except: return ""

# ==============================================================================
# 🧩 模块 S4: 推理引擎 (Simple Video Mode)
# ==============================================================================
class InferenceEngine:
    def __init__(self, model_dir, device_id):
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_dir, torch_dtype=torch.float16, device_map="auto"
        )
        # 1280*1280 足够支持 32 帧的高清输入 (AnyRes)
        self.processor = AutoProcessor.from_pretrained(model_dir, min_pixels=256*256, max_pixels=1280*1280)
        self.device = self.model.device

    def generate(self, frames, prompt):
        # 使用标准的 Video 格式输入，让 Qwen 处理时序
        messages = [{"role": "user", "content": [
            {"type": "video", "video": frames}, 
            {"type": "text", "text": prompt}
        ]}]
        
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], videos=[frames], padding=True, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            gen_ids = self.model.generate(**inputs, do_sample=False, max_new_tokens=256)
            
        return self.processor.batch_decode(gen_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()

    def run_pipeline(self, frames, question, asr, rag_ctx):
        # 极简 Prompt: 移除思维链干扰，直接问答
        # 强音频注入: 不截断 asr
        
        content = f"""Question: {question}

Context Information:
- Audio Transcript: "{asr}"
- {rag_ctx}

Instruction:
Based on the video visuals and the audio transcript, answer the question directly and concisely.
"""
        ans = self.generate(frames, content)
        return ans

# ==============================================================================
# 主程序
# ==============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu_id", type=str, required=True)
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=-1)
    args = parser.parse_args()

    # 路径配置
    CONFIG = {
        "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
        "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
        "rag_model": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5",
        "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
        "video_root": "/data1/rmx/projectb/AdsQA-main/data/videos",
        "question": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
        "asr": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
        "output": "/data1/rmx/projectb/AdsQA-main/evaluation/188_final_adaptive" # 最终目录
    }

    logger.info(f"🚀 Launching Final Adaptive Attempt on GPU {args.gpu_id}")
    selector = AVAM_Selector(clip_path=CONFIG['clip_path'])
    rag = MarketingRAG(CONFIG['kb_file'], CONFIG['rag_model'])
    engine = InferenceEngine(CONFIG['model_dir'], args.gpu_id)

    with open(CONFIG['question']) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG['asr'])) if os.path.exists(CONFIG['asr']) else {}
    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
    # ⚠️ 采样验证 (如需全量跑请注释)
    # questions = questions[::30]

    os.makedirs(CONFIG['output'], exist_ok=True)

    for i, item in enumerate(tqdm(questions, desc=f"Shard {args.shard_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        qid = item['question_id']
        save_path = Path(CONFIG['output']) / qid / "prediction.json"
        if save_path.exists(): continue
        
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        vpath = os.path.join(CONFIG['video_root'], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG['video_root'], vid)

        raw_frames = []
        if DECORD_AVAILABLE:
            try:
                vr = VideoReader(vpath, ctx=cpu(0))
                # 预读 128 帧，确保有足够的池子做选择
                idx = np.linspace(0, len(vr)-1, 128, dtype=int)
                raw_frames = [Image.fromarray(vr[j].asnumpy()).convert("RGB") for j in idx]
            except: pass
        if not raw_frames: continue
        
        asr = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        # 1. S2: 选 32 帧 (分段自适应，返回原图)
        input_frames = selector.select_frames(raw_frames, item['question'], asr, target_k=32)
        
        # 2. S3: RAG
        rag_info = rag.search(f"{item['question']} {asr[:200]}")
        
        # 3. 推理
        ans = engine.run_pipeline(input_frames, item['question'], asr, rag_info)

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump({
                "question_id": qid, 
                "prediction": ans, 
                "pipeline": "Patent_Final_Adaptive", 
            }, f, indent=2, ensure_ascii=False)

    logger.info("Done.")

if __name__ == "__main__":
    main()