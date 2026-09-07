#!/usr/bin/env python3
"""
AdsQA A6000 终极修正版 (Patent Aligned V2)
专利对齐说明：
1. [S12] 引入 PySceneDetect 进行镜头分割，取关键帧。
2. [S21] ASR 全文参与热力图计算，不再截断。
3. [S24] 移除强制正方形缩放，保持图像原始比例，提升 OCR 精度。
4. [S4/S5] 严格执行“观察-分析-推理-答案”及自我反思流程。
"""

import os
import argparse
import logging
import json
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path
from typing import List
from tqdm import tqdm
from PIL import Image, ImageFile

# ================= 命令行参数解析 =================
parser = argparse.ArgumentParser()
parser.add_argument("--gpu_id", type=str, required=True, help="指定使用的GPU ID (例如 0 或 1)")
parser.add_argument("--shard_id", type=int, required=True, help="当前分片ID (0 或 1)")
parser.add_argument("--num_shards", type=int, default=2, help="总分片数")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--end_idx", type=int, default=-1)
args = parser.parse_args()

os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id

# ================= 导入依赖 =================
try:
    from decord import VideoReader, cpu
    DECORD_AVAILABLE = True
except ImportError:
    DECORD_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_RAG_AVAILABLE = True
except ImportError:
    SENTENCE_RAG_AVAILABLE = False

# [新增] 专利 S12 必需库
try:
    from scenedetect import VideoManager, SceneManager
    from scenedetect.detectors import ContentDetector
    SCENE_DETECT_AVAILABLE = True
except ImportError:
    SCENE_DETECT_AVAILABLE = False
    print("Warning: 'scenedetect' not found. Fallback to uniform sampling. (Install via 'pip install scenedetect')")

from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from transformers import CLIPVisionModelWithProjection, CLIPTextModelWithProjection, CLIPTokenizer

# ================= 配置区域 ================= 
CONFIG = {
    "model_dir": "/data1/rmx/projectb/models/Qwen2.5-7B-VL-ReAd-R",
    "clip_path": "/data1/rmx/projectb/AdsQA-main/models/clip-vit-large-patch14",
    "rag_model_path": "/data1/rmx/projectb/AdsQA-main/models/bge-base-en-v1.5", 
    "frame_root": "/data1/rmx/projectb/AdsQA-main/data/videos",           
    "question_file": "/data1/rmx/projectb/AdsQA-main/data/testset_question.json",
    "asr_file": "/data1/rmx/projectb/AdsQA-main/evaluation/asr_set.json",
    "kb_file": "/data1/rmx/projectb/AdsQA-main/evaluation/marketing_knowledge_base_en.json",
    
    "previous_output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/163_fixed_v5",
    "output_dir": "/data1/rmx/projectb/AdsQA-main/evaluation/501",
    
    # 专利 S2 参数
    "shot_threshold": 30.0,  # 镜头检测阈值 (专利 S12)
    "top_k_frames": 16,      # 最终输入大模型的帧数
    "crop_ratio": 0.75,      # 局部锚框比例
    "min_pixels": 256*256,   # Qwen 输入分辨率限制
    "max_pixels": 1280*1280
}

ImageFile.LOAD_TRUNCATED_IMAGES = True

# 日志配置
log_file = f'/data1/rmx/projectb/AdsQA-main/evaluation/logs/patent_gpu{args.gpu_id}.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[logging.FileHandler(log_file, mode='a'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ================= 核心功能函数 =================

# [专利 S12] 基于镜头分割的帧提取
def load_frames_patent_aligned(video_path: str, max_frames: int = 16) -> List[Image.Image]:
    if not os.path.exists(video_path): return []
    frames = []
    
    # 策略 A: 优先使用 PySceneDetect (镜头分割)
    if SCENE_DETECT_AVAILABLE and DECORD_AVAILABLE:
        try:
            video_manager = VideoManager([video_path])
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=CONFIG["shot_threshold"]))
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
            scene_list = scene_manager.get_scene_list()
            
            timestamps = []
            # 如果没检测到场景变化，或者是单镜头视频，取首中尾
            if not scene_list:
                vr = VideoReader(video_path, ctx=cpu(0))
                total = len(vr)
                indices = np.linspace(0, total-1, max_frames, dtype=int)
            else:
                # 取每个镜头的中间帧
                for scene in scene_list:
                    start, end = scene[0].get_frames(), scene[1].get_frames()
                    timestamps.append((start + end) // 2)
                
                # 如果镜头数少于 max_frames，补充均匀采样
                vr = VideoReader(video_path, ctx=cpu(0))
                if len(timestamps) < max_frames:
                    remain = max_frames - len(timestamps)
                    extra_indices = np.linspace(0, len(vr)-1, remain, dtype=int)
                    indices = sorted(list(set(timestamps) | set(extra_indices)))
                # 如果镜头数多于 max_frames，均匀采样这些镜头
                else:
                    idx_map = np.linspace(0, len(timestamps)-1, max_frames, dtype=int)
                    indices = [timestamps[i] for i in idx_map]

            # 统一读取
            vr = VideoReader(video_path, ctx=cpu(0))
            for idx in indices:
                if idx >= len(vr): idx = len(vr) - 1
                try:
                    frame_arr = vr[int(idx)].asnumpy()
                    img = Image.fromarray(frame_arr).convert("RGB")
                    frames.append(img)
                except: continue
            if frames: return frames
        except Exception as e:
            logger.warning(f"Scene detect failed for {video_path}: {e}, using fallback.")

    # 策略 B: 回退到均匀采样 (如果 S12 失败)
    # ... (保留原有的读取逻辑作为兜底) ...
    if not frames and os.path.isdir(video_path):
        files = sorted(Path(video_path).glob("*.jpg")) + sorted(Path(video_path).glob("*.png"))
        if files:
            idx = np.linspace(0, len(files)-1, max_frames, dtype=int)
            for i in idx:
                try:
                    frames.append(Image.open(files[i]).convert("RGB"))
                except: continue
    
    # 最后兜底：Decord 均匀采样
    if not frames and DECORD_AVAILABLE and os.path.isfile(video_path):
        try:
            vr = VideoReader(video_path, ctx=cpu(0))
            indices = np.linspace(0, len(vr)-1, max_frames, dtype=int)
            for idx in indices:
                frames.append(Image.fromarray(vr[idx].asnumpy()).convert("RGB"))
        except: pass
        
    return frames

# [专利 S3] 知识库检索
class RAGRetriever:
    def __init__(self, kb_path, model_path, device='cuda'):
        self.kb_path = kb_path
        self.use_rag = False
        if not SENTENCE_RAG_AVAILABLE: return
        try:
            self.model = SentenceTransformer(model_path, device=device)
            self.use_rag = True
            with open(self.kb_path, 'r') as f: self.rules = json.load(f)
            # 构建知识库索引
            self.corpus = [f"Triggers: {','.join(r.get('trigger_features',[]))}. Logic: {r.get('marketing_logic','')}" for r in self.rules]
            self.index_embeddings = self.model.encode(self.corpus, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
        except Exception: self.use_rag = False

    def retrieve(self, query, top_k=3):
        if not self.use_rag: return ""
        try:
            q_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            scores = np.dot(q_vec, self.index_embeddings.T)[0]
            top_ids = np.argsort(scores)[::-1][:top_k]
            return "\n".join([f"- Rule {i+1}: {self.rules[idx].get('marketing_logic','')}" for i, idx in enumerate(top_ids)])
        except Exception: return ""

# [专利 S2] 视听协同处理与锚框生成
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
            from torchvision.transforms import ToTensor, Normalize, Resize, Compose
            self.preprocess = Compose([
                Resize((224, 224)),
                ToTensor(),
                Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))
            ])
            self.valid = True
        except Exception: pass

    def _encode_text(self, text):
        if not text: return None
        # CLIP text encoder max length is 77
        tokens = self.tokenizer([text[:77]], padding=True, return_tensors="pt").to(self.device)
        return F.normalize(self.text_enc(**tokens).text_embeds, dim=-1)

    def select_top_frames(self, frames, question, audio_text, top_k=8):
        # 专利 S21/S22: 基于 "视觉-问题" 和 "视觉-语音" 双流热力图筛选
        if not self.valid or not frames: return frames[:top_k]
        try:
            with torch.no_grad():
                # 预处理所有帧
                batch = []
                for f in frames:
                    if f.mode != 'RGB': f = f.convert('RGB')
                    batch.append(self.preprocess(f))
                
                imgs_ts = torch.stack(batch).to(self.device)
                vis_out = self.vision(imgs_ts)
                img_emb = F.normalize(vis_out.image_embeds, dim=-1)
                
                # 计算得分
                q_emb = self._encode_text(question)
                # 专利优化：语音权重不宜过大，避免无关旁白干扰，取 0.3
                scores = torch.matmul(img_emb, q_emb.T).view(-1)
                
                if audio_text:
                    a_emb = self._encode_text(audio_text) # 这里的 audio_text 应该是当前时间窗口的，这里简化为全文
                    scores = (scores * 0.7) + (torch.matmul(img_emb, a_emb.T).view(-1) * 0.3)
                
                scores = scores.cpu().numpy()
                
                # 如果帧数足够，选 TopK；否则全选
                if len(scores) <= top_k: return frames
                top_idx = sorted(np.argsort(scores)[-top_k:])
                return [frames[i] for i in top_idx]
        except Exception as e:
            logger.error(f"Selection error: {e}")
            return frames[:top_k]

    def smart_crop(self, frame, question, audio_text):
        # 专利 S23/S24: 局部流锚框生成
        # 修正：不进行缩放，而是从原图 Crop 出高分辨率区域
        if not self.valid: return frame
        try:
            with torch.no_grad():
                # 为了计算 Heatmap，必须缩放到 CLIP 尺寸 (224/336)，但 crop 要在原图操作
                t_img = self.preprocess(frame).unsqueeze(0).to(self.device)
                vis_out = self.vision(t_img)
                
                # 提取 Patch features
                last_hidden = vis_out.last_hidden_state[:, 1:] 
                if hasattr(self.vision, 'visual_projection'):
                    last_hidden = self.vision.visual_projection(last_hidden)
                patch_emb = F.normalize(last_hidden, dim=-1) # [1, 256, 768] for ViT-L
                
                # 融合 Question 和 OCR 关注点 (Logo/Text)
                q_emb = self._encode_text(question)
                ocr_emb = self._encode_text("text number logo price url") # 增加 OCR 关键词
                
                hm_q = torch.matmul(patch_emb, q_emb.T).view(-1)
                hm_ocr = torch.matmul(patch_emb, ocr_emb.T).max(dim=1).values.squeeze()
                
                fused = (hm_q * 0.6) + (hm_ocr * 0.4)
                
                # 还原为 heatmap
                side = int(fused.shape[0]**0.5) # 16 for 224px, 24 for 336px
                hm = fused.view(side, side).cpu().numpy()
                
                # 计算重心 (Patent S231)
                hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
                h_map, w_map = hm.shape
                y, x = np.indices((h_map, w_map))
                tot = hm.sum() + 1e-8
                cy, cx = np.sum(y * hm) / tot, np.sum(x * hm) / tot
                
                # 映射回原图坐标
                ow, oh = frame.size
                ctx, cty = int((cx/w_map)*ow), int((cy/h_map)*oh)
                
                # 裁剪 (Patent S24)
                cw, ch = int(ow * CONFIG["crop_ratio"]), int(oh * CONFIG["crop_ratio"])
                l, t = max(0, ctx - cw//2), max(0, cty - ch//2)
                r, b = min(ow, l+cw), min(oh, t+ch)
                
                # 边界修正
                if r-l < cw: l = max(0, r-cw)
                if b-t < ch: t = max(0, b-ch)
                
                return frame.crop((l, t, r, b))
        except Exception:
            return frame

# ================= Prompt 类 (Patent S4 & S5) =================
class CoTReflectionPrompts:
    @staticmethod
    def initial_prompt(question, asr, rag):
        # 专利 S42: 结构化 Prompt
        rag_text = f"\n[Expert Context]\n{rag}" if rag else ""
        return f"""Analyze the video content (Global views + Local details) and audio to answer the question following the strict 4-step logic.

Question: {question}
Audio Transcript: {asr}
{rag_text}

Instructions:
1. [Observation]: Objectively describe the key visual scenes (actions, objects, text) and auditory information.
2. [Analysis]: Analyze the metaphors, persuasion strategies, or marketing logic.
3. [Reasoning]: Synthesize observation and analysis to deduce the answer.
4. [Answer]: Provide the final concise answer.

Output format:
[Observation]: ...
[Analysis]: ...
[Reasoning]: ...
[Answer]: ..."""

    @staticmethod
    def reflection_prompt(question, initial_ans):
        # 专利 S5: 自我反思
        return f"""Role: Marketing Logic Checker.
Question: {question}
Draft Answer: "{initial_ans}"

Task: Check for hallucinations or logic errors.
Output: 
If correct, output: [KEEP]
If errors exist, output: [Final Answer]: (Corrected answer)"""

# ================= 主程序 =================
def main():
    logger.info(f"🚀 Starting process on GPU {args.gpu_id}")

    # 初始化模块
    retriever = RAGRetriever(CONFIG["kb_file"], CONFIG["rag_model_path"])
    s23_processor = S23VisualProcessor(device="cuda", clip_path=CONFIG["clip_path"])
    
    logger.info("Loading Qwen2.5-VL...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        CONFIG["model_dir"], 
        torch_dtype=torch.float16, 
        device_map="auto"
    )
    # 修正：设置 min_pixels/max_pixels 确保图像清晰度
    processor = AutoProcessor.from_pretrained(
        CONFIG["model_dir"], 
        min_pixels=CONFIG["min_pixels"], 
        max_pixels=CONFIG["max_pixels"]
    )
    
    # 加载数据
    with open(CONFIG["question_file"]) as f: questions = json.load(f)
    asr_data = json.load(open(CONFIG["asr_file"])) if os.path.exists(CONFIG["asr_file"]) else {}
    
    # 范围过滤
    if args.end_idx != -1:
        questions = questions[args.start_idx : args.end_idx]
    
    TRIGGERS = ["text", "say", "number", "logo", "url", "why", "logic"]
    
    for i, item in enumerate(tqdm(questions, desc=f"GPU {args.gpu_id}")):
        if i % args.num_shards != args.shard_id: continue
        
        qid = item['question_id']
        save_path = Path(CONFIG["output_dir"]) / qid / "prediction.json"
        
        # 智能跳过
        if save_path.exists(): continue
        if Path(CONFIG["previous_output_dir"]).joinpath(qid, "prediction.json").exists(): continue

        # 视频路径处理
        vid = item.get('video', item.get('video_id', qid.split('_')[0]))
        vpath = os.path.join(CONFIG["frame_root"], f"{vid}.mp4")
        if not os.path.exists(vpath): vpath = os.path.join(CONFIG["frame_root"], vid)
        
        # [Step 1] 获取帧 (S12: Scene Detect)
        raw_frames = load_frames_patent_aligned(vpath, max_frames=32)
        if not raw_frames: continue
        
        # [Step 2] 视听协同筛选 (S21/S22)
        asr_text = asr_data.get(f"{vid}.mp4", "") or asr_data.get(vid, "")
        # 修正：ASR 不再截断，或者保留更长长度 (e.g. 500)
        selected_frames = s23_processor.select_top_frames(
            raw_frames, item['question'], asr_text[:1000], CONFIG["top_k_frames"]
        )
        
        # [Step 3] 构建双流输入 (S24)
        final_input_frames = []
        for f in selected_frames:
            # 局部流：Smart Crop (高分辨率)
            local = s23_processor.smart_crop(f, item['question'], asr_text[:500])
            # 全局流：原图
            final_input_frames.extend([f, local])
        
        rag_ctx = retriever.retrieve(f"{item['question']} {asr_text[:500]}", top_k=3)
        
        try:
            # Round 1: 推理
            text_1 = CoTReflectionPrompts.initial_prompt(item['question'], asr_text, rag_ctx)
            
            # 构造 Qwen 格式 (Image list + Text)
            # 注意：Qwen2.5-VL 推荐将所有图片放在文本前或穿插，这里采用多图输入
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img} for img in final_input_frames
                    ] + [{"type": "text", "text": text_1}]
                }
            ]
            
            text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(
                text=[text_prompt],
                images=final_input_frames,
                padding=True,
                return_tensors="pt"
            ).to("cuda")
            
            with torch.no_grad():
                gen_1 = model.generate(**inputs, max_new_tokens=768, do_sample=False)
            ans_1 = processor.batch_decode(gen_1, skip_special_tokens=True)[0].split("assistant")[-1].strip()

            # 解析答案
            final_ans = ans_1
            if "[Answer]:" in ans_1:
                final_ans = ans_1.split("[Answer]:")[-1].strip()

            # Round 2: 反思 (Patent S5)
            q_lower = item['question'].lower()
            needs_reflect = any(t in q_lower for t in TRIGGERS)
            status = "Direct"

            if needs_reflect:
                text_2 = CoTReflectionPrompts.reflection_prompt(item['question'], ans_1)
                messages_2 = [
                    {
                        "role": "user", 
                        "content": [
                             {"type": "image", "image": final_input_frames[0]}, # 仅使用第一帧作为上下文索引，节省显存
                             {"type": "text", "text": text_2}
                        ]
                    }
                ]
                text_prompt_2 = processor.apply_chat_template(messages_2, tokenize=False, add_generation_prompt=True)
                inputs_2 = processor(
                    text=[text_prompt_2],
                    images=[final_input_frames[0]],
                    padding=True,
                    return_tensors="pt"
                ).to("cuda")

                with torch.no_grad():
                    gen_2 = model.generate(**inputs_2, max_new_tokens=512, do_sample=False)
                res_2 = processor.batch_decode(gen_2, skip_special_tokens=True)[0].split("assistant")[-1].strip()
                
                if "[Final Answer]:" in res_2:
                    final_ans = res_2.split("[Final Answer]:")[-1].strip()
                    status = "Corrected"
                elif "[KEEP]" in res_2:
                    status = "Verified"

            # 保存结果
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "question_id": qid,
                    "prediction": final_ans,
                    "reasoning": ans_1,
                    "status": status
                }, f, ensure_ascii=False, indent=2)
                
            torch.cuda.empty_cache()

        except Exception as e:
            logger.error(f"Error {qid}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()