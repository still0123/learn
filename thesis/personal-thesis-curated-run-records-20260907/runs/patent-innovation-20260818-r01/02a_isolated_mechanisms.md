# I2-A 隔离构思：由本地失败证据反推的所需机制

## 0. 定位与边界

- 本文件仅列“所需机制”，用于解释当前“低支持触发补看 + 门控回退”仍未解决的失败。
- 下列内容不是专利候选定稿，不构成新颖性、创造性、可实施性或效果结论。
- 证据仅来自本地正式申请稿、代码、冻结实验记录和负结果；未进行外部检索。
- 未读取任何 `01*_paper_cards`、prior-art 论文清单或 `patent-innovation-analysis` Skill。
- 当前正式方案已经覆盖：初答原子声明评分、低支持触发、一次补看、独立候选、同验证器评分、阈值/裕量门控和失败回退。以下机制必须解决其外部剩余问题，而不是改写这些已有步骤。

## 1. 失败簇摘要

| failure_id | 冻结失败 |
|---|---|
| `I2A-F01` | 从 QA 答案抽出的宽泛声明并非当前证据下的可靠正例；固定协议 Smoke20 仅 `2/20`。 |
| `I2A-F02` | 广告内同一品牌、人物、场景、文字和 CTA 重复出现，排除锚点或局部遮挡后事实仍在，Candidate A/B 仅 `0/20`、`8/20`。 |
| `I2A-F03` | 显式缺失状态被 ASR 简单任务主导，跨模态总体分数失真；Candidate C 为 ASR `7/7`、OCR `4/7`、视觉 `3/6`。 |
| `I2A-F04` | OCR 像素确已删除，但冻结模型的连续支持似然对删除没有稳定方向；Candidate D 为 ASR `10/10`、OCR `5/10`。 |
| `I2A-F05` | “证据存在/声明受支持”不能独立证明候选答案正确，Candidate E 无泄漏选举前置条件失败。 |
| `I2A-F06` | 主动补看动作未稳定优于随机/整帧；TIME 子集净增益为零，区域门控跨分区失效。 |
| `I2A-F07` | 全文候选大量改写却没有可辨认增益；Qwen2.5 中 461 个不同候选仅 7 gain、442 tie、12 harm，456 个支持度差落在 `[0,0.03)`。 |
| `I2A-F08` | 整体正向结果仍含大量伤害且成本高：Full-7844 相对 MMR 有 896 负、604 次 right-to-wrong，触发率 `91.45%`。 |
| `I2A-F09` | 同模型成对选举存在顺序冲突，保守双顺序规则仍得到 `0胜/2负`。 |
| `I2A-F10` | AV 门控可能退化为纯 CLIP：旧 OOF 仅触发 7 题，7 题均无 ASR/OCR，AV 与 CLIP 计划及答案完全相同。 |

---

## 2. 所需机制 M1：声明义务图与关键叶节点触发

- **failure_id：** `I2A-F01`、`I2A-F05`、`I2A-F08`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md:15-20`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:4480-4510`
  - `/Users/bytedance/vqa_thesis_continue/code_refactor/reflection/claim_checker.py:18-42`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md:223-233`
- **失败现象：** 答案级均值或单一支持分数不能区分“一个关键事实缺证”与“多个非关键描述较弱”；宽泛声明还可能不是当前证据可证实的命题。低支持触发能决定“再看”，但不能指出哪个决定答案正确性的最小义务尚未闭合。
- **根因假设：** 当前声明拆解缺少逻辑关系、重要性和可证实性约束。声明列表是平面集合，不是带 `AND/OR/SEQ`、答案依赖关系和关键叶节点的义务图。
- **所需状态量或数据结构：**
  - `ClaimObligationGraph`：问题根节点、答案原子声明节点、证据义务叶节点；
  - 每个叶节点记录 `required_modality`、`time_relation`、`anchor_set`、`state={supported,refuted,not_detected,unavailable}`、`criticality`；
  - `closure_mask` 与 `unresolved_critical_leaf_ids`。
- **控制规则：** 仅当所有关键叶节点按逻辑算子闭合时，答案才可被视为可采纳；任一关键叶节点为 `refuted` 时禁止采纳；`not_detected` 才允许定向补看；`unavailable` 不得被当作低支持或反驳。
- **最小处理链：** 问题与 A0 → 拆解答案原子声明 → 构建义务图 → 逐叶绑定证据与状态 → 计算关键未闭合叶 → 将叶节点而非答案均值交给补看控制器。
- **删除测试：** 将义务图替换为现有声明均值/最低值聚合，比较关键事实漏检率、无关叶触发率、复合答案 right-to-wrong 和触发成本。
- **现有实现状态：** **部分存在。** 正式稿已有声明拆解、均值/最低值聚合和问题逻辑树；`claim_checker.py` 仅用关键词生成平面检查计划，没有答案依赖边、关键叶、状态闭合或部署态持久化。
- **可验证指标：** 关键叶召回率、义务闭合准确率、关键叶 ECE/Brier、每次补看关闭的关键叶数量、关键叶触发后的 correction precision。
- **不可声称效果：** 未验证前不得声称该图降低错误替换、减少触发率、提高 QA，亦不得把现有 Full-7844 增益归因于该机制。

## 3. 所需机制 M2：证据副本图与“删除充分”证书

- **failure_id：** `I2A-F02`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md:15-20,28-36`
  - `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md:613-627`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_b_same_video_smoke_v1.py:109-138,199-265`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_d_formal_data_v1.py:263-311,361-376`
- **失败现象：** 排除锚点时间窗、替换完整 32 帧片段或遮挡 OCR 框后，负样本仍支持原声明；广告片尾、Logo、CTA 和重复文案构成替代证据路径。
- **根因假设：** 当前干预以“位置”为单位，没有先发现同一事实的全部时空/模态副本，因此“删除了目标框或锚点”不等于“删除了决定性事实”。
- **所需状态量或数据结构：**
  - `EvidenceOccurrenceGraph`：事实节点连接所有视觉区域、OCR 字符串、ASR span 和时间区间；
  - `equivalence_cluster_id`、`occurrence_count`、`cross_modal_paths`；
  - `residual_support_path_count` 与 `deletion_certificate`。
- **控制规则：** 只有当目标事实的所有已发现支持路径均被覆盖，且外部复验器确认残余支持低于门槛时，才把干预样本标为有效 E-；否则标记 `counterfactual_invalid`，禁止训练排序头或据此校准门控。
- **最小处理链：** 原子声明 → 全视频多模态副本检索 → 等价聚类 → 计算支持路径 → 对路径集合执行最小覆盖干预 → 独立复验残余路径 → 生成或拒绝 E-。
- **删除测试：** 去掉副本图，只对首个锚点或最高分框干预；比较 E- 中残余支持率、严格配对正确率和错误负标签率。
- **现有实现状态：** **实验性局部实现。** 代码可排除锚点段、马赛克多个 OCR 框并审计像素变化，但没有跨时刻、跨模态的事实等价聚类，也没有“全部支持路径已断开”的证书。
- **可验证指标：** 残余支持路径率、E- 外部复验通过率、每模态配对方向准确率、删除覆盖率、反事实无效率。
- **不可声称效果：** 像素变化 `500/500` 只能证明图像被改动；不得声称事实已被删除、排序监督有效或验证器因此获得 QA 增益。

## 4. 所需机制 M3：模态可用性、激活度与可辨识性账本

- **failure_id：** `I2A-F03`、`I2A-F10`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md:22-34`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:2899-2911,2943-2955`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/gate_protocol.py:286-334`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_c_missingness_smoke_v1.py:14-24,190-274`
- **失败现象：** 总体 Smoke 分数被易识别的 ASR 缺失哨兵主导；另一路 AV 实验虽名义使用视听信息，但触发样本实际没有 ASR/OCR，AV 退化为 CLIP 而未被主指标阻止。
- **根因假设：** 系统只记录“是否有字段/是否触发”，没有记录每个模态是否真实参与决策、能否与对照产生不同证据签名，以及该模态是否有可识别的因果响应。
- **所需状态量或数据结构：**
  - `ModalityLedger[claim_id][modality]`；
  - 字段含 `availability_state`、`evidence_signature`、`control_signature`、`activation_delta`、`direction_passed`、`fallback_reason`；
  - `joint_identifiable` 和 `dominant_modality`.
- **控制规则：** 联合模态机制只有在至少两个所需模态均可用、与单模态对照签名不同、且各自干预方向通过时才允许标记激活；否则自动降级为明确命名的单模态路径，不得把其结果计入联合机制证据。
- **最小处理链：** 读取模态状态 → 生成每模态证据签名 → 与冻结单模态控制比较 → 执行小干预方向检查 → 写入账本 → 决定 joint/single/fallback。
- **删除测试：** 去掉账本，只按 `asr_present`、OCR 数量或总响应阈值触发；统计名义联合但实际单模态的比例及总体指标被易模态主导的程度。
- **现有实现状态：** **部分存在。** 已有显式 ASR 缺失状态、门控摘要、视觉计划哈希和回退记录；没有统一的模态可辨识性判定，旧门控甚至允许无 ASR/OCR 时把 AV 结果计为 AV。
- **可验证指标：** 真联合激活率、AV/单模态签名差异率、每模态方向通过率、模态主导指数、降级路径准确记录率。
- **不可声称效果：** 不得把“字段存在”“门控命中”或“联合名称”表述为视听协同已发生；不得用退化为 CLIP 的结果支撑 AV 效果。

## 5. 所需机制 M4：按模态分离的单调响应验证器

- **failure_id：** `I2A-F03`、`I2A-F04`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md:28-36`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:2908-2915`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/audit_candidate_d_formal_data_v1.py:53-87,141-181`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/run_candidate_d_pairwise_logit_smoke_v1.py:239-289,441-503`
- **失败现象：** 完全相同的四状态打分接口对 ASR 删除为 `10/10`，对 OCR 删除仅 `5/10`；OCR 像素审计通过仍不能得到单调分数下降。
- **根因假设：** 一个共享输出头把“文本缺失哨兵识别”“OCR 视觉读取”“一般视觉支持”混为同一概率空间；不同模态的噪声、缺失语义和可观测性不具可比性。
- **所需状态量或数据结构：**
  - 每模态独立的 `support/refute/not_detected/unavailable` logits；
  - `MonotonicityCertificate`：E+、E-、分差、置信下界、干预类型；
  - 模态专属校准器及 `calibration_version`.
- **控制规则：** 某模态分数只有在该模态的 E+→E- 单调性下界通过冻结门槛时，才可进入声明聚合和候选门控；未通过的模态输出 `unidentifiable`，不能被其他模态的高分抵消。
- **最小处理链：** 声明模态路由 → 调用对应验证头 → 计算 E+/E- 单调差 → 校准为模态内状态 → 写入证书 → 再按声明义务图聚合。
- **删除测试：** 合并回一个共享支持概率；比较 OCR/视觉方向准确率、模态间校准偏差及错误抵消率。
- **现有实现状态：** **仅有实验原型。** 已实现模态提示、四状态 token 概率和配对分差；正式答案门控仍依赖统一支持度，没有可部署的模态专属头、证书和拒用规则。
- **可验证指标：** 每模态配对 AUROC/准确率、单调差置信下界、每模态 ECE/Brier、`unidentifiable` 覆盖率、跨模态错误抵消率。
- **不可声称效果：** ASR 分支通过不能外推 OCR/视觉；OCR `5/10` 时不得声称跨模态排序监督可用，更不得挂接现有 `0.6599` 验证器结果。

## 6. 所需机制 M5：候选答案的因果正确性证书与风险拒答

- **failure_id：** `I2A-F05`、`I2A-F08`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md:30-36`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/audit_candidate_e_precondition_v1.py:69-118`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:2917-2923`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA最终结果交付_20260731.md:205-218,244-261`
- **失败现象：** ASR/OCR 证书只能说明证据存在，不能说明候选答案正确；无参考答案、裁判分数或泄漏特征时，Candidate E 无法形成可信切换信号。现有主方法仍观察到 604 次 right-to-wrong。
- **根因假设：** “声明被当前包支持”与“候选相对初答更正确”是两个变量。现有门控比较支持度，但没有独立估计候选采纳风险，也没有在风险不可识别时输出拒答/保持。
- **所需状态量或数据结构：**
  - `AnswerEvidenceCertificate`：候选原子命题、必要证据锚点、反驳搜索结果、E+/经复验 E- 分差；
  - `risk_upper_bound`、`coverage_level`、`decision={accept_candidate,keep_initial,abstain}`；
  - 标签来源与人工/机器 provenance。
- **控制规则：** 只有证书完整、候选关键命题无反驳、模态证书均可识别且冻结风险上界不超过目标时才采纳；证书不完整时保持 A0；A0 与候选均存在关键未闭合义务时允许拒答，而不是强制二选一。
- **最小处理链：** A0/A2 原子命题对齐 → 对变化命题构造必要证据证书 → 搜索反驳与残余支持 → 模态内校准 → 计算风险上界 → 接受/保持/拒答。
- **删除测试：** 去掉证书和风险上界，恢复现有绝对阈值+支持度裕量；比较 risk-coverage、right-to-wrong、无证书替换率和拒答覆盖率。
- **现有实现状态：** **前置数据结构部分存在，部署机制不存在。** Candidate F 已生成候选答案—命题—帧/ASR/OCR 双审模板，但标签未填，`threshold_calibration_allowed=false`；正式系统没有风险上界或拒答状态。
- **可验证指标：** risk-coverage 曲线、固定覆盖下错误风险上界、right-to-wrong、证书完整率、人工双审一致性、拒答精度与覆盖率。
- **不可声称效果：** 未取得独立标注和冻结风险校准前，不得声称共形保证、安全自动纠错、拒答有效或 QA 增益。

## 7. 所需机制 M6：动作可辨识性与预期缺口闭合控制器

- **failure_id：** `I2A-F06`、`I2A-F10`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:4973-5008,5020-5028`
  - `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md:765-809`
  - `/Users/bytedance/vqa_thesis_continue/docs/方案B_多中心裁剪消融结果_20260731.md:44-56`
  - `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/gate_protocol.py:25-36,307-334`
- **失败现象：** ActiveLook、RandomLook、FullOnly 在 Confirm-100 近乎相同；TIME 子集净增益为零；区域候选有信号但门控跨分区失败；多中心裁剪不优于整帧。当前“触发后补什么”缺少动作是否真正改变证据与是否能闭合目标缺口的前置判定。
- **根因假设：** 控制器按静态规则或问题类型选动作，没有估计动作相对当前证据的新增信息、目标叶覆盖、与控制动作的可区分性及单位成本价值。
- **所需状态量或数据结构：**
  - `ActionCandidate`：`DIRECT/LOOK_TIME/LOOK_REGION/LOOK_AUDIO`；
  - 每个动作记录 `target_leaf_ids`、`novel_evidence_signature`、`expected_closure_gain`、`uncertainty`、`token_cost`；
  - `action_identifiable` 与 `control_collision`.
- **控制规则：** 仅执行与当前证据签名不同、覆盖至少一个未闭合关键叶、且预期闭合增益下界/成本为正的动作；与随机/整帧控制碰撞时不宣称专用动作被激活，并优先执行更简单控制或 DIRECT。
- **最小处理链：** 未闭合叶 → 枚举动作 → 预生成证据计划与签名 → 去除控制碰撞 → 估计闭合增益/成本 → 选择一个动作或 DIRECT → 执行后回写叶状态。
- **删除测试：** 替换为固定 `LOOK_TIME/LOOK_REGION` 映射或仅按问题类型触发；比较动作签名碰撞率、目标叶闭合率、相对随机/整帧增量和单位 Token 收益。
- **现有实现状态：** **部分存在。** 有固定规则、问题类型门控、一次动作限制、裁剪计划和 Token 审计；没有目标叶级动作收益、控制碰撞拦截或动作后闭环更新。
- **可验证指标：** 动作可辨识率、控制碰撞率、目标叶闭合率、每千 Token 闭合增益、TIME/REGION 分层 correction precision。
- **不可声称效果：** 动作轨迹合法或证据发生变化不等于动作有效；未超过随机/整帧控制前不得声称主动路由、时间补看或多中心裁剪带来收益。

## 8. 所需机制 M7：变化命题级局部合并，而非整答案替换

- **failure_id：** `I2A-F07`、`I2A-F08`、`I2A-F09`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:4466-4510,5030-5043`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA冻结结果远端核对记录_20260731.md:18-20`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA论文定稿实验结果总表_20260730.md:31-39`
  - `/Users/bytedance/vqa_thesis_continue/code_refactor/reflection/claim_checker.py:29-42`
- **失败现象：** 大量 A2 与 A0 文本不同但支持度几乎不可分，完整替换会同时改动已正确事实；直接成对选举又受候选顺序影响。Full-7844 的总体正增益仍伴随 896 个负例和 604 次 right-to-wrong。
- **根因假设：** 当前决策粒度是整答案。门控无法区分“新增证据只修正一个决定性事实”与“候选顺便改写其他已支持事实”，也没有把未变化命题锁定。
- **所需状态量或数据结构：**
  - `AnswerEditGraph`：A0/A2 命题对齐、`unchanged/added/deleted/modified` 边；
  - 每个变化命题的证据增量、反驳状态和依赖关系；
  - `protected_claim_ids`、`accepted_edit_ids`、`merge_conflict`.
- **控制规则：** 已支持且无新反驳的 A0 命题进入保护集；仅对有新增决定性证据且通过 M5 证书的变化命题接受编辑；删除或改写保护命题时直接回退；冲突编辑不得通过整答案分数掩盖。
- **最小处理链：** A0/A2 拆解 → 命题对齐 → 锁定 A0 已支持命题 → 对变化命题逐项验证新增证据 → 合并允许编辑 → 对合并答案复验。
- **删除测试：** 禁用编辑图，恢复整答案 A2/A0 二选一；比较保护命题破坏率、局部纠正率、right-to-wrong 和顺序敏感性。
- **现有实现状态：** **基本缺失。** 现有代码能拆分声明，实验做过最小编辑 Prompt，但没有结构化 A0/A2 命题对齐、保护集、可组合编辑或合并后复验。
- **可验证指标：** 保护命题保持率、变化命题 precision/recall、每次替换的有效编辑数、right-to-wrong、成对顺序不变率。
- **不可声称效果：** 既有最小编辑 Smoke 未超过旧 A2；不得据此声称局部合并已有效、已降低伤害或优于整答案候选。

## 9. 所需机制 M8：边际价值驱动的预算与停止状态机

- **failure_id：** `I2A-F06`、`I2A-F07`、`I2A-F08`
- **本地路径/行号：**
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:4336-4380,4466-4480`
  - `/Users/bytedance/vqa_thesis_continue/docs/AdsQA最终结果交付_20260731.md:29-40,128-171`
  - `/Users/bytedance/vqa_thesis_continue/docs/ReAd-R裁剪Token效率诊断_20260804.md:58-72,74-96`
  - `/Users/bytedance/vqa_thesis_continue/evaluation/methods/common/qwen_video_budget.py:12-31,34-68,71-155`
- **失败现象：** Full-7844 的准确率点触发 `91.45%`，平均 `2,926.07` Token；降低阈值可省成本但风险线不稳定。Qwen2.5 把触发提高到 100% 也仅多出极少替换并引入损失，说明“是否触发”不是充分控制量。
- **根因假设：** 当前预算逻辑只校验上限，补看则固定获取一包证据；没有估计下一证据单元对未闭合义务的边际价值，也没有支持度平台、风险恶化和证据重复的停止状态。
- **所需状态量或数据结构：**
  - `BudgetState`：已用 Token/时延、剩余上限、未闭合关键叶；
  - `MarginalEvidenceValue`：候选证据对叶状态的预期变化、置信下界、重复率、成本；
  - 状态机 `INIT→ACQUIRE→RESCORE→STOP_ACCEPT/STOP_KEEP/STOP_ABSTAIN`.
- **控制规则：** 每轮只获取边际闭合价值/成本最高且下界为正的最小证据单元；新增证据与现有签名重复、支持差进入平台区、风险上界恶化或预算不足时立即停止；停止后按 M5 决定接受、保持或拒答。
- **最小处理链：** 初始化预算与义务图 → 排序最小证据单元 → 获取一单元 → 更新证据/支持/风险 → 计算边际价值 → 继续或停止。
- **删除测试：** 退化为当前“一次固定四视图补包”与单阈值触发；比较平均 Token、p95 时延、每千 Token 纠正数、平台后无效补看率和风险。
- **现有实现状态：** **预算审计存在，价值控制不存在。** `qwen_video_budget.py` 能严格检查视图和 Token 上限，正式稿规定生成前拦截；没有逐单元价值、状态更新或停止策略。
- **可验证指标：** 准确率/风险—成本前沿、每千 Token correction、平均轮数、平台停止率、预算违规率、固定风险下覆盖率。
- **不可声称效果：** 不得把预算上限可审计表述为成本最优；未独立确认前不得声称该状态机同时降本增精或满足严格风险保证。

---

## 10. 机制间最小依赖关系

这 8 项不是简单并列模块。最低限度的处理依赖为：

```text
M1 声明义务图
  → M3 模态账本
  → M2 证据副本图 / M4 模态单调验证
  → M6 动作选择
  → M8 增量取证与停止
  → M7 变化命题局部合并
  → M5 正确性风险证书
  → 接受 / 保持 / 拒答
```

删除任一前置状态后，后续控制量可能退化为当前已失败的代理：平面支持度、字段存在、局部像素变化、固定补看动作、整答案替换或单一阈值。

## 11. 优先验证顺序

1. **先验证 M2/M3/M4。** 当前反事实训练数据的负样本有效性和跨模态可辨识性尚未成立；这三项不过，不应训练新验证器。
2. **再验证 M1/M6。** 在不生成新答案的离线轨迹上，先看关键叶与动作是否可识别、是否超过随机/整帧控制。
3. **最后验证 M7/M5/M8。** 需要候选答案、独立证据标注和风险—覆盖评价，成本与标签要求最高。

该顺序本身不表示机制一定可行；任一门禁失败都应保留零机制通过的结果。

---

## 12. 读取文件与 SHA256

以下为本轮实际用于边界、失败归因、实现状态或哈希核验的本地文件。文件名级目录盘点和 `rg` 定位结果不另计入。

| 文件 | SHA256 |
|---|---|
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/00_brief.md` | `dfb0edf52df7c8b58e8ed9ebc33220b174111d27d98be408fd085296513c49cb` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/新申请初稿V2.1_说明书全文_20260817.md` | `1e980b4a7dcc87ead5a368d0523f65da8a94318a21d1dee1a9bde019d8d04c7b` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md` | `224e09e6c3de3e2ca5ae5d1f3726fc266d4c06bbf4f1536340b6bb2d884bb2fa` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md` | `0898ca7167854c68e4b56e5513a3bb8a091629974f8d62b1a993651bde6e7561` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA_Qwen3联合方法Confirm1000冻结确认集_20260728.md` | `12be9ee5c047ce9757c3a3f4d3605cf2dee561d82370eb45abdda12648868ac6` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA_Qwen3选择性证据补看ConfirmD300预注册_20260727.md` | `ae5d13cf6d37b1ca2697032deeb4355fa93ef4f102be8c45910bbde3b35dc57b` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA冻结结果远端核对记录_20260731.md` | `8c96ffdaf2f4088083ab8f1e3fd8d3096aa6b1729cf7936142c554a29be634a0` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA论文定稿实验结果总表_20260730.md` | `290d8e7bc8b6627d7172158f4401c19b469dbddf8c3a152aa33c5b44f638594c` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA最终结果交付_20260731.md` | `c0d417a268b1358e0ab7fba327be79c40e06d30572b4d9dbc309232f8a0db062` |
| `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md` | `d8ed2f81f03d4d6d3eecc54549312abb0edd814271c58b1e2436300e013cdca6` |
| `/Users/bytedance/vqa_thesis_continue/docs/方案B_多中心裁剪消融结果_20260731.md` | `0147fa5e8166dcdcbd9efa08be33938367d1201082e2d10d9912bf6c3ab4b655` |
| `/Users/bytedance/vqa_thesis_continue/docs/ReAd-R裁剪Token效率诊断_20260804.md` | `1eb301c3d4701886f7365e75cba66017d6604d8f92b08b9212e59b76acd3a14f` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/gate_protocol.py` | `68f34a0564a78f3d9f63f320af5aab9d807a3d10d975f7055aaac73e888b2e63` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/run_qwen25_gated_avcrop_groupcv_v1.py` | `9d999afd6794a9aadb3868eaa20fbc2f0df72a03e1a41b33609784bd968b7539` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/audit_qwen25_gated_avcrop_protocol_v1.py` | `bbe968774f4767e0d6f46f0d841ce7e0006cbda0869009609465cbe13d8c68ff` |
| `/Users/bytedance/vqa_thesis_continue/evaluation/methods/common/qwen_video_budget.py` | `282ebeb7c7658f227acb36dbc5a477106b3955133dd3b0f0e63f30abbaf48666` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/evidence/evidence_package.py` | `746cbccc5808b6c5b61cf57bced004657bd111c72f559ef7f477515fadd8c16d` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/reflection/claim_checker.py` | `7978bfe8fdcf0d6c450c25dcf12cd369fc672d95aa514142768dec02983e38bc` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/reasoning/prompt_builder.py` | `481549b37d8bf2b187ee71776b1cee3ed1c14aacb054d18a14662896599365e1` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_lightweight_pipeline.py` | `f9a256b051b8e04775bd36e49f5c98eaf7faa34f7fad6102390354e429b22da4` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/scripts/run_rag_qwen3_inference.py` | `28fb4e3caf1210c2a49000096512e538fe267a8cc9476c3d030707e19b4eb19c` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md` | `44c9ff0a4be631969dbb2cc124150120d07c5e28eb6bc37358370e2b2cd3b4e1` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/audit_candidate_d_formal_data_v1.py` | `17184061834ae6f907cb839fc4df10250085dd468aa409197945d3167133b5d0` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/audit_candidate_e_precondition_v1.py` | `1e65d9e7de483e450f6a9a621a3216993f10583564ca7f4057401a55e5c4b379` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_b_same_video_smoke_v1.py` | `720f1aa6e8eb31e64bbffc0052f64c5f4b7b58a274cf341b1e5dc7d36c217b59` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_c_missingness_smoke_v1.py` | `d45388d44b6a00bf23bc9c353ac1674bb6e5ce134a8a62688c7f7878f1594966` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_d_formal_data_v1.py` | `94354aefe0b1eea452684679bbdcc1005134b5080223b14383347ee1f8693fe8` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_f_raw_claim_templates_v1.py` | `3bf226e8cc3c3565b5581780b42f8c30e685a2105f02caa87988355a40fefaca` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_modality_counterfactual_train_v2.py` | `22d3ec424e2009c0ba39e407bb1b8a57ba71011d59074cf2fd9558aae67deb44` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/freeze_candidate_failure_v1.py` | `2bedbfda1da04fcc05917621167415ef8e47db4c8eb8c3c1cbc3fa7f41dd39b5` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/prepare_candidate_a_smoke_claims_v1.py` | `e08ee75edb6e6b6867c3837e6b42edfd46c1e13383477b38bcc802a1e704512c` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/remap_evidence_anchored_claims_v2.py` | `242257fe16924ea1be81f964d25f824f70ea711b96569d93f46f80c2b7cf64cc` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/run_candidate_d_pairwise_logit_smoke_v1.py` | `43eaf46c92090130633cc2004bb8819fe9927d135d31f30452aa410b453a89d3` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/run_candidate_f_machine_preannotation_v1.py` | `6d8b7839bc9d5dedecb528bd31574ffe15c76057ce41159634f111a484a544da` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/run_modality_counterfactual_smoke_v2.py` | `6ae7d21354e5accc3e01cb2810becc2b564c8602a62db98c04b482c8af080f2a` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/run_modality_counterfactual_smoke_v3.py` | `5c742c52ce3a239732707767198b9e80a87f9c4906d79d9f299a15fd20b927ef` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/run_raw32_avcrop8_nonfixedtoken_dev100_v1.py` | `658d1dc669811a0f63ab6e4291c14e0feaa71a0e4beaac529555022d5ff1e3ab` |

## 13. 隔离合规记录

- 外部网络检索：`0`
- 正式申请稿修改：`0`
- Git commit：`0`
- Git push：`0`
- `01*_paper_cards` 读取：`0`
- prior-art 论文清单读取：`0`
- `patent-innovation-analysis` Skill 读取：`0`

