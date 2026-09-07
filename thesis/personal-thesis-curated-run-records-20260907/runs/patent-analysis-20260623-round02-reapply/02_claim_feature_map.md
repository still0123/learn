# P2 新申请候选特征映射

> 本轮不是沿用旧案 claim，而是从当前代码与样例输出中提炼**新的可申请特征簇**。

## NF-01 知识条目污染/泄漏风险感知机制

- 候选特征：知识条目在进入推理前，显式携带 `source_seed_id`、`potential_leakage` 和 `risk_notes`，并把这些风险标记传入检索结果与推理上下文。
- 归一化技术含义：系统不仅检索知识，还判断该知识是否可能来源于训练/测试样本种子或存在污染风险，并据此控制后续使用方式。
- 代码支撑：`code_refactor/rag/marketing_kb.py:18-21,56-76`。
- 样例支撑：`code_refactor/sample_outputs/sample0_pipeline.json:103-116` 中 `potential_leakage=true` 和 `risk_notes` 已进入检索结果。
- 新申请价值：高。它明显不同于旧案“广告知识库 RAG”主线，更偏向**risk-aware retrieval governance**。

## NF-02 supporting_evidence_ids 驱动的证据约束检索结果结构

- 候选特征：每个检索到的知识条目都显式携带 `supporting_evidence_ids`，并把知识条目与 evidence package 绑定。
- 归一化技术含义：检索结果不是孤立文本，而是带有“由哪些证据支持被检索出来”的可追溯中间表示。
- 代码支撑：`code_refactor/rag/retriever.py:24-26,114-116`；`code_refactor/rag/embedding_retriever.py:193-205,231-241`。
- 样例支撑：`sample0_pipeline.json:103-117`。
- 新申请价值：高。与旧案“广告知识库”相比，这更像**检索结果 provenance 结构**。

## NF-03 多检索器编排（lexical / embedding / hybrid）

- 候选特征：系统支持 lexical、embedding、hybrid 三种检索器路径，并在统一 pipeline 下切换与组合。
- 归一化技术含义：不是单一 RAG，而是多检索器编排框架，可根据任务或风险状态选择更保守或更强表达能力的检索路线。
- 代码支撑：`code_refactor/rag/embedding_retriever.py:174-245`；`code_refactor/scripts/run_rag_qwen3_inference.py:119-129,173-177`。
- 文档支撑：`docs/RAG升级_Embedding与Hybrid检索说明.md:1-139`。
- 新申请价值：中高。单独主张“hybrid retrieval”不够新，但如果与 provenance / risk gating 结合，价值上升。

## NF-04 claim_type 路由与 required_evidence 绑定

- 候选特征：把答案/声明拆分为 `ocr_or_logo_claim`、`asr_claim`、`marketing_claim`、`visual_claim`，并为每类声明规定不同的 `required_evidence`。
- 归一化技术含义：不同声明类型进入不同证据验证路径，不再做统一的泛化反思。
- 代码支撑：`code_refactor/reflection/claim_checker.py:7-42`。
- 样例支撑：`sample0_pipeline.json` 中 `claim_type` 已落盘。
- 新申请价值：高。相比旧案“高风险触发 + 链式校验”，这个更具体、更像新的 verification routing 机制。

## NF-05 traceable_to_raw 与 raw frame path 贯通机制

- 候选特征：evidence package 中保留 `traceable_to_raw`、`frame_paths`、`global_view`、`local_high_resolution_evidence_view`，并在统一推理脚本中贯通。
- 归一化技术含义：系统在回答前、中、后都保留与原始视频帧或原始输入的可追溯关系，而不是只保留最终文本结论。
- 代码支撑：`code_refactor/evidence/evidence_package.py:18-38`；`code_refactor/scripts/run_rag_qwen3_inference.py:55-81,143-157`。
- 新申请价值：中高。若和 provenance gating 结合，可以形成新的系统主线。

## NF-06 风险感知的结构化回答上下文

- 候选特征：Prompt 中同时显式写入 evidence package、knowledge id、supporting_evidence_ids、risk_notes，并要求模型只使用 evidence-permitted knowledge。
- 归一化技术含义：系统在生成时不仅传内容，还传“可用范围与风险边界”。
- 代码支撑：`code_refactor/reasoning/prompt_builder.py:9-47`。
- 样例支撑：`sample0_pipeline.json` 中完整 prompt 已包含这些元素。
- 新申请价值：中。单独主张“prompt 里写规则”偏弱，但若和 provenance / leakage control 结合可增强。

## NF-07 测试可验证的新 disclosure

- 候选特征：embedding/hybrid retrieval、lightweight pipeline、统一输出 JSON 已有测试与样例，说明这不是概念草图。
- 归一化技术含义：当前系统具备可复跑和可核验的工程 disclosure，可支撑一件新的系统/方法申请。
- 代码支撑：
  - `code_refactor/tests/test_embedding_rag.py`
  - `code_refactor/tests/test_lightweight_pipeline.py`
- 新申请价值：辅助高。更适合作为新申请实施例/可实施性支撑，而不是独权核心。