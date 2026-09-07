# Round Report: round04-image-vqa-patent-research

---

## File: 00_plan.md

# P0 本轮计划

## 本轮目标

- 不再局限广告视频，面向图像 VQA / 多模态问答构思新专利方向。
- 基于 2023-2026 近年论文热点，筛选一个不容易被说成“RAG + CoT + self-check + 规则路由”组合的单一技术机制。
- 初始主线设为“声明级证据许可状态机”：答案声明 -> 证据需求 -> 证据匹配 -> 支持/冲突/不足许可状态 -> 生成/降级/拒答。
- 选择能快速跑实验的图像任务数据集，为下一轮代码 MVP 和实验结果准备。

## 本轮材料范围

- 原案驳回和前轮结论：`source_texts/patent_office_action_pdf_extract.txt`、`runs/patent-analysis-20260624-round03-reapply-design/`
- 现有代码基础：`code_refactor/evidence/evidence_package.py`、`code_refactor/reflection/claim_checker.py`、`code_refactor/reasoning/prompt_builder.py`
- 近年热点方向：VLM hallucination、grounded visual reasoning、Visual RAG、claim-level diagnosis、uncertainty calibration、selective answering
- 候选数据集：VLR-Bench、MagiC、PhD、TextVQA、DocVQA、ChartQA、ScienceQA、AI2D、VizWiz、VQAv2

## 计划输出

- 01_material_inventory.md
- 02_claim_feature_map.md
- 03_office_action_issue_map.md
- 04_prior_art_comparison_matrix.md
- 05_code_implementation_map.md
- 06_innovation_candidates.md
- 07_examiner_critic_review.md
- 08_revision_strategy.md
- 09_search_materials_report.md
- 10_final_recommendation.md
- gates.md

## 本轮注意事项

- 不编造数据
- 所有结论必须给出本地来源路径
- gate 未通过时只能输出候选/修订建议
- 不把“多模块拼接”包装为创新；必须收敛到一个可定义状态、输入输出、状态转移规则的核心机制。
- 优先选择图像数据集，原因是实验快、样例可视化清楚、实施例更容易写。
- 外部论文仅作为趋势和风险参考，正式提交前仍需代理人做专利检索。

---

## File: 01_material_inventory.md

# P1 材料清单

## 本地材料

| ID | 路径 | 类型 | 用途 | 可靠性 | 备注 |
|---|---|---|---|---|---|
| M1 | `source_texts/patent_office_action_pdf_extract.txt` | 驳回决定/审查意见 | 识别原案被拆解为功能组合的风险 | 高 | 本轮需避免重复“广告场景 + RAG + CoT + 自验证” |
| M2 | `runs/patent-analysis-20260624-round03-reapply-design/10_final_recommendation.md` | 前轮总报告 | 作为证据图谱方向的基础和风险输入 | 高 | round03 推荐证据图谱，但本轮进一步压缩为状态机 |
| M3 | `runs/patent-analysis-20260624-round03-reapply-design/07_examiner_critic_review.md` | 前轮审查员批判 | 识别图谱、路由、仲裁被打成常规组合的风险 | 高 | 本轮需避免四模块并列堆叠 |
| M4 | `code_refactor/reflection/claim_checker.py` | 代码实现 | 声明类型到证据需求的已有雏形 | 高 | 可演化为声明级证据许可状态机 |
| M5 | `code_refactor/evidence/evidence_package.py` | 代码实现 | 证据包字段基础 | 高 | 可作为 EvidenceUnit / PermissionRecord 的数据来源 |
| M6 | `code_refactor/reasoning/prompt_builder.py` | 代码实现 | 证据约束生成 prompt 基础 | 中高 | 可改为只允许许可声明输出 |
| E1 | Web: PhD visual hallucination benchmark | 外部论文趋势 | 视觉幻觉来源拆分：视觉模糊、输入冲突、反常识冲突 | 中 | 作为热点参考，不直接作为本地事实 |
| E2 | Web: PREHAL/evidential conflict | 外部论文趋势 | 用证据冲突检测视觉幻觉 | 中 | 与“冲突状态”相关 |
| E3 | Web: MagiC grounded visual reasoning | 外部论文趋势 | 评估推理步骤与视觉 grounding 的一致性 | 中 | 适合做图像实验 |
| E4 | Web: VLR-Bench / MRAG-Suite | 外部论文趋势 | Visual RAG 证据利用、干扰项、声明级诊断 | 中 | 适合快速实验 |
| E5 | Web: calibration / conformal prediction for VLM | 外部论文趋势 | 不确定性、选择性回答、拒答 | 中 | 与“证据不足状态”相关 |

## 本轮材料判断

- 原案和 round03 的“证据图谱”方向有价值，但如果同时写路由、图谱、仲裁、可信包，仍有被认定为功能组合的风险。
- 更适合新案的压缩表达是“声明级证据许可状态机”，把路由、冲突、降级都收敛为同一个状态转移机制。
- 图像任务数据集优先，因为可以快速构造证据许可记录和可视化实施例。

---

## File: 02_claim_feature_map.md

# P2 权利要求-技术特征映射

---

## File: 03_office_action_issue_map.md

# P3 审查意见问题图谱

---

## File: 04_prior_art_comparison_matrix.md

# P4 对比文件矩阵

---

## File: 05_code_implementation_map.md

# P8 代码实现难度评审

## 数据集与实验可行性结论

本轮建议把快速实验聚焦在“声明级证据许可状态机”，而不是泛化的 VQA 准确率提升。最合适的实验数据应满足至少一个条件：有可定位证据、有外部 passage 或干扰 passage、有 answerability/拒答标签、有 OCR/布局/图表结构，或天然包含幻觉诱导样本。

推荐组合：

1. **VLR-Bench / VLR-IF 作为主实验集**：它直接提供有效 passage、无效 passage 和“检索结果不足则不能推断”的样本形态，最贴合 `SUPPORTED / CONFLICTED / INSUFFICIENT / REFUSE` 的许可状态机。
2. **TextVQA 作为 OCR 证据集**：自带 OCR token 和 OCR bbox，适合验证“答案声明必须绑定图像中文字证据”的许可规则。
3. **VizWiz-VQA-Grounding 作为拒答与证据定位集**：原始 VizWiz 有 answerable 标签，Grounding 子集有答案区域 mask/边界点，适合验证“证据不足时降级或拒答”。
4. **MagiC 作为 grounded reasoning 诊断集**：有人类精标样本含 answer、rationale、bbox grounding，可作为小规模高质量 sanity check。
5. **ChartQA 或 AI2D 作为结构化视觉备选**：ChartQA 更适合数值声明许可，AI2D 更适合图示区域证据许可；二选一即可，不建议首周同时做。

不建议把 VQAv2 作为主实验集。VQAv2 规模大且成熟，但缺少显式 evidence、bbox/OCR/passage/uncertainty 标注，最多作为语言先验对照，不能很好支撑“证据许可状态机”的专利差异。

## 数据集对比

| 数据集 | 规模 | 证据字段 | 是否支持许可状态机 | 人力标注成本 | MVP 难度 | 建议用途 |
|---|---:|---|---|---|---|---|
| VLR-Bench | 300 benchmark samples；VLR-IF 32,000 instruction samples | image、question、answer、keywords、5 passages、gold passage；VLR-IF 含 valid/invalid passage 组合 | **高**。可把 gold passage 映射为支持证据，把 invalid passage 映射为冲突/无关证据，把 only-invalid 映射为不足/拒答 | 低。字段已经贴近状态机 | 低 | 主实验：passage 证据许可、冲突 passage 干扰、拒答 |
| MagiC | 约 5,500 弱监督 QA；约 900 human-curated examples | answer、rationale、bbox grounding、reasoning/grounding 评价 | **高**。适合验证 reasoning step 是否绑定 bbox 证据 | 中。若只用精标样本，需解析 bbox 与 rationale | 中 | 小规模诊断：声明与视觉区域证据的一致性 |
| PhD | 超 14k daily images、750 CCS images、102k VQA triplets | task/mode、正常问题、似是而非上下文、错误上下文、反常识图像 | **中高**。很适合构造 hallucination/conflict，但公开字段需进一步确认 | 中。需要把模式转成许可状态标签 | 中 | 幻觉压力测试：错误上下文诱导下是否拒绝无证据声明 |
| TextVQA | train 34,602 Q / 21,953 images；val 5,000 Q / 3,166 images；test 5,734 Q / 3,289 images | OCR tokens、OCR bbox、10 answers、OpenImages class | **高**。答案通常依赖图中文字，可做 OCR evidence gating | 低。OCR token/bbox 已有 | 低 | OCR 证据许可主验证集 |
| DocVQA | 50,000 questions、12,000+ document images | document image、QA、布局隐含；常需 OCR | **中**。有文档文本证据，但原始标准集细粒度 bbox 支撑弱 | 中。需要 OCR/布局解析或额外 bbox 数据 | 中 | 文档场景扩展，不放首周主线 |
| BBox-DocVQA | 3.6K documents、32K QA pairs | explicit bbox grounding，单/多区域，单/多页 | **高**。很贴合 evidence bbox，但 2025 新集需确认可得性 | 低到中 | 中 | 若可下载，优先替代原始 DocVQA |
| ChartQA | 9.6K human-written Q + 23.1K augmented Q；常用 eval split 2,500 samples | chart image、QA、部分设置有 gold table | **中高**。适合数值/比较声明许可；冲突样本需合成 | 低到中。gold table 可自动构造证据 | 低到中 | 数值声明许可备选 |
| ScienceQA | 21,208 MCQ；10,332 image context；10,220 text context；6,532 image+text；83.9% lecture、90.5% explanation | image/text context、choices、lecture、explanation | **中**。适合多模态+知识解释，但 evidence 不一定来自图像 | 低。解释可作为弱证据 | 低 | 知识型 VQA 对照，不作主证据定位集 |
| AI2D | 4,903 images、4,563 questions；每图 dense annotations | diagram object segmentation、diagram/text elements、QA | **中高**。适合图示元素证据许可，但样本较小 | 中。要把 dense annotation 转成 evidence unit | 中 | 图示 grounding 备选 |
| VizWiz-VQA | train 20,523；val 4,319；test 8,000；10 answers/问题；answerable 标签 | answerable、answer_type、answer confidence | **高**。天然有“不可回答”监督 | 低 | 低 | 拒答/不足证据验证 |
| VizWiz-VQA-Grounding | train 6,494；val 1,131；test 2,373 | answer grounding boundary points / binary masks | **高**。答案区域证据可直接用于许可判断 | 低到中 | 中 | 证据定位验证 |
| VQAv2 | 204,721 COCO images、1,105,904 questions、11,059,040 answers | image、question、10 answers、plausible answers；无显式证据 | **低**。缺 evidence/uncertainty/grounding | 高。需要额外标注或模型生成伪证据 | 低但价值低 | 只做传统 VQA 对照 |

## 最推荐的 1 周 MVP

### 实验目标

验证一个明确问题：把答案拆成声明后，若每个声明必须通过证据许可状态机，是否能减少无证据回答、错误 passage 诱导回答和 OCR 幻觉，同时保持可回答样本的准确率。

状态定义：

- `SUPPORTED`：声明可由至少一个图像/OCR/passage/bbox 证据直接支持。
- `CONFLICTED`：声明与图像/OCR/passage/bbox 中的候选证据冲突。
- `INSUFFICIENT`：有相关证据类型，但匹配分数或覆盖度不足。
- `REFUSE`：问题本身不可回答，或仅存在无效 passage/低可信 evidence。
- `UNVERIFIED_BACKGROUND`：只能由外部知识或模型先验支持，不能作为事实声明许可依据。

### 数据组合

首周只做三类数据，控制复杂度：

1. `VLR-IF` 采样 800-1,200 条：覆盖 `{V}`、`{I}`、`{V,I}`、`{V,I,I}` 四种 passage 情况。
2. `TextVQA val` 采样 500-1,000 条：保留 OCR token 和 bbox，优先选答案在 OCR token 中可匹配的样本。
3. `VizWiz-VQA val` 采样 500 条 + `VizWiz-VQA-Grounding val` 采样 200 条：分别验证拒答和 grounding。

可选第 4 个小集：`MagiC human-curated` 100-200 条，用来做人工可读案例分析，不纳入首周主要统计。

### 基线与消融

| 设置 | 输入 | 输出约束 | 目的 |
|---|---|---|---|
| Baseline VLM | image + question | 直接回答 | 传统 VQA 对照 |
| RAG Prompt | image + question + passages/OCR | 直接回答，可引用证据 | 排除“只是加 RAG”的解释 |
| Claim Check Prompt | baseline answer + evidence | 事后判断声明是否支持 | 排除“普通 self-check”解释 |
| Permission FSM | claims + evidence units + state transition | 只允许生成 supported claims；insufficient/refuse 降级 | 主方案 |
| Oracle Evidence | gold passage / OCR exact match / grounding mask | FSM 上界 | 测状态机是否真的利用证据 |

### 指标

- `Answer accuracy`：VLR-Bench/TextVQA/ChartQA 用标准 exact/relaxed/VQA accuracy；ScienceQA/AI2D 用 MCQ accuracy。
- `Unsupported claim rate`：最终答案中无法映射到证据的声明占比，主指标。
- `Conflict acceptance rate`：存在 invalid passage 或错误上下文时仍采纳冲突声明的比例，VLR-IF/PhD 主指标。
- `Refusal precision/recall`：VizWiz answerable=0 或 VLR-IF only-invalid 情况下是否拒答。
- `Evidence coverage`：每个最终声明绑定的 evidence unit 数量、bbox IoU 或 OCR token overlap。
- `Over-refusal rate`：gold evidence 存在但被拒答的比例，用来约束状态机不要过保守。

### 一周排期

| 天数 | 任务 | 产出 |
|---|---|---|
| Day 1 | 下载/抽样 VLR-IF、TextVQA、VizWiz；统一成 `sample_id, image, question, answer, evidence_units, gold_state` | 小型 JSONL 数据包 |
| Day 2 | 定义 evidence unit：passage、OCR token/bbox、answerable、grounding mask；实现 gold/weak gold 状态映射规则 | 状态标签生成脚本设计文档 |
| Day 3 | 跑 Baseline VLM 与 RAG Prompt，保存 answer、claim list、引用 evidence | baseline 输出 |
| Day 4 | 跑 Permission FSM：claim 分解、证据匹配、状态迁移、生成/降级/拒答 | 主方案输出 |
| Day 5 | 统计 accuracy、unsupported claim、conflict acceptance、refusal P/R、over-refusal | 实验表 |
| Day 6 | 抽 30-50 个失败样本做案例分析，区分 OCR 错误、检索干扰、视觉不可见、状态阈值过严 | error taxonomy |
| Day 7 | 写专利支撑结论：哪些状态迁移有效、哪些字段能支撑实施例、哪些数据不适合作为主证据 | round04 实验建议 |

## 对现有代码的映射

现有 `code_refactor` 可复用：

- `evidence/evidence_package.py`：把 passage、OCR token、bbox、answerability 封装成统一 evidence field。
- `rag/retriever.py` 与 `rag/embedding_retriever.py`：用于 VLR-IF passage 检索和 invalid passage 干扰实验。
- `reflection/claim_checker.py`：答案声明拆分和声明类型推断。
- `reasoning/prompt_builder.py`：扩展为带许可状态的 constrained prompt。

建议新增的最小接口，不在本 Agent 中写代码：

```text
EvidenceUnit:
  evidence_id
  modality: image_region | ocr | passage | answerability | chart_table | diagram_region
  text
  bbox_or_mask
  source_confidence
  gold_role: support | distractor | conflict | insufficient

ClaimPermissionState:
  claim_id
  required_modality
  matched_evidence_ids
  state: SUPPORTED | CONFLICTED | INSUFFICIENT | REFUSE | UNVERIFIED_BACKGROUND
  transition_reason
```

## 数据集取舍建议

主线优先级：

1. `VLR-IF + TextVQA + VizWiz`：最省人力、最贴合许可状态机、能覆盖 passage/OCR/refusal 三个关键证据形态。
2. `MagiC`：作为高质量视觉 grounding 诊断，样本少但说服力强。
3. `ChartQA`：如果想体现“数值声明不能无证据生成”，加入 300-500 条即可。

暂缓：

- `DocVQA`：普通版本没有足够细粒度 grounding，除非使用 BBox-DocVQA 或自行 OCR/布局解析。
- `ScienceQA`：解释和 lecture 很有价值，但容易被审查员看作 CoT/RAG 解释增强，不适合作为主创新支撑。
- `AI2D`：dense annotations 有潜力，但转换为 evidence unit 的工程成本高于 TextVQA/VizWiz。
- `VQAv2`：只适合展示传统准确率不下降，不适合证明本专利机制。

## 主要来源

- VLR-Bench project page: https://vlr-bench.github.io/
- MagiC arXiv page: https://arxiv.org/html/2507.07297v1
- PhD CVPR 2025 page: https://www.computer.org/csdl/proceedings-article/cvpr/2025/436400t857/299aHMugtPi
- TextVQA dataset page: https://textvqa.org/dataset/
- DocVQA paper mirror: https://www.arxiv-vanity.com/papers/2007.00398/
- BBox-DocVQA arXiv page: https://arxiv.org/html/2511.15090v1
- ChartQA summary: https://www.researchgate.net/publication/359390370_ChartQA_A_Benchmark_for_Question_Answering_about_Charts_with_Visual_and_Logical_Reasoning
- ScienceQA project page: https://scienceqa.github.io/
- AI2D project page: https://prior.allenai.org/projects/diagram-understanding
- VizWiz VQA page: https://vizwiz.org/tasks%20-%20and%20-%20datasets/vqa/
- VizWiz grounding page: https://vizwiz.org/tasks-and-datasets/answer-grounding-for-vqa/
- VQAv2 official page: https://visualqa.org/

---

## File: 06_innovation_candidates.md

# P6 创新点候选：图像 VQA 声明级证据许可状态机

## 执行判断

round04 不建议沿用 round03 的“多模态证据一致性图谱 + 冲突仲裁 + 可信证据包”宽链条作为独立权利要求核心。该链条虽然完整，但仍容易被审查员拆解为多模态 RAG、知识图谱、自检和规则路由的组合。

本轮建议收敛为一个更单一的核心发明点：

> 面向图像 VQA 的声明级证据许可状态机：将候选答案拆成声明单元，为每个声明生成证据需求，匹配图像区域、OCR、表格/图表元素、外部文本或知识项等证据后，为该声明赋予支持、冲突、不足、越权、可降级等许可状态，并根据状态控制答案生成、改写或拒答。

该机制的关键不是“又加一个校验模块”，而是把“每个答案声明能否被说出口”变成一个可计算的状态转移问题。生成器不再只接收证据上下文，而是接收声明级许可状态；未获许可的声明不能以确定语气输出。

本文件仅作为新申请/继续申请底稿，不构成授权结论。正式提交前仍需专利代理人做外部专利检索，尤其检索 evidence-aware VQA、multimodal fact verification、selective answering、visual grounding with uncertainty 等方向。

## I-01：声明级证据许可状态机

### 1. 技术机制

核心步骤：

1. 接收图像、用户问题和候选答案，或在生成前生成一组候选声明槽位。
2. 将候选答案拆分为声明单元，声明单元至少包括对象存在、属性、数量、文字读取、空间关系、图表数值、文档字段、解释性结论中的一种。
3. 对每个声明单元识别声明类型，生成证据需求集合，例如局部图像区域、OCR 文本、表格单元格、图表轴标、视觉标签、检索段落、模型不确定性分数。
4. 将证据需求与可用证据项匹配，得到声明-证据匹配结果，匹配结果包括证据项标识、来源模态、定位信息、支持分数、冲突分数、缺失项和置信度。
5. 基于匹配结果进入许可状态机，状态至少包括：
   - `UNVERIFIED`：声明尚未完成证据匹配；
   - `SUPPORTED`：必要证据满足，且冲突低于阈值；
   - `CONFLICTED`：存在足以反驳声明的视觉、OCR、图表或文本证据；
   - `INSUFFICIENT`：缺少声明类型要求的必要证据；
   - `OVERREACH`：声明超出图像或给定资料可支持范围，例如从单一画面推断意图、因果或人群；
   - `DOWNGRADED`：原确定性声明被改写为不确定或条件性表达；
   - `BLOCKED`：声明被禁止输出；
   - `PERMITTED`：声明允许进入最终答案。
6. 根据状态转移动作控制生成：`SUPPORTED -> PERMITTED`，`CONFLICTED -> BLOCKED 或 触发反证说明`，`INSUFFICIENT -> DOWNGRADED 或 拒答`，`OVERREACH -> DOWNGRADED`。
7. 输出最终答案及声明-证据-状态表，使每个事实性或解释性声明具有可追溯许可依据。

输入：图像、问题、候选答案或候选声明、证据项集合、声明类型到证据需求的映射规则、状态转移规则。

输出：最终答案、声明级许可状态表、被支持/被降级/被阻断声明列表、证据引用表。

与现有流程的连接点：位于 `claim_checker.py` 的声明拆分/证据需求之后，`prompt_builder.py` 的答案生成之前或之后；`EvidencePackage` 提供证据字段，状态机决定哪些证据和声明可进入生成。

### 2. 为什么不是模块拼接

- 它不是普通 RAG：RAG 解决“检索什么”，本机制解决“声明在什么证据状态下才允许输出”。
- 它不是普通 CoT：状态转移不依赖模型自由推理文本，而依赖声明类型、必要证据、支持/冲突分数和许可动作。
- 它不是普通 self-check：校验对象不是整段答案，而是每个声明；输出不是一句“是否可信”，而是可执行的生成许可、降级或阻断。
- 它不是普通置信度阈值：同一置信度在不同声明类型下具有不同后果，例如 OCR 文字声明缺 OCR 时阻断，解释性声明缺知识或视觉证据时降级。
- 关键耦合关系：声明类型决定证据需求，证据需求决定匹配项，匹配项决定许可状态，许可状态直接控制答案生成动作。

### 3. 本地支持

| 支持点 | 本地来源路径 | 摘录/章节 | 支撑强度 |
|---|---|---|---|
| round04 已确定不局限广告视频，主线为声明级证据许可状态机 | `runs/round04-image-vqa-patent-research/00_plan.md` | “答案声明 -> 证据需求 -> 证据匹配 -> 支持/冲突/不足许可状态 -> 生成/降级/拒答” | 强 |
| 现有声明拆分和声明类型识别 | `code_refactor/reflection/claim_checker.py` | `split_claims()`、`infer_claim_type()`、`ClaimCheckPlan.required_evidence` | 强 |
| 现有证据包结构 | `code_refactor/evidence/evidence_package.py` | `EvidencePackage` 包含 `global_view`、`local_high_resolution_evidence_view`、`asr`、`ocr_text`、`logo_text`、`visual_tags`、`scores` | 强 |
| round03 风险教训 | `runs/patent-analysis-20260624-round03-reapply-design/10_final_recommendation.md` | 普通 RAG、CoT、自我反思、知识库、双流视觉不宜作为核心 | 强 |
| 项目级约束 | `/Users/bytedance/.trae-cn/memory/projects/-Users-bytedance-vqa-thesis-continue/project_memory.md` | 新案必须突出非显而易见性，通过模态冲突或证据不确定性构建壁垒 | 强 |

### 4. 相对 round03 方案的差异

| round03 宽链条 | round04 收敛机制 | 差异价值 |
|---|---|---|
| 证据路由、图谱、仲裁、可信包、生成约束均作为链条 | 一个声明级许可状态机统摄证据需求、匹配、状态、动作 | 更像单一可定义机制，减少模块堆叠风险 |
| 场景限定为广告视频 | 泛化到图像 VQA、文档 VQA、图表 VQA、科学图像问答 | 数据集实验更快，保护范围更宽 |
| 图谱边和仲裁规则可能被打成知识图谱/数据融合 | 状态转移表直接控制声明是否允许输出 | 技术效果更集中：控制幻觉性声明 |
| 可信证据包偏上下文封装 | 许可状态偏生成控制接口 | 更容易写成方法步骤和系统模块 |

### 5. 技术效果

可合理主张的技术效果：

- 降低图像 VQA 中无证据事实声明、越权推断和跨模态冲突导致的确定性错误。
- 将答案级校验细化为声明级许可控制，提高输出答案的可追溯性和可审计性。
- 在 OCR、图表、文档、视觉对象等不同证据类型下采用不同许可动作，避免统一阈值造成的误放行或过度拒答。
- 为快速实验提供可度量指标：被阻断声明数、被降级声明数、许可状态准确率、最终答案幻觉率。

不能直接主张或需实验补充的效果：

- 不能声称一定提升所有 VQA 数据集准确率。
- 不能声称完全消除幻觉。
- 不能声称状态机优于所有 RAG 或所有 grounded VQA 方法，除非后续有实验对比。

### 6. 权利要求路径

适合写入独立权利要求：是，建议作为权利要求1的核心。

适合写入从属权利要求：是，状态类型、证据需求、状态转移表、降级模板、冲突分数均可拆为从属特征。

推荐限定语：

> 对候选答案进行声明级拆分；依据声明类型生成必要证据需求；将必要证据需求与图像及关联文本中的证据项进行匹配；基于证据匹配结果为每个声明分配许可状态；根据许可状态对该声明执行输出许可、确定性降级、反证说明或阻断处理。

新增内容风险：中。现有代码已有声明拆分、证据需求和证据包，但没有完整状态机；适合作为新申请，不宜主张原申请已完整公开。

### 7. 代码实现依据和难度

现有代码支撑：

- `code_refactor/reflection/claim_checker.py`：可扩展 `ClaimCheckPlan` 为 `ClaimPermissionPlan`。
- `code_refactor/evidence/evidence_package.py`：可扩展证据字段、证据标识和置信度。
- `code_refactor/reasoning/prompt_builder.py`：已有“只使用 evidence_id”的生成提示基础，可改为接收许可状态。

需要新增实现：

- `claim_permission_state.py`：定义状态枚举、状态转移规则和动作。
- `claim_evidence_matcher.py`：对声明需求和证据项做匹配，输出支持/冲突/缺失。
- `permission_prompt_builder.py`：只允许 `PERMITTED` 或 `DOWNGRADED` 声明进入最终答案。

难度：中。文本/OCR/图表类 MVP 可以较快实现；真实视觉 grounding、bbox、图表元素解析需要更多工程。

主要风险：如果只做关键词规则，会被认为是业务规则；需要在权利要求中强调“状态由必要证据覆盖、冲突强度、声明越权类型共同决定”，而不是人工列规则。

### 8. 模拟审查员攻击预测

可能攻击点：

- 声明拆分、证据检索和置信度判断属于大模型事实核查常规流程。
- 支持、冲突、不足只是人类审阅逻辑的自动化。
- 根据阈值拒答或降级是 selective answering 的常规手段。

反制要点：

- 本机制不是答案级置信度判断，而是“声明类型 -> 必要证据 -> 匹配结果 -> 许可状态 -> 生成动作”的闭环。
- 状态机的动作不是简单拒答；它区分反证阻断、证据不足降级、越权降级和可许可输出。
- 对 OCR、图表、文档、空间关系、解释性推断等声明使用不同必要证据配置，解决图像 VQA 中证据形态不一致的问题。

仍需补强：

- 外部检索 selective VQA、abstention、visual fact verification、grounded claim verification 的近年公开。
- 设计 10-20 个样例，展示同一答案中不同声明进入不同状态。

### 9. 建议

保留，作为 round04 首选主创新机制和权利要求1核心。

## I-02：证据需求矩阵与最低证据覆盖率

### 1. 技术机制

为不同声明类型配置最低证据需求矩阵。例如：

| 声明类型 | 必要证据 | 可选证据 | 许可条件 |
|---|---|---|---|
| 对象存在 | 图像区域或视觉标签 | 全局 caption | 至少一个定位证据支持 |
| 属性/颜色 | 局部图像区域 | 全局图像描述 | 局部证据优先 |
| 数量 | 目标实例或计数证据 | 全局描述 | 计数证据不足则降级 |
| OCR/文档文字 | OCR token、文本区域 | 图像 caption | 无 OCR 时阻断确定性文字声明 |
| 图表数值 | 图表元素、轴标、数据点 | OCR、表格结构 | 轴标和数据点均需覆盖 |
| 解释性结论 | 视觉证据 + 问题相关知识或上下文 | 模型常识 | 只有常识时标记越权 |

该矩阵不是独立发明主线，而是 I-01 状态机的“证据需求生成器”。

### 2. 差异和价值

- 与普通规则路由不同，它不只选择输入证据，还定义声明进入 `SUPPORTED` 所需的最低覆盖条件。
- 与普通置信度不同，它允许不同声明类型有不同必要证据项和不同降级动作。

### 3. 本地支持

| 支持点 | 本地来源路径 | 支撑强度 |
|---|---|---|
| `infer_claim_type()` 已将 OCR/logo、ASR、marketing、visual 声明映射到 `required_evidence` | `code_refactor/reflection/claim_checker.py` | 强 |
| `EvidencePackage` 已含局部视图、OCR、Logo、视觉标签、分数等字段 | `code_refactor/evidence/evidence_package.py` | 强 |

### 4. 权利要求用途

建议作为从属权利要求或实施例，不建议单独作为独立权利要求。它可以限定“必要证据需求集合根据声明类型从预设矩阵中选取，并以最低覆盖率参与许可状态转移”。

### 5. 风险

容易被认为是人工规则表。补强方式是把矩阵与状态机绑定，强调它输出的是状态转移条件，而非单纯检索路由。

## I-03：冲突优先的声明阻断状态

### 1. 技术机制

当同一声明同时存在支持证据和反证证据时，不简单做加权平均，而优先进入 `CONFLICTED`，再根据声明类型执行不同动作：

- OCR/数字/文档字段冲突：阻断确定性声明，输出“图中可见文字与候选说法不一致”。
- 视觉属性冲突：降级为“不确定”或要求局部证据复核。
- 图表数值冲突：阻断精确数值，允许输出区间或趋势。
- 解释性结论冲突：保留多种可能解释，禁止单一确定判断。

### 2. 差异和价值

普通方法常将证据分数加权后给出最高置信答案；本机制把反证作为状态转移触发器，使冲突证据具有阻断权。这对 VLM hallucination 和 Visual RAG 干扰项尤其关键。

### 3. 本地支持

| 支持点 | 本地来源路径 | 支撑强度 |
|---|---|---|
| round03 已识别“冲突仲裁”是新案创造性重点，但链条较宽 | `runs/patent-analysis-20260624-round03-reapply-design/10_final_recommendation.md` | 中 |
| `EvidenceField.confidence` 和 `EvidencePackage.scores` 可承载支持/冲突分数 | `code_refactor/evidence/evidence_package.py` | 中 |

### 4. 权利要求用途

建议作为从属权利要求：当声明存在反证证据且冲突分数超过阈值时，将声明状态从 `UNVERIFIED` 或 `SUPPORTED` 转移至 `CONFLICTED`，并执行阻断、反证说明或降级动作。

### 5. 风险

“冲突检测”本身公开很多。必须限定为声明许可状态转移条件，而不是泛泛的冲突检测模块。

## I-04：越权推断降级器

### 1. 技术机制

识别候选答案中超出图像可支持范围的声明，例如：

- 从静态图像直接推断人物动机、产品真实功效、因果关系；
- 从单个画面推断群体偏好或广告效果；
- 用常识或检索知识替代图中证据；
- 将图像中未出现的品牌、价格、数量写成确定事实。

状态机将这类声明标记为 `OVERREACH`，默认不能以确定语气输出，只能改写为“图像显示...，但不足以证明...”。

### 2. 差异和价值

该机制针对 VQA 中常见的“看图过度解释”问题，不要求外部大规模知识图谱，而是用声明类型和证据覆盖状态控制语言强度。

### 3. 本地支持

| 支持点 | 本地来源路径 | 支撑强度 |
|---|---|---|
| round04 计划明确关注 hallucination、uncertainty calibration、selective answering | `runs/round04-image-vqa-patent-research/00_plan.md` | 中 |
| `claim_checker.py` 已区分事实类和解释/marketing 类声明 | `code_refactor/reflection/claim_checker.py` | 中 |

### 4. 权利要求用途

建议作为从属权利要求或实施例。它增强 I-01 的专利故事：不是所有不足都拒答，越权推断可以转为低确定性表达。

### 5. 风险

容易被认为是提示词规范。需写成状态转移和输出动作，例如“将确定性谓词替换为不确定性谓词，并保留已许可的低层视觉声明”。

## 最终排序

| 排名 | 创新点 | 用途 | 推荐程度 |
|---|---|---|---|
| 1 | 声明级证据许可状态机 | 独立权利要求核心 | 高 |
| 2 | 证据需求矩阵与最低证据覆盖率 | 从属权利要求 | 高 |
| 3 | 冲突优先的声明阻断状态 | 从属权利要求/实施例 | 中高 |
| 4 | 越权推断降级器 | 从属权利要求/实施例 | 中 |

## 结论

round04 的最优策略是把“可信 VQA”收敛为一个声明级许可控制机制，而不是继续叠加路由、图谱、RAG、反思和仲裁。权利要求1应围绕状态机写，其他机制只作为状态转移条件或从属特征出现。

---

## File: 07_examiner_critic_review.md

# P5 模拟审查员批判报告

## 批判对象

- 本轮新方向：图像 VQA 场景下的“声明级证据许可状态机”。
- 核心候选机制：将模型答案拆解为原子声明；为每个声明生成证据需求；在图像区域、OCR 文本、检测结果、检索知识和历史上下文中执行证据匹配；为每个声明赋予 `SUPPORTED`、`CONFLICTED`、`INSUFFICIENT`、`UNSUPPORTED`、`PERMITTED`、`BLOCKED` 等许可状态；仅允许满足证据许可条件的声明进入最终答案，对冲突或证据不足声明执行补证、降级或拒答。
- 本报告使用材料：
  - `source_texts/patent_office_action_pdf_extract.txt`
  - `runs/patent-analysis-20260624-round03-reapply-design/07_examiner_critic_review.md`
  - `runs/patent-analysis-20260624-round03-reapply-design/10_final_recommendation.md`

## 总体敌对判断

从审查员视角看，本轮方向比 round03 的“多模态证据一致性图谱 + 证据包”更有收敛空间，因为它不再把多个大模块并列堆叠，而是试图把可信 VQA 表达为一个声明级状态转移流程。但是它仍然存在高创造性风险：如果权利要求只写“将答案拆成声明、检索证据、判断是否支持、低置信则拒答或修正”，很容易被认定为 RAG、CoT 自校验、事实核查、置信度阈值、规则路由和结构化提示词的常规组合。

第二次审查意见已经给出非常明确的攻击路径：D1 覆盖多模态问答主流程，D2 覆盖大模型自验证和答案修正，D3 覆盖外部知识检索增强，D4/D5 及公知常识可覆盖多模态对齐、OCR/ROI/热力图和约束解码。新案要想提高存活率，不能只强调“可信”“证据许可”“状态机”这些结果性概念，必须把状态机限定为图像 VQA 中可计算的中间控制结构：声明如何原子化、证据需求如何编码、证据状态如何从节点匹配结果转移、哪些状态会硬阻断输出、补证动作如何由状态而不是自然语言提示触发。

初步结论：该方向可以继续推进，但独立权利要求必须主打“声明级证据许可状态转移 + 输出门控”，避免写成泛化 RAG 或普通 verifier。当前状态下若直接申请，创造性风险为高；经强限定、补实验和补实施例后，可降至中高。

## C-01 状态机会被认为只是普通 self-check 或 CoT 验证流程

### 1. 攻击结论

- 风险等级：高。
- 可能结论：相对于 D2 的自验证、验证问题、证据链和答案修正显而易见。

### 2. 攻击理由

- 原案第二次审查意见已经明确认定：把初始问题和初始答案组成提示词，再生成验证问题、验证答案，并依据一致性修正初始答案，属于 D2 已公开或容易想到的幻觉抑制手段。
- 若新案的“声明级状态机”只是先生成答案，再让模型判断每个声明是否有证据，最后删除或改写无证据内容，审查员可直接等同为“更细粒度的自验证”。
- 如果状态转移由 LLM 自己输出，例如让模型标注 `supported/conflicted/insufficient`，审查员会认为这只是结构化反馈令牌，比原案的“确认令牌/修正令牌”没有实质差异。

### 3. 当前证据弱点

- “声明级”本身只是处理粒度变化，不必然产生新的技术效果。
- “许可状态”如果没有外部可计算依据，容易被认为是提示词输出格式。
- 原案已被攻击为链式校验显而易见，新案必须避免再次落入“二次核查 + 修正”的框架。

### 4. 如何补强

- 权利要求：限定状态转移不由 LLM 主观判断，而由声明-证据匹配矩阵、证据类型满足度、冲突标签和证据覆盖率共同计算。
- 说明书：给出状态转移表，例如 `CLAIMED -> NEEDS_EVIDENCE -> MATCHED / CONTRADICTED / MISSING -> PERMITTED / BLOCKED / DEGRADED`，并说明每条转移的输入字段和阈值。
- 实验：对比“LLM 自校验”和“程序化状态机门控”，指标包括无证据声明输出率、冲突声明漏放率、拒答正确率。

### 5. 是否幸存

- 结论：修改后可能通过。
- 理由：只有当“许可状态”是程序化控制信号，而不是 LLM 反馈文本时，才可能与 D2 的自验证拉开距离。

## C-02 会被打成 RAG 的来源引用和证据过滤

### 1. 攻击结论

- 风险等级：高。
- 可能结论：相对于 D3 的多模态检索增强生成、外部知识召回和上下文拼接显而易见。

### 2. 攻击理由

- RAG 的常规流程已经包括查询解析、检索证据、将证据放入上下文、要求答案引用来源。
- 如果本方案只是把图像 OCR、区域描述、检测标签、外部知识检索结果组织成证据，再让模型基于证据回答，会被视为多模态 RAG 的普通变体。
- “证据不足则拒答”在检索增强问答中也常见，可能被认为是基于相似度或置信度阈值的常规输出策略。

### 3. 当前证据弱点

- 证据包、证据 ID、来源引用本身难以抗住 RAG 现有技术。
- 图像 VQA 数据源如 OCR、bbox、caption、object tags 都是常见证据形式。
- 若只写“检索到支持证据后生成答案”，技术效果仍是可预期的准确率提升。

### 4. 如何补强

- 权利要求：不要把核心写成检索增强，而要写成“每个答案声明必须通过证据需求许可检查后才可进入解码候选集”。强调输出门控发生在声明级，而非仅把证据作为 prompt 上下文。
- 说明书：定义证据需求向量，例如 `required_modality`、`required_region_type`、`required_text_span`、`required_relation`、`minimum_support_count`、`forbidden_conflict_type`。
- 实验：设置三组对照：普通 RAG、RAG + 来源引用、声明级许可状态机。重点展示普通 RAG 仍会输出未被证据覆盖的细节，而状态机能阻断该类声明。

### 5. 是否幸存

- 结论：需强限定。
- 理由：RAG 风险是本方向最大外部现有技术风险之一，必须把区别放在“声明输出许可控制”而不是“证据检索”。

## C-03 会被认为是 confidence threshold 或不确定性校准的常规应用

### 1. 攻击结论

- 风险等级：中高。
- 可能结论：把支持分数、相似度、置信度低于阈值的声明拒答或降级，是本领域常规技术手段。

### 2. 攻击理由

- 多模态问答、分类和检索系统中，基于置信度阈值决定输出、拒答或二次检索非常常见。
- 原审查意见已经把“基于触发条件节省算力、低置信度迭代”归入容易想到的设计。
- 如果状态转移条件只是 `score >= threshold`，审查员会认为状态机只是阈值判断的包装。

### 3. 当前证据弱点

- `SUPPORTED`、`INSUFFICIENT`、`BLOCKED` 等状态如果只由单一分数决定，没有复杂技术结构。
- “高风险问题触发核查”已经在原案中被打掉，不能改名为“许可阈值”后继续使用。

### 4. 如何补强

- 权利要求：状态转移不应只依赖单一置信度，至少限定三类条件共同决定：证据类型满足条件、证据覆盖条件、冲突排除条件。
- 说明书：将 `INSUFFICIENT` 与 `CONFLICTED` 分离。前者表示证据缺失，后者表示存在反证；二者触发不同动作：补采/检索、声明降级、禁止输出或要求用户补充问题。
- 实验：证明单阈值策略会错误放行“高相似但证据类型不满足”的声明，而多条件状态机能拦截。

### 5. 是否幸存

- 结论：修改后可能通过。
- 理由：必须把状态机做成多条件门控，而不是置信度阈值外壳。

## C-04 声明拆解会被认为是普通 CoT、fact verification 或信息抽取

### 1. 攻击结论

- 风险等级：中高。
- 可能结论：答案拆分为原子事实、逐项核验，是事实核查和链式推理中的常见步骤。

### 2. 攻击理由

- 大模型事实核查中常见“claim extraction -> evidence retrieval -> verification”的流程。
- 若声明拆解只是自然语言处理层面的主谓宾抽取，审查员会认为它不是图像 VQA 的特定技术手段。
- CoT 和 self-consistency 也会生成中间步骤，再逐步验证，容易与“声明级”流程发生重叠。

### 3. 当前证据弱点

- “原子声明”需要清楚界定，否则权利要求不清楚。
- 不同声明类型如何对应图像证据类型尚未写清，例如颜色、数量、位置、文字、关系、常识推断应有不同证据最低要求。

### 4. 如何补强

- 权利要求：把声明类型限定为图像 VQA 可验证类型，例如对象存在、属性、数量、空间关系、OCR 文本、图表数值、跨区域关系、外部知识依赖关系。
- 说明书：给出声明类型到最低证据配置的映射表。例如数量声明至少需要检测计数证据或区域集合；OCR 声明必须绑定文本框和字符 span；空间关系声明必须绑定两个区域框及相对位置。
- 实验：不要只做自然语言 claim checking；选 TextVQA、ChartQA、AI2D/ScienceQA 子集展示不同声明类型的证据需求差异。

### 5. 是否幸存

- 结论：需收窄后通过概率更高。
- 理由：声明拆解本身不强，强点在“声明类型驱动的视觉证据最低配置”。

## C-05 证据需求路由会被认为是规则路由或知识图谱匹配

### 1. 攻击结论

- 风险等级：高。
- 可能结论：问题类型到 OCR、检测、caption、知识库的路由属于常规工程规则。

### 2. 攻击理由

- round03 已明确：若路由只是“价格看 OCR、品牌看 logo、旁白看 ASR、常识看知识库”，审查员会认为是基于问题类型选择数据源的常规设计。
- 图像 VQA 中，OCR 问题走 OCR、图表问题走图表解析、知识型问题走检索，是数据集和系统设计中的常见路线。
- 若使用知识图谱表达问题-证据关系，也可能被认为是普通知识图谱查询或规则引擎。

### 3. 当前证据弱点

- 本轮从广告视频转向图像 VQA 后，场景限定更宽，现有技术更多。
- 简单规则路由无法形成强创造性。

### 4. 如何补强

- 权利要求：路由对象不是“问题”，而是“答案声明的证据需求”。同一个问题生成的不同声明可以路由到不同证据源，并分别进入许可状态。
- 说明书：限定动态补证：当某声明处于 `INSUFFICIENT` 且缺失证据类型为 OCR 时，才触发 OCR 区域重识别；当冲突类型为空间关系时，才触发区域关系重算。
- 实验：展示固定规则路由无法处理一个答案中混合出现的 OCR 声明、数量声明和常识声明，而声明级路由可以逐项许可。

### 5. 是否幸存

- 结论：修改后可能通过。
- 理由：把路由从“问题级选择模块”改成“声明级状态触发补证”，才有区别。

## C-06 冲突处理会被认为是投票、排序或常规 verifier

### 1. 攻击结论

- 风险等级：中高。
- 可能结论：支持证据和反证证据比较后决定保留、修正或拒答，是常规验证机制。

### 2. 攻击理由

- 多模型集成、事实核查、RAG reranking 都包含支持/反对证据的打分和排序。
- 若冲突处理只是选择置信度最高的证据，或让 LLM 判断哪条证据可信，则缺少新技术特征。
- 图像 VQA 中 OCR 与视觉描述冲突、检测标签与 caption 冲突并不罕见，简单优先级规则容易被认为显而易见。

### 3. 当前证据弱点

- 缺少明确的冲突类型和相应状态转移。
- “冲突则降级或拒答”属于合理但可预期的安全策略。

### 4. 如何补强

- 权利要求：限定冲突类型进入状态机，例如文本冲突、数值冲突、区域归属冲突、空间关系冲突、知识依赖冲突。不同冲突类型触发不同动作。
- 说明书：给出优先级规则但避免泛化排序。例如 OCR 文本声明必须以 OCR span 为主证，caption 只能作为辅助证；图表数值声明必须以图表解析单元为主证；外部知识不得覆盖图像内直接证据。
- 实验：构造冲突样例，统计冲突声明误放行率和错误证据覆盖率。

### 5. 是否幸存

- 结论：需补强。
- 理由：冲突处理必须成为状态转移的一部分，不能只是后处理排序。

## C-07 技术效果可能被认为是准确率提升的可预期结果

### 1. 攻击结论

- 风险等级：高。
- 可能结论：已知模块组合后减少幻觉、提升可追溯性、提高准确率，属于可预期技术效果。

### 2. 攻击理由

- 原审查意见已将多模态检索、外部知识、链式校验和约束生成组合后的准确性提升视为显而易见。
- “减少幻觉”“提升可信度”如果没有机制性指标，很容易被认为是目标而非技术效果。
- 状态机本质上会增加拒答和降级，可能提高保守性但未必提高答案质量，审查员可能质疑效果不充分。

### 3. 当前证据弱点

- 目前没有实验数据支持状态机优于 RAG 或 self-check。
- 若只使用准确率指标，可能无法体现状态机的真正效果。

### 4. 如何补强

- 权利要求：将技术效果内化为可检查流程约束，例如“无许可状态声明不进入最终答案”“冲突未消解声明不输出”“输出答案中的每个声明均具有证据绑定记录”。
- 说明书：主张更稳的效果：降低无证据声明输出率、降低冲突声明放行率、提高答案声明与图像证据的可追溯绑定率。
- 实验：至少包含四组消融：基础 VLM、普通 RAG、RAG + self-check、声明级许可状态机。指标包括无证据声明率、冲突漏检率、拒答精度、过度拒答率。

### 5. 是否幸存

- 结论：当前不充分，补实验后可改善。
- 理由：本方向的效果不应只讲准确率，而应围绕声明级证据控制。

## C-08 权利要求清楚性和支持性风险

### 1. 攻击结论

- 风险等级：中。
- 可能结论：如果状态名称、声明粒度、证据需求和许可条件没有定义，可能被质疑不清楚或公开不充分。

### 2. 攻击理由

- `SUPPORTED`、`CONFLICTED`、`PERMITTED` 等术语如果没有客观判断标准，属于功能性或结果性限定。
- “证据”范围过宽，可能包括图像区域、OCR、caption、知识库、模型注意力、人工标注等，边界不清。
- “许可”如果只是允许或禁止输出，可能被认为是抽象控制逻辑，没有足够技术细节。

### 3. 当前证据弱点

- 本轮目录中的候选文件仍是模板，尚未形成完整定义。
- 原案第二次审查意见还涉及修改超范围和说明书支持问题；新申请虽可新增内容，但必须一次性公开充分。

### 4. 如何补强

- 权利要求：减少开放词。建议限定状态集合、状态转移输入、状态转移动作和输出记录字段。
- 说明书：提供状态转移表、证据需求编码表、声明类型表、伪代码、输入输出 JSON 示例和 2-3 个图像 VQA 实施例。
- 实验：输出每个样例的声明列表、证据需求、匹配证据、状态转移日志和最终答案，作为实施例支撑。

### 5. 是否幸存

- 结论：需代理人复核。
- 理由：这是新申请可解决的问题，但需要在交底书阶段写细，不能留给答复阶段补。

## 审查员视角下的建议收窄主线

不建议把独立权利要求写成“图像 VQA + RAG + 证据验证 + 拒答”。更稳的写法是连续限定以下技术链条：

1. 对候选答案执行原子声明拆分，并将每个声明分类为对象存在、属性、数量、空间关系、OCR 文本、图表数值或外部知识依赖声明。
2. 根据声明类型生成证据需求向量，证据需求向量至少包括所需证据模态、证据位置约束、主证类型、辅助证类型、最小支持数量和禁止冲突类型。
3. 在图像区域、OCR 文本框、对象检测框、图表解析单元、图像描述和外部知识条目中执行声明-证据匹配，形成声明-证据匹配矩阵。
4. 根据匹配矩阵、证据类型满足度、证据覆盖率和冲突标签，将每个声明在许可状态机中转移到支持、冲突、证据不足或未支持状态。
5. 对处于证据不足状态的声明触发定向补证；对处于冲突状态的声明执行类型化仲裁；对仍未满足许可条件的声明执行删除、降级或拒答。
6. 仅将达到许可状态的声明写入最终答案，并输出声明到证据节点的绑定记录。

这条主线的可辩护点在于：它把可信 VQA 的控制对象从“整段答案”下沉到“原子声明”，并把证据验证从 LLM 自我判断改成可记录、可复核、可阻断输出的状态转移。它仍然不应被包装成通用“减少幻觉”的大而全方案，而应被写成图像 VQA 中声明级证据许可控制方法。

## 下一步补强清单

- 检索：重点查 `claim-level verification visual question answering`、`multimodal fact verification evidence retrieval`、`VQA abstention uncertainty calibration`、`grounded VQA hallucination`，确认是否已有高度相似的 claim-evidence-state 方案。
- 数据集：优先选 TextVQA、ChartQA、AI2D/ScienceQA、VLR-Bench 或 Visual SimpleQA 子集，因为它们更容易构造声明级证据需求和冲突/不足样例。
- 实验：不要先追求端到端大模型提升，先做状态机可视化日志和消融指标，证明它不是 prompt 约束。
- 交底书：必须补状态转移表、证据需求向量格式、声明类型映射表、冲突类型表、拒答/降级规则和完整实施例。

---

## File: 08_revision_strategy.md

# P7 新申请策略：图像 VQA 声明级证据许可状态机

## 1. 执行结论

本轮建议不再围绕原案“广告视频 + 双流视觉 + RAG + 链式校验”继续补强，也不建议照搬 round03 的“证据图谱 + 冲突仲裁 + 可信证据包”宽链条。新方向应收敛为：

> 一种面向图像视觉问答的声明级证据许可状态机方法及系统。

核心发明点是：在图像 VQA 答案生成前后，将候选答案拆分为声明单元；对每个声明单元生成必要证据需求；将证据需求与图像区域、OCR、图表元素、文档字段或检索文本等证据项匹配；根据匹配结果进入支持、冲突、不足、越权、降级、阻断、许可等状态；再由状态控制最终答案的确定输出、降级表达或拒答。

代理人加工时应避免把权利要求写成“图像识别模块、OCR 模块、检索模块、校验模块、生成模块”的并列堆叠。独立权利要求必须围绕“状态机”组织，使每个步骤服务于声明许可状态转移。

## 2. 建议新专利名称

首选名称：

**一种面向图像视觉问答的声明级证据许可状态机方法及系统**

备选名称：

1. 一种基于声明证据状态转移的图像问答可信生成方法及系统
2. 一种用于视觉问答的声明级证据许可、降级与阻断方法
3. 一种基于证据需求匹配和许可状态控制的多模态问答生成方法

首选名称更直接，能把审查焦点固定到“状态机”而不是泛化的可信问答或 RAG。

## 3. 技术问题表述

背景技术建议聚焦图像 VQA 的声明级幻觉，不再以广告视频声画异步作为主要矛盾。

建议技术问题：

> 现有图像视觉问答方法通常将图像、OCR 文本、检索文本或模型推理过程合并输入多模态大模型，由模型直接生成整段答案；当答案中同时包含对象、属性、数量、文字、空间关系和解释性推断时，系统缺少针对每个答案声明的必要证据覆盖判断和输出许可控制，导致无证据声明、与图像证据冲突的声明以及超出图像可支持范围的越权推断以确定语气输出。

本发明要解决的问题：

> 如何将图像 VQA 答案拆分为可验证声明，并基于声明类型、必要证据覆盖情况、反证冲突情况和越权推断情况，为每个声明确定许可状态，从而控制该声明是否可输出、是否需降级或是否应阻断。

## 4. 状态机定义

### 4.1 状态集合

建议在说明书中定义以下状态：

| 状态 | 含义 | 典型触发 |
|---|---|---|
| `UNVERIFIED` | 声明已抽取但尚未完成证据匹配 | 初始状态 |
| `SUPPORTED` | 声明类型要求的必要证据已满足，且无强反证 | OCR/局部视觉/图表元素等覆盖必要需求 |
| `CONFLICTED` | 存在与声明相反或不一致的证据 | 图中数字与候选答案数字不同 |
| `INSUFFICIENT` | 证据不足以支持确定性声明 | 缺少 OCR、bbox、图表轴标或必要上下文 |
| `OVERREACH` | 声明超出图像和给定资料可支持范围 | 从图像推断功效、意图、因果或人群 |
| `DOWNGRADED` | 声明被改写为不确定或条件性表达 | 证据不足但可保留低确定性描述 |
| `BLOCKED` | 声明禁止进入最终答案 | 强冲突或关键证据缺失 |
| `PERMITTED` | 声明允许以目标语气输出 | 支持状态通过输出许可规则 |

### 4.2 状态转移规则

建议写成可计算规则，而不是提示词：

1. `UNVERIFIED -> SUPPORTED`：必要证据需求的覆盖率达到阈值，支持分数高于阈值，冲突分数低于阈值。
2. `UNVERIFIED -> INSUFFICIENT`：至少一个必要证据类型缺失，或证据定位信息无法映射到图像区域、OCR token、图表元素或文档字段。
3. `UNVERIFIED/SUPPORTED -> CONFLICTED`：存在反证证据，且反证强度超过声明类型对应阈值。
4. `UNVERIFIED -> OVERREACH`：声明包含因果、意图、功效、受众、偏好等超出图像直接证据的谓词，且缺少相应上下文或知识证据。
5. `SUPPORTED -> PERMITTED`：声明满足输出语气对应的许可条件。
6. `INSUFFICIENT -> DOWNGRADED`：声明可被改写为低确定性表达且不引入新事实。
7. `INSUFFICIENT -> BLOCKED`：声明为数字、文字、文档字段等高精确事实且关键证据缺失。
8. `CONFLICTED -> BLOCKED`：反证强度高于阻断阈值。
9. `OVERREACH -> DOWNGRADED`：保留已支持的低层视觉事实，删除或弱化越权结论。

### 4.3 输出动作

| 许可状态 | 输出动作 |
|---|---|
| `PERMITTED` | 进入最终答案，并附证据标识 |
| `DOWNGRADED` | 改写为“图像显示...，但不足以确定...” |
| `BLOCKED` | 不输出该声明，或输出反证/证据不足说明 |
| `CONFLICTED` | 禁止确定性输出，优先说明冲突证据 |
| `INSUFFICIENT` | 根据声明类型降级或拒答 |
| `OVERREACH` | 删除因果/意图/功效等越权部分 |

## 5. 独立权利要求1草案

一种面向图像视觉问答的声明级证据许可状态机方法，其特征在于，包括：

S1、获取待问答图像、用户自然语言问题以及与所述待问答图像对应的候选答案，或获取由视觉问答模型针对所述用户自然语言问题生成的候选答案；

S2、对所述候选答案进行声明级拆分，得到至少一个答案声明，并确定每个答案声明的声明类型，所述声明类型包括对象存在声明、对象属性声明、数量声明、图像文字声明、空间关系声明、图表数值声明、文档字段声明和解释性推断声明中的至少一种；

S3、根据所述声明类型为每个答案声明生成必要证据需求，所述必要证据需求包括图像区域证据、局部视觉证据、OCR 文本证据、图表元素证据、文档结构证据、检索文本证据和视觉标签证据中的至少一种；

S4、从所述待问答图像及其关联证据中获取与所述必要证据需求对应的证据项，并将每个答案声明与所述证据项进行匹配，得到声明级证据匹配结果，所述声明级证据匹配结果包括证据项标识、证据来源类型、定位信息、支持分数、冲突分数、缺失证据类型和置信度中的至少一种；

S5、基于所述声明级证据匹配结果，将每个答案声明输入声明级证据许可状态机，确定所述答案声明的许可状态，所述许可状态包括支持状态、冲突状态、证据不足状态、越权状态、降级状态、阻断状态和许可输出状态中的至少一种；

S6、根据所述许可状态对每个答案声明执行对应的生成控制动作，其中，对处于许可输出状态的答案声明允许进入最终答案，对处于降级状态的答案声明改写为不确定或条件性表达，对处于冲突状态或阻断状态的答案声明禁止作为确定性结论输出；

S7、基于经所述生成控制动作处理后的答案声明生成图像视觉问答结果，并输出所述图像视觉问答结果对应的声明、证据项标识和许可状态之间的映射关系。

## 6. 权利要求1写法要点

- “状态机”必须出现在独立权利要求的核心步骤中，不能只在说明书或从属权利要求中出现。
- S3 到 S6 必须保持连续因果链：声明类型决定证据需求，证据需求决定匹配结果，匹配结果决定许可状态，许可状态决定输出动作。
- 不要把“检索增强生成”“思维链”“自我反思”“知识图谱”写成发明点；这些可以作为证据来源或候选答案生成方式出现在从属权利要求。
- “越权状态”和“降级状态”建议保留，这是区别于普通支持/不支持二分类校验的重要特征。
- 如果代理人担心“状态机”过窄，可在说明书中说明状态机可由规则表、有限状态自动机、决策树或可学习分类器实现，但权利要求仍围绕状态和转移动作。

## 7. 从属权利要求布局

### 权利要求2：声明类型识别

限定声明类型通过关键词、句法结构、视觉问答任务类型或分类模型确定；图像文字、数量、图表数值、文档字段等高精确事实声明与解释性推断声明采用不同证据需求。

### 权利要求3：必要证据需求矩阵

限定预设声明类型与必要证据需求的对应矩阵：

- 图像文字声明至少需要 OCR token 或文本区域证据；
- 数量声明至少需要目标实例、计数结果或局部图像区域证据；
- 图表数值声明至少需要图表轴标、图例或数据点证据；
- 文档字段声明至少需要字段名、字段值或版面区域证据；
- 解释性推断声明至少需要图像证据及问题相关上下文证据。

### 权利要求4：声明级证据匹配结果

限定匹配结果包括 evidence_id、source_type、region/bbox、token_span、table_cell、chart_element、support_score、conflict_score、coverage_score 和 missing_required_evidence。

### 权利要求5：支持状态转移

限定当必要证据覆盖率大于第一阈值、支持分数大于第二阈值且冲突分数小于第三阈值时，将声明状态转移为支持状态或许可输出状态。

### 权利要求6：冲突状态转移

限定当反证证据与答案声明在对象、属性、数值、文字、空间关系或图表趋势上不一致，且冲突分数大于冲突阈值时，将声明状态转移为冲突状态，并禁止该声明作为确定性结论输出。

### 权利要求7：证据不足状态转移

限定当至少一个必要证据类型缺失时，将声明状态转移为证据不足状态；对于文字、数量、图表数值或文档字段声明执行阻断，对于属性或解释性声明执行降级。

### 权利要求8：越权状态和降级动作

限定当答案声明包含因果、意图、功效、偏好、受众或未来结果等谓词且缺少图像或上下文证据支持时，将声明状态转移为越权状态，并将确定性表达改写为不确定性表达。

### 权利要求9：生成控制

限定多模态模型仅基于处于许可输出状态或降级状态的声明生成最终答案；处于阻断状态的声明不得进入最终答案，或仅以证据不足说明形式输出。

### 权利要求10：系统、设备和介质

系统模块建议包括：

- 声明拆分模块；
- 声明类型识别模块；
- 证据需求生成模块；
- 证据匹配模块；
- 许可状态机模块；
- 生成控制模块；
- 声明-证据-状态映射输出模块。

同时保留电子设备和计算机可读存储介质权利要求。

## 8. 与原案和 round03 的区别

| 项目 | 原案 | round03 | round04 建议 |
|---|---|---|---|
| 场景 | 广告视频 | 广告视频可信生成 | 图像 VQA，可覆盖 OCR、图表、文档、自然图像 |
| 核心 | 视听协同、响应图、双流表征、链式校验 | 证据图谱、路由、冲突仲裁、可信证据包 | 声明级证据许可状态机 |
| 风险 | 容易被 D1-D5 组合覆盖 | 仍可能被拆成多个常规模块 | 状态转移和生成动作更集中 |
| 输出控制 | 生成后校验/修正 | 可信证据包约束生成 | 每个声明按许可状态输出、降级或阻断 |
| 实验可行性 | 依赖视频处理 | 视频和多模态证据链较重 | 图像数据集可快速验证 |

## 9. 说明书实施例建议

### 实施例一：自然图像对象和属性问答

问题：图中红色杯子旁边有什么？

候选答案包含两个声明：“图中有红色杯子”“杯子旁边有手机”。状态机分别要求局部视觉证据和空间关系证据。若局部区域支持杯子但不支持手机，第一声明进入 `PERMITTED`，第二声明进入 `INSUFFICIENT` 或 `BLOCKED`。

技术效果：避免整段答案因一个无证据空间关系声明而产生确定性幻觉。

### 实施例二：OCR/文档 VQA

问题：收据上的总金额是多少？

候选答案中的金额声明必须匹配 OCR token 和版面区域。若 OCR 结果显示“$18.90”，候选答案为“$19.80”，状态转移至 `CONFLICTED`，金额声明被阻断并输出反证说明。

技术效果：对高精确文字/数字声明使用冲突优先阻断，而不是由语言模型猜测。

### 实施例三：图表问答

问题：2022 年哪一类销量最高？

候选答案必须匹配图表轴标、图例和数据点。若只检索到图表标题但缺少数据点定位，状态为 `INSUFFICIENT`，输出“无法从当前证据确定最高类别”或降级为趋势描述。

技术效果：减少图表 VQA 中由标题或常识导致的数值幻觉。

### 实施例四：解释性问题的越权降级

问题：这张图片是否证明该产品一定有效？

候选答案若包含“该产品一定有效”，状态机识别为功效/因果越权声明；若图像只显示产品包装和使用场景，则该声明进入 `OVERREACH`，改写为“图像显示产品被展示，但不足以证明其实际效果”。

技术效果：将图像事实与无法从图像证明的结论区分开。

## 10. 代码落地建议

可基于现有代码做最小实现：

| 模块 | 现有基础 | 新增建议 |
|---|---|---|
| 声明拆分 | `code_refactor/reflection/claim_checker.py` 的 `split_claims()` | 扩展声明类型和声明 ID |
| 证据需求 | `ClaimCheckPlan.required_evidence` | 增加图像/OCR/图表/文档的需求矩阵 |
| 证据字段 | `code_refactor/evidence/evidence_package.py` | 增加 bbox、token_span、chart_element、support/conflict |
| 状态机 | 暂无 | 新增 `claim_permission_state.py` |
| 生成控制 | `code_refactor/reasoning/prompt_builder.py` | 只允许许可/降级声明进入 prompt |

一周 MVP 不需要完整视觉检测器，可先用 TextVQA、ChartQA 或人工样例构造 evidence item，验证状态转移和输出控制。

## 11. 风险和补强

主要风险：

- 审查员认为声明拆分和事实核查是常规大模型校验。
- 审查员认为状态只是业务规则或抽象逻辑。
- 近年 grounded VQA、visual fact verification、selective answering 论文可能已有相近机制。

补强方式：

- 权利要求中固定“声明类型、必要证据、匹配结果、许可状态、输出动作”的连续链条。
- 强调不同声明类型对应不同必要证据和不同状态转移动作。
- 准备实验日志，展示同一答案内多个声明被分别许可、降级、阻断。
- 在说明书中给出状态转移表、证据需求矩阵和声明-证据-状态输出表，避免抽象化。

## 12. 最终建议

权利要求1采用“声明级证据许可状态机”作为唯一主线；证据需求矩阵、冲突优先阻断、越权降级作为从属权利要求。不要在独立权利要求中同时展开图谱、RAG、CoT、自反思和知识库，否则会重新变成 round03 的多模块组合。

---

## File: 09_search_materials_report.md

# Round04 图像 VQA / VLM 幻觉 / Visual RAG 论文热点检索报告

生成日期：2026-06-24  
角色：round04 论文热点检索 Agent  
目标：从 2023-2026 图像 VQA、VLM hallucination、visual grounding、multimodal RAG、uncertainty calibration 的近期工作中，筛选可支撑“单一深机制”专利的新方向，尤其评估“声明级证据许可状态机”的可行性。

## 0. 执行结论

本轮检索结论很明确：近期热点不是“再接一个 RAG、CoT、知识图谱或自检模块”，而是围绕 **细粒度声明/证据对齐、证据冲突、不足证据拒答、视觉区域 grounding、过度自信校准** 展开。

最适合本项目的新专利主线是：

> **声明级证据许可状态机**：先把 VQA 答案拆成可验证声明，再为每个声明生成证据需求，匹配视觉区域、OCR、检索文本、知识证据，计算支持/冲突/不足状态，最后只允许“被许可”的声明进入答案；冲突或不足声明触发改写、降级、拒答或补证。

该机制能吸收近期研究趋势，但不直接落入“普通 RAG + 自检 + 置信度阈值”的组合陷阱。关键是权利要求中必须固定：声明粒度、证据需求类型、证据状态集合、状态转移条件、生成许可动作。

## 1. 热点方向总览

| 方向 | 代表来源 | 核心趋势 | 对本专利的价值 | 风险判断 |
|---|---|---|---|---|
| 细粒度幻觉定位 | ViCrit、PRE-HAL | 不只判答案对错，而是定位哪个对象/属性/关系/推理声明错 | 支撑“声明级”而非答案级校验 | 若只做检测，容易被已有幻觉检测覆盖 |
| 证据冲突与不确定性 | PRE-HAL、conformal prediction、calibration | 用冲突度、不确定性、预测集判断回答可靠性 | 支撑“支持/冲突/不足”状态量 | 单纯置信度阈值风险高 |
| Grounded visual reasoning | MagiC、Ground-R1、GroundSight | 评价/训练模型是否看对区域、理由是否对齐视觉证据 | 支撑证据许可前的视觉证据绑定 | 只写 bbox/region focus 属常规 grounding |
| Visual / Multimodal RAG | VLR-Bench、MRAG-Bench、MRAG-Suite、Double-Bench | 关注检索证据、干扰项、证据不足、过度自信 | 支撑证据候选与“无证据不得答” | RAG 框架本身高度拥挤 |
| Fact-seeking VQA | VisualSimpleQA、Video SimpleQA | 短答案、多跳事实、证据来源、过度自信 | 支撑声明拆解和事实粒度评估 | 直接做 benchmark 不构成方法创新 |
| 多学科/文档/图表 VQA | MMMU、ScienceQA、AI2D、ChartQA、TextVQA、DocVQA | 从自然图像扩展到图表、文档、OCR、科学图像 | 适合快速实验和从属实施例 | 数据集选择不是专利核心 |

## 2. 重点论文与数据集

### 2.1 ViCrit：可验证的视觉幻觉批判任务

来源：
- arXiv: https://arxiv.org/html/2506.10128v1
- 代码/数据：论文页面列出 ViCrit GitHub、ViCrit-Train、ViCrit-Bench。

核心方法：
- 在人写图像 caption 中注入一个细微视觉错误，如对象、属性、数量、空间关系错误。
- 要求模型根据图像定位被污染的文本 span。
- 训练目标是可验证的 exact-match reward，用于强化 VLM 的视觉感知能力。

可借鉴机制：
- “局部文本声明是否被图像支持”比“整个答案是否正确”更适合作为专利机制入口。
- 可以把答案声明切成 span/claim，再要求每个 claim 绑定证据区域或证据单元。

专利风险：
- 如果新案只写“检测答案中不符合图像的片段”，容易被 ViCrit 类工作覆盖。
- 需要把创新落到“检测结果如何控制生成许可状态”，而不是停留在 hallucination critic。

### 2.2 PRE-HAL / Evidential Conflict：基于证据冲突的视觉幻觉检测

来源：
- Visual hallucination detection in LVLMs via evidential conflict: https://arxiv.org/html/2506.19513v1/

核心方法：
- 提出 PRE-HAL 数据集，覆盖 perception 与 reasoning 两类幻觉，涉及实例、场景、关系等视觉语义。
- 使用 Dempster-Shafer Theory 的 mass function 融合高层特征，估计证据冲突程度。
- 目标是在推理阶段捕捉视觉输入与文本输出之间的高层冲突。

可借鉴机制：
- “证据冲突”是本轮最值得吸收的技术变量，可用于定义声明状态：SUPPORTED、CONFLICTED、INSUFFICIENT。
- 与普通 confidence 不同，冲突度可以由不同证据源之间的互斥质量、支持质量、未知质量组成。

专利风险：
- DST 和 evidential conflict 已是明确近似现有技术，不能把“用 Dempster-Shafer 检测幻觉”作为核心。
- 新案应限定为“冲突度参与声明许可状态转移”，而不是单纯输出幻觉分数。

### 2.3 MagiC：面向 grounded visual reasoning 的认知评测

来源：
- arXiv: https://arxiv.org/html/2507.07297v1
- OpenReview: https://openreview.net/forum?id=HuOYKg2FwU

核心方法：
- 数据包含约 5,500 个弱监督 QA 和约 900 个人工精标样本。
- 标注 final answer、rationale、bounding box grounding。
- 评价维度包括答案正确性、推理有效性、grounding fidelity、自我纠错能力。
- 引入 MagiScore、StepSense 等指标。

可借鉴机制：
- 支撑“答案不能只看最终正确，还要看中间推理步骤是否被视觉区域支撑”。
- 适合作为 MVP 实验数据源之一，验证状态机是否减少无证据声明。

专利风险：
- MagiC 本身已经覆盖 reasoning validity + grounding fidelity + self-correction。
- 新案不能泛泛写“根据 bbox 校验推理步骤”，要写成“声明状态决定生成动作”的机制。

### 2.4 VLR-Bench：视觉语言 RAG 中的 passage selection 与证据不足

来源：
- 项目页： https://vlr-bench.github.io/
- arXiv 链接见项目页： https://arxiv.org/abs/2412.10151

核心方法：
- 面向 Vision-Language RAG 的 VQA benchmark。
- 每个样本包含问题、答案、关键词、多个 passages，并标注 gold passage。
- VLR-Bench 约 300 样本，英文/中文/韩文平行；VLR-IF 约 32,000 指令样本。
- VLR-IF 包含有效 passage、无效 passage、有效+无效组合，并要求无足够检索结果时输出“无法推理”。

可借鉴机制：
- “证据不足时不得回答”正好支撑状态机中的 INSUFFICIENT -> ABSTAIN/ASK_MORE。
- 多 passage 干扰项可用于测试证据许可是否能抗干扰。

专利风险：
- VLR-Bench 已经把 passage selection、invalid passage、insufficient search results 做成数据机制。
- 新案不能只写“选最相关 passage 后回答”，必须把 passage 证据变成声明级许可条件。

### 2.5 MRAG-Bench / MRAG-Suite：视觉 RAG 诊断与 claim-level analysis

来源：
- MRAG-Bench: https://openreview.net/forum?id=Usklli4gMc&noteId=78RxjWt523
- MRAG-Suite: https://arxiv.org/html/2509.24253v1

核心方法：
- MRAG-Bench 关注“视觉增强知识什么时候比文本知识更有用”，包含 16,130 张图像和 1,353 个多选问题，覆盖 9 类场景。
- MRAG-Suite 是 Visual RAG 诊断平台，集成图表、plot、扫描文档、幻灯片、开放网页图像等 8 类异构数据。
- MRAG-Suite 引入 MM-RAGChecker，做 multimodal claim-level diagnosis，并分析 evidence utilization、cross-modality behavior、distractor impact、ambiguity。

可借鉴机制：
- “claim-level diagnosis”证明社区已经从答案级评估转向声明级评估。
- “distractor impact”和“evidence utilization”可作为本专利实验指标：状态机是否降低未被许可声明比例、冲突声明输出率。

专利风险：
- MRAG-Suite 已经显式出现 claim-level analysis，若权利要求只说“对声明进行证据诊断”，新颖性/创造性压力很大。
- 需要突出“诊断不是终点，而是进入生成许可状态机，控制每个声明的输出、改写、降级和拒答”。

### 2.6 GroundSight / Ground-R1：区域聚焦与 grounded answering

来源：
- GroundSight: https://arxiv.org/html/2509.25669v1
- Ground-R1: https://arxiv.org/html/2505.20272v1/

核心方法：
- GroundSight：先根据问题生成相关对象 bbox，裁剪目标区域再做图像检索/回答；还使用 question type 做 de-hallucination。
- Ground-R1：通过强化学习使模型生成 evidence region rollouts，再基于答案正确性和格式约束奖励回答，不依赖显式 bbox/rationale 标注。

可借鉴机制：
- 支撑“证据需求可以要求视觉区域证据”，尤其适合对象、属性、计数、空间关系类声明。
- 可作为从属实施例：当声明类型为视觉对象/属性/关系时，状态机要求至少一个区域证据达到 IoU/相关度条件。

专利风险：
- 视觉 grounding、区域裁剪、zoom-in、bbox rollouts 已高度拥挤。
- 本案不宜把“定位 ROI”作为核心，只把它作为状态机中的证据类型之一。

### 2.7 VisualSimpleQA / Video SimpleQA：事实寻求、证据来源与过度自信

来源：
- VisualSimpleQA: https://www.researchgate.net/publication/389713967_VisualSimpleQA_A_Benchmark_for_Decoupled_Evaluation_of_Large_Vision-Language_Models_in_Fact-Seeking_Question_Answering
- VisualSimpleQA 数据： https://huggingface.co/datasets/WYLing/VisualSimpleQA
- Video SimpleQA: https://videosimpleqa.github.io/
- Video SimpleQA arXiv: https://arxiv.org/html/2503.18923v2

核心方法：
- VisualSimpleQA 做图像事实问答，强调 visual 与 linguistic 模块的解耦评估，包含 ROI、难度标准和 evidence。
- Video SimpleQA 强调多跳事实、短格式确定答案、证据来源、时间 grounding，并发现 LVLM 普遍过度自信。

可借鉴机制：
- 支撑“短事实声明 + evidence source + ROI/grounding”的实验范式。
- 多跳事实可拆成多个子声明，每个子声明分别许可，最终答案只有在必要子声明均通过时输出。

专利风险：
- 数据集和评测方法本身不是可保护的系统机制。
- 不能把“多跳 fact-seeking QA”写成核心，需要绑定状态转移和许可动作。

### 2.8 MMMU / ScienceQA / AI2D / ChartQA / TextVQA / DocVQA：快速实验候选

来源：
- MMMU 项目页： https://mmmu-benchmark.github.io/
- VQA benchmark 综述页面： https://aiwiki.ai/wiki/visual_question_answering_models
- 视觉推理 benchmark 排行综述： https://awesomeagents.ai/leaderboards/vision-language-benchmarks-leaderboard/

核心方法/定位：
- MMMU：11.5K 大学级多学科题目，涵盖 30 个科目、183 个子领域、30 类图像格式，强调 perception + knowledge + reasoning。
- ScienceQA：科学图文问答，适合选择题与解释型答案。
- AI2D：科学图示理解，适合区域/结构证据。
- ChartQA：图表问答，适合数值声明与 OCR/坐标证据。
- TextVQA/DocVQA：文本/文档图像问答，适合 OCR 证据许可。

可借鉴机制：
- 用这些数据集覆盖不同声明类型：视觉对象、OCR 文本、图表数值、科学关系、文档字段。
- MVP 不应一开始覆盖所有数据集，建议先选 VLR-Bench + VisualSimpleQA/MagiC + ChartQA/TextVQA 子集。

专利风险：
- 数据集组合没有创造性。
- 这些 benchmark 只能作为实施例和效果验证，不能作为权利要求核心。

### 2.9 Uncertainty Calibration / Conformal Prediction：从置信度到可拒答状态

来源：
- Split conformal prediction for LVLM VQA: https://arxiv.org/html/2504.17671v3/
- The Art of Saying "Maybe": https://arxiv.org/html/2509.13379v2/
- Medical VQA calibration 2026: https://arxiv.org/html/2604.02543v1
- ConfRAG: https://openreview.net/forum?id=eQwWSsgsgQ

核心方法：
- 用 conformal prediction 构造预测集并控制错误率。
- 比较 VLM 在 MMMU、MMMU-Pro、ScienceQA、AI2D、MathVision 等数据上的 uncertainty performance。
- 医疗 VQA 研究显示过度自信无法靠 scaling 或普通 CoT 彻底解决。
- ConfRAG 使用 confidence-aware retrieval、hallucination detection、IDK-aware training。

可借鉴机制：
- “maybe/IDK/abstain”是状态机最终动作的重要组成。
- 可将 uncertainty 作为状态转移的辅助量：低支持 + 高未知质量 -> INSUFFICIENT，而不是直接输出低置信答案。

专利风险：
- 置信度阈值、conformal prediction、IDK-aware training 都是现有热点。
- 本案不宜主张“阈值过滤”本身，必须主张“声明证据状态 -> 生成许可动作”的结构化控制。

### 2.10 其他相关热点：长推理放大幻觉、组合幻觉、自验证

来源：
- More Thinking, Less Seeing?: https://arxiv.org/html/2505.21523v3
- Discovering Compositional Hallucinations in LVLMs: https://nips.cc/virtual/2025/loc/san-diego/poster/119442
- REVERSE retrospective resampling: https://nips.cc/virtual/2025/loc/san-diego/poster/120029
- ViLP visual language priors: https://icml.cc/virtual/2025/poster/44730

核心方法：
- 长 CoT 可能让模型更依赖语言先验，视觉注意下降。
- 组合问题中，即便单独视觉/文本问题能答对，组合后仍会产生幻觉。
- REVERSE 通过 hallucination-aware training 和 inference-time retrospective resampling 动态修正幻觉。
- ViLP 研究视觉语言先验，说明 VLM 会靠训练分布猜测而非真实看图。

可借鉴机制：
- 强化了本案“不应靠更长 CoT 解决”的立场。
- 状态机可以限制未被证据许可的长推理声明，避免 reasoning drift。

专利风险：
- 自验证、重采样、训练目标属于竞争热点。
- 新案应保持模型无关、训练无关，突出推理控制层的状态转移机制。

## 3. 哪些方向适合做单一专利机制

| 候选机制 | 是否推荐 | 理由 | 权利要求写法建议 |
|---|---|---|---|
| 声明级证据许可状态机 | 强推荐 | 能把 claim-level diagnosis、evidential conflict、insufficient evidence、grounding 统一成单一机制 | 固定 claim -> evidence requirement -> evidence matching -> state transition -> generation action |
| 证据冲突度量 + 状态转移 | 推荐，作为核心数学特征 | 比普通置信度更有技术深度 | 写支持质量、冲突质量、未知质量如何影响 SUPPORTED/CONFLICTED/INSUFFICIENT |
| 无证据拒答/降级生成 | 推荐，作为状态动作 | 对抗 RAG 过度自信，容易实验验证 | 写删除、改写、降级、补证、拒答，不写泛泛“提高可信度” |
| 视觉区域许可条件 | 推荐，作为从属 | 绑定 grounding，适合对象/属性/空间关系声明 | 写声明类型到证据需求的映射和区域相关度门槛 |
| 多跳声明依赖图 | 可选 | 对 VisualSimpleQA/ScienceQA 有价值 | 只作为从属，避免变成知识图谱 |
| Conformal prediction 校准 | 不建议做核心 | 现有技术密集，容易被认为统计校准 | 只作为状态转移辅助阈值 |
| 普通 Visual RAG | 不建议 | VLR/MRAG/Double-Bench/CogPlanner/MI-RAG 很拥挤 | 只作为证据来源，不作为发明点 |
| GNN/知识图谱 commonsense VQA | 不建议 | MAGIC-VQA 等已有 explicit + implicit KG/GNN | 若用，只作为证据候选生成 |
| CoT/self-correction | 不建议 | MagiC、REVERSE、长推理幻觉工作已覆盖 | 本案强调许可控制，不强调模型自省 |

## 4. 对“声明级证据许可状态机”的专利化启示

建议把创新机制收敛为一个连续流程：

1. 将候选答案或中间答案分解为若干声明 `c_i`。
2. 根据声明类型生成证据需求 `r_i`，例如对象存在、属性、数量、空间关系、OCR、图表数值、外部事实。
3. 从图像区域、OCR、文档 passage、检索文本、知识条目中抽取证据单元 `e_j`。
4. 对每个 `(c_i, e_j)` 计算支持量、冲突量、未知量或不足量。
5. 对每个声明进入状态集合：
   - `UNVERIFIED`：尚未检查；
   - `SUPPORTED`：满足最低证据需求且冲突低；
   - `CONFLICTED`：存在强反证或跨证据互斥；
   - `INSUFFICIENT`：证据缺失或不满足必要证据类型；
   - `PERMITTED`：允许进入最终答案；
   - `SUPPRESSED`：删除、改写或拒答。
6. 只有 `PERMITTED` 声明参与最终生成；`CONFLICTED/INSUFFICIENT` 触发补证、改写、降级或拒答。

关键专利边界：
- 不保护“检测幻觉”本身；
- 不保护“检索证据”本身；
- 不保护“置信度过滤”本身；
- 保护 **按声明粒度将证据支持/冲突/不足转化为生成许可状态，并据此控制最终答案构成**。

## 5. 本轮推荐引用/对标清单

高优先级：
- PRE-HAL / evidential conflict: https://arxiv.org/html/2506.19513v1/
- MRAG-Suite / MM-RAGChecker: https://arxiv.org/html/2509.24253v1
- VLR-Bench: https://vlr-bench.github.io/
- MagiC: https://arxiv.org/html/2507.07297v1
- VisualSimpleQA: https://huggingface.co/datasets/WYLing/VisualSimpleQA

中优先级：
- ViCrit: https://arxiv.org/html/2506.10128v1
- Ground-R1: https://arxiv.org/html/2505.20272v1/
- GroundSight: https://arxiv.org/html/2509.25669v1
- MMMU: https://mmmu-benchmark.github.io/
- Conformal prediction for LVLM VQA: https://arxiv.org/html/2504.17671v3/

风险对照：
- ConfRAG: https://openreview.net/forum?id=eQwWSsgsgQ
- MI-RAG: https://arxiv.org/html/2509.00798v1/
- CogPlanner: https://arxiv.org/html/2501.15470v2
- REVERSE: https://nips.cc/virtual/2025/loc/san-diego/poster/120029

## 6. 对下一步 Agent 的输入建议

给创新机制 Agent：
- 主创新点锁定“声明级证据许可状态机”。
- 权利要求 1 不要出现一串模块堆叠，要围绕状态集合和状态转移写。
- 必须把“证据不足/冲突时的生成动作”写进独权，避免被理解为离线评估。

给数据集/实验 Agent：
- MVP 推荐优先组合：VLR-Bench + VisualSimpleQA + MagiC 子集。
- 扩展验证：TextVQA/ChartQA/ScienceQA/AI2D 各抽小样本覆盖 OCR、数值、科学图示。
- 指标：未许可声明输出率、冲突声明抑制率、证据不足拒答率、答案准确率变化。

给专利批判 Agent：
- 重点攻击点应是：RAG、self-check、confidence threshold、claim-level checker、visual grounding 都已有。
- 补强方向是：状态集合、状态转移条件、声明-证据需求映射、生成许可动作四件事必须同时限定。

---

## File: 10_final_recommendation.md

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

---

## File: gates.md

# Gate 检查

## Gate 1 材料覆盖
- 结论：进行中。
- 已覆盖原案驳回材料、round03 风险材料、现有证据包/声明检查代码，并启动外部热点检索。

## Gate 2 原始公开支持
- 结论：本轮不作为复审修改评估。
- 本轮目标是另案重申请，因此允许设计原案未充分公开的新技术机制，但需在新申请说明书中完整公开。

## Gate 3 现有技术差异
- 结论：待最终 Agent 汇总。
- 初步标准：如果方案只是 claim checker、RAG evidence citation、confidence threshold、self-reflection 的组合，则不通过。
- 通过标准：必须定义“声明级证据许可状态”的状态集合、状态转移、证据需求生成、证据匹配和生成控制之间的闭环。

## Gate 4 非模块拼接
- 结论：待最终 Agent 汇总。
- 本轮禁止以“路由 + 图谱 + 仲裁 + 可信包”并列堆叠作为主创新。
- 推荐表达：一个状态机机制内部包含证据请求、证据校验和生成许可三个阶段。

## Gate 5 实验可行性
- 结论：待最终 Agent 汇总。
- 优先选择图像数据集，要求 1 周内能跑出 MVP：输入图像和问题，输出声明许可记录、降级/拒答样例和至少一种对比基线。

## Gate 6 技术效果
- 结论：待最终 Agent 汇总。
- 可主张机制性效果：减少无证据声明、识别视觉/文本冲突、提高答案可追溯性。
- 不得在未实验前主张量化提升。

---

## File: artifacts.md

# Artifacts

- `00_plan.md`：本轮图像 VQA 专利研究计划。
- `01_material_inventory.md`：本地材料和外部热点材料清单。
- `05_code_implementation_map.md`：数据集与首周 MVP 实验设计。
- `06_innovation_candidates.md`：声明级证据许可状态机及备选创新点。
- `07_examiner_critic_review.md`：审查员攻击预判和补强策略。
- `08_revision_strategy.md`：新申请名称、状态机定义、权利要求1草案和从属权利要求布局。
- `09_search_materials_report.md`：2023-2026 论文热点检索报告。
- `10_final_recommendation.md`：本轮最终推荐结论。
- `gates.md`：本轮 Gate 检查标准和初步结论。

## 本轮结论文件

- 优先阅读：`10_final_recommendation.md`
- 写专利交底书：`06_innovation_candidates.md` + `08_revision_strategy.md`
- 做代码 MVP：`05_code_implementation_map.md`
- 应对审查员：`07_examiner_critic_review.md`
- 查近年热点：`09_search_materials_report.md`

## 本轮未完成事项

- 尚未实现状态机 MVP 代码。
- 尚未下载或跑通 VLR-IF / TextVQA / VizWiz。
- 尚未生成真实实验指标。
- 尚未形成完整专利交底书正文。
