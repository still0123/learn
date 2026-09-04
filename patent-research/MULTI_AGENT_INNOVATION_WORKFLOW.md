# 专利创新多 Agent 闭环工作流

## 1. 目标

本工作流用于从最新论文中提炼可落地的专利创新候选，并经过独立评审、专利查新和总评审后，输出可审计的候选结论。

工作流不以“找几个新名词拼进专利”为目标，而要求每个候选同时回答：

1. 解决了什么具体技术问题；
2. 采用了什么可执行的技术机制；
3. 各技术特征为什么存在功能耦合，而不是模块并列；
4. 本地论文、代码或实验是否提供原始支持；
5. 相对论文和专利现有技术还剩下什么区别；
6. 适合进入独立权利要求、从属权利要求，还是应当淘汰。

## 2. 角色

| 编号 | 角色 | 核心职责 | 不得做的事 |
|---|---|---|---|
| I0 | 协调与总控 Agent | 冻结任务边界、调度、校验产物、控制回退、汇总最终文件 | 不得替其他 Agent 补造证据 |
| I1 | 论文检索 Agent | 检索、核验并拆解相关论文机制 | 不得直接判断专利授权性，不得构思候选 |
| I2 | 创新构思 Agent | 将论文机制与本地专利、代码、实验结合，形成候选 | 不得宣称新颖性，不得引用未核验论文 |
| I3 | 候选门禁 Agent | 以敌对审查员和工程评审视角决定候选能否进入专利查新 | 不得替候选润色过关，不得降低硬门禁 |
| I4 | 专利检索 Agent | 对幸存候选执行中英文专利检索、特征比对和组合风险分析 | 不得只搜候选名称，不得以搜索摘要代替权利要求核验 |
| I5 | 最终评审 Agent | 综合论文距离、专利距离、原始支持和实施证据作最终裁决 | 不得用平均分掩盖硬门禁失败 |

I0 由主 Agent 担任。I1 至 I5 使用相互隔离的上下文执行，只通过固定产物交换信息。

### 与 `patent-innovation-analysis` Skill 的关系

该 Skill 有必要使用，但定位是上位审计框架，不是外部检索工具。Skill 中既有 `P0–P9` 编号保持原义；本文件使用 `I0–I5` 表示本轮精简执行角色，避免编号冲突。

| 阶段 | 是否加载 Skill | 原因 |
|---|---|---|
| I0 任务冻结与总控 | 是 | 复用证据路径、运行目录、风险门禁和禁止虚构规则 |
| I1 论文检索 | 否，仅接收检索合同 | 避免被 Skill 中既有候选方向锚定；专注客观召回和论文机制核验 |
| I2-A 隔离构思 | 否 | 保持对论文结论和既有候选的隔离，从本地失败证据独立构思 |
| I2-B 论文校准后的候选成形 | 是 | 复用创新候选 Schema、原始支持检查和非模块拼接要求 |
| I3 候选门禁 | 是 | 复用敌对审查员模板、代码可行性和证据门禁 |
| I4 专利检索 | 部分使用 | Skill 提供特征矩阵和组合风险要求；实际检索仍由专利数据库与网页工具完成 |
| I5 最终评审 | 是 | 复用最终标级、法律风险提示和禁止“保证授权”规则 |

因此，执行时不是“调用一次 Skill 就自动得到创新点”，而是让 Skill 约束 I0、I2-B、I3、I5；论文搜索和专利搜索仍分别使用专门检索 Agent。

## 3. 总体流程

```text
I0 冻结任务合同
    ↓
    ├─ I1-M 元数据批量召回
    ├─ I1-X Exa语义补召回与重排
    ├─ I1-V 官方正文核验与机制卡片
    └─ I2-A 基于本地失败证据隔离构思
           ↓ G1：日期、正文、来源核验 + 隔离构思留痕
I2-B 用论文机制校准并生成创新候选
    ↓ G2：候选完整性检查
I3 敌对候选门禁
    ↓ G3：硬淘汰 + 评分阈值
I4 对幸存候选做专利查新
    ↓ G4：单篇覆盖 + 组合风险 + 日期/法律状态
I5 最终评审
    ↓ G5：证据合同与用途分级
I0 输出最终建议、权项布局与待办
```

若 I4 发现高度相近专利，允许候选回到 I2 修订一次，再经过 I3 和 I4 增量复核。每个候选最多回退两轮，超过两轮仍无法形成稳定区别时淘汰。

## 4. I0：任务合同

每轮开始前，I0 写入 `00_brief.md`：

```yaml
round_id: patent-innovation-YYYYMMDD-rXX
target_application: 当前申请或新申请名称
objective: 本轮要解决的问题
technical_domain: 视频问答 / 多模态证据校验
paper_window: 近三年
patent_cutoff_date: 检索截止日
jurisdictions: [CN, WO, US, EP]
max_candidates: 8
max_survivors_before_patent_search: 4
max_revision_rounds: 2
local_materials:
  - 当前权利要求
  - 说明书
  - 代码
  - 冻结实验记录
public_disclosure_to_audit:
  - GitHub
  - 论文或预印本
  - 答辩材料
```

I0 同时冻结：

- 当前专利的独立权利要求原子特征；
- 自家在先申请中已经公开的特征；
- 允许使用的实验数据及其来源；
- 禁止宣称的失败结果和未实现功能；
- 本轮论文与专利检索截止日期。

## 5. I1：论文检索 Agent

### 5.1 检索范围

优先检索近三年论文，另保留必要的基础论文。来源优先级：

1. 正式会议或期刊页面；
2. arXiv 正文；
3. 作者或机构代码仓库；
4. Semantic Scholar、Crossref 等元数据源；
5. 二手博客只能作为线索，不能作为结论证据。

时间范围由每轮 `00_brief.md` 冻结。本轮采用2026发表口径：

- 正式会议或期刊发表年份为2026的论文可以纳入；
- 2025年首次发布预印本、2026年正式会议或期刊发表的论文可以纳入2026论文池；
- 仅有预印本的论文，须在2026年首次公开才可纳入；
- arXiv、会议版和期刊扩展版合并为一个文献族，以最早公开版本计数；
- 每篇同时记录`research_pool_year`和`earliest_public_date`：前者决定是否进入本轮论文池，后者用于判断专利现有技术时间；
- 2026年以前的基础论文只能在“历史背景/已知机制”附录中提及，不进入I2候选依据，也不占2026论文配额。

检索采用四层领域版图，不局限于视频问答。

#### A层：直接任务与核心近邻

- 视频问答、图像问答、长视频理解、时序问答；
- 图像理解、视频理解、图像描述、视频描述；
- 多模态问答、知识型视觉问答、开放域视觉问答；
- 文档图像理解、DocVQA、图表问答、表格问答、场景文字问答；
- 视频时序定位、事件定位、动作识别、视频片段检索；
- 主动视觉感知、二次观察、视觉工具调用、视觉 Agent。

#### B层：计算机视觉与视觉证据基础

- 图像分类、目标检测、实例分割、语义分割、关键点检测；
- 视觉定位、指代表达理解、视觉 grounding、区域－文本对齐；
- OCR、场景文字检测与识别、Logo识别、文档版面分析；
- 细粒度识别、小目标检测、高分辨率视觉理解；
- 显著性检测、注意力图、响应图、CAM与证据区域提取；
- 目标跟踪、视频目标分割、跨帧关联和时序一致性；
- 场景图、对象关系建模、视觉蕴含与图像事实验证；
- 图像检索、视频检索、跨模态检索和证据重排序。

#### C层：多模态大模型与跨模态学习

- 多模态大模型、视觉语言模型、视频语言模型；
- 视觉编码器、投影连接器、视觉 Token 化与多图输入；
- 图文对齐、视听对齐、跨模态融合和交叉注意力；
- 多模态指令微调、偏好优化、强化学习和参数高效微调；
- Grounded CoT、视觉推理、程序化推理和工具增强推理；
- 多模态 RAG、视觉知识检索、证据包和引用归因；
- 多模态 Agent、规划、记忆、状态机和多 Agent 协作；
- 多图、多帧、交错图文和超长多模态上下文建模。

#### D层：可靠性、训练与系统机制

- 多模态幻觉检测、声明级事实验证、证据归因；
- 不确定性估计、概率校准、选择性预测、拒答和风险覆盖；
- 候选答案排序、验证器－生成器架构、保守替换和回退；
- 反事实证据、困难负例、对比学习、排序学习和对抗扰动；
- 分布外检测、鲁棒性、噪声标签学习和弱监督学习；
- 主动学习、自训练、课程学习、蒸馏和测试时适应；
- 视觉 Token 预算、帧/片段选择、Token剪枝/合并和上下文压缩；
- 动态分辨率、区域放大、级联推理、早退和模型路由；
- 预算感知推理、时延/显存约束、审计轨迹、数据血缘和可复现回执。

#### 检索配额与相关性分级

首轮采用“宽召回→正文核验→机制去重”三级漏斗：

```yaml
recall_records_target: 800
recall_records_soft_cap: 1200
abstract_screened_target: 300
full_text_verified_target: 120
full_text_verified_soft_cap: 180
final_R1_R2_mechanism_families_target: 60至90
```

这里的篇数均指整轮去重后的论文族，不是单次查询返回数量。

召回阶段优先使用可批量返回元数据的来源，如OpenAlex、Crossref、DBLP和arXiv API。Exa作为语义补召回与重排通道，用于发现术语不同但机制相近的论文，并提取与检索问题相关的highlights。全文核验仍须回到会议、期刊或预印本正文。标题、摘要或Exa highlights命中均不能计入`full_text_verified`。

#### Exa语义通道

Exa只在I1阶段使用，建议配置：

```yaml
category: publication
type: auto
numResults: 100
contents:
  highlights: true
startPublishedDate: 2025-01-01
endPublishedDate: 检索日
```

时间范围从2025开始是为了召回“2025预印本＋2026正式发表”的论文族；最终是否进入2026论文池仍由正式venue年份和最早公开日期双字段决定。

Exa查询采用长语义描述，按机制簇而不是单个关键词组织。每个查询必须包含：

- 具体技术问题；
- 输入和输出对象；
- 核心状态量或控制关系；
- 需要排除的普通实现；
- 优先来源域，如`arxiv.org`、`openaccess.thecvf.com`、`aclanthology.org`、`openreview.net`、`dl.acm.org`。

Exa结果进入`exa_semantic_only`状态，必须完成DOI/arXiv归一、论文族去重、2026资格核验和官方正文核验后，才能升级为R1/R2论文卡片。

密钥规则：

- 只从进程环境变量`EXA_API_KEY`读取；
- 不写入脚本、配置、Receipt、终端输出或Git；
- 请求日志只记录查询簇、结果数、费用和错误码；
- 运行结束后不保留含认证头的原始HTTP日志；
- 费用达到每轮硬上限时立即停止Exa通道，由现有元数据与正文通道继续。

这里的篇数均指整轮去重后的论文族，不是单次查询返回数量。

| 层级 | 建议比例 | 用途 |
|---|---:|---|
| A层 | 35% | 寻找最接近方案及直接反向证据 |
| B层 | 20% | 获取视觉定位、识别和证据提取机制 |
| C层 | 25% | 获取多模态模型、推理和Agent机制 |
| D层 | 20% | 获取训练、可靠性、预算和审计机制 |

每篇论文标记相关性：

- `R1-直接`：技术问题、输入输出和控制流程均接近；
- `R2-机制`：任务不同，但核心状态量或计算机制可迁移；
- `R3-启发`：只提供局部组件或工程原理；
- `R4-背景`：仅用于了解领域，不进入创新构思核心依据。

I2 只能把 R1、R2 论文作为候选的核心来源。R3只能补充从属实现，R4不能用于论证候选机制。

### 5.2 论文卡片

I1 输出 `01_paper_cards.md` 和 `01_sources_papers.jsonl`。每篇论文使用固定卡片：

```yaml
paper_id: PAPER-001
title:
venue_year:
official_url:
doi_or_arxiv:
publication_date:
research_pool_year:
earliest_public_date:
code_url:
search_layer: A | B | C | D
relevance_tier: R1 | R2 | R3 | R4
mechanism_cluster:
verified_from_full_text: true
technical_problem:
inputs:
core_mechanism:
training_or_optimization:
inference_control_flow:
data_structures:
technical_effect:
limitations:
overlap_with_current_patent:
reusable_principle:
cannot_copy_directly:
evidence_quote_or_section:
```

### 5.3 G1 门禁

- 每篇必须有准确 URL、时间和正文依据；
- 同一机制的重复论文合并成机制簇；
- 至少包含一篇反向证据，即已经非常接近当前设想的论文；
- I1 不输出“建议申请”“具备创造性”等判断；
- 无法获得正文的论文只能标记为线索，不得进入 I2 的核心依据。

## 6. I2：创新构思 Agent

I2 分两阶段接收输入：

- I2-A 只读取 `00_brief.md`、当前权利要求和说明书、本地代码、实验及在先申请特征表，不得读取论文卡片；
- I2-B 再读取 I2-A 的隔离构思结果和 I1 通过 G1 的论文卡片。

### 6.1 构思规则

I2 采用两段式构思，防止读完论文后直接排列组合：

1. **隔离构思**：I2-A 只读取项目失败证据、当前权项、代码和实验边界，提出项目自身需要的状态量、控制规则或数据结构，输出 `02a_isolated_mechanisms.md`；
2. **论文校准**：再读取 I1 的机制卡片，判断隔离构思是否已公开，并仅吸收可迁移原理，不复制论文流程。

候选不能是论文机制的名称替换，也不能是多个模块的串联。至少要写清：

- 论文提供的可迁移原理；
- 当前系统独有的约束或数据结构；
- 迁移后发生了什么机制变化；
- 三个以上步骤之间的数据依赖或控制依赖；
- 可由说明书公开的实施路径；
- 可测量但不虚构的技术效果。

每个候选还必须通过：

- **单因果核测试**：存在一个贯穿流程的状态变量、反馈信号或控制约束；
- **删除测试**：删除任一必要特征后，目标因果链被破坏，而不仅是一般性能下降；
- **组合动机测试**：说明本领域技术人员为何不能仅依据两篇论文自然组合得到；
- **等价替换测试**：模块被常规模型、阈值或检索器替换后，核心机制是否仍然完全不变；若不变，说明该模块不应作为创新核心。

### 6.2 候选卡片

I2 输出 `02_candidate_cards.md`，每个候选使用：

```yaml
candidate_id: I-01
name:
status: DRAFT
source_papers: [PAPER-001]
technical_problem:
current_baseline_failure:
core_data_structure:
essential_features:
  - F1
  - F2
  - F3
processing_flow:
  - S1
  - S2
  - S3
feature_coupling:
input_output_contract:
local_original_support:
code_support:
experiment_support:
expected_technical_effect:
unsupported_effects:
difference_from_source_papers:
difference_from_self_prior_application:
independent_claim_skeleton:
dependent_claim_fallbacks:
implementation_difficulty:
known_risks:
```

### 6.3 G2 门禁

以下任一情况直接退回 I2：

- 没有本地原始支持；
- 只有场景替换，例如“把图像方法用于广告视频”；
- 只有阈值、权重、Prompt 或模型名称变化；
- 没有核心数据结构或步骤间依赖；
- 技术效果无法由机制合理推出；
- 与自家在先申请的核心特征重合且没有新增耦合关系；
- 把计划实现写成已经实现。

## 7. I3：候选门禁 Agent

I3 采用敌对审查员立场，先找淘汰理由，再评分。I3 不进行外部专利检索，避免与 I4 职责混淆。

### 7.1 硬淘汰项

出现任一项则直接 `REJECT`：

1. 无本地原始公开或技术实现支撑；
2. 属于业务规则、内容规则或人工判断规则；
3. 仅为公知模块并列，没有输入输出互锁；
4. 论文机制直接照搬，仅更换应用对象；
5. 唯一区别是参数范围、阈值或模型型号；
6. 所声称效果依赖不存在或失败的实验；
7. 与自家在先申请实质相同；
8. 无法写成清楚、可执行的技术步骤。

### 7.2 评分

| 维度 | 分值 |
|---|---:|
| 技术问题具体性 | 10 |
| 核心机制与数据流清晰度 | 15 |
| 特征之间的非平凡耦合 | 20 |
| 本地原始支持 | 15 |
| 技术效果和实验支撑 | 15 |
| 代码实现可行性 | 10 |
| 权利要求可表达性 | 15 |
| 总分 | 100 |

裁决：

- `>= 80`：进入 I4；
- `70–79`：允许 I2 定向修订一次；
- `< 70`：淘汰；
- 即使总分达标，只要触发硬淘汰项仍然淘汰。
进入 I4 还必须同时满足单项最低分：

| 维度 | 最低分 |
|---|---:|
| 技术问题具体性 | 6/10 |
| 核心机制与数据流清晰度 | 9/15 |
| 特征之间的非平凡耦合 | 14/20 |
| 本地原始支持 | 10/15 |
| 技术效果和实验支撑 | 9/15 |
| 代码实现可行性 | 6/10 |
| 权利要求可表达性 | 9/15 |

总分达标但任一单项未达最低分时，裁决仍为 `REVISE`。I3 必须给出一个最可能击穿候选的“主对比文件骨架 + 第二文献区别特征”的组合路径，供 I4 定向检索。

I3 输出 `03_candidate_gate.md`：

```yaml
candidate_id:
hard_failures: []
score:
strongest_attack:
weakest_evidence:
required_revision:
decision: PASS_TO_PATENT_SEARCH | REVISE | REJECT
```

进入 I4 的候选最多四个。

## 8. I4：专利检索 Agent

I4 只检索通过 I3 的冻结候选版本，不接受候选名称作为唯一检索词。

### 8.1 检索展开

对每个必要特征生成：

- 中文同义词；
- 英文同义词；
- 上位概念和下位实现；
- 输入对象、处理动作、控制条件和输出结果；
- IPC/CPC 分类；
- 申请人、发明人、引用和被引用专利；
- 自家在先申请和同族。

执行三层检索：

1. 单特征检索：确认每个特征是否公知；
2. 双特征共现检索：寻找最可能的主对比文件；
3. 完整组合检索：寻找覆盖必要特征及其关系的单篇文献。

### 8.2 专利命中卡片

I4 输出 `04_patent_search_report.md` 和 `04_sources_patents.jsonl`：

```yaml
patent_id:
publication_number:
title:
jurisdiction:
priority_date:
filing_date:
publication_date:
legal_status:
family_members:
verified_url:
relevant_claims_or_paragraphs:
covered_features:
missing_features:
same_purpose:
combination_motivation:
date_eligible_as_prior_art:
```

### 8.3 风险裁决

| 情形 | 风险 |
|---|---|
| 单篇在先文献覆盖全部必要特征及其关系 | 极高，原则上淘汰 |
| 主文献覆盖骨架，另一文献给出明确组合启示 | 高，需重构 |
| 多篇分别公开特征，但缺少组合动机或技术目的不同 | 中 |
| 仅概念相似，数据结构、控制关系和效果均不同 | 中低 |
| 未检到接近组合，但检索覆盖不足 | 不确定，不得写低风险 |

I4 必须检查公开日是否早于本申请关键日期，并记录法律状态。法律状态不决定是否构成现有技术，但用于评估权利稳定性和商业风险。

## 9. 回退与版本规则

如果 I4 发现高风险文献：

1. I4 只输出“被覆盖特征”和“尚未覆盖差异”，不得替 I2 发明新方案；
2. I0 将差异约束发送给 I2；
3. I2 生成 `I-XX-v2`，不得覆盖旧候选；
4. I3 重新执行完整门禁；
5. I4 只对新增或改变的必要特征执行增量检索；
6. 最多两轮，仍为高风险则淘汰。

禁止通过不断增加无关限定来规避现有技术。

## 10. I5：最终评审 Agent

I5 读取全部产物，但不读取 I2 的主观“推荐等级”，以减少锚定偏差。

I5 对每个候选输出：

```yaml
candidate_id:
paper_distance: LOW | MEDIUM | HIGH
patent_distance: LOW | MEDIUM | HIGH | UNKNOWN
original_support: E0 | E1 | E2 | E3 | E4
implementation_status: NOT_STARTED | PARTIAL | IMPLEMENTED | VERIFIED
single_reference_risk:
combination_risk:
section_26_support_risk:
inventive_step_argument:
best_examiner_attack:
recommended_use:
  INDEPENDENT_CLAIM |
  DEPENDENT_CLAIM |
  CONTINUATION_APPLICATION |
  EXPERIMENT_FIRST |
  PAPER_ONLY |
  REJECT
required_actions:
final_decision: KEEP | MODIFY | REJECT
```

证据等级：

- `E0`：仅有想法；
- `E1`：只有外部论文启发；
- `E2`：本地技术材料明确支持；
- `E3`：已有代码或可复现实验链；
- `E4`：已有冻结正向实验结果。

独立权利要求候选至少达到 E2。涉及量化效果的主张必须达到 E4，否则只能写合理预期效果或列为待验证。

I5 不采用简单平均投票。以下门禁优先于总分：

- 单篇现有技术覆盖；
- 原始支持不足；
- 公开时间不利；
- 技术效果证据错误；
- 无法实施；
- 与自家在先申请重复。

## 11. I0：最终输出

I0 输出 `05_final_board.md` 和 `06_claim_strategy.md`：

1. 最终保留、修改和淘汰候选；
2. 每个结论的论文证据、专利证据和本地证据路径；
3. 推荐独权核心特征；
4. 从属权利要求降落点；
5. 最强组合驳回路径；
6. 可用的创造性抗辩逻辑；
7. 必须补做的代码、实验、查新或说明书公开；
8. 需代理人确认的法律问题；
9. 公开披露与申请时间风险。

最终标级只能使用：

- 候选方向；
- 修订后候选；
- 建议从属保护；
- 建议补实验后再评；
- 不建议主张；
- 需代理人复核。

禁止使用“保证授权”“一定具备创造性”。

## 12. 运行目录与审计

```text
runs/patent-innovation-YYYYMMDD-rXX/
  00_brief.md
  01_paper_cards.md
  01_sources_papers.jsonl
  02a_isolated_mechanisms.md
  02_candidate_cards.md
  03_candidate_gate.md
  04_patent_search_report.md
  04_sources_patents.jsonl
  05_final_board.md
  06_claim_strategy.md
  gates.yaml
  receipts.jsonl
  artifacts.md
```

`receipts.jsonl` 每一步追加一条记录：

```json
{
  "stage": "I3",
  "input_files": ["02_candidate_cards.md"],
  "input_sha256": {},
  "output_files": ["03_candidate_gate.md"],
  "output_sha256": {},
  "decision": "PASS",
  "timestamp": ""
}
```

任何 Agent 不得覆盖其他 Agent 的产物。所有外部来源必须同时进入对应的 `sources_*.jsonl`。

## 13. 首轮建议配置

针对当前视频问答专利，首轮建议：

```yaml
objective: 找到2至4个能够提高广告视频理解精度、且不属于简单模块拼接的耦合创新点
baseline_to_beat:
  - 声明级验证器识别初答的视频证据支持风险
  - 风险触发后获取新的视频内证据
  - 候选不以初答为改写对象，而基于增强证据独立生成
  - 同一验证器按同一协议评价初答与候选
  - 候选不满足采纳条件时回退初答
candidate_may_replace_baseline: true
candidate_classification:
  - CURRENT_APPLICATION_ENHANCEMENT
  - NEW_APPLICATION
  - DEPENDENT_CLAIM_ONLY
  - EXPERIMENT_FIRST
  - REJECT
paper_window: 2026年正式会议/期刊论文，以及2026年首次公开的预印本
research_pool_year_policy: VENUE_2026_OR_FIRST_PUBLIC_2026
prior_art_date_policy: EARLIEST_PUBLIC_DATE
recall_records_target: 800
recall_records_soft_cap: 1200
abstract_screened_target: 300
full_text_verified_target: 120
full_text_verified_soft_cap: 180
final_R1_R2_mechanism_families_target: 60至90
max_candidates: 8
max_survivors_before_patent_search: 4
focus:
  - 图像理解、图像问答、DocVQA与视觉grounding
  - 目标检测、OCR、细粒度识别与证据区域提取
  - 视频问答、长视频理解与时序定位
  - 多模态大模型、视频语言模型与跨模态对齐
  - 多模态Agent、工具调用、规划与状态机
  - 声明级视频证据验证
  - 决定性证据最小破坏
  - 主动补看与风险选择
  - 不确定性、校准、选择性预测与拒答
  - 反事实学习、困难负例、对比与排序训练
  - 视觉Token压缩、动态分辨率与预算感知推理
  - 证据状态机和可审计回执
  - 候选答案比较与保守回退
exclude_as_core:
  - 单纯MMR选帧
  - 单纯多尺度裁剪
  - 单纯LoRA
  - 单纯阈值加margin
  - 仅广告场景限定
```

第一轮结束的成功标准不是“产出八个创新点”，而是：

- 至少淘汰一半候选；
- 最终保留不超过三个；
- 每个幸存候选都有明确现有技术差异；
- 每个幸存候选都有本地原始支持或明确补强任务；
- 能写出一条独权骨架和至少三条从属降落路径。

## 14. Overnight 无人值守模式

夜间运行必须在 `00_brief.md` 中写明绝对截止时间，并创建 `status.yaml`。默认策略是“保留可审计的部分结果”，不得为了完成全部阶段而降低门禁。

### 14.1 时间盒与并发

| 阶段 | 时间盒 | 最大并发 |
|---|---:|---:|
| I0 初始化 | 20分钟 | 1 |
| I1论文检索 + I2-A隔离构思 | 150分钟 | 3 |
| I2-B候选成形 | 60分钟 | 2 |
| I3候选门禁 | 40分钟 | 2 |
| I4专利检索 | 150分钟 | 2 |
| I5总评审 | 40分钟 | 1 |

任何新任务不得在绝对截止时间前30分钟启动；最后30分钟只允许收口、校验和写Receipt。

### 14.2 外部访问预算

```yaml
paper_search_queries_max: 72
paper_full_text_fetches_max: 180
paper_recall_records_target: 800
paper_recall_records_soft_cap: 1200
paper_abstract_screened_target: 300
paper_verified_families_target: 120
paper_verified_families_soft_cap: 180
exa_queries_max: 18
exa_results_per_query: 100
exa_cost_hard_cap_usd: 2.00
patent_search_queries_max: 20
patent_full_text_fetches_max: 30
patent_candidates_max: 4
```

优先复用本地已核验材料和既有来源清单。除I0明确授权且设有费用硬上限的Exa外，禁止其他付费API、登录后资源、验证码绕过和外部写操作。单一检索通道预算耗尽时，切换到替代源继续执行；所有可用通道均耗尽时，以 `coverage=PARTIAL` 收口，不得把“未检到”写成“没有现有技术”。

### 14.3 状态机与恢复

`status.yaml` 中每个阶段只能处于：

```text
PENDING | RUNNING | COMPLETE | PARTIAL | FAILED | SKIPPED
```

恢复时：

1. 校验上游输出文件存在且SHA256与最近Receipt一致；
2. `COMPLETE`阶段不得重跑；
3. `RUNNING`但无有效输出的阶段重置为`PENDING`；
4. 有部分有效输出时标记`PARTIAL`并从未完成项继续；
5. 同一外部访问连续失败三次后停止重试，改用本地材料并标记覆盖不足。

### 14.4 故障自愈与替代通道

无人值守运行不得因单一工具失败而暂停。每次故障写入`receipts.jsonl`，按下表处理：

| 故障 | 自动处理 | 替代通道 |
|---|---|---|
| 超时、连接重置、HTTP 5xx | 指数退避重试3次：2秒、8秒、30秒 | 切换同一论文的其他官方入口、arXiv或缓存 |
| HTTP 429限流 | 遵循`Retry-After`；无该字段时等待30秒、120秒后重试 | OpenAlex→Crossref→DBLP→arXiv API→WebSearch |
| Exa费用达到硬上限或额度耗尽 | 停止新增Exa请求，不重复消耗 | 使用已返回的Exa池，与OpenAlex/arXiv池合并后继续摘要筛选和官方全文核验 |
| Exa认证失败 | 去敏诊断1次；仍失败则禁用Exa | 不影响元数据、WebSearch和官方正文通道 |
| 正文页面403、404或机器人校验 | 依次尝试会议HTML、arXiv HTML/PDF、作者仓库、DOI落地页 | 仍失败则标记`FULL_TEXT_UNAVAILABLE`，不得冒充全文核验 |
| 解析器失败 | 保存原始非敏感响应摘要，换备用解析器重试2次 | 降级为元数据/标题/摘要记录 |
| 子Agent失败或无产物 | 原任务重试1次；再次失败则缩小任务重新派发 | I0根据已有部分产物继续后续阶段 |
| 输出格式或Schema失败 | 先做机械修复，再重新执行门禁 | 无法修复则标记`PARTIAL`，不得阻塞其他候选 |
| 专利数据库不可用 | 重试并切换Google Patents、WIPO、Espacenet或官方数据库 | 日期/法律状态无法核验时风险标记`UNKNOWN` |

自愈原则：

1. 先判断是否为瞬态、认证、配额、参数或内容问题，不盲目重复同一请求；
2. 同一失败最多三次，之后必须改变参数、入口或数据源；
3. 阶段失败只影响对应覆盖度，不得删除已通过哈希核验的产物；
4. I1部分失败不阻止I2-A；I4部分失败不阻止I5输出`UNKNOWN/PARTIAL`结论；
5. 仅当所有本地与替代通道均不可用且无法生成任何审计产物时，才允许标记Goal受阻。

### 14.5 夜间安全边界

- 不修改现有正式申请稿、V2.1基准稿及其Word文件；
- 启动前和结束后核验上述文件SHA256；
- 不执行Git提交、推送、删除、覆盖或分支切换；
- 不运行GPU训练、批量模型推理和付费LLM评测；
- 不把计划实现写成已经实现；
- 不因候选数量不足而降低80分门禁或单项最低分。

### 14.6 停止与降级

满足任一条件即停止扩张并进入收口：

- 达到绝对截止时间；
- 已有三个候选通过I4；
- 论文机制连续两轮检索无新增R1/R2机制簇；
- 专利检索连续两轮无新增高相关专利族；
- 所有候选均触发硬淘汰项；
- 外部网络连续失败三次。

最终允许零个候选通过。零候选是有效结论，I5仍须说明淘汰原因、最接近现有技术和下一轮需要改变的核心机制。
