# 检索材料报告

## 本轮使用范围

本轮未新增外部检索，依据驳回决定中已经引用的5篇专利和公知常识材料进行复核。

## 已知对比文件覆盖

- D1：视频问答、候选区域、字幕、关键帧、低置信度迭代。
- D2：LLM初始答案、验证问题、验证答案、答案修正和证据链。
- D3：OCR、ROI、全局/局部视觉、外部知识Top-K和多模态拼接。
- D4：异构模态接入、时间对齐、统一语义表示、约束解码和领域规则。
- D5：问题导向Grad-CAM关注区域。

## 下一轮必须检索

1. `claim-evidence graph` / `statement evidence graph`
2. `evidence gap driven active perception`
3. `temporal spatial evidence acquisition for video QA`
4. `provenance-aware answer verification`
5. `parent-child evidence lineage`
6. `claim-level multimodal retrieval and verification`

## 检索目标

不是再次证明MMR、ROI、RAG或自验证分别已知，而是确认以下紧密组合是否已公开：

> 声明-证据状态直接产生时间/空间获取参数，补充证据以父子谱系回写同一状态图，并由更新后的同一状态控制答案替换。

## 风险提示

新申请前还应核对旧申请是否已经公开，以及旧申请和本项目论文、代码、答辩材料是否构成影响新颖性或创造性的在先公开。
