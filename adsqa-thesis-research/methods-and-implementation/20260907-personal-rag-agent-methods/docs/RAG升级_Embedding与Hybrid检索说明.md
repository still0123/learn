# RAG 升级说明：Embedding / Hybrid 检索

## 1. 本轮完成

在原有 lexical RAG 基础上，已新增可选的 embedding / hybrid RAG。

新增文件：

```text
code_refactor/rag/embedding_retriever.py
code_refactor/scripts/build_rag_index.py
code_refactor/tests/test_embedding_rag.py
```

已修改：

```text
code_refactor/scripts/run_rag_qwen3_inference.py
```

现在支持：

```text
--retriever lexical
--retriever embedding
--retriever hybrid
```

---

## 2. 当前支持的 embedding backend

### 2.1 hashing

```text
--embedding-backend hashing
```

无依赖，用于测试代码路径，不是真语义 embedding。

### 2.2 sentence-transformers

```text
--embedding-backend sentence-transformers
--embedding-model /path/to/model_or_model_name
```

适合接：

```text
BAAI/bge-m3
BAAI/bge-large-zh-v1.5
BAAI/bge-large-en-v1.5
moka-ai/m3e-base
```

前提：环境安装 `sentence-transformers`。

### 2.3 FlagEmbedding

```text
--embedding-backend flagembedding
--embedding-model BAAI/bge-m3
```

如果模型名包含 `bge-m3`，会优先用：

```text
BGEM3FlagModel
```

否则用：

```text
FlagModel
```

前提：环境安装 `FlagEmbedding`。

### 2.4 transformers mean pooling

```text
--embedding-backend transformers
--embedding-model /path/to/embedding_model
```

用 AutoModel + mean pooling，兼容性更通用，但效果依赖模型。

---

## 3. 检索模式说明

### lexical

当前 MVP：

```text
token overlap + TF cosine + evidence-aware rerank
```

命令中使用：

```text
--retriever lexical
```

不需要索引。

### embedding

使用 embedding index：

```text
query embedding vs knowledge embedding
```

命令中使用：

```text
--retriever embedding
--rag-index path/to/index.json
```

### hybrid

融合 lexical 和 embedding：

```text
score = lexical_weight * lexical_score + (1 - lexical_weight) * embedding_score
```

命令中使用：

```text
--retriever hybrid
--rag-index path/to/index.json
```

---

## 4. 构建索引

### 4.1 测试用 hashing 索引

已测试通过：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/build_rag_index.py \
  --backend hashing \
  --out /Users/bytedance/vqa_thesis_continue/code_refactor/indexes/marketing_kb_hashing.index.json
```

输出：

```text
indexed 268 items with backend=hashing
```

### 4.2 bge-m3 索引建议命令

如果服务器有 `FlagEmbedding` 和 bge-m3：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/build_rag_index.py \
  --backend flagembedding \
  --model BAAI/bge-m3 \
  --out /data1/rmx/projectb/AdsQA-main/evaluation/indexes/marketing_kb_bge_m3.index.json
```

如果模型是本地路径：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/build_rag_index.py \
  --backend flagembedding \
  --model /data1/rmx/projectb/models/bge-m3 \
  --out /data1/rmx/projectb/AdsQA-main/evaluation/indexes/marketing_kb_bge_m3.index.json
```

如果用 sentence-transformers：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/build_rag_index.py \
  --backend sentence-transformers \
  --model /data1/rmx/projectb/models/bge-m3 \
  --out /data1/rmx/projectb/AdsQA-main/evaluation/indexes/marketing_kb_bge_m3_st.index.json
```

---

## 5. RAG 推理脚本使用

### 5.1 lexical dry-run

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py \
  --dry-run \
  --retriever lexical \
  --start-idx 0 \
  --end-idx 10 \
  --output-dir /data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_rag_lexical_dryrun
```

### 5.2 hybrid dry-run

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py \
  --dry-run \
  --retriever hybrid \
  --rag-index /data1/rmx/projectb/AdsQA-main/evaluation/indexes/marketing_kb_bge_m3.index.json \
  --embedding-backend flagembedding \
  --embedding-model /data1/rmx/projectb/models/bge-m3 \
  --start-idx 0 \
  --end-idx 10 \
  --output-dir /data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_rag_hybrid_dryrun
```

### 5.3 hybrid + Qwen3 正式推理

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py \
  --retriever hybrid \
  --rag-index /data1/rmx/projectb/AdsQA-main/evaluation/indexes/marketing_kb_bge_m3.index.json \
  --embedding-backend flagembedding \
  --embedding-model /data1/rmx/projectb/models/bge-m3 \
  --model-dir /data1/qky/Model/QWen3VL \
  --gpu-id 0 \
  --start-idx 0 \
  --end-idx 10 \
  --output-dir /data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_rag_hybrid \
  --overwrite
```

---

## 6. 本地测试结果

已通过：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/tests/test_embedding_rag.py
```

输出：

```text
embedding/hybrid rag tests passed
```

已构建 hashing 索引：

```text
/Users/bytedance/vqa_thesis_continue/code_refactor/indexes/marketing_kb_hashing.index.json
```

已跑 hybrid dry-run：

```json
{
  "total": 2,
  "written": 2,
  "skipped": 0,
  "errors": []
}
```

输出目录：

```text
/Users/bytedance/vqa_thesis_continue/code_refactor/outputs/rag_hybrid_dryrun
```

---

## 7. 论文写法建议

如果只用当前 lexical：

```text
原型系统采用词项重叠与 TF-cosine 实现轻量广告知识检索，并加入证据匹配项进行重排序。
```

如果你后续用 bge-m3 跑通：

```text
进一步地，本文使用 bge-m3 对用户问题、证据包和广告知识条目进行语义向量编码，并采用混合检索方式融合词项匹配分数与向量相似度分数，从而提升广告营销概念的语义召回能力。
```

---

## 8. 注意事项

1. `hashing` 只是测试 backend，不应作为最终论文中的 embedding 模型；
2. 若使用 `bge-m3`，需要记录模型路径、版本、embedding 维度、索引文件；
3. 当前索引是 JSON 存储，知识库只有 268 条足够用；若知识库扩展到上万条，再考虑 FAISS；
4. RAG 知识库存在 `source_seed_id`，正式实验需要处理数据泄漏风险。
