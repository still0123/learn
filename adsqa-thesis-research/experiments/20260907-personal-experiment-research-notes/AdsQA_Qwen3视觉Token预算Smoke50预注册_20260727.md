# AdsQA Qwen3 视觉 Token 预算与证据分配 Smoke-50 预注册

日期：2026-07-27

## 1. 研究问题

本实验回答两个彼此分离的问题：

1. 在相同 8 个均匀帧、相同干净 Qwen3、相同 Prompt 下，单纯增加视觉 Token 是否提高 AdsQA 回答精度；
2. 在与高预算 Raw8 完全相同的视觉 Token 和视图数下，把局部细节以问题相关的 ASR/OCR PiP 形式呈现，是否优于单纯提高全帧分辨率。

实验是机制诊断 Smoke，不访问 Development244 或 Confirm-D，不训练模型，不扫描参数。

## 2. 冻结数据

- 来源：`adsqa_sft_lora_groupcv500_v1/oof500_v2_audit/oof_questions_answer_free.json`；
- 仅选择既有 `pip8_manifest_v1` 中至少有一个合法 ASR/OCR PiP 证据框的问题；
- 每个视频只取一题；
- 五折固定配额为 `10/8/11/10/11`，共 50 题、50 个视频；
- 折内先按 `sha256("token-budget-smoke50-v1|" + video_id)` 排序视频，再按相同种子的题目哈希选择一题；
- 构建阶段禁止读取参考答案、模型预测、裁判分数或 `meta_info`。

配额由 answer-free 可行性预检决定：五折可用证据视频数为 `12/8/13/10/13`。

## 3. 四个实验臂

| 方法 | 视图 | 尺寸 | 预期实际视觉 Token | 说明 |
|---|---:|---:|---:|---|
| `CleanQwen3_Raw8_1K` | 8 | 512 | 约 1,024 | 精确复用既有 Clean Qwen3 OOF 结果 |
| `CleanQwen3_Raw8_2K` | 8 | 672 | 约 2K，按实测报告 | 同一帧，只提高全帧分辨率 |
| `CleanQwen3_Raw8_4K` | 8 | 896 | 约 4,096 | 同一帧，只提高全帧分辨率 |
| `CleanQwen3_EvidenceMix8_4K` | 8 | 896 | 与 Raw8-4K 相同 | 最多两帧加入既有 ASR/OCR 证据框的上下文—细节 PiP |

共同设置：

- 模型：干净 `/data1/qky/Model/Qwen3Vl-8B`；
- 不加载 LoRA；
- 8 个源帧的帧号必须逐题完全一致；
- Prompt、ASR、解码参数相同，`do_sample=false`；
- 关闭模型内部二次帧采样；
- 输出上限 256 Token；
- 所有新结果写入独立 run，不覆盖历史结果。

`EvidenceMix8_4K` 的操作定义冻结为既有 PiP 方法：保留完整帧，在与源证据框相反的角落叠加局部放大，同时标出原区域；不额外增加视图。它只检验“同预算下结构化呈现局部证据”，不把更多 Token 本身算作方法创新。

## 4. 协议审计

推理评分前必须确认：

- 四臂均为 50/50，错误为 0；
- 50 个视频唯一，折配额符合预注册；
- 四臂模型配置与 Prompt 哈希一致；
- Raw1K、Raw2K、Raw4K 的 8 个源帧逐题一致；
- EvidenceMix 与 Raw4K 的源帧、实际视觉 Token 逐题一致；
- Raw1K < Raw2K < Raw4K 的实际视觉 Token 顺序成立；
- EvidenceMix 每题至少应用一个、最多两个冻结 PiP；
- 关闭二次采样；
- 构建与推理均未读取参考答案、裁判分数或 `meta_info`。

若 Token 顺序、帧对齐或 EvidenceMix/Raw4K 同预算任一失败，则停止评分并修复工程协议；不得解释精度。

## 5. 评分与指标

协议通过后，才允许在用户单独授权下使用统一 answer-only DeepSeek 裁判。可对 `CleanQwen3_Raw8_1K` 精确复用同一历史批次分数，但必须同时匹配题号、GT、候选答案文本和 SHA256；其余答案按同一模型、Prompt和解析口径新增评分。

报告：

- Strict、Relaxed；
- 0/0.5/1 分布；
- 逐题胜/平/负；
- `wrong→right`、`right→wrong`；
- 50 个视频簇 10,000 次 Bootstrap；
- 平均/最小/最大视觉 Token；
- 平均延迟及相对 Raw1K 的成本。

## 6. 冻结判定

主比较为 `EvidenceMix8_4K` 对 `Raw8_4K`。进入新的 300 题独立开发实验必须同时满足：

1. 协议审计通过；
2. Relaxed 点估计提高；
3. Strict 点估计不下降；
4. 逐题胜数大于负数；
5. `right→wrong` 不超过 1；
6. Relaxed 差值 Bootstrap 95% CI 下界不低于 -5 pp。

预算曲线 `Raw1K/2K/4K` 只回答更多 Token 是否有价值，不参与主方法门禁。若 Raw4K 优于 Raw1K，但 EvidenceMix 不优于 Raw4K，只能得出“分辨率有效、当前证据呈现无额外收益”；若 EvidenceMix 优于 Raw4K，才支持自适应证据预算分配方向。

本 Smoke 完成前不得改尺寸、PiP 数量、裁剪比例、Prompt或抽样规则。失败后不在同一 50 题上扫描参数。
