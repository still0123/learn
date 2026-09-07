#!/usr/bin/env python3
"""
AdsQA Patent Edition (Qwen2.5-VL + Rich Prompt) - FIXED VERSION
修复了 GLIBC 错误，强制使用 eager 模式运行。
"""

import sys
# [关键修复 1] 强行屏蔽 flash_attn，防止触发 GLIBC 底层错误
sys.modules['flash_attn'] = None 

import os
import argparse
import json
import logging
import numpy as np
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile
import torch
import torch.nn.functional as F

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

# ================= 命令行参数 =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="Target GPU ID")
parser.add_argument("--shard_id", type=int, default=0)
parser.add_argument("--num_shards", type=int, default=1)
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

# [强硬锁卡]
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id
print(f"🔒 [System] Hard-locked process to Physical GPU: {args.gpu_id}")

# ================= 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-VL-7B-Instruct",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163qwen2.5_rich_prompt",
    "oversample_count": 32,
    "top_k_frames": 16, 
    "unified_size": (896, 896), 
}

# 显存优化
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except ImportError:
    DECORD_AVAILABLE = False

# 日志
log_dir = '/data1/rmx/projectb/AdsQA-main/evaluation/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'qwen2.5_rich_fix_gpu{args.gpu_id}.log')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# [辅助] 智能缩放
def smart_resize(img, target_size): return img.resize(target_size, Image.BICUBIC)

def load_frames_oversampled(video_path, sample_count=32):
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

# [保留 S2 模块]
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

    def select_top_frames(self, frames, question, audio_text, top_k=8):
        if not self.valid or not frames: return frames[:top_k]
        try:
            with torch.no_grad():
                processed, valid_idx = [], []
                for i, f in enumerate(frames):
                    t = self._safe_preprocess(f)
                    if t is not None: processed.append(t); valid_idx.append(i)
                if not processed: return frames[:top_k]
                
                imgs_ts = torch.stack(processed).to(self.device)
                img_emb = F.normalize(self.vision(imgs_ts).image_embeds, dim=-1)
                q_emb = self._encode_text(question)
                a_emb = self._encode_text(audio_text)
                
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                if a_emb is not None:
                    scores = (scores * 0.6) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.4)
                
                top_idx = sorted(np.argsort(scores.cpu().numpy())[-top_k:])
                return [frames[valid_idx[i]] for i in top_idx]
        except: return frames[:top_k]

    def smart_crop(self, frame, question, audio_text):
        if not self.valid: return frame
        try:
            with torch.no_grad():
                t = self._safe_preprocess(frame)
                if t is None: return frame
                img_ts = t.unsqueeze(0).to(self.device)
                vis_out = self.vision(img_ts)
                last_hidden = vis_out.last_hidden_state[:, 1:]
                if hasattr(self.vision, 'visual_projection'): 
                    last_hidden = self.vision.visual_projection(last_hidden)
                patch_emb = F.normalize(last_hidden, dim=-1)
                
                q_emb = self._encode_text(question)
                hm_q = torch.matmul(patch_emb, q_emb.T).view(-1)
                
                safe_audio = audio_text if audio_text and len(audio_text) > 1 else "sound"
                a_tokens = self.tokenizer([safe_audio[:77]], padding=True, truncation=True, return_tensors="pt").to(self.device)
                a_emb = F.normalize(self.text_enc(**a_tokens).text_embeds, dim=-1)
                hm_audio = torch.matmul(patch_emb, a_emb.T).view(-1)
                
                ocr_tokens = self.tokenizer(["text", "logo", "brand", "words"], padding=True, return_tensors="pt").to(self.device)
                ocr_emb = F.normalize(self.text_enc(**ocr_tokens).text_embeds, dim=-1)
                hm_ocr = torch.matmul(patch_emb, ocr_emb.T).max(dim=1).values.squeeze()
                
                fused = (hm_q * 0.5) + (hm_audio * 0.3) + (hm_ocr * 0.2)
                
                side = int(fused.shape[0]**0.5)
                hm = fused.view(side, side).cpu().numpy()
                hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
                
                h, w = hm.shape
                y_grid, x_grid = np.indices((h, w))
                cy = np.sum(y_grid * hm) / (hm.sum() + 1e-8)
                cx = np.sum(x_grid * hm) / (hm.sum() + 1e-8)
                
                ow, oh = frame.size
                center_x, center_y = int((cx / w) * ow), int((cy / h) * oh)
                
                scales = [0.6, 0.8, 1.0] 
                best_box = (0, 0, ow, oh)
                max_energy = -1.0
                
                for scale in scales:
                    if scale >= 1.0:
                        current_score = hm.sum() / (scale ** 0.5)
                        if current_score > max_energy: max_energy = current_score; best_box = (0, 0, ow, oh)
                        continue
                    cw, ch = int(ow * scale), int(oh * scale)
                    l, t = max(0, center_x - cw // 2), max(0, center_y - ch // 2)
                    r, b = min(ow, l + cw), min(oh, t + ch)
                    if (r - l) < cw: l = max(0, r - cw)
                    if (b - t) < ch: t = max(0, b - ch)
                    grid_l, grid_r = int((l/ow)*w), int((r/ow)*w)
                    grid_t, grid_b = int((t/oh)*h), int((b/oh)*h)
                    if grid_r > grid_l and grid_b > grid_t:
                        score = hm[grid_t:grid_b, grid_l:grid_r].sum() / (scale ** 0.5)
                        if score > max_energy: max_energy = score; best_box = (l, t, r, b)
                return frame.crop(best_box)
        except: return frame

class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr):
        return f"""Analyze the video content and audio transcript.
Question: {question}
Audio Transcript: {asr}

Instructions:
1. [Observation]: Describe visual scenes (actions, objects, text) AND audio cues.
2. [Reasoning]: Connect evidence to the question.
3. [Answer]: Direct and descriptive.
   - **MUST Include**: Specific action verbs (e.g., "sprinting"), emotional adjectives (e.g., "urgent"), and exact text seen on screen.
   - **Format**: Keep it factual but detailed.
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
    logger.info(f"🚀 Qwen2.5 Rich Prompt (Fix Mode) started on GPU: {args.gpu_id}")
    
    s23_processor = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info(f"Loading Qwen2.5-VL from {CONFIG['model_dir']}...")
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            CONFIG["model_dir"], 
            torch_dtype=torch.bfloat16,  
            device_map="auto", 
            # [关键修复 2] 改为 eager，避免 GLIBC 错误
            attn_implementation="eager"
        )
        processor = AutoProcessor.from_pretrained(CONFIG["model_dir"])
        logger.info("✅ Model loaded successfully (Eager Mode)")
    except Exception as e:
        logger.error(f"❌ Model load failed: {e}")
        return

    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    
    questions = questions[args.start_idx : args.end_idx] if args.end_idx != -1 else questions[args.start_idx:]
    TRIGGERS = ["text", "say", "number", "logo", "url", "why", "reason", "logic"]

    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        torch.cuda.empty_cache() 
        qid = item['question_id']
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        if save_path.exists(): continue
        
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        raw_frames = load_frames_oversampled(vpath, CONFIG["oversample_count"])
        if not raw_frames: continue
        
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        
        selected_frames = s23_processor.select_top_frames(raw_frames, item['question'], asr_text[:100], CONFIG["top_k_frames"])
        final_input_frames = []
        for f in selected_frames:
            local = s23_processor.smart_crop(f, item['question'], asr_text[:100])
            global_v = f
            final_input_frames.extend([smart_resize(global_v, CONFIG["unified_size"]), smart_resize(local, CONFIG["unified_size"])])
        
        try:
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text)
            messages = [{
                "role": "user",
                "content": [
                    {"type": "video", "video": final_input_frames},
                    {"type": "text", "text": text_1}
                ]
            }]
            text_in = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(text=[text_in], videos=[final_input_frames], padding=True, return_tensors="pt").to(model.device)
            
            with torch.no_grad(): 
                gen_1 = model.generate(
                    **inputs, 
                    do_sample=True, 
                    temperature=0.7, 
                    max_new_tokens=512
                )
            
            generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, gen_1)]
            ans_1 = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

            q_lower = item['question'].lower()
            needs_reflect = any(t in q_lower for t in TRIGGERS)
            final_ans, status = ans_1, "Skipped"

            if needs_reflect:
                text_2 = CoTReflectionPrompts.reflection_prompt(item['question'], ans_1)
                messages_2 = [{
                    "role": "user",
                    "content": [
                        {"type": "video", "video": final_input_frames},
                        {"type": "text", "text": text_2}
                    ]
                }]
                text_in_2 = processor.apply_chat_template(messages_2, tokenize=False, add_generation_prompt=True)
                inputs_2 = processor(text=[text_in_2], videos=[final_input_frames], padding=True, return_tensors="pt").to(model.device)
                
                with torch.no_grad(): 
                    gen_2 = model.generate(**inputs_2, do_sample=True, temperature=0.7, max_new_tokens=512)
                
                generated_ids_trimmed_2 = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs_2.input_ids, gen_2)]
                res_2 = processor.batch_decode(generated_ids_trimmed_2, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
                
                if "[Final Answer]:" in res_2: final_ans, status = res_2.split("[Final Answer]:")[-1].strip(), "Corrected"
                elif "[KEEP]" in res_2: status = "Verified"
                elif len(res_2) > 20: final_ans = res_2

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid, 
                    "prediction": final_ans, 
                    "initial_reasoning": ans_1, 
                    "pipeline": "Qwen2.5_Rich_Prompt_Fix", 
                    "reflection_status": status
                }, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Inference failed {qid}: {e}")
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()

    logger.info("Done.")

if __name__ == "__main__":
    main()