# Round 09：遥感图像问答 / 多尺度空间推理方向

## 1. 本轮方向

- 方向名称：遥感图像问答、变化检测问答、多尺度空间推理、小目标证据定位、地理空间关系推理
- 检索范围：2020-2026 年 RSVQA、EarthVQA、CDVQA/CDQAG、GeoChat、VRSBench、RemoteReasoner、多模态多分辨率遥感 VQA、遥感 visual grounding 与地理空间关系推理
- 目标问题：从遥感图像的“高分辨率大场景 + 小目标 + 局部/全局尺度冲突 + 空间关系”中提炼可迁移到普通图像 VQA 的单一技术机制，使回答必须经过问题驱动的尺度选择、局部证据校验和全局语义约束，降低小目标遗漏、场景先验幻觉和局部裁剪误答。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | RSVQA: Visual Question Answering for Remote Sensing Data | IEEE TGRS / RSVQA project | 2020 | 使用 OSM 自动生成低/高分辨率遥感图像 QA，覆盖存在性、计数、面积、比较和关系问题 | 遥感 VQA 基础数据集，突出自然语言查询大尺度图像中对象和关系的需求 | https://rsvqa.sylvainlobry.com/ |
| 2 | Change Detection Meets Visual Question Answering | IEEE TGRS | 2022 | 构建多时相变化检测 VQA，使用多时相编码、变化增强、多模态融合和答案预测 | 把“变化区域”从纯分割转为可问答的信息访问方式，可迁移为多图/前后图 VQA | https://m.x-mol.net/paper/detail/1575883279748882432 |
| 3 | Multi-Step Question-Driven Visual Question Answering for Remote Sensing | IEEE TGRS | 2023 | 问题类型和关键词驱动多步注意力，组合不同尺度图像特征，并标注与问题相关区域 | 说明“问题类型 -> 尺度选择 -> 局部区域注意”的路线已存在，单纯多尺度注意力不够新 | https://www.researchgate.net/publication/373729472_Multi-Step_Question-Driven_Visual_Question_Answering_for_Remote_Sensing |
| 4 | EarthVQA: Towards Queryable Earth via Relational Reasoning-Based Remote Sensing Visual Question Answering | AAAI | 2024 | EarthVQA 含 6000 张图、语义 mask 和 208,593 个 QA；SOBA 用对象语义、伪 mask、对象内特征和对象间层次 cross-attention 做关系推理 | 从单目标识别推进到对象关系、计数和综合分析，是空间关系 VQA 的强相关先例 | https://ojs.aaai.org/index.php/AAAI/article/view/28357 |
| 5 | GeoChat: Grounded Large Vision-Language Model for Remote Sensing | CVPR | 2024 | 基于 LLaVA-1.5 和 318k 遥感指令数据，支持高分辨率遥感图像、区域级推理、VQA、grounded conversation 和 referring object detection | 证明遥感 VQA 正在向 grounded VLM 收敛；单纯输出框或区域回答已有较近现有技术 | https://mbzuai-oryx.github.io/GeoChat/ |
| 6 | VRSBench: A Versatile Vision-Language Benchmark Dataset for Remote Sensing Image Understanding | arXiv | 2024 | 29,614 张图、详细 caption、52,472 个 object references、123,221 个 QA，统一 caption / grounding / VQA 评测 | 提供可评估 grounding 与 VQA 联动的遥感基准，可用于验证证据定位类机制 | https://arxiv.org/html/2406.12384v1/ |
| 7 | Show Me What and Where has Changed? Question Answering and Grounding for Remote Sensing Change Detection | arXiv | 2024 | 提出 CDQAG 和 QAG-360K，输出文本答案和对应变化 mask；VisTA 用多阶段语义推理和文本-视觉答案解码 | 关键启发是“回答必须绑定视觉证据区域”，但其重点是多时相变化检测 | https://arxiv.org/html/2410.23828v1 |
| 8 | Co-LLaVA: Efficient Remote Sensing Visual Question Answering via Model Collaboration | Remote Sensing | 2025 | LLaVA 与轻量 contrastive captioner 协作，使用高维多尺度特征和更高分辨率图像增强细节感知，降低多 Agent 辩论成本 | 表明小目标、细节和幻觉是遥感 VQA 当前显性痛点，但模型协作本身较容易被认为常规 | https://www.mdpi.com/2072-4292/17/3/466/html |
| 9 | Visual Question Answering on Multiple Remote Sensing Image Modalities | arXiv | 2025 | TAMMI 数据集结合高分辨率 RGB、多光谱 Sentinel-2、SAR Sentinel-1；MM-RSVQA 融合多模态多分辨率特征 | 支持“同一问题需要不同分辨率/模态证据”的判断，但多模态融合本身不宜作为本轮主创新 | https://arxiv.org/html/2505.15401v1/ |
| 10 | RemoteReasoner: Towards Unifying Geospatial Reasoning Workflow | arXiv | 2025 | 以 MLLM 解释用户意图并定位目标，通过任务转换支持对象、区域、像素级输出，使用强化学习增强推理自主性 | 说明“多粒度任务转换 + 推理工作流”已出现，若做专利需抓更具体的证据许可动作 | https://arxiv.org/html/2507.19280v2/ |
| 11 | Text-conditioned State Space Model for Domain-generalized Change Detection VQA | arXiv | 2025 | BrightVQA 关注 CDVQA 跨域泛化，含损毁、数量、比较、严重度、空间、上下文、阈值、恢复评估等问题类型；TCSSM 用文本条件状态空间建模 | 说明变化问答中的空间/阈值/上下文问题已系统化，普通 VQA 可迁移其“问题条件化证据跟踪”思想 | https://arxiv.org/html/2508.08974v1 |
| 12 | A Review of Visual Grounding on Remote Sensing Images | Electronics | 2025 | 总结遥感 visual grounding 的尺度异质性、语义复杂性、标注稀缺、多尺度与层次特征处理等瓶颈 | 支撑本轮判断：遥感 grounding 的特殊痛点可抽象为普通图像 VQA 的尺度证据可靠性问题 | https://www.mdpi.com/2079-9292/14/14/2815 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 从“分类式回答”转向可定位、可解释、可验证的 grounded VQA。GeoChat、VRSBench 和 CDQAG 都在把文本回答与框、mask 或 object reference 绑定。
  - 从单图全局语义转向对象关系、计数、空间邻近、方向、包含、变化区域等结构化空间推理。EarthVQA 的 SOBA 和地理空间关系研究尤其明显。
  - 从固定低分辨率输入转向高分辨率、多尺度、多模态、多时相输入。Co-LLaVA、TAMMI、BrightVQA 都把分辨率、模态或时间作为关键变量。
  - 从遥感专用模型转向通用 MLLM 的遥感适配、指令微调、工具化工作流和推理链路。

- 已经成熟、不能作为创新点的部分：
  - “把 VQA 用到遥感图像”本身已经非常成熟，RSVQA、RSVQAxBEN、RSIVQA、TextRS-VQA、EarthVQA 等均覆盖。
  - “多尺度特征融合 + cross-attention + transformer/BERT/ViT”已是常规路径，MQVQA、TCMME、SOBA、Co-LLaVA 都有相关实现。
  - “输出 bounding box/mask 作为解释”也已接近常规，GeoChat、VRSBench、CDQAG 均提供 grounding 或 evidence mask。
  - “多 Agent 辩论、自一致 CoT、RAG、工具调用”不宜作为核心创新，因为已有 Co-LLaVA、Self-GeoSense、RS-Agent、RemoteReasoner 等近似路线。

- 仍有空白或可迁移空间的部分：
  - 遥感方法多强调性能提升，但较少把“某个答案声明到底需要哪个尺度的证据、哪个尺度能够授权、哪个尺度只能提供背景”做成明确的许可状态。
  - 小目标问答常在局部裁剪和全局场景之间摇摆：全局图提供场景先验但看不清对象，局部图看清对象却丢失关系和边界。现有方法多融合特征，较少显式判定“局部证据是否被全局上下文许可”。
  - 普通图像 VQA 同样存在类似问题：例如问“桌上左边红杯旁边是什么”“远处路牌写了什么”“这个人手里是否拿着刀”。它们需要在全局关系和局部细节之间建立证据账本，而不是一次性让 VLM 自由回答。
  - 可迁移的核心不是遥感，而是“问题驱动的尺度证据需求 -> 多尺度证据采样 -> 跨尺度一致/冲突/不足判定 -> 对声明进行许可或降级”。

## 4. 候选创新点

```text
候选名称：问题驱动的多尺度证据许可账本
解决的具体技术问题：
普通 VQA 和遥感 VQA 中，模型容易用全局场景先验回答小目标问题，或用局部裁剪回答需要全局关系的问题，导致小目标漏检、数量错误、位置关系错误和越权推断。现有多尺度融合通常把特征混合后直接预测，缺少对“答案声明是否被相应尺度证据授权”的显式判定。
输入：
用户问题、原始图像、基础 VLM/检测器/grounding 模型产生的候选答案声明、候选证据区域，可选的多尺度图像金字塔或动态裁剪结果。
核心处理步骤：
1. 将问题拆为声明槽位和证据需求，标注每个槽位所需尺度类型：全局场景、对象局部、对象间关系、数量密度、文本/符号、小目标细节。
2. 为每个证据需求生成尺度账本项，包括候选区域、尺度级别、应验证属性、最低可接受分辨率或覆盖范围、需要保留的上下文边界。
3. 在多个尺度上分别抽取证据，而不是直接融合：全局尺度负责场景和相对位置，局部高分尺度负责类别/文字/细节，中间尺度负责对象间距离和计数。
4. 对每个声明执行跨尺度许可判定：支持、冲突、不足、尺度错配、上下文丢失、过度泛化。只有当声明所需的关键账本项均被相应尺度证据支持，才允许进入最终答案。
5. 对冲突或不足的声明执行降级：改写为“无法确认细节”“只可确认存在疑似对象”“可确认位置关系但不可确认类别”等，并保留被拒绝的候选答案。
输出：
最终答案、每个答案声明的许可状态、对应尺度证据区域、被阻断或降级的声明列表。
为什么不是简单组合：
不是“多尺度特征融合 + VQA”，因为核心动作不是融合，而是把答案声明与尺度证据需求绑定，并用跨尺度许可状态控制声明是否可输出。不是普通 grounding，因为同一声明必须区分全局、局部、关系、计数等不同尺度证据的授权范围。
可实验数据集：
VRSBench、EarthVQA、RSVQA-HR、QAG-360K/CDQAG；迁移到普通图像可用 VLR-Bench、VQAv2 的空间关系子集、GQA、TextVQA、VizWiz、小目标/远距离细节样本集合。
主要风险：
MQVQA 已有问题驱动多尺度注意，EarthVQA 已有对象关系，CDQAG 已有证据 mask。需要把权利要求限定在“声明级尺度证据许可账本和跨尺度许可/降级动作”，否则容易被认为是现有多尺度 grounding 的自然组合。
```

```text
候选名称：局部裁剪的全局上下文反证门控
解决的具体技术问题：
动态裁剪或 zoom-in 能提升小目标识别，但裁剪后容易丢失方位、相邻关系、数量范围和场景边界，导致“看清局部但答错关系”。需要在局部高分答案输出前，用全局上下文对其进行反证。
输入：
用户问题、全局图像、若干局部裁剪、局部答案候选、全局关系图或对象布局摘要。
核心处理步骤：
1. 根据问题生成需要局部裁剪验证的目标区域。
2. 在局部区域识别候选对象、属性、文本或变化。
3. 将局部候选映射回全局坐标，检测其是否满足问题中的方向、邻近、包含、数量和场景边界条件。
4. 若局部候选与全局布局冲突，则阻断该局部声明；若全局条件不可见，则要求扩大裁剪或降级回答。
5. 输出经过全局反证门控后的答案。
输出：
答案、局部证据、全局反证结果、需要扩大裁剪的区域。
为什么不是简单组合：
它不是普通动态裁剪，因为局部答案必须回投到全局坐标并接受关系反证；不是普通 grounding，因为重点是裁剪导致的上下文丢失检测。
可实验数据集：
VRSBench object reference、EarthVQA 空间关系问题、RSVQA-HR 计数/邻近问题；普通图像可用 GQA spatial、VLR-Bench spatial、TextVQA 远距离文本。
主要风险：
容易被归入 active perception / zoom-in / grounding 后处理；单独作为专利点不如“多尺度证据许可账本”完整。
```

```text
候选名称：空间关系问题的尺度自适应候选排除链
解决的具体技术问题：
空间关系问答常有多个候选对象满足类别但不满足关系，例如“道路左侧的建筑”“靠近水域的停车场”。模型若只检测类别或只做语言匹配，会选错候选。需要按问题关系逐步排除候选。
输入：
问题、对象候选集合、对象位置/框/mask、多尺度图像特征、候选答案。
核心处理步骤：
1. 从问题抽取目标类别、参照物、空间谓词和度量条件。
2. 在粗尺度建立候选对象和参照物集合。
3. 按拓扑、方向、距离、包含、数量等关系逐步排除不满足条件的候选。
4. 对剩余候选做局部高分辨率确认，避免因粗尺度误检而错误排除。
5. 以候选排除轨迹生成答案和解释。
输出：
最终候选、排除轨迹、答案。
为什么不是简单组合：
不是简单 scene graph，因为排除动作由问题中的关系谓词驱动，并在粗/细尺度间切换。
可实验数据集：
EarthVQA、RSVQA-HR、VRSBench；普通图像可用 GQA、Visual Genome spatial relation 子集。
主要风险：
scene graph VQA、object-centric VQA 和 EarthVQA/SOBA 已经很接近；作为独立创新点非显而易见性偏弱。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对“遥感 VQA”本身是。遥感图像、城市规划、变化检测、地理空间关系都不能作为普通 VQA 专利的新颖性来源。
  - 对最佳候选而言，必须明确迁移后的技术问题是“多尺度证据对答案声明的授权范围判定”，而不是“把遥感多尺度方法用到普通图片”。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 如果实现为让模型多问几次、输出推理链、投票或按置信度过滤，会被直接打掉。
  - 需要把核心限定为结构化账本：每个声明有证据需求、尺度级别、证据区域、许可状态和降级规则。许可不是置信度阈值，而是证据类型和尺度是否满足声明需求的离散状态判定。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 风险较高。GeoChat、VRSBench、CDQAG 已经把回答和视觉证据绑定。
  - 可区分点在于：现有 grounding 通常回答“证据在哪里”，本候选回答“某个声明是否被正确尺度的证据授权”。例如全局图可授权“图中有道路”，但不能授权“远处小标牌写着 P”；局部图可授权“局部有 P 字样”，但不能单独授权“该标牌在道路左侧”。这是跨尺度授权边界，不是单一 grounding。

- 是否能被一篇或几篇论文自然组合推出？
  - MQVQA 的问题驱动多尺度特征、EarthVQA 的对象关系、GeoChat 的 grounded conversation、CDQAG 的答案 mask 可以自然组合出“多尺度 grounded VQA”。
  - 因此专利写法不能泛泛写“多尺度特征 + grounding + VQA”。必须抓“声明级尺度需求建账、跨尺度许可状态、尺度错配阻断/降级”三个动作，尤其是尺度错配状态，例如“局部支持但全局关系不足”“全局支持但局部细节不足”。

- 是否缺少可验证技术效果？
  - 可验证。构造或筛选需要多尺度证据的问题，比较基础 VLM、zoom-in VLM、多尺度融合模型、普通 grounding 后处理和本机制。
  - 指标不应只看总体 accuracy，还要看：小目标细节幻觉率、空间关系错误率、证据不足拒答率、局部裁剪导致的上下文错答率、声明级证据匹配 F1。

## 6. 本轮最佳候选

**最佳候选：问题驱动的多尺度证据许可账本。**

- 为什么选它：
  - 它最符合本项目已有“声明级证据许可状态机”的主线，可把遥感领域的多尺度空间推理痛点转化为普通图像 VQA 中的声明级证据授权问题。
  - 它不是单纯的遥感场景替换，而是抽象出通用 VQA 问题：不同答案声明需要不同尺度的证据，全局先验、局部细节和对象关系不能互相越权。
  - 它比“局部裁剪反证门控”和“空间关系候选排除链”覆盖更广，可以包含小目标、计数、空间关系、局部文字、变化区域和多图比较等子问题。

- 为什么淘汰其他候选：
  - “局部裁剪的全局上下文反证门控”机制清楚，但范围偏窄，容易落入 active perception / zoom-in / crop-and-check 的常规改进。
  - “空间关系问题的尺度自适应候选排除链”与 scene graph VQA、EarthVQA/SOBA、对象关系推理太接近，非显而易见性较弱。
  - “多模态多分辨率输入融合”没有保留为候选，因为 TAMMI/MM-RSVQA 已经直接覆盖，多模态融合本身太常规。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“根据问题和候选答案声明生成尺度证据账本，并根据账本对每个声明进行跨尺度许可状态判定”的动作。
  - 独立权利要求可包含：
    - 对问题拆分得到答案声明槽位及其证据需求；
    - 为每个声明槽位分配至少一个证据尺度类型和证据区域要求；
    - 在多个尺度图像或区域中分别获得证据项；
    - 根据证据项与声明槽位的尺度匹配关系、内容匹配关系和上下文保持关系，生成支持、冲突、不足、尺度错配、上下文丢失、越权中的至少一种许可状态；
    - 按许可状态输出、阻断或降级候选声明。
  - 关键术语应避免“遥感”“卫星”限定，写成“包含大场景和小尺度目标的图像问答”，遥感只作为实施例。

- 如果做实验，最快怎么证明：
  - 数据：优先用 EarthVQA 和 VRSBench 做空间关系/小目标/grounding 验证，用 RSVQA-HR 做高分辨率计数和关系问题，用 QAG-360K/CDQAG 做变化证据区域验证；普通图像侧补 VLR-Bench、GQA spatial、TextVQA 远距离文本和 VizWiz 不足证据样本。
  - 基线：Qwen2-VL 直接回答；Qwen2-VL + crop；Qwen2-VL + grounding；多尺度 crop 后投票；本机制。
  - 最快可做的指标：答案准确率、声明级证据匹配率、尺度错配检出率、应拒答样本的越权回答率、局部裁剪上下文错误率。
  - 最小实验闭环：先人工构造 100-200 个“全局能看关系但看不清细节 / 局部能看细节但缺关系”的普通图像与遥感混合样本，验证本机制能减少错误声明输出；再扩展到公开数据集。
