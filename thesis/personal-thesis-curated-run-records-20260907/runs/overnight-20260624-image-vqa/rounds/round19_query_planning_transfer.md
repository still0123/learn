# Round 19：数据库查询优化 / 证据查询计划迁移

## 1. 本轮方向

- 方向名称：数据库查询优化机制向图像问答证据选择迁移
- 检索范围：query planning、cost-based optimizer、join ordering、index selection、adaptive query processing、learned query optimizer、Visual RAG、active visual acquisition、region-level retrieval
- 目标问题：图像问答系统在回答前通常会做检索、裁剪、OCR、grounding、caption 或多图证据聚合，但多数方法只强调“取到相关证据”，缺少类似数据库优化器的证据获取顺序、成本预算、运行中反馈和停止机制。本轮目标是寻找一个不是普通“先检索再回答”的技术机制。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | SkinnerDB: Regret-bounded Query Evaluation via Reinforcement Learning | ACM TODS | 2021 | 不依赖静态统计或训练工作负载，在当前查询执行过程中切分小时间片，尝试不同 join order，并以执行进展反馈选择更优顺序；提出 regret-bounded execution criterion | 可迁移为 VQA 中“边取证边更新证据计划”的机制，避免一次性固定检索/裁剪顺序 | https://dl.acm.org/doi/fullHtml/10.1145/3464389 |
| 2 | POLAR: Adaptive and Non-invasive Join Order Selection via Plans of Least Resistance | VLDB / DuckDB Library | 2024 | 为左深 join pipeline 增加替代 join order，通过 regret-bounded tuple routing 找到并验证阻力最小计划；强调低侵入和有界开销 | 可迁移为在多个视觉证据路径之间做小批量探测，再把预算分配给“阻力最小”的证据路径 | https://duckdb.org/library/polar/ |
| 3 | Adaptive Join Decisions | Snowflake Engineering Blog | 2024 | 利用运行时 query execution feedback 在 broadcast join 与 hash-partitioned join 间自适应选择 | 对应 VQA 中根据早期视觉证据规模/歧义程度，动态决定是继续局部裁剪、OCR、对象检测还是直接回答 | https://www.snowflake.com/en/engineering-blog/query-acceleration-smarter-join-decisions/ |
| 4 | GenJoin: Conditional Generative Plan-to-Plan Query Optimizer that Learns from Subplan Hints | arXiv | 2025 | 将 query optimization 看成 plan-to-plan 生成任务，用 subplan hints 缩小搜索空间并生成更优计划 | 可迁移为从“问题谓词/已获证据”生成下一步视觉取证计划，而不是端到端一次生成答案 | https://arxiv.org/html/2411.04525v2/ |
| 5 | Utility-Oriented Visual Evidence Selection for Multimodal RAG | arXiv | 2026 | 将视觉证据选择定义为对输出分布的信息增益，而不是语义相关度；用 surrogate 估计证据 utility | 直接说明 Visual RAG 的痛点：相关性不等于对回答有用；但仍偏证据选择评分，缺少数据库式计划执行和自适应重规划 | https://arxiv.org/html/2605.13277v1 |
| 6 | RegionRAG: Region-level Retrieval-Augmented Generation for Visually-Rich Documents | arXiv | 2025 | 从文档级检索转向 region-level retrieval，动态组合显著 patch 成语义区域，减少无关上下文 | 说明 VQA/DocVQA 已经在做区域级证据检索；本轮创新应避开“区域检索本身”，转向区域证据的计划、排序和停止 | https://arxiv.org/html/2510.27261v1 |
| 7 | CMRAG: Co-modality-based document retrieval and visual question answering | arXiv | 2025 | 对文本段和图像区域分别建立 co-modality representation，再做跨模态聚合 | 证明多通道证据检索已较成熟；本轮不能只提出“文本+图像双路检索” | https://arxiv.org/html/2509.02123v1/ |
| 8 | AdaptVision: Efficient Vision-Language Models via Adaptive Visual Acquisition | arXiv | 2025 | 从低分辨率压缩视觉 token 开始，必要时调用 bbox/crop 工具获取额外视觉信息，并用奖励平衡准确性和效率 | 与本轮最接近：自适应获取视觉信息；但它更偏 token/工具使用效率，本轮可进一步强调问题谓词驱动的计划图、运行中重估和遗憾有界停止 | https://arxiv.org/html/2512.03794v1/ |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - Visual RAG 和 DocVQA 开始从“检索更多上下文”转向“选择对答案真正有用的视觉证据”，尤其是多图、多页、图表、文档场景。
  - 数据库优化侧持续关注 learned optimizer、join order、runtime feedback、adaptive query processing，因为静态估计在复杂查询上容易灾难性失误。
  - VLM 侧出现 adaptive visual acquisition、active view selection、region-level retrieval，说明“按需取证”已经成为效率和可靠性共同问题。

- 已经成熟、不能作为创新点的部分：
  - 单纯用 CLIP/embedding 检索图像或区域；
  - 对图像先做 OCR、caption、object detection，再把结果喂给 VLM；
  - 用置信度阈值决定是否继续检索；
  - 把 RAG 从文本换成图片；
  - 对候选区域做 top-k rerank；
  - 只说“根据问题选择重要区域”，没有明确成本模型、计划空间和运行中反馈。

- 仍有空白或可迁移空间的部分：
  - 把问题解析成可验证谓词后，建立视觉证据操作的计划图，而非一次性召回 top-k 证据。
  - 像 query optimizer 一样显式估计每个视觉操作的成本、选择率、证据收益和后续计划影响。
  - 在回答生成前按小步执行证据计划，并用每步证据对候选答案集合的收缩程度更新计划。
  - 设计“遗憾有界”或“预算有界”的继续取证/停止准则，使系统可解释地说明为什么不再看更多区域。

## 4. 候选创新点

```text
候选名称：
遗憾有界视觉证据查询计划器（Regret-bounded Visual Evidence Query Planner）

解决的具体技术问题：
图像问答系统在面对复杂问题时，常把全图、若干裁剪、OCR、检测框、caption 或检索图像一次性输入模型，导致无关视觉 token 过多、关键证据遗漏、推理成本不可控，并且无法解释证据获取顺序。该机制解决“下一步应该看哪个证据、用什么视觉操作看、什么时候停止”的计划问题。

输入：
原始图像或图像集合；自然语言问题；可用视觉操作集合（全图粗读、候选框检测、区域裁剪、OCR、局部 caption、属性识别、关系验证、相似区域检索等）；每类操作的成本先验；候选答案初始分布或候选答案集合；最大视觉预算。

核心处理步骤：
1. 将问题解析为谓词图：实体谓词、属性谓词、关系谓词、数量/比较谓词、文本读取谓词等。
2. 为每个谓词生成可执行证据操作节点，例如“读左上角文字”“验证红色物体是否在杯子右侧”“对候选区域做高分辨率裁剪”。
3. 为证据操作建立计划图：节点表示视觉操作，边表示操作依赖，状态记录已验证谓词、候选答案熵、剩余预算和未解释冲突。
4. 估计每个候选操作的单位收益：预期候选答案收缩量、预期冲突消除量、预期谓词覆盖增量，除以视觉 token/模型调用/OCR/检测成本。
5. 先执行少量低成本探测操作，观察其对候选答案分布和谓词置信区间的实际改变。
6. 用运行中反馈更新计划成本和收益估计：如果某区域没有信息，降低同类区域优先级；如果某谓词造成答案分歧，提升其依赖证据路径。
7. 按遗憾有界准则选择下一步：只有当当前最优未执行操作的预期收益超过“继续取证成本 + 当前答案风险下降阈值”时继续执行。
8. 当候选答案稳定、关键谓词覆盖达标、或继续取证的预期遗憾低于阈值时停止，并把已执行证据路径交给回答模块。

输出：
最终答案；已执行的证据计划序列；每步操作的成本、收益、覆盖谓词和是否触发重规划；停止原因。

为什么不是简单组合：
它不是“检索图像区域 + VQA”，而是在 VQA 前增加一个类似数据库 optimizer/executor 的计划层。创新动作集中在：问题谓词图到视觉操作计划图的转换、成本-收益估计、运行中反馈重规划、遗憾有界停止。该层决定证据获取顺序，而不是只对已取证据打分。

可实验数据集：
GQA、VQA v2、OK-VQA、A-OKVQA、TextVQA、DocVQA、ChartQA、InfographicVQA、MMDocRAG；也可构造多步区域证据子集，记录每题所需区域/操作数。

主要风险：
需要定义可复现实验指标；谓词解析错误会影响计划质量；如果只实现成 top-k region rerank，会被认为缺少实质区别；已有 adaptive visual acquisition 和 utility-based evidence selection 会构成近似现有技术，需要强调“计划图 + 运行反馈 + 停止准则”的组合技术动作。
```

```text
候选名称：
视觉谓词选择率估计器（Visual Predicate Selectivity Estimator）

解决的具体技术问题：
数据库 optimizer 依赖 cardinality/selectivity estimate；VQA 中也需要知道某个证据操作能排除多少候选答案，但现有 VQA 很少显式估计“视觉谓词选择率”。

输入：
问题解析出的谓词；候选答案集合；全图低成本特征；候选区域特征；历史题目中谓词验证结果。

核心处理步骤：
1. 将问题拆成实体、属性、关系、计数、文本、空间等谓词类型。
2. 对每个谓词估计验证成功概率、候选答案排除比例、误判风险和视觉操作成本。
3. 将高选择率低成本谓词优先放入证据计划。
4. 在执行后用实际候选收缩量更新估计器。

输出：
每个视觉谓词的选择率、成本、风险和推荐验证顺序。

为什么不是简单组合：
重点不是回答模型，而是建立 VQA 中的 selectivity/cardinality 类估计模块。

可实验数据集：
GQA、CLEVR、NLVR2、TextVQA、ChartQA。

主要风险：
单独作为专利可能偏“评分模型”；如果没有和计划执行/重规划绑定，容易被认为只是 attention/rerank 分数。
```

```text
候选名称：
索引提示式多模态证据访问方法（Index-hint Guided Multimodal Evidence Access）

解决的具体技术问题：
图像问答存在多种证据索引：对象框索引、OCR 文本索引、布局索引、区域 embedding 索引、图结构索引。不同问题适合不同索引，但现有系统通常固定检索路线。

输入：
问题；图像预处理索引集合；索引访问成本；候选答案类型。

核心处理步骤：
1. 根据问题类型生成 index hints，例如文本题优先 OCR 索引、空间关系题优先对象关系图索引、图表题优先坐标轴/单位索引。
2. 对多个索引访问计划做成本估计，选择低成本高覆盖路线。
3. 如果初始索引返回证据冲突，则切换到备用索引验证。

输出：
被访问的索引类型、证据片段和答案。

为什么不是简单组合：
试图迁移数据库 index selection；但技术动作更像路由器。

可实验数据集：
TextVQA、DocVQA、ChartQA、InfographicVQA。

主要风险：
容易被说成规则化 query router 或多路检索融合，不如“遗憾有界计划器”有独立技术高度。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对“视觉谓词选择率估计器”和“索引提示式访问方法”的攻击较强：它们分别像把数据库 selectivity 和 index hint 换到 VQA 场景。
  - 对“遗憾有界视觉证据查询计划器”的攻击较弱一些，因为其技术对象不是数据库查询本身，而是 VQA 中的视觉操作序列；关键在于把 answer uncertainty、predicate coverage、visual token cost 和 evidence conflict 统一进计划执行状态。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 如果只做 top-k evidence selection，就是 RAG。
  - 如果只让模型解释“我还需要看哪里”，就是 CoT/tool-use。
  - 如果只在置信度低时继续裁剪，就是阈值策略。
  - 需要在权利要求中限定：先生成视觉证据操作计划图；每步执行后计算候选答案集合收缩量或谓词覆盖增量；基于实际收益重估未执行节点；使用遗憾/预算准则停止。这些动作超出普通 RAG 和 self-check。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 有风险，因为证据操作节点可能调用现有 grounding、OCR、region caption。
  - 反驳点应放在“操作调度层”而非底层感知模型：本方法不声称发明 OCR 或 grounding，而是发明面向回答任务的证据访问计划、反馈重规划和停止方法。

- 是否能被一篇或几篇论文自然组合推出？
  - SkinnerDB/POLAR 提供数据库自适应执行思想，Utility-Oriented Visual Evidence Selection 提供视觉证据 utility，AdaptVision 提供按需视觉获取。这三者组合会形成强近似。
  - 需要拉开距离：不是简单把 utility 分数用于选择证据，而是把视觉操作建成具有依赖关系的计划图，并引入类似 join order 的“先验证哪个谓词会影响后续证据空间”的顺序优化。专利文本必须强调运行中反馈改变后续计划，不只是预排序。

- 是否缺少可验证技术效果？
  - 可验证。至少有四类指标：
    1. 同等准确率下减少视觉 token、裁剪次数或模型调用次数；
    2. 同等预算下提高复杂问题准确率；
    3. 关键证据召回率/谓词覆盖率提升；
    4. 遇到干扰区域或错误 OCR 时，答案稳定性提高。
  - 风险在于需要设计“证据计划质量”标注或代理指标。最快实验可用现有区域标注/scene graph/OCR box 近似。

## 6. 本轮最佳候选

本轮只保留：遗憾有界视觉证据查询计划器。

- 为什么选它：
  - 它把数据库查询优化中最有价值的部分抽象成 VQA 可落地的技术动作：计划空间、成本估计、执行反馈、重规划、停止准则。
  - 它不是把数据库术语贴到 VQA 上，而是解决 VQA 系统真实存在的问题：复杂问题中证据很多，但取证顺序和停止理由不可控。
  - 它能兼容现有 VLM、OCR、grounding、Visual RAG，不依赖发明新基础模型，适合快速实验和专利撰写。

- 为什么淘汰其他候选：
  - “视觉谓词选择率估计器”更像一个打分/预测子模块，技术效果需要依赖上层计划器才能显现，单独成案显得薄。
  - “索引提示式多模态证据访问方法”容易被审查员理解为多路检索路由或规则选择，和现有 RAG/router/index selection 组合距离过近。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“基于问题谓词图生成视觉证据操作计划图，并在逐步执行视觉操作后依据实际候选答案收缩量、谓词覆盖增量和操作成本重估未执行操作，按照遗憾有界或预算有界停止准则输出答案”的动作。
  - 独权不应写成“根据问题检索相关图像区域并回答”，应写成：
    1. 解析问题得到谓词图；
    2. 将谓词映射为多个具有依赖关系的视觉证据操作节点；
    3. 为节点估计预期收益和执行成本；
    4. 执行一个或多个低成本探测节点；
    5. 根据实际证据反馈更新未执行节点的收益/成本；
    6. 选择下一节点或停止；
    7. 基于已执行证据路径生成答案和证据说明。

- 如果做实验，最快怎么证明：
  - 数据集：优先 GQA 或 TextVQA。GQA 有结构化语义和关系问题，适合谓词分解；TextVQA 有 OCR 操作成本差异，适合证明“不是全量 OCR/全图输入”。
  - Baseline：
    - 全图直接 VLM；
    - 固定 top-k 区域输入；
    - relevance-only region rerank；
    - confidence-threshold adaptive crop；
    - utility-only evidence selection。
  - 指标：
    - Accuracy / EM；
    - 平均视觉 token 数；
    - 平均工具调用次数；
    - 每题执行证据节点数；
    - 关键证据召回率；
    - accuracy-cost Pareto 曲线。
  - 最小原型：
    - 用现成 detector/OCR/region proposal 生成候选证据；
    - 用 LLM 或规则把问题拆成谓词；
    - 用候选答案熵下降或答案 logit margin 改变量近似证据收益；
    - 执行 3-5 步预算内计划；
    - 对比固定 top-k 和置信度阈值策略。
