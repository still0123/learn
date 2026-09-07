# AdsSFTLoRA_Raw8 错误来源审计与选择性反思决策

**日期：** 2026-07-24  
**范围：** AdsQA Train-500 的视频级五折 OOF；冻结回答器 `AdsSFTLoRA_Raw8`。  
**运行约束：** 本次只读取已有预测、DeepSeek 历史裁判、GT、视频路径、分段 ASR 与 OCR 缓存；未使用 GPU、未调用 API、未修改任何历史预测或评分。

## 1. 目的与结论

本审计不再假定“RAG 或反思一定能提高精度”，而是先回答：现有错误是否真的缺少可新增的证据。

**结论：**

1. 不应直接做泛化的 ASR-RAG 或网页 RAG。五折 OOF 的 500 个问题均已在 `question` 字段中含有完整 `Voiceover: ... Question: ...` 文本；将分段 ASR 再检索一次通常只是重复回答器已经收到的语义。
2. 可以条件性尝试一个很小的 **OCR 证据约束反思** smoke：OCR 不是当前 Raw8 Prompt 的独立文本输入，且 `84/393` 个错误存在至少两个参考答案内容词的 OCR 重合信号。该信号不是金标，但足以支持一次有严格停止规则的工程验证。
3. 暂不做外部网页知识库。`meta_info` 与参考答案存在词重叠，只能说明数据集中存在活动背景描述，不能证明该事实在广告视频外可公平、可复现地获得。直接把 `meta_info`、论文说明或检索到的同源 campaign 文案作为回答证据会造成标签泄漏风险。
4. “画面可见”“确需外部知识”“题目/答案模糊”不能由 ASR/OCR 文本缓存可靠判定。当前 180 条清单必须经独立视觉/人工复核后，才可写出这些语义类别的比例，更不能把本次自动信号称为人工金标。

因此，本阶段的决定是：**保留视频内 OCR 证据驱动的选择性反思候选，先做 50 条 smoke；不启动通用 RAG、网页检索或新的验证器训练。**

## 2. 可追溯数据来源

| 来源 | 路径 | 本次用途 | 是否用于模型输入 |
|---|---|---|---|
| OOF GT | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/oof500_v2_audit/oof_groundtruth_separate.json` | 对错误进行离线审计 | 否 |
| OOF Raw8 预测 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/oof500_v2/fold_*/lora_raw8/*/prediction.json` | 初答 A0、错误样本定位 | A0 已冻结 |
| 历史裁判 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/judge_deepseek_legacy_answer_only_v1/results.jsonl` | `0/0.5/1` 错误分层 | 否 |
| 分段 ASR | `data/segmented_asr_pilot_train_confirm_v1/records/<video>.json` | 覆盖与时间戳可用性检查 | 仅未来证据索引候选 |
| OCR 缓存 | `data/candidate_cache_full_v1/ocr/<video>.json` | OCR 文本、框、帧号可用性检查 | 仅未来证据索引候选 |
| 视频 | `data/videos/<video>.mp4` | 后续独立视觉复核 | 否 |

本次新建的只读审计产物在远端：

```text
evaluation/runs/adsqa_sft_lora_groupcv500_v1/error_source_audit_v1/
  all_errors_source_audit.jsonl
  sample180_pending_semantic_review.jsonl
  review_protocol.json
  summary.json
```

构建工具为 `evaluation/tools/build_answer_lora_error_audit_v1.py`；本地对应脚本为 `scripts/build_answer_lora_error_audit_v1.py`。输入 GT、裁判结果及脚本 SHA256 已写入 `summary.json`。

## 3. 抽样与覆盖统计

全量 OOF 的 GT、预测和裁判均为 `500/500` 一一对应。`AdsSFTLoRA_Raw8` 的非完全正确题为 `393` 条：评分 `0` 为 `206`，评分 `0.5` 为 `187`，跨 `100` 个视频。

从中确定性抽取 `180` 条：按 `judge score (0/0.5) × fold` 比例分层，seed=`20260724`，同一视频最多两题。样本含 `94` 条 0 分、`86` 条 0.5 分，覆盖 `97` 个视频；五折分别为 `35/38/34/36/37` 条。

| 覆盖指标 | 全部 393 错题 | 180 条分层样本 |
|---|---:|---:|
| 原视频路径存在 | 393/393 | 180/180 |
| 分段 ASR record 存在，状态 success | 393/393 | 180/180 |
| OCR record 存在 | 393/393 | 180/180 |
| OCR 至少有一个检测框 | 393/393 | 180/180 |
| 参考答案与 ASR/OCR 合计至少 2 个内容词重合 | 130 | 56 |
| 有文本缓存但未达到上述答案词重合 | 263 | 124 |

额外的全量诊断：参考答案与 ASR 至少 2 个内容词重合仅 `37/393`；与 OCR 至少 2 个内容词重合为 `84/393`；与只作审计用途的 `meta_info` 至少 2 个内容词重合为 `242/393`。其中 `143/393` 属于“内部 ASR/OCR 未形成强词重合、但 meta_info 有至少 2 个重合词”的**外部/背景候选**，另有 `120/393` 在三类文本上均无强词重合。

这些是可复现的字符串信号，不是事实性语义标签：同义词、跨语种转写、OCR 错字和抽象问法都会产生漏检。因此不能把 `143` 直接报告为“外部知识题”，也不能把 `84` 直接报告为“OCR 可解题”。

## 4. 为什么 ASR-RAG 不应作为下一候选

500/500 OOF 问题均采用如下格式：

```text
Voiceover: <视频级转写>

Question: <问题>
```

所以 Raw8 回答器已经看到视频级 Voiceover。分段 ASR 的价值仅在于时间戳、不同语言转写或可引用的证据定位；它不是一个新的知识源。将原 ASR 内容以 RAG 形式重复追加，无法作为“检索带来增益”的合理实验，也会混淆 Prompt 长度与检索效果。

OCR 不同：它尚未作为独立文本证据稳定输入 Raw8，且可回指到帧号、时间戳和框。故后续唯一允许的“视频内检索”候选是 OCR 主导、ASR 只作时间定位辅助的保守纠错，而不是自由 RAG。

## 5. 代表性错误（审计示例，不是人工标注）

| qid | 评分 | 观察到的来源信号 | 审计解释 |
|---|---:|---|---|
| `116` | 0 | OCR 含 `Romanian / K-pop / 58 / audience` | 答案中的 `58%` 具有明确可检索的画面文字锚点，是 OCR 约束纠错的合格候选。 |
| `117` | 0 | OCR 含 `Instagram / polls / fans / winner` | 竞赛胜者由 Instagram polls 决定可由画面文字支持，适合要求帧号引用的纠错。 |
| `102` | 0 | 视频 ASR/OCR 未出现“influencers tag each other”；meta_info 有相关背景 | 可能需要广告外的社媒活动资料，也可能是视频外延素材。当前不能把 meta_info 当 RAG 证据。 |
| `145` | 0 | 视频文字描述 Baltic 口味，答案中的 `food bloggers` 只在 meta_info 出现 | 这是外部/背景候选，需独立观看原视频或检索公开来源后才可判断。 |
| `121` | 0 | OCR 只有 succession slogan；答案要求识别 workshop 中工具架的视觉组织 | 属于“画面可见性待复核”样例；文本缓存不足以判定。 |
| `110` | 0 | ASR/OCR 都描述控制行为，参考答案是“引发不适感”的抽象效果 | 更像语义推断或答案表达边界，不能假定额外检索即可修正。 |

## 6. 最小补充：语义来源复核 50 条

在任何 OCR 纠错候选扩大前，从现有 180 条中固定抽取 50 条做独立复核：20 条 OCR 词重合、20 条 meta-only 候选、10 条文本无重合且可能依赖画面/抽象判断。评审者可看原视频或时间联系表、问题、参考答案、ASR 和 OCR 框；必须隐藏 `meta_info`、历史预测和裁判结果。

每条选择一个主因并允许多标签：

```text
video_visible
asr_or_ocr_obtainable
external_knowledge_required
question_or_answer_ambiguous
mixed_or_other
```

必须记录帧号、OCR 框或 ASR 时间段；若判外部知识，记录“视频内未见”的具体核查理由。两位独立复核者应报告 observed agreement 与 Cohen's kappa。该 50 条不是训练集，也不是最终评测金标；它只决定是否值得投入后续 OCR-反思工作。

## 7. 预注册的后续实验设计

### 7.1 数据划分

冻结 GroupCV-500 的视频级 OOF 回答 A0 后，按未查看的固定视频哈希分为：300 题/60 视频开发集与 200 题/40 视频确认集。当前只允许使用 300 题开发集选择“是否值得继续”；200 题在实现、Prompt、检索数和门控规则冻结前不得读取其答案、历史裁判或逐题分数。

### 7.2 三臂定义

| 臂 | 输入与输出 | 用途 |
|---|---|---|
| A0 初答 | 现有冻结 `AdsSFTLoRA_Raw8` OOF 输出 | 不重跑，基线 |
| A1 无门控 OCR 反思 | 同一折 LoRA、同一 8 个 448 视图与视觉 Token；附加固定数量的 OCR 片段（文本、框、帧号）后生成一次候选答案 | 量化自由反思的收益与伤害 |
| A2 证据门控反思 | 复用 A1；只有变更答案能引用高置信 OCR 文本且变化的数字/品牌/CTA/显式名词可与引用对齐时，才用 A1 替换 A0；否则保留 A0 | 检验保守选择是否降低 `right→wrong` |

ASR 仅提供对应 OCR 帧的时间窗口，不重复追加视频级 Voiceover。禁止使用 `meta_info`、参考答案、网页检索、历史分数或裁判输出构建检索清单。所有 OCR 引用必须回指原始 cache 的 `video_id/frame_index/timestamp_sec/box/text/score`。

### 7.3 运行顺序与门禁

1. **Smoke50：** 10 个视频的完整五题包。只检查三臂输出结构、8 视图/Token 不变、OCR 引用存在、无答案泄漏、A2 可复算；不以 50 条准确率挑 Prompt。
2. **Dev300：** Smoke 通过后，以完全冻结的 OCR 选择、Prompt、门控和 LoRA 权重运行 60 个视频/300 题。DeepSeek 只在推理和协议审计后按既有 answer-only 口径评分；A0 分数复用，A1 去重裁判。
3. **Confirm200：** 仅当 Dev300 中 A2 的 Relaxed 点估计不低于 A0、`wrong→right > right→wrong`、修正精度高于 50%，且视频簇 Bootstrap 没有明确负向证据时，才对冻结 40 视频运行一次。失败即停止该 OCR-反思候选，不扫描 OCR top-k、阈值、Prompt 或反思轮数。

### 7.4 指标

所有三臂同题报告：Strict、Relaxed、`wrong→right`、`right→wrong`、修正精度 `wrong→right / (wrong→right + right→wrong)`、rescue rate、harm rate、A2 触发率、有效 OCR 引用率、平均与 P95 延迟、语言/视觉 Token 和 10,000 次视频簇 Bootstrap。A0 与 A2 的逐题胜平负和类型/证据可用性分层也必须保留。

## 8. 停止规则

- OCR citation 无法可靠回指缓存，或 Smoke 出现答案/`meta_info` 泄漏：停止。
- Dev300 的无门控 A1 伤害明显而 A2 也无法把伤害降到纠正收益以下：停止，不改为普通思维链。
- 50 条独立复核显示多数 meta-only 错题实际属于抽象/含混标签，而非可公开检索事实：停止外部 RAG 设计。
- 只有在独立复核确认存在足够多“视频外、公开且版本化可取得”的事实后，才另行设计外部知识快照与公平性协议；这是一条新候选，不与当前 OCR 反思混合。

## 9. 后续结构化证据链验证结果（2026-07-27）

在 OCR 约束反思失败后，进一步测试了更强但仍受控的结构化思维链：冻结 A0，A1自由反思，A2要求原子声明、所需模态、帧/OCR/ASR引用和E+/E-反事实，A3只在候选声明全部受支持、有可追溯引文、A0存在被反驳声明且反事实支持下降时改答。50题工程审计通过，引文回指率100%，但反事实支持下降仅28%，A3触发0次。

当前统一DeepSeek评分下，A0/A1/A2/A3的Strict为`18/18/20/18%`，Relaxed为`31/31/29/31%`。A2相对A0表现为Strict `+2 pp`而Relaxed `-2 pp`；A3没有任何纠正。该候选已冻结为`candidate_failed_no_dev300`，不扩到300题。结论是：错误来源审计提出的“视频内证据约束”确实能实现可追溯输出，却仍不足以形成稳定的答案纠错规则；继续增加普通思维链轮数或放宽门控不再是合理下一步。
