#!/usr/bin/env python3
"""
AdsQA A6000 Patent Edition (V10.15 - Rich Prompt Mode)
优化目标：
1. [Strict保持] 维持高精度的逻辑推理和反思机制。
2. [Relaxed提升] 通过 Prompt 强制模型输出更丰富的描述性关键词 (形容词、具体动词、OCR文字)。
3. [专利特性] 完整保留 S2 (视听协同+OCR混合热力图) 和 S23 (动态多尺度锚框)。
"""

import os
import argparse
import sys

# ================= 命令行参数预处理 (最优先) =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="Target GPU ID (e.g., '2')")
parser.add_argument("--shard_id", type=int, default=0)
parser.add_argument("--num_shards", type=int, default=1)
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

# [强硬指定显卡] 
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
print(f"🔒 [System] Hard-locked process to Physical GPU: {args.gpu_id}")

# ================= 正常的 Import =================
import json
import logging
import numpy as np
import traceback
import gc
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile
import torch
import torch.nn.functional as F

from transformers import AutoModelForVision2Seq, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

# ================= 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/qky/Model/QWen3VL",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    
    # [GT文件]
    "groundtruth_file": "/data1/rmx/projectb/AdsQA-main/data/testset_groundtruth.json",
    
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    
    # [输出目录] 更新为 Rich Prompt 版本，方便对比实验
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163qwen3_rich_prompt",
    
    # [智能跳过] 检查之前的 V5 结果
    "previous_output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5",

    # [高配参数]
    "oversample_count": 32,
    "top_k_frames": 16, 
    "crop_ratio": 0.75, 
    "unified_size": (896, 896), 
}

# [显存优化]
os.environ["expandable_segments"] = "True"
ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except ImportError:
    DECORD_AVAILABLE = False

# 日志
log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/qwen3_v10_15_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# [辅助] 智能缩放
def smart_resize(img, target_size):
    return img.resize(target_size, Image.BICUBIC)

def load_frames_oversampled(video_path: str, sample_count: int = 32) -> list:
    if not os.path.exists(video_path): return []
    frames = []
    try:
        if DECORD_AVAILABLE:
            vr = VideoReader(video_path, ctx=cpu(0))
            if len(vr) > 0:
                indices = np.linspace(0, len(vr)-1, sample_count, dtype=int)
                for idx in indices:
                    frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
                if frames: return frames
    except: pass
    
    if not frames and os.path.isdir(video_path):
        files = sorted(Path(video_path).glob("*.jpg")) + sorted(Path(video_path).glob("*.png"))
        if files:
            idx = np.linspace(0, len(files)-1, sample_count, dtype=int)
            for i in idx:
                try: frames.append(Image.open(files[i]).convert("RGB"))
                except: continue
    return frames

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

    def select_top_frames(self, frames, question, audio_text, top_k=8):
        if not self.valid or not frames: return frames[:top_k]
        try:
            with torch.no_grad():
                processed, valid_idx = [], []
                for i, f in enumerate(frames):
                    t = self._safe_preprocess(f)
                    if t is not None:
                        processed.append(t); valid_idx.append(i)
                if not processed: return frames[:top_k]
                
                imgs_ts = torch.stack(processed).to(self.device)
                img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                q_emb = self._encode_text(question)
                a_emb = self._encode_text(audio_text)
                
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                if a_emb is not None:
                    # 视听双流初筛
                    scores = (scores * 0.6) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.4)
                
                top_idx = sorted(np.argsort(scores.cpu().numpy())[-top_k:])
                return [frames[valid_idx[i]] for i in top_idx]
        except: return frames[:top_k]

    def smart_crop(self, frame, question, audio_text):
        """
        [Patent Hybrid Mode] 视听协同 + OCR增强 + 动态多尺度锚定
        符合专利 S2 和 S23 的技术要求。
        """
        if not self.valid: return frame
        try:
            with torch.no_grad():
                # 1. 预处理
                t = self._safe_preprocess(frame)
                if t is None: return frame
                img_ts = t.unsqueeze(0).to(self.device)
                
                # 2. 提取 Grid Features
                vis_out = self.vision(img_ts)
                last_hidden = vis_out.last_hidden_state[:, 1:]
                if hasattr(self.vision, 'visual_projection'): 
                    last_hidden = self.vision.visual_projection(last_hidden)
                patch_emb = F.normalize(last_hidden, dim=-1)
                
                # =========================================================
                # [融合逻辑] Question(50%) + Audio(30%) + OCR(20%)
                # =========================================================
                
                # A. 问题特征
                q_emb = self._encode_text(question)
                hm_q = torch.matmul(patch_emb, q_emb.T).view(-1)
                
                # B. 音频特征 (专利 S21 要求)
                safe_audio = audio_text if audio_text and len(audio_text) > 1 else "sound"
                a_tokens = self.tokenizer([safe_audio[:77]], padding=True, truncation=True, return_tensors="pt").to(self.device)
                a_emb = F.normalize(self.text_enc(**a_tokens).text_embeds, dim=-1)
                hm_audio = torch.matmul(patch_emb, a_emb.T).view(-1)
                
                # C. OCR特征 (保留此项以维持 Type 4 精度)
                ocr_tokens = self.tokenizer(["text", "logo", "brand", "words"], padding=True, return_tensors="pt").to(self.device)
                ocr_emb = F.normalize(self.text_enc(**ocr_tokens).text_embeds, dim=-1)
                hm_ocr = torch.matmul(patch_emb, ocr_emb.T).max(dim=1).values.squeeze()
                
                # D. 视听综合响应图生成 (S22)
                fused = (hm_q * 0.5) + (hm_audio * 0.3) + (hm_ocr * 0.2)
                
                # =========================================================
                # [动态锚框优选] (专利 S23)
                # =========================================================
                
                side = int(fused.shape[0]**0.5)
                hm = fused.view(side, side).cpu().numpy()
                hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
                
                # 1. 计算重心 (S231)
                h, w = hm.shape
                y_grid, x_grid = np.indices((h, w))
                tot = hm.sum() + 1e-8
                cy = np.sum(y_grid * hm) / tot
                cx = np.sum(x_grid * hm) / tot
                
                ow, oh = frame.size
                center_x = int((cx / w) * ow)
                center_y = int((cy / h) * oh)
                
                # 2. 多尺度优选 (S232, S233)
                scales = [0.6, 0.8, 1.0] 
                best_box = (0, 0, ow, oh)
                max_energy = -1.0
                
                for scale in scales:
                    if scale >= 1.0: # 全图 Case
                        current_score = hm.sum() / (scale ** 0.5)
                        if current_score > max_energy:
                            max_energy = current_score
                            best_box = (0, 0, ow, oh)
                        continue

                    # 候选框生成
                    cw, ch = int(ow * scale), int(oh * scale)
                    l = max(0, center_x - cw // 2)
                    t = max(0, center_y - ch // 2)
                    r, b = min(ow, l + cw), min(oh, t + ch)
                    
                    # 边界回弹
                    if (r - l) < cw: l = max(0, r - cw)
                    if (b - t) < ch: t = max(0, b - ch)
                    
                    # 计算该框内的响应密度
                    grid_l, grid_r = int((l/ow)*w), int((r/ow)*w)
                    grid_t, grid_b = int((t/oh)*h), int((b/oh)*h)
                    
                    if grid_r > grid_l and grid_b > grid_t:
                        box_energy = hm[grid_t:grid_b, grid_l:grid_r].sum()
                        # 响应密度计算公式 (S233)
                        score = box_energy / (scale ** 0.5) 
                        
                        if score > max_energy:
                            max_energy = score
                            best_box = (l, t, r, b)
                
                return frame.crop(best_box)
        except: return frame

class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr):
        # [修改点] 引入 Rich-Factual 策略：在保持准确的同时，强制输出更丰富的描述性关键词
        return f"""Analyze the video content and audio transcript.
Question: {question}
Audio Transcript: {asr}

Instructions:
1. [Observation]: Describe visual scenes (actions, objects, text) AND audio cues.
2. [Reasoning]: Connect evidence to the question.
3. [Answer]: Direct and descriptive.
   - **MUST Include**: Specific action verbs (e.g., "sprinting" instead of "running"), emotional adjectives (e.g., "joyful", "urgent"), and exact text seen on screen.
   - **Format**: Keep it factual, but ensure you explicitly mention the key visual and auditory elements that support your conclusion.
"""
    @staticmethod
    def reflection_prompt(question, initial_ans):
        return f"""Role: Fact-Checker.
Question: {question}
Draft: "{initial_ans}"
Task: Verify against video/audio.
Output: [KEEP] or [Final Answer]: ...
"""

def main():
    logger.info(f"🚀 Process started on Physical GPU: {args.gpu_id}")
    
    # GT 加载
    gt_map = {}
    if os.path.exists(CONFIG["groundtruth_file"]):
        try:
            with open(CONFIG["groundtruth_file"], 'r', encoding='utf-8') as f:
                for x in json.load(f): gt_map[x['question_id']] = x.get('answer', x.get('gt_answer', 'N/A'))
        except: pass

    # RAG 被禁用 (符合 Pure Mode 策略)
    # 专利 S2 的视听协同在 s23_processor 中实现
    
    s23_processor = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info(f"Loading Qwen3VL from {CONFIG['model_dir']}...")
    try:
        model = AutoModelForVision2Seq.from_pretrained(
            CONFIG["model_dir"], 
            torch_dtype=torch.bfloat16,  
            device_map="auto", 
            trust_remote_code=True       
        )
        processor = AutoProcessor.from_pretrained(
            CONFIG["model_dir"], 
            min_pixels=256*256, 
            max_pixels=1280*1280, 
            trust_remote_code=True
        )
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        return

    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    if args.end_idx == -1: args.end_idx = len(questions)
    questions = questions[args.start_idx : args.end_idx]
    TRIGGERS = ["text", "say", "number", "logo", "url", "why", "reason", "logic"]

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        torch.cuda.empty_cache() 
        qid = item['question_id']
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        
        # Skip logic
        if (Path(CONFIG["previous_output_dir"])/qid/"prediction.json").exists(): continue
        if (Path(CONFIG["output_dir"])/qid/"prediction.json").exists(): continue
        save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        selected_frames = s23_processor.select_top_frames(raw_frames, item['question'], asr_text[:100], CONFIG["top_k_frames"])
        
        final_input_frames = []
        for f in selected_frames:
            # 混合热力图 + 动态裁剪
            local = s23_processor.smart_crop(f, item['question'], asr_text[:100])
            global_v = f
            final_input_frames.extend([smart_resize(global_v, CONFIG["unified_size"]), smart_resize(local, CONFIG["unified_size"])])
        
        try:
            # [关键] 使用 Rich-Factual Prompt
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text)
            msg_1 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames, "fps": 1.0}, {"type": "text", "text": text_1}]}]
            text_in = processor.apply_chat_template(msg_1, tokenize=False, add_generation_prompt=True)
            
            inputs = processor(text=[text_in], videos=[final_input_frames], padding=True, return_tensors="pt").to(model.device)
            
            with torch.no_grad(): 
                gen_1 = model.generate(**inputs, do_sample=False, max_new_tokens=512)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()

            q_lower = item['question'].lower()
            needs_reflect = any(t in q_lower for t in TRIGGERS)
            final_ans, status = ans_1, "Skipped"

            if needs_reflect:
                text_2 = CoTReflectionPrompts.reflection_prompt(item['question'], ans_1)
                msg_2 = [{"role": "user", "content": [{"type": "video", "video": final_input_frames, "fps": 1.0}, {"type": "text", "text": text_2}]}]
                text_in_2 = processor.apply_chat_template(msg_2, tokenize=False, add_generation_prompt=True)
                inputs_2 = processor(text=[text_in_2], videos=[final_input_frames], padding=True, return_tensors="pt").to(model.device)
                
                with torch.no_grad(): 
                    gen_2 = model.generate(**inputs_2, do_sample=False, max_new_tokens=512)
                res_2 = processor.batch_decode(gen_2, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                
                if "[Final Answer]:" in res_2: final_ans, status = res_2.split("[Final Answer]:")[-1].strip(), "Corrected"
                elif "[KEEP]" in res_2: status = "Verified"
                elif len(res_2) > 20: final_ans = res_2

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid, "prediction": final_ans, "ground_truth": gt_map.get(qid, "N/A"),
                    "initial_reasoning": ans_1, "pipeline": "A6000_V10_15_Rich_Prompt", "reflection_status": status
                }, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Inference failed {qid}: {e}")
            torch.cuda.empty_cache()
    logger.info("Done.")

if __name__ == "__main__":
    main()