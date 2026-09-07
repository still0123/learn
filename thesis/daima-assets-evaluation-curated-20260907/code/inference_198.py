#!/usr/bin/env python3
"""
AdsQA Patent Compliant Edition (Dual-Stream + RAG + CoT/Reflection)
文件名: inference_patent_compliant.py

[专利权利要求对齐]:
1. S2 (Dual-Stream): 使用 Audio-Text 对齐技术，在时域上自适应选择 Visual Frames。
2. S3 (RAG): 引入外部 Marketing Knowledge Base。
3. S4/S5 (Reasoning): 强制模型执行 "Observation -> Reflection -> Answer" 的思维链。
4. 评估优化: 输出"Direct Complete Sentence"，平衡 Strict 和 Relaxed 准确率。
"""

import sys
import os
import argparse
import json
import torch
import numpy as np
import logging
import re
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
    format='%(asctime)s - [Patent-Compliance] %(message)s', 
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 🧩 模块 S2: 视听双流计算与自适应选帧 (Audio-Visual Selection)
# ==============================================================================
class DualStream_Selector:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path:
            try:
                self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.tokenizer = CLIPTokenizer.from_pretrained(clip_path)
                from torchvision.transforms import ToTensor, Normalize, Resize, Compose
                self.preprocess = Compose([
                    Resize((224, 224), interpolation=Image.BICUBIC),
                    ToTensor(),
                    Normalize((0.481, 0.457, 0.408), (0.268, 0.261, 0.275))
                ])
                self.valid = True
            except Exception as e:
                logger.error(f"⚠️ [S2] Init Failed: {e}")

    def select_frames(self, frames, question, asr_text, target_k=16):
        """
        专利点: 双流交互。
        使用 Audio (asr_text) 的语义向量去"激活" Video (frames) 中的关键帧。
        """
        total_frames = len(frames)
        if total_frames <= target_k: return frames
        
        # Fallback: 均匀采样
        if not self.valid:
            idx = np.linspace(0, total_frames-1, target_k, dtype=int)
            return [frames[i] for i in idx]

        try:
            # 1. 音频/文本流编码
            # 融合 Question 和 Audio 信息
            text_input = f"{question} {asr_text}" # 不截断，保留更多语义
            tk = self.tokenizer([text_input], padding=True, truncation=True, max_length=77, return_tensors="pt").to(self.device)
            with torch.no_grad():
                text_emb = F.normalize(self.text_enc(**tk).text_embeds[0].unsqueeze(0), dim=-1)

            # 2. 视觉流分段处理 (Segment-based)
            # 将视频划分为 target_k 个片段，保证时序覆盖
            segments = np.array_split(np.arange(total_frames), target_k)
            selected_indices = []

            for seg_indices in segments:
                if len(seg_indices) == 0: continue
                
                # 默认选中间帧
                best_idx = seg_indices[len(seg_indices)//2]
                best_score = -999.0
                
                # 在片段内采样几帧进行 Audio-Visual 对齐计算
                check_indices = seg_indices
                if len(seg_indices) > 5:
                     check_indices = np.linspace(seg_indices[0], seg_indices[-1], 5, dtype=int)

                for idx in check_indices:
                    frame = frames[idx]
                    
                    # 计算视觉信息熵 (代表画面丰富度)
                    gray = frame.convert("L").resize((112, 112))
                    entropy = np.var(np.array(gray)) 
                    
                    # 计算图文匹配度 (代表语义相关性)
                    img_tensor = self.preprocess(frame).to(self.device)
                    with torch.no_grad():
                        vis_out = self.vision(img_tensor.unsqueeze(0))
                        img_emb = F.normalize(vis_out.image_embeds, dim=-1)
                        clip_score = torch.matmul(img_emb, text_emb.T).item()
                    
                    # 综合评分: 相关性优先(0.8)，清晰度为辅(0.2)
                    score = clip_score * 0.8 + (entropy / 2000.0) * 0.2
                    
                    if score > best_score:
                        best_score = score
                        best_idx = idx
                
                selected_indices.append(best_idx)
            
            selected_indices = sorted(list(set(selected_indices)))
            return [frames[i] for i in selected_indices]

        except Exception as e:
            logger.error(f"S2 Error: {e}")
            idx = np.linspace(0, total_frames-1, target_k, dtype=int)
            return [frames[i] for i in idx]

# ==============================================================================
# 🧩 模块 S3: RAG 知识检索
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
            # 提供为 "Expert Knowledge"，用于 CoT 阶段的参考
            return f"Expert Marketing Knowledge: {self.kb[top_idx[0]]['marketing_logic']}"
        except: return ""

# ==============================================================================
# 🧩 模块 S4/S5: 思维链与反思推理 (CoT + Reflection)
# ==============================================================================
class CoTEngine:
    def __init__(self, model_dir, device_id):
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_dir, torch_dtype=torch.float16, device_map="auto"
        )
        # 16帧 * 1008x1008，显存安全配置
        self.processor = AutoProcessor.from_pretrained(model_dir, min_pixels=256*256, max_pixels=1008*1008)
        self.device = self.model.device

    def generate(self, frames, prompt):
        messages = [{"role": "user", "content": [
            {"type": "video", "video": frames}, 
            {"type": "text", "text": prompt}
        ]}]
        
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], videos=[frames], padding=True, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            # 增加 token 上限，因为 CoT 需要输出思考过程
            gen_ids = self.model.generate(**inputs, do_sample=False, max_new_tokens=512)
            
        return self.processor.batch_decode(gen_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()

    def run_pipeline(self, frames, question, asr, rag_ctx):
        # [核心优化] 平衡 Strict (准确性) 和 Relaxed (完整性) 的 Prompt
        
        cot_prompt = f"""Question: {question}

[Input Sources]
1. Visuals: (See input frames)
2. Audio Transcript: "{asr}"
3. Knowledge Base: {rag_ctx}

[Instruction]
You are an expert advertising analyst.
1. **Observation**: Identify visual details (text, products, actions) and combine with audio.
2. **Reflection**: Verify details. Ensure numbers, prices, and brand names are correct.
3. **Answer**: Provide a **direct, complete sentence** containing the key information.
   - ❌ Avoid too short: "60 minutes" (Might be penalized for lack of context)
   - ❌ Avoid too verbose: "Based on the analysis of the video..." (Might contain hallucinations)
   - ✅ Perfect: "The delivery time is 60 minutes."

[Output Format]
<think>
[Observation]: ...
[Reflection]: ...
</think>
<answer>
(Your direct, complete English sentence here)
</answer>"""
        
        # 1. 生成完整 CoT 响应
        full_response = self.generate(frames, cot_prompt)
        
        # 2. 解析输出 (提取 Answer 用于评测)
        final_answer = full_response
        reasoning_trace = full_response
        
        # 使用正则提取 <answer> 标签内的内容
        match = re.search(r"<answer>(.*?)</answer>", full_response, re.DOTALL)
        if match:
            final_answer = match.group(1).strip()
        else:
            # Fallback 策略
            if "</think>" in full_response:
                final_answer = full_response.split("</think>")[-1].strip()
            final_answer = final_answer.replace("Answer:", "").strip()
        
        return final_answer, reasoning_trace

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
        "output": "/data1/rmx/projectb/AdsQA-main/evaluation/198" 
    }

    logger.info(f"🚀 Launching Patent Compliant Edition on GPU {args.gpu_id}")
    
    # 初始化各模块
    dual_stream = DualStream_Selector(clip_path=CONFIG['clip_path']) # S2
    rag = MarketingRAG(CONFIG['kb_file'], CONFIG['rag_model'])       # S3
    engine = CoTEngine(CONFIG['model_dir'], args.gpu_id)             # S4/S5

    with open(CONFIG['question']) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG['asr'])) if os.path.exists(CONFIG['asr']) else {}
    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
    # ⚠️ 采样验证 (如需全量跑请注释下面这行)
    questions = questions[::30]

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
                # 预读 64 帧做池子
                idx = np.linspace(0, len(vr)-1, 64, dtype=int)
                raw_frames = [Image.fromarray(vr[j].asnumpy()).convert("RGB") for j in idx]
            except: pass
        if not raw_frames: continue
        
        asr = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        # 1. 专利 S2: 双流自适应选帧 (16帧)
        input_frames = dual_stream.select_frames(raw_frames, item['question'], asr, target_k=16)
        
        # 2. 专利 S3: RAG 检索
        rag_info = rag.search(f"{item['question']} {asr[:200]}")
        
        # 3. 专利 S4/S5: CoT + Reflection 推理
        final_ans, full_trace = engine.run_pipeline(input_frames, item['question'], asr, rag_info)

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump({
                "question_id": qid, 
                "prediction": final_ans,   # 这里的答案是干净的，供 Llama-3 评测
                "reasoning_trace": full_trace, # 这里保留完整的思维链，供专利证明
                "pipeline": "Patent_Compliance_Suite", 
            }, f, indent=2, ensure_ascii=False)

    logger.info("Done.")

if __name__ == "__main__":
    main()