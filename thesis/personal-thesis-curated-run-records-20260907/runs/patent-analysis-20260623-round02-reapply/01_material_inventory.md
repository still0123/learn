# P1 材料清单

## 本地材料

| ID | 路径 | 类型 | 用途 | 可靠性 | 备注 |
|---|---|---|---|---|---|
| N01 | `source_texts/patent_docx.txt` | 旧申请专利正文 | 提取“不能再用”的旧创新点边界 | 高 | 用于排除旧主线 |
| N02 | `source_texts/patent_office_action_pdf_extract.txt` | 第二次审查意见 | 提炼审查员已经攻击过的组合模式 | 高 | 用于反向定义新申请避坑区 |
| N03 | `source_texts/patent_opinion_statement.txt` | 旧意见陈述 | 看旧答复已经主张过什么 | 高 | 避免重复包装 |
| N04 | `code_refactor/evidence/evidence_package.py` | 代码 | 识别 evidence package、source_type、traceable_to_raw 等新机制 | 高 | 新申请候选的重要来源 |
| N05 | `code_refactor/rag/marketing_kb.py` | 代码 | 识别 source_seed_id、potential_leakage、risk_notes 等知识风险控制机制 | 高 | 很像新的专利切入点 |
| N06 | `code_refactor/rag/retriever.py` | 代码 | 识别 supporting_evidence_ids、evidence_score 等证据约束检索能力 | 高 | 与 provenance 主线耦合 |
| N07 | `code_refactor/rag/embedding_retriever.py` | 代码 | 识别 embedding / hybrid retrieval orchestration 能力 | 高 | 说明系统已从单一路径升级 |
| N08 | `code_refactor/reasoning/prompt_builder.py` | 代码 | 识别 prompt 中 evidence_id + knowledge_id 绑定方式 | 高 | 可支撑跨阶段 provenance 传递 |
| N09 | `code_refactor/reflection/claim_checker.py` | 代码 | 识别 claim_type 路由与 required_evidence 机制 | 高 | 新申请中最有希望的“声明路由校验”来源 |
| N10 | `code_refactor/scripts/run_rag_qwen3_inference.py` | 代码 | 识别 raw frame traceability、retriever mode、evidence package 贯通能力 | 高 | 工程整合层支撑很强 |
| N11 | `code_refactor/tests/test_embedding_rag.py` | 测试 | 证明 embedding / hybrid 路径不是纸上设计 | 高 | 可作实施例支撑 |
| N12 | `code_refactor/tests/test_lightweight_pipeline.py` | 测试 | 证明 evidence package、retrieval、prompt、claim plan 已串通 | 高 | 可作实施例支撑 |
| N13 | `code_refactor/sample_outputs/sample0_pipeline.json` | 样例输出 | 证明 supporting_evidence_ids、potential_leakage、claim_type 已进入中间产物 | 高 | 非常适合作为说明书实施例 |
| N14 | `docs/RAG升级_Embedding与Hybrid检索说明.md` | 文档 | 提炼新能力的工程说明 | 中高 | 有助于整理新申请主线 |
| N15 | `docs/RAG接入推理脚本说明与测试报告.md` | 文档 | 整理 pipeline 与 dry-run/正式推理链路 | 中高 | 对新申请系统流程有帮助 |
| N16 | `docs/主线重构与创新点改写稿.md` | 文档 | 判断旧主线与新主线的切割方式 | 中 | 主要作为辅助分析 |

## 关键证据摘录

| 证据 ID | 来源路径 | 摘录 | 支撑内容 |
|---|---|---|---|
| NE01 | `code_refactor/rag/marketing_kb.py` | `source_seed_id`, `potential_leakage`, `risk_notes` | 知识条目具备来源污染/泄漏风险标注机制 |
| NE02 | `code_refactor/rag/retriever.py` | `supporting_evidence_ids`, `evidence_score` | 检索结果显式带出支撑证据 ID |
| NE03 | `code_refactor/rag/embedding_retriever.py` | `embedding_retrieve`, `hybrid_retrieve` | 系统具备 lexical / embedding / hybrid 多检索路径 |
| NE04 | `code_refactor/reflection/claim_checker.py` | `ocr_or_logo_claim`, `asr_claim`, `marketing_claim`, `visual_claim` | 声明类型化与 required evidence 路由机制 |
| NE05 | `code_refactor/scripts/run_rag_qwen3_inference.py` | `traceable_to_raw`, `frame_paths`, `retriever` | evidence package 与 raw asset / retriever mode 在统一 pipeline 中贯通 |
| NE06 | `code_refactor/sample_outputs/sample0_pipeline.json` | `supporting_evidence_ids`, `potential_leakage`, `claim_type` 出现在同一 JSON | provenance、knowledge-risk、claim-routing 已进入实际输出 |

## 缺失材料

| 材料 | 为什么需要 | 如何获取 |
|---|---|---|
| 新申请的明确标题和目标保护边界 | 便于独权聚焦 | 在本轮推荐中给出候选标题 |
| 更多外部公开对“knowledge leakage aware retrieval / claim-type routing” 的对比资料 | 便于提前判断新颖性 | 等 `deep-research` 继续返回或后续补检 |

## 结论

本轮新申请不应继续围绕旧案的“证据定位 / 双流视觉表征 / 链式校验”主战场，而应围绕**provenance、risk-aware retrieval、claim-type routing、traceability-aware control** 这类当前代码中已出现、但旧申请未充分覆盖的新机制重建主线。