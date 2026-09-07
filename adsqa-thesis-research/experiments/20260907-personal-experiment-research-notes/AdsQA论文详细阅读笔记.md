# AdsQA 论文详细阅读笔记

> 论文：AdsQA: Towards Advertisement Video Understanding  
> arXiv: https://arxiv.org/abs/2509.08621  
> 本笔记基于 arXiv 页面、PDF 文本抽取和本地关键词检索整理。

---

## 1. 基本信息

| 项目 | 内容 |
|---|---|
| 题名 | AdsQA: Towards Advertisement Video Understanding |
| 作者 | Xinwei Long, Kai Tian, Peng Xu, Guoli Jia, Jingxuan Li, Sa Yang, Yihua Shao, Kaiyan Zhang, Che Jiang, Hao Xu, Yang Liu, Jiaheng Ma, Bowen Zhou |
| 单位 | Tsinghua University 等 |
| arXiv | 2509.08621 |
| 年份 | 2025 |
| 备注 | ICCV 2025 |
| Project page | https://github.com/TsinghuaC3I/AdsQA |
| Workshop | https://mars2workshop.github.io/iccv2025/ |

---

## 2. AdsQA 的核心定位

AdsQA 将广告视频作为大语言模型/多模态模型的新型高难度测试场景。论文强调广告视频不同于普通视频，因为它们具有：

- clue-rich：线索丰富；
- information-dense：信息密度高；
- marketing logic：营销逻辑；
- persuasive strategies：说服策略；
- audience engagement：受众参与；
- implicit / non-physical / mental / heuristic：隐含、非物理、心理性、启发式。

论文认为，现有 LLM 在数学和编程等显式推理任务上进展很快，但广告视频理解要求模型超越“if A then B”的显式逻辑，理解隐含营销逻辑和受众心理。

---

## 3. 数据集规模

论文明确给出：

| 项目 | 数值 |
|---|---:|
| 广告视频数量 | 1,544 unique advertisements |
| 视频 clip 数量 | 10,962 video clips |
| 总时长 | 22.7 hours |
| 视频时长范围 | 15 到 120 秒 |
| 平均视频时长 | 52.9 秒 |
| QA pair 数量 | 7,859 QA pairs |
| 多标签展开后的评估 QA 数量 | 10,154 QA pairs for evaluation |
| 平均问题长度 | 17 words |
| 平均答案长度 | 12 words |

关键原文信息：

```text
AdsQA Benchmark includes a total of 1,544 unique advertisements, comprising 10,962 video clips for evaluation.
The video durations range from 15 to 120 seconds, with an average length of 52.9 seconds, amounting to a total of 22.7 hours of content.
AdsQA Benchmark includes 7,859 QA pairs (among which 29.2% of the questions can be categorized into two types, resulting in a total of 10,154 QA pairs for evaluation).
```

---

## 4. 你的“7812 测试样本”是否来自 AdsQA 官方？

本次在 AdsQA PDF 文本中没有检索到：

```text
7812
7,812
```

论文中明确出现的是：

```text
7,859 QA pairs
10,154 QA pairs for evaluation
```

因此：

> 当前不能把“7812 个测试样本”写成 AdsQA 官方数字。

如果你实验里确实有 7812 个样本，应写成：

```text
本文在 AdsQA 数据集基础上，根据可下载样本、视频可访问性和预处理有效性筛选得到 7812 个有效测试样本。
```

但这需要你提供筛选脚本或样本统计结果。否则应该暂时写“待复核”。

---

## 5. AdsQA 官方五类任务

AdsQA 官方定义了 5 类 open-ended video QA 任务。英文名称和缩写如下：

| 官方缩写 | 官方英文任务名 | 论文解释 | 可对应中文 |
|---|---|---|---|
| VU | Visual Concept Understanding | Identify and analyze visual elements in ads | 视觉概念理解 / 视觉感知 |
| ER | Emotion Recognition | Detect emotions and infer their roles in ads | 情绪识别 / 情感分析 |
| TE | Theme and Core Message Extraction | Summarize the central theme and key messages | 主题与核心信息提取 |
| PS | Persuasion Strategy Mining | Analyze the strategies used to persuade the audience | 说服策略挖掘 / 营销策略分析 |
| AM | Potential Audience Modeling | Identify and characterize the target audience | 潜在受众建模 / 受众分析 |

你当前论文中的五类：

```text
视觉感知、情感分析、主题提取、营销策略、受众分析
```

是可以对应 AdsQA 官方五类的，但建议更准确地写成：

```text
视觉概念理解（Visual Concept Understanding, VU）
情绪识别（Emotion Recognition, ER）
主题与核心信息提取（Theme and Core Message Extraction, TE）
说服策略挖掘（Persuasion Strategy Mining, PS）
潜在受众建模（Potential Audience Modeling, AM）
```

如果为了中文简洁，可以在首次出现时写：

```text
下文简称为视觉感知、情感分析、主题提取、营销策略和受众分析。
```

---

## 6. 五类任务占比

论文给出 QA pairs 分布：

| 任务 | 占比 |
|---|---:|
| Visual Concept Understanding | 21.4% |
| Theme and Message Extraction | 28.5% |
| Persuasion Strategy Mining | 25.3% |
| Potential Audience Modeling | 15.1% |
| Emotion Recognition | 9.8% |

注意：顺序不是你表格里的顺序，但语义一致。

---

## 7. 数据来源与构建流程

论文说明 AdsQA construction pipeline 是三阶段：

```text
Data Collection & Auto Filter
Auto QA Pair Generation
Auto & Manual Quality Control
```

### 7.1 数据收集与自动过滤

论文说明：

- 不使用 private data；
- 从 creative community platform 收集 Creative Commons License 下的广告视频；
- crawl videos along with metadata；
- metadata 通常由 uploader / creator 提供；
- 包含 theme、content 等信息；
- 使用自动过滤，根据 video duration、aesthetic score、content 过滤；
- 排除 non-ethical and negative content。

### 7.2 视频切分与多模态序列

论文说明：

- 使用 PySceneDetect 将广告视频切成细粒度 clips；
- 对每个 clip 使用 Video-LLMs 生成描述；
- 用 SSIM 计算 frame similarity，并从每个 clip 采样关键帧；
- 使用 Whisper 提取 ASR；
- 使用 GPT-4 将 ASR 翻译成英文；
- 最终表示为 modality-interleaved sequence：

```text
V = {M, {F_i^0, ..., F_i^n_i, Desc_i, Asr_i}_{i=1}^N}
```

其中 M 是视频 metadata。

### 7.3 Role-Played Multi-Agent Annotation

AdsQA 的 QA 生成使用 Role-Played Multi-Agent Annotation：

1. master agent 生成初始 QA annotation；
2. master agent 检查质量，并决定是否招募 specialized expert agent；
3. expert agent 基于广告专家角色生成新 QA；
4. master agent 根据 expert 输出修订原始 annotation；
5. 迭代终止后，master agent 综合输出最终 QA annotation。

专家角色包括：

- marketing；
- visual design；
- consumer psychology。

### 7.4 自动清洗与人工质控

论文说明：

- 使用 IXC-2.5-Reward model 自动验证答案正确性；
- 给定 video、question 和 meta information，reward model 给答案打分；
- 低于阈值的 QA pair 被标记并由 annotators 审查；
- 人工检查关注：question suitability、annotation correctness、video content、task difficulty；
- 删除 homogeneous、unrelated to ads' theme、cannot be answered based on ad video 的问题；
- 删除 inaccurate、ambiguous、biased answers；
- 两轮严格筛选后，只保留 37% QA pairs；
- 修改样本会由其他 annotators 复核。

---

## 8. AdsQA 的评估方式

论文说明：

- 五类任务均为 open-ended QA；
- 传统 free-text 指标对词面变化敏感；
- 采用 GPT-4o 辅助评估 free-text similarity；
- 使用 inclusion and exclusion rules；
- 每个样本提供 ground-truth answer 和 meta-information；
- 评估包含 strict accuracy 和 relaxed accuracy。

Relaxed accuracy 定义：

```text
Acc_relaxed = 1/n * Σ_i ( 1{x_i = y_i} + λ * 1{x_i ≈ y_i} )
```

论文中 λ=0.5。

含义：

- strict：完全满足标准答案；
- relaxed：部分覆盖标准答案要素可得 0.5。

---

## 9. AdsQA baseline 模型

论文评估了 14 个 top-tier LLMs，分为三类：

### 9.1 GPT-4 level baselines

包括：

- GPT-4o；
- GPT-4V；
- Qwen2.5-VL-72B；
- Gemini-2.5-Pro。

### 9.2 Open-sourced Video-LLMs

从表格和文本可见包括：

- VideoLLaMA2-7B；
- InternLM-XComposer2.5-7B；
- LLaVA-OneVision-7B；
- LLaVA-Video-7B；
- MiniCPM-o 2.6-7B；
- Qwen2-VL-7B；
- Qwen2.5-VL-7B；
- Qwen2.5-VL-72B。

### 9.3 Reasoning-based Models

包括：

- VOT (Qwen2-VL-7B)；
- EvolAgent (Qwen2-VL-7B)；
- MCTSr (Qwen2-VL-7B)；
- Qwen2-VL-7B (SFT)；
- ReAd-R (Qwen2-VL-7B)；
- ReAd-R (Qwen2.5-VL-7B)。

---

## 10. ReAd-R 方法

ReAd-R 全称：

```text
Reinforced Ad Reasoner
```

论文描述：

- DeepSeek-R1 styled RL reasoning model；
- 模拟 human heuristic thinking；
- learns to gather effective visual stimuli from ad videos；
- reflects on questions；
- answers in a human-like manner；
- 使用 reward function 评估回答；
- 根据 correctness 调整参数；
- 通过 outcome-reward-driven optimization 提升广告隐含逻辑理解；
- 不需要 costly step-wise supervision 或 CoT training data。

训练实现：

- model-agnostic；
- 主实验使用 Qwen2-VL-7B 作为 base model；
- 冻结 visual backbone；
- 只 fine-tune language model parameters；
- batch size = 4；
- learning rate = 1e-6；
- eight A100 GPUs；
- training duration = 12 hours；
- 使用 GRPO，而不是 PPO；
- 额外爬取 1,053 ad videos；
- 最终选择 100 videos 和 500 QA pairs 用于训练/数据准备。

---

## 11. AdsQA 实验表关键信息

论文表 1 使用五类任务：

```text
VU ER TE PS AM Overall
```

并同时报告：

```text
Strict Accuracy
Relaxed Accuracy
```

抽取到的部分结果：

| Model | Strict Overall | Relaxed Overall |
|---|---:|---:|
| Human Results | 51.3 | 71.4 |
| GPT-4o | 29.4 | 56.6 |
| Gemini-2.5-Pro | 35.9 | 60.7 |
| VideoLLaMA2-7B | 6.48 | 25.2 |
| InternLM-XComposer2.5-7B | 12.6 | 36.5 |
| LLaVA-OneVision-7B | 14.0 | 39.1 |
| LLaVA-Video-7B | 16.1 | 41.0 |
| MiniCPM-o 2.6-7B | 16.3 | 42.5 |
| Qwen2-VL-7B | 17.2 | 41.0 |
| Qwen2.5-VL-7B | 23.0 | 48.9 |
| Qwen2.5-VL-72B | 31.0 | 55.8 |
| VOT (Qwen2-VL-7B) | 17.0 | 40.2 |
| EvolAgent (Qwen2-VL-7B) | 18.3 | 42.6 |
| MCTSr (Qwen2-VL-7B) | 17.1 | 43.4 |
| Qwen2-VL-7B (SFT) | 14.1 | 38.8 |
| ReAd-R (Qwen2-VL-7B) | 18.6 | 44.9 |
| ReAd-R (Qwen2.5-VL-7B) | 25.0 | 51.5 |

注意：这些是 AdsQA 论文中的结果，不等同于你当前论文表格里的 `0.416` 等数值。你的数值应解释为你自己的实验口径，不能直接说来自 AdsQA 原文。

---

## 12. AdsQA 对你论文的启示

### 12.1 数据集表述需要修改

你现在可以更准确地写：

```text
本文以 AdsQA 广告视频问答数据集作为主要实验数据集。AdsQA 包含 1,544 条广告视频、10,962 个视频片段，总时长 22.7 小时，并提供 7,859 个问答对。由于 29.2% 的问题可归入两个任务类别，展开后共有 10,154 个用于评估的问答条目。AdsQA 官方定义五类开放式问答任务：视觉概念理解、情绪识别、主题与核心信息提取、说服策略挖掘和潜在受众建模。
```

### 12.2 你原来的五类名称可以保留，但要映射官方英文

建议写：

```text
本文沿用 AdsQA 的五类任务划分，并在中文叙述中分别称为视觉感知、情感分析、主题提取、营销策略和受众分析。
```

但第一次出现必须写官方英文：

```text
视觉概念理解（Visual Concept Understanding, VU）
情绪识别（Emotion Recognition, ER）
主题与核心信息提取（Theme and Core Message Extraction, TE）
说服策略挖掘（Persuasion Strategy Mining, PS）
潜在受众建模（Potential Audience Modeling, AM）
```

### 12.3 你的 7812 要改成待复核

除非你能证明 7812 是你的筛选后样本数，否则不要写：

```text
AdsQA 包含 7812 个测试样本
```

建议改成：

```text
本文阶段性实验使用的有效样本数为 7812，该数值需根据本地数据筛选脚本进一步复核。
```

或者在正式论文中暂时不写 7812。

### 12.4 你的 baseline 名称需要对齐 AdsQA

AdsQA 原文中是：

```text
ReAd-R (Qwen2-VL-7B)
ReAd-R (Qwen2.5-VL-7B)
```

你之前写的：

```text
Qwen2.5-ReAd
```

建议改成：

```text
ReAd-R (Qwen2.5-VL-7B)
```

如果你实际跑的是自己复现的变体，可以写：

```text
ReAd-R-style Qwen2.5-VL baseline
```

但要说明不是 AdsQA 官方原表结果。

---

## 13. 对你第5章应修改的点

1. 将 AdsQA 样本数从待补改为官方核查数：1,544 videos、10,962 clips、22.7h、7,859 QA pairs、10,154 evaluation QA entries。
2. 五类任务使用官方英文名 + 中文简称。
3. 说明 29.2% 问题可归入两类。
4. 说明 AdsQA 为 open-ended QA。
5. 说明 AdsQA 使用 GPT-4o 评估 strict / relaxed accuracy。
6. 说明 relaxed accuracy 的 λ=0.5。
7. baseline 应参考 AdsQA 原文分类：GPT-4 level、open-source Video-LLMs、reasoning-based methods。
8. 你自己的实验结果必须和 AdsQA 原文结果分开。
9. 如果使用 7812，必须说明是你本地筛选后的有效样本，并给出筛选规则。

---

## 14. 最重要结论

AdsQA 官方五类任务确实存在，但更准确名称是：

```text
Visual Concept Understanding (VU)
Emotion Recognition (ER)
Theme and Core Message Extraction (TE)
Persuasion Strategy Mining (PS)
Potential Audience Modeling (AM)
```

AdsQA 官方规模不是 7812 测试样本，而是：

```text
1,544 unique advertisements
10,962 video clips
22.7 hours
7,859 QA pairs
10,154 QA entries for evaluation after multi-label expansion
```

因此，你论文里关于数据集的表述需要按这个修正。当前“视觉感知、情感分析、主题提取、营销策略、受众分析”可以作为中文简称，但应明确对应官方五类任务。
