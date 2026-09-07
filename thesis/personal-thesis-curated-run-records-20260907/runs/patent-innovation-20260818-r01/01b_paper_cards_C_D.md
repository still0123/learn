# I1-B 论文机制卡片：C层多模态大模型与D层可靠性系统

## 1. 边界与审计摘要

- 角色边界：仅检索、核验和拆解论文机制；不判断专利授权性，不构思专利候选。
- 检索日期：2026-08-18。
- 去重规则：arXiv、会议版和后续修订版合并为一个论文族，以最早公开日期为准。
- 外部检索：WebSearch `12/12`。
- 全文抓取：`23/23` 次尝试；成功核验 `20` 个论文族，失败 `3` 次。
- 失败抓取：CVPR 2026 `Understanding the Role of Hallucination...` PDF 返回404；NeurIPS 2025 `ViCrit`、`When Thinking Drifts` PDF超时。三者均未进入卡片。
- 日期核验：19个arXiv论文族使用免费arXiv Atom元数据的 `published` 字段核对v1日期；HalLoc使用CVF正式全文页，未核得更早预印本。
- 本地复用：优先复用 `docs/2025-2026视觉VQA定位视频理解扩展文献池.md`、`docs/论文思考记录.md`、`learn/patent-research/audit/09_search_materials_report.md` 中的候选URL；所有纳入结论重新以正文核验。

## 2. 机制覆盖

| 机制簇 | 论文 |
|---|---|
| 假设/声明验证与工具调用 | PAPER-CD-001、009、010 |
| 主动观察、补证、预算停止 | PAPER-CD-002、004、005、006、007、020 |
| 候选比较、证据选举与保守改写 | PAPER-CD-003、016 |
| 证据质量、选择性预测与风险控制 | PAPER-CD-008、014、015 |
| 幻觉定位与检测 | PAPER-CD-009、010、011、013、016 |
| Grounded推理与审计轨迹 | PAPER-CD-001、002、003、005、012、013 |
| 反事实/困难负例训练 | PAPER-CD-013、016 |
| 视觉Token压缩与预算分配 | PAPER-CD-004、017、018、019、020 |

## 3. 最接近的反向证据

以下论文不是一般背景，而是已经覆盖当前流程若干关键关系的强反向证据：

1. `PAPER-CD-001 Think, Then Verify`：先把候选答案改写为可验证假设，再生成最小判别线索，定位细粒度视频证据并验证后作答。
2. `PAPER-CD-002 Active Video Perception`：反射器以证据充分性/置信阈值决定停止或继续观察，并维护结构化、带时间戳的累积证据。
3. `PAPER-CD-003 RLER`：训练时产出机器可解析的关键帧证据；推理时对多候选按证据一致性、置信度、透明度和非冗余性加权选举，并在低裕量时扩充预算。
4. `PAPER-CD-008 SIEVES`：显式评价回答正确性、证据定位质量和答案-证据一致性，并据此执行选择性回答/拒答。
5. `PAPER-CD-009 TACO`：把回答拆成原子二元查询，对每条原子事实做多重改写、自一致性/概率置信聚合，再据此修订回答。

这些论文分别缺少视频声明级独立验证器、初答/候选同协议对称评分、绝对阈值与相对裕量共同控制的回退协议等部分，但已经使“拆声明、验证、按充分性补看、比较候选、拒答/选举”本身成为拥挤机制区。

## 4. 论文卡片

### PAPER-CD-001

```yaml
paper_id: PAPER-CD-001
title: "Think, Then Verify: A Hypothesis-Verification Multi-Agent Framework for Long Video Understanding"
venue_year: "CVPR 2026"
official_url: "https://arxiv.org/abs/2603.04977"
doi_or_arxiv: "arXiv:2603.04977"
publication_date: "2026-03-05"
code_url: "https://github.com/Haorane/VideoHV-Agent"
search_layer: C
relevance_tier: R1
mechanism_cluster: hypothesis_verification
verified_from_full_text: true
technical_problem: "长视频CoT和相关性检索易发生语义漂移、早期错误传播，检到相关片段不等于证据支持候选。"
inputs: "长视频、问题、候选答案、帧级描述/查询相关摘要。"
core_mechanism: "Thinker把候选改写成含实体、动作及时序/因果约束的可检验假设；Judge提炼区分假设的最小线索；Verifier定位局部片段并判定支持/部分支持/反驳；Answer整合已验证证据。"
training_or_optimization: "以多Agent提示编排为主，正文未提出声明支持度校准训练。"
inference_control_flow: "摘要→假设→判别线索→定位与细粒度验证→证据整合；可进入自精炼循环。"
data_structures: "候选假设H、判别线索kappa、证据E、验证状态S。"
technical_effect: "将相关性检索转为候选假设驱动的证据检验，并减少无目的试错。"
limitations: "面向多选长视频QA；依赖预生成描述和多个LLM Agent；验证状态不是经独立校准的声明支持概率，也未定义候选替换失败时保留初答的协议。"
overlap_with_current_patent: "高度覆盖候选答案假设化、定向取证、验证后决策的流程骨架。"
reusable_principle: "先定义可证伪信息需求，再获取最小判别证据。"
cannot_copy_directly: "多Agent角色拆分和提示链本身已公开，且其验证对象是候选选项而非开放回答中的原子声明。"
evidence_quote_or_section: "Abstract; §3.2 Overall Framework; §3.3 Hypothesis/Verification"
```

### PAPER-CD-002

```yaml
paper_id: PAPER-CD-002
title: "Active Video Perception: Iterative Evidence Seeking for Agentic Long Video Understanding"
venue_year: "CVPR 2026 Findings"
official_url: "https://arxiv.org/abs/2512.05774"
doi_or_arxiv: "arXiv:2512.05774"
publication_date: "2025-12-05"
code_url: "https://github.com/SalesforceAIResearch/ActiveVideoPerception"
search_layer: C
relevance_tier: R1
mechanism_cluster: active_evidence_loop
verified_from_full_text: true
technical_problem: "查询相关证据稀疏且分散，查询无关的视频描述既耗算力又损失精细时空信息。"
inputs: "长视频、查询、历轮计划和结构化证据。"
core_mechanism: "Planner决定看什么、在哪里看、如何采样；Observer从像素提取带时间戳证据；Reflector按查询充分性估计置信度，超过阈值则停止，否则写入计划/证据/理由并重规划。"
training_or_optimization: "训练自由的Agent编排；通过最大轮数和置信阈值控制流程。"
inference_control_flow: "plan→observe→reflect→stop/re-plan。"
data_structures: "结构化时间对齐证据列表、轮次历史、观察规格(what/where/how)。"
technical_effect: "把视觉预算集中到问题相关区域，并让证据充分性而非固定轮数决定继续观察。"
limitations: "充分性由MLLM反射器自评，存在共同失误；多Agent调用仍有成本；没有原子声明级监督、候选对称评分或替换失败回退。"
overlap_with_current_patent: "直接覆盖低充分性触发继续观察、累积证据、充分即停。"
reusable_principle: "证据列表和不足理由共同构成下一次观察的控制状态。"
cannot_copy_directly: "plan-observe-reflect及阈值停止已公开，不能仅改工具名称或应用场景。"
evidence_quote_or_section: "Abstract; §3.1-§3.3; Appendix B.3 threshold sensitivity"
```

### PAPER-CD-003

```yaml
paper_id: PAPER-CD-003
title: "Reinforce to Learn, Elect to Reason: A Dual Paradigm for Video Reasoning"
venue_year: "CVPR 2026"
official_url: "https://arxiv.org/abs/2604.04379"
doi_or_arxiv: "arXiv:2604.04379"
publication_date: "2026-04-06"
code_url: ""
search_layer: D
relevance_tier: R1
mechanism_cluster: evidence_weighted_candidate_election
verified_from_full_text: true
technical_problem: "单次视频推理不能检验推理是否与关键帧一致，多条轨迹也缺少证据层仲裁。"
inputs: "视频、问题、多条候选推理/答案及关键帧引用。"
core_mechanism: "训练阶段用关键帧敏感、思维透明和反重复奖励塑造可解析证据；推理阶段解析候选，按证据共现/关系一致性、长度归一置信、透明度和冗余度打分，去极值后证据加权选举，并做一次反驳检查。"
training_or_optimization: "GRPO加格式、答案正确及三类证据奖励。"
inference_control_flow: "多样采样→结构解析→证据评分→加权选举→低裕量增样/足够则早停→referee复核。"
data_structures: "reasoning trace z、关键帧集合K、候选证据分数、选举裕量。"
technical_effect: "把训练时证据输出与推理时多候选选择闭环连接。"
limitations: "平均需多候选推理；证据主要来自模型自报关键帧和自检，缺少外部事实验证；分数不提供跨分布校准或有限样本风险保证。"
overlap_with_current_patent: "高度覆盖同题多候选、证据评分、相对裕量控制增算力/停止及保守复核。"
reusable_principle: "训练输出字段与推理评分字段应同构，证据裕量可控制预算。"
cannot_copy_directly: "证据加权候选选举和低裕量增样已被完整公开。"
evidence_quote_or_section: "Abstract; §1; §4.1 RLER-Training; §4.2 RLER-Inference"
```

### PAPER-CD-004

```yaml
paper_id: PAPER-CD-004
title: "LongVideo-R1: Smart Navigation for Low-cost Long Video Understanding"
venue_year: "CVPR 2026"
official_url: "https://arxiv.org/abs/2602.20913"
doi_or_arxiv: "arXiv:2602.20913"
publication_date: "2026-02-24"
code_url: "https://github.com/qiujihao19/LongVideo-R1"
search_layer: C
relevance_tier: R2
mechanism_cluster: budget_aware_navigation
verified_from_full_text: true
technical_problem: "穷举处理长视频的成本随时长增长，有限预算下需决定下一段看哪里及何时停止。"
inputs: "分层视频树、问题、已观察片段描述。"
core_mechanism: "从顶层摘要开始，Agent在树中下钻、横移或回退；收集到足够上下文后调用叶节点VideoQA并停止，否则继续导航。"
training_or_optimization: "GPT-5合成33K CoT-with-tool轨迹；Qwen3-8B先SFT再用导航效率/定位/答案奖励做RL。"
inference_control_flow: "caption→判断充分性→navigate或leaf QA→答案/最大轮次停止。"
data_structures: "K叉D层视频树、导航步骤序列、累计计算成本。"
technical_effect: "显式优化准确率-计算成本Pareto权衡。"
limitations: "均匀树切分会割裂语义；依赖合成轨迹和片段描述；QA工具仅在叶层调用；无声明事实校准和候选回退。"
overlap_with_current_patent: "覆盖预算感知的证据获取和充分即停，但不比较初答与独立候选。"
reusable_principle: "把每次工具调用成本纳入轨迹目标，并允许回退到上层重新导航。"
cannot_copy_directly: "分层树导航、充分即停和成本奖励已公开。"
evidence_quote_or_section: "Abstract; §3.1-§3.3; Appendix D failure examples"
```

### PAPER-CD-005

```yaml
paper_id: PAPER-CD-005
title: "LensWalk: Agentic Video Understanding by Planning How You See in Videos"
venue_year: "CVPR 2026"
official_url: "https://arxiv.org/abs/2603.24558"
doi_or_arxiv: "arXiv:2603.24558"
publication_date: "2026-03-25"
code_url: ""
search_layer: C
relevance_tier: R2
mechanism_cluster: reason_plan_observe_audit
verified_from_full_text: true
technical_problem: "固定预处理视图无法随中间假设变化重新分配时间范围和采样密度。"
inputs: "源视频、问题、累计证据、主体记忆表。"
core_mechanism: "Reasoner逐轮选择带参数的Scan Search、Segment Focus或Stitched Verify，指定时间范围和密度；工具返回帧间时间戳锚点；主体记忆表维持跨轮实体一致性。"
training_or_optimization: "训练自由，依赖现成LLM/VLM组合。"
inference_control_flow: "reason→plan(tool, range, density)→observe→update evidence/memory→continue/answer。"
data_structures: "工具调用Schema、时间戳锚点、subject memory table、逐轮证据。"
technical_effect: "使观察粒度随推理状态改变，并留下可读的工具轨迹。"
limitations: "证据仍由VLM生成而非独立验证；多轮调用成本依赖问题难度；时间戳和主体表是可追溯记录但不是防篡改审计或事实保证。"
overlap_with_current_patent: "覆盖动态时间补看、多段拼接验证和审计轨迹。"
reusable_principle: "工具参数、原始时间锚点和记忆更新应作为同一回执保存。"
cannot_copy_directly: "reason-plan-observe、多粒度工具和主体表均已公开。"
evidence_quote_or_section: "§3.1-§3.4; Appendix A tool schema; Appendix C.3 failure modes"
```

### PAPER-CD-006

```yaml
paper_id: PAPER-CD-006
title: "DeepEyes: Incentivizing Thinking with Images via Reinforcement Learning"
venue_year: "ICLR 2026"
official_url: "https://arxiv.org/abs/2505.14362"
doi_or_arxiv: "arXiv:2505.14362"
publication_date: "2025-05-20"
code_url: "https://github.com/Visual-Agent/DeepEyes"
search_layer: C
relevance_tier: R2
mechanism_cluster: native_visual_tool_rl
verified_from_full_text: true
technical_problem: "纯文本CoT不能持续利用细粒度视觉信息，小目标/模糊区域易引发幻觉。"
inputs: "图像、问题、累计文本与裁剪观察。"
core_mechanism: "模型在每个文本推理步后决定直接回答或生成bbox调用zoom-in；裁剪结果回注轨迹，可重复多次；对整条图文交错轨迹做端到端RL。"
training_or_optimization: "无冷启动SFT；主动感知潜力数据筛选+任务成功时工具奖励加成。"
inference_control_flow: "text reasoning→answer或bbox crop→append observation→继续推理。"
data_structures: "交错文本/图像状态序列、bbox工具调用。"
technical_effect: "将视觉工具动作内生到策略模型，形成图文交错CoT。"
limitations: "主要是单图而非视频；动作集中于区域裁剪；成功奖励不等同于证据事实校准；同一模型同时定位、推理和回答，错误相关。"
overlap_with_current_patent: "覆盖模型自决二次观察和视觉回注，但无声明验证器及保守替换协议。"
reusable_principle: "把工具观察作为MDP状态的一部分，对完整轨迹而非单动作优化。"
cannot_copy_directly: "按需zoom、bbox回注和端到端工具RL已公开。"
evidence_quote_or_section: "§3.1 DeepEyes; §3.2 Agentic RL; Appendix E Limitations"
```

### PAPER-CD-007

```yaml
paper_id: PAPER-CD-007
title: "Thinking With Videos: Multimodal Tool-Augmented Reinforcement Learning for Long Video Reasoning"
venue_year: "CVPR 2026"
official_url: "https://arxiv.org/abs/2508.04416"
doi_or_arxiv: "arXiv:2508.04416"
publication_date: "2025-08-06"
code_url: ""
search_layer: C
relevance_tier: R2
mechanism_cluster: multimodal_tool_augmented_rl
verified_from_full_text: true
technical_problem: "视频长CoT跨模态交互弱，语言推理链容易脱离原视频并产生幻觉。"
inputs: "视频、问题、历轮文本推理、视频裁剪工具返回的密集帧。"
core_mechanism: "模型逐轮决定调用视频裁剪工具或回答，工具按起止时间返回密集帧并回注多模态CoT；联合训练时序定位、VQA和grounded VQA。"
training_or_optimization: "MTVR-CoT-72k SFT冷启动+MTVR-RL-110k；DGRPO按任务和样本难度调节奖励尺度。"
inference_control_flow: "生成思考/工具调用→解析→裁剪回注→下一轮→答案。"
data_structures: "多模态工具轨迹tau、时间裁剪参数、解析错误/工具错误状态。"
technical_effect: "把时序定位和回答联合为原生视频工具调用学习。"
limitations: "训练数据和RL成本高；工具主要是时间裁剪；奖励以任务结果为主，不提供声明级事实判别、校准或安全回退。"
overlap_with_current_patent: "覆盖按需时间补看和独立工具轨迹训练。"
reusable_principle: "对不同难度任务进行奖励尺度归一，避免工具策略被容易样本主导。"
cannot_copy_directly: "视频裁剪回注、SFT+RL工具轨迹和难度感知GRPO已公开。"
evidence_quote_or_section: "§3.1 Tool-Augmented Learning; §3.2 datasets; §3.3 DGRPO; Appendix F"
```

### PAPER-CD-008

```yaml
paper_id: PAPER-CD-008
title: "SIEVES: Selective Prediction Generalizes through Visual Evidence Scoring"
venue_year: "arXiv 2026"
official_url: "https://arxiv.org/abs/2604.25855"
doi_or_arxiv: "arXiv:2604.25855"
publication_date: "2026-04-28"
code_url: "https://github.com/hector-gr/SIEVES"
search_layer: D
relevance_tier: R1
mechanism_cluster: visual_evidence_selective_prediction
verified_from_full_text: true
technical_problem: "VQA置信分数跨模型和OOD数据泛化差，模型内部logit/激活对闭源模型不可用。"
inputs: "问题、原图、含zoom裁剪的多模态CoT、最终答案。"
core_mechanism: "小型selector同时预测答案正确性、证据定位质量和答案-证据一致性，组合为可跨问题排序的置信分数，在用户风险水平下选择回答或拒答。"
training_or_optimization: "在开放模型轨迹上监督训练selector，测试时迁移到未见数据及闭源reasoner。"
inference_control_flow: "reasoner产出视觉证据与答案→selector三轴评分→按风险阈值回答/拒答。"
data_structures: "correctness/localization/coherence三分量、risk-coverage曲线。"
technical_effect: "把显式定位证据变成模型无关的选择性预测信号。"
limitations: "单图VQA；依赖reasoner显式zoom轨迹和有标签selector训练；是整题正确性选择而非原子声明验证；经验risk-coverage不等于有限样本风险保证。"
overlap_with_current_patent: "高度覆盖用外显视觉证据质量控制回答采纳/拒绝。"
reusable_principle: "可靠性分数应显式分解为答案、定位和证据一致性，而非只读模型自信。"
cannot_copy_directly: "证据质量selector和risk-coverage拒答机制已公开。"
evidence_quote_or_section: "Abstract; §3.1-§3.2; Appendix A selective metrics"
```

### PAPER-CD-009

```yaml
paper_id: PAPER-CD-009
title: "Taming Object Hallucinations with Verified Atomic Confidence Estimation"
venue_year: "arXiv 2025"
official_url: "https://arxiv.org/abs/2511.09228"
doi_or_arxiv: "arXiv:2511.09228"
publication_date: "2025-11-12"
code_url: ""
search_layer: D
relevance_tier: R1
mechanism_cluster: atomic_self_verification_calibration
verified_from_full_text: true
technical_problem: "MLLM对象存在、属性和关系幻觉受措辞敏感性与失准影响。"
inputs: "图像、用户问题、初始回答。"
core_mechanism: "抽取最小原子语义单元并转成正向二元问题；为每题生成多种等价改写；用多数一致性或带logit权重的自信聚合；将更可信的原子答案回写到最终回答。"
training_or_optimization: "推理时校准，无外部视觉专家；黑盒/灰盒两种置信估计。"
inference_control_flow: "初答→原子问题→改写采样→置信聚合→文本LLM修订。"
data_structures: "实体/属性/关系taxonomy、原子二元问题集、self-consistency/self-confidence。"
technical_effect: "把整体幻觉纠正细化到可独立校准的原子事实。"
limitations: "同一MLLM自验会保留相关错误；多次改写增加成本；以单图对象类幻觉为主；最终文本修订器可能引入新错误；不获取新视频证据。"
overlap_with_current_patent: "直接覆盖答案原子化、逐声明评分、聚合后修订。"
reusable_principle: "用语义等价改写暴露措辞敏感性，并在原子层聚合置信。"
cannot_copy_directly: "原子问题、自一致/概率置信和回答回写的完整链路已公开。"
evidence_quote_or_section: "§3.1 Atomic Query; §3.2 Reformulation; §3.3 Confidence; §3.4 Refinement"
```

### PAPER-CD-010

```yaml
paper_id: PAPER-CD-010
title: "Unified Hallucination Detection for Multimodal Large Language Models"
venue_year: "ACL 2024"
official_url: "https://arxiv.org/abs/2402.03190"
doi_or_arxiv: "arXiv:2402.03190"
publication_date: "2024-02-05"
code_url: "https://github.com/zjunlp/EasyDetect"
search_layer: D
relevance_tier: R1
mechanism_cluster: claim_level_tool_augmented_hallucination_detection
verified_from_full_text: true
technical_problem: "多模态幻觉检测任务、类别和粒度分裂，整体回答标签不能定位具体错误。"
inputs: "图文对或文本到图像对、生成回答。"
core_mechanism: "抽取essential claims；为每条claim生成查询并自主选择视觉/知识工具；并行执行工具；聚合证据后判断claim是否幻觉并输出理由。"
training_or_optimization: "主要依赖GPT-4/Gemini编排及现成工具，MHaluBench用于检测器元评估。"
inference_control_flow: "claim extraction→query/tool routing→parallel execution→evidence aggregation→claim verdict+rationale。"
data_structures: "response/segment/claim三级标注、对象/属性/场景文字/事实taxonomy。"
technical_effect: "把工具增强事实核验统一到claim粒度，并支持多类冲突。"
limitations: "依赖闭源大模型和多工具，成本/时延高；正文承认任务和幻觉类别覆盖仍有限；检测不自动形成保守候选替换或风险保证。"
overlap_with_current_patent: "覆盖声明抽取、多工具取证、声明级幻觉判断。"
reusable_principle: "按claim类型路由专用工具并行核验，证据和理由一起返回。"
cannot_copy_directly: "claim级工具路由与证据聚合已公开，简单视频化不足以形成新机制。"
evidence_quote_or_section: "§4.1-§4.4; §5.3 failure analysis; Limitations"
```

### PAPER-CD-011

```yaml
paper_id: PAPER-CD-011
title: "HalLoc: Token-level Localization of Hallucinations for Vision Language Models"
venue_year: "CVPR 2025"
official_url: "https://openaccess.thecvf.com/content/CVPR2025/html/Park_HalLoc_Token-level_Localization_of_Hallucinations_for_Vision_Language_Models_CVPR_2025_paper.html"
doi_or_arxiv: ""
publication_date: "2025-06-11"
code_url: "https://github.com/dbsltm/cvpr25_halloc"
search_layer: D
relevance_tier: R2
mechanism_cluster: token_hallucination_localization
verified_from_full_text: true
technical_problem: "句子/回答级二值检测粒度粗且外部大模型核验延迟高，不能指出具体高风险token。"
inputs: "VLM生成期间的隐藏表示/生成token。"
core_mechanism: "构建155K token级对象、属性、关系、场景幻觉标注；轻量HalLocalizer与VLM并发运行，逐token输出幻觉概率。"
training_or_optimization: "HQA注入管线构造可控幻觉样本，监督训练轻量检测头。"
inference_control_flow: "VLM生成与token风险检测并行；高概率token提示外部复核。"
data_structures: "token标签、幻觉类型、连续概率。"
technical_effect: "低开销定位答案内的具体高风险内容。"
limitations: "大量样本由注入式合成；主要是单图VQA/描述/指令；概率检测不验证真实证据，也未证明视频时序泛化。"
overlap_with_current_patent: "部分覆盖答案内部细粒度风险定位，但不做声明-视频证据验证。"
reusable_principle: "检测输出应保留连续风险与类型，而不是只给整句二值结果。"
cannot_copy_directly: "token级并发幻觉检测已公开。"
evidence_quote_or_section: "Abstract; §3 taxonomy; §4 HalLoc; PDF pp.1-5"
```

### PAPER-CD-012

```yaml
paper_id: PAPER-CD-012
title: "Evidence-Backed Video Question Answering"
venue_year: "ECCV 2026 / arXiv"
official_url: "https://arxiv.org/abs/2607.11862"
doi_or_arxiv: "arXiv:2607.11862"
publication_date: "2026-07-13"
code_url: "https://github.com/SalesforceAIResearch/EVQA"
search_layer: C
relevance_tier: R1
mechanism_cluster: dense_spatiotemporal_evidence
verified_from_full_text: true
technical_problem: "VideoLLM文本答案缺少可核验视觉依据，稀疏框不能覆盖遮挡、形变和跨帧身份保持。"
inputs: "视频、问题。"
core_mechanism: "要求联合输出答案、支持时间段和密集追踪分割masklet；ST-Evidence人工标注/复核，ST-Evidence-Instruct 160K用于联合指令微调。"
training_or_optimization: "语义QA、时间证据和像素级时空grounding联合训练。"
inference_control_flow: "视频QA→时间段→关键证据对象描述/密集masklet输出。"
data_structures: "统一三元组(A, E_t, E_s)，E_t为不重叠时间段集，E_s为masklet。"
technical_effect: "把高层答案与可检查的像素级时空证据绑定。"
limitations: "证据标注昂贵；高QA准确率仍可伴随低grounding；不检测原子声明、不执行低支持补看或候选回退。"
overlap_with_current_patent: "强覆盖答案证据回指和审计字段，但不覆盖可靠性控制闭环。"
reusable_principle: "答案与证据应作为同一结构化输出合同联合评测。"
cannot_copy_directly: "答案+时间段+masklet的证据输出任务和训练数据已公开。"
evidence_quote_or_section: "Abstract; §3 E-VQA; §3.1 ST-Evidence; §5.4 analyses"
```

### PAPER-CD-013

```yaml
paper_id: PAPER-CD-013
title: "DeFacto: Counterfactual Thinking with Images for Enforcing Evidence-Grounded and Faithful Reasoning"
venue_year: "arXiv 2025; v4标注ICML"
official_url: "https://arxiv.org/abs/2509.20912"
doi_or_arxiv: "arXiv:2509.20912"
publication_date: "2025-09-25"
code_url: "https://github.com/tinnel123666888/defacto"
search_layer: D
relevance_tier: R1
mechanism_cluster: counterfactual_evidence_abstention
verified_from_full_text: true
technical_problem: "回答正确不代表证据正确，视觉推理会出现错定位但蒙对答案。"
inputs: "原图、问题、正证据区域、证据遮挡图、随机无关遮挡图。"
core_mechanism: "正样本要求证据框和答案均正确；反事实样本遮掉必要证据并要求unknown；随机遮挡无关区域用于排除遮罩捷径；结构化输出bbox/think/answer。"
training_or_optimization: "语言引导+RPN/OCR/开放词汇检测构造DeFacto-100K；GRPO同时奖励答案、格式和证据一致性。"
inference_control_flow: "定位证据→grounded reasoning→答案；必要证据缺失时拒答。"
data_structures: "正/反事实/随机遮挡三元组，bbox-think-answer合同。"
technical_effect: "用最小证据可用性变化区分真实依赖与视觉/语言捷径。"
limitations: "单图区域级；依赖候选框、OCR和开放词汇检测质量；遮罩伪影可能形成分布线索；训练的是回答模型而非独立验证器。"
overlap_with_current_patent: "直接覆盖必要证据最小移除、反事实拒答和证据-答案一致训练。"
reusable_principle: "必须加入同形随机无关干预，才能把缺证据效应与遮罩效应分离。"
cannot_copy_directly: "正/必要证据遮挡/随机遮挡三路训练和unknown约束已公开。"
evidence_quote_or_section: "§1; §3.1 Overall Framework; §3.2 counterfactual construction; §3.3 rewards"
```

### PAPER-CD-014

```yaml
paper_id: PAPER-CD-014
title: "Conformal Risk Control"
venue_year: "ICLR 2024; arXiv 2022"
official_url: "https://arxiv.org/abs/2208.02814"
doi_or_arxiv: "arXiv:2208.02814"
publication_date: "2022-08-04"
code_url: ""
search_layer: D
relevance_tier: R2
mechanism_cluster: conformal_risk_control
verified_from_full_text: true
technical_problem: "普通置信阈值缺少有限样本风险保证，且目标风险不总是简单miscoverage。"
inputs: "冻结模型、独立校准集、随保守参数单调下降的有界损失。"
core_mechanism: "在校准集上选择最小保守参数lambda，使修正经验风险加有限样本项B/(n+1)不超过目标alpha，从而控制新样本期望损失。"
training_or_optimization: "模型无关后处理，无需重训基础模型。"
inference_control_flow: "定义单调风险族→独立校准→冻结lambda→部署。"
data_structures: "风险函数L_i(lambda)、经验风险、目标alpha、冻结lambda。"
technical_effect: "在交换性和单调损失条件下提供分布无关有限样本期望风险控制。"
limitations: "依赖交换性、损失有界及相对lambda单调；非单调风险不保证；是总体期望保证而非单样本正确保证，也不指定视频证据获取机制。"
overlap_with_current_patent: "提供阈值冻结和风险-覆盖控制的基础方法，不直接覆盖视频QA闭环。"
reusable_principle: "阈值应由独立校准和明确风险函数冻结，不能在评测集调参。"
cannot_copy_directly: "共形风险控制为通用基础方法。"
evidence_quote_or_section: "§1.1 Algorithm; Theorem 1; §2.4 non-monotone risks; §3.4 QA example"
```

### PAPER-CD-015

```yaml
paper_id: PAPER-CD-015
title: "An Empirical Analysis of Calibration and Selective Prediction in Multimodal Clinical Condition Classification"
venue_year: "CHIL 2026"
official_url: "https://arxiv.org/abs/2603.02719"
doi_or_arxiv: "arXiv:2603.02719"
publication_date: "2026-03-03"
code_url: "https://github.com/jlaitue/medcertain"
search_layer: D
relevance_tier: R2
mechanism_cluster: calibration_failure_reverse_evidence
verified_from_full_text: true
technical_problem: "多模态融合提高判别性能时，基于不确定性的拒答未必更可靠。"
inputs: "EHR时序、胸片、多标签疾病预测和模型概率。"
core_mechanism: "按类别分解ECE，绘制选择性AUROC/AUPRC随拒绝阈值变化，比较多种融合架构和损失重加权。"
training_or_optimization: "MedFuse/DrFuse/MeTra；温度缩放、少数类损失重加权等校准干预。"
inference_control_flow: "概率/熵→阈值拒绝→按覆盖率评测；无生成式回答。"
data_structures: "总体ECE、正负类ECE、selective curves、少数类分层。"
technical_effect: "证明聚合指标会掩盖类别级失准，选择性预测甚至可能随着拒绝而退化。"
limitations: "单一ICU基准、回顾性且同分布；任务是临床多标签分类而非开放式VideoQA；作者未提出完整修复方法。"
overlap_with_current_patent: "作为反向证据，否定“有不确定性阈值就能安全选择”的一般化假设。"
reusable_principle: "必须做类别/模态分层校准和risk-coverage，不能只报告总体ECE/AUROC。"
cannot_copy_directly: "其贡献是失效诊断，不是视频回答验证流程。"
evidence_quote_or_section: "§3 calibration/selective prediction; §5.2; §6 Limitations"
```

### PAPER-CD-016

```yaml
paper_id: PAPER-CD-016
title: "When Model Priors Conflict with Visual Evidence: Mitigating Commonsense-Driven Hallucinations by Selective Prior Calibration"
venue_year: "arXiv 2026"
official_url: "https://arxiv.org/abs/2607.29240"
doi_or_arxiv: "arXiv:2607.29240"
publication_date: "2026-07-31"
code_url: "https://github.com/MiLab-HITSZ/2026ChenSPC"
search_layer: D
relevance_tier: R1
mechanism_cluster: selective_prior_calibration
verified_from_full_text: true
technical_problem: "视觉反事实与常识先验冲突时模型偏向普通答案，但无差别抑制先验又会伤害正常图像。"
inputs: "图像、问题、候选集、带图与无图的候选token分数。"
core_mechanism: "以无图候选分数估计先验偏好；13维实例特征预测校正强度lambda；从图像条件分数扣除先验分数；只有替代候选满足支持条件时才改答。"
training_or_optimization: "在成对CF/CS开发集上低容量MAP拟合校正强度，兼顾反事实修复和正常样本保持。"
inference_control_flow: "带图/无图双评分→自适应先验扣除→替代提案→支持条件门控改答/保持。"
data_structures: "图像分数s_I、先验分数s_P、13维特征、校正分数s_C、改答支持条件。"
technical_effect: "把有方向的先验冲突转为实例化校正，并限制无证据的有害改答。"
limitations: "限多选/二元问题；需logit和成对CF/CS开发数据；无图分数只是先验代理；单图，不含视频补证或原子声明。"
overlap_with_current_patent: "高度覆盖双评分、相对支持条件和保守保持原答案。"
reusable_principle: "把候选校正视为提案，只有视觉支持充分时才覆盖原输出。"
cannot_copy_directly: "带图/无图分数差和选择性改答条件已公开。"
evidence_quote_or_section: "§3 Candidate-Level Score Correction; Learning Strength; Selective Answer Revision"
```

### PAPER-CD-017

```yaml
paper_id: PAPER-CD-017
title: "PruneVid: Visual Token Pruning for Efficient Video Large Language Models"
venue_year: "Findings of ACL 2025"
official_url: "https://arxiv.org/abs/2412.16117"
doi_or_arxiv: "arXiv:2412.16117"
publication_date: "2024-12-20"
code_url: "https://github.com/Visual-AI/PruneVid"
search_layer: D
relevance_tier: R2
mechanism_cluster: spatiotemporal_token_pruning
verified_from_full_text: true
technical_problem: "视频时空冗余造成预填充、KV缓存和解码成本高。"
inputs: "视频token、问题token、LLM中间层注意力。"
core_mechanism: "先沿时间合并静态区域token，再聚类合并空间相似token；随后用问题到视频的中间层注意力保留任务相关token，并同步压缩后续KV缓存。"
training_or_optimization: "训练自由，接入现有VideoLLM。"
inference_control_flow: "静动态分离→时空合并→LLM中间层问题引导剪枝→压缩KV解码。"
data_structures: "静态/动态token、聚类、question-to-video attention、压缩KV。"
technical_effect: "在多种VideoLLM上大比例减少视觉token、FLOPs和显存。"
limitations: "注意力并非因果证据；小字和短时关键事件可能被误合并/误剪；优化平均任务性能而非声明证据保留，无事实可靠性保证。"
overlap_with_current_patent: "覆盖问题条件化视频token压缩，不覆盖补看和验证闭环。"
reusable_principle: "冗余合并与任务相关性剪枝应分阶段处理。"
cannot_copy_directly: "普通时空token合并和问题注意力剪枝已公开。"
evidence_quote_or_section: "§3.2 Spatial-Temporal Merging; §3.3 LLM-Guided Selection; §4.5"
```

### PAPER-CD-018

```yaml
paper_id: PAPER-CD-018
title: "FrameFusion: Combining Similarity and Importance for Video Token Reduction on Large Vision Language Models"
venue_year: "ICCV 2025"
official_url: "https://arxiv.org/abs/2501.01986"
doi_or_arxiv: "arXiv:2501.01986"
publication_date: "2024-12-30"
code_url: "https://github.com/thu-nics/FrameFusion"
search_layer: D
relevance_tier: R2
mechanism_cluster: similarity_then_importance_compression
verified_from_full_text: true
technical_problem: "只按重要性剪枝忽略相邻帧重复，且token重要性跨层不稳定。"
inputs: "相邻帧对应位置视觉token、跨层特征和重要性。"
core_mechanism: "利用相邻帧对应token的高相似度及跨层排序稳定性，在浅层级联合并相似token，再按重要性剪枝到预算。"
training_or_optimization: "plug-and-play，无额外训练。"
inference_control_flow: "浅层相似度计算→级联合并→重要性剪枝→后续LLM。"
data_structures: "token相似度、Spearman跨层排序稳定性、预算。"
technical_effect: "同时利用重复性和重要性，改善压缩-性能Pareto前沿。"
limitations: "相邻对应位置假设不适合快速镜头切换；视觉相似片段可能有不同事实状态；平均性能损失小不代表关键证据不丢失，也无问题级可靠性校验。"
overlap_with_current_patent: "覆盖预算内视频token去重，但不覆盖动态补证或验证。"
reusable_principle: "先消除重复，再评估任务重要性，避免重要但重复token挤占预算。"
cannot_copy_directly: "相似度级联合并加重要性剪枝已公开。"
evidence_quote_or_section: "§3.2-§3.4 similarity observations; method and experiments"
```

### PAPER-CD-019

```yaml
paper_id: PAPER-CD-019
title: "SpecVLM: Enhancing Speculative Decoding of Video LLMs via Verifier-Guided Token Pruning"
venue_year: "EMNLP 2025"
official_url: "https://arxiv.org/abs/2508.16201"
doi_or_arxiv: "arXiv:2508.16201"
publication_date: "2025-08-22"
code_url: "https://github.com/zju-jiyicheng/SpecVLM"
search_layer: D
relevance_tier: R2
mechanism_cluster: verifier_guided_draft_pruning
verified_from_full_text: true
technical_problem: "视频token使推测解码草稿模型KV缓存成为瓶颈，直接输入剪枝又可能损失生成质量。"
inputs: "目标模型注意力、草稿模型、长视频token。"
core_mechanism: "目标模型作为推测解码verifier提供注意力评分；第一阶段Top-P保留高信息token，第二阶段对低注意token做空间均匀缩减；仅草稿分支激进剪枝，目标模型并行验收草稿token以保持无损输出。"
training_or_optimization: "训练自由推测解码。"
inference_control_flow: "target attention rating→draft两阶段剪枝→草稿多token→target并行验收/拒绝。"
data_structures: "高信息token集、低注意token空间采样、accept length、draft/target KV。"
technical_effect: "把激进视觉剪枝限制在可被目标模型验收的草稿路径。"
limitations: "此处verifier验证的是草稿token分布一致性，不是回答事实或证据支持；目标模型仍处理完整上下文；收益是解码速度，非可靠性提升。"
overlap_with_current_patent: "仅在“先激进候选、再由较强路径验收”抽象层相似。"
reusable_principle: "有信息损失的近似路径可受无损验收路径约束。"
cannot_copy_directly: "推测解码和目标模型注意力引导的两阶段剪枝已公开。"
evidence_quote_or_section: "§2.2; §3.1-§3.2; §9 Limitation"
```

### PAPER-CD-020

```yaml
paper_id: PAPER-CD-020
title: "LENS: Adaptive Spatio-Temporal Zooming for Keyframe Sampling in Long-Form Videos"
venue_year: "ECCV 2026"
official_url: "https://arxiv.org/abs/2607.25125"
doi_or_arxiv: "arXiv:2607.25125"
publication_date: "2026-07-27"
code_url: "https://github.com/zhangce01/LENS"
search_layer: C
relevance_tier: R2
mechanism_cluster: adaptive_spatiotemporal_budget
verified_from_full_text: true
technical_problem: "有限帧预算下，局部细节分辨率与长时覆盖相互竞争。"
inputs: "长视频、文本查询、固定帧预算。"
core_mechanism: "空间分支用图文相似度和CLIP注意做查询相关视觉提示；时间分支构建视频图、消息传递并聚合hyperframe；轻量控制器按查询在空间zoom-in与时间zoom-out间动态分配预算。"
training_or_optimization: "训练自由、plug-and-play。"
inference_control_flow: "查询分析→空间/时间预算分配→两分支采样→合并关键帧→VideoLLM回答。"
data_structures: "空间注意图、视频图、hyperframe、分支预算。"
technical_effect: "在固定预算下按问题类型平衡细粒度细节和长程上下文。"
limitations: "是一次性采样而非验证后迭代；控制器不输出校准不确定性；CLIP注意和图聚合可能漏掉短时/小区域决定性证据，无声明级保留保证。"
overlap_with_current_patent: "覆盖动态分辨率/时空预算分配，但不覆盖低支持触发和候选回退。"
reusable_principle: "预算应显式分配给空间精度与时间覆盖两个竞争维度。"
cannot_copy_directly: "按查询自适应时空zoom和预算分配已公开。"
evidence_quote_or_section: "§3.2 Spatial Zoom-in; §3.3 Temporal Zoom-out; §3.4 Budget Allocation; Appendix C"
```

## 5. 覆盖不足

1. 视频开放回答的“原子声明→独立视频证据验证→校准风险→保守替换”完整单篇仍缺少直接实证；现有最接近工作分别覆盖其中不同子链。
2. 音频/ASR与视觉证据的跨模态时间对齐未做专项深挖，本轮主要覆盖视觉和视频帧证据。
3. 审计轨迹多数是时间戳、关键帧引用、工具调用和结构化证据列表；未检到面向VideoLLM的不可篡改血缘、哈希回执或完整数据谱系论文。
4. 选择性预测的有限样本保证来自通用共形风险控制；SIEVES等Video/VQA方法主要提供经验risk-coverage，二者之间的端到端适配尚未充分覆盖。
5. 动态分辨率覆盖以LENS的时空预算为主，未系统覆盖所有编码器内动态分辨率和patch级路由方法。
6. 三篇本地高相关候选因正文端点失败未纳入，不能据此下结论：ViCrit、When Thinking Drifts、Understanding the Role of Hallucination in Reinforcement Post-Training。

## 6. 结论边界

本文件只说明论文已经公开的技术问题、机制、控制流和局限。任何“未检到”的表述仅代表本轮C/D层、12次检索和23次全文抓取预算内的部分覆盖，不代表不存在相关论文，也不构成新颖性、创造性或授权判断。
