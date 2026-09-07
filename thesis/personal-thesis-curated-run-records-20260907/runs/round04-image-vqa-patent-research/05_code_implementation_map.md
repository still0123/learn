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
