# Round 06：视觉幻觉 / 不确定性 / 拒答方向

## 1. 本轮方向

- 方向名称：视觉幻觉、不确定性校准、选择性回答与证据不足拒答
- 检索范围：2021-2026 VLM hallucination、visual hallucination detection、uncertainty calibration、selective answering、abstention、counterfactual hallucination、visual conflict；优先 CVPR/ICCV/ECCV/NeurIPS/ICLR/AAAI/ACL/EMNLP。
- 目标问题：找到一个比“置信度低就拒答”“生成后再检测幻觉”“让模型自检”更有技术壁垒的 VQA 创新点，使模型能在视觉证据不足、视觉与语言先验冲突、局部证据冲突时按声明粒度决定回答、降级或拒答。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---:|---:|---|---|---|
| 1 | Evaluating Object Hallucination in Large Vision-Language Models / POPE | EMNLP | 2023 | 用轮询式二分类问题评估对象是否被模型错误确认，强调共现偏置和指令数据分布对对象幻觉的影响。 | VQA 中的 yes/no 对象存在问题是幻觉高发场景，可作为拒答和证据不足评测基线。 | https://openreview.net/forum?id=xozJw0kZXF |
| 2 | Detecting and Preventing Hallucinations in Large Vision Language Models / M-HalDetect, FDPO | arXiv / ScaleAI | 2023 | 建立细粒度幻觉标注数据集，按实体、描述、关系标注准确/不准确，并用 fine-grained DPO 或 reward model 降低幻觉。 | 说明后验检测和偏好优化已是成熟路线，单纯“训练检测器再过滤回答”风险很高。 | https://ar5iv.org/html/2308.06394 |
| 3 | OPERA: Over-Trust Penalty and Retrospection-Allocation | CVPR | 2024 | 基于注意力聚合模式发现“过度信任摘要 token”导致忽视图像 token，在解码时加惩罚并回滚重选 token。 | 对 VQA 开放生成有用，但核心是解码级幻觉缓解，不处理“哪些问题应拒答”。 | https://arxiv.org/html/2311.17911v3 |
| 4 | Mitigating Object Hallucinations through Visual Contrastive Decoding / VCD | CVPR | 2024 | 对原图和扰动图的输出分布做对比，削弱统计偏置和语言先验导致的对象幻觉。 | 证明“视觉冲突/扰动对比”已有基础；不能把“加扰动看一致性”直接作为新点。 | https://www.computer.org/csdl/proceedings-article/cvpr/2024/530000n872/20hOoxn4ypW |
| 5 | Multi-Modal Hallucination Control by Visual Information Grounding / M3ID | CVPR | 2024 | 用多模态互信息解码放大视觉提示对生成 token 的影响，减少语言先验主导。 | 说明“增强视觉 grounding 的解码方法”已成熟，候选必须跳出纯解码调参。 | https://openaccess.thecvf.com/content/CVPR2024/html/Favero_Multi-Modal_Hallucination_Control_by_Visual_Information_Grounding_CVPR_2024_paper.html |
| 6 | Selectively Answering Visual Questions | Findings ACL | 2024 | 分析 in-context LMM 的 VQA 校准和选择性回答，比较 likelihood、采样等不确定性指标，并提出 Avg BLEU 校准分数。 | 直接覆盖“校准后决定回答/拒答”，普通置信度阈值创新性弱。 | https://aclanthology.org/2024.findings-acl.250/ |
| 7 | Selective “Selective Prediction”: ReCoVERR | arXiv / CL | 2024 | 低置信时不立即拒答，而是生成相关视觉子问题，收集高置信证据，证据足够才回答。 | 与本项目接近：已覆盖“证据补充减少过度拒答”，但其证据主要是辅助问答链，不是声明级许可状态。 | https://arxiv.org/html/2402.15610 |
| 8 | Consistency and Uncertainty for Selective VQA | arXiv | 2024 | 黑盒 VLM 下通过问题邻域重述采样，利用回答一致性识别不可靠响应。 | 已覆盖“语义等价改写 + 一致性拒答”，不能把多问几遍作为核心创新。 | https://arxiv.org/html/2404.10193 |
| 9 | VL-Uncertainty: Detecting Hallucination via Uncertainty Estimation | arXiv | 2024 | 对视觉和文本做语义等价扰动，聚类回答语义并用分布熵作为幻觉检测信号。 | 直接覆盖“扰动一致性 + 熵检测幻觉”，对本轮候选构成强近似现有技术。 | https://arxiv.org/html/2411.11919v2 |
| 10 | Certainly Uncertain | arXiv | 2024 | 区分 VLM 的 epistemic / aleatoric uncertainty，构造 answerable 与 unanswerable 对比 VQA 样本，并用 confidence-weighted accuracy 评估校准。 | 支持“不可回答样本”的实验设计，但不提供声明级冲突处置机制。 | https://arxiv.org/abs/2407.01942 |
| 11 | What if...?: Counterfactual Keywords | Findings EMNLP | 2024 | 通过自生成反事实关键词和 plausibility verification process 触发模型考虑替代场景，降低跨模态不一致回答。 | 覆盖“反事实提示减幻觉”；候选若只做 counterfactual prompt 会被打掉。 | https://aclanthology.org/2024.findings-emnlp.626/ |
| 12 | Calibrated Self-Rewarding Vision Language Models | NeurIPS | 2024 | 模型生成候选、按视觉约束自评奖励、构造偏好数据迭代微调以改善模态对齐。 | 自奖励/自检方向已有强论文，单纯“让模型自己评估答案是否可靠”不稳。 | https://openreview.net/forum?id=nXYedmTf1T |
| 13 | Unified Triplet-Level Hallucination Evaluation | arXiv | 2024 | 从回答中抽取 object-relation-object 三元组，用 NLI/GPT judge 评估对象与关系幻觉。 | 提示“关系声明”是对象幻觉之外的关键粒度，但主要仍是评测/后验判断。 | https://arxiv.org/html/2410.23114v1/ |
| 14 | Multi-Object Hallucination in VLMs / ROPE | NeurIPS | 2024 | 研究多对象场景下的对象级幻觉，使用视觉 referring prompts 降低指代歧义。 | 指向真实 VQA 难点：多对象、干扰物和指代冲突容易诱发错误确认。 | https://openreview.net/forum?id=KNrwaFEi1u |
| 15 | Generate, but Verify / REVERSE | NeurIPS | 2025 | 结合幻觉验证训练和推理时 retrospective resampling，在生成中检测并动态修正幻觉。 | 强化“生成中验证”趋势，单纯后验删改已缺少新颖性。 | https://nips.cc/virtual/2025/loc/san-diego/poster/120029 |
| 16 | HII-DPO: Hallucination-Inducing Counterfactual Images | arXiv | 2026 | 合成“移除对象但保留场景”的反事实图像，揭示模型会补全场景典型对象，并用于 DPO。 | 对“视觉冲突/反事实缺证”很相关，但重点是数据构造与偏好优化。 | https://arxiv.org/html/2602.10425v1 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - VLM 幻觉不再只被看作“模型说错对象”，而是被拆成对象存在、属性、关系、数量、空间关系、多对象指代、视觉语言冲突、answerability 等细粒度问题。
  - 主流技术路线集中在四类：解码时削弱语言先验；训练/偏好优化提高视觉对齐；后验幻觉检测与修正；选择性回答和不确定性校准。
  - 2024 之后，“不确定性”已经从简单 softmax 分数转向语义等价扰动、采样一致性、熵、校准误差、answerable/unanswerable 对比样本。
  - “视觉冲突”成为重要触发条件：文本先验或场景先验强烈指向某对象，但局部视觉证据缺失或相反时，模型容易确认不存在的对象。

- 已经成熟、不能作为创新点的部分：
  - 用置信度、log-likelihood、entropy 或一致性分数设阈值决定拒答。
  - 对同一问题做重述、扰动、采样，多次问模型后用一致性判断可靠性。
  - 生成答案后用另一个 VLM/LLM/NLI judge 检测幻觉，再删除或改写。
  - 用 DPO/RLHF/reward model 训练模型少幻觉。
  - 用原图与噪声图/遮挡图做视觉对比解码。
  - 把回答拆成三元组或子句后做事实性检测，如果只作为评测或后处理，创新性不足。

- 仍有空白或可迁移空间的部分：
  - 很多方法判断“整个答案是否可靠”，但 VQA 答案内部常包含多个声明；真正需要的是对每个声明判定证据是否足以许可输出。
  - 现有选择性回答多以“答/不答”为二元决策，缺少“支持、冲突、不足、越权、降级、阻断、许可”等中间状态。
  - 视觉冲突处理仍常停留在扰动分布或后验检测，较少把“冲突证据”转成可追踪的输出许可规则。
  - 对拒答的技术效果通常只看准确率/覆盖率，较少验证“错误声明被阻断、可支持声明仍保留、过度拒答减少”的声明级效果。

## 4. 候选创新点

```text
候选名称：声明级视觉证据许可状态机
解决的具体技术问题：
VQA 模型在一个回答中混合可证实声明、缺证声明和与图像冲突的声明时，普通置信度阈值只能对整个答案拒答或放行，导致过度拒答或带幻觉输出。
输入：
用户问题、图像、VLM 初始候选答案、候选答案拆分出的原子声明、每个声明对应的视觉证据需求。
核心处理步骤：
1. 将候选答案拆分为原子视觉声明，例如对象存在、属性、数量、空间关系、文字读取、关系推断。
2. 为每个声明生成证据需求，包括必须观察的视觉区域、属性槽、关系槽，以及允许使用的辅助证据类型。
3. 对每个声明执行多视角证据匹配：原图局部证据、反事实遮挡后证据变化、语义等价问题下的回答稳定性、冲突探针问题的反向证据。
4. 将证据匹配结果映射为有限许可状态：支持、冲突、不足、越权、降级、阻断、许可。
5. 输出阶段只允许“支持/许可”的声明进入最终回答；“不足”转为限定性表述或询问补充；“冲突/越权”触发局部拒答，不影响其他已支持声明。
输出：
带许可状态的声明列表，以及由被许可声明组成的最终 VQA 回答；必要时输出局部拒答理由。
为什么不是简单组合：
核心不在于使用某个置信度或检测器，而在于把回答生成问题转成“声明-证据需求-许可状态-输出门控”的状态转移；同一个答案可局部放行、局部降级、局部阻断。
可实验数据集：
VizWiz、VQA 2.0/A-OKVQA selective answering、TextVQA、POPE、M-HalDetect、ROPE、Tri-HE、Certainly Uncertain、HII/MOH 类反事实样本。
主要风险：
声明拆分和证据需求生成本身可能依赖 LLM；如果状态转移规则过于手写，容易被认为是业务规则或常规后处理。
```

```text
候选名称：视觉冲突触发的最小反证探针拒答
解决的具体技术问题：
当语言先验和图像局部证据冲突时，模型往往给出流畅但无视觉依据的答案；普通自检会被原始答案锚定。
输入：
用户问题、图像、初始答案、从初始答案抽取的高风险对象/属性/关系声明。
核心处理步骤：
1. 识别容易由场景先验补全的声明，例如“厨房里有刀”“桌上有杯子”等。
2. 为每个高风险声明生成最小反证探针：不存在性问题、属性取反问题、遮挡/裁剪局部问题、同类干扰对象问题。
3. 比较原声明与反证探针在局部视觉区域上的证据响应，形成冲突图。
4. 只有当原声明证据强于反证探针并满足局部区域一致时才许可输出，否则触发局部拒答或改为“不确定是否存在”。
输出：
每个高风险声明的冲突强度、反证探针结果和局部拒答/许可决策。
为什么不是简单组合：
不是随机 perturbation 或多问几遍，而是针对“原声明的最小可否定条件”生成反证探针；目标是发现语言先验补全造成的视觉冲突。
可实验数据集：
POPE adversarial/popular split、HII-DPO/MOH、ROPE、Visual Genome relation questions、VLR-IF 干扰项样本。
主要风险：
与 VCD、HII-DPO、Counterfactual Inception 很接近，容易被认为是反事实探针或对比解码的自然延伸。
```

```text
候选名称：拒答预算约束的证据补采样选择器
解决的具体技术问题：
选择性 VQA 为降低错误率会过度拒答；证据补采样可以减少拒答，但若无限追加子问题会增加成本且引入新幻觉。
输入：
用户问题、图像、初始答案、初始不确定性、候选补证据子问题集合、成本预算。
核心处理步骤：
1. 对初始答案中的待确认声明估计错误风险和拒答收益。
2. 为每个声明生成可降低不确定性的补证据动作，例如局部放大、OCR 子问、对象存在子问、关系子问。
3. 按“单位成本预期风险下降”选择补证据动作，而非固定问若干轮。
4. 当补证据收益不足时停止采样并拒答；当关键声明达到证据许可状态时输出。
输出：
补证据动作序列、最终回答/拒答决策、拒答预算消耗记录。
为什么不是简单组合：
引入成本约束和声明级收益评估，避免 ReCoVERR 式证据收集被泛化成“低置信就多问几个问题”。
可实验数据集：
VQAv2、A-OKVQA、VizWiz、TextVQA、GQA、OK-VQA。
主要风险：
ReCoVERR 已经覆盖“低置信时收集相关视觉证据以减少过度拒答”，本候选必须在预算优化和声明级动作收益上做得很具体才有区别。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 对候选 1 的攻击：把文本事实核查的“claim-level verification”搬到 VQA，并不天然构成创新；如果只写“将答案拆成声明并验证”，会被认为是已有事实核查流程在图像问答中的直接应用。
  - 抗辩要点：必须把“视觉证据需求”和“许可状态转移”写成核心技术动作，而不是泛泛事实核查。尤其要强调同一回答内的局部许可、局部降级、局部阻断，而非整体拒答。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 对候选 1 的攻击：声明状态最后还是依赖一个分数，实质可能是置信度阈值；证据需求也可能只是让模型自检“图片中是否有证据”。
  - 抗辩要点：不能把“阈值高低”作为独立权利要求核心。要抓住离散状态转移条件，例如“存在支持证据但冲突探针更强时进入冲突状态”“OCR 证据缺失但对象存在证据充分时进入降级状态”“关系证据不足但对象证据充分时阻断关系声明而保留对象声明”。这些不是普通单分数阈值。
  - 对候选 2 的攻击：最小反证探针很像 counterfactual prompt、自检或扰动一致性。
  - 对候选 3 的攻击：低置信时补采样和 ReCoVERR 高度接近，可能只是选择性预测的常规优化。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - 候选 1 的风险中等：它可能调用 grounding、OCR、关系检测、VQA 子问作为证据源，但创新点不应落在这些模块本身。
  - 有效写法：把外部工具都降格为“证据产生器”，核心权利要求限定在“按声明类型生成证据需求、聚合支持/冲突/不足信号并驱动许可状态机输出”。

- 是否能被一篇或几篇论文自然组合推出？
  - 强攻击组合：POPE/ROPE 提供对象幻觉评测，Tri-HE 提供三元组级幻觉评测，VL-Uncertainty 提供扰动熵，ReCoVERR 提供补证据减少拒答。审查员可能认为组合后自然得到“逐声明判断可靠性后拒答”。
  - 抗辩要点：现有组合仍多是评测分数或整体选择性预测，缺少“状态机式输出许可”。要把技术效果限定为：在同一答案中保留被支持声明，同时阻断冲突声明，并减少整体拒答造成的信息损失。

- 是否缺少可验证技术效果？
  - 候选 1 可验证，但必须设计声明级指标：unsupported claim rate、conflicted claim block rate、supported claim retention rate、selective risk-coverage、over-abstention rate。
  - 如果只报告 VQA accuracy、POPE accuracy 或 hallucination rate，难以体现状态机贡献。

- 是否只是普通置信度阈值？
  - 候选 1 如果实现为“证据分数大于阈值则回答，小于阈值则拒答”，会被直接打掉。
  - 应改成多条件状态迁移：不同声明类型有不同证据槽；支持证据、冲突证据、缺失证据分别进入不同状态；最终输出是状态驱动的局部改写，而非一个全局阈值。

- 是否只是自检？
  - 如果让 VLM 生成答案后再问“你确定吗/图片是否支持吗”，就是自检。
  - 候选 1 必须要求独立的证据需求生成与反向冲突探针，并记录每个声明的证据许可状态；自检文本不能直接决定最终放行。

- 是否只是后验检测？
  - 如果完整答案已经生成，再标出哪句幻觉并删除，就是后验检测/修正。
  - 候选 1 的专利写法应强调“输出前门控”：候选声明在进入最终自然语言答案前必须取得许可状态，未许可声明不进入生成约束或被强制降级表达。

## 6. 本轮最佳候选

本轮最佳候选：**声明级视觉证据许可状态机**。

- 为什么选它：
  - 它最符合当前项目主线“声明级证据许可状态机”，也最能避开普通校准、扰动一致性、自检、后验检测的拥挤现有技术。
  - 该候选把拒答从“整个问题答或不答”改成“每个视觉声明是否允许进入最终回答”，可形成更清晰的技术效果：减少幻觉声明，同时降低过度拒答。
  - 它能吸收不确定性、视觉冲突、反事实探针、OCR/grounding 证据，但不把这些成熟模块当创新点。

- 为什么淘汰其他候选：
  - “视觉冲突触发的最小反证探针拒答”有价值，但与 VCD、HII-DPO、Counterfactual Inception、VL-Uncertainty 的距离不够远；容易被解释为反事实扰动和一致性检测的自然组合。
  - “拒答预算约束的证据补采样选择器”工程上实用，但 ReCoVERR 已经覆盖低置信时生成相关视觉证据以减少过度拒答；除非把成本收益模型写得非常硬，否则专利风险偏高。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“对候选答案拆分得到的各原子视觉声明，按声明类型生成证据需求；基于支持证据、冲突证据和缺失证据将每个声明映射到预设许可状态；依据许可状态对最终回答执行声明级放行、降级或阻断”的技术动作。
  - 不要把权利要求核心写成“计算置信度并与阈值比较”“多次询问模型并检查一致性”“生成后检测幻觉”。

- 如果做实验，最快怎么证明：
  - 数据：优先用 VizWiz 的不可回答样本、POPE adversarial/popular、TextVQA/OCR 缺证样本、Tri-HE 关系声明、ROPE 多对象样本。
  - 模型：用 Qwen2-VL 或 LLaVA 系列产生初始回答，再加状态机门控。
  - 基线：原始模型、置信度阈值拒答、VL-Uncertainty/一致性拒答、ReCoVERR 式补证据、后验 hallucination detector。
  - 指标：unsupported claim rate 下降、conflicted claim block rate 上升、supported claim retention rate 保持、overall over-abstention rate 下降、risk-coverage 曲线优于普通阈值。
  - 最小验证：构造 200-500 条带对象/属性/关系/文字证据的声明级标注样本，比较“整答拒答”和“声明级许可”在保留正确信息与阻断错误信息上的差异。
