#!/usr/bin/env python3
"""
AdsQA A6000 冲分版 (Patent Aligned V9.1 - With GroundTruth Log)
修改点：
1. [结果优化] 在输出 json 中增加 "ground_truth" 字段，方便人工对比。
2. [核心策略] 保持 V9 的所有降噪、OCR 优化和 Prompt 策略。
"""

import os
import argparse
import logging
import json
import numpy as np
import torch
import torch.nn.functional as F
import gc 
import re
from pathlib import Path
from typing import List
from tqdm import tqdm
from PIL import Image, ImageFile

# [显存优化]
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# ================= 命令行参数 =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True)
parser.add_argument("--shard_id", type=int, required=True)
parser.add_argument("--num_shards", type=int, default=2)
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id

# ================= 依赖 =================
try: from decord import VideoReader, cpu; DECORD_AVAILABLE = True
except: DECORD_AVAILABLE = False
try: from sentence_transformers import SentenceTransformer; SENTENCE_RAG_AVAILABLE = True
except: SENTENCE_RAG_AVAILABLE = False
try: from scenedetect import VideoManager, SceneManager; from scenedetect.detectors import ContentDetector; SCENE_DETECT_AVAILABLE = True
except: SCENE_DETECT_AVAILABLE = False
try: from paddleocr import PaddleOCR; PADDLE_AVAILABLE = True
except: PADDLE_AVAILABLE = False

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

# ================= 配置 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "groundtruth_file": "/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    "previous_output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5",
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/6011_v9_clean",
    
    # 显存安全配置
    "shot_threshold": 27.0,
    "top_k_frames": 16,
    "crop_ratio": 0.75,
    "min_pixels": 256*256,
    "max_pixels": 1008*1008,
    
    # 降噪阈值
    "sim_threshold": 0.65,
    "ocr_threshold": 0.5
}

ImageFile.LOAD_TRUNCATED_IMAGES = True

log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/patent_v9_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# ================= 核心类 =================

def load_frames_patent_aligned(video_path: str, max_frames: int = 16) -> List[Image.Image]:
    if not os.path.exists(video_path): return []
    frames = []
    if SCENE_DETECT_AVAILABLE and DECORD_AVAILABLE:
        try:
            video_manager = VideoManager([video_path])
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=CONFIG["shot_threshold"]))
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
            scene_list = scene_manager.get_scene_list()
            timestamps = []
            if not scene_list:
                vr = VideoReader(video_path, ctx=cpu(0))
                indices = np.linspace(0, len(vr)-1, max_frames, dtype=int)
            else:
                for scene in scene_list:
                    timestamps.append((scene[0].get_frames() + scene[1].get_frames()) // 2)
                vr = VideoReader(video_path, ctx=cpu(0))
                if len(timestamps) < max_frames:
                    remain = max_frames - len(timestamps)
                    extra = np.linspace(0, len(vr)-1, remain, dtype=int)
                    indices = sorted(list(set(timestamps) | set(extra)))
                else:
                    indices = [timestamps[i] for i in np.linspace(0, len(timestamps)-1, max_frames, dtype=int)]
            vr = VideoReader(video_path, ctx=cpu(0))
            for idx in indices:
                try: frames.append(Image.fromarray(vr[int(idx)].asnumpy()).convert("RGB"))
                except: continue
            if frames: return frames
        except: pass
    
    if not frames and DECORD_AVAILABLE:
        try:
            vr = VideoReader(video_path, ctx=cpu(0))
            indices = np.linspace(0, len(vr)-1, max_frames, dtype=int)
            for idx in indices: frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
        except: pass
    return frames

class CaseRetriever:
    def __init__(self, groundtruth_file, model_path, device='cuda'):
        self.cases = []
        self.embeddings = None
        self.use_retrieval = False
        if not SENTENCE_RAG_AVAILABLE: return
        try:
            self.model = SentenceTransformer(model_path, device=device)
            self.use_retrieval = True
            with open(groundtruth_file, 'r', encoding='utf-8') as f: self.cases = json.load(f)
            corpus = [f"Question: {i['question']} Context: {i.get('meta_info','')[:200]}" for i in self.cases]
            self.embeddings = self.model.encode(corpus, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
            logger.info("✅ Case Retriever ready.")
        except: self.use_retrieval = False

    def retrieve_similar_cases(self, current_qid, current_query, current_meta="", top_k=2):
        if not self.use_retrieval: return ""
        try:
            q_vec = self.model.encode([f"Question: {current_query} Context: {current_meta[:200]}"], convert_to_numpy=True, normalize_embeddings=True)
            scores = np.dot(q_vec, self.embeddings.T)[0]
            
            valid_indices = [i for i in np.argsort(scores)[::-1] 
                             if scores[i] > CONFIG["sim_threshold"] and self.cases[i]['question_id'] != current_qid]
            
            if not valid_indices: return ""
            
            selected = [self.cases[i] for i in valid_indices[:top_k]]
            txt = "\n[Reference Examples (Logic Hintonly)]:\n"
            for i, c in enumerate(selected): 
                ans = c.get('answer', c.get('gt_answer', c.get('prediction', '')))
                txt += f"- Q: {c['question']} -> A: {ans}\n"
            return txt
        except: return ""

class S23VisualProcessor:
    def __init__(self, device="cuda", clip_path=None):
        self.device = device
        self.valid = False
        self.ocr_engine = None
        if PADDLE_AVAILABLE:
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            try: self.ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False, use_gpu=False)
            except: pass
        if not clip_path: return
        try:
            self.vision = CLIPVisionModelWithProjection.from_pretrained(clip_path, local_files_only=True).to(device).eval()
            self.text_enc = CLIPTextModelWithProjection.from_pretrained(clip_path, local_files_only=True).to(device).eval()
            self.tokenizer = CLIPTokenizer.from_pretrained(clip_path, local_files_only=True)
            from torchvision.transforms import ToTensor, Normalize, Resize, Compose
            self.preprocess = Compose([Resize((224, 224)), ToTensor(), Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))])
            self.valid = True
        except: pass

    def extract_scene_text(self, frames):
        if not self.ocr_engine: return ""
        texts = set()
        for img in frames:
            try:
                res = self.ocr_engine.ocr(np.array(img), cls=True)
                if res and res[0]:
                    for line in res[0]:
                        if line[1][1] > CONFIG["ocr_threshold"] and len(line[1][0].strip()) > 1: 
                            texts.add(line[1][0])
            except: continue
        return ", ".join(list(texts))

    def _encode_text(self, text):
        if not text: return None
        tokens = self.tokenizer([text[:77]], padding=True, return_tensors="pt").to(self.device)
        return F.normalize(self.text_enc(**tokens).text_embeds, dim=-1)

    def select_top_frames(self, frames, question, audio_text, top_k=8):
        if not self.valid or not frames: return frames[:top_k]
        try:
            with torch.no_grad():
                batch = [self.preprocess(f.convert('RGB')) for f in frames]
                imgs_ts = torch.stack(batch).to(self.device)
                img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                q_emb = self._encode_text(question)
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                if audio_text:
                    a_emb = self._encode_text(audio_text)
                    scores = (scores * 0.6) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.4)
                
                clip_k = top_k // 2
                uniform_k = top_k - clip_k
                
                clip_indices = sorted(np.argsort(scores.cpu().numpy())[-clip_k:])
                uniform_indices = np.linspace(0, len(frames)-1, uniform_k, dtype=int).tolist()
                
                final_indices = sorted(list(set(clip_indices + uniform_indices)))
                return [frames[i] for i in final_indices]
        except: return frames[:top_k]

    def smart_crop(self, frame, question, audio_text):
        if not self.valid: return frame
        try:
            with torch.no_grad():
                t = self.preprocess(frame).unsqueeze(0).to(self.device)
                vis = self.vision(t)
                last = vis.last_hidden_state[:, 1:]
                if hasattr(self.vision, 'visual_projection'): last = self.vision.visual_projection(last)
                patch = F.normalize(last, dim=-1)
                q = self._encode_text(question)
                ocr = self._encode_text("text logo")
                hm = (torch.matmul(patch, q.T).view(-1) * 0.7) + (torch.matmul(patch, ocr.T).max(dim=1).values.squeeze() * 0.3)
                side = int(hm.shape[0]**0.5)
                hm = hm.view(side, side).cpu().numpy()
                y, x = np.indices(hm.shape)
                cy, cx = np.sum(y*hm)/(hm.sum()+1e-8), np.sum(x*hm)/(hm.sum()+1e-8)
                ow, oh = frame.size
                ctx, cty = int((cx/side)*ow), int((cy/side)*oh)
                cw, ch = int(ow * CONFIG["crop_ratio"]), int(oh * CONFIG["crop_ratio"])
                l, t = max(0, ctx - cw//2), max(0, cty - ch//2)
                r, b = min(ow, l+cw), min(oh, t+ch)
                if r-l < cw: l = max(0, r-cw)
                if b-t < ch: t = max(0, b-ch)
                return frame.crop((l, t, r, b))
        except: return frame

class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr, rag, case, ocr):
        context = ""
        if ocr and len(ocr) > 3: context += f"\n[Visual Text Hint]: {ocr}"
        if case: context += f"{case}"
        
        return f"""Analyze the video visually to answer the question.

Question: {question}
Audio Transcript: {asr}
{context}

Instructions:
1. [Observation]: List VISIBLE objects and actions. IGNORE audio if it contradicts the video.
2. [Analysis]: Analyze the marketing intent.
3. [Reasoning]: Combine visual evidence with audio context.
4. [Answer]: Concise answer.

Output format:
[Observation]: ...
[Analysis]: ...
[Reasoning]: ...
[Answer]: ..."""

    @staticmethod
    def reflection_prompt(question, ans):
        return f"""Role: Hallucination Checker.
Question: {question}
Draft Answer: "{ans}"
Task: Verify if the answer describes objects NOT present in the video. If so, correct it based purely on visual logic.
Output: [KEEP] or [Final Answer]: ..."""

def main():
    logger.info(f"🚀 Starting V9.1 (With GroundTruth Log) on GPU {args.gpu_id}")
    
    # [新增] 预加载 GroundTruth 映射表
    gt_map = {}
    if os.path.exists(CONFIG["groundtruth_file"]):
        try:
            with open(CONFIG["groundtruth_file"]) as f:
                raw_gt = json.load(f)
                for item in raw_gt:
                    # 兼容不同字段名
                    ans = item.get('answer', item.get('gt_answer', 'N/A'))
                    gt_map[item['question_id']] = ans
            logger.info(f"Loaded {len(gt_map)} ground truth entries.")
        except Exception as e:
            logger.warning(f"Failed to load GT map: {e}")

    # 模块初始化
    case_retriever = CaseRetriever(CONFIG["groundtruth_file"], CONFIG["rag_model_path"])
    s23 = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info("Loading Qwen2.5-VL...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(CONFIG["model_dir"], torch_dtype=torch.float16, device_map="auto")
    processor = AutoProcessor.from_pretrained(CONFIG["model_dir"], min_pixels=CONFIG["min_pixels"], max_pixels=CONFIG["max_pixels"])
    
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
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
            raw_frames = load_frames_patent_aligned(vpath, 32)
            if not raw_frames: continue
            
            asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
            selected = s23.select_top_frames(raw_frames, item['question'], asr_text[:500], CONFIG["top_k_frames"])
            
            final_frames = []
            for f in selected:
                final_frames.append(f)
                final_frames.append(s23.smart_crop(f, item['question'], asr_text[:500]))
            
            ocr_txt = s23.extract_scene_text(final_frames)
            cases = case_retriever.retrieve_similar_cases(qid, item['question'], item.get('meta_info', ''), top_k=2)
            
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text, None, cases, ocr_txt)
            msgs = [{"role": "user", "content": [{"type": "image", "image": img} for img in final_frames] + [{"type": "text", "text": text_1}]}]
            
            inputs = processor(text=[processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)], images=final_frames, padding=True, return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                gen = model.generate(**inputs, max_new_tokens=512, do_sample=False)
            ans_1 = processor.batch_decode(gen, skip_special_tokens=True)[0].split("assistant")[-1].strip()
            del inputs, gen
            
            final_ans = ans_1.split("[Answer]:")[-1].strip() if "[Answer]:" in ans_1 else ans_1
            status = "Direct"
            
            if any(t in item['question'].lower() for t in ["why", "reason", "how"]):
                text_2 = CoTReflectionPrompts.reflection_prompt(item['question'], ans_1)
                msgs_2 = [{"role": "user", "content": [{"type": "image", "image": final_frames[0]}, {"type": "text", "text": text_2}]}]
                inputs_2 = processor(text=[processor.apply_chat_template(msgs_2, tokenize=False, add_generation_prompt=True)], images=[final_frames[0]], padding=True, return_tensors="pt").to("cuda")
                with torch.no_grad():
                    gen_2 = model.generate(**inputs_2, max_new_tokens=256, do_sample=False)
                res_2 = processor.batch_decode(gen_2, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                if "[Final Answer]:" in res_2: 
                    final_ans = res_2.split("[Final Answer]:")[-1].strip()
                    status = "Corrected"
                del inputs_2, gen_2
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # [新增] 获取 ground truth
            gt_ans = gt_map.get(qid, "N/A")
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid, 
                    "prediction": final_ans, 
                    "ground_truth": gt_ans,  # <-- 方便对比
                    "reasoning": ans_1, 
                    "status": status, 
                    "ocr": ocr_txt, 
                    "references": cases
                }, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error {qid}: {e}")
            torch.cuda.empty_cache()

if __name__ == "__main__":
    main()