#!/usr/bin/env python3
"""
AdsQA Final Inference Engine (v303 - Balanced & Comprehensive)
Architecture: QAAR-Balanced

[优化目标]: "Strict > Baseline" AND "Relaxed ≈ Baseline"
[核心策略]:
1. Type 2 (Detail): "Concise Mode" - 只要核心词，去除冗余句式，提升 Strict/Relaxed。
2. Type 3/5 (Reason): "Comprehensive Mode" - 要求结合多模态信息生成内容丰富的回答，以此挽回 Relaxed 分数。
3. Type 1/4 (Action): "CoT Mode" - 保持 v301 的高精度逻辑。
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [QAAR-303] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# ==============================================================================
# 🔥 模块 1: AVAM 热力图引擎
# ==============================================================================
class AVAM_Heatmap_Engine:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path and os.path.exists(clip_path):
            try:
                self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path).to(device).eval()
                self.tokenizer = CLIPTokenizer.from_pretrained(clip_path)
                from torchvision.transforms import ToTensor, Normalize, Resize, Compose
                self.preprocess = Compose([Resize((224, 224), interpolation=Image.BICUBIC), ToTensor(), Normalize((0.481, 0.457, 0.408), (0.268, 0.261, 0.275))])
                self.valid = True
            except: pass

    def compute_heatmap_scores(self, frames, question, asr_text):
        if not self.valid or not frames: return None
        try:
            text_query = f"{question} {asr_text[:100]}"
            tk = self.tokenizer([text_query], padding=True, truncation=True, max_length=77, return_tensors="pt").to(self.device)
            with torch.no_grad():
                text_emb = F.normalize(self.text_enc(**tk).text_embeds[0].unsqueeze(0), dim=-1)
            scores = []
            for i in range(0, len(frames), 32):
                batch = frames[i : i+32]
                imgs = torch.stack([self.preprocess(f) for f in batch]).to(self.device)
                with torch.no_grad():
                    vis_out = self.vision(imgs)
                    img_embs = F.normalize(vis_out.image_embeds, dim=-1)
                    sims = torch.matmul(img_embs, text_emb.T).squeeze().cpu().numpy()
                    if sims.ndim == 0: sims = [sims.item()]
                    scores.extend(sims)
            return np.array(scores)
        except: return None

# ==============================================================================
# 🧩 模块 2: 混合选帧器
# ==============================================================================
class HybridFrameSelector:
    def __init__(self, avam_engine):
        self.avam = avam_engine

    def select(self, frames, category, question, asr):
        total = len(frames)
        if total == 0: return []
        def get_uniform(k):
            if total <= k: return np.arange(total)
            return np.linspace(0, total-1, k, dtype=int)

        if category == "ACTION":
            # 保持 32 帧的高时序精度 (你在这里赢了9%)
            return [frames[i] for i in get_uniform(32)], "Uniform (Temporal 32)"
        
        elif category == "DETAIL":
            # OCR 只需要覆盖率，16帧足够
            return [frames[i] for i in get_uniform(16)], "Uniform (Coverage 16)"
        
        else: # REASON
            # 混合模式：8帧骨架 + 8帧高光
            scores = self.avam.compute_heatmap_scores(frames, question, asr)
            if scores is None: return [frames[i] for i in get_uniform(16)], "Uniform (Fallback)"
            highlight = np.argsort(scores)[::-1][:8]
            struct = get_uniform(8)
            final = sorted(list(set(highlight) | set(struct)))
            return [frames[int(i)] for i in final], f"Hybrid (Struct+High) {len(final)}"

# ==============================================================================
# 🧠 模块 3: 路由器
# ==============================================================================
class SemanticRouter:
    def route(self, model, processor, question):
        q_upper = question.upper()
        hint = ""
        if any(k in q_upper for k in ["TEXT", "NUMBER", "PHONE", "LOGO", "URL"]): hint = "(Visual details)"
        if any(k in q_upper for k in ["HAPPEN", "ACTION", "MOVING", "SEQUENCE"]): hint = "(Temporal events)"
        prompt = f"""Task: Categorize video question. Question: "{question}" {hint}
Definitions:
1. DETAIL: OCR, text, logos.
2. ACTION: Events, movement.
3. REASON: Intent, theme.
Output ONE word: DETAIL, ACTION, or REASON."""
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text], padding=True, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            gen_ids = model.generate(**inputs, do_sample=False, max_new_tokens=10)
        cat = processor.batch_decode(gen_ids, skip_special_tokens=True)[0].upper()
        if "DETAIL" in cat: return "DETAIL"
        if "ACTION" in cat: return "ACTION"
        return "REASON"

# ==============================================================================
# 🧠 模块 4: 分辨率管理
# ==============================================================================
class ResolutionManager:
    def process(self, frames, category):
        if not frames: return []
        w, h = frames[0].size
        # DETAIL 必须 1280px，其他 1008px 足够
        target = 1008 if category in ["ACTION", "REASON"] else 1280
        proc = []
        for img in frames:
            scale = target / max(w, h)
            if scale < 1.0:
                nw, nh = (int(w*scale)//28)*28, (int(h*scale)//28)*28
                proc.append(img.resize((nw, max(28, nh)), Image.BICUBIC))
            else: proc.append(img)
        return proc

# ==============================================================================
# 📚 模块 5: RAG
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
            return f"{self.kb[np.argsort(scores)[::-1][0]]['marketing_logic']}"
        except: return ""

# ==============================================================================
# 🎮 模块 6: 推理引擎 (Balanced Edition)
# ==============================================================================
class InferenceEngine:
    def __init__(self, model_dir, device_id):
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_dir, torch_dtype=torch.float16, device_map="cuda")
        self.processor = AutoProcessor.from_pretrained(model_dir, min_pixels=256*256, max_pixels=1280*1280)
        self.device = self.model.device

    def generate_response(self, frames, prompt):
        messages = [{"role": "user", "content": [{"type": "video", "video": frames}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], videos=[frames], padding=True, return_tensors="pt").to(self.device)
        with torch.inference_mode(): 
            gen_ids = self.model.generate(**inputs, do_sample=False, max_new_tokens=512)
        return self.processor.batch_decode(gen_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()

    def run_strategy(self, category, frames, question, asr, rag_info=""):
        
        # [策略 1: DETAIL] -> 极简模式 (挽回 Type 2 分数)
        if category == "DETAIL":
            prompt = f"""Question: {question}
Audio Context: "{asr}"
[Mode: EXACT EXTRACTION]
Instruction: 
1. Locate the text, logo, or object.
2. Output ONLY the extracted text or object name. Do NOT use full sentences.
3. Be exact with spelling and numbers.

Output Format:
<think>Locating...</think>
<answer>[Exact Text/Name]</answer>"""

        # [策略 2: ACTION] -> 维持现状 (你已经赢了)
        elif category == "ACTION":
            prompt = f"""Question: {question}
Audio Context: "{asr}"
[Mode: ACTION TRACKING]
Instruction: 
1. Analyze the sequence of events.
2. Answer in a complete, descriptive sentence.

Output Format:
<think>First [X] happens, then [Y]...</think>
<answer>In the video, [Subject] does [Action]...</answer>"""

        # [策略 3: REASON] -> 全面模式 (挽回 Relaxed 分数)
        else: # REASON
            prompt = f"""Question: {question}
Audio Context: "{asr}"
Context: {rag_info}
[Mode: COMPREHENSIVE REASONING]
Instruction: 
1. Combine visuals, audio, and marketing logic.
2. Provide a COMPREHENSIVE answer that explains the main point and includes supporting details from the video.
3. Make sure the answer is self-contained and convincing.

Output Format:
<think>Synthesizing visual and audio cues...</think>
<answer>[Comprehensive Answer]</answer>"""
            
        return self.generate_response(frames, prompt)

# ==============================================================================
# 🛠️ 辅助: 加载
# ==============================================================================
def load_frames(vid, frames_root, video_root):
    frame_folder = os.path.join(frames_root, vid)
    if os.path.exists(frame_folder):
        images = sorted(glob.glob(os.path.join(frame_folder, "*.[jp][pn]g")))
        if len(images) >= 16:
            indices = np.linspace(0, len(images)-1, 64, dtype=int) if len(images)>64 else np.arange(len(images))
            return [Image.open(images[j]).convert("RGB") for j in indices], "Folder"
    
    vpath = os.path.join(video_root, f"{vid}.mp4")
    if not os.path.exists(vpath): vpath = os.path.join(video_root, vid)
    if os.path.exists(vpath) and DECORD_AVAILABLE:
        try:
            vr = VideoReader(vpath, ctx=cpu(0))
            idx = np.linspace(0, len(vr)-1, 64, dtype=int)
            return [Image.fromarray(vr[j].asnumpy()).convert("RGB") for j in idx], "Video"
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

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
    
    CONFIG = {
        "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
        "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
        "rag_model": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5",
        "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
        "frames_root": args.frames_dir,
        "video_root": "/data1/rmx/projectb/AdsQA-main/data/videos",
        "question": os.path.join(args.file_dir, "testset_question.json"),
        "asr": os.path.join(args.file_dir, "asr_set.json"),
        "output": "/data1/rmx/projectb/AdsQA-main/evaluation/401"
    }

    logger.info(f"🚀 Launching QAAR v303 (Balanced) on GPU {args.gpu_id}")
    
    engine = InferenceEngine(CONFIG['model_dir'], args.gpu_id)
    router = SemanticRouter()
    avam = AVAM_Heatmap_Engine(CONFIG['clip_path']) 
    selector = HybridFrameSelector(avam)               
    res_mgr = ResolutionManager()
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
            raw_frames, src_type = load_frames(vid, CONFIG['frames_root'], CONFIG['video_root'])
            if not raw_frames: continue
            asr = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
            if i % 30 == 0: gc.collect(); torch.cuda.empty_cache()

            category = router.route(engine.model, engine.processor, item['question'])
            selected_frames, sel_note = selector.select(raw_frames, category, item['question'], asr)
            final_frames = res_mgr.process(selected_frames, category)
            
            rag_info = ""
            if category == "REASON": rag_info = rag.search(f"{item['question']} {asr[:100]}")
            
            # 执行 v303 均衡策略
            final_ans = engine.run_strategy(category, final_frames, item['question'], asr, rag_info)

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid, 
                    "prediction": final_ans, 
                    "pipeline": f"v303_Balanced_{category}",
                    "category": category
                }, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error on {qid}: {e}")
            if "out of memory" in str(e).lower(): torch.cuda.empty_cache()

if __name__ == "__main__":
    main()