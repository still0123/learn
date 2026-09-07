# Round 22：小样本 / 测试时自适应方向

## 1. 本轮方向

- 方向名称：小样本 VQA、测试时自适应、在线校准与证据许可策略自适应
- 检索范围：few-shot VQA、multimodal in-context learning、test-time adaptation、test-time prompt tuning、prompt adaptation、online calibration、selective answering、self-training、auxiliary-task adaptation。
- 目标问题：寻找一个能让图像问答系统根据少量样例自适应“何时回答、何时要求证据、何时拒答或降级”的单一技术机制，而不是简单做 few-shot prompt、LoRA 微调、TTA 熵最小化或置信度阈值调整。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | Test-Time Prompt Tuning for Zero-Shot Generalization in Vision-Language Models | NeurIPS | 2022 | 对单个测试样本生成增强视图，优化可学习 prompt，使预测熵最小并保持跨视图一致 | TTA 代表方法，但主要面向 CLIP 分类，不处理 VQA 证据许可 | https://arxiv.org/abs/2209.07511 |
| 2 | Investigating Prompting Techniques for Zero- and Few-Shot Visual Question Answering | arXiv | 2024 | 系统比较问题模板、caption、CoT、text-only few-shot examples 和答案预处理对 VQA 的影响 | 说明 few-shot 示例常改善格式和答案分布，但容易被视为 prompt engineering | https://arxiv.org/html/2306.09996v2 |
| 3 | LIVE: Learnable In-Context Vector for Visual Question Answering | NeurIPS | 2024 | 将少量 multimodal demonstrations 蒸馏为 learnable in-context vector，降低 ICL 推理成本和示例选择敏感性 | 直接覆盖“少样例 VQA 示例压缩/向量化”路线 | https://openreview.net/forum?id=QhRemVrZbG |
| 4 | Aggregate-and-Adapt Natural Language Prompts for Downstream Generalization of CLIP | NeurIPS | 2024 | 聚合自然语言 prompt 知识并生成图像相关 prompt embedding，支持 few-shot 分类、VQA、captioning | 证明少样例 prompt adaptation 已延伸到 VQA，但核心仍是 prompt 表示学习 | https://openreview.net/forum?id=Yz3wBKoK0K |
| 5 | Low-Rank Few-Shot Adaptation of Vision-Language Models | arXiv | 2024 | 将 LoRA 引入 few-shot VLM 适配，在 11 个数据集上作为简单强基线 | 参数高效小样本适配已成熟，单独做 LoRA/adapter 很难成为本轮创新 | https://arxiv.org/html/2405.18541v2 |
| 6 | A Lost Opportunity for Vision-Language Models: A Comparative Study of Online Test-Time Adaptation for Vision-Language Models | arXiv | 2024 | 系统评估 CLIP/VL 模型的在线 TTA、prompt-based adaptation 和 vision-text ensemble | 表明 VL TTA 已是拥挤方向，且核心仍围绕分布偏移下的分类鲁棒性 | https://arxiv.org/html/2405.14977v2 |
| 7 | Frustratingly Easy Test-Time Adaptation of Vision-Language Models | NeurIPS | 2024 | ZERO：对增强视图预测，保留高置信结果并零温度边缘化，无需反向传播 | 强化了“增强视图 + 置信选择”是 TTA 强基线，不能把它作为新机制核心 | https://openreview.net/forum?id=eQ6VjBhevn |
| 8 | Selectively Answering Visual Questions | arXiv | 2024 | 分析 VQA/LMM 的校准和选择性回答，比较 likelihood、sampling repetition、sampling diversity、Avg BLEU 等 score | 与“回答/拒答”直接相关，但主要是校准评分和选择性预测分析 | https://arxiv.org/html/2406.00980 |
| 9 | Selective “Selective Prediction”: Reducing Unnecessary Abstention in Vision-Language Reasoning | ACL Findings | 2024 | ReCoVERR 在低置信时生成相关问题，收集高置信视觉线索，减少不必要拒答 | 代表“低置信时主动补证据”路线，需避免直接重复 | https://aclanthology.org/2024.findings-acl.767 |
| 10 | VL-ICL Bench: The Devil in the Details of Multimodal In-Context Learning | ICLR | 2025 | 构建 10 类 multimodal ICL 任务，指出传统 VQA/captioning 不足以衡量真正 ICL 能力 | 说明少样例 VQA 很多时候只是格式学习，真正自适应应关注规则/证据策略 | https://openreview.net/forum?id=cpGPPLLYYx |
| 11 | Variational Visual Question Answering for Uncertainty-Aware Selective Prediction | arXiv | 2025/2026 | 用 variational learning 得到参数后验和输出方差，提升 VQA 校准和选择性预测 | 说明 VQA 不确定性/拒答已有专门路线，但不是基于少样例策略迁移 | https://arxiv.org/html/2505.09591v3 |
| 12 | Meta-Adaptive Prompt Distillation for Few-Shot Visual Question Answering | arXiv / ICLR | 2025/2026 | 用 meta-learning 学习 soft prompts 和 attention-mapper，并在测试时用少量样例更新 | 直接覆盖“few-shot VQA + test-time adaptation + soft prompt”组合 | https://arxiv.org/html/2506.06905v2 |
| 13 | Test-Time Warmup for Multimodal Large Language Models | arXiv | 2025 | 为每个测试实例生成弱监督辅助任务数据，并在推理前 warmup 更新模型 | 代表 MLLM 测试时训练/辅助任务适配方向，但计算较重、专利空间需避开“生成辅助题再训练” | https://arxiv.org/html/2509.10641 |
| 14 | Calibrated Self-Rewarding Vision Language Models | NeurIPS | 2024 | 通过自生成候选、自评 reward、偏好数据微调，强调视觉约束以减轻幻觉 | 说明“自我奖励 + 校准 + 视觉约束”已有，不能简单用 self-training 作为创新 | https://openreview.net/forum?id=nXYedmTf1T |
| 15 | TTA-VLM: A Critical Look at Test-Time Adaptation for Vision-Language Models | NeurIPS | 2025 | 统一评估 8 个 episodic TTA 和 7 个 online TTA，发现许多 TTA 增益有限且可能损害可信度 | 反向提醒：单纯追求 TTA 准确率并不稳，可信证据许可更有差异化空间 | https://nips.cc/virtual/2025/loc/san-diego/poster/121767 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 从手写 prompt 走向可学习 prompt、in-context vector、soft prompt distillation、LoRA/adapter 等轻量少样例适配。
  - 从训练前适配走向测试时适配，包括单样本增强视图、在线流式 TTA、辅助任务 warmup、meta test-time training。
  - 从只看 accuracy 走向 calibration、selective prediction、abstention、coverage-risk tradeoff、OOD reliability。
  - 多模态 ICL 的评测正在从普通 VQA/captioning 转向 rule induction、fast concept binding、interleaved image-text reasoning，说明“少样例真正学到了什么”成为热点。

- 已经成熟、不能作为创新点的部分：
  - 给 VQA prompt 中加入 few-shot examples。
  - 根据验证集或少量样例选择问题模板、caption、CoT 或答案格式。
  - 用 soft prompt、learnable in-context vector、LoRA、adapter 做 few-shot VQA 适配。
  - 在测试时做增强视图一致性、熵最小化、置信样本筛选。
  - 用 likelihood、采样一致性、输出方差或简单校准分数决定是否拒答。
  - 低置信时让模型自问自答或补充相关问题来找证据。

- 仍有空白或可迁移空间的部分：
  - 少量样例通常被用于“提高答案准确率”，很少被用于学习“不同问题类型下，答案必须满足哪些视觉证据许可条件”。
  - 选择性回答多依赖全局置信分数，较少把少量校准样例转化为声明级证据门控规则。
  - TTA 方法多更新 prompt/参数，却不显式输出“证据要求、许可/阻断原因、样例迁移来的策略”。
  - 可以把少量样例组织为“问题类型-证据需求-错误模式-许可动作”的可更新策略表，而不是直接作为 ICL 示例拼到上下文中。
  - 该路线实验成本低：不必训练大模型，只需在 VQA/OK-VQA/A-OKVQA/VizWiz/UNK-VQA 上构造少量校准样例，评估 selective accuracy、coverage、ECE、拒答质量和幻觉率。

## 4. 候选创新点

```text
候选名称：少样例证据许可策略自适应的图像问答方法
解决的具体技术问题：
现有 few-shot VQA 通常把少量样例作为答案格式或任务语义提示，TTA 通常优化 prompt/参数以提升预测一致性，选择性回答通常使用全局置信分数。这些方法不能根据少量校准样例学习“某类问题在当前场景中必须满足哪些视觉证据条件才能回答”，导致模型在新领域或新用户任务中仍会对缺少证据的对象、属性、数量、关系、外部知识问题过度回答。本机制要解决的是：如何把少量样例转化为可执行的证据许可策略，并在每个测试问题上控制答案、降级或拒答。
输入：
目标图像；用户问题；基础 VQA/VLM 生成的候选答案和可选 rationale；少量校准样例，每个样例包含图像、问题、标准答案或拒答标签、关键证据区域/证据短语、错误类型或是否可回答标签；可选的候选证据提取器，如 grounding、OCR、caption、object detector、region crop VQA。
核心处理步骤：
1. 校准样例归因：对少量样例解析问题类型和证据需求，形成结构化单元，例如“数量题需要枚举目标实例并覆盖全图”“颜色题需要目标区域和属性区域重合”“外部知识题需要图像实体可识别后才允许调用常识”“不可见对象题必须拒答”。
2. 错误模式抽取：比较样例中的候选答案和标准答案/拒答标签，抽取导致错误的触发条件，例如答案对象未被定位、证据区域与问题对象不一致、多个候选答案视觉支持接近、问题要求的关系无法由图像直接观测。
3. 策略表更新：把少量样例压缩成“问题类型-证据检查项-许可阈值/相对排序-阻断动作”的策略表，而不是直接更新大模型参数。策略项可带权重，并随样例数量在线调整。
4. 测试问题匹配：对新问题解析问题类型，检索最相近的策略项；若没有匹配项，回退到默认证据许可策略。
5. 候选答案声明化：将基础模型答案拆成声明单元，如对象存在、属性、数量、空间关系、外部知识结论、不可见推断。
6. 证据检查执行：对每条声明调用对应证据检查项，例如 grounding 覆盖率、跨 crop 一致性、候选数量枚举一致性、OCR/视觉冲突、采样答案分歧、answerability probe。
7. 许可动作生成：依据自适应策略表对声明执行 allow、revise、ask-clarification、abstain、answer-with-limited-scope。若只有部分声明通过，则输出被许可的短答案或带限制条件的回答。
8. 在线校准反馈：若后续获得用户确认或少量新标注，将本次证据检查结果和正确性写回策略表，优先调整证据检查项权重，而不是直接调整基础 VLM。
输出：
最终答案或拒答/澄清请求；触发的策略项；每条答案声明的证据许可状态；少样例迁移来的证据要求；可选的最小支持证据。
为什么不是简单组合：
核心不是把 few-shot examples 拼进 prompt，也不是用 TTA 更新 prompt token，更不是置信度阈值拒答。它将少量样例转化为“证据许可策略”，并把该策略作用于答案声明级别，改变回答动作。少样例学习的对象从“答案分布/参数”变为“回答前必须通过的证据检查程序”。
可实验数据集：
VQAv2、OK-VQA、A-OKVQA、GQA、VizWiz、UNK-VQA、VQA-CP、VL-ICL Bench 中的 image-to-text 任务。最快实验可在 VizWiz/UNK-VQA 上做 answerability few-shot calibration，在 VQAv2/GQA 上按问题类型构造 5/10/20-shot 策略样例，比较基础 VLM、few-shot prompt、置信度拒答、ReCoVERR 式补证据、本机制的 selective accuracy、coverage、ECE、幻觉率。
主要风险：
审查员可能认为它是 few-shot prompt + grounding + abstention 的组合。需要把权利要求集中在“从少量样例生成证据许可策略表，并依据该策略表对候选答案声明执行许可/阻断/降级动作”这一技术动作，而不是泛泛写少样例自适应。
```

```text
候选名称：少样例覆盖-风险曲线在线校准的 VQA 拒答阈值方法
解决的具体技术问题：
VQA 系统在新场景中缺少标注数据，固定置信度阈值常导致过度拒答或错误回答。
输入：
少量带正确/错误标签的校准样例；基础模型输出概率、采样一致性、答案长度、OCR/grounding 分数；测试问题。
核心处理步骤：
1. 在少量样例上计算多个不确定性特征。
2. 拟合覆盖率-风险曲线或 conformal-style 阈值。
3. 按问题类型维护不同阈值。
4. 对测试样本输出回答或拒答。
输出：
回答/拒答决策和校准分数。
为什么不是简单组合：
如果只到这一步，基本就是小样本校准和选择性预测，技术差异有限。
可实验数据集：
VizWiz、UNK-VQA、VQAv2、A-OKVQA。
主要风险：
风险很高。Selectively Answering Visual Questions、Variational VQA、选择性预测、conformal prediction 等都可组合推出，容易被认为是置信度阈值。
```

```text
候选名称：测试时辅助子题生成驱动的 VQA 局部策略热身方法
解决的具体技术问题：
复杂 VQA 问题需要局部感知和多步推理，基础模型直接回答容易忽略关键局部证据。
输入：
图像、主问题、基础模型、辅助子题生成器、少量任务样例。
核心处理步骤：
1. 根据主问题生成局部感知子题，例如对象计数、属性识别、关系确认。
2. 使用少量样例选择子题类型和顺序。
3. 在测试时先回答子题，形成临时上下文或轻量参数更新。
4. 再回答主问题。
输出：
主答案和子题证据链。
为什么不是简单组合：
如果只生成子题，会接近 ReCoVERR 或 test-time warmup；必须证明子题顺序和许可条件由少样例策略学习得到。
可实验数据集：
GQA、A-OKVQA、OK-VQA、MMMU、VL-ICL Bench。
主要风险：
Test-Time Warmup、ReCoVERR、RAM-TTT 等已有“测试时生成辅助任务/补证据/检索训练”思路，创造性不稳。
```

```text
候选名称：少样例多答案分歧模式迁移的答案改写方法
解决的具体技术问题：
开放式 VQA 中，模型多次采样答案分歧，但不同分歧模式对应的处理动作不同：同义词可合并，视觉证据冲突应拒答，表述粒度差异应降级回答。
输入：
少量校准样例、多次采样答案、候选证据、问题类型。
核心处理步骤：
1. 从校准样例中学习分歧模式到动作的映射。
2. 对测试问题多次采样候选答案。
3. 聚类分歧答案并匹配分歧模式。
4. 输出合并答案、限定答案或拒答。
输出：
改写后的答案和分歧处理原因。
为什么不是简单组合：
比采样一致性多一步“分歧模式-回答动作”的少样例迁移。
可实验数据集：
VQAv2、OK-VQA、VizWiz。
主要风险：
容易被 Avg BLEU、sampling diversity、self-consistency 和答案归一化覆盖，除非和声明级证据许可绑定。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 如果只是把 TTA、LoRA、soft prompt 或 conformal calibration 用到 VQA，是应用场景替换。
  - 最佳候选的抗辩点在于：少量样例学习的不是模型参数、prompt token 或答案阈值，而是问题类型对应的证据检查程序和回答许可动作。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 不能写成“检索相似样例后让模型参考回答”，那就是 few-shot/RAG。
  - 不能写成“让模型解释后自检”，那就是 CoT/self-check。
  - 不能写成“低于阈值拒答”，那就是选择性预测。
  - 必须强调声明级证据检查、策略表更新、许可/降级/阻断动作，这些动作由少量样例中的错误模式和证据需求归纳得到。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 存在风险，因为证据检查可能调用 grounding、OCR、detector、captioner。
  - 抗辩方式：这些模块只是证据检查器，发明核心是根据少量样例自适应选择和加权检查器，并对候选答案声明执行许可状态转换。没有少样例策略表时，普通 grounding/VQA/OCR 组合不会自动得到这种回答动作控制。

- 是否能被一篇或几篇论文自然组合推出？
  - 强攻击组合：TPT 或 MAPD 提供测试时/小样本适配；Selectively Answering Visual Questions 或 Variational VQA 提供选择性回答；ReCoVERR 提供低置信补证据；LIVE/AAPE 提供少样例表示压缩。审查员可能说自然组合即可得到“少样例自适应拒答”。
  - 反击关键：上述组合通常优化 prompt、参数、置信分数或补充证据；它们没有把少量样例显式转换为“问题类型-证据检查项-许可动作”的可执行策略，也没有对答案声明逐条执行 allow/revise/abstain。

- 是否缺少可验证技术效果？
  - 若只声称“更可信”会很弱。
  - 可验证指标应包括：在相同 coverage 下提高 selective accuracy；在相同 risk 下提高 coverage；降低 hallucination 或 unanswerable false answer；减少过度拒答；提升 evidence-grounded answer ratio；在 5/10/20-shot 校准样例下随样例数稳定改善。

## 6. 本轮最佳候选

最佳候选：少样例证据许可策略自适应的图像问答方法。

- 为什么选它：
  - 它避开了最拥挤的“少样例提升准确率”和“测试时更新 prompt/参数”路线，把创新点放在回答控制层。
  - 它能吸收 few-shot、TTA、online calibration 的需求，但核心技术动作是策略归纳和声明级许可，不是现有方法的直接同义替换。
  - 它和图像问答中的幻觉、拒答、证据一致性都直接相关，容易设计快速实验，也适合写成算法步骤。

- 为什么淘汰其他候选：
  - “覆盖-风险曲线在线校准”太接近选择性预测和置信度阈值，创造性弱。
  - “测试时辅助子题热身”容易撞上 ReCoVERR、Test-Time Warmup 和 test-time training，且计算成本高。
  - “多答案分歧模式迁移”有价值，但容易被 sampling diversity、self-consistency、Avg BLEU 和答案归一化覆盖，除非作为最佳候选中的一个证据检查项。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - “根据少量校准样例生成问题类型对应的证据许可策略表；将待测图像问答的候选答案拆分为声明单元；依据所述证据许可策略表选择证据检查项并对每个声明单元执行许可、降级、阻断或拒答动作；根据各声明单元的许可状态生成最终回答。”
  - 权利要求不要把重点写成“使用 few-shot examples 调整 prompt”或“根据置信度拒答”，这两个都很容易被现有技术覆盖。

- 如果做实验，最快怎么证明：
  - 选 VizWiz 或 UNK-VQA 做 answerable/unanswerable 场景，选 VQAv2/GQA 做数量、属性、关系三类问题。
  - 每类只取 5/10/20 个校准样例，人工标注或用已有标注推导证据需求和错误类型。
  - Baseline：zero-shot VLM、few-shot prompt、confidence threshold、sampling consistency、ReCoVERR-style related-question evidence。
  - 指标：selective accuracy、coverage@risk、ECE、unanswerable false-answer rate、over-abstention rate、声明证据通过率。
  - 预期最快可验证效果：在相同错误率下回答更多可回答问题，或在相同覆盖率下降低不可回答问题的误答率；同时给出每个回答被允许或阻断的策略项。
