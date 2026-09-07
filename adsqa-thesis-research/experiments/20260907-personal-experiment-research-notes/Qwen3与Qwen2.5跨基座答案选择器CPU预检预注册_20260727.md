# Qwen3 与 Qwen2.5 跨基座答案选择器 CPU 预检预注册

日期：2026-07-27  
状态：在训练选择器和查看其 OOF 指标前冻结

## 1. 目的

当前同批 DeepSeek 评分显示：

- `CleanQwen3_Raw8`：Strict/Relaxed=`26.0/41.2%`；
- `Qwen25AdsSFTLoRA_Raw8`：Strict/Relaxed=`21.4/40.2%`；
- 两者逐题 Oracle：Strict/Relaxed=`36.4/54.7%`。

Oracle 只说明两个模型存在互补，不能作为可部署结果。本预检只回答：

> 能否利用推理时可见的问题、Voiceover 和两模型输出结构，在视频隔离 OOF 中学到一个不读取参考答案的保守选择规则？

该预检不直接构成创新点二，也不声称提升已得到独立确认；只有通过门禁，才允许进一步设计“证据充分性驱动的跨基座选择”。

## 2. 数据与隔离

- 数据：AdsQA Train-500，100个视频；
- 基础答案均为已有视频隔离五折 OOF：
  - 干净 Qwen3 Raw8；
  - Qwen2.5 AdsSFT-LoRA Raw8；
- 选择器沿用相同五折视频划分；
- 每次外层验证只在20个未参与该选择器训练的视频上评测；
- 训练标签来自当前批 `deepseek-v4-flash` 的 `0/0.5/1` 评分，必须标记 `not_human_gold=true`；
- 分数相同的样本不参与二分类训练，但保留在验证指标中；
- 不访问 `meta_info`、参考答案、历史裁判输出文本、视频外知识或确认集。

## 3. 冻结输入特征

只使用推理时可见信息：

1. 问题与 Voiceover 的长度、数字和词汇统计；
2. 两模型完整响应及 answer-only 区段的长度、唯一词比例、数字数量；
3. 是否存在合法 `[Answer]` 标记、回答是否疑似截断；
4. 各答案与问题、Voiceover、各自 Observation 区段的词汇重合；
5. 两答案之间的词汇重合、长度差、数字一致性和精确相同标记。

禁止加入：

- 参考答案及其任何字符串特征；
- `meta_info`；
- DeepSeek 分数、裁判文本或由分数派生的逐题特征；
- 视频 ID、题目 ID、fold ID 的数值编码；
- 旧实验方法名、历史胜负或人工/机器审查标签。

## 4. 冻结模型

- 标准化：`StandardScaler`；
- 分类器：`LogisticRegression`；
- 固定参数：`C=1.0`、`class_weight=balanced`、`max_iter=1000`、`random_state=20260727`；
- 固定阈值：`P(Qwen3更优) >= 0.5` 选择 Qwen3，否则选择 Qwen2.5-LoRA；
- 不扫描特征子集、阈值、正则强度、模型类型或随机种子。

## 5. 对照与指标

对照：

1. 始终选择 `CleanQwen3_Raw8`；
2. 始终选择 `Qwen25AdsSFTLoRA_Raw8`；
3. 两模型逐题 Oracle，仅作为上限。

选择器报告：

- Strict、Relaxed；
- 相对 Clean Qwen3 的胜/平/负；
- `wrong→right`、`right→wrong`、纠正精度；
- 选择 Qwen2.5-LoRA 的触发率；
- 100个视频聚类的10,000次 Bootstrap 95% CI；
- 五折训练非平局样本数和类别分布；
- 特征系数仅用于失败归因，不用于回头筛特征。

## 6. 通过门禁

以下条件必须同时满足：

1. Relaxed 点估计高于 Clean Qwen3；
2. Strict 不低于 Clean Qwen3；
3. `wrong→right > right→wrong`；
4. Relaxed 差的 Bootstrap 不存在明确负向证据；
5. 五折均成功，视频交集为0，无参考答案或 `meta_info` 泄漏。

若失败：

- 标记 `freeze_crossbase_selector_cpu_failed`；
- 不换成树模型、神经网络或手工阈值继续搜索；
- 不进入确认集，不启动新的 GPU 推理。

若通过：

- 仅说明跨基座选择具有开发期可学习性；
- 后续必须新增证据充分性特征并在独立数据上冻结确认；
- 仍不得把本500题结果写成最终增精结论。
