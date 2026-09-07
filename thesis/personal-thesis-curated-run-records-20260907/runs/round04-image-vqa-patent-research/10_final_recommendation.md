# 最终专利创新推荐报告

## 执行结论

- 本轮目标：不再局限广告视频，围绕图像 VQA / 多模态问答重新构思更单一、更易实验的新专利技术机制。
- 最终建议：采用 **声明级证据许可状态机** 作为新申请核心，不再把“路由 + 图谱 + 仲裁 + 可信包”并列堆叠为独立权利要求。
- 推荐新专利名称：**一种面向图像视觉问答的声明级证据许可状态机方法及系统**。
- 推荐实验路线：首周 MVP 使用 `VLR-IF + TextVQA + VizWiz`，小规模补充 `MagiC` 或 `ChartQA`。
- 可直接用于后续交底书的文件：`06_innovation_candidates.md`、`08_revision_strategy.md`、`05_code_implementation_map.md`、`09_search_materials_report.md`。

## 为什么切换方向

原案和 round03 的问题是技术链条过长，容易被审查员拆成：

- 多模态输入；
- RAG；
- CoT/self-check；
- 置信度阈值；
- 知识图谱或规则路由；
- 结构化 prompt。

本轮将方案压缩为一个状态机：

```text
声明拆分
-> 证据需求
-> 证据匹配
-> 支持/冲突/不足/越权/降级/阻断/许可状态
-> 输出、降级或拒答
```

这样每一步都服务于“声明能不能被允许说出口”这一单一技术问题。

## 最佳创新点排序

| 排名 | 创新点 | 推荐用途 | 代码可行性 | 专利风险 |
|---|---|---|---|---|
| 1 | 声明级证据许可状态机 | 独立权利要求核心 | 中 | 中 |
| 2 | 声明类型到证据需求矩阵 | 从属权利要求/实施例 | 低到中 | 中 |
| 3 | 冲突优先阻断规则 | 从属权利要求/关键实施例 | 中 | 中 |
| 4 | 越权推断降级机制 | 从属权利要求/拒答实验 | 低到中 | 中 |
| 5 | 声明-证据-状态审计表 | 系统权利要求/实验输出 | 低 | 低到中 |

## 推荐权利要求策略

### 独立权利要求应限定

- 获取图像、问题和候选答案或候选声明；
- 将候选答案拆分为原子声明；
- 根据声明类型生成证据需求集合；
- 将证据需求与图像区域、OCR 文本、图表元素、文档字段或检索证据进行匹配；
- 计算声明-证据匹配矩阵，至少包含支持分数、冲突分数、缺失标记和证据定位；
- 根据匹配矩阵进入许可状态机；
- 根据状态执行输出、降级或阻断；
- 生成最终答案和声明级证据许可记录。

### 状态集合建议写入说明书

- `UNVERIFIED`
- `SUPPORTED`
- `CONFLICTED`
- `INSUFFICIENT`
- `OVERREACH`
- `DOWNGRADED`
- `BLOCKED`
- `PERMITTED`

### 不建议作为主创新点

- 普通 Visual RAG；
- 普通 claim checker；
- 普通 prompt 约束；
- 普通 confidence threshold；
- 普通知识图谱；
- 普通大模型自我反思。

## 论文热点依据

本轮外部检索显示，近年热点确实集中在声明级诊断、视觉证据 grounding、冲突来源拆分和拒答/不确定性：

- PhD CVPR 2025 将视觉幻觉来源拆成视觉模糊、多模态输入冲突、反常识冲突。
- PREHAL / evidential conflict 用证据冲突和不确定性检测视觉幻觉。
- MagiC 和 TreeBench 强调推理步骤与视觉区域证据对齐。
- MRAG-Suite / MRAG-Bench 强调 Visual RAG 中的 claim-level grounding、distractor 和证据利用问题。
- calibration / selective answering 方向强调模型何时应降级或拒答。

这些趋势支持“声明级证据许可状态机”的合理性，但也说明不能只写成 RAG 后处理。

## 推荐数据集

| 数据集 | 作用 | 推荐程度 |
|---|---|---|
| VLR-IF | 测 passage 干扰、证据有效/无效选择 | 高 |
| TextVQA | 测 OCR 文字声明许可 | 高 |
| VizWiz | 测证据不足、不可回答和拒答 | 高 |
| MagiC | 测 reasoning step 与 grounding 对齐 | 中高 |
| ChartQA | 测图表数值声明许可 | 中 |
| VQAv2 | 通用 VQA 对比，不适合作主实验 | 低 |

首周 MVP 推荐组合：`VLR-IF + TextVQA + VizWiz`。

## 代码实现支撑

| 模块 | 现有基础 | 建议新增/修改 |
|---|---|---|
| 声明拆分 | `code_refactor/reflection/claim_checker.py` | 扩展 `AtomicClaim`、`ClaimType` |
| 证据包 | `code_refactor/evidence/evidence_package.py` | 新增 `EvidenceItem`、`EvidencePermissionRecord` |
| 证据需求矩阵 | 部分来自 `ClaimCheckPlan.required_evidence` | 新增 `evidence_requirement.py` |
| 许可状态机 | 暂无 | 新增 `claim_permission_state_machine.py` |
| 受控生成 | `code_refactor/reasoning/prompt_builder.py` | 修改为只输出 `PERMITTED/DOWNGRADED` 声明 |
| 实验输出 | 暂无 | 输出 `claim_permission_records.json` |

## 主要风险

- 如果只写“拆声明、找证据、判断支持”，会被认为是普通 claim checker。
- 如果只写“证据不足就拒答”，会被认为是常规阈值策略。
- 如果把 OCR、图表、检索、grounding 都并列写成模块，会回到组合发明风险。
- 需要把权利要求核心放在“证据需求矩阵 + 匹配矩阵 + 状态转移 + 生成动作绑定”。

## 下一步任务

1. 启动 round05：实现状态机 MVP。
2. 新增 `claim_permission_state_machine.py`、`evidence_requirement.py`、`permission_prompt_builder.py`。
3. 构造 20-50 条本地样例，先不大规模跑模型。
4. 输出 `claim_permission_records.json`，作为专利实施例材料。
5. 再基于 MVP 结果写新专利交底书。
