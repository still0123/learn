# P1 材料清单

## 本地材料

| ID | 路径 | 类型 | 用途 | 可靠性 | 备注 |
|---|---|---|---|---|---|
| M1 | `source_texts/patent_docx.txt` | 原始申请提取文本 | 判断原案已公开内容、避免复审超范围，也用于识别可迁移到新申请的技术基础 | 高 | 包含三流热力图、滑动窗口、响应密度、自适应锚定、链式校验等原案内容 |
| M2 | `source_texts/patent_office_action_pdf_extract.txt` | 驳回决定/审查意见提取文本 | 识别审查员拆解路径和新申请应避开的弱表达 | 高 | 已明确原案被 D1-D5 和公知常识组合驳回 |
| M3 | `source_texts/patent_opinion_statement.txt` | 意见陈述文本 | 识别已用过但未说服审查员的论点 | 中高 | 重点避免重复“广告场景特殊”“法律问答不同”等弱论证 |
| M4 | `runs/patent-analysis-20260623-round01/10_final_recommendation.md` | 第一轮多 Agent 总结 | 作为本轮重申请设计的起点 | 高 | 已指出 evidence package / evidence ID 更适合继续申请/新申请 |
| M5 | `runs/patent-analysis-20260623-round01/06_innovation_candidates.md` | 第一轮创新点候选 | 复用其中可转化的候选，排除复审风险较高的候选 | 高 | I-01/I-02 适合原案，evidence package 适合新申请 |
| M6 | `code_refactor/evidence/evidence_package.py` | 代码实现 | 证据包、ASR/OCR/Logo/Meta 字段基础 | 高 | 可作为 EvidenceUnit / TrustedEvidencePackage 的工程起点 |
| M7 | `code_refactor/reflection/claim_checker.py` | 代码实现 | 声明类型到证据类型的路由雏形 | 高 | 可演化为问题驱动证据路由 |
| M8 | `code_refactor/reasoning/prompt_builder.py` | 代码实现 | 证据约束 prompt 基础 | 高 | 可演化为可信证据包约束生成 |
| M9 | `code_refactor/rag/retriever.py` | 代码实现 | 检索和 evidence_id 支撑字段 | 中高 | 可作为证据约束知识检索的辅助模块 |
| M10 | `docs/patent_agent_workflow.md` | 工作流规范 | 约束本轮输出结构和门禁 | 高 | 明确禁止模块拼接式表述 |
| M11 | `docs/patent_agent_roles.md` | 角色规范 | 定义 P0-P9 多 Agent 职责 | 高 | 本轮按 P6/P8/P5/P7 并行执行 |

## 本轮材料判断

- 原案复审可用的强点仍是“三模态响应图 + 声画异步 + 响应密度锚定”，但这一路线已被审查员重点攻击，继续重发风险较高。
- 新申请更适合把重点转到“证据单元化、一致性图谱、冲突仲裁、可信证据包”，因为该路线能从现有代码中的 `EvidencePackage` 和 `claim_checker` 自然延展，并与原案的热力图/RAG/链式校验表达拉开距离。
- 当前代码尚未实现新路线的核心模块，因此本轮只能给出设计和实现路线，不能声称已有完整实验结果。
