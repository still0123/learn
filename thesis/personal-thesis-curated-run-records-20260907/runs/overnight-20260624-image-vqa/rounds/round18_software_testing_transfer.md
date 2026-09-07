# Round 18：软件测试 / 差分验证迁移方向

## 1. 本轮方向

- 方向名称：软件测试中的 mutation testing、differential testing、metamorphic testing、program slicing、test oracle 向图像问答声明稳定性验证迁移
- 检索范围：2021-2026 年软件测试与 AI testing；LLM/VLM testing；metamorphic relation；mutation testing；differential testing；program slicing；test oracle problem；VQA robustness、hallucination、contrastive decoding、visual perturbation。
- 目标问题：图像问答经常缺少逐题 oracle，尤其候选答案的“对象、属性、数量、空间关系、OCR、图表数值、推断性声明”是否真的由图像支持并不容易自动判断。本轮尝试把软件测试的“变形关系 + 差分执行 + 切片定位 + 突变杀死”迁移成一个 VQA 技术机制，用于对问题、图像局部、候选答案做扰动检查，验证声明应该稳定、应该翻转还是必须降级。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | METAL: Metamorphic Testing Framework for Analyzing Large-Language Model Qualities | ICST | 2024 | 用模板化 metamorphic relations 自动生成大量 follow-up cases，并用多指标评价 LLM 质量属性 | 说明 MR 已被用于黑盒 LLM 测试；迁移到 VQA 时要把 MR 从文本任务扩展为图像局部、问题谓词、答案声明三者之间的关系 | https://www.computer.org/csdl/proceedings-article/icst/2024/081800a117/1ZKz4TISqEU |
| 2 | Metamorphic Testing of Large Language Models for Natural Language Processing / LLMorph | arXiv | 2025 | 系统整理 NLP 任务中的 191 个 metamorphic relations，强调在缺少显式 oracle 时用输入输出关系暴露错误 | 可作为“无标注 VQA 也能检测不稳定声明”的方法来源，但不能停留在文本改写一致性 | https://arxiv.org/html/2511.02108v1/ |
| 3 | Software Testing with Large Language Models: Survey, Landscape, and Vision | arXiv | 2024 | 综述 LLM 用于测试用例生成、oracle 生成、系统测试输入生成、bug 分析和修复 | 指出 test oracle problem 是 LLM testing 关键难题；VQA 中同样缺少细粒度 oracle | https://arxiv.org/html/2307.07221v2 |
| 4 | A Comprehensive Study on Large Language Models for Mutation Testing | arXiv | 2024/2026 | 用 LLM 生成更接近真实 bug 的 mutants，并评估 detectability、validity、equivalent mutants、成本等 | 可迁移为生成“视觉声明突变体”：把答案中的颜色、数量、关系、文本值、实体替换成高迷惑反事实，检查系统能否杀死错误声明 | https://arxiv.org/html/2406.09843v5/ |
| 5 | LLMorpheus: Mutation Testing Using Large Language Models | IEEE TSE | 2025 | 用 LLM 进行语义更丰富的 mutation testing，突破传统规则突变算子过窄的问题 | 支持用 VLM/LLM 生成上下文相关的 VQA 声明突变，但专利点不能只是“用 LLM 造干扰项” | https://dblp1.uni-trier.de/rec/journals/tse/TipBS25.html |
| 6 | Program Slicing in the Era of Large Language Models | arXiv | 2024 | 研究 LLM 做静态/动态 program slicing，发现复杂控制流仍是难点 | 启发 VQA 中的“声明影响切片”：只找影响某个声明的图像区域、OCR token、问题短语、候选答案片段 | https://arxiv.org/html/2409.12369v1/ |
| 7 | Predictive Program Slicing via Execution Knowledge-Guided Dynamic Dependence Learning | FSE | 2024 | 学习动态依赖关系，预测特定执行输入下影响 slicing criterion 的代码片段 | 可迁移为在不能穷举视觉推理过程时，预测影响答案声明的视觉/语言依赖切片 | https://ml4code.github.io/publications/yadavally2024predictive/ |
| 8 | Self-Introspective Decoding: Alleviating Hallucinations for LVLMs | ICLR | 2025 | 选择性扰动或保留视觉 token，构造对比 logits 来缓解 hallucination | 说明“扰动视觉输入并比较输出”在 LVLM 幻觉抑制中已有近似；本轮机制必须更具体到声明级 MR 和切片 | https://openreview.net/forum?id=rsZwwjYHuD |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 软件测试侧：LLM 正在用于 test generation、oracle generation、mutation testing、metamorphic testing 和 program slicing，但 oracle 问题仍然突出。
  - AI testing 侧：黑盒模型不可解释，测试更依赖输入变换后的输出关系，而不是单个输入的绝对正确性。
  - VLM/VQA 侧：模型会在视觉证据不足时强答；长 CoT 可能进一步脱离视觉；单次 confidence 或 self-check 很难判断答案是否被图像支持。
  - 幻觉抑制侧：已有视觉 token 重注入、contrastive decoding、head suppression、DPO 对齐等方法，说明“扰动或干预模型”本身不是空白。

- 已经成熟、不能作为创新点的部分：
  - 普通图像增强后要求答案一致；
  - 对同一问题多问几次，看输出是否一致；
  - 把问题 paraphrase 后做 self-consistency；
  - 用 VLM/LLM 自动生成 hard negative 或候选答案；
  - 低置信度时触发二次推理；
  - 遮挡图像区域后观察答案是否变化；
  - 用多个模型投票做 differential testing。

- 仍有空白或可迁移空间的部分：
  - 缺少面向“候选答案内部声明”的 metamorphic relation catalog：不同声明类型对应不同稳定/翻转/降级规则。
  - 缺少类似 program slicing 的“声明影响切片”，即先定位影响某个声明的最小图像区域、OCR token、问题短语和候选答案片段，再做扰动。
  - 缺少 mutation testing 中“杀死突变体”的概念：如果把答案中的关键声明改成错误但迷惑的突变体，VQA 验证器是否能拒绝它。
  - 缺少把三类扰动结果合并为输出控制动作的机制：稳定则保留，语义翻转则要求答案翻转，不应变化却变化则降级，应该变化却不变则标记幻觉。

## 4. 候选创新点

```text
候选名称：
声明影响切片驱动的三轴变形差分验证器

解决的具体技术问题：
图像问答系统生成候选答案后，缺少自动 oracle 判断其中每个声明是否真正依赖图像证据。普通一致性测试只比较改写问题或增强图像后的最终答案，无法区分哪些变化应保持稳定、哪些变化应导致答案翻转、哪些变化应触发拒答。

输入：
原始图像；用户问题；候选答案；候选答案拆分出的最小声明；可用视觉证据单元（object box、OCR token、chart element、region crop、scene graph edge）；可用扰动算子；声明类型到 metamorphic relation 的规则表。

核心处理步骤：
1. 将候选答案拆分为对象存在、属性、数量、空间关系、OCR 文本、图表数值、跨图比较、推断性描述等声明。
2. 对每个声明建立 slicing criterion，预测影响该声明的视觉切片、问题切片和答案切片。
3. 在视觉切片上生成两类 follow-up inputs：保真扰动（亮度、轻微裁剪、无关背景遮挡、同义 OCR 版式变化）和语义翻转扰动（替换颜色区域、遮挡关键对象、交换空间关系、改写 OCR 数字、替换图表轴值）。
4. 在问题切片上生成两类 follow-up questions：语义等价改写和谓词翻转改写，例如“左侧”变“右侧”、“红色”变“蓝色”、“多少”变“是否大于”。
5. 在答案切片上生成声明 mutants，例如实体替换、属性替换、数量 +-1、关系反向、文本值近邻替换。
6. 对原输入和 follow-up inputs 执行同一 VQA/验证模型，记录每个声明的支持状态、答案文本、证据定位和置信区间。
7. 根据声明类型的 MR 判定期望关系：保真扰动下声明应稳定；语义翻转扰动下相关声明应翻转或拒答；无关切片扰动不应影响声明；答案 mutant 应被杀死。
8. 汇总三轴差分结果，给每个声明输出 PASS、UNSTABLE、MUTANT_SURVIVED、SLICE_MISMATCH、NEED_MORE_EVIDENCE、REFUSE_OR_DOWNGRADE。

输出：
经过验证的最终答案；每个声明的影响切片；每个 follow-up case 的期望关系和实际关系；被保留、降级、删除或拒答的声明清单。

为什么不是简单组合：
它不是普通数据增强，因为扰动不是全局随机增强，而是由声明影响切片限定；也不是普通 self-consistency，因为不同扰动具有不同期望关系；也不是普通 hard negative 生成，因为答案突变体必须通过“是否被杀死”反馈到最终输出控制。

可实验数据集：
GQA、CLEVR、VQA v2、TextVQA、DocVQA、ChartQA、InfographicVQA、NLVR2、Visual7W、VCR、Visual Haystacks、CDQAG/QAG-360K；可先在 GQA/TextVQA/ChartQA 上构造声明级扰动子集。

主要风险：
已有 metamorphic testing、contrastive decoding、visual perturbation、hard negative generation 会构成近似文献；必须把权利要求收窄到“声明切片 + 三轴 follow-up + MR 期望关系 + 输出许可动作”，否则容易被认为只是鲁棒性评测。
```

```text
候选名称：
视觉答案突变体存活率驱动的拒答控制
解决的具体技术问题：
当候选答案的错误变体仍能被模型或 verifier 支持时，说明该问题的证据约束不足，直接回答风险高。
输入：
候选答案声明；声明突变算子；图像证据；问题。
核心处理步骤：
为每个声明生成语义相近但互斥的 mutant，用同一证据验证原声明与 mutant，计算 mutant survival rate；若多个互斥 mutant 存活，则降低原答案许可等级或拒答。

输出：
突变体存活率、拒答/降级动作、风险声明。

为什么不是简单组合：
把 mutation testing 的“测试集是否杀死突变体”改成“视觉证据是否杀死错误声明”；但如果没有切片和 MR 规则，单独写会偏评测指标。

可实验数据集：
GQA、TextVQA、ChartQA、POPE、AMBER、HaloQuest、自构造 hard negative VQA。

主要风险：
容易被认为是 hard negative / adversarial answer generation 加 verifier。
```

```text
候选名称：
多模型差分视觉 oracle 仲裁器
解决的具体技术问题：
单个 VQA 模型输出不稳定，缺少人工标注时可用多个结构不同的模型或工具产生差分 oracle。
输入：
问题、图像、候选答案、多种 VLM/OCR/detector/chart parser 输出。

核心处理步骤：
对同一声明调用多个异构模型或工具，将输出规范化为声明支持状态；当分歧集中在同一视觉切片时触发局部复查，再根据仲裁规则保留或降级答案。

输出：
差分 oracle 结果和答案控制动作。

为什么不是简单组合：
有工程实用性，但核心更像 ensemble/verifier。

可实验数据集：
TextVQA、DocVQA、ChartQA、MMMU、GQA。

主要风险：
差分测试和多模型投票均已有大量近似，创造性弱。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对“多模型差分视觉 oracle 仲裁器”攻击最强：把 differential testing 从软件换到 VQA，再加多模型投票，容易被认为是场景替换。
  - 对“视觉答案突变体存活率”也有风险：mutation testing 的 mutant 被替换成答案干扰项，若没有新的声明级处理结构，创造性不足。
  - 对“声明影响切片驱动的三轴变形差分验证器”的抗辩点在于：它不是单纯测试模型，而是把测试结果转成 VQA 输出控制状态，并限定了切片、三轴扰动、MR 期望关系和声明动作。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 不是 RAG，因为不以检索外部知识为核心。
  - 若实现成“让模型再检查一遍答案”，会被打成 self-check。
  - 若实现成“置信度低则扰动”，会被打成阈值策略。
  - 独权应避免写“模型自评是否一致”，而要写“依据声明类型选择 MR，生成保真/翻转/突变 follow-up，比较期望输出关系和实际输出关系，得到许可动作”。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 底层可以调用 grounding、OCR、chart parser，但它们不是创新核心。
  - 审查风险在于“切片”可能被理解为 attention/grounding。如果只找 bbox 再遮挡，就是现有 grounding + perturbation。
  - 反驳点应放在：切片 criterion 是答案声明；扰动算子由声明类型决定；验证的对象是 MR 是否满足，而不是 bbox 是否准确。

- 是否能被一篇或几篇论文自然组合推出？
  - METAL / LLMorph 可推出 LLM metamorphic testing。
  - LLM mutation testing 可推出语义突变体生成。
  - program slicing 可推出影响片段定位。
  - SID、MemVR、SPIN 等可推出视觉扰动或视觉重注入用于幻觉抑制。
  - 因此需要承认组合压力较大。可专利化空间在于把这些思想压缩成 VQA 专用的声明级执行流程：声明切片、三轴 follow-up、期望关系表、mutant killed/survived 判定、最终声明许可动作。

- 是否缺少可验证技术效果？
  - 可验证，但不要只承诺 accuracy 提升。
  - 更合适指标：unsupported claim rate、mutant survival rate、metamorphic violation rate、irrelevant perturbation stability、semantic-flip sensitivity、claim-level support F1、拒答/降级正确率。
  - 最快实验可在 GQA/TextVQA/ChartQA 上构造 200-500 条声明级 follow-up cases，对比原始 VLM、paraphrase consistency、random augmentation consistency、answer self-check。

## 6. 本轮最佳候选

本轮只保留：声明影响切片驱动的三轴变形差分验证器。

- 为什么选它：
  - 它把软件测试中最有迁移价值的四个概念合成一个面向 VQA 的单一机制：slicing criterion 对应答案声明，metamorphic relation 对应扰动期望，mutation testing 对应错误声明是否被杀死，differential execution 对应原输入与 follow-up 输入的关系验证。
  - 它解决的是 VQA 的真实难题：缺少逐声明 oracle，且普通一致性测试不知道哪些变化应该影响答案、哪些不应该影响答案。
  - 它能直接服务当前主线“声明级证据许可状态机”：测试结果可以变成声明级 PASS、降级、拒答、删除动作。

- 为什么淘汰其他候选：
  - “视觉答案突变体存活率驱动的拒答控制”更像一个指标或子模块，适合作为最佳候选中的一个判定维度，不宜单独成案。
  - “多模型差分视觉 oracle 仲裁器”与 ensemble、self-check、tool verifier 太接近，审查员容易用常规差分测试和多模型投票组合击穿。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“以候选答案声明为 slicing criterion，确定视觉/问题/答案三类影响切片；按声明类型生成保真扰动、语义翻转扰动和答案突变体；依据预设 metamorphic relation 判断输出应稳定、应翻转或应拒答；根据 violation / mutant survival 结果控制声明保留、降级、删除或拒答”。
  - 不要把权利要求写成“对图像和问题进行扰动后比较答案一致性”。必须限定：扰动是切片驱动的，期望关系是声明类型驱动的，输出是声明级许可动作。

- 如果做实验，最快怎么证明：
  - 数据集先选 GQA、TextVQA、ChartQA：分别覆盖对象/关系、OCR 文本、图表数值。
  - 每题先由 VLM 生成候选答案并拆声明，再人工或规则生成少量切片扰动和答案 mutants。
  - Baseline：原始 VLM；question paraphrase self-consistency；random image augmentation consistency；answer self-check；multi-model vote。
  - 指标：metamorphic violation rate、mutant survival rate、unsupported claim rate、semantic-flip sensitivity、irrelevant-perturbation stability、最终 answer accuracy 作为辅助。
  - 最小可行结果：证明本机制比普通一致性测试更能发现“看似稳定但错误的声明”，并能在干扰/反事实样本中减少无证据强答。
