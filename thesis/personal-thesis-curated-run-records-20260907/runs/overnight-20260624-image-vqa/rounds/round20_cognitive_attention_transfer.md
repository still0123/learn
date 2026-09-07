# Round 20：认知科学 / 人类视觉注意迁移方向

## 1. 本轮方向

- 方向名称：认知科学 / 人类视觉注意 / 人类不确定性迁移到图像问答证据许可
- 检索范围：cognitive vision、visual attention、eye-tracking VQA、human uncertainty、human-in-the-loop visual reasoning、selective VQA、gaze-guided VLM
- 目标问题：把“人看哪里、何时不确定”从训练数据或交互信号，转化为图像问答系统在生成声明前的证据许可机制，而不是简单把 gaze heatmap 当作额外输入或 prompt。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | VQA-MHUG: A Gaze Dataset to Study Multimodal Neural Attention in Visual Question Answering | CoNLL | 2021 | 采集 49 名参与者在回答 VQA 时对图像和问题文本的注视数据，分析人类注意与神经注意的相关性 | 证明 VQA 不仅需要图像区域注意，也需要问题文本注意；文本注意与性能显著相关 | https://aclanthology.org/2021.conll-1.3/ |
| 2 | Selectively Answering Visual Questions | Findings of ACL | 2024 | 分析多模态大模型在 VQA 中何时回答、何时拒答或澄清；比较 likelihood、采样和 Avg BLEU 等校准信号 | 直接对应图像问答的“答/拒答”选择，但主要还是模型置信度与校准 | https://aclanthology.org/2024.findings-acl.250/ |
| 3 | Mind the Uncertainty in Human Disagreement: Evaluating Discrepancies between Model Predictions and Human Responses in VQA | arXiv | 2024 | 用人类回答分布和 human uncertainty in disagreement, HUD, 衡量模型是否贴近人类分歧 | 说明 VQA 中“人类不确定”是可度量对象，不能只用单一多数票标签训练或评估 | https://arxiv.org/html/2410.02773v1 |
| 4 | Selective “Selective Prediction”: Reducing Unnecessary Abstention in Vision-Language Reasoning / ReCoVERR | arXiv | 2024 | 对低置信度预测生成相关视觉证据问题，检查证据可靠性、相关性和充分性，减少不必要拒答 | 和证据许可非常接近，但其核心是低置信度后的证据补充，未引入人类注意/不确定性作为许可标准 | https://arxiv.org/html/2402.15610 |
| 5 | GazeLLM: Multimodal LLMs incorporating Human Visual Attention | arXiv / AHs | 2025 | 对第一人称视频按注视点裁剪局部输入，用约十分之一像素达到相当或更好的任务理解 | 证明 gaze 可作为计算资源分配和证据选择信号，但偏视频活动理解，不是声明级证据许可 | https://arxiv.org/html/2504.00221 |
| 6 | In the Eye of MLLM: Benchmarking Egocentric Video Intent Understanding with Gaze-Guided Prompting / EgoGazeVQA | arXiv | 2025 | 构建 gaze-guided egocentric video QA，注视提示整合空间、时间和意图线索 | 证明注视可表达用户意图，尤其适合解决“用户问的是哪个对象/动作”的歧义 | https://arxiv.org/html/2509.07447v1 |
| 7 | Gaze-VLM: Eye-Tracking Informed Multimodal Large Language Models | OpenReview | 2025/2026 | 实时 VQA 中使用用户提问前附近的 fixations 消解指代歧义，训练无关地引导 VLM | 直接相关，但重点是指代消歧；作为未正式发表/withdrawn submission，专利查新时只能作趋势参考 | https://openreview.net/forum?id=RWOpRDABEr |
| 8 | Human Uncertainty-Aware Data Selection and Automatic Labeling in Visual Question Answering / HaDola | arXiv | 2025 | 利用人类不确定性选择训练样本、自动标注和校准，降低有害高不确定样本影响 | 说明 human uncertainty 可用于数据选择和校准，但未把不确定性转为推理时的“声明许可状态” | https://arxiv.org/html/2510.11295v1 |
| 9 | DriVQA: A gaze-based dataset for visual question answering in driving scenarios | Data in Brief | 2025 | 在驾驶场景中采集图像、问题、参与者答案、gaze plots 和 heatmaps | 提供高风险场景下 gaze 与回答主观性的 VQA 数据，可用于验证注意偏移/证据不足 | https://pubmed.ncbi.nlm.nih.gov/40027252/ |
| 10 | MagiC: Evaluating Multimodal Cognition Toward Grounded Visual Reasoning | arXiv | 2025 | 评估答案、推理步骤、grounding fidelity 和自纠错能力 | 强调“看对区域”与“推理正确”之间的关系，可作为证据许可实验基准 | https://arxiv.org/html/2507.07297v1 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - VLM 是否真的使用了视觉证据，而不是靠语言先验、数据偏差或高频答案。
  - 模型何时应回答、拒答、澄清，尤其是面向无障碍、驾驶、医疗等高风险 VQA 场景。
  - 人类 gaze/fixation/scanpath 是否能作为用户意图、证据关注区域和认知负荷的外部信号。
  - 人类回答分歧和不确定性是否应进入模型训练、校准和评估，而不是被多数票标签抹平。

- 已经成熟、不能作为创新点的部分：
  - 直接把 gaze heatmap 叠到图像上作为视觉提示。
  - 根据注视点裁剪局部区域，再送入 VLM。
  - 用模型置信度阈值决定拒答。
  - 用人类 gaze 监督模型 attention 或做 attention alignment loss。
  - 用人类答案分布做校准、数据选择或样本重加权。

- 仍有空白或可迁移空间的部分：
  - 现有工作多把 gaze 当“输入增强”或“注意监督”，很少把 gaze 与每个答案声明的证据需求绑定。
  - 现有 selective VQA 更依赖模型内部置信度，没有明确区分“模型不确定”和“人类在同类问题上本来就不确定”。
  - 对于歧义问题，gaze 可以消解用户意图；对于证据不足问题，人类 gaze 的分散、反复回扫和低一致性可作为“证据不可许可”的信号。
  - 可以把人类注意模板从训练集/少量标注集蒸馏成“认知证据先验”，推理时不要求真实眼动设备，只要求预测出该问题类型下人类应关注的候选证据区。

## 4. 候选创新点

```text
候选名称：
认知注视一致性约束的声明级证据许可状态机

解决的具体技术问题：
图像问答模型经常在看错区域、视觉证据不足或人类本身高度分歧的问题上仍输出确定性答案。现有方法通常用模型置信度或后验自检拒答，无法区分“答案声明是否落在人类应关注证据范围内”，也无法识别“模型很自信但证据关注路径不符合人类认知注意”的越权声明。

输入：
1. 图像 I；
2. 用户问题 Q；
3. 待输出答案或候选答案 A；
4. 从 A 拆出的声明集合 C={c1...cn}；
5. 问题类型对应的人类认知注意先验 H，包括预期关注区域分布、问题词关注权重、允许的注视分散度、人类回答分歧等级；
6. 模型实际证据 E，包括候选区域、区域描述、OCR/对象/关系证据、模型内部或外部 grounding 分数。

核心处理步骤：
1. 对问题 Q 进行认知证据需求解析，判断每个声明 ci 需要的视觉证据类型，例如对象属性、空间关系、计数、文本读数、意图指代或常识补全。
2. 根据问题类型检索或预测人类注意先验 H，生成“应被观察的证据窗口”，包括关键图像区域、关键问题词和可接受的注意分散范围。
3. 为每个声明 ci 计算三类一致性：
   a. 证据覆盖一致性：模型用于支持 ci 的区域是否落入或覆盖 H 的高关注区域；
   b. 注意路径一致性：模型从问题词到图像区域的跨模态证据链是否与人类常见关注顺序一致，例如先定位对象再读取属性；
   c. 分歧许可一致性：当 H 显示同类问题人类回答分歧高或 gaze 分散时，ci 是否被降级为不确定/需澄清，而非确定性声明。
4. 将每个声明 ci 映射到许可状态：PERMIT、DOWNGRADE、CLARIFY、INSUFFICIENT_EVIDENCE、CONFLICT、BLOCK。
5. 对答案 A 进行声明级改写：许可声明保留；降级声明添加不确定限定；冲突或越权声明删除或触发拒答/澄清。

输出：
1. 最终答案；
2. 每个声明的证据许可状态；
3. 被采用/拒绝的证据区域；
4. 若拒答或澄清，输出缺失的证据类型，而不是泛泛说“我不确定”。

为什么不是简单组合：
该机制不是“gaze + VQA”或“置信度阈值 + 拒答”。核心技术动作是把人类注意和人类不确定性转译为声明级许可条件：同一个答案中不同声明可因证据覆盖、注意路径和人类分歧等级不同而分别许可、降级或阻断。gaze 不是直接提示模型回答，而是约束声明是否有资格被输出。

可实验数据集：
VQA-MHUG、VQAv2、VizWiz、A-OKVQA、DriVQA、MagiC；若做图表或可视化扩展，可用 SalChartQA。

主要风险：
1. 如果只实现为 gaze heatmap overlap 分数，容易被认为是 attention alignment 的常规应用。
2. 若缺少真实 gaze 数据，需说明人类注意先验可由少量 gaze 数据、公开 gaze 数据或问题类型统计蒸馏得到。
3. 审查员可能认为 ReCoVERR 已经有证据可靠性/相关性/充分性检查，需要突出本方案的“认知注意先验 + 人类分歧许可”而不是单纯补证据。
```

```text
候选名称：
提问前注视峰值驱动的歧义对象许可机制

解决的具体技术问题：
当图像中存在多个候选对象，用户使用“这个”“那个”“左边那个”等不完整指代时，VLM 难以判断问题目标，容易回答错误对象。

输入：
图像、问题、用户提问前后短时间窗内的 gaze fixations 或估计注视点、候选对象检测框、候选答案。

核心处理步骤：
1. 检测问题中的指代歧义；
2. 在提问开始前的时间窗内聚合 fixation；
3. 将 fixation 与候选对象框匹配；
4. 只有被 gaze 峰值支持的对象声明被许可输出；
5. 若多个对象得分接近，则输出澄清问题。

输出：
被许可的目标对象、答案、或澄清请求。

为什么不是简单组合：
它把 gaze 时间窗限定为“提问前意图窗口”，比普通 gaze prompt 更具体。

可实验数据集：
Gaze-VLM benchmark、EgoGazeVQA、DriVQA、人工构造多对象 VQA。

主要风险：
该方向已被 Gaze-VLM/EgoGazeVQA 很接近地覆盖，专利新颖性压力较大；且依赖真实眼动设备，通用图像 VQA 落地范围窄。
```

```text
候选名称：
人类不确定性分布约束的 VQA 拒答/澄清门控

解决的具体技术问题：
VQA 中存在人类天然分歧问题，例如图像模糊、遮挡、主观属性判断。模型若只依据自身置信度，可能在高人类分歧问题上过度确定，也可能在低分歧问题上过度拒答。

输入：
图像、问题、候选答案、模型置信度、人类回答分布或 HUD 预测器。

核心处理步骤：
1. 预测样本的人类分歧等级；
2. 将模型置信度与人类分歧等级联合校准；
3. 高模型置信度但高人类分歧时，触发降级表达或澄清；
4. 低模型置信度但低人类分歧时，触发补证据而非直接拒答；
5. 输出回答/拒答/澄清三态。

输出：
选择性回答策略和校准后的不确定性。

为什么不是简单组合：
引入人类分歧作为拒答门控的基准，而不是只看模型自身置信度。

可实验数据集：
VQAv2 多标注答案、VizWiz、HUD 相关划分、CERTAINLYUNCERTAIN。

主要风险：
与 HUD、HaDola、selective answering 的距离较近；如果没有声明级证据许可动作，容易被认为只是校准或数据选择。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对“提问前注视峰值驱动的歧义对象许可机制”攻击成立风险高。现有 Gaze-VLM/EgoGazeVQA 已经把 gaze 用于 VQA 指代消歧和意图理解，若只是从视频/实时交互换到静态图像，创造性不足。
  - 对“人类不确定性分布约束的 VQA 拒答/澄清门控”也有一定风险。已有 HUD、HaDola、selective VQA 都讨论人类不确定性或选择性回答。
  - “认知注视一致性约束的声明级证据许可状态机”较强，因为它不是换场景，而是把认知信号转成声明输出前的许可条件。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 若实现为“模型生成答案后自问是否看到了证据”，会被打成 self-check。
  - 若实现为“低置信度拒答”，会被打成置信度阈值。
  - 最佳候选需要强调：许可依据不是模型自我置信度，而是“声明所需证据是否覆盖人类注意先验、是否遵守注意路径、是否处在人类高分歧区域”。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 单独使用 grounding 检查答案区域，容易被认为是现有视觉 grounding。
  - 本轮候选必须避免 claim：“先做 grounding，再回答 VQA”。应抓住“人类认知注意先验定义了每类声明的可许可证据窗口”，这是 grounding 方法之外的判定规则。
  - OCR/图表方向不是本轮主轴，除非作为验证场景，不应写入核心权利要求。

- 是否能被一篇或几篇论文自然组合推出？
  - 审查员可能组合 VQA-MHUG + Selectively Answering Visual Questions + ReCoVERR，认为可得到“用人类注意改进选择性回答”。
  - 反驳点：这些论文分别处理注意相关性、拒答校准、低置信度补证据，并未教导“对每个答案声明生成认知证据需求，并根据人类注视一致性和人类分歧等级映射为许可/降级/阻断状态”。
  - 还可强调状态级输出效果：同一回答中一部分声明保留，一部分降级，一部分阻断，不是整题级二分类拒答。

- 是否缺少可验证技术效果？
  - 可验证。最快实验包括：
    - 在 VQA-MHUG 上比较错误答案中模型证据区域与人类 gaze 的偏离程度，验证许可状态能识别高风险样本。
    - 在 VizWiz/answerability benchmark 上比较拒答准确率、过度拒答率和错误回答率。
    - 在 MagiC 上比较 grounding fidelity、StepSense/MagiScore 与最终答案准确率。
    - 在 VQAv2 多标注答案上比较模型置信分布与人类答案分布的 ECE/KL/JS divergence。
  - 需要避免声称已得到实验数字；当前只写可验证路径。

## 6. 本轮最佳候选

最佳候选：认知注视一致性约束的声明级证据许可状态机。

- 为什么选它：
  - 它与项目主线“声明级证据许可状态机”一致，能把认知科学方向变成一个具体技术动作，而不是新加一个 gaze 模块。
  - 它同时吸收了 gaze、人类问题注意、人类回答分歧三个认知信号，但输出端统一为声明级许可状态，专利表达更集中。
  - 它能覆盖无真实眼动设备的普通 VQA 场景：训练或离线阶段用 gaze/HUD 数据蒸馏“认知注意先验”，推理时只需预测问题类型和应关注证据窗口。

- 为什么淘汰其他候选：
  - “提问前注视峰值驱动的歧义对象许可机制”太接近 Gaze-VLM/EgoGazeVQA，且依赖交互式眼动设备，适用面窄。
  - “人类不确定性分布约束的 VQA 拒答/澄清门控”与 HUD、HaDola、selective answering 距离近，若没有声明级处理，容易被看成校准方法。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“针对候选答案中的每个声明，根据问题类型生成认知证据需求；将模型证据区域/证据链与人类注意先验及人类分歧等级进行一致性计算；根据一致性结果把该声明映射为许可、降级、澄清、证据不足、冲突或阻断状态；再按状态改写或拒绝输出答案”。
  - 不建议把权利要求核心写成“获取眼动数据”或“使用 gaze heatmap”，因为这会被现有 gaze-guided VQA 直接压住。

- 如果做实验，最快怎么证明：
  - 第一步：在 VQA-MHUG 上构造规则版认知注意先验，用人类 gaze 区域和问题词关注权重标注“应关注证据窗口”。
  - 第二步：用现有 VLM 生成答案和 grounding/rationale，把答案拆成声明，计算声明证据与人类注意窗口的 overlap、路径一致性和分歧等级。
  - 第三步：在 VQAv2/VizWiz/MagiC 上比较三组策略：
    - baseline：直接回答；
    - confidence-only：置信度阈值拒答；
    - proposed：声明级认知注意许可。
  - 第四步：指标优先看错误回答率下降、过度拒答率、answerability F1、grounding fidelity、声明级 hallucination rate。只要能证明在相同覆盖率下错误声明更少，或在相同错误率下回答覆盖率更高，就足以支持技术效果。
