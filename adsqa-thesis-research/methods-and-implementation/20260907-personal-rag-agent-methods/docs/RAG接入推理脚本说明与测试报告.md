# RAG 接入推理脚本说明与测试报告

## 1. 已完成接入

新增脚本：

```text
/Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py
```

该脚本将以下模块接入到一个统一 pipeline：

```text
AdsQA Loader
→ Evidence Package
→ Marketing KB
→ Evidence-aware RAG Retriever
→ Structured Prompt Builder
→ Claim Check Plan
→ Qwen3 Inference（非 dry-run 时）
→ 输出 JSON
```

---

## 2. 支持两种运行模式

### 2.1 dry-run 模式

不加载 GPU 模型，只测试：

- 数据读取；
- evidence package；
- RAG；
- Prompt；
- claim check plan；
- 输出 JSON。

命令：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py \
  --dry-run \
  --start-idx 0 \
  --end-idx 3 \
  --output-dir /Users/bytedance/vqa_thesis_continue/code_refactor/outputs/rag_inference_dryrun \
  --overwrite
```

测试结果：

```json
{
  "total": 3,
  "written": 3,
  "skipped": 0,
  "errors": []
}
```

### 2.2 正式 Qwen3 推理模式

去掉 `--dry-run` 即会尝试加载 Qwen3：

```bash
PYTHONPATH=/Users/bytedance/vqa_thesis_continue/code_refactor \
python3 /Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py \
  --model-dir /data1/qky/Model/QWen3VL \
  --gpu-id 0 \
  --start-idx 0 \
  --end-idx 10 \
  --output-dir /data1/rmx/projectb/AdsQA-main/evaluation/results_qwen3_rag \
  --overwrite
```

注意：正式模式依赖服务器上的模型路径、GPU、`transformers`、`qwen_vl_utils` 和 CUDA 环境。本地 Mac 环境只验证了 dry-run。

---

## 3. 输出格式

每个样本输出：

```text
output_dir/question_id/rag_qwen3_pipeline.json
```

如果正式推理成功，还会输出：

```text
output_dir/question_id/prediction.json
```

`rag_qwen3_pipeline.json` 包含：

```json
{
  "question_id": "...",
  "video": "...",
  "question": "...",
  "answer": "...",
  "task_types": ["Type_..."],
  "prediction": null,
  "latency_sec": null,
  "dry_run": true,
  "evidence_packages": [...],
  "retrieved_knowledge": [...],
  "prompt": "...",
  "claim_check_plan": [...],
  "frame_paths": [...]
}
```

---

## 4. dry-run 样例结果

样本：

```text
b850d75633fa4d3abe8041d6d4402b4c_2
```

问题：

```text
How does the ad visually communicate the speed of Screwfix Sprint's delivery service?
```

检索结果：

```text
MK0017 跨渠道叙事与稀缺性营销 score=0.4246
MK0009 Social Impact score=0.422
MK0232 Lifestyle Association score=0.3788
```

Prompt 长度：

```text
3365 chars
```

说明：dry-run 本地没有 `/data1/.../frames_8`，所以 frame_paths 数量为 0。到服务器路径存在时会自动读取帧。

---

## 5. 当前 RAG 用的是什么模型？

当前 RAG 没有使用 embedding 模型。

当前方法是：

```text
token overlap + TF cosine + evidence-aware rerank
```

代码：

```text
code_refactor/rag/retriever.py
```

打分：

```text
score = 0.50 * semantic_score
      + 0.20 * keyword_score
      + 0.30 * evidence_score
```

其中 semantic_score 也是 TF cosine，不是 dense embedding。

---

## 6. 当前限制

1. 本地 dry-run 没有视频帧路径，所以 evidence package 是文本级；
2. 当前没有 OCR bbox；
3. 当前没有 Logo detection；
4. 当前 RAG 是词项级，不是 embedding；
5. 当前 claim checker 是规则版，不是真 LLM 证据判定；
6. 正式 Qwen3 推理需要服务器 GPU 环境。

---

## 7. 下一步建议

下一步最应该做：

1. 在服务器上用 `--dry-run` 先跑 10 条，确认 frame_paths 不为 0；
2. 去掉 `--dry-run` 跑 5–10 条 Qwen3 RAG 推理；
3. 检查输出的 `rag_qwen3_pipeline.json` 和 `prediction.json`；
4. 用 `eval/aggregate_results.py` 做 coverage；
5. 再接 LLM Judge 计算 Accuracy。

---

## 8. 后续升级 RAG 模型

建议升级顺序：

1. 当前 lexical RAG 作为 baseline；
2. 接 `bge-m3` 做 embedding RAG；
3. 用 FAISS 建索引；
4. 比较：
   - no RAG；
   - random RAG；
   - lexical RAG；
   - evidence-aware lexical RAG；
   - embedding RAG；
   - evidence-aware embedding RAG。
