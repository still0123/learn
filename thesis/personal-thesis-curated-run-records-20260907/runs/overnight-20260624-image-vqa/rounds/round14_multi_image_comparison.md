# Round 14：多图像 / 对比问答方向

## 1. 本轮方向

- 方向名称：多图像 / 对比问答 / 变化推理
- 检索范围：multi-image VQA、image set reasoning、before-after reasoning、difference QA、visual comparison、change reasoning、multi-view reasoning、visual retrieval over image sets。
- 目标问题：寻找一个能落到图像问答系统中的单一技术机制，使模型在多张图像之间先对齐可比较证据，再判断某个差异性、比较性或变化性回答是否被图像充分支持，避免仅靠语言先验、位置偏置或粗粒度 caption 得出结论。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | Visual Question Answering on Image Sets / ISVQA | arXiv / UMD-AWS | 2020 | 将单图 VQA 扩展为图像集合问答，要求在多视角室内/室外图像间关联对象并避免重复计数 | 多图 VQA 早期任务定义，暴露同一场景多视角对象关联与去重问题 | https://www.arxiv-vanity.com/papers/2008.11976/ |
| 2 | BLINK: Multimodal Large Language Models Can See but Not Perceive | ECCV | 2024 | 将相对深度、视觉对应、多视角推理等经典视觉感知任务改写为问答；证明 MLLM 在视觉对应和多视角感知上明显弱于人类 | 说明多图/对比问答的关键瓶颈不是语言推理，而是视觉对应和细粒度观察 | https://arxiv.org/html/2404.12390v3 |
| 3 | MuirBench: A Comprehensive Benchmark for Robust Multi-image Understanding | ICLR | 2025 | 12 类多图理解任务、10 类图像关系，并构造 answerable/unanswerable 成对样本测试稳健性 | 对“差异声明许可”很关键：模型必须知道何时不能由给定图像回答 | https://muirbench.github.io/ |
| 4 | Visual Haystacks / MIRAGE | ICLR | 2025 | 在大规模图像集合中做视觉检索与多图推理，显示长上下文多图输入存在视觉干扰和位置偏置；MIRAGE 用视觉 RAG 先检索再回答 | 多图 VQA 中“找对相关图”是前置难题，但单纯 RAG 仍未解决跨图证据是否可比较 | https://visual-haystacks.github.io/ |
| 5 | ReMI: A Dataset for Reasoning with Multiple Images | arXiv / Google DeepMind | 2024 | 覆盖数学、物理、逻辑、代码、表格、空间和时间推理等多图推理任务 | 提供泛化评测来源，可检验候选机制是否只适用于某一类图片 | https://arxiv.org/html/2406.09175v1/ |
| 6 | MIRB: Multi-Image Relational Benchmark | arXiv / benchmark page | 2024 | 2-42 张图输入，覆盖感知、视觉世界知识、推理和多跳推理；发现拼接图片通常伤害性能 | 支持“不要把多图简单拼成一张”的技术判断 | https://www.alphaxiv.co/benchmarks/tongji-university/mirb |
| 7 | Show Me What and Where has Changed? CDQAG / QAG-360K | arXiv | 2024 | 遥感变化检测问答与 grounding，输出文本答案和变化区域 mask | 变化问答的成熟方向，强调“什么变了”和“哪里变了”必须共同验证 | https://arxiv.org/html/2410.23828v2/ |
| 8 | PLURAL: Pretraining VLM for Difference VQA in Longitudinal Chest X-rays | MIDL / arXiv | 2024 | 使用纵向胸片和报告进行差异 VQA 预训练，回答两张医学影像之间病灶变化 | 医学 diff-VQA 证明成对图像差异问答是高价值任务，但领域较窄 | https://arxiv.org/html/2402.08966v2 |
| 9 | Multi-Image VQA for Unsupervised Anomaly Detection | arXiv | 2024 | 将原图、重建图、异常图等多图输入问答框架，用 Knowledge Q-Former 融合异常相关视觉知识 | 提供“异常/差异图作为证据”的可迁移思想，但容易被认为是异常检测组合 | https://arxiv.org/html/2404.07622v1/ |
| 10 | CompareBench: Visual Comparison Reasoning in VLMs | arXiv | 2025 | 用数量、时间、几何、空间四类比较任务诊断 VLM；发现强模型仍在时间顺序和空间关系上系统失败 | 直接证明视觉比较推理仍是 VLM 盲点，适合作为实验评测集 | https://arxiv.org/html/2509.22737v1/ |
| 11 | BLINK-Twice | NeurIPS | 2025 | 使用自然对抗图像对和推理链标注，评估模型是否真正观察细节；发现 CoT/self-criticism 不稳定，重复视觉观察有效 | 支持候选方案中的“证据重观察/重定位”需要外部技术约束，而不是普通 CoT | https://nips.cc/virtual/2025/loc/san-diego/poster/121522 |
| 12 | XVR: Learning Multi-View Spatial Reasoning from Cross-View Relations | arXiv | 2026 | 构造跨视角关系数据，包含 correspondence、verification、localization 三类任务 | 与跨图对象对应、关系验证高度相关，可作为多视角子任务评测 | https://arxiv.org/html/2603.27967v1 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 多图输入数量变多后，模型不是自然学会跨图推理，而是出现视觉干扰、位置偏置、相关图检索失败和跨图对象对应失败。
  - 从“回答一个多图问题”转向“先找哪几张图相关、哪几个区域可比较、比较结论是否被证据许可”。
  - 评测开始引入 unanswerable / adversarial pair / natural pair / subtle difference，用来打击语言先验和粗糙 caption。
  - 对比问答的难点集中在细粒度属性、空间关系、时间顺序、同一对象跨视角对应、变化区域定位。

- 已经成熟、不能作为创新点的部分：
  - 直接把多张图拼接或全部送入 VLM，再提示“请比较”。
  - 对每张图分别 caption，再让 LLM 在文本上做差异总结。
  - 普通 visual RAG：先检索相关图，再问答。
  - 普通 CoT / self-check / majority vote。
  - 传统变化检测、异常检测、医学 diff-VQA 的特定领域模型本身。
  - 输出 bounding box、mask 或 heatmap 作为解释，本身已经是常规 grounding 方向。

- 仍有空白或可迁移空间的部分：
  - “可比较性”判断：在多图中，两个区域是否代表同一对象、同类对象、同一空间关系或同一时间轨迹，现有 VQA 通常没有显式许可环节。
  - “差异声明许可”：回答前先判断每个拟输出的比较性陈述是否有一对或多对跨图证据支持，不足则拒绝或降级为不确定。
  - “负证据”表达：不仅说明哪里不同，也说明哪些图像/区域不能支撑某个差异。
  - “跨图证据对齐日志”：输出答案时附带最小跨图证据单元，便于实验评估和专利权利要求落点。

## 4. 候选创新点

```text
候选名称：
问题约束的跨图证据对齐与差异声明许可机制

解决的具体技术问题：
多图像问答中，模型经常在未确认跨图对象/区域可比较的情况下输出“更大、更少、变化、消失、位置不同、前后顺序”等比较性答案，导致答案由语言先验或局部 caption 推出，而不是由多图视觉证据推出。

输入：
多张图像 I1...In；自然语言问题 Q；可选的候选答案或由模型草拟的比较性陈述集合 S；视觉检测/分割/patch 特征；可选时间戳或图像顺序元数据。

核心处理步骤：
1. 从 Q 中解析比较意图，得到比较维度 D，例如数量、属性、空间位置、时间顺序、状态变化、对象存在性。
2. 对每张图生成问题相关候选证据单元 E，包括对象区域、局部 patch、关系三元组、计数片段或变化候选区域。
3. 构建跨图证据二部图/多部图 G，边表示两个证据单元在 D 下是否“可比较”；边权由视觉相似性、类别一致性、空间上下文一致性、问题词对齐和元数据一致性共同确定。
4. 对每个候选比较性陈述 s，寻找最小支持证据链 C_s：至少包含两个图像中的可比较证据单元、比较维度 D、差异方向 delta，以及反例搜索结果。
5. 计算差异声明许可分数 P_s，包括可比较性分数、差异幅度分数、反证冲突分数、图像覆盖度和位置偏置惩罚。
6. 当 P_s 达到阈值时允许输出 s，并附带证据链；当可比较性不足或反证强时，将 s 降级为“不足以判断”或输出限定性回答。

输出：
最终答案；每条比较性陈述的许可/拒绝标签；对应跨图证据链；不可回答或不确定原因。

为什么不是简单组合：
核心不是“检索相关图 + VQA”或“caption 后比较”，而是在答案生成前引入一个显式的可比较性判定和差异声明许可门控。该门控把跨图对象对应、比较维度、反证搜索和回答许可绑定为同一技术动作。

可实验数据集：
MuirBench、Visual Haystacks、ReMI、BLINK、BLINK-Twice、CompareBench、ISVQA、CDQAG/QAG-360K、MIMIC-Diff-VQA、MIRB。

主要风险：
可比较性边权若只用现有 detector/embedding，容易被审查员认为是常规图匹配；需要强调“面向问答陈述许可”的流程闭环。实验上也需要证明它减少错误比较和错误变化声明，而不只是提高普通准确率。
```

```text
候选名称：
多图问答中的反证优先检索机制

解决的具体技术问题：
模型在多图比较时倾向于寻找支持答案的图像，而忽略其他图片中会推翻该答案的反例。

输入：
多图像集合、问题、候选答案、候选支持图像。

核心处理步骤：
1. 生成候选答案及其支持证据。
2. 将候选答案转换成可证伪视觉条件，例如“所有含 A 的图都有 B”“图 2 比图 1 多一个对象”。
3. 在未选图像和未选区域中检索反例证据。
4. 若找到反例，触发答案修正或拒答。

输出：
答案、支持证据、反证证据、修正记录。

为什么不是简单组合：
不是普通 self-check，而是把候选答案转换为视觉可证伪条件，再做跨图反证检索。

可实验数据集：
Visual Haystacks multi-needle、MuirBench unanswerable variants、ReMI、MIRB。

主要风险：
容易被认为是 RAG/self-check 的自然扩展；独立性弱于“差异声明许可”。
```

```text
候选名称：
比较维度自适应的多图最小证据集选择

解决的具体技术问题：
多图输入中相关图片数量和区域过多，模型受无关图干扰，导致比较问答错误。

输入：
图像集合、问题、候选比较维度、图像和区域特征。

核心处理步骤：
1. 判断问题属于数量、属性、空间、时间、状态变化等比较维度。
2. 为每种维度选择不同的证据粒度，例如数量用实例级，空间用关系级，状态变化用局部差异级。
3. 选择能覆盖问题约束的最小图像/区域集合。
4. 仅将最小证据集送入 VLM 或答案模块。

输出：
最小证据集、答案、证据选择理由。

为什么不是简单组合：
它不是固定 Top-K 检索，而是依据比较维度动态改变证据粒度和选择准则。

可实验数据集：
Visual Haystacks、MuirBench、CompareBench、ISVQA。

主要风险：
更像检索优化，容易被 Visual RAG 或 attention pruning 覆盖；技术效果也可能只表现为效率提升。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对候选 1：不是单纯把 VQA 放到多图场景，而是在多图回答前增加“比较性陈述是否被跨图证据许可”的判定环节。独立点应落在许可门控和证据链构造，而不是多图 VQA 场景。
  - 对候选 2：有风险。反证优先检索可以用于文本 RAG、事实核查和多图 VQA，若不限定视觉可证伪条件和跨图反证区域，容易被认为只是场景替换。
  - 对候选 3：有风险。最小证据集选择属于多图检索/压缩常规优化，需要更强的“比较维度-证据粒度”绑定。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 候选 1 的抗辩点：不是根据置信度阈值决定答不答，而是为每条比较性陈述构造跨图证据链，并检测该链是否满足可比较性、差异幅度、覆盖度和反证约束。CoT 只是文本推理，不能保证视觉重观察；Visual Haystacks 和 BLINK-Twice 的结果也说明简单长上下文、CoT 或 self-criticism 不足。
  - 候选 2 的风险较高，容易被攻击为“检索反例 + self-check”。需要将反证检索约束为视觉区域级、跨图条件级，才有防御空间。
  - 候选 3 容易被攻击为 RAG 的 Top-K 变体。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 候选 1 使用 grounding 作为证据单元，但技术动作不是 grounding 本身，而是判断两个或多个 grounded evidence 是否在问题指定维度下可比较，并据此许可或禁止输出比较性陈述。
  - 本轮不依赖 OCR 或图表解析。
  - 如果权利要求只写“检测目标、比较差异、回答问题”，会被组合掉；必须写成“候选陈述-跨图证据链-许可门控”的流程。

- 是否能被一篇或几篇论文自然组合推出？
  - Visual Haystacks 教会相关图检索，MuirBench 教会 answerable/unanswerable，CDQAG 教会变化 grounding，BLINK/CompareBench 教会比较失败现象。审查员可能认为组合这些论文即可得到候选 1。
  - 反驳空间在于：这些工作大多是 benchmark 或领域任务，没有提出“针对每条比较性答案陈述进行跨图可比较性许可”的统一机制。尤其是把可比较性边、差异方向、反证搜索和输出门控合并为回答许可条件，仍有可写性。

- 是否缺少可验证技术效果？
  - 可验证。指标不应只看 overall accuracy，还应看：
    - 错误比较性陈述率下降；
    - unanswerable / insufficient-evidence 样本上的错误作答率下降；
    - 多图位置扰动后的稳定性提升；
    - 证据链与人工标注区域/图像的匹配率；
    - 相比 caption-then-compare、multi-image direct prompting、visual RAG、CoT/self-check 的消融提升。

## 6. 本轮最佳候选

最佳候选：问题约束的跨图证据对齐与差异声明许可机制。

- 为什么选它：
  - 它正面对应多图/对比问答的核心失败：模型没有先证明“这些区域可以比较”，就输出比较结论。
  - 它具有明确技术闭环：问题解析、证据单元生成、跨图可比较性图、候选陈述证据链、许可分数、回答门控。
  - 它能覆盖多图比较、before-after、difference QA、change reasoning 和 unanswerable variants，而不是局限在医学、遥感或异常检测单一场景。
  - 它的实验效果可直接测量：减少错误变化声明和无证据比较声明。

- 为什么淘汰其他候选：
  - “反证优先检索机制”有价值，但和 RAG/self-check 的边界较薄，除非进一步绑定到候选 1 的许可分数中作为一个子模块。
  - “比较维度自适应的多图最小证据集选择”更像检索/压缩优化，容易被 Visual Haystacks/MIRAGE 或 attention pruning 自然覆盖，专利独立性较弱。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“针对候选比较性陈述生成跨图最小支持证据链，并基于可比较性、差异幅度和反证冲突计算差异声明许可分数，以控制该陈述是否进入图像问答答案”的动作。
  - 不要把独权写成“多图输入后比较差异并回答”，那会太宽且容易被现有 diff-VQA、change detection QA、visual RAG 组合击穿。

- 如果做实验，最快怎么证明：
  - 选 MuirBench 的 unanswerable variants、Visual Haystacks multi-needle、CompareBench 的空间/数量/时间比较、BLINK 的 visual correspondence/multi-view 子任务。
  - Baseline：direct multi-image prompting、caption-then-compare、visual RAG/MIRAGE-style retrieval、CoT/self-check。
  - 加一个轻量实现：用现成检测/分割或 VLM region proposal 生成证据单元，用 embedding + 问题词约束建跨图边，用规则许可分数控制输出。
  - 主要看三类指标：准确率、错误许可率、不可回答样本上的拒答/降级正确率。只要错误许可率显著下降，即使总体准确率提升不大，也能证明“差异声明许可”的技术效果。
