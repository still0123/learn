# 代码闭环多 Agent 编排方案

> 目标：根据论文“证据定位—证据压缩—证据解释—证据校验”主线闭环修改代码。  
> 输入代码包：`/Users/bytedance/Documents/代码.zip`  
> 原始解压目录：`/Users/bytedance/vqa_thesis_continue/code_review_extract/代码`  
> 新代码工作区：`/Users/bytedance/vqa_thesis_continue/code_refactor`  
> 规则：不直接修改原始 zip 解压结果；所有新代码写到 `code_refactor`。

---

## 1. 固定目标

本轮代码闭环要完成最小可运行版本，而不是一次性完成全部论文理想系统。

最小目标：

```text
AdsQA JSON 读取
→ 证据包 schema
→ 由现有字段构建文本级 evidence package
→ 营销知识库转换
→ 证据驱动 RAG 检索
→ Prompt 构建
→ 结果聚合评估脚本
→ 轻量测试
```

GPU 模型推理不作为本轮测试硬依赖。已有 `inference.py` 中的 Qwen3 推理可后续接入。

---

## 2. Agent 角色

## C0 代码主编 Agent

职责：

- 决定本轮代码改动范围；
- 保持代码和论文主线一致；
- 控制不编造实验结果；
- 最终判断测试是否通过。

输出：

```text
代码修改总结
测试结果
仍需补充
```

---

## C1 代码阅读 Agent

职责：

- 阅读原始代码包；
- 建立脚本到论文模块的映射；
- 找出可复用代码和缺口。

输出 schema：

```markdown
## 已有代码模块
## 可复用逻辑
## 缺失模块
## 风险点
```

---

## C2 架构设计 Agent

职责：

- 设计 `code_refactor` 目录；
- 定义模块边界；
- 定义输入输出 JSON schema；
- 定义测试策略。

输出 schema：

```markdown
## 目录结构
## 模块接口
## 数据 schema
## 测试计划
```

---

## C3 实现 Agent

职责：

- 写代码；
- 复用已有数据文件；
- 实现 evidence package、RAG、prompt、eval；
- 不写 GPU 推理重代码。

输出 schema：

```markdown
## 新增文件
## 修改说明
## 如何运行
```

---

## C4 技术审查 Agent

职责：

- 检查代码是否和第3/4/5章一致；
- 检查 schema 是否清楚；
- 检查 RAG 是否是证据驱动；
- 检查营销知识库是否有泄漏风险。

输出 schema：

```markdown
## 技术问题
## 必须修改
## 可选优化
## 是否通过
```

---

## C5 测试 Agent

职责：

- 跑轻量测试；
- 不依赖 GPU；
- 检查 JSON 读取、类型映射、知识库转换、RAG 检索、prompt 构建、结果聚合。

输出 schema：

```markdown
## 测试命令
## 测试结果
## 失败项
## 是否通过
```

---

## C6 修改 Agent

职责：

- 根据 C4/C5 修复代码；
- 重新跑测试；
- 输出最终版。

---

## 3. 本轮实现范围

### 必须实现

1. `data/adsqa_loader.py`
   - 读取 `testset_question.json`、`testset_groundtruth.json`、`asr_set.json`；
   - 统计 Type_1–Type_5；
   - 映射 AdsQA 官方任务名。

2. `evidence/evidence_package.py`
   - 定义 evidence package schema；
   - 从 question、gt、asr、meta_info 构建文本级 evidence package；
   - 为后续图像 evidence 留字段。

3. `rag/marketing_kb.py`
   - 读取原始 `patent_marketing_knowledge_base_deduplicated.json`；
   - 转换为统一 KB schema；
   - 标记 source_seed_id 和 potential_leakage；
   - 支持导出 JSON。

4. `rag/retriever.py`
   - 无外部依赖；
   - token overlap + TF cosine；
   - evidence-aware score；
   - 输出 knowledge_id、score、supporting_evidence_ids。

5. `reasoning/prompt_builder.py`
   - 构建“观察—知识匹配—分析—答案”Prompt；
   - 输入 question、evidence_package、retrieved_knowledge。

6. `reflection/claim_checker.py`
   - 轻量声明类型规则；
   - 不调用模型；
   - 根据证据文本判断 claim_type 和所需 evidence_type。

7. `eval/aggregate_results.py`
   - 读取 prediction 目录和 groundtruth；
   - 统计 missing；
   - 按 Type_1–Type_5 聚合；
   - 输出 Markdown 表。

8. `tests/test_lightweight_pipeline.py`
   - 使用本地 JSON；
   - 测试 loader、KB 转换、RAG、Prompt。

### 暂不实现

1. GPU 多模态模型推理；
2. PaddleOCR / EasyOCR；
3. Logo 检测；
4. 真正 patch-level 响应图；
5. 真实 LLM Judge。

这些后续再做。

---

## 4. 通过门槛

本轮通过必须满足：

- Python 测试脚本能跑通；
- 能读取 7859 条 AdsQA QA；
- Type 展开统计为 10154；
- 能把 268 条营销知识库转换为统一 schema；
- RAG 对示例问题能返回相关条目；
- Prompt 能包含 evidence_id 和 knowledge_id；
- 不编造任何实验结果；
- 输出代码审查报告。

---

## 5. 后续接入 inference.py 的计划

本轮完成后，将在下一轮做：

1. 修改 `inference.py` 保存 evidence package JSON；
2. 把 `rag/retriever.py` 接入 prompt；
3. 把 `claim_checker.py` 升级为模型反思 prompt；
4. 记录 Token、Latency、Memory；
5. 输出第5章真实实验表。
