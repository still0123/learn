# P2 当前 AdsQA Pipeline 映射摘要

## 1. 当前实验口径

完整 baseline 主口径：

| 方法 | 样本数 | Strict | Relaxed | 口径 |
|---|---:|---:|---:|---|
| Qwen3-Base / Qwen3-VL-Instruct | 7812 | 0.3788 | 0.5113 | 当前完整 baseline 最强 |
| Qwen2.5-7B-VL-ReAd-R | 7829 | 0.3460 | 0.4810 | ReAd 主口径 |
| MiniCPM-V-2_6 | 7839 | 0.2327 | 0.3647 | 多模型 baseline |
| Qwen2-VL-7B-Instruct | 7829 | 0.2095 | 0.3407 | 多模型 baseline |
| Qwen2.5-VL-7B-Instruct | 7829 | 0.1529 | 0.2578 | 普通 Qwen2.5-VL |
| LLaVA-OneVision | 7839 | 0.1484 | 0.2735 | 多模型 baseline |

当前最强内部实验：

```text
ours_qwen3_evidence_norag_bal2500_20260629
strict ≈ 41.96%
relaxed ≈ 54.62%
```

注意：这是 2500 balanced 子集，不能直接和全量 baseline 混比。

## 2. 当前方法结论

当前最稳结论：

```text
证据选择 > 检索更多知识
```

- evidence no-RAG 是最值得保留的主线。
- RAG/verifier 当前不能作为强贡献。
- verifier 目前只是骨架或关键词触发 self-check，不足以声称可靠性提升。

## 3. 已有可复用模块

### 原始代码

- `/Users/bytedance/vqa_thesis_continue/代码/inference.py`
  - 32 帧过采样；
  - CLIP 选 16 帧；
  - Question + ASR + OCR prompt 融合响应图；
  - 动态裁剪；
  - Global+Local 双流；
  - 关键词触发反思。

### `code_refactor`

- `data/adsqa_loader.py`：AdsQA 读取与 Type 映射。
- `evidence/evidence_package.py`：文本级 evidence package schema。
- `rag/retriever.py`：evidence-aware lexical RAG。
- `rag/embedding_retriever.py`：embedding / hybrid 检索接口。
- `reasoning/prompt_builder.py`：证据约束 Prompt。
- `reflection/claim_checker.py`：规则式 claim type / required evidence plan。
- `eval/aggregate_results.py`：prediction coverage 聚合。
- `scripts/run_rag_qwen3_inference.py`：RAG-Qwen3 pipeline，支持 dry-run。

## 4. 一周内可实现缺口

1. evidence package 落盘。
2. slot evidence no-RAG。
3. low-noise RAG 对照。
4. 真实 OCR 轻接入。
5. 规则版 claim permission。
6. Strict/Relaxed + 类型聚合评测脚本补齐。

## 5. 应降级的设想

- 训练新多模态大模型。
- 训练专门 OCR/Logo detector。
- 大规模人工标注全量 evidence frame/bbox/claim support。
- 完整图数据库 VideoRAG 作为主贡献。
- 复杂 LLM verifier 闭环并声称降低幻觉率。
- 缺乏日志支撑的 token/latency 大幅下降结论。

## 6. 适合 MVP 的 Top5 改造点

1. Ad Evidence Slot no-RAG。
2. Evidence Package 落盘 + 可追溯日志。
3. Typed OCR + Local Crop。
4. Slot-triggered RAG。
5. Claim Permission Audit 子集。

