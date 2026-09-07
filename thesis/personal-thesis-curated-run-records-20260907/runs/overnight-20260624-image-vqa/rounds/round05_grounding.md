# Round 05: Grounding / 视觉证据定位方向

## 1. 本轮方向

- 方向名称：Grounding / 视觉证据定位 / 可追溯证据推理
- 检索范围：2021-2026 年 CVPR/ICCV/ECCV/NeurIPS/ICLR/AAAI/ACL/EMNLP/ACMMM/TPAMI/IJCV 及 arXiv/OpenReview 中与 visual grounding、bbox rationale、grounded reasoning、reasoning step grounding、traceable evidence 相关的工作。
- 目标问题：判断图像问答中“回答必须被视觉证据定位支撑”能否形成单一技术机制；重点避免落入“VQA + grounding + prompt / CoT / RAG”的常规组合。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | KOSMOS-2: Grounding Multimodal Large Language Models to the World | arXiv / Microsoft | 2023 | 将文本 span 与 bounding boxes 表示成类似 Markdown 链接的 location token，使 MLLM 可生成 grounded caption、grounded QA、referring expression。 | 证明“文本片段-视觉框”统一生成已经是基础能力，不能再把输出 bbox 本身作为创新点。 | https://ar5iv.labs.arxiv.org/html/2306.14824 |
| 2 | Groma: Localized Visual Tokenization for Grounding MLLMs | arXiv | 2024 | 在视觉 tokenizer 中引入 ROI/region token，将定位能力前置到图像 token 化过程，而不是让 LLM 直接回归坐标。 | 提供 grounding 模型结构路线：区域 token 可直接服务 VQA 解释，但“区域 token 化”本身已有强先例。 | https://www.arxiv-vanity.com/papers/2404.13013 |
| 3 | CogCoM: Chain of Manipulations | arXiv | 2024 | 让 VLM 通过 grounding、zoom-in 等 manipulation 逐步查看细节，输出可追踪操作结果。 | 针对 detailed VQA、TextVQA、TallyVQA 等细粒度问答，说明“先定位再放大再回答”已有公开路线。 | https://arxiv.org/html/2402.04236v2 |
| 4 | Visual CoT: Unleashing Chain-of-Thought Reasoning in MLLMs | arXiv | 2024 | 构造 373K 含中间 bounding boxes 的 Visual CoT 数据，推动多轮聚焦关键区域后回答。 | 已覆盖“推理步骤 + bbox”式解释 VQA，不能简单提出 step grounding。 | https://arxiv.org/html/2403.16999v1 |
| 5 | Visual Chain-of-Thought Prompting for Knowledge-Based Visual Reasoning | AAAI | 2024 | see-think-confirm 三阶段：扫描并 grounding 视觉概念，LLM 思考，再用跨模态分类器确认 rationale 与视觉上下文一致。 | 是 VQA 中“看-想-确认”的早期组合式方案，对 prompt + grounding + verify 的创造性构成强阻碍。 | https://ojs.aaai.org/index.php/AAAI/article/view/27888 |
| 6 | Multimodal Rationales / CRVQA for Explainable VQA | arXiv | 2024/2025 | 同时输出答案、文本 rationale 和 visual rationale；visual rationale 使用目标框，提出 visual-textual similarity 指标。 | 直接落在 bbox rationale for VQA，说明“答案旁边附视觉证据框”已成熟。 | https://arxiv.org/html/2402.03896v3/ |
| 7 | Grounded Chain-of-Thought for MLLMs / MM-GCoT | arXiv | 2025 | 定义 GCoT 任务：逐步识别并 grounding 相关视觉线索，建立 answer accuracy、grounding accuracy、answer-grounding consistency 评价。 | 把“答案-推理-坐标一致性”系统化，对本轮创新点形成强近似现有技术。 | https://arxiv.org/html/2503.12799v1/ |
| 8 | Ground-R1: Incentivizing Grounded Visual Reasoning via RL | arXiv | 2025 | grounding rollout + answer rollout；用格式约束和答案奖励诱导证据区域生成，无需显式 bbox/rationale 标注。 | 说明“无监督/弱监督诱导视觉证据区域 + 回答”已被 RL 框架覆盖。 | https://arxiv.org/html/2505.20272v1/ |
| 9 | GRIT: Teaching MLLMs to Think with Images | Project / arXiv | 2025 | reasoning chain 中交错自然语言与 bbox 坐标，用 GRPO-GR 奖励格式、计数框数量和答案正确性。 | 进一步确认“坐标化 CoT + RL”是热点路线，专利风险高。 | https://grounded-reasoning.github.io/ |
| 10 | ViGoRL: Grounded Reinforcement Learning for Visual Reasoning | NeurIPS / OpenReview | 2025 | 用 RL 强制每个 reasoning step 锚定到视觉坐标，并支持动态 zoom-in 反馈。 | 对“每步推理绑定坐标、动态查看局部”的方案构成非常强的现有技术。 | https://openreview.net/forum?id=1amnhVRQ3l |
| 11 | Point-RFT: Visually Grounded Reinforcement Finetuning | NeurIPS | 2025 | 文档 VQA 中让 CoT 的每一步引用视觉元素 point 坐标，再做 reinforcement finetuning。 | 在文档/图表 VQA 中已经验证 point-level grounded CoT 优于 text-only CoT。 | https://nips.cc/virtual/2025/loc/san-diego/poster/115309 |
| 12 | VISTAR: Visually Interpretable Subtask Reasoning for VQA | arXiv | 2025 | 将问题拆成结构化 subtask-of-thought，每个子任务输出文本解释和 bounding box。 | “子任务级视觉证据框解释”已明确出现，单纯子问题分解不可作为创新点。 | https://arxiv.org/html/2505.08084v1/ |
| 13 | TreeVGR / TreeBench: Traceable Evidence Enhanced Visual Grounded Reasoning | arXiv | 2026 | 构造 traceable evidence benchmark，强调 subtle targets、bbox evidence、second-order reasoning；用 RL 联合监督定位与推理。 | 与本轮主题高度重合，尤其是“traceable evidence + second-order reasoning”。 | https://arxiv.org/html/2507.07999v2 |
| 14 | RegionReasoner: Region-Grounded Multi-Round Visual Reasoning | ICLR / OpenReview | 2026 | 多轮视觉推理中要求 reasoning trace 显式引用 reference boxes，并用 global-local consistency reward 约束语义一致。 | 直接覆盖“多轮 region grounded reasoning trace”，需要避开“引用框 + 多轮推理”的表层方案。 | https://openreview.net/forum?id=KW6ZNSCrNG |
| 15 | VQA Therapy: Exploring Answer Differences by Visually Grounding Answers | arXiv | 2023 | 为每个有效答案标注视觉 evidence segmentation，分析多答案是否来自不同 visual grounding。 | 说明“不同答案对应不同证据区域”的问题已被提出，但未形成回答许可机制，可作为切入启发。 | https://www.arxiv-vanity.com/papers/2308.11662/ |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 从“答案正确”转向“答案是否由具体视觉区域支撑”。2025-2026 年的热点不是普通 visual grounding，而是 traceable evidence、step-level grounding、grounded RL、动态 zoom、坐标化 CoT。
  - 从静态框定位转向过程级证据：每个推理步骤、每个 subtask、每个 visual element 都需要可回溯到点/框/区域。
  - 从监督 bbox/rationale 数据转向弱监督或 RL：Ground-R1、GRIT、ViGoRL 都在减少显式人工证据标注依赖。
  - 从自然图像扩展到文档、图表、GUI、diagram、医学、视频等高风险或结构化场景，核心指标变成 grounding fidelity、answer-grounding consistency、evidence coverage。

- 已经成熟、不能作为创新点的部分：
  - 让模型输出 bounding box、point、坐标 token。
  - 在 CoT 中插入 bbox，或让每一步推理附带坐标。
  - 先检测/ground，再 crop/zoom，再回答。
  - 用 prompt 要求“请给出证据区域”。
  - 用 RL 奖励答案正确性、格式正确性、bbox 精度。
  - 用 GroundingDINO/SAM/OCR/检测器做候选证据，再交给 VQA 模型回答。
  - 用 answer-grounding consistency / visual-textual similarity 作为解释质量评价。

- 仍有空白或可迁移空间的部分：
  - 现有工作多在“生成证据”或“训练模型生成 grounded trace”，较少把最终回答拆成声明，并对每个声明做“证据许可/禁止/降级”的判定。
  - 现有 grounded CoT 往往只要求有框、有格式、有答案，未细分：证据是否覆盖了答案中的所有视觉谓词，证据是否只支持较弱声明，答案是否越过证据边界。
  - 多数方法把 bbox 作为解释输出，不把 bbox 与 answer claim 之间的覆盖、冲突、缺失关系作为核心控制机制。
  - 对专利而言，最可能成立的不是“grounding + VQA”，而是“声明级证据许可状态机”：每个回答声明必须经过证据覆盖状态判定，状态决定输出、降级、拒答或追问。

## 4. 候选创新点

```text
候选名称：
声明级视觉证据许可状态机（Claim-level Visual Evidence Permission State Machine）

解决的具体技术问题：
图像问答模型即使输出了 bbox 或 grounded CoT，也可能把证据框外的信息写进答案，或者用局部证据支持过强的全局声明。需要一个机制在最终输出前判断每个答案声明是否被视觉证据充分许可。

输入：
1. 图像 I；
2. 用户问题 Q；
3. 初始候选答案 A；
4. grounding 模型或 VLM 产生的候选证据区域集合 E={e_i}，每个 e_i 包含 bbox/point/mask、区域描述、置信度；
5. 从答案 A 拆出的原子视觉声明 C={c_j}，例如对象存在、属性、数量、关系、文本读取、比较、全局判断。

核心处理步骤：
1. 将候选答案拆成原子声明，并为每个声明生成证据需求类型：存在型、属性型、关系型、计数型、OCR 型、比较型、全局场景型。
2. 将每个声明映射为一个或多个必要视觉谓词，例如 subject、attribute、relation、reference object、count target、text span。
3. 对每个声明计算证据覆盖状态，而不是只计算 bbox 是否存在：
   - SUPPORT：必要视觉谓词均被证据区域覆盖；
   - PARTIAL：只覆盖部分谓词，可降级输出；
   - CONFLICT：证据区域与声明冲突；
   - INSUFFICIENT：证据不足；
   - OVERREACH：证据只支持弱声明，但答案写成强声明；
   - IRRELEVANT：证据框存在但与声明无关。
4. 根据状态机改写最终答案：
   - SUPPORT 的声明允许输出；
   - PARTIAL/OVERREACH 的声明降级为“图中可见区域显示...”；
   - CONFLICT/INSUFFICIENT 的声明阻断或转为无法确认；
   - 多声明答案按最弱状态决定整体可信级别。
5. 输出答案、每个声明的证据区域、许可状态和被降级/阻断的原因。

输出：
1. 经许可状态机过滤后的最终答案；
2. claim-evidence-state 表；
3. 被删除、降级、拒答或追问的声明列表。

为什么不是简单组合：
不是把 grounding 框附在 VQA 答案后面，也不是要求 CoT 输出坐标；核心技术动作是“以答案声明为对象，计算证据覆盖状态，并用状态驱动答案许可、降级和阻断”。grounding 只是输入，状态迁移和声明许可才是机制中心。

可实验数据集：
VLR-IF / V*Bench（干扰项与视觉搜索）、GQA（关系与属性）、TextVQA（OCR 声明）、VizWiz（证据不足和拒答）、VQA-AnswerTherapy（不同答案的不同证据区域）、MM-GCoT / TreeBench（若可获取）。

主要风险：
1. 审查员可能认为是 grounding consistency 的规则化后处理；
2. 原子声明拆分质量会影响稳定性；
3. 需要证明状态机相较“输出 bbox + self-check”有可验证技术效果，例如越权声明减少、错误拒答率可控、answer-grounding consistency 提升。
```

```text
候选名称：
反事实证据擦除的回答越权检测机制（Counterfactual Evidence Erasure for Answer Overreach Detection）

解决的具体技术问题：
模型可能把正确答案归因于错误或非必要区域。需要判断某个证据区域是否真是回答声明的必要视觉依据，而不是装饰性解释框。

输入：
图像、问题、候选答案、答案原子声明、候选证据区域。

核心处理步骤：
1. 对每个声明绑定候选证据区域；
2. 生成三类反事实图像：擦除声明证据区域、保留声明证据区域但擦除背景、替换相似干扰区域；
3. 在三类图像上重新回答或重新判定声明；
4. 若擦除证据后声明仍稳定成立，说明该证据不是必要证据；
5. 若保留证据但擦除背景后声明仍成立，则提高证据许可级别；
6. 若替换相似干扰区域后答案不变，则标记语言先验/幻觉风险。

输出：
每个声明的必要性分数、充分性分数、干扰敏感性分数，以及是否允许输出。

为什么不是简单组合：
不是普通 grounding，也不是 self-check；其核心是通过证据区域的反事实扰动验证“证据是否必要/充分”，把证据框从解释输出变成因果检验对象。

可实验数据集：
VQA-AnswerTherapy、GQA、VLR-IF、V*Bench、VizWiz。

主要风险：
计算成本高；擦除/替换可能引入图像分布偏移；因果验证在自然图像上容易被质疑为启发式。
```

```text
候选名称：
证据覆盖闭包的多声明答案压缩机制（Evidence-Coverage Closure for Multi-Claim Answer Compression）

解决的具体技术问题：
VQA 模型常在回答中加入未被问到或未被证据支持的修饰信息。需要将答案压缩到证据闭包内，只输出被视觉区域覆盖的最小充分声明。

输入：
问题、候选长答案、候选证据区域、每个区域的视觉描述。

核心处理步骤：
1. 将长答案拆成原子声明；
2. 将问题需求拆成必须回答项和可选补充项；
3. 对每个声明计算证据覆盖集合；
4. 构造“问题需求-证据区域-声明”的二部/三部覆盖图；
5. 求满足问题需求的最小声明集合，删除没有证据边或只满足可选补充的声明；
6. 对无法满足的必须项生成“无法从图中确认”的局部拒答。

输出：
最小证据闭包答案、删除声明及删除原因、证据覆盖图。

为什么不是简单组合：
不是新增 grounding 模型，而是把 grounding 结果转化为答案压缩约束，技术动作是求证据覆盖闭包并据此裁剪答案。

可实验数据集：
VizWiz、TextVQA、GQA、VQA-X、VQA-AnswerTherapy。

主要风险：
容易被认为是规则化摘要/后处理；如果没有明确状态定义和可量化收益，创造性弱于候选 1。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对“让 VQA 输出证据框”的方案：是，现有 KOSMOS-2、Visual CoT、GCoT、GRIT、ViGoRL、TreeVGR 已覆盖。
  - 对候选 1：不完全是。其对象不是 grounding 输出，而是“答案声明的许可状态”。要把权利要求写在声明拆分、证据需求类型、覆盖状态迁移、状态驱动输出控制上，才可能避开场景替换。
  - 对候选 2：不是单纯场景替换，但可能被认为是视觉问答中的反事实解释验证，需强调“以 evidence region 为扰动单元，判定声明必要性/充分性”。
  - 对候选 3：有较大后处理风险，容易被说成摘要裁剪或规则过滤。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - grounding 文献已大量使用 CoT、RL、自检、格式奖励；如果只要求“生成证据后再检查答案”，会被直接打掉。
  - 候选 1 不能写成 self-check，应写成确定的状态机：claim -> evidence demand -> predicate coverage -> state transition -> output permission。
  - 候选 2 不能写成普通 self-check，应强调反事实图像族生成和必要性/充分性分数。
  - 置信度阈值不是创新点，所有候选必须避免把“低置信拒答”作为核心。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 如果证据来源依赖 GroundingDINO/SAM/OCR，再直接给 VQA 回答，就是明显组合。
  - 候选 1 可以把 GroundingDINO/SAM/OCR 都降级为可替换的证据提取器，核心保护“证据许可状态判定”。这样即便证据来自不同模型，机制仍成立。
  - OCR/TextVQA 只能作为实验场景，不能作为发明点。

- 是否能被一篇或几篇论文自然组合推出？
  - “每步推理坐标化”可由 Visual CoT + GRIT/ViGoRL 推出。
  - “用 RL 奖励 grounding fidelity”可由 Ground-R1 + ViGoRL + TreeVGR 推出。
  - “输出 bbox rationale”可由 CRVQA/MRVQA + GCoT 推出。
  - 候选 1 的风险在于 answer-grounding consistency 已存在；需要把区别压实：已有 consistency 多用于评价/训练，而本候选用于逐声明许可状态迁移，并将 OVERREACH/PARTIAL/CONFLICT 等状态直接控制答案删除、降级、拒答。

- 是否缺少可验证技术效果？
  - 候选 1 可验证：
    - 越权声明率下降：答案中无证据支持的原子声明比例；
    - 证据覆盖完整率提升：每个答案声明必要视觉谓词被覆盖的比例；
    - 幻觉率下降：POPE/VizWiz/VLR-IF 干扰项场景；
    - 拒答质量：证据不足时的正确拒答率和过拒率；
    - answer-grounding consistency 提升。
  - 候选 2 可验证必要性/充分性，但工程成本较高。
  - 候选 3 可验证答案冗余和幻觉下降，但创造性较弱。

## 6. 本轮最佳候选

只保留 1 个：声明级视觉证据许可状态机（Claim-level Visual Evidence Permission State Machine）。

- 为什么选它：
  - 2025-2026 的 grounding 热点已经把“生成框、步骤绑定框、RL 训练 grounded trace”做得很密。本轮可争取的空间不在“如何生成证据”，而在“证据如何许可答案声明”。
  - 该候选把技术对象从模型输出形态转移到回答控制机制：每个原子声明必须经过 evidence demand、predicate coverage、state transition，最终状态决定允许、降级、阻断或拒答。
  - 与项目既有专利方向一致，可继续收敛到单一深机制，而不是发散成 grounding + VQA + prompt。

- 为什么淘汰其他候选：
  - 反事实证据擦除机制技术味较强，但计算成本和图像扰动偏差风险大；更适合作为候选 1 的验证模块或从属权利要求。
  - 证据覆盖闭包压缩机制工程可行，但容易被审查员认为是规则化后处理或答案摘要，创造性不如状态机。
  - “grounded CoT / bbox rationale / dynamic zoom / RL grounding”全部被已有论文密集覆盖，不建议作为独立创新点。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓“对候选答案拆分得到的每个原子视觉声明，依据该声明的证据需求类型计算视觉谓词覆盖状态，并根据覆盖状态在许可状态机中迁移，从而控制该声明在最终答案中的输出、降级、阻断或拒答”。
  - 关键状态建议至少包括：支持、部分支持、冲突、证据不足、越权、无关。
  - 关键输入不要限定为某个 grounding 模型；证据区域可来自 bbox、point、mask、OCR box、region token 或 attention-derived region。
  - 关键输出不要只是“带框答案”，而是“经过状态机过滤后的答案 + claim-evidence-state 表”。

- 如果做实验，最快怎么证明：
  - 用 Qwen2.5-VL 或现有 VLM 先生成候选答案和候选证据框，不训练模型；
  - 在 GQA/TextVQA/VizWiz/VLR-IF 上抽样构造 claim-evidence 标注或弱标注；
  - 比较三组：
    - baseline：直接 VQA；
    - grounded baseline：要求输出证据框后回答；
    - ours：证据许可状态机过滤后回答；
  - 指标：
    - answer accuracy；
    - unsupported claim rate；
    - overreach claim rate；
    - correct refusal rate；
    - answer-grounding consistency；
  - 最快可先人工评估 200-500 条样本，证明状态机能显著减少无证据声明和越权表述，再决定是否扩展自动评测。
