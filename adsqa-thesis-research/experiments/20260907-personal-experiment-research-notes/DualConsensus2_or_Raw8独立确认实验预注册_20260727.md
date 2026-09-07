# DualConsensus2-or-Raw8独立确认实验预注册

日期：2026-07-27

## 1. 研究问题

上一轮`Anchor6+CEPO-QACF2`在Dev-100上相对Raw8保持Strict并使Relaxed提高4.0个百分点，但未通过预注册的Strict纠正数门禁。事后分层发现：最终接受两个三seed共识替换的27题为6胜、21平、0负，而仅接受一个替换的49题收益不稳定。

本实验把该开发期发现冻结为全新候选：

> 只有至少两个时间槽位分别获得三个固定seed完全一致的QACF选择，且可形成两个非重复、非Raw锚点替换时，才替换margin最高的两个槽位；否则八帧全部精确回退Raw8。

该规则不得再根据任何Confirm-D结果修改。

## 2. 数据边界

- 训练集：AdsQA Train-500，500题、100视频。
- 开发来源：上一轮确定性Dev-100；只用于形成“双共识才触发”规则，不再用于本实验调参或评分。
- 独立确认：既有封存`Confirm-D300`，300题、300个唯一视频、Type1-5各60。
- Confirm-D与Train-500、Pilot50及Confirm-A/B/C的问题和视频均零重合。
- Confirm-D此前仅完成数据冻结、候选缓存和分段ASR预处理，没有运行过本候选、最终答案LoRA或QACF部署选择器。
- Smoke只读取Confirm-D中确定性前20题的answer-free输入和视觉协议，不读取参考答案、不调用裁判、不比较答案质量。

## 3. 冻结训练

### 3.1 最终答案器

从干净`Qwen2.5-VL-7B-Instruct`开始，在全部Train-500上训练一个最终`AdsSFTLoRA-Raw8-Full500`：

- Uniform8全帧；
- 448统一尺寸；
- 实际视觉Token预计1,024，上限4,096；
- 1 epoch、学习率`5e-5`、梯度累积4；
- LoRA rank/alpha/dropout=`16/32/0.05`；
- 只训练语言侧`q/k/v/o_proj` LoRA，冻结视觉编码器；
- 使用原冻结回答Prompt和ASR；
- seed=`2026072202`。

### 3.2 最终QACF选择器

使用上一轮已经审计的Train-500 4,000组E+和8,000组E-奖励缓存，在全部500题上分别训练三个固定seed：

```text
2026072711
2026072712
2026072713
```

架构和训练配置保持不变：两层64维Temporal Transformer、4头、FFN 128、80 epoch、学习率`1e-3`、weight decay`1e-4`、pairwise weight`0.10`，奖励为标准化QA奖励加`0.5×`标准化反事实下降。选择器输入仍为13维answer-free候选特征，不读取Confirm-D答案、`meta_info`、历史预测或裁判分数。

## 4. 冻结方法

### FinalLoRA-Raw8

使用最终Full500 LoRA和8个均匀全帧锚点。

### DualConsensus2-or-Raw8

1. 对64个候选帧按时间分为8个八分区；
2. 三个最终QACF seed分别在每个八分区选1帧；
3. 仅当三个seed在某槽位选择完全相同的候选，且该候选也是三seed平均logit的top1，该槽位才合格；
4. 排除与Raw锚点相同或导致重复帧的候选；
5. 若最终合格槽位少于2个，八个输入全部精确回退Raw8；
6. 若不少于2个，只替换mean-logit top1-top2 margin最高的两个槽位；
7. 不使用margin阈值，不允许替换1帧，不增加视图、Token、裁剪、RAG或回答后反思。

## 5. 公平协议

两方法必须逐题共享：

- 同一最终Full500 LoRA；
- 同一问题、ASR和回答Prompt；
- 8个448全帧视图；
- 同一视觉Token上限，关闭二次采样；
- 同一确定性生成参数；
- 只有最终输入帧号允许不同。

Smoke-20必须两方法各20/20、错误0，帧号与冻结清单一致、8视图、Token不超限、回退题逐帧等于Raw，才可运行Confirm-D300。

## 6. 评测与门禁

Raw8与候选必须在同一当前DeepSeek answer-only批次统一评分，同题同答案只调用一次，不复用历史分数；所有结果标记`not_human_gold=true`。执行300视频聚类10,000次Bootstrap。

本轮以回答完整程度为主要目标，不再把`wrong→right > right→wrong`设为独立硬门槛：

1. 主要指标：候选Relaxed点估计高于Raw8；
2. Relaxed差值95% CI不得显示明确负向；若下界不低于0，可支持稳定正向；
3. 安全指标：Strict点估计不得低于Raw8；
4. 报告但不单独门控：wrong→right、right→wrong、胜平负、纠正精度；
5. 双共识实际触发至少30题，否则只能报告低覆盖探索结果；
6. 任一Type的Relaxed不得出现超过5个百分点的明显退化；
7. 所有输入隔离、帧号、Token和二次采样审计必须通过。

只有上述门禁全部通过，才能把该方法写成独立确认支持的准确率贡献。失败后冻结本候选，不在Confirm-D扫描共识人数、margin、替换数、Prompt、LoRA或视觉预算。
