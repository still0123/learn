# Qwen3 RealClaim 跨基座答案重排序 Smoke-50 预注册

## 1. 目的

本实验检验已经完成的 Qwen3 RealClaim985 声明—证据验证器能否把两种现成回答基座的互补性转化为 QA 精度，而不是继续训练 OCR、选帧或回答模型。

比较对象：

```text
A0：Clean Qwen3 + Raw8
A1：Qwen2.5 AdsSFTLoRA + Raw8
选择器：Qwen3 RealClaim985 LoRA
```

本轮只做 Train-500 五折 OOF 内的开发期 Smoke，不访问 Development244、Confirm-D 或新的独立确认集。

## 2. 数据与样本冻结

- 两组答案均来自既有视频隔离五折 OOF；
- 每题使用两方法已经审计一致的 Raw8 帧；
- 只保留两组答案均能抽取 `[Answer]` 且规范化文本不同的题目；
- 按 `SHA256(seed:question_id)` 冻结 50 题；
- 优先保证一题一视频，目标为 50 个视频；
- 抽样和选择脚本不得读取参考答案或 DeepSeek 分数。

每个候选答案只作为一个 answer-level claim。该设计是低成本 Smoke，不宣称已经实现完整的原子声明分解。

## 3. 冻结验证器与选择规则

模型保持冻结：

- 基座：`/data1/qky/Model/Qwen3Vl-8B`；
- Adapter：Qwen3 RealClaim985 LoRA；
- 8 个 Raw 全帧视图；
- 448 像素上限；
- 最多 4,096 视觉 Token；
- 相同声明验证 Prompt；
- 关闭二次帧采样。

沿用 RealClaim Calibration240 已冻结阈值：

```text
support_threshold = 0.8933094143867493
minimum_margin = 0.25
```

只有同时满足以下条件时，才将 A0 切换为 A1：

```text
score(A1) >= support_threshold
score(A0) < support_threshold
score(A1) - score(A0) >= minimum_margin
```

否则保留 Clean Qwen3。不得在 Smoke-50 上扫描阈值、margin、聚合方式或 Prompt。

## 4. QA 评分

选择结果冻结后，才允许读取两组答案在同一当前 `deepseek-v4-flash` answer-only 批次中的既有分数。只复用与候选文本 SHA256 精确匹配的分数，不新增 API 调用。

报告：

- Strict、Relaxed；
- 触发率；
- 胜/平/负；
- wrong→right、right→wrong；
- correction precision；
- 10,000 次视频级 Bootstrap；
- 视图数、Token 和二次采样协议。

## 5. 扩展门禁

只有同时满足以下条件，才允许把冻结规则扩展到全部 OOF-500：

- 至少触发 3 题；
- Relaxed 点估计高于 Clean Qwen3；
- Strict 点估计不低于 Clean Qwen3；
- `wrong→right > right→wrong`；
- Relaxed 差 Bootstrap 95% CI 下界不低于 `-5 pp`；
- 所有协议审计通过；
- 没有读取私有标签参与抽样或选择。

任一门禁失败即停止本候选，不扫描参数，也不进入独立确认集。

## 6. GPU 前可行性修订

在任何 GPU 推理和私有分数读取之前，CPU 格式预检确认：

- Qwen2.5 的 `[Answer]` 可抽取率为 `500/500`；
- Clean Qwen3 只有 `60/500` 条存在可精确回指的 `[Answer]`；
- 两侧可抽取且答案不同的 60 题只覆盖 36 个视频。

因此保持 Smoke-50 的题目数不变，先按哈希取每个视频一题，再补足至 50 题；最低视频覆盖冻结为 30，实际为 36。所有 Bootstrap 改为视频簇抽样。该修订发生在验证器推理和裁判分数读取之前，原因是输入格式可用性，不是根据实验效果放宽门禁。
