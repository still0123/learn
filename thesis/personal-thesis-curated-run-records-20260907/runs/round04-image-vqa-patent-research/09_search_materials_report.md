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
