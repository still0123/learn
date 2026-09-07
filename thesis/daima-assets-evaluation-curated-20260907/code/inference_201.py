#!/usr/bin/env python3
"""
AdsQA Final Inference Engine (v207 - Segment-based AVAM)
Architecture: QAAR-STTC + Segment-based AVAM

[核心修复]: 解决 "Top-K 选帧导致时间坍塌" 的问题。
[专利策略]: "Temporally-Constrained Semantic Sampling" (时序约束语义采样)。
1. 将候选池 (64-128帧) 均匀切分为 N 个时间窗口 (Time Bins)。
2. 在每个窗口内，利用 CLIP 热力图选出分数最高的一帧。
3. 结果: 既保留了全视频的时序结构 (Structure)，又保证了关键帧的语义强度 (Relevance)。
"""

import sys
import os
import argparse
import json
import torch
import numpy as np
import logging
import glob
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
except ImportError:
    DECORD_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except: RAG_AVAILABLE = False

# ================= 日志配置 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [QAAR-207] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# ==============================================================================
# 🔥 模块 1: AVAM 分段热力选帧器 (Segment-based Heatmap) - [核心修改]
# ==============================================================================
class AVAM_Segment_Selector:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path and os.path.exists(clip_path):
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
                logger.info("✅ AVAM Segment Module Loaded")
            except Exception as e:
                logger.warning(f"⚠️ AVAM Init Failed: {e}")

    def select(self, frames, question, asr_text, category, target_k):
        """
        [专利逻辑]: 分段局部最优选择
        1. 把 frames 分成 target_k 个时间段。
        2. 每段选一个 CLIP 分数最高的。
        """
        total = len(frames)
        # 如果帧数不够切，直接返回全部
        if total <= target_k: 
            return frames
        
        # 如果模块失效，退化为均匀采样
        if not self.valid:
            indices = np.linspace(0, total-1, target_k, dtype=int)
            return [frames[i] for i in indices]

        try:
            # 1. 计算所有帧的分数
            # 构造 Query
            text_query = f"{question} {asr_text[:100]}"
            tk = self.tokenizer([text_query], padding=True, truncation=True, max_length=77, return_tensors="pt").to(self.device)
            with torch.no_grad():
                text_emb = F.normalize(self.text_enc(**tk).text_embeds[0].unsqueeze(0), dim=-1)

            scores = []
            batch_size = 32
            for i in range(0, total, batch_size):
                batch_frames = frames[i : i+batch_size]
                imgs = torch.stack([self.preprocess(f) for f in batch_frames]).to(self.device)
                with torch.no_grad():
                    vis_out = self.vision(imgs)
                    img_embs = F.normalize(vis_out.image_embeds, dim=-1)
                    sims = torch.matmul(img_embs, text_emb.T).squeeze().cpu().numpy()
                    if sims.ndim == 0: sims = [sims.item()]
                    scores.extend(sims)
            
            scores = np.array(scores)

            # 2. [核心] 分段选择 (Segment-based Selection)
            # 将所有帧的索引切分为 target_k 个片段
            all_indices = np.arange(total)
            segments = np.array_split(all_indices, target_k)
            
            selected_indices = []
            
            for seg in segments:
                if len(seg) == 0: continue
                
                # 策略分支:
                if category == "ACTION":
                    # Action 题: 优先保中间 (动作通常在中间最完整)，或者取分数最高的
                    # 这里为了兼顾“相关性”，我们取段内分数最高的
                    seg_scores = scores[seg]
                    best_in_seg = seg[np.argmax(seg_scores)]
                    selected_indices.append(best_in_seg)
                    
                elif category == "DETAIL":
                    # Detail 题: 必须最清晰/最相关。取段内 Max Score。
                    seg_scores = scores[seg]
                    best_in_seg = seg[np.argmax(seg_scores)]
                    selected_indices.append(best_in_seg)
                    
                else: # REASON
                    # Reason 题: 取段内 Max Score
                    seg_scores = scores[seg]
                    best_in_seg = seg[np.argmax(seg_scores)]
                    selected_indices.append(best_in_seg)

            # 3. 排序并返回 (虽然按顺序处理本来就是有序的，但保险起见)
            selected_indices = sorted(list(set(selected_indices)))
            return [frames[i] for i in selected_indices]

        except Exception as e:
            logger.error(f"AVAM Segment Select Error: {e}")
            # 出错回退到均匀
            indices = np.linspace(0, total-1, target_k, dtype=int)
            return [frames[i] for i in indices]

# ==============================================================================
# 🧠 模块 2: Token 压缩器
# ==============================================================================
class TokenCompressor:
    def compress(self, frames, category):
        if not frames: return [], "Empty"
        w, h = frames[0].size
        
        # 策略配置
        if category == "ACTION":
            target_res = 768  # 32帧 -> 强压缩
            note = "Spatial Compression (High)"
        elif category == "REASON":
            target_res = 896  # 16帧 -> 中压缩
            note = "Spatial Compression (Medium)"
        else: # DETAIL
            target_res = 1280 # 12帧 -> 原画质
            note = "No Compression (Native)"

        compressed_frames = []
        for img in frames:
            scale = target_res / max(w, h)
            if scale < 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                # Align to 28
                new_w = (new_w // 28) * 28
                new_h = (new_h // 28) * 28
                if new_w < 28: new_w = 28
                if new_h < 28: new_h = 28
                img_resized = img.resize((new_w, new_h), Image.BICUBIC)
                compressed_frames.append(img_resized)
            else:
                compressed_frames.append(img)
                
        return compressed_frames, note

# ==============================================================================
# 🧠 模块 3: 软语义路由器
# ==============================================================================
class SemanticRouter:
    def route(self, model, processor, question):
        q_upper = question.upper()
        # Keyword Heuristics
        hint = ""
        if any(k in q_upper for k in ["TEXT", "NUMBER", "PHONE", "LOGO", "URL"]): 
            hint = "(Hint: Visual details)"
        if any(k in q_upper for k in ["HAPPEN", "ACTION", "MOVING", "SEQUENCE"]): 
            hint = "(Hint: Temporal events)"

        # LLM Decision
        prompt = f"""Task: Categorize video question.
Question: "{question}" {hint}
Definitions:
1. DETAIL: OCR, text, logos, small objects.
2. ACTION: Events, movement, sequence.
3. REASON: Intent, theme, inference.
Output ONE word: DETAIL, ACTION, or REASON."""

        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], padding=True, return_tensors="pt").to(model.device)
        
        with torch.inference_mode():
            gen_ids = model.generate(**inputs, do_sample=False, max_new_tokens=10)
        
        category = processor.batch_decode(gen_ids, skip_special_tokens=True)[0].upper()
        
        if "DETAIL" in category: return "DETAIL"
        if "ACTION" in category: return "ACTION"
        return "REASON" 

# ==============================================================================
# 📚 模块 4: RAG
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
            except: pass

    def search(self, query, k=1):
        if not self.active: return ""
        try:
            q_vec = self.model.encode([query], normalize_embeddings=True)
            scores = np.dot(q_vec, self.embeddings.T)[0]
            top_idx = np.argsort(scores)[::-1][:k]
            return f"{self.kb[top_idx[0]]['marketing_logic']}"
        except: return ""

# ==============================================================================
# 🎮 模块 5: 推理引擎
# ==============================================================================
class InferenceEngine:
    def __init__(self, model_dir, device_id):
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_dir, torch_dtype=torch.float16, device_map="cuda", 
        )
        self.processor = AutoProcessor.from_pretrained(model_dir, min_pixels=256*256, max_pixels=1280*1280)
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
        
        if "<answer>" in full_text: return full_text.split("<answer>")[-1].split("</answer>")[0].strip()
        if "</think>" in full_text: return full_text.split("</think>")[-1].strip()
        return full_text.replace("Answer:", "").strip()

    def run_strategy(self, category, frames, question, asr, rag_info=""):
        if category == "DETAIL":
            prompt = f"""Question: {question}
Audio: "{asr}"
[Mode: DETAIL INSPECTION]
Instruction: Extract exact text/logo/details.
Output: <think>Locate...</think><answer>Final Answer</answer>"""
        elif category == "ACTION":
            prompt = f"""Question: {question}
Audio: "{asr}"
[Mode: ACTION TRACKING]
Instruction: Trace movement/events.
Output: <think>Trace flow...</think><answer>Final Answer</answer>"""
        else: # REASON
            prompt = f"""Question: {question}
Audio: "{asr}"
Knowledge: {rag_info}
[Mode: REASONING]
Instruction: Infer intent/theme.
Output: <think>Reason...</think><answer>Final Answer</answer>"""
        return self.generate_response(frames, prompt)

# ==============================================================================
# 🛠️ 辅助: 智能候选池加载
# ==============================================================================
def load_candidate_pool(vid, frames_root, video_root):
    candidates = []
    # 1. 优先文件夹
    frame_folder = os.path.join(frames_root, vid)
    if os.path.exists(frame_folder):
        images = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
        if len(images) >= 24: # 只有当本地已经有足够多的图时才用
            # 限制读取上限 128，防止 CLIP 算太慢
            if len(images) > 128:
                indices = np.linspace(0, len(images)-1, 128, dtype=int)
                candidates = [Image.open(images[j]).convert("RGB") for j in indices]
            else:
                candidates = [Image.open(p).convert("RGB") for p in images]
            return candidates, "Folder"

    # 2. 否则读视频 (自动补到 64 帧给 AVAM 挑)
    vpath = os.path.join(video_root, f"{vid}.mp4")
    if not os.path.exists(vpath): vpath = os.path.join(video_root, vid)
    
    if os.path.exists(vpath) and DECORD_AVAILABLE:
        try:
            vr = VideoReader(vpath, ctx=cpu(0))
            idx = np.linspace(0, len(vr)-1, 64, dtype=int)
            candidates = [Image.fromarray(vr[j].asnumpy()).convert("RGB") for j in idx]
            return candidates, "Video"
        except: pass

    return [], "None"

# ==============================================================================
# 主程序
# ==============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu_id", type=str, required=True)
    parser.add_argument('--frames_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data/frames_8')
    parser.add_argument('--file_dir', type=str, default='/data1/rmx/projectb/AdsQA-main/data')
    parser.add_argument("--shard_id", type=int, default=0)
    parser.add_argument("--num_shards", type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=-1)
    args = parser.parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)
    
    CONFIG = {
        "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
        "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
        "rag_model": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5",
        "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
        "frames_root": '/data1/rmx/projectb/AdsQA-main/data/frames_8',
        "video_root": "/data1/rmx/projectb/AdsQA-main/data/videos",
        "question": '/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json',
        "asr": '/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json',
        "output": "/data1/rmx/projectb/AdsQA-main/evaluation/201_segment_avam"
    }

    logger.info(f"🚀 Launching QAAR v207 (Segment-AVAM) on GPU {args.gpu_id}")
    
    engine = InferenceEngine(CONFIG['model_dir'], args.gpu_id)
    router = SemanticRouter()
    # 实例化分段热力选帧器
    avam = AVAM_Segment_Selector(clip_path=CONFIG['clip_path']) 
    compressor = TokenCompressor()
    rag = MarketingRAG(CONFIG['kb_file'], CONFIG['rag_model']) 

    with open(CONFIG['question']) as f: questions = json.load(f)
    if os.path.exists(CONFIG['asr']):
        with open(CONFIG['asr']) as f: asr_data = json.load(f)
    else: asr_data = {}

    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
    os.makedirs(CONFIG['output'], exist_ok=True)

    for i, item in enumerate(tqdm(questions, desc=f"Shard {args.shard_id}")):
        if i % args.num_shards != args.shard_id: continue
        qid = item['question_id']
        save_path = Path(CONFIG['output']) / qid / "prediction.json"
        if save_path.exists(): continue
        
        try:
            vid = item.get('video', item.get('video_id', qid.split('_')[0]))
            
            # 1. 加载候选池 (64帧)
            candidate_frames, src_type = load_candidate_pool(vid, CONFIG['frames_root'], CONFIG['video_root'])
            
            if not candidate_frames:
                logger.warning(f"Skipping {vid}")
                continue

            asr = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
            if i % 30 == 0: gc.collect(); torch.cuda.empty_cache()

            # === Pipeline ===
            category = router.route(engine.model, engine.processor, item['question'])
            
            # 2. AVAM 分段选帧 (保证时序覆盖 + 局部最优)
            target_k = 12 if category == "DETAIL" else (32 if category == "ACTION" else 16)
            selected_frames = avam.select(candidate_frames, item['question'], asr, category, target_k)
            
            # 3. Token 压缩
            compressed_frames, note = compressor.compress(selected_frames, category)
            
            # 4. RAG
            rag_info = ""
            if category == "REASON":
                rag_info = rag.search(f"{item['question']} {asr[:100]}")
            
            # 5. 生成
            final_ans = engine.run_strategy(category, compressed_frames, item['question'], asr, rag_info)

            # Save
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid, 
                    "prediction": final_ans, 
                    "pipeline": f"v207_SegAVAM_{category}",
                    "selection": "Segment_Heatmap",
                    "compression": note
                }, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error on {qid}: {e}")
            if "out of memory" in str(e).lower(): torch.cuda.empty_cache()

if __name__ == "__main__":
    main()