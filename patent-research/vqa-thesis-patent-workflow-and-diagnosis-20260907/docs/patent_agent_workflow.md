# 专利多 Agent 工作流规范

> 状态：有效草案。  
> 适用项目：`/Users/bytedance/vqa_thesis_continue`  
> 关联主线：`证据定位 → 证据压缩 → 证据解释 → 证据校验`  
> 参考规范：`docs/agent_orchestration_v2.md`

## 1. 目标

本工作流用于本地专利分析，不直接替代专利代理人的法律判断。系统目标是通过闭环多 Agent 机制，分析：

1. 原始专利文件；
2. 审查意见、驳回决定、意见陈述书；
3. 本地论文/开题材料；
4. 本地代码实现；
5. 本地对比文件/现有技术；

并产出：

- 可辩护的新创新点候选；
- 审查员式批判；
- 权利要求修改和意见陈述策略；
- 代码实现难度评估；
- 风险门禁报告。

## 2. 基本原则

### 2.1 不做模块拼接式表述

禁止把方案主线写成：

```text
视觉压缩 + RAG + CoT + Self-Reflection
```

推荐统一为：

```text
面向广告视频高信息密度、短时文字/Logo、声画异步和营销隐喻理解难题的可追溯多模态证据流闭环。
```

### 2.2 不编造数据

不得编造：

- 实验准确率；
- Token 节省比例；
- 延迟；
- 人工评估；
- 消融实验结果；
- 授权概率。

没有证据时写“待补”或“需实验证明”。

### 2.3 所有专利结论必须有证据路径

最终报告中的每个核心判断必须包含：

- 本地来源路径；
- 摘录、章节、页码或代码对象；
- 该来源支撑什么；
- 支撑强度：强 / 中 / 弱。

### 2.4 区分用途

每个创新点必须分类为：

- 可用于当前答复；
- 仅适合从属权利要求；
- 适合继续申请/新申请；
- 仅适合论文创新表述；
- 应放弃。

## 3. 输入材料优先级

### 3.1 机器可读文本

优先读取：

- `source_texts/patent_docx.txt`
- `source_texts/patent_office_action_pdf_extract.txt`
- `source_texts/patent_opinion_statement.txt`
- `source_texts/proposal_doc.txt`
- `source_texts/proposal_pptx.txt`
- `source_texts/adsqa_paper_extracted.txt`

### 3.2 专利与审查原件

必要时回查：

- `专利相关/`
- 根目录下的驳回决定 PDF。

### 3.3 论文与编排文档

- `docs/开题专利创新性诊断报告.md`
- `docs/agent_orchestration_v2.md`
- `docs/术语与题目真源.md`

### 3.4 代码实现

优先使用：

- `code_refactor/evidence/evidence_package.py`
- `code_refactor/rag/retriever.py`
- `code_refactor/reasoning/prompt_builder.py`
- `code_refactor/reflection/claim_checker.py`
- `rag_mvp/rag_retriever.py`

## 4. 每轮运行目录

每轮必须建立独立目录：

```text
runs/patent-analysis-YYYYMMDD-roundXX/
  00_plan.md
  01_material_inventory.md
  02_claim_feature_map.md
  03_office_action_issue_map.md
  04_prior_art_comparison_matrix.md
  05_code_implementation_map.md
  06_innovation_candidates.md
  07_examiner_critic_review.md
  08_revision_strategy.md
  09_search_materials_report.md
  10_final_recommendation.md
  gates.md
  artifacts.md
  sources_used.json
```

## 5. 标准执行顺序

1. `P0` 建立本轮计划和输出目录。
2. `P1` 盘点本地材料，输出 `01_material_inventory.md` 和 `sources_used.json`。
3. `P2` 拆解权利要求，输出 `02_claim_feature_map.md`。
4. `P3` 拆解审查意见/驳回理由，输出 `03_office_action_issue_map.md`。
5. `P4` 对比本地现有技术，输出 `04_prior_art_comparison_matrix.md`。
6. `P8` 评估代码实现难度，输出 `05_code_implementation_map.md`。
7. `P6` 构思创新点，输出 `06_innovation_candidates.md`。
8. `P5` 模拟审查员批判，输出 `07_examiner_critic_review.md`。
9. `P7` 形成修改与答复策略，输出 `08_revision_strategy.md`。
10. `P1` 如需外部检索，补充 `09_search_materials_report.md`。
11. `P9` 执行门禁，输出 `gates.md`。
12. `P0` 形成 `10_final_recommendation.md`。

## 6. 首轮默认问题

```text
基于审查意见/驳回决定、意见陈述书、专利文本、本地论文/开题材料、代码实现和本地对比文件，找出 3-5 个不属于简单模块拼接、且能够支撑权利要求修改/意见陈述/继续申请的新创新点。
```

## 7. 首轮重点候选方向

以下方向可作为初始假设，但必须经过 `P5` 和 `P9`：

1. 三模态协同响应图 + 声画异步滑动窗口；
2. 响应密度驱动的自适应局部证据锚定；
3. 证据约束的广告知识检索；
4. 声明级证据回溯校验；
5. 统一 evidence package / evidence ID 可追溯闭环。

## 8. 最终报告要求

`10_final_recommendation.md` 必须包含：

- 执行结论；
- 最佳 3-5 个创新点；
- 权利要求修改建议；
- 意见陈述建议；
- 代码实现支撑；
- 不建议主张的内容；
- 必须由专利代理人复核的事项；
- 下一步任务。
