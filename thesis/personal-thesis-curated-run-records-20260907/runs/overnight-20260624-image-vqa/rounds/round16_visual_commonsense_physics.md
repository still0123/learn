# Round 16：视觉常识 / 物理合理性方向

## 1. 本轮方向

- 方向名称：视觉常识与物理合理性约束下的图像问答回答许可机制
- 检索范围：visual commonsense reasoning、physical plausibility、affordance、scene graph reasoning、counter-commonsense image/video QA、VLM hallucination mitigation、unanswerable VQA。
- 目标问题：当图像表面事实与常识或物理先验冲突时，图像问答系统如何判断一个解释性回答是允许给出、必须限定、还是应当阻断，而不是直接用语言先验补全一个听起来合理但未被图像支持的解释。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | From Recognition to Cognition: Visual Commonsense Reasoning / VCR | CVPR / arXiv | 2019 | 将视觉问答扩展为“回答 + rationale”，强调人物意图、动作、关系等高阶常识推断，并用 adversarial matching 降低语言偏置。 | VCR 是视觉常识问答的经典源头，但更关注选择正确 rationale，不直接处理图像事实与常识冲突时的拒答或许可。 | https://www.arxiv-vanity.com/papers/1811.10830/ |
| 2 | Do Vision-Language Transformers Exhibit Visual Commonsense? An Empirical Study of VCR | ACM MM | 2023 | 系统分析 VL Transformers 在 VCR 上的语言偏置、预训练增益有限、object-tag correlation 等问题。 | 说明“VCR 高分”不等价于真正视觉常识；创新不能只是把 VCR 数据拿来微调。 | https://dl.acm.org/doi/abs/10.1145/3581783.3612395 |
| 3 | HaloQuest: A Visual Hallucination Dataset for Advancing Multimodal Reasoning | arXiv | 2024 | 构造包含 false premises、insufficient contexts、visual challenges 的 VQA 数据，并用 synthetic image 扩展幻觉诱发样本。 | 与“该不该回答”直接相关，但核心是数据集与评测，不是回答许可算法。 | https://arxiv.org/html/2407.15680v1 |
| 4 | Eyes Can Deceive: Benchmarking Counterfactual Reasoning Capabilities of MLLMs / CFMM | arXiv | 2024 | 构造多模态反事实问题，发现 MLLM 倾向相信图像表面内容而忽略问题中的反事实前提。 | 提醒冲突不只有“常识否定图像”，也有“问题前提要求临时改写图像事实”。 | https://arxiv.org/html/2404.12966v3 |
| 5 | Unified Triplet-Level Hallucination Evaluation for Large Vision-Language Models / Tri-HE | arXiv | 2025 | 将 LVLM 输出解析为 object / relation triplets，并用 NLI 与 LLM judge 判断对象和关系幻觉。 | 关系级幻觉与物理合理性强相关；可作为候选机制中的结构化事实核验模块。 | https://arxiv.org/html/2410.23114v3 |
| 6 | CoRGI: Verified Chain-of-Thought Reasoning with Post-hoc Visual Grounding | arXiv | 2025 | 将 CoT 拆成步骤声明，逐步寻找视觉证据，过滤或修正未被图像支持的推理步骤。 | 证明“逐步解释必须被图像证据复核”是明确趋势，但若只照搬会被打成 CoT + grounding。 | https://arxiv.org/html/2508.00378v2/ |
| 7 | VisionTrap: Unanswerable Questions On Visual Data | arXiv | 2025 | 针对混合实体、非现实图像、不存在人物等构造不可回答问题，评估模型是否知道拒答。 | 与“常识冲突时阻断解释性回答”高度相关，但偏 benchmark，不提供细粒度许可规则。 | https://arxiv.org/html/2507.17262v1/ |
| 8 | VideoHallu: Evaluating and Mitigating Multi-modal Hallucinations on Synthetic Video Understanding | NeurIPS / OpenReview | 2025 | 用生成视频构造物理和常识违反样本，负控制测试 VLM 是否识别异常，并探索基于负样本的后训练。 | 虽然是视频，但“负控制样本 + 违反物理/常识检测”可以迁移到图像问答。 | https://openreview.net/forum?id=NoC9HT7Kf7 |
| 9 | PhysBench: Benchmarking and Enhancing VLMs for Physical World Understanding | ICLR | 2025 | 覆盖物体物理属性、物体关系、物理场景理解、物理动态四大类，评测 VLM 物理世界理解。 | 给出可实验的物理理解类别，但核心是 benchmark 和 PhysAgent，不是 VQA 回答许可。 | https://physbench.github.io/ |
| 10 | Affordance-R1: Reinforcement Learning for Generalizable Affordance Reasoning in MLLM | arXiv | 2025 | 用 affordance-centric reasoning data 和 GRPO 奖励学习可供性 grounding 与推理。 | 可供性是“图像中动作/用途是否合理”的关键证据，但本轮创新不能只做机器人 affordance。 | https://arxiv.org/html/2508.06206v3 |
| 11 | A Study of Commonsense Reasoning over Visual Object Properties / OPTICS-CNT, OPTICS-CMP | arXiv | 2025/2026 | 以对象属性、推理层级、图像类型构建对象属性常识 VQA，发现 VLM 在物理和功能属性、反事实推理上明显弱。 | 可作为快速实验数据源，验证物理/功能属性推断是否被正确许可。 | https://arxiv.org/html/2508.10956v2 |
| 12 | PAC Bench: Do Foundation Models Understand Prerequisites for Executing Manipulation Policies? | arXiv / project | 2025 | 从 property、affordance、constraint 三类任务评估基础模型是否理解任务执行前提，如稳定性、可达性、可抓取性。 | 提供“属性-可供性-约束”三分框架，可迁移为图像问答中的物理许可类别。 | https://pacbench.github.io/ |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 从“能否回答常识题”转向“回答是否被图像证据约束”。VCR 时代关注 answer/rationale 选择，近两年 HaloQuest、VisionTrap、VideoHallu、PhysBench 更关心模型是否会在证据不足、反常识、物理异常场景中继续给出貌似合理的解释。
  - 从对象级幻觉转向关系级、动作级、物理约束级幻觉。Tri-HE 明确指出 relation hallucination 需要单独评估；PAC Bench、Affordance-R1、BOP-Ask 类工作也说明仅识别物体不足以判断动作是否可执行、关系是否物理可行。
  - 从“生成更多 CoT”转向“验证推理步骤”。CoRGI、REVERSE、HaloQuest 等都在说明，解释性文本本身会漂移，必须把声明拆解后复核。
  - 负控制和反常识样本成为关键评测工具。VideoHallu 和 VisionTrap 都强调通过不可能、混合、不可回答样本暴露模型的语言先验依赖。

- 已经成熟、不能作为创新点的部分：
  - 单纯说“引入常识知识库辅助 VQA”已经很旧，OK-VQA/A-OKVQA、知识图谱增强、GraphVis 类路线都有大量已有工作。
  - 单纯做“VQA + CoT + self-check”风险很高，CoRGI 已经把 post-hoc visual grounding 做得很接近。
  - 单纯做“用 scene graph 检查回答对象/关系是否存在”也不够新，PROVE、Tri-HE 已经覆盖 scene graph / triplet verification。
  - 单纯做“物理常识 benchmark”也不适合专利创新，PhysBench、PAC Bench、OPTICS、VideoHallu、VisionTrap 都在快速填坑。
  - 单纯阈值化置信度或让模型回答“不确定”容易被认为是 selective answering / abstention 常规方案。

- 仍有空白或可迁移空间的部分：
  - 多数方法检查“回答是否符合图像”，但较少明确区分三类声明：可直接由图像证明的事实、只能由常识推断的解释、与图像事实或物理约束冲突的推断。
  - 现有 grounding 往往只问“证据是否存在”，但没有把“常识前提在本图中是否被破坏”作为单独的许可条件。例如图像中杯子漂浮、刀柄断裂、人物姿态异常时，常规 affordance 或 commonsense answer 应降低许可。
  - 现有 unanswerable VQA 更偏数据集与评测；缺少一个可嵌入任意 VLM 推理流程的“常识声明许可层”，输出允许、限定、阻断和需要反问的状态。
  - 图像问答中的物理合理性可以从机器人 affordance 迁移，但不必进入机器人控制，只需判断某个动作/用途/因果解释在当前图像中是否满足物体属性、接触关系、支撑关系、可达性等前提。

## 4. 候选创新点

```text
候选名称：反常识冲突感知的回答许可门控
解决的具体技术问题：
当图像中存在违反常识或物理约束的局部现象时，VQA 模型容易沿用语言先验给出正常世界解释，例如“杯子在桌上所以能稳定放置”“人拿着刀所以正在切菜”。本机制判断候选回答中的解释性声明是否需要被许可、限定或阻断。
输入：
图像、问题、候选回答、候选回答拆解出的声明集合、图像事实 triplets、常识/物理约束模板集合。
核心处理步骤：
1. 将候选回答拆成原子声明，并标注声明类型：图像事实声明、物体属性声明、关系/接触声明、动作可供性声明、因果/意图解释声明。
2. 从图像中抽取对象、属性、空间关系、接触/支撑关系、异常关系，形成图像事实图。
3. 对每条解释性声明生成其最小常识前提集合，例如“能倒水”需要容器完整、开口朝上/可倾倒、液体或水源存在；“能坐”需要支撑面、承重、姿态兼容。
4. 将前提集合与图像事实图匹配，得到三类状态：已满足、未知、被图像反证。
5. 若关键前提被反证，则阻断该解释性声明；若关键前提未知，则要求回答限定为“图像无法确认”；若直接事实满足但常识异常存在，则允许事实回答但禁止正常世界因果解释。
6. 生成最终回答许可标签：ALLOW、QUALIFY、BLOCK、ASK_CLARIFICATION，并给出被触发的前提和反证证据。
输出：
带许可标签的最终回答、被阻断/限定的声明列表、对应图像证据或反证前提。
为什么不是简单组合：
不是先回答再 self-check，而是把“常识前提是否在当前图像中被破坏”作为独立许可变量；核心技术动作是从解释性声明反推出最小物理/可供性前提，并用图像事实图判断前提状态。
可实验数据集：
VisionTrap、HaloQuest、PhysBench、OPTICS-CNT/OPTICS-CMP、PAC Bench constraint images、VCR rationale 子集，以及自建小规模反常识图像问答集。
主要风险：
需要稳定抽取图像事实图；常识前提模板覆盖有限；如果依赖 LLM 生成前提，容易被认为只是 prompt 工程。
```

```text
候选名称：图像事实-常识推断分层的解释降级生成
解决的具体技术问题：
VQA 系统常把可见事实和常识推测混在一个自然语言答案中，导致用户无法区分“看见的”和“猜的”。在图像事实不足或常识冲突时，需要自动降级解释强度。
输入：
图像、问题、候选答案、候选解释、区域级证据、常识推断类别。
核心处理步骤：
1. 将回答拆为可见事实、弱推断、强推断、因果解释四层。
2. 为每层声明计算证据覆盖：可见对象覆盖、关系覆盖、动作/属性覆盖、反证覆盖。
3. 根据证据覆盖和反证覆盖选择回答模板：直接回答、保守回答、无法确认、指出异常。
4. 对强推断和因果解释设置更高证据门槛；未达门槛时自动降级为“可能/无法从图像确定”。
输出：
按证据层级降级后的答案。
为什么不是简单组合：
强调解释强度控制，而不是二分类拒答；但若没有独特的反证建模，容易被认为是置信度/模板化回答。
可实验数据集：
VCR、A-OKVQA、HaloQuest、VisionTrap、HallusionBench。
主要风险：
创新性弱，容易被 CoRGI、selective answering、calibration 覆盖。
```

```text
候选名称：可供性前提链驱动的动作类 VQA 反证检测
解决的具体技术问题：
动作类图像问答中，模型经常根据物体类别推断用途或动作，却忽略图像中局部状态不满足该动作前提，例如工具不可抓、容器封闭、接触关系缺失、支撑关系异常。
输入：
图像、动作类问题、候选答案、对象检测/分割结果、动作-前提库。
核心处理步骤：
1. 识别问题和候选答案涉及的动作谓词、施事对象、受事对象和工具对象。
2. 从动作-前提库中检索该动作的必要条件，拆成属性前提、几何前提、接触前提、状态前提。
3. 对每个前提生成图像查询并定位对应区域。
4. 统计必要前提是否满足；若关键前提被图像否定，则标记候选答案为物理不可许可。
5. 对用户输出反证原因，例如“图中未显示刀刃接触食物，因此不能确认正在切割”。
输出：
动作回答是否许可、缺失或冲突的前提、对应证据区域。
为什么不是简单组合：
不是一般 affordance grounding，而是面向 VQA 候选答案反证；从答案中的动作谓词反推必要前提，再做图像验证。
可实验数据集：
PAC Bench、Affordance-R1/ReasonAff、MOKA 场景、VCR 动作题、PhysBench physical scene understanding。
主要风险：
偏机器人/动作，覆盖范围比通用 VQA 窄；动作前提库构建成本较高。
```

```text
候选名称：反常识负控制样本的测试时答案一致性筛查
解决的具体技术问题：
模型面对正常图像和轻微反常识编辑图像时常给出同样解释，说明回答依赖语言先验而非图像差异。需要在测试时检测候选答案是否对关键物理扰动敏感。
输入：
原图、问题、候选答案、自动生成或检索的反常识扰动图、扰动说明。
核心处理步骤：
1. 识别问题所需的关键物理/常识变量，如支撑、接触、完整性、可见性、方向、数量。
2. 生成或检索只改变该变量的负控制图像/区域描述。
3. 对原图和负控制图分别回答同一问题。
4. 若候选答案在关键变量改变后仍保持不变，则判定该答案对图像证据不敏感，触发降级或阻断。
输出：
答案稳定性报告、是否依赖语言先验的标签。
为什么不是简单组合：
引入负控制思想，但测试时生成/编辑图像成本高，也容易被看作数据增强或鲁棒性测试。
可实验数据集：
VideoHallu、VisionTrap、HaloQuest、BLINK-Twice adversarial pairs、自建编辑样本。
主要风险：
部署成本高；生成图可能引入新偏差；专利落点容易偏评测而非回答方法。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对候选 1：不完全是。它不是把 VQA 应用于物理常识场景，而是定义了“解释性声明的常识前提许可”这个中间技术层，处理图像事实与常识冲突。
  - 对候选 2：风险较高。证据层级降级本身可能被认为是现有 selective answering / calibration 在 VQA 上的应用。
  - 对候选 3：中等风险。若只写动作-前提验证，容易被机器人 affordance 或 task executability 论文覆盖；必须强调它验证的是“候选答案中的动作声明”而非规划动作。
  - 对候选 4：风险较高。负控制样本和反常识 benchmark 已经很多，测试时一致性筛查更像评测流程。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 候选 1 的防守点：不依赖外部知识检索来增加答案，而是把候选回答拆成声明并反推出最小前提，再用图像事实图进行许可判断；输出不是一个分数阈值，而是 ALLOW/QUALIFY/BLOCK/ASK_CLARIFICATION 和具体被破坏前提。
  - 候选 2 的弱点：很容易被认为是 CoT 后验验证 + 置信度降级。
  - 候选 3 的防守点：核心是动作谓词到必要前提链的结构化展开和图像反证，不是让模型自我反思。
  - 候选 4 的弱点：若负控制图由 prompt 生成，再比较答案稳定性，会被认为是测试增强或 adversarial consistency。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - OCR/图表解析无关。
  - Grounding 风险存在。候选 1 和 3 必须避免只写“把回答中的实体 grounding 到图像”。应把权利要求落在“从解释性声明反推常识/物理前提，并基于前提状态许可或阻断回答”。
  - Scene graph 也已有大量工作。候选 1 不能只依赖普通 scene graph，而要引入“反常识关系”或“前提状态三值判断”。

- 是否能被一篇或几篇论文自然组合推出？
  - 审查员可能组合 CoRGI（逐步声明 visual grounding）+ Tri-HE（triplet-level hallucination）+ PAC Bench/PhysBench（物理属性/约束）来攻击候选 1。
  - 防守角度：上述论文分别做 grounding、评测或物理理解，但没有明确把候选回答中的解释性声明映射到最小常识前提，并在图像事实反证时只阻断解释而保留可见事实回答。例如“图中物体看起来像杯子，但图像未显示它能盛水/其开口完整，因此不能回答它正在倒水”。
  - 候选 3 会被 Affordance-R1/PAC Bench/BOP-Ask 攻击。必须收窄到“问答答案反证”，而非通用 affordance 预测。
  - 候选 4 会被 VideoHallu、VisionTrap、BLINK-Twice 攻击，因为负控制、反常识样本、对比图像已经是热点。

- 是否缺少可验证技术效果？
  - 候选 1 可验证：在 VisionTrap/HaloQuest/PhysBench/PAC Bench constraint 子集上，比较普通 VLM、CoT、CoRGI 式后验 grounding 与本机制的错误解释率、错误拒答率、可见事实保留率。
  - 候选 2 可验证但效果可能不独特：看解释强度校准、ECE、错误解释率。
  - 候选 3 可验证：动作类问题上比较动作前提冲突检测准确率和错误动作回答降低幅度。
  - 候选 4 可验证：扰动敏感性和回答一致性，但更像评测指标。

## 6. 本轮最佳候选

- 最佳候选：反常识冲突感知的回答许可门控。

- 为什么选它：
  - 它正面处理本轮核心问题：图像事实和常识/物理先验冲突时，系统不是简单回答或拒答，而是区分“事实可见但解释不可许可”“事实不可见但常识可猜”“常识前提被图像反证”三种状态。
  - 它比普通 hallucination mitigation 更具体：不是减少所有幻觉，而是针对解释性 VQA 中的物理/常识前提破坏。
  - 它能吸收 scene graph、affordance、physical plausibility 的研究进展，但权利要求可以抓住一个较清晰的中间动作：从候选回答反推最小前提集合，并基于图像事实图进行许可分类。

- 为什么淘汰其他候选：
  - “图像事实-常识推断分层的解释降级生成”过于接近 selective answering、calibration、CoT grounding，审查员容易认为只是回答模板和阈值策略。
  - “可供性前提链驱动的动作类 VQA 反证检测”技术上可行，但范围偏窄，容易落入机器人 affordance / manipulation prerequisite 的已有技术包围。
  - “反常识负控制样本的测试时答案一致性筛查”更像评测或数据增强，部署成本高，且 VideoHallu、VisionTrap、BLINK-Twice 等已有负控制和对比样本思路。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“对候选回答中的解释性声明生成常识/物理必要前提集合，并将所述必要前提与图像事实图进行三值匹配，以确定该解释性声明的回答许可状态”的技术动作。
  - 独立权利要求应避免泛泛写“使用常识知识库验证答案”。建议写成：
    - 获取图像、问题和候选回答；
    - 将候选回答解析为多个原子声明，并识别其中的解释性声明；
    - 针对解释性声明生成至少一个物理或常识必要前提；
    - 根据图像生成包含对象、属性、空间关系、接触/支撑关系的图像事实图；
    - 将必要前提与图像事实图匹配为满足、未知或反证状态；
    - 根据关键必要前提的状态，对解释性声明执行允许、限定、阻断或请求澄清的处理；
    - 基于处理后的声明生成最终图像问答回答。

- 如果做实验，最快怎么证明：
  - 数据：先选 HaloQuest、VisionTrap、PhysBench/PAC Bench 中的 200-500 个与 false premise、unanswerable、physical constraint、affordance 相关样本，再补 50-100 个手工反常识图像问题。
  - 基线：原始 VLM、CoT、self-check、CoRGI 式逐步 visual grounding、简单拒答阈值。
  - 指标：错误解释率、应拒答而未拒答率、可回答事实被误拒率、反证前提定位准确率。
  - 最快 demo：人工定义 30-50 条常识/物理前提模板，例如支撑、接触、容器完整、工具可抓、开口方向、遮挡/不可见、材料状态；先不训练模型，只做候选答案后处理，验证在反常识和不可回答样本上能减少“正常世界解释”。
