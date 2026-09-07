# P9 最终 Top 方案与实验路线

日期：2026-07-07

本轮根据 P1 文献吸收、P2 当前 pipeline 映射、P5 创新性审查、P6 实验设计和 P7 反方审稿结果，最终不采用 6 个方案并列的写法，而将其合并为 3 个可实验路线。

核心判断：

```text
主线不能是 token pruning + crop + RAG + self-check 的模块拼接。

更稳的主线是：
广告证据槽驱动的输入重构
-> 文字/局部/声画错位证据增强
-> 声明级证据许可与可靠性审计
```

---

## 最终排名表

| 排名 | 方案 | 创新性 | 广告贴合度 | 可实现性 | 实验可验证性 | 论文叙事 | 风险可控 | 总评 |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | AdSlot Evidence Reconstruction | 4 | 5 | 4 | 5 | 5 | 4 | 主创新，优先远端 3000 |
| 2 | TypedText + Local Evidence View | 3 | 5 | 4 | 4 | 4 | 3 | 与方案1合并为输入重构增强，但可单独做 3000 对照 |
| 3 | Claim-level Evidence Permission | 4 | 4 | 3 | 4 | 5 | 4 | 可靠性贡献，accuracy 未必最大，但论文价值高 |
| 4 | AV-Offset Evidence Routing | 4 | 4 | 3 | 3 | 4 | 3 | ASR 子集强时可替代第3名 |
| 5 | Slot-triggered Knowledge Permission | 3 | 4 | 4 | 3 | 3 | 3 | 不作为主创新，作为 ClaimPermit/RAG 对照 |
| 6 | AdEvidence Audit Set | 2 | 5 | 4 | 4 | 4 | 4 | 必做评价资产，不作为独立方法 |

---

## Top 1：AdSlot Evidence Reconstruction

中文名：

```text
广告证据槽驱动的多模态输入重构
```

合并来源：

- Candidate 1 AdSlot-IR；
- Candidate 2 的 typed OCR 思路；
- Candidate 3 的 ASR/visual temporal routing 的轻量部分。

### 技术目标

将当前 evidence no-RAG 的统一帧选择，升级为：

```text
question -> evidence slots -> slot-adaptive budget -> evidence package
```

每个问题根据广告证据槽动态决定：

- 选多少全局帧；
- 是否强化 OCR/ASR；
- 是否保留结尾 CTA；
- 是否需要局部高分辨率视图；
- 是否需要 temporal diversity。

### 借鉴但不照搬

- 借鉴 BIMBA/PruneVid/Dynamic-VLM 的证据保留型压缩动机，但不做通用 token pruning；
- 借鉴 Q-Frame/Frame-Voyager 的 question-aware 选帧，但不做普通 query-frame matching；
- 借鉴 VideoAds 的快节奏广告短时证据；
- 差异落在广告证据槽和 slot-adaptive budget。

### 远端 3000 主实验

| 方法 | 样本 | 目的 |
|---|---:|---|
| qwen3 raw uniform | 3000 | 同底座均匀基线 |
| qwen3 evidence no-RAG | 3000 | 当前最强内部基线 |
| AdSlot Evidence Reconstruction | 3000 | 验证广告证据槽输入重构 |

关键消融：

- 去 ASR；
- 去 OCR；
- 去 ad_salience；
- fixed top-k vs slot-adaptive budget；
- equal-frame/equal-token 对照。

成功判据：

- strict/relaxed 高于 evidence no-RAG；
- OCR/CTA/brand/product 子集提升；
- evidence package 中 slot/source 分布可解释；
- equal-budget 下仍不劣于当前 evidence no-RAG。

---

## Top 2：TypedText + Local Evidence View

中文名：

```text
广告文字类型化与局部证据视图
```

### 技术目标

将 OCR 从“额外文本”升级为广告文字证据对象：

```text
OCR text + bbox + timestamp
-> ad_text_type
-> slot-triggered local evidence view
```

广告文字类型包括：

- brand_text；
- price_text；
- claim_text；
- disclaimer_text；
- cta_text；
- audience_text。

### 借鉴但不照搬

- 借鉴 EgoTextVQA 的 scene-text VideoQA；
- 借鉴 FOCUS/ZoomEye 的局部看图；
- 不主张“crop 新”，而主张“广告文字证据对象化”和“证据槽触发局部图”。

### 远端 3000 主实验

| 方法 | 样本 | 目的 |
|---|---:|---|
| qwen3 evidence no-RAG | 3000 | 当前证据基线 |
| raw OCR text only | 3000 | 验证普通 OCR 拼接 |
| typed OCR | 3000 | 验证广告文字类型化 |
| typed OCR + local evidence view | 3000 | 验证局部证据视图 |

关键消融：

- typed vs untyped；
- local crop vs no crop；
- random crop vs slot-triggered crop；
- OCR-heavy 子集。

成功判据：

- price/discount/CTA/disclaimer/OCR-heavy 子集显著提升；
- local crop usefulness 在 audit 中有支撑；
- 不是简单多喂图：random crop 对照弱于 slot-triggered crop。

---

## Top 3：Claim-level Evidence Permission

中文名：

```text
广告答案声明级证据许可
```

合并来源：

- Candidate 5 ClaimPermit；
- Candidate 4 SlotRAG-KB 的 knowledge permission；
- Candidate 6 AdEvidence Audit Set 的评价方法。

### 技术目标

把答案拆成声明，并按声明类型设置证据门槛：

| claim_type | required evidence |
|---|---|
| visual_fact | visual frame / local view |
| text_fact | OCR / subtitle / local text crop |
| speech_fact | ASR |
| marketing_semantic | video evidence + allowed marketing knowledge |
| audience_inference | visual/person/scene/text evidence |
| knowledge_only | 不允许单独输出，需降级或删除 |

### 借鉴但不照搬

- 借鉴 Entailment Tree / MM-Verify / MJ1 的 claim verification；
- 借鉴 EV2-Bench 的 evidence-grounded evaluation；
- 差异落在广告声明类型、knowledge-only blocking 和证据许可状态。

### 远端 3000 主实验

| 方法 | 样本 | 目的 |
|---|---:|---|
| evidence no-RAG | 3000 | 当前基线 |
| AdSlot/TypedText answer without permission | 3000 | 无许可版本 |
| ClaimPermit check only | 3000 | 只标注 claim state |
| ClaimPermit + answer rewrite | 3000 | 验证降级/删除无证据声明 |

辅助 audit：

- 从 3000 中抽 300 条；
- 标注 evidence support rate；
- unsupported claim rate；
- knowledge override rate；
- downgrade precision。

成功判据：

- accuracy 不明显下降；
- unsupported claim rate 明显下降；
- knowledge-only claim 被有效阻断；
- 对营销语义题的解释更可支撑。

---

## 备选：AV-Offset Evidence Routing

如果 ASR 时间戳质量好，且 screening 发现 ASR-dependent 子集提升明显，可将它替换 Top3。

主实验：

- same-time ASR；
- ASR window ±k；
- adaptive offset routing。

重点看：

- audio-leading；
- visual-leading；
- sync；
- selling point / CTA / speech-dependent 子集。

---

## 不建议作为主创新的方向

### Slot-triggered RAG

保留为辅助对照，不做主创新。原因：

- ViG-RAG、VideoRAG、VideoStir、AD-MIR 覆盖很近；
- 当前 naive RAG/verifier 实验明显失败；
- 更适合作为 ClaimPermit 中的 knowledge permission 部分。

### AdEvidence Audit Set

必须做，但它是评价资产，不是主算法贡献。

---

## 远端实验执行路线

### Step 0：固定 balanced-3000

所有方案共用同一批 3000 样本。

建议抽样：

| 类型族 | 数量 |
|---|---:|
| brand / logo / product | 600 |
| price / discount / CTA / disclaimer / OCR-heavy | 700 |
| speech / selling point / claim / function | 500 |
| audience / emotion / persuasion / intent | 600 |
| generic visual fact / scene / action | 400 |
| mixed hard cases | 200 |

### Step 1：跑两个基线

1. `qwen3_raw_uniform_3000`
2. `qwen3_evidence_norag_3000`

### Step 2：跑 Top3

1. `adslot_ir_3000`
2. `typedtext_local_3000`
3. `claimpermit_3000`

### Step 3：自动指标

- strict；
- relaxed；
- coverage；
- by question type；
- by expected slot；
- by evidence source。

### Step 4：人工 audit 300

从 3000 中抽 300 条：

| 子集 | 数量 |
|---|---:|
| OCR-heavy | 70 |
| ASR-dependent | 60 |
| brand/product/logo | 50 |
| marketing/audience/emotion | 70 |
| baseline 错误难例 | 50 |

---

## 下一步

1. 连接远端 `adsqa`。
2. 进入 `/data1/rmx/projectb/AdsQA-main`。
3. 检查当前是否已有 3000 抽样脚本和 latest evidence no-RAG 推理脚本。
4. 若无，先复制/改造现有 balanced2500 脚本为 balanced3000。
5. 优先跑：
   - raw uniform 3000；
   - evidence no-RAG 3000；
   - adslot_ir_3000。

