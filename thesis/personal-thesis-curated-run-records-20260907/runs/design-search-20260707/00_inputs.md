# 方案孵化输入记录

日期：2026-07-07

目标：

```text
启动方案孵化多 Agent，结合 2025-2026 新文献和现有 AdsQA 实验，迭代筛选 top3/top5 技术方案并给出实验路线。
```

## 本轮输入材料

- `/Users/bytedance/vqa_thesis_continue/docs/方案孵化多Agent编排方案.md`
- `/Users/bytedance/vqa_thesis_continue/.claude/workflows/thesis-design-search-loop.js`
- `/Users/bytedance/vqa_thesis_continue/docs/2025-2026视觉问答定位视频理解顶会创新点详细综述.md`
- `/Users/bytedance/vqa_thesis_continue/docs/2025-2026视觉问答定位视频理解顶会创新点检索笔记.md`
- `/Users/bytedance/vqa_thesis_continue/docs/2025-2026多模态与视频问答顶会论文调研及论文改题建议.md`
- `/Users/bytedance/vqa_thesis_continue/docs/中期后技术改造路线-借鉴2025-2026视觉问答工作.md`
- `/Users/bytedance/vqa_thesis_continue/docs/AdsQA本地Baseline评测结果记录.md`
- `/Users/bytedance/vqa_thesis_continue/code_refactor/`

## 当前已知实验口径

| 方法 | 设置 | Strict | Relaxed | 结论 |
|---|---|---:|---:|---|
| qwen3 raw uniform no-RAG | oversample=8, top_k_frames=8 | 37.88 | 51.14 | Qwen3 同底座均匀/原始证据基线 |
| ours qwen3 evidence no-RAG | oversample=32, top_k_frames=16 | 41.96 | 54.62 | 当前最新三次中最好 |
| ours RAG v2 BGE verifier | hybrid RAG + BGE + verifier | 27.92 | 45.76 | 明显失败，不能作为主线 |

## 本轮方案搜索原则

1. 优先在当前 evidence no-RAG 成功基础上升级。
2. 不把普通 RAG、普通 crop、普通 token pruning、普通 self-check 当创新。
3. 每个候选方案必须能映射到 AdsQA 的广告视频特征：
   - Logo；
   - 价格；
   - 字幕/OCR；
   - 包装；
   - CTA；
   - ASR/旁白；
   - 声画错位；
   - 营销语义。
4. 候选方案必须给出可跑实验，不只给概念。
5. RAG 只能作为证据触发式、低噪声、受控知识注入，不能作为无约束增强。

## 本轮联网新增关注

除本地已记录文献外，本轮额外关注：

- VideoITG：instructed temporal grounding / discriminative frame selection。
- ReQuest：uncertainty-driven, question-adaptive keyframe selection。
- DyCoke / StreamingTOM / STC：2025-2026 video token compression。
- MME-VideoOCR：视频 OCR 能力评测。
- VideoRAG / ViG-RAG / temporal-aware RAG：视频结构化检索。
- VideoZeroBench / EV2-Bench：证据化视频理解评测。

