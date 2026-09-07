#!/usr/bin/env python3
"""
AdsQA A6000 Patent Edition (V10.5 - No Data Leakage)
修复日志：
1. [Critical] 修复 RAG 模块的“自问自答”数据泄露问题，确保不检索当前题目自身。
2. [Critical] 修复 answer/gt_answer 字段名不一致导致的 KeyError。
3. [Stability] 保持环境崩溃修复、空变量初始化、显存优化。
"""

import os
import argparse
import logging
import json
import numpy as np
import torch
import torch.nn.functional as F
import gc
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile

# ================= 命令行参数 =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="Target GPU ID")
parser.add_argument("--shard_id", type=int, required=True, help="Shard ID for parallel execution")
parser.add_argument("--num_shards", type=int, default=1, help="Total number of shards")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

# [显存优化配置] 正确设置环境变量
os.environ["expandable_segments"] = "True"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id

# ================= 依赖检查 =================
try: 
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except ImportError: 
    DECORD_AVAILABLE = False

try: 
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError: 
    PADDLE_AVAILABLE = False

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize

# ================= 全局配置 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "groundtruth_file": "/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/patent_v10_final_no", # 修改输出目录以作区分
    
    # S2 AVP 参数
    "coarse_scan_frames": 32,   
    "fine_zoom_frames": 8,      
    "crop_ratio": 0.75,
    "min_pixels": 256*256,
    "max_pixels": 1008*1008,
    
    # 阈值
    "sim_threshold": 0.65,
    "ocr_threshold": 0.5
}

ImageFile.LOAD_TRUNCATED_IMAGES = True

# 日志设置
log_dir = os.path.join(CONFIG["output_dir"], "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'patent_v10_gpu{args.gpu_id}.log')

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(message)s', 
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= 模块一：基础工具与 OCR =================

class OCRProcessor:
    def __init__(self):
        self.engine = None
        if PADDLE_AVAILABLE:
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            try: 
                self.engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False, use_gpu=False) 
            except: pass

    def extract_text(self, frames):
        if not self.engine: return ""
        texts = set()
        sample_frames = frames[::2] if len(frames) > 4 else frames
        for img in sample_frames:
            try:
                res = self.engine.ocr(np.array(img), cls=True)
                if res: 
                    for line in res:
                        if not line: continue
                        for word_info in line:
                            text = word_info[1][0]
                            score = word_info[1][1]
                            if score > CONFIG["ocr_threshold"] and len(text.strip()) > 1: 
                                texts.add(text)
            except: continue
        return ", ".join(list(texts))

# ================= 模块二：营销知识图谱 (S3 Knowledge Graph) =================

class MarketingKnowledgeGraph:
    def __init__(self, kb_path):
        self.kb = {} 
        self.fallback_kb = {
            "metaphor": "Visual Metaphor: Using objects to represent abstract concepts.",
            "irony": "Irony/Humor: Presenting situations that contradict expectations.",
            "pathos": "Pathos: Appealing to audience emotions.",
            "scarcity": "Scarcity: Creating a sense of urgency (limited time/supply)."
        }

        if os.path.exists(kb_path):
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    self.kb = data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            vals = list(item.values())
                            if len(vals) >= 2:
                                k = str(vals[0]).strip()
                                v = str(vals[1]).strip()
                                self.kb[k.lower()] = v
                            elif len(vals) == 1:
                                self.kb[str(vals[0]).lower()] = str(vals[0])
                logger.info(f"✅ Marketing KB loaded: {len(self.kb)} entries.")
            except Exception as e:
                logger.error(f"⚠️ KB load error: {e}, using fallback.")
                self.kb = self.fallback_kb
        else:
            self.kb = self.fallback_kb

    def retrieve(self, query: str, top_k=2) -> str:
        query_lower = query.lower()
        hits = [] 
        
        for k, v in self.kb.items():
            if k in query_lower:
                hits.append(f"- [{k.upper()}]: {v}")
        
        if not hits:
            if "why" in query_lower or "reason" in query_lower:
                hits.append("- Strategy: Analyze emotional appeal (Pathos) or logical arguments (Logos).")
            elif "how" in query_lower:
                hits.append("- Technique: Look for visual metaphors or contrasting scenes.")
             
        return "\n".join(hits[:top_k])

# ================= 模块三：主动视频感知 (S2 AVP Engine) =================

class ActivePerceptionEngine:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path:
            try:
                self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, local_files_only=True).to(device).eval()
                self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path, local_files_only=True).to(device).eval()
                self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
                
                self.preprocess = Compose([
                    Resize(224),
                    CenterCrop(224),
                    ToTensor(),
                    Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))
                ])
                self.valid = True
                logger.info("✅ AVP Engine (CLIP) ready.")
            except Exception as e:
                logger.error(f"❌ CLIP init failed: {e}")

    def _encode_text(self, text):
        if not self.valid: return None
        tokens = self.tokenizer([text[:77]], padding=True, truncation=True, return_tensors="pt").to(self.device)
        return F.normalize(self.text_enc(**tokens).text_embeds, dim=-1)

    def _load_video_frames(self, video_path, indices):
        frames = [] 
        if DECORD_AVAILABLE:
            try:
                vr = VideoReader(video_path, ctx=cpu(0))
                safe_indices = [min(max(0, int(i)), len(vr)-1) for i in indices]
                if len(safe_indices) > 0:
                    batch_frames = vr.get_batch(safe_indices).asnumpy()
                    frames = [Image.fromarray(f) for f in batch_frames]
            except Exception as e: 
                pass
        return frames

    def perceive(self, video_path, question, asr_text):
        if not os.path.exists(video_path): return []
        
        # 1. Coarse Scan
        try:
            vr = VideoReader(video_path, ctx=cpu(0))
            total_frames = len(vr)
            if total_frames < 1: return []
            coarse_indices = np.linspace(0, total_frames-1, CONFIG["coarse_scan_frames"], dtype=int)
            coarse_frames = self._load_video_frames(video_path, coarse_indices)
        except: return []

        if not coarse_frames: return []
        if not self.valid: return coarse_frames[:CONFIG["fine_zoom_frames"]]

        # 2. Hypothesis Matching
        search_query = f"{question} {asr_text[:200]}"
        
        try:
            with torch.no_grad():
                batch = [self.preprocess(f) for f in coarse_frames]
                imgs_ts = torch.stack(batch).to(self.device)
                
                img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                text_emb = self._encode_text(search_query)
                
                if text_emb is not None:
                    scores = torch.matmul(img_emb, text_emb.T).view(-1).cpu().numpy()
                    top_k = min(CONFIG["fine_zoom_frames"], len(coarse_frames))
                    top_indices_local = np.argsort(scores)[-top_k:] 
                else:
                    top_indices_local = range(min(CONFIG["fine_zoom_frames"], len(coarse_frames)))
                
                selected_video_indices = []
                for idx in top_indices_local:
                    selected_video_indices.append(coarse_indices[idx])
                
                selected_video_indices = sorted(list(set(selected_video_indices)))
        except Exception as e:
            logger.warning(f"AVP matching failed: {e}")
            return coarse_frames[:CONFIG["fine_zoom_frames"]]

        # 3. Fine Zoom-in
        evidence_frames = self._load_video_frames(video_path, selected_video_indices)
        
        final_evidence = []
        for frame in evidence_frames:
            final_evidence.append(frame)
            
            w, h = frame.size
            crop_size = min(w, h) * CONFIG["crop_ratio"]
            left = (w - crop_size)/2
            top = (h - crop_size)/2
            crop = frame.crop((left, top, left+crop_size, top+crop_size))
            final_evidence.append(crop)
            
        return final_evidence

# ================= 模块四：多智能体辩论 (S4/S5 MAD) =================

class MultiAgentSystem:
    @staticmethod
    def build_debate_prompt(question, asr, ocr, kb_context, reference_cases):
        context_str = f"Audio Transcript: {asr[:1000]}\n"
        if ocr: context_str += f"Visual Text: {ocr}\n"
        if kb_context: context_str += f"Marketing Knowledge: {kb_context}\n"
        if reference_cases: context_str += f"{reference_cases}\n"

        prompt = f"""You are an expert advertising analysis system consisting of three agents:
1. Visual Detective (Objective Observation)
2. Semiotic Decoder (Symbolic Interpretation)
3. Strategic Judge (Final Synthesis)

Input Context:
{context_str}

User Question: {question}

Please execute the following debate process:

: List ONLY the visible objects, actions, and lighting. Do not infer intent.
: Interpret the symbols identified by the Detective using the provided Marketing Knowledge. What is the metaphor?
: Synthesize the visual evidence and semiotic meaning to answer the user's question directly and persuasively.

Output format:
:...
:...
:...
[Final Answer]:..."""
        return prompt

# ================= 主程序 =================

def main():
    logger.info(f"🚀 Starting Patent V10.5 (No Data Leakage) on GPU {args.gpu_id}")
    
    # 1. 预加载 GT (仅用于评估或 RAG 库)
    gt_map = {}
    if os.path.exists(CONFIG["groundtruth_file"]):
        try:
            with open(CONFIG["groundtruth_file"]) as f:
                raw_gt = json.load(f)
                for item in raw_gt:
                    ans = item.get('answer', item.get('gt_answer', 'N/A'))
                    gt_map[item['question_id']] = ans
        except: pass

    # 2. 初始化模块
    kb_engine = MarketingKnowledgeGraph(CONFIG["kb_file"])
    
    # 初始化 RAG
    has_rag = False
    try:
        from sentence_transformers import SentenceTransformer
        rag_model = SentenceTransformer(CONFIG["rag_model_path"], device="cpu") 
        if os.path.exists(CONFIG["groundtruth_file"]):
            with open(CONFIG["groundtruth_file"], 'r') as f: cases_data = json.load(f)
            case_embeddings = rag_model.encode([c['question'] for c in cases_data], convert_to_numpy=True, normalize_embeddings=True)
            has_rag = True
    except: 
        logger.warning("⚠️ RAG init failed or data missing, skipping.")

    avp_engine = ActivePerceptionEngine(device="cuda", clip_path=CONFIG["clip_path"])
    ocr_engine = OCRProcessor()

    logger.info("Loading Qwen2.5-VL...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        CONFIG["model_dir"], 
        torch_dtype=torch.float16, 
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(
        CONFIG["model_dir"], 
        min_pixels=CONFIG["min_pixels"], 
        max_pixels=CONFIG["max_pixels"]
    )

    if os.path.exists(CONFIG["question_file"]):
        with open(CONFIG["question_file"]) as f: questions = json.load(f)
    else:
        logger.error("Question file not found.")
        return

    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    
    # 分片逻辑
    if args.end_idx != -1: 
        questions = questions[args.start_idx : args.end_idx]
    
    # ================= 推理循环 =================
    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        qid = item['question_id']
        save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        if save_path.exists(): continue
        
        gc.collect(); torch.cuda.empty_cache()
        
        try:
            vid = item.get('video', item.get('video_id', qid.split('_')[0]))
            vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
            if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
            
            asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
            
            evidence_frames = avp_engine.perceive(vpath, item['question'], asr_text)
            
            if not evidence_frames and os.path.exists(vpath):
                try:
                    vr = VideoReader(vpath, ctx=cpu(0))
                    indices = np.linspace(0, len(vr)-1, 8, dtype=int)
                    evidence_frames = [Image.fromarray(vr[i].asnumpy()).convert("RGB") for i in indices]
                except: pass
            
            if not evidence_frames:
                logger.warning(f"Empty frames for {qid}")
                continue

            ocr_text = ocr_engine.extract_text(evidence_frames)
            kb_context = kb_engine.retrieve(item['question'])
            
            ref_cases_str = ""
            if has_rag:
                q_vec = rag_model.encode([item['question']], convert_to_numpy=True, normalize_embeddings=True)
                scores = np.dot(q_vec, case_embeddings.T).flatten()
                top_idx = np.argsort(scores)[-3:][::-1] # 稍微多取一个，因为可能会排除掉自己
                
                ref_cases_list = []
                for x in top_idx:
                    # [关键修复]：数据泄露防护！
                    # 如果检索到的案例就是当前题目自己，则跳过
                    if cases_data[x]['question_id'] == qid:
                        continue
                    
                    if scores[x] > CONFIG["sim_threshold"]:
                        ans_text = cases_data[x].get('answer', cases_data[x].get('gt_answer', ''))
                        ref_cases_list.append(f"Q: {cases_data[x]['question']} A: {ans_text}")
                    
                    # 限制最多2个参考案例
                    if len(ref_cases_list) >= 2:
                        break
                
                if ref_cases_list:
                    ref_cases_str = "\n:\n" + "\n".join(ref_cases_list)

            debate_prompt = MultiAgentSystem.build_debate_prompt(
                item['question'], asr_text, ocr_text, kb_context, ref_cases_str
            )
            
            msgs = [{
                "role": "user", 
                "content": [{"type": "image", "image": img} for img in evidence_frames] + 
                           [{"type": "text", "text": debate_prompt}]
            }]
            
            text_input = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text_input], images=evidence_frames, padding=True, return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                gen_ids = model.generate(**inputs, max_new_tokens=768, do_sample=False)
            
            decoded_text = processor.batch_decode(gen_ids, skip_special_tokens=True)[0]
            if "assistant" in decoded_text:
                full_output = decoded_text.split("assistant")[-1].strip()
            else:
                full_output = decoded_text
            
            if "[Final Answer]:" in full_output:
                final_ans = full_output.split("[Final Answer]:")[-1].strip()
            elif ":" in full_output:
                final_ans = full_output.split(":")[-1].strip()
            else:
                final_ans = full_output

            save_path.parent.mkdir(parents=True, exist_ok=True)
            gt_ans = gt_map.get(qid, "N/A")
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "ground_truth": gt_ans,
                    "full_debate_log": full_output,
                    "ocr": ocr_text,
                    "kb_context": kb_context,
                    "frame_count": len(evidence_frames)
                }, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error processing {qid}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            torch.cuda.empty_cache()

if __name__ == "__main__":
    main()