# I2-B PRELIMINARY 候选

## 0. 结论边界

- 角色：I2-B 预候选 Agent。
- 生成日期：2026-08-18。
- 状态：下列内容均为 `PRELIMINARY`，仅用于后续敌对门禁、实验和专利代理人复核。
- 本轮没有进行外部专利检索，不能据此判断新颖性、创造性、授权前景或自由实施。
- 当前“低支持触发补看、独立重答、同协议验证、门控回退”仅作为比较基线；候选允许增强或替换该闭环。
- 既有实验结果只按其冻结归因使用。`0.5409→0.6599`只归于真实正反声明分类训练；Full-7844 的`+7.00/+10.12 pp`只归于低支持触发、证据补看和独立候选生成的联合流程；E-VAds `28胜0负`只支撑双条件门控。上述结果均不归因于本文件新增机制。
- 自家在先申请 `202610425757.8` 已公开三流热力图、时序滑动窗口、加权融合、响应密度多尺度锚框、全局/局部双流、RAG、结构化链式推理和关键词触发反思。本文件不把这些内容作为候选核心。

## 1. 候选总览

| 候选 | 隔离来源 | 预分类 | 当前判断 |
|---|---|---|---|
| I2B-P01 短时文字显隐脉冲记忆 | M01 | `CURRENT_APPLICATION_ENHANCEMENT` | 有跨帧 OCR 基础，但脉冲生命周期与问题槽位耦合未实现、未验证 |
| I2B-P02 声画时延假设格 | M02 | `NEW_APPLICATION` | 可替换固定滑窗，但与自家时序滑窗距离近，需强删除实验 |
| I2B-P03 镜头曝光欠账突发采样 | M04 | `EXPERIMENT_FIRST` | 固定预算审计可复用，镜头级状态与效果均缺失 |
| I2B-P04 产品实体属性绑定账本 | M05 | `NEW_APPLICATION` | 数据结构清楚，需实体跟踪与属性绑定标注 |
| I2B-P05 时间化多模态冲突张量 | M06 | `CURRENT_APPLICATION_ENHANCEMENT` | 能修复标量抵消和 ASR 主导，但当前 OCR 可辨识性失败 |
| I2B-P06 数据驱动广告叙事阶段图 | M07 | `EXPERIMENT_FIRST` | 面向抽象题，但业务规则攻击和 CaST 组合攻击强 |
| I2B-P07 报价与主张版本化事实账本 | M09 | `NEW_APPLICATION` | 广告特性强，适用题量和实现基础不足 |
| I2B-P08 证据副本图与删除充分证书 | I2-A M2 | `CURRENT_APPLICATION_ENHANCEMENT` | 直接修复当前反事实负样本失效，优先级最高但实现难 |

未列为独立候选：

- M03 复现拓扑：当前只有“去重复惩罚贡献很小”的负结果，尚无元素级复现图或独立效果，暂不为凑数立项。
- M08 条件新信息细节注入：与自家响应密度裁剪、全局/局部双流雷区过近，且同锚点全帧控制多次不劣于裁剪；可作为 P01/P04 的从属实验，不单列。
- M10 角色、行动、结果因果骨架：与 P06 可形成后续关系，但现在合并会成为硬凑组合，单独又容易被认定为营销语义规则；先验证 P06 的阶段边必要性。

---

## I2B-P01 PRELIMINARY：短时文字与 Logo 显隐脉冲记忆

### 1. 技术问题与广告特性

- **技术问题：** 固定帧采样或逐帧 OCR Top-K 可能跨过仅出现数帧的价格、折扣、Logo、CTA 和免责声明；普通跨帧合并也没有把“短曝光但与问题槽位决定性匹配”的事件转成采样控制量。
- **广告特性：** 短时文字/Logo、片尾闪现、高信息密度、同一文字重复出现且可读尺度变化。
- **可测目标：** 按可见时长分桶的文字事件召回、品牌/数值 exact match、事件边界误差、每千视觉 Token 的决定性文字召回和对应题型 QA。

### 2. 核心数据结构

`TextPulseTrack`：

```text
pulse_id, normalized_text, logo_embedding, start_time, end_time,
visible_duration, first/peak/last_frame, max_readable_scale,
cross_frame_consistency, recurrence_count, region_trajectory,
question_slot_matches, raw_frame_ids, provenance
```

### 3. 必要特征

1. 对低成本密集缩略帧执行 OCR/Logo 检测，并按字符串、视觉标识和区域连续性聚合为带显隐边界的脉冲，而不是只保留逐帧分数。
2. 将用户问题解析为品牌、数值、时间、CTA 或限制条件槽位，并把槽位匹配结果写回 `TextPulseTrack`。
3. 依据“槽位匹配度、可见时长、可读尺度和跨帧一致性”的共同状态选择脉冲，不以单帧最大响应作为唯一选择量。
4. 对被选脉冲回取原分辨率的首次、峰值和末次出现帧，并在统一视觉 Token 预算内替换普通采样帧。

### 4. 处理链

视频与问题 → 密集缩略帧 OCR/Logo 扫描 → 跨帧关联与显隐边界生成 → 问题槽位匹配 → 选择短而决定性的脉冲 → 回取原分辨率关键帧及文字摘要 → 一次回答或作为当前闭环的结构化补充证据。

### 5. 耦合关系

脉冲不是 OCR、跟踪和采样三个并列模块。`visible_duration`、`max_readable_scale` 与 `question_slot_matches` 同时决定是否回取原帧、回取哪三个时刻以及占用多少预算；删除任一状态后会退化成逐帧 OCR Top-K 或普通高分辨率裁剪。

### 6. 删除测试

在相同问题、回答器、原始视频、最终视图数和视觉 Token 下，用“逐帧 OCR 相关性 Top-K”替换 `TextPulseTrack`；比较短曝光事件 Recall、数值/品牌 exact match、对应题型 QA 和误召回长时无关文字比例。另做仅保留峰值帧、删除首次/末次帧的消融。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| 旧实验没有时间戳 ASR，OCR 还是语义代理，不能声称跨帧稳定性 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:175-204` | 强，负向边界 |
| 查询条件化 OCR 已有 800 帧、2,210 框缓存与 fail-closed 校验 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:459-486` | 强，构件支持 |
| OCR 将 Region Recall 提高到 10/10，但没有提高整体 QA | `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md:42-46` | 强，效果边界 |
| 当前正式稿已披露相邻帧文字合并、时间、区域、置信度和跨帧次数 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md:203-215` | 强，当前申请基础 |
| EvidencePackage 有时间、OCR、Logo、全局/局部字段，但轻量构建器仍主要填 ASR/元信息 | `/Users/bytedance/vqa_thesis_continue/code_refactor/evidence/evidence_package.py:18-37,79-98` | 强，代码状态 |

### 8. 代码状态

- **状态：** `PARTIAL_BUILDING_BLOCKS`。
- **已有：** OCR 缓存、时间字段、Logo/OCR 字段、原始帧回指基础、固定预算审计。
- **缺失：** 显隐边界、脉冲轨迹、问题槽位、短曝光优先级、首次/峰值/末次联合回取和部署态持久化。

### 9. 已有实验、可验证效果与不可归因效果

- 已有 OCR 缓存使证据单元命中达到 `29/30`、Region Recall 达到 `10/10`，但 pilot QA 与对照持平。
- 因此可将“已有 OCR 定位构件可运行”作为实现依据，不能把任何既有 QA 增益归于脉冲记忆。
- 未完成删除测试前，不得声称短时文字召回、品牌/价格 QA 或 Token 效率提高。

### 10. 与源论文差异

- `PAPER-A012 MME-VideoOCR`（NeurIPS 2025，背景论文，不进入 2026 候选源池）已经公开文字时空定位、变化跟踪、跨帧整合及帧数/分辨率诊断，构成最强论文攻击。
- `PAPER-CD-020 LENS`（ECCV 2026，最早公开 2026-07-27，§3.2-3.4）按查询在空间与时间预算间分配帧，但没有文字显隐生命周期、问题槽位到脉冲的绑定或首次/峰值/末次原帧回取。
- 本候选不能主张“跨帧 OCR”本身；可区分的关系只在“脉冲生命周期状态共同控制问题槽位定向采样”。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请只用 OCR 关键词生成热力图，再经响应密度锚框输出全局/局部双流，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:13-22`；本候选的控制单位是跨帧文字事件，不使用热力图加权或响应密度作为核心。
- 当前申请已经披露“跨帧文字事件”，所以独权不能只写事件合并；必须限定显隐边界、问题槽位匹配及其对原分辨率回取的共同控制，否则实质重复或仅为说明书细化。

### 12. 独权骨架

一种面向广告视频问答的短时文字证据获取方法，包括：从广告视频的密集缩略帧中提取文字或标识实例；将跨帧同一文字或标识实例聚合为含显隐边界、可读尺度和区域轨迹的文字脉冲；将问题解析为文字证据槽位并与文字脉冲匹配；基于槽位匹配度、脉冲可见时长和可读尺度共同选择目标脉冲；在固定视觉输入预算内回取目标脉冲的多个原分辨率时刻并用于生成视频问答答案。

### 13. 从属降落点

1. 规范化字符串与 Logo 嵌入共同确定脉冲身份。
2. 回取时刻限定为首次出现、最大可读尺度时刻和末次出现。
3. 对重复出现但区域或上下文不同的脉冲保留独立轨迹，不直接合并。
4. 按可见时长分桶设置最低回取数量，并在预算不足时优先保留槽位 exact-match 脉冲。
5. 输出脉冲 ID、原帧 ID、文字框和识别置信度组成的审计回执。

### 14. 实现难度与最强审查攻击

- **难度：** 中。
- **最强攻击：** MME-VideoOCR 已证明跨帧文字跟踪是直接需求，当前申请又已有跨帧文字事件；将事件增加持续时间、首末帧和问题匹配字段，可能被认定为常规时序 OCR 数据组织。若“脉冲控制原帧回取”不能在等 Token 删除测试中超过逐帧 Top-K，本候选应降为 `DEPENDENT_CLAIM_ONLY` 或 `REJECT`。

### 15. 分类

`CURRENT_APPLICATION_ENHANCEMENT`

---

## I2B-P02 PRELIMINARY：声画时延假设格

### 1. 技术问题与广告特性

- **技术问题：** 固定同刻匹配、固定距离衰减或单一滑动窗口把所有邻近音频聚合到当前画面，无法表示旁白领先、旁白滞后和多个局部相关峰，容易把真实跨模态事件拆开或把无关语音混入。
- **广告特性：** 画外音提前铺垫、产品先出现后解释、片尾品牌揭示与口播错位、音乐高潮与视觉揭示不同步。
- **可测目标：** 人工声画配对 lag MAE/Recall、错配边比例、跨模态事件召回、speech/audio 子集 QA 及零时延对照差。

### 2. 核心数据结构

`LagHypothesisLattice`：视觉事件节点、ASR/音频事件节点和有向边；边字段包含 `signed_lag`、方向、相关性、局部峰宽、互斥组、问题槽位、证据来源、冲突状态和置信区间。

### 3. 必要特征

1. 将视频切分为视觉事件，并将分段 ASR 或音频切分为带起止时间的音频事件。
2. 在有界正负时延区间内计算视觉事件与音频事件的多峰关联，不预先把时延固定为零或单一窗口。
3. 保留至少两个互斥时延假设及其方向、峰宽和证据来源，禁止在选择前求平均。
4. 由问题所需实体、动作或属性槽位选择一条或多条相容边，并把采用的时延边随答案输出。

### 4. 处理链

视频、分段 ASR 与问题 → 视觉/音频事件切分 → 正负时延多峰关联 → 构建互斥假设格 → 问题槽位约束边选择 → 联合回取边两端证据 → 一次回答与时延回执。

### 5. 耦合关系

`signed_lag` 不是附加时间特征。它同时决定视觉证据与哪一语音段配对、回取时间范围及冲突判断；互斥组防止多个相反时延在加权平均后形成虚假的“同步”证据。

### 6. 删除测试

将全部格边强制设为零时延，保持事件候选、视图数、ASR 文本量、回答器和 Token 不变；另以自家固定滑动窗口为第二对照。比较人工配对、speech/audio 子集 QA、错配边和采用证据跨度。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| 早期 ASR 为整段文本，没有时间戳，偏移估计未启用 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:175-204` | 强，负向边界 |
| 后续已有 9,481 个带时间状态的 ASR 句段 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:4073-4082` | 强，数据基础 |
| 现有时间线代码仅以绝对时间距离作单峰衰减 | `/Users/bytedance/vqa_thesis_continue/evaluation/tools/build_evads_avfunnel_manifest_entropy_v1.py:138-159` | 强，代码差距 |
| EvidencePackage 已有 timestamp/time_window/ASR | `/Users/bytedance/vqa_thesis_continue/code_refactor/evidence/evidence_package.py:18-31` | 中 |

### 8. 代码状态

- **状态：** `NOT_IMPLEMENTED`。
- **已有：** 分段 ASR、时间戳字段、固定距离衰减和固定窗口相关基础。
- **缺失：** 视觉事件切分、多峰时延估计、互斥假设、问题槽位边选择和时延消融。

### 9. 已有实验、可验证效果与不可归因效果

- 旧 AV 门控命中的 7 题均没有 ASR/OCR，AV 与 CLIP 计划和答案完全相同，不能支撑声画协同，见 `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:2943-2955`。
- 现有分段 ASR 只证明数据基础存在，不证明时延估计有效。
- 未完成零时延和固定滑窗对照前，不得声称异步对齐、语音题增益或跨模态协同。

### 10. 与源论文差异

- `PAPER-CD-020 LENS` 在固定帧预算内分配空间/时间观察，但不建立音频事件与视觉事件的有向时延边。
- `PAPER-CD-002 Active Video Perception`（CVPR 2026 Findings，最早公开 2025-12-05，§3.1-3.3）按证据充分性重规划观察，没有多峰声画时延状态。
- 本候选的差异不在“多模态对齐”，而在“保留相反方向的互斥时延假设，并由问题槽位决定采用边”。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请已用中心滑动窗口聚合邻近语音热力图，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:15-18,99-101`。
- 本候选必须排除“扩大窗口、改变衰减或改变权重”的写法；核心差异是带符号、多峰、互斥的边结构及其对证据配对的控制。
- 当前申请只提带时间段语音和未覆盖时间位置，不公开时延假设格。

### 12. 独权骨架

一种广告视频的声画异步证据组合方法，包括：生成视觉事件和带时间范围的音频事件；在正负时延范围内为事件对计算多个局部关联峰；构建包含方向、时延和互斥关系的时延假设格；依据用户问题的证据槽位从所述假设格选择相容时延边；按照所选边联合获取视觉与音频证据并生成视频问答答案。

### 13. 从属降落点

1. 时延方向区分音频领先、视觉领先和近同步。
2. 用局部峰宽表示可接受时延区间，而不是单一时间点。
3. 当两个相反方向假设属于同一互斥组时，禁止加权平均。
4. 格边保存 ASR span、视觉事件帧和问题槽位的共同 provenance。
5. 无假设通过时降级到明确标记的单模态证据路径。

### 14. 实现难度与最强审查攻击

- **难度：** 高。
- **最强攻击：** 自家滑动窗口已经针对声画异步，多峰互相关、动态时间规整和保留 Top-K 峰属于常规信号处理选择；没有 lag 标注和零时延配对实验时，本候选很可能被认为是滑动窗口的参数化扩展。

### 15. 分类

`NEW_APPLICATION`

---

## I2B-P03 PRELIMINARY：镜头曝光欠账驱动的突发采样

### 1. 技术问题与广告特性

- **技术问题：** 均匀采样按时长分配视图，相关性 Top-K 按峰值分配视图，两者都可能低估短镜头；后者还会扩大时间空洞。
- **广告特性：** 快速镜头切换、短镜头承载品牌/产品揭示、长静态镜头挤占预算。
- **可测目标：** 短镜头 Recall、每镜头覆盖率、最大归一化空洞、关键转场事件 Recall、QA/Token 和快切子集配对区间。

### 2. 核心数据结构

`ShotExposureLedger`：`shot_id`、起止时间、时长、切换强度、镜头内语义变化、实体连续性、已分配视图、最低覆盖量、曝光欠账、候选突发组三帧和预算成本。

### 3. 必要特征

1. 先执行低成本镜头边界检测，至少为每个有效镜头建立独立账本项。
2. 根据镜头时长、切换强度和镜头内语义变化计算曝光欠账，短而高变化镜头的欠账高于长静态镜头。
3. 先保证每镜头最低覆盖，再为高欠账镜头分配边界前、中、后三个突发视图。
4. 在固定总视图与视觉 Token 下，从长静态镜头回收预算，并由统一处理器审计实际表示帧和 Token。

### 4. 处理链

视频与问题 → 镜头切分 → 初始化曝光账本 → 分配每镜头最低视图 → 对高欠账镜头生成突发组 → 从低欠账长镜头回收预算 → 固定预算审计 → 回答。

### 5. 耦合关系

镜头时长不直接决定采样数；只有和切换强度、语义变化、已分配视图共同形成的“欠账”才控制预算转移。突发组与回收操作共享同一账本，保证增加短镜头视图不会突破总预算。

### 6. 删除测试

在完全相同视图数和视觉 Token 下，分别以 Uniform、MMR Top-K 替换曝光欠账分配；另删除“三帧突发”只保留每镜头一帧。比较短镜头 Recall、最大空洞、关键转场召回和快切子集 QA。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| MMR32 提高帧精度但最大时间空洞从 3.28% 增至 12.51% | `/Users/bytedance/vqa_thesis_continue/docs/创新点一时间证据定位最终结论与复现索引.md:23-44` | 强 |
| 去覆盖约束会继续扩大空洞，去重复惩罚无退化 | `/Users/bytedance/vqa_thesis_continue/docs/创新点一时间证据定位最终结论与复现索引.md:55-59` | 强 |
| 视觉预算工具可固定全局/局部视图数并精确审计实际帧和 Token | `/Users/bytedance/vqa_thesis_continue/evaluation/methods/common/qwen_video_budget.py:12-31,34-68,71-155` | 强，构件支持 |
| 增加全帧 Token 没有单调增益 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:3868-3886` | 强，效果边界 |

### 8. 代码状态

- **状态：** `PARTIAL_BUILDING_BLOCKS`。
- **已有：** 固定视图/Token 审计、候选帧、时间覆盖指标。
- **缺失：** 镜头切分、曝光欠账、突发组生成、预算回收和快切专项集。

### 9. 已有实验、可验证效果与不可归因效果

- 时间相关性选择只获得证据筛选价值，没有稳定 QA 增益。
- 现有预算工具只证明上界可审计，不证明曝光分配更优。
- 未完成三臂等预算实验前，不得声称短镜头召回或 QA/Token 提升。

### 10. 与源论文差异

- `PAPER-CD-004 LongVideo-R1`（CVPR 2026，2026-02-24，§3.1-3.3）在分层视频树中导航并按成本停止，核心不是镜头曝光欠账。
- `PAPER-CD-020 LENS` 按查询在空间 zoom-in 和时间 zoom-out 之间分预算，没有“每镜头最低覆盖、短镜头欠账、长镜头预算回收”的账本约束。
- `PAPER-CD-018 FrameFusion`（ICCV 2025，背景）按相似度合并和重要性剪枝，且论文局限已指出快速切换破坏相邻位置假设；本候选不以 token 相似度合并为核心。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请 S1 是高频过采样后语义 Top-K，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:3,8-10`；没有镜头账本、最低覆盖或曝光欠账。
- 当前申请使用均匀候选网格与 MMR，见正式稿 `:203-215`；本候选改变首次回答前的预算分配单位，但不能复用 MMR 作为创新核心。

### 12. 独权骨架

一种固定视觉预算下的广告视频采样方法，包括：将广告视频切分为多个镜头；为各镜头记录时长、切换强度、语义变化和已分配视图；依据所述记录计算镜头曝光欠账；在保证各镜头最低覆盖的条件下，为高曝光欠账镜头分配包含多个镜头内时刻的突发视图，并从低曝光欠账镜头回收视图预算；在总视图数和视觉令牌不超过预算时生成视频问答输入。

### 13. 从属降落点

1. 突发视图限定为镜头边界后、镜头中部和镜头边界前。
2. 曝光欠账随镜头时长减少、切换强度增加或语义变化增加而提高。
3. 跨镜头实体连续时保留相邻两镜头的边界视图。
4. 预算回收优先来自长时、低变化且已超过最低覆盖的镜头。
5. 输出每镜头欠账、分配视图和实际视觉 Token 审计记录。

### 14. 实现难度与最强审查攻击

- **难度：** 中。
- **最强攻击：** 镜头检测、每镜头至少一帧、短镜头多采样和长镜头少采样均可能是常规分层采样。只有“曝光欠账作为同一状态同时约束最低覆盖、突发分配和预算回收”且删除实验显著时，才值得进入专利检索。

### 15. 分类

`EXPERIMENT_FIRST`

---

## I2B-P04 PRELIMINARY：产品实体属性绑定账本

### 1. 技术问题与广告特性

- **技术问题：** 局部高分辨率视图能让属性更可见，但不保存颜色、容量、型号、接口、材质或配方属于哪个产品实例和哪个版本，交替剪辑时会发生跨镜头属性串绑。
- **广告特性：** 多产品/多版本交替、产品特写、包装文字、细粒度属性、快速切镜。
- **可测目标：** 实体 track IDF1、属性抽取 F1、属性串绑错误率、细粒度产品题 exact match 和按属性类型分层 QA/Token。

### 2. 核心数据结构

`EntityAttributeLedger`：以跨镜头产品实体 ID 为键；每个属性槽保存候选值、视觉区域、OCR span、时间范围、来源模态、身份连续性、支持/冲突状态、版本 ID 和 provenance。

### 3. 必要特征

1. 检测产品候选并跨镜头维持实体身份，不把相邻帧检测框当作独立产品。
2. 从局部视图和 OCR 中提取属性值，并只在身份连续性达到条件时写入对应实体槽位。
3. 同一实体同一属性出现多个值时保留冲突和时间范围，不以最高分值覆盖其余值。
4. 将问题解析为实体键和属性键，只向回答器提交目标槽位、原始证据及冲突值。

### 4. 处理链

视频与问题 → 产品检测/跟踪 → 跨镜头身份归并 → 局部属性/OCR 读取 → 写入带 provenance 的属性槽 → 问题实体属性键解析 → 读取对应槽位和冲突 → 回答。

### 5. 耦合关系

实体轨迹决定属性写入目标，属性冲突又反馈身份归并是否可信；问题键只读取该实体槽位。若删除实体 ID，局部识别结果会重新退化为无归属的属性集合。

### 6. 删除测试

在同一视频内随机置换产品实体 ID，保持帧、属性候选、OCR 和回答器不变；若绑定有效，属性题应显著下降而非属性题变化较小。另以“所有属性扁平拼接”作为对照。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| EvidencePackage 有全局/局部/OCR/Logo，但没有实体或属性关系 | `/Users/bytedance/vqa_thesis_continue/code_refactor/evidence/evidence_package.py:18-35` | 强 |
| 当前声明路由只按关键词粗分 OCR、ASR、营销和视觉 | `/Users/bytedance/vqa_thesis_continue/code_refactor/reflection/claim_checker.py:18-26` | 强 |
| 同 Token 的 EvidenceMix4K 低于 Raw4K，局部证据可能放大非决定区域 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:3868-3886` | 强，负向边界 |
| 当前申请只把局部属性作为补看类型，没有实体绑定 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md:241-263` | 强 |

### 8. 代码状态

- **状态：** `NOT_IMPLEMENTED`。
- **已有：** 局部视图、OCR/Logo、时间和 evidence ID 字段。
- **缺失：** 产品检测/跟踪、跨镜头身份、属性槽位、版本与冲突状态、实体 ID 打乱实验。

### 9. 已有实验、可验证效果与不可归因效果

- 多中心裁剪和同锚点整帧都比 A0 高，但多中心始终略低于整帧且区间跨零，说明“裁剪位置”没有独立增益，见 `/Users/bytedance/vqa_thesis_continue/docs/方案B_多中心裁剪消融结果_20260731.md:35-55`。
- 该结果只能说明属性可见性不等于属性绑定；不能归因于本候选。
- 未完成实体 ID 打乱测试前，不得声称降低串绑或提高细粒度 QA。

### 10. 与源论文差异

- `PAPER-CD-005 LensWalk`（CVPR 2026，2026-03-25，§3.1-3.4）维护主体记忆表，但没有产品属性槽、冲突值和实体属性查询合同。
- `PAPER-CD-012 Evidence-Backed VQA`（ECCV 2026，2026-07-13，§3/§5.4）输出时间段与跨帧 masklet，公开了对象级证据绑定，但没有把多个属性值写入版本化产品实体账本。
- `PAPER-A003`（ICCV 2025，背景）已公开对象提示跨帧传播和 mask 输出，因此“对象跟踪+VQA”本身不能作为差异。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请的局部视图由热力图锚框产生并与全局流拼接，没有跨镜头实体 ID 或属性槽，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:19-22`。
- 当前申请的 evidence package 和补看流程仍以帧/区域为单位；本候选以产品实体账本替换无归属局部视图，但不能把裁剪作为核心。

### 12. 独权骨架

一种广告视频中的产品属性问答方法，包括：从多个视频镜头检测产品实例并建立跨镜头实体身份；从与产品实例对应的视觉区域和文字区域提取属性候选；依据实体身份连续性将属性候选写入对应实体的属性槽并保留时间、来源和冲突状态；根据用户问题确定目标实体键和属性键；基于目标槽位及其原始证据生成答案。

### 13. 从属降落点

1. 实体身份由外观嵌入、包装文字和时间连续性共同确定。
2. 属性槽区分颜色、型号、容量、接口、材质、配方或包装版本。
3. 同槽多值不直接覆盖，而记录并列、替代或未解析冲突。
4. OCR 属性必须保存字符框、原帧和识别置信度。
5. 身份连续性不足时输出 `unbound_attribute`，禁止进入目标实体答案。

### 14. 实现难度与最强审查攻击

- **难度：** 高。
- **最强攻击：** 多目标跟踪、实体消歧和属性槽填充都是成熟技术，将其用于广告产品可能被认定为直接应用；LensWalk 主体表、E-VQA masklet 与常规知识图谱组合可能覆盖大部。需要实体 ID 打乱产生明确特异性效应，才能证明绑定关系不是并列模块。

### 15. 分类

`NEW_APPLICATION`

---

## I2B-P05 PRELIMINARY：时间化多模态冲突张量

### 1. 技术问题与广告特性

- **技术问题：** 单一支持分数把“视觉支持、ASR 反驳”“早期值被片尾值更新”“没有检测到”和“模态不可用”压成一个标量，易被 ASR 简单缺失状态主导或发生跨模态错误抵消。
- **广告特性：** 旁白、屏幕文字、包装、演示和元信息可能冲突；原价/现价或前后版本使冲突只在局部时段成立。
- **可测目标：** 冲突检测 macro-F1、缺失/反驳区分率、每模态 ECE/Brier、错误抵消率、冲突题 QA 和错误自信率。

### 2. 核心数据结构

`ConflictTensor[claim_id, modality, time_bin]`，单元包含 `supported/refuted/not_detected/unavailable/unidentifiable`、强度、来源、有效时间、校准版本和冲突边；另含 `ResolutionPolicy` 与未解析状态。

### 3. 必要特征

1. 对同一原子声明按视觉、OCR、ASR 和其他允许模态分别生成带符号状态，不先求平均。
2. 将 `not_detected`、`unavailable` 与 `refuted` 分开；不可用模态不得被其他模态高分抵消。
3. 按时间箱区分同刻冲突、时序更新和持续缺失，并保留跨时间冲突边。
4. 根据问题对象、时态和所需证据类型执行解析；未解析冲突必须保留为未确定状态，不强制输出单一事实。

### 4. 处理链

问题/候选答案 → 原子声明与时态槽位 → 各模态各时段取证 → 写入带符号冲突张量 → 判定模态可用性与可辨识性 → 区分同刻冲突/时序更新/缺失 → 解析或保留冲突 → 生成答案或控制当前闭环。

### 5. 耦合关系

模态维和时间维不能独立删除：模态维提供冲突方向，时间维决定该冲突是同时矛盾还是合法更新；`ResolutionPolicy` 读取二者后才能决定采用、补证或保持未确定。

### 6. 删除测试

将张量沿模态维和时间维求均值，退化为当前答案级支持分数；比较冲突 macro-F1、缺失/反驳混淆、错误抵消率、冲突题 QA 和校准。另删除时间维，检验“时序更新被误判为同时冲突”的比例。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| 显式缺失候选被 ASR 7/7 主导，OCR/视觉仅 4/7、3/6 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:2904-2915` | 强 |
| RealClaim LoRA 达 AUROC 0.6599，但 Calibration240 无 OCR-present，OCR 门禁不可评估 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:3797-3822` | 强 |
| 反事实构造已按声明类型路由 ASR/OCR/视觉/联合模态 | `/Users/bytedance/vqa_thesis_continue/evaluation/tools/build_modality_counterfactual_train_v1.py:62-73,141-178` | 强，构件支持 |
| 当前申请有支持/反驳/不足和“多源冲突”缺口，但答案级仍可均值/最低值聚合 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md:223-247` | 强，当前申请边界 |

### 8. 代码状态

- **状态：** `PARTIAL_BUILDING_BLOCKS`。
- **已有：** 声明类型、三态标签、模态路由、反事实构造和验证器分数。
- **缺失：** 部署态张量、`unavailable/unidentifiable` 状态、时间箱冲突、模态内校准和解析策略。

### 9. 已有实验、可验证效果与不可归因效果

- `0.6599`只支撑真实正反声明分类训练，且 OCR 分层未通过，不能归因于冲突张量。
- 正式 OCR 反事实 Smoke 为 `5/10`，不得声称 OCR 单调性或跨模态排序可用。
- 本候选必须先在同刻冲突、时序更新、缺失三类人工小集上验证，之后才能做 QA。

### 10. 与源论文差异

- `PAPER-CD-008 SIEVES`（arXiv 2026，2026-04-28，§3.1-3.2）联合评分答案正确性、定位质量和证据一致性并做拒答，但对象是整题，未形成声明×模态×时间的带符号张量。
- `PAPER-CD-012 Evidence-Backed VQA` 分别评测答案、时间和空间证据，但不解析 OCR/ASR/视觉之间的时序冲突。
- `PAPER-CD-015`（CHIL 2026，2026-03-03，§3/§5.2）直接说明聚合校准会掩盖类别失准，支持本候选的失败动机，但没有给出视频生成式冲突张量。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请将问题、语音和 OCR 热力图线性加权，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:13-18`；本候选明确禁止先融合，保留带符号冲突和不可用状态。
- 当前申请已披露多源冲突缺口，因此不能只写“检测冲突”；差异必须落在时间化张量、不可用/反驳分离和防跨模态抵消控制。

### 12. 独权骨架

一种多模态广告视频问答的证据冲突处理方法，包括：将候选答案拆解为原子声明；针对各声明在多个时间区间分别获取视觉、文字和语音证据；将各模态证据写入以声明、模态和时间为维度的冲突张量，单元状态至少区分支持、反驳、未检测和不可用；根据问题时态和证据类型区分同时冲突与时序更新；基于解析后的张量状态生成答案或保留未解析状态。

### 13. 从属降落点

1. 增设 `unidentifiable` 状态，模态反事实方向未通过时禁止参与聚合。
2. 时序更新边记录旧值、新值和生效时间。
3. 不可用模态不计为低支持或反驳。
4. 同刻冲突未解析时触发定向补证或拒绝替换。
5. 输出每个张量单元的 evidence ID、时间范围和校准版本。

### 14. 实现难度与最强审查攻击

- **难度：** 高。
- **最强攻击：** 多维证据表、四态逻辑和时间版本冲突可被认为是常规数据组织；当前申请已写多源冲突，源论文又已分解证据质量。若不能证明“禁止跨模态抵消”和“时间维区分更新/冲突”各自有删除效应，本候选只适合从属限定。

### 15. 分类

`CURRENT_APPLICATION_ENHANCEMENT`

---

## I2B-P06 PRELIMINARY：数据驱动广告叙事阶段图

### 1. 技术问题与广告特性

- **技术问题：** 逐帧相关性容易只保留产品或片尾，丢失情境、问题、转折和结果；主题、情绪、策略和受众问题依赖跨时间叙事，不是单一 ROI。
- **广告特性：** 快节奏叙事、问题到产品介入、前后对照、CTA/品牌收束、阶段跳步和回环。
- **可测目标：** 阶段边界 F1、阶段覆盖率、最小连通子图充分率、阶段边打乱敏感性、Type_2 至 Type_5 QA 和长跨度问题配对增益。

### 2. 核心数据结构

`NarrativePhaseGraph`：节点为数据驱动的阶段事件，保存时间跨度、角色、动作、状态、产品、情绪和视听 provenance；边表示时间先后、状态转折、对照、因果候选和品牌收束。阶段类型允许缺失、重复和回环。

### 3. 必要特征

1. 从镜头、ASR、角色变化、产品揭示和 CTA 信号生成阶段候选，不以固定 AIDA/PAS 模板强制分段。
2. 依据事件状态变化建立时间、转折和因果候选边，并保留边的原始证据跨度。
3. 根据问题类型查询包含所需角色、动作和结果的最小连通叙事子图，而不是提交节点 Top-K。
4. 按图中阶段顺序编码证据；边不确定时保留多个候选路径，不把营销标签本身当答案。

### 4. 处理链

镜头/ASR 事件切分 → 阶段候选生成 → 状态变化与转折建边 → 问题所需证据槽位 → 最小连通叙事子图 → 顺序化多段证据 → 一次回答。

### 5. 耦合关系

节点提供局部事实，边决定这些事实是否构成前后变化、对照或收束；问题查询必须覆盖一条连通路径。仅保留节点会退化为普通 Top-K 多证据检索，固定营销阶段则退化为业务规则。

### 6. 删除测试

保持节点、视图数和 Token 不变，随机打乱或删除阶段边；第二对照只提交节点 Top-K。比较 Type_2 至 Type_5 QA、长跨度题、阶段连通率和答案证据跨度。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| 受众、情绪、叙事策略、隐喻和品牌使命依赖跨时间叙事，不是单个 ROI | `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md:66-80` | 强 |
| AdsQA 正式任务覆盖情绪、主题、策略和受众 | `/Users/bytedance/vqa_thesis_continue/code_refactor/data/adsqa_loader.py:9-39` | 强 |
| 相关帧精度提升同时扩大时间空洞 | `/Users/bytedance/vqa_thesis_continue/docs/创新点一时间证据定位最终结论与复现索引.md:35-44` | 强 |
| 当前 Prompt 仍是通用 Observation/Knowledge/Analysis/Answer 文本结构 | `/Users/bytedance/vqa_thesis_continue/code_refactor/reasoning/prompt_builder.py:29-46` | 强，代码差距 |

### 8. 代码状态

- **状态：** `NOT_IMPLEMENTED`。
- **已有：** 任务类型、帧/ASR 时间、通用结构化 Prompt。
- **缺失：** 阶段候选、边界模型、状态转折边、最小连通子图和阶段标注。

### 9. 已有实验、可验证效果与不可归因效果

- 现有局部定位和相关性选帧负结果只支持“跨时间结构可能缺失”的动机，不证明阶段图有效。
- 现有 Full-7844 增益来自补看联合流程，不归因于叙事阶段。
- 未完成阶段边打乱测试前，不得声称提高抽象广告理解或长跨度 QA。

### 10. 与源论文差异

- `PAPER-A010 CaST-Bench`（CVPR 2026，2026-05-22，§3-5）已公开可变长因果链、时间段和 bbox 轨迹，是最强反向证据；但它是人工构建的因果链诊断任务，不是从广告视频先构建允许跳步/回环的阶段图并按问题查询最小连通子图。
- `PAPER-A011 HERBench`（CVPR 2026，最早公开 2025-12-16，§3/§5）已公开至少三段分散证据和 MRFS，说明多证据融合拥挤；本候选不能只主张“至少三段证据”。
- 可区分关系只能是“数据驱动阶段边作为检索与顺序编码的共同控制状态”，不是营销模板或普通因果链输出。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请使用营销知识库和“观察、分析、推理、答案”文本协议，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:24-30,106-114`。
- 本候选不检索固定营销理论，也不以 Prompt 阶段名约束输出；阶段由视频事件变化生成，并直接控制多段证据选择。
- 当前申请只含问题证据需求逻辑树，没有视频叙事阶段图。

### 12. 独权骨架

一种广告视频的阶段化证据组织方法，包括：从广告视频的镜头事件和语音事件生成多个阶段候选；依据事件中的角色、动作、产品和状态变化建立阶段候选之间的时间或转折边，形成允许阶段缺失、重复或回环的叙事阶段图；根据用户问题确定所需事件槽位；从叙事阶段图提取覆盖所述槽位的最小连通子图；按照子图边顺序组织多段视频证据并生成答案。

### 13. 从属降落点

1. 阶段边由转折词、角色变化、产品揭示或 CTA 信号中的至少两类共同支持。
2. 每条边保存起止时间、视觉区域、ASR span 和证据置信度。
3. 不确定边保留多个候选路径并输出路径置信。
4. 最小连通子图必须覆盖问题所需的前态、介入事件和后态。
5. 对主题/情绪题保留全局阶段，对产品细节题只读取目标阶段节点。

### 14. 实现难度与最强审查攻击

- **难度：** 高。
- **最强攻击：** CaST 已公开有序因果证据链，HERBench 已公开多段证据；将广告分为阶段还可能是 AIDA/PAS 等业务规则。若阶段标签来自固定营销模板，直接 `REJECT`；只有数据驱动边和边删除效应成立后，才考虑另起申请。

### 15. 分类

`EXPERIMENT_FIRST`

---

## I2B-P07 PRELIMINARY：报价与主张版本化事实账本

### 1. 技术问题与广告特性

- **技术问题：** 扁平 OCR 文本集合不能表示原价/现价、套餐层级、限时条件、脚注和片尾 CTA 的生效区间、适用实体及覆盖关系；相似数字容易被错误合并或绑定到错误商品。
- **广告特性：** 多报价、多条件、片尾更新、OCR 与口播并列或冲突、同一视频多产品版本。
- **可测目标：** 数值/单位 exact match、实体报价绑定 F1、版本关系 F1、最终有效报价准确率、冲突率和 price/promo 子集 QA。

### 2. 核心数据结构

`VersionedOfferLedger`：事实键为 `entity_id + attribute + condition_scope`；每个版本保存值、币种/单位、生效时间、来源区域、来源模态、适用范围、替代/并列/冲突关系和 evidence ID。

### 3. 必要特征

1. 从 OCR 和 ASR 中抽取数值、单位、促销关系和限制条件，并保留原始时间与区域。
2. 将每一报价或主张绑定到产品实体和条件范围，未绑定项不得进入最终报价。
3. 根据时间、条件和实体判断新事实是覆盖旧事实、与旧事实并列还是冲突，不以“后出现”自动覆盖。
4. 根据问题对象、条件和时态读取对应版本，并返回原帧/ASR provenance。

### 4. 处理链

OCR/ASR 事件 → 数值、单位、条件抽取 → 产品实体绑定 → 版本写入 → 替代/并列/冲突关系判定 → 问题对象与时态查询 → 输出目标版本及原始证据。

### 5. 耦合关系

时间顺序只有结合实体和条件范围才能形成版本关系；实体绑定又依赖文字区域、ASR 和时间。三者共同决定读哪个值，不能拆成普通 OCR 加数据库。

### 6. 删除测试

删除版本边和条件范围，只向回答器提供所有 OCR/ASR 数值集合；保持文本、视图和 Token 相同，比较最终价、折扣条件、套餐差异、CTA 题及错误数字引用率。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| 现有代码只以弱关键词识别 price/scarcity/CTA，没有事实版本 | `/Users/bytedance/vqa_thesis_continue/code_refactor/evidence/evidence_package.py:55-76` | 强 |
| 价格、数字、折扣只被粗分到 OCR/Logo/local view | `/Users/bytedance/vqa_thesis_continue/code_refactor/reflection/claim_checker.py:18-26` | 强 |
| 价格、Logo、CTA 被记录为脆弱小目标 | `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md:260-264` | 中 |
| 当前申请已有跨帧文字事件和价格类补看，但没有实体、条件或版本关系 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md:203-215,241-251` | 强 |

### 8. 代码状态

- **状态：** `NOT_IMPLEMENTED`。
- **已有：** OCR/Logo/ASR 字段、时间和弱 price/promo 类型。
- **缺失：** 数值单位解析、实体绑定、条件范围、版本关系、专项数据和查询接口。

### 9. 已有实验、可验证效果与不可归因效果

- OCR 定位可提高 Region Recall，但没有证明整体 QA；不能把该结果外推为报价解析正确。
- 当前没有版本关系、实体报价绑定或 price/promo 专项实验。
- 未完成扁平数值集合删除测试前，不得声称最终有效报价准确率提高。

### 10. 与源论文差异

- `PAPER-A012 MME-VideoOCR` 已覆盖视频文字变化跟踪和跨帧整合，但没有广告报价的实体、条件和版本关系；它仍会构成“OCR 变化跟踪”部分的直接攻击。
- `PAPER-CD-012 Evidence-Backed VQA` 绑定答案与时空 masklet，不构造可查询的报价版本账本。
- 本候选不能以“识别价格”作为差异，只能以实体、条件和时间共同决定替代/并列/冲突的事实状态机划界。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请只把 OCR 作为热力图和局部视图依据，没有报价语义关系，见 `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt:13-22`。
- 当前申请已有跨帧文字事件，故不能仅增加“时间戳价格”；必须加入实体键、条件范围和版本边。

### 12. 独权骨架

一种广告视频中的报价事实解析方法，包括：从带时间信息的文字和语音事件中提取报价值、单位和适用条件；将报价事件绑定到广告视频中的产品实体；以产品实体、报价属性和适用条件为事实键写入多个时间版本；根据版本之间的实体一致性、条件范围和时间关系确定替代、并列或冲突关系；按照用户问题的对象、条件和时态读取目标版本并生成答案。

### 13. 从属降落点

1. 报价值包含原价、现价、折扣、套餐价或免费条件。
2. 条件范围包含时间、数量、会员、地区或购买组合。
3. 新版本仅在实体和条件范围一致时允许覆盖旧版本。
4. OCR 与 ASR 值冲突时保留两个来源并输出未解析状态。
5. 输出币种/单位归一结果及原始字符、框、帧和 ASR span。

### 14. 实现难度与最强审查攻击

- **难度：** 高。
- **最强攻击：** 版本化数据库、时态事实抽取、实体属性绑定和促销条件解析均有成熟基础；“报价”还可能被认为是业务数据。独权必须强调视频 OCR/ASR 的跨时证据绑定和防错误合并的技术处理，且专项题量不足会削弱技术效果。

### 15. 分类

`NEW_APPLICATION`

---

## I2B-P08 PRELIMINARY：证据副本图与删除充分证书

### 1. 技术问题与广告特性

- **技术问题：** 当前反事实训练把首个锚点、一个 OCR 框或一个时间段当作决定性证据；广告中同一事实会在 Logo、包装、口播、片尾和重复镜头中多次出现，局部删除后负样本仍支持原声明，造成错误负标签。
- **广告特性：** 重复品牌、人物、CTA、口号、包装和跨模态同义表达。
- **可测目标：** 残余支持路径率、E- 外部复验通过率、删除覆盖率、错误负标签率、每模态配对方向准确率和反事实无效率。

### 2. 核心数据结构

`EvidenceOccurrenceGraph`：事实节点连接全部视觉区域、OCR 字符串、Logo、ASR span 和时间区间；包含 `equivalence_cluster_id`、出现次数、跨模态路径、路径覆盖状态、残余支持路径数和 `DeletionSufficiencyCertificate`。

### 3. 必要特征

1. 针对待训练原子声明在全视频检索视觉、OCR、Logo 和 ASR 支持实例，并按事实等价关系聚类。
2. 将每个等价实例表示为一条可独立支持声明的路径，计算目标事实的支持路径集合。
3. 对路径集合求覆盖干预，至少破坏每条已发现支持路径，同时保持非目标背景上下文。
4. 由与构造器隔离的复验器重新搜索残余支持；只有残余路径为零或低于冻结标准时签发删除充分证书，否则标记 `counterfactual_invalid` 并禁止进入排序训练。

### 4. 处理链

原子声明 → 全视频多模态副本检索 → 事实等价聚类 → 支持路径图 → 最小覆盖干预 → 独立残余支持复验 → 签发/拒绝删除充分证书 → 仅使用有效 E+/E- 训练或校准验证器。

### 5. 耦合关系

等价聚类定义哪些实例属于同一事实，路径图把实例转换为删除覆盖约束，复验结果决定样本是否进入训练。删除图、干预和训练准入共享同一 `residual_support_path_count`，不是“检测后再遮挡”的并列流程。

### 6. 删除测试

去掉副本图，只干预首个锚点、最高分框或一个时间窗；比较残余支持率、错误负标签率和 E+→E- 配对方向。另删除独立复验器，检验构造器自证导致的无效证书比例。

### 7. 本地原始支持

| 支持点 | 本地路径与行号 | 强度 |
|---|---|---|
| 固定协议 Smoke20 仅 2/20，通用替换/马赛克未删除决定性事实 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md:15-20` | 强 |
| 候选 A/B 为 0/20、8/20，12/20 同视频负样本仍支持 | `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md:607-617` | 强 |
| 候选 B 已实现锚点排除窗口和完整 32 帧同视频替换 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_b_same_video_smoke_v1.py:109-138,198-265` | 强，实验原型 |
| 候选 D 已聚类同文本 OCR 出现并对多个框马赛克，但没有跨模态事实图 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_d_formal_data_v1.py:263-311,361-376` | 强，实验原型 |
| 当前申请只要求“破坏决定性证据并保留背景”，没有全部副本覆盖证书 | `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md:305-319` | 强，当前申请边界 |

### 8. 代码状态

- **状态：** `EXPERIMENTAL_LOCAL_IMPLEMENTATION`。
- **已有：** 锚点排除、同视频整段替换、OCR 同字符串分组、多框马赛克、像素变化审计、视频隔离和固定 Token 协议。
- **缺失：** 跨时/跨模态事实等价聚类、路径最小覆盖、独立残余搜索、删除充分证书和训练准入门禁。

### 9. 已有实验、可验证效果与不可归因效果

- 候选 A/B 的 `0/20`、`8/20` 证明单锚点/单时段干预不足。
- OCR 负例 `500/500` 发生像素变化，但固定模型 OCR 方向只有 `5/10`；像素变化不等于事实已删除。
- 当前没有有效证书样本、排序头训练或 QA 结果；`0.6599` 不归因于反事实排序，更不归因于本候选。

### 10. 与源论文差异

- `PAPER-A010 CaST-Bench` 已用遮蔽全部标注证据区域过滤可猜问题，公开“全部证据区域破坏”的强反向思路；但其证据是人工因果链和 bbox，不构建同一事实的 OCR/Logo/ASR/视觉等价副本图，也不签发训练样本删除证书。
- `PAPER-CD-012 Evidence-Backed VQA` 以 masklet 破坏证明决定性证据，但不覆盖广告中的跨模态重复事实。
- `PAPER-CD-013 DeFacto`（2025 预印本，正式年份未按本轮规则确认，背景）已公开必要区域遮挡、随机遮挡和 unknown 训练；因此“遮挡必要证据”不能作为差异。

### 11. 与自家在先申请和当前申请差异

- 自家在先申请没有反事实训练和删除证书；其重复元素仅通过热力图、锚框和双流处理。
- 当前申请权利要求8已经覆盖最小破坏证据对，见正式稿 `:77-85`。本候选不是新的“最小破坏”概念，而是对“何时可称删除充分”的必要实现约束：全路径发现、覆盖干预、独立复验和无效样本拒用。

### 12. 独权骨架

一种视频声明验证器的反事实证据构造方法，包括：针对原子声明在广告视频中检索多个模态的支持实例；将表达同一事实的支持实例聚类并构建事实到支持实例的证据副本图；确定覆盖所述证据副本图全部已发现支持路径的干预集合并生成被干预证据；由独立复验过程搜索被干预证据中的残余支持路径；仅在残余支持路径满足删除充分条件时生成删除充分证书并将证据对用于验证器训练，否则拒绝该证据对。

### 13. 从属降落点

1. 支持实例包括视觉区域、OCR 字符串、Logo、ASR span 和时间区间。
2. 等价聚类同时使用文本语义、对象身份、时间上下文和跨模态对齐。
3. 干预集合通过最小集合覆盖确定，并记录每一支持路径对应的干预算子。
4. 复验器与构造器使用不同模型版本、不同检索规则或人工双审。
5. 证书记录覆盖路径数、残余路径数、像素/音频变化哈希和无效原因。

### 14. 实现难度与最强审查攻击

- **难度：** 高。
- **最强攻击：** CaST 的全证据遮蔽、E-VQA 的 masklet 破坏、DeFacto 的必要证据遮挡与常规集合覆盖算法可组合得到大部分步骤；当前申请又已宽泛写入最小破坏。可辩护点只能是广告重复事实的跨模态等价副本图与“残余路径决定训练准入”的闭环关系，仍必须经正式专利检索。

### 15. 分类

`CURRENT_APPLICATION_ENHANCEMENT`

---

## 2. 后续门禁建议

1. 优先实验 P08：先在现有 Candidate B/D 数据上补“全副本标注、覆盖率、残余路径复验”，不训练新验证器。
2. 第二优先 P05：构造同刻冲突、时序更新、缺失三类人工小集，先检验四/五态张量和禁止抵消规则。
3. P01 可并行做 100 个短曝光文字事件标注；只比较 Pulse 与逐帧 OCR Top-K，固定 Token。
4. P02、P03、P04、P06、P07 在对应删除测试前不进入外部专利检索。
5. I3 敌对门禁应允许零候选通过；尤其不得因候选数量不足而把 M03/M08/M10 硬并入现有候选。

## 3. 已核验论文来源清单

以下仅列本文件实际用于差异分析的论文族；URL、正文位置和全文抓取哈希见 `01a/01b` 来源文件。

| paper_id | 正式身份/池角色 | 最早公开日期 | 本文件用途 |
|---|---|---|---|
| PAPER-A003 | ICCV 2025，背景 | 2025-07-25 | 对象轨迹与 mask 反向证据 |
| PAPER-A010 | CVPR 2026，2026池 | 2026-05-22 | 因果链、全证据遮蔽反向证据 |
| PAPER-A011 | CVPR 2026，2026池 | 2025-12-16 | 多段证据/MRFS 反向证据 |
| PAPER-A012 | NeurIPS 2025，背景 | 2025-05-27 | 视频 OCR 跟踪与跨帧整合反向证据 |
| PAPER-CD-002 | CVPR 2026 Findings，2026池 | 2025-12-05 | 主动观察与充分性闭环反向证据 |
| PAPER-CD-004 | CVPR 2026，2026池 | 2026-02-24 | 预算感知视频导航 |
| PAPER-CD-005 | CVPR 2026，2026池 | 2026-03-25 | 主体记忆与工具轨迹 |
| PAPER-CD-008 | arXiv 2026，2026池 | 2026-04-28 | 证据质量选择性预测 |
| PAPER-CD-012 | ECCV 2026，2026池 | 2026-07-13 | 答案、时间段与 masklet 绑定 |
| PAPER-CD-013 | 2025 预印本，背景 | 2025-09-25 | 必要证据遮挡与随机遮挡反向证据 |
| PAPER-CD-015 | CHIL 2026，2026池 | 2026-03-03 | 聚合校准和拒答失效反向证据 |
| PAPER-CD-018 | ICCV 2025，背景 | 2024-12-30 | 相似度合并在快切中的局限 |
| PAPER-CD-020 | ECCV 2026，2026池 | 2026-07-27 | 固定预算时空分配反向证据 |

## 4. 本地来源与 SHA256

### 4.1 任务、隔离构思和论文卡片

| 文件 | SHA256 |
|---|---|
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/00_brief.md` | `48113d5c3e9680ffeadc489c6174828c9c8aa1c5f61f75532883001c9ec3705d` |
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/02a_isolated_mechanisms.md` | `498435435cbfbfdce9eea20cdd6bf811ee0ff228e0e9fdca68e7e3c6e0bb4c05` |
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/02a2_broad_isolated_mechanisms.md` | `f3fc3bd103148eeddc9efd349a70ca9287105f08d4fa1b843e547c2d855c6b42` |
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/01a_paper_cards_A_B.md` | `d81dc77e8222d80e2a3e8b78ffd7fde0372bee430242d98a8ca3ed933bb85081` |
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/01a_sources_papers.jsonl` | `4a42d3c4bd8a1522b7efd8f2ec8fc444695ea4fb63f6c289bf38cf43f90b5f24` |
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/01b_paper_cards_C_D.md` | `6cd9704136a77abb2dcee655f30daa319a09e0d4f851a08b4ec36c74f600fadf` |
| `/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01/01b_sources_papers.jsonl` | `a3b10aa3259773b34dcdf7e77aebb242f73aad887d1e3425818854c3e073a847` |

### 4.2 自家申请、代码和实验原始来源

| 文件 | SHA256 |
|---|---|
| `/Users/bytedance/vqa_thesis_continue/source_texts/patent_docx.txt` | `87b9de130f3a0e4f2296d9f956af2f63bc1946961e3c05c495cf96ee12ebc24f` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/一种视频问答的答案可靠性保障方法、验证器训练方法、装置、电子设备及存储介质_20260817135947.md` | `224e09e6c3de3e2ca5ae5d1f3726fc266d4c06bbf4f1536340b6bb2d884bb2fa` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/application/新申请初稿V2.1_说明书全文_20260817.md` | `1e980b4a7dcc87ead5a368d0523f65da8a94318a21d1dee1a9bde019d8d04c7b` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/audit/01_material_inventory.md` | `e35239950d3c1cac261f63410350c75bf4f4dcc3fe425fbe02f93fb082677d6a` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/learn/patent-research/audit/05_examiner_critic_review.md` | `216f8a4d72dcf0b3cdb2cbf6b5664d24a73458b8adfa0aa5f5efae1235474e7e` |
| `/Users/bytedance/vqa_thesis_continue/docs/AdsQA实验结果总表与复现索引.md` | `0898ca7167854c68e4b56e5513a3bb8a091629974f8d62b1a993651bde6e7561` |
| `/Users/bytedance/vqa_thesis_continue/docs/创新点一阶段性负结果与论文降级方案.md` | `d8ed2f81f03d4d6d3eecc54549312abb0edd814271c58b1e2436300e013cdca6` |
| `/Users/bytedance/vqa_thesis_continue/docs/创新点一时间证据定位最终结论与复现索引.md` | `b0fa6b97fa51e7a69eb12b8c7e4780e791b0d349b0f902aa87759886b69de393` |
| `/Users/bytedance/vqa_thesis_continue/docs/方案B_多中心裁剪消融结果_20260731.md` | `0147fa5e8166dcdcbd9efa08be33938367d1201082e2d10d9912bf6c3ab4b655` |
| `/Users/bytedance/vqa_thesis_continue/docs/ReAd-R裁剪Token效率诊断_20260804.md` | `1eb301c3d4701886f7365e75cba66017d6604d8f92b08b9212e59b76acd3a14f` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/evidence/evidence_package.py` | `746cbccc5808b6c5b61cf57bced004657bd111c72f559ef7f477515fadd8c16d` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/reflection/claim_checker.py` | `7978bfe8fdcf0d6c450c25dcf12cd369fc672d95aa514142768dec02983e38bc` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/reasoning/prompt_builder.py` | `481549b37d8bf2b187ee71776b1cee3ed1c14aacb054d18a14662896599365e1` |
| `/Users/bytedance/vqa_thesis_continue/code_refactor/data/adsqa_loader.py` | `a717137b9df385fdb1d65ff086609e8e8d786a5eaadba5ea9bfe8e9d5174a877` |
| `/Users/bytedance/vqa_thesis_continue/evaluation/methods/common/qwen_video_budget.py` | `282ebeb7c7658f227acb36dbc5a477106b3955133dd3b0f0e63f30abbaf48666` |
| `/Users/bytedance/vqa_thesis_continue/evaluation/tools/build_evads_avfunnel_manifest_entropy_v1.py` | `1152edb346bc62d870a9d2e1140928e72158f2db64ac01e523885953d527c8d1` |
| `/Users/bytedance/vqa_thesis_continue/evaluation/tools/build_modality_counterfactual_train_v1.py` | `f0bbb4f1d4e61f3e4a7d6198a73aaca56b42f412d71754bb8ccb46fbe83a584a` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/failure_attribution.md` | `44c9ff0a4be631969dbb2cc124150120d07c5e28eb6bc37358370e2b2cd3b4e1` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_b_same_video_smoke_v1.py` | `720f1aa6e8eb31e64bbffc0052f64c5f4b7b58a274cf341b1e5dc7d36c217b59` |
| `/Users/bytedance/vqa_thesis_continue/ad_video_analysis_system/tmp/innovation2_stage2/build_candidate_d_formal_data_v1.py` | `94354aefe0b1eea452684679bbdcc1005134b5080223b14383347ee1f8693fe8` |

### 4.3 执行规范与模板

| 文件 | SHA256 |
|---|---|
| `/Users/bytedance/.agents/skills/patent-innovation-analysis/SKILL.md` | `04e32dbbf76c529cab1060cbdb690cb4ed611e4d1795bda4160db6d67af6fef3` |
| `/Users/bytedance/.agents/skills/patent-innovation-analysis/templates/innovation_candidate.md` | `7d5e94b427859d1dc1a1578ae1ebdce9a4fe9c6989cbc3e0889d3c2efc84d1f0` |
| `/Users/bytedance/.agents/skills/patent-innovation-analysis/templates/examiner_critic.md` | `1d2a6300bdbe6e46461a169b3aa2c599bf2725636891f2e080c02020b711ef79` |
| `/Users/bytedance/.agents/skills/patent-innovation-analysis/templates/final_recommendation.md` | `f00daaf4d63e81f1be755ab32bd989145c0456bad53a403f03a52f59af179908` |

## 5. 合规记录

- 外部专利检索：`0`。
- 正式申请稿修改：`0`。
- V2.1 修改：`0`。
- Git 操作：`0`。
- 付费 API：`0`。
- 本文件未宣称任何候选具备新颖性、创造性或最终可通过。
