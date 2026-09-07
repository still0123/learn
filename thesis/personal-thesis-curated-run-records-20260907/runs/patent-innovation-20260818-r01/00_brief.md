# I0 Overnight 任务合同

```yaml
round_id: patent-innovation-20260818-r01
mode: overnight_unattended
started_at: 2026-08-18T00:40:08+08:00
hard_deadline: 2026-08-18T08:00:00+08:00
closeout_only_after: 2026-08-18T07:30:00+08:00
target_application: 一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质
objective: 找到不依赖简单模块拼接、比“低支持触发补看+门控回退”更强的耦合创新候选，并完成论文证据、专利现有技术、实施支持与权项用途的闭环评审
technical_domain: 计算机视觉、图像/视频理解、图像/视频问答、多模态大模型、证据可靠性与预算感知推理
paper_window: 2026年正式会议/期刊论文，以及2026年首次公开的预印本
research_pool_year_policy: VENUE_2026_OR_FIRST_PUBLIC_2026
prior_art_date_policy: EARLIEST_PUBLIC_DATE
patent_cutoff_date: 2026-08-18
jurisdictions: [CN, WO, US, EP]
max_candidates: 8
max_survivors_before_patent_search: 4
max_final_candidates: 3
max_revision_rounds: 2
max_parallel_agents: 3
paper_search_queries_max: 72
paper_full_text_fetches_max: 180
paper_recall_records_target: 800
paper_recall_records_soft_cap: 1200
paper_abstract_screened_target: 300
paper_verified_families_target: 120
paper_verified_families_soft_cap: 180
paper_final_R1_R2_mechanism_families_target: 60至90
patent_search_queries_max: 20
patent_full_text_fetches_max: 30
exa_enabled: true
exa_role: semantic_recall_and_rerank_only
exa_queries_max: 18
exa_results_per_query: 100
exa_cost_hard_cap_usd: 2.00
exa_secret_source: transient_user_authorization
external_write_allowed: false
paid_api_allowed: exa_only_with_cost_cap
git_commit_allowed: false
git_push_allowed: false
gpu_training_allowed: false
formal_application_edit_allowed: false
```

## 输入真源

- `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md`
- `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/新申请初稿V2.1_说明书全文_20260817.md`
- `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/audit/`
- `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/prior-art/`
- `/Users/bytedance/vqa_thesis_continue/docs/论文思考记录.md`
- `/Users/bytedance/vqa_thesis_continue/docs/完整论文_题目不变_证据选择与主动补看版_20260817.md`
- `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md`
- `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/evaluation/`
- `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/code_refactor/`

## 正式稿完整性基线

| 文件 | SHA256 |
|---|---|
| `新申请初稿V2.1_说明书全文_20260817.md` | `1e980b4a7dcc87ead5a368d0523f65da8a94318a21d1dee1a9bde019d8d04c7b` |
| `一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md` | `224e09e6c3de3e2ca5ae5d1f3726fc266d4c06bbf4f1536340b6bb2d884bb2fa` |
| `一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.docx` | `844a947527b8921e7258966a3ebe7b36967d41ac767296773f2c7af1f8205e2f` |

## 当前独权原子特征

- F1：从视频和问题构建初始证据并生成初始答案；
- F2：将答案拆解为原子声明并聚合声明支持度；
- F3：初始答案低支持时获取新的时间或区域证据；
- F4：不以初始答案为改写对象，基于增强证据独立生成候选；
- F5：同一验证器按同一协议对初答和候选评分；
- F6：绝对阈值与相对裕量共同控制替换；
- F7：条件失败时回退初始答案；
- F8：正反声明监督训练验证器；
- F9：真实视频决定性证据最小破坏与排序约束。

## 当前基线与允许改变范围

当前需要被比较和超越的基线方案为：

```text
初始视频证据E0生成初答A0
→ 声明级验证器发现A0的证据支持风险
→ 获取新的视频内证据ΔE
→ 不以A0为改写对象，基于E0∪ΔE独立生成候选A2
→ 同一验证器按同一评分协议评价A0与A2
→ 候选满足采纳条件则替换，否则回退A0
```

该闭环不是不可变核心。候选可以修改或完全替换其任意步骤，只要满足：

- 目标仍是提升广告视频理解、问答或证据可靠性的可测技术指标；
- 技术机制明确利用广告视频的至少一种可计算特性：信息密集、短时文字或Logo、细粒度产品细节、声画异步、重复营销元素、快速镜头切换或多模态证据冲突；
- 相对于当前基线给出可复现的输入、状态、处理、输出和对照实验；
- 不以营销分类、受众画像或内容规则本身作为创造性核心；
- 不以模型名称、Prompt、阈值、权重或数据集替换作为唯一区别。

候选最终按关系分类：

- `CURRENT_APPLICATION_ENHANCEMENT`：可在当前申请框架内增强；
- `NEW_APPLICATION`：核心机制替换现有闭环，建议另起新申请；
- `DEPENDENT_CLAIM_ONLY`：只适合从属限定；
- `EXPERIMENT_FIRST`：先验证后决定；
- `REJECT`：不建议专利化。

## 自家在先公开与排除项

- 三流热力图、时序滑动窗口、响应密度多尺度锚框、全局/局部双流已经由在先申请公开；
- MMR、普通阈值、LoRA、普通视觉裁剪、普通RAG、CoT、自我反思不得作为核心创新；
- 仅广告场景限定、模型名称替换、Prompt变化、参数范围变化直接淘汰。

## 证据边界

- Exa仅用于论文语义补召回、highlights提取和候选重排，不用于直接形成创新结论；
- Exa结果必须回到DOI/arXiv、正式venue和官方正文核验，才能升级为全文已验证论文；
- Exa密钥不得写入本目录、日志、Receipt、脚本或Git；只允许作为本轮瞬时认证信息；
- 正式会议或期刊发表年份为2026的论文可进入I1论文池，包括2025年预印本、2026年正式发表的版本；
- 仅有预印本时，必须在2026年首次公开才能进入I1论文池；
- 每篇论文必须同时记录2026论文池资格和最早公开日期，后者用于专利现有技术时间判断；
- 2026年以前论文可以作为背景附录，但不得进入I2候选的`source_papers`；
- `0.5409→0.6599`只归因于真实正反声明分类训练，不归因于反事实排序训练；
- Full-7844 `+7.00/+10.12pp`只支撑支持度触发、证据补看和独立候选生成的联合效果；
- E-VAds `28胜0负`支撑绝对阈值与相对裕量双条件门控；
- 反事实排序训练是候选/从属机制，不得挂接`0.6599`；
- 未执行、失败或仅计划的机制不得表述为已实现。

## 夜间停止条件

- 达到硬截止时间；
- 三个候选通过I4；
- 所有候选被硬淘汰；
- 外部网络连续失败三次；
- 查询或全文抓取预算耗尽。

零候选通过视为有效结果，不得为凑数放宽门禁。
