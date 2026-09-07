# Round 15: 图表 / 数值 / 量纲一致性方向

## 1. 本轮方向

- 方向名称：面向图像问答的图表数值声明、坐标轴、单位与趋势证据一致性约束。
- 检索范围：
- 2021-2026 ChartQA、PlotQA、ChartQAPro、RefChartQA、ChartGemma、ChartLlama、ChartReasoner、DePlot、MatCha。
- chart reasoning、numerical reasoning、unit consistency、axis grounding、table/chart VQA、plot-to-table、chart-to-code、visual answer grounding。
- 目标问题：
- 现有图表问答已能抽取表格、执行算术、生成答案，但常把“最终答案正确率”当作主目标。
- 对专利创新而言，单纯做 OCR、plot-to-table、chart-to-code 或 LLM 推理，已明显拥挤。
- 本轮寻找的空白是：模型输出数值声明时，能否被强制绑定到坐标轴、刻度、单位、图例、局部图元与趋势证据，并在单位换算或趋势结论不自洽时拒答或降级。
- 重点不是“答出 ChartQA”，而是“每个数值/趋势声明都带可验证的证据约束和量纲一致性检查”。

## 2. 代表论文/方法

| 序号 | 论文/方法 | 来源 | 年份 | 核心机制 | 与图像问答关系 | 链接 |
|---|---|---|---|---|---|---|
| 1 | ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning | ACL Findings | 2022 | 构造含 9.6K 人写问题和 23.1K 摘要生成问题的图表 QA 基准；模型联合图像特征和表格信息 | 定义真实图表中的视觉与逻辑/算术推理任务，是本方向基本先验 | https://aclanthology.org/2022.findings-acl.177/ |
| 2 | PlotQA | WACV / arXiv | 2020, 仍被 2021-2026 工作引用 | 大规模合成 plot QA，包含开放词汇、数值读取、比较和算术问题 | 说明数值读取和图表结构解析早已是成熟任务，不能直接作为新点 | https://arxiv.org/abs/1909.00997 |
| 3 | MatCha: Enhancing Visual Language Pretraining with Math Reasoning and Chart Derendering | ACL | 2023 | 用 chart de-rendering 和 math reasoning 预训练像素到文本模型 | 已覆盖“从图像恢复表格/代码 + 数学推理”的基础范式 | https://arxiv.org/abs/2212.09662 |
| 4 | DePlot: One-shot visual language reasoning by plot-to-table translation | ACL Findings | 2023 | 将图表转为线性表，再交给 LLM few-shot 推理；ChartQA 人写问题显著提升 | 证明 plot-to-table + LLM 是强现有组合，专利不能只写这一点 | https://aclanthology.org/2023.findings-acl.660/ |
| 5 | Pix2Struct / chart screenshot parsing | ICML / Google | 2023 | 以截图解析为预训练任务，端到端处理视觉语言结构 | 增强图表、网页、文档等视觉结构理解，压缩单纯图像编码空间 | https://arxiv.org/abs/2210.03347 |
| 6 | UniChart | EMNLP / arXiv | 2023 | 统一 chart summarization、QA、fact-checking 等任务的图表模型 | 说明多任务图表理解、摘要和问答已是常规路线 | https://arxiv.org/abs/2305.14761 |
| 7 | ChartLlama | arXiv / project | 2023 | 用多步数据生成流程构造高质量 chart instruction tuning 数据 | 覆盖 chart QA、chart-to-text、chart extraction、chart generation | https://tingxueronghua.github.io/ChartLlama/ |
| 8 | ChartBench | arXiv | 2023 | 面向多图表类型和复杂推理的评测基准 | 说明复杂图表类型覆盖和 benchmark 本身已拥挤 | https://arxiv.org/abs/2312.15915 |
| 9 | ChartGemma: Visual Instruction-tuning for Chart Reasoning in the Wild | arXiv | 2024 | 基于 PaliGemma，直接从图像生成 instruction-tuning 数据，覆盖多任务 | 强化“真实图表、多任务、instruction tuning”已有现有技术 | https://arxiv.org/abs/2407.04172 |
| 10 | ChartQAPro | arXiv | 2025 | 引入更复杂多样的真实图表、dashboard、infographic、unanswerable 和 hypothetical 问题 | 显示真实场景的难点转向复杂组合、不可答和分布外鲁棒性 | https://arxiv.org/html/2504.05506v1/ |
| 11 | RefChartQA: Grounding Visual Answer on Chart Images through Instruction Tuning | arXiv | 2025 | 为 ChartQA 增加 bbox grounding，要求答案绑定支持图元；grounding 提升准确率并减少幻觉 | 与本轮最接近，必须进一步区分：不只定位图元，还要做轴-单位-量纲约束 | https://arxiv.org/html/2503.23131v2 |
| 12 | ChartReasoner: Code-Driven Modality Bridging for Long-Chain Reasoning in Chart QA | arXiv | 2025 | 图表转 ECharts code，再生成 140K 多步推理样本，SFT+RL 训练 | 说明“代码表示 + 长链推理”已可被自然组合，需避开纯符号桥接 | https://arxiv.org/html/2506.10116v1 |
| 13 | Chart-HQA: Hypothetical Question Answering in Charts | arXiv | 2025 | 用假设条件迫使模型基于图表做反事实推理，揭示参数记忆偏差 | 与趋势/声明反事实检查相关，但重点是 benchmark 任务而非证据约束机制 | https://arxiv.org/html/2503.04095v1/ |
| 14 | General visual answer grounding / referring VQA | VQA / grounding 文献 | 2021-2026 | 对答案支持区域做定位或引用 | 可借鉴 grounding，但普通 bbox 不能解决单位换算、坐标标定和趋势一致性 | 多篇 |

## 3. 热点趋势判断

- 当前领域真正关注的问题：
- 图表从“读数问答”转向真实图表、复杂图表、仪表盘、信息图和论文/报告内嵌图的泛化。
- 从最终答案准确率转向可解释证据，包括 visual answer grounding、bbox 引用、PoT/code 推理轨迹。
- 从单步问答转向多步数值推理、hypothetical/counterfactual 问题、unanswerable 问题和分布外鲁棒性。
- 从 OCR+规则管线转向 VLM、chart-specific instruction tuning、chart-to-table、chart-to-code 和 RL 长链推理。
- 已经成熟、不能作为创新点的部分：
- 识别图表类型、坐标轴文字、图例、柱/点/线等基本图元。
- OCR 提取标签和刻度，再交给 LLM 做数值问答。
- 将图表转换为线性表、代码或结构化文本，再用 LLM/PoT/CoT 推理。
- 在答案后给出 bbox、attention heatmap 或“依据某个柱子”的普通 grounding。
- 用 relaxed accuracy、数值容差、表格抽取准确率评价 ChartQA。
- 仍有空白或可迁移空间的部分：
- 数值声明级别的“量纲证据约束”：答案中的每个数值是否可由某个轴标尺、单位、图例、比例尺和图元几何共同推出。
- 坐标轴标定不确定性传播：轴 OCR、刻度间距、非零基线、断轴、对数轴、双 y 轴、百分比轴、堆叠图造成的读数误差如何进入答案可信度。
- 趋势声明的局部反证：模型说“持续上升”“A 高于 B”“增长最快”时，是否逐段检查斜率、局部极值和类别对齐。
- 单位规范化与跨单位换算：million/billion、%/percentage point、USD/local currency、per-capita/total、kWh/MWh 等是否被混用。
- 不可答判定：如果轴单位缺失、图例模糊、刻度无法标定，系统应拒绝确定数值，而非幻觉填数。
- 专利机会应落在“生成答案前后的可执行一致性检查与纠错动作”，而不是训练一个新图表模型。

## 4. 候选创新点

```text
候选名称：图像问答中的数值声明证据图谱与量纲一致性校验器
解决的具体技术问题：
VLM 对图表给出数值、比较或趋势答案时，可能数值看似合理但未绑定真实轴、单位或图元；尤其在双轴、百分比/绝对值混用、缩放单位、断轴和趋势判断中容易产生幻觉。
输入：
图表图像、用户问题、候选自然语言答案、可选的 OCR/图元检测结果、可选的图转表或图转代码结果。
核心处理步骤：
1. 将候选答案解析为原子声明：数值声明、比较声明、趋势声明、极值声明、比例/差值声明。
2. 为每个原子声明生成所需证据槽：目标类别/系列、图元位置、坐标轴、刻度区间、单位、图例映射、计算操作。
3. 从图像中建立 chart evidence graph：节点包括轴标题、刻度文本、刻度像素坐标、图元几何、图例项、数据标签、标题和注释；边包括图例-系列、轴-图元、刻度-像素映射、单位-数值字段。
4. 对数值声明执行轴标定：用相邻刻度拟合像素到数值的映射，检测线性/对数/断轴/双轴，输出数值区间而非单点值。
5. 对单位执行规范化：识别缩放词、百分比、货币、数量级、rate/total，并把答案单位转换到与证据图相同的 canonical unit。
6. 对趋势声明执行局部反证扫描：沿系列逐段比较，若存在违反“持续上升/下降/最大增幅”等声明的局部段，标记反证。
7. 对计算声明执行量纲检查：差值、比值、百分比变化、均值、总和分别验证输入量纲和输出量纲是否匹配。
8. 汇总每个原子声明的可验证状态：supported、contradicted、underdetermined、unit-mismatch、axis-ambiguous。
9. 若关键声明失败，触发答案重写、数值区间化或拒答；若通过，输出带证据引用的答案。
输出：
带证据链的最终答案、每个原子声明的支持图元/轴/单位/计算记录、量纲一致性状态和拒答/降级原因。
为什么不是简单组合：
不是把 OCR、图转表和 LLM 串起来，而是把候选答案拆成声明后进行轴标定、单位规范化、量纲代数和趋势反证；核心动作是“声明约束验证与纠错”，可以叠加到任意 ChartQA 模型之后。
可实验数据集：
ChartQA、PlotQA、ChartQAPro、RefChartQA、ChartBench、Chart-HQA；另可构造双 y 轴、断轴、单位缩放、百分比点/百分比混淆、非零基线的 stress set。
主要风险：
RefChartQA 已做答案 grounding，需要强调本候选不只给 bbox，而是验证 bbox 与轴、单位和声明量纲之间的可计算一致性；ChartReasoner 已做 chart-to-code，需要强调本候选可检查自然语言答案中的单位和趋势声明，而非仅依赖 code 推理。
```

```text
候选名称：面向图表问答的轴标定不确定性传播拒答机制
解决的具体技术问题：
当轴 OCR、刻度间距、图元边界或图例绑定不确定时，模型仍输出精确数值，造成过度确定。
输入：
图表图像、问题、候选答案、轴/刻度/图元检测置信度。
核心处理步骤：
1. 估计每个刻度和图元边界的像素不确定性。
2. 将像素不确定性传播到读数区间。
3. 将多个读数区间传播到差值、比例、增幅等复合答案区间。
4. 如果答案精度高于可支持精度，自动改写为区间或近似表达。
5. 如果类别排序在不确定区间内不稳定，则拒绝极值/比较声明。
输出：
带置信区间的答案或拒答。
为什么不是简单组合：
其重点是数值不确定性传播，不是普通置信度阈值。
可实验数据集：
ChartQA、PlotQA、合成噪声刻度 stress set。
主要风险：
专利保护面可能偏窄，且统计不确定性传播属于常见技术；需要与 chart-specific 轴类型和声明重写绑定。
```

```text
候选名称：趋势声明的反事实局部扰动验证器
解决的具体技术问题：
模型对折线图/柱状序列常输出“持续增长”“波动下降”“增长最快”等趋势结论，但没有检查局部段。
输入：
图表图像、候选趋势答案、系列图元序列。
核心处理步骤：
1. 把趋势答案解析为可检验谓词。
2. 沿时间/类别顺序抽取局部斜率、差值和极值。
3. 对相邻点、滑动窗口和局部噪声扰动生成反证候选。
4. 若任一反证满足阈值，要求模型改写趋势表述。
输出：
被支持或被反证的趋势答案。
为什么不是简单组合：
强调自然语言趋势谓词和局部图元证据的互相约束。
可实验数据集：
ChartQAPro、ChartBench、合成折线/面积图。
主要风险：
容易被认为是普通一致性评测或后处理规则，独立性弱于候选 1。
```

## 5. 模拟审查员攻击

- 是否只是应用场景替换？
- 对候选 1 的攻击：visual answer grounding 已经在自然图像和 RefChartQA 中做了，换到图表并要求证据，看起来像场景替换。
- 反驳要点：自然图像 grounding 只定位物体区域，候选 1 的技术动作是对“数值声明”建立轴标定、单位归一、量纲代数和趋势反证，输出 supported/contradicted/underdetermined 等验证状态。
- 对候选 2 的攻击：不确定性传播是通用测量技术，换到图表不一定有创造性。
- 对候选 3 的攻击：趋势谓词检查像时间序列规则，不一定属于图像问答核心创新。
- 是否只是 RAG / CoT / self-check / 置信度阈值？
- 候选 1 不是 RAG，因为证据来自图像中的轴、刻度、图元和单位关系，而不是外部知识召回。
- 候选 1 不是普通 CoT，因为它不信任模型自述推理，而是把答案拆成可计算声明并对照 evidence graph 验证。
- 候选 1 也不是简单 self-check，因为检查结果由轴映射、单位代数和局部反证生成，可以独立于生成模型执行。
- 候选 2 若只用检测置信度做拒答，会被打成置信度阈值；需要强调读数区间和计算区间传播。
- 候选 3 若只让 LLM 反思趋势，会被打成 self-check；需要固定为局部序列谓词验证。
- 是否只是现有 grounding / VQA / OCR / 图表解析方法组合？
- 最危险的组合路径：ChartQA/DePlot/ChartReasoner 抽取结构化表，RefChartQA 给 bbox grounding，再加单位转换规则。
- 对候选 1 的防线：现有组合通常输出答案或支持区域，没有以“答案原子声明”为中心建立证据槽，并逐项验证轴类型、单位、量纲和趋势反证。
- 需要在专利中避免泛泛写“提取 OCR、识别图元、生成答案”，而要把创新限定在声明级证据图谱和量纲一致性状态机。
- 是否能被一篇或几篇论文自然组合推出？
- ChartQA + DePlot 自然推出“图转表后计算答案”。
- RefChartQA + ChartReasoner 自然推出“答案 grounding + 代码推理”。
- 如果候选 1 只说“给答案找证据”，会被上述组合覆盖。
- 候选 1 的可争点在于：自然语言答案中的数值/趋势/比较声明被解析为 typed claims，每类 claim 都有不同的证据槽和量纲验证算子，并且验证失败会驱动答案重写/拒答。
- 是否缺少可验证技术效果？
- 可验证效果 1：在单位缩放、双轴、断轴、百分比点混淆 stress set 上降低 unsupported numeric claim rate。
- 可验证效果 2：在 RefChartQA 上提升 grounding faithfulness，不仅 bbox 命中，还要求 bbox 对应轴和单位正确。
- 可验证效果 3：在 ChartQAPro/Chart-HQA 的 unanswerable 或 counterfactual 场景中提高拒答正确率。
- 可验证效果 4：在保持 ChartQA relaxed accuracy 的同时，减少数值过精确输出和趋势幻觉。

## 6. 本轮最佳候选

- 最佳候选：图像问答中的数值声明证据图谱与量纲一致性校验器。
- 为什么选它：
- 它最贴近图表问答的真实高风险错误：数值、单位、坐标轴和趋势声明看似流畅但证据不成立。
- 它与 ChartQA/DePlot/ChartReasoner 的区别清楚：不是生成答案的主模型，而是对候选答案执行声明级验证、单位归一、轴标定和反证扫描。
- 它与 RefChartQA 的区别也较清楚：RefChartQA 主要解决答案支持区域 grounding，本候选进一步要求支持区域必须能通过轴、刻度、单位和量纲计算推出声明。
- 为什么淘汰其他候选：
- 轴标定不确定性传播拒答机制有价值，但更像候选 1 的子模块，独立写容易被认为是通用测量误差传播。
- 趋势声明反事实局部扰动验证器适合做实验增强，但范围偏窄，容易被看成规则化一致性评测。
- 如果写专利，独立权利要求应该抓住哪个技术动作：
- 抓住“将图表问答候选答案解析为多个 typed numeric/comparison/trend claims，并为每个 claim 构建包含图元、坐标轴、刻度、单位和计算操作的证据槽；基于图像构建 evidence graph；对每个 claim 执行轴标定、单位规范化、量纲一致性和局部趋势反证；根据验证状态重写、区间化或拒答答案”。
- 权利要求不应只写“识别图表元素并回答问题”，也不应只写“输出答案证据框”。
- 如果做实验，最快怎么证明：
- 先用 ChartQA/RefChartQA 子集和合成 stress set 做后处理实验，不训练大模型。
- 让 GPT-4o、Qwen-VL、或已有 chart model 先生成答案，再由校验器检查。
- 构造 200-500 个针对性样本：单位缩放、双 y 轴、断轴、非零基线、百分比点、堆叠图、趋势局部反例。
- 评价三项指标：答案准确率、unsupported numeric claim rate、正确拒答/降级率。
- 若校验器能在准确率基本不降的情况下显著降低 unsupported claim，并对单位/趋势错误给出可定位原因，即可支持技术效果。
