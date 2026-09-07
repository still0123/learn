# Round 23：数据集构造 / 幻觉诱发项生成方向

## 1. 本轮方向

- 方向名称：自动生成幻觉诱发难例、反证项与可验证 hard negative 的 VQA 数据构造
- 检索范围：hallucination benchmark、counterfactual data generation、hard negative generation、hitem selection、adversarial VQA data、POPE、AMBER、PhD、CHAIR、HaloQuest、NaturalBench、CounterCurate、ViLP、JourneyBench、Hallu-PI。
- 目标问题：判断“自动生成难例和反证项”能否成为图像问答新专利创新点；如果可以，必须避免落入普通数据增强、普通反事实样本生成、普通 benchmark curation 或 hard negative mining。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---:|---:|---|---|---|
| 1 | CHAIR: Object Hallucination in Image Captioning | EMNLP | 2018 | 用 MSCOCO 对象标注衡量 caption 中不存在对象的比例，区分 CHAIRi / CHAIRs。 | 奠定“对象不在图中却被说出”的评测定义，但不是 VQA 难例生成机制。 | https://ar5iv.org/abs/1809.02156 |
| 2 | POPE: Evaluating Object Hallucination in LVLMs | arXiv / EMNLP | 2023 | 用 polling 式 yes/no 对象存在问题评测幻觉，负样本分 random、popular、adversarial。 | 说明对象共现和热门类别负样本已是成熟的幻觉诱发设计。 | https://ar5iv.org/abs/2305.10355 |
| 3 | AMBER: LLM-free Multi-dimensional Benchmark | arXiv | 2023 | 覆盖生成式与判别式评测，评估 existence、attribute、relation hallucination。 | 把幻觉从对象扩展到属性和关系，提示难例不能只做“图中没有某物”。 | https://arxiv.org/abs/2311.07397 |
| 4 | PhD: Prompted Visual Hallucination Evaluation Dataset | arXiv | 2024 | ChatGPT 辅助半自动流水线：hitem 选择、hitem-embedded 问题、不准确/错误上下文、反常识图像。 | 与本轮最接近，已覆盖“选择幻觉元素并嵌入问题/上下文”的数据构造。 | https://arxiv.org/html/2403.11116v2/ |
| 5 | HaloQuest | Google DeepMind / arXiv | 2024 | 真实图和合成图结合，构造 false premise、insufficient context、visual challenge 三类 VQA 幻觉样本。 | 证明合成图可规模化构造幻觉 VQA，且可作为微调数据。 | https://haloquest.github.io/ |
| 6 | NaturalBench | NeurIPS Datasets | 2024 | 半自动收集自然对抗 VQA；同一问题配两张答案不同的图，防止语言先验答题。 | 关键现有技术：视觉中心配对设计，用图像差异迫使模型看图。 | https://openreview.net/forum?id=Dx88A9Zgnv |
| 7 | CounterCurate | arXiv | 2024 | 通过翻转、替换、移除、生成等方法构造物理/语义反事实图文对。 | 覆盖“用生成模型做反事实 hard negatives”路线，普通反事实增强风险高。 | https://arxiv.org/html/2402.13254v3/ |
| 8 | Hallu-PI | arXiv | 2024 | 在扰动输入场景下评估 MLLM 幻觉，包含多种图像扰动和 prompt misleading。 | 说明“扰动输入诱发幻觉”已成为 benchmark 设计元素。 | https://arxiv.org/html/2408.01355v1/ |
| 9 | JourneyBench | arXiv | 2025 | 使用生成图构造非典型场景，包含 hallucination trigger、fine-grained retrieval hard negatives。 | 说明“生成图 + 样本特定干扰项”已可规模化，必须进一步限定技术机制。 | https://arxiv.org/html/2409.12953v4/ |
| 10 | ViLP: Probing Visual Language Priors | ICML | 2025 | 合成 OOD 图像和 VQA，构造可由语言先验误导的答案与需视觉推理的 good-bad 图像对。 | 与“诱发语言先验幻觉”高度相关；普通 prior probing 不新。 | https://icml.cc/virtual/2025/poster/44730 |
| 11 | SHALE | ACM MM | 2025 | 自动构造细粒度 hallucination evaluation 数据，覆盖 faithfulness / factuality 和输入扰动。 | 说明自动化、可控、多样化的幻觉 benchmark pipeline 已出现。 | https://arxiv.org/html/2508.09584v2/ |
| 12 | HALVA | Google Research | 2024 | 通过选择性改写 ground-truth 对象/属性生成 hallucinated responses，再做 contrastive tuning。 | 已覆盖“生成正负回答对训练模型少幻觉”，不能把改答案当核心新点。 | https://research.google/blog/halva-hallucination-attenuated-language-and-vision-assistant/ |
| 13 | REVERSE | NeurIPS | 2025 | 构建 1.3M 半合成幻觉验证数据，并在推理时 retrospective resampling。 | 说明大规模半合成 hallucination-verification 数据已是强现有技术。 | https://nips.cc/virtual/2025/loc/san-diego/poster/120029 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 幻觉评测从对象存在扩展到属性、关系、数量、位置、OCR、false premise、insufficient context、反常识图像和语言先验依赖。
  - 数据构造从人工标注转向半自动：先选 hitem / risk item，再生成问题、错误上下文、反事实图像或 hard negative answer，最后用模型和人工过滤。
  - 2024 之后更强调“不能被语言先验答对”：NaturalBench 的双图同问、ViLP 的 good-bad 图像对、JourneyBench 的非典型生成图都在压制 shortcut。
  - 难例质量不再只看模型答错率，还看唯一正确性、可验证性、跨模型稳定性、是否覆盖多类幻觉、是否与人工判断一致。

- 已经成熟、不能作为创新点的部分：
  - 随机替换对象、颜色、数量、关系生成负答案。
  - 从 COCO/Visual Genome 中选不存在对象做 yes/no 问题。
  - 用 LLM 生成问题和干扰项，再人工过滤。
  - 用扩散模型生成反事实图像或反常识图像。
  - 选当前模型答错的样本作为 hard negative mining。
  - 构造 false premise / insufficient context / misleading prompt 测 hallucination。
  - 把生成的正负样本用于 DPO、contrastive tuning 或普通微调。

- 仍有空白或可迁移空间的部分：
  - 现有难例生成多数以“让模型错”为目标，但没有强制每个负项对应一个可定位、可机器验证的视觉反证。
  - 很多 hard negative 只是语义相似或高混淆，缺少“最小差异导致答案翻转”的约束，因此容易被审查员认为是普通数据增强。
  - 现有 benchmark 往往离线构造固定数据；较少根据目标模型的语言先验、视觉证据缺口和反证可验证性动态生成样本。
  - 幻觉诱发项的质量控制仍依赖人工或通用 VLM judge，缺少面向专利的技术动作：生成、反证、筛选、难度调度、泄漏检测形成闭环。

## 4. 候选创新点

```text
候选名称：证据反转约束的幻觉诱发难例生成器
解决的具体技术问题：
普通 hard negative / 反事实增强只保证干扰项语义相似或能让模型答错，不能保证该干扰项与图像中一个可定位视觉证据形成明确反证，因此生成数据容易有歧义、不可验证，且被认为是普通数据增强。
输入：
图像、原始问题、正确答案、对象/属性/关系/OCR 标注或自动 grounding 结果、候选模型的回答分布、可编辑视觉槽位集合。
核心处理步骤：
1. 从正确问答中抽取目标声明槽位，例如对象存在、属性、数量、空间关系、文字内容、动作状态。
2. 为每个槽位生成候选诱发项，不是随机替换，而是选择与图像全局语境高度共现、与局部视觉证据相冲突、且可由语言先验诱导的元素。
3. 对每个候选诱发项生成“反证定位约束”，例如不存在对象的候选应绑定到可见背景区域或同类对象区域；错误属性应绑定到目标框内的真实属性；错误关系应绑定到两个实体框的真实几何关系。
4. 构造最小反转样本：保持问题模板、图像主体和答案语法尽量不变，只替换一个会改变答案的视觉槽位。
5. 使用多路验证器过滤：视觉检测/分割/OCR 验证反证存在，语言模型验证问题自然性，目标 VLM 验证诱发难度，交叉模型验证唯一正确答案。
6. 根据“反证强度、语言先验诱导强度、模型混淆度、人工可解释性”给样本打分，并按难度课程输出。
输出：
带有问题、正确答案、幻觉诱发答案、反证证据区域、反证类型、难度分数和过滤日志的 VQA 难例。
为什么不是简单组合：
核心不是生成负样本，而是要求每个负样本必须同时满足“语言先验可诱发”和“局部视觉反证可定位可验证”两个约束，并以最小槽位反转保证因果归因。
可实验数据集：
COCO/Visual Genome/GQA/TextVQA/VizWiz/OK-VQA/A-OKVQA，评测可用 POPE、AMBER、PhD、HaloQuest、NaturalBench、ViLP、JourneyBench。
主要风险：
PhD 已有 hitem selection 和错误上下文；NaturalBench 已有双图同问；CounterCurate/ViLP 已有反事实图像对。必须把“反证定位约束 + 最小槽位反转 + 多路可验证过滤”写成不可拆开的核心。
```

```text
候选名称：目标模型先验剖面的自适应 hitem 选择
解决的具体技术问题：
固定的 hallucination item 列表只能覆盖通用对象共现偏置，不能针对某个 VLM 的具体语言先验和视觉弱点生成高价值难例。
输入：
目标 VLM、图像集合、候选 hitem 库、对象共现图、问题模板、模型在无图/遮图/原图下的回答分布。
核心处理步骤：
1. 对每个图像问题分别运行无图、遮图、低分辨率图和原图推理，估计目标模型对对象/属性/关系的语言先验依赖。
2. 选择“无图高置信、原图证据相反、遮挡后仍坚持”的 hitem 作为诱发项。
3. 将 hitem 嵌入 false premise、insufficient context、关系比较、计数等不同问题模式。
4. 用动态难度调度保留从容易到困难的样本，避免只生成模型已经完全无法处理的噪声样本。
输出：
针对目标模型的 hitem 列表和对应 VQA 难例。
为什么不是简单组合：
它不是静态 hitem selection，而是用无图/遮图/原图差分估计模型先验剖面，再自适应选诱发项。
可实验数据集：
POPE adversarial/popular、PhD、AMBER、COCO、GQA、Visual Genome。
主要风险：
容易被认为是 active hard negative mining 或 adversarial sampling；如果不绑定视觉反证和最小槽位反转，专利性较弱。
```

```text
候选名称：双图同问的答案翻转一致性数据生成
解决的具体技术问题：
单图单问难以证明模型是否真正看图，语言先验可能答对；需要构造同一问题在两张视觉近邻图上答案翻转的数据。
输入：
图像库、图像生成/编辑模型、问题模板、视觉槽位和目标答案。
核心处理步骤：
1. 对原图抽取可问视觉槽位。
2. 检索或生成只在目标槽位上不同的近邻图，保持背景、对象类别或场景语义相似。
3. 对两张图使用同一问题，要求答案在目标槽位上翻转。
4. 过滤掉多处差异导致多解的样本，输出 paired VQA。
输出：
同问双图、答案翻转标签、差异区域和验证记录。
为什么不是简单组合：
若只做双图同问，NaturalBench 已覆盖；必须进一步要求自动生成/编辑时的最小视觉差异和可定位验证。
可实验数据集：
NaturalBench、CounterCurate、ViLP、JourneyBench、GQA、Visual Genome。
主要风险：
NaturalBench 与 ViLP 的现有技术压力很强，不建议作为本轮最佳。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 攻击：hard negative mining、adversarial data synthesis、counterfactual data generation 在 CV/NLP/VQA 中都很成熟；把它叫“幻觉诱发项”只是换名。
  - 抗辩：候选 1 不能主张“生成 hard negative”本身，应主张“诱发项必须由语言先验强度和局部视觉反证强度共同约束，并输出反证区域和可验证日志”。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 攻击：用 VLM/LLM judge 过滤样本，本质是 self-check；用模型答错率排序，本质是置信度阈值。
  - 抗辩：过滤器只是质量控制，核心技术动作是生成时的最小槽位反转和反证定位约束；最终难例包含可由视觉工具独立验证的反证，不依赖模型自我声明。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 攻击：对象检测、OCR、grounding、问题生成、LLM 改写组合起来就是这个流程。
  - 抗辩：这些模块是证据产生器；创新应落在“候选负项必须绑定到与其矛盾的视觉证据槽，并通过槽位级最小反转构成诱发样本”的数据构造规则。

- 是否能被一篇或几篇论文自然组合推出？
  - 强组合 1：POPE 的 adversarial negative + PhD 的 hitem selection + HaloQuest 的 false premise。
  - 强组合 2：CounterCurate 的反事实生成 + NaturalBench 的双图同问 + ViLP 的 language prior probing。
  - 强组合 3：HALVA 的 hallucinated token 改写 + AMBER 的属性/关系评测。
  - 风险判断：如果候选只写“自动生成难例、负答案和反事实图像”，很容易被上述组合打掉。
  - 抗辩方向：把新颖性压缩到“证据反转约束”。现有方法通常只保证负项困难或反事实合理，未必要求负项与图像内可定位反证一一绑定，也未必要求最小槽位变化导致答案翻转。

- 是否缺少可验证技术效果？
  - 候选 1 可验证：生成样本的唯一答案率、反证定位准确率、人工一致性、目标模型诱发率、跨模型难度稳定性、训练后 hallucination rate 降幅。
  - 必须避免只报告“模型准确率下降”或“生成数据更多”。这只能证明难，不证明高质量或有技术效果。

- 是否只是普通数据增强？
  - 攻击：将正确答案中的对象/属性替换为错误对象/属性，再训练模型区分，就是普通数据增强。
  - 抗辩：普通增强不要求负项有视觉反证，也不要求最小反转和因果归因；本候选输出的每条样本都有“为什么这个负项错”的区域级证据。

- 是否只是普通 benchmark curation？
  - 攻击：构造一个数据集通常不被视为强算法创新。
  - 抗辩：专利写法应避免只保护“数据集”，而保护“生成、筛选和标注幻觉诱发样本的方法及装置”，并把反证区域、反转槽位、难度调度作为技术处理步骤。

## 6. 本轮最佳候选

本轮最佳候选：**证据反转约束的幻觉诱发难例生成器**。

- 为什么选它：
  - 它比“自动生成难例”更窄、更有技术动作，核心是把每个 hallucination negative 绑定到一个可定位、可机器验证的视觉反证。
  - 它能吸收 POPE/AMBER/PhD/HaloQuest 的对象、属性、关系、false premise 设计，但不会只停留在 benchmark 列表或普通 LLM 生成。
  - 它与项目主线兼容：后续可把生成出的反证项喂给声明级证据许可状态机，用于训练或评估“冲突声明阻断”。

- 为什么淘汰其他候选：
  - “目标模型先验剖面的自适应 hitem 选择”有工程价值，但更像 adversarial hard negative mining；专利上容易被认为只是按模型错误率采样。
  - “双图同问的答案翻转一致性数据生成”已被 NaturalBench、ViLP、CounterCurate 强覆盖；除非加入更强的最小编辑和反证验证，否则新颖性不足。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“从图像问答样本中确定待反转视觉槽位；基于语言先验诱导强度生成候选幻觉诱发项；为候选诱发项确定与其相矛盾的图像局部反证证据；在保持其他槽位不变的条件下构造最小反转问答样本；依据反证可验证性和模型混淆度筛选输出难例”的连续流程。
  - 不要把权利要求核心写成“用大模型生成负样本”“用检测器过滤错误样本”“选择模型答错的样本训练”。

- 如果做实验，最快怎么证明：
  - 数据：从 COCO/GQA/Visual Genome 各取 300-500 张图，覆盖对象存在、属性、数量、空间关系；TextVQA 另取 OCR 类 100-200 条。
  - 生成：对每条样本构造 1 个普通随机负项、1 个语义相似负项、1 个证据反转约束负项。
  - 评测 1：人工验证唯一正确率和反证区域准确率，目标是证据反转负项显著高于普通 LLM 负项。
  - 评测 2：在 Qwen2-VL、LLaVA、InternVL、GPT-4o 类模型上测诱发率，目标是比随机负项更难，但人工一致性不下降。
  - 评测 3：用生成数据微调或 DPO 后，在 POPE、AMBER、HaloQuest、PhD 上测 hallucination rate 下降，并确认 VQA 通用准确率不明显下降。
  - 最小可行证明：先做 500 条声明级样本，报告四个指标：诱发成功率、反证可定位率、唯一答案率、训练后 unsupported claim rate 降幅。
