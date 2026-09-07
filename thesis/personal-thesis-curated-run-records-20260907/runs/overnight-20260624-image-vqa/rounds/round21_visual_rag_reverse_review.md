# Round 21：多模态检索 / 视觉 RAG 反向审查

## 1. 本轮方向

- 方向名称：多模态检索 / 视觉 RAG / 声明级多模态证据利用反向审查
- 检索范围：Visual RAG、MRAG、MMRAG、retrieval-augmented VQA、knowledge-intensive VQA、multimodal fact-checking、claim-level evidence checking，覆盖 2021-2026 年 arXiv、ICLR、ACL、KDD Cup/benchmark、CV/NLP 交叉工作。
- 目标问题：明确“检索增强图像问答”中哪些技术点已经成熟、不能作为专利创新点；再从 evidence utilization 而非 retrieval pipeline 切入，筛出一个更不容易被 RAG / CoT / self-check 常规组合击穿的候选机制。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | VisRAG: Vision-based Retrieval-augmented Generation on Multi-modality Documents | ICLR | 2025 | 直接把文档页面作为视觉输入嵌入和检索，避免先 OCR/解析为文本导致版面、图像、结构信息损失；检索后由 VLM 基于页面图像生成答案 | 证明“视觉文档直接检索 + VLM 生成”已是明确路线，不能再把 OCR-free Visual RAG 当核心创新 | https://openreview.net/forum?id=zG459X3Xge |
| 2 | MRAG-Bench: Vision-Centric Evaluation for Retrieval-Augmented Multimodal Models | ICLR | 2025 | 构造 16,130 张图像、1,353 个问题、9 类场景，评估 LVLM 利用视觉检索知识的能力；显示模型拿到视觉知识后仍利用不足 | 关键启发是“有检索结果不等于会用证据”，evidence utilization 是仍有空白的方向 | https://mragbench.github.io/ |
| 3 | Multimodal Iterative RAG for Knowledge Visual Question Answering (MI-RAG) | arXiv | 2025 | 维护累计 reasoning record，迭代生成多查询，并在视觉/文本异构知识库中联合搜索，再更新 reasoning record | 迭代检索、multi-query、跨模态知识库搜索已可由现有 RAG 自然推出，不宜作为主创新 | https://arxiv.org/html/2509.00798v2 |
| 4 | Fine-Grained Retrieval-Augmented Generation for Visual Question Answering (KU-RAG) | arXiv | 2025 | 将文本片段和实体图像合成细粒度 knowledge unit，进行向量库管理、匹配和 knowledge correction chain | 细粒度知识单元、实体图像 + 文本片段联合检索已经出现，不能简单改名为“证据单元检索” | https://arxiv.org/html/2502.20964v2 |
| 5 | Benchmarking Multimodal RAG with Dynamic VQA Dataset and Self-adaptive Planning Agent | arXiv | 2024 | 构造动态 VQA，强调固定 mRAG 流程在动态、多跳、多工具问题上失败；提出自适应搜索/规划 | 自适应检索查询、工具选择、动态规划已经是 MRAG 热点，单独写“按问题选择检索工具”风险高 | https://arxiv.org/html/2411.02937v2 |
| 6 | Enhancing Document VQA Models via Retrieval-Augmented Generation | arXiv | 2025 | 系统比较多页 DocVQA 中文本 RAG、视觉 RAG、重排、版面切分等组件 | 说明多页文档 VQA 里“先检索相关页面/片段再回答”已是工程常规 | https://arxiv.org/html/2508.18984v1 |
| 7 | Chart-MRAG Bench / CHARGE | arXiv | 2025 | 面向图表文档 MRAG，抽取 keypoints、跨模态验证并生成 QA；发现 unified multimodal embedding 对图表场景不足，且有 text-over-visual bias | 图表 MRAG 的 benchmark 和跨模态验证已有，但“回答声明是否被图表证据许可”仍可迁移 | https://arxiv.org/html/2502.14864v1 |
| 8 | DEFAME: Dynamic Evidence-based Fact-checking with Multimodal Experts | arXiv | 2024/2025 | 六阶段多模态事实核查：规划动作、执行工具、汇总结果、形成 fact-check、预测 verdict、解释 verdict | 多模态 claims + 动态证据搜索 + verdict 已成熟；但它面向事实核查，不是 VQA 内部回答声明的许可状态 | https://arxiv.org/html/2412.10510 |
| 9 | Open-Domain, Content-based, Multi-modal Fact-checking of Out-of-Context Images | arXiv | 2021 | 基于图文互证与 cycle-consistency，从图像/文本各自检索证据并做跨模态一致性判断 | 证明“图文证据一致性检查”不是新概念；若用于 VQA，必须落到更细的声明级输出控制 | https://ar5iv.labs.arxiv.org/html/2112.00061 |
| 10 | MetaSumPerceiver: Multimodal Multi-Document Evidence Summarization for Fact-Checking | ACL | 2024 | 面向 fact-checking 的多文档多模态证据摘要，使用动态 perceiver 和 entailment 目标生成 claim-specific evidence summary | 多模态多证据聚合、面向 claim 的证据摘要已出现，不能只写“证据摘要后回答” | https://aclanthology.org/2024.acl-long.474/ |
| 11 | Adaptive Multimodal Fact-Checking with Visual Evidence Necessity | arXiv | 2026 | 判断视觉证据是否必要，再让 verifier 基于必要性评估和检索证据做判断；指出盲目加入视觉证据可能降低准确率 | “视觉证据是否必要”已是显式研究点，后续创新需更具体地控制 VQA 答案中的每个声明 | https://arxiv.org/html/2604.04692v1 |
| 12 | Retrieval Augmented Generation and Understanding in Vision: A Survey and New Outlook | arXiv | 2025 | 系统综述视觉理解、VQA、文档理解、医学、工业等场景中的 RAG/RAU | 说明视觉 RAG 已是大方向，不宜把“把 RAG 用于图像问答”作为独立权利要求主干 | https://arxiv.org/html/2503.18016v1 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 从“给 LVLM 加文本知识”转向“图像、页面、图表、实体图片、文本片段等异构证据共同检索”。
  - 从单轮 top-k 检索转向迭代查询、multi-query、自适应工具规划、多跳检索。
  - 从只看最终答案准确率转向分解评估：retrieval recall、evidence utilization、grounding、coverage、factuality、visual evidence necessity。
  - 从普通 OK-VQA / InfoSeek 扩展到多页文档、图表、长尾实体、动态事实、智能眼镜 egocentric 场景。
  - 越来越多 benchmark 指出：即使给了 ground-truth 或 top-k 视觉证据，LVLM 仍不能稳定利用证据，甚至出现文本证据压过视觉证据、无关证据污染回答的问题。

- 已经成熟、不能作为创新点的部分：
  - 不能写“将 RAG 用于图像问答”。该方向已经是公开常规路线。
  - 不能写“将图像和文本统一嵌入到向量库后检索”。VisRAG、KU-RAG、MRAG-Bench 相关路线已经覆盖。
  - 不能写“OCR 文本检索 + 页面图像检索 + VLM 回答”。多页 DocVQA 和 Visual RAG 文档工作已经成熟。
  - 不能写“根据问题生成多个查询进行迭代检索”。MI-RAG、Dyn-VQA/OmniSearch 类工作已经自然公开。
  - 不能写“检索后让模型自检或解释答案”。RAG fact-checking、CoRAG/ToRAG、DEFAME、MetaSumPerceiver 已经覆盖。
  - 不能写“对图像和文本证据做一致性检查”。out-of-context image fact-checking、multimodal fact-checking 已经有图文 cycle consistency、verdict、explanation。
  - 不能写“判断是否需要视觉证据”。2026 年 adaptive multimodal fact-checking 已经直接研究 visual evidence necessity。
  - 不能把“视觉 grounding + 检索 + 生成”堆叠为主创新，审查员很容易用 VisRAG / KU-RAG / DEFAME / grounding 文献组合击穿。

- 仍有空白或可迁移空间的部分：
  - RAG 系统通常把证据作为生成上下文，缺少对最终答案中每个声明的“可说/不可说/降级说/需拒答”的中间控制。
  - 多模态 fact-checking 多以外部 claim 为对象，目标是 verdict；图像问答则是模型自己生成答案，关键风险是生成过程中出现多个子声明，其中一部分被图像支持、一部分来自检索文本、一部分越权推断。
  - 现有 evidence utilization 多是训练模型“更会用证据”，但较少把证据类型、证据粒度、证据冲突和声明强度绑定为确定性状态转移。
  - 视觉证据必要性研究通常判断整条 claim 是否需要视觉证据；仍可切入“同一回答内，不同声明分别需要图像局部、检索文本、OCR、表格数值或跨模态一致证据”的局部许可。
  - MRAG benchmark 暴露了“有证据但不会用”的问题，可把技术效果定义为减少 unsupported claims、降低视觉证据被文本证据覆盖、提升拒答/降级回答准确性，而不必承诺最终 VQA accuracy 大幅提升。

## 4. 候选创新点

```text
候选名称：声明级多模态证据许可状态机

解决的具体技术问题：
在视觉 RAG 图像问答中，检索到的文本/图像/OCR/图表证据常被直接拼入上下文，模型会把局部支持、弱相关证据、冲突证据和语言先验混合成流畅答案，导致答案中出现无证据声明、越权解释、视觉证据被文本证据覆盖等问题。

输入：
用户问题、原始图像、候选答案草稿或候选回答片段、检索得到的多模态证据集合（图像页、局部框、OCR 文本、图表 keypoint、外部文本段、实体图像）、每条证据的来源和模态标签。

核心处理步骤：
1. 将候选答案拆分为最小可验证声明，包括对象存在、属性、数量、空间关系、文本内容、外部知识、因果/意图/常识推断等类型。
2. 为每个声明生成证据需求向量，标记其最低证据门槛：必须由原图支持、必须由 OCR 支持、必须由外部文本支持、必须由图像与文本共同支持、只允许弱描述、不允许回答等。
3. 对每个声明分别计算多模态证据匹配状态，而不是对整条答案打总分；状态包括：SUPPORTED_VISUAL、SUPPORTED_TEXTUAL、SUPPORTED_CROSS_MODAL、CONFLICTED、INSUFFICIENT、OUT_OF_SCOPE、VISUAL_OVERRIDE_REQUIRED、TEXT_ONLY_ALLOWED。
4. 根据声明类型和问题类型执行状态转移：例如视觉属性声明若只有外部文本支持则降级或阻断；百科知识声明若实体图像未确认则阻断；图表数值声明若 OCR 与轴线证据冲突则标为冲突；推断性声明若缺少视觉可观察依据则降级为“不确定/无法判断”。
5. 对最终答案执行声明级重写：许可声明保留，证据不足声明降级，冲突声明标注冲突或拒答，越权声明删除；输出答案同时附带每个声明的许可状态。

输出：
经过证据许可控制的最终答案、每个声明的证据状态、被删除/降级/拒答的声明清单。

为什么不是简单组合：
该机制的核心不是检索更多证据，也不是让模型自检，而是把“答案声明强度”和“多模态证据门槛”绑定为状态转移规则。它限制的是生成内容的许可边界，可以嵌入任意 Visual RAG 检索器之后；即使检索器、VLM、CoT 全部替换，声明级状态机仍是独立技术动作。

可实验数据集：
MRAG-Bench（视觉检索知识利用）、InfoSeek / Encyclopedic VQA / OK-VQA（外部知识 VQA）、TextVQA / DocVQA / MP-DocVQA / InfographicVQA（OCR 和文档证据）、ChartQA / Chart-MRAG Bench（数值和图表证据）、VLR-IF 或带干扰证据的自构造 VQA 子集。

主要风险：
claim decomposition 和 evidence matching 可能被认为是 LLM prompt/self-check；需要在权利要求中抓“声明类型-证据门槛-许可状态-输出动作”的确定映射，而不是泛泛描述模型判断。另一个风险是与 fact-checking verdict 过近，需要强调对象是 VQA 答案内部的多个生成声明，而非外部事实核查 claim。
```

```text
候选名称：视觉证据必要性驱动的检索模态门控

解决的具体技术问题：
视觉 RAG 中盲目把文本、图像、OCR、网页证据全部加入上下文，可能引入噪声或让文本证据覆盖图像观察，导致回答偏离原图。

输入：
问题、原图、候选检索模态列表、初始图像理解结果、外部文本/视觉检索结果。

核心处理步骤：
1. 判断问题是否必须依赖原图可观察信息、外部知识、OCR、图表数值或历史上下文。
2. 根据问题类型选择可用检索模态，禁止无关模态进入上下文。
3. 对进入上下文的模态设置优先级，例如视觉属性问题中原图证据优先于网页文本。
4. 生成答案时记录每个模态是否实际贡献。

输出：
模态门控后的证据集合和答案。

为什么不是简单组合：
有一定工程价值，但“是否需要视觉证据/文本证据”的思想已经在 adaptive multimodal fact-checking 和 MRAG planning 中出现；若不结合声明级状态，容易被认为是检索前路由。

可实验数据集：
MRAG-Bench、CRAG-MM、InfoSeek、TextVQA、ChartQA。

主要风险：
非常容易被审查员认定为“根据问题类型选择检索工具”的常规 RAG 路由，创造性弱。
```

```text
候选名称：反证优先的多模态 RAG 答案抑制机制

解决的具体技术问题：
普通 RAG 只检索支持答案的证据，缺少主动检索反证或冲突证据的机制，导致答案在存在视觉/文本冲突时仍被生成。

输入：
问题、原图、候选答案、支持性检索证据、可选反向查询模板。

核心处理步骤：
1. 根据候选答案生成反向查询，例如“不是该实体/不在该位置/不同数值/相反趋势”。
2. 检索可能反驳候选声明的视觉或文本证据。
3. 对支持证据和反证证据进行冲突评分。
4. 若反证强于支持证据，则阻断或降级候选答案。

输出：
经反证检查后的答案和冲突报告。

为什么不是简单组合：
反证优先比普通 self-check 更强，但反向检索、fact-checking、contradiction detection 都有大量近似工作，必须进一步绑定到图像问答声明类型才有机会。

可实验数据集：
VLR-IF、MRAG-Bench、MOCHEG、VERITE、TextVQA 干扰项子集、自构造 hard negative VQA。

主要风险：
会被 DEFAME、RAGAR、out-of-context image fact-checking、CoVe/self-check 类文献自然组合推出；单独作为主案风险较高。
```

```text
候选名称：检索证据利用失败的测试集生成器

解决的具体技术问题：
现有 VQA/MRAG 测试集常评估最终答案，难以定位模型是未检索到、检索到了但未使用、还是被错误证据误导。

输入：
图像、问题、标准答案、可控证据库、干扰证据模板。

核心处理步骤：
1. 为每个问题构造支持证据、无关证据、冲突证据和部分支持证据。
2. 控制不同 evidence condition：无证据、支持证据、冲突证据、混合证据、ground-truth 视觉证据。
3. 比较模型答案变化，标记 retrieval failure、utilization failure、over-trust failure。
4. 输出针对 evidence utilization 的评测样本。

输出：
带证据条件标签的 VQA 测试样本和错误类型标签。

为什么不是简单组合：
它是评测/数据构造方向，不是回答机制；适合实验支撑，不适合做主专利机制。

可实验数据集：
MRAG-Bench、VLR-IF、OK-VQA、InfoSeek、TextVQA、ChartQA。

主要风险：
数据集生成和 hard negative construction 已经是成熟方向，除非有非常具体的生成约束，否则专利壁垒不足。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对“将 RAG 用于图像问答”“将 fact-checking 用于 VQA”而言，是。VisRAG、MRAG-Bench、MI-RAG、KU-RAG、DEFAME 都能证明相关组合已显而易见。
  - 对“声明级多模态证据许可状态机”而言，抗辩点在于处理对象不是外部 fact-checking claim，而是 VQA 生成答案内部的多个最小声明；处理结果不是真假 verdict，而是逐声明的许可、降级、阻断和重写动作。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 如果只写“检索证据后让模型检查答案是否正确”，会被直接打成 RAG + self-check。
  - 最佳候选必须避免使用泛化的“模型自评置信度”。应强调每类声明有不同证据门槛，例如视觉属性声明不能仅由网页文本许可，图表数值声明必须同时满足 OCR/轴线/数值区域一致，外部知识声明必须先由图像实体定位确认。
  - 状态输出不是一个分数，而是离散许可状态和确定动作：保留、降级、删除、拒答、提示冲突。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 检索、grounding、OCR、图表解析本身都是成熟模块，不能作为创新核心。
  - 可保留它们作为证据来源，但独立权利要求应抓“声明类型对应的证据需求生成、跨模态证据匹配状态判定、基于状态的输出许可控制”。
  - 如果权利要求写成“先 OCR，再检索，再 grounding，再回答”，会被现有文献组合击穿。

- 是否能被一篇或几篇论文自然组合推出？
  - VisRAG + MI-RAG 可以推出视觉/文本异构检索和迭代查询。
  - DEFAME + RAGAR + out-of-context fact-checking 可以推出多模态证据检索、动态工具、事实核查 verdict。
  - MRAG-Bench + Chart-MRAG 可以推出“证据利用不足、图表/视觉证据难用”的问题动机。
  - 因此，候选必须把自然组合的终点继续推进一步：不是“检索证据并判断真假”，而是“把答案内部各类声明映射到证据门槛和许可动作”。这个动作在 VQA 输出控制中更具体，组合难度相对更高。

- 是否缺少可验证技术效果？
  - 若只承诺提高 VQA accuracy，效果不稳定且容易被认为是模型能力提升。
  - 可验证指标应改为：unsupported claim rate、over-claim rate、evidence conflict pass-through rate、视觉证据被文本证据覆盖率、正确拒答率/降级率、claim-level support F1。
  - 最快实验不必训练模型：用 Qwen2-VL / GPT-4o 类模型生成初稿，再加声明级许可后处理，在 MRAG-Bench、TextVQA、ChartQA、VLR-IF 干扰项上比较上述错误率。

## 6. 本轮最佳候选

本轮只保留：**声明级多模态证据许可状态机**。

- 为什么选它：
  - 反向查重后，Visual RAG 的检索、迭代、多模态融合、自适应工具、证据摘要、fact-checking verdict 都已经很成熟。继续从“怎么检索”切入风险很高。
  - 现有 MRAG benchmark 明确暴露“检索到了但不会用”的问题，且 fact-checking 方向多处理外部 claim；图像问答中真正可写的是“生成答案内部每个声明是否被证据许可”。
  - 它与项目既定主线“声明级证据许可状态机”一致，能形成单一深机制，而不是 RAG + grounding + self-check 的横向堆叠。

- 为什么淘汰其他候选：
  - 淘汰“视觉证据必要性驱动的检索模态门控”：已有 visual evidence necessity 和自适应 MRAG planning，单独写会像工具路由。
  - 淘汰“反证优先的多模态 RAG 答案抑制机制”：fact-checking、反向检索、contradiction detection 近似文献太多，可作为状态机中的冲突证据来源，不宜做主案。
  - 淘汰“证据利用失败测试集生成器”：适合作为实验配套和指标构造，不适合作为核心专利机制。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“对候选回答进行最小可验证声明拆分；根据声明类型生成多模态证据需求；将检索证据分别映射为声明级许可状态；依据许可状态对声明执行保留、降级、阻断或拒答”的连续动作。
  - 权利要求中应避免把“RAG 检索器、OCR、VLM、向量数据库”写成发明点，只把它们作为可替换输入来源。
  - 关键限定可以写成：同一答案内不同声明采用不同证据门槛；当声明所需模态与实际支持模态不匹配时触发降级/阻断；当视觉证据与文本证据冲突时按声明类型执行视觉优先、文本优先或拒答。

- 如果做实验，最快怎么证明：
  - 数据集：先用 MRAG-Bench + TextVQA + ChartQA / Chart-MRAG 小样本；再加 VLR-IF 或自构造干扰证据子集。
  - Baseline：原始 VLM、普通 RAG、RAG + self-check、RAG + CoT。
  - 方法：生成候选答案后做声明拆分和证据许可状态判定，再重写答案。
  - 指标：unsupported claim rate、claim-level support F1、conflict pass-through rate、正确拒答/降级率、最终 answer accuracy 作为辅助。
  - 预期最可辩护效果：不一定显著提高所有场景 accuracy，但应显著减少无证据声明和冲突证据下的错误强答，这更贴合专利技术效果。
