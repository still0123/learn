# Overnight Goal V2：广告视频理解专利创新多 Agent 闭环

## 目标

无人值守运行广告视频理解专利创新多 Agent 工作流一晚，从2026年正式发表论文和2026年首次公开预印本中，寻找能够提高广告视频理解、视频问答准确率或证据可靠性的技术机制，并完成论文核验、隔离构思、候选门禁、专利查新和最终权项策略。

当前“证据触发补看→独立重答→同口径验证→保守回退”只作为基线。候选可以增强或完全替换该流程。

## 运行与恢复

- 运行目录：`/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01`
- 工作流规范：`/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/MULTI_AGENT_INNOVATION_WORKFLOW.md`
- 若运行目录已存在，读取`status.yaml`和`receipts.jsonl`断点续跑；
- 已标记`COMPLETE`且SHA256一致的阶段不得重跑；
- 绝对截止时间为`2026-08-18T08:00:00+08:00`；
- `07:30`后只允许校验、汇总和写Receipt，不得启动新检索。

## 研究边界

候选必须满足：

1. 提高广告视频理解、问答精度、证据召回、事实可靠性或精度－成本前沿中的至少一项可测指标；
2. 明确利用广告视频至少一种可计算特性：
   - 短时字幕、价格、Logo或免责声明；
   - 细粒度产品属性；
   - 声画异步；
   - 快速镜头切换；
   - 重复营销元素；
   - 广告叙事阶段；
   - 多模态证据冲突；
3. 给出输入、中间状态、处理操作、输出和删除测试；
4. 不把营销规则、模型名称、Prompt、阈值或数据集替换作为唯一创新；
5. 不编造实验、代码实现、论文、专利或法律状态。

候选分类：

- `CURRENT_APPLICATION_ENHANCEMENT`
- `NEW_APPLICATION`
- `DEPENDENT_CLAIM_ONLY`
- `EXPERIMENT_FIRST`
- `REJECT`

## 论文范围

允许进入2026论文池：

- 2026年正式会议或期刊论文；
- 2025年预印本但在2026年正式会议或期刊发表的论文；
- 2026年首次公开且尚未正式发表的预印本。

每篇论文必须同时记录：

- `research_pool_eligible`
- `formal_venue_year`
- `earliest_public_date`
- `prior_art_date`
- DOI或arXiv
- 官方正文URL
- 正文证据位置

最早公开日期用于专利现有技术判断，不能因2026正式发表而覆盖2025预印本日期。

## 检索范围

### A层：直接任务

- 视频/图像问答、长视频理解、DocVQA、图表问答；
- 时序定位、动作识别、主动视觉、二次观察、视觉工具调用。

### B层：计算机视觉

- 检测、分割、OCR、Logo、小目标与细粒度识别；
- 高分辨率理解、视觉Grounding、显著性/CAM；
- 跟踪、跨帧关联、场景图、视觉蕴含和跨模态检索。

### C层：多模态大模型

- VLM、VideoLLM、图文/视听对齐；
- 视觉Token化、多图多帧、长上下文；
- Grounded推理、多模态RAG、视觉Agent、规划、记忆和状态机；
- 多模态微调、偏好优化和强化学习。

### D层：可靠性与系统

- 幻觉检测、声明事实验证和证据归因；
- 不确定性、校准、选择性预测、拒答和风险覆盖；
- 候选排序、验证器－生成器、反事实、困难负例和排序训练；
- Token压缩、动态分辨率、路由、早退、预算与审计轨迹。

## 检索漏斗

```yaml
metadata_recall_target: 800
metadata_recall_soft_cap: 1200
abstract_screen_target: 300
full_text_verified_target: 120
full_text_verified_soft_cap: 180
final_R1_R2_mechanism_families_target: 60至90
max_candidates: 8
max_patent_search_candidates: 4
max_final_candidates: 3
```

## 检索通道编排

### I1-M：批量元数据

使用OpenAlex、Crossref、DBLP和arXiv API做批量召回、日期、作者、venue、DOI和论文族归一。

### I1-X：Exa语义补召回

Exa仅用于：

- 发现术语不同但机制相近的论文；
- 机制簇语义补召回；
- 对元数据池进行相关性重排；
- 提取与查询相关的highlights。

配置：

```yaml
category: publication
type: auto
numResults: 100
queries_max: 18
cost_hard_cap_usd: 2.00
```

密钥只使用用户提供的瞬时认证信息：

- 不写入任何文件、脚本、环境配置、Receipt或Git；
- 不回显密钥；
- 只记录查询簇、结果数、错误码和费用；
- 达到费用上限后立即熔断，不再调用Exa。

### I1-V：官方正文核验

Exa highlights、标题和摘要都不能标记为全文核验。必须回到会议官网、期刊页、arXiv HTML/PDF或作者官方仓库。

## Agent流程

1. `I0`：冻结任务、预算、正式稿SHA256和证据边界；
2. `I1-M/I1-X`：并行召回与重排；
3. `I2-A`：不读取论文，从本地失败证据独立构思；
4. `I1-V`：对筛选论文做正文核验和机制卡片；
5. `I2-B`：结合隔离机制与已核验论文，生成最多8个候选；
6. `I3`：敌对门禁，80分且各维度达最低分才进入专利检索；
7. `I4`：对最多4个候选检索CN、WO、US、EP专利；
8. `I5`：最终评审，保留不超过3个候选；
9. `I0`：生成权利要求布局、实验待办、风险清单和Receipt。

## 故障重试与自动降级

不得因单一API、网页、解析器或子Agent失败而暂停。

| 故障 | 重试 | 降级方案 |
|---|---|---|
| 超时、连接重置、5xx | 2秒、8秒、30秒，最多3次 | 切换官方HTML、arXiv、作者仓库或缓存 |
| 429 | 遵循Retry-After；否则30秒、120秒 | OpenAlex→Crossref→DBLP→arXiv→WebSearch |
| Exa额度或费用上限 | 不继续消耗 | 使用已返回Exa池＋元数据池继续摘要和正文核验 |
| Exa认证失败 | 去敏诊断1次 | 禁用Exa，其他通道继续 |
| 正文403/404 | 切换4类入口 | 标记`FULL_TEXT_UNAVAILABLE`，不得冒充全文核验 |
| 解析失败 | 换解析器重试2次 | 降级为元数据/摘要记录 |
| 子Agent失败 | 原任务重试1次 | 缩小任务重派；仍失败则以PARTIAL继续 |
| Schema失败 | 机械修复并重验 | 无法修复则标记PARTIAL |
| 专利库不可用 | 切换Google Patents/WIPO/Espacenet/CNIPA | 无法核验字段标记UNKNOWN |

规则：

1. 同一失败最多三次，随后必须改变参数、入口或数据源；
2. 失败只降低对应覆盖度，不删除已有产物；
3. `I1`部分失败不阻止`I2-A`；
4. `I4`部分失败不阻止`I5`输出`UNKNOWN/PARTIAL`；
5. 只有所有本地和替代通道均不可用，且无法生成任何审计产物时，才允许标记Goal受阻。

## 候选硬门禁

出现任一项直接淘汰：

- 无本地支持；
- 只有场景替换；
- 只有模型、Prompt、阈值、权重或Top-K变化；
- 模块并列，没有共同状态量或控制关系；
- 论文机制直接照搬；
- 效果依赖失败或不存在的实验；
- 与自家在先申请实质重复；
- 无法写成可执行技术步骤。

进入专利检索还须：

- 总分至少80；
- 技术问题至少6/10；
- 数据流至少9/15；
- 非平凡耦合至少14/20；
- 本地支持至少10/15；
- 技术效果至少9/15；
- 实现可行性至少6/10；
- 权项表达至少9/15。

## 专利查新要求

对每个幸存候选：

- 拆成原子必要特征和关系链；
- 检索单特征、双特征共现和完整组合；
- 核验权利要求/说明书段落；
- 检查最早优先权日、申请日、公开日、同族和法律状态；
- 分析单篇覆盖和两篇组合动机；
- 法律状态或日期无法核验时标记`UNKNOWN`；
- “未检到”只能表示本轮覆盖范围内未检出。

## 安全边界

- 不修改正式申请稿、V2.1和Word文件；
- 开始与结束时核验SHA256；
- 不提交、不推送、不删除、不覆盖；
- 不运行GPU训练和付费LLM评测；
- 除已授权且受费用上限约束的Exa外，不使用其他付费API；
- 计划机制不得表述为已实现；
- 允许最终零候选，不得为凑数降低门禁。

## 必须产物

- `01_paper_cards.md`
- `01_sources_papers.jsonl`
- `02a_isolated_mechanisms.md`
- `02_candidate_cards.md`
- `03_candidate_gate.md`
- `04_patent_search_report.md`
- `04_sources_patents.jsonl`
- `05_final_board.md`
- `06_claim_strategy.md`
- `gates.yaml`
- `receipts.jsonl`
- `artifacts.md`

## 完成条件

最终报告必须包含：

- 保留、修改和淘汰候选；
- 最接近论文与专利；
- 单篇覆盖与组合驳回风险；
- 本地代码、实验和说明书支持；
- 当前申请增强与新申请候选的区分；
- 独权骨架和从属降落点；
- 必须补做的代码、实验和正式查新；
- 公开时间风险和代理人复核事项；
- 全部阶段Receipt及正式稿SHA256复核。

除非用户明确停止，否则持续执行至截止时间或完成全部阶段，不因可恢复错误中途询问用户。
