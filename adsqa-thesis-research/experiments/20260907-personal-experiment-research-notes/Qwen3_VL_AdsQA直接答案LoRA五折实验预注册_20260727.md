# Qwen3-VL AdsQA直接答案LoRA五折实验预注册

日期：2026-07-27

## 1. 研究问题

本实验只回答两个问题：

1. 在完全相同的 `Uniform8` 输入、视觉预算和回答 Prompt 下，AdsQA 直接答案 LoRA 是否能稳定提高干净 Qwen3-VL-8B 的回答准确率；
2. 同样采用视频隔离五折 OOF 时，Qwen3-LoRA 是否优于既有的干净 Qwen2.5-LoRA。

本实验不用于挽救 `DualConsensus2-or-Raw8`，不读取或调整 Confirm-D300，也不把基座升级本身计作创新点一的证据定位收益。

## 2. 数据与隔离

- 数据：AdsQA Train-500，500题、100视频。
- 固定划分：复用已审计的 `splits_v2` 视频级五折。
- 每折训练：400题、80视频。
- 每折验证：100题、20视频。
- 每个验证视频只在一个外折出现，训练/验证视频零重叠。
- 推理输入不含参考答案、`meta_info`、历史分数或裁判结果。

## 3. 模型与训练

- 干净基座：`/data1/qky/Model/Qwen3Vl-8B`。
- 模型类：Transformers 原生 `Qwen3VLForConditionalGeneration`。
- 视觉输入：8个均匀全帧。工程探针发现 Qwen3 在448尺寸下为784 Token，在512尺寸下精确为1,024 Token；因此正式协议冻结为512尺寸。
- 视觉 Token：实际1,024，上限4,096，与既有 Qwen2.5-LoRA 的模型侧视觉 Token 数一致。由于两代模型原生视觉分词不同，这是 Token 公平而非输入像素公平。
- Prompt、ASR截断、答案目标格式与既有 Qwen2.5 直接答案 LoRA 完全一致。
- 训练：1 epoch，学习率 `5e-5`，梯度累积4。
- LoRA：rank/alpha/dropout=`16/32/0.05`。
- 目标模块：语言侧 `q_proj/k_proj/v_proj/o_proj`；视觉编码器冻结。
- seed=`2026072202`。
- 不使用 ReAd-R、AdsQA 已训练权重、RAG、反思或证据选择器。

## 4. Smoke门禁

先只在 Fold-0 建立独立工程 Smoke：

- 使用固定训练子集运行8步 LoRA；
- 冻结基座和 Smoke LoRA 各推理5条 answer-free 验证题；
- 两臂错误均为0；
- 输入均为8个实际表示视图，统一512尺寸；
- 视觉 Token 不超过4,096；
- 实际视觉 Token 必须恒为1,024；
- 关闭二次帧采样；
- LoRA 权重确实变化，且视觉参数未训练。

Smoke 只验证工程协议，不调用裁判、不查看精度。通过后才运行五折正式训练。

## 5. 正式评测

每折分别运行：

```text
Clean-Qwen3-Raw8
Qwen3-AdsSFTLoRA-Raw8
```

五折合并后，与既有 `Qwen2.5-AdsSFTLoRA-Raw8` 一起按同一当前 DeepSeek answer-only 批次统一评分。同题同答案只调用一次，历史分数复用为0，所有结果标记 `not_human_gold=true`。

报告：

- Strict、Relaxed；
- Qwen3-LoRA 相对干净 Qwen3 的配对差值；
- Qwen3-LoRA 相对 Qwen2.5-LoRA 的配对差值；
- wrong→right、right→wrong、胜平负；
- 100视频聚类10,000次 Bootstrap；
- 推理延迟、视觉 Token 和 LoRA 参数量。

只有在以下条件均满足时，才把 Qwen3-LoRA 作为新的最终精度基座：

1. 相对干净 Qwen3 的 Relaxed 点估计提高，且95% CI无明确负向；
2. 相对 Qwen2.5-LoRA 的 Relaxed 点估计提高，且95% CI无明确负向；
3. Strict 点估计不低于两条对应基线；
4. 五折视觉、输入隔离和模型审计全部通过。

若失败，冻结该结果，不扫描学习率、epoch、LoRA rank、Prompt、视觉预算或训练 seed。
