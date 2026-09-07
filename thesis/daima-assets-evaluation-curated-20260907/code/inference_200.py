#!/usr/bin/env python3
"""
AdsQA Final Inference Engine (v202 - Balanced Routing)
Architecture: QAAR (Question-Aware Adaptive Routing)
[修复核心问题]: 解决 Router 坍塌到 DETAIL 的问题。
[策略]: 引入 "Keyword Heuristics" (规则优先) + "Strict Prompting" (严格定义)。
"""

import sys
import os
import argparse
import json
import torch
import numpy as np
import logging
import re
import gc
from pathlib import Path
from tqdm import tqdm
from PIL import Image
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [QAAR-202] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧠 模块 1: 混合语义路由器 (Hybrid Router) - [核心修改]
# ==============================================================================
class SemanticRouter:
    def route(self, model, processor, question):
        q_upper = question.upper()
        
        # 1. === 规则优先 (Rule-Based Fast Path) ===
        # 强制 REASON 类: 只要问 为什么、主旨、受众、情感
        reason_keywords = ["WHY", "THEME", "MEANING", "INTENT", "AUDIENCE", "TONE", "MESSAGE", "STRATEGY", "PROMOTE", "EMPHASIZE", "IDEA", "INFER", "SUGGEST"]
        if any(k in q_upper for k in reason_keywords):
            return "REASON"

        # 强制 ACTION 类: 只要问 发生了什么、动作、顺序
        action_keywords = ["HAPPEN", "ACTION", "MOVING", "MOVEMENT", "SEQUENCE", "AFTER", "BEFORE", "PROCESS", "EVENT", "START", "END"]
        if any(k in q_upper for k in action_keywords):
            return "ACTION"
            
        # 强制 DETAIL 类: 只要问 字幕、颜色、数字、电话
        detail_keywords = ["TEXT", "NUMBER", "PHONE", "PRICE", "COLOR", "LOGO", "WRITTEN", "SAY", "URL", "WEBSITE", "ADDRESS", "CONTACT"]
        if any(k in q_upper for k in detail_keywords):
            return "DETAIL"

        # 2. === LLM 深度判断 (LLM Slow Path) ===
        # 只有模棱两可的题才走这里 (Prompt 更加严格)
        prompt = f"""Task: Categorize the video question into exactly one type.

Definitions:
1. DETAIL: STRICTLY for reading text (OCR), recognizing small logos, phone numbers, prices, or counting tiny objects.
2. ACTION: Asking about a sequence of events, what someone is doing, or plot movement.
3. REASON: Asking about the "Whole Picture", abstract concepts, atmosphere, or deducing information not directly seen.

Question: "{question}"

Output ONE word: DETAIL, ACTION, or REASON."""

        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], padding=True, return_tensors="pt").to(model.device)
        
        with torch.inference_mode():
            gen_ids = model.generate(**inputs, do_sample=False, max_new_tokens=5)
        
        category = processor.batch_decode(gen_ids, skip_special_tokens=True)[0].upper()
        
        if "ACTION" in category: return "ACTION"
        if "REASON" in category: return "REASON"
        return "DETAIL" # 默认兜底

# ==============================================================================
# 🧩 模块 2: 双流选帧工具 (Detail Mode)
# ==============================================================================
class AVAM_Selector:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path:
            try:
                self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.tokenizer = CLIPTokenizer.from_pretrained(clip_path)
                from torchvision.transforms import ToTensor, Normalize, Resize, Compose
                self.preprocess = Compose([Resize((224, 224), interpolation=Image.BICUBIC), ToTensor(), Normalize((0.481, 0.457, 0.408), (0.268, 0.261, 0.275))])
                self.valid = True
            except: pass

    def select_dual_stream(self, frames, base_k=8):
        if not frames: return []
        indices = np.linspace(0, len(frames)-1, base_k, dtype=int)
        output_frames = []
        for idx in indices:
            frame = frames[idx]
            output_frames.append(frame) # Global
            w, h = frame.size
            # Center Zoom 优化: 既然已经确认为 DETAIL 题，说明目标很小，
            # 我们把裁剪框缩小到 50% (0.25-0.75)，放大倍率更高，看得更清。
            box = (w*0.25, h*0.25, w*0.75, h*0.75) 
            local_frame = frame.crop(box).resize((w, h), Image.BICUBIC)
            output_frames.append(local_frame)
        return output_frames

# ==============================================================================
# 📚 模块 3: 知识检索 (Reason Mode)
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
                logger.info("✅ RAG Module Loaded")
            except Exception as e: 
                logger.warning(f"⚠️ RAG Init Failed: {e}")

    def search(self, query, k=1):
        if not self.active: return "General marketing principles apply."
        try:
            q_vec = self.model.encode([query], normalize_embeddings=True)
            scores = np.dot(q_vec, self.embeddings.T)[0]
            top_idx = np.argsort(scores)[::-1][:k]
            return f"{self.kb[top_idx[0]]['marketing_logic']}"
        except: return "General marketing principles apply."

# ==============================================================================
# 🎮 模块 4: 推理执行引擎
# ==============================================================================
class InferenceEngine:
    def __init__(self, model_dir, device_id):
        # 移除 auto map，直接 cuda
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_dir, 
            torch_dtype=torch.float16, 
            device_map="cuda", 
        )
        self.processor = AutoProcessor.from_pretrained(model_dir, min_pixels=256*256, max_pixels=1008*1008)
        self.device = self.model.device

    def generate_response(self, frames, prompt):
        messages = [{"role": "user", "content": [
            {"type": "video", "video": frames},
            {"type": "text", "text": prompt}
        ]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], videos=[frames], padding=True, return_tensors="pt").to(self.device)
        
        with torch.inference_mode(): 
            gen_ids = self.model.generate(**inputs, do_sample=False, max_new_tokens=512)
        
        full_text = self.processor.batch_decode(gen_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
        
        match = re.search(r"<answer>(.*?)</answer>", full_text, re.DOTALL)
        if match: return match.group(1).strip()
        if "</think>" in full_text: return full_text.split("</think>")[-1].strip()
        return full_text.replace("Answer:", "").strip()

    # --- 策略实现 (Prompt 已优化) ---
    def run_detail_strategy(self, avam, raw_frames, question, asr):
        # 16 帧 (8 Global + 8 Local)
        frames = avam.select_dual_stream(raw_frames, base_k=8)
        prompt = f"""Question: {question}
[Context] Audio: "{asr}"
[Strategy: DETAIL FOCUS]
Input includes ZOOM-IN frames to see small text/logos clearly.
[Task] Provide a direct, complete sentence. 
**CRITICAL**: Answer ONLY what is asked (e.g. if asked "Who", do not mention "When")."""
        return self.generate_response(frames, prompt)

    def run_action_strategy(self, raw_frames, question, asr):
        # 32 帧 (High FPS)
        idx = np.linspace(0, len(raw_frames)-1, 32, dtype=int)
        frames = [raw_frames[i] for i in idx]
        prompt = f"""Question: {question}
[Context] Audio: "{asr}"
[Strategy: ACTION FLOW]
Watching high-frame-rate sequence (32 frames) for smooth movement.
[Task] Describe the action/event in a direct, complete sentence."""
        return self.generate_response(frames, prompt)

    def run_reason_strategy(self, raw_frames, question, asr, rag_info):
        # 16 帧 (Standard) + RAG
        idx = np.linspace(0, len(raw_frames)-1, 16, dtype=int)
        frames = [raw_frames[i] for i in idx]
        prompt = f"""Question: {question}
[Context] Audio: "{asr}"
[Knowledge] {rag_info}
[Strategy: REASONING]
Infer the intent/theme based on visuals + audio + marketing logic.
[Output]
<think>Analysis...</think>
<answer>(Direct complete sentence)</answer>"""
        return self.generate_response(frames, prompt)

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

    CONFIG = {
        "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
        "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
        "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
        "video_root": "/data1/rmx/projectb/AdsQA-main/data/videos",
        "question": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
        "asr": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
        "output": "/data1/rmx/projectb/AdsQA-main/evaluation/202_qaar_new",
        "rag_model": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5"
    }

    logger.info(f"🚀 Launching QAAR (Inference 202 - Balanced) on GPU {args.gpu_id}")
    
    gc.collect()
    torch.cuda.empty_cache()
    
    engine = InferenceEngine(CONFIG['model_dir'], args.gpu_id)
    router = SemanticRouter()
    avam = AVAM_Selector(clip_path=CONFIG['clip_path'])
    rag = MarketingRAG(CONFIG['kb_file'], CONFIG['rag_model']) 

    with open(CONFIG['question']) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG['asr'])) if os.path.exists(CONFIG['asr']) else {}
    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
    # questions = questions[::30] # 全量跑请保持注释

    os.makedirs(CONFIG['output'], exist_ok=True)

    for i, item in enumerate(tqdm(questions, desc=f"Shard {args.shard_id}")):
        if i % args.num_shards != args.shard_id: continue
        qid = item['question_id']
        save_path = Path(CONFIG['output']) / qid / "prediction.json"
        if save_path.exists(): continue
        
        try:
            vid = item.get('video', item.get('video_id', qid.split('_')[0]))
            vpath = os.path.join(CONFIG['video_root'], f"{vid}.mp4")
            if not os.path.exists(vpath): vpath = os.path.join(CONFIG['video_root'], vid)

            raw_frames = []
            if DECORD_AVAILABLE:
                try:
                    vr = VideoReader(vpath, ctx=cpu(0))
                    idx = np.linspace(0, len(vr)-1, 64, dtype=int)
                    raw_frames = [Image.fromarray(vr[j].asnumpy()).convert("RGB") for j in idx]
                except: pass
            if not raw_frames: continue
            
            asr = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
            
            if i % 20 == 0:
                gc.collect()
                torch.cuda.empty_cache()

            # 1. 路由 (Hybrid: Rule + LLM)
            category = router.route(engine.model, engine.processor, item['question'])
            
            # 2. 策略
            final_ans = ""
            pipeline_info = f"QAAR_{category}"
            
            if category == "DETAIL":
                final_ans = engine.run_detail_strategy(avam, raw_frames, item['question'], asr)
            elif category == "ACTION":
                final_ans = engine.run_action_strategy(raw_frames, item['question'], asr)
            else: # REASON
                rag_info = rag.search(f"{item['question']} {asr[:100]}")
                final_ans = engine.run_reason_strategy(raw_frames, item['question'], asr, rag_info)

            # Save
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid, 
                    "prediction": final_ans, 
                    "pipeline": pipeline_info,
                    "category": category
                }, f, indent=2, ensure_ascii=False)
                
        except RuntimeError as e:
            if "out of memory" in str(e):
                logger.error(f"OOM on {qid}, clearing cache.")
                torch.cuda.empty_cache()
            else:
                logger.error(f"Error on {qid}: {e}")
        except Exception as e:
            logger.error(f"Error on {qid}: {e}")

if __name__ == "__main__":
    main()