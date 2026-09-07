# I1-V0 最小可信论文集合并卡片

## 合并口径

- 输入仅限 `00_brief.md`、`01a_sources_papers.jsonl`、`01a_paper_cards_A_B.md`、`01b_sources_papers.jsonl`、`01b_paper_cards_C_D.md`。
- 以 `family_key` 按论文族去重；arXiv、会议版和后续修订合并为同一族。
- 重复族共 3 组：`arxiv:2603.04977`、`arxiv:2512.05774`、`arxiv:2607.11862`。
- 入池政策：2026 正式发表；或仅有预印本但首次公开于 2026；或 2025 预印本后于 2026 正式发表。
- 合并后共 34 个论文族：入池 16 个，背景 18 个。`R1=16`，`R2=18`；入池中 `R1=8`，`R2=8`。
- `formal_year: null` 表示输入材料未核验到正式发表年份，不以预印本年份冒充正式年份。
- 逐族完整机器可读字段以 `01h_verified_seed_papers.jsonl` 为准。

## 入池论文族（16）

### PAPER-A007 / PAPER-CD-002

- **论文族**：`arxiv:2512.05774`，Active Video Perception: Iterative Evidence Seeking for Agentic Long Video Understanding
- **R1/R2**：R1
- **最早公开 / 正式年份**：2025-12-05 / 2026
- **政策判定**：`pool_eligible=true`；2025 预印本 + 2026 正式发表。
- **正文核验位置**：§3 Method and Algorithm 1；Appendix A Limitations；Appendix failure analysis；§3.1-§3.3；Appendix B.3。
- **机制**：Planner 决定 what/where/how，Observer 累加带时间戳证据，Reflector 以充分性阈值决定回答或按缺口重规划。
- **局限**：仅离线 QA；提示驱动；76% 失败来自观察器；轮数耗尽强制回答；无声明级监督、候选对称评分或保守回退。
- **来源**：`01a_sources_papers.jsonl`；重复来源 `01b_sources_papers.jsonl`。

### PAPER-A008 / PAPER-CD-001

- **论文族**：`arxiv:2603.04977`，Think, Then Verify: A Hypothesis-Verification Multi-Agent Framework for Long Video Understanding
- **R1/R2**：R1
- **最早公开 / 正式年份**：2026-03-05 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3 Method and Algorithm 1；§4.4 Ablation；§5 Conclusion；Abstract；§3.2-§3.3。
- **机制**：候选答案转可测试假设，Judge 生成最小判别线索，Verifier 局部回看并输出三态，证据不足时追加观察或重写假设。
- **局限**：依赖预给多选项和逐帧 caption；每次细看最多五帧；Agent 与状态由提示产生；无独立校准声明支持度及失败回退协议。
- **来源**：`01a_sources_papers.jsonl`；重复来源 `01b_sources_papers.jsonl`。

### PAPER-A009 / PAPER-CD-012

- **论文族**：`arxiv:2607.11862`，Evidence-Backed Video Question Answering
- **R1/R2**：R1
- **最早公开 / 正式年份**：2026-07-13 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3 Evidence-Backed Video QA；§4 Instruction Tuning Data Construction；Table 2/5；§6 Conclusion；§3.1；§5.4。
- **机制**：联合输出答案、非重叠时间段和跨帧密集 masklet；双路径生成 160K 答案-证据训练数据。
- **局限**：密集标注昂贵且依赖大型 VLM/分割器；QA 与 grounding 仍解耦；未覆盖 OCR/ASR；不做原子声明检测、低支持补看或候选回退。
- **来源**：`01a_sources_papers.jsonl`；重复来源 `01b_sources_papers.jsonl`。

### PAPER-A010

- **论文族**：`arxiv:2605.23216`，CaST-Bench
- **R1/R2**：R1
- **最早公开 / 正式年份**：2026-05-22 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3 Task Definition；§4 CaST-Bench；§5.2-§5.3；§6 Conclusion。
- **机制**：因果链证据包含时间段、事实 rationale 和 1-FPS bbox 轨迹；遮蔽全部证据区域以过滤可猜问题。
- **局限**：诊断基准而非闭环模型；1-FPS 框非像素级；结构化输出遵循率及 faithful rate 低。
- **来源**：`01a_sources_papers.jsonl`。

### PAPER-A011

- **论文族**：`arxiv:2512.14870`，HERBench
- **R1/R2**：R1
- **最早公开 / 正式年份**：2025-12-16 / 2026
- **政策判定**：`pool_eligible=true`；2025 预印本 + 2026 正式发表。
- **正文核验位置**：§3 HERBench；§5.1-§5.2；§6 Conclusion。
- **机制**：每题至少三个分散 cue；MRFS、oracle frame 和 leave-one-out 分离证据检索缺口与融合缺口。
- **局限**：多选且固定 16 帧；oracle 帧不可部署；只诊断检索/融合错误而不修复。
- **来源**：`01a_sources_papers.jsonl`。

### PAPER-B015

- **论文族**：`arxiv:2512.17495`，GroundingME
- **R1/R2**：R2
- **最早公开 / 正式年份**：2025-12-19 / 2026
- **政策判定**：`pool_eligible=true`；2025 预印本 + 2026 正式发表。
- **正文核验位置**：§3 GroundingME；§5 Analysis；§6 Conclusion。
- **机制**：以 Discriminative、Spatial、Limited、Rejection 四维评测复杂 grounding，并测试 Best-of-16 与正负样本混合训练。
- **局限**：静态图像框任务；Best-of-16 成本高；拒绝 SFT 使更难域外正 grounding 退化。
- **来源**：`01a_sources_papers.jsonl`。

### PAPER-B017

- **论文族**：`arxiv:2604.08456`，Entropy-Gradient Grounding
- **R1/R2**：R2
- **最早公开 / 正式年份**：2026-04-09 / `null`
- **政策判定**：`pool_eligible=true`；仅核验到预印本，但首次公开于 2026。
- **正文核验位置**：§3 Method；Table 7；Appendix I Limitations。
- **机制**：将下一 token 分布熵反传到视觉 token，提取并排名多连通区域，迭代重定位并以空间熵上升停止。
- **局限**：重复前反向传播成本高；定位正确不保证回答正确；基础模型不重视的区域无法由梯度恢复。
- **来源**：`01a_sources_papers.jsonl`。

### PAPER-CD-003

- **论文族**：`arxiv:2604.04379`，Reinforce to Learn, Elect to Reason
- **R1/R2**：R1
- **最早公开 / 正式年份**：2026-04-06 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§1；§4.1；§4.2。
- **机制**：GRPO 塑造关键帧证据输出；多候选按证据一致性、置信、透明度和非冗余性加权选举，低裕量增样并反驳检查。
- **局限**：多候选成本；证据来自模型自报和自检；无跨分布校准或有限样本风险保证。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-004

- **论文族**：`arxiv:2602.20913`，LongVideo-R1
- **R1/R2**：R2
- **最早公开 / 正式年份**：2026-02-24 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3.1-§3.3；Appendix D。
- **机制**：在分层视频树中下钻、横移或回退，以上下文充分性控制叶节点 QA 和停止，并累计工具成本。
- **局限**：均匀切分会割裂语义；依赖合成轨迹与片段描述；无声明校准和候选回退。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-005

- **论文族**：`arxiv:2603.24558`，LensWalk
- **R1/R2**：R2
- **最早公开 / 正式年份**：2026-03-25 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3.1-§3.4；Appendix A。
- **机制**：Reasoner 选择 Scan Search、Segment Focus 或 Stitched Verify，参数化时间范围/密度并保存时间戳锚点和主体记忆表。
- **局限**：证据由 VLM 生成而非独立验证；多轮成本；时间戳轨迹不是防篡改审计或事实保证。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-006

- **论文族**：`arxiv:2505.14362`，DeepEyes
- **R1/R2**：R2
- **最早公开 / 正式年份**：2025-05-20 / 2026
- **政策判定**：`pool_eligible=true`；2025 预印本 + 2026 正式发表。
- **正文核验位置**：§3.1；§3.2；Appendix E。
- **机制**：模型逐步决定回答或生成 bbox 执行 zoom，裁剪回注交错图文轨迹并对完整轨迹做 RL。
- **局限**：主要是单图和 crop；结果奖励不等于证据校准；同一模型定位、推理和回答导致错误相关。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-007

- **论文族**：`arxiv:2508.04416`，Thinking With Videos
- **R1/R2**：R2
- **最早公开 / 正式年份**：2025-08-06 / 2026
- **政策判定**：`pool_eligible=true`；2025 预印本 + 2026 正式发表。
- **正文核验位置**：§3.1-§3.3；Appendix F。
- **机制**：视频裁剪工具按起止时间返回密集帧并回注多模态 CoT，联合时序定位、VQA 和 grounded VQA 做难度感知 GRPO。
- **局限**：SFT/RL 数据和训练成本高；工具主要为时间裁剪；无声明事实校准与安全回退。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-008

- **论文族**：`arxiv:2604.25855`，SIEVES
- **R1/R2**：R1
- **最早公开 / 正式年份**：2026-04-28 / `null`
- **政策判定**：`pool_eligible=true`；仅核验到预印本，但首次公开于 2026。
- **正文核验位置**：§3.1；§3.2；Appendix A。
- **机制**：selector 联合评分回答正确性、定位质量和证据-答案一致性，并按 risk-coverage 回答或拒答。
- **局限**：单图 VQA；依赖显式 zoom 轨迹和有标签 selector；整题而非原子声明；经验风险曲线无有限样本保证。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-015

- **论文族**：`arxiv:2603.02719`，An Empirical Analysis of Calibration and Selective Prediction in Multimodal Clinical Condition Classification
- **R1/R2**：R2
- **最早公开 / 正式年份**：2026-03-03 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3；§5.2；§6。
- **机制**：按类别分解 ECE 并评估选择性 AUROC/AUPRC，显示多模态判别增益可与少数类失准和拒答退化并存。
- **局限**：单一 ICU 基准、回顾性同分布；多标签分类而非开放式 VideoQA；未提出完整修复。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-016

- **论文族**：`arxiv:2607.29240`，When Model Priors Conflict with Visual Evidence
- **R1/R2**：R1
- **最早公开 / 正式年份**：2026-07-31 / `null`
- **政策判定**：`pool_eligible=true`；仅核验到预印本，但首次公开于 2026。
- **正文核验位置**：§3；Candidate-Level Score Correction；Learning the Correction Strength；Selective Answer Revision。
- **机制**：带图/无图双评分估计先验冲突，实例特征预测校正强度，仅在替代候选满足支持条件时改答。
- **局限**：多选/二元；需 logit 和成对 CF/CS 开发集；无图分数仅为先验代理；单图且无补证。
- **来源**：`01b_sources_papers.jsonl`。

### PAPER-CD-020

- **论文族**：`arxiv:2607.25125`，LENS
- **R1/R2**：R2
- **最早公开 / 正式年份**：2026-07-27 / 2026
- **政策判定**：`pool_eligible=true`；2026 首次预印本且 2026 正式发表。
- **正文核验位置**：§3.2-§3.4；Appendix C。
- **机制**：按查询在空间 zoom-in 视觉提示与时间 zoom-out 图聚合间动态分配固定帧预算。
- **局限**：一次性采样而非验证后迭代；控制器无校准不确定性；无声明级证据保留保证。
- **来源**：`01b_sources_papers.jsonl`。

## 背景论文族（18）

| ID | 论文族 | R | 最早公开 | 正式年份 | 机制 | 局限 | 正文核验位置 | 来源 |
|---|---|---:|---|---:|---|---|---|---|
| A001 | `arxiv:2509.08621` | R1 | 2025-09-10 | 2025 | AdsQA 与 ReAd-R 规则奖励 GRPO | 污染/标注/评测偏差；无时空证据 | §4；Appendix E | `01a_sources_papers.jsonl` |
| A002 | `arxiv:2501.05069` | R1 | 2025-01-09 | 2025 | 声明递归分解、局部证据证明/反驳与树回溯 | 多选和字幕中介；定位仍是瓶颈 | §3；§5 Table 7-8；§6 | `01a_sources_papers.jsonl` |
| A003 | `arxiv:2507.19599` | R1 | 2025-07-25 | 2025 | 视觉提示跨帧传播、VideoLLM 与 SAM2 mask | 帧数少、时延高、不处理 OCR/ASR | §3；Table 6-8；§5 | `01a_sources_papers.jsonl` |
| A004 | `arxiv:2502.07411` | R1 | 2025-02-11 | 2025 | scene-text VideoQA 的时间/分辨率/OCR 诊断 | 最佳约 33%；增益依模型和场景 | Abstract/§1；§5；§6 | `01a_sources_papers.jsonl` |
| A005 | `arxiv:2411.14901` | R2 | 2024-11-22 | 2025 | 稀疏/密集层级表示递归细化时间边界 | 仅时间定位；未覆盖音频 | §3；Figure 5/Table 4；§6 | `01a_sources_papers.jsonl` |
| A012 | `arxiv:2505.21333` | R1 | 2025-05-27 | 2025 | 25 类视频 OCR 识别、定位、跟踪与跨帧任务 | 样本有限；仅诊断不修复 | §3；Figure 5；§4；§5 | `01a_sources_papers.jsonl` |
| B013 | `arxiv:2412.08746` | R2 | 2024-12-11 | `null` | OCR+布局经 64 queries 压缩并与视觉 token 合并 | 依赖 OCR；单页训练扩多页 | §3；§5 Table 3；Appendix D | `01a_sources_papers.jsonl` |
| B014 | `arxiv:2506.21710` | R2 | 2025-06-26 | 2025 | KV value 相似图、ROI/NMS 与存在置信重排 | 小目标分辨率限制；crop 对仍可能答错 | §3；§4.3-§4.6；§5 | `01a_sources_papers.jsonl` |
| B016 | `arxiv:2501.18954` | R2 | 2025-01-31 | 2025 | 检测器联合框、词-区域及图像/区域 caption 损失 | caption 噪声；仅静态检测 | §3；§4；§5.3；§6 | `01a_sources_papers.jsonl` |
| B018 | `arxiv:2411.04923` | R2 | 2024-11-07 | 2025 | 空间/时间双编码和 SEG token 驱动跨帧 mask | 标注噪声；粒度不稳；短中视频 | §3；Table 6-7；Limitations | `01a_sources_papers.jsonl` |
| CD009 | `arxiv:2511.09228` | R1 | 2025-11-12 | `null` | 初答原子化、多改写自一致/置信聚合再修订 | 同模型相关错误；不获取新证据 | §3.1-§3.4 | `01b_sources_papers.jsonl` |
| CD010 | `arxiv:2402.03190` | R1 | 2024-02-05 | 2024 | essential claims、多工具并行取证与声明判决 | 闭源/多工具成本；无保守替换 | §4.1-§4.4；§5.3 | `01b_sources_papers.jsonl` |
| CD011 | `cvpr2025:halloc` | R2 | 2025-06-11 | 2025 | 轻量检测器并行输出逐 token 幻觉概率 | 合成标签；不验证真实证据 | Abstract；§3；§4 | `01b_sources_papers.jsonl` |
| CD013 | `arxiv:2509.20912` | R1 | 2025-09-25 | `null` | 正证据/必要证据遮挡/随机遮挡三路 GRPO | 单图、依赖检测/OCR、遮罩伪影 | §1；§3.1-§3.3 | `01b_sources_papers.jsonl` |
| CD014 | `arxiv:2208.02814` | R2 | 2022-08-04 | 2024 | 独立校准集选择保守参数控制期望风险 | 交换性/有界/单调要求；非单样本保证 | §1.1；§2.1；§2.4；§3.4 | `01b_sources_papers.jsonl` |
| CD017 | `arxiv:2412.16117` | R2 | 2024-12-20 | 2025 | 时空 token 合并、问题注意力剪枝与 KV 压缩 | 注意力非因果证据；可能误剪短时小字 | §3.2；§3.3；§4.5 | `01b_sources_papers.jsonl` |
| CD018 | `arxiv:2501.01986` | R2 | 2024-12-30 | 2025 | 浅层相似 token 合并后按重要性剪枝 | 镜头切换破坏假设；不保证关键证据 | §3.2-§3.4；Method | `01b_sources_papers.jsonl` |
| CD019 | `arxiv:2508.16201` | R2 | 2025-08-22 | 2025 | 目标模型引导草稿视觉 token 剪枝并验收 token | 只验证分布一致性；收益主要为速度 | §2.2；§3.1；§3.2；§9 | `01b_sources_papers.jsonl` |

所有背景记录均为 `pool_eligible=false`。其中 `PAPER-CD-013` 仅有“v4 marked ICML”，输入未提供可确认的 2026 正式发表年份，按保守政策不入池。
