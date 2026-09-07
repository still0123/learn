# P1 材料清单

## 本地材料

| ID | 路径 | 类型 | 用途 | 可靠性 | 备注 |
|---|---|---|---|---|---|
| S01 | `source_texts/patent_docx.txt` | 专利正文提取文本 | 拆权利要求、找原始公开支持 | 高 | 当前最核心的一手机器可读材料 |
| S02 | `source_texts/patent_office_action_pdf_extract.txt` | 第二次审查意见通知书提取文本 | 提炼审查员的显而易见性逻辑 | 高 | 可直接定位到 D1-D5 的攻击路径 |
| S03 | `source_texts/patent_opinion_statement.txt` | 意见陈述书提取文本 | 分析现有答复的强点和弱点 | 高 | 有助于找“为什么当前论证还不够稳” |
| S04 | `docs/开题专利创新性诊断报告.md` | 二次分析文档 | 辅助识别主线重构方向 | 中 | 不是一手材料，但总结得较准确 |
| S05 | `docs/agent_orchestration_v2.md` | 项目编排主规范 | 复用闭环多 Agent、gates、可复跑结构 | 高 | 用于工作流设计而非专利事实判断 |
| S06 | `code_refactor/evidence/evidence_package.py` | 代码证据 | 判断 evidence package / evidence id 的实现基础 | 高 | 已有统一证据容器结构 |
| S07 | `code_refactor/rag/retriever.py` | 代码证据 | 判断“证据约束知识检索”是否已有实现基础 | 高 | 已有 supporting_evidence_ids 和 evidence_score |
| S08 | `code_refactor/reasoning/prompt_builder.py` | 代码证据 | 判断结构化观察-分析-答案协议实现程度 | 高 | 已有 observation / knowledge / analysis / answer 框架 |
| S09 | `code_refactor/reflection/claim_checker.py` | 代码证据 | 判断声明级证据回溯校验实现程度 | 高 | 已有 claim type 路由雏形 |
| S10 | `runs/patent-analysis-20260623-round01/09_search_materials_report.md` | 本轮局部检索结果 | 回看“链式校验”“RAG”等关键术语在专利中的原文落点 | 中 | 当前只做了本地关键词检索 |

## 关键证据摘录

| 证据 ID | 来源路径 | 摘录 | 支撑内容 |
|---|---|---|---|
| E01 | `source_texts/patent_docx.txt` | “构建跨模态视听-文字协同响应图…通过时序滑动窗口与加权融合机制解决声画异步问题” | 视听-文字协同响应图与声画异步处理 |
| E02 | `source_texts/patent_docx.txt` | “基于响应密度自适应锚定关键视觉区域…构建包含全局上下文与局部精细视角的双流视觉表征” | 响应密度、自适应锚定、全局/局部双流 |
| E03 | `source_texts/patent_docx.txt` | “提取用户问题及视频内容的关键词…利用RAG技术在知识库中匹配最相关的营销理论条目” | 广告知识检索 |
| E04 | `source_texts/patent_docx.txt` | “观察—分析—推理—答案”的结构化生成协议 | 结构化语义约束与链式推理 |
| E05 | `source_texts/patent_docx.txt` | “基于关键词的敏感触发检测…回溯视频与音频证据…确认令牌/修正令牌” | 链式校验与触发式核查 |
| E06 | `source_texts/patent_office_action_pdf_extract.txt` | 审查员将方案拆为“通用视频问答 + 过采样 + 全局/局部 + RAG + CoT + 自我验证 + 热力图 + 广告场景” | 当前最大创造性风险是“模块拼接” |
| E07 | `code_refactor/rag/retriever.py` | `supporting_evidence_ids`、`evidence_score` | 代码中已出现“证据约束检索”的实现基础 |
| E08 | `code_refactor/reflection/claim_checker.py` | `ocr_or_logo_claim` / `asr_claim` / `marketing_claim` 路由 | 代码中已有声明级证据回溯的雏形 |

## 缺失材料

| 材料 | 为什么需要 | 如何获取 |
|---|---|---|
| 对比文件 1-5 的完整机器可读文本 | 当前矩阵更多依赖审查意见中的摘述，缺少逐段核对 | 等待 `deep-research` 或单独提取本地 PDF/专利全文 |
| 当前权利要求全文的分项版 | 便于把每个 feature 与 claim clause 对齐 | 从专利正文再单独抽取或人工整理 |
| 当前答复后的最新替换页版本 | 便于核查是否已有实质限缩 | 从 `专利相关/` 进一步抽取文本 |

## 外部检索建议

| Query | 用途 | 预期证据类型 | 是否已执行 |
|---|---|---|---|
| `广告视频问答 视听 协同 响应图 OCR 语音` | 查中文近似公开方案 | 中文专利/论文 | 已交给 deep-research |
| `multimodal video question answering audio visual alignment OCR logo local evidence retrieval verification` | 查英文相近路线 | 英文论文/专利 | 已交给 deep-research |
| `claim-level evidence verification multimodal QA` | 查“声明级证据回溯”是否已有强公开 | 英文论文/系统方案 | 已交给 deep-research |