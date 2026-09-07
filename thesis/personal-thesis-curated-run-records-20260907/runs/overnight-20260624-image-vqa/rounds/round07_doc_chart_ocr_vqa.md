# Round 07：文档图像 / 图表 / OCR VQA

## 1. 本轮方向

- 方向名称：文档图像、图表、OCR 证据冲突下的图像问答
- 检索范围：DocVQA、TextVQA、ChartQA、InfographicVQA、MMDocRAG、layout understanding、table/chart reasoning、OCR evidence conflict、document perception-cognition consistency
- 目标问题：寻找一个不是“OCR + VQA + RAG”堆叠的技术机制，使图像问答系统在文档、图表、信息图等文字密集图像中，能处理 OCR 文本、视觉布局、图表结构、页面上下文之间的冲突，并输出可验证答案。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | DocVQA: A Dataset for VQA on Document Images | WACV | 2021 | 构建 12K+ 文档图像和 50K 问题，指出模型在需要理解文档结构的问题上仍明显落后人类 | 文档图像问答基础基准，证明结构理解不是普通 OCR 可替代 | https://arxiv.org/abs/2007.00398 |
| 2 | M4C: Iterative Answer Prediction with Pointer-Augmented Multimodal Transformers for TextVQA | CVPR | 2020 | 用多模态 Transformer 融合问题、视觉区域、OCR token，并通过 pointer 逐步复制 OCR token 生成答案 | TextVQA 早期强基线，代表“识别文字并复制答案”的成熟路线 | https://ar5iv.labs.arxiv.org/html/1911.06258 |
| 3 | InfographicVQA | WACV | 2022 | 数据集要求同时理解文本、布局、图形元素、数据可视化，并包含基础推理和算术问题 | 说明信息图问答的难点是多类证据联合推理，不是单一文本识别 | https://doi.org/10.1109/WACV51458.2022.00264 |
| 4 | ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning | ACL Findings / arXiv | 2022 | 包含人工问题和摘要生成问题，要求视觉定位、数值读取、比较、聚合等逻辑/算术操作 | 图表问答核心基准，推动“图表转表 + 推理”路线 | https://ar5iv.org/abs/2203.10244 |
| 5 | Hierarchical Multimodal Transformers for Multi-Page DocVQA | arXiv / ICDAR 相关方向 | 2023 | 将单页 DocVQA 扩展到多页，采用层级 Transformer 汇总每页信息并定位答案页 | 代表多页文档问答中“先找页、再回答”的层级路线 | https://www.arxiv-vanity.com/papers/2212.05935/ |
| 6 | Analyzing the Efficacy of an LLM-Only Approach for Image-based Document Question Answering | arXiv | 2023 | 将 OCR 文本按阅读顺序序列化输入 LLM，分析视觉编码器、布局、语言模型各自贡献 | 说明许多 DocVQA 题可被文本序列化解决，也暴露真正创新必须避开单纯 prompt/serialization | https://ar5iv.org/html/2309.14389 |
| 7 | Layout and Task Aware Instruction Prompt for Zero-shot Document Image Question Answering | arXiv | 2023 | 用空格、换行恢复 OCR 文档布局，让指令模型零样本理解文档 | 代表 layout-aware prompt 路线，容易成为审查员组合对比文献 | https://www.arxiv-vanity.com/papers/2306.00526/ |
| 8 | OCRBench: On the Hidden Mystery of OCR in Large Multimodal Models | arXiv | 2023/2024 | 汇集 29 个文本相关视觉任务，评估 LMM 的 OCR、TextVQA、DocVQA、KIE 能力 | 证明 OCR 能力已成为通用多模态模型常规评测，不能单独作为创新点 | https://arxiv.org/html/2305.07895 |
| 9 | Adversarial Training with OCR Modality Perturbation for Scene-Text VQA | arXiv | 2024 | 在 OCR embedding 上做对抗扰动，并加入空间感知自注意力，提升 OCR 错误容忍 | 代表“增强 OCR 噪声鲁棒性”的直接路线 | https://arxiv.org/html/2403.09288 |
| 10 | LayTextLLM: A Bounding Box is Worth One Token | OpenReview / ICLR submission | 2024/2025 | 将每个文本框投影成单个 bbox embedding 并与文本交错输入 LLM，降低布局序列长度 | 代表“布局框 token 化 + LLM”的成熟组合方向 | https://openreview.net/forum?id=lFijzkTUNB |
| 11 | Is Cognition Consistent with Perception? | arXiv / OpenReview | 2025 | 定义文档理解中的认知-感知知识冲突，发现 MLLM 的答案与 OCR/视觉感知常不一致，并用一致性微调缓解 | 与本轮最相关：它指出答案和可感知证据不一致是独立问题 | https://arxiv.org/html/2411.07722 |
| 12 | DocVXQA: Context-Aware Visual Explanations for Document QA | ICML | 2025 | 学习可解释热力图，使 DocVQA 答案具备上下文充分且紧凑的视觉解释 | 说明“答案 + 证据区域”正在成为 DocVQA 热点 | https://icml.cc/virtual/2025/poster/43613 |
| 13 | MMDocRAG: Benchmarking Retrieval-Augmented Multimodal Generation for Document QA | NeurIPS Datasets & Benchmarks | 2025 | 4,055 个专家标注 QA，包含多页、跨模态证据链，并评估多模态 quote selection | 代表多页多模态 RAG 评测趋势，强调证据选择和整合仍困难 | https://openreview.net/forum?id=W4b3v9jx1p |
| 14 | MHier-RAG: Multi-Modal RAG for Visual-Rich Document QA via Hierarchical and Multi-Granularity Reasoning | arXiv | 2025 | 建立页内扁平块和跨页拓扑块，做多粒度检索和重排序 | 代表“层级索引 + 多模态 RAG”的强对比文献 | https://arxiv.org/html/2508.00579 |
| 15 | ChartQAPro | arXiv | 2025 | 包含 reasoning、conversational、multiple-choice、hypothetical、fact-checking 五类问题 | 说明图表问答正在从数值抽取走向事实核验和开放复杂推理 | https://arxiv.org/html/2504.05506 |
| 16 | ChartMind | arXiv | 2025 | 面向复杂真实图表 QA，覆盖多语种、多图表类型、开放文本输出，并提出上下文提取框架 | 说明图表问答难点已转向复杂上下文抽取、噪声控制和开放回答 | https://arxiv.org/html/2505.23242 |
| 17 | InfoChartQA | arXiv | 2025 | 构造信息图表与普通图表成对样本，分析设计元素、文本顺序、视觉连接对 MLLM 的影响 | 说明信息图中的视觉修饰会改变模型答案，适合构造冲突评测 | https://arxiv.org/html/2505.19028 |
| 18 | BBox-DocVQA | arXiv | 2025 | 为 DocVQA 标注显式 bbox 证据，覆盖单/多区域和单/多页场景 | 代表 grounded DocVQA 的新趋势，但主要是数据和定位，不直接解决证据冲突裁决 | https://arxiv.org/html/2511.15090 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 文档 VQA 从单页、单答案抽取，转向多页、多区域、跨模态证据链。
  - 图表 VQA 从表格数值读取，转向复杂视觉编码、事实核验、假设问题、开放答案和鲁棒性。
  - 信息图/文档图像中，文字、布局、图形元素、颜色、图例、表格和页面上下文都会影响答案。
  - 多模态 RAG 已开始关注 evidence selection、quote selection、grounding verification，而不是只检索文本 chunk。
  - MLLM 的感知结果与认知回答不一致已被单独提出，说明“答案是否被图像证据支持”是热点问题。

- 已经成熟、不能作为创新点的部分：
  - OCR 后把文本输入 LLM 或 VQA 模型。
  - OCR token 复制、pointer decoder、动态词表。
  - 将 bbox/布局坐标编码为 embedding 或用空格换行恢复布局。
  - 图表转表，再用 LLM/程序做数值推理。
  - 多页文档的页级检索、层级索引、多粒度 RAG。
  - 让模型输出热力图、bbox 或自然语言 rationale。
  - 用置信度阈值决定是否拒答。

- 仍有空白或可迁移空间的部分：
  - 多类证据互相冲突时的裁决机制仍不成熟。例如 OCR 文本显示一个数，图表柱高支持另一个数，标题/脚注又改变单位。
  - 现有方法常评估最终答案准确率，但较少把“候选答案-证据声明-冲突关系-裁决动作”显式建模。
  - 文档和图表问题中存在大量快速可造的冲突样本：OCR 错字、单位缩放、表格汇总行、图例颜色错配、设计型图标误导、跨页引用冲突。
  - 可以不训练大模型，只在推理侧构建候选答案的证据冲突图，适合快速实验和专利化描述。

## 4. 候选创新点

```text
候选名称：跨模态证据冲突图驱动的文档图像问答裁决方法
解决的具体技术问题：
在文档、图表、信息图问答中，OCR 文本、布局邻接、图表视觉读数、页面上下文、答案生成模型可能给出互相矛盾的证据。现有方法通常直接融合这些证据生成答案，或只用置信度/自检判断答案可靠性，导致错误证据被语言模型平滑掩盖。本机制要解决的是：候选答案出现前后，如何把不同来源证据转化为可比较的声明，并基于冲突结构选择答案、修正答案或拒答。
输入：
图像或多页文档图像；自然语言问题；OCR token 及其 bbox/置信度；页面布局块；可选图表结构化元素，如坐标轴、图例、数据点、单位；一个或多个基础 VQA/VLM 生成的候选答案。
核心处理步骤：
1. 问题证据需求解析：将问题拆成答案类型、目标对象、约束条件、所需证据类型，例如文本字段、表格单元、图表读数、单位换算、跨页引用。
2. 候选答案生成：由基础 VQA/VLM、OCR 检索、图表解析器分别产生候选答案集合，而不是直接采用最高概率答案。
3. 证据声明抽取：对每个候选答案生成若干声明三元组，例如“候选 A 被 OCR token T 支持”“候选 A 与图例颜色 L 一致”“候选 A 的单位来自脚注 U”“候选 A 的数值与柱高估计相差 d”。
4. 冲突边构建：在声明之间建立 contradiction、support、unit-mismatch、layout-detached、chart-text-mismatch、page-reference-mismatch 等边，并为每类边计算可解释分数。
5. 冲突裁决：不是简单投票，而是按问题证据需求为不同证据类型分配优先级。例如“according to chart trend”优先视觉曲线/柱高，“what is printed”优先 OCR token，“total revenue”要求表格汇总行和单位一致。
6. 答案许可输出：若候选答案的关键证据闭包无高强度冲突，则输出答案和最小证据集；若存在关键冲突但可由单位/别名/阅读顺序解释，则输出修正答案；若关键冲突无法消解，则输出拒答或低置信答案，并返回冲突原因。
输出：
最终答案；支持该答案的最小证据单元；被压制的竞争候选；冲突类型；裁决原因。
为什么不是简单组合：
该机制的核心不是 OCR、图表解析或 RAG 本身，而是把不同证据源统一成“可裁决声明图”，再依据问题证据需求动态改变证据优先级。它显式处理证据冲突，不是把证据拼接给 LLM，也不是用置信度阈值后验过滤。
可实验数据集：
DocVQA、InfographicVQA、ChartQA、ChartQAPro、InfoChartQA、MMDocRAG、BBox-DocVQA。最快实验可在 ChartQA/InfographicVQA 上人工或脚本构造 OCR 错字、单位扰动、图例颜色扰动、表格汇总行冲突样本。
主要风险：
现有 C&P consistency、DocVXQA、MMDocRAG、BBox-DocVQA 已覆盖“感知-认知一致性”“可解释证据”“grounded QA”。必须强调本机制的冲突边类型、证据需求驱动优先级和答案许可动作，否则容易被认为是 evidence grounding + self-check。
```

```text
候选名称：单位-比例尺守恒的图表问答答案修正方法
解决的具体技术问题：
图表问答中，模型常正确识别数值却忽略单位、缩放、百分比/绝对值、千/百万等标注，导致答案数值量级错误。
输入：
图表图像、问题、OCR 轴标签/标题/脚注、图例、候选答案。
核心处理步骤：
1. 抽取问题中的目标指标和期望单位。
2. 从标题、坐标轴、脚注、表注抽取单位声明。
3. 将候选答案映射到可能的单位空间。
4. 检查视觉读数、文本单位、问题单位之间是否守恒。
5. 对可解释单位差异做换算，对无法解释的差异拒答。
输出：
单位一致的答案和单位来源。
为什么不是简单组合：
它把单位作为答案许可条件，而不只是读图或 OCR。
可实验数据集：
ChartQA、ChartQAPro、ChartMind、InfoChartQA。
主要风险：
容易被认为是图表解析后的规则校验，技术面偏窄；如果独立申请，创造性可能弱。
```

```text
候选名称：阅读顺序反证采样的 DocVQA 鲁棒答题方法
解决的具体技术问题：
文档问答中，OCR reading order 错误会导致 LLM 将相邻但无关字段拼接，产生看似合理的错误答案。
输入：
文档图像、OCR token/bbox、问题、候选答案。
核心处理步骤：
1. 生成多个可能阅读顺序，而非单一序列化文本。
2. 对每个阅读顺序生成候选答案。
3. 找出答案对阅读顺序扰动敏感的 token 区间。
4. 回到二维布局验证敏感区间是否在同一字段、表格行或语义块。
5. 仅在答案对合理阅读顺序稳定且布局验证通过时输出。
输出：
答案、敏感字段、布局稳定性评分。
为什么不是简单组合：
它用 reading order 反事实扰动定位潜在误读，而不是设计一个更好的序列化 prompt。
可实验数据集：
DocVQA、MP-DocVQA、DUDE、InfographicVQA。
主要风险：
与已有 reading-order serialization 和 layout prompt 文献距离较近，审查时可能被认为是常规鲁棒性增强。
```

```text
候选名称：信息图设计元素降权的视觉问答证据净化方法
解决的具体技术问题：
信息图中的图标、装饰性颜色、插画和视觉隐喻会误导 MLLM，使其把设计元素当作数据证据。
输入：
信息图图像、问题、OCR、候选视觉元素、候选答案。
核心处理步骤：
1. 将图像块分为数据承载元素、标签元素、装饰/隐喻元素。
2. 对每个候选答案记录其依赖的视觉元素类型。
3. 若答案主要依赖装饰/隐喻元素而缺少文本或数据映射支持，则降权。
4. 若问题明确询问设计元素，则反向提升相关元素。
输出：
净化后的答案和设计元素依赖报告。
为什么不是简单组合：
它把信息图中的“视觉设计是否有证据资格”作为显式判定对象。
可实验数据集：
InfographicVQA、InfoChartQA。
主要风险：
元素分类本身难界定，容易变成视觉分割/分类常规任务；实验构造稍慢。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 攻击：把普通多模态冲突检测放到 DocVQA/ChartQA 场景，可能只是应用领域替换。
  - 应对：独立权利要求不能写成“用于文档图像的冲突检测”。必须限定文档/图表特有的冲突边，如 unit-mismatch、layout-detached、chart-text-mismatch、page-reference-mismatch，并限定“问题证据需求驱动的证据优先级裁决”。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 攻击：先生成答案再检查证据，很像 self-check；多源证据也像 RAG。
  - 应对：本方案不依赖自然语言自我反思，也不以检索分数或置信度为核心。它要求把候选答案对应到结构化证据声明，并根据声明图中的冲突边执行答案许可、修正或拒答。技术效果是减少“高置信但证据矛盾”的错误。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 攻击：OCR、bbox grounding、chart-to-table、layout encoder 都已有，把它们接起来缺少创造性。
  - 应对：这些只作为输入证据源。创新点应落在证据冲突图的构建和裁决规则：同一候选答案必须经过“声明抽取-冲突边计算-证据需求优先级-答案许可”的闭环。尤其强调不同问题类型下证据优先级可变，而不是固定加权融合。

- 是否能被一篇或几篇论文自然组合推出？
  - 攻击路径 1：C&P consistency 论文指出认知-感知冲突，DocVXQA 输出解释区域，MMDocRAG 做证据选择，组合后可得到答案证据一致性检查。
  - 攻击路径 2：ChartQA/ChartMind 已做图表上下文抽取，OCRBench/ATS 已处理 OCR 噪声，组合后可做鲁棒图表问答。
  - 应对：现有文献多是训练一致性、解释热力图、检索 evidence 或 OCR 鲁棒性；它们没有把候选答案间的多类冲突声明建图，也没有将“问题证据需求”作为裁决优先级输入。专利撰写要避免泛泛声称“提高一致性”，而要抓住结构化冲突边和答案许可动作。

- 是否缺少可验证技术效果？
  - 攻击：如果只输出解释，无法证明比原模型好。
  - 应对：可以快速构造冲突集验证：在 ChartQA/InfographicVQA 中注入 OCR 错字、单位扰动、图例颜色替换、表格汇总行冲突，比较基础 VLM、RAG 拼接、self-check 与本方法在冲突样本上的准确率、拒答准确率、证据一致率。无需训练大模型，实验快。

## 6. 本轮最佳候选

本轮最佳候选：跨模态证据冲突图驱动的文档图像问答裁决方法。

为什么选它：

- 它正好卡在当前热点空白：DocVQA/ChartQA/MMDocRAG 已经有 OCR、布局、图表解析、RAG、grounding，但多证据冲突时“凭什么信哪一个”仍未被充分机制化。
- 它有明确技术动作：问题证据需求解析、候选答案生成、证据声明抽取、冲突边构建、证据优先级裁决、答案许可输出。
- 它实验快：不需要训练模型，可用现成 VLM/OCR/chart parser 产出候选，再在已有数据集上构造冲突扰动。
- 它比单纯图表单位校验或 reading-order 鲁棒性更宽，但仍然能落到文档/图表特有证据冲突，不至于泛化成普通 self-check。

为什么淘汰其他候选：

- 单位-比例尺守恒方法太窄，容易被认为是图表解析后的规则校验。
- 阅读顺序反证采样与已有 layout prompt、LLM-only DocVQA、阅读顺序序列化研究过近，需要更多细节才能避免显而易见。
- 信息图设计元素降权有新意，但依赖装饰/数据元素分类，实验闭环比冲突图更慢，且专利边界不如“证据冲突裁决”清晰。

如果写专利，独立权利要求应该抓住哪个技术动作：

- 抓住“针对候选答案构建跨模态证据声明图，并根据问题证据需求对冲突边进行裁决以输出答案许可状态”的动作。
- 核心限定建议：
  - 对问题解析得到至少一种证据需求类型；
  - 从 OCR 文本、布局块、图表结构、视觉区域、页面上下文中为候选答案生成证据声明；
  - 在证据声明之间建立至少包括文本-图表不一致、单位不一致、布局脱离、跨页引用不一致之一的冲突边；
  - 根据证据需求类型调整不同冲突边或证据源的优先级；
  - 输出答案、修正答案或拒答，并输出最小支持证据和冲突原因。

如果做实验，最快怎么证明：

- 数据：选 ChartQA + InfographicVQA 各 200-500 个样本，优先选数值、单位、图例、表格、标题/脚注相关问题。
- 扰动：构造四类冲突版本：
  - OCR 字符扰动：把关键数字/实体 OCR 文本改错，但图像或结构读数保持正确。
  - 单位扰动：在标题、轴标签、脚注中制造千/百万、百分比/绝对值冲突。
  - 图例颜色扰动：交换图例颜色或系列名称，制造 chart-text mismatch。
  - 布局扰动：打乱 OCR reading order 或把相邻字段拼接，制造 layout-detached 错误。
- 对比：
  - 基础 VLM 直接回答；
  - OCR 文本 + 图像拼接回答；
  - RAG/检索证据拼接回答；
  - 让 VLM 自检答案是否由图像支持；
  - 本方法的证据冲突图裁决。
- 指标：
  - 原始准确率；
  - 冲突样本准确率；
  - 应拒答样本的拒答准确率；
  - 答案-证据一致率；
  - 冲突类型定位准确率。
