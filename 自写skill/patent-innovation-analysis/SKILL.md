---
name: patent-innovation-analysis
description: 本地专利多 Agent 编排：分析专利/审查意见/驳回意见/意见陈述/代码实现，构思创新点，模拟审查员批判并形成修改策略。
---

# Patent Innovation Analysis Skill

## 何时使用

当用户要求以下任一事项时使用本 skill：

- 分析专利创新性、创造性、新颖性风险。
- 解读审查意见、驳回决定、意见陈述书、答复策略。
- 从本地代码、论文、开题、实验材料中提炼可写入专利的新技术点。
- 模拟审查员批判当前权利要求、创新点或答复意见。
- 规划权利要求修改、从属权利要求布局、继续申请/新申请方向。
- 评估某个专利创新点的代码实现难度。

## 固定项目上下文

- 项目根目录：`/Users/bytedance/vqa_thesis_continue`
- 专利/审查材料：`专利相关/`
- 机器可读提取文本：`source_texts/`
- 项目多 Agent 总规范：`docs/agent_orchestration_v2.md`
- 创新性诊断参考：`docs/开题专利创新性诊断报告.md`
- 核心技术主线：`证据定位 → 证据压缩 → 证据解释 → 证据校验`

禁止把本项目简单表述成：

```text
视觉压缩 + RAG + CoT + Self-Reflection
```

应优先表述成：

```text
面向广告视频中高信息密度、短时文字/Logo、声画异步和营销隐喻理解难题的可追溯多模态证据流闭环。
```

## 关键本地材料

优先读取这些机器可读文件，而不是直接从 PDF/DOCX 开始：

- `source_texts/patent_docx.txt`
- `source_texts/patent_office_action_pdf_extract.txt`
- `source_texts/patent_opinion_statement.txt`
- `source_texts/proposal_doc.txt`
- `source_texts/proposal_pptx.txt`
- `source_texts/adsqa_paper_extracted.txt`
- `docs/开题专利创新性诊断报告.md`
- `docs/agent_orchestration_v2.md`

代码证据优先看：

- `code_refactor/evidence/evidence_package.py`
- `code_refactor/rag/retriever.py`
- `code_refactor/reasoning/prompt_builder.py`
- `code_refactor/reflection/claim_checker.py`
- `rag_mvp/rag_retriever.py`

## 多 Agent 角色

使用 `P` 前缀，避免和论文写作 Agent `A0-A9` 冲突。

| 编号 | 名称 | 职责 |
|---|---|---|
| P0 | 专利主编/协调 Agent | 总控、拆解任务、合并产物、最终裁决 |
| P1 | 材料与检索 Agent | 盘点本地专利、审查、意见陈述、论文、代码资料 |
| P2 | 权利要求-技术特征映射 Agent | 拆解权利要求并映射说明书/代码/论文支撑 |
| P3 | 审查意见问题分析 Agent | 抽取驳回逻辑、对比文件组合路径、当前答复弱点 |
| P4 | 对比文件/现有技术矩阵 Agent | 生成我方特征与本地对比文件的矩阵 |
| P5 | 模拟审查员批判 Agent | 敌对攻击模块拼接、常规手段、无技术效果、无原始支持等风险 |
| P6 | 创新点构思 Agent | 生成新技术点候选，并给出来源、差异、效果、风险 |
| P7 | 修改与答复策略 Agent | 形成权利要求修改、意见陈述、从属权利要求或继续申请策略 |
| P8 | 代码实现难度评审 Agent | 判断每个创新点的实现现状和实现难度 |
| P9 | 证据与风险门禁 Agent | 检查原始公开支持、现有技术差异、技术效果、无虚构数据、法律风险 |

## 标准工作流

每轮建立独立目录：

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

执行顺序：

1. `P0` 明确本轮问题、材料范围、输出目录。
2. `P1` 生成材料清单和关键证据摘录。
3. `P2` 生成权利要求-特征-支撑映射。
4. `P3` 生成审查意见/驳回逻辑问题图谱。
5. `P4` 生成对比文件矩阵。
6. `P8` 先评估代码可行性，避免提出无法落地的“纸面创新”。
7. `P6` 生成创新点候选。
8. `P5` 模拟审查员逐条攻击候选。
9. `P7` 将幸存候选转成修改/答复/继续申请策略。
10. `P9` 执行 gates。
11. `P0` 输出最终建议。

## 创新点候选必须包含

每个创新点必须写清：

- 技术机制。
- 为什么不是模块拼接。
- 原始公开支持：具体本地文件路径和摘录/章节。
- 相对对比文件的差异。
- 技术效果，不能编造实验数值。
- 权利要求修改路径。
- 代码实现依据和难度。
- 模拟审查员攻击预测。
- 建议：保留 / 修改 / 放弃 / 用于继续申请 / 仅用于论文表述。

可直接套用模板：`templates/innovation_candidate.md`。

## 模拟审查员原则

`P5` 必须敌对而不是配合，重点攻击：

- 是否只是普通视频问答套广告场景。
- 是否只是 RAG、CoT、自我验证、热力图、全局/局部特征的常规组合。
- 是否缺少原始说明书支持。
- 是否缺少客观技术效果。
- 是否属于业务规则/营销规则而非技术手段。
- 是否代码不可实现或当前代码没有支撑。

可套用模板：`templates/examiner_critic.md`。

## 当前优先候选方向

首轮优先考察这些方向，但必须接受 `P5` 批判和 `P9` gates：

1. 三模态协同响应图 + 声画异步滑动窗口。
2. 响应密度驱动的自适应局部证据锚定。
3. 证据约束的广告知识检索。
4. 声明级证据回溯校验。
5. 统一 evidence package / evidence ID 可追溯闭环。

## 门禁规则

最终建议不得出现：

- “保证授权”“一定具备创造性”等确定性法律结论。
- 未引用本地来源路径的核心事实。
- 未说明原始公开支持的新增技术特征。
- 编造的实验数据、准确率、token、latency、人工评估结果。
- 将 scaffold 或计划实现说成已完整实现。

如果 gate 未通过，输出只能标为：

```text
候选方向 / 修订建议 / 需代理人复核
```

不能标为：

```text
可直接提交
```

## 推荐首轮任务提示

```text
基于审查意见/驳回决定、意见陈述书、专利文本、本地论文/开题材料、代码实现和本地对比文件，找出 3-5 个不属于简单模块拼接、且能够支撑权利要求修改/意见陈述/继续申请的新创新点。请按 P0-P9 闭环执行，最后输出 gates 和最终建议。
```
