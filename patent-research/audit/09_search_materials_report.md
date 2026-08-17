# 查新检索报告（09，P1/P4/P9）

**日期：** 2026-08-17　**检索人：** AI 辅助（Web 检索 + Google Patents + 本地文献审计）
**对象：** `专利相关/新申请草案_支持度驱动补看与保守替换_20260817.md` 权利要求 1 核心——反事实最小破坏证据对训练的支持度验证器 + 同一分数三重驱动（触发/缺口对齐/门控替换）。
**检索级别声明：** 本报告为 Web 级查新，**不替代**代理机构在 CNIPA/正式数据库的查新报告；标级：候选方向/需代理人复核。

## 一、检索式与来源

| 方向 | 检索式（Web/Google Patents） |
|---|---|
| D-1 反事实×视频QA | counterfactual data augmentation video question answering evidence perturbation；contrastive negative evidence construction train entailment verifier video key frame masking removal |
| D-2 声明级验证×多模态 | claim-level fact verification multimodal video LVLM hallucination FActScore atomic claims |
| D-3 置信度驱动主动获取 | confidence-driven second-look video QA active visual acquisition 2026；video QA answer verification confidence threshold retrieve additional frames patent CN |
| P 专利 | patents.google.com CN：视频问答+置信度阈值+回答验证+增加帧；结合本地驳回决定 D1-D5 |

## 二、分方向结论

### D-1 反事实×视频问答 —— 未检到覆盖本申请训练方式

最近文献与差异：
1. **CounterVid**（arXiv:2601.04778，2026，已全文核实）：生成"同场景、不同动作"的**合成反事实视频**（Qwen-Image-Edit+Wan2.2 图生视频），构造 2.6 万偏好对，用 **MixDPO 偏好优化直接微调回答模型**。明确无独立验证器（"without an explicit reward model"）、无推理时按置信度补看机制、推理配置固定（32帧固定预算）。**差异：本申请对真实视频证据施加最小破坏（删关键帧/模糊文字/语音段错移/替换片段、保留背景）构造 E+/E− 对，训练独立的声明-证据支持度验证器（冻结视觉编码器+LoRA+排序裕量），且反事实对不用于训练回答模型。**
2. ACQUIRED 数据集（EMNLP 2023）：人工标注反事实问题的**评测数据集**，非训练构造方法。
3. 文本域：FEVER 对比检索（ACL 2024 fever-1.28）生成正负证据对**训练检索器**；证明步硬负例（arXiv:2311.06736）训练文本推理验证器。**均为文本域、非视频时间轴最小破坏。**

### D-2 声明级验证×多模态 —— 门控概念有近邻，组合未见

1. **Multi-Modal Fact-Verification Framework**（arXiv:2510.22751，已全文核实）：文本 LLM 幻觉治理；声明抽取（T5）+外部知识源并行验证+贝叶斯融合；置信度 = α·内在+β·外部+γ·一致性；有门控"Conf>τ?（τ=0.7）"触发纠错管线（替换/加模糊限制）。**与本申请差异：（a）文本/知识图谱域，无视频证据；（b）无反事实最小破坏训练对、无多模态 LoRA 验证器（其置信度为规则加权融合）；（c）低置信一律尝试修正，无双条件（绝对阈值+相对裕量）替换、无显式回退路径；（d）无"再获取视频证据"步骤——其证据来自外部检索而非受触发补看。**这是检索到的**最接近单篇**，说明书论证时须正面引用并划界。
2. ACM MM 2025 Responsible AI Challenge Task B（多模态事实性检测）：任务定义存在（用视觉+上下文验证文本声明），未见面世与本申请相同的训练与门控机制。
3. Unified Hallucination Detection（ACL 2024）等：检测/评测向，非答案替换闭环。

### D-3 置信度驱动主动视觉获取 —— 概念密集区，但"训练分数三重驱动"未见

本地文献审计已确认 2026 年公开的：Active-Look（ACL Findings 2026，定位信号不一致触发再看）、LENS（arXiv:2607.25125，预算自适应分配）、QANTA（置信度决定何时继续获取证据/何时提交）、LFPC/AdaptVision/VisionLeaf（CVPR 2026）、OmniReasoner、DeepEyes（arXiv:2505.14362）、ZoomEye（EMNLP 2025）、VLM-R3。**这些覆盖"按需获取/置信度触发"的概念层，但均为策略模型/提示驱动获取，无一以"反事实对训练的声明-证据支持度"作为触发与采纳的统一信号，也无双条件保守替换。**检索亦未发现 2026 年"confidence-driven second-look video QA"直接命中。E-VQA（arXiv:2607.11862）为证据回指任务定义，无验证器训练。

### P 专利文献 —— 未检到组合覆盖

1. CN 检索命中均为相邻域：CN115599954B（场景图推理）、CN114996513A（跨模态提示学习）、CN112559698A（多模态融合），无验证器训练/触发补看/门控替换。
2. US20160110357A1：文本 QA 候选答案置信度阈值（2016，纯文本）。
3. 本地驳回对比文件 D1（CN121388101A，置信度迭代）+ D2（CN117744802A，自验证修正）：覆盖"触发+校验"骨架，但均无反事实对训练验证器、无缺口分类补看、无双条件门控。
4. 自家在先申请 202610425757.8：已按草案第二节划界。

## 三、特征-风险矩阵

| 独权核心特征 | 最近现有技术 | 重叠度 | 风险 |
|---|---|---|---|
| E+/E− 最小破坏证据对（真实视频、保留背景、四算子） | CounterVid（合成视频、DPO 训练回答模型）；FEVER 文本负例 | 部分 | 中低 |
| 冻结视觉编码器 LoRA 声明-证据验证器 + 排序裕量 | 2510.22751（规则融合置信度，无训练验证器）；文本 entailment verifier | 部分 | 中低 |
| 支持度触发补看 | D1/QANTA/Active-Look（概念）；US20160110357A1（文本） | 概念层 | 中（须靠"同一训练分数"绑定） |
| 缺口分类→时间/区域补看 | AdaptVision/LENS/OmniReasoner（策略获取） | 概念层 | 中（从属权4决策表承载） |
| 双条件（绝对阈值+相对裕量）替换/回退 | 2510.22751（单阈值、无回退） | 部分 | 中低 |
| **同一验证器分数三重使用闭环（整体组合）** | **未检到** | — | **未见单篇覆盖；组合类风险=审查员多篇拼凑（D1+CounterVid+2510.22751）** |

## 四、查新结论与方案定稿建议

1. **未检索到单篇现有技术覆盖独权 1 的整体组合**；主要残余风险是三篇拼凑式组合驳回（D1 提供触发迭代骨架 + CounterVid 提供反事实训练概念 + 2510.22751 提供置信度门控）。抗辩支点：（a）CounterVid 反事实对象与训练目标均不同（合成视频训练回答模型 vs 真实证据最小破坏训练独立验证器）；（b）2510.22751 无视频补看、无双条件回退；（c）本申请同一分数贯穿三重决策的功能互存关系。
2. **草案 V1 骨架维持不变**，按查新做三处强化（已同步更新草案 V1→V1.1）：
   - 从属新增权 2.5（破坏算子须同时覆盖视觉帧、文字区域、语音段三类模态中的至少两类）——与 CounterVid 单一视觉模态合成形成硬区别；
   - 说明书正面引用并划界 2510.22751、CounterVid、Active-Look/LENS/QANTA、D1/D2；
   - 背景技术段落明确"现有置信度门控（单阈值、修正式）不提供证据获取与答案采纳的统一信号"。
3. 代理人提交前仍须做 CNIPA 正式查新（本报告为 Web 级），重点补检中文专利库"反事实+验证器+视频"与"支持度+门控+替换"。

## 五、来源清单

- CounterVid: https://arxiv.org/html/2601.04778v1 （全文核实）
- Multi-Modal Fact-Verification: https://arxiv.org/html/2510.22751v1 （全文核实）
- ACQUIRED (EMNLP 2023): https://aclanthology.org/2023.emnlp-main.719/
- E-VQA: https://arxiv.org/html/2607.11862v1
- Unified Hallucination Detection (ACL 2024): https://aclanthology.org/2024.acl-long.178.pdf
- ACM MM 2025 Challenge: https://mm-hall-fact.github.io/ACMMM2025/
- FEVER contrastive retrieval: https://aclanthology.org/2024.fever-1.28.pdf
- Proof-step hard negatives: https://arxiv.org/html/2311.06736v3
- Awesome-Video-Hallucination: https://github.com/hukcc/Awesome-Video-Hallucination
- CN115599954B: https://patents.google.com/patent/CN115599954B/zh
- CN114996513A: https://patents.google.com/patent/CN114996513A/zh
- CN112559698A: https://patents.google.com/patent/CN112559698A/zh
- US20160110357A1: https://patents.google.com/patent/US20160110357A1/en
- 本地：驳回决定（source_texts/patent_office_action_pdf_extract.txt）、在先申请（source_texts/patent_docx.txt）、用户文献审计（docs/Qwen2.5主动证据补看_2026论文启发与实验预注册_20260804.md）
