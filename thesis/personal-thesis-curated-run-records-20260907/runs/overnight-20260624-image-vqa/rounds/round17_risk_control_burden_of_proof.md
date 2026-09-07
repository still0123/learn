# Round 17：安全风控 / 证据负担迁移到图像问答

## 1. 本轮方向

- 方向名称：安全风控 / 合规证据链 / 证据负担迁移到高风险图像问答
- 检索范围：risk control、compliance evidence chain、burden of proof、audit trail、legal evidence reasoning、risk-based decision、AI governance logging、high-risk VQA hallucination、medical VQA trustworthiness。
- 目标问题：判断“证据负担”能否从法律/风控迁移为图像问答中的技术机制，即当答案声明风险升高时，系统不再用统一置信度输出，而是动态提高该声明所需的视觉、OCR、检索、反证和可追溯证据门槛。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | EU AI Act / AI governance audit trail practice | Regulation / compliance engineering | 2024-2026 | 高风险 AI 要记录输入、模型版本、置信度、人类覆盖、结果和解释，形成可追溯审计链 | 启发 VQA 不应只输出答案，还应保留声明级证据、版本、触发路径和降级原因 | https://theneuralbase.com/ai-for-finance/learn/advanced/compliance-considerations/ |
| 2 | Technical audit trails and defensible classification logs | AI governance article | 2025 | 风险分类必须基于显式系统属性、数据敏感性、上下文影响，并写入不可篡改日志 | 可迁移为 VQA 对问题/声明的风险分类与证据门槛绑定，而不是事后说明 | https://undercodetesting.com/beyond-the-badge-why-your-eu-ai-act-compliance-will-fail-without-technical-audit-trails-and-defensible-classification-logs-video/ |
| 3 | GxP Audit Trails for AI: 21 CFR Part 11 & Annex 11 Rules | Compliance analysis | 2024/2026 | 审计轨迹要求记录 who/when/what/why，强调 ALCOA+ 数据完整性 | 高风险视觉问答可把“回答为何被许可”变成可复查记录，便于错误归因 | https://intuitionlabs.ai/articles/audit-trail-requirements-ai-gxp-compliance |
| 4 | Judicial Requirements for Generative AI in Legal Reasoning | arXiv | 2025 | 司法推理中必须正确处理证据评估、事实真实性和 burden of proof；证据不足时应判为未证明 | 直接启发：VQA 对高风险声明也应有“未证明/证据不足”状态，而不是强答 | https://arxiv.org/html/2508.18880v1/ |
| 5 | Burden of Proof Reversal in AI Litigation | Legal analysis | 2024/2026 | AI 黑箱方若无法提供日志、文档、监控记录，法院可作不利推定 | 迁移为 VQA：当系统不能给出声明证据链时，应由系统承担不输出强声明的负担 | https://www.raphaelnagel.com/burden-of-proof-ai-litigation |
| 6 | Applying Daubert and Frye to AI Evidence | Legal evidence article | 2024 | AI 增强视频证据需满足可测试性、错误率、标准化、领域接受度等可靠性要求 | 启发视觉证据不能只看模型置信度，还要看证据生成工具/增强步骤本身是否可靠 | https://www.msba.org/site/site/content/News-and-Publications/News/General-News/Applying_Daubert_and_Frye_to_AI_Evidence.aspx |
| 7 | CARES: A Comprehensive Benchmark of Trustworthiness in Medical Vision Language Models | OpenReview | 2024 | 从真实性、公平、安全、隐私、鲁棒性评估医疗 VLM，发现事实错误和信任风险 | 医疗 VQA 是典型高风险场景，适合验证风险加权证据门槛 | https://openreview.net/forum?id=b6IBmU1uzw |
| 8 | NIH findings on GPT-4V medical decision-making | NIH / npj Digital Medicine report | 2024 | GPT-4V 可能答对最终诊断，但图像描述和推理解释仍出错 | 说明“最终答案正确”不足以许可高风险回答，声明级证据链更重要 | https://www.nlm.nih.gov/news/NIH_AI_medical_decision-making.html |
| 9 | Long-Form Answers to Visual Questions from Blind and Low Vision People | arXiv | 2025 | VizWiz-LF 显示长答案包含解释和建议，VLM 对不可回答问题很少拒答且会幻觉 | 真实辅助场景中，建议类/行动类回答需要更高证据负担 | https://i6172786976o6f7267z.oszar.com/html/2408.06303v2 |
| 10 | Generate, but Verify: REVERSE | NeurIPS | 2025 | 结合 hallucination-aware training 与 retrospective resampling，动态检测并修正幻觉 | 代表现有“生成后验证/修正”路线；本轮机制需区别于普通后验 verifier | https://nips.cc/virtual/2025/loc/san-diego/poster/120029 |
| 11 | GroundSight: Grounding and De-hallucination for VQA | arXiv / KDD Cup workshop | 2025 | 用文本 grounding 定位 ROI，裁剪检索并降低幻觉 | 说明 grounding + 去幻觉已成熟，不能把“高风险时先 grounding”当创新 | https://arxiv.org/html/2509.25669v1 |
| 12 | Improving Medical Diagnostics with VLMs: Convex Hull-Based Uncertainty Analysis | arXiv | 2024 | 通过温度采样响应的几何分布估计医疗 VQA 不确定性 | 说明不确定性估计已有；本轮候选应超越统一 uncertainty 分数 | https://arxiv.org/html/2412.00056v1/ |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
  - 高风险 AI 不再只追求准确率，而是要求可解释、可追溯、可审计、可复现的决策链。
  - 法律和合规场景强调“谁主张谁举证”：当系统输出会影响诊断、行动、安全、金融或法律后果时，证据不足不应被包装成确定结论。
  - 多模态 VQA 研究正在暴露一个风险：模型可能给出正确最终选项，却在图像描述、局部证据、推理路径上犯错。
  - 长答案 VQA 和辅助场景会生成建议、提醒、因果解释、风险判断，这些声明比普通对象识别更需要证据负担控制。
  - 医疗、无障碍、工业、交通、安全巡检等场景开始把“拒答/降级/请求更多图像”视为技术质量，而不只是用户体验。

- 已经成熟、不能作为创新点的部分：
  - 不能写“高风险问题提高置信度阈值”。风险阈值是风控和 ML calibration 的常规做法。
  - 不能写“输出答案时记录日志”。audit trail、model governance、GxP 电子记录已经成熟。
  - 不能写“让模型解释答案”。CoT、rationale、self-check、verifier 已经大量公开。
  - 不能写“图像问答中加入人工审核”。human-in-the-loop 是合规常规控制。
  - 不能写“遇到医疗/法律问题拒答”。这属于策略规则，不是算法机制。
  - 不能写“根据问题类别选择不同模型”。这是风险路由或业务编排。
  - 不能写“对高风险答案做事实核查”。fact-checking 和 post-hoc verification 已有大量工作。

- 仍有空白或可迁移空间的部分：
  - 现有 VQA 多把所有答案声明用同一个置信度或 verifier 评分处理，缺少按声明后果动态调节证据负担的机制。
  - 合规里的“证据负担”可以转化为技术动作：输出强度越高、潜在后果越高、可观察性越差，所需证据类型和数量越严格。
  - 高风险声明不一定要拒答；可以降级为观察性描述、条件性回答、需补充图像、需人工确认，这些动作可由状态转移驱动。
  - 可追溯日志不应是事后记录，而应参与生成控制：只有满足证据负担的声明才能进入最终答案。
  - 与普通 self-check 不同，证据负担机制可把“声明类型、风险等级、证据链完整度、冲突证据、输出动作”绑定为确定性决策表。

## 4. 候选创新点

```text
候选名称：风险加权证据负担调度器

解决的具体技术问题：
图像问答系统在医疗、工业、安全、无障碍等高风险问题中，常用统一置信度或统一拒答阈值控制输出，导致低风险观察声明和高风险诊断/行动建议被同等处理；当证据不足或证据链不可追溯时，模型仍可能输出强结论。

输入：
用户问题、图像、候选回答草稿、候选回答中的最小声明、图像局部证据/OCR/检测框/检索证据/反证证据、场景风险标签、声明后果标签、证据来源和模型版本信息。

核心处理步骤：
1. 将候选回答拆为最小声明，并为每个声明标注声明类型：可观察事实、数量/位置、身份识别、异常判断、诊断结论、行动建议、因果解释、外部知识。
2. 对每个声明计算风险负担向量，包括潜在伤害、不可逆性、领域敏感性、是否超出图像可观察范围、是否需要专业知识、是否会触发用户行动。
3. 根据声明类型和风险负担向量生成最低证据负担，而不是统一阈值：例如诊断结论需图像局部证据+领域知识证据+反证缺失；行动建议需异常证据+风险条件+不确定性说明；普通颜色声明只需视觉局部支持。
4. 对每个声明检查证据链完整度：证据来源、模态匹配、局部定位、时间/版本记录、冲突证据、模型内部不确定性、外部检索一致性。
5. 将声明映射为 BURDEN_MET、BURDEN_PARTIAL、BURDEN_CONFLICTED、BURDEN_UNMET、BURDEN_NOT_AUDITABLE 等状态。
6. 依据状态执行输出动作：保留强声明、降级为观察性描述、加入条件限制、请求补充图像、转人工/专家确认、拒答、删除建议性内容。
7. 生成可审计记录，记录每个声明的风险负担、满足证据、缺失证据、降级原因和最终输出动作。

输出：
风险调度后的最终答案、声明级证据负担状态、被降级/阻断/保留的声明清单、可复查证据链日志。

为什么不是简单组合：
核心不是“高风险阈值更高”，而是把声明风险转换为不同证据负担，并让证据负担直接控制输出动作。它不是风控规则表，也不是业务关键词拦截；同一问题中的不同声明可被分配不同负担，同一声明在证据链缺口、反证冲突、不可审计时会触发不同技术动作。

可实验数据集：
CARES、VQA-RAD、SLAKE、PathVQA、VizWiz-LF、TextVQA、DocVQA、POPE/HaloQuest、工业异常 VQA 自构造集、交通/安全巡检图像问答子集。

主要风险：
审查员可能认为这是 risk-based threshold 或 policy rule。权利要求必须抓“声明拆分-风险负担向量-最低证据负担生成-证据链完整度状态-输出动作”的算法闭环，并避免只写医疗/法律场景策略。
```

```text
候选名称：证据链缺失的反向不利推定回答控制

解决的具体技术问题：
VQA 系统在无法定位支持区域、无法复现检索来源或无法说明模型版本时，仍输出确定性答案，导致黑箱回答被用户误信。

输入：
问题、图像、候选答案、证据链日志、证据链完整性字段。

核心处理步骤：
1. 为每个答案声明建立证据链必需字段。
2. 检查是否缺失局部定位、OCR 来源、检索快照、模型版本、冲突检查结果。
3. 若关键字段缺失，则对声明作不利推定，降级或阻断强结论。
4. 输出“证据链不足，无法确认”的回答。

输出：
被不利推定控制后的答案和缺失字段列表。

为什么不是简单组合：
有明确迁移点，但若单独存在，容易被认为只是 audit logging + refusal rule。

可实验数据集：
VizWiz-LF、DocVQA、TextVQA、医疗 VQA、工业巡检 VQA。

主要风险：
创新深度不足，适合作为最佳候选中的一个状态，而不适合独立主案。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
  - 如果只是把金融/法律风控搬到图像问答，属于应用场景替换。
  - 最佳候选的抗辩点是：迁移对象不是业务风险等级，而是“证据负担”这一推理约束；它被编码为声明级证据门槛生成和输出许可状态。
  - 需要强调处理对象是 VQA 生成答案中的最小声明，而不是用户、交易、案件或业务流程。

- 是否只是 RAG / CoT / self-check / 置信度阈值？
  - 普通 RAG 是补充证据，CoT 是生成解释，self-check 是后验判断，置信度阈值是统一数值门控。
  - 本候选要求每个声明先生成最低证据负担，再检查证据链是否满足；输出动作来自 BURDEN 状态，而不是来自一个总置信度。
  - 若权利要求写成“高风险时提高阈值并让模型自检”，会被直接击穿。
  - 应写成“风险负担向量驱动证据类型、证据数量、反证检查、可审计字段的不同组合要求”。

- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
  - Grounding、OCR、检索、检测框都只能作为证据来源。
  - 发明点不在这些模块，而在把不同风险声明映射到不同最低证据负担，并根据证据链状态控制输出强度。
  - 对同一图像，低风险事实可以保留，高风险诊断或建议可以降级，这种声明级差异化控制不是 OCR/grounding 的自然输出。

- 是否能被一篇或几篇论文自然组合推出？
  - AI governance 文献能推出审计日志和高风险记录。
  - 法律 AI 文献能推出证据不足时不应作结论。
  - VQA 去幻觉文献能推出 grounding、verification、uncertainty 和 refusal。
  - 审查员可能组合这些文献说：高风险 VQA 中加入日志和 verifier 是显而易见。
  - 抗辩要点是组合后仍缺少一个具体技术动作：按“声明后果/可观察性/领域敏感性”生成差异化证据负担，并让负担状态决定答案重写，而非只做记录或拒答。

- 是否缺少可验证技术效果？
  - 不能只说“更安全”或“更符合法规”。
  - 可验证指标应包括：high-risk unsupported claim rate、unsafe strong-answer rate、正确降级率、正确拒答率、evidence-chain completeness、conflict pass-through rate、专家复核通过率。
  - 需要同时报告副作用：过度拒答率、低风险问题准确率下降、答案可用性下降。
  - 最快实验应使用高风险子集和干扰证据条件，而不是只跑通用 VQA accuracy。

## 6. 本轮最佳候选

本轮只保留：**风险加权证据负担调度器**。

- 为什么选它：
  - 它把法律/风控中的 burden of proof 转成可执行算法：风险越高，声明进入答案所需的证据负担越高。
  - 它避开了“风控规则”“合规日志”“人工审核”这些业务层内容，落到了 VQA 输出控制中的声明级证据门槛和状态转移。
  - 它能和项目主线“证据许可状态机”合并，但提供了新的专利角度：许可门槛不是固定的，而是由声明风险动态调度。

- 为什么淘汰其他候选：
  - 淘汰“证据链缺失的反向不利推定回答控制”：机制太窄，单独看像 audit logging + refusal rule，可作为 BURDEN_NOT_AUDITABLE 状态。
  - 不选择“可复核证据包”“高风险问题路由/人工审核”：前者偏解释和审计材料生成，后者偏业务规则，都不直接构成答案许可算法。

- 如果写专利，独立权利要求应该抓住哪个技术动作：
  - 抓住“对候选答案进行声明拆分；为每个声明计算风险负担向量；依据风险负担向量生成最低证据负担；检查多模态证据链完整度并生成负担满足状态；依据该状态对声明执行保留、降级、条件化、请求补充、转人工或拒答”的连续动作。
  - 关键限定应写清：同一答案中的不同声明可以具有不同证据负担；证据负担包括模态要求、局部定位要求、反证要求和可审计字段要求；输出动作由负担状态而非统一置信度阈值决定。
  - 不应把“医疗、金融、法律、无障碍”等场景写成发明核心，只作为实施例。

- 如果做实验，最快怎么证明：
  - 数据集：先用 CARES/VQA-RAD/SLAKE 的医疗高风险问题，加 VizWiz-LF 不可回答问题，再加 TextVQA/DocVQA 中会触发行动或身份判断的子集。
  - Baseline：原始 VLM、VLM + uncertainty threshold、VLM + self-check、VLM + grounding verifier、普通高风险拒答策略。
  - 方法：先生成候选长答案，再做声明拆分、风险负担向量生成、证据链检查和答案重写。
  - 指标：高风险无证据强声明率、正确降级/拒答率、冲突证据通过率、专家复核通过率、低风险答案保留率。
  - 预期最可辩护效果：不是单纯提升 accuracy，而是在高风险声明上显著减少“证据不足但强答”的比例，同时保持低风险可观察声明的回答率。
