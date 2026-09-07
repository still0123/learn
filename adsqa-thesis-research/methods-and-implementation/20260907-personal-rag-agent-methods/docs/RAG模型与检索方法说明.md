# 当前 RAG 采用的模型/方法说明

## 1. 简短回答

当前代码中的 RAG **没有使用神经 embedding 模型**，也没有使用 FAISS / Milvus / Chroma 这类向量库。

当前实现是一个无外部依赖的轻量检索器：

```text
token overlap + TF cosine + evidence-aware rerank
```

对应文件：

```text
code_refactor/rag/retriever.py
```

原始代码包里也没有完整 RAG 模块，只有营销知识库：

```text
patent_marketing_knowledge_base_deduplicated.json
```

我本轮做的是把这个知识库转换为统一 schema，并实现一个可跑通的证据驱动检索器。

---

## 2. 当前 RAG 的输入

当前 RAG 输入包括：

```text
question
EvidencePackage.asr
EvidencePackage.ocr_text
EvidencePackage.logo_text
EvidencePackage.meta_info
EvidencePackage.visual_tags
EvidencePackage.ad_evidence_types
```

也就是：

```text
用户问题 + 证据包文本
```

这符合论文第4章的“证据驱动广告知识检索”。

---

## 3. 当前 RAG 的知识库

当前知识库来自：

```text
/Users/bytedance/vqa_thesis_continue/code_review_extract/代码/patent_marketing_knowledge_base_deduplicated.json
```

共：

```text
268 条
```

原始字段：

```text
trigger_features
marketing_logic
dimension
industry_context
source_seed_id
```

转换后字段：

```text
knowledge_id
title
content
keywords
trigger_features
dimension
industry_context
source_seed_id
potential_leakage
risk_notes
```

注意：

```text
source_seed_id 存在潜在数据泄漏风险
```

如果 source_seed_id 来自测试集，正式实验中需要重新构建知识库或证明 train/test 隔离。

---

## 4. 当前 RAG 的打分公式

代码中最终分数：

```text
score = 0.50 * semantic_score
      + 0.20 * keyword_score
      + 0.30 * evidence_score
```

其中：

### semantic_score

使用 TF cosine：

```text
cosine(Counter(tokens(query)), Counter(tokens(knowledge_text)))
```

### keyword_score

计算 query 和知识条目关键词/trigger_features 的 token overlap。

### evidence_score

计算 evidence package 文本与知识条目的 TF cosine，并根据 `ad_evidence_types` 做轻量加权。

---

## 5. 当前 RAG 的优点

1. 无需安装模型；
2. 无需 GPU；
3. 可复现；
4. 能快速跑通论文 pipeline；
5. 能明确输出 supporting_evidence_ids；
6. 适合作为 MVP 和消融 baseline。

---

## 6. 当前 RAG 的不足

1. 不是语义 embedding 检索；
2. 中文/英文混合语义匹配能力有限；
3. 无法处理深层同义表达；
4. 没有向量索引；
5. evidence_score 仍然是词面级；
6. 不能直接作为最终最强 RAG 实验版本。

---

## 7. 后续升级建议

如果要做正式实验，建议逐步升级：

### 方案 A：bge-m3

推荐度最高。

```text
BAAI/bge-m3
```

优点：

- 支持中文、英文、多语言；
- 支持 dense / sparse / multi-vector；
- 适合中英混合广告数据。

### 方案 B：bge-large-zh / bge-large-en

如果主要中文知识库，可用：

```text
BAAI/bge-large-zh-v1.5
```

如果主要英文 AdsQA，可用：

```text
BAAI/bge-large-en-v1.5
```

### 方案 C：m3e

中文轻量方案：

```text
moka-ai/m3e-base
```

### 方案 D：text-embedding API

如果可以调用外部 embedding API，可用文本 embedding 服务。

### 方案 E：FAISS

向量库建议先用 FAISS：

```text
faiss-cpu / faiss-gpu
```

---

## 8. 论文中应该怎么写当前实现

如果你还没升级 embedding 模型，论文中建议写：

```text
当前原型系统采用轻量级词项重叠与 TF-cosine 检索实现广告知识召回，并加入证据匹配项进行重排序。该实现不依赖额外向量模型，便于验证证据驱动 RAG 流程。后续实验可进一步替换为 bge-m3、bge-large 或 FAISS 向量检索，以提升语义召回能力。
```

不要写：

```text
本文使用 bge-m3 向量模型
本文使用 FAISS 向量库
本文使用 dense retrieval
```

除非你真的接入并跑了。

---

## 9. 消融实验建议

RAG 相关消融可以设计成：

| 设置 | 检索方法 | 说明 |
|---|---|---|
| no RAG | 无 | 不注入知识 |
| random RAG | 随机 | 随机抽知识，排除 Prompt 变长影响 |
| lexical RAG | TF cosine | 当前实现 |
| evidence-aware lexical RAG | TF cosine + evidence rerank | 当前主实现 |
| embedding RAG | bge-m3 / FAISS | 后续升级 |
| oracle RAG | 人工选知识 | 上限参考 |

---

## 10. 当前接入脚本

我已新增：

```text
code_refactor/scripts/run_rag_qwen3_inference.py
```

支持：

```text
--dry-run
```

dry-run 不加载 Qwen3，只构建 evidence package、RAG、prompt、claim plan。

正式推理时去掉：

```text
--dry-run
```

即可尝试加载 Qwen3。
