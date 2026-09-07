# 材料清单

## 当前主线

- `deliverables/patent/视频问答答案可靠性保障专利申请候选稿_V3_20260823.md`
- `runs/patent-analysis-20260823-round04/10_final_recommendation.md`

## 可复用本地基础

- `code_refactor/reflection/claim_checker.py:18-42`：答案轻量拆分及声明类型到 OCR、ASR、局部/全局视图需求的映射；目前是脚手架。
- `code_refactor/evidence/evidence_package.py:9-40`：证据 ID、帧位置、时间窗口、局部视图、ASR、OCR、Logo 等结构；文本桥接包不等于完整视觉实现。
- `evaluation/tools/build_modality_counterfactual_train_v1.py:217-340`：E+/单因素 E− 构造，但标签含 synthetic/not_human_gold。
- `evaluation/tools/train_lightweight_claim_evidence_verifier_v23.py:155-201`：分类、排序和一致性损失。
- `.remote_threshold_work/infer_qwen3_adaptive_crop_threshold_full_v1.py:179-208`：现有 A2 输入 A0，与隔离候选相反。
- `.remote_overnight_work/materialize_adsqa_supplement2526_candidates_v1.py:136-154`：Full-7844 触发后直接使用 A2，未执行后置配对门控。

## 新增外部近邻

- Q-Guide：问题引导识别缺失证据并调用 OCR/缩放/定位工具。
- Omni-Decision：显式多模态证据状态统一控制取证、验证、修复和停止。
- PBRC：只有提供外部验证证据见证集才允许信念改变，并包含回退策略。
- CN122264085A：第三方公开页显示同图像上下文下多候选生成并由选择模型裁决；需 CNIPA 正式核验。
- SciClaimEval/CMA：证据修改与反事实模态归因已有公开研究。

