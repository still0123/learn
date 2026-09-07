# I1-A 论文机制卡片：A 层直接任务与 B 层 CV 基础

## 1. 检索合同与结论边界

- 检索截止：2026-08-18。
- 覆盖范围：图像/视频问答、长视频、DocVQA、时序定位、目标检测、OCR、细粒度识别、视觉 grounding、证据区域提取、跨帧关联。
- 去重规则：arXiv、会议版及后续修订合并为同一论文族，以最早可公开获得日期为准。
- 纳入门槛：正文可获取且已核验；必须能从正文确认机制、控制流或数据结构以及局限。
- 角色边界：本文件只做论文事实拆解和与当前技术流程的客观重合描述，不判断专利授权性，不构思专利候选。
- 最终纳入：17 个论文族，`R1=10`、`R2=7`；A 层 11 篇、B 层 6 篇。
- 最接近反向证据：`PAPER-A007`、`PAPER-A008`。补充反向证据：`PAPER-A002`、`PAPER-A009`。

## 2. 机制簇总览

| 机制簇 | 论文族 | 直接结论 |
|---|---|---|
| 广告/文字密集视频问答 | A001、A004、A012 | 广告及视频 OCR 依赖高分辨率、足够时序覆盖和跨帧整合；语言先验会覆盖真实文字证据。 |
| 声明/假设分解与视频核验 | A002、A008 | 把候选答案转为可验证声明/假设，再定位局部视频证据并回溯或整合，已经有直接公开。 |
| 主动补看与充分性停止 | A007、A008、A017 | 低充分性触发下一轮时间/区域观察、迭代裁剪以及停止条件，已形成多种直接流程。 |
| 长视频粗到细定位 | A005、A007 | 递归层级定位和按需观察均可在长视频中降低无关帧成本，但仍受观察器感知错误影响。 |
| 密集时空证据与跨帧对象 | A003、A009、A010、A018 | 答案/描述与时间段、bbox 轨迹或 masklet 联合输出和训练已公开。 |
| 多证据检索与融合 | A010、A011、A017 | 多证据问题存在检索缺口和融合缺口；即使给出 oracle 证据，模型也可能过度依赖单帧。 |
| DocVQA/OCR 压缩 | A013 | OCR 文本与二维布局可压缩为少量查询 token，与视觉 token 互补。 |
| 细粒度区域提取 | A014、A017 | KV 缓存相似度或输出熵梯度均可在免训练条件下产生问题相关区域并迭代细化。 |
| 目标检测与拒绝 grounding | A015、A016 | 开放词汇检测可由图像/区域描述联合监督增强；不可定位拒绝仍是明显短板。 |

## 3. 论文卡片

### PAPER-A001

```yaml
paper_id: PAPER-A001
title: "AdsQA: Towards Advertisement Video Understanding"
venue_year: "ICCV 2025"
official_url: "https://arxiv.org/abs/2509.08621"
full_text_url: "https://arxiv.org/pdf/2509.08621"
doi_or_arxiv: "arXiv:2509.08621"
publication_date: "2025-09-10"
code_url: "https://github.com/TsinghuaC3I/AdsQA"
search_layer: A
relevance_tier: R1
mechanism_cluster: "广告视频问答基准与奖励驱动回答"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "普通视频问答不能充分覆盖广告视频中的营销逻辑、说服策略和受众推断。"
inputs: "广告视频、开放式问题；训练时另有答案和广告元信息。"
core_mechanism: "AdsQA 将 1,544 个广告视频组织为五类开放式任务；ReAd-R 对同一视频问题生成多条思考与答案，用包含规则、排除规则和格式规则组成奖励，再以 GRPO 更新策略。"
training_or_optimization: "500 条高质量问答用于强化微调；组内标准化奖励作为优势，另以 KL 约束策略与参考模型偏移。"
inference_control_flow: "视频和问题 -> 生成思考/答案 -> 直接输出；没有证据定位、二次观察或候选回退控制。"
data_structures: "广告视频-片段-任务问答；奖励由 answer inclusion/exclusion 与 format 两部分组成。"
technical_effect: "建立广告视频理解难度基线，并显示小规模规则奖励强化可优于若干长链推理基线。"
limitations: "作者明确指出预训练污染无法完全排除、人工与 LLM 标注偏差、LLM 自动评测和人工判断可能不一致；机制不输出可核验时空证据。"
overlap_with_current_patent: "输入任务和广告场景直接重合，对应初始视频问答生成；不公开声明级支持度、低支持补看、同协议对称评分、双条件替换或回退。"
reusable_principle: "广告回答评价需同时奖励覆盖标准答案事实并惩罚视频或元信息未支持的新增内容。"
cannot_copy_directly: "ReAd-R 的通用 GRPO、格式奖励和 inclusion/exclusion 规则本身不构成证据可靠性闭环。"
evidence_quote_or_section: "正文 §4 Methodology；附录 E Limitations。"
```

### PAPER-A002

```yaml
paper_id: PAPER-A002
title: "Commonsense Video Question Answering through Video-Grounded Entailment Tree Reasoning"
venue_year: "CVPR 2025"
official_url: "https://openaccess.thecvf.com/content/CVPR2025/html/Liu_Commonsense_Video_Question_Answering_through_Video-Grounded_Entailment_Tree_Reasoning_CVPR_2025_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2025/papers/Liu_Commonsense_Video_Question_Answering_through_Video-Grounded_Entailment_Tree_Reasoning_CVPR_2025_paper.pdf"
doi_or_arxiv: "arXiv:2501.05069"
publication_date: "2025-01-09"
code_url: null
search_layer: A
relevance_tier: R1
mechanism_cluster: "答案声明分解、局部视频证据核验与树回溯"
verified_from_full_text: true
reverse_evidence: true
technical_problem: "VLM 可能依赖答案偏置和视频-答案伪相关，且黑盒回答缺少显式证据路径。"
inputs: "视频、问题及多个候选答案。"
core_mechanism: "每个问答候选先转为声明，再递归分解为蕴含子声明；问题感知逐帧描述提取 anchor fact，以结构化对象-属性-关系三元组定位 anchor frame 和相关时间片段；逐节点证明或反驳后回溯蕴含树，必要时动态扩树。"
training_or_optimization: "主要是免训练推理编排；另以 LLM 重写候选集合去除语言偏置。"
inference_control_flow: "候选答案 -> 声明树 -> 局部视频 grounding -> 节点真值验证 -> 树回溯与动态扩展 -> 选择答案。"
data_structures: "多层蕴含树、声明真值/置信、anchor frame、grounded video fragment。"
technical_effect: "正文消融显示 grounded fragment 优于全视频输入，动态树深度优于固定深度；GT 片段仍可进一步提升，说明定位是主要瓶颈。"
limitations: "依赖预给定多选候选和中间视频字幕；递归超过约四层收益递减；正文显示使用真实片段仍优于自动定位，且没有基于已生成开放式答案的补看和保守回退。"
overlap_with_current_patent: "与答案/候选声明拆解、声明证据验证直接接近；区别在于其从多选候选同时建树，不以低支持初答触发新观察，也无初答-候选同协议评分、绝对阈值+裕量替换和失败回退。"
reusable_principle: "复杂答案可先分解为更易被视频片段证明或反驳的原子声明，再通过显式结构聚合。"
cannot_copy_directly: "蕴含树、LLM 声明分解和局部片段验证组合已被正文完整公开。"
evidence_quote_or_section: "正文 §3 Video-grounded entailment tree reasoning；§5 消融 Table 7/8；§6 Conclusion。"
```

### PAPER-A003

```yaml
paper_id: PAPER-A003
title: "Object-centric Video Question Answering with Visual Grounding and Referring"
venue_year: "ICCV 2025"
official_url: "https://openaccess.thecvf.com/content/ICCV2025/html/Wang_Object-centric_Video_Question_Answering_with_Visual_Grounding_and_Referring_ICCV_2025_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/ICCV2025/papers/Wang_Object-centric_Video_Question_Answering_with_Visual_Grounding_and_Referring_ICCV_2025_paper.pdf"
doi_or_arxiv: "arXiv:2507.19599"
publication_date: "2025-07-25"
code_url: "https://qirui-chen.github.io/RGA3-release/"
search_layer: A
relevance_tier: R1
mechanism_cluster: "对象中心 VideoQA、视觉提示跨帧传播与分割 grounding"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "VideoLLM 多为文本输入输出，不能在多轮问答中持续指代对象并输出对象级视觉 grounding。"
inputs: "视频、问题、任意时间戳上的框/掩码/涂鸦/箭头/点等视觉提示。"
core_mechanism: "STOM 用点跟踪器双向传播提示并以 alpha blending 叠加到各帧；Qwen2.5-VL 编码融合后的帧并回答；输出出现 SEG token 时，其隐藏状态映射到 SAM2 解码器生成跨帧掩码。"
training_or_optimization: "图文生成交叉熵与 BCE+DICE 掩码损失联合训练；图像按单帧视频加入统一训练。"
inference_control_flow: "单帧视觉提示 -> 跨帧跟踪传播 -> 叠加帧编码 -> 文本推理 -> 可选 SEG token -> SAM2 mask。"
data_structures: "RGBA visual prompt、跨帧提示轨迹、SEG token、视频 mask 序列。"
technical_effect: "支持对象级输入 referring 和文本+掩码输出；消融表明 STOM 改善对象推理，SAM2 改善视频分割。"
limitations: "实验通常只输入 8/16 帧；CoTracker3 与 SAM2 是主要时延来源；对象轨迹依赖传播质量，oracle propagation 仍高于自动传播；不处理 OCR/ASR 或声明支持度。"
overlap_with_current_patent: "与区域证据获取和跨帧对象关联重合，可为证据区域提供 mask；不公开声明核验、低支持触发、独立候选生成和回退门控。"
reusable_principle: "对象证据应保持跨帧身份并以可追踪 mask 表示，而不是把相邻帧检测当成独立对象。"
cannot_copy_directly: "提示传播、alpha overlay、SEG token 与 SAM2 联合解码已被公开为完整对象中心 VideoQA 流程。"
evidence_quote_or_section: "正文 §3 Method；Table 6-8；§5 Conclusion。"
```

### PAPER-A004

```yaml
paper_id: PAPER-A004
title: "EgoTextVQA: Towards Egocentric Scene-Text Aware Video Question Answering"
venue_year: "CVPR 2025"
official_url: "https://openaccess.thecvf.com/content/CVPR2025/html/Zhou_EgoTextVQA_Towards_Egocentric_Scene-Text_Aware_Video_Question_Answering_CVPR_2025_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2025/papers/Zhou_EgoTextVQA_Towards_Egocentric_Scene-Text_Aware_Video_Question_Answering_CVPR_2025_paper.pdf"
doi_or_arxiv: "arXiv:2502.07411"
publication_date: "2025-02-11"
code_url: "https://github.com/zhousheng97/EgoTextVQA"
search_layer: A
relevance_tier: R1
mechanism_cluster: "动态场景文字 VideoQA 与时间/分辨率诊断"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "真实动态第一视角中，用户不会明确指出文字位置，文字还会模糊、短时出现并需要跨帧和意图推理。"
inputs: "截至提问时间戳的第一视角视频、问题，可选辅助 OCR 文本。"
core_mechanism: "构建 1.5K 视频、7K 问题的 scene-text VideoQA 基准；通过单帧、多帧、QA 关键帧、时间戳回溯采样、全局/局部高分辨率和辅助 OCR 输入做受控诊断。"
training_or_optimization: "基准与启发式实验，不提出新的端到端训练目标。"
inference_control_flow: "视频采样/关键帧定位 -> 可选文字区域超分与 OCR -> 视频+问题(+文字)回答。"
data_structures: "问题时间戳、QA 关键帧、OCR 字符串、室内/室外场景和问题类别。"
technical_effect: "关键帧、多帧、高分辨率和视频+OCR 联合输入可显著改善部分模型；单独文字输入不足。"
limitations: "最佳模型准确率仍约 33%；时间 grounding 对不同模型/场景并非稳定提升；室内低分辨率和复杂视角使 OCR 增益很小；自动评测依赖 GPT-4o-mini。"
overlap_with_current_patent: "直接支撑 OCR、小字、短时文字和多帧证据是视频问答可靠性的基础问题；不公开答案后验证、低支持补看或候选替换控制。"
reusable_principle: "文字证据必须同时保留视觉上下文、时间位置和 OCR 内容，不能仅把 OCR 字符串拼入提示。"
cannot_copy_directly: "关键帧、高分辨率和辅助 OCR 只是论文验证的常规改进条件。"
evidence_quote_or_section: "正文 Abstract/§1；§5 Heuristic Solution Investigations；§6 Conclusion。"
```

### PAPER-A005

```yaml
paper_id: PAPER-A005
title: "ReVisionLLM: Recursive Vision-Language Model for Temporal Grounding in Hour-Long Videos"
venue_year: "CVPR 2025"
official_url: "https://openaccess.thecvf.com/content/CVPR2025/html/Hannan_ReVisionLLM_Recursive_Vision-Language_Model_for_Temporal_Grounding_in_Hour-Long_Videos_CVPR_2025_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2025/papers/Hannan_ReVisionLLM_Recursive_Vision-Language_Model_for_Temporal_Grounding_in_Hour-Long_Videos_CVPR_2025_paper.pdf"
doi_or_arxiv: "arXiv:2411.14901"
publication_date: "2024-11-22"
code_url: "https://github.com/Tanveer81/ReVisionLLM"
search_layer: A
relevance_tier: R2
mechanism_cluster: "小时级视频递归粗到细时间定位"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "VLM 帧数限制使小时级视频中的短事件边界丢失。"
inputs: "长视频与目标事件文本。"
core_mechanism: "CLIP 提取逐帧特征；Hierarchical Adapter 以查询交叉注意力把滑窗压成稀疏段表示，同时保留底层密集表示；LLM 先在全视频稀疏层定位大段，再逐层用密集特征修正起止边界或输出 Not Present。"
training_or_optimization: "先在短片段上用正样本和事件缺失反例训练边界/存在判断，再冻结相应模块并在小时级视频上渐进训练稀疏表示。"
inference_control_flow: "全局稀疏扫描 -> 预测候选段 -> 下一层递归细化 -> 精确 start/end 或 Not Present。"
data_structures: "多层视频表示、稀疏 segment token、密集 frame token、层间边界状态。"
technical_effect: "递归处理以较少 LLM 输入帧显著优于非递归基线，并可扩展到合成 10 小时视频。"
limitations: "只做文本到时间段定位，不输出区域或答案；作者将音频融合和跨日视频列为未来工作；更长视频仍略降，反向层级能提高精度但使用更多帧。"
overlap_with_current_patent: "与时间证据获取和粗到细补看重合；不包含声明支持度、答案候选比较和保守回退。"
reusable_principle: "长视频定位可把全局稀疏存在判断与局部密集边界回归分层，且训练必须包含事件缺失片段。"
cannot_copy_directly: "递归粗到细定位、稀疏/密集层级表示和 Not Present 训练已完整公开。"
evidence_quote_or_section: "正文 §3 Method；Figure 5/Table 4；§6 Conclusion and Future Work。"
```

### PAPER-A007

```yaml
paper_id: PAPER-A007
title: "Active Video Perception: Iterative Evidence Seeking for Agentic Long Video Understanding"
venue_year: "CVPR Findings 2026"
official_url: "https://arxiv.org/abs/2512.05774"
full_text_url: "https://arxiv.org/pdf/2512.05774"
doi_or_arxiv: "arXiv:2512.05774"
publication_date: "2025-12-05"
code_url: "https://github.com/ActiveVideoPerception/AVP"
search_layer: A
relevance_tier: R1
mechanism_cluster: "证据充分性驱动的主动时间/分辨率补看"
verified_from_full_text: true
reverse_evidence: true
technical_problem: "长视频关键线索稀疏，问题无关的全量字幕既昂贵又模糊细粒度时空信息。"
inputs: "长视频、查询、最大轮数和充分性置信阈值。"
core_mechanism: "Planner 每轮决定 what/where/how（观察指令、时间区间、FPS/分辨率）；Observer 从像素提取带时间戳的结构化证据并累加；Reflector 对累计证据估计充分性置信和缺口说明，低于阈值则把历史和缺口反馈给 Planner 重规划。"
training_or_optimization: "当前实现主要由提示驱动，不训练感知策略；正文把 RL 或可微规划器列为后续方向。"
inference_control_flow: "plan -> targeted observe -> append evidence -> reflect sufficiency -> 达阈值回答，否则 re-plan；达到最大轮数时强制回答。"
data_structures: "累计 evidence list E、历史 H、观察计划 P=(what, where, how)、充分性分数 C 和 justification J。"
technical_effect: "跨五个长视频基准提升平均准确率，同时减少推理时间和输入 token；结构化证据优于无结构证据。"
limitations: "只在离线视频 QA 验证；依赖提示而非学习策略；失败分析中 76% 错误来自 Observer 感知；达到轮数上限会强制回答而非回退或拒答。"
overlap_with_current_patent: "直接覆盖低充分性触发新的时间/空间观察、证据累积和阈值停止，是当前流程最接近的反向证据之一；未公开基于初答独立生成候选、初答/候选同协议评分、相对裕量替换及失败回退。"
reusable_principle: "每次补看应由明确证据缺口生成可执行的时间与分辨率计划，并把新增证据与历史一起重新评估。"
cannot_copy_directly: "plan-observe-reflect、充分性阈值、证据列表和低置信重规划的完整闭环已被公开。"
evidence_quote_or_section: "正文 §3 Method/Algorithm 1；附录 A Limitations；附录失败分析。"
```

### PAPER-A008

```yaml
paper_id: PAPER-A008
title: "Think, Then Verify: A Hypothesis-Verification Multi-Agent Framework for Long Video Understanding"
venue_year: "CVPR 2026"
official_url: "https://arxiv.org/abs/2603.04977"
full_text_url: "https://arxiv.org/pdf/2603.04977"
doi_or_arxiv: "arXiv:2603.04977"
publication_date: "2026-03-05"
code_url: "https://github.com/Haorane/VideoHV-Agent"
search_layer: A
relevance_tier: R1
mechanism_cluster: "候选假设化、判别线索生成与局部视频验证"
verified_from_full_text: true
reverse_evidence: true
technical_problem: "长视频检索/CoT 容易累积语义漂移和伪相关，摘要不足以区分相近答案。"
inputs: "长视频、问题和多选候选答案；预计算逐帧字幕。"
core_mechanism: "Thinker 将每个候选改写为必须在视频中成立的可测试假设；Judge 生成区分候选的最小判别线索；Verifier 用字幕定位最小时间窗口并回看原始帧，输出 VERIFIED/PARTIAL/NOT VERIFIED；Answer 只整合摘要与已验证证据。"
training_or_optimization: "提示式多 Agent 推理，无专门参数训练；通过两个自细化循环增强假设具体性、可区分性和补充观察。"
inference_control_flow: "视频摘要 -> 候选假设 -> 判别线索 -> 时间定位/细粒度回看 -> 三态验证 -> 追加观察或重写假设 -> 证据整合答案。"
data_structures: "候选-假设一一映射 H、clue κ、证据 E、验证状态 S 和 reasoning trace。"
technical_effect: "消融显示移除 hypothesis、clue 或 verification status 均降准确率；额外循环达到一定次数后收益趋于饱和。"
limitations: "仅处理预给多选候选；依赖逐帧 caption，细看每次最多五帧；验证状态和 Agent 均由提示产生；没有明确开放式初答的对称分数或保守回退。"
overlap_with_current_patent: "直接接近候选/声明分解、局部证据验证、证据不足再看和最终证据整合，是另一篇最接近反向证据；其候选来自题目选项而非低支持初答后的独立生成。"
reusable_principle: "先定义候选之间可区分的最小观察，再验证该观察，比无目标扩张检索范围更稳定。"
cannot_copy_directly: "Thinker-Judge-Verifier-Answer 及三态验证/自细化控制流已被正文明确公开。"
evidence_quote_or_section: "正文 §3 Method/Algorithm 1；§4.4 Ablation；§5 Conclusion。"
```

### PAPER-A009

```yaml
paper_id: PAPER-A009
title: "Evidence-Backed Video Question Answering"
venue_year: "ECCV 2026"
official_url: "https://arxiv.org/abs/2607.11862"
full_text_url: "https://arxiv.org/pdf/2607.11862"
doi_or_arxiv: "arXiv:2607.11862"
publication_date: "2026-07-13"
code_url: "https://github.com/SalesforceAIResearch/EVQA"
search_layer: A
relevance_tier: R1
mechanism_cluster: "答案与时间段、跨帧密集 masklet 联合输出"
verified_from_full_text: true
reverse_evidence: true
technical_problem: "VideoLLM 答案可能正确但没有可验证的视觉 grounding，稀疏框不能覆盖遮挡和非刚性形变。"
inputs: "视频、问题及可选答案候选。"
core_mechanism: "E-VQA 把输出定义为 (答案 A、多个时间段 Et、跨帧对象 masklet Es)；ST-Evidence 用人工三阶段 Sample-Annotate-Verify 建标；160K ST-Evidence-Instruct 通过 grounding-to-semantics 和 semantics-to-grounding 双路径生成并过滤训练数据。"
training_or_optimization: "联合答案生成、时间监督和分割监督；自动数据路径包含证据对象识别、时间段生成、框过滤、SAM-3 密集传播和高 IoU masklet 去重。"
inference_control_flow: "回答问题并同步输出时间段与证据对象 masklet；不是答后低支持触发式补看。"
data_structures: "E-VQA 六元组 (V,Q,A,C,Et,Es)、非重叠时间段集合、跨帧密集 masklet。"
technical_effect: "联合训练显著提高时间与空间证据指标；证据区域破坏比非证据区域破坏更大幅降低 QA，表明标注捕获决定性证据。"
limitations: "高质量密集标注昂贵；自动生成仍依赖大型 VLM、框预测和 SAM；正文显示 QA 准确与证据准确明显解耦，最强模型 grounding 仍低；样本聚焦 5-200 秒视觉视频，未处理 OCR/ASR。"
overlap_with_current_patent: "直接公开答案与可验证时空证据绑定及决定性证据破坏评测；不公开低支持补看、独立候选、同协议比较和双条件回退。"
reusable_principle: "可靠性评估应分别测答案、时间证据和跨帧空间证据，不能以答案正确替代证据正确。"
cannot_copy_directly: "答案+时间段+密集 masklet 的任务定义、数据结构和联合训练已直接公开。"
evidence_quote_or_section: "正文 §3 E-VQA；§4 Instruction Tuning Data Construction；Table 2/5；§6 Conclusion。"
```

### PAPER-A010

```yaml
paper_id: PAPER-A010
title: "CaST-Bench: Benchmarking Causal Chain-Grounded Spatio-Temporal Reasoning for Video Question Answering"
venue_year: "CVPR 2026"
official_url: "https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_CaST-Bench_Benchmarking_Causal_Chain-Grounded_Spatio-Temporal_Reasoning_for_Video_Question_Answering_CVPR_2026_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2026/papers/Zhang_CaST-Bench_Benchmarking_Causal_Chain-Grounded_Spatio-Temporal_Reasoning_for_Video_Question_Answering_CVPR_2026_paper.pdf"
doi_or_arxiv: "arXiv:2605.23216"
publication_date: "2026-05-22"
code_url: "https://woven-by-toyota.github.io/CaST-Bench"
search_layer: A
relevance_tier: R1
mechanism_cluster: "多段因果链、时间区间与 bbox 轨迹证据"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "视频因果问答缺少逐步、细粒度、可定位的因果链证据，正确答案可能来自伪相关。"
inputs: "视频和因果问题。"
core_mechanism: "输出答案前先输出可变长因果链；每个证据项包含 start/end、事实 rationale 和 1-FPS bbox map；数据构建用实例分割/跟踪、人工修订描述、VLM 生成因果问答，再通过遮蔽全部证据区域检查问题是否仍可被猜中。"
training_or_optimization: "基准构建与评价，不提出专用训练模型；评价答案、grounding、逻辑一致、证据覆盖和答案-证据忠实度。"
inference_control_flow: "识别多段因果证据 -> 按因果顺序组织 rationale+bbox track -> 输出答案。"
data_structures: "变长 causal chain；Evidence=(t_start,t_end,rationale,{timestamp:bbox})。"
technical_effect: "给出真实因果链可使多种模型提升约 20-25 点；大模型和 thinking 不保证更高 grounding 或忠实度。"
limitations: "是诊断基准而非闭环方法；bbox 以 1 FPS 标注，未覆盖像素级细节；部分模型无法遵循结构化格式；正确答案的 faithful rate 仍低。"
overlap_with_current_patent: "与多时间段证据、答案-证据忠实性和决定性证据遮蔽测试重合；不包含答案后主动补看和候选门控回退。"
reusable_principle: "多跳视频结论应记录有序证据项及其时空轨迹，并用证据区域遮蔽排除无视觉依据的猜中。"
cannot_copy_directly: "因果链证据结构、遮蔽过滤和忠实度评价均已公开。"
evidence_quote_or_section: "正文 §3 Task Definition；§4 Construction；§5.2-5.3；§6 Conclusion。"
```

### PAPER-A011

```yaml
paper_id: PAPER-A011
title: "HERBench: A Benchmark for Multi-Evidence Integration in Video Question Answering"
venue_year: "CVPR 2026"
official_url: "https://openaccess.thecvf.com/content/CVPR2026/html/Ami_HERBench_A_Benchmark_for_Multi-Evidence_Integration_in_Video_Question_Answering_CVPR_2026_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2026/papers/Ami_HERBench_A_Benchmark_for_Multi-Evidence_Integration_in_Video_Question_Answering_CVPR_2026_paper.pdf"
doi_or_arxiv: "arXiv:2512.14870"
publication_date: "2025-12-16"
code_url: null
search_layer: A
relevance_tier: R1
mechanism_cluster: "至少三段证据、跨帧身份保持与检索/融合解耦"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "现有 VideoQA 常可由单个显著线索猜中，不能检验分散多证据的完整检索与融合。"
inputs: "视频与五选一问题，每题结构上要求至少三个不重叠时间 cue。"
core_mechanism: "12 类任务覆盖时序、跨帧 referring/tracking、全局存在/缺失验证和多实体计数；提出 Minimum Required Frame-Set；用统一采样、学习选择器、oracle frame 和 oracle-only frame 拆分检索缺口与融合缺口。"
training_or_optimization: "基准与诊断分析，不提供新训练算法；以 leave-one-out 概率差测每帧对模型选择的贡献。"
inference_control_flow: "检索多段证据 -> 跨帧保持身份/顺序/计数 -> 融合后选择答案。"
data_structures: "MRFS、oracle frame set、逐帧贡献 delta/share、Top-1 evidence share。"
technical_effect: "13 个模型仅 31.4%-42.1%；即使给 oracle frame 仍低于 50%，错误答案常把约 0.8 权重集中到单帧。"
limitations: "基准为多选且统一 16 帧预算；oracle frame 由构建流程提供，不是可部署检索器；只诊断融合失败，不提供修复闭环。"
overlap_with_current_patent: "直接支撑多证据不能只聚合单一高分片段，且需区分证据没找全与找到后没融合；不公开答案候选门控。"
reusable_principle: "证据可靠性评测应分别报告 retrieval recall 和 oracle-evidence fusion，防止把检索失败误归因于回答器。"
cannot_copy_directly: "至少三 cue 的任务构造、MRFS 和 leave-one-out 帧贡献诊断已公开。"
evidence_quote_or_section: "正文 §3 HERBench；§5.1-5.2；§6 Conclusion。"
```

### PAPER-A012

```yaml
paper_id: PAPER-A012
title: "MME-VideoOCR: Evaluating OCR-Based Capabilities of Multimodal LLMs in Video Scenarios"
venue_year: "NeurIPS 2025 Datasets and Benchmarks"
official_url: "https://arxiv.org/abs/2505.21333"
full_text_url: "https://arxiv.org/pdf/2505.21333"
doi_or_arxiv: "arXiv:2505.21333"
publication_date: "2025-05-27"
code_url: "https://github.com/DogNeverSleep/MME-VideoOCR"
search_layer: A
relevance_tier: R1
mechanism_cluster: "视频 OCR、文字 grounding、变化跟踪和跨帧整合"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "静态 OCR 能力不能直接迁移到含运动模糊、文字变化、跨镜头跟踪和长序列的真实视频。"
inputs: "视频与 OCR 相关问答。"
core_mechanism: "基准含 10 类 25 项任务：文字识别、视觉文字 QA、时空文字定位、属性、变化检测与跟踪、表格/图表/文档/公式、跨帧文字、文字推理、长视频和对抗鲁棒性；人工标注后专家复核，并做无视觉输入去偏测试。"
training_or_optimization: "评价基准，不训练新模型。"
inference_control_flow: "视频帧采样 -> 识别/定位/跟踪文字 -> 跨帧聚合或推理 -> 回答。"
data_structures: "1,464 视频、2,000 QA；任务含 text bbox/time、change/trajectory、distributed text cue。"
technical_effect: "高分辨率和足够帧数普遍重要；多数模型跨帧文字任务约 20%，轨迹识别可为 0%；32 增到 64 帧还可能因注意/记忆压缩下降。"
limitations: "作者指出部分概念样本稀疏且总量受标注成本限制为 2,000；当前题目含易中难，未来模型可能饱和；它是诊断基准而非补看方法。"
overlap_with_current_patent: "覆盖 OCR 证据、时间定位、跨帧文字整合和语言先验错误，是区域/时间证据质量的重要基础；不涉及声明验证与答案替换。"
reusable_principle: "OCR 证据至少应保留原字符、空间位置、出现时间、跨帧身份/变化和识别可靠度。"
cannot_copy_directly: "增加 OCR、提高分辨率或增加帧数均属于已被系统验证的常规方向。"
evidence_quote_or_section: "正文 §3 Task Definition；Figure 5；§4 Temporal Integration/Language Prior；§5 Limitations。"
```

### PAPER-B013

```yaml
paper_id: PAPER-B013
title: "DocVLM: Make Your VLM an Efficient Reader"
venue_year: "arXiv 2024"
official_url: "https://arxiv.org/abs/2412.08746"
full_text_url: "https://arxiv.org/pdf/2412.08746"
doi_or_arxiv: "arXiv:2412.08746"
publication_date: "2024-12-11"
code_url: null
search_layer: B
relevance_tier: R2
mechanism_cluster: "DocVQA 的 OCR+二维布局压缩与视觉互补"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "文档理解需要高分辨率，纯视觉 token 成本高；把 OCR 原文直接放进提示又丢失布局和视觉上下文。"
inputs: "文档图像、问题、OCR token 及二维框。"
core_mechanism: "冻结基础 VLM；DocFormerV2 OCR encoder 编码 OCR 文本、二维位置和问题指令；64 个可学习 query 压缩编码结果，投影后与视觉 token 拼接；多页可全局压缩或逐页压缩。"
training_or_optimization: "两阶段：先无图像进行 OCR-LLM 对齐，再加入视觉信息训练 OCR 模块补充视觉特征；基础 VLM 始终冻结。"
inference_control_flow: "OCR+layout+instruction -> 64 query 压缩 -> 与有限视觉 token 合并 -> 文档问答。"
data_structures: "OCR token+bbox、instruction embedding、固定数 learned queries、page-wise token group。"
technical_effect: "低视觉预算下显著提升 DocVQA；64 token 接近 800 token 未压缩 OCR 效果，并支持多页。"
limitations: "依赖外部 OCR 质量；仅用 OCR 不如 OCR+视觉；单页训练后才零样本扩展多页；作者提示提示调优会隐式注入训练数据偏差。"
overlap_with_current_patent: "为文字区域证据的紧凑表示提供 B 层机制；不包含视频时序、声明核验或补看控制。"
reusable_principle: "文字证据压缩应同时条件化于问题并编码二维布局，且要与原始视觉上下文互补。"
cannot_copy_directly: "OCR encoder+64 query 压缩+冻结 VLM 的 DocVQA 架构已完整公开。"
evidence_quote_or_section: "正文 §3 Our Method；§5 Ablation Table 3；附录 D visual features effect。"
```

### PAPER-B014

```yaml
paper_id: PAPER-B014
title: "FOCUS: Internal MLLM Representations for Efficient Fine-Grained Visual Question Answering"
venue_year: "NeurIPS 2025"
official_url: "https://openreview.net/forum?id=8I1XNt70lj"
full_text_url: "https://arxiv.org/pdf/2506.21710"
doi_or_arxiv: "arXiv:2506.21710"
publication_date: "2025-06-26"
code_url: "https://focus-mllm-vqa.github.io/"
search_layer: B
relevance_tier: R2
mechanism_cluster: "KV 缓存相似度驱动的免训练细粒度 crop"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "MLLM 对小目标细节识别弱，穷举 crop 昂贵，直接请求框又会产生幻觉坐标。"
inputs: "高分辨率图像和细粒度 VQA 问题。"
core_mechanism: "先从问题提取目标对象；用后层 KV cache 的目标词 value 与视觉 token value 余弦相似度构造 relevance map，多 token 图逐元素相乘；从峰值提出多 ROI、扩框、NMS 去重，再用目标存在置信重排，最终对最佳局部区域回答。"
training_or_optimization: "完全免训练；通过前向预算 nsteps 控制候选 ROI 重排成本。"
inference_control_flow: "目标词提取 -> relevance map -> ROI proposal/NMS -> existence rerank -> 选 crop -> VQA。"
data_structures: "object relevance map、anchor points、ROI list、existence confidence。"
technical_effect: "在四个细粒度 VQA 数据集上以更少计算匹配或超过 crop 基线。"
limitations: "作者明确指出内部 relevance map 分辨率限制 8K 小目标定位；继承基础 MLLM 的左右等空间关系弱点；候选过多时重排会选错，即使 crop 正确基础模型仍可能答错。"
overlap_with_current_patent: "与问题驱动区域证据提取和局部补看重合；没有视频、支持度触发或答案候选比较。"
reusable_principle: "区域提取应将目标定位信号与区域内目标存在验证分开，避免只按单一热力峰值裁剪。"
cannot_copy_directly: "KV value-value pseudo-attention、ROI 提案和存在置信重排已公开。"
evidence_quote_or_section: "正文 §3 FOCUS；§4.3-4.6；§5 Conclusion。"
```

### PAPER-B015

```yaml
paper_id: PAPER-B015
title: "GroundingME: Exposing the Visual Grounding Gap in MLLMs through Multi-Dimensional Evaluation"
venue_year: "CVPR 2026"
official_url: "https://openaccess.thecvf.com/content/CVPR2026/html/Li_GroundingME_Exposing_the_Visual_Grounding_Gap_in_MLLMs_through_Multi-Dimensional_CVPR_2026_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2026/papers/Li_GroundingME_Exposing_the_Visual_Grounding_Gap_in_MLLMs_through_Multi-Dimensional_CVPR_2026_paper.pdf"
doi_or_arxiv: "arXiv:2512.17495"
publication_date: "2025-12-19"
code_url: "https://groundingme.github.io/"
search_layer: B
relevance_tier: R2
mechanism_cluster: "细粒度 grounding、tiny/occlusion 与不可定位拒绝"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "现有 grounding 基准描述简单，不能测相似目标区分、复杂空间关系、小目标/遮挡和不可定位拒绝。"
inputs: "高分辨率图像与完整指代表达。"
core_mechanism: "1,005 个样本按 Discriminative、Spatial、Limited、Rejection 四维组织；人工修订框和描述，Rejection 样本故意引入事实不匹配；另测试 Best-of-16 思考轨迹选择和正负样本混合训练。"
training_or_optimization: "基准本身无训练；改进实验以思考质量 judge 做 test-time scaling，或用不同比例负样本 SFT 学拒绝。"
inference_control_flow: "描述 -> 框或 null；TTS 版本生成 16 条轨迹后由 judge 逐对选优。"
data_structures: "bbox/null、四级任务标签、负/正 grounding mixture、thinking trajectory。"
technical_effect: "多数模型 rejection 为 0%；思考和 TTS 可提高但仍低；负样本训练提升拒绝，却使更难的域外正 grounding 从 38.8% 降至最高 33.0%。"
limitations: "仍是静态图像框定位；Best-of-16 成本高；简单负样本混合存在拒绝与正定位退化权衡，拒绝能力不能免费域外泛化。"
overlap_with_current_patent: "为未检测到、不可定位和证据不存在的区分提供基础反例；不包含视频证据覆盖证明或答案门控。"
reusable_principle: "证据定位器必须允许 null/reject，并单独测试 tiny、occlusion、相似实例和不存在描述。"
cannot_copy_directly: "不可定位拒绝基准、负样本训练和思考轨迹筛选均已公开。"
evidence_quote_or_section: "正文 §3 GroundingME；§5 Analysis；§6 Conclusion。"
```

### PAPER-B016

```yaml
paper_id: PAPER-B016
title: "LLMDet: Learning Strong Open-Vocabulary Object Detectors under the Supervision of Large Language Models"
venue_year: "CVPR 2025"
official_url: "https://openaccess.thecvf.com/content/CVPR2025/html/Fu_LLMDet_Learning_Strong_Open-Vocabulary_Object_Detectors_under_the_Supervision_of_CVPR_2025_paper.html"
full_text_url: "https://openaccess.thecvf.com/content/CVPR2025/papers/Fu_LLMDet_Learning_Strong_Open-Vocabulary_Object_Detectors_under_the_Supervision_of_CVPR_2025_paper.pdf"
doi_or_arxiv: "arXiv:2501.18954"
publication_date: "2025-01-31"
code_url: "https://github.com/iSEE-Laboratory/LLMDet"
search_layer: B
relevance_tier: R2
mechanism_cluster: "LLM 描述监督的开放词汇检测与细粒度区域对齐"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "开放词汇检测只用区域短语时缺少对象属性、关系和全图上下文，稀有类别表示弱。"
inputs: "图像、grounding 短语与框、全图详细事实 caption。"
core_mechanism: "GroundingCap-1M 为每图同时提供 region grounding 和全图详细描述；先训练 projector 对齐 detector feature 与 LLM，再联合优化词-区域对齐、框回归、全图 caption 和区域 caption；区域 object query 通过 cross-attention 获取全图信息。"
training_or_optimization: "L=L_align+L_box+L_image_lm+L_region_lm；LLM 只用于训练监督，部署检测时可丢弃。"
inference_control_flow: "图像+开放词汇 -> detector -> bbox/class；不执行问答或证据补看。"
data_structures: "样本四元组 (image, grounding text, boxes, detailed caption)、object query、image/region caption。"
technical_effect: "全图与区域语言监督联合提高开放词汇检测，尤其稀有类别；单独区域 caption 无增益。"
limitations: "生成 caption 仍含噪声/幻觉且会降低稀有类 AP；受计算限制数据仅约 1M；是静态框检测，未建模跨帧身份和答案证据。"
overlap_with_current_patent: "可作为 Logo/产品/细粒度对象区域提取基础；与答案验证控制流无直接重合。"
reusable_principle: "检测器的区域词对齐应由全图事实描述补足关系上下文，同时过滤推测性 caption。"
cannot_copy_directly: "详细图像描述+区域描述联合监督开放词汇 detector 已被公开。"
evidence_quote_or_section: "正文 §3 GroundingCap-1M；§4 LLMDet；§5.3 Ablation；§6 Conclusion。"
```

### PAPER-B017

```yaml
paper_id: PAPER-B017
title: "Entropy-Gradient Grounding: Training-Free Evidence Retrieval in Vision-Language Models"
venue_year: "arXiv 2026"
official_url: "https://arxiv.org/abs/2604.08456"
full_text_url: "https://arxiv.org/pdf/2604.08456"
doi_or_arxiv: "arXiv:2604.08456"
publication_date: "2026-04-09"
code_url: "https://github.com/merci00001/entropy-gradient-grounding"
search_layer: B
relevance_tier: R2
mechanism_cluster: "输出熵梯度、多区域证据提取与空间熵停止"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "注意力图依赖层/头启发式且常聚焦错误区域；细粒度和空间分离的多证据难以一次找到。"
inputs: "图像与问题。"
core_mechanism: "计算下一 token 分布 Shannon entropy，并反传到投影后的视觉 token，以梯度 L2 范数形成 relevance map；高斯平滑后用 elbow 阈值二值化，连通域按原梯度总量排名；保留全局视图并对多个区域迭代重定位，空间熵下降时继续、上升时停止。"
training_or_optimization: "完全免训练，无外部 detector；每轮需要前向和反向传播。"
inference_control_flow: "entropy gradient -> multi-region extraction/ranking -> global+local views -> iterative re-ground/zoom -> spatial-entropy stop -> answer。"
data_structures: "视觉 token 梯度图、connected components、region score、view set、spatial entropy。"
technical_effect: "跨四种 VLM 和七个基准改善细粒度/文档任务，并能返回多个不相连证据区域。"
limitations: "迭代约为单轮 2-3 倍时延；正确定位不保证基础 LLM 正确解释；若基础模型本身不认为某区域重要，梯度也无法恢复该证据。"
overlap_with_current_patent: "与问题驱动证据区域提取和迭代补看重合；没有初答支持度触发、候选对称评分和回退。"
reusable_principle: "区域提取可用输出不确定性对视觉输入的敏感度，而非把内部注意力直接等同于证据。"
cannot_copy_directly: "熵梯度、多连通域排名和空间熵停止组成的免训练闭环已直接公开。"
evidence_quote_or_section: "正文 §3 Method；Table 7；附录 I Limitations。"
```

### PAPER-B018

```yaml
paper_id: PAPER-B018
title: "VideoGLaMM: A Large Multimodal Model for Pixel-Level Visual Grounding in Videos"
venue_year: "CVPR 2025"
official_url: "https://arxiv.org/abs/2411.04923"
full_text_url: "https://arxiv.org/pdf/2411.04923"
doi_or_arxiv: "arXiv:2411.04923"
publication_date: "2024-11-07"
code_url: "https://mbzuai-oryx.github.io/VideoGLaMM"
search_layer: B
relevance_tier: R2
mechanism_cluster: "视频像素级 grounding 与空间-时间双编码"
verified_from_full_text: true
reverse_evidence: false
technical_problem: "视频 LMM 能描述视频，但难把文本响应精确对应到跨帧像素区域。"
inputs: "视频与文本查询/对话。"
core_mechanism: "图像 encoder 提取逐帧空间特征，视频 encoder 提取分段时间特征；两个 V->L adapter 把二者送入 LLM；SEG token 隐状态经 L->V adapter 提示时空 pixel decoder，输出跨帧 mask。"
training_or_optimization: "冻结两类视觉 encoder、LLM 主权重、frame encoder 和 pixel decoder，只训练 LoRA 与 V->L/L->V adapter；联合文本交叉熵和 mask IoU 损失。"
inference_control_flow: "双视觉编码 -> LLM 文本响应 -> SEG token -> pixel decoder -> 时空 mask。"
data_structures: "空间/时间 token、SEG token、跨帧 mask；训练集含 38K grounded video-QA、83K 对象和 671K masks。"
technical_effect: "联合空间和时间分支优于仅空间 decoder；支持 grounded conversation、visual grounding 和 referring video segmentation。"
limitations: "作者指出自动/半自动标注仍有噪声且不覆盖所有对象；不同粒度对象表现不稳；数据主要为短中视频，尚未扩展长视频；增加帧数在对话质量与 mIoU 间有权衡。"
overlap_with_current_patent: "提供跨帧像素证据区域和对象关联基础；不处理 OCR/ASR、声明支持度或答案替换。"
reusable_principle: "跨帧证据区域应同时利用逐帧空间细节和分段时间上下文，并由统一对象 mask 保持身份。"
cannot_copy_directly: "双视觉 encoder、双向 adapter、SEG token 与视频 pixel decoder 已形成完整公开架构。"
evidence_quote_or_section: "正文 §3 VideoGLaMM；Table 6/7；Limitations and Future Work。"
```

## 4. 最接近反向证据

1. `PAPER-A007 Active Video Perception`
   - 已公开：证据充分性置信低于阈值时，根据缺口重规划时间区间、FPS 和分辨率，累加新证据后再次判断，达到阈值停止。
   - 未公开：围绕一个已生成开放式初答独立生成候选；初答与候选采用完全同一验证协议评分；绝对阈值与相对裕量共同控制替换；条件失败时保留初答。

2. `PAPER-A008 Think, Then Verify`
   - 已公开：候选答案假设化、最小判别线索、局部原始帧回看、三态验证、证据不足追加观察或重写假设、只基于已验证证据整合答案。
   - 未公开：候选由题目多选项给定，不是低支持初答后独立生成；没有初答/候选对称标尺、替换裕量和保守回退。

补充反向证据：

- `PAPER-A002` 已公开候选答案声明树、局部视频证据证明/反驳和动态扩树。
- `PAPER-A009` 已公开答案与时间段、跨帧密集 masklet 的联合输出及证据破坏评价。

以上仅描述论文覆盖范围，不作新颖性、创造性或授权判断。

## 5. 覆盖审计

| 用户要求方向 | 覆盖论文 |
|---|---|
| 图像/视频问答 | A001、A002、A003、A004、A008、A009、A010、A011、B014 |
| 长视频 | A005、A007、A008、A011、A012 |
| DocVQA | B013、B017 |
| 时序定位 | A002、A005、A007、A008、A009、A010 |
| 目标检测 | B015、B016 |
| OCR | A004、A012、B013 |
| 细粒度识别 | A003、B014、B015、B016 |
| 视觉 grounding | A002、A003、A009、A010、B015、B017、B018 |
| 证据区域提取 | A007、A009、A010、B014、B017、B018 |
| 跨帧关联 | A003、A009、A010、A011、A012、B018 |

## 6. 检索与抓取审计

- `WebSearch`：8 次，未超过 12 次预算。
- arXiv 批量元数据查询：3 次，用于核验最早公开日期和论文族，不计入 `WebSearch`。
- 全文请求：22 次，其中成功抓取并解析 17 篇、失败请求 5 次，恰好用完 22 次预算。失败请求包括 AAAI PDF 中途截断 1 次、FOCUS 的 OpenReview 403/浏览器校验 3 次、VideoGLaMM 的错误 CVF PDF 路径 1 次；FOCUS 与 VideoGLaMM 后续通过 arXiv 正文成功核验。
- 失败且未纳入：`Grounded Multi-Hop VideoQA in Long-Form Egocentric Videos` 的 AAAI PDF 下载中途截断；为避免超预算，未重试且未写入正式卡片。
- 本地优先复用：
  - `learn/patent-research/prior-art/2026顶会论文检索与广告视频问答专利创新方案_20260814.md`
  - `docs/2025-2026视觉VQA定位视频理解扩展文献池.md`
  - `docs/AdsQA_2026_crop_literature_review_20260806.md`
  - `docs/真实参考文献核查清单.md`
- 覆盖不足：
  - 目标检测仅覆盖开放词汇检测与不可定位拒绝，未系统覆盖 2024-2026 小目标检测全部分支。
  - DocVQA 只精读一篇架构论文及一篇同时覆盖 DocVQA 的区域检索论文，未扩展表格/图表问答专门模型。
  - 跨帧关联主要来自对象 mask/track 和任务基准，未单列传统 MOT/ReID 基础论文。
  - 未做引用链穷举、未覆盖付费数据库；“未检到”不得解释为不存在相关论文。
