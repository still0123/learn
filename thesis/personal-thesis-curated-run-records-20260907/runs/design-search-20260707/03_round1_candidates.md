# P3 第一轮候选技术方案

本轮目标：基于 2025-2026 文献原语和现有 AdsQA pipeline，生成可在中期后继续实验的候选方案。候选方案必须能在当前 evidence no-RAG 成功基础上升级，而不是另起炉灶。

---

## Candidate 1：AdSlot-IR，广告证据槽驱动的输入重构

### 一句话目标

把当前“统一 top-k 选帧”升级为“根据广告问题证据槽自适应分配帧、局部图、ASR/OCR 预算”的输入重构方法。

### 借鉴文献与化用方式

- BIMBA / PruneVid / Dynamic-VLM：借鉴“视频冗余高、需要问题相关压缩”，但不做普通 token pruning。
- Q-Frame / Frame-Voyager：借鉴 question-aware frame selection 和 multi-resolution adaptation。
- VideoAds：借鉴广告视频短时密集证据特点。

化用方式：

```text
不是学习通用压缩器，而是构造广告证据槽：
brand/logo, product, price, claim, disclaimer, CTA, audience, emotion, persuasion。

每个问题先路由到一个或多个 evidence slots，再按 slot 分配：
global frames / local crops / ASR snippets / OCR snippets / temporal diversity。
```

### 解决的 AdsQA 问题

- 统一 top-k 可能漏掉短时字幕、价格、Logo、CTA。
- 不同问题需要不同证据：品牌题和情绪题不该用同样输入预算。

### 技术流程

1. Question -> question_type -> evidence_slots。
2. 候选帧过采样。
3. 每个 frame 计算 visual_score、asr_score、ocr_score、ad_salience_score、temporal_diversity_score。
4. 根据 slot 权重融合 evidence_response_score。
5. 输出 global_context_frames + slot-specific evidence snippets。
6. 构造 evidence package 并送入 Qwen3。

### 新增模块

- `slot_router.py`
- `slot_budget_allocator.py`
- evidence package 落盘字段：slot、score、source_type。

### 可复用模块

- 原始 `inference.py` 的过采样和 CLIP 选帧。
- `code_refactor/evidence/evidence_package.py`
- `code_refactor/reasoning/prompt_builder.py`

### 预期提升问题类型

- 品牌/商品识别；
- 价格/促销；
- CTA；
- 广告卖点；
- 目标受众/情绪。

### 主实验

- qwen3 raw uniform；
- qwen3 evidence no-RAG；
- qwen3 AdSlot-IR no-RAG。

### 消融

- 去 ASR；
- 去 OCR；
- 去 ad_salience；
- 固定 top-k vs slot adaptive budget；
- equal-frame budget。

### 风险

- 如果 slot router 只是 prompt/规则，会被质疑工程启发式。
- 必须报告中间指标：slot 命中率、evidence hit rate、equal-budget accuracy。

---

## Candidate 2：TypedText-Loc，广告文字类型化与局部证据视图

### 一句话目标

把 OCR 从“额外文本”升级为“广告文字证据对象”，根据 brand/price/claim/disclaimer/CTA/audience 等类型触发局部高清证据视图。

### 借鉴文献与化用方式

- EgoTextVQA：视频文字、多帧、高分辨率、temporal grounding 很关键。
- FOCUS / ZoomEye / ViCrop：局部看图有效，但不能照搬普通 crop。
- Object-centric VideoQA：对象级 grounding/referring 思路。

化用方式：

```text
OCR text + bbox -> ad_text_type -> slot-triggered local crop。

局部图必须绑定：
evidence_id, frame_id, timestamp, bbox, text, ad_text_type, trigger_slot。
```

### 解决的 AdsQA 问题

- 广告中价格、折扣、CTA、小字免责声明容易被低分辨率帧忽略。
- 普通 OCR 拼接无法保留文字所在画面和视觉语境。

### 技术流程

1. 对候选帧跑 OCR 或读取已有 OCR。
2. OCR 文本规则/LLM 分类为 brand/price/claim/disclaimer/CTA/audience。
3. 根据问题 slot 选择相关 OCR bbox。
4. 裁剪局部高清图，并保留全局 frame。
5. Prompt 中同时提供 typed OCR text 与 local evidence view。

### 新增模块

- `typed_ocr.py`
- `local_crop_builder.py`
- OCR/局部图 evidence package 字段。

### 可复用模块

- 当前 dynamic crop / local view 思路。
- `prompt_builder.py`

### 预期提升问题类型

- 价格/折扣；
- 品牌/Logo；
- 功效卖点；
- CTA；
- 限制条件/免责声明。

### 主实验

- global only；
- raw OCR text only；
- typed OCR；
- typed OCR + local crop。

### 消融

- OCR typed vs untyped；
- local crop vs no crop；
- random crop vs slot-triggered crop。

### 风险

- OCR bbox 质量可能限制效果。
- 如果没有真实 OCR，只能做近似，实验可信度会弱。

---

## Candidate 3：AV-Offset Routing，声画错位感知的证据路由

### 一句话目标

针对广告中旁白与画面不同步的问题，构建 ASR-neighborhood 与视觉帧的错位补偿路由，避免只看同一时间戳导致证据遗漏。

### 借鉴文献与化用方式

- ReVisionLLM / Grounded Multi-Hop VideoQA：借鉴 temporal evidence 和多段证据。
- ED-VTG / VideoITG：借鉴 query enrichment 与 temporal grounding。
- VideoAds：广告快节奏、短时证据依赖高 FPS。

化用方式：

```text
不是长视频粗到细定位，而是在短广告中对 ASR 与视觉证据做 window-shift matching。

对每个 ASR segment 检索 t-k 到 t+k 的视觉候选帧，
为 audio-leading / audio-lagging / sync 三类关系打分。
```

### 解决的 AdsQA 问题

- 旁白先说卖点，画面后展示商品；
- 画面展示 Logo，旁白后解释品牌；
- 结尾 CTA 与口播可能错位。

### 技术流程

1. ASR segment -> semantic embedding / keyword。
2. 构造时间窗口：同步、前移、后移。
3. 对窗口内视觉帧计算 question-ASR-visual 三方相关性。
4. 输出 evidence chain：speech evidence -> visual support frame -> OCR/CTA。
5. 与 AdSlot-IR 的 frame score 融合。

### 新增模块

- `av_offset_router.py`
- audio-visual evidence chain 字段。

### 可复用模块

- ASR 文件；
- 原始帧选择；
- evidence package。

### 预期提升问题类型

- 旁白解释类；
- 卖点/功效；
- 受众/情绪；
- CTA。

### 主实验

- visual only；
- ASR same-time；
- ASR window ±k；
- AV-offset adaptive routing。

### 风险

- 如果 ASR 时间戳不准，收益不稳定。
- 需要构造 audio-leading/audio-lagging 子集，否则 overall 提升可能不明显。

---

## Candidate 4：SlotRAG-KB，证据槽触发式低噪声广告知识检索

### 一句话目标

把失败的普通 RAG 改成“只有视频证据触发相应广告语义槽时，才允许检索 top-1/top-2 营销知识”的受控知识注入。

### 借鉴文献与化用方式

- ViG-RAG / VideoRAG / VideoStir：借鉴结构化检索和 intent-aware RAG。
- AD-MIR：借鉴广告专家知识与结构化记忆。

化用方式：

```text
不做开放式 Video RAG。
query = question + evidence_slot + observed_evidence。
knowledge 只能解释视频证据，不能替代视频事实。
```

### 解决的 AdsQA 问题

- 营销策略、受众、情绪诉求需要领域概念；
- 但 naive RAG 容易引入噪声，当前实验已失败。

### 技术流程

1. 从 evidence package 中识别可触发营销知识的 slots。
2. 构造 slot-aware query。
3. dense + lexical / lexical MVP 检索 top-1/top-2。
4. knowledge 与 evidence_id 绑定。
5. Prompt 中标注：知识只能辅助解释，不允许支持视频中未出现事实。

### 新增模块

- `slot_triggered_rag.py`
- `knowledge_permission.py`

### 可复用模块

- `rag/retriever.py`
- `embedding_retriever.py`
- `prompt_builder.py`

### 预期提升问题类型

- 营销策略；
- 受众；
- 情绪诉求；
- 广告意图；
- 说服方式。

### 主实验

- no-RAG evidence；
- naive RAG；
- slot-triggered RAG；
- slot-triggered RAG + knowledge-only blocking。

### 风险

- 可能仍不提升 overall accuracy。
- 应以 unsupported claim rate、knowledge override rate 作为辅助指标。

---

## Candidate 5：ClaimPermit，广告答案声明级证据许可

### 一句话目标

将答案拆成视觉事实、文字事实、语音事实、营销语义和知识声明，只有满足对应证据条件的声明才能进入最终答案。

### 借鉴文献与化用方式

- Entailment Tree：借鉴子命题验证。
- EV2-Bench / VideoZeroBench：借鉴 evidence-grounded evaluation。
- MJ1 / MM-Verify：借鉴 observations -> claims -> verification。

化用方式：

```text
不是普通 self-check。
每个 claim 必须绑定 claim_type 和 required_evidence_type：
visual_fact, text_fact, speech_fact, marketing_semantic, audience_inference, knowledge_only。
```

### 解决的 AdsQA 问题

- 模型容易凭常识生成营销解释；
- RAG 容易输出视频中未出现的内容；
- 结构化答案更受 judge 偏好但可能无证据。

### 技术流程

1. 初始答案 -> claim split。
2. claim_type classification。
3. 根据 claim_type 查 evidence package。
4. 输出 supported / contradicted / insufficient / knowledge_only。
5. 对 insufficient 或 knowledge_only claim 降级、删除或标注不确定。

### 新增模块

- `claim_permission.py`
- `answer_rewriter.py`
- audit 输出字段。

### 可复用模块

- `reflection/claim_checker.py`
- `evidence_package.py`

### 预期提升问题类型

- 营销策略；
- 目标受众；
- 情绪；
- 需要解释的开放题。

### 主实验

- no permission；
- permission check only；
- permission + answer rewrite；
- permission + slot-triggered RAG。

### 评价

- strict/relaxed；
- unsupported claim rate；
- downgrade precision；
- knowledge-only claim rate；
- 人工 audit 200-300 条。

### 风险

- 如果只靠规则，技术含量会被质疑。
- 需要人工 audit，否则很难证明有效。

---

## Candidate 6：AdEvidence Audit Set，广告证据支持评测子集

### 一句话目标

构造 300 条广告证据支持审计集，用来验证候选方法是否真的降低无证据声明、知识越权和证据错配。

### 借鉴文献与化用方式

- EV2-Bench / VideoZeroBench / VISTAQA：借鉴答案-证据联合评测。
- EgoTextVQA：借鉴文字证据专项分析。

化用方式：

```text
不做大规模新 benchmark。
只抽 300 条 AdsQA 样本，标注：
answer claims、required evidence、support state、error type。
```

### 解决的 AdsQA 问题

- overall accuracy 可能无法体现可靠性；
- RAG/verifier 失败需要解释；
- 论文需要证据支撑指标。

### 技术流程

1. 从 3000 实验样本中分层抽 300 条。
2. 覆盖 OCR/Logo/价格/CTA/营销策略/受众/情绪。
3. 人工或半自动标注 claim support。
4. 计算 evidence support rate、unsupported claim rate、knowledge override rate。

### 新增模块

- `audit_sampler.py`
- `audit_annotation_template.csv`
- `audit_metrics.py`

### 可复用模块

- `aggregate_results.py`
- `claim_checker.py`

### 预期价值

- 即使 overall accuracy 提升有限，也能证明方法提升可信度。
- 支撑答辩中“不是模块拼接，而是证据许可机制”的论点。

### 风险

- 它更像评价贡献，不适合单独作为主创新。
- 需要人工时间。

