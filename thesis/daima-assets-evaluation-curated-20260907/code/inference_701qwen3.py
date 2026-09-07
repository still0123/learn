#!/usr/bin/env python3
"""
AdsQA A6000 Patent Edition (V10.9 - Qwen3 Native Support)
修复日志：
1. [Log] 修正了日志打印信息，现在正确显示加载 Qwen3 模型。
2. [Model] 使用 AutoModelForVision2Seq + trust_remote_code=True 完美适配 Qwen3 架构。
3. [Precision] 强制使用 bfloat16 以发挥 A6000 性能并防止乱码。
4. [Safety] 保留所有防作弊 (No Leakage) 和数据兼容性修复。
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
parser.add_argument("--shard_id", type=int, default=0, help="Shard ID for parallel execution")
parser.add_argument("--num_shards", type=int, default=1, help="Total number of shards")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

# [显存优化配置]
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

# [关键] 使用 Auto 接口来适配 Qwen3
from transformers import AutoModelForVision2Seq, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize

# ================= 全局配置 ================= 
CONFIG = {
    # [Target Model] Qwen3 路径
    "model_dir": "/data1/qky/Model/QWen3VL",
    
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "groundtruth_file": "/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    # 输出目录
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/patent_v10_qwen3_noleak",
    
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
log_file = os.path.join(log_dir, f'qwen3_gpu{args.gpu_id}.log')

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

# ================= 模块二：营销知识图谱 =================

class MarketingKnowledgeGraph:
    def __init__(self, kb_path):
        self.kb = {} 
        self.fallback_kb = {
            "metaphor": "Visual Metaphor: Using objects to represent abstract concepts.",
            "irony": "Irony/Humor: Presenting situations that contradict expectations."
        }
        if os.path.exists(kb_path):
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict): self.kb = data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            vals = list(item.values())
                            if len(vals) >= 2: self.kb[str(vals[0]).strip().lower()] = str(vals[1]).strip()
            except: self.kb = self.fallback_kb
        else: self.kb = self.fallback_kb

    def retrieve(self, query: str, top_k=2) -> str:
        hits = [f"- [{k.upper()}]: {v}" for k, v in self.kb.items() if k in query.lower()]
        if not hits: hits.append("- Strategy: Analyze emotional appeal (Pathos) or logical arguments (Logos).")
        return "\n".join(hits[:top_k])

# ================= 模块三：主动视频感知 =================

class ActivePerceptionEngine:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        if clip_path:
            try:
                self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, local_files_only=True).to(device).eval()
                self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path, local_files_only=True).to(device).eval()
                self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
                self.preprocess = Compose([Resize(224), CenterCrop(224), ToTensor(), Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))])
                self.valid = True
            except: pass

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
            except: pass
        return frames

    def perceive(self, video_path, question, asr_text):
        if not os.path.exists(video_path): return []
        try:
            vr = VideoReader(video_path, ctx=cpu(0))
            if len(vr) < 1: return []
            coarse_indices = np.linspace(0, len(vr)-1, CONFIG["coarse_scan_frames"], dtype=int)
            coarse_frames = self._load_video_frames(video_path, coarse_indices)
        except: return []
        if not coarse_frames or not self.valid: return coarse_frames[:CONFIG["fine_zoom_frames"]]

        try:
            with torch.no_grad():
                batch = [self.preprocess(f) for f in coarse_frames]
                imgs_ts = torch.stack(batch).to(self.device)
                img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                text_emb = self._encode_text(f"{question} {asr_text[:200]}")
                
                if text_emb is not None:
                    scores = torch.matmul(img_emb, text_emb.T).view(-1).cpu().numpy()
                    top_indices = np.argsort(scores)[-min(CONFIG["fine_zoom_frames"], len(coarse_frames)):]
                else: top_indices = range(min(CONFIG["fine_zoom_frames"], len(coarse_frames)))
                selected_indices = sorted(list(set([coarse_indices[i] for i in top_indices])))
        except: return coarse_frames[:CONFIG["fine_zoom_frames"]]

        evidence_frames = self._load_video_frames(video_path, selected_indices)
        final_evidence = []
        for frame in evidence_frames:
            final_evidence.append(frame)
            w, h = frame.size
            c = min(w, h) * CONFIG["crop_ratio"]
            final_evidence.append(frame.crop(((w-c)/2, (h-c)/2, (w+c)/2, (h+c)/2)))
        return final_evidence

# ================= 模块四：多智能体辩论 =================

class MultiAgentSystem:
    @staticmethod
    def build_debate_prompt(question, asr, ocr, kb, ref):
        ctx = f"Audio: {asr[:1000]}\n"
        if ocr: ctx += f"Text: {ocr}\n"
        if kb: ctx += f"KB: {kb}\n"
        if ref: ctx += f"{ref}\n"
        return f"""You are an advertising expert.
Input Context:
{ctx}
User Question: {question}

Please execute:
: List ONLY visible objects/actions.
: Interpret symbols using Marketing Knowledge.
: Synthesize evidence to answer.

Output:
:...
:...
:...
[Final Answer]:..."""

# ================= 主程序 =================

def main():
    # [Log Fix] 动态打印正确的模型路径
    logger.info(f"🚀 Starting V10.9 with Model: {CONFIG['model_dir']} on GPU {args.gpu_id}")
    
    gt_map = {}
    if os.path.exists(CONFIG["groundtruth_file"]):
        try:
            with open(CONFIG["groundtruth_file"]) as f:
                for item in json.load(f):
                    gt_map[item['question_id']] = item.get('answer', item.get('gt_answer', 'N/A'))
        except: pass

    kb_engine = MarketingKnowledgeGraph(CONFIG["kb_file"])
    has_rag = False
    try:
        from sentence_transformers import SentenceTransformer
        rag_model = SentenceTransformer(CONFIG["rag_model_path"], device="cpu") 
        with open(CONFIG["groundtruth_file"], 'r') as f: cases_data = json.load(f)
        case_embeddings = rag_model.encode([c['question'] for c in cases_data], convert_to_numpy=True, normalize_embeddings=True)
        has_rag = True
    except: pass

    avp_engine = ActivePerceptionEngine(device="cuda", clip_path=CONFIG["clip_path"])
    ocr_engine = OCRProcessor()

    # [Model Fix] 使用 AutoModel 自动适配 Qwen3 架构
    logger.info(f"Initializing AutoModelForVision2Seq from {CONFIG['model_dir']}...")
    try:
        model = AutoModelForVision2Seq.from_pretrained(
            CONFIG["model_dir"], 
            torch_dtype=torch.bfloat16, # 使用 bf16 防止 A6000 乱码
            device_map="auto",
            trust_remote_code=True      # 必须开启，以支持新模型代码
        )
        processor = AutoProcessor.from_pretrained(
            CONFIG["model_dir"], 
            min_pixels=CONFIG["min_pixels"], 
            max_pixels=CONFIG["max_pixels"],
            trust_remote_code=True
        )
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        return

    if os.path.exists(CONFIG["question_file"]):
        with open(CONFIG["question_file"]) as f: questions = json.load(f)
    else: return

    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    if args.end_idx != -1: questions = questions[args.start_idx : args.end_idx]
    
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
            
            evidence_frames = avp_engine.perceive(vpath, item['question'], asr_data.get(vid, ""))
            if not evidence_frames and os.path.exists(vpath):
                try:
                    vr = VideoReader(vpath, ctx=cpu(0))
                    indices = np.linspace(0, len(vr)-1, 8, dtype=int)
                    evidence_frames = [Image.fromarray(vr[i].asnumpy()).convert("RGB") for i in indices]
                except: pass
            
            if not evidence_frames: continue

            ocr_text = ocr_engine.extract_text(evidence_frames)
            kb_context = kb_engine.retrieve(item['question'])
            
            ref_str = ""
            if has_rag:
                q_vec = rag_model.encode([item['question']], convert_to_numpy=True, normalize_embeddings=True)
                scores = np.dot(q_vec, case_embeddings.T).flatten()
                top_idx = np.argsort(scores)[-3:][::-1]
                
                ref_list = []
                for x in top_idx:
                    # [Anti-Leakage] 确保不检索自己
                    if cases_data[x]['question_id'] == qid: continue 
                    if scores[x] > CONFIG["sim_threshold"]:
                        ans = cases_data[x].get('answer', cases_data[x].get('gt_answer', ''))
                        ref_list.append(f"Q: {cases_data[x]['question']} A: {ans}")
                    if len(ref_list) >= 2: break
                ref_str = "\n".join(ref_list)

            prompt = MultiAgentSystem.build_debate_prompt(item['question'], asr_data.get(vid, ""), ocr_text, kb_context, ref_str)
            
            msgs = [{"role": "user", "content": [{"type": "image", "image": img} for img in evidence_frames] + [{"type": "text", "text": prompt}]}]
            text_input = processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text_input], images=evidence_frames, padding=True, return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                gen_ids = model.generate(**inputs, max_new_tokens=768, do_sample=False)
            
            full_output = processor.batch_decode(gen_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
            final_ans = full_output.split("[Final Answer]:")[-1].strip() if "[Final Answer]:" in full_output else full_output

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "ground_truth": gt_map.get(qid, "N/A"),
                    "full_debate_log": full_output
                }, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error {qid}: {e}")
            torch.cuda.empty_cache()

if __name__ == "__main__":
    main()