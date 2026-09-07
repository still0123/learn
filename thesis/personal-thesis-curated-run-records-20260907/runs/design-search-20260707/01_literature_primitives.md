# P1 文献吸收摘要

本轮 P1 联网与本地文档结合，得到的核心结论：

```text
AdsQA 方案最该吸收的是：
证据槽 + 输入重构 + 低噪声知识许可 + 声明级约束。

不应把普通 token compression、crop、RAG、self-check 当主创新。
```

## 1. 广告视频理解

| 文献 | 技术原语 | 对 AdsQA 的启发 |
|---|---|---|
| AdsQA | 广告 VideoQA benchmark、ReAd-R | 广告证据槽需覆盖品牌、卖点、受众、情绪、CTA |
| VideoAds | 快节奏广告理解、高 FPS、短时证据 | 输入重构要防止漏掉闪现字幕、Logo、价格 |
| AD-MIR | 结构化记忆、营销专家推理、自校验 | 差异必须落在 evidence_id、证据触发 RAG、声明许可 |

## 2. 视频压缩 / 帧选择 / 输入重构

| 文献 | 技术原语 | 不能照搬 | 对 AdsQA 的启发 |
|---|---|---|---|
| BIMBA | selective-scan 视频 token 压缩 | 通用长视频效率，不关注广告细粒度证据 | evidence-preserving input reconstruction |
| PruneVid | training-free token merging + question-aware pruning | 普通 pruning 可能误删小字、价格、Logo | 广告证据槽作为不可剪约束 |
| Dynamic-VLM | 动态视觉 token 压缩 | 动态压缩本身已不新 | 动态性转成证据槽预算 |
| Q-Frame | query-aware frame selection + multi-resolution adaptation | 未区分广告证据类型 | OCR/Logo/CTA 槽控制分辨率 |
| GenS | 生成式帧采样 | 训练数据成本高 | 可作为强 baseline 或启发候选帧召回 |
| Frame-Voyager | 学习最优帧组合 | 训练/枚举成本高 | 轻量 temporal diversity，避免全选同一镜头 |

## 3. 局部细节 / OCR / 时空定位

| 文献 | 技术原语 | 不能照搬 | 对 AdsQA 的启发 |
|---|---|---|---|
| FOCUS | KV cache / object relevance map crop | attention/crop 已被占位 | local crop 必须绑定 evidence_id、slot、timestamp、bbox |
| ZoomEye | 树状区域搜索、zoom-in | 直接全局到局部不新 | 只有证据槽缺口触发 zoom |
| EgoTextVQA | scene-text aware VideoQA | ego-view，不是广告 | OCR 类型化为 brand/price/claim/disclaimer/CTA/audience |
| ReVisionLLM | coarse-to-fine temporal grounding | 小时级视频，不是短广告 | 短广告密集证据定位 |
| Grounded Multi-Hop VideoQA | 多时间段 evidence | egocentric long-form | 旁白、画面、字幕形成广告证据链 |
| Object-centric VideoQA | object grounding/referring | 通用对象，不含广告语义 | 商品、Logo、包装升级为广告证据对象 |
| TCRT | LLM prior + task-aware grounding | 静态图像 grounding | 广告问题类型转成 grounding prior |

## 4. Video RAG / 证据验证 / 声明许可

| 文献 | 技术原语 | 不能照搬 | 对 AdsQA 的启发 |
|---|---|---|---|
| ViG-RAG | temporal knowledge graph、semantic-temporal retrieval | 普通 Video RAG 会引入噪声 | 只做证据槽触发式低噪声 RAG |
| VideoRAG | 视频语料检索增强 | AdsQA 核心是当前广告证据，不是跨视频事实 | 外部知识不能替代视频事实 |
| VideoStir | spatio-temporal + intent-aware RAG | 面向长视频通用理解 | query = question + slot + observed evidence |
| Entailment Tree | video-grounded 子命题验证 | commonsense QA，不含知识越权控制 | 广告声明类型许可 |
| EV2-Bench | spatio-temporal evidence-grounded benchmark | 长视频评测 | AdsQA evidence audit set |
| MM-Verify | 多模态 verifier | 训练成本高 | 先做规则 + LLM 轻量声明许可 |
| MJ1 | observations → claims → verification → scoring | 主要是 judge | 显式记录 evidence support state |

## 5. 需要重点核查

- AD-MIR：目前以 arXiv/OpenReview 为主，正式 venue 需核查。
- MJ1：目前以 arXiv 为主，正式 venue 需核查。

