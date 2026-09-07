# I1 2026论文机制卡片（全文核验）

- 最终卡片仅保留R1/R2论文族。
- R1：34
- R2：43
- 合计：77
- R3/R4、背景论文及不可用记录保留在 `01_sources_papers.jsonl`。

## PAPER-VERIFIED-003 A Unified Object-Centric Spatio-Temporal Graph Reasoning Framework for Audio-Visual Question Answering

- **标识：** 10.1145/3805622.3810845
- **正式年份：** Proceedings of the 2026 International Conference on Multimedia Retrieval (2026)
- **最早公开：** 2026-06-15
- **正文入口：** https://doi.org/10.1145/3805622.3810845
- **层级：** A / R1
- **机制簇：** AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M06, M05, M08
- **正文位置：** §3.1 Input Representation, §3.2 Motion-guided Object Tracking, §3.3 Sound-guided Object Tracking, §3.4 Question-guided Spatio-temporal Graph, §3.5 Multimodal Reasoning and Prediction, §4.5 Ablation Studies
- **技术问题：** AVQA的帧/patch级粗粒度表示难以定位发声对象和连续建模时空动态，问题语义通常只在后期融合，指导会衰减。
- **核心机制：** MOT用时间共指边和运动差分突出运动对象；SOT按音频-视觉一致性强化发声对象；QSTG统一视觉对象与音频对象节点，以运动差分门控和问题引导图注意持续调节消息传播。
- **控制流：** 提取对象、音频和问题表示；运动引导跟踪筛出显著对象；声音引导绑定视觉对象与音频；构建统一时空图并执行问题条件消息传播；融合后预测答案。
- **数据结构：** 视觉对象节点, 音频对象节点, 时间共指边, 空间/时间关系边, 运动显著性, 运动差分门控, 问题引导注意权重
- **技术效果：** 在MUSIC-AVQA和MUSIC-AVQA-R上提升细粒度发声对象定位、时空动态建模和复杂推理准确率。
- **局限：** 正文无独立Limitations章节；依赖对象跟踪和音频绑定质量，错误会沿图传播；实验集中于音乐AVQA分类数据，未验证开放式长视频、主动补证或证据校准。
- **反向证据：** 否

## PAPER-VERIFIED-054 Hierarchical Long Video Understanding with Audiovisual Entity Cohesion and Agentic Search

- **标识：** arXiv:2601.13719
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-01-20
- **正文入口：** https://arxiv.org/abs/2601.13719
- **层级：** A / R1
- **机制簇：** AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M06, M04, M05
- **正文位置：** §3.1 Overview, §3.2 Database Construction, §3.3 Agentic Search with Reasoning, §4.3 Ablation Study, §5 Conclusion, Appendix B Multi-Granularity Tools
- **技术问题：** 平坦clip-caption检索会造成信息碎裂，跨镜头实体身份和音视频语义在长时间跨度内难以保持一致。
- **核心机制：** 离线构建segment、canonical audiovisual entity、scene和global四级数据库，以说话人身份连接跨镜头实体；推理代理按需组合场景、caption、视觉、实体搜索和局部检查工具。
- **控制流：** 每30秒segment生成说话人感知caption和视觉embedding；聚类并由LLM规范化跨段实体；按语义连续性聚合scene/global摘要；查询从全局摘要开始，逐步升级文本、视觉和实体工具，找到答案或达到步数上限后停止。
- **数据结构：** 四级数据库D={segment,entity,scene,global}, 时间戳转写与speaker label, canonical audiovisual entity, scene/global摘要, 工具上下文记忆
- **技术效果：** 通过音视频实体凝聚和层级索引增强跨段实体识别、时间定位和推理，并减少平坦检索的迭代次数。
- **局限：** 无独立Limitations章节；数据库构建和规划依赖闭源模型；固定30秒segment与稀疏采样可能漏短时细节；部分数据无音频，停止由同一Planner控制。
- **反向证据：** 否

## PAPER-VERIFIED-107 See More, Think Deeper: Query-Expanded Visual Evidence and Answer-Clue Guided Reflection for Long Video Understanding

- **标识：** arXiv:2606.09064
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-08
- **正文入口：** https://arxiv.org/abs/2606.09064
- **层级：** A / R1
- **机制簇：** SELF_CORRECTION_REFLECTION
- **对应本地机制：** M06, M05, M08, M07
- **正文位置：** §3.1 Overview, §3.2 CueZoom, §3.3 Query-Expanded Visual Evidence, §3.4 Answer-Clue Guided Reflection, §3.5 Two-Stage SFT, §3.6 GRPO, §6 Limitations
- **技术问题：** 长视频证据获取通常只有单一搜索意图，初始答案生成后又缺少基于新视觉证据的反馈验证。
- **核心机制：** QVE从问题与全局观察生成最多三个伪查询，CueZoom按多cue相似度、时间平滑和自适应阈值检索高分辨率片段；AGR从草稿答案生成应满足的视觉clue，再检索支持/反驳证据并保留或修订答案。
- **控制流：** 建立低分辨率全局观察；按需生成伪查询并第一次zoom-in，结合扩展证据生成草稿；从草稿提取验证clue并第二次zoom-in；检查视觉支持后保留或修订；训练由两阶段SFT和证据奖励GRPO完成。
- **数据结构：** 伪查询集合P, 逐帧cue相关性, 平滑相关性序列, 自适应阈值, query-expanded evidence clips, answer-specific clue, 草稿/最终答案
- **技术效果：** 形成显式视觉反馈闭环，使7B模型在长视频基准上优于同规模模型并在部分指标超过闭源模型。
- **局限：** 伪查询和答案clue可能含糊或有偏；验证clue受初始答案条件化，可能形成确认偏差；两次zoom-in增加计算；整体理解问题未必适合局部证据检索。
- **反向证据：** 否

## PAPER-VERIFIED-141 When and Where to Look: Adaptive Visual Evidence Scheduling for Efficient Long Video Understanding

- **标识：** arXiv:2608.03918
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-08-04
- **正文入口：** https://arxiv.org/abs/2608.03918
- **层级：** A / R1
- **机制簇：** ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M08, M05, M07
- **正文位置：** §3 Motivation and Analysis, §4.1 Overview, §4.2 Entropy-Gated Budget Scheduling, §4.3 Attention-Guided Candidate Proposal, §4.4 Marginal-Utility Frame Reselection, §5.2–5.4 Experiments, §7 Conclusion, Appendix C Limitations
- **技术问题：** 固定帧预算和固定候选池无法适应不同问题的证据需求，而代理式多轮搜索调度开销过高。
- **核心机制：** EcoFrame复用目标VLM内部信号进行免训练调度：以输出熵判断当前证据是否充分并控制预算扩展，以帧级attention形成时间先验并扩展候选池，再按查询相关性、时间覆盖和边际效用重选帧。
- **控制流：** 从低预算帧集生成答案、熵和attention；若熵低于随轮次放宽的阈值则提前停止，否则按几何计划增加预算；集中attention触发局部密集搜索，分散attention保持全局覆盖；重选后进入下一轮，达到最大预算时停止。
- **数据结构：** 轮次帧预算序列, 输出熵, 帧级attention, 时间cell先验, 候选帧池, 相关性/覆盖边际效用
- **技术效果：** 在不增加独立Agent的情况下获得闭环证据调度，正文报告相对静态选择和代理调度实现更优准确率-延迟权衡。
- **局限：** 输出熵不是正确性证书；阈值与最大预算仍为全局配置且跨模型/领域需校准；极短事件在长视频中仍可能因候选帧有限而遗漏；attention只是搜索先验。
- **反向证据：** 否

## PAPER-VERIFIED-006 AdaptToken: Entropy-based Adaptive Token Selection for MLLM Long Video Understanding

- **标识：** arXiv:2603.28696
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-30
- **正文入口：** https://arxiv.org/abs/2603.28696
- **层级：** A / R1
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §3.1 Group Relevance with Response Entropy, §3.2 Entropy-guided Global Token Selection, §3.3 Location-aware Global Token Removal, §3.4 Early-stopping, §5 Conclusion
- **技术问题：** 分组处理超长视频时缺少跨组连续相关性比较，也缺少证据已足够时提前停止的控制信号。
- **核心机制：** 用每组回答中最低置信10% token的负熵估计组相关性；同一次前向提取跨模态注意作为组内token分数；全局分配token并做位置感知去冗余，AdaptToken-Lite再以置信度早停。
- **控制流：** 交错划分覆盖全视频的帧组；逐组前向得到响应熵和token注意；按组置信与组内分数全局选token并去除位置相近冗余；置信达到条件时跳过剩余组，否则继续；选中token供最终回答。
- **数据结构：** 帧组, 组置信C_g, 视觉token相关性R, 全局token预算, 位置与相似度去冗余集合, 早停状态
- **技术效果：** 训练免费地扩展到10K帧，并在多模型/基准上提升准确率；Lite版本约减半推理时间。
- **局限：** 响应熵只是模型自置信代理，可能高置信出错；帧组组织和遍历顺序影响早停；组内分数依赖选定LLM层的注意力，尚无独立充分性保证。
- **反向证据：** 否

## PAPER-VERIFIED-010 Beyond Frame Selection: Generative Latent Evidence Aggregation for Long-Video Understanding

- **标识：** arXiv:2607.28516
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-07-30
- **正文入口：** https://arxiv.org/abs/2607.28516
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION, LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M04, M07
- **正文位置：** §3.1 Problem Formulation: Latent Evidence Interface, §3.2 Evidence-Budget Allocation, §3.3 Query-Aware Latent Evidence Aggregation, §3.4–3.5 Joint Optimization and Adaptive Invocation, §4 Experiments, §5 Conclusion, §7.2–7.3 Case Studies and Token Accounting
- **技术问题：** 即使帧选择器把相关视觉内容送入模型，显式可见并不保证跨时刻互补线索会在回答前被有效整合。
- **核心机制：** GenEvA先用查询条件分布给每帧分配至少一个、总数固定的潜证据slot；以逐帧内容和共享的问视觉cross-attention上下文条件化潜变量基，再由LoRA集成器吸收完整显式多模态输入；去掉保底slot后的分配离散度决定是否插入潜证据，集中分配走显式路由，分散分配触发跨帧潜聚合。
- **控制流：** 冻结选择器先给出K帧；allocator计算连续份额并确定性整数化为逐帧slot数；aggregation head生成并集成B个潜证据token；计算残余分配离散度，超过1/2则调用潜证据路由，否则保留显式帧路由；最终由同一冻结骨干生成答案。
- **数据结构：** 查询条件帧分配分布, 逐帧整数潜token预算, 可学习潜变量基, 共享问视觉上下文, B个集成潜证据token, 分配离散度与二元路由
- **技术效果：** 在不扩大显式帧上下文的情况下增强跨帧证据利用，正文在四个基准和两种骨干上报告匹配帧预算的稳定增益及很低的平均token开销。
- **局限：** 机制只处理冻结选择器已经保留的帧，无法恢复选择阶段遗漏的原始证据；仍需在8K样本上训练allocator、LoRA和聚合头，且依赖特定TSPO选择器及固定离散度阈值；两条路由都保留显式帧，潜token并非可审计的源片段或事实保证。
- **反向证据：** 否

## PAPER-VERIFIED-012 CADER: Confidence-Aware Dynamic Evidence Reasoning for Long-Video Understanding

- **标识：** arXiv:2607.24582
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-07-27
- **正文入口：** https://arxiv.org/abs/2607.24582
- **层级：** A / R1
- **机制簇：** CONFIDENCE_UNCERTAINTY_ROUTING, ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M06, M08
- **正文位置：** Method — Overview and Stage 1, Method — Stage 2 Tool-assisted Fine-grained Reasoning, Method — Relevance-Guided Resampling, Experiments — Ablation and Routing Analysis, Appendix D Reflection Depth Analysis, Conclusion
- **技术问题：** 统一对所有长视频问题执行完整工具推理会浪费计算，而单次全局推理在困难样本上又会被无关帧稀释并缺少精细时间证据。
- **核心机制：** CADER以Top-1/Top-2温度softmax裕量路由：高置信样本在全局阶段早退，低置信样本进入时间段提议、预算感知密采样和轻量VLM二元验证；验证失败时反思提出不重叠新区间，RGR再按累计相关分数降低已判无关区域帧率、保留未探索区域覆盖。
- **控制流：** 1 FPS全局推理并计算logit margin；margin≥0.97直接输出；否则提议局部区间，过宽区间回退全局答案；对有效crop密采样并验证，Yes≥0.60则局部推理；否则至多反思2次并以RGR重采样；仍失败时返回缓存的Stage 1答案。
- **数据结构：** 候选答案概率与logit裕量, 候选时间区间, Yes/No验证概率, 带分数搜索区间历史, 分段fps映射, Stage 1缓存答案
- **技术效果：** 把工具调用按样本难度分配，在五个长视频基准上改善骨干准确率，同时让38.6%的评测样本跳过第二阶段。
- **局限：** logit裕量和Yes概率均是模型内部置信代理而非正确性证书，阈值跨域仍需校准；过宽提议、两轮反思耗尽或证据持续漏检时直接回退原答案；最大深度样本增益仅0.5个百分点，显示搜索预算存在明显递减；实验集中于多选题和Qwen3-VL同族主模型/验证器。
- **反向证据：** 否

## PAPER-VERIFIED-036 Evidence-Driven Dynamic Visual Selector for Efficient Long Video Understanding

- **标识：** arXiv:2608.05780
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-08-06
- **正文入口：** https://arxiv.org/abs/2608.05780
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION
- **对应本地机制：** M04, M08, M07
- **正文位置：** Methodology Overview, Evidence Grounding, Distribution-Aware Dynamic Sampling, Policy Optimization with GRPO, Ablation Study, Conclusion
- **技术问题：** 外部代理评分器和固定规则与目标MLLM内部证据不一致，也不能适应视频时空信息密度变化。
- **核心机制：** 在高度压缩视频上做块稀疏prefill，提取query-frame、cross-frame和intra-frame三类注意力先验；轻量策略同时预测时间戳保留、局部采样率和空间分辨率，并用准确率-效率联合奖励做GRPO。
- **控制流：** 均匀划分时间段并生成低分辨率锚帧；目标MLLM稀疏prefill并分解三类证据；selector采样(z_t,rho_t,lambda_t)；按决策重采样多尺度视频；目标MLLM最终推理；GRPO按正确性和视觉成本更新。
- **数据结构：** 三类注意力证据E_qf/E_ff/E_if, 逐时间戳联合动作u_t, 保留/采样率/分辨率分布, 压缩多尺度视觉输入
- **技术效果：** 在三个长视频基准上用约一半答案阶段视觉token获得更高表现，并实现3.9倍端到端加速。
- **局限：** 依赖目标MLLM可访问的内部注意力，迁移到其他架构可能受限；闭源MLLM无法使用。
- **反向证据：** 否

## PAPER-VERIFIED-043 FocusGraph: Graph-Structured Frame Selection for Embodied Long Video Question Answering

- **标识：** arXiv:2603.04349
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-04
- **正文入口：** https://arxiv.org/abs/2603.04349
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION
- **对应本地机制：** M04, M07, M08
- **正文位置：** §3 Method, §3.1–3.5 Scene Graph, Selector, Training and PSFR, §4.1 Results, §4.2 Ablation studies, §5 Conclusion
- **技术问题：** 具身长视频包含大量冗余帧，直接增加MLLM输入会同时降低回答质量和推理效率，而仅靠低分辨率帧序列又难以保留长程对象与场景关系。
- **核心机制：** FocusGraph先让MLLM把固定长度clip压缩为对象中心文本场景图，再由Scene-Caption LLM Selector从时间增强caption中选相关clip，最后用训练免费的Patchwise Sparse-Flow Retention按局部角点轨迹留存和结构变化选取去冗余关键帧。
- **控制流：** 离线切分视频并生成clip级场景图；ModernBERT表示经adapter送入微调后的LLM选择Top相关clip；PSFR在所选clip内按patch稀疏光流检测结构变化并在固定预算下保留多样关键帧；按时间顺序送入MLLM回答。
- **数据结构：** 带时间区间的clip级文本场景图, caption embedding序列, 相关clip集合, patch角点轨迹与留存率, 固定预算关键帧集合
- **技术效果：** 把语义片段选择与低层视觉去冗余解耦，在FindingDory和HourVideo上以少量帧取得有竞争力的准确率并显著降低选择器推理时间。
- **局限：** 依赖预生成MLLM场景图和GenS-Video-150K监督微调；Top-8 clip及文本图压缩可能丢失未被描述的视觉细节；PSFR按查询无关的低层光流选帧，且超参数由特定数据上的程序进化确定，跨域和多目标任务表现仍受限。
- **反向证据：** 否

## PAPER-VERIFIED-048 Ground, Cover, and Refine: Evidence-Centric Frame Selection for Long-Video Question Answering

- **标识：** arXiv:2608.01660
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-08-03
- **正文入口：** https://arxiv.org/abs/2608.01660
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION
- **对应本地机制：** M04, M07, M08
- **正文位置：** Methodology — Problem Formulation and Budget Allocation, Ground: Narrative-Grounded Event Anchoring, Cover: Complementary Evidence Construction, Refine: Omitted Evidence Reclamation, Experiments — Overall/Ablation/Sensitivity, Conclusion — Limitations
- **技术问题：** 固定预算选帧容易在局部相关峰聚集，预算耗尽后无法回收遗漏证据；时间戳文本若仅作为独立提示，也难与对应视觉时刻可靠绑定。
- **核心机制：** GCR把预算分为受保护的叙事锚点、视觉锚点和可替换上下文：Ground按文本与视觉相关性选事件真帧并把事件文字渲染到对应帧；Cover以直接视觉Top-K和全局MMR补足互补上下文；Refine扫描未选择时间间隙，以相关性、新颖性和变化评分真实medoid，仅在其价值高于最弱上下文帧时一换一回收。
- **控制流：** 从时间戳事件生成候选区间并选唯一锚点；加入查询相关视觉锚点；MMR填满固定预算形成初始集；若最大遗漏间隙超过阈值，则按价值降序检查间隙medoid并至多替换Kr个弱上下文帧；受保护核心不被驱逐，最终按时间排序回答。
- **数据结构：** 时间戳文本事件及帧区间, 受保护Ground/Visual锚点集, MMR上下文集, 遗漏时间间隙, 真实帧medoid, 相关性/新颖性/变化统一价值与替换裕量
- **技术效果：** 在不训练下游VLM、不增加帧预算的情况下联合文本落地、全局覆盖和遗漏回收，在两个长视频基准、三种7B骨干和多种预算上稳定提升。
- **局限：** 依赖可用的时间戳字幕或ASR，缺少此类文本的视频适用性有限；文本渲染和关键词视觉需求先验依赖对齐质量；计数等任务仍较弱，未来需引入更稳健的音频和视觉grounding。
- **反向证据：** 否

## PAPER-VERIFIED-055 HiMu: Hierarchical Multimodal Frame Selection for Long Video Question Answering

- **标识：** arXiv:2603.18558
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-19
- **正文入口：** https://arxiv.org/abs/2603.18558
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION, AUDIO_VISUAL_ALIGNMENT, EVENT_CAUSAL_REASONING
- **对应本地机制：** M02, M04, M07
- **正文位置：** §3 Method, §3.1 Neuro-Symbolic Query Decomposition, §3.2–3.3 Expert Processing and Fuzzy Logic Composition, §4 Experiments, §5 Discussion — Limitations, Appendix C/D/E
- **技术问题：** 单一全局查询embedding会压平复合问题中的子事件顺序和音视频模态绑定，导致固定帧预算下漏选回答所需证据。
- **核心机制：** HiMu用一次纯文本LLM调用把问题分解为层级逻辑树，将原子谓词路由到CLIP、开放词汇检测、OCR、ASR和CLAP专家；经稳健归一化与模态带宽平滑后，用AND、OR、SEQ和RIGHTAFTER模糊算子自底向上合成逐帧满足曲线，再由PASS执行多峰发现、局部扩散和剩余预算填充。
- **控制流：** 解析问题生成受JSON约束的逻辑树；条件执行并缓存所需专家；归一化和平滑跨模态时间信号；按树拓扑合成满足曲线；PASS先选时间分离峰值、补峰值邻域，再按分数填满K帧；选中帧一次性送入下游MLLM。
- **数据结构：** 层级原子谓词逻辑树, 多专家逐帧信号, 跨模态平滑满足曲线, 峰值与邻域集合, 逐叶证据分数轨迹
- **技术效果：** 在不训练选择器且不反复调用视觉MLLM的情况下实现可解释的复合音视频选帧，正文在多个基准和七种MLLM上报告稳定增益。
- **局限：** 专家抽取慢于全局embedding检索；质量依赖逻辑树解析及底层专家覆盖，尤其受多语或噪声音频中的ASR影响；即使选对帧，下游MLLM仍可能无法融合跨帧证据。
- **反向证据：** 否

## PAPER-VERIFIED-058 How Well Can Your Video Model Remember? Measuring Memory-Budget Trade-offs in Long Video Understanding

- **标识：** arXiv:2606.20726
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-17
- **正文入口：** https://arxiv.org/abs/2606.20726
- **层级：** A / R1
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07, M04
- **正文位置：** §3.1 Problem Formulation, §3.2 The Empirical Model, §3.3 Estimation, §3.4 Validation, §4.6 Budget Allocation Application, §5.4 Limitations
- **技术问题：** 长视频中帧预算缩减和答案事件距查询时间变远时的准确率退化缺少可比较、可预测的连续模型。
- **核心机制：** 对约155K个二元预测拟合logit(P)=alpha(D)log10(B)+beta log10(D)+delta log10(T)+c，且alpha(D)=a+e log10(D)，以距离条件预算指数度量额外帧的边际价值。
- **控制流：** 按随机、均匀或近期策略离线采样B比例帧；批量运行模型；聚合预算-距离-长度单元；WLS估计系数并验证；用alpha(D)比较模型和分配预算。
- **数据结构：** 约155K个二元预测, 预算-距离-长度聚合单元, WLS系数(a,e,beta,delta,c), 距离条件预算指数alpha(D)
- **技术效果：** 提供连续的预算-距离诊断和部署预算分配依据，并揭示模型排序会随时间距离反转。
- **局限：** 主结果限于RIVER-bench事实回忆；部分模型拟合度低；未控制答案时间窗宽度；离线批量输入衡量帧覆盖而非原生在线缓存；采样策略和随机种子有限。
- **反向证据：** 否

## PAPER-VERIFIED-089 One Token per Highly Selective Frame: Towards Extreme Compression for Long Video Understanding

- **标识：** arXiv:2604.14149
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-04-15
- **正文入口：** https://arxiv.org/abs/2604.14149
- **层级：** A / R1
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §3.1 Preliminaries and Formulation, §3.2 Learnable and Progressive Token Compression, §3.3 Question-Conditioned Frame Compression, §4.3 Ablation Study, §5 Conclusion
- **技术问题：** 长视频逐帧产生大量视觉token，启发式极限压缩易丢信息，LLM长上下文注意力又存在首尾位置偏置。
- **核心机制：** LP-Comp在LLM层间按平滑计划学习渐进压缩，最终每帧一token；QC-Comp用LLM内部注意力选问题相关帧，并把长视频分段后做局部注意以减弱位置偏置。
- **控制流：** 视觉token进入LLM；各层按余弦计划逐步删除前缀并保留可吸收历史信息的后缀token；推理时分段计算问题条件注意力、选择高相关帧；组合两级压缩后生成答案。
- **数据结构：** 逐层每帧token序列, 压缩计划N(l), 问题条件帧注意力, 局部分段帧集合
- **技术效果：** 将每帧压缩到一个token并允许输入更多帧，在仅用少量监督微调数据时提升多个长视频基准。
- **局限：** 主要验证VideoChat-Flash-2B和LLaVA-Next-Video；QC帧选择未联合训练；更大模型、更多任务和预训练阶段集成尚未验证。
- **反向证据：** 否

## PAPER-VERIFIED-097 Reflect-R1: Evidence-Driven Reflection for Self-Correction in Long Video Understanding

- **标识：** arXiv:2606.27922
- **正式年份：** ECCV 2026
- **最早公开：** 2026-06-26
- **正文入口：** https://arxiv.org/abs/2606.27922
- **层级：** A / R1
- **机制簇：** SELF_CORRECTION_REFLECTION, EVIDENCE_SUFFICIENCY_VERIFICATION, ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M06, M08
- **正文位置：** §2 Preliminary Investigation, §3.1 Inference Framework, §3.2–3.4 SD-GRPO and Training, §4.2–4.3 Results and Ablations, §5 Qualitative Analysis, §6 Limitations, §7 Conclusion
- **技术问题：** 只靠内部参数反思会在缺少新视觉锚点时延续或放大初始幻觉，且端到端联合训练多阶段反思会因策略耦合退化为复制初始答案。
- **核心机制：** Reflect-R1用同一策略执行直觉、独立验证和仲裁三阶段：验证阶段隔离初答和全局视频，只看问题与检索关键帧并允许证据不足时弃答；仲裁阶段合并两路判断且强制再次调用工具回溯；SD-GRPO按阶段独立归一化优势，并以渐进优化、弃答激励和防错误改写奖励避免策略耦合。
- **控制流：** 直觉阶段回答并主动定位关键帧；隔离上下文后仅据关键帧生成验证或弃答；仲裁读取初答、验证和视频，重新检索以解决冲突并给最终答案；训练时分别计算三阶段组内优势和阶段奖励，再分阶段稳定后联合优化。
- **数据结构：** 初始答案y1, 检索关键帧F, 独立验证y2, 仲裁答案y3, 阶段特定上下文, 分阶段奖励与优势组, 工具调用轨迹
- **技术效果：** 把反思从内部闭环改为外部证据驱动，在三个长视频基准上提升最终准确率，并显示内部反思基线通常会降低准确率。
- **局限：** 三阶段长生成和多次工具调用增加延迟及算力，不适合严格实时场景；时间检索不准或关键线索弱时，验证与仲裁仍无充分支持；性能受底层VLM上限约束，复杂或歧义证据仍会失败。
- **反向证据：** 是

## PAPER-VERIFIED-102 REVEAL: A Rubric-Guided Agent for Explicit Evidence Sufficiency Verificationin Long-Video Question Answering

- **标识：** arXiv:2608.08612
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-08-09
- **正文入口：** https://arxiv.org/abs/2608.08612
- **层级：** A / R1
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, LONG_VIDEO_MEMORY_RETRIEVAL, ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M03, M04, M06
- **正文位置：** §3.1 Offline-Online Memory Framework, §3.2 Rubric Construction Pipeline, §3.3 Retrieve–Verify–Answer Loop, §4.2–4.4 Results, Ablation and Analysis, §5 Conclusion — Limitation, Appendix C.1 Case Study
- **技术问题：** 长视频检索常以语义相关性作为停止条件，相关片段即使缺少决定性的顺序、状态变化或细节也会触发回答；固定切块和静态离线记忆还会割裂事件且不记录搜索失败。
- **核心机制：** REVEAL把持久离线记忆与逐题在线状态分离；离线以视觉相似分段并建立L1局部事件、L2时间线和L3全局叙事，在线记录去重证据、已访问ID、历史查询、新证据标记和缺口分析；验证器从统一rubric池选准则并加权评分，未达阈值就把未满足准则转成定向或探索检索，达标后才交给隔离的answerer。
- **控制流：** 初轮把问题分解为2–4条检索查询并查三级记忆；更新在线证据与搜索历史；验证器对相关准则打0/0.5/1并聚合充分性ρ；ρ不足则输出具体缺失事实，Planner据此修复检索或探索未访问段；ρ达阈值或预算耗尽后，由独立回答角色基于最终去重证据作答。
- **数据结构：** L1/L2/L3层级离线记忆, 时间锚定文本与视觉embedding, 在线证据缓存与访问集合, 查询历史和新增证据标记, 统一加权rubric池, 准则满足向量与缺失证据分析
- **技术效果：** 将停止控制从相关性提升为可检查的充分性判断，在五个长视频基准上显著提升同骨干表现，并以更少证据获得更高准确率。
- **局限：** 充分性只表示决定性信息已收集而不保证答案正确；在线验证信号尚不能持续反向修订离线记忆；Planner、Verifier和Answerer共享同一VLM，错误可能相关；预算不足时仍输出best-supported答案而非拒答，rubric也依赖训练集上的对比证据和教师过滤。
- **反向证据：** 否

## PAPER-VERIFIED-132 VideoDetective: Clue Hunting via both Extrinsic Query and Intrinsic Relevance for Long Video Understanding

- **标识：** arXiv:2603.22285
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-23
- **正文入口：** https://arxiv.org/abs/2603.22285
- **层级：** A / R1
- **机制簇：** ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §3.2 Visual-Temporal Affinity Graph Construction, §3.3 Hypothesis-Verification-Refinement Iteration, §3.4 Segment Selection via Graph-NMS, §4.4 Efficiency Analysis, §6 Limitation
- **技术问题：** 仅按问题到片段相似度找线索忽略视频自身结构，稀疏观察难以推断未访问片段的相关性。
- **核心机制：** 把视频片段构成融合视觉相似与时间邻近的稀疏图，维护稀疏Injection Vector和稠密Belief Field；通过假设-验证-细化循环观察锚点并在图上扩散相关性，最后用Graph-NMS选证据。
- **控制流：** 语义分段并建图；把问题拆成facet并初始化先验；每轮按未解决facet或belief gap选择锚点，VLM检查片段并写入相关性分数；图扩散更新全局belief；预算结束后选Top片段回答。
- **数据结构：** 视觉-时间亲和图, Injection Vector Y, Belief Field F, 已访问掩码, 未解决facet集合, Graph-NMS证据包
- **技术效果：** 在只观察少量片段时利用片段间结构传播相关性，在多种MLLM和长视频基准上提升准确率。
- **局限：** 反馈信号依赖VLM自反思和缺失关键词判断；错误相关性可在图中传播，未提供独立证据充分性或保守回退。
- **反向证据：** 否

## PAPER-VERIFIED-135 VideoSEAL: Mitigating Evidence Misalignment in Agentic Long Video Understanding by Decoupling Answer Authority

- **标识：** arXiv:2605.12571
- **正式年份：** ICML 2026
- **最早公开：** 2026-05-12
- **正文入口：** https://arxiv.org/abs/2605.12571
- **层级：** A / R1
- **机制簇：** AGENT_TOOL_ROUTING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §3 Diagnosing Evidence Misalignment, §3.4 Remedy: Separating Planning and Answering, §4.1–4.4 Method, §6 Conclusion, Appendix C.9 Limitations, Appendix E Algorithm Details
- **技术问题：** 长视频代理把检索、共享上下文推理和最终回答耦合在同一模型中，会在证据不足时受prompt/reward pressure驱动而提前承诺。
- **核心机制：** 将长程搜索与回答权分离：Planner只检索或提交候选span，冻结的MLLM Inspector仅根据原问题和所提交视频证据给出二元充分性及反馈，并独占停止和最终回答权；证据不足则反馈驱动继续搜索。
- **控制流：** 离线建立16秒clip caption/embedding索引；Planner选择VisualRetrieve或VisualInspect；Inspector返回(z_t,f_t)；z_t=0时扩展或收紧时间窗并更新search memory，z_t=1时由Inspector回答；预算K耗尽则合并candidate cache并强制最后一次VisualInspect。
- **数据结构：** clip caption/embedding索引, compact search memory, 候选时间段cache, 二元充分性z_t, 缺失证据反馈f_t
- **技术效果：** 降低correct-but-ungrounded的证据错位，使搜索预算可转化为更好的答案准确率和groundedness，并允许Inspector替换升级。
- **局限：** 显式检查增加推理延迟；Inspector会误判充分性，造成过早停止或无谓检索；语义groundedness依赖LLM judge；残余错误包括细粒度视觉误识别、全局时序覆盖失败，且预算耗尽仍会强制检查。
- **反向证据：** 是

## PAPER-VERIFIED-139 VisualRouter: Query-Grounded Visual Sampling for Long Video Understanding

- **标识：** arXiv:2607.28463
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-07-30
- **正文入口：** https://arxiv.org/abs/2607.28463
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION, EVENT_CAUSAL_REASONING
- **对应本地机制：** M04, M07, M08
- **正文位置：** §III Method, §IV-A–IV-C Experiments and Ablation, §III-C Query Gating and §IV-C3 scope-boundary evidence
- **技术问题：** 固定或仅按相关性采样无法同时适配证据分散的全局问题与证据集中的局部问题，容易造成覆盖不足或帧冗余。
- **核心机制：** VisualRouter先用LVLM把问题二分为global或local；global分支将预算分给均匀覆盖与高相关帧，local分支按语义漂移划分事件、按事件相关性分配预算，并在事件内用相关性与K-DPP多样性选帧。
- **控制流：** 构建候选帧及相关性、语义和视觉特征；执行global/local门控；global分支合并均匀帧与Top相关帧，local分支执行事件划分、段级预算分配和段内去冗余选择；按时间排序后送入LVLM回答。
- **数据结构：** global/local路由标签, 帧级ITM相关性分数, EMA语义漂移与事件段, 事件级帧预算, K-DPP帧子集
- **技术效果：** 在相同帧预算下跨多种LVLM和三个长视频基准持续优于均匀采样；正文报告Qwen2.5-VL-7B在Video-MME、LongVideoBench和MLVU分别提升5.2、7.7和11.6个百分点。
- **局限：** 无独立Limitations章节；候选帧固定为1 FPS，门控仅二分global/local并由LVLM提示完成，LongVideoBench样本被统一硬路由为local；消融证明错误分支策略会降分，但未单独报告门控误分类率。
- **反向证据：** 否

## PAPER-VERIFIED-004 Active Video Perception: Iterative Evidence Seeking for Agentic Long Video Understanding

- **标识：** arXiv:2512.05774
- **正式年份：** CVPR Findings 2026
- **最早公开：** 2025-12-05
- **正文入口：** https://arxiv.org/abs/2512.05774
- **层级：** A+C / R1
- **机制簇：** DETAIL_INFORMATION_GATING, FRAME_EVIDENCE_SELECTION, active_evidence_loop
- **对应本地机制：** M04, M08
- **正文位置：** §3 Method and Algorithm 1, Appendix A Limitations, Appendix failure analysis, §3.1, §3.2, §3.3, Appendix B.3
- **技术问题：** 长视频中的决定性证据稀疏，单次全局观看难以在成本约束下获得充分证据。
- **核心机制：** Planner决定what/where/how，Observer累加带时间戳证据，Reflector以充分性阈值决定回答或按缺口重规划。
- **控制流：** Planner决定what/where/how；Observer获取局部证据；Reflector判断充分性，充分则回答，否则依据缺口重规划，轮次耗尽时强制回答。
- **数据结构：** 证据轨迹, 时间戳观察, 规划状态, 充分性判断
- **技术效果：** 以迭代证据寻求替代一次性全视频摄入，并显式分析观察器失效。
- **局限：** 仅离线QA；提示驱动而非学习策略；76%失败来自观察器；轮数耗尽会强制回答；无声明级监督、候选对称评分或保守回退。
- **反向证据：** 是

## PAPER-VERIFIED-013 CaST-Bench: Benchmarking Causal Chain-Grounded Spatio-Temporal Reasoning for Video Question Answering

- **标识：** arXiv:2605.23216
- **正式年份：** CVPR 2026
- **最早公开：** 2026-05-22
- **正文入口：** https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_CaST-Bench_Benchmarking_Causal_Chain-Grounded_Spatio-Temporal_Reasoning_for_Video_Question_Answering_CVPR_2026_paper.html
- **层级：** A / R1
- **机制簇：** EVENT_CAUSAL_REASONING, ROLE_ACTION_CAUSAL_REASONING
- **对应本地机制：** M07, M10
- **正文位置：** §3 Task Definition, §4 CaST-Bench, §5.2-5.3, §6 Conclusion
- **技术问题：** 视频QA缺少对多步因果链及其时空证据忠实性的细粒度诊断。
- **核心机制：** 每个因果链证据含时间段、事实rationale和1-FPS bbox轨迹；用遮蔽全部证据区域过滤可被猜中的问题。
- **控制流：** 无闭环推理模型；基准构造因果链证据，并通过遮蔽全部证据区域过滤可猜问题，再评测答案与证据忠实性。
- **数据结构：** 因果链, 事实rationale, 时间段, 1-FPS边界框轨迹
- **技术效果：** 分离因果答案正确性、结构化输出遵循性和证据忠实性。
- **局限：** 诊断基准而非闭环模型；1-FPS框非像素级；模型经常不遵循结构化输出且faithful rate低。
- **反向证据：** 否

## PAPER-VERIFIED-022 DigimonGPT: An Evolvable Agent with Hierarchical Human-like Memory for Video Question Answering

- **标识：** 10.1609/aaai.v40i8.37523
- **正式年份：** Proceedings of the AAAI Conference on Artificial Intelligence (2026)
- **最早公开：** 2026-03-14
- **正文入口：** https://doi.org/10.1609/aaai.v40i8.37523
- **层级：** A / R1
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07
- **正文位置：** Memory Construction, Intra-video Declarative Memory, Inter-task Procedural Memory, Hierarchical Memory Replay, Conclusion
- **技术问题：** VideoQA代理难以从历史问答和跨任务工具轨迹持续积累知识，反复从零规划带来计算开销且无法适应新任务。
- **核心机制：** 视频内声明性记忆包含segment caption/特征/对象轨迹的情景记忆和经LLM验证、摘要的历史QA语义记忆；跨任务程序性记忆存成功工具工作流；按问题复杂度动态决定三类记忆的回放数量。
- **控制流：** 基础代理执行观察-动作循环；完成任务后验证并摘要QA、归档工具序列到向量库；新问题到来时按相似度检索记忆，再以LLM评分和关键词熵估计复杂度，动态回放足量记忆指导工具调用和回答。
- **数据结构：** 情景记忆, 语义记忆向量库D_s, 程序性记忆向量库D_p, 对象轨迹与帧位置, 工具工作流, 问题复杂度分数
- **技术效果：** 无需反复微调即可复用视频内知识和跨任务策略，在NExT-QA与Intent-QA上提高平均准确率。
- **局限：** 正文无独立Limitations章节；依赖外部嵌入/LLM、对象跟踪和历史QA验证；错误记忆可能被持续复用，实验限于两个VideoQA数据集。
- **反向证据：** 否

## PAPER-VERIFIED-035 Evidence-Backed Video Question Answering

- **标识：** arXiv:2607.11862
- **正式年份：** ECCV 2026
- **最早公开：** 2026-07-13
- **正文入口：** https://arxiv.org/abs/2607.11862
- **层级：** A+C / R1
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, FINE_GRAINED_REGION_GROUNDING, dense_spatiotemporal_evidence
- **对应本地机制：** M05, M06
- **正文位置：** §3 Evidence-Backed Video QA, §4 Instruction Tuning Data Construction, Table 2 and Table 5, §6 Conclusion, §3, §3.1, §5.4
- **技术问题：** 视频问答答案通常没有同步输出可审计的时空支持证据。
- **核心机制：** E-VQA联合输出答案、非重叠时间段和跨帧密集masklet；双路径自动生成160K答案-证据训练数据。
- **控制流：** 模型联合生成语义答案、非重叠时间段和跨帧密集masklet；训练数据由两条自动化路径构建。
- **数据结构：** 答案, 支持时间段集合, 跨帧masklet
- **技术效果：** 为视频答案附加稠密时空证据，但不保证高QA准确率必然对应高grounding质量。
- **局限：** 密集标注昂贵且自动管线依赖大型VLM和分割器；QA与grounding仍解耦；未覆盖OCR/ASR；不做原子声明检测、低支持补看或候选回退。
- **反向证据：** 是

## PAPER-VERIFIED-047 GOPAgen: Motion-Aware and Efficient Agentic Long-Video Understanding with Structural Memory and Hierarchical Reasoning

- **标识：** arXiv:2606.06532
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-03
- **正文入口：** https://arxiv.org/abs/2606.06532
- **层级：** A / R1
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07
- **正文位置：** §3.1 Motion Agent Training Strategy, §3.2 Coarse-to-fine Structural Memory Construction, §3.3 GOP-Tree Reasoning, §4.5 Ablation Analysis, §4.6 Time and Token Efficiency, §5 Conclusion
- **技术问题：** 长视频代理很少利用编解码器运动矢量，且细粒度局部运动记忆的构建、存储和检索成本高。
- **核心机制：** 训练专用motion agent读取关键帧和运动矢量；global agent两轮粗到细选段；motion/caption agents构建包含视觉特征、详细caption和运动分析的分页记忆；GOP-tree按充分性检索和排序页面。
- **控制流：** 全局关键帧两级筛选Top-k片段；按GOP块存储并切片更新运动矢量数据库；构建超细片段memory pages；压缩全局上下文，信息不足时嵌入检索并由小LM排序页面，最后统一回答。
- **数据结构：** GOP块, 运动矢量数据库, 分页局部结构记忆, 全局记忆, 相关页面排名
- **技术效果：** 把视频codec原语和细粒度运动纳入代理推理，降低结构记忆检索的时间与token成本并改善动作和时序理解。
- **局限：** 无独立Limitations章节；依赖多代理、外部LLM API和向量库；motion agent训练含生成式描述；Top-k前置漏检难以恢复，充分性由同一推理代理判断。
- **反向证据：** 否

## PAPER-VERIFIED-053 HERBench: A Benchmark for Multi-Evidence Integration in Video Question Answering

- **标识：** arXiv:2512.14870
- **正式年份：** CVPR 2026
- **最早公开：** 2025-12-16
- **正文入口：** https://openaccess.thecvf.com/content/CVPR2026/html/Ami_HERBench_A_Benchmark_for_Multi-Evidence_Integration_in_Video_Question_Answering_CVPR_2026_paper.html
- **层级：** A / R1
- **机制簇：** EVENT_CAUSAL_REASONING, LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07
- **正文位置：** §3 HERBench, §5.1-5.2, §6 Conclusion
- **技术问题：** 长视频QA难以区分证据未检出与多条分散证据未融合两类错误。
- **核心机制：** 每题强制至少三个分散cue；MRFS和oracle frame/leave-one-out分析分离证据检索缺口与融合缺口。
- **控制流：** 无部署型控制流；以MRFS、oracle frame和leave-one-out实验分别诊断检索与融合缺口。
- **数据结构：** 分散证据cue集合, oracle帧集合, 消融结果
- **技术效果：** 把长视频多证据失败拆分为检索问题和融合问题。
- **局限：** 多选基准且固定16帧；oracle帧不可部署；只诊断检索/融合错误而不修复。
- **反向证据：** 否

## PAPER-VERIFIED-076 MemDreamer: Decoupling Perception and Reasoning for Long Video Understanding via Hierarchical Graph Memory and Agentic Retrieval Mechanism

- **标识：** arXiv:2606.07512
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-05
- **正文入口：** https://arxiv.org/abs/2606.07512
- **层级：** A / R1
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07
- **正文位置：** §3.1 Hierarchical Graph Memory, §3.2 Agentic Tool-Augmented Retrieval, §4.3 Analysis, §5 Conclusion
- **技术问题：** 小时级视频的完整视觉序列造成token爆炸和注意力稀释，平坦文本记忆又难以保留实体、微事件和因果关系。
- **核心机制：** 感知模型按语义边界流式分段，向下构建实体-微事件局部异构图并向上聚合为Macro Event、Super Event和Video Root三级图记忆；推理模型用多维工具在图中搜索节点、层级和逻辑边。
- **控制流：** 视频流自适应分段并生成局部子图；向上聚合层级摘要和跨层边；查询到来后，推理代理在Observation-Reason-Action循环中导航、搜索和遍历，收集精简线索后回答。
- **数据结构：** Video Root/Super Event/Macro Event三级节点, 实体节点, 微事件节点, 空间属性边, 主客体边, 时间因果边, 跨层边
- **技术效果：** 把感知与推理解耦，使推理仅访问约2%的完整上下文，并在四个长视频基准上提升准确率。
- **局限：** 无独立Limitations章节；纯文本图记忆受前置感知和摘要错误制约，未保留的视觉细节无法恢复；多轮工具与外部模型增加成本，停止缺少独立充分性校准。
- **反向证据：** 否

## PAPER-VERIFIED-088 One Ranking, Any Budget: Matryoshka Evidence-to-Context Frame Selection for Long-Video Understanding

- **标识：** arXiv:2608.05707
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-08-06
- **正文入口：** https://arxiv.org/abs/2608.05707
- **层级：** A / R1
- **机制簇：** FRAME_EVIDENCE_SELECTION
- **对应本地机制：** M04, M08
- **正文位置：** §3 Method, §3.2 Reusable Sparse Video Index, §3.3 Query-Conditioned Evidence Discovery, §3.4 Evidence-to-Context Matryoshka Ranking, §4.1–4.3 Experiments, Appendix D Limitations
- **技术问题：** 按不同帧预算分别优化子集会重复运行选择器并替换既有证据，而固定分数排序又无法让短前缀聚焦证据、长前缀逐步扩展上下文。
- **核心机制：** MEC构建可复用稀疏索引，缓存低分辨率外观、局部变化和可观测性；按问题以BLIP-2相关性等多线索激活高分segment并围绕anchor局部zoom；随后以随排名位置递减的证据权重和递增的时间覆盖权重，结合视觉多样性贪心生成不可替换的Matryoshka帧序列。
- **控制流：** 按视频时长建立有界均匀probe和segment；计算查询条件证据并激活Top segment；在anchor两侧补采zoom候选；从最高证据帧开始，逐位按证据、时间覆盖和视觉多样性的动态权重追加帧；请求任意K时截取同一序列前缀并按时间排序后送入LMM。
- **数据结构：** 稀疏probe索引, 低分辨率外观向量, 变化与可观测性分数, 激活segment和zoom候选池, 位置自适应权重序列, 嵌套Matryoshka帧排名
- **技术效果：** 一次排序可服务六种帧预算，短前缀保留核心证据、长前缀增补时序上下文；正文报告相对均匀采样更高的平均准确率和更低的端到端选择延迟。
- **局限：** 稀疏probe、segment均值和单anchor zoom会漏掉短暂孤立事件，后续排名无法恢复未进入候选池的证据；BLIP-2单帧相关性、32像素灰度变化和清晰度/曝光只是近似效用；贪心不可替换序列不保证任一预算或加权多预算目标的全局最优。
- **反向证据：** 否

## PAPER-VERIFIED-123 Think, Then Verify: A Hypothesis-Verification Multi-Agent Framework for Long Video Understanding

- **标识：** arXiv:2603.04977
- **正式年份：** CVPR 2026
- **最早公开：** 2026-03-05
- **正文入口：** https://arxiv.org/abs/2603.04977
- **层级：** A+C / R1
- **机制簇：** DETAIL_INFORMATION_GATING, EVIDENCE_SUFFICIENCY_VERIFICATION, hypothesis_verification
- **对应本地机制：** M06, M08
- **正文位置：** §3 Method and Algorithm 1, §4.4 Ablation, §5 Conclusion, Abstract, §3.2, §3.3
- **技术问题：** 长视频多选问答容易在未形成可检验假设和判别证据时直接作答。
- **核心机制：** 候选答案转可测试假设，Judge生成最小判别线索，Verifier局部回看并输出三态，证据不足时追加观察或重写假设。
- **控制流：** 候选答案转为可测试假设；Judge提炼最小判别线索；Verifier局部回看并输出三态；证据不足时追加观察或重写假设。
- **数据结构：** 候选假设, 判别线索, 局部观察, 三态验证结果
- **技术效果：** 把答案比较转化为假设-证据验证循环。
- **局限：** 依赖预给多选项和逐帧caption；每次细看最多五帧；Agent与状态均由提示产生；无独立校准的声明支持度及失败回退协议。
- **反向证据：** 是

## PAPER-VERIFIED-125 TimeLogic Challenge @ CVPR 2026: Strong MLLMs Meet Evidence-Seeking Agents for Temporal-Logic Video Question Answering

- **标识：** arXiv:2606.01631
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-01
- **正文入口：** https://arxiv.org/abs/2606.01631
- **层级：** A / R1
- **机制簇：** ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M08
- **正文位置：** §3.1 Overview, §3.2 Multi-Granular Sampling Toolkit, §3.3 Question-Type-Aware Exploration, §3.4 Think-Act-Observe Loop, §5 Conclusion
- **技术问题：** 固定均匀采样和单次作答容易漏掉窄动作边界或相隔很远的多事件证据，导致时间逻辑关系无法核验。
- **核心机制：** 先按规则把问题路由到时间逻辑类别，再使用overview、temporal_scan、skim和focus四级采样工具主动寻找带绝对时间戳的证据，并以最小步数门控抑制过早作答。
- **控制流：** 问题分类后执行初始扫描；VLM在Think-Act-Observe循环中读取累计状态、调用更细粒度采样或作答；达到置信条件且满足最小步数，或耗尽帧/步数预算后终止。
- **数据结构：** 带时间戳的观察序列, 动作时间线, 累计推理状态, 类别对应的帧预算与步数预算
- **技术效果：** 把时间逻辑VideoQA转为可迭代的时间戳证据搜索，在TimeLogic官方测试集取得77.13 AvgAcc。
- **局限：** 无独立Limitations章节；类别路由依赖规则和类别提示，停止依赖同一VLM的自评置信，实验使用Gemini 3.1 Pro并针对单一挑战设计。
- **反向证据：** 否

## PAPER-VERIFIED-134 VideoRouter: Query-Adaptive Dual Routing for Efficient Long-Video Understanding

- **标识：** arXiv:2605.05848
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-07
- **正文入口：** https://arxiv.org/abs/2605.05848
- **层级：** A / R1
- **机制簇：** AGENT_TOOL_ROUTING
- **对应本地机制：** M04, M08
- **正文位置：** §3.1 VideoRouter Architecture, §3.2 Inference, §4 Supervision and Data Construction, §5.4 Ablation Studies, §6 Conclusion
- **技术问题：** 固定或弱查询感知的视频压缩无法适应证据在时间上的非均匀分布，易在有限上下文中浪费token或丢失关键帧细节。
- **核心机制：** Semantic Router在全局覆盖与自适应保真策略间路由；Image Router复用早期LLM层估计逐帧相关性；在动态视觉预算下对关键帧保高分辨率、非关键帧强压缩或丢弃。
- **控制流：** 先计算可用视觉token预算；语义路由选择Global或Fragment策略；Fragment策略按逐帧分数分配两级分辨率，优先保关键帧、再保背景，极端预算下先丢低优先级帧；重建序列后自回归回答。
- **数据结构：** 策略概率, 逐帧相关性分数, 动态视觉预算B_img, 高/低保真帧集合, 压缩后的可变长视觉序列
- **技术效果：** 在相当或更低预算下提高长视频基准准确率，视觉token最多减少67.9%。
- **局限：** 主要在InternVL3-8B上评估且离线访问采样帧；监督标签由VLM/LLM辅助构建，可能把基础模型偏差固化到证据保留策略。
- **反向证据：** 否

## PAPER-VERIFIED-136 VideoTIR: Accurate Understanding for Long Videos with Efficient Tool-Integrated Reasoning

- **标识：** arXiv:2603.25021
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-26
- **正文入口：** https://arxiv.org/abs/2603.25021
- **层级：** A / R1
- **机制簇：** ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M08
- **正文位置：** §3.1 Overview, §3.2 Multi-Modal Hierarchical Retrieval Toolkits, §3.3 RL Algorithm Design, §3.4 Trajectory Synthesis, §5 Conclusion
- **技术问题：** 长视频中文本token与视觉token失衡易引发幻觉，SFT工具调用又需要大量精细轨迹且调用路径僵化。
- **核心机制：** 文本路由器在直接回答、全局浏览和时间-空间grounding之间决策；后者串联segment、frame和zoom-in检索；TAGPO对每次工具调用分配局部优势，惩罚成功轨迹中的冗余调用。
- **控制流：** 先用低分辨率视频建立初始上下文；路由器判断信息是否足够；不足时调用浏览或层级grounding工具并把新证据回注；循环到回答或最大轮次；训练时用准确、格式和工具奖励及TAGPO更新策略。
- **数据结构：** 多轮上下文, segment/frame/region层级工具, 工具调用轨迹, 逐调用奖励与优势, 沙箱合成轨迹
- **技术效果：** 让7B模型学习更有效的多级工具使用，在三个长视频QA基准上兼顾准确率和调用效率。
- **局限：** 无独立Limitations章节；充分性仍由文本路由器自判；依赖合成轨迹、工具检索质量和最大轮次，未给出独立校准或失败回退。
- **反向证据：** 否

## PAPER-VERIFIED-137 Visual Agentic Memory: Enabling Online Long Video Understanding via Online Indexing, Hierarchical Memory, and Agentic Retrieval

- **标识：** arXiv:2605.16481
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-15
- **正文入口：** https://arxiv.org/abs/2605.16481
- **层级：** A / R1
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07
- **正文位置：** §3.2 Online Indexing, §3.3 Hierarchical Memory, §3.4 Agentic Retrieval, §3.5 Asynchronous Orchestration, Appendix A Limitations
- **技术问题：** 在线长视频需要在流式约束下决定保留哪些视觉证据，并让月级历史中的原始观察仍可搜索、检查和引用。
- **核心机制：** 在线索引用清晰度、冗余和自适应Otsu变化阈值提交moment/event；按年龄组织recent/mid/long层级记忆并并行保存时间摘要与空间原帧；查询代理执行search、inspect、summarize、answer四类有界动作。
- **控制流：** 后台持续过滤、嵌入并提交moment和event；查询时解析意图，在时间摘要和帧嵌入两路检索候选；直接检查原始帧解决冲突；证据充分、进展停滞或达到轮次预算时携带best_ref终止。
- **数据结构：** moment帧条目, event及摘要, recent/mid/long年龄层, 帧嵌入, 时间-空间共享锚点, best_ref证据指针, 多轮检索轨迹
- **技术效果：** 在保留可恢复原帧的同时把月级流压缩为可查询层级记忆，并在OVO-Bench和MM-Lifelong上提升长程检索表现。
- **局限：** 视觉强而音频弱；索引遗漏的边界或细微状态不可恢复；月到年级搜索空间继续增长；连续索引、存储和多轮视觉检查带来显著延迟与成本。
- **反向证据：** 否

## PAPER-VERIFIED-100 Reinforce to Learn, Elect to Reason: A Dual Paradigm for Video Reasoning

- **标识：** arXiv:2604.04379
- **正式年份：** CVPR 2026
- **最早公开：** 2026-04-06
- **正文入口：** https://arxiv.org/abs/2604.04379
- **层级：** D / R1
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, evidence_weighted_candidate_election
- **对应本地机制：** M06
- **正文位置：** §1, §4.1, §4.2
- **技术问题：** 单次视频推理候选可能缺乏证据一致性，且固定采样不足以处理低裕量答案。
- **核心机制：** GRPO塑造关键帧证据输出；多候选按证据一致性、置信、透明度和非冗余性加权选举，低裕量增样并做反驳检查。
- **控制流：** GRPO训练关键帧证据输出；按一致性、置信、透明度和非冗余性加权选举；低裕量时增样并执行反驳检查。
- **数据结构：** 候选答案集, 关键帧证据, 加权选举分数, 裕量
- **技术效果：** 用证据加权候选选举和低裕量复核提高视频推理稳定性。
- **局限：** 需要多候选成本；证据来自模型自报和自检；无跨分布校准或有限样本风险保证。
- **反向证据：** 是

## PAPER-VERIFIED-114 SIEVES: Selective Prediction Generalizes through Visual Evidence Scoring

- **标识：** arXiv:2604.25855
- **正式年份：** arXiv 2026
- **最早公开：** 2026-04-28
- **正文入口：** https://arxiv.org/abs/2604.25855
- **层级：** D / R1
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, visual_evidence_selective_prediction
- **对应本地机制：** M06
- **正文位置：** §3.1, §3.2, Appendix A
- **技术问题：** VQA系统需要依据视觉证据质量选择回答或拒答，而非只看语言置信度。
- **核心机制：** selector联合评分回答正确性、定位质量和证据-答案一致性，并按risk-coverage执行回答或拒答。
- **控制流：** selector联合评分答案正确性、定位质量和证据-答案一致性；按risk-coverage阈值回答或拒答。
- **数据结构：** 视觉证据分数, 定位质量, 一致性分数, risk-coverage曲线
- **技术效果：** 让选择性预测利用显式视觉证据质量。
- **局限：** 单图VQA；依赖显式zoom轨迹和有标签selector；整题而非原子声明；经验风险曲线无有限样本保证。
- **反向证据：** 是

## PAPER-VERIFIED-143 When Model Priors Conflict with Visual Evidence: Mitigating Commonsense-Driven Hallucinations by Selective Prior Calibration

- **标识：** arXiv:2607.29240
- **正式年份：** arXiv 2026
- **最早公开：** 2026-07-31
- **正文入口：** https://arxiv.org/abs/2607.29240
- **层级：** D / R1
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, selective_prior_calibration
- **对应本地机制：** M06
- **正文位置：** §3, Candidate-Level Score Correction, Learning the Correction Strength, Selective Answer Revision
- **技术问题：** 模型常识先验与图像证据冲突时会压制正确视觉候选。
- **核心机制：** 带图/无图双评分估计先验冲突，实例特征预测校正强度，仅在替代候选满足支持条件时改答。
- **控制流：** 比较带图和无图评分估计先验冲突；预测实例校正强度；仅当替代候选满足支持条件时改答。
- **数据结构：** 候选级视觉/先验分数, 冲突特征, 校正强度, 替换条件
- **技术效果：** 选择性抑制与视觉证据冲突的模型先验。
- **局限：** 多选/二元；需logit和成对CF/CS开发集；无图分数只是先验代理；单图且无补证。
- **反向证据：** 是

## PAPER-VERIFIED-093 Query-Guided Spatial-Temporal-Frequency Interaction for Music Audio-Visual Question Answering

- **标识：** arXiv:2601.19821
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-01-27
- **正文入口：** https://arxiv.org/abs/2601.19821
- **层级：** A / R2
- **机制簇：** AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M06, M05, M08
- **正文位置：** §3.1 Input Representation, §3.2 Query-Guided Multimodal Correlation, §3.3 Spatial-Temporal-Frequency Interaction, §3.4 Query Context Reasoning, §4.4 Ablation Studies
- **技术问题：** 现有音乐AVQA偏重视觉，音频仅作补充，问题语义介入过晚，难以联合定位发声区域、时间关系和频域线索。
- **核心机制：** QGMC先用问题词特征捕获并回传到音视频流；STFI把patch空间、跨时音视频和AST频域特征交互；QCR用问题上下文提示进一步融合后分类。
- **控制流：** 分段并提取视觉、音频和文本表示；问题跨注意捕获两模态语义并反向传播指导；执行空间-时间和时间-频率交互；提示式QCR聚合后预测答案。
- **数据结构：** 帧级/patch级视觉张量, 音频时序与频域特征, 词级问题特征, 问题引导音视频表示, STI/TFI交互表示
- **技术效果：** 在多个音乐AVQA基准上提高问题相关音视频对齐、发声区域定位和复杂推理准确率。
- **局限：** 无独立Limitations章节；依赖固定一秒分段和预训练CLIP/VGGish/AST；集中验证音乐AVQA分类数据，未评估长广告视频、开放式生成或主动补证。
- **反向证据：** 否

## PAPER-VERIFIED-095 Reading or Guessing? Visual Grounding Failures of Vision-Language Models for OCR in Ancient Greek Editions

- **标识：** arXiv:2605.27750
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-26
- **正文入口：** https://arxiv.org/abs/2605.27750
- **层级：** B / R2
- **机制簇：** TRANSIENT_TEXT_OCR
- **对应本地机制：** M01, M09, M05, M08
- **正文位置：** §3 RQ1 Error Taxonomy, §4 RQ2 Language Priors, §5 RQ3 Inference-Time Interventions, §6 Conclusion, Limitations, Appendix C Token-Level Image Gain
- **技术问题：** VLM OCR会输出流畅但视觉无支撑的文本，传统准确率指标难以区分语言先验修复与真实图像读取。
- **核心机制：** 用错误类型、受控反事实字符扰动和token级image-gain比较VLM与传统OCR；再测试脚本限制、长度拒答、对比解码和后OCR语言修正是否恢复视觉grounding。
- **控制流：** 对真实扫描做OCR并分类错误；修改页面字符后重新渲染，比较输出对扰动真值的忠实度；计算条件分布与无图分布的token image gain；施加多种解码干预并复测。
- **数据结构：** 扫描/扰动页面对, 八类OCR错误, token级image-gain, 条件/无图解码分布, 干预结果表
- **技术效果：** 证明流畅输出不等于视觉落地，且先验依赖具有模型差异；多数推理期干预不能普遍恢复grounding。
- **局限：** 仅研究Ancient Greek prose；扰动页为渲染而非真实扫描；错误分类依赖固定规则；后处理只测一个文本修正器；无法排除预训练接触。
- **反向证据：** 是

## PAPER-VERIFIED-112 Semantic Event Graphs for Long-Form Video Question Answering

- **标识：** arXiv:2601.06097
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-01-02
- **正文入口：** https://arxiv.org/abs/2601.06097
- **层级：** A / R2
- **机制簇：** EVENT_CAUSAL_REASONING, LONG_VIDEO_MEMORY_RETRIEVAL, ROLE_ACTION_CAUSAL_REASONING
- **对应本地机制：** M03, M05, M07, M10
- **正文位置：** §2.1–§2.4 Methods, §4.1–§4.5 Results, §5.2 Failure Modes and §5.3 Limitations
- **技术问题：** 长视频原始帧或完整事件日志既消耗大量token又掩盖稀疏的人-物交互，难以支持长时序问答。
- **核心机制：** 先以YOLOv11跟踪持久对象ID，再用人-物质心距离和迟滞规则产生START/END交互事件；把事件写入带时间戳的有向多重Temporal Scene Graph，按问题中的实体ID或类别锚点裁剪一跳子图后转成事件叙事供LLM回答。
- **控制流：** 检测并跨帧保持对象身份；邻近触发START、分离或消失触发END；构建时间场景图；从查询抽取词法锚点并选择相关一跳事件，必要时回退相似度筛选；去重、按时间排序并交给回答模型。
- **数据结构：** 持久对象ID与边界框, START/END人-物事件, NetworkX MultiDiGraph, 查询锚点, 一跳事件子图
- **技术效果：** 在5个长视频、120题的概念验证中把平均token从40.39k降至3.47k，压缩91.4%，准确率由Full Log的62.5%提高到65.0%。
- **局限：** 词法锚点对同义词、复数、代词和改写脆弱；离屏动作不会形成事件，多对象共指难恢复，纯符号事件不能回答颜色、身份和姿态；仅5个视频和120题，问答生成及同族Gemini自动评测可能有偏差，尚非完整基准。
- **反向证据：** 否

## PAPER-VERIFIED-119 SVAgent: Storyline-Guided Long Video Understanding via Cross-Modal Multi-Agent Collaboration

- **标识：** arXiv:2604.05079
- **正式年份：** CVPR 2026
- **最早公开：** 2026-04-06
- **正文入口：** https://arxiv.org/abs/2604.05079
- **层级：** A / R2
- **机制簇：** AGENT_TOOL_ROUTING, ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M06, M07, M08
- **正文位置：** §3 Method and Algorithm 1, §3.1 Storyline Generation, §3.2 Hypothesis Formation and DPPs, §3.3–3.4 Verification and Suggestion Agent, §4.1–4.6 Experiments and Analysis, §5 Conclusion
- **技术问题：** 长视频中的关键证据跨远距离分布，单次局部检索会破坏全局叙事连续性，且缺少对假设与跨模态证据一致性的显式复核。
- **核心机制：** SVAgent维护随新观察更新的查询条件故事线；Hypothesis Agent提出答案及支持/反驳证据，查询条件和证据条件两个DPP分别选帧并用交集比例做粗验证；文本与视觉决策代理独立判断，Meta Agent消解冲突，证据不足时Suggestion Agent按未探索区域和预期信息增益补帧。
- **控制流：** 从10%均匀帧构建初始故事线；生成假设并执行双DPP检索；交集比例不足则建议新帧、更新历史和故事线后重试；比例达阈值或到最终轮次时执行文本/视觉双路判断；两路一致或耗尽轮次后由Meta Agent输出。
- **数据结构：** 查询条件故事线, 答案假设与证据集, 查询/证据双DPP核及帧集合, 交集一致率, 历史错误与已访问帧索引, 文本/视觉判断及理由
- **技术效果：** 将时间叙事、假设检验、跨模态复核和定向补看组成闭环，在四个长视频基准及多种骨干规模上报告一致提升。
- **局限：** 初始数据库固定1 FPS且仅取10%帧，短时线索可能在进入闭环前丢失；交集阈值0.3和最多3轮为固定配置；代理由同类VLM提示驱动，DPP相似度与自验证错误可能相关；提高阈值或轮数会明显增加延迟，轮次耗尽仍强制进入最终决策。
- **反向证据：** 否

## PAPER-VERIFIED-126 TLG: Temporal-Logic Grounding for Video Question Answering via Source-Annotation Reconstruction and Category-Targeted Reasoning

- **标识：** arXiv:2606.01591
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-01
- **正文入口：** https://arxiv.org/abs/2606.01591
- **层级：** A / R2
- **机制簇：** EVENT_CAUSAL_REASONING
- **对应本地机制：** M07, M10, M05, M08
- **正文位置：** §3.1 Overview, §3.2 Timeline Reconstruction, §3.3 Parsing and Execution, §3.4 Fuzzy Action Grounding, §5 Discussion and Limitations, §6 Conclusion
- **技术问题：** VideoQA模型把视频当帧袋，无法可靠定位动作时间；TimeLogic问题实际上可由源数据集时间标注确定性求解。
- **核心机制：** TLG从源数据标注重建动作区间时间线，把问题解析为时间逻辑程序并做区间运算；无匹配标注时拒绝到符号层，按问题类别回退开放VLM或前沿推理模型。
- **控制流：** 按视频ID映射源标注并合并动作/状态；模糊匹配问题动作到时间线；执行before、overlap、always-before等算子；符号层无覆盖则路由到Tier 2，弱多选类别路由Tier 3。
- **数据结构：** 动作时间线T_v={(a_i,s_i,e_i)}, 时间逻辑程序, 动作词汇映射, 符号层覆盖/拒绝状态, 类别路由表
- **技术效果：** 用真实时间标注把基线46.9%提高到71.37%，并证明模型重建时间线不如原始标注，时间grounding是主要瓶颈。
- **局限：** 依赖挑战源数据公开标注，约220个STAR/AGQA问题缺少可用动作标签；方法绕过真实视频感知，不能直接迁移到无标注部署。
- **反向证据：** 否

## PAPER-VERIFIED-001 A Cost-Aware, Paired Protocol for Auditing Dynamic Tool Synthesis in Agentic Video Question Answering

- **标识：** arXiv:2607.01469
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-07-01
- **正文入口：** https://arxiv.org/abs/2607.01469
- **层级：** A / R2
- **机制簇：** AGENT_TOOL_ROUTING
- **对应本地机制：** M04, M06, M08
- **正文位置：** §3.2–§3.6 Methods, §5.1–§5.3 Results and Paired Decomposition, §5.4–§5.5 Failures and §6 Conclusion
- **技术问题：** 视频问答代理反复用原子工具重建常见流程，而仅看最终准确率无法判断复合工具究竟节省、转移还是增加了推理成本。
- **核心机制：** Dynamic-SAGE由Signature、Implementation和Verification agents离线发现常见轨迹、合成只调用既有原语的复合工具，并经静态检查、stub dry-run、重试、去包装和指纹去重后持久注册；配对审计协议按正确性变化和可见工具调用变化把同题结果分为六类并联合报告成本。
- **控制流：** 离线提出复合工具签名、生成函数体并最多修复三次；验证通过后注册到扩展动作空间；在线orchestrator在原子或复合工具间选择并回答；同一问题上与Static-SAGE配对，计算正确性、调用、原语操作、时延、token和费用差异及显著性。
- **数据结构：** 静态/动态工具注册表, 复合工具原语序列与深度, 验证错误和指纹, 六类配对结果, 逐题正确性-成本向量
- **技术效果：** 在1,304题SAGE-Bench上准确率由60.43%升至67.94%，推理轮次和可见调用约降28%；同时揭示原语操作增31%、token增34%、费用增26%，说明成本被转移而非全面降低。
- **局限：** 动态系统仍有90个相对静态系统的正确性回退，主要集中于困难、开放式问题；深层复合工具采用率低且准确率较差；17%候选因源视频不可用被删除，主实验依赖GPT-4o orchestrator，原RL策略对新工具采用率为0%，仍需跨基准和跨orchestrator验证。
- **反向证据：** 是

## PAPER-VERIFIED-018 CREST: Curvature-Regulated Event-Centric Sampling for Efficient Long-Video Understanding

- **标识：** arXiv:2605.09223
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-09
- **正文入口：** https://arxiv.org/abs/2605.09223
- **层级：** A / R2
- **机制簇：** EVENT_CAUSAL_REASONING
- **对应本地机制：** M07, M10, M04
- **正文位置：** §2.1 Preliminaries, §2.2 Temporal Geometry, §2.3 CREST, §3.2 Ablation and Robustness, Limitations
- **技术问题：** 固定帧预算下，单看查询-帧相关性幅值无法区分短暂尖峰事件与缓慢平台，Top-K容易选出相邻冗余帧。
- **核心机制：** 对相关性序列计算二阶差分曲率；贪心选择最高分帧后，以曲率调节抑制半径，尖峰用窄半径保留邻近决定性证据，平坦区用宽半径去冗余，并让旧抑制随迭代衰减。
- **控制流：** 归一化相关性并计算局部曲率；循环选择当前最高分帧；按R_base/(1+kappa)抑制邻域；随步数指数缩小旧抑制半径并恢复候选；选满M帧后送入下游MLLM。
- **数据结构：** 查询-帧相关性时间序列, 局部曲率kappa_t, 动态抑制半径, 已选帧索引集合
- **技术效果：** 以训练免费、低预处理成本的方式兼顾短暂事件与缓变证据，优于轻量基线并接近多阶段检索管线。
- **局限：** 与强基线使用不同帧预算，效果与预算差异未完全解耦；衰减参数固定且跨域敏感性未知；必须在选择时已知查询，不适用于离线无查询摘要。
- **反向证据：** 否

## PAPER-VERIFIED-024 Dual-Signal Adaptive KV-Cache Optimization for Long-Form Video Understanding in Vision-Language Models

- **标识：** arXiv:2602.14236
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-02-15
- **正文入口：** https://arxiv.org/abs/2602.14236
- **层级：** C / R2
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §III-A Temporal Filtering, §III-B Saliency-Guided Quantization, §III-C Just-In-Time Dequantization, §V-D Limitations, §VI Conclusion
- **技术问题：** 视频序列使KV-cache线性增长，先算完整注意力再淘汰token的反应式方法浪费计算。
- **核心机制：** Sali-Cache在注意力前用时间冗余信号复用前帧cache，再用空间显著性把patch分为保留、INT8、INT4或剪枝级别；计算时按需解量化。
- **控制流：** 比较相邻帧patch并计算冗余比例；高冗余帧直接指向前帧cache；非冗余帧按显著性分级存储；注意力使用前即时解量化相应K/V。
- **数据结构：** 逐帧冗余分数, 前帧cache指针, patch显著性等级, 混合精度KV-cache, 量化元数据
- **技术效果：** 在LLaVA 1.6实验中实现2.20倍有效内存压缩并保持所测指标，同时延长可保留上下文。
- **局限：** 主动过滤增加23.6%延迟；显著性模型为经典CV方法；阈值固定且跨域需调；仅在LLaVA 1.6验证，混合精度内核仍需优化。
- **反向证据：** 否

## PAPER-VERIFIED-026 EG-VQA: Benchmarking Verifiable Video Question Answering with Grounded Temporal Evidence

- **标识：** arXiv:2606.24797
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-23
- **正文入口：** https://arxiv.org/abs/2606.24797
- **层级：** A / R2
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, EVENT_CAUSAL_REASONING
- **对应本地机制：** M06, M07, M10
- **正文位置：** §4.1–§4.4 EG-Reasoner, §5.1–§5.4 Experiments and Ablation, §5.3 Analysis and Discussion; §5.5 failure cases
- **技术问题：** 视频问答的答案正确率无法判断模型是否定位到真正支持答案的时间证据，时间重叠和语义一致也缺少联合评价。
- **核心机制：** EG-VQA为答案配置多段时间-语义证据；EG-F1对预测与真值证据同时计算时间IoU和语义相似度并做匈牙利一对一匹配；EG-Reasoner联合生成证据、推理轨迹和答案，以格式、答案和软硬EG-F1组合奖励进行GRPO训练。
- **控制流：** 策略对同一视频问题采样多条结构化候选；分别计算格式、答案和证据奖励；组内归一得到相对优势并更新策略；推理时一次输出证据段、证据链和最终答案。
- **数据结构：** 时间段-文字描述证据对, 预测/真值二部匹配图, evidence-think-answer结构化响应, 组合奖励与组内优势
- **技术效果：** EG-Reasoner达到26.88%严格准确率、42.71%宽松准确率和27.27 F1@0.5，并揭示高答案准确率不等于正确证据定位。
- **局限：** 精确时间边界仍是瓶颈，所有模型随IoU阈值提高明显退化；总体推理和语义理解仍低于人工；数据由GPT-4o生成后经双模型和人工抽检，答案正确性也采用LLM评价，仍受自动生成与评测偏差影响。
- **反向证据：** 是

## PAPER-VERIFIED-049 GroundingME: Exposing the Visual Grounding Gap in MLLMs through Multi-Dimensional Evaluation

- **标识：** arXiv:2512.17495
- **正式年份：** CVPR 2026
- **最早公开：** 2025-12-19
- **正文入口：** https://openaccess.thecvf.com/content/CVPR2026/html/Li_GroundingME_Exposing_the_Visual_Grounding_Gap_in_MLLMs_through_Multi-Dimensional_CVPR_2026_paper.html
- **层级：** B / R2
- **机制簇：** DETAIL_INFORMATION_GATING, EVIDENCE_SUFFICIENCY_VERIFICATION, FINE_GRAINED_REGION_GROUNDING
- **对应本地机制：** M05, M06, M08
- **正文位置：** §3 GroundingME, §5 Analysis, §6 Conclusion
- **技术问题：** 现有MLLM grounding评测无法同时覆盖辨别、空间、受限输出和拒绝能力。
- **核心机制：** 以Discriminative、Spatial、Limited和Rejection四维评测复杂grounding；测试Best-of-16思考选择和负样本混合训练。
- **控制流：** 无单一部署控制流；按四维任务评测，并比较Best-of-16选择与正负样本混合训练。
- **数据结构：** 边界框, 正负grounding样本, 四维评测指标
- **技术效果：** 系统暴露复杂grounding和拒绝之间的能力缺口及训练权衡。
- **局限：** 静态图像框任务；Best-of-16成本高；拒绝SFT使更难域外正grounding退化。
- **反向证据：** 否

## PAPER-VERIFIED-060 Incentivizing Vision Language Models to Search for Long Video Question Answering

- **标识：** arXiv:2607.02959
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-07-03
- **正文入口：** https://arxiv.org/abs/2607.02959
- **层级：** C / R2
- **机制簇：** ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §4.1 Interactive Video-Evidence Seeking Trajectory, §4.2 Agentic Tool Infrastructure, §4.3 VETL, §5.3 Verified-Signal Reward, §6 Limitations
- **技术问题：** 长视频RL搜索缺少可验证的中间奖励，仅用最终答案正确性难以学习针对性查询和真实视觉证据获取。
- **核心机制：** VSeek让单个VLM交替推理与自然语言搜索；VETL把问题和答案编译成含原子视觉谓词及时间关系的形式规范，用检索到的视觉原语满足度提供稠密可验证奖励。
- **控制流：** 预处理视频为ViCLIP视觉索引和字幕索引；代理每轮生成search、search_subtitle或summary动作并接收最多16帧；上下文累积至最终回答；训练时生成并审查时间逻辑规范，按原子证据检索和终答共同奖励。
- **数据结构：** 8秒clip向量索引, 字幕-时间窗索引, 多轮轨迹tau, 时间逻辑规范phi, 原子视觉谓词集合P, 逐步证据奖励
- **技术效果：** 把被动VideoQA变为多轮证据搜索，并通过形式化中间奖励提升Pass@1和Pass@4。
- **局限：** 搜索顺序为串行且可能乱序处理时间线；形式逻辑表达能力有限；效果受检索器和索引瓶颈约束。
- **反向证据：** 否

## PAPER-VERIFIED-077 MemoryCard: Topic-Aware Multi-Modal Clue Compression for Long-Video Question Answering

- **标识：** arXiv:2606.05917
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-04
- **正文入口：** https://arxiv.org/abs/2606.05917
- **层级：** A / R2
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07, M04
- **正文位置：** §3.1 Long-Form Video QA, §3.2 Event-Level Multimodal Evidence Construction, §5.4 Card Selection and Allocation, §6 Conclusion, Limitations
- **技术问题：** 独立帧作为检索单元缺少事件边界、语音上下文和时间连续性，难以支撑跨事件长程推理。
- **核心机制：** 自读VLM按事件、主题或场景把视频分成semantic sessions；每个session生成视频gist并选代表帧，渲染为统一Memory Card；查询时检索Top-K卡片供VLM回答。
- **控制流：** 离线分割semantic sessions；对每段联合视觉和转写生成gist与代表帧索引；把文本gist和视觉帧渲染成卡片库；查询-卡片相似度检索Top-K；按时间组织后回答。
- **数据结构：** semantic session边界, event-level gist, 代表帧集合, 图像化Memory Card, Memory Card库
- **技术效果：** 把稀疏帧转为高密度事件级多模态证据，在相似视觉预算下提升多个VLM的长视频QA准确率。
- **局限：** 卡片构建有额外预处理成本；依赖自读VLM分段、摘要和选帧；unit-level gist与代表帧不适合细粒度运动或连续动作问题。
- **反向证据：** 否

## PAPER-VERIFIED-080 MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering

- **标识：** arXiv:2605.22269
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-21
- **正文入口：** https://arxiv.org/abs/2605.22269
- **层级：** A / R2
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL, VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M03, M04, M08
- **正文位置：** §3.1–§3.5 Method, §4.1–§4.3 Experiments and Ablation, §4.2 counting failure; §7.2 hyperparameter boundaries
- **技术问题：** 流式视频QA逐帧保存KV既冗余又缺少跨帧语义，纯层级检索还会因顶层误检向下传播错误。
- **核心机制：** MuKV按patch、frame和segment三种粒度构建历史视频KV；用self-attention重要性与FFT频率双信号按粒度剪枝；查询时先跨粒度并行召回，再以高层segment全局查询对低粒度候选做一致性重排。
- **控制流：** 视频到达时按段prefill并生成三粒度KV；双信号评分后按粒度压缩入库；问题到达时从各粒度并行取Top-2k；用高层segment聚合查询重排patch/frame候选；选择Top-k KV并与问题token共同解码答案。
- **数据结构：** patch/frame/segment三级KV缓存, attention与FFT重要性分数, 粒度自适应保留率, 跨粒度召回候选, 全局一致性重排分数
- **技术效果：** 在不增加既定缓存和在线QA开销的设置下相对ReKV提升多个流式基准准确率；67%压缩配置在RVSEgo和RVSMovie分别提升5.8和3.3个百分点，并降低真实缓存与时延。
- **局限：** 无独立Limitations章节；压缩更偏向段级全局语义，在StreamingBench Counting问题上表现较弱；0.5 FPS、压缩率和跨粒度权重由RVSEgo贪心调参，最优值随数据集变化；部分开放式结果依赖已变更版本的GPT-3.5自动评测，半层级重排也会略降效率。
- **反向证据：** 否

## PAPER-VERIFIED-082 Narrative Aligned Long Form Video Question Answering

- **标识：** arXiv:2603.19481
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-19
- **正文入口：** https://arxiv.org/abs/2603.19481
- **层级：** A / R2
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL, EVENT_CAUSAL_REASONING
- **对应本地机制：** M03, M07, M10
- **正文位置：** §4.1–§4.3 Video-NaRA, §5.1–§6.1 Experiments and Ablation, §5.1 evaluation scope; §6.2–§6.3 failure boundaries
- **技术问题：** 全长电影问答需要把相距很远的角色、目标和因果事件连接为叙事链，均匀帧序列和孤立片段检索难以完成该任务。
- **核心机制：** Video-NaRA用MLLM按人物、目标、上下文及时间连贯性把片段归入叙事memory slots；查询先与片段帧特征计算相关性，再把slot内均值与最大值组合成叙事重要度并回灌片段分数，选Top-20片段供微调reasoner回答。
- **控制流：** 离线为片段生成描述并顺序构建叙事槽；查询到达后计算逐片段CLIP相关性；聚合为slot级叙事分数并校正片段排名；选取Top-20片段、均匀压到128帧；reasoner基于叙事证据生成答案。
- **数据结构：** 短/中/远证据跨度标签, 叙事memory slots, 片段描述与帧级embedding, 片段相关性和slot重要度, Top-20证据片段
- **技术效果：** 在88部电影、4.4K开放式问题的NA-VQA上，Video-NaRA相对基线提高长程叙事推理约3个百分点；去除叙事记忆使Far证据分数由35.20降至32.70。
- **局限：** 无独立Limitations章节；片段描述、事件和问答大量依赖Claude/Qwen生成，开放式评价使用Claude Sonnet 4 judge；数据仅88部电影，1 FPS、32秒切片、Top-20和128帧上限可能丢失细节；模型对短距离证据也难定位，因果、多步和反事实仍是最难类别。
- **反向证据：** 是

## PAPER-VERIFIED-083 NEST: Narrative Event Structures in Time for Long Video Understanding

- **标识：** arXiv:2606.19706
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-06-18
- **正文入口：** https://arxiv.org/abs/2606.19706
- **层级：** A / R2
- **机制簇：** EVENT_CAUSAL_REASONING
- **对应本地机制：** M03, M07, M10
- **正文位置：** §3 NEST, §3.2 Event Annotation Pipeline, §4 Experiments, §5 Results and Analysis, §7 Limitations, Appendix A.2/A.4/A.7
- **技术问题：** 现有长视频基准偏向针式检索，不能诊断模型能否从低层动作发现叙事事件、落地参与者，并理解跨长时间间隔和闪回的事件关系。
- **核心机制：** NEST以PropBank谓词抽取事件trigger和argument，标注时间、因果、层级、前置与共指关系，并把事件保守落地到场景边界；通过LLM辅助SILVER集和人工GOLD集构造ETD、EL、EAE和ERE四类任务，分离原始视频中的事件发现与给定事件后的关系推理。
- **控制流：** 收集并切分全长电影；从音频描述和文本抽取trigger、argument及关系；用时序grounding模型定位，失败时回退到包含事件的场景边界；双源验证SILVER并人工标注GOLD；分别评测事件发现、定位、论元和关系分类。
- **数据结构：** 带时间边界的叙事事件, PropBank语义角色, 多类型事件关系图, SILVER/GOLD标注集, 场景级grounding与闪回子集
- **技术效果：** 构建小时级结构化叙事基准，并证明当前模型的主要瓶颈是事件发现和落地而非给定事件后的封闭集关系分类；增加帧数也未解决该缺口。
- **局限：** LLM验证会继承模型偏差；时序grounding较弱，场景级边界不能刻画精细时间；逐场景标注遗漏必须跨多个非相邻场景联合判断的复合事件；版权限制原始视频发布，ETD/EAE的LLM judge也会引入偏差。
- **反向证据：** 是

## PAPER-VERIFIED-096 Reasoning for Social Audio-Visual Question Answering: Where Do We Stand?

- **标识：** arXiv:2608.13239
- **正式年份：** HCMIW @ ECCV 2026
- **最早公开：** 2026-08-13
- **正文入口：** https://arxiv.org/abs/2608.13239
- **层级：** A / R2
- **机制簇：** AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M06, M10
- **正文位置：** Abstract, §3 IntentBench-Prime, §4 Ineffectiveness of Reasoning for Social AV-QA, §5 Limited Gap Between Video and Caption-Based Answering, §6 Conclusion, Limitations
- **技术问题：** 社会音视频QA中的推理增益可能被基准噪声、文本先验和昂贵CoT开销夸大。
- **核心机制：** 清洗IntentBench得到IntentBench-Prime；用不生成推理轨迹的Vanilla SFT与CoT/GRPO方法对照；再以Question SFT和Caption SFT隔离文本先验及音视频贡献。
- **控制流：** 无证据闭环；分别训练直接AV-QA、仅问题和仅caption三种SFT基线，在多基准上比较准确率、训练成本和解码延迟。
- **数据结构：** IntentBench-Prime过滤集, 音视频QA样本, 问题无关细粒度caption, 三种模态对照结果
- **技术效果：** 正文显示简单Vanilla SFT匹配或优于现有推理方法，caption-only与全音视频表现接近，构成对复杂推理和真实多模态利用的强反向证据。
- **局限：** 仅删除而未新增/改写问题，样本减少且类别仍不平衡；同源微调仍可利用先验；实验仅用Qwen2.5-Omni，caption/video对照仅覆盖社会领域。
- **反向证据：** 是

## PAPER-VERIFIED-115 Small Vision-Language Models are Smart Compressors for Long Video Understanding

- **标识：** arXiv:2604.08120
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-04-09
- **正文入口：** https://arxiv.org/abs/2604.08120
- **层级：** C / R2
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §3.1 Overall, §3.2 Query-Aware Visual Compression, §3.3 Zero-Shot Relevance Prior, §3.4 Adaptive Token Allocation, §4.3 Ablation Studies, §6 Discussion and Future Works
- **技术问题：** 小时级视频的密集视觉token耗尽上下文，稀疏采样或均匀池化会丢短暂证据并浪费预算于无关背景。
- **核心机制：** 小型VLM把每段视觉和问题压入固定容量memory tokens；同一前向用Yes/No logit差得到零样本相关性；ATA在全局预算下为每段分配k_min到k_max并直接截取语义前置的memory token。
- **控制流：** 逐段将视觉token、问题和可学习memory token输入SVLM；提取压缩表示和相关性分数；对分数归一化并先保每段最小时间锚点，再把剩余容量分给高相关段；拼接时间戳与压缩记忆供全局LLM回答。
- **数据结构：** 分段memory tokens, 时间戳锚点, 零样本相关性s_i, 逐段token预算k_i, 全局预算B_max
- **技术效果：** 在0.5到16 token/帧范围动态压缩，保持时间因果并在极长视频基准上获得较强准确率。
- **局限：** 相关性完全依赖SVLM零样本先验；固定memory token数量不能按证据充分性自适应停止；主要验证单一6B层级架构，多轮对话和自回归压缩未解决。
- **反向证据：** 否

## PAPER-VERIFIED-120 Symphony: A Cognitively-Inspired Multi-Agent System for Long-Video Understanding

- **标识：** arXiv:2603.17307
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-18
- **正文入口：** https://arxiv.org/abs/2603.17307
- **层级：** A / R2
- **机制簇：** AGENT_TOOL_ROUTING, SELF_CORRECTION_REFLECTION
- **对应本地机制：** M04, M06, M07
- **正文位置：** §3.1–§3.3 Method, §4.3–§4.4 Experiments and Ablation, §4.4.2 sampling/cost boundaries; Appendix C Cost
- **技术问题：** 单一长视频代理在复杂问题上容易超出推理容量，按模态孤立分工的多代理又缺少深层协作和可靠的复杂问题定位。
- **核心机制：** Symphony按认知能力而非模态解耦Planning、Grounding、Subtitle、Visual Perception和Reflection agents；Planner动态派发子任务，Grounding按问题复杂度选择CLIP检索或VLM片段评分，独立Reflector检查轨迹并在不可信时给出修正意见触发新一轮规划。
- **控制流：** Planner读取问题与历史轨迹并调用专用agent；观察写入轨迹；达到终止条件后由Reflector判断答案和过程是否可信；不可信则把修正意见加入状态并重新规划，可信或达到轮次上限时由Planner回答。
- **数据结构：** 动作-观察推理轨迹, 动态agent集合, VLM片段相关性评分, 反思有效性标记与修正意见, 字幕及视觉观察
- **技术效果：** 在四个长视频基准上取得正文所报SOTA结果，LVBench总体71.8%，较DVD高5个百分点；移除独立Reflection、Subtitle或Visual Perception agent均造成消融下降。
- **局限：** 无独立Limitations章节；系统依赖多种大模型、Whisper和外部LLM API，每题最多15轮调度且Reflector最多3轮；过低FPS会漏关键帧，过长片段会引入噪声；Appendix C报告平均每题约22万token和0.124美元，仍有显著成本。
- **反向证据：** 否

## PAPER-VERIFIED-128 Transcoders Trace Visual Grounding and Hallucinations in Vision-Language Models

- **标识：** arXiv:2605.22902
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-21
- **正文入口：** https://arxiv.org/abs/2605.22902
- **层级：** B / R2
- **机制簇：** HALLUCINATION_DETECTION
- **对应本地机制：** M06, M05, M08
- **正文位置：** Abstract, 2 Methodology, 3.3 Circuit tracing, 4 Counterfactual Analysis, 5 Structural Analysis of Hallucinations, 7 Discussion and Future Work, 8 Limitations and Scope
- **技术问题：** 静态稀疏自编码器只分解残差状态，难解释视觉输入如何经MLP功能更新影响文本生成及幻觉。
- **核心机制：** 用Transcoder稀疏近似各MLP子层，构建从图像patch到生成token的功能计算图；从图结构提取深度、跨度、熵和贡献集中度等特征预测幻觉。
- **控制流：** 训练Transcoder→归因视觉patch到生成token→patch消融验证→追踪跨层计算图→提取五类图指标→逻辑回归判别幻觉。
- **数据结构：** 稀疏Transcoder特征, 跨层归因图, 节点/边贡献, 路径深度与层跨度, 图级指标向量
- **技术效果：** 归因比SAE更稳定且更符合语义区域；仅用图结构特征的分类器达到AUC 0.68，高于0.55先验基线。
- **局限：** 仅Gemma 3-4B-IT、约500M token训练语料和较小样本；特征非单义；检测性能不与输出级方法竞争，尚未验证干预修复。
- **反向证据：** 否

## PAPER-VERIFIED-131 Video Active Perception: Effective Inference-Time Long-Form Video Understanding with Vision-Language Models

- **标识：** arXiv:2605.01662
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-03
- **正文入口：** https://arxiv.org/abs/2605.01662
- **层级：** C / R2
- **机制簇：** ACTIVE_EVIDENCE_SEEKING
- **对应本地机制：** M04, M08, M07
- **正文位置：** §3.1 A Priori Knowledge, §3.2 Data Acquisition, §3.3 VLM Inference, §4.5 Quantitative Analyses, §5 Conclusions
- **技术问题：** 均匀采样在长视频中既浪费帧又可能错过信息密集转折，增加帧数后性能还会平台化。
- **核心机制：** 用CogVideoX根据初始帧、问题和候选答案生成整段预期视频latent；同一VAE编码所有真实帧；选择与对应生成latent余弦最不相似的真实帧作为超出先验的“惊讶”证据。
- **控制流：** 均匀抽取初始帧；条件扩散和插值产生全时间轴预测latent；编码全部真实帧；逐时刻比较真实/预测latent；排序选最低相似的n帧；将选中帧和问题送旗舰VLM回答。
- **数据结构：** 生成视频latent序列, 真实视频latent序列, 逐帧相似度列表, Top-n惊讶帧索引, 长视频latent memory bank
- **技术效果：** 训练免费地提高关键帧有效性，在多个长视频/推理QA基准上用更少帧达到更高或相近准确率。
- **局限：** 无独立Limitations章节；仍需编码全部真实帧并运行扩散先验，计算不轻；实验多为多选QA且固定选帧数；生成先验或候选答案偏差可能影响选帧。
- **反向证据：** 否

## PAPER-VERIFIED-144 Where to Focus: Query-Modulated Multimodal Keyframe Selection for Long Video Understanding

- **标识：** arXiv:2604.17422
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-04-19
- **正文入口：** https://arxiv.org/abs/2604.17422
- **层级：** A / R2
- **机制簇：** FRAME_EVIDENCE_SELECTION, AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M04, M08
- **正文位置：** §3.1–§3.3 Methodology, §4.1–§5.2 Experiments and Ablation, §5.3–§5.8 robustness, sensitivity and latency boundaries
- **技术问题：** 视觉、全局语义和字幕线索对不同问题的重要性不同，静态融合会把无关模态噪声带入关键帧选择。
- **核心机制：** Q-Gate并行计算YOLO-World对象grounding、BLIP-2全局图文匹配和Sentence-BERT问题-字幕对齐三路分数，经统一归一化后由LLM根据问题意图生成三路权重，再按融合分数选取带时间戳的Top-K帧与字幕。
- **控制流：** 抽取对象、场景和字幕三路时间分数；Masked Temperature Softmax抑制缺失字幕及低分噪声；LLM门控器按问题分配权重；融合后选择Top-K时刻；把带时间戳帧和字幕交给下游VLM交叉核验并回答。
- **数据结构：** 三路时间对齐相关性分布, 问题条件门控权重, Masked Softmax分布, 带时间戳的帧-字幕证据集
- **技术效果：** 在LongVideoBench和Video-MME多数设置下优于单模态及静态融合基线，正文报告Video-MME Long上相对AKS最高提升6.40个百分点，路由额外时延约1.35%。
- **局限：** 无独立Limitations章节；依赖YOLO-World、BLIP-2、Sentence-BERT、对齐字幕和LLM门控器，任一上游误差都会影响选帧；门控模型在8帧预算下存在明显性能差异，softmax温度呈倒U敏感性，过低损失时间多样性、过高无法抑制模态噪声。
- **反向证据：** 否

## PAPER-VERIFIED-017 CounterVid: Counterfactual Video Generation for Mitigating Action and Temporal Hallucinations in Video-Language Models

- **标识：** arXiv:2601.04778
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-01-08
- **正文入口：** https://arxiv.org/abs/2601.04778
- **层级：** C / R2
- **机制簇：** HALLUCINATION_MITIGATION
- **对应本地机制：** M06, M10
- **正文位置：** Abstract, 3 Proposed Method, 3.2 Counterfactual Video Generation Pipeline, 3.3 Task and Preference Construction, 3.4 The MixDPO Alignment Framework, 5 Conclusion, Limitations
- **技术问题：** 随机扰动难产生场景相同但动作或顺序语义不同的硬负例，模型可继续依赖语言先验。
- **核心机制：** 从关键帧提出替代动作并编辑动作完成帧，再生成保持场景身份的反事实视频；MixDPO联合同视频的答案偏好与同文本的视觉偏好。
- **控制流：** 关键帧选择→MLLM提出替代动作→编辑关键帧→图生视频→构造动作/时序偏好对→MixDPO微调VLM。
- **数据结构：** 锚视频, 反事实视频集合, 动作轨迹标签, 文本偏好对, 视觉偏好对, CounterVid约2.6万对
- **技术效果：** 改善动作识别和时序排序并迁移到视频幻觉基准，同时基本保持通用视频理解性能。
- **局限：** 反事实质量依赖生成模型和过滤；当前动作短于2秒；冻结视觉编码器；约3000 GPU小时且存在合成误导内容的双用风险。
- **反向证据：** 否

## PAPER-VERIFIED-032 Entropy-Gradient Grounding: Training-Free Evidence Retrieval in Vision-Language Models

- **标识：** arXiv:2604.08456
- **正式年份：** arXiv 2026
- **最早公开：** 2026-04-09
- **正文入口：** https://arxiv.org/abs/2604.08456
- **层级：** B / R2
- **机制簇：** DETAIL_INFORMATION_GATING, FINE_GRAINED_REGION_GROUNDING
- **对应本地机制：** M05, M08
- **正文位置：** §3 Method, Table 7, Appendix I Limitations
- **技术问题：** 无需训练的VLM证据定位缺少可直接由生成不确定性驱动的区域选择机制。
- **核心机制：** 把下一token分布熵反传至视觉token，提取并排名多连通区域，迭代重定位并用空间熵上升停止。
- **控制流：** 将token分布熵反传至视觉token；提取并排名连通区域；迭代重定位；空间熵上升时停止。
- **数据结构：** 视觉token梯度, 熵图, 连通区域候选, 区域排名
- **技术效果：** 以模型自身熵梯度定位证据区域，但定位正确不等同于回答正确。
- **局限：** 迭代需重复前反向传播；定位正确不保证回答正确；基础模型不重视的区域无法由梯度恢复。
- **反向证据：** 否

## PAPER-VERIFIED-033 Event-Anchored Frame Selection for Effective Long-Video Understanding

- **标识：** arXiv:2603.00983
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-01
- **正文入口：** https://arxiv.org/abs/2603.00983
- **层级：** A / R2
- **机制簇：** FRAME_EVIDENCE_SELECTION, EVENT_CAUSAL_REASONING
- **对应本地机制：** M04, M07
- **正文位置：** §3.1–§3.3 Methodology, §4.1–§4.3 Experiments and Ablation, §6.1 Limitations
- **技术问题：** 把长视频视为无结构帧集合的平坦采样难以在有限预算下兼顾事件覆盖、问题相关性和视觉多样性。
- **核心机制：** EFS用DINOv2相邻帧相似度的局部极小值划分视觉事件，必要时合并到目标事件数；每个事件先选BLIP2-ITM最高分帧作为锚点，再用内容自适应MMR在全局补充兼顾相关性与多样性的帧。
- **控制流：** 提取DINOv2视觉特征与BLIP2-ITM问题相关性；划分并合并事件；逐事件建立相关锚点；以锚点初始化关键帧集并自适应放宽多样性阈值完成全局细化；送入LVLM回答。
- **数据结构：** 帧级DINOv2特征, 时间相似度曲线, 视觉事件段, 事件锚点集合, 自适应MMR候选集
- **技术效果：** 作为免训练模块跨三个LVLM和三个长视频基准提升准确率，紧帧预算下收益尤其明显；组件消融支持事件划分、相关锚点和自适应细化的独立贡献。
- **局限：** 需要离线运行DINOv2和BLIP2-ITM，长视频预处理开销不适合低延迟场景；事件数和阈值放宽因子依赖人工网格搜索，跨域迁移不确定；上游特征模型的偏差、域差和失效会传递到最终选帧。
- **反向证据：** 否

## PAPER-VERIFIED-046 Geometry-Guided 3D Visual Token Pruning for Video-Language Models

- **标识：** arXiv:2604.18260
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-04-20
- **正文入口：** https://arxiv.org/abs/2604.18260
- **层级：** C / R2
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08
- **正文位置：** §3.1 Preliminaries, §3.2 Intra-Voxel View Consistency Pruning, §3.3 Inter-Voxel Spatial Diversity Pruning, §4.4 Ablation Studies, §4.5 Efficiency Analysis
- **技术问题：** 3D空间视频含大量跨视角重复token，普通文本/视觉引导剪枝忽略同一3D位置的视图一致性和剩余场景覆盖。
- **核心机制：** 用几何模型恢复相机与深度并把token投到体素；体素内按局部跨视角注意保留代表token；体素间再选空间分布多样的体素以保持完整3D覆盖。
- **控制流：** 视觉与几何特征相加；逆投影token并体素化；从全局注意取体素子矩阵计算入边贡献，保留Top-alpha；再按体素空间多样性剪枝；剩余token送Video-3D LLM。
- **数据结构：** 几何增强视觉token, 相机内外参, 深度图, 体素到token映射, 体素局部注意子矩阵, 空间多样体素集合
- **技术效果：** 剪除90%视觉token时在多个3D理解基准保留超过90%的原始性能。
- **局限：** 正文无独立Limitations章节；需要额外3D几何编码、可靠深度和相机估计；面向空间视频/3D场景，未验证普通广告视频和快速动态对象。
- **反向证据：** 否

## PAPER-VERIFIED-057 HORNet: Task-Guided Frame Selection for Video Question Answering with Vision-Language Models

- **标识：** arXiv:2603.18850
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-19
- **正文入口：** https://arxiv.org/abs/2603.18850
- **层级：** A / R2
- **机制簇：** FRAME_EVIDENCE_SELECTION
- **对应本地机制：** M04, M08
- **正文位置：** §3 Method, §3.1 Select Any Frames Formulation, §3.3 HORNet Architecture, §3.4 Training with GRPO, §4.3–4.5 Results and Ablations, §5 Conclusion — Limitations
- **技术问题：** 均匀或启发式视频采样不能针对冻结VLM的最终问答质量优化，导致大量无关帧进入模型且关键事件可能未被选择。
- **核心机制：** HORNet用轻量TimeSFormer提取时空帧表示，以不足1M参数的逐帧MLP输出独立Bernoulli选择概率；训练时组合确定性Top-k sweep与随机mask生成候选子集，调用冻结VLM回答并按F1/编辑相似度或选择准确率给奖，再用GRPO组内相对优势更新选帧策略。
- **控制流：** 编码候选帧并输出逐帧概率；按预算形成二进制mask；选中帧送冻结VLM回答；训练阶段对8个候选mask计算问答奖励并做GRPO更新，推理阶段直接使用学习到的策略。
- **数据结构：** TimeSFormer逐帧表示, Bernoulli选择概率向量, 二进制帧mask, Top-k与随机候选组, 问答奖励及组内优势
- **技术效果：** 以极少可训练参数显著减少输入帧和VLM处理时间，并在部分短视频及时间推理设置中优于盲采样。
- **局限：** 固定8帧在小时级VideoMME上不足，正文准确率较完整输入下降16.2个百分点，多个长视频设置也存在质量损失；策略受文本QA奖励和训练分布约束，跨域测试仍退化；独立Bernoulli决策未显式建模预算自适应、连续区间或证据充分性。
- **反向证据：** 是

## PAPER-VERIFIED-066 Knowing When to Answer: Adaptive Confidence Refinement for Reliable Audio-Visual Question Answering

- **标识：** arXiv:2602.04924
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-02-04
- **正文入口：** https://arxiv.org/abs/2602.04924
- **层级：** A / R2
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M06
- **正文位置：** §3.4 Adaptive Confidence Refinement, §4.1–§4.4 Experiments, Appendix P Additional Discussion and Future Work
- **技术问题：** 音视频问答模型即使总体准确率较高，也会因多模态错位和置信度失准而在低风险要求下大量误答或过度拒答。
- **核心机制：** ACR保留最大softmax概率作为主置信信号，以Residual Risk Head从中间多模态特征预测正确性，再由Confidence Gating Head按输入生成融合权重，对MSP进行样本自适应残差校正。
- **控制流：** 先冻结已训练的AVQA回答器；在独立选择集上训练残差风险头和门控头；推理时融合MSP与残差正确性分数；按验证集确定的风险阈值选择回答或拒答。
- **数据结构：** MSP置信度, 残差正确性分数, 输入自适应门控权重, risk-coverage曲线, AURC与ECE
- **技术效果：** 在MUSIC-AVQA、MUSIC-AVQA-R和MUSIC-AVQA-v2.0的同分布、分布外及偏置设置中改善低风险覆盖、AURC和校准误差。
- **局限：** 当前实现仅适用于固定有限答案空间，不能直接处理开放式生成；需要独立选择集训练selector，且以经验排序收益换取了保形方法的分布无关保证；复杂声画歧义下仍存在高置信错误，跨群体拒答不均衡也未被消除。
- **反向证据：** 是

## PAPER-VERIFIED-068 LENS: Adaptive Spatio-Temporal Zooming for Keyframe Sampling in Long-Form Videos

- **标识：** arXiv:2607.25125
- **正式年份：** ECCV 2026
- **最早公开：** 2026-07-27
- **正文入口：** https://arxiv.org/abs/2607.25125
- **层级：** C / R2
- **机制簇：** DETAIL_INFORMATION_GATING, FRAME_EVIDENCE_SELECTION, adaptive_spatiotemporal_budget
- **对应本地机制：** M04, M08
- **正文位置：** §3.2, §3.3, §3.4, Appendix C
- **技术问题：** 固定帧预算下，长视频关键帧选择需要在空间细节和时间覆盖间自适应分配。
- **核心机制：** 按查询在空间zoom-in视觉提示与时间zoom-out图聚合之间动态分配固定帧预算。
- **控制流：** 控制器按查询在空间zoom-in视觉提示和时间zoom-out图聚合之间一次性分配预算并采样。
- **数据结构：** 时空采样预算, 视觉提示, 时间聚合图
- **技术效果：** 在固定预算下自适应平衡局部细节与长程覆盖。
- **局限：** 一次性采样而非验证后迭代；控制器无校准不确定性；无声明级证据保留保证。
- **反向证据：** 否

## PAPER-VERIFIED-069 LensWalk: Agentic Video Understanding by Planning How You See in Videos

- **标识：** arXiv:2603.24558
- **正式年份：** CVPR 2026
- **最早公开：** 2026-03-25
- **正文入口：** https://arxiv.org/abs/2603.24558
- **层级：** C / R2
- **机制簇：** EVENT_CAUSAL_REASONING, FRAME_EVIDENCE_SELECTION, reason_plan_observe_audit
- **对应本地机制：** M04, M07
- **正文位置：** §3.1, §3.2, §3.3, §3.4, Appendix A
- **技术问题：** 长视频代理缺少按问题动态选择全局扫描、局部聚焦和跨段核验的视觉计划。
- **核心机制：** Reasoner选择Scan Search、Segment Focus或Stitched Verify并参数化时间范围/密度，保存时间戳锚点和主体记忆表。
- **控制流：** Reasoner在Scan Search、Segment Focus和Stitched Verify间选择并设定范围/密度；观察结果写入记忆后继续或回答。
- **数据结构：** 时间戳锚点, 主体记忆表, 工具调用轨迹
- **技术效果：** 使观看策略随问题和当前证据动态变化，并保留可读轨迹。
- **局限：** 证据由VLM生成而非独立验证；多轮成本；时间戳轨迹不是防篡改审计或事实保证。
- **反向证据：** 否

## PAPER-VERIFIED-070 Less Is More -- Until It Breaks: Security Pitfalls of Vision Token Compression in Large Vision-Language Models

- **标识：** arXiv:2601.12042
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-01-17
- **正文入口：** https://arxiv.org/abs/2601.12042
- **层级：** C / R2
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08
- **正文位置：** §3 Demystifying Robustness Degradation, §4.1–4.4 Compression-Aware Attack, §5.3–5.4 Evaluation, §6 Discussion, §7 Conclusion, Appendix D/F/G
- **技术问题：** 视觉token压缩的排序不稳定会产生只在低保留率压缩状态出现、在全token测试中消失的隐蔽安全失效。
- **核心机制：** Compression-Aware Attack以低重要区域选择性扰动、分层token排序目标和语义擦除，诱导压缩器保留无关token并丢弃任务关键证据；T-CAA用边框区域和升/降双通用模板在未知模型与压缩配置下迁移该排序操纵。
- **控制流：** 先比较压缩/非压缩状态下的扰动敏感性并定位排序不稳；白盒CAA在首个压缩层操纵低重要token排名并擦除存活语义；黑盒T-CAA枚举可能压缩层范围，在代理模型优化通用模板；分别测量压缩攻击效果、非压缩性能保持和Compression Sensitivity Gap。
- **数据结构：** token重要性排序, Top/Bottom token集合, 分层排名约束, 保留率/压缩层配置, UPR/CAE/CSG指标
- **技术效果：** 揭示效率-安全权衡及压缩状态特有攻击面，证明标准非压缩安全测试可能无法复现或归因低预算运行时故障。
- **局限：** 正文主要评测单图LVLM和attention驱动的文本引导压缩，尚未覆盖长视频时序压缩；攻击/防御依赖压缩机制类别和配置范围；现有检测与自适应防御在保持干净性能时保护有限。
- **反向证据：** 是

## PAPER-VERIFIED-072 Long Video Understanding With Learnable Retrieval in Video-Language Models

- **标识：** 10.1109/tmm.2026.3664996
- **正式年份：** IEEE Transactions on Multimedia (2026)
- **最早公开：** 2023-12-08
- **正文入口：** https://doi.org/10.1109/tmm.2026.3664996
- **层级：** C / R2
- **机制簇：** LONG_VIDEO_MEMORY_RETRIEVAL
- **对应本地机制：** M03, M07
- **正文位置：** §III-A Video Tokenization, §III-B Question-guided Retrieval, §III-C End-to-End Optimization, §IV-D Complexity Analysis, §IX Limitation and Future Work
- **技术问题：** 长视频产生大量视觉token并包含无关片段，全局聚合会丢失局部细节且干扰LLM推理。
- **核心机制：** 每个chunk经CLIP编码并做空间/时间池化为68个token存入memory；冻结文本编码器前增加轻量MLP学习问题表示，检索Top-K相关chunk；用答案交叉熵和soft matching loss端到端训练检索器与投影器。
- **控制流：** 视频切成4秒chunk并压缩token；问题经CLIP文本编码器和MLP；计算问题与chunk相似度并选择Top-K；只把选中chunk token投影给冻结LLM生成答案。
- **数据结构：** chunk token memory, 68-token局部表示, 问题嵌入, Top-K chunk索引, soft matching目标
- **技术效果：** 减少LLM视觉token、过滤无关内容并保留局部细节，在多个零样本VideoQA数据集提高性能。
- **局限：** 固定K=5并非样本自适应；检索未选中正确chunk时必然失败；作者建议加入少量全局token但尚未实现。
- **反向证据：** 否

## PAPER-VERIFIED-073 LongVideo-R1: Smart Navigation for Low-cost Long Video Understanding

- **标识：** arXiv:2602.20913
- **正式年份：** CVPR 2026
- **最早公开：** 2026-02-24
- **正文入口：** https://arxiv.org/abs/2602.20913
- **层级：** C / R2
- **机制簇：** EVENT_CAUSAL_REASONING, FRAME_EVIDENCE_SELECTION, budget_aware_navigation
- **对应本地机制：** M04, M07
- **正文位置：** §3.1, §3.2, §3.3, Appendix D
- **技术问题：** 长视频问答需要在工具成本约束下导航到足够的局部证据。
- **核心机制：** 在分层视频树中下钻、横移或回退，以上下文充分性控制叶节点QA和停止，并显式累计工具成本。
- **控制流：** 代理在树中下钻、横移或回退；依据上下文充分性决定继续导航、在叶节点回答或停止。
- **数据结构：** 层级视频树, 导航轨迹, 上下文充分性状态, 累计工具成本
- **技术效果：** 把低成本长视频理解表述为显式预算导航问题。
- **局限：** 均匀切分会割裂语义；依赖合成轨迹与片段描述；无声明校准和候选回退。
- **反向证据：** 否

## PAPER-VERIFIED-086 OmniRAG-Agent: Agentic Omnimodal Reasoning for Low-Resource Long Audio-Video Question Answering

- **标识：** arXiv:2602.03707
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-02-03
- **正文入口：** https://arxiv.org/abs/2602.03707
- **层级：** A / R2
- **机制簇：** AUDIO_VISUAL_ALIGNMENT
- **对应本地机制：** M02, M06
- **正文位置：** §4.1 Multi-Modal RAG, §4.2 Multi-Turn Reasoning Process, §4.3 RL-Based Optimization, §5.5 Ablation Study, §5.6 Budget Analysis, §6 Conclusion
- **技术问题：** 低资源长音视频QA中的密集编码成本高，图像与音频细粒度检索、主动规划和端到端优化不足。
- **核心机制：** 构建带时间戳的图像和音频双库；OmniLLM逐轮生成自然语言检索查询、调用对应Top-K工具并合并证据；以GRPO联合优化工具使用和答案质量。
- **控制流：** 视频先下采样成初始流并建立图像/ASR库；代理基于问题和历史生成图像或音频查询；环境返回紧凑证据并追加到历史；循环规划、检索、观察直到回答；训练时按组相对奖励更新。
- **数据结构：** 图像库B_img, 音频转写库B_aud, 带时间元数据的Top-K证据, 多轮历史H_t, 规划轨迹与工具动作
- **技术效果：** 在紧预算下检索分散的音视频线索，并在三个omnimodal基准上优于先前低资源方法。
- **局限：** 依赖检索器质量；多轮错误会累积；迭代交互增加计算；停止和验证机制仍需增强，真实领域迁移尚未充分验证。
- **反向证据：** 否

## PAPER-VERIFIED-087 On the Adversarial Robustness of Large Vision-Language Models under Visual Token Compression

- **标识：** arXiv:2601.21531
- **正式年份：** ICML 2026
- **最早公开：** 2026-01-29
- **正文入口：** https://arxiv.org/abs/2601.21531
- **层级：** C / R2
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08
- **正文位置：** §2.2 Threat Model, §3 Motivation: An Empirical Study, §4.1–4.4 Compression-Aligned Attack, §5.2–5.3 Results and Analysis, §6 Possible Defenses, §7 Conclusion, Appendix G Limitations
- **技术问题：** 全token空间上优化的传统攻击与压缩后推理路径不一致，会高估视觉token压缩LVLM的对抗鲁棒性。
- **核心机制：** CAGE将攻击优化对齐压缩瓶颈：Expected Feature Disruption按未知预算下的存活概率把扰动集中到可能保留的token，Rank Distortion Alignment使高扰动token同时获得高选择排名，从而穿过剪枝/合并瓶颈。
- **控制流：** 在灰盒视觉编码器上估计token重要性及预算先验；联合优化期望特征破坏和排名-扰动对齐；生成压缩感知扰动；跨压缩机制和预算比较clean/robust accuracy，并测试选择随机化、稳健选择和attention检测。
- **数据结构：** token存活概率分布, clean/adversarial token特征, 重要性排名, 扰动强度排名, 预算先验区间
- **技术效果：** 证明压缩会保留高度失真的高重要token，压缩无关攻击给出过于乐观的鲁棒性；CAGE在多种压缩机制和预算下暴露更强漏洞。
- **局限：** 主要覆盖单图、训练外即插即用/outer-LLM压缩；对视频、多图和Agent长循环尚未验证；灰盒优势依赖已知或近似视觉编码器；当前检测和轻量防御对攻击分布变化泛化不足。
- **反向证据：** 是

## PAPER-VERIFIED-110 Seeing the Scene Matters: Revealing Forgetting in Video Understanding Models with a Scene-Aware Long-Video Benchmark

- **标识：** arXiv:2603.27259
- **正式年份：** CVPR 2026 (Highlight)
- **最早公开：** 2026-03-28
- **正文入口：** https://arxiv.org/abs/2603.27259
- **层级：** A / R2
- **机制簇：** EVENT_CAUSAL_REASONING
- **对应本地机制：** M07, M10
- **正文位置：** §3 SceneBench: Design and Construction, §4.1 Scene-RAG, §5.1 SceneBench Benchmark, §5.2 Scene-RAG and Memory Loss, §5.3 Scene-RAG Ablation, §6 Conclusion, Appendix A/B/F
- **技术问题：** 现有长视频基准难以在同一视频内隔离场景跨度、长期遗忘、跨场景因果与音频线索融合问题。
- **核心机制：** 构建SceneBench，以至少两分钟的场景级证据跨度评测长程理解；提出Scene-RAG，通过TV-L1场景切分、视觉编码与音频caption构建动态多模态场景记忆，并将查询分解为细粒度线索后检索Top场景供MLLM推理。
- **控制流：** 离线按语义连续性切分场景；对每个场景生成视觉embedding和时间对齐音频caption；查询到达后由Qwen3分解线索，执行相似度检索，融合Top场景证据并交给MLLM回答。
- **数据结构：** SceneBench六类任务, 场景时间区间, 视觉embedding, 音频caption, 多模态场景memory bank
- **技术效果：** 正文显示模型性能随场景证据距离增加而下降，Scene-RAG在中长距离上缓解遗忘并优于帧级Video-RAG，构成长上下文遗忘的反向证据。
- **局限：** SceneQA/I-VQA长视频人工标注昂贵且存在人物、地点和场景边界歧义；Scene-RAG依赖离线场景切分、InternVideo2/Qwen-Audio2/Qwen3组件和动态记忆；过长音视频上下文仍可能引入冗余噪声。
- **反向证据：** 是

## PAPER-VERIFIED-118 Stress Tests REVEAL Fragile Temporal and Visual Grounding in Video-Language Models

- **标识：** arXiv:2602.11244
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-02-11
- **正文入口：** https://arxiv.org/abs/2602.11244
- **层级：** B / R2
- **机制簇：** FINE_GRAINED_REGION_GROUNDING
- **对应本地机制：** M05, M08
- **正文位置：** §3.1 Video Sycophancy, §3.2 Language-only Shortcuts, §3.3 Temporal Expectation Bias, §3.4 Spatiotemporal Occlusion, §3.5 Camera-Motion Sensitivity, §5 Discussion and Conclusion
- **技术问题：** 常规视频基准的最终准确率无法判断模型是否真正使用视觉、时间顺序和运动证据，语言先验可能制造虚假能力。
- **核心机制：** REVEAL构建五类受控压力测试：视频顺从性、语言捷径、时间期望偏置、互补时空遮挡和摄像机运动，分别隔离视觉证据使用、跨帧绑定和运动感知缺陷。
- **控制流：** 从现有数据自动生成成对扰动；人工验证关键样本；向模型提供原始或扰动视频及诊断问题；按任务特定指标比较模型与人类，形成多维脆弱性画像。
- **数据结构：** 原始/扰动视频对, 时序重排与空白基线, 互补遮挡帧序列, 合成摄像机运动, 多维压力测试结果
- **技术效果：** 揭示主流VidLM会忽略视频、迎合错误声明、把逆序场景描述为正序并误判基础摄像机运动，提供可扩展诊断管线。
- **局限：** 受控扰动不完全代表真实部署；人与模型帧采样方式不同；部分标注由VidLM生成，虽经人工验证仍可能残留偏差；尚未给出修复机制。
- **反向证据：** 是

## PAPER-VERIFIED-129 TTF: Temporal Token Fusion for Efficient Video-Language Model

- **标识：** arXiv:2605.07355
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-05-08
- **正文入口：** https://arxiv.org/abs/2605.07355
- **层级：** C / R2
- **机制簇：** VISUAL_TOKEN_BUDGETING
- **对应本地机制：** M04, M08
- **正文位置：** §3.1 Problem Setup, Anchor Frame Selection, Pointwise Matching, Threshold Gating, Positional Alignment, §5 Discussion
- **技术问题：** 视频视觉token随帧数增长，全球相似度或全矩阵合并开销高，且现有压缩没有利用相邻帧同一空间位置的局部时间冗余。
- **核心机制：** 选均值token最接近全局均值的代表锚帧；每个非锚token只在锚帧对应位置的局部窗口中找最佳余弦匹配；高相似token用锚token身份替代，低相似token保留，并重排3D位置与KV-cache偏移。
- **控制流：** 选锚帧；逐源帧逐位置做3×3局部匹配；阈值门控决定融合或保留；拼接锚token和保留token；同步收集原始时空位置并按真实压缩长度校准解码位置。
- **数据结构：** 锚帧token, 局部匹配映射dst(k,i), 保留掩码, 压缩token序列, 3D位置三元组, KV-cache实际长度
- **技术效果：** 以线性匹配开销在LLM前删除约三分之二视觉token，同时基本保持基线准确率并兼容高效注意力内核。
- **局限：** 全局手工阈值不适合所有视频，快速运动需要更保守阈值；未测试更大或MoE模型；当前时空对应依赖小局部位移假设。
- **反向证据：** 否

## PAPER-VERIFIED-008 An Empirical Analysis of Calibration and Selective Prediction in Multimodal Clinical Condition Classification

- **标识：** arXiv:2603.02719
- **正式年份：** CHIL 2026
- **最早公开：** 2026-03-03
- **正文入口：** https://arxiv.org/abs/2603.02719
- **层级：** D / R2
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION, calibration_failure_reverse_evidence
- **对应本地机制：** M06
- **正文位置：** §3, §5.2, §6
- **技术问题：** 多模态临床分类的平均判别提升可能掩盖少数类失准和拒答能力退化。
- **核心机制：** 按类别分解ECE并评估选择性AUROC/AUPRC，证明多模态融合的判别增益可与少数类失准和拒答退化并存。
- **控制流：** 按类别分解ECE，并计算选择性AUROC/AUPRC，对融合前后校准与拒答能力进行比较。
- **数据结构：** 类别概率, ECE分解, 选择性预测曲线
- **技术效果：** 提供多模态增益与校准/选择性风险并存的反向证据。
- **局限：** 单一ICU基准、回顾性同分布；多标签分类而非开放式VideoQA；未提出完整修复。
- **反向证据：** 是

## PAPER-VERIFIED-019 DeepEyes: Incentivizing Thinking with Images via Reinforcement Learning

- **标识：** arXiv:2505.14362
- **正式年份：** ICLR 2026
- **最早公开：** 2025-05-20
- **正文入口：** https://arxiv.org/abs/2505.14362
- **层级：** C / R2
- **机制簇：** DETAIL_INFORMATION_GATING, native_visual_tool_rl
- **对应本地机制：** M08
- **正文位置：** §3.1, §3.2, Appendix E
- **技术问题：** MLLM在细粒度单图问题上需要自主决定何时放大局部区域。
- **核心机制：** 模型逐步决定回答或生成bbox执行zoom，裁剪回注交错图文轨迹并对完整轨迹做RL。
- **控制流：** 模型逐步选择直接回答或输出bbox执行zoom；裁剪结果回注轨迹；RL对完整工具轨迹优化。
- **数据结构：** bbox动作, 裁剪图像, 交错图文轨迹
- **技术效果：** 通过原生视觉工具动作训练局部细看策略。
- **局限：** 主要是单图和crop动作；结果奖励不等于证据校准；同一模型定位、推理和回答导致错误相关。
- **反向证据：** 否

## PAPER-VERIFIED-031 Entropy Alone is Insufficient for Safe Selective Prediction in LLMs

- **标识：** arXiv:2603.21172
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-03-22
- **正文入口：** https://arxiv.org/abs/2603.21172
- **层级：** D / R2
- **机制簇：** EVIDENCE_SUFFICIENCY_VERIFICATION
- **对应本地机制：** M06
- **正文位置：** Abstract, 2 Methods, 2.2 Uncertainty Signals as Risk Scores, 3.2 Model-Specific Failure Modes, 3.3 Combining Entropy and Correctness, 4 Conclusion, Limitations
- **技术问题：** 低熵并不等于正确，熵型不确定性会把“自信但错误”的回答放入高可信覆盖区。
- **核心机制：** 把语义/预测熵风险分数与从模型激活训练的正确性探针分数做轻量组合，再按组合风险阈值执行回答或拒答。
- **控制流：** 生成回答并计算熵信号→单次前向提取激活→正确性探针打分→组合风险→按目标风险选择覆盖率/拒答。
- **数据结构：** 熵分数, 正确性探针logit, 组合风险分数, 风险-覆盖曲线, 目标校准误差
- **技术效果：** 在三类QA和四个模型族上通常降低E-AURC与TCE，且组合器除基础生成外不增加额外LLM推理轮次。
- **局限：** 仅短答案QA；3B至8B少量模型族；正确性探针依赖监督标签；组合器与探针同分割训练有轻度乐观偏差。
- **反向证据：** 是

## PAPER-VERIFIED-039 FaithSCAN: Model-Driven Single-Pass Hallucination Detection for Faithful Visual Question Answering

- **标识：** arXiv:2601.00269
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-01-01
- **正文入口：** https://arxiv.org/abs/2601.00269
- **层级：** D / R2
- **机制簇：** HALLUCINATION_DETECTION
- **对应本地机制：** M06
- **正文位置：** Abstract, IV Methodology, IV-C Low-Cost Supervision via Model-Driven Labeling, IV-D Uncertainty-Related Internal Signals, IV-E Model Architecture, VII Conclusion
- **技术问题：** 多模态幻觉检测常依赖重复采样或外部验证，成本高且忽略模型内部不同故障路径。
- **核心机制：** FaithSCAN从单次前向中提取生成token不确定性、视觉语义状态和跨模态对齐状态，分支编码后以不确定性感知注意力融合，监督输出幻觉分数。
- **控制流：** 冻结VLM生成→抽取三类内部信号→各分支压缩为定长向量→门控注意力融合→二分类幻觉判断。
- **数据结构：** token级logit/熵/隐藏状态序列, 原始视觉表示, 对齐视觉表示, 分支证据向量, 幻觉置信分数
- **技术效果：** 在多种VLM架构和分布外设置中优于采样式基线，并保持单次前向检测；消融显示三类信号互补。
- **局限：** 标签由参考答案和外部视觉NLI判别器生成并需人工抽检；检测器与底层模型架构绑定；仅VQA图像、只检测不补证或回退。
- **反向证据：** 否

## PAPER-VERIFIED-101 ReMoRa: Multimodal Large Language Model based on Refined Motion Representation for Long-Video Understanding

- **标识：** arXiv:2602.16412
- **正式年份：** 仅2026预印本
- **最早公开：** 2026-02-18
- **正文入口：** https://arxiv.org/abs/2602.16412
- **层级：** C / R2
- **机制簇：** SELF_CORRECTION_REFLECTION
- **对应本地机制：** M06
- **正文位置：** Abstract, 4 Method, 4.1 Refined Motion Representation Module, 4.2 Hierarchical Motion State Space Module, 5.3 Ablation Studies, 6 Conclusion
- **技术问题：** 密集RGB帧计算呈二次增长且高度冗余，稀疏采帧又会漏掉短时动作；原始压缩域运动向量噪声大且粗糙。
- **核心机制：** ReMoRa保留稀疏I帧表观，用RMR把块级运动向量去噪并稠密化，再由分层运动状态空间模块在GOP内融合运动与表观、跨GOP线性建模长程依赖。
- **控制流：** 解析GOP→编码I帧→提取并细化运动向量→GOP内选择性扫描/双向混合→跨GOP状态空间聚合→对齐LLM回答。
- **数据结构：** GOP层级, I帧patch token, 块级运动向量, 细化运动表示, 状态空间记忆
- **技术效果：** 以线性时序建模避免完整RGB解码，在LongVideoBench、NExT-QA、MLVU等多个长视频基准超过强基线。
- **局限：** 依赖视频编码结构与运动向量质量；运动细化需光流预训练；空间细节仍主要由稀疏I帧提供，未设计答案验证闭环。
- **反向证据：** 否

## PAPER-VERIFIED-124 Thinking With Videos: Multimodal Tool-Augmented Reinforcement Learning for Long Video Reasoning

- **标识：** arXiv:2508.04416
- **正式年份：** CVPR 2026
- **最早公开：** 2025-08-06
- **正文入口：** https://arxiv.org/abs/2508.04416
- **层级：** C / R2
- **机制簇：** FRAME_EVIDENCE_SELECTION, multimodal_tool_augmented_rl
- **对应本地机制：** M04
- **正文位置：** §3.1, §3.2, §3.3, Appendix F
- **技术问题：** 长视频推理难以在有限上下文中自主选取需要密集观察的时间区间。
- **核心机制：** 视频裁剪工具按起止时间返回密集帧并回注多模态CoT，联合时序定位、VQA和grounded VQA做难度感知GRPO。
- **控制流：** 模型生成起止时间调用视频裁剪工具；密集帧回注多模态CoT；以难度感知GRPO训练工具使用和回答。
- **数据结构：** 时间裁剪动作, 密集帧, 多模态CoT轨迹
- **技术效果：** 联合学习时间定位、局部观察和视频问答。
- **局限：** SFT/RL数据和训练成本高；工具主要为时间裁剪；无声明事实校准与安全回退。
- **反向证据：** 否
