# AdsQA 实验结果总表与复现索引

> 用途：集中记录 AdsQA 实验的模型、数据集、代码与结果路径、关键参数、评测口径、指标、复现状态和已知问题。以后撰写论文第 5 章、制作主结果表或重新运行实验时，以本文件为统一入口。
>
> 维护原则：《论文思考记录》只保存结论和决策；本文件保存详细路径与数字。历史文件《AdsQA 本地 Baseline 评测结果记录》保留为来源记录，但未收入本去重归档，也不再作为后续实验的唯一更新位置。

## 1. 指标与状态说明

- `Strict = Answer:1 / N`。
- `Relaxed = (Answer:1 + 0.5 x Answer:0.5) / N`。
- “覆盖样本口径”只在已完成预测上计算。
- “缺失计 0”把未完成或缺失预测按 0 分计入完整目标集合。
- 自有评测文件产生的数字不得写成 AdsQA 官方评测结果。
- 历史结果不得覆盖；修正处理器、Prompt、裁判或数据后必须新建实验 ID 和结果目录。

状态含义：

| 状态 | 含义 |
|---|---|
| 有效本地 baseline | 模型推理与本地评测结果可追溯，可作为阶段性本地对照 |
| 待统一重评 | 需要使用论文最终统一裁判、Prompt 或缺失项规则重新评测 |
| 历史参考 | 保留用于追溯，不进入论文最终主表 |
| 无效/不完整 | 存在严重缺失、口径错误或无法复现，不得作为结论 |

## 2. 实验总览

| 实验 | 模型 | 数据范围 | Strict | Relaxed | 当前状态 |
|---|---|---:|---:|---:|---|
| ReAd-R 本地完整测试集 | Qwen2.5-7B-VL-ReAd-R | 7829/7859 | 34.60% | 48.10% | 有效本地 baseline；待统一重评 |
| ReAd-R balanced-3000 覆盖口径 | Qwen2.5-7B-VL-ReAd-R | 2990/3000 | 35.35% | 49.25% | 有效子集结果；待补缺失项 |
| ReAd-R balanced-3000 缺失计 0 | Qwen2.5-7B-VL-ReAd-R | 3000 | 35.23% | 49.08% | 可用于保守报告；待统一重评 |
| 公平协议 Raw Uniform smoke | Qwen3-VL-8B | 10/10 | - | - | 协议验证通过；尚未评测 |
| 公平协议 CLIP Single-Peak smoke | Qwen3-VL-8B | 10/10 | - | - | 协议验证通过；尚未评测 |
| 公平协议 AdSlot Fixed smoke | Qwen3-VL-8B | 10/10 | - | - | 协议验证通过；尚未评测 |
| 可靠性校准 AV Response V2 smoke | Qwen3-VL-8B | 10/10 | - | - | 实现与协议验证通过；尚未评测 |
| 固定 pilot Raw Uniform | Qwen3-VL-8B | 50/50 | 64.00% | 78.00% | 含 22 条空标准答案；仅作历史诊断 |
| 固定 pilot CLIP Single-Peak | Qwen3-VL-8B | 50/50 | 62.00% | 74.00% | 含 22 条空标准答案；仅作历史诊断 |
| 固定 pilot AdSlot Fixed | Qwen3-VL-8B | 50/50 | 56.00% | 73.00% | 含 22 条空标准答案；仅作历史诊断 |
| 固定 pilot AV Response V1 | Qwen3-VL-8B | 50/50 | 58.00% | 72.00% | 含 22 条空标准答案；仅作历史诊断 |
| 固定 pilot AV Response V2 | Qwen3-VL-8B | 50/50 | 52.00% | 68.00% | 含 22 条空标准答案；仅作历史诊断 |
| 固定 pilot AdSlot Fixed（Answer-only 诊断） | Qwen3-VL-8B | 50/50 | 56.00% | 72.00% | 含 22 条空标准答案；不进主表 |
| 预算比例 AV V1 24+8（Answer-only 诊断） | Qwen3-VL-8B | 50/50 | 48.00% | 66.00% | 负结果；不扩大 |
| 预算比例 AV V2 24+8（Answer-only 诊断） | Qwen3-VL-8B | 50/50 | 44.00% | 64.00% | 负结果；不扩大 |
| 有效答案 pilot Raw（Answer-only） | Qwen3-VL-8B | 50/50 | 44.00% | 61.00% | 公平有效对照 |
| 有效答案 pilot CLIP（Answer-only） | Qwen3-VL-8B | 50/50 | 44.00% | 62.00% | 公平有效对照 |
| 有效答案 pilot AdSlot（Answer-only） | Qwen3-VL-8B | 50/50 | **48.00%** | **63.00%** | 当前有效 pilot 最优 |
| 有效答案 pilot AV V1（Answer-only） | Qwen3-VL-8B | 50/50 | 40.00% | 58.00% | 未超过公平基线 |
| 有效答案 pilot AV V2（Answer-only） | Qwen3-VL-8B | 50/50 | 38.00% | 61.00% | 未超过公平基线 |
| AV V1 每帧单裁剪（Answer-only） | Qwen3-VL-8B | 50/50 | 44.00% | 61.00% | 相对 V1 可重复 +4/+3；CI 跨 0 |
| AV V1 固定先验+单裁剪（Answer-only） | Qwen3-VL-8B | 50/50 | 42.00% | 58.00% | 负结果；停止固定权重 |
| AV V1 单裁剪+缓存 OCR（本地 Llama Answer-only） | Qwen3-VL-8B | 50/50 | 54.00% | 58.00% | 区域 Recall 10/10；相对单裁剪方向为正但 CI 跨 0，待 DeepSeek 同批重评 |

### 2.1 论文最终主结果的两表结构（2026-07-16 冻结决策）

论文最终不把所有 baseline 塞入一张表，而是按可比性拆成两张主结果表。

#### 表一：同底座、同预算的严格公平对比

| 方法 | 比较身份 | 统一协议 | 当前复现状态 |
|---|---|---|---|
| Raw Uniform32 | 基础 baseline | Qwen3-VL-8B；32 实际视图；11,664 视觉 Token；同 Prompt/裁判；关闭二次采样 | Evidence-300 300/300 已完成 |
| CLIP Top-K32 / CLIP Single-Peak | 常规选帧 baseline | 与 Raw 完全同模型、预算和评测 | Pilot50、Confirm-300 已有结果；最终同集结果待确认/补齐 |
| VideoITG-32 | 外部强选帧 baseline | 官方选择器；统一输出 32 帧后接同一 Qwen3-VL 回答器 | Pilot50 50/50 已完成；尚未扩大 |
| MMR32 | 本文中间版本/强内部对照 | 64 候选到 32 帧；同模型、预算和评测 | Evidence-300 300/300 已完成 |
| 本文完整创新点一 | 本文方法 | 问题/ASR/OCR条件化证据定位与动态配置；同预算 | 最终冻结版本结果待补齐 |
| Oracle Evidence32（可选） | 上限参考，不是 baseline | 人工证据选择；仍限制同样视图和 Token | 未运行 |

表一至少报告 Strict、Relaxed、逐题胜/平/负、10,000 次配对 Bootstrap、证据 Recall/Precision、Region Recall、实际视觉 Token 和二次采样审计。MMR32 是本文自研中间方法，不得写成外部已有 baseline。

#### 表二：AdsQA 已有论文方法比较

| 方法 | 模型/性质 | 当前数据来源 | 论文使用规则 |
|---|---|---|---|
| AdsQA/Qwen 基础模型 | 数据集基础参考 | 官方报告或本地统一复现 | 标明模型、输入和评测协议 |
| ReAd-R | Qwen2.5-VL-7B；GRPO训练方法 | 已有本地完整/子集结果 | 最终统一重评后标记为本地复现 |
| AD-MIR | 训练免费结构化推理方法 | 当前仅有论文报告值，完整本地闭环未建立 | 未复现前只能标记为原论文引用 |
| 本文方法 | Qwen3-VL-8B；固定 Token 预算 | 最终冻结实验 | 明确不同底座与预算，不作绝对公平领先表述 |

建议表注：`†` 表示本文环境统一复现与重评，`*` 表示引用原论文报告结果。不同底座、预算、子集或裁判口径只允许作为研究水平参考，不能与表一混用来证明公平增益。

若增加 E-VAds，须为 E-VAds 另建同样两层比较，不与 AdsQA 分数求平均。E-VAds-R1 只进入 E-VAds 的公开方法表。

## 3. ReAd-R：Qwen2.5 官方训练模型本地评测

### 3.1 实验身份与复现入口

| 字段 | 内容 |
|---|---|
| 模型 | Qwen2.5-7B-VL-ReAd-R |
| 模型性质 | AdsQA 官方 GRPO 强化学习训练模型 |
| checkpoint | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-7B-VL-ReAd-R` |
| 推理脚本 | `evaluation/archive/legacy_scripts_2025/eval_adqa.py` |
| 输入 | 8 个均匀采样图像 + ASR |
| 完整测试集 | 7859 条 |
| 已完成 | 7829 条，覆盖率 99.62% |
| 结果路径 | `evaluation/archive/legacy_results_2025/results/` |
| 评测口径 | 自有评测文件，不是 AdsQA 官方评测 |
| Answer 1/0.5/0 | 2709 / 2113 / 3007 |
| Strict | 34.60% |
| Relaxed | 48.10% |
| balanced-3000 覆盖 | 2990/3000 |
| balanced Strict/Relaxed | 35.35% / 49.25% |
| balanced 缺失计 0 | 35.23% / 49.08% |
| 二次采样 | 没有；使用 8 个独立 image 输入，不经过 Qwen3-VL 视频处理器二次采样 |
| 当前状态 | 有效本地 baseline；最终主表前需统一裁判重评并补齐缺失项 |

### 3.2 当前可用结论

该结果能够证明本地已经完整运行过 AdsQA 官方训练的 ReAd-R Qwen2.5 模型，并形成接近全量测试集的本地 baseline。它可以用于说明本地模型对比基础，但由于采用自有评测文件，不能与 AdsQA 官方论文中的数字直接混用，也不能与不同裁判口径的 Qwen3 实验直接混成最终主表。

### 3.3 最终主表前待补信息

- [ ] 记录推理环境、Transformers 版本和精确运行命令；
- [ ] 记录 checkpoint 文件哈希或目录清单；
- [ ] 定位并登记自有评测文件、裁判 Prompt 和版本；
- [ ] 列出完整测试集缺失的 30 条样本及原因；
- [ ] 列出 balanced-3000 缺失的 10 条样本及原因；
- [ ] 使用论文最终统一裁判重评 ReAd-R 与其他主方法；
- [ ] 明确最终主表采用覆盖样本口径还是缺失计 0 口径。

## 4. Qwen3-VL 统一视觉预算公平协议

### 4.1 协议定义

| 字段 | 内容 |
|---|---|
| 实验日期 | 2026-07-11 |
| 模型/checkpoint | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| 公平基线入口 | `evaluation/methods/fair_protocol/inference_fair_baselines_v1.py` |
| 统一处理器 | `evaluation/methods/common/qwen_video_budget.py` |
| smoke 启动脚本 | `evaluation/scripts/run_fair_baselines_smoke_v1.sh` |
| 测试范围 | `testset_question.json` 的前 10 条；三种方法使用同一问题集合 |
| 候选帧 | 每条视频均匀解码 32 帧 |
| 提交视图 | 每条固定 32 个 PIL 视频帧视图 |
| 实际表示帧 | 每条 32 帧；`video_grid_thw=[16,54,54]` |
| 合并后视觉 Token | 每条 11,664；上限 12,000 |
| 二次采样 | 已关闭；`do_sample_frames=False`，逐条检查无帧丢失和时间填充 |
| RAG/反思 | 均关闭 |
| Prompt/生成参数 | 三种方法共享 |
| GPU 分配 | Raw Uniform=`5`，CLIP Single-Peak=`2`，AdSlot Fixed=`3`；保留 GPU `1` |
| 当前状态 | 真实模型 smoke 和逐条协议审计通过；尚未进行答案裁判 |

### 4.2 三种方法和路径

| 方法 | 视图构成 | 10 条结果路径 | 完成/错误 |
|---|---|---|---:|
| `raw_uniform` | 32 个均匀全局帧 | `evaluation/runs/fair_raw_uniform_smoke1_20260711_true10/` | 10/0 |
| `clip_singlepeak` | 16 个 CLIP 全局帧 + 16 个单峰局部裁剪 | `evaluation/runs/fair_clip_singlepeak_smoke1_20260711_true10/` | 10/0 |
| `adslot_fixed` | 动态 16-20 个全局帧 + `32-global` 个局部裁剪 | `evaluation/runs/fair_adslot_fixed_smoke1_20260711_true10/` | 10/0 |

另有三种方法各 1 条的首次真实模型验证，目录后缀为 `20260711_true1b`。累计 33 次真实推理均成功。对 10 条结果目录中的 30 份 `evidence.json` 逐条检查后，违规记录为 0：提交视图均为 32，实际表示帧均为 32，视觉 Token 均为 11,664，二次采样均关闭，全局与局部视图之和均为 32。

### 4.3 使用边界

- 这批 smoke 只证明推理链路和公平预算成立，不产生可报告的 Strict/Relaxed 结论；
- 历史 balanced-3000 三组结果实际只编码 4 帧，仍保留为历史趋势，不进入新协议主表；
- 下一步先跑同一 50-100 条 pilot 并统一裁判，再决定是否启动 balanced-3000；
- 新方法必须复用统一处理器，并继续保存 `video_grid_thw`、实际表示帧数和视觉 Token。

## 5. 可靠性校准 AV Response V2

### 5.1 实验身份与复现入口

| 字段 | 内容 |
|---|---|
| 实验 ID | `av_reliability_v2_smoke_20260711_true10` |
| 日期 | 2026-07-11 |
| 模型/checkpoint | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| V2 推理入口 | `evaluation/methods/av_evidence/inference_av_evidence_reliability_v2.py` |
| V1/V2 共享主流程 | `evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py` |
| 纯算法模块 | `evaluation/methods/av_evidence/av_response.py` |
| 三卡启动脚本 | `evaluation/scripts/run_av_reliability_v2_smoke.sh` |
| GPU 分配 | shard 0/1/2 分别使用 GPU `2/3/5`；GPU `1` 保留 |
| 数据范围 | `testset_question.json` 前 10 条，共 10 个唯一问题 ID |
| 视图构成 | 16 个问题/ASR选择的全局帧 + 16 个预算内局部裁剪 |
| 响应观察 | `original + blur + downscale`，一次 CLIP batch 完成 |
| 融合方式 | 局部响应一致性调权 + 有界不稳定区域细化奖励 |
| ASR 状态 | 本批 10 条均为整段文本；全局 ASR 可靠性固定为 0.25 |
| OCR 状态 | CLIP 文字/Logo语义代理，不是真实 OCR |
| 实际表示帧 | 每条 32；无二次采样 |
| 视觉 Token | 每条 11,664；上限 12,000 |
| 结果路径 | `evaluation/runs/av_reliability_v2_smoke_20260711_true10/shard*/` |
| 完成/错误 | 10/0 |
| 帧级响应记录 | 160 条；每个问题 16 条 |
| 平均单样本总时延 | 19.69 秒；仅供 smoke 性能参考 |
| QA 指标 | 尚未运行统一裁判，Strict/Relaxed 不得填写 |
| 当前状态 | V2 实现、V1 回归、预算审计均通过；待 50-100 条统一评测 |

### 5.2 已验证事实

- 15 个纯算法与 Qwen 视频预算测试全部通过；
- V2 dry-run 正确记录入口、方法名和一致性参数；
- V2 单样本及三卡 10 样本真实 Qwen3-VL 推理均无错误；
- 10 条结果中提交视图与实际表示帧均为 32，视觉 Token 均为 11,664；
- 160 个帧级融合记录均使用三个确定性观察，融合不稳定度均值范围为 0.2117-0.4173；
- 同一首样本中，V2 与 V1 的 16 个局部选择只有 3 个“帧位次 + 裁剪框”完全相同，说明校准机制实际改变了预算分配；
- V1 默认分支另行完成 1 条真实模型回归，结果为 `processed=1, errors=0`，路径为 `evaluation/runs/av_dynamic_v1_regression_smoke1_20260711/`。

### 5.3 尚不能得出的结论

- 10 条 smoke 没有统一裁判，不能说明 V2 的 QA 准确率优于 V1 或公平基线；
- 当前方差来自确定性尺度/模糊观察，只能称“响应一致性”或“可靠性估计”，不能称已校准概率不确定性；
- 当前 ASR 文件 1,548 个条目中有 1,402 个非空整段字符串、146 个其他/空值，没有带时间戳片段，因此声画偏移估计尚未实际启用；
- 当前 OCR 是语义代理，不能据此宣称 OCR 置信度或跨帧文字稳定性已经实现。

### 5.4 下一步门槛

先在同一 50-100 条固定子集比较 Raw Uniform、CLIP Single-Peak、AdSlot Fixed、V1 与 V2，并使用同一裁判。只有 V2 在固定 Token 下取得稳定增益，才扩大到 balanced-3000；同时增加 `refinement_weight=0`、单观察和三观察消融，分离可靠性调权与细化奖励的贡献。

## 6. 第一创新点固定 50 条 pilot：DeepSeek 历史同口径评测

### 6.1 实验身份与复现入口

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_pilot50_20260711_v1` |
| 日期 | 2026-07-11 |
| 模型/checkpoint | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| 数据集 | 5 个主问题类型各 10 条，共 50 条、50 个唯一视频 |
| 问题文件 | `data/pilot50_balanced5x10_seed42_uniquevideo_question.json` |
| Ground Truth | `data/pilot50_balanced5x10_seed42_uniquevideo_groundtruth.json` |
| 数据 SHA256 | 问题文件 `edbf330374a64c9e435915a9c3abd27f42aa799f0ccc7e20157dae56d8c215b0` |
| 方法 | Raw Uniform、CLIP Single-Peak、AdSlot Fixed、AV V1、AV V2 |
| 公平预算 | 每条 32 个提交视图、32 个实际表示帧、11,664 个合并后视觉 Token |
| 二次采样 | 无；`do_sample_frames=False` |
| 推理结果根目录 | `evaluation/runs/innovation1_pilot50_20260711_v1/` |
| 历史评测脚本 | `evaluation/eval/evaluate_compare_new.py` |
| 裁判 | `deepseek-chat`；`temperature=0`；回答截断为前 300 词 |
| API base URL | `https://api.deepseek.com`，与整理前该脚本一致 |
| 评分 | 与历史实验一致的 `0/0.5/1` 规则；Prompt 包含 meta-information、问题与 golden answer |
| Prompt SHA256 | `898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19` |
| `parse_score` 源码 SHA256 | `fe42aa06105c2559ca32cf6073dd738478466888e6f480edcf6a2350398c9716` |
| 适配器 | `evaluation/eval/evaluate_adsqa_deepseek_legacy_v1.py` |
| 启动脚本 | `evaluation/scripts/run_legacy_deepseek_pilot50_v1.sh` |
| 远端裁判结果 | `evaluation/runs/innovation1_pilot50_20260711_v1/judge_deepseek_legacy_v1/` |
| 本地结果副本 | `artifacts/innovation1_pilot50_20260711/judge_deepseek_legacy_v1/` |
| 完整性 | 5 组均 50/50，合计 250/250 分数可解析；原始预测文件未写入裁判分数 |

整理前备份中的旧脚本将 API key 写在源码中；当前脚本只从 `DEEPSEEK_API_KEY` 环境变量读取。此次评测复用了旧连接，但没有将密钥写入新代码、日志或结果文件。

### 6.2 总结果

| 方法 | Answer 1/0.5/0 | Strict | Relaxed | Relaxed 95% bootstrap CI |
|---|---:|---:|---:|---:|
| Raw Uniform | 32 / 14 / 4 | **64.00%** | **78.00%** | [69.00%, 86.00%] |
| CLIP Single-Peak | 31 / 12 / 7 | 62.00% | 74.00% | [63.00%, 84.00%] |
| AdSlot Fixed | 28 / 17 / 5 | 56.00% | 73.00% | [63.00%, 82.00%] |
| AV Response V1 | 29 / 14 / 7 | 58.00% | 72.00% | [61.00%, 82.00%] |
| AV Response V2 | 26 / 16 / 8 | 52.00% | 68.00% | [57.00%, 78.00%] |

主类型每类严格固定为 10 条。旧脚本同时按 `question_type` 的全部成员关系统计，因此日志中的类型计数可超过 50；论文分析固定采用主类型统计，成员关系统计只用于兼容历史输出。

### 6.3 配对结果与复评

- AV V1 对 AV V2：V1 胜 7、平 38、V2 胜 5，Relaxed 平均差为 `+4` 个百分点，95% bootstrap CI 为 `[-4, +13]` 个百分点；不能认为 V1 或 V2 存在稳定优势。
- Raw Uniform 对 AV V1：平均差为 `+6` 个百分点，95% CI 为 `[-2, +15]` 个百分点。
- Raw Uniform 对 AV V2：平均差为 `+10` 个百分点，95% CI 为 `[+2, +18]` 个百分点；在该 pilot 和裁判下 Raw Uniform 明显占优。
- 使用旧脚本精确 API URL 对 AV V1/V2 独立重复裁判一次：两种方法的总体 Strict/Relaxed 与第一次完全相同，且两种方法均逐题 50/50 一致。复评路径为 `judge_deepseek_legacy_v1_repeat_av/`。

### 6.4 当前结论与使用边界

本次 pilot 没有验证可靠性校准或局部裁剪能够提升 QA。Raw Uniform 当前最好，V2 也没有优于 V1。50 条样本的置信区间较宽，不能据此宣布方法最终失败，但足以否决“直接扩到 balanced-3000”的计划。

下一步先审查 Raw Uniform 胜出而 AV 方法失分的配对样本，重点检查 `16 全局 + 16 局部` 是否替换掉了必要的时间上下文，以及可靠性权重是否压低了价格、Logo、CTA 等脆弱小目标。只做最小预算比例实验（如 `32+0`、`24+8`、`16+16`）和必要机制消融，并增加小规模人工 Evidence Recall；在定位到原因前不叠加新模块。

该 DeepSeek 评测与历史实验具有脚本口径可比性，但 API 后端没有可固定的服务端 checkpoint。最终论文主表仍应在同一时间对全部方法统一重评，并对关键争议样本人工复核。

## 7. 裁判口径诊断与全局/局部预算比例实验

### 7.1 为什么增加 Answer-only 诊断

模型回答遵循 `[Observation] -> [Reasoning] -> [Answer]` 三段格式，而历史 `evaluate_compare_new.py` 最多读取完整响应的前 300 词。检查发现最终 `[Answer]` 标记在 Raw、AV V1、AV V2 中分别有 2/50、1/50、3/50 条位于窗口外或缺失；更重要的是，即使最终答案语义相近，Observation/Reasoning 中的附加细节也会触发旧规则中的矛盾惩罚，从而改变分数。

因此保留两套结果：

- `full-response`：完全沿用历史前 300 词口径，用于和旧实验追溯比较；
- `answer-only`：仅抽取 `3. [Answer]` 段后交给同一个 DeepSeek Prompt 和 `0/0.5/1` 规则，用于判断证据方法对最终答案的实际影响。

Answer-only 不是覆盖历史指标，而是诊断口径。适配器只对形如 `: 0`、`: 0.5`、`: 1` 的无歧义裁判输出做显式解析修复，并在逐题结果中记录 `score_parse_repaired=true`。本轮 400 条 Answer-only 裁判中有 10 条使用该修复。

### 7.2 预算比例实验设置

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_budget_ratio_pilot50_20260711_v1` |
| 数据 | 与第 6 节完全相同的固定 50 条、50 个唯一视频 |
| 模型与 Prompt | 与第 6 节相同 |
| 固定预算 | 32 个提交视图、32 个实际表示帧、11,664 个视觉 Token |
| 新配置 | AV V1 `24 全局 + 8 局部`、AV V2 `24+8`、AV V1 `32+0` |
| 对照 | Raw、CLIP、AdSlot、AV V1 `16+16`、AV V2 `16+16` |
| 启动脚本 | `evaluation/scripts/run_av_budget_ratio_pilot50_v1.sh` |
| 同批裁判脚本 | `evaluation/scripts/run_budget_ratio_deepseek_judges_pilot50_v1.sh` |
| 远端结果 | `evaluation/runs/innovation1_budget_ratio_pilot50_20260711_v1/` |
| 本地副本 | `artifacts/innovation1_budget_ratio_pilot50_20260711_v1/` |
| 协议审计 | 6 个推理配置全部通过；违规 0 |
| 管线等价性 | AV V1 `32+0` 与 Raw：50/50 帧索引相同、50/50 生成答案逐字节相同 |
| 测试 | AV、视觉预算、Prompt、裁判与新适配器共 27 项 `unittest` 通过 |

### 7.3 同批结果

| 方法 | Full Strict | Full Relaxed | Answer-only Strict | Answer-only Relaxed |
|---|---:|---:|---:|---:|
| Raw Uniform | **64.00%** | 77.00% | 50.00% | 68.00% |
| CLIP Single-Peak | 62.00% | 73.00% | 48.00% | 67.00% |
| AdSlot Fixed | 58.00% | 74.00% | **56.00%** | **72.00%** |
| AV V1 `16+16` | 58.00% | 72.00% | 52.00% | 68.00% |
| AV V2 `16+16` | 54.00% | 70.00% | 46.00% | 68.00% |
| AV V1 `24+8` | 56.00% | 72.00% | 48.00% | 66.00% |
| AV V2 `24+8` | 56.00% | 71.00% | 44.00% | 64.00% |
| AV V1 `32+0` | **64.00%** | **78.00%** | 50.00% | 68.00% |

Answer-only 配对结果：Raw 对 V1 `24+8` 的平均差为 `+2` 个百分点，95% CI `[-6,+10]`；V1 `16+16` 对 V1 `24+8` 为 `+2` 个百分点，95% CI `[-6,+11]`。两者区间均跨 0，但 `24+8` 没有显示正向趋势。V2 `24+8` 同样没有改善。

### 7.4 结论和裁判波动

单纯从 `16+16` 改为 `24+8` 不能提升准确率，尤其在 Answer-only 的 Type 1/2 上下降，因此停止继续扫描 `20+12`、`28+4` 等固定比例。`32+0` 与 Raw 完全等价，证明差异来自证据预算，不是两条推理管线或随机生成。

DeepSeek 服务端 checkpoint 无法固定。同一输入在不同时段批次存在约 1-2 个百分点的绝对分数波动：例如 AV V1 Answer-only 曾复评为 `54%/69%`，本次八方法同批为 `52%/68%`。因此以后只使用同批配对差和置信区间判断方法优劣，并对最终主表重复裁判或人工复核；禁止跨批次直接比较 1-2 个百分点差异。

离线分析显示，相关性集中度与最佳预算存在关联，但分层五折路由仅把 V1 Answer-only 从 `52%/68%` 提高到约 `52%/69%`，尚不足以成立。下一步保持 `16+16`，只增加时间分箱覆盖约束，验证能否同时保留局部细节和完整叙事。

## 8. 时间覆盖约束负结果与有效答案 Pilot 修正

### 8.1 时间覆盖实验设置

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_temporal_coverage_pilot50_20260711_v1` |
| 数据 | 原固定 50 条 pilot；每类 10 条、50 个唯一视频 |
| 对照 | AV V1/V2 `16 全局 + 16 局部` |
| 新配置 | V1+4 分箱、V1+8 分箱、V2+8 分箱 |
| 约束方式 | 每个时间分箱先保留一个最高分锚点，再按相关性补足 Top-16 |
| 固定预算 | 32 个提交视图、32 个实际表示帧、11,664 个视觉 Token |
| 二次采样 | 无；`do_sample_frames=False` |
| 推理入口 | `evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py` |
| 启动脚本 | `evaluation/scripts/run_av_temporal_coverage_pilot50_v1.sh` |
| 双口径裁判 | `evaluation/scripts/run_temporal_coverage_deepseek_judges_pilot50_v1.sh` |
| 远端结果 | `evaluation/runs/innovation1_temporal_coverage_pilot50_20260711_v1/` |
| 协议审计 | 3 个新配置均为 50/50、错误 0、预算违规 0 |
| 测试 | AV、预算、Prompt、裁判和覆盖选择共 27 项 `unittest` 通过 |

### 8.2 同批结果

| 方法 | Full Strict | Full Relaxed | Answer-only Strict | Answer-only Relaxed |
|---|---:|---:|---:|---:|
| Raw Uniform | 64.00% | 77.00% | 50.00% | 68.00% |
| AdSlot Fixed | 56.00% | 72.00% | 54.00% | **71.00%** |
| AV V1 `16+16` | 58.00% | 72.00% | **54.00%** | 69.00% |
| AV V2 `16+16` | 52.00% | 68.00% | 46.00% | 68.00% |
| AV V1 + 4 分箱 | 60.00% | 73.00% | **54.00%** | 69.00% |
| AV V1 + 8 分箱 | 50.00% | 70.00% | 48.00% | 66.00% |
| AV V2 + 8 分箱 | 62.00% | 76.00% | **54.00%** | 69.00% |

V1+4 分箱与 V1 的 Answer-only 配对为 1 胜、48 平、1 负，均值差为 0，95% CI `[-3,+3]` 个百分点；它只改变 8/50 条的全局帧集合，未形成有效算法差异。V1+8 分箱相对 V1 为 4 胜、39 平、7 负，覆盖版本低 3 个百分点，95% CI `[-10,+3]`。V2+8 分箱的 full-response 提升主要来自推理文本；Answer-only 相对 V2 仅高 1 个百分点，95% CI `[-5,+7]`，不能视为稳定增益。因此时间覆盖保留为可选消融，不作为默认方法，也停止继续扫描固定分箱规则。

### 8.3 原 Pilot 的标准答案缺失

进一步审计发现，原 50 条 pilot 中有 22 条 `_modify` 问题的 `answer` 为空，按主类型分布为 Type 1/2/3/4/5=`4/5/6/3/4`。旧 DeepSeek Prompt 同时包含 `meta_info`，因此这些题仍会得到分数，但它们不是标准的“候选答案对参考答案”评价，且分数显著偏高。原 pilot 的整体数字今后只作历史诊断，不进入最终主表。

Answer-only 按参考答案可用性分层如下：

| 方法 | 28 条非空 Strict/Relaxed | 22 条空答案 Strict/Relaxed |
|---|---:|---:|
| Raw Uniform | 39.29% / 60.71% | 63.64% / 77.27% |
| AdSlot Fixed | **46.43% / 64.29%** | 63.64% / 79.55% |
| AV V1 | 42.86% / 60.71% | 68.18% / 79.55% |
| AV V1 + 4 分箱 | 39.29% / 58.93% | **72.73% / 81.82%** |
| AV V1 + 8 分箱 | 35.71% / 55.36% | 63.64% / 79.55% |
| AV V2 + 8 分箱 | **50.00% / 64.29%** | 59.09% / 75.00% |

分层报告位于远端结果根目录的 `reference_availability_full_response.*` 和 `reference_availability_answer_only.*`；生成脚本为 `evaluation/eval/analyze_reference_availability.py`。

### 8.4 有效答案 Pilot

| 字段 | 内容 |
|---|---|
| 数据 ID | `pilot50_validanswer_balanced5x10_seed42_uniquevideo` |
| 构建策略 | 保留旧 pilot 的全部 28 条非空答案题，再从原 balanced600 源按主类型补齐 |
| 规模 | 50 条；每类 10 条；50 个唯一问题和 50 个唯一视频 |
| 与旧 pilot 重合 | 28/50 |
| 空标准答案 | 0/50 |
| 问题文件 SHA256 | `1045079bad6813c02d9b2a222c1b80d84bd8057b6e522aef56484e137af2cdad` |
| Ground Truth SHA256 | `6597eefbc1ab20f25a1f1b020dba8e2c8014379b13681a1ce8fb48114d2b1855` |
| 构建器 | `evaluation/scripts/build_balanced_pilot_subset.py --require-nonempty-answer --seed-question-file ...` |
| 构建器测试 | 本地和远端 `test_build_balanced_pilot_subset.py` 均通过；重复构建字节一致 |
| 推理脚本 | `evaluation/scripts/run_validanswer_pilot50_v1.sh` |
| 实验结果根目录 | `evaluation/runs/innovation1_validanswer_pilot50_20260711_v1/` |
| GPU | 仅 2/3/5；GPU 1 保留 |
| 1 条 smoke | 五方法全部成功，32 帧、11,664 Token、预算违规 0 |
| 当前状态 | 五方法推理、协议审计和同批双口径裁判完成；AdSlot 当前最优，AV 尚无显著优势 |

有效答案 pilot 的最新七方法同批结果如下。旧 full-response 仍用于历史追溯，算法选择以 Answer-only 和配对区间为主。

| 方法 | Full Strict | Full Relaxed | Answer-only Strict | Answer-only Relaxed |
|---|---:|---:|---:|---:|
| Raw Uniform | **52.00%** | **69.00%** | 44.00% | 61.00% |
| CLIP Single-Peak | **52.00%** | 67.00% | 44.00% | 62.00% |
| AdSlot Fixed | 48.00% | 64.00% | **48.00%** | **63.00%** |
| AV V1 | 50.00% | 63.00% | 40.00% | 58.00% |
| AV V2 | 50.00% | 64.00% | 38.00% | 61.00% |
| AV V1 每帧单裁剪 | 50.00% | 66.00% | 44.00% | 61.00% |
| AV V1 固定 `0.6/0.4` 先验 + 每帧单裁剪 | 48.00% | 63.00% | 42.00% | 58.00% |

所有方法均为 50/50，32 个实际表示帧、11,664 个视觉 Token、预算违规 0。最新七方法裁判位于 `evaluation/runs/innovation1_fixedglobal_framebalanced_pilot50_20260711_v1/`。

### 8.5 每帧单裁剪消融

| 字段 | 内容 |
|---|---|
| 方法名 | `av_v1_framecap1` |
| 唯一改动 | `--max_local_views_per_frame 1`；默认 V1 为 2 |
| 结果根目录 | `evaluation/runs/innovation1_framebalanced_pilot50_20260711_v1/` |
| 全局帧 | 50/50 与 AV V1 完全相同 |
| 局部视图 | 每条 16 个局部视图来自 16 个不同源帧；原 V1 平均为 14.18 个源帧 |
| 输出变化 | 局部计划改变 46/50 条；生成答案改变 45/50 条 |
| Answer-only | `44%/61%`，相对 V1 的 `40%/58%` 为 Strict `+4`、Relaxed `+3` 个百分点 |
| 配对 | frame-cap 胜 4、平 44、负 2；均值 `+3`，95% CI `[-2,+9]` 个百分点 |
| 独立复评 | V1 与 frame-cap 均逐题 50/50 完全复现，配对结果不变 |
| 当前判断 | 可重复正向趋势；保留为当前 AV 最优结构，但尚不足以扩大到 balanced-3000 |

### 8.6 固定全局先验消融

固定 `0.6 问题 + 0.4 ASR` 后，Answer-only 为 `42%/58%`，低于动态 frame-cap 的 `44%/61%`。两者全局帧仅 13/50 完全相同，说明先验覆盖确实改变了选择；但固定版没有产生增益，因此停止继续扫描选帧权重。

该固定版仍不等于 CLIP 基线：它与 CLIP 仅 25/50 帧集完全相同，因为旧 CLIP 入口只使用 ASR 前 100 字符，而 AV 入口使用更完整的 ASR。该实验只解释“动态先验 vs 固定先验”，不得写成严格 CLIP 选帧复现。

### 8.7 区域证据审计

在有效答案 pilot 中完成人工审查 23 条，共 30 个必需证据单元，其中 10 个带原始分辨率帧上核对的归一化区域框。完整参考答案可由视频/ASR 支持 17 条，部分可观测 6 条。Unfear 样本存在明确冲突：视频显示 `+100 testers among doctors`，标准答案的 ASD patients and families 来自 `meta_info`。

| 方法 | 提交视图时间证据精度 | 证据单元命中 | Region Recall |
|---|---:|---:|---:|
| CLIP Single-Peak | 53.26% | **29/30** | **10/10** |
| AdSlot Fixed | 52.31% | 28/30 | 9/10 |
| AV V1 | **53.80%** | 26/30 | 7/10 |
| AV V1 每帧单裁剪 | 53.53% | 26/30 | 7/10 |
| AV V1 每帧单裁剪、80% 覆盖 | 53.53% | 28/30 | 9/10 |
| AV V1 每帧单裁剪+缓存 OCR | 53.53% | **29/30** | **10/10** |

Region Recall 要求方法在正确时间区间提交的局部裁剪包含标注框中心。V1 和每帧单裁剪共同漏掉 GBP340 顶部金额以及 Gatorade 的第 1、3 步，说明 frame-cap 的问答趋势不是由更好的区域定位产生。所有选择方法仍共同漏掉 Ozuna 从理发场景转为龙舌兰庆祝的中段事件，这是当前唯一共同时间遗漏。

本地标注与指标副本位于 `artifacts/innovation1_validanswer_pilot50_20260711_v1/evidence_recall_annotation_v1/`。

### 8.8 统一放大裁剪负结果

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_framebalanced_cov80_pilot50_20260711_v1` |
| 方法名 | `av_v1_framecap1_cov80` |
| 唯一改动 | `--crop_coverage_target 0.80`，对照为原 0.60 |
| 远端结果 | `evaluation/runs/innovation1_framebalanced_cov80_pilot50_20260711_v1/` |
| 协议 | 50/50；16 全局+16 局部；32 个表示帧；11,664 Token；违规 0；无二次采样 |
| Region Recall | 9/10；GBP340 框中心仍比裁剪上边界高 1.5% 归一化高度 |
| 裁剪尺度 | 大多数局部视图变为 0.85，实质是普遍放大而非问题条件化定位 |
| 本地 Llama Answer-only | `40%/47%`；低于 frame-cap 的 `50%/55%` |
| 配对 | frame-cap 9 胜、39 平、2 负；均值 `+8`，95% CI `[0,+16]` 个百分点 |
| 结论 | 作为负结果保留；停止统一扩大裁剪及继续扫描固定覆盖率 |

### 8.9 查询条件化缓存 OCR 响应

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_cachedocr_framebalanced_pilot50_20260711_v1` |
| 方法名 | `av_v1_framecap1_cachedocr` |
| 模型/checkpoint | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| 主推理入口 | `evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py` |
| OCR 响应 | `evaluation/methods/av_evidence/ocr_response.py` |
| OCR 预计算 | `evaluation/tools/precompute_ocr_evidence.py` |
| 启动脚本 | `evaluation/scripts/run_av_cachedocr_framebalanced_pilot50_v1.sh` |
| 远端结果 | `evaluation/runs/innovation1_cachedocr_framebalanced_pilot50_20260711_v1/` |
| 本地完整副本 | `artifacts/innovation1_cachedocr_framebalanced_pilot50_20260711_v1/` |
| OCR 运行时 | `<REMOTE_HOME>/tools/adsqa_rapidocr`；RapidOCR 3.9.1、ONNX Runtime 1.23.2；CPU 离线预计算 |
| OCR 缓存 | `evaluation/cache/ocr/pilot50_validanswer_framecap1_rapidocr_v1.json` |
| 缓存 SHA256 | `7bb0400e3c84542b6188c1bc589586b631895420179bfee0a54bd2df00d8b489` |
| 缓存规模 | 50 条、800 个选中全局帧、525 个含文字帧、2,210 个检测框；69.18 秒 |
| 固定配置 | frame-cap=1；裁剪覆盖目标 0.60；OCR 最低置信度 0.50；OCR 可靠性 0.80 |
| 公平协议 | 50/50；16 全局+16 局部；32 个表示帧；11,664 Token；违规 0；无二次采样 |
| Region Recall | **10/10**；证据单元 29/30 |
| 裁剪尺度 | 760/800 为原 0.70 尺度，40/800 为 0.85；不是统一放大 |
| OCR 激活 | 525/800 个局部视图有 OCR 证据；其平均融合权重约 0.2186 |
| 回归测试 | `test_ocr_response.py` 与 `test_evidence_recall_annotation.py` 共 8 项通过 |
| 重复性 | 独立 11 条重跑：答案、帧索引、候选框、最终裁剪、预算和响应轨迹均 11/11 完全一致 |

OCR 不作为独立问答模块，而是与问题、ASR 一起形成空间响应场。每个文字框先按 OCR 置信度和问题/音频语义相关性加权，再栅格化到 16x16 响应图；数字或货币问题增加类型匹配。推理阶段只读缓存，不导入 OCR 运行时，因此不会改变 Qwen3-VL 显存或视觉预算。

实现审查后补充了 fail-closed 校验：缓存问题 ID、样本帧 rank、重复项或检测列表结构不一致时立即报错，不再静默退回无 OCR；未来运行配置同时记录缓存 SHA256。三分片真实缓存 dry-run 全部通过。该改动只加强未来重跑的复现约束，不回写或冒充已经完成的 50 条源快照。

PaddleOCR 方案因远端 Paddle 2.6.2 与 PaddleX 新接口不兼容，修补后还出现段错误，已停止；RapidOCR 隔离环境没有修改 ReadR 推理环境。

### 8.10 本地临时裁判结果与 DeepSeek 恢复前状态

本节记录 DeepSeek 恢复前的本地临时裁判结果。为先检查方向，当时使用已有 `<REMOTE_PROJECT_ROOT>/models/Meta-Llama-3.1-70B-Instruct-AWQ-INT4` 和旧 0/0.5/1 Answer-only Prompt 完成一次同批本地裁判；裁判服务结束后已释放 GPU 2，GPU 1 全程未使用。DeepSeek 后续恢复结果以 8.13 节为准。

DeepSeek 恢复入口已准备为 `evaluation/scripts/run_cachedocr_deepseek_judge_pilot50_v1.sh`。它复用 `evaluate_compare_new.py` 的固定 Prompt/解析哈希，默认只运行 Answer-only，并在 AdSlot、frame-cap、80% 覆盖和缓存 OCR 四方法间同批计算配对区间。脚本默认断点续评且不占 GPU；只有显式 `OVERWRITE=1` 才清空已有裁判副本。远端语法和输入目录检查已通过，缺少密钥时会在任何 API 调用前明确退出。

| 方法 | Strict | Relaxed | Answer 1/0.5/0 |
|---|---:|---:|---:|
| AdSlot Fixed | 48.00% | 50.00% | 24 / 2 / 24 |
| AV V1 每帧单裁剪 | 50.00% | 55.00% | 25 / 5 / 20 |
| AV V1 每帧单裁剪、80% 覆盖 | 40.00% | 47.00% | 20 / 7 / 23 |
| AV V1 每帧单裁剪+缓存 OCR | **54.00%** | **58.00%** | 27 / 4 / 19 |

缓存 OCR 相对 frame-cap 为 6 胜、40 平、4 负，均值 `+3`，95% CI `[-6,+11]` 个百分点；相对 AdSlot 为 7 胜、41 平、2 负，均值 `+8`，95% CI `[-2,+19]`。方向为正但区间均跨 0，且逐题审查发现本地 Llama 对若干近义回答评分不稳定。因此当前状态是“区域指标成立、问答趋势待确认”，不得据此扩大到 balanced-3000。

对 AdSlot 和 frame-cap 的 100 个历史 DeepSeek/本地 Llama 同题分数做交叉审计后，逐题完全一致率仅 73%，平均绝对差 0.145；本地 Llama 平均比 DeepSeek 低 0.095，主要把 DeepSeek 的 `0.5` 判为 `0`。更重要的是，frame-cap 相对 AdSlot 的均值在历史 DeepSeek 下为 `-2` 个百分点，在本地 Llama 下为 `+5`，方法排序发生反转。因此本地 Llama 不能作为 DeepSeek 的替代裁判，只能识别像统一 80% 放大这类明显负结果。分析文件为 `evaluation/runs/innovation1_cachedocr_framebalanced_pilot50_20260711_v1/judge_agreement_historical_deepseek_vs_local_llama_v1.json`，复现脚本为 `evaluation/eval/analyze_judge_agreement.py`。

该本地结果现仅作为历史方向筛查记录，不进入论文主表。DeepSeek 已恢复并否定其 OCR 正向趋势，详见 8.13 节。

### 8.11 OCR 跨帧相关性竞争消融

当前帧内 OCR 会在每一帧独立做 min-max 归一化，因此一帧只有一个无关文字时，该文字也会得到相关性 1。为验证这一结构缺陷，新增 `--ocr_relevance_scope video`：同一问题的 16 个选中帧内所有文字共同与问题和各自 ASR 窗口比较，再在整段视频内归一化；每帧 OCR 源可靠性同时使用该帧最高加权相关性。旧 `frame` 模式保留为默认且 GBP340 smoke 的全局帧、全部候选框、最终局部框和答案与历史运行逐项一致。

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_cachedocr_videorelevance_pilot50_20260711_v1` |
| 方法名 | `av_v1_framecap1_cachedocr_videorelevance` |
| 唯一算法改动 | OCR 相关性从逐帧归一化改为 16 帧联合归一化，并以加权相关性校准每帧 OCR 可靠性 |
| 启动脚本 | `evaluation/scripts/run_av_cachedocr_videorelevance_pilot50_v1.sh` |
| 远端结果 | `evaluation/runs/innovation1_cachedocr_videorelevance_pilot50_20260711_v1/` |
| 本地副本 | `artifacts/innovation1_cachedocr_videorelevance_pilot50_20260711_v1/` |
| 公平协议 | 50/50；16 全局+16 局部；32 个表示帧；11,664 Token；无二次采样；违规 0 |
| 全局帧 | 与帧内 OCR 50/50 完全相同 |
| 局部计划 | 最终局部框 50/50 改变；视觉计划 49/50 改变；生成答案 37/50 改变 |
| OCR 源可靠性均值 | 帧内 0.7598；跨帧 0.5508 |
| OCR 融合权重均值 | 帧内 0.2186；跨帧 0.1669 |
| 裁剪尺度 | 帧内 0.70/0.85=`760/40`；跨帧=`759/41`，不是统一放大或缩小 |
| Evidence Recall | 两者均为证据单元 29/30、Region Recall **10/10** |
| 本地 Llama Answer-only | 帧内 `54%/58%`；跨帧 `52%/55%` |
| 本地配对 | 跨帧 3 胜、42 平、5 负；跨帧减帧内均值 `-3`，95% CI `[-11,+5]` 个百分点 |
| 重复性 | 独立索引 39:50 的 11 条：答案、帧、候选框、最终框、响应、预算和 OCR 统计均 11/11 完全一致 |
| 当前判断 | 有效抑制无关 OCR 且区域指标不退化，但 DeepSeek QA 进一步下降；保留为负消融，默认仍为帧内 OCR |

本地 Llama 的 8 个分歧中，跨帧版本的下降主要出现在“视觉隐喻、视觉元素、幻想交通工具”等非文字主导问题，说明统一压低 OCR 后改变了视觉热图的相对位置，但尚不能证明更符合最终答案。DeepSeek 同批结果为帧内 `44%/61%`、跨帧 `40%/56%`；跨帧相对帧内 2 胜、42 平、6 负，均值 `-5`，95% CI `[-1,+12]` 个百分点（以“帧内减跨帧”记）。因此停止继续扫描跨帧权重，脚本 `evaluation/scripts/run_cachedocr_videorelevance_deepseek_judge_pilot50_v1.sh` 仅用于复现。

### 8.12 本地裁判候选的预注册校准规则

在查看新模型评分前，固定使用历史 DeepSeek 已完成的同一批 100 个 `AdSlot Fixed` 与 `AV V1 每帧单裁剪` Answer-only 分数做校准。候选为官方 `Qwen3-32B-AWQ`，只运行旧 Prompt 和旧 `0/0.5/1` 解析；关闭模型思考输出，不改标准答案、候选答案或裁判规则。模型仅使用 GPU 2，GPU 1 不使用，评完立即关闭服务。

候选必须同时满足以下条件才可作为后续实验的临时方向裁判：

1. 两方法合并 100 个同题分数的逐题精确一致率不低于 `80%`；
2. 合并平均绝对差不高于 `0.10`；
3. `AV V1 每帧单裁剪 - AdSlot Fixed` 的方法均值方向与历史 DeepSeek 一致，不得发生排序反转；
4. 即使通过，也只能用于筛除明显负结果和安排实验优先级，最终论文主表仍由历史同口径 DeepSeek 复评。

任何一项不满足即淘汰该本地模型，不继续下载更多模型或依据它扩大样本。校准入口为 `evaluation/scripts/run_qwen3_32b_judge_calibration_pilot50_v1.sh`，一致性分析继续使用 `evaluation/eval/analyze_judge_agreement.py`。

校准已完成，三项门禁全部失败，因此 `Qwen3-32B-AWQ` 不作为 AdsQA 临时裁判。

| 字段 | 内容 |
|---|---|
| 模型来源 | 官方 [Qwen3-32B-AWQ](https://huggingface.co/Qwen/Qwen3-32B-AWQ) |
| 本地模型 | `<REMOTE_PROJECT_ROOT>/models/Qwen3-32B-AWQ` |
| 固定 revision | `0499c3ac83fdef8810b907a23894ba91e95eddd8` |
| 模型校验 | 4 个权重分片及配置、tokenizer 均通过固定 SHA256；清单为 `evaluation/configs/qwen3_32b_awq_revision_0499.sha256` |
| 服务配置 | vLLM 0.11.0；GPU 2；AWQ Marlin；4,096 上下文；eager；关闭 thinking；温度 0 |
| 校准样本 | 历史 DeepSeek 已评分的 AdSlot 50 条 + frame-cap 50 条，共 100 个同题分数 |
| 协议 | 原 Answer-only Prompt 与解析函数哈希不变；100/100 输出均为严格 `Answer: 0/0.5/1` |
| 远端结果 | `evaluation/runs/innovation1_framebalanced_pilot50_20260711_v1/judge_local_qwen3_32b_awq_answer_only_calibration_v1/` |
| 本地副本 | `artifacts/local_judge_calibration_qwen3_32b_awq_20260711_v1/` |
| AdSlot Qwen3 | Strict `38%`，Relaxed `53%`；历史 DeepSeek 为 `48%/63%` |
| frame-cap Qwen3 | Strict `42%`，Relaxed `56%`；历史 DeepSeek 为 `44%/61%` |
| 逐题一致率 | AdSlot `68%`；frame-cap `82%`；合并 **75%**，低于预注册 `80%` |
| 合并平均绝对差 | **0.125**，高于预注册 `0.10` |
| 系统偏差 | Qwen3 相对 DeepSeek 平均 `-0.075`；32 个 DeepSeek `0.5` 中有 13 个被判为 `0` |
| 方法均值方向 | 历史 DeepSeek：frame-cap - AdSlot=`-0.02`；Qwen3=`+0.03`，发生排序反转 |
| 门禁结论 | 精确一致率、平均绝对差、方法方向三项均失败；`passed=false` |

该负结果说明更换一个较新的 32B 本地模型仍不能自动获得 DeepSeek 同口径。Qwen3 服务结束后 GPU 2 已释放，GPU 1 全程未使用；不再用它评价帧内/跨帧 OCR，也不依据其结果扩大样本。远端还发现官方 Qwen3.5-35B-A3B-FP8 权重，但 A6000 计算能力为 8.6，而其 FP8 加载器要求至少 8.9，因此只做了兼容性探针，没有产生任何评分。DeepSeek 已恢复且可稳定复现历史分数，因此停止继续安装本地裁判模型。

### 8.13 DeepSeek 旧口径恢复与 OCR 最终裁判

从整理前只读备份中的旧评测脚本恢复了同一 DeepSeek 访问配置。密钥未打印、未写入活动代码或实验产物，仅由运行包装器在内存中注入。继续使用历史模型别名 `deepseek-chat`、旧 Answer-only Prompt 和旧 `0/0.5/1` 解析；当前 API 实际返回模型为 `deepseek-v4-flash`。

恢复后的口径先与历史结果校验：AdSlot 50 条与 frame-cap 50 条共 100 个共享分数全部逐题一致，精确一致率 `100/100`、平均绝对差 `0`，两方法均值差也保持 `frame-cap - AdSlot=-0.02`。随后两次独立调用中，重复的 AdSlot 与帧内 OCR 又分别 `50/50` 逐题及原始裁判输出完全一致，因此当前服务可继续承担本论文旧口径主裁判。

| 方法 | Strict | Relaxed | Answer 1/0.5/0 |
|---|---:|---:|---:|
| AdSlot Fixed | **48.00%** | **63.00%** | 24 / 15 / 11 |
| AV V1 每帧单裁剪 | 44.00% | 61.00% | 22 / 17 / 11 |
| AV V1 每帧单裁剪、80% 覆盖 | 38.00% | 55.00% | 19 / 17 / 14 |
| AV V1 每帧单裁剪+帧内缓存 OCR | 44.00% | 61.00% | 22 / 17 / 11 |
| AV V1 每帧单裁剪+跨帧 OCR 相关性 | 40.00% | 56.00% | 20 / 16 / 14 |

关键配对结论：

- 帧内 OCR 相对 frame-cap 为 4 胜、42 平、4 负，均值 `0`，95% CI `[-6,+6]` 个百分点；没有 QA 增益；
- AdSlot 相对帧内 OCR 为 10 胜、32 平、8 负，均值 `+2`，95% CI `[-6,+10]`；
- 帧内 OCR 相对跨帧 OCR 为 6 胜、42 平、2 负，均值 `+5`，95% CI `[-1,+12]`；跨帧校准没有改善 QA；
- 80% 统一扩大仍明显较差，frame-cap 相对其均值 `+6`，95% CI `[0,+12]`。

边界分析显示，帧内 OCR 相对 frame-cap 只有 8 条得分变化，其中 7 条不含显式文字意图。变化样本的 OCR 最大源可靠性约为 `0.986-1.000`，但大量文字与问题无关；例如隐喻问题仍把 `MASH/DIGITAIL` 或订票电话赋予高 OCR 权重。这说明当前 `source_reliability` 主要测量识别置信度和帧内相对排序，不能表示“文字是否足以回答当前问题”。下一步不再扫描 OCR 权重，而是在训练/开发数据上预定义问题意图与绝对语义可靠性门控，再对固定 pilot 做一次验证。

| 产物 | 路径 |
|---|---|
| 四方法 DeepSeek 结果 | `evaluation/runs/innovation1_cachedocr_framebalanced_pilot50_20260711_v1/judge_deepseek_legacy_answer_only_v1/` |
| 跨帧 DeepSeek 结果 | `evaluation/runs/innovation1_cachedocr_videorelevance_pilot50_20260711_v1/judge_deepseek_legacy_answer_only_v1/` |
| 本地副本 | `artifacts/innovation1_cachedocr_framebalanced_pilot50_20260711_v1/` 与 `artifacts/innovation1_cachedocr_videorelevance_pilot50_20260711_v1/` |
| 边界分析 | `evaluation/eval/analyze_ocr_judge_boundary.py` 及 `boundary_framecap_vs_cachedocr.json/.md` |
| 裁判产物校验 | `artifacts/deepseek_judge_20260711_v1.sha256` |

### 8.14 独立 Confirm-300 与零分布 OCR 预注册

旧 50 条 pilot 已被用于多轮机制诊断，今后只承担 smoke、协议回归和人工 Evidence Recall，不再承担方法胜负确认。新的 Confirm-300 在看到零分布 OCR 的任何问答结果前固定，来源为 balanced-600，排除旧 pilot 的全部问题及全部视频。

| 字段 | 内容 |
|---|---|
| 问题文件 | `data/confirm300_validanswer_disjoint_pilot50_question.json` |
| Ground Truth | `data/confirm300_validanswer_disjoint_pilot50_groundtruth.json` |
| Manifest | `data/confirm300_validanswer_disjoint_pilot50_manifest.json` |
| 规模 | 300 条；Type 1-5 各 60 条 |
| 唯一性 | 300 个问题、300 个视频 |
| 与旧 pilot 重合 | 问题 `0`、视频 `0` |
| 空标准答案 | `0/300` |
| 问题 SHA256 | `5e25577352a1411df387c51df0bd462036eec7faf78446e36082977374b7d968` |
| Ground Truth SHA256 | `1b74acdb3758f170f471fd6296202130a5a550b15c7b5fc248b889e3945f5665` |
| ASR | 全局文本 265 条；缺失/其他 35 条 |
| 固定比较方法 | Raw Uniform、CLIP Single-Peak、AdSlot Fixed、AV frame-cap、AV frame-cap + 零分布 OCR |
| GPU | 只用 2/3/5；GPU 1 保留 |
| 公平协议 | 同一 Qwen3-VL checkpoint、答案 Prompt、32 个表示帧、11,664 Token、关闭二次采样 |
| 主裁判 | 已恢复并通过历史一致性校验的 DeepSeek Answer-only 旧口径 |
| 结果根目录 | `evaluation/runs/innovation1_confirm300_20260711_v1/` |

运行边界：问题 `611e166ba44c2a31cbf29f62b5986dcc_7` 的视频只有 31 个可解码源帧，Raw Uniform 无法取得 32 个唯一全局帧。固定处理为 `linspace_floor_repeat`：保持均匀序列并确定性重复 1 个源帧；证据中记录 31 个唯一源帧、1 个重复提交视图及重复序号。该条仍由处理器验证为 32 个实际表示视图、11,664 Token、关闭二次采样。没有替换确认样本，也没有把缺失计 0；正常长度视频行为不变。

零分布 OCR 不使用 pilot 得分拟合阈值。对 OCR 文本 `t` 与当前问题 `q` 的 CLIP 相似度 `s(t,q)`，以 500 个 `data/train.json` 训练问题形成经验零分布：

```text
p(t,q) = mean_q'[s(t,q') < s(t,q)]
c_abs(t,q) = max(0, 2p(t,q) - 1)
r_final(t,q) = r_frame_minmax(t,q) * c_abs(t,q)
```

`c_abs` 在零分布中位数及以下为 0，随经验百分位单调增加，不新增从 pilot 搜索的阈值。OCR 源可靠性由置信度加权响应计算，不再直接等于识别置信度。数字/金额问题沿用既有类型先验，其余预算、选帧、裁剪候选与 frame-cap 完全相同。

在此之前测试过固定“文字问题/非文字问题”CLIP 原型门控，但它把训练集 413/500、旧 pilot 41/50 都判为偏文字，无法形成有效区分，因此没有进入代码或 Confirm-300。训练零分布含 500 个问题、100 个唯一训练视频，与 Confirm-300 的视频重合为 0；训练文件 SHA256 为 `3cf47613da457d857222b38c671b57d0cd9a61d245833a9b5423f8d1b786d6a1`。

预注册停止规则：先完成 1 条真实 smoke；随后 Confirm-300 只运行该一个候选，不在结果出来后扫描百分位、温度或 OCR 权重。若相对 frame-cap 的 DeepSeek 配对均值不为正，或区间宽且边界变化仍主要来自非充分文字，则该机制作为负消融停止；只有方向为正、协议与边界审查通过，才进入更大数据集。

### 8.15 Confirm-300 五方法统一裁判与零分布 OCR 负结果

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_confirm300_20260711_v1` |
| 完成日期 | 2026-07-12 |
| 模型/checkpoint | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| 数据集 | Confirm-300；Type 1-5 各 60；与 pilot50 问题/视频均零重合 |
| 方法 | Raw Uniform、CLIP Single-Peak、AdSlot Fixed、AV frame-cap、AV frame-cap+train-null OCR |
| 公平协议 | 各 300/300；32 个表示/提交视图；11,664 Token；关闭二次采样；违规 0 |
| Answer Prompt | `adsqa_answer_prompt_v1`；SHA256 `238b6915bcbe785708eb6b8ac877b930d2ac8bbac5148ff630f4db1ee96061a9` |
| 主裁判 | 历史 Answer-only DeepSeek 口径；实际 `deepseek-v4-flash` 1500/1500；全部可解析 |
| Bootstrap | 配对 10,000 次；seed 42 |
| 远端结果 | `evaluation/runs/innovation1_confirm300_20260711_v1/` |
| 本地归档 | `<LOCAL_RESEARCH_ROOT>/artifacts/innovation1_confirm300_20260711_v1/` |
| OCR 缓存 | `evaluation/cache/ocr/confirm300_framecap1_rapidocr_v1.json` |
| OCR 缓存 SHA256 | `2911834a36b9fcc399f76f1f0b67db229dd21cf5d572d1948e25c0840ed8ced4` |
| 训练问题 SHA256 | `3cf47613da457d857222b38c671b57d0cd9a61d245833a9b5423f8d1b786d6a1` |
| 当前状态 | Confirm-300 完成；零分布 OCR 按预注册规则停止；转入 24+8 预算实验 |

| 方法 | Answer 1/0.5/0 | Strict | Relaxed | Strict 95% CI | Relaxed 95% CI |
|---|---:|---:|---:|---:|---:|
| Raw Uniform | 150 / 111 / 39 | **50.00%** | **68.50%** | [44.33,55.67] | [64.50,72.33] |
| CLIP Single-Peak | 147 / 98 / 55 | 49.00% | 65.33% | [43.33,54.67] | [61.00,69.50] |
| AdSlot Fixed | 134 / 107 / 59 | 44.67% | 62.50% | [39.00,50.33] | [58.17,66.67] |
| AV frame-cap 16+16 | 144 / 104 / 52 | 48.00% | 65.33% | [42.33,53.67] | [61.00,69.50] |
| AV frame-cap+train-null OCR | 139 / 110 / 51 | 46.33% | 64.67% | [40.67,52.00] | [60.50,68.83] |

关键配对结果：

- train-null OCR 相对 frame-cap：27 胜、244 平、29 负，均值 `-0.67` 个百分点，95% CI `[-3.33,+1.83]`；
- Raw 相对 frame-cap：57 胜、201 平、42 负，均值 `+3.17`，95% CI `[-0.67,+7.00]`；
- Raw 相对 train-null OCR：59 胜、200 平、41 负，均值 `+3.83`，95% CI `[+0.17,+7.67]`；
- frame-cap 相对 AdSlot：50 胜、213 平、37 负，均值 `+2.83`，95% CI `[-0.50,+6.17]`。

机制审计确认候选与 frame-cap 的全局帧 300/300 相同，但局部框改变 299/300。OCR 平均每题激活 10.83 帧，候选相对 frame-cap 的 56 个评分变化中 52 个没有显式文字意图。因此该机制不是“偶然没有显著”，而是出现了可定位的过度干预；不再在 Confirm-300 上扫描 OCR 参数。

### 8.16 预算消融、Focus-Context pilot 与 Confirm-300B 预注册

| 字段 | 24+8 替换式裁剪 | Focus-Context 32 帧 |
|---|---|---|
| 实验 ID | `innovation1_budget24g8l_pilot50_20260712_v1` | `innovation1_focuscontext32_pilot50_20260712_v1` |
| 视觉输入 | 24 全局+8 独立局部 | 32 个时间帧；其中 8 帧嵌入“全局+ROI” |
| 实际预算 | 32 视图；11,664 Token | 32 视图；11,664 Token |
| 二次采样/协议违规 | 关闭 / 0 | 关闭 / 0 |
| Answer 1/0.5/0 | 20 / 20 / 10 | 首轮 27 / 12 / 11；复评 26 / 13 / 11 |
| Strict/Relaxed | 40.00% / 60.00% | 首轮 **54.00%/66.00%**；复评 **52.00%/65.00%** |
| 相对 Raw | 4/42/4，均值 -1，CI `[-5,+8]` | 首轮 8/40/2，+6，CI `[0,+12]`；复评 6/42/2，+4，CI `[-1,+10]` |
| Evidence visual/region | 30/30；4/10 | 30/30；3/10 |
| 远端结果 | `evaluation/runs/innovation1_budget24g8l_pilot50_20260712_v1/` | `evaluation/runs/innovation1_focuscontext32_pilot50_20260712_v1/` |
| 本地归档 | `artifacts/innovation1_budget24g8l_pilot50_20260712_v1/` | `artifacts/innovation1_focuscontext32_pilot50_20260712_v1/` |
| 结论 | 无 QA 增益，停止扩大 | 两轮 pilot 正向，冻结后独立确认 |

Focus-context 在一个视觉槽位内采用上下布局：完整帧在上、响应 ROI 在下，全局/ROI 比例固定为 0.5。左右布局仅在 1 条 smoke 中因大面积黑边被淘汰，发生在完整 pilot QA 之前。正式版本保留 32 个均匀时间点，不再用局部图替换全局时间帧。

Confirm-300B 在任何候选推理前冻结：

| 字段 | 内容 |
|---|---|
| 问题文件 | `data/confirm300b_focuscontext_disjoint_prior_question.json` |
| Ground Truth | `data/confirm300b_focuscontext_disjoint_prior_groundtruth.json` |
| Manifest | `data/confirm300b_focuscontext_disjoint_prior_manifest.json` |
| 规模 | 300；Type 1-5 各 60；300 个唯一视频 |
| 排除范围 | pilot50 + 首个 Confirm-300，共 350 个问题/视频 |
| 与既有样本重合 | 问题 0；视频 0 |
| 问题 SHA256 | `7fb20f612597a8531f0c26cc653bbd0d8a0bbe2a010d9a4fc797dd93fac28d58` |
| Ground Truth SHA256 | `10c5c418c1dc8415a87cd3d704609a7578f5d8776ce84703eaf9e77551000e47` |
| ASR | 全局文本 277；缺失/其他 23 |
| 第一阶段方法 | Raw Uniform、冻结的 focus-context32-budget8 |
| 停止规则 | 候选配对均值不为正则停止；正向才补 CLIP/AdSlot/16+16，不在本集调参 |

### 8.17 Confirm-300B Focus-Context 独立确认负结果

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_confirm300b_focuscontext_20260712_v1` |
| 数据集 | Confirm-300B；Type 1-5 各 60；与此前 350 条问题/视频均零重合 |
| 模型 | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| 方法 | Raw Uniform；冻结的 focus-context32-budget8 |
| 协议 | 各 300/300；32 视图；11,664 Token；关闭二次采样；违规 0 |
| 源帧一致性 | 300/300 逐题完全一致 |
| 嵌入 ROI | 每题 8；visual plan 总数仍为 32 |
| 主裁判 | 历史 Answer-only DeepSeek；`deepseek-v4-flash` 600/600；全部可解析 |
| Bootstrap | 配对 10,000 次；seed 42 |
| 远端结果 | `evaluation/runs/innovation1_confirm300b_focuscontext_20260712_v1/` |
| 本地归档 | `artifacts/innovation1_confirm300b_focuscontext_20260712_v1/` |
| 当前状态 | 独立确认未复现；按预注册规则停止固定 focus-context |

| 方法 | Answer 1/0.5/0 | Strict | Relaxed | Strict 95% CI | Relaxed 95% CI |
|---|---:|---:|---:|---:|---:|
| Raw Uniform | 151 / 109 / 40 | 50.33% | **68.50%** | [44.67,56.00] | [64.50,72.50] |
| Focus-Context 32/8 | 154 / 93 / 53 | **51.33%** | 66.83% | [45.67,57.00] | [62.67,71.17] |

配对结果：focus-context 相对 Raw 为 36 胜、216 平、48 负，均值 `-1.67` 个百分点，95% CI `[-4.83,+1.33]`。分数转移为：`0.5->1` 29 条、`1->0.5` 28 条、`0.5->0` 20 条、`0->0.5` 5 条、`0->1` 2 条，其余 216 条不变。候选增加满分的同时也显著增加零分，因此不能只报告 Strict 的 +1。

失败归因显示，84 个变化问题中 82 个没有显式文字意图；win/tie/loss 的 crop score、density、utility 基本不可分，问题响应 concentration 均约 0.01。下一步停止下游预算与布局修改，先替换弥散的 CLIP patch-token 余弦定位器。

### 8.18 Contrastive-Gradient Localization-Only 门禁

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_contrastive_gradient_localization_pilot50_20260712_v1` |
| 模式 | localization-only；不加载 Qwen；不生成 prediction |
| 唯一改动 | 空间问题响应从 patch-token 余弦改为全局图文匹配的 gradient x input |
| 数据 | pilot50；人工完成 23 条、30 个证据单元、10 个区域框 |
| Patch-cosine concentration | mean 0.01254；median 0.01248；p90 0.01871 |
| Contrastive-gradient concentration | mean 0.15342；median 0.14692；p90 0.22810 |
| Patch-cosine Evidence/Region | 26/30；7/10 |
| Contrastive-gradient Evidence/Region | 26/30；7/10 |
| 区域变化 | GBP340 `miss->hit`；Maisa Rojas `hit->miss`；净 0 |
| 远端结果 | `evaluation/runs/innovation1_contrastive_gradient_localization_pilot50_20260712_v1/` |
| 本地归档 | `artifacts/innovation1_contrastive_gradient_localization_pilot50_20260712_v1/` |
| 结论 | 定位门禁失败，不进入 QA |

### 8.19 时间证据定位阶段：接口与真实 Smoke

| 字段 | 内容 |
|---|---|
| 阶段 ID | `innovation1_temporal_grounding_phase2` |
| 日期 | 2026-07-12 |
| 当前性质 | 接口、环境与协议 smoke；尚不是准确率实验 |
| 回答模型 | Qwen3-VL-8B；`<MODEL_ROOT>/Qwen3Vl-8B` |
| 强基线 | VideoITG-8B；官方提交 `50a60a8`；4 个权重分片已下载并通过 safetensors 读取检查 |
| 自研原型 | `ads_temporal_mmr_v1` |
| 候选/提交 | 64 个均匀候选 -> 32 个按时间顺序提交 |
| 空间处理 | 无裁剪；32 个均为全局帧 |
| 实际输入审计 | submitted 32；represented 32；padding 0；`video_grid_thw=[16,54,54]` |
| 实际视觉 Token | 11,664；预算上限 12,000 |
| 二次采样 | 关闭 |
| RAG/反思 | 均关闭 |
| Answer Prompt | `adsqa_answer_prompt_v1`；SHA256 `238b6915bcbe785708b6b8ac877b930d2ac8bbac5148ff630f4db1ee96061a9` |
| 缓存协议 | `adsqa_temporal_indices_v1`；问题哈希、候选源帧、完整排名和 Top-32 均强校验 |
| 轻量缓存 smoke | `evaluation/runs/lightweight_temporal_cache_smoke_v1/`；1/1 成功 |
| Qwen 协议 smoke | `evaluation/runs/lightweight_temporal_qwen_smoke_v1/`；1/1 成功；错误 0 |
| VideoITG 源码 | `external/VideoITG_official_main/`；归档 `external/VideoITG-main.tar.gz` |
| 隔离依赖 | `external/videoitg_pydeps/`；Transformers 4.47.1；本机编译 FlashAttention 2.8.3；builder 导入通过；不修改共享 `ReadR` 环境 |
| 当前状态 | 接口、自研 smoke、VideoITG 权重与环境已就绪；首次官方 smoke 因 GPU 2/3/5 被他人任务占用而在加载前停止，等待允许卡空闲；禁止解读单条 QA 准确率 |
| 断点与错误记录 | `cache_shard*.jsonl` 逐条落盘；`errors_shard*.jsonl` 保存异常与 traceback；`run_summary_shard*.json` 保存成功/跳过/失败数及输出哈希 |
| GPU 启动保护 | smoke 仅接受环境变量 `GPU_ID=2/3/5`，其他编号在模型加载前拒绝 |
| 候选协议修正 | 独立 64/32 点 `linspace` 不严格嵌套；当前改为 `nested_uniform_raw32_plus_maxgap_v1`，保证 Raw32 是 64 候选的严格子集 |
| 轻量嵌套缓存 | `evaluation/runs/lightweight_temporal_cache_nested_pilot50_v1/`；50/50；SHA256 `6717f3ce80e9a0501fc13207c8e34cd14327f2debc703ccff6e732566c3eabeb` |
| 缓存审计 | 50/50 通过；错误 0；源视频一致 50/50；8-bin 50/50；32 个唯一帧 |
| 人工时间证据 | 23 条、30 单元；Raw 30/30，轻量嵌套 30/30；证据帧精度 47.42% -> 53.26% |
| 时间覆盖代价 | 平均最大归一化空洞 3.28% -> 12.51%；尚需 QA 验证，不冻结配置 |
| Qwen pilot 状态 | 三分片安全启动脚本已就绪；GPU 2/3/5 均被他人占用，尚未启动 |
| Raw 对照复用审计 | 历史 Raw pilot50 重新审计 50/50 有效；32 submitted/represented；11,664 Token；二次采样关闭；违规 0 |
| 后处理门禁 | `run_lightweight_temporal_postprocess_pilot50_v1.sh`；完整视觉审计通过后才启动 Answer-only DeepSeek 与 10,000 次 Bootstrap |
| 三卡编排 | `run_lightweight_temporal_qwen_three_gpu_pilot50_v1.sh`；GPU 2/3/5 全部空闲后绑定 shard 0/1/2；任一卡占用则整组不启动 |
| DeepSeek 凭据状态 | 当前非交互 SSH 未设置 `DEEPSEEK_API_KEY`；QA 可先运行，裁判前必须恢复合法环境变量，不复用历史评分 |
| ASR 口径 | 当前只有视频级全文，无时间戳；本版为问题门控的全局 ASR-帧相似度代理，不宣称 temporal ASR alignment |
| 本地归档 | `artifacts/innovation1_temporal_phase2_20260712_v1/` |
| VideoITG 视觉塔 | 本地 SigLIP `models/siglip-so400m-patch14-384`；3.3GB；888 张量；离线模式加载 |
| VideoITG 缓存 smoke | 1/1 成功；SHA256 `083113682878ac4ef6019f8616509510113fc3b0e68d0e450530b0e653c25c19`；缓存审计错误 0 |
| VideoITG Qwen smoke | 1/1；缓存/evidence 源帧完全一致；32 submitted/represented；11,664 Token；二次采样关闭；违规 0 |
| 轻量 Qwen pilot50 | 三卡 17/17/16；50/50 prediction/evidence；推理错误 0；视觉协议违规 0 |
| 缓存-Qwen 对齐 | 50/50 evidence 源帧与缓存逐项完全一致；三分片 run_config 审计全部通过 |
| 当前 QA 结论 | Pilot50 候选相对 Raw：Strict 44% -> 52%，Relaxed 61% -> 66%；候选 10胜/35平/5负；均值 +0.05；10,000 次 Bootstrap CI `[-0.04,+0.14]`，方向正但区间跨 0 |
| 安全凭据入口 | 旧评判脚本备份中的合法 key 仅通过 AST 临时注入进程；不打印、不复制、不归档凭据 |

### 8.20 轻量时间选择器 Pilot50 裁判与 Confirm-300C 冻结

| 字段 | 内容 |
|---|---|
| 实验 ID | `lightweight_temporal_qwen_nested_pilot50_v1` |
| 数据 | Pilot50；Type 1-5 各 10 |
| Raw Answer 1/0.5/0 | 22 / 17 / 11；Strict 44%；Relaxed 61% |
| 候选 Answer 1/0.5/0 | 26 / 14 / 10；Strict 52%；Relaxed 66% |
| 配对 | 候选 10 胜、35 平、5 负；平均 `+0.05` |
| Bootstrap | 10,000 次；seed 42；候选减 Raw 95% CI `[-0.04,+0.14]` |
| 裁判 | 历史 Answer-only DeepSeek；100/100 可解析；实际模型 `deepseek-v4-flash` |
| Prompt/解析 SHA | `898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19` / `fe42aa06105c2559ca32cf6073dd738478466888e6f480edcf6a2350398c9716` |
| 结论 | 满足小样本均值为正门禁；CI 跨 0，不宣称稳定增益；冻结配置进入 Confirm-300C |

| Confirm-300C 字段 | 内容 |
|---|---|
| 问题/GT/Manifest | `data/confirm300c_temporal_disjoint_prior_{question,groundtruth,manifest}.json` |
| 规模 | 300；Type 1-5 各 60；300 个唯一问题与视频 |
| 排除 | Pilot50 + Confirm-300A + Confirm-300B，共 650 个问题/视频 |
| 重合审计 | 对三个既有集合分别为问题 0、视频 0 |
| 问题 SHA256 | `a4664683ddeea2b5140cb1a5b1c46aaccad7a3b060156a497dfdd0c50cd20f48` |
| Ground Truth SHA256 | `465fa6d9efc9dc2a9f6e528ac3e0ccf9ce8cc206deaba2b5e067c8ac9a870276` |
| Manifest SHA256 | `92038e84ad42431d7b81c5bd12f1462d3f84d977d8fdcc19309573b32f4dd694` |
| 冻结规则 | C 上禁止调参；先跑 Raw/冻结候选，方向不正即停止，方向正且统计合理才接空间模块 |

长期任务恢复：额度耗尽后等待重置并从本台账续跑；若 `ssh adsqa` 断开，打开本机 EasyConnect 并点击已预填凭据的“登录”，VPN 恢复后按 JSONL 缓存和逐题结果断点继续。

新增代码索引：

```text
evaluation/methods/temporal_evidence/temporal_cache.py
evaluation/methods/temporal_evidence/build_videoitg_cache_v1.py
evaluation/methods/temporal_evidence/lightweight_selector.py
evaluation/methods/temporal_evidence/build_lightweight_temporal_cache_v1.py
evaluation/methods/fair_protocol/inference_fair_baselines_v1.py
```

### 8.21 Confirm-300C 运行前工程审计

| 字段 | 内容 |
|---|---|
| 数据状态 | 已冻结 300 条；五类各 60；与此前 650 个问题/视频零重合 |
| 缓存方式 | 3 个低优先级 CPU 分片，完成后按问题顺序合并；算法参数不变 |
| 并行一致性 | 与单进程共同样本逐字段完全一致 |
| 自动测试 | 时间缓存/选择器/审计/指标/裁判解析共 18/18 通过 |
| GPU 保护 | GPU1 始终保留；GPU0 不使用；GPU2/3/5 仅在确认无他人进程时使用；2026-07-12 经用户明确授权后新增 GPU4。三卡编排仍只绑定 2/3/5，GPU4 通过单 worker 顺序运行分片。 |
| 缓存审计 | 已完成 300/300：缺失/额外/错误均 0；源视频一致 300/300；32 个唯一帧；全部时序有序；8-bin 300/300。合并缓存 SHA256 `aa895d4e49f57ca4bc4cbba3e8b01bd72abf21f2f47d3235b96065ca41b75c4c`。 |
| Qwen 审计 | Raw 已完成 300/300 且 `all_valid=true`：缺失、重复、解析错误、协议违规均 0；32 submitted/represented、11,664 Token、无二次采样均为 300/300。候选完成后还需同口径审计及缓存-evidence 精确对齐。 |
| 裁判门禁 | 视觉协议 `all_valid` 且索引对齐 `valid` 后才允许 DeepSeek |
| 当前状态 | Raw Uniform 已完成 300/300 且完整视觉协议审计通过。冻结 `lightweight_nested` shard0/3 与 shard1/3 共完成 200/200：错误/协议违规 0，缓存-evidence 精确对齐 200/200；shard2/3 已在 GPU4 接续。后处理 watcher PID `2927012` 仅在候选全部完成且视觉/索引总审计通过后调用 DeepSeek。当前不填写 Confirm-300C QA 指标。 |

VideoITG Pilot50 的完整缓存、三卡 Qwen、缓存审计、索引对齐和同口径 DeepSeek 脚本也已准备，但保持外部强基线身份；当前优先完成 Confirm-300C 主对照，不让其结果参与冻结配置调整。

### 8.22 Confirm-300C 冻结时间选择器独立确认结果

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_temporal_confirm300c_20260712_v1` |
| 数据 | Confirm-300C；300 条；Type1-5 各 60；与此前 650 个问题/视频零重合 |
| 模型与协议 | Qwen3-VL-8B；Raw/候选各 300/300；32 submitted/represented；11,664 Token；关闭二次采样；无 RAG/反思 |
| 时间缓存 | `ads_temporal_mmr_v1`；64 候选到 32；SHA256 `aa895d4e49f57ca4bc4cbba3e8b01bd72abf21f2f47d3235b96065ca41b75c4c` |
| 视觉/索引审计 | 联合视觉审计 `all_valid=true`；候选缓存-evidence 精确对齐 300/300；缺失、重复、错误、违规均 0 |
| 裁判 | 历史 Answer-only DeepSeek；600/600 可解析；实际响应模型 `deepseek-v4-flash` |
| Raw Answer 1/0.5/0 | 162 / 90 / 48 |
| 候选 Answer 1/0.5/0 | 165 / 89 / 46 |
| Raw Strict/Relaxed | 54.00% / 69.00% |
| 候选 Strict/Relaxed | 55.00% / 69.83% |
| 配对 | 候选 44 胜、215 平、41 负；候选减 Raw `+0.00833` |
| Bootstrap | 10,000 次，seed 42；候选减 Raw 95% CI `[-0.02667,+0.04333]` |
| 类型归因 | Type1 `0`；Type2 `-0.04167`；Type3 `+0.04167`；Type4 `+0.03333`；Type5 `+0.00833` |
| 分数转移 | `0→1` 6、`1→0` 4、`0.5→1` 26、`1→0.5` 25、`0→0.5` 12、`0.5→0` 12 |
| Prompt 门禁修复 | 后处理预期 SHA 常量漏写一个 `e`，首次在 API 前停止；核对源码与 9 份历史/当前 run_config 后修正常量，重新审计通过，推理结果未重跑或修改 |
| 结果哈希 | summary `4522eb6747d32e1c946e4692c5b438cfcd56b2d4b0390cb5ed611794d4938507`；results `6611648258d03dd7636017a6023bb81760154e230be009d0fcd8a5251203570c`；provenance `e6c5a7aefb6c68008253fa767cbca8b446d9ce0d267ac6a7674230181ebdac85` |
| 当前结论 | 独立集方向微正但 CI 跨 0，类型与边界不稳定；不宣称稳定增益，暂不接空间模块，先完成 VideoITG 强基线 |

### 8.23 VideoITG 官方强基线 Pilot50

| 字段 | 内容 |
|---|---|
| 方法 | VideoITG-8B；官方源码 revision `50a60a8`；离线 64 候选到 32 帧 |
| 缓存 | 50/50；错误 0；SHA256 `5ccb6ee5e3f862ce15424188901007f15265928bd433c14ba69eeaf069e58406` |
| 缓存审计 | 源视频一致 50/50；时序有序；每题 32 个唯一帧；31/50 覆盖全部 8 bins，平均 7.5 bins，平均最大候选空洞 10.54 |
| 覆盖门禁修正 | 官方相关性定位允许集中时间段；8-bin 从硬门禁改为报告指标，不修改 VideoITG 帧索引 |
| Qwen 协议 | 50/50；17/17/16 三片；错误 0；32 submitted/represented；11,664 Token；关闭二次采样 |
| 视觉/索引审计 | `all_valid=true`；缓存-evidence 精确对齐 50/50 |
| 裁判 | 历史 Answer-only DeepSeek；100/100 可解析；实际响应模型 `deepseek-v4-flash` |
| Raw Strict/Relaxed | 44% / 61% |
| VideoITG Strict/Relaxed | 44% / 60% |
| 配对 | VideoITG 5 胜、39 平、6 负；VideoITG 减 Raw `-0.01` |
| Bootstrap | 10,000 次；VideoITG 减 Raw 95% CI `[-0.08,+0.05]` |
| 结果哈希 | summary `462fc7aceb3f99ad535bef67295842bcbd24de5da2c10b96c044ac5dcde5861f`；results `dc1adcdb50550680ff6d3f3db788580f8dd9d45d73be0fbe48a1ba50c71b63e5`；provenance `ae2929f4545a2c527b5b7df78434f80f4c25e2123f6e644b8387553b7d3e8fa7` |
| 结论 | 官方强基线未超过 Raw；不扩大到 Confirm-C。结合轻量版结果，只进行一次覆盖约束的保守时间选择修正。 |

### 8.24 保守覆盖修正 Pilot50

| 字段 | 内容 |
|---|---|
| 策略 | `conservative_raw24_evidence8_v1`；每个 8-bin 保留 3 个 Raw 锚点并加入 1 个非 Raw 高价值帧 |
| 冻结分量 | 问题 0.55、ASR 0.20、场景变化 0.15、覆盖 0.10、重复惩罚 0.20；不扫描权重 |
| 单测/smoke | 选择器 5/5；真实 smoke 1/1，替换 8、每箱 4、32 唯一帧、错误 0 |
| Pilot50 缓存 | 50/50；错误 0；8-bin 50/50；平均最大候选空洞 4.74；平均替换 8；源视频一致 50/50 |
| 缓存 SHA256 | `790a64f7c191c2ec98cbed14c13100ad63e93c87517907af499710f323d35689` |
| 人工证据结果 | Raw Recall/Precision/Gap `30/30, 47.42%, 3.28%`；原轻量版 `30/30, 53.26%, 12.51%`；24+8 `29/30, 48.10%, 7.17%` |
| 当前状态 | 开发集 Evidence Recall 降为 29/30，未通过证据门禁；已停止本实验等待器，不运行 Qwen/DeepSeek，不派生第二组比例或权重 |

### 8.25 时间证据路线停止结论

| 方法 | 数据 | 配对结果 | 结论 |
|---|---|---|---|
| `ads_temporal_mmr_v1` | Pilot50 | 10胜/35平/5负，`+0.05`，CI `[-0.04,+0.14]` | 小样本门禁通过 |
| `ads_temporal_mmr_v1` | Confirm-300C | 44胜/215平/41负，`+0.00833`，CI `[-0.02667,+0.04333]` | 独立集微正但不稳定；Type2 退化 |
| VideoITG-8B | Pilot50 | 5胜/39平/6负，`-0.01`，CI `[-0.08,+0.05]` | 官方强基线无增益 |
| `conservative_raw24_evidence8_v1` | Pilot50 人工证据 | Recall `29/30`，Precision `48.10%`，Gap `7.17%` | 唯一原理修正未通过证据门禁，停止 QA |

最终决策：不接回空间模块、不运行统一时空 QA、不运行 balanced-3000。原因不是工程未完成，而是预注册门禁不允许用不稳定时间收益继续叠加模块。当前最优 QA 仍为 Raw Uniform；最佳时间证据精度分支为原轻量版，最佳空间证据分支为 16+16 + 查询条件化 OCR。论文按完整负结果与定位/问答非单调性收束。

### 8.26 时间选择器组件消融

人工完成子集为 23 问题、30 个视觉证据单元；所有消融均使用同一 64 候选、32 帧预算和 CLIP，只关闭单一分量。

| 版本 | Evidence Recall | 帧精度 | 平均 bins | 最大归一化空洞 | 解释 |
|---|---:|---:|---:|---:|---|
| Full | 30/30 | 53.26% | 7.96 | 12.51% | 完整自研选择器 |
| 去问题 | 29/30 | 48.10% | 8.00 | 8.50% | 问题相关性是核心召回来源 |
| 去 ASR | 29/30 | 52.72% | 8.00 | 11.78% | ASR 对一个证据单元不可替代 |
| 去场景变化 | 30/30 | 53.80% | 8.00 | 12.05% | 当前数据上贡献很小，不宣称正增益 |
| 去覆盖 | 30/30 | 54.35% | 7.48 | 16.02% | 精度略升但覆盖显著恶化，证明折中作用 |
| 去重复惩罚 | 30/30 | 53.53% | 7.96 | 12.34% | 当前数据上贡献很小 |

消融报告 SHA256：`012f8cc33f84f2f72861d96a479ec5af43a8f462a0d45b62af9145acd076f1f7`。不把小幅数值变化包装为所有组件均有效；论文只把问题/ASR和覆盖约束作为有实证支持的核心项，场景变化与重复抑制按辅助设计或负消融报告。

### 8.27 创新点二反事实充分性 Dev100 Pilot（运行中）

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation2_counterfactual_dev100_v1` |
| 目的 | 验证反事实充分性和一次 24+8 预算内补全能否独立改善答案，并拆分 Raw、Raw+2、MMR32、MMR32+2 四组贡献 |
| 开发数据 | `data/counterfactual_dev100_v1/`；训练集 100 个唯一视频各 1 题；与 Pilot50、Confirm-A/B/C、testset 的问题/视频重合均为 0 |
| 类别 | visual_detail 44、narrative_other 19、brand 16、price_promo 11、OCR 4、CTA 4、speech_audio 2 |
| 冻结创新点一 | `ads_temporal_mmr_v1`；开发缓存 100/100，64→32，SHA256 `2a738a033cdb2560b6f46d3224395d9657d028cc310bbdb18cf124ec485b446e` |
| 反事实 | 视觉题马赛克化相关性最高 4 个视图且保持 32 槽位；语音题撤去 ASR；均保存 E+/E- 轨迹 |
| 充分性分数 | 冻结 Qwen 的候选答案平均条件对数似然；弃用会饱和的 Yes/No Prompt 自评 |
| 纠错动作 | 低充分性时固定 `24 context + 8 local rescue = 32`，并按救援证据下的条件对数似然保守重排序 |
| 模型与协议 | Qwen3-VL-8B；每次前向 32 submitted/represented views、11,664 Token、二次采样关闭、无 RAG/自由反思；额外反事实前向计入时延 |
| 单测/smoke | 纯算子 5/5；Raw 和 MMR32 各 1 条 Qwen smoke 成功，视觉协议违规 0 |
| 结果路径 | `evaluation/runs/innovation2_counterfactual_dev100_v1/` |
| 当前状态 | Raw 与 Raw+2 的 100 条三分片推理运行中；尚无 QA 结论，禁止与 Confirm 结果混用 |

### 8.28 创新点二反事实充分性 Dev100 Pilot（已停止）

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation2_counterfactual_dev100_v1` |
| 数据 | 训练开发集 100 条、100 个唯一视频；与 Pilot50、Confirm-A/B/C、testset 问题/视频重合均为 0 |
| 模型/协议 | Qwen3-VL-8B；四组各 100/100；每次前向 32 submitted/represented views、11,664 Token、无 RAG/自由反思、二次采样关闭 |
| 四组 | Raw、Raw+反事实充分性、冻结 MMR32、MMR32+反事实充分性 |
| 视觉/缓存审计 | Raw 与 MMR 各 100/100 完整；MMR 初答与冻结缓存精确对齐 100/100；所有协议违规为 0 |
| 裁判 | 历史 Answer-only DeepSeek，400/400 可解析，实际模型 `deepseek-v4-flash`，10,000 次 paired bootstrap |
| Raw Strict/Relaxed | 42.0% / **58.0%** |
| Raw+二 Strict/Relaxed | 40.0% / 55.0%；相对 Raw `-0.03`，2 胜/90 平/8 负，95% CI `[-0.06, 0]` |
| MMR32 Strict/Relaxed | 40.0% / 55.5%；相对 Raw `-0.025` |
| MMR32+二 Strict/Relaxed | 39.0% / 54.0%；相对 MMR `-0.015`，6 胜/86 平/8 负，95% CI `[-0.065,+0.03]` |
| 机制 | Raw 97/100、MMR 98/100 的 `s(E+) > s(E-)`；触发/重排序为 14/14 和 40/40；方向性存在但不能预测纠错收益 |
| 真实边界 | MMR+二有 1 条 `0→1`（`traincf_355`），同时 2 条 `1→0`（`traincf_45`、`traincf_434`） |
| 结果哈希 | summary `317876e8305e2ce022a7ac27ad31f439fb068f43012ad683396dcf1f9106117a`；results `6c27c24a2a33c03da0ff59f02a67b3fa86a587da6d22c3f3607345f429851533`；analysis `12bf3108cc887141c2cea91bc3b4b8b6ba823d72a536baba178d29c898d21508` |
| 当前结论 | 未达到开发门槛；停止调参与扩量，不进入 Confirm-300C 或 balanced-3000；保留为反事实敏感性与纠错收益脱节的负结果 |

### 8.29 反事实监督声明—证据验证器第一阶段（代码完成，真实实验未运行）

| 字段 | 内容 |
|---|---|
| 实验 ID | `claim_evidence_stage1_v1` |
| 当前目的 | 冻结初答和固定 24+8 补看候选，只学习“保留/切换”选择器 |
| 训练数据计划 | AdsQA Train500；Raw 与 MMR32 候选可共同训练；按视频分组划分内部训练/校准 |
| 新评测集计划 | `Dev300` 与 `Confirm-D300` 在任何调参前联合预注册；各 Type1-5 每类 60；与 Pilot50、Confirm-A/B/C 及彼此问题/视频零重合 |
| 回答器 | 冻结 Qwen3-VL-8B；32 个 submitted/represented views；11,664 视觉 Token；关闭二次采样 |
| 候选 | Raw/MMR32 初答与固定 24 context + 8 local rescue；每题强制生成候选对，但旧条件似然选择仍作为对照 |
| 选择器 | 256 维声明交互哈希 + 44 维运行时/文本统计，单隐层 64 维 NumPy MLP；冻结 Qwen，不做 SFT/GRPO |
| 防泄漏 | 标准答案和 DeepSeek 分数只作为监督标签；特征构建不读取 `supervision`，已有专门单测 |
| Dev 阈值 | 只在 Raw Dev300 选择；switch precision 至少 70%；同一阈值用于 MMR32 与 Confirm-D |
| 门禁 | Relaxed 正向且 Bootstrap 下界非负、Strict 不降、恢复至少一半 oracle 增益、敏感类别无广泛退化、严重 `1→0` 受控 |
| Confirm-D | Dev 门禁通过后只运行一次冻结配置；脚本会检查 Dev gate 和完成标记 |
| GPU 约束 | 仅真正空闲的 GPU2/3/4；同时检查显存和 compute PID；保留 GPU1，不使用 GPU0/5 |
| 本地代码 | `remote_worktree/evaluation/methods/claim_evidence_verifier/` 及 `remote_worktree/evaluation/scripts/run_claim_evidence_*_v1.sh` |
| 已验证 | 新代码单测 7/7；旧时间选择器 10/10；合成端到端训练/推理 smoke 通过 |
| 尚未完成 | Dev100 全量远端冻结、代码同步、真实 split 构建、Train500 候选/裁判/训练、Dev300 与 Confirm-D300 |
| 当前结果 | **无新准确率结果**；不得把合成 smoke 或旧 Dev100 分数当作新方法成绩 |
| 当前状态 | 本地实现完成；`ssh adsqa` 超时，等待 EasyConnect 系统权限确认后继续 |

### 8.30 Candidate64 视频预处理与证据缓存

| 字段 | 内容 |
|---|---|
| 资产 ID | `video_index_v1` / `candidate_cache_pilot50_v1` / `candidate_cache_full_v1` |
| 全量索引 | 1707/1707；严格审计通过；ASR 1398/1707（81.90%） |
| 候选协议 | Candidate64；Raw32 为严格嵌套子集；精确帧号/时间戳；禁止下游二次采样 |
| 时间元数据 | 场景变化分数；atomic、8 秒和 20 秒分段 |
| 修复视频 | `611e166ba44c2a31cbf29f62b5986dcc.mp4` 使用独立 `data/video_repair_cache_v1/` 完整副本，未覆盖原文件 |
| Pilot50 CLIP | 50/50；每视频 `64x768`；L2 归一化；审计失败 0 |
| Pilot50 OCR | 50/50；1984 个含文字帧；7643 个检测框；阈值 0.35；审计失败 0 |
| Pilot50 路径 | 远端 `data/candidate_cache_pilot50_v1/`；大小 6.5 MB |
| 全量路径 | 远端 `data/candidate_cache_full_v1/` |
| 运行资源 | CLIP 为 3 个互斥分片进程共享同一 GPU3（约 1.7 倍于单进程）；OCR CPU 8 workers x 2 threads；GPU1保留；不使用其他 GPU |
| 代码 | `preprocess/build_video_index_v1.py`、`build_candidate_clip_cache_v1.py`、`build_candidate_ocr_cache_v1.py`、`audit_candidate_cache_v1.py` |
| 启动脚本 | `evaluation/scripts/run_candidate_preprocess_full_v1.sh`；原子写入、确定性分片、默认断点续跑 |
| 当前状态 | 全量 CLIP/OCR 1707/1707、Raw32 嵌套 1707/1707，联合审计通过；该资产仅是冻结预处理底座，无方法准确率结论 |

### 8.31 分段 ASR 预处理

| 字段 | 内容 |
|---|---|
| 资产 ID | `segmented_asr_pilot_train_confirm_v1` |
| 范围 | Pilot50、Train、Confirm-A/B/C；1050 个唯一视频；索引缺失 0 |
| 模型 | ModelScope `Whisper-large-v3-turbo`；SHA256 `aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a` |
| 环境 | `<REMOTE_HOME>/venvs/adsqa_asr_v1/`；`openai-whisper==20250625` |
| 输出 | 句段和词级时间戳、文本、语言、置信统计；`success/no_audio/no_speech/transcription_failed` 四类状态 |
| 质量门控 | 拒绝低置信度短幻觉；保留原候选、质量统计和拒绝原因，不以空字符串代替状态 |
| Smoke | 1/1 审计通过；纯音乐低置信度 `I` 被正确转为 `no_speech` |
| 代码 | `preprocess/build_segmented_asr_cache_v1.py`、`audit_segmented_asr_cache_v1.py` |
| 自动串联 | `watch_candidate_audit_then_asr_v1.sh`；缓存审计必须 1707/1707 且 Raw32 嵌套 1707/1707；已有 ASR 运行时防重复 |
| GPU | 仅 GPU3；因 OCR 使用 CPU，按用户决定提前并行启动 |
| 当前状态 | 1050/1050 完成并通过审计；success/no_speech/no_audio 为 1040/9/1，失败 0；Whisper 词时间戳允许跨分段边界最多 1.0 秒，仍严格检查视频边界与排序 |

### 8.32 创新点一第一阶段自动编排与 Confirm-D300 冻结

| 字段 | 内容 |
|---|---|
| 编排 ID | `innovation1_stage1_orchestrator_v1` |
| 编排脚本 | `evaluation/scripts/watch_and_run_innovation1_stage1_v1.sh` |
| 状态路径 | `evaluation/runs/innovation1_stage1_orchestrator_v1/state.json` |
| GPU 规则 | 所有 CUDA 步骤仅 GPU3；发现 compute PID 时等待；不使用其他 GPU |
| Confirm-D | 300 题、300 个唯一视频、Type1-5 各 60；与 Pilot50、Confirm-A/B/C 问题和视频零重合 |
| Confirm-D 路径 | `data/innovation1_confirmd300_v1/` |
| Confirm-D question SHA256 | `896cfa8029cba0f6c79fb3b6a8bc52772b5add37ea1f446df23db9f2b233c543` |
| 自动实验 | Confirm-D 分段 ASR完成后，运行 Pilot23 grouped 5-fold 校准和 Raw32/Rel32/Rel-U32/Penalty-U32 固定预算证据对比 |
| 人工门禁 | 至少 100 题独立证据复核前不运行 Qwen；自动流程停在 `WAITING_HUMAN_EVIDENCE_100` |
| 当前状态 | 自动阶段已完成并停在 `WAITING_HUMAN_EVIDENCE_100`；Confirm-D ASR 300/300 审计通过；Pilot23 G2/G3 均未通过，未运行 Qwen |

### 8.33 创新点一 Pilot23 可靠性校准与定额选帧首轮结果

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation1_reliability_pilot23_cv_v1` |
| 数据 | 23 题已有人工证据标注、30 个视觉证据单元、1472 个 Candidate64 帧；按问题 grouped 5-fold OOF |
| 特征 | 视觉 CLIP、分段 ASR 相似度/置信度/偏移方差、OCR 相似度/置信度/跨帧稳定性、视觉邻域差异、场景变化 |
| F0 仅视觉 | AUROC 0.63024；AUPRC 0.62025；Brier 0.23904；ECE 0.06945 |
| F4 完整未校准 | AUROC 0.60204；AUPRC 0.58260；Brier 0.25353；ECE 0.11537 |
| F5 完整校准 | AUROC 0.58544；AUPRC 0.57259；Brier 0.25508；ECE 0.11562 |
| Raw32 | Evidence Recall 30/30；Evidence Precision 47.42%；平均最大归一化空洞 0.04762 |
| Rel32 | Evidence Recall 29/30；Evidence Precision 52.04%；平均最大归一化空洞 0.12146 |
| Rel-U32 | Evidence Recall 29/30；Evidence Precision 51.77%；平均最大归一化空洞 0.12422 |
| 门禁 | G2 校准失败；G3 证据门禁失败；未运行 Qwen |
| 主要问题 | ASR/OCR 特征在 23 题小样本上降低判别与校准；MMR 填充虽覆盖 8 个粗粒度时间 bin，仍形成较大局部空洞并漏掉 1 个稀疏证据单元 |
| 结果路径 | `evaluation/runs/innovation1_reliability_pilot23_cv_v1/` |
| summary SHA256 | `8d4c62065b93bf4af5276ee8e7560b055bbdb20afafe7633ed6f466240cfc8da` |
| 当前结论 | 定位精度存在正向信号，但可靠性校准和证据保底未成立；先扩充证据标注并修改方法，不进入 QA 精度实验 |

### 8.34 Evidence-300 扩展开发集

| 字段 | 内容 |
|---|---|
| 数据 ID | `innovation1_evidence300_v1` |
| 规模 | 300 题、209 个唯一视频；Type1-5 各 60 |
| 分组 | train/calibration/development 为 200/50/50；按视频确定分组，跨分组视频重合 0 |
| 隔离 | 与 Pilot50、Confirm-A/B/C、Confirm-D 的问题及视频重合均为 0 |
| 数据路径 | `data/innovation1_evidence300_v1/` |
| question SHA256 | `d4b1a693c7ce52eded712f6fe78a5d6f631a1ec60828655b6896a2f754773825` |
| 标注口径 | 参考答案条件化模型只生成候选时间段，状态固定为 `pending_review`；未经复核不得作为正式评测真值 |
| ASR | 209 个视频仅 GPU3补充同口径 Whisper large-v3-turbo；完成后自动审计 |
| 自动串联 | `watch_evidence300_asr_then_proposals_v1.sh` 在 ASR 审计通过后生成弱候选与复核包 |
| 当前状态 | ASR 209/209 和弱候选 300/300 已完成；复核材料含 209 张联系表、819 张候选原图，失败 0；Codex 已复核 300/300，67 题进入二审，剩余0题；正式 G2/G3 尚未启动。前200条 exploratory pilot 已完成缓存并在 GPU4 运行 Qwen 推理，当前仅作开发性验证 |

### 8.35 Evidence-300 Codex 图片证据复核 Batch009

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch009_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 41–45 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 依据联系表、候选帧、参考答案、ASR 和 OCR 重新确定证据区间；其中 OnePlus 题替换了偏后的自动候选时间点 |
| 合并结果 | `ai_reviews_merged.json` 共 45 条唯一记录；`second_review_queue.json` 共 14 条 |
| 进度文件 | `review_progress.json`：reviewed 45、remaining 255、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch009.json`、`second_review_queue.pre_batch009.json`、`review_progress.pre_batch009.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.48 Evidence-300 Codex 图片证据复核 Batch022

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch022_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 106–110 条；新增唯一题目 5 |
| 复核结果 | 1 条 `AI_REVIEWED`，4 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Moxies 厨师/新鲜食材/细节风味、Vistaprint 个性化庆祝物品、镜子与人物内心叙事、母亲支持女儿训练；目标受众和镜子/情绪/亲子支持语义进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 110 条唯一记录；`second_review_queue.json` 共 38 条 |
| 进度文件 | `review_progress.json`：reviewed 110、remaining 190、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch022.json`、`second_review_queue.pre_batch022.json`、`review_progress.pre_batch022.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`48a2ca13ed0f26b2e923f3a45b7547bd7171c5e9560e19193739596b3a46971e` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.49 Evidence-300 Codex 图片证据复核 Batch023

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch023_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 111–115 条；新增唯一题目 5 |
| 复核结果 | 2 条 `AI_REVIEWED`，3 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Alexa 广告的家庭支持、坚持训练和日常语音控制；Standard Bank 的年轻人/创业雄心受众；Betis 广告通过胜利回忆、球迷支持和“我们的家”制造归属感；Untuckit 通过孤独、幽默和 Zoom 社交场景建立共鸣 |
| 合并结果 | `ai_reviews_merged.json` 共 115 条唯一记录；`second_review_queue.json` 共 41 条 |
| 进度文件 | `review_progress.json`：reviewed 115、remaining 185、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch023.json`、`second_review_queue.pre_batch023.json`、`review_progress.pre_batch023.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`820f95aabee75b139fed7b771c0eff0dea375f341f62e3069b6aae9ff6dd9018` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.50 Evidence-300 Codex 图片证据复核 Batch024

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch024_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 116–120 条；新增唯一题目 5 |
| 复核结果 | 3 条 `AI_REVIEWED`，2 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Uswitch 的一键切换承诺；Tennessee Playcation 的 Grand Ole Opry 文化体验；800PIZZA 的 Nonna 明示背书与真实性情绪；D&G 的奢华时尚受众推断 |
| 合并结果 | `ai_reviews_merged.json` 共 120 条唯一记录；`second_review_queue.json` 共 43 条 |
| 进度文件 | `review_progress.json`：reviewed 120、remaining 180、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch024.json`、`second_review_queue.pre_batch024.json`、`review_progress.pre_batch024.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`9406af0cb53d970d024d8da2fd2a09ef8d4d6ff1f040317df6e3bbf47de8a2d9` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.51 Evidence-300 Codex 图片证据复核 Batch025

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch025_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 121–125 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Kingfisher 通过视频社交、舞蹈、欢快音乐和“good times”营造正向情绪；COVID-19 PSA 明确论证留家可避免医院超负荷并争取疫苗时间；Farmdrop 舞蹈表达食物愉悦；刺猬广告的救助动作与象征寓意分开处理 |
| 合并结果 | `ai_reviews_merged.json` 共 125 条唯一记录；`second_review_queue.json` 共 44 条 |
| 进度文件 | `review_progress.json`：reviewed 125、remaining 175、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch025.json`、`second_review_queue.pre_batch025.json`、`review_progress.pre_batch025.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`255cfadf2c7cd2dc1bfd9971e4ae9067bfdaddb5dbe8e92edb1692201041cae2` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.52 Evidence-300 Codex 图片证据复核 Batch026

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch026_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 126–130 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Tata 影片片尾安全与国家共同体主题；Snickers 通过饥饿导致失常和食用后恢复的幽默连接；Mastermind Toys 用儿童户外玩耍、情绪感染和 `Let's play` 行动号召回答同视频的三类问题 |
| 合并结果 | `ai_reviews_merged.json` 共 130 条唯一记录；`second_review_queue.json` 共 44 条 |
| 进度文件 | `review_progress.json`：reviewed 130、remaining 170、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch026.json`、`second_review_queue.pre_batch026.json`、`review_progress.pre_batch026.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`9974dd22ad7020563acd69aaeed6a9fa085a516f1a545b82ef79bd97c837b06a` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.53 Evidence-300 Codex 图片证据复核 Batch027

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch027_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 131–135 条；新增唯一题目 5 |
| 复核结果 | 0 条 `AI_REVIEWED`，5 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Rugby 青少年励志叙事、Toyota Venza 与报纸/天气页面的证据不足、`ANYONE CAN DO YOGA` 的包容性角色特征、赌场魔术小物体效果、Gonzo 的受众推断；本批均存在参考答案为空或模态证据不足问题 |
| 合并结果 | `ai_reviews_merged.json` 共 135 条唯一记录；`second_review_queue.json` 共 49 条 |
| 进度文件 | `review_progress.json`：reviewed 135、remaining 165、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch027.json`、`second_review_queue.pre_batch027.json`、`review_progress.pre_batch027.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`b5ee36f0de1bc065d878d9228d6780bcbb6799a2fc1fab3c41f92fc49307cabc` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.54 Evidence-300 Codex 图片证据复核 Batch028

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch028_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 136–140 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | BetterMe 的舞蹈、自我表达和自信；Levi’s Fresh 的自然染料/可持续机制因联系表与 ASR 不足进入二审；Google Play Points 的印尼移动游戏受众；Adidas Veste as Brabas 的女性自由、代表性和拉丁女性角色 |
| 合并结果 | `ai_reviews_merged.json` 共 140 条唯一记录；`second_review_queue.json` 共 50 条 |
| 进度文件 | `review_progress.json`：reviewed 140、remaining 160、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch028.json`、`second_review_queue.pre_batch028.json`、`review_progress.pre_batch028.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`3407e752a70e1afd662b5555f1cad9d7183d28ac6d58243c33aca8ed0c170aa4` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.55 Evidence-300 Codex 图片证据复核 Batch029

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch029_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 141–145 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Adidas 的包容/代表性；FitVine 的幽默情绪和共享餐桌；Earth Hour 的全球协作与关灯行动；Bobo’s 通过妈妈烘焙、简单原料和家庭场景连接目标受众 |
| 合并结果 | `ai_reviews_merged.json` 共 145 条唯一记录；`second_review_queue.json` 共 50 条 |
| 进度文件 | `review_progress.json`：reviewed 145、remaining 155、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch029.json`、`second_review_queue.pre_batch029.json`、`review_progress.pre_batch029.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`779eebf8c61cb1b1999e1437e9a1c3e6d581fa0003bb8cf9f2659e6715c33ddf` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.56 Evidence-300 Codex 图片证据复核 Batch030

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch030_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 146–150 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Samsung 用科技、行动和 `DON'T FEAR FEAR ANYMORE` 表达克服限制；Money Heist 用红色面罩/制服和任务叙事连接受众；Fiverr 对照 AI 与人的创造/灵感；Skippy 用 90 年、共享食物和 `Spreading Fun` 表达持续存在与情绪连接 |
| 合并结果 | `ai_reviews_merged.json` 共 150 条唯一记录；`second_review_queue.json` 共 50 条 |
| 进度文件 | `review_progress.json`：reviewed 150、remaining 150、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch030.json`、`second_review_queue.pre_batch030.json`、`review_progress.pre_batch030.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`45841816879380736a668bdb5dbf8fa3807e2af81097efaef32f8650bd37beab` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.57 Evidence-300 Codex 图片证据复核 Batch031

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch031_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 151–155 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Supercell 通过谜题难度与奖励鼓励不同技能水平玩家；Melamii 面向工作/生活并关注色斑问题的女性；Spider-Man 将玩家与角色通过 PlayStation 游戏叙事连接；Children’s Wisconsin 用拟人化担忧和儿童/家庭/医护角色降低就医焦虑 |
| 合并结果 | `ai_reviews_merged.json` 共 155 条唯一记录；`second_review_queue.json` 共 50 条 |
| 进度文件 | `review_progress.json`：reviewed 155、remaining 145、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch031.json`、`second_review_queue.pre_batch031.json`、`review_progress.pre_batch031.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`589de2d162c917da8171087444a88119ba24265a860fdf419738e54761321b3d` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.58 Evidence-300 Codex 图片证据复核 Batch032

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch032_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 156–160 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Hyundai IONIQ 的蓝色球体、共同前进和掌控叙事；Bergen 的 Jack/朋友对照与山泉过滤；Mimowie 的无承诺灵活租车；Corona 的海滩清凉感进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 160 条唯一记录；`second_review_queue.json` 共 51 条 |
| 进度文件 | `review_progress.json`：reviewed 160、remaining 140、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch032.json`、`second_review_queue.pre_batch032.json`、`review_progress.pre_batch032.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`b25fc2b1c8730bc9e4284f656b3ac9912ba625ad69cfb7bdb05ccd4e9771fe1a` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.59 Evidence-300 Codex 图片证据复核 Batch033

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch033_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 161–165 条；新增唯一题目 5 |
| 复核结果 | 3 条 `AI_REVIEWED`，2 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Basecamp 的户外冒险感官刺激；Toyota Vios 城市灵活受众推断；#NoForcedLabor 的震撼/同理/道德对抗；Samsung Nightography 的夜潜相机能力与探索型受众 |
| 合并结果 | `ai_reviews_merged.json` 共 165 条唯一记录；`second_review_queue.json` 共 53 条 |
| 进度文件 | `review_progress.json`：reviewed 165、remaining 135、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch033.json`、`second_review_queue.pre_batch033.json`、`review_progress.pre_batch033.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`5c213ca55dd5496f537304d54763c02c5a0618327f77d3f574b0a07f0b5e0c9e` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.60 Evidence-300 Codex 图片证据复核 Batch034

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch034_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 166–170 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Nosotras 通过校园月经焦虑到同伴/教育支持；Kia 以 Michelle Wie 的挑战精神、年轻活力和高尔夫表现打破旧式俱乐部；WPEngine “网站是新的前门”隐喻；Chelsea/Three 的合作与 `#SupportSomeoneElse` 话题功能 |
| 合并结果 | `ai_reviews_merged.json` 共 170 条唯一记录；`second_review_queue.json` 共 53 条 |
| 进度文件 | `review_progress.json`：reviewed 170、remaining 130、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch034.json`、`second_review_queue.pre_batch034.json`、`review_progress.pre_batch034.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`8dd1d712a8784c31b2682cebfbb78d21a6107d820ed37fd2121d284d10e0c378` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.61 Evidence-300 Codex 图片证据复核 Batch035

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch035_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 171–175 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Chelsea/Three 通过孤独案例与电话/WhatsApp行动建立同理；阿根廷投票仪式连接四十年民主；`#flutwein` 以泥痕酒瓶重构洪水地区形象但公众认知变化进入二审；Star Pubs & Bars 将酒吧变成体育、影院和音乐/变装场景；Special Olympics 将“special”落到运动能力、生活成就和关系支持 |
| 合并结果 | `ai_reviews_merged.json` 共 175 条唯一记录；`second_review_queue.json` 共 54 条 |
| 进度文件 | `review_progress.json`：reviewed 175、remaining 125、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch035.json`、`second_review_queue.pre_batch035.json`、`review_progress.pre_batch035.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`fdeb583816a0bb650069fbdbdd857154396f7bfe0d0c6cd3ccd74b802e7d6896` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.62 Evidence-300 Codex 图片证据复核 Batch036

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch036_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 176–180 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 反电子烟广告从儿童化口味转向尼古丁揭示和震惊警惕；`Sleep4Climate` 面向 Netflix/Gen Z 睡前流媒体用户；Spotify 通过同一听众的不同空间和音乐世界表达个性化；Fernet 1882 以街头 OOH 装置传播；Findasense 以反 LGBTIQ+ 仇恨经历强调无歧视的多元文化 |
| 合并结果 | `ai_reviews_merged.json` 共 180 条唯一记录；`second_review_queue.json` 共 54 条 |
| 进度文件 | `review_progress.json`：reviewed 180、remaining 120、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch036.json`、`second_review_queue.pre_batch036.json`、`review_progress.pre_batch036.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`a8fae71da44cea3a376c045683b8846e5d0fad1f3189c23f06b6afcdb4017e7a` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.63 Evidence-300 Codex 图片证据复核 Batch037

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch037_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 181–185 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Bonds 用“turtleneck/crewneck”隐喻幽默化男性内衣需求；ADT 以猎豹、海洋生物、蛇和大象对应快速、全天候、非眨眼监控与理解保护对象；Lacoste/Netflix 面向跨代剧集粉丝；其“民主愿景”抽象解释进入二审；Jow 连接选餐、购物篮和配送 |
| 合并结果 | `ai_reviews_merged.json` 共 185 条唯一记录；`second_review_queue.json` 共 55 条 |
| 进度文件 | `review_progress.json`：reviewed 185、remaining 115、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch037.json`、`second_review_queue.pre_batch037.json`、`review_progress.pre_batch037.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`f2fd1715e7b31d06d63fa8b7df87ddd3e710a1738074a67553c72ddd48968846` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.64 Evidence-300 Codex 图片证据复核 Batch038

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch038_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 186–190 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 反皮草广告面向皮草消费者并揭示手袋背后的动物伤害；Sonos Roam 用家居、沙漠、海岸和森林展示便携多场景与颜色；Juanita's 面向节日聚会中的 nacho cheese 爱好者和无接触分餐需求；Verizon 用 NFL App/Fortnite 5G 沉浸体验吸引科技与游戏受众；Sleep Boss 用“睡在另一个星球”连接梦境、睡眠重要性和可持续明天 |
| 合并结果 | `ai_reviews_merged.json` 共 190 条唯一记录；`second_review_queue.json` 共 55 条 |
| 进度文件 | `review_progress.json`：reviewed 190、remaining 110、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch038.json`、`second_review_queue.pre_batch038.json`、`review_progress.pre_batch038.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`2270b987756776ca3bf15fc2516ff2dba8c2d49c0c2ebb41dafbfe1aaaa4b339` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.65 Evidence-300 Codex 图片证据复核 Batch039

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch039_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 191–195 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Sleep Boss 夜景引发平静、惊奇与希望；Pringles 将圣诞和足球碰撞成欢乐庆祝；Belvedere 以自然、传统和工艺暗示高品质受众但进入二审；Hargreaves Lansdown 的书桌学习者代表儿童教育愿望；Redrow 以破旧房屋、工具和翻修痛苦反衬买新房 |
| 合并结果 | `ai_reviews_merged.json` 共 195 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 195、remaining 105、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch039.json`、`second_review_queue.pre_batch039.json`、`review_progress.pre_batch039.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`0533062b80da617471153baee278b5a00c8dc2c6a9844408e1b053395d495c9d` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.66 Evidence-300 Codex 图片证据复核 Batch040

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch040_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 196–200 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Żubrówka 通过假明星、假酒和社交反转吸引观众识别假货；HBO/Rock the Vote 让观众填写个人投票理由并连接平等、环境等议题；Westinghouse 用鱼闯入晚宴制造幽默与解围后的温暖；CF 青少年以终身防感染经历成为社交距离专家，并为同龄人提供安慰和希望 |
| 合并结果 | `ai_reviews_merged.json` 共 200 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 200、remaining 100、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch040.json`、`second_review_queue.pre_batch040.json`、`review_progress.pre_batch040.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`e0ff584d9db8716ef207c0f41c4a4896f2f5517776b6f77db57ad98f5ddcaa0b` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.67 Evidence-300 Codex 图片证据复核 Batch041

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch041_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 201–205 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Portal 通过祖孙分享学校小事和自然对话塑造家庭连接；IKEA 以可负担性、日常家庭场景和多样用户说明设计面向所有人；目标受众为广泛家庭与家居消费者 |
| 合并结果 | `ai_reviews_merged.json` 共 205 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 205、remaining 95、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch041.json`、`second_review_queue.pre_batch041.json`、`review_progress.pre_batch041.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`7b945ef7b253cf9498a09f06e535a886edd4155dfbbef1ad0c4bb41dae1c2e0c` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.68 Evidence-300 Codex 图片证据复核 Batch042

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch042_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 206–210 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | IKEA 用伪统计和日常场景讲述设计普及；Specsavers 用“恋爱关系”到验光师的反转建立信任；Krave 用 Comic-Con 现场谷物巧克力艺术制造惊喜；GNV 以宠物肖像引发同理和感恩；Seagram's 用 Dive Bar Trainer 教观众回归酒吧的动作 |
| 合并结果 | `ai_reviews_merged.json` 共 210 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 210、remaining 90、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch042.json`、`second_review_queue.pre_batch042.json`、`review_progress.pre_batch042.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`17c2ef4f15e9e2fb62735417b789a2c58c7b869fce8706182408096f6247aa4c` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.69 Evidence-300 Codex 图片证据复核 Batch043

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch043_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 211–215 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Veet 以居家美容角和话题分享鼓励用户参与；Sport England 展示健康状况不同的人仍能运动并传达坚韧；13cabs 描绘城市打车等待和取消；Rappi Turbo-Fresh 以十分钟到达和 Simu Liu 的名人反差突出速度 |
| 合并结果 | `ai_reviews_merged.json` 共 215 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 215、remaining 85、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch043.json`、`second_review_queue.pre_batch043.json`、`review_progress.pre_batch043.json` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`9ca60de43b7aed570a12e2f412296b457714f590021f8f2eec44daa4e5506117` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.70 Evidence-300 Codex 图片证据复核 Batch044

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch044_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 216–220 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Lacoste 两题确认跨城市、跨年龄和多元身份共享鳄鱼价值；Renault Megane 确认电动/汽油选择与驾驶愉悦；IKEA 通过跨代家庭互动支持温情、怀旧与代际连接；Artlist 确认音乐、音效、筛选和授权共同承担广告叙事功能 |
| 合并结果 | `ai_reviews_merged.json` 共 220 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 220、remaining 80、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch044/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`f925d56c626a8cb40f8584f9d01fb859bb879896f34c6a1480f3e1ec24b2f679` |
| 并行开发边界 | 可冻结前 200 条作为探索性开发子集运行后续 pilot；不得将 pilot 指标写成 Evidence-300 全量结果，也不得解除正式训练门禁 |
| 当前边界 | 继续复核第 221–300 条；正式 G2/G3、Qwen 训练和最终论文主表仍等待全量复核及二审 |

### 8.71 Evidence-300 Codex 图片证据复核 Batch045

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch045_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 221–225 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Artlist 的视觉元素与创作者工作流；IKEA 的父子共同烹饪与家庭重联；Greenpeace 的“9/10 城市居民呼吸污染空气”统计；O2 的欧盟免额外漫游费及 Bubl 机器人旅行叙事 |
| 合并结果 | `ai_reviews_merged.json` 共 225 条唯一记录；`second_review_queue.json` 共 56 条 |
| 进度文件 | `review_progress.json`：reviewed 225、remaining 75、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch045/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`05903bbc1458eaff89cb8b7cc13b6504a9060cb453c408b67fe4b7b53b9cec54` |
| 独立审计 | Batch045 单批审计通过；全历史重建审计仍发现早期批次已有 13 条视频时长边界超出记录，未在本批擅自修改 |
| 并行开发边界 | 前 200 条已冻结为 `exploratory_dev200_v1`，当前 GPU4 正在运行 MMR32 缓存；pilot 不用于正式真值、训练或最终主表 |
| 当前边界 | 继续复核第 226–300 条；正式 G2/G3、Qwen 训练和最终论文主表仍等待全量复核及二审 |

### 8.72 Evidence-300 Codex 图片证据复核 Batch046

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch046_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 226–230 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Flintstones 面向家庭消费者；Timotei 以植物/户外画面和 98% 天然成分表达自然性，并覆盖温和护发与全发质；Hook & Ladder 的电影取景地论证因抽象层级较高进入二审；McDonald's 相关广告以怀旧歌曲和旅行蒙太奇制造感官/情绪吸引 |
| 合并结果 | `ai_reviews_merged.json` 共 230 条唯一记录；`second_review_queue.json` 共 57 条 |
| 进度文件 | `review_progress.json`：reviewed 230、remaining 70、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch046/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`107c55647d65ed18e8b071bfe84625c1c6fff2ac650b38130ed804e1e33f5273` |
| 独立审计 | Batch046 单批审计通过；第229条的高层“电影作用”推断进入二审 |
| 当前边界 | 继续复核第 231–300 条；前200条 exploratory pilot 正在 GPU4 上生成缓存，不用于正式真值或最终主表 |

### 8.73 Evidence-300 Codex 图片证据复核 Batch047

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch047_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 231–235 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Shelter 通过租房拒绝和“1/5租房家长因有孩子被拒”统计呈现租房歧视；Kajabi 通过创作者障碍、平台解决方案和“摆脱自我阻碍”制造鼓励；PETA 以节日动画反转火鸡虐待传统；Bankia 以爱、团结和共同力量回应经济困难 |
| 合并结果 | `ai_reviews_merged.json` 共 235 条唯一记录；`second_review_queue.json` 共 57 条 |
| 进度文件 | `review_progress.json`：reviewed 235、remaining 65、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch047/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`5e9e748ebe6115a4182df2bc390b9c4a6fa865e5199c332983dd48b8f8065dca` |
| 独立审计 | Batch047 单批审计通过 |

### 8.74 Evidence-300 Codex 图片证据复核 Batch048

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch048_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 236–240 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Goodys 以现代高强度工作/游戏场景连接目标用户；Super-Wear 以生育风险、超级英雄保护和安心感推动购买；Valley Health 以多样群体和共同家园表达社区连接；Heluva Good! 展现露营、篝火和分享食物的户外社交生活；Verizon 以医护场景说明5G不能替代勇气与同理心 |
| 合并结果 | `ai_reviews_merged.json` 共 240 条唯一记录；`second_review_queue.json` 共 57 条 |
| 进度文件 | `review_progress.json`：reviewed 240、remaining 60、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch048/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`48737dc7e46b79cf362b66459d19136541aea3556d3038e1106cf7bb673ca209` |
| 独立审计 | Batch048 单批审计通过 |
| 并行实验 | `exploratory_dev200_v1/mmr32_cache/cache.jsonl` 已完成200/200；`qwen_mmr32` 已在GPU4启动，结果不进入正式主表 |

### 8.75 Evidence-300 Codex 图片证据复核 Batch049

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch049_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 241–245 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Kalakari 以女性农业劳动和73%统计揭示被低估的女性农民；Rockshore 露营/聚会题中象征性解释进入二审，朋友聚会情绪直接确认；Les Mills 以高强度画面、旁白和节奏音效连接健身体验；Foot Locker/Gatorade 以Snapchat互动、限量发售和Jordan信号定位数字化运动鞋消费者 |
| 合并结果 | `ai_reviews_merged.json` 共 245 条唯一记录；`second_review_queue.json` 共 58 条 |
| 进度文件 | `review_progress.json`：reviewed 245、remaining 55、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch049/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`c289b931463c4c3d4a9648383764f3ba23a5e138053f4618c7231d632856eb68` |
| 独立审计 | Batch049 单批审计通过；Rockshore 象征性问题进入二审 |

### 8.76 Evidence-300 Codex 图片证据复核 Batch050

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch050_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 246–250 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED`，0 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Gatorade/Jordan 通过Foot Locker限量发售和Snapchat互动连接球鞋文化；Aivein强调十年历史和十年无静脉曲张；Nissan Virtual Showroom通过YouTube、手机、360度视图和热点降低购车门槛；Uber Eats/Visa以餐馆、顾客、配送和无接触支付展现小企业支持及本地经济影响 |
| 合并结果 | `ai_reviews_merged.json` 共 250 条唯一记录；`second_review_queue.json` 共 58 条 |
| 进度文件 | `review_progress.json`：reviewed 250、remaining 50、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch050/`，包含三份状态快照 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`de86a269a251aa3e007d65a29b80d05e1b27edd924e491f6ebc95f04525003c5` |
| 独立审计 | Batch050 单批审计通过 |
| 并行实验 | Qwen exploratory pilot 已处理约26/200，无错误，结果仍不进入正式主表 |

### 8.47 Evidence-300 Codex 图片证据复核 Batch021

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch021_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 101–105 条；新增唯一题目 5 |
| 复核结果 | 2 条 `AI_REVIEWED`，3 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认反仇恨视频通过共享人性连接观众、Noble & Cooley 从鼓手历史到 Union Series、Regions Bank 将生活不确定性转成金融可能性、Heinz Organic Puffs 面向照护者；其中情绪/受众推断进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 105 条唯一记录；`second_review_queue.json` 共 34 条 |
| 进度文件 | `review_progress.json`：reviewed 105、remaining 195、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch021.json`、`second_review_queue.pre_batch021.json`、`review_progress.pre_batch021.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.46 Evidence-300 Codex 图片证据复核 Batch020

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch020_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 96–100 条；新增唯一题目 5 |
| 复核结果 | 0 条 `AI_REVIEWED`，5 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 记录 Just Egg 的植物蛋/运动表现叙事、工作场所安全广告、黎巴嫩葡萄酒的餐饮社交场景、反仇恨黑白人像与结尾标识；五条因参考答案为空或 ASR 不可靠，均保留二审 |
| 合并结果 | `ai_reviews_merged.json` 共 100 条唯一记录；`second_review_queue.json` 共 31 条 |
| 进度文件 | `review_progress.json`：reviewed 100、remaining 200、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch020.json`、`second_review_queue.pre_batch020.json`、`review_progress.pre_batch020.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.45 Evidence-300 Codex 图片证据复核 Batch019

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch019_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 91–95 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 SodaStream 在家制水与产品功能、动物绘画到环保信息、Bojangles 的调味鸡肉/配菜/饼干和 Bow Box；动物广告的情绪目标因参考答案为空进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 95 条唯一记录；`second_review_queue.json` 共 26 条 |
| 进度文件 | `review_progress.json`：reviewed 95、remaining 205、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch019.json`、`second_review_queue.pre_batch019.json`、`review_progress.pre_batch019.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.44 Evidence-300 Codex 图片证据复核 Batch018

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch018_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 86–90 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Avon 多元身份与包容信息、ABSA 角色提出财务愿望并以“I can”回应；DoorDash 社区餐饮可达性因参考答案为空进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 90 条唯一记录；`second_review_queue.json` 共 25 条 |
| 进度文件 | `review_progress.json`：reviewed 90、remaining 210、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch018.json`、`second_review_queue.pre_batch018.json`、`review_progress.pre_batch018.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.43 Evidence-300 Codex 图片证据复核 Batch017

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch017_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 81–85 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Elite 将巧克力棒改名为常见批评、Snack Jack 的积极思考、Lurpak 面向健康爱好者、输血延长癌症患者生命；Ford 车辆重构可能性的题因参考答案为空进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 85 条唯一记录；`second_review_queue.json` 共 24 条 |
| 进度文件 | `review_progress.json`：reviewed 85、remaining 215、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch017.json`、`second_review_queue.pre_batch017.json`、`review_progress.pre_batch017.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.42 Evidence-300 Codex 图片证据复核 Batch016

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch016_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 76–80 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Guaraná 女性玩家设计非性化游戏皮肤、Project Relate 非标准语音用户、反 COVID 歧视宣传、Dell 宇航员与空间探索；Renault Clio 作为人生伙伴的全片隐喻进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 80 条唯一记录；`second_review_queue.json` 共 23 条 |
| 进度文件 | `review_progress.json`：reviewed 80、remaining 220、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch016.json`、`second_review_queue.pre_batch016.json`、`review_progress.pre_batch016.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.41 Evidence-300 Codex 图片证据复核 Batch015

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch015_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 71–75 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 GPS Trackit 平板与软件界面、Sendwave 海外菲律宾人汇款受众、Virgin Media 以游戏打破无聊、WWF 动物图案毛衣与模仿行为；“幸福来自日常小事”属于全片归纳，进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 75 条唯一记录；`second_review_queue.json` 共 22 条 |
| 进度文件 | `review_progress.json`：reviewed 75、remaining 225、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch015.json`、`second_review_queue.pre_batch015.json`、`review_progress.pre_batch015.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.40 Evidence-300 Codex 图片证据复核 Batch014

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch014_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 66–70 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Fellow 科学家/调查者角色、有限空间派对方案、病人躺在沙发上的痛苦表情、Virgin Holidays 的旅行蒙太奇；Burger King 抵制转参与式创意的活动级叙事进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 70 条唯一记录；`second_review_queue.json` 共 21 条 |
| 进度文件 | `review_progress.json`：reviewed 70、remaining 230、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch014.json`、`second_review_queue.pre_batch014.json`、`review_progress.pre_batch014.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.39 Evidence-300 Codex 图片证据复核 Batch013

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch013_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 61–65 条；新增唯一题目 5 |
| 复核结果 | 3 条 `AI_REVIEWED`，2 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Marshall 音箱标志、Acer 跨自然/办公/出行环境、Single Fin 末段举罐并说“tastes like summer”；埃及静脉健康广告的目标受众和 Lacoste 的磁吸扣/可调肩带属于更细的隐含证据，进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 65 条唯一记录；`second_review_queue.json` 共 20 条 |
| 进度文件 | `review_progress.json`：reviewed 65、remaining 235、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch013.json`、`second_review_queue.pre_batch013.json`、`review_progress.pre_batch013.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.38 Evidence-300 Codex 图片证据复核 Batch012

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch012_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 56–60 条；新增唯一题目 5 |
| 复核结果 | 2 条 `AI_REVIEWED`，3 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Kajabi 温暖舒适的客厅场景、Goody's 头痛到恢复活力的前后转折；PETA 火鸡反虐待情绪、Cocio 快乐兴奋和 Marshall 摇滚心态因抽象语义或活动级上下文进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 60 条唯一记录；`second_review_queue.json` 共 18 条 |
| 进度文件 | `review_progress.json`：reviewed 60、remaining 240、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch012.json`、`second_review_queue.pre_batch012.json`、`review_progress.pre_batch012.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.37 Evidence-300 Codex 图片证据复核 Batch011

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch011_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 51–55 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 Renault 情绪题 `NEEDS_SECOND_REVIEW` |
| 复核内容 | 确认 Disco Darling 夜生活、Specsavers 友好交谈与关怀、Defender 自然场景中的城市标志、Total Fitness 克服挑战并庆祝胜利；Renault 保留熟悉感/兴奋感的抽象解释进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 55 条唯一记录；`second_review_queue.json` 共 15 条 |
| 进度文件 | `review_progress.json`：reviewed 55、remaining 245、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch011.json`、`second_review_queue.pre_batch011.json`、`review_progress.pre_batch011.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.36 Evidence-300 Codex 图片证据复核 Batch010

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch010_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 46–50 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED` |
| 复核内容 | 确认 Zubrowka 的 Jason Statham、Macy's 圣诞戏剧情绪、Westinghouse 鱼跃餐桌与家电运行、Frontline 免费前排票；对自动候选进行了连续区间扩展和无关结尾点降权 |
| 合并结果 | `ai_reviews_merged.json` 共 50 条唯一记录；`second_review_queue.json` 共 14 条 |
| 进度文件 | `review_progress.json`：reviewed 50、remaining 250、failures 0 |
| 备份 | `ai_reviews_merged.pre_batch010.json`、`second_review_queue.pre_batch010.json`、`review_progress.pre_batch010.json` |
| 当前边界 | 仍禁止启动正式训练；Evidence-300 尚未完成独立复核，弱候选不得作为正式真值 |

### 8.51 Evidence-300 Codex 图片证据复核 Batch051

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch051_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 251–255 条；新增唯一题目 5 |
| 复核结果 | 3 条 `AI_REVIEWED`，2 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | GIPHY Daily Affurmations 的屏幕/现实生活对比和狗角色、adidas Faster Than_ 的个人化速度与自我提升信息形成直接证据；Burger King 受众问题和 adidas 单一角色指代问题因抽象推断/多角色歧义进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 255 条唯一记录；`second_review_queue.json` 共 60 条 |
| 进度文件 | `review_progress.json`：reviewed 255、remaining 45、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch051/`，另保留两次边界/身份修正前的校正备份 |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`8ef9d36477c91e3cb8dac673f53a5fc943a417fb3b0d3fe0e4fb6e2b26c0a608` |
| 审计 | Batch051 独立协议审计通过；历史全量审计中既有的13条时长边界问题未改动 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.52 Evidence-300 Codex 图片证据复核 Batch052

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch052_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 256–260 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Fellow 将 Ode grinder 面向家庭咖啡冲煮者；Bixtonim 通过孩子和家庭照护增加感情与幽默；The Future Rocks 推广日常佩戴的现代实验室培育钻石首饰；BuzzBallz 以圆形容器突出产品独特性；Southwest 间谍晚宴的目标情绪保留二审 |
| 合并结果 | `ai_reviews_merged.json` 共 260 条唯一记录；`second_review_queue.json` 共 61 条 |
| 进度文件 | `review_progress.json`：reviewed 260、remaining 40、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch052/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`8a73802b630a752148b989b0d8260d21316e0f7e6a2395ea9d881a9844ec995f` |
| 审计 | Batch052 独立协议审计通过；未改动更早批次的历史数据质量问题 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.53 Evidence-300 Codex 图片证据复核 Batch053

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch053_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 261–265 条；新增唯一题目 5 |
| 复核结果 | 3 条 `AI_REVIEWED`，2 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | GPS Trackit 通过车队安全软件赋予受众改善驾驶安全的角色；Coca-Cola 的灯光象征和目标受众属于较抽象的节日叙事解释；Meta Rugby 题确认 AR/VR、Avatar 和 Meta 平台带来的全球互动机制 |
| 合并结果 | `ai_reviews_merged.json` 共 265 条唯一记录；`second_review_queue.json` 共 63 条 |
| 进度文件 | `review_progress.json`：reviewed 265、remaining 35、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch053/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`c66c32bebfe4d76032ee9db4bf5addfd135616c8785752dd45852eee2175ca38` |
| 审计 | Batch053 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.54 Evidence-300 Codex 图片证据复核 Batch054

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch054_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 266–270 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Tide to Go 的即时便携去污；Army Reserve 的个人成长、社区帮助与19天兼职；Undnyable 明确面向 CMO；Miller Lite 灯光秀受众因传播语境推断进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 270 条唯一记录；`second_review_queue.json` 共 64 条 |
| 进度文件 | `review_progress.json`：reviewed 270、remaining 30、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch054/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`ff02f8784ad61d4bb938ae02515fe9f73d05b8dc05dd467913a64529f7832152` |
| 审计 | Batch054 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.55 Evidence-300 Codex 图片证据复核 Batch055

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch055_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 271–275 条；新增唯一题目 5 |
| 复核结果 | 3 条 `AI_REVIEWED`，2 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | Undnyable 的 CMO 定向反无聊广告服务；Virgin Media 用玩偶拟人化表现打破日常枯燥；UNOCHA 将真实人道工作者重新定义为英雄；AlmapBBDO 十年成绩和 Mulino Bianco 情绪目标因证据噪声进入二审 |
| 合并结果 | `ai_reviews_merged.json` 共 275 条唯一记录；`second_review_queue.json` 共 66 条 |
| 进度文件 | `review_progress.json`：reviewed 275、remaining 25、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch055/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`e8e272fc5dbdbbb20f122fb1ed515d7f508b39090ceb94c4e15186b0b0dae76f` |
| 审计 | Batch055 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.56 Evidence-300 Codex 图片证据复核 Batch056

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch056_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 276–280 条；新增唯一题目 5 |
| 复核结果 | 4 条 `AI_REVIEWED`，1 条 `NEEDS_SECOND_REVIEW` |
| 复核内容 | WWF 的100%回收与可持续羊毛；CUPRA 的多学科创作者群体；Vodafone 的家庭连接与数字保护；Corona 的自然驱动生活；Renault 用 Wonderwall 女声翻唱贯穿爱情叙事 |
| 合并结果 | `ai_reviews_merged.json` 共 280 条唯一记录；`second_review_queue.json` 共 67 条 |
| 进度文件 | `review_progress.json`：reviewed 280、remaining 20、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch056/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`4f0799acad27acf6bdee7a5b9d58c8f6ade0211c918c3cc5b004ff0aa2c57181` |
| 审计 | Batch056 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.57 Evidence-300 Codex 图片证据复核 Batch057

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch057_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 281–285 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED` |
| 复核内容 | RIMOWA 将开放心态、旅行和进步联系起来，并用移动中的人物、行李和场景强化连续运动；Columbia 通过自然环境中的人物活动表现户外探索；Guaraná 通过玩家共创反性别刻板的游戏皮肤；Receipts of Respect 用握拳 QR 符号代表 Black resistance |
| 合并结果 | `ai_reviews_merged.json` 共 285 条唯一记录；`second_review_queue.json` 共 67 条 |
| 进度文件 | `review_progress.json`：reviewed 285、remaining 15、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch057/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`9784576766e848c0b4e83775c037d72477c9393c31fc1bcedfce327bd72bdd36` |
| 审计 | Batch057 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.58 Evidence-300 Codex 图片证据复核 Batch058

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch058_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 286–290 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED` |
| 复核内容 | Receipts of Respect 通过个人受害故事引发共情并推动投诉/支持；Adobe 说明创造力能跨越边界连接人；Project Relate 的个性化语音模型和 Listen/Repeat/Assistant 功能；Up Syndrome 由成员分享成就并反转污名 |
| 合并结果 | `ai_reviews_merged.json` 共 290 条唯一记录；`second_review_queue.json` 共 67 条 |
| 进度文件 | `review_progress.json`：reviewed 290、remaining 10、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch058/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`d817bb15b81eed5f6946735b23fea300ce8ed639173a22311bab5d059392c7df` |
| 审计 | Batch058 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.59 Evidence-300 Codex 图片证据复核 Batch059

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch059_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 291–295 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED` |
| 复核内容 | Cusqueña 通过地标、复制品拍卖和数字销售帮助旅游与工匠复苏；Stop the Spread 将卫生标签映射为反仇恨行为；Pringles 的“熟悉但不同”；乌兹别克装饰数据库服务工匠与创作者；Lu 成为 Magalu 的虚拟 influencer 和媒体渠道 |
| 合并结果 | `ai_reviews_merged.json` 共 295 条唯一记录；`second_review_queue.json` 共 67 条 |
| 进度文件 | `review_progress.json`：reviewed 295、remaining 5、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch059/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`dc844fe01b0d0282100dd3f7c5222991f68b8e50052a6f23142e7b9b1fac7fb5` |
| 审计 | Batch059 独立协议审计通过；未改动历史批次 |
| 当前边界 | 继续禁止正式训练、最终裁判和正式主表统计；前200条 exploratory pilot 与正式复核结果保持隔离 |

### 8.60 Evidence-300 Codex 图片证据复核 Batch060

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch060_codex_reviewed5.jsonl` |
| 本批数量 | 5 条；第 296–300 条；新增唯一题目 5 |
| 复核结果 | 5 条 `AI_REVIEWED` |
| 复核内容 | Abbé Pierre 通过歌曲贯穿流浪者重建故事；Snack Jack 用泰式幽默、反转和积极信息连接 Gen Z；Sky Bet 将球员训练与 Acca Freeze 的球迷控制形成反差，并面向足球投注用户 |
| 合并结果 | `ai_reviews_merged.json` 共 300 条唯一记录；`second_review_queue.json` 共 67 条 |
| 进度文件 | `review_progress.json`：reviewed 300、remaining 0、failures 0；`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch060/` |
| 哈希 | 本批 JSONL 本地/远端 SHA256 一致：`867c3fa3a370dfc6b310e607b1d8e9778d075c38594e48eda780643df36e90a9` |
| 审计 | Batch060 独立协议审计通过；全量重建审计待运行 |
| 当前边界 | 300条初审完成，但67条二审和历史区间边界问题未闭环；继续禁止正式训练、最终裁判和正式主表统计 |

### 8.61 Evidence-300 初审完成后的阶段门禁与全量审计

| 字段 | 内容 |
|---|---|
| 当前 Goal 阶段 | 初审已完成；转入67条二审、历史边界审计和 exploratory pilot 收尾 |
| 权威初审进度 | `reviewed=300`、`remaining=0`、`needs_second_review=67`、`formal_training_allowed=false` |
| 原始批次 | `evaluation/runs/innovation1_evidence300_stage_v1/ai_review_batches/`，60个 JSONL，保持不变 |
| 原始全量重建审计 | `ai_review_audit/full_rebuild_audit_current/`；13条记录失败，原因是14个区间端点超过严格视频时长边界 |
| 独立归一化副本 | `ai_review_audit/normalized_batches_v1/`；只用于审计，不作为新的人工真值 |
| 归一化清单 | `ai_review_audit/full_rebuild_interval_normalization_manifest.json`；记录28个端点修正，包含严格越界和浮点/索引边界修正 |
| 归一化全量审计 | `ai_review_audit/full_rebuild_audit_normalized_v1/`；`300/300`、失败 `0`、二审 `67`、`formal_training_allowed=false` |
| 探索性 pilot | 前200条 Qwen MMR32 推理继续运行；完成后必须独立进行视觉协议对齐审计，不进入正式主表 |
| 当前禁止事项 | 二审闭环前不启动正式训练、不调用最终裁判、不把 exploratory pilot 当作论文正式结果 |
| 下一步 | 逐条完成67条二审，更新权威 JSONL/哈希/门禁，再决定正式实验 |

### 8.62 Evidence-300 二审 Batch061

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch061_second_review5.jsonl` |
| 本批数量 | 5 条；二审队列前5条 |
| 处理方式 | 替换原始批次中的5条记录；原始批次文件不覆盖 |
| 本批结果 | 5 条全部改为 `AI_REVIEWED`；Sherwin-Williams、Noble & Cooley 保留 `partial` 可观察性说明 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共62条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=62`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch061/` |
| 本批 SHA256 | `596df11c202534443d4ab29c6fcaa6ab1f7d450bd9133943229374da690093cf` |
| 原始替换审计 | 仍只暴露既有13条历史记录的严格时长边界问题 |
| 归一化替换审计 | `ai_review_audit/full_rebuild_audit_after_batch061_normalized_v1/`；300/300，失败0，二审62 |
| 当前边界 | 二审尚余62条；正式训练、最终裁判和正式主表统计继续禁止 |
| 下一步 | 从新的二审队列首条继续，每批5条 |

### 8.63 Evidence-300 二审 Batch062

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch062_second_review5.jsonl` |
| 本批数量 | 5 条；二审队列第6–10条 |
| 处理方式 | 替换原始批次中的5条记录；原始批次文件不覆盖 |
| 本批结果 | 5 条全部改为 `AI_REVIEWED`；情绪、隐喻、儿童权益等抽象结论保留 `partial` 或上下文限制 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共57条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=57`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch062/` |
| 本批 SHA256 | `9de94409ebb214700102f11bb0b60da5f49b8ac197bcc47aadf1a06cb7275b9e` |
| 原始替换审计 | 仍只暴露既有13条历史记录的严格时长边界问题 |
| 归一化替换审计 | `ai_review_audit/full_rebuild_audit_after_batch062_normalized_v1/`；300/300，失败0，二审57 |
| 当前边界 | 二审尚余57条；正式训练、最终裁判和正式主表统计继续禁止 |
| 下一步 | 从新的二审队列首条继续，每批5条 |

### 8.64 Evidence-300 二审 Batch063 与当前 Goal 有效版本

| 字段 | 内容 |
|---|---|
| 当前有效 Goal | 完成剩余52条二审；exploratory_dev200 已完成并通过单 shard 协议审计；门禁通过后才启动正式训练/最终评测 |
| 旧断点 | “从第96条开始、95/300、二审26、剩余205”已过时，仅保留在系统历史元数据中 |
| 复核批次 | `batch063_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 处理方式 | 替换原始批次中的5条记录；原始批次文件不覆盖 |
| 本批结果 | 5条全部改为 `AI_REVIEWED`；抽象情绪和用途结论保留 `partial`，OnePlus 充电延迟结论为 `visual_audio` |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共52条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=52`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch063/` |
| 本批 SHA256 | `498836329b77c923c43b078c1587f0ac79ed4d9b2153bc6dfaac4a51da4ee3e8` |
| 权威合并哈希 | `ai_reviews_merged.json`: `ae747d2a07845758299950b922d7d8f29b74ce1ed722b716bb71cbe8872a6c46`; `second_review_queue.json`: `349ebe2dfe221b0c51fddd9051afaa6bc373bff6af5695e0655ddff4c6b6a7e8` |
| 原始审计 | 正确暴露既有13条历史区间时长边界问题；Batch063未新增边界错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch063_normalized_v1/`；300/300，失败0，二审52 |
| 探索性 pilot | GPU4 上 Qwen exploratory_dev200 已完成200/200并通过单 shard视觉协议审计，仍不能作为正式论文主表结果 |
| 下一步 | 继续每批5条二审；门禁通过前不启动正式训练/最终裁判 |

### 8.65 exploratory_dev200 完成与视觉协议审计

| 字段 | 内容 |
|---|---|
| 实验路径 | `evaluation/runs/innovation1_evidence300_stage_v1/exploratory_dev200_v1/` |
| 模型 | `<MODEL_ROOT>/Qwen3Vl-8B` |
| GPU | GPU4；单 shard；进程已自然退出 |
| 推理覆盖 | 证据 `200/200`；预测 `200/200`；缺失/额外/重复/解析错误均为0 |
| 公平协议 | 32输入/表示/提交视图，11,664视觉Token，二次采样关闭，RAG关闭，反思关闭 |
| 审计脚本 | `evaluation/eval/audit_visual_protocol.py` |
| 审计结果 | `audit_visual_protocol.json`：`all_valid=true`，协议违规0 |
| 对齐脚本说明 | temporal alignment 脚本固定要求3个shard，不适用于本次单shard pilot；不将该拓扑限制误判为实验失败 |
| 论文状态 | exploratory 结果不能直接作为正式主表；Evidence-300 二审尚余52条，`formal_training_allowed=false` |
| 下一步 | 继续二审；二审闭环后再决定正式训练和最终评测 |

### 8.66 Evidence-300 二审 Batch064 与边界修正

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch064_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；4条 `partial`，Lacoste 特征项为 `ungroundable` |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共47条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=47`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch064/`；边界修正前另有 `ai_review_audit/backups/pre_batch064_correction/` |
| 本批 SHA256 | `69cdc07fdd8168b7c36cb63c4fa780fa76fe74080e48f02cd739d4a8724c9ea0` |
| 权威合并哈希 | `ai_reviews_merged.json`: `f23cef611c9b5727a91da78ea64434ce315482299bd4c3d81bab03a1f83172cb`; `second_review_queue.json`: `b4843617b37490bc5a833fb3bb4dbc7557889f08b7dca5b1fc185f75bf1d4085` |
| 边界修正 | Turkey 区间末端从 `90.2s` 修正为视频索引时长 `90.0s` |
| 原始审计 | `287/300` 严格通过；13条历史区间边界问题；Batch064修正后无新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch064_normalized_v1/`；300/300，失败0，二审47 |
| 当前门禁 | 47条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.67 Evidence-300 二审 Batch065

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch065_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；抽象叙事保留 `partial`，无参考答案项明确限制解释范围 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共42条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=42`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch065/` |
| 本批 SHA256 | `06d9ca1661b6a3b26ca185829ce71de5c661a800a82a94a973a9e9d65bbc56c0` |
| 权威合并哈希 | `ai_reviews_merged.json`: `9c6dd65cbe6896d5889d01dce9fabeef7fe187318b624527f6d3cfceb323576b`; `second_review_queue.json`: `725f268a2cc7244f1d5252b5e30bfa3ad20908b6f53a18f62938bae24140db1c` |
| 原始审计 | 13条历史区间边界问题；Batch065未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch065_normalized_v1/`；300/300，失败0，二审42 |
| 当前门禁 | 42条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.68 Evidence-300 二审 Batch066

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch066_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；无参考答案项保留 `partial` 和解释限制 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共37条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=37`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch066/` |
| 本批 SHA256 | `c3c91afac495ff8c0135fcb35e6cdd1e82f2bfe78ef3d759cc025e3f7437ecbc` |
| 权威合并哈希 | `ai_reviews_merged.json`: `8b7c3158bd36b6446c523c16a67a5551f62a4274b6efa607ed075c4a94c1dce4`; `second_review_queue.json`: `b27762de85cc36f7c807ae25cb4f62670e5fbec89f3c9c0f4cb5e27e9d75e52e` |
| 原始审计 | 13条历史区间边界问题；Batch066未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch066_normalized_v1/`；300/300，失败0，二审37 |
| 当前门禁 | 37条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.69 Evidence-300 二审 Batch067

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch067_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；抽象情绪/受众结论保留 `partial` |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共32条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=32`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch067/` |
| 本批 SHA256 | `56ef531483e07926f1c87939bb19c76739dda569c51a94c8f6aae03cfcbbed36` |
| 权威合并哈希 | `ai_reviews_merged.json`: `e63ee1f7a4fec69c342ec21809b72e46e33299acbc3cbda73ba07bce7db5cff3`; `second_review_queue.json`: `3d7db68dc793f03879752d3d75e84995068504c4af150f78add1192471fb37d0` |
| 原始审计 | 13条历史区间边界问题；Batch067未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch067_normalized_v1/`；300/300，失败0，二审32 |
| 当前门禁 | 32条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.70 Evidence-300 二审 Batch068

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch068_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；镜面叙事和情绪连接题保留 `partial`，Alexa 产品题补充片尾证据 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共27条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=27`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch068/` |
| 本批 SHA256 | `5ecef05a0a5ed4f7eec6a7b8045196e786d2a4c6d683f2bcfdf960b13f05a5a8` |
| 权威合并哈希 | `ai_reviews_merged.json`: `0222d796ebad0d50274123852eaa7e87ffa2b14ddc873132c18a36df993a6e7e`; `second_review_queue.json`: `9247ab027019255992a2207e8517a7a3913b95f938ff967ef4aa4628294f7bfa`; `review_progress.json`: `3a15dbdcf55698093ec4b39567dbe1a889ceb6c4c9defb0175bcf43274d3b087` |
| 原始审计 | 13条历史区间边界问题；Batch068未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch068_normalized_v1/`；300/300，失败0，二审27 |
| 当前门禁 | 27条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.71 Evidence-300 二审 Batch069

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch069_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；抽象受众、情感和象征意义均保留 `partial` |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共22条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=22`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch069/` |
| 本批 SHA256 | `6e3ce2c7fc0900df428216025d60349e3ef24a6c67009b080e0d5e3f1839f5b6` |
| 权威合并哈希 | `ai_reviews_merged.json`: `9b595eff3303a76e99196572be4580594e18a46279b14f77e30a99af4e4cce35`; `second_review_queue.json`: `1b917b43edaf5d4616cfa4a8cd2bde8ded71a370776e05c6598ed78ce6fac9fe`; `review_progress.json`: `83713d606f875871431d2fcf8c07677e48e52dc921fc758b22e1ab5ccdaa67c2` |
| 原始审计 | 13条历史区间边界问题；Batch069未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch069_normalized_v1/`；300/300，失败0，二审22 |
| 当前门禁 | 22条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.72 Evidence-300 二审 Batch070

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch070_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；2条判定为 `ungroundable`，其余保留 `partial` 或直接视觉证据 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共17条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=17`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch070/` |
| 本批 SHA256 | `eee752245e84164b0e02e957f09446e9252c3c61b60848836e0493a36fd42fd7` |
| 权威合并哈希 | `ai_reviews_merged.json`: `9a0103ea28d36c1efdeb786abed52d0f8ae1de3481011d5a8440fa75ae0de95b`; `second_review_queue.json`: `7f8086adb90366b7b1bb37376d1db5c71e9529f283b130f6d45ff048d4ab6198`; `review_progress.json`: `215d71f6cf1dd17a9e9de32f0c4d5f4c5ed48d5cb81717a70e6f58c2557360f6` |
| 原始审计 | 13条历史区间边界问题；Batch070未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch070_normalized_v1/`；300/300，失败0，二审17 |
| 当前门禁 | 17条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.73 Evidence-300 二审 Batch071

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch071_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；Flutwein 影响题判定为 `ungroundable`，其余保留部分可观察性 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共12条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=12`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch071/` |
| 本批 SHA256 | `656139c6c850c8bc5dc2ed61d1deafa37d30761036154f471548665061048193` |
| 权威合并哈希 | `ai_reviews_merged.json`: `8db74f123e0d7576dbd469fd5c6f8d6b100ea93111dba291af345b1102052863`; `second_review_queue.json`: `874f871c956581ce19f160a291a8a4fa27c9f0894eba07a43a2585509f180ada`; `review_progress.json`: `ba7915fa5e5b37c2fb6ff3557faa3370ce0a5b75b5be536edbadb4ba050983f1` |
| 原始审计 | 13条历史区间边界问题；Batch071未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch071_normalized_v1/`；300/300，失败0，二审12 |
| 当前门禁 | 12条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审 |

### 8.74 Evidence-300 二审 Batch072

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch072_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；抽象语义均绑定到具体视听证据，Adidas 年长女性跑者题置信度较高 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共7条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=7`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch072/` |
| 本批 SHA256 | `8083ae8233e844a3e3233704c1b29fa6b636eb2b41ad7baf77fbd154bea2ac6b` |
| 权威合并哈希 | `ai_reviews_merged.json`: `a6b65ec197aa09c958f09e44b8343225afdcd128f6bb4433a94cee7471de8e83`; `second_review_queue.json`: `8a76484771c06aaec758249c433caf08a43e999bf11a90024c513174c3660fc2`; `review_progress.json`: `ee55b3c14b2d2198fc833083e12720c68704d635ebc85ae13e687588946fd187` |
| 原始审计 | 13条历史区间边界问题；Batch072未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch072_normalized_v1/`；300/300，失败0，二审7 |
| 当前门禁 | 7条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 继续每批5条二审，随后处理最后2条 |

### 8.75 Evidence-300 二审 Batch073

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch073_second_review5.jsonl` |
| 本批数量 | 5条；二审队列第1–5条 |
| 复核结果 | 5条全部 `AI_REVIEWED`；间谍、圣诞灯光和广告公司题的关键证据得到确认 |
| 处理方式 | 替换原始批次中的5条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 共2条 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=2`、`formal_training_allowed=false` |
| 备份 | `ai_review_audit/backups/pre_batch073/` |
| 本批 SHA256 | `848e18835af188ac50b915ceac9a26c4608f22625d68d8e53ffcd44c63f637ea` |
| 权威合并哈希 | `ai_reviews_merged.json`: `a671a70589918471dfebe3e9d9f67af1c583adbed6deae5eca0d344bbc44ea6f`; `second_review_queue.json`: `1124a9ed0fded2c81bd669fe531baee5b14333a652769d703287d5c4af2c0820`; `review_progress.json`: `90ada13518fa8d90d6549ba30cdb3c82581f81efcbd3e6d0e40c7cc839421e71` |
| 原始审计 | 13条历史区间边界问题；Batch073未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch073_normalized_v1/`；300/300，失败0，二审2 |
| 当前门禁 | 2条二审仍未闭环，继续禁止正式训练、最终裁判和正式主表统计 |
| 下一步 | 处理最后2条二审并进行最终门禁审计 |

### 8.76 Evidence-300 二审 Batch074 与最终门禁

| 字段 | 内容 |
|---|---|
| 复核批次 | `batch074_second_review2.jsonl` |
| 本批数量 | 2条；处理最后2条二审 |
| 复核结果 | 2条全部 `AI_REVIEWED`；Mulino Bianco 与 Corona Living Billboard 保留 `partial` |
| 处理方式 | 替换原始批次中的2条记录；原始批次不覆盖 |
| 合并结果 | `ai_reviews_merged.json` 共300条唯一记录；`second_review_queue.json` 为空 |
| 权威进度 | `reviewed=300`、`remaining=0`、`needs_second_review=0`、`formal_training_allowed=true` |
| 备份 | `ai_review_audit/backups/pre_batch074/` |
| 本批 SHA256 | `db05cb97f0e6005bf3a77cc1824e964b37ea845752a24a63a7c4517a1b48787c` |
| 权威合并哈希 | `ai_reviews_merged.json`: `e68472f39fa47010acf4d59dae3fc770a71ef27e98a2ee16b5a76e0411a23404`; `second_review_queue.json`: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`; `review_progress.json`: `1566d8a558f22422f30b43d7e9ed10ff079c0cd1c7faa14c2e919a0e156bc424` |
| 原始审计 | 13条历史区间边界问题；Batch074未新增错误 |
| 归一化审计 | `ai_review_audit/full_rebuild_audit_after_batch074_normalized_v1/`；300/300，失败0，二审0 |
| 当前门禁 | Evidence-300 复核闭环，允许进入冻结配置下的正式对比实验；仍需单独完成视觉协议审计和正式结果评测 |
| 下一步 | 启动正式创新点一对比实验前的配置冻结与最终协议检查 |

### 8.77 Evidence-300 冻结对照 Goal 启动

| 字段 | 内容 |
|---|---|
| Goal 状态 | 旧复核 Goal 已收口；新冻结配置对照 Goal active |
| 人工复核 | `300/300`；二审队列 `0`；规范化审计通过 |
| 已有探索结果 | `exploratory_dev200_v1/qwen_mmr32`，`200/200`，视觉协议 `all_valid=true` |
| 后100缓存 | `evaluation/runs/innovation1_evidence300_stage_v1/exploratory_tail100_v1/mmr32_cache/cache.jsonl` |
| 后100缓存审计 | `100/100`；候选源帧一致 `100/100`；8-bin覆盖 `100/100`；错误 `0` |
| 后100推理 | `evaluation/runs/innovation1_evidence300_stage_v1/exploratory_tail100_v1/qwen_mmr32/` |
| 模型 | Qwen3-VL-8B，`<MODEL_ROOT>/Qwen3Vl-8B` |
| 固定协议 | 32视图、11,664视觉Token、无RAG、无反思、关闭二次采样 |
| GPU | GPU4；GPU1保留，GPU0/5不使用 |
| 当前状态 | 后100条 Qwen 推理运行中；完成后做视觉协议审计 |
| 禁止结论 | 在 Raw 对照、裁判和Bootstrap完成前，不宣称 QA 精度提升 |

### 8.78 Evidence-300 正式 Raw Uniform 对照启动

| 字段 | 内容 |
|---|---|
| 状态核验 | Evidence-300 已 `300/300`；二审队列 `0`；完整协议门禁通过 |
| MMR32 后100 | 已完成 `100/100`；目录 `evaluation/runs/innovation1_evidence300_stage_v1/exploratory_tail100_v1/qwen_mmr32/` |
| Raw Uniform | 已启动 `300/300`，目录 `evaluation/runs/innovation1_evidence300_stage_v1/formal_raw_uniform_v1/` |
| 模型与协议 | Qwen3-VL-8B；32视图；11,664视觉Token；无RAG；无反思；关闭二次采样 |
| GPU | GPU4；GPU1保留；GPU0/5未使用 |
| 当前状态 | Raw 生成运行中；完成后做全量视觉协议审计 |
| 统计门禁 | 两方法完整、question_id对齐且审计通过后，才运行逐题结果和10,000次Bootstrap |
| 其他 | 不新增参数扫描；不启动创新点二；不把探索性结果提前写入正式结论 |

## 9. 后续实验登记模板

新增实验时先在“实验总览”增加一行，再复制以下模板。禁止只记录结果目录名而不记录数据集、模型和评测口径。

```markdown
## X. 实验名称

| 字段 | 内容 |
|---|---|
| 实验 ID | |
| 日期 | |
| 模型/checkpoint | |
| 推理脚本及哈希 | |
| 数据集及样本数 | |
| 输入帧/视图 | |
| video_grid_thw | |
| 视觉 Token | |
| RAG/反思 | |
| 关键参数 | |
| 结果路径 | |
| 评测文件及裁判 | |
| 覆盖率 | |
| Answer 1/0.5/0 | |
| Strict/Relaxed | |
| 已知问题 | |
| 当前状态 | |
```

### 8.79 Evidence-300 冻结配置正式对比结果

| 字段 | 内容 |
|---|---|
| 实验 ID | innovation1_evidence300_stage_v1_formal_raw_vs_mmr32 |
| 日期 | 2026-07-16 |
| 数据集及样本数 | Evidence-300，300 条；人工复核 `300/300`，二审队列 `0` |
| 模型/checkpoint | Qwen3-VL-8B，`<MODEL_ROOT>/Qwen3Vl-8B` |
| 输入帧/视图 | 两组均 32 个实际表示视图；关闭二次采样 |
| 视觉 Token | 11,664；视觉协议审计 `all_valid=true` |
| RAG/反思 | 无 RAG；无反思 |
| Raw 结果 | `evaluation/runs/innovation1_evidence300_stage_v1/formal_raw_uniform_v1/` |
| MMR32 结果 | `evaluation/runs/innovation1_evidence300_stage_v1/formal_mmr32_v1/`；目录级符号链接，审计使用文件级链接视图，不改变结果 |
| 视觉审计 | `evaluation/runs/innovation1_evidence300_stage_v1/formal_visual_protocol_audit_v1.json`；两组 `300/300`，违规 `0` |
| 裁判 | `evaluation/runs/innovation1_evidence300_stage_v1/deepseek_judge_v1/`；历史 full-response DeepSeek 协议 |
| 裁判模型 | `deepseek-v4-flash`；API key 仅在远端临时环境使用，未打印、复制或归档 |
| Raw Answer 1/0.5/0 | `189/74/37` |
| MMR32 Answer 1/0.5/0 | `188/76/36` |
| Raw Strict/Relaxed | `63.00% / 75.33%` |
| MMR32 Strict/Relaxed | `62.67% / 75.33%` |
| 配对结果 | Raw 胜 `42`，平 `218`，MMR32 胜 `40`；均值差 `0` |
| Bootstrap | `10,000` 次；配对均值差 CI `[-0.0317, 0.0317]` |
| 分类分析 | 已写入 `summary.json`，覆盖 Type_1 至 Type_5 主类型及 membership 统计 |
| 当前状态 | 正式对比完成；证据定位协议通过，但 QA 准确率无稳定提升 |
| 论文口径 | 不宣称 MMR32 提高总体 QA；保留“定位—回答收益不一致”的实证贡献 |

### 8.80 Evidence-300 问题自适应 Raw/MMR 路由门禁

| 字段 | 内容 |
|---|---|
| 实验 ID | `adaptive_temporal_router_evidence300_v1` |
| 日期 | 2026-07-16 |
| 目的 | 用回答前特征预测每题应选择 Raw32 还是 MMR32，不增加视觉 Token 或 Qwen 调用次数 |
| 数据划分 | Evidence-300 视频隔离 `200/50/50`；跨划分视频重合 `0`；五类均衡 |
| 正例定义 | 同题 DeepSeek 分数中 `MMR32 > Raw` |
| 正例数量 | 训练 `25/200`；校准 `6/50`；开发 `9/50` |
| 特征 | 问题文本/类型、ASR 可用性、问题-ASR 可靠性、响应统计、Raw/MMR 重合率、时间空洞与覆盖；无答案、标准答案或裁判分数输入 |
| 模型 | 固定单隐层 16 维 NumPy MLP；内部视频分组验证；无参数扫描 |
| 防泄漏 | 本地与远端单测均 `3/3`；监督字段改变时特征向量完全不变 |
| 校准结果 | 无阈值满足预注册约束；fail-closed 阈值 `0.7873916182` |
| 开发结果 | 切换 `0/50`；Raw 与路由均为 Strict `62.00%`、Relaxed `74.00%`；增益 `0` |
| 开发门禁 | `has_switches=false`、`relaxed_positive=false`，总体 `passed=false` |
| 类型规则诊断 | 训练集选 Type_1/5；校准与开发 Relaxed 均 `+1` 点，但有效切换仅 `2/20`、`3/20`，且类型方向跨划分翻转 |
| Confirm-D | **禁止运行**；未通过开发门禁，不使用 GPU |
| 结果路径 | `evaluation/runs/adaptive_temporal_router_evidence300_v1/` |
| 数据集 SHA256 | `1f637931acf04607b965d9c31d8eb827994ca35dcb552c36dc01e12ae29c1d93` |
| 门禁报告 SHA256 | `ddaed61b117ab28714e9e383c5b868b518262fd595fc21f4abb8a7b3d2380f70` |
| 当前状态 | 负结果；创新点一准确率优化冻结，不再更换分类器或扫描阈值 |

### 8.81 创新点二声明级 Target/Control Smoke30

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation2_claim_verifier_v2_smoke30_oracle_protocol_v1` |
| 日期 | 2026-07-16 |
| 目的 | 在训练前检验声明支持分数能否区分决定性证据删除与等成本对照删除 |
| 数据 | Evidence-300 分层30条；Type_1至Type_5各6条；30个唯一视频 |
| 模型 | Qwen3-VL-8B，`<MODEL_ROOT>/Qwen3Vl-8B` |
| 输入协议 | Raw32；三种证据状态均32个实际表示视图；视觉Token不超过12,000；关闭二次采样 |
| 干预 | 完整证据、人工区间内目标帧马赛克、等帧数区间外对照帧马赛克 |
| 推理状态 | `30/30`，错误0，视觉协议违规0 |
| 严格配对 | `15/30 = 50.00%` |
| 平均 target/control 下降 | `0.00251 / 0.06046` |
| 必要性对比 | 均值 `-0.05796`；10% trimmed mean `-0.00200` |
| 支持概率饱和 | `>=0.99` 为 `25/30`；`>=0.999` 为 `22/30` |
| 正确性识别 | Full-support 对 Strict 正确答案 AUROC `0.5566` |
| 诊断门禁 | **失败**；不训练、不扩样本、不补证、不运行Confirm-D |
| 失败原因 | 长证据区间迫使control集中到含总结语/Logo/CTA的片尾；零样本支持裁判明显饱和 |
| 远端路径 | `evaluation/runs/innovation2_claim_verifier_v2/` |
| 本地产物 | `artifacts/innovation2_claim_verifier_smoke30_20260716_v1/` |
| scores SHA256 | `3ea5896fdfab97c4f97f27098bf49e0e27ab14adbfd060d298aee068d420b89a` |
| diagnostic SHA256 | `aeb6edf9b6046864dabc18558271544ab861ce259699ebda65a191449b73aa68` |

### 8.82 创新点二 Guarded Target/Control Smoke30 v2.1

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation2_claim_verifier_smoke30_guarded_v21` |
| 日期 | 2026-07-16 |
| 数据 | 新30条；五类各6条；唯一视频30；与v2首轮问题/视频重合均0 |
| 合格策略 | 证据覆盖≤70%；首尾保护5%；边界保护2%；control跨≥2时间段；ASR时长误差≤35% |
| 模态 | 视觉15；ASR15 |
| 模型与协议 | Qwen3-VL-8B；Raw32；三态均固定32视图；视觉Token≤12,000；无二次采样/RAG/反思 |
| 完整性 | `30/30`，错误0，协议违规0 |
| 整体 target/control 下降 | `0.05127 / -0.00100` |
| 整体严格配对 | `18/30=60.00%`；Wilson CI `[42.32%,75.41%]` |
| 整体必要性 | 均值 `0.05227`；Bootstrap CI `[-0.00241,0.13094]` |
| 视觉分支 | `13/15=86.67%`；Wilson CI `[62.12%,96.26%]`；必要性 Bootstrap CI `[0.00378,0.25143]` |
| ASR分支 | `5/15=33.33%`；必要性均值 `-0.00390` |
| 正确性关系 | 视觉必要性AUROC `0.5179`；ASR必要性AUROC `0.78`，但ASR干预方向失败 |
| 结论 | 视觉干预工具成立；统一跨模态验证器未成立；禁止训练跨模态MLP、补证和Confirm-D |
| 远端路径 | `evaluation/runs/innovation2_claim_verifier_v2/smoke30_guarded_protocol_v21/`、`smoke30_qwen_support_v21/` |
| 本地产物 | `artifacts/innovation2_claim_verifier_smoke30_v21_20260716/` |
| scores SHA256 | `30f82b0ef1fc8b54789ca41cd4bdc2748b54d4ba6d026cf30c1482341b6d3998` |
| diagnostic SHA256 | `72294a6522c1e1bb1f70511e0d2b87f9f602fb2d2680748d822deb0dbe0873e2` |

### 8.83 创新点二直接声明可靠性验证器 v2.2

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation2_claim_reliability_v22` |
| 日期 | 2026-07-16 |
| 数据划分 | Evidence-300视频隔离 `200/50/50`；跨划分视频重合0 |
| 可靠标签 | DeepSeek Raw评分1；Train/Calib/Dev正例 `127/31/31` |
| 输入特征 | Qwen full-support三类概率、文本一致性、ASR/OCR可用性、候选相关性统计、问题类型 |
| 禁止特征 | 标准答案、裁判分数、人工证据区间、人工target/control差值 |
| Qwen覆盖 | `300/300`；最终错误0、视觉协议违规0；Raw32、Token≤12,000、无二次采样 |
| 模型 | 固定L2逻辑回归；温度 `1.8`；Calib阈值 `0.465175`；无模型/正则扫描 |
| 模型AUROC | Train `0.7191`；Calib `0.6129`；Dev `0.5688` |
| Dev基线AUROC | Qwen full-support `0.5637`；模型仅 `+0.0051` |
| Dev AUPRC/F1/Accuracy | `0.7501 / 0.7297 / 0.6000` |
| Dev ECE | 模型 `0.0846`；基线 `0.4147` |
| Dev AURC | 模型 `0.2821`；基线 `0.3002` |
| 风险覆盖 | 模型40/60/80/100%风险 `0.30/0.40/0.35/0.38`，不单调 |
| 门禁 | **失败**：AUROC<0.70且风险覆盖不单调；禁止补证与Confirm-D |
| 远端路径 | `evaluation/runs/innovation2_claim_reliability_v22/` |
| 本地产物 | `artifacts/innovation2_claim_reliability_v22_20260716/` |
| scores SHA256 | `b9618dd2da05aef1c82c5de30a4e6982072c34941075d76418a39bdbcd7eb6ad` |
| gate SHA256 | `8bd826dc9fbbb9e4091e90e48c1e3447b66058b719b352bb8ac5911714fd3ea2` |

### 8.84 创新点二 v2.3 声明支持/冲突证据依赖性门禁

| 字段 | 内容 |
|---|---|
| 实验 ID | `innovation2_claim_support_conflict_v23` |
| 日期 | 2026-07-16 |
| 任务 | 固定问题下判断声明被视频证据支持，或与决定性事实直接冲突 |
| Smoke数据 | `29` 个有效声明对，`58` 条；三分类不足证据被永久移除 |
| Qwen协议 | Qwen3-VL-8B；Raw32；32个实际表示视图；视觉Token `11,664`；关闭二次采样；无RAG/反思 |
| 正确证据配对准确率 | `29/29=100.00%` |
| 失配证据配对准确率 | `11/29=37.93%` |
| 平均正确—失配证据增益 | `0.85550`；10,000次Bootstrap CI `[0.73050,0.95723]` |
| 证据依赖性门禁 | **通过**：准确率差超过0.20，且增益CI下界大于0 |
| 全量候选 | Train `156` 对 / `312` 行；Eval `69` 对 / `138` 行；输入审计与泄漏审计通过 |
| 当前状态 | Qwen全量评分运行中；Train/Eval评估和Bootstrap尚未产生，不提前写正式结论 |
| 远端路径 | `evaluation/runs/innovation2_claim_support_conflict_v23/` |
| 关键门禁文件 | `pair_smoke29/evidence_dependence.json` |

### 8.85 v2.3 全量 Eval 与 text-only 控制

| 字段 | 内容 |
|---|---|
| Train完成度 | `312/312`；`119`个视频；错误0；协议通过 |
| Eval完成度 | `138/138`；`52`个视频；错误0；协议通过 |
| Train/Eval视频交集 | `0` |
| 视觉协议 | 每行32个唯一帧；实际表示32；视觉Token `11,664`；二次采样关闭 |
| Eval视觉配对结果 | AUROC `0.94938`；AUPRC `0.94368`；配对准确率 `97.10%`；CI `[92.75%,100.00%]` |
| Eval视觉证据增益 | 平均支持度差 `0.76253`；Bootstrap CI `[0.66685,0.85093]` |
| Train视觉配对结果 | AUROC `0.95081`；AUPRC `0.94407`；配对准确率 `94.87%`；CI `[91.03%,98.08%]` |
| Eval text-only | AUROC `0.83848`；AUPRC `0.81105`；配对准确率 `85.51%`；CI `[76.81%,92.75%]` |
| 视觉—text-only差异 | 配对准确率 `+11.59`个百分点；Bootstrap CI `[+2.90,+20.29]`个百分点；平均支持度差增益 CI `[0.10124,0.39736]` |
| 门禁 | **通过**：证据依赖、text-only差异、协议审计和监督泄漏审计均通过 |
| 运行时审计 | `evaluation/runs/innovation2_claim_support_conflict_v23/runtime_audit_v23.json` |
| Eval报告 | `full_pairs_eval/evaluation.json` |
| text-only报告 | `text_only_eval/evaluation.json`；比较报告 `visual_vs_text_only.json` |
| 当前状态 | Eval冻结；失配视觉/text-only、轻量验证器和完整审计均已完成；不进入QA答案切换 |

### 8.86 v2.3 失配控制、轻量验证器与最终门禁

| 字段 | 内容 |
|---|---|
| 失配视觉评分 | `train_mismatched_evidence/qwen_support/`，312/312，错误0，协议通过 |
| 失配 text-only | `train_mismatched_evidence/text_only/`，312/312，错误0 |
| 训练方式 | CPU轻量MLP；128个Train来源问题拟合，28个Train来源问题内部开发；Eval69对冻结 |
| 变体 | `full`、`no_mismatch_ranking`、`no_fact_conflict`、`no_distractor_consistency` |
| 完整验证器 Eval | 配对94.20%；CI `[88.41%,98.55%]`；AUROC 0.91745；AUPRC 0.86483 |
| 最强基线视觉Qwen | 配对97.10%；CI `[92.75%,100.00%]`；AUROC 0.94938；AUPRC 0.94369 |
| text-only基线 | 配对85.51%；CI `[76.81%,92.75%]`；AUROC 0.83848；AUPRC 0.81119 |
| v2.2基线 | 配对50.00%；同问题两条声明同分，平局按0.5计分，不代表全错 |
| 消融结论 | 去掉事实冲突目标降至42.03%；去掉失配排序和干扰一致性均为92.75% |
| 完整审计 | `lightweight_verifier_audit_v23.json`，`passed=true` |
| 逐题结果 | `lightweight_verifier_v23/predictions_*.jsonl` |
| 最终报告 | `lightweight_verifier_v23/report.json` |
| 最终决策 | 验证器超过text-only但未超过视觉Qwen；创新点二冻结为声明级证据验证，不进入QA答案切换 |

关键哈希：Train输入 `fa7e913ad36cd0a20defbc51b88d373516d631e7bea3934c282fe4f299c96d10`；Train标签 `6fb487da614f3fcbfbead08b0f63adbf9f4a0031791854a8a1efa2db36a1b9b7`；Eval输入 `03e2b23531df6423b5e5975e3d43cbaf9944d0e621fa8b18535af3a5ccedb225`；Eval标签 `da4767da75e3e381333a31837dd5d392f3bc0532c97c9958e17d627055ef9a5a`；失配输入 `e7c595e7d4c2decf5d0c57d85d05c191ebe586675bbcb76024775334a81dd8d9`；最终报告 `a27e663ed1de3420aa0708796321da30049e88d56437a2ba802ad8b676a56c11`。

### 8.87 RealClaim-300 v2 正确 Raw32 视觉重跑（2026-07-16）

| 字段 | 内容 |
|---|---|
| 实验目录 | `evaluation/runs/innovation2_realclaim300_v2_corrected_frames/` |
| 数据 | Evidence-300；300题、209个视频、1469条原子声明；视频隔离 Train/Calibration/Development=`200/50/50` |
| 模型与输入 | Qwen3-VL-8B；正确 `visual_plan.frame_index` Raw32 源帧；32个实际表示视图；11,664视觉Token |
| 运行协议 | RAG关闭；反思关闭；二次采样关闭；推理输入不含答案或旧标签 |
| 完成度 | `1469/1469`；errors=`0`；`complete=true`；`protocol_passed=true` |
| 视觉审计 | `realclaim_visual_protocol_audit_v2.json`，`passed=true`；所有行均为 `32/32/11664/secondary=false` |
| Development Qwen视觉 | AUROC `0.5378`；AUPRC `0.6186` |
| Development text-only | AUROC `0.5457`；AUPRC `0.6268` |
| Development v2.3 | AUROC `0.5310`；AUPRC `0.6380` |
| 视觉相对 text-only | AUROC差 `-0.0080`；10,000次问题级Bootstrap CI `[-0.1277, 0.1145]` |
| 结果口径 | 旧参考答案语义标签诊断，非独立视频证据金标签；不得写成自动纠错或QA提升 |
| 关键哈希 | claims `3a36042121fa72abcacfae2a32521745f9b458d84a96bebfeafaed5931e2dc76`；scores `cc8c4f20b65fe829e470c63fa7e901b108c2618af43632ceb1ebb7383836b84c` |

下一门禁是 `EvidenceSupport-Pilot60` 两套独立盲审的一致性与旧标签冲突率。门禁通过前，不扩展 Development 证据标签，也不启动自动答案修正、补证、拒答或阈值扫描。

### 8.88 EvidenceSupport-Pilot60 双盲证据标签门禁（2026-07-16）

| 字段 | 内容 |
|---|---|
| 盲审数据 | 60条；问题、声明、ASR和32帧联系表；不含参考答案或旧标签 |
| 评审完成 | Review A/B 均 `60/60`，manifest 顺序和字段审计通过 |
| 总体一致率 | `93.33%` |
| Cohen's Kappa | `0.7193` |
| 分类型一致率 | Type_1 `86.67%`；Type_2 `100.00%`；Type_3 `92.31%`；Type_4 `91.67%`；Type_5 `100.00%` |
| 旧语义标签冲突率 | Review A `60.00%`；Review B `53.33%`；仅作描述性冲突，不把旧标签当真值 |
| 门禁 | `passed=true`；agreement≥0.80、kappa≥0.60 |
| 审计 | `evidence_support_pilot60_v1/pilot60_interrater_audit_v1.json`，已同步远端 |

该门禁只证明证据标注协议达到可用一致性，不证明创新点二提高 QA。门禁通过后已启动全量 `EvidenceSupport-Development244` 盲审包；该包不按旧标签抽样，远端 `development_audit_v1.json` 显示 `244/244` 且无答案/旧标签泄漏。两位评审完成后，才用独立视频证据标签重新训练/校准并对 Development 执行一次冻结评价。

### 8.89 Evidence-300 同预算缺失基线启动（2026-07-17）

| 字段 | 内容 |
|---|---|
| CLIP方法 | `clip_singlepeak`，作为 CLIP Top-K32 常规选帧 baseline |
| 远端路径 | `evaluation/runs/innovation1_evidence300_stage_v1/formal_clip_singlepeak_v1/` |
| 固定协议 | Qwen3-VL-8B；32视图；11,664视觉Token；同 Prompt；RAG/反思关闭；二次采样关闭 |
| GPU | GPU4；你的 `agentskill-gpu4-reservation` 保活进程保留不动 |
| 当前进度 | 约 `170/300`，errors=`0`；最终 summary 尚未生成 |
| 后续自动任务 | `watch_clip_then_adslot_v1.sh`；CLIP完成且summary通过后启动冻结 `adslot_fixed`，不覆盖旧结果 |

这两组结果完成前不运行裁判、不填写正式 QA 指标；完成后先做逐题视觉协议和输入对齐审计，再与 Raw/MMR 使用同一裁判和10,000次配对 Bootstrap。

## RealClaim-300 真实声明级验证（2026-07-16）

> **状态：协议错误历史结果，禁止进入论文主表。** v1 全部300个问题误用 processor槽位 `[0..31]` 作为原视频帧号，并且参考答案语义标签与视频证据支持任务口径不同。下表仅供追溯，已由 `innovation2_realclaim300_v2_corrected_frames` 修复实验取代。

| 项目 | 内容 |
|---|---|
| 数据 | Evidence-300 Raw32 真实模型答案拆分的 1469 条原子声明 |
| 划分 | 视频隔离 Train/Calibration/Development = 200/50/50 问题；声明 = 985/240/244 |
| 标签 | supported 938，contradicted 24，unsupported 507 |
| 推理完成 | Qwen 视觉 1469/1469；text-only 1469/1469；两者 errors=0 |
| 评测 | 10000 次 question-cluster bootstrap；无 Development 调参 |
| Development 主结果 | Qwen AUROC 0.5510；text-only 0.5457；v2.2 0.3913；v2.3 0.5998 |
| 视觉增益 | 0.0053；bootstrap 95% CI [-0.1002, 0.1107] |
| v2.3 高置信错误精度 | 46.11%，question bootstrap CI [36.22%,55.78%] |
| 门禁 | `development_gates_passed=false` |
| 最终决策 | 停止自动答案修正；创新点二冻结为声明级证据验证、证据依赖分析与反事实失配审计 |
| 结果文件 | `evaluation/runs/innovation2_realclaim300_v1/realclaim_metrics_v1.json` |

RealClaim-300 的数据、视频隔离、输入和两阶段推理协议审计均通过，但所有正式自动纠错门槛均未通过。该实验只能支持声明级验证/风险分析贡献，不能写成最终 QA 准确率提升。

**RealClaim-300 哈希：** claims `a3051349709951861efd23c133bc05aca991e6144eef6e4e2cd94b710f6cfb60`；inference inputs `170f138093bbd5124cc0679ca033e9609001be6158523b0f2c95ae6b433bc125`；Qwen visual scores `9fbd34549b2b048d565be9e8a97e72938bbf0a9a5545a30fcfa260dce0e46605`；text-only scores `ee1442e645fb5d68096f41ccafcd357d6da643e4757e14759ab2ce5371b3e225`；逐声明预测 `586ff84f56cd3d6e5c80f245f46fc0f8d3ed2fd45a9395a72a74caad0fe8f6c0`；最终指标 `1575b680280081e6b5dd5af4b0b1bc19329e671c70ab7b867f19d9b1599b6e5a`。

## RealClaim-300 诊断分析（2026-07-16）

> **状态：随 v1 一并失效。** 下列校准与风险数值基于错误视频帧和错位标签，只能作为错误排查记录，不可用于论文结论。

| 指标 | Qwen视觉 | text-only | v2.2统计 | v2.3轻量 |
|---|---:|---:|---:|---:|
| Development错误率 | 49.59% | 43.44% | 53.28% | 56.97% |
| Brier | 0.4690 | 0.3936 | 0.2736 | 0.4529 |
| ECE | 0.4729 | 0.3801 | 0.1602 | 0.4641 |
| confidence>=0.70 coverage / risk | 93.85% / 48.91% | 91.80% / 42.86% | 11.89% / 51.72% | 93.85% / 57.21% |
| confidence>=0.90 coverage / risk | 87.70% / 49.53% | 80.74% / 41.62% | 无 / 无 | 61.48% / 52.00% |

v2.3 的 Development 支持类错误为 `139/142`，unsupported 和 contradicted 均没有错误，说明分数发生了明显的“不支持”塌缩；它不具备安全自动切换所需的风险排序能力。v2.3 的 primary type 错误率依次为 Type_1=`50.00%`、Type_2=`63.46%`、Type_3=`54.90%`、Type_4=`60.00%`、Type_5=`55.81%`；声明类型中 inference=`71.54%`、visual=`46.75%`。Development 的 `ocr_present` 全部为 false，OCR 子组不作结论。

**诊断产物：** 远端 `evaluation/runs/innovation2_realclaim300_v1/diagnostics_v1/`，包括 `realclaim_diagnostic_analysis_v1.json`、`.md`、`realclaim_casebook_v1.md` 以及 `figures/` 下的校准、风险—覆盖和 primary type 错误图。诊断 JSON SHA256=`0d3147056037bc51b9c7f7c65b35aeb37edbb1ad83717955027d0780c1cd754a`；Markdown SHA256=`8db1ce8b97771bc601632b80ebf7b54db5d1052eda362842db62887ac0be421d`；casebook SHA256=`78bece731d49b7487a0760d443efac217124cda1395e508f063f0f6ae704f6ec`。

## RealClaim-300 v2 源帧修复与证据标签 Pilot（2026-07-16，运行中）

| 项目 | 内容 |
|---|---|
| v1错误范围 | 300/300问题；stored `[0..31]` 与真实 `visual_plan.frame_index` 不一致 |
| 修复目录 | `evaluation/runs/innovation2_realclaim300_v2_corrected_frames/` |
| 数据保持 | 300问题、1469声明、Train/Calibration/Development=200/50/50，旧标签与文本不变 |
| 源帧审计 | `realclaim_input_audit_v2.json`，passed=true，逐题与visual_plan精确一致 |
| 修复claims哈希 | `3a36042121fa72abcacfae2a32521745f9b458d84a96bebfeafaed5931e2dc76` |
| 修复inference哈希 | `bf17d87b26d480e675b19c0845649acdfa18eee48c9eadfa2ef3bbce9455e8aa` |
| 正确Raw32视觉重跑 | GPU4，`qwen_visual_corrected_v2/`，1469条运行中 |
| EvidenceSupport-Pilot60 | `evidence_support_pilot60_v1/`；60条盲审联系表，旧标签配额28 supported/28 unsupported/4 contradicted |
| 盲审防泄漏 | 不含reference_answer或旧label；只含问题、声明、ASR、32帧联系表 |
| Pilot manifest哈希 | `ce37b61cc30b20804b2bd2b685d19b5e920c964775076d421e7257c58de02e75` |

正式结论暂缓：修复版视觉评分完成后先报告协议诊断；只有 EvidenceSupport-Pilot60 的独立标注一致性通过，才能扩展证据级标签并重新判断创新点二。
### 8.90 Evidence-300 五组公平主表流水线（2026-07-17）

| 项目 | 状态 |
|---|---|
| 公平主表方法 | Raw Uniform32、MMR32、CLIP Top-K32、adslot_fixed、VideoITG-32 |
| VideoITG 实现 | 官方本地 `VideoITG-8B`；64候选→32选帧；同底座 Qwen3-VL-8B 回答 |
| VideoITG 运行入口 | `evaluation/scripts/watch_evidence300_videoitg_v1.sh` |
| VideoITG 门禁 | 缓存完整性、视频源匹配、时间顺序、实际消费帧精确对齐、32视图/11,664 Token/二次采样关闭 |
| 统一后处理 | `evaluation/scripts/watch_evidence300_main_postprocess_v1.sh`；五组均通过视觉审计后才调用同一 DeepSeek full-response 裁判 |
| 统计口径 | Strict、Relaxed、逐题胜平负、10,000次配对 Bootstrap；不拼接不同测试集 |
| 当前状态 | CLIP运行中（约170/300，errors=0）；adslot和VideoITG等待GPU4；Development244 Review A完成244条，Review B未完成 |

VideoITG 标记为外部强基线，MMR32 标记为本文中间版本；任何一组视觉审计或缓存对齐失败都阻止正式裁判，旧参考答案语义标签不进入证据金标签。

## 8.91 Development244 证据标签与修正版视觉分数评价（2026-07-17）

| 字段 | 内容 |
|---|---|
| 数据 | RealClaim-300 v2 corrected frames 的 Development244 声明 |
| 双盲完成 | Review A/B 均 `244/244`；manifest、字段顺序和防泄漏审计通过 |
| 一致性门禁 | agreement=`93.8525%`；Cohen's Kappa=`0.6834`；`passed=true` |
| 标签计数 | A=`supported/refuted/insufficient=219/1/24`；B=`216/0/28` |
| 主评价样本 | 共识 `229`；分歧 `15`，分歧不进入主指标 |
| 修正版视觉分数 | AUROC=`0.6655`；AUPRC=`0.9525`；三分类准确率=`85.59%` |
| Bootstrap | 问题级10,000次；AUROC 95% CI=`[0.5288,0.8299]` |
| 旧标签冲突 | Review A=`43.44%`；Review B=`44.26%`；仅作诊断 |
| 评价边界 | 证明一定的声明—证据分数对齐；不证明 QA 提升或自动纠错可用 |
| 远端审计 | `evaluation/runs/innovation2_realclaim300_v2_corrected_frames/evidence_support_development244_v1/development244_interrater_audit_v1.json` |
| 远端评价 | `evaluation/runs/innovation2_realclaim300_v2_corrected_frames/evidence_support_development244_v1/development244_evaluation_v1.json` |
| 评分子集 | `development244_scores_v1.jsonl`，由 `1469` 条全集按 blind manifest 精确过滤为 `244` 条 |
| 本地产物哈希 | audit `5434da18b348fbabe082c36bb6a2b3baaacfb66b2a99369d91d50ea24278c9b7`；evaluation `c5205dbf2cb68495843ed03dc7bd1931aabf3df7f7489364549cb5ed16e7ef24` |

本轮只完成独立证据标签门禁和一次 Development 冻结评价，没有进行答案自动修正、拒答、补证或阈值扫描。后续实验仍以 Evidence-300 五组同预算主表为优先；任何训练/校准只能使用 Train/Calibration，不能使用 Development 反向调参。

（历史状态，已由 8.92 更新）CLIP Top-K32 当时在 GPU4 运行至 `218/300`、errors=`0`；你的 GPU4 保留进程 `PID 671014` 继续保留，不终止、不计入实验异常。

### 8.92 Evidence-300 CLIP Top-K32 正式组完成（2026-07-17）

| 字段 | 内容 |
|---|---|
| 方法 | CLIP Top-K32（正式单峰版本） |
| 推理状态 | `300/300`，errors=`0` |
| 模型与预算 | Qwen3-VL-8B；32 个实际视图；11,664 视觉 Token |
| 公平协议 | 同 Prompt；RAG/反思关闭；二次采样关闭 |
| 视觉审计 | `visual_protocol_audit_v1.json`，`passed=true` |
| 统一裁判 | 尚未运行，待五组视觉审计全部通过后统一执行 |
| 远端目录 | `evaluation/runs/innovation1_evidence300_stage_v1/formal_clip_singlepeak_v1/` |
| run summary SHA256 | `1b9c6a5bea1ceec4b345171a33295fe3475fa9a7432d421dec4d3c0f8ad5c8cc` |
| visual audit SHA256 | `eac75a63aebcf6ed393171e4d2a25fb377cae2b32a12706f2c9ded9ceb09eb82` |

CLIP 完成后 watcher 已启动 `adslot_fixed`；VideoITG-32 等待 GPU4 释放。GPU4 的用户保留 PID `671014` 不属于实验进程，不得终止。

### 8.93 VideoITG-32 GPU1 并行启动（2026-07-17）

| 字段 | 内容 |
|---|---|
| 启动方式 | 独立 GPU1 并行 watcher，跳过 adslot 完成等待 |
| GPU1 启动前状态 | 约 13 MiB 显存、利用率 0%、无计算进程 |
| 当前阶段 | VideoITG 64-to-32 缓存模型加载中，尚无 summary 或缓存审计结果 |
| GPU4 并行任务 | `adslot_fixed` 继续独立运行，记录时约 `40/300` |
| 脚本 | `evaluation/scripts/watch_evidence300_videoitg_gpu1_parallel_v1.sh` |
| 模型路径 | `<REMOTE_PROJECT_ROOT>/models/VideoITG-8B`；`<REMOTE_PROJECT_ROOT>/models/siglip-so400m-patch14-384` |
| 脚本 SHA256 | `61bbf0e8f5524396f39118436ce57d94bbc43f99816eeda6eb77307a724ae5cd` |

原 GPU4 等待 watcher 是本人的旧等待进程，已停止，避免 adslot 完成后重复启动 VideoITG。正式裁判仍须等待所有方法的视觉协议和缓存对齐审计通过。

设备映射复核：最小测试确认 `CUDA_VISIBLE_DEVICES=1` 的实际计算落在物理 GPU1；并行脚本现已对缓存和 Qwen 子进程显式设置 `CUDA_VISIBLE_DEVICES="$GPU_ID"`。最新脚本 SHA256=`312620249dd09783972a4292f21432c408f6b24875bdd10712e9d2946562ecd8`，GPU2 未出现本实验 PID。

### 8.94 VideoITG GPU1 缓存进入推理（2026-07-17）

| 字段 | 内容 |
|---|---|
| GPU1 状态 | VideoITG 缓存 PID `2641478`，约 19.5 GiB，利用率 100% |
| 缓存进度 | `cache_shard0.jsonl` 当前 `11` 条，尚未完成 |
| GPU2 审计 | 仅有原有他人 PID `290389`，本实验 PID 不在 GPU2 |
| GPU4 状态 | `adslot_fixed` 记录时约 `59/300` |
| 后续门禁 | 缓存完整性、视觉协议、缓存—实际消费帧对齐全部通过后才可统一裁判 |

该缓存与后续 Qwen 回答仍沿用固定的 64 候选、32 选帧、32 视图和 11,664 视觉 Token 协议。

进度更新：`cache_shard0.jsonl` 已产出 `24/300`；GPU1 缓存 PID `2641478` 仍在运行，GPU2 仅有他人 PID `290389`，GPU4 `adslot_fixed` 约 `61/300`。尚未生成缓存 summary 或正式裁判结果。

进度复核（2026-07-17 02:05）：VideoITG GPU1 缓存 `68/300`，GPU4 `adslot_fixed` `68/300`，均保持运行；GPU1 当前非空闲，未启动叠加任务。GPU2 仅保留他人进程，未干扰。正式裁判仍未启动。

再次复核（2026-07-17 02:06）：VideoITG 缓存 `80/300`，GPU1 仍由其进程占用约 `19.5 GiB`；GPU4 `adslot_fixed` `70/300`。GPU1 瞬时利用率为 0% 但进程未退出，不能复用；正式裁判仍未启动。

进度复核（2026-07-17 02:07）：VideoITG 缓存 `93/300`，GPU4 `adslot_fixed` `72/300`，均正常运行；尚无完成 summary 或协议审计，正式裁判未启动。

进度复核（2026-07-17 02:07）：VideoITG 缓存 `102/300`，GPU4 `adslot_fixed` `74/300`；GPU1 进程仍占用约 `19.5 GiB`，尚未生成完成审计，正式裁判未启动。

进度复核（2026-07-17 02:08）：VideoITG 缓存 `113/300`，GPU4 `adslot_fixed` `76/300`；两组均在运行，尚无 VideoITG 审计或 ready 标记，正式裁判未启动。

进度复核（2026-07-17 02:09）：VideoITG 缓存 `126/300`，GPU4 `adslot_fixed` `78/300`；日志持续产出选帧记录，未见错误，正式裁判未启动。

进度复核（2026-07-17 02:09）：VideoITG 缓存 `136/300`，GPU4 `adslot_fixed` `80/300`；尚无 VideoITG ready 文件，继续等待 watcher 的完整审计链路。

进度复核（2026-07-17 02:10）：VideoITG 缓存 `146/300`，GPU4 `adslot_fixed` `81/300`；缓存目录尚无 summary、audit 或 ready 文件，正式裁判未启动。

进度复核（2026-07-17 02:11）：VideoITG 缓存 `156/300`，GPU4 `adslot_fixed` `83/300`；缓存未完成，正式审计、回答器和裁判均未启动。

进度复核（2026-07-17 02:11）：VideoITG 缓存 `164/300`，GPU4 `adslot_fixed` `84/300`；GPU1 未释放，缓存审计文件尚未出现，正式裁判未启动。

进度复核（2026-07-17 02:12）：VideoITG 缓存 `172/300`，GPU4 `adslot_fixed` `86/300`；GPU1 仍在高利用率推理，缓存审计未生成，正式裁判未启动。

进度复核（2026-07-17 02:13）：VideoITG 缓存 `181/300`，GPU4 `adslot_fixed` `87/300`；日志持续增长，尚无完成或审计产物，正式裁判未启动。

进度复核（2026-07-17 02:13）：VideoITG 缓存 `190/300`，GPU4 `adslot_fixed` `89/300`；两组仍在运行，缓存未完成，正式裁判未启动。

进度复核（2026-07-17 02:14）：VideoITG 缓存 `200/300`，GPU4 `adslot_fixed` `91/300`；尚无审计或 ready 文件，正式裁判未启动。

进度复核（2026-07-17 02:14）：VideoITG 缓存 `209/300`，GPU4 `adslot_fixed` `92/300`；两个任务正常推进，尚无审计或 ready 文件。

进度复核（2026-07-17 02:15）：VideoITG 缓存 `217/300`，GPU4 `adslot_fixed` `94/300`；GPU1 未释放，缓存审计和 ready 文件尚未生成。

进度复核（2026-07-17 02:16）：VideoITG 缓存 `227/300`，GPU4 `adslot_fixed` `95/300`；两组仍正常产出，尚无审计或 ready 文件。

进度复核（2026-07-17 02:16）：VideoITG 缓存 `236/300`，GPU4 `adslot_fixed` `97/300`；GPU1 未释放，缓存审计尚未启动。

进度复核（2026-07-17 02:17）：VideoITG 缓存 `243/300`，GPU4 `adslot_fixed` `99/300`；GPU1 未释放，缓存审计尚未出现，正式裁判未启动。

进度复核（2026-07-17 02:18）：VideoITG 缓存 `254/300`，GPU4 `adslot_fixed` `100/300`；缓存审计和 ready 文件尚未出现，正式裁判未启动。

进度复核（2026-07-17 02:18）：VideoITG 缓存 `265/300`，GPU4 `adslot_fixed` `102/300`；缓存尚未完成，正式审计和裁判未启动。

进度复核（2026-07-17 02:19）：VideoITG 缓存 `275/300`，GPU4 `adslot_fixed` `104/300`；缓存尚未完成，正式审计和裁判未启动。

进度复核（2026-07-17 02:19）：VideoITG 缓存 `283/300`，GPU4 `adslot_fixed` `105/300`；VideoITG 进入收尾但尚未完成，正式审计和裁判未启动。

进度复核（2026-07-17 02:20）：VideoITG 缓存 `292/300`，GPU4 `adslot_fixed` `107/300`；VideoITG 尚余 8 条，正式审计和裁判未启动。

### 8.95 VideoITG 缓存完成、审计通过与 Qwen 阶段修复

VideoITG 缓存已完成 `300/300`，`audit_temporal_cache_v1.json` 通过：64 候选、32 选帧、视频源匹配 `300/300`、平均唯一源帧数 `32.0`。首次 Qwen 阶段因 watcher 全局注入 VideoITG 专用旧 Transformers，无法识别 `qwen3_vl` 而失败；缓存产物未被覆盖。

已修复为仅缓存构建使用 VideoITG 依赖，Qwen3-VL 推理和后续审计清除该 `PYTHONPATH`。修正版脚本 SHA256=`d545aca3b2711360fa66d304ebd759da69c9cfa2a4ca42d9cbc5b93d72befa2e`。GPU1 已重启 Qwen3-VL-8B 回答器 PID `3002499`，日志确认已读取 `300` 条缓存；GPU4 adslot_fixed 保持运行。当前尚未进入统一裁判。

进度复核（2026-07-17 02:25）：GPU1 VideoITG-Qwen 已进入真实推理，约 `20.8 GiB`、利用率约 `96%`；GPU4 adslot_fixed 约 `120/300`。GPU1 保留给 VideoITG 外部强基线，不重复启动 adslot。

进度复核（2026-07-17 02:26）：GPU1 VideoITG-Qwen 仍在初始化/推理，约 `20.8 GiB`、利用率约 `93%`，尚无逐题 JSONL；GPU4 adslot_fixed 约 `123/300`，正式裁判未启动。

进度复核（2026-07-17 02:27）：GPU1 VideoITG-Qwen 已写出 `7` 个 `evidence.json`，显存约 `20.8 GiB`、利用率约 `97%`；GPU4 adslot_fixed 约 `125/300`，正式裁判未启动。

进度复核（2026-07-17 02:28）：GPU1 VideoITG-Qwen 已写出 `9` 个 `evidence.json`，显存约 `20.8 GiB`、利用率约 `97%`；GPU4 adslot_fixed 约 `127/300`，未见错误。

进度复核（2026-07-17 02:29）：GPU1 VideoITG-Qwen 已处理 `10/300`、错误 `0`，结果目录有 `13` 个证据文件；GPU4 adslot_fixed 约 `129/300`，正式裁判未启动。

进度复核（2026-07-17 02:30）：GPU1 VideoITG-Qwen 结果文件 `15` 个，最新日志统计已处理 `10/300`、错误 `0`；GPU4 adslot_fixed 约 `131/300`，正式裁判未启动。

进度复核（2026-07-17 02:30）：GPU1 VideoITG-Qwen 结果文件 `17` 个，GPU4 adslot_fixed 约 `133/300`；最新日志统计尚未刷新，未见错误记录。

进度复核（2026-07-17 02:31）：GPU1 VideoITG-Qwen 结果文件 `19` 个，显存约 `17.4 GiB`、利用率约 `97%`；GPU4 adslot_fixed 约 `134/300`。回答器进程仍活跃。

进度复核（2026-07-17 02:32）：GPU1 VideoITG-Qwen 已处理 `20/300`、错误 `0`，结果文件 `20` 个；GPU4 adslot_fixed 约 `136/300`，两组运行正常。

进度复核（2026-07-17 02:32）：GPU1 VideoITG-Qwen 结果文件 `22` 个，最新完整统计 `20/300`、错误 `0`；GPU4 adslot_fixed 约 `138/300`，正式裁判未启动。

进度复核（2026-07-17 02:36）：短周期复核确认 GPU1 VideoITG-Qwen 结果文件由 `32` 增至 `34`，进程正常推进且未见错误；GPU4 adslot_fixed 由 `145` 推进至 `147/300`。GPU1 瞬时利用率波动到 `0` 后恢复，未启动重复 adslot。

进度复核（2026-07-17 02:37）：GPU1 VideoITG-Qwen 结果文件增至 `37`，最新日志未见错误；GPU4 adslot_fixed 至 `149/300`。两组尚未生成最终视觉/对齐审计标记，正式裁判未启动，也未启动重复 adslot。

进度复核（2026-07-17 02:38）：GPU1 VideoITG-Qwen 已处理 `40/300`、错误 `0`，结果文件 `43` 个；GPU4 adslot_fixed 至 `153/300`。主后处理 watcher 仍等待两组完成，正式裁判未启动。

进度复核（2026-07-17 02:40）：GPU1 VideoITG-Qwen 结果文件增至 `46` 个，最新完整日志仍为 `40/300`、错误 `0`；GPU4 adslot_fixed 至 `156/300`。主后处理 watcher 继续等待，正式裁判未启动。

门禁复核（2026-07-17 02:41）：远端确认 RealClaim-300 修正版 `1469/1469`、errors=`0`、complete=`true`、protocol_passed=`true`，视觉协议审计通过；实际为 32 个视图、11664 个视觉 Token，二次采样关闭。GPU2/3/5 有其他用户进程，未干扰。

进度复核（2026-07-17 02:42）：GPU1 VideoITG-Qwen 已处理 `50/300`、错误 `0`，结果文件 `52` 个；GPU4 adslot_fixed 至 `160/300`。两组持续产出，主后处理 watcher 未提前启动裁判。

进度复核（2026-07-17 02:43）：GPU1 VideoITG-Qwen 结果文件增至 `54` 个，最新完整日志为 `50/300`、错误 `0`；GPU4 adslot_fixed 至 `162/300`。未见异常或审计标记，watcher 继续等待。

进度复核（2026-07-17 02:44）：GPU1 VideoITG-Qwen 结果文件增至 `56` 个，最新完整日志仍为 `50/300`、错误 `0`；GPU4 adslot_fixed 至 `164/300`。GPU4 瞬时利用率为 `0` 但进程仍活跃，正式裁判未启动。

进度复核（2026-07-17 02:45）：GPU1 VideoITG-Qwen 已处理 `60/300`、错误 `0`，结果文件 `60` 个；GPU4 adslot_fixed 至 `167/300`。主 watcher 仍等待两组完成，尚未生成审计或裁判结果。

进度复核（2026-07-17 02:46）：GPU1 VideoITG-Qwen 结果文件增至 `63` 个，最新完整日志仍为 `60/300`、错误 `0`；GPU4 adslot_fixed 至 `169/300`。两组进程活跃，主 watcher 仍等待。

进度复核（2026-07-17 02:47）：GPU1 VideoITG-Qwen 结果文件增至 `64` 个，最新完整日志仍为 `60/300`、错误 `0`；GPU4 adslot_fixed 至 `171/300`。尚无完成标记或审计产物，主 watcher 正常等待。

进度复核（2026-07-17 02:48）：GPU1 VideoITG-Qwen 结果文件增至 `66` 个，最新完整日志仍为 `60/300`、错误 `0`；GPU4 adslot_fixed 至 `172/300`。主 watcher 仍等待两组完成，未触发审计或裁判。

进度复核（2026-07-17 02:48）：GPU1 VideoITG-Qwen 已处理 `70/300`、错误 `0`，结果文件 `70` 个；GPU4 adslot_fixed 至 `175/300`。主 watcher 仍等待两组完成，正式审计和裁判未启动。

进度复核（2026-07-17 02:49）：GPU1 VideoITG-Qwen 结果文件增至 `73` 个，最新完整日志仍为 `70/300`、错误 `0`；GPU4 adslot_fixed 至 `177/300`。两组继续计算，主 watcher 未提前启动后处理。

进度复核（2026-07-17 02:50）：GPU1 VideoITG-Qwen 结果文件增至 `76` 个，最新完整日志仍为 `70/300`、错误 `0`；GPU4 adslot_fixed 至 `180/300`。两组持续计算，主 watcher 仍等待，未提前启动后处理。

进度复核（2026-07-17 02:51）：GPU1 VideoITG-Qwen 结果文件增至 `79` 个，进程活跃且持续写入；GPU4 adslot_fixed 至 `182/300`、利用率 `100%`。GPU1 瞬时利用率为 `0` 但无停滞证据，未重启或叠加任务。

进度复核（2026-07-17 02:52）：GPU1 VideoITG-Qwen 已处理 `80/300`、错误 `0`，结果文件 `81` 个；GPU4 adslot_fixed 至 `184/300`、利用率 `100%`。主 watcher 仍等待，未提前后处理。

进度复核（2026-07-17 02:53）：GPU1 VideoITG-Qwen 结果文件增至 `83` 个，最新完整日志仍为 `80/300`、错误 `0`；GPU4 adslot_fixed 至 `185/300`。两组由原进程正常推进，主 watcher 未提前启动后处理。

进度复核（2026-07-17 02:54）：短周期确认 GPU1 VideoITG-Qwen 结果文件由 `83` 增至 `87`，进程仍活跃且无新增错误；GPU4 adslot_fixed 由 `185` 至 `189/300`。GPU1 瞬时利用率为 `0` 但文件持续增加，未重启。

进度复核（2026-07-17 02:55）：GPU1 VideoITG-Qwen 结果文件增至 `89` 个，最新完整日志仍为 `80/300`、错误 `0`；GPU4 adslot_fixed 至 `191/300`。GPU4 瞬时利用率为 `16%` 但进程和断点仍增长，正式任务未重启或复用。

进度复核（2026-07-17 02:56）：GPU1 VideoITG-Qwen 已处理 `90/300`、错误 `0`，结果文件 `91` 个；GPU4 adslot_fixed 至 `193/300`。两组进程和利用率正常，主 watcher 仍等待。

进度复核（2026-07-17 02:57）：GPU1 VideoITG-Qwen 结果文件增至 `94` 个，最新完整日志为 `90/300`、错误 `0`；GPU4 adslot_fixed 至 `195/300`。主 watcher 仍等待，未提前启动审计或裁判。

进度复核（2026-07-17 02:58）：GPU1 VideoITG-Qwen 结果文件增至 `96` 个，最新完整日志仍为 `90/300`、错误 `0`；GPU4 adslot_fixed 至 `196/300`。两组进程均活跃，主 watcher 继续等待。

进度复核（2026-07-17 02:59）：GPU1 VideoITG-Qwen 结果文件增至 `98` 个，最新完整日志仍为 `90/300`、错误 `0`；GPU4 adslot_fixed 至 `198/300`。主 watcher 继续等待，未提前进入审计或裁判。

进度复核（2026-07-17 02:58）：GPU1 VideoITG-Qwen 已处理 `100/300`、错误 `0`，结果文件 `100` 个；GPU4 adslot_fixed 至 `200/300`。两组正常运行，主 watcher 仍等待完整结果。

进度复核（2026-07-17 02:59）：GPU1 VideoITG-Qwen 结果文件增至 `103` 个，最新完整日志为 `100/300`、错误 `0`；GPU4 adslot_fixed 至 `201/300`。两组正常运行，主 watcher 仍等待。

进度复核（2026-07-17 03:00）：GPU1 VideoITG-Qwen 结果文件增至 `105` 个，最新完整日志仍为 `100/300`、错误 `0`；GPU4 adslot_fixed 至 `203/300`。尚无完成标记，主 watcher 继续等待。

进度复核（2026-07-17 03:01）：GPU1 VideoITG-Qwen 结果文件增至 `107` 个，最新完整日志仍为 `100/300`、错误 `0`；GPU4 adslot_fixed 至 `205/300`。两组仍活跃，主 watcher 继续等待。

进度复核（2026-07-17 03:02）：GPU1 VideoITG-Qwen 已处理 `110/300`、错误 `0`，结果文件 `110` 个；GPU4 adslot_fixed 至 `207/300`。两组正常运行，主 watcher 继续等待。

进度复核（2026-07-17 03:03）：GPU1 VideoITG-Qwen 结果文件增至 `113` 个，最新完整日志为 `110/300`、错误 `0`；GPU4 adslot_fixed 至 `209/300`。GPU1 瞬时利用率为 `0` 但进程和文件持续推进，未重启。

并行调度复核（2026-07-17 03:06）：GPU1 在 VideoITG-Qwen 运行期间追加启动 adslot_fixed `start_idx=220,end_idx=300`，输出目录为 `evaluation/runs/innovation1_evidence300_stage_v1/formal_adslot_fixed_v1_gpu1_tail`；GPU4 主结果目录保持不变。GPU1 双模型加载后约使用 `42.1/49.1 GiB`，尾段已进入 `0/80`，未见 OOM。GPU1 尾段属于加速副本，只有与主目录按题目 ID 精确合并并通过全量视觉协议审计后，才可进入正式 adslot 结果。

进度复核（2026-07-17 03:08）：GPU1 adslot 尾段完成 `2/80`，未见错误；VideoITG-Qwen 仍在同卡运行。双模型并行时显存约 `43.3/49.1 GiB`，尾段暂按加速副本管理，不进入正式主表。

进度复核（2026-07-17 03:09）：GPU4 主 adslot_fixed 已处理 `230/300`，VideoITG-Qwen 已处理 `130/300`，两者日志错误均为 `0`；GPU1 双模型显存约 `39.6/49.1 GiB`。GPU1 尾段仍运行，日志暂未刷新新统计，尚不计入正式结果。

进度复核（2026-07-17 03:11）：GPU1 尾段目录已落盘约 `8` 条结果，GPU1 显存约 `43.4/49.1 GiB`，无 OOM。已核对主后处理脚本：五路视觉审计与统一裁判仅使用主目录 `formal_adslot_fixed_v1`，尾段目录不会自动进入正式主表。

进度复核（2026-07-17 03:12）：GPU1 尾段独立目录约 `9` 条结果；GPU4 主 adslot 和 VideoITG 的正式 summary 尚未生成，主 watcher 仍等待，尾段不计入正式主表。

进度复核（2026-07-17 03:13）：GPU1 adslot 尾段已处理 `10/80`、错误 `0`；GPU4 主 adslot 与 VideoITG 正式 summary 仍未生成，主 watcher 继续等待。

进度复核（2026-07-17 03:14）：VideoITG-Qwen 已处理 `140/300`、错误 `0`；GPU4 主 adslot 最近统计 `230/300`、错误 `0`，进程仍活跃；GPU1 adslot 尾段 `10/80`，暂不计入正式主表。

进度复核（2026-07-17 03:15）：GPU4 主 adslot_fixed 已处理 `240/300`、错误 `0`；VideoITG-Qwen 最近完整统计 `140/300`、错误 `0`；GPU1 尾段 `10/80`，双模型显存约 `42.3/49.1 GiB`，正式 summary 尚未生成。

进度复核（2026-07-17 03:16）：GPU4 主 adslot 与 VideoITG 正式 summary 仍未出现，最近完整进度分别为 `240/300` 和 `140/300`、错误均为 `0`；GPU1 尾段无新统计但进程仍活跃，不计入正式主表。

进度复核（2026-07-17 03:18）：GPU4 主 adslot 已处理 `250/300`、错误 `0`；VideoITG 结果目录约 `150` 条、GPU1 尾段约 `17` 条，但正式 summary 尚未生成。目录计数仅作进度参考，不替代正式 summary 和审计。

进度复核（2026-07-17 03:19）：GPU4 主 adslot 仍为 `250/300`、错误 `0`；VideoITG 与 GPU1 尾段进程活跃但正式日志尚未刷新，主 watcher 继续等待，不启动裁判。

进度复核（2026-07-17 03:20）：VideoITG-Qwen 已处理 `150/300`、错误 `0`；GPU4 主 adslot 仍为 `250/300`、错误 `0`，GPU1 尾段继续运行；正式 summary 尚未生成。

进度复核（2026-07-17 03:20）：GPU1 adslot 尾段已处理 `20/80`、错误 `0`；VideoITG 最近完整统计 `150/300`、错误 `0`；GPU4 主 adslot `250/300`、错误 `0`。尾段仍不计入正式主表。

并行调度复核（2026-07-17 03:23）：GPU1 adslot 尾段已推进至约 `24/80`、错误 `0`，GPU4 主 adslot 已推进至 `260/300`、错误 `0`。GPU1 同时保留 VideoITG-Qwen，显存约 `43.2/49.1 GiB`、利用率 `100%`；未启动新的重复实例。GPU1 尾段属于独立加速副本，暂不进入正式主表，需完成题目 ID 对齐和全量视觉协议审计后再处理。

进度复核（2026-07-17 03:24）：GPU1 VideoITG-Qwen 结果目录已落盘 `158` 条，adslot 尾段约 `26/80`；GPU4 主 adslot 已推进至 `265/300`，均未见错误。GPU1 双模型显存约 `43.3/49.1 GiB`；正式主表仍只等待 GPU4 主目录和完整 VideoITG summary，尾段不自动计入。

进度复核（2026-07-17 03:26）：GPU4 主 adslot 约 `271/300`；GPU1 VideoITG-Qwen 已处理 `160/300`、错误 `0`，GPU1 adslot 尾段约 `29/80`、错误 `0`。正式 summary 和统一审计尚未出现，尾段继续作为独立加速副本保存。

进度复核（2026-07-17 03:27）：GPU4 主 adslot 约 `274/300`，GPU1 VideoITG-Qwen `160/300`、GPU1 adslot 尾段 `30/80`，错误均为 `0`。GPU4 瞬时利用率为 `0%` 但进程和日志仍活跃，继续等待正式 summary，不提前启动后处理。

进度复核（2026-07-17 03:28）：GPU4 主 adslot 约 `276/300`，GPU1 VideoITG-Qwen `160/300`、GPU1 adslot 尾段约 `31/80`，均未见错误。正式主表仍等待两路完整 summary，尾段继续独立保存、不自动计入。

进度复核（2026-07-17 03:29）：GPU4 主 adslot 约 `278/300`，GPU1 VideoITG-Qwen `160/300`、GPU1 adslot 尾段约 `33/80`，错误均为 `0`。后处理仍等待两路正式 summary；旧 `deepseek_judge_v1/summary.json` 明确排除，不混入本轮主表。

进度复核（2026-07-17 03:30）：GPU4 主 adslot 约 `281/300`，GPU1 VideoITG-Qwen `160/300`、GPU1 adslot 尾段约 `34/80`，错误均为 `0`。正式 watcher 仍等待 VideoITG 完整 summary，不提前使用探索性结果。

进度复核（2026-07-17 03:30）：GPU4 主 adslot 约 `283/300`，GPU1 VideoITG-Qwen `160/300`、GPU1 adslot 尾段 `35/80`，未见错误。正式主表继续等待 VideoITG summary，尾段不自动计入。

进度复核（2026-07-17 03:31）：GPU4 主 adslot 约 `286/300`，GPU1 VideoITG-Qwen `160/300`、GPU1 adslot 尾段 `36/80`，无错误或 OOM。正式 summary 尚未生成，继续等待完整 VideoITG 结果。

进度复核（2026-07-17 03:32）：GPU1 VideoITG-Qwen 已处理 `170/300`、错误 `0`；GPU4 主 adslot 约 `287/300`，GPU1 adslot 尾段约 `37/80`，均无错误。正式 summary 尚未生成，尾段继续独立保存、不计入主表。

进度复核（2026-07-17 03:33）：GPU4 主 adslot `290/300`、GPU1 VideoITG-Qwen `170/300`、GPU1 adslot 尾段约 `39/80`，错误均为 `0`。正式 summary 尚未生成，继续等待两路完整结果。

进度复核（2026-07-17 03:34）：GPU4 主 adslot 约 `292/300`，GPU1 VideoITG-Qwen `170/300`、GPU1 adslot 尾段 `40/80`，错误均为 `0`。正式 summary 尚未生成，尾段继续独立保存。

进度复核（2026-07-17 03:35）：GPU4 主 adslot 约 `294/300`，GPU1 VideoITG-Qwen `170/300`、GPU1 adslot 尾段 `41/80`，均无错误。主 adslot 接近完成，正式主表仍等待 VideoITG summary。

正式结果里程碑（2026-07-17 03:39）：GPU4 `formal_adslot_fixed_v1` 已生成全量 `run_summary_gpu4_shard0.json`；冻结配置为 32 个实际视图、11,664 个视觉 Token、Qwen3-VL-8B、无 RAG/反思、关闭二次采样。GPU1 VideoITG-Qwen 已推进至 `180/300`，并行 adslot 尾段最近为 `40/80`，均无错误；统一后处理仍等待 VideoITG-32 完成，尾段副本不计入正式主表。

进度复核（2026-07-17 03:42）：日志统计刷新存在延迟，但远端 JSONL 已确认 VideoITG-Qwen 输出 `186/300`、GPU1 adslot 尾段输出 `54/80`，两路均持续写入且未见错误；正式 summary 和统一后处理仍等待全量完成，尾段副本不计入正式主表。

流程修复与进度（2026-07-17 03:49）：发现并修复两个 watcher 将 GPU1 VideoITG 误等为 `run_summary_gpu4_shard0.json` 的路径问题，远端原脚本已备份后同步修正版；新 watcher 已识别现有推理 PID 并等待续跑，没有重复启动 VideoITG。当前日志为 `196/300`，GPU1 adslot 尾段为 `65/80`，主后处理已改为兼容 GPU1/GPU4 summary。

正式结果里程碑（2026-07-17 04:00）：GPU1 adslot 辅助尾段已完成 `80/80`，错误为 0；GPU4 的正式 adslot 结果为 `300/300`。GPU1 尾段输出仅作运行核对，不并入正式主表；正式主表继续等待 GPU1 VideoITG-32 全量完成。

### Evidence-300 正式同预算主表（2026-07-17）

VideoITG-32 在 GPU1 完成 `300/300`。五方法均通过统一视觉协议审计：Qwen3-VL-8B、32 个实际视图、11,664 视觉 Token、同 Prompt/DeepSeek 裁判、无 RAG/反思、关闭二次采样。正式裁判为 full-response，配对 Bootstrap 为 10,000 次，seed=42。

| 方法 | 比较身份 | Strict | Relaxed | 1/0.5/0 | 证据单元召回* | 提交视图证据精度* | Region Recall |
|---|---|---:|---:|---:|---:|---:|---:|
| Raw Uniform32 | 基础 baseline | 64.00% | 76.17% | 192/73/35 | 100.00% | 75.05% | N/A |
| MMR32 | 本文内部中间版本 | 63.33% | 75.17% | 190/71/39 | 100.00% | 78.23% | N/A |
| CLIP Single-Peak | 常规选帧 baseline | 57.00% | 69.50% | 171/75/54 | 99.17% | 78.46% | N/A |
| AdSlot Fixed | 本文完整创新点一 | 58.00% | 70.83% | 174/77/49 | 99.72% | 78.25% | N/A |
| VideoITG-32 | 外部强选帧 baseline | 65.33% | 76.33% | 196/66/38 | 100.00% | 78.42% | N/A |

`*` 证据指标是 296 条可评估、4 条不可定位的 AI 复核时间区间代理，不是盲人工金标准；Evidence-300 没有 bbox 标注，因此 Region Recall 不可估计。VideoITG 相对 Raw 的 Relaxed 配对胜/平/负为 `39/225/36`，差值 `+0.17` 个百分点，95% CI `[-3.33,+3.00]`；Raw 相对 AdSlot 的 Relaxed 差值 `+5.33` 个百分点，95% CI `[+1.50,+9.00]`。正式 manifest、审计和证据代理清单见 `<LOCAL_RESEARCH_ROOT>/artifacts/innovation1_evidence300_formal_main_v1/`，远端正式结果根目录为 `<REMOTE_ADSQA_ROOT>/evaluation/runs/innovation1_evidence300_stage_v1/`。

正式主表的结论：VideoITG 是本集最高 QA 方法，但相对 Raw 的差异不显著；AdSlot 的证据代理精度接近其他选择器，却没有提高 QA。因此创新点一应表述为固定预算下的问题条件化视听证据定位、预算审计和证据可观察性分析，不宣称稳定准确率提升。

### 创新点二：证据精读反思 Dev100（2026-07-17）

#### 冻结设置

| 项目 | 设置 |
|---|---|
| 数据 | Counterfactual-Dev100，100 个训练视频，独立于正式测试集 |
| 输入 | Raw Uniform32；32 个实际视图；11,664 个视觉 Token |
| 模型 | Qwen3-VL-8B |
| 禁止项 | 新增帧、局部裁剪、定向补看、RAG、二次视觉采样 |
| 组别 | A 直接回答；B 普通自反思；C 结构化声明—证据精读；D 精读后的保守最小修正 |
| 裁判 | DeepSeek answer-only，旧版同口径评测协议，10,000 次 Bootstrap，seed=42 |
| 冻结清单 | `evaluation/runs/innovation2_evidence_reflection_dev100_v1/frozen_dev100_manifest_v1.json`，SHA256 `3cf7ff4a785a16b348f2146cdcb3adb4f61e3fc4a2fbd83075ad432ba13be1f3` |

#### 结果

| 方法 | Strict | Relaxed | 相对 Raw Relaxed | 配对胜/平/负 | 95% CI（百分点） |
|---|---:|---:|---:|---:|---:|
| Raw Uniform32 | 41.00% | 56.50% | - | - | - |
| Generic Reflection | 41.00% | 57.00% | +0.50 | 2/97/1 | [-1.00, +2.50] |
| Structured Read | 40.00% | 56.00% | -0.50 | 1/97/2 | [-2.50, +1.00] |
| Conservative Revision | 41.00% | 56.50% | 0.00 | 0/100/0 | [0.00, 0.00] |

逐题分析文件为远端 `evaluation/runs/innovation2_evidence_reflection_dev100_v1/reflection_analysis_v2.json`，裁判汇总为 `judge_deepseek_legacy_answer_only_v2/summary.json`，裁判来源和协议哈希为 `judge_deepseek_legacy_answer_only_v2/provenance.json`。三组视觉反思审计均 `complete=true`、`passed=true`；structured 的 3 条 768-token 截断输出按协议保留草稿，不伪造结构化解析。

#### 结论与门禁

Generic 只有 2 条部分改进、1 条部分回退；Structured 有 1 条部分改进、1 条部分回退和 1 条 correct-to-wrong；Conservative 全部保持原答案。没有一组达到稳定正向净修正，因此不启动第二阶段的反思与创新点一联合补看，也不做正式测试集上的阈值扫描。创新点二当前应记录为证据依赖诊断/可审计分析，不作为已验证的 QA 增益模块；Evidence-300 五方法正式结果继续冻结。

### Qwen2.5 同基座验证完成（2026-07-17）

远端实验根目录：`<REMOTE_ADSQA_ROOT>/evaluation/runs/qwen25_evidence300_afternoon_v1/`。

| 字段 | 内容 |
|---|---|
| 基座模型 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct` |
| 排除模型 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-7B-VL-ReAd-R`，未混入本轮 |
| 数据 | Evidence-300，题目 300 条，question SHA256 `d4b1a693c7ce52eded712f6fe78a5d6f631a1ec60828655b6896a2f754773825` |
| 公平协议 | 32 个实际视图、16,384 视觉 Token、同 Prompt/processor、无 RAG/反思/二次采样；`preprocessor_config.json` 存在，ReadR 环境 Transformers `4.57.1` |
| Raw 输出 | `formal_raw_uniform_v1`，300/300 |
| AdSlot 输出 | `formal_adslot_fixed_v1`，300/300 |
| 四方法 smoke | Raw/AdSlot 各 5 条；CLIP Top-K 3 条；VideoITG-32 3 条，均 `errors=0` |
| 已知警告 | Transformers 提示 Qwen2VL fast processor 默认行为；`do_sample=false` 时提示 `temperature` 可能被忽略；均未改变视图数、Token 数或结果状态 |
| 视觉审计 | 两组 `complete=true`、`passed=true`、`failure_count=0`；两组每条记录的全部检查项通过 |
| 模型哈希 | `qwen25_model_sha256.txt`，文件 SHA256 `6b2363d1560a2adb4f8a662876c68b883bd0068984a666659dd89add0f4830ee` |
| 评判 | DeepSeek legacy evaluator，`candidate_mode=full_response`，`deepseek-chat`/`deepseek-v4-flash`，600 条解析成功 |
| Bootstrap | 10,000 次，seed=42 |

正式结果：

| 方法 | Strict | Relaxed | 0/0.5/1 | 95% CI（Strict） | 95% CI（Relaxed） |
|---|---:|---:|---:|---:|---:|
| Raw Uniform32 | 48.33% | 61.83% | 74/81/145 | 42.67–54.00% | 57.17–66.50% |
| AdSlot Fixed | 42.67% | 58.67% | 76/96/128 | 37.00–48.33% | 54.17–63.17% |

配对结果（Raw − AdSlot）：胜/平/负 `55/206/39`，平均分差 `+3.17` 个百分点，95% CI `[-0.67,+7.00]` 个百分点。Raw 的点估计高于 AdSlot，但区间跨 0。逐题结果位于 `judge_deepseek_full_response_v1/results.jsonl`（600 行），汇总为 `summary.json`，来源与评判协议为 `provenance.json`；三者及两份审计 JSON 的 SHA256 已由远端后处理记录在 `QWEN25_POSTPROCESS_SHA256SUMS`。本轮核验到的 SHA256 为：`summary.json`=`843d2530399214da47bde8a70f61fe5ecf65badd4da809a2fe7c676e528095bf`，`results.jsonl`=`721901c19f61400530eff7437cae0f4c0efa8d276bde19c710dfb7e94ec5dc3c`，`provenance.json`=`a13b07361486a6f784e56ee35a5e4aec0bd165d133dff96fd8a37909359bfccc`，Raw/AdSlot 审计 JSON 分别为 `1bd2faf4181fd2ee5f9a7e321ee24cf0c67eea172fed5770d91d8d1440d12d08` / `206c27eee8044ac56f42d8e5037fa2945c0fb607811dd402ce1d796dc22e4e54`；汇总文件 `QWEN25_POSTPROCESS_SHA256SUMS` 的 SHA256 为 `2be2046c959e1f0277de2a993830fdac981074ffe1f63ac1eb654e4dbdee9f9f`。

与 Qwen3-VL-8B 主表的同口径数字并列如下（只作受限比较，Qwen2.5 为 16,384 Token，Qwen3 为 11,664 Token）：

| 基座 | Raw Strict/Relaxed | AdSlot Strict/Relaxed | AdSlot 相对 Raw |
|---|---:|---:|---:|
| Qwen2.5-VL-7B-Instruct | 48.33%/61.83% | 42.67%/58.67% | -5.67/-3.17 pp |
| Qwen3-VL-8B | 64.00%/76.17% | 58.00%/70.83% | -6.00/-5.33 pp |

最终实验判断：Qwen3 的强能力不是当前 AdSlot 无 QA 收益的充分解释，因为 Qwen2.5 上出现了同方向的点估计回退；当前版本更像是证据选择与生成所需冗余之间没有对齐。创新点一的正式结论应写为“在固定预算下改善证据定位可观察性，但 QA 收益不稳定”，不能写成“提升问答准确率”。本轮没有继续跑 Qwen2.5 的 CLIP/VideoITG 全量，也没有启动 NExT-GQA 全量；相关状态保持只读准备。
最终实验判断：Qwen3 的强能力不是当前 AdSlot 无 QA 收益的充分解释，因为 Qwen2.5 上出现了同方向的点估计回退；当前版本更像是证据选择与生成所需冗余之间没有对齐。创新点一的正式结论应写为“在固定预算下改善证据定位可观察性，但 QA 收益不稳定”，不能写成“提升问答准确率”。本轮只完成 Qwen2.5 的 CLIP/VideoITG smoke，未启动其全量，也没有启动 NExT-GQA 全量；相关状态保持只读准备。VideoITG 曾有一次候选帧数不一致的失败 smoke（缓存为 64、推理误设为 32），已保留原日志；修正为 `oversample_count=64` 后的 v4 smoke 为有效结果。

### NExT-GQA 只读准备审计（2026-07-17）

远端仅有 VideoITG 外部仓库的 NextQA 任务适配目录 `external/VideoITG_official_main/lmms_eval/tasks/nextqa/`，可见 OE validation/test 与 MC test 配置；`data/` 和 `models/` 下未发现对应数据、视频缓存、标注或权重。因此当前状态为“代码入口存在、数据未准备”，没有启动全量或虚构小规模结果。

### Coverage-AdSlot Dev100 修复实验（2026-07-17）

#### 实验身份与冻结配置

| 字段 | 内容 |
|---|---|
| 实验目标 | 修复 AdSlot 过度集中选帧导致的时间覆盖不足和生成冗余损失 |
| 数据 | Counterfactual-Dev100，100 条训练视频，独立于 Evidence-300 |
| 题目 SHA256 | `21841ee13bb19d408ae28fce5f2768f5581d32fcc8cd9d09d66a6601b64521a9` |
| 标注 SHA256 | `7dfef167c5e104515dfb0d32c129ec9149b8a705c1e5e06a266bf905b876d608` |
| 基座 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct` |
| 视觉协议 | 32 候选/实际视图，16,384 Token，oversample=32 |
| Coverage-AdSlot | 8 个时间区间，固定 18 global +14 local，每区间 1 个保留全局帧 |
| 禁止项 | RAG、反思、二次视觉采样、参数扫描 |
| 裁判 | DeepSeek legacy `full_response`，实际响应模型 `deepseek-v4-flash` |
| Bootstrap | 配对 10,000 次，seed=42 |

#### QA 结果

| 方法 | Strict | Relaxed | 评分计数（0/0.5/1） | 解析数 |
|---|---:|---:|---:|---:|
| Raw Uniform32 | 37.00% | 51.50% | 34/29/37 | 100/100 |
| AdSlot Fixed | 33.00% | 47.50% | 38/29/33 | 100/100 |
| Coverage-AdSlot | 35.00% | 50.50% | 34/31/35 | 100/100 |

配对结果：

| 对比 | 胜/平/负 | 平均分差（前者−后者） | 95% CI（百分点） |
|---|---:|---:|---:|
| Raw − AdSlot | 25/56/19 | +4.00 pp | [-4.00, +12.00] |
| Raw − Coverage | 16/69/15 | +1.00 pp | [-5.50, +7.50] |
| AdSlot − Coverage | 13/71/16 | -3.00 pp | [-9.50, +3.50] |

#### 审计与复现路径

- 三组推理均 `100/100`、`errors=0`；三组通用 Qwen2.5 视觉协议审计均 `complete=true`、`passed=true`、`failure_count=0`。
- Coverage 专项协议审计 `100/100`：每题 `global_count=18`、`local_count=14`、8 个覆盖区间均出现、8 个保留帧均存在。
- 推理结果：`evaluation/runs/innovation1_coverage_adslot_dev100_v1/{raw_uniform_qwen25,adslot_fixed_qwen25,coverage_adslot_qwen25}/`。
- 裁判结果：`evaluation/runs/innovation1_coverage_adslot_dev100_v1/judge_deepseek_qwen25_full_response_v1/`，包含逐题 `results.jsonl`、`summary.json` 和 `provenance.json`。
- 方法脚本 SHA256：`12321651b225c0d0a24167e3238479f70ca1278e118feb5c11edafd7989cb5de`。
- 裁判 `results.jsonl` / `summary.json` / `provenance.json` SHA256：`dfc103804b384ef65d8a65285c7bab61da0c328faf7ec807813ac9e09d181bda` / `fc06c328553c447775c4acfb928d4ec7b943002919202a8c3193456f1c53ac13` / `fb59a1c9d64b5519793b3234b6572dd93a90a2d1c9ba27d6c8addc6e50281939`。

#### 门禁结论

Coverage-AdSlot 相对当前 AdSlot 的点估计改善为 `+3.00 pp`，但仍低于 Raw `1.00 pp`，且 Raw−Coverage 的配对 CI 跨 0。因此“相对 AdSlot 有改善”成立，“不低于 Raw”不成立，预注册门禁失败。**不启动 Confirm-300，不把该候选写入正式主表，不继续做参数扫描。**该实验作为创新点一的探索性修复结果保存：时间覆盖和冗余保护是合理的改进方向，但在当前数据和 Qwen2.5 基座上尚未转化为稳定 QA 增益。

本地复现 manifest：`<LOCAL_RESEARCH_ROOT>/artifacts/innovation1_coverage_adslot_dev100_v1/manifest.json`。

### 创新点二 Stage-1 真实校准门禁（2026-07-17）

#### Development244 冻结基线重算

| 方法 | AUROC | AUPRC（supported） | AUPRC（negative） | Balanced Acc. | Macro-F1 | ECE | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| 修正版 Raw32 视觉 Qwen | 0.6655 | 0.9525 | 0.1718 | 0.5337 | 0.5312 | 0.1309 | 0.1237 |
| text-only Qwen | 0.5328 | 0.9339 | 0.1043 | 0.5272 | 0.4526 | 0.3491 | 0.3377 |
| 旧 v2.3 轻量验证器 | 0.4732 | 0.9270 | 0.0794 | 0.5595 | 0.1916 | 0.6557 | 0.5383 |

评测集为双盲一致的 `229/244` 条，标签为 supported=`210`、insufficient=`19`、refuted=`0`，来自50个问题簇和35个视频；15条双评审分歧不进入主指标。10,000次问题簇 Bootstrap 的 AUROC CI：视觉 `[0.5282,0.8282]`、text-only `[0.3701,0.7367]`、v2.3 `[0.3412,0.6035]`；相对视觉的 text-only 差值 CI `[-0.2783,+0.0329]`，v2.3 差值 CI `[-0.3671,-0.0438]`。

审计文件：`evaluation/runs/innovation2_realclaim300_v2_corrected_frames/evidence_support_development244_v1/development244_frozen_baselines_v1.json`。该结果只用于冻结基线，不改变 Evidence-300 QA 主表。

#### Calibration240 机器候选标签与数据边界

Calibration240 双盲联系表审计通过，240条、35个视频、无参考答案/旧标签泄漏。Qwen2.5-VL-7B-Instruct 与 Qwen3-VL-8B 两套机器评审均完成 `240/240`、错误0、解析失败0；一致率=`65.42%`、Cohen's Kappa=`0.2994`、一致样本=`157`、分歧=`83`。该结果标记为 `machine_only=true`、`not_human_gold=true`，不能用于阈值校准。

训练侧使用 v2.3 `full_pairs_train` 的受控 supported/contradicted 对：312行、156对、119个视频；与 RealClaim Calibration/Development 视频交集均为0，训练数据边界审计通过。固定分数融合候选内部留出：AUROC=`0.9229`、AUPRC=`0.9007`、配对准确率=`96.88%`；这些数字不是独立真实集结果。

远端目录：`evaluation/runs/innovation2_realclaim300_v2_corrected_frames/evidence_support_calibration240_v1/` 和 `evaluation/runs/innovation2_realclaim300_v2_corrected_frames/innovation2_stage1_score_fusion_v1/`。当前门禁：`stage1_training_allowed=true`、`stage1_calibration_allowed=false`、`development_evaluation_allowed=false`。校准完成前不得运行 Development 正式评测或自动答案切换。

人工校准输入模板已生成并通过边界审计：`evidence_support_calibration240_v1/human_calibration_templates_v1/`，A/B 各 240 条；模板 SHA256 分别为 `1d959f041f7682f1ccb8740f90b2a1c2367a2bbfcf61653ba8adeb8c1b7845e1` 和 `997d4493a8389091b5c0e03b1faebc1d62535f89a616db0d041edcec43cda5ba`。当前 `labels_filled=false`、`threshold_calibration_allowed=false`、`development_evaluation_allowed=false`。

人工标签合并器 `evaluation/tools/merge_human_calibration_labels_v1.py` 已同步远端并完成空模板回归；它不读取私有旧标签，默认门禁为 agreement>=0.80、Kappa>=0.60、负类共识>=20，门禁失败时只保存审计，不允许阈值校准或 Development 评测。

一次性阈值脚本 `evaluation/tools/calibrate_stage1_threshold_v1.py` 已同步并通过帮助命令检查；它只接受 `labels_are_human_gold=true` 的合并审计，当前没有生成冻结阈值文件。

#### Calibration240 三方机器复核分歧审计（2026-07-17）

Codex 独立盲审已完成 `240/240`。与两套已有机器复核对齐后，Codex/Qwen2.5 一致率=`55.00%`、Kappa=`0.0997`，Codex/Qwen3 一致率=`68.75%`、Kappa=`0.1996`；三方完全一致=`109/240`，至少两方一致=`236/240`。该结果只作机器间分歧诊断，不能作为人工金标签。

产物目录：`artifacts/innovation2_stage1_20260717/codex_machine_agreement_v1/`，包括两份配对审计、三方汇总、131 条机器分歧队列及其哈希报告。队列中 P0 三方完全冲突 `4` 条，P1 两方分歧 `127` 条。`calibration_gate_passed=false`、`development_evaluation_allowed=false` 保持不变；在独立人工视觉复核完成前，不冻结阈值、不运行 Development 正式评测、不进行答案自动切换。

#### Codex 独立视觉复核完成（2026-07-17）

针对上述 131 条机器分歧，Codex 已完成 P0=`4/4`、P1=`127/127` 的独立视觉复核。结果为 `supported=88`、`insufficient=41`、`refuted=2`；claim_id 集合审计为 131/131，重复 0、缺失 0、队列外 0。该批结果是 `machine_only` 诊断，所有行均标记 `not_human_gold=true`，不能直接并入人工 Calibration 标签。

汇总与哈希清单：`artifacts/innovation2_stage1_20260717/codex_adjudication_summary_v1/`，清单 SHA256=`82aa863d097f772c6a035756c63fdbfa5600606b20873015d5cd38f913d77466`。现有门禁不变：`calibration_gate_passed=false`、`development_evaluation_allowed=false`；仍不得用该批结果冻结阈值、运行 Development 正式评测或自动改写答案。

#### LLM 替代人工标注试运行（2026-07-17）

已生成完整 `Calibration240` LLM 替代标注：240 条、ID 覆盖完整，131 条为分歧复核覆盖，109 条为直接盲审结果；标签为 `supported=187`、`insufficient=51`、`refuted=2`。标注源为 `llm_substitute_for_human`，明确 `human_gold=false`、`not_human_gold=true`。

单独的探索性阈值结果为 threshold=`0.22086`、AUROC=`0.6578`、balanced accuracy=`0.6547`，文件 `artifacts/innovation2_stage1_20260717/llm_substitute_calibration_v1/llm_substitute_threshold_provisional_v1.json`。该阈值不是正式冻结阈值，`calibration_gate_passed=false`、`development_evaluation_allowed=false` 保持不变。

#### LLM-assisted Development244 探索性评测（2026-07-17）

固定 checkpoint 和 provisional threshold=`0.22086` 后，完成 Development244 探索性评测：共识样本 `229` 条，分歧 `15` 条；verifier AUROC=`0.6404`、AUPRC=`0.9445`、balanced accuracy=`0.5701`，Qwen 视觉基线 AUROC=`0.6655`。相对 Qwen 视觉的 10,000 次 Bootstrap AUROC 差值区间为 `[-0.1379, 0.0810]`，跨 0。

该结果明确标记为 `llm_assisted_exploratory`，不进入正式主表，不改变 `calibration_gate_passed=false`。远端产物为 `evaluation/runs/innovation2_realclaim300_v2_corrected_frames/llm_assisted_exploratory_v1/`，本地副本及哈希见 `artifacts/innovation2_stage1_20260717/llm_assisted_exploratory_v1/`。

### 创新点二 Stage-2 模态反事实训练数据与 Smoke20（2026-07-17）

| 项目 | 路径/结果 | 状态 |
|---|---|---|
| 初始数据构造 | `evaluation/runs/innovation2_stage2_modality_cf_v1/dataset/` | 冻结失败；视觉操作审计错误、Evidence-300 视频泄漏、模型输入元数据泄漏 |
| 修复数据构造 | `.../dataset_v2/` | CPU 审计通过；500 来源、1000 对、2000 输入，正负各1000，100 个视频 |
| 视频隔离 | `dataset_v2/audit.json` | Calibration、Development、Evidence-300 交集均为 0；Train-fit/Stage2-Dev 视频为 80/20 |
| 协议 Smoke20 v2 | `.../smoke20_v2_readr/` | 冻结失败；32 帧正确但 Token 在 2,464–11,520 间变化 |
| 协议 Smoke20 v3 | `.../smoke20_v3_fixedtoken/` | 视觉协议通过：40/40 为32帧、11,664 Token、关闭二次采样；反事实配对仅 2/20，未进入训练 |

`dataset_v2` 的标签来自训练答案派生和合成干预，所有相关 JSONL/manifest 均标记 `not_human_gold=true`。Smoke20 v3 的失败属于反事实源声明和必要性问题，不是 QA 指标，也不允许写为验证器提升或答案选举结果。冻结失败归因见远端 `evaluation/runs/innovation2_stage2_modality_cf_v1/failure_attribution_smoke20_v3.json`、`failure_attribution.md` 与 `candidate_ledger.jsonl`。

### 创新点二 Stage-2 候选 A/B 追加门禁（2026-07-18）

| 候选 | 数据与机制 | 视觉协议 | Strict 反事实方向 | 门禁结论 |
|---|---|---|---:|---|
| A：模态类型化评分 | 45 条冻结 Qwen 视觉/OCR 锚定来源；视觉/OCR声明不传入 ASR | 40/40 输入为 32 视图、11,664 Token、无二次采样 | 0/20 | 冻结失败；局部干预后事实仍在同视频其他帧出现 |
| B：同视频困难负样本 | 相同来源；负样本为锚点时间窗外的同视频完整 32 帧片段 | 40/40 输入为 32 视图、11,664 Token、无二次采样 | 8/20 | 冻结失败；12/20 负样本仍可见同一事实，不进入 50 对或训练 |

候选 A 路径：`evaluation/runs/innovation2_stage2_modality_cf_v1/candidate_A_modality_smoke20_v2/`；失败归因：`candidate_A_modality_typed_aggregation_v1/failure_attribution.json`。候选 B 路径：`candidate_B_same_video_smoke20_v1/`；失败归因：`candidate_B_same_video_hard_negative_v1/failure_attribution.json`。两者均为内部弱监督反事实 smoke，标签和来源明确 `not_human_gold=true`，不能充当人工金标准或 QA 主结果。

### 创新点二 Stage-2 候选 C/D/E 收束（2026-07-18）

| 候选 | 正式/探索性数据 | 固定视觉协议 | Strict 方向 | 决策 |
|---|---|---|---:|---|
| C：显式模态缺失闭合 | 109 来源探索性集合；ASR/OCR/视觉混合 | 40/40 为32视图、11,664 Token、无二次采样 | 14/20；ASR 7/7、OCR 4/7、视觉 3/6 | 冻结。总体由显式 ASR 缺失状态主导，不能训练跨模态验证器 |
| D：连续状态似然，旧小试 | 109 来源探索性集合 | 100/100 为32视图、11,664 Token、无二次采样 | 44/50；ASR 17/17、OCR 14/17、视觉 13/16 | 仅作机制诊断；来源不足500，不进入训练或论文正结果 |
| D：连续状态似然，正式数据 | 500 来源、1000 对、2000 输入；ASR/OCR=250/250，100视频，Train-fit/Dev=400/100 | 40/40 为32视图、11,664 Token、无二次采样 | 15/20；ASR 10/10、OCR 5/10 | 冻结。OCR 方向等于随机，禁止小试50、训练排序头和 QA 评测 |
| E：保守答案选举 | 使用 D 正式数据作无泄漏前置审计 | 不启动 Qwen 推理 | `switch_allowed=false` | 冻结。证据存在不等价于答案正确，且无独立候选答案/可信 OCR 证书 |

正式 D 数据路径：`evaluation/runs/innovation2_stage2_modality_cf_v1/candidate_D_formal_dataset_v1/`。CPU 构造审计 `audit.json` 为 500/1000/2000、外部视频交集均为0、无模型输入监督字段；`pixel_audit.json` 确认 500/500 OCR 负例至少一个目标文本框的像素变化，SHA256=`86767d606489c6b684bdac7d35695be78f3bd0e18f4441a91523da725f1cc17b`。正式 Smoke 路径为 `candidate_D_formal_smoke20_v1/`，其 `run_summary.json` SHA256=`c24291805a96edd7f180e555729befc5fae1504d1045d709f5254952d3651fd6`，`pair_results.jsonl` SHA256=`3f3884461f77956a683b4dd49aa517dd04ad7651a9f56293f4cd9dd22ce8a662`，协议审计通过。

候选 D 失败归因：`candidate_D_continuous_pairwise_ranking_v1/failure_attribution.json`；候选 E 前置门禁：`candidate_E_conservative_answer_election_v1/precondition_audit.json`；全部候选状态：`candidate_ledger.jsonl`。所有新增反事实、OCR来源和机器状态均为内部弱监督，明确 `not_human_gold=true`，不得称为人工金标准。

### A-E 后的预注册新机制

不再把“支持状态”或“局部文本遮挡”直接当作答案选择分数。下一路线为“答案条件化的因果证据校准与保守拒答”：只比较冻结 Prompt 下已有的 Raw32/MMR32 候选答案；每个答案原子命题必须先获得独立人工的时间段、文本框或 ASR span 标注，再计算答案 token 在 `E+`/外部复验的 `E-` 间的对数似然差。阈值按 ASR、OCR、视觉、联合命题分别在人工 Calibration 一次性冻结，使用共形风险控制决定接受、保持 Raw 或拒答。Development244 只允许一次评测，报告 QA、证据一致性、每模态方向、ECE/Brier、risk-coverage 和10,000次问题簇 Bootstrap。人工门禁未通过前，不启动该路线的训练、答案切换或 QA 评测。

Candidate F 的第一份人工输入已生成：`candidate_F_answer_conditioned_calibration_v1/`。它包含 A/B 两份各240行的 Raw32 候选答案—命题—证据轨迹模板和 `audit.json`。审计为 `rows=240`、Raw32预测完整、保护字段为空；模板 A/B SHA256 分别为 `c295b772887f1b43a9bc967bb6125aef68d8a4243d5bcce2848c452722a94130`、`7b1a845ce57b3ff9690141599a8e7443e0aa6ad6090aa97aad4c26d286bfe1e4`。当前 `labels_filled=false`，故它不是人工金标准，也不允许阈值冻结或 Development 评测。

用户授权的机器初标已完成，路径为 `candidate_F_machine_preannotation_full_v1/machine_preannotations.jsonl`。完整性审计为 240/240 唯一 ID、240/240 结构合法、帧/ASR锚点可回映、无 `ground_truth`/标签/参考答案/评分字段；输出 SHA256=`b1bc4450f2c6e75ded54861c824a104c8a611fad7a05d6438b24836531c429d2`。所有行均为 `machine_only=true`、`not_human_gold=true`，因此保持 `threshold_calibration_allowed=false`、`development_evaluation_allowed=false`；A/B 人审模板哈希未变化。

### 非固定 Token Dev100 探索：Raw32 + AVCrop8（2026-07-18）

| 项目 | 结果/约束 |
|---|---|
| 数据 | `counterfactual_dev100_v1`，100题、100个唯一视频 |
| 输入 | 32 Raw Uniform 全帧 + 8 AV 响应裁剪 = 40实际输入 |
| 模型与回答 | Qwen3-VL-8B；冻结回答 Prompt；RAG/反思关闭；二次采样关闭 |
| Token | 动态 `2,400–12,180`；79/100 为11,880 |
| 完整性 | 100/100 prediction、100/100 evidence、errors=0、40/40表示帧每题 |
| 比较边界 | `not_comparable_to_fixed_token_main_table=true`，不进入固定11,664 Token 主表 |
| QA裁判 | Immutable DeepSeek answer-only；100/100可解析；Raw32 `41.0%/56.0%`，AVCrop8 `40.0%/55.5%` |

运行根目录：`evaluation/runs/innovation2_exploratory_raw32_avcrop8_dev100_nonfixedtoken_v1/full_v1/`；协议审计：`protocol_audit_v1.json`。该运行只检验“额外局部视图与动态Token”是否值得后续受控研究，不能表述为公平预算下的方法提升。

预检说明：首个 Smoke1 因原始帧与裁剪帧形状不一致而在处理器堆叠阶段失败；修复为视频内原生画布适配，Smoke1 v2 通过，随后全量运行。该修复不改变跨视频的动态尺寸/Token属性。

配对结果：Raw胜/平/AVCrop8胜=`15/70/15`，Raw−AVCrop8平均差=`+0.5 pp`，10,000次Bootstrap CI=`[-5.0,+6.0] pp`；Strict wrong→right=`0`、right→wrong=`1`，Relaxed gain/harm=`15/15`。点估计不支持AVCrop8，区间跨零，且动态Token使其本身不具备固定预算可比性。因此该分支冻结，绝不扩展至 Confirm 或主表。裁判根目录：`judge_deepseek_answer_only_v1/`；分析：`pairwise_analysis_v1.json`；失败归因：`failure_attribution.json`。

## Clean Qwen2.5 GroupCV-500 OOF（2026-07-19）

| 方法 | 输入 | Strict | Relaxed | 相对 Raw32 的配对结论 |
|---|---|---:|---:|---|
| A_Raw32 | 32全局帧，16,384 Token | 31.4% | 50.8% | 基线 |
| B_Raw40 | 40全局帧，20,480 Token | 34.8% | 50.3% | Strict `+3.4 pp`，CI `[-0.8,+7.4]`；Relaxed `-0.5 pp`，CI `[-4.1,+2.9]` |
| C_Gated_RandomCrop8 | 仅7题追加随机裁剪8帧 | 31.4% | 50.8% | 1胜/498平/1负，净变化0 |
| D_Gated_CLIPCrop8 | 仅7题追加CLIP裁剪8帧 | 31.6% | 51.0% | 2胜/498平/0负；Strict/Relaxed均 `+0.2 pp` |
| E_Gated_AVCrop8 | 仅7题追加AV裁剪8帧 | 31.6% | 51.0% | 与D的500条答案及分数完全一致 |

实验边界：官方训练集500题、100个视频，视频级五折 OOF；模型 `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct`，未使用 ReAd-R。25/25 method-fold 完成，2,500条预测，联合审计通过。门控命中7/500，且7题全部 `ASR=false`、`OCR候选=0`，CLIP/AV裁剪帧与框相同。因此 E 没有实际测试到视听贡献，状态为 `candidate_failed_av_degenerated_to_clip`。

远端复现索引：运行根目录 `evaluation/runs/innovation1_qwen25_gated_avcrop_dev200_v1/`；协议审计 `oof_protocol_audit_v1.json`；裁判结果 `judge_deepseek_answer_only_oof_dedup_v1/results.jsonl`；统计 `judge_deepseek_answer_only_oof_dedup_v1/analysis_v1/oof_judge_clustered_analysis_v1.json`；失败归因位于同目录 `failure_attribution.json`。

裁判请求 `deepseek-chat`，实际响应模型为 `deepseek-v4-flash`。冻结 Prompt SHA256=`898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19`。相同题目与完全相同预测只评一次：API调用1,021条，复用1,479条；最终2,500条均可解析。未运行 Fresh81，未根据 OOF 调整阈值。

## Modality-Active AVCrop40 GroupCV-500（已完成，2026-07-19）

| 字段 | 内容 |
|---|---|
| 目标 | 修复旧 Gated-AV 的 ASR/OCR 输入退化，只比较真实模态激活后的固定预算裁剪 |
| 模型 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct`，禁止 ReAd-R |
| 方法 | `D_CLIPCrop40`；`E_ModalityActiveAVCrop40` |
| 预算 | 32全局+8局部=40视图；896×896；实际20,480视觉Token；关闭二次采样 |
| 数据 | 官方训练集500题、100视频、原五折 OOF 划分 |
| 门控拟合 | 每折只使用外层训练题的 ASR relevance contrast 75%分位数 |
| 真实激活 | 147/500题、61/100视频；OCR显式36、ASR显式5、高置信ASR 106 |
| 回退 | 353题 AV 裁剪与 CLIP 裁剪签名相同，按确定性规则复用 CLIP 预测 |
| Smoke20 | 两组20/20完成；每题40帧、20,480 Token、错误0；激活题计划10/10不同，回退题计划与预测10/10一致 |
| Raw40可比性 | 模型哈希、Python、Transformers、Prompt、生成参数、实际40帧与20,480 Token逐项一致，可复用旧 `B_Raw40` |
| 正式完整性 | CLIP 500/500；AV真实激活147/147、回退复用353/353；错误0；协议审计 `passed=true` |

正式结果：

| 方法 | Strict | Relaxed | 相对 Raw40 |
|---|---:|---:|---|
| `B_Raw40` | 34.8% | 50.3% | 基线 |
| `D_CLIPCrop40` | 42.0% | 54.1% | Strict `+7.2 pp`，CI `[+3.0,+11.4]`；Relaxed `+3.8 pp`，CI `[+0.3,+7.4]` |
| `E_ModalityActiveAVCrop40` | 41.2% | 53.9% | Strict `+6.4 pp`，CI `[+2.2,+11.0]`；Relaxed `+3.6 pp`，CI `[0.0,+7.3]` |

AV与CLIP的500题配对胜/平/负为 `23/452/25`，AV−CLIP Relaxed=`-0.2 pp`、CI `[-1.7,+1.3]`，Strict=`-0.8 pp`、CI `[-3.0,+1.4]`。147题模态激活子集上的 AV−CLIP 为 Relaxed `-0.68 pp`、CI `[-5.67,+4.22]`，Strict `-2.72 pp`、CI `[-10.32,+4.70]`。36条OCR显式题虽有正点估计，但区间跨0；5条ASR显式题不可作推断。

结论：冻结决策树命中“AV与CLIP无可确认差异、CLIP优于Raw40”。论文可主张同预算的问题条件化局部视觉增强带来本组稳定收益，不可主张ASR/OCR模态激活进一步提高QA。创新点一据此停止精度调参。

远端根目录：`evaluation/runs/innovation1_qwen25_modality_active_avcrop_groupcv_v1/`。协议审计：`formal/protocol_audit_v1.json`；裁判：`judge_deepseek_answer_only_oof_dedup_v1/results.jsonl`；聚类分析：`judge_deepseek_answer_only_oof_dedup_v1/analysis_v1/modality_active_clustered_analysis_v1.json`。裁判结果 SHA256=`f97a6e46b5edd79407dc99b2cd281cc891a8adf0c446f936ada8ea7c0e74de74`，Prompt SHA256=`898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19`，裁判 provenance 明确 `contains_api_key=false`。

本地只读结果副本与哈希清单：`artifacts/innovation1_qwen25_modality_active_avcrop_groupcv_v1/manifest.json`。

## FreshQ-500：Qwen2.5固定40视图独立题目确认（完成，门禁未通过，2026-07-20）

| 字段 | 内容 |
|---|---|
| 正式名称 | FreshQ-500；题目级零重合确认，不是视频级全新集合 |
| 规模 | 500题、500个不同视频；Type_1至Type_5各100题 |
| 与既往集合重合 | 题目ID重合0；498个视频曾在其他问题中出现 |
| 视频级Fresh不可行原因 | 既往集合并集覆盖1,633个视频；严格排除后五类仅余7/0/8/2/0条可用题 |
| 技术预检 | v1发现1个损坏视频；v2仅按解码失败替换后500/500通过 |
| 模型 | 干净 `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct`，禁止ReAd-R |
| 方法 | `B_Raw40`；`D_CLIPCrop40`（32全局+8问题条件化局部裁剪） |
| 公平预算 | 40实际视图、896x896、20,480视觉Token、关闭二次采样 |
| Smoke10 | 两组10/10、错误0、协议审计通过；Raw/Crop平均17.33/16.91秒 |
| 当前状态 | 两组500/500、错误0；协议审计、DeepSeek裁判和10,000次视频聚类Bootstrap均完成；确认门禁未通过 |

冻结数据路径：`data/freshq_confirm500_qwen25_clipcrop_v2/`；问题 SHA256=`b83f62431fd0d87da5ba71676f2b987e42e2739bf75de8ef88e107c7baeefc00`，groundtruth SHA256=`1b1925553785a68ff9fe62e0f807fef648677dfe7220a13e9f8bf28281237e54`。裁剪manifest：`evaluation/runs/innovation1_qwen25_clipcrop_freshq500_v1/manifests/clipcrop40_manifest_v1.jsonl`，SHA256=`5fa91cb3e833866bb7b0f4094f0db8459c75ad9c57b45e928308362df15af523`。运行根目录：`evaluation/runs/innovation1_qwen25_clipcrop_freshq500_v1/`。

预注册确认门禁：Relaxed差值大于0且视频聚类95% CI下界不低于0；Strict点估计不下降；裁剪胜数多于Raw胜数；任一问题类型Relaxed不得下降超过5个百分点。结果完成前禁止调裁剪数、尺度、Prompt或视觉预算。

正式结果：

| 方法 | Strict | Relaxed | 计分分布（0/0.5/1） |
|---|---:|---:|---:|
| `B_Raw40` | 40.4% | 55.0% | 152/146/202 |
| `D_CLIPCrop40` | 38.8% | 53.8% | 156/150/194 |

CLIPCrop−Raw40：Strict `-1.6 pp`，视频聚类95% CI `[-5.8,+2.4]`；Relaxed `-1.2 pp`，CI `[-4.4,+1.9]`。CLIPCrop胜/平/Raw胜=`87/325/88`。Type_1至Type_5的Relaxed差值为 `-4/-1/-3/-1/+3 pp`，各类型区间均跨0。

确认门禁结果：Relaxed正点估计失败、Relaxed CI下界非负失败、Strict不下降失败、胜数大于负数失败；仅“无类型下降超过5 pp”通过。因此 `confirmation_passed=false`，不得将GroupCV-500的正结果外推为稳定QA精度提升，也不得在本集合调参。该结果应与GroupCV正结果并列记录，用于说明局部证据增强收益存在明显分布敏感性。

正式协议审计 SHA256=`d73cbfa4ad2222733d5944d2efa77dd6b395d6b0e6434d451428d06d3b1a3998`；裁判结果 SHA256=`c2c5f509fe19dc26ceeacda06424891271e10e038116e2a299219dcb131afe80`；冻结裁判Prompt SHA256=`898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19`。本地只读副本见 `artifacts/innovation1_qwen25_clipcrop_freshq500_v1/`。

既有GroupCV机制复核队列为181条：CLIP gain 104、harm 77；远端路径 `evaluation/runs/innovation1_qwen25_modality_active_avcrop_groupcv_v1/mechanism_review_v1/`，队列 SHA256=`5268b44e92d13baac9668dc442d91e1eb97d281fe5c80f11d6b8fa6b41ec45e5`。现已完成机器初审和21题LLM二次复核，但仍没有人工机制金标签。

## GroupCV-181：Raw40/CLIPCrop40 分数变化机制复核（完成，非人工金标准，2026-07-20）

| 字段 | 内容 |
|---|---|
| 范围 | GroupCV中裁判分数发生变化的181题；gain 104、harm 77 |
| 初审模型 | `<MODEL_ROOT>/Qwen3Vl-8B`，机器视觉归因181/181、错误0 |
| 二次复核 | 按全部机制类别分层抽取21题；Codex LLM视觉复核，不是人工标注 |
| 一致性 | 精确标签12/21（57.1%）；三类合并标签15/21（71.4%） |
| 已确认机制 | 局部文字/Logo、对象/动作及问题相关细节可以得到恢复或强调；无关/误导局部图会造成少量真实伤害 |
| 主要归因问题 | 初审会高估Raw40全局网格独占证据；多例分数下降无法由视觉差异解释或与视觉证据方向冲突 |
| 协议发现 | Raw40与Global32+Local8使用不同全局采样网格，存在全局帧位置与局部裁剪同时变化的因果混杂 |
| 下一门禁 | 先运行共享32全局锚点的三臂隔离实验，再决定是否扩到3000题 |
| 远端根目录 | `evaluation/runs/innovation1_qwen25_modality_active_avcrop_groupcv_v1/mechanism_review_visual_v1/` |
| 本地只读副本 | `artifacts/innovation1_qwen25_modality_active_avcrop_groupcv_v1/mechanism_review_v1/` |

正式三臂定义为：`Shared32+ExtraGlobal8`、`Shared32+Local8`、`Shared32+RandomLocal8`。三组必须共享同一32帧全局网格，均为40实际/表示视图和同一视觉Token预算，关闭二次采样并固定模型、Prompt、生成配置和配对裁判。21题为机制分层样本，只能用于审查归因可靠性，不能估计181题机制占比；所有复核均保持`not_human_gold=true`。

## Shared32 三臂因果隔离实验（已启动，结果待定，2026-07-20）

| 字段 | 内容 |
|---|---|
| 目标 | 消除Raw40与Global32+Local8同时改变全局采样网格和局部视图的因果混杂 |
| 方法 | `Shared32_ExtraGlobal8`、`Shared32_Local8`、`Shared32_RandomLocal8` |
| 共享部分 | 每题完全相同的32个均匀全局锚点 |
| 干预部分 | 固定全局中点 / 问题条件局部裁剪 / 确定性随机局部控制，各追加8视图 |
| 公平协议 | 40实际/表示视图、20,480视觉Token、Qwen2.5干净基座、同Prompt、关闭二次采样 |
| 数据 | GroupCV-500，视频级五折，先20题×3 smoke，再500题正式推理 |
| 远端根目录 | `evaluation/runs/innovation1_qwen25_shared32_isolation_groupcv500_v1/` |
| 当前状态 | 三组 smoke 通过；GPU4/GPU5 已开始正式五折推理，尚未写QA结论 |
| GPU | GPU2、GPU4、GPU5 分担不重叠折；GPU0/3不使用，后台编排器持续托管 |

正式结果门禁：三组题目集合完整、错误为0、每题40视图/20,480 Token、共享32帧签名完全一致、局部与随机控制追加签名不碰撞、模型和Prompt配置哈希一致。门禁通过后才进行DeepSeek answer-only配对裁判和10,000次视频聚类Bootstrap。

GPU加速记录：smoke完成后停止原GPU4单卡协调器，改由独立worker运行GPU4与GPU5；随后获授权的GPU2接手尚未开始的fold2。GPU4负责fold 0/1/2，GPU5负责fold 3/4，GPU2负责fold2；每个worker内部按方法顺序断点续跑，输出分别落在 `formal/<method>/fold_<fold>/`。最终审计等待器在GPU2、GPU4、GPU5三个worker全部完成后运行，实验仍在进行中。

调度审计补充：GPU2启动时原GPU4 worker已推进至fold2的RandomLocal，短暂出现同一fold的重复计算风险。已停止GPU4对应的自有子进程，保留既有完整fold0/1输出和GPU5 fold3/4输出，GPU2独占fold2；`repair_shared32_gpu4_marker_v1.sh` 仅在GPU4负责的fold0/1/2三组各100条齐全后生成完成标记。最终审计等待器会重新核对三组总数、共享32帧签名、视图和Token协议。

跨实验口径盘点和论文路线收敛原见《当前实验数据盘点与论文路线收敛》（历史来源，未收入本去重归档）。该文档区分可进主表、机制诊断、历史参考和无效/不完整结果。

### Shared32 三臂正式推理与协议审计完成（2026-07-20）

三组均已完成 `500/500`，合计1500条逐题预测，错误数为0。统一协议审计 `passed=true`：每组均为40个实际/表示视图、20,480视觉Token，共享32帧签名不一致数为0，Local8与RandomLocal8追加签名碰撞数为0，五折配置和模型/Prompt签名一致。该阶段只证明推理输出和公平预算协议有效，尚未运行DeepSeek裁判，不能把当前状态写成最终QA精度。下一步为冻结口径的answer-only配对裁判与10,000次视频聚类Bootstrap。

### Shared32 三臂裁判与视频聚类 Bootstrap 完成（2026-07-20）

| 方法 | Strict | Relaxed | 逐题数量 |
|---|---:|---:|---:|
| `Shared32_ExtraGlobal8` | 27.8% | 43.5% | 500 |
| `Shared32_Local8` | 31.8% | 45.9% | 500 |
| `Shared32_RandomLocal8` | 28.6% | 43.9% | 500 |

裁判口径为旧 `evaluate_compare_new.py`、`answer_only`、DeepSeek；三组共1500条，均无缺失。10,000次Bootstrap按视频聚类进行。`Local8 - ExtraGlobal8` 的 Strict 为 `+4.0 pp`，95% CI `[+0.8,+7.2]`；Relaxed 为 `+2.4 pp`，CI `[-0.4,+5.1]`。`Local8 - RandomLocal8` 的 Strict 为 `+3.2 pp`，CI `[-0.2,+6.6]`；Relaxed 为 `+2.0 pp`，CI `[-0.8,+4.9]`。因此Strict结果支持局部增强相对全局补充的作用，但Relaxed及相对随机局部控制仍不能宣称稳定提升。

结果文件：远端 `evaluation/runs/innovation1_qwen25_shared32_isolation_groupcv500_v1/judge_deepseek_answer_only_v1/`；视频聚类分析：`analysis_shared32_threearm_v1/shared32_threearm_clustered_analysis_v1.json`。

### Confirm-3000 独立确认最终结果（2026-07-21）

| 字段 | 内容 |
|---|---|
| 方法 | `Shared32_ExtraGlobal8` vs `Shared32_Local8` |
| 模型 | 干净 `Qwen2.5-VL-7B-Instruct`，非 AdsQA 微调模型 |
| 数据 | Confirm-3000，两个方法各 3000/3000，无缺失 |
| 公平协议 | 同32个全局锚点、40视图、20,480视觉Token、同Prompt、关闭二次采样 |
| 协议审计 | `passed=true`；共享帧不一致数0，局部签名碰撞数0 |
| 裁判 | 冻结 DeepSeek answer-only，10,000次视频聚类Bootstrap |
| ExtraGlobal8 | Strict `32.93%`，Relaxed `54.00%` |
| Local8 | Strict `33.57%`，Relaxed `54.45%` |
| Local8−ExtraGlobal8 | Strict `+0.63 pp`，Relaxed `+0.45 pp` |
| 配对胜/平/负 | `509/2000/491` |
| Bootstrap CI | 配对平均 `0/0.5/1` 评分差（ExtraGlobal8−Local8）`[-1.57,+0.68] pp` |
| 门禁结论 | 未通过；区间跨0，不宣称稳定QA提升 |
| 结果摘要 | `judge_deepseek_answer_only_v1/summary.json` |

该结果是独立确认结果，不覆盖 GroupCV-500 的开发集结果。论文主张应收束为：问题条件化局部证据分配在固定预算和共享全局上下文下具有微弱正向信号，但收益存在明显分布敏感性，不能写成稳定泛化的准确率提升。

### 不确定性门控 Local8 单候选探索（2026-07-21）

| 字段 | 内容 |
|---|---|
| 候选 | `UncertaintyGatedLocal8-v1` |
| 基座 | 干净 `Qwen2.5-VL-7B-Instruct` |
| 输入协议 | Shared32 + Local8，40 视图，20,480 Token，关闭二次采样 |
| 选择机制 | 32 个 CLIP 候选的邻域均值−方差稳健分数；拥挤且不稳定时最多替换2帧 |
| 数据 | GroupCV-500，answer-free manifest |
| manifest 审计 | 500/500；触发12条；改变11条；替换22帧；无答案/标签/裁判泄漏 |
| 运行根目录 | `evaluation/runs/innovation1_uncertainty_gated_local8_groupcv500_v1/` |
| 当前状态 | 已完成推理、协议审计、DeepSeek裁判和10,000次视频聚类Bootstrap |
| 论文口径 | 探索性候选，不覆盖 Confirm-3000 冻结结论，不进行参数扫描 |

| Local8 | Strict `31.8%` | Relaxed `46.2%` |
| UncertaintyGatedLocal8 | Strict `32.0%` | Relaxed `46.4%` |
| 候选相对 Local8 | Strict `+0.2 pp` | Relaxed `+0.2 pp` |
| 视频聚类 Bootstrap CI | Strict `[-1.0,+1.4] pp` | Relaxed `[-0.5,+0.9] pp` |
| 配对胜/平/负（Local8/候选） | `6/486/8` | `6/486/8` |
| 门禁结论 | 未通过，区间跨0 | 标记 `candidate_failed` |

结果摘要：`evaluation/runs/innovation1_uncertainty_gated_local8_groupcv500_v1/judge_deepseek_answer_only_v1/summary.json`；视频聚类分析：`analysis_uncertainty_gated_local8_v1/shared32_uncertainty_gated_local8_twoarm_clustered_analysis_v1.json`。结果 `not_human_gold=true`，不作为人工金标准。

#### 同答案去重与匿名配对裁判复核

| 字段 | 内容 |
|---|---|
| 实际视觉与答案变化 | `11/500`；其余489条同题同答案哈希复用同一分数 |
| 配对裁判 | 11题，每题3轮匿名A/B，强制交换顺序，共33轮，全部解析成功 |
| 变化子集多数决 | 候选胜2、平9、负0；可靠改善题号21、134 |
| Local8 | Strict `31.8%`，Relaxed `46.2%` |
| UncertaintyGatedLocal8 | Strict `32.2%`，Relaxed `46.4%` |
| 候选增益 | Strict `+0.4 pp`，Relaxed `+0.2 pp` |
| 视频聚类95% CI | Strict `[0.0,+1.0] pp`，Relaxed `[0.0,+0.5] pp` |
| 结论 | 低覆盖、无观测伤害的正向信号；区间含0且未达到1.5 pp门禁，不进入Confirm |
| 结果目录 | `evaluation/runs/innovation1_uncertainty_gated_local8_groupcv500_v1/judge_identity_dedup_paired_v1/` |

该复核不覆盖旧裁判结果，而是明确其9条同答案异分属于裁判噪声。`summary.json`、`rounds.jsonl`和`adjudicated_changed11.jsonl`均标记`not_human_gold=true`，未保存API key。

## 创新点二 RealClaim LoRA 声明证据验证器（阶段性结果，2026-07-21至2026-07-22）

| 字段 | 内容 |
|---|---|
| 目标 | 训练真正读取视觉/ASR证据的声明支持—冲突验证器，并与冻结视觉Qwen同协议比较 |
| 基座 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct`，干净Qwen2.5，非ReAd-R |
| 训练方式 | 冻结视觉编码器；语言层`q_proj/v_proj` LoRA，2,523,136可训练参数 |
| 输入 | 每条8证据视图 + 问题 + 原子声明 + ASR；无参考答案、标签或证据状态泄漏 |
| 当前训练数据 | v2.3审计通过的156对supported/contradicted；自动标签，`not_human_gold=true` |
| 内部分割 | 125对训练、31对视频隔离验证，视频交集0 |
| Smoke20 | 两版均2/3 pair accuracy；分类/配对排序平均间隔3.708/5.417，仅作工程门禁 |
| 正式候选 | GPU1普通分类；GPU2分类+pairwise ranking；均2 epoch、8视图 |
| 远端根目录 | `evaluation/runs/innovation2_realclaim_lora_verifier_v1/` |
| 训练脚本 | `evaluation/tools/train_realclaim_lora_verifier_v1.py` |
| 评分脚本 | `evaluation/tools/evaluate_realclaim_lora_verifier_v1.py` |
| 后台续跑 | `evaluation/scripts/continue_realclaim_lora_calibration_v1.sh` |
| 下一门禁 | 两适配器与冻结基座在Calibration240同协议比较；通过后才单次评测Development244 |
| 当前状态 | 后续RealClaim985、软标签与HardNeg结果见本节下文；当前最佳为直接RealClaim985，HardNeg路线已冻结失败 |

数据审计边界：已有500条自动证据锚定声明严重偏向ASR短语代理任务（442条audio、448条仅有ASR锚点），暂不并入正式训练。受控反事实上的高分不能替代真实模型错误识别；后续仍需构建并审计RealClaim-Train v1，或证明当前LoRA能在独立真实声明集上超过冻结基座。

### Full156 与 Calibration240 完成结果

| 方法 | 内部Pair Acc | Calibration AUROC | AUPRC | Balanced Acc |
|---|---:|---:|---:|---:|
| 冻结Qwen2.5基座 | — | 0.4869 | 0.6321 | 0.5153 |
| 分类LoRA | 90.32% | 0.5752 | 0.6958 | 0.5660 |
| 分类+Pairwise LoRA | 90.32% | 0.5715 | 0.6967 | 0.5650 |

两版训练与三路Calibration均完整、无缺失，GPU1/2已释放。当前暂定普通分类LoRA为候选，但AUROC未达到0.70门禁，Development244仍未评测。结果文件为 `evaluation/runs/innovation2_realclaim_lora_verifier_v1/full156/*/complete.json` 与 `calibration240/comparison.json`。

### RealClaim-Train985 完整弱监督训练与Calibration

| 方法 | 内部验证 AUROC | Calibration AUROC | Calibration AUPRC | Calibration BA |
|---|---:|---:|---:|---:|
| 冻结Qwen2.5基座 | — | 0.4869 | 0.6321 | 0.5153 |
| 直接RealClaim LoRA | 0.6931 | **0.6345** | 0.7348 | **0.6349** |
| 受控反事实→RealClaim课程式LoRA | 0.6839 | 0.6244 | **0.7458** | 0.6000 |

数据为985条、139个训练视频，supported/not-supported=`642/343`，与Calibration和Development视频零交集，输入无参考答案或标签泄漏，`not_human_gold=true`。直接训练相对冻结基座的Calibration AUROC视频聚类Bootstrap增益为`+0.1498`，95% CI `[+0.0613,+0.2388]`。当前最佳为直接RealClaim LoRA，但绝对AUROC未达到0.70门禁，Development244仍未使用。训练目录为 `realclaim_weak_full985_v1/`，校准目录为 `realclaim_weak_full985_calibration240_v1/`。

### 置信度软标签 Smoke80（失败）

| 方法 | 验证条数 | AUROC | AUPRC | Balanced Acc |
|---|---:|---:|---:|---:|
| Hard-label直接训练 | 16 | 0.6417 | 0.7223 | 0.5000 |
| Confidence soft-label | 16 | 0.6417 | 0.6917 | 0.5000 |

高置信过滤未启动：`confidence≥0.8`仅保留13条not-supported，类别分布无效。Soft-label候选没有改善AUROC且降低AUPRC，故不扩跑985条，不扫描阈值。远端目录为 `evaluation/runs/innovation2_realclaim_lora_verifier_v1/realclaim_softlabel_smoke80_v1/`。

### 同视频证据锚点排除 HardNeg90（失败）

| 方法 | 自身验证 AUROC | Calibration AUROC | AUPRC | Balanced Acc |
|---|---:|---:|---:|---:|
| RealClaim直接训练 incumbent | — | 0.6345 | 0.7348 | 0.6349 |
| Incumbent→HardNeg90顺序微调 | 0.7825 | 0.5099 | 0.6146 | 0.5616 |

HardNeg90包含90对、正负各90、视觉124条、OCR 56条、33个训练视频，负操作审计有效且与保留集零重叠。候选只在合成干预分布上表现较好，真实Calibration明显退化，标记`candidate_failed_task_shift`。结果目录为 `evaluation/runs/innovation2_realclaim_lora_verifier_v1/same_video_hardneg90_lora_v1/`，Development244未使用。

### RealClaim985 + HardNeg90 联合回放（失败，2026-07-22）

| 字段 | 内容 |
|---|---|
| 候选 | `RealClaim985+HardNeg90` 联合回放 LoRA |
| 基座 | 干净 `Qwen2.5-VL-7B-Instruct`，视觉编码器冻结，非 ReAd-R |
| 固定协议 | 8视图、既有学习率、1 epoch；不扫描超参数、阈值或Token预算 |
| 训练数据 | RealClaim985 + HardNeg90；与Calibration/Development视频零重叠；`not_human_gold=true` |
| Calibration240 | AUROC `0.6108`，AUPRC `0.6923`，BA `0.6246` |
| incumbent | RealClaim985 AUROC `0.6345`，AUPRC `0.7348`，BA `0.6349` |
| 视频聚类Bootstrap | 10,000次；候选−incumbent AUROC均值 `-0.02418`，95% CI `[-0.05663,+0.00758]`，`P(diff>0)=0.0699` |
| 决策 | `candidate_failed_no_development`；未运行 Development244 |

该联合训练没有修复顺序 HardNeg 微调的迁移问题，且未超过 incumbent；停止该候选，不再自动启动创新点二训练或参数扫描。远端结果：`evaluation/runs/innovation2_realclaim_lora_verifier_v1/realclaim_hardneg_replay_v1/`，包括 `calibration240/bootstrap_vs_incumbent.json`、`failure_diagnostics.json`、`failure_attribution.md` 与 `candidate_ledger.jsonl`。

### E-VAds 独立预处理与复现索引（2026-07-22）

| 字段 | 内容 |
|---|---|
| 数据定位 | 可选外部验证；绝不混入 AdsQA 训练、Calibration、阈值或主表 |
| 原始数据 | 3,961 MP4；官方 Test 为16,925题、3,389视频 |
| 完整性 | 3个 Parquet 与 `videos.zip+z01-z09` 的13项 LFS SHA256 全部通过；分卷合并/解压通过 |
| 官方文本审计 | Test 中时间对齐 ASR 标记 `16,925/16,925`；OCR 标记 `16,835/16,925` |
| answer-free 输入 | 已生成16,925条；不含答案、奖励、标签、证据状态或成对监督字段 |
| 64帧候选索引 | `3,961/3,961`，无缺失/重复/记录错误；候选64与Raw32嵌套审计通过 |
| ASR映射 | 现有 answer-free ASR 映射覆盖2,714视频；其余状态保留为缺失，不伪造空文本 |
| smoke | 5视频解码、Raw32/候选64 公共输入适配通过；未做Qwen或CLIP模型推理 |
| 状态 | 仅预处理完成，任何全量基线/方法评测须单独冻结协议并经用户确认 |

远端根目录：`data/external/evads_v1/`；索引审计和哈希清单：`data/external/evads_v1/cache/video_index64_v1/audit.json`、`manifest.json`、`sha256_inputs_outputs.txt`。其中“64帧候选”是 query-agnostic 帧/时间戳/场景索引，不应误写为 CLIP embedding 缓存。

### E-VAds External-500 冻结外部验证（启动记录，2026-07-22）

| 字段 | 内容 |
|---|---|
| 冻结数据 | 100视频 × 每视频完整5题 = 500题；八类商品各12–13视频 |
| 选择规则 | 按类别分层后对视频ID执行固定SHA256排序；排除8个不完整五题视频 |
| 任务标签边界 | 发布的Parquet无逐题BP/CM/ML/CI/RC字段；不推测或伪造标签 |
| 输入隔离 | 推理文件answer-free；参考答案、clues和OCR/ASR仅存于独立裁判目录 |
| 32视图表 | `Uniform32` vs `SigLIPTopK32`，各16,384视觉Token |
| 40视图表 | `Shared32_ExtraGlobal8` vs `Shared32_SigLIPLocal8`，各20,480视觉Token |
| 模型与Prompt | 干净`Qwen2.5-VL-7B-Instruct`；官方E-VAds Prompt；确定性生成 |
| 公平协议 | 同表内视图/Token相同，所有帧被表示，关闭二次采样，不向回答模型提供裁判元数据 |
| Smoke5 | 四组各5/5，无错误；20/20输出含`<answer>`；协议审计通过 |
| 当前阶段 | Full500已完成；最终指标、配对Bootstrap和结论见下节 |

中文检索诊断确认旧OpenAI CLIP的同视频跨问题Top-8高度重合，外部实验改用本地SigLIP做中文问题条件化检索，并在方法名中明确标注，不与AdsQA上的CLIP实现混称。远端实验根目录：`data/external/evads_v1/experiments/external500_v1/`；冻结清单：`freeze_manifest.json`；问题输入：`questions_inference.json`；续跑器：`evaluation/scripts/continue_evads_external_v1.sh`。

### E-VAds External-500 冻结外部验证：最终结果（2026-07-22）

| 字段 | 内容 |
|---|---|
| 数据与模型 | 冻结Test-500（100完整五题视频包）；干净 `Qwen2.5-VL-7B-Instruct`，非ReAd-R |
| 回答协议 | 官方E-VAds Prompt、确定性生成、关闭二次采样；回答模型不读取答案、证据、OCR/ASR裁判元数据 |
| 评分协议 | 冻结 DeepSeek 官方R5/R3/R2口径；同题同答案哈希仅判一次；`not_human_gold=true`；10,000次视频聚类Bootstrap |
| 完整性 | 四种方法各500/500，错误0；视觉、Token、帧对齐和缓存审计通过 |
| 32视图预算 | `Uniform32` 与 `SigLIPTopK32` 各32视图、16,384视觉Token |
| 40视图预算 | `Shared32_ExtraGlobal8` 与 `Shared32_SigLIPLocal8` 各40视图、20,480视觉Token |

| 方法 | R5 | R3 | R2 |
|---|---:|---:|---:|
| `Uniform32` | 54.10% | 40.50% | 13.80% |
| `SigLIPTopK32` | 51.05% | 36.70% | 11.20% |
| `Shared32_ExtraGlobal8` | 53.80% | 39.80% | 14.00% |
| `Shared32_SigLIPLocal8` | 54.15% | 40.10% | 13.20% |

| 配对比较 | R5差值 | 95% CI | 结论 |
|---|---:|---|---|
| `SigLIPTopK32 - Uniform32` | `-3.05 pp` | `[-5.20,-0.90] pp` | 稳定负向；`candidate_failed_external` |
| `Shared32_SigLIPLocal8 - Shared32_ExtraGlobal8` | `+0.35 pp` | `[-1.30,+2.00] pp` | 无稳定增益；不得写成外部精度提升 |

补充：Top-K比较的R3差值为`-3.80 pp`，95% CI `[-6.20,-1.40] pp`；Local8比较的R3/R2差值分别为`+0.30/-0.80 pp`，区间均跨0。该外部验证只能用于检验泛化与报告边界，禁止用于新的参数调优、阈值选择或训练。远端完整复现根目录为 `data/external/evads_v1/experiments/external500_v1/`；关键文件为 `full500/protocol_audit.json`、`full500/judge_deepseek_official_v1/summary.json`、`results.jsonl` 与 `judge_cache.jsonl`，完成标记为 `full500/complete.marker`。

### CP-AVR GroupCV-500 路由器 Smoke（2026-07-22，非正式结论）

| 字段 | 内容 |
|---|---|
| 候选 | `CPAVR_Router8`：32共享均匀全局视图 + 8个五折OOF路由残余视图 |
| 模型 | 干净 `Qwen2.5-VL-7B-Instruct`，非ReAd-R |
| 数据 | Train-500 的fold3固定20题，7个视频；仅作工程/裁判Smoke |
| 教师与路由 | Qwen3弱标签仅用于各外折训练；推理输入仅含问题、冻结视觉、ASR/OCR answer-free特征 |
| 视觉协议 | 每题40实际/表示视图，`32+8`，896统一尺寸，`20,480`视觉Token，二次采样关闭 |
| 路由动作 | 160个残余视图中`1`个`crop`、`159`个`full`；这是动作预算匹配训练折教师裁剪率的结果，不是事后阈值 |
| 推理完整性 | `20/20`预测，错误`0`；`qwen_smoke_audit.json`为`pass=true` |
| 主对照 | 同折、同模型、同Prompt、同40视图/Token的既有 `Shared32_ExtraGlobal8` |
| 裁判 | 旧DeepSeek answer-only固定Prompt；Groundtruth在推理后才从OOF文件抽取；`not_human_gold=true` |
| ExtraGlobal8 | Strict/Relaxed=`35.0%/52.5%` |
| CP-AVR | Strict/Relaxed=`50.0%/65.0%` |
| 配对 | CP-AVR胜/平/负=`6/13/1`；Strict/Relaxed点差=`+15.0/+12.5 pp` |
| 视频Bootstrap | 10,000次、7视频；Relaxed CI=`[-16.67,+32.76] pp`，Strict CI=`[-20.0,+50.0] pp` |
| 决策 | 正向Smoke，**不构成正式增益**；允许进入冻结五折OOF-500，不允许调参或访问Confirm-3000 |

### CP-AVR GroupCV-500 五折 OOF（2026-07-22，最终失败记录）

| 字段 | 内容 |
|---|---|
| 候选 | `CPAVR_Router8`：32共享全局锚点 + 8个五折OOF学习路由残余视图 |
| 模型 | 干净 `Qwen2.5-VL-7B-Instruct`，非 AdsQA/ReAd-R 微调版本 |
| 数据 | AdsQA Train-500，100视频，五折 OOF；500/500预测，错误0 |
| 视觉协议 | 40实际视图，`20,480`视觉Token，896统一尺寸，关闭二次采样 |
| 对照 | `Shared32_ExtraGlobal8` 与 `Shared32_Local8`，同模型、Prompt、视图数和Token |
| 裁判 | 冻结 DeepSeek answer-only 历史口径；`not_human_gold=true` |
| ExtraGlobal8 Strict/Relaxed | `27.8% / 43.5%` |
| Local8 Strict/Relaxed | `31.8% / 45.9%` |
| CP-AVR Strict/Relaxed | `27.2% / 42.9%` |
| CP-AVR - ExtraGlobal8 | Strict/Relaxed=`-0.6/-0.6 pp`；100视频 Bootstrap 95% CI=`[-4.6,+3.6]/[-3.7,+2.6] pp` |
| CP-AVR - Local8 | Strict/Relaxed=`-4.6/-3.0 pp`；Strict 95% CI=`[-8.4,-1.0] pp`，存在明确负向证据 |
| 裁决 | `candidate_failed_no_confirm`；不运行Confirm-3000，不在同一OOF上调参 |
| 失败诊断 | 裁剪/OCR路由91题相对Extra为Strict/Relaxed=`-6.59/-4.40 pp`；仅作事后观察，不作因果或调参依据 |
| 复现根目录 | 远端 `evaluation/runs/innovation1_cpavr_groupcv500_v1/`；审计 `qwen_groupcv500_v1/groupcv500_protocol_audit.json`，裁判 `judge_frozen_baselines_v1/summary.json`，诊断 `failure_diagnostics.{json,md}` |

远端根目录：`evaluation/runs/innovation1_cpavr_groupcv500_v1/`。有效推理与裁判分别为 `qwen_smoke20_v1/cpavr_fold3_retry2/` 和 `qwen_smoke20_v1/paired_judge_extra_global_v3/`；`paired_judge_extra_global_v1/`（旧评测器忽略CLI路径）及`v2/`（服务返回`: 0`时解析中止）均保留为无效工程失败记录，不参与任何数值结论。有效文件包括 `qwen_smoke_audit.json`、`cpavr_visual_protocol_audit.json`、`groundtruth20_manifest.json`、`dry_run_audit.json`、`results.jsonl`与`summary.json`。

### 干净 Qwen2.5 直接答案 LoRA 五折 OOF（有效训练基线，2026-07-22）

| 字段 | 内容 |
|---|---|
| 目的 | 验证任务内直接答案训练是否能形成可复现的回答器基线；不作为创新点一/二的增益结论 |
| 基座 | 干净 `Qwen2.5-VL-7B-Instruct`，明确非 AdsQA/ReAd-R 训练模型 |
| 数据 | AdsQA Train-500，100视频，视频级五折OOF；每折训练400题/80视频、验证100题/20视频 |
| 训练输入 | 8个均匀全局视频视图、448；训练/推理共用Qwen视频接口 |
| 视觉协议 | 实际8帧、实际`1,024`后合并视觉Token（上限`4,096`）、无时间padding、关闭二次采样 |
| 训练 | 视觉编码器冻结；语言侧`q/k/v/o` LoRA，rank16/alpha32/dropout0.05，`lr=5e-5`，1 epoch，梯度累积4 |
| 权重审计 | 5/5折通过；每折224个可训练张量均改变；初末adapter SHA和最大参数差均记录 |
| 输入隔离 | 训练答案、验证answer-free问题、验证groundtruth物理分离；裁判只在推理和审计后读取groundtruth |
| 推理完整性 | Base与LoRA各`500/500`，错误0；五折匹配视觉/Prompt/模型协议审计全部通过 |
| 裁判 | 历史 DeepSeek answer-only固定Prompt/解析口径；1000个唯一候选请求；`not_human_gold=true`；10,000次视频聚类Bootstrap |

| 方法 | Strict | Relaxed | 相对 `BaseRaw8` |
|---|---:|---:|---|
| `BaseRaw8` | 20.0% | 36.4% | — |
| `AdsSFTLoRA_Raw8` | 21.4% | 40.1% | Strict `+1.4 pp`，Relaxed `+3.7 pp` |

| 配对统计 | 结果 |
|---|---|
| 胜/平/负（LoRA/相同/Base） | `115/291/94` |
| Relaxed Bootstrap 95% CI | `[+0.2,+7.2] pp` |
| Strict Bootstrap 95% CI | `[-2.8,+5.6] pp` |
| 判定 | Relaxed存在视频级正向证据；Strict区间跨0；仅记为有效训练基线提升 |

远端根目录：`evaluation/runs/adsqa_sft_lora_groupcv500_v1/`。关键文件：`splits_v2/manifest.json`、`oof500_v2/fold_{0..4}/train/weight_delta_audit.json`、`oof500_v2/fold_{0..4}/matched_protocol_audit.json`、`oof500_v2_audit/groupcv_oof_protocol_audit.json`、`judge_deepseek_legacy_answer_only_v1/{dry_run_audit.json,results.jsonl,summary.json,SHA256SUMS}`。该训练平台后续只能以冻结配置用于单一预注册视觉证据对照，不能在其OOF结果上继续挑超参数。

### 直接答案 LoRA 上的 Context-Detail PiP8 三臂 OOF（2026-07-22，正式负结果）

| 字段 | 内容 |
|---|---|
| 目的 | 在已验证的直接答案LoRA上检验“全帧背景 + 局部放大画中画”能否在**相同8视图/Token**下增加证据收益 |
| 基座 | 干净 `Qwen2.5-VL-7B-Instruct` + 已冻结五折直接答案LoRA；非AdsQA/ReAd-R模型 |
| 数据 | AdsQA Train-500，100视频，视频级五折OOF；每臂`500/500`，错误`0` |
| 共同视觉协议 | 每题8个448视图，实际`1,024`后合并视觉Token（上限`4,096`），无padding，关闭二次采样 |
| `Raw8` | 已冻结 `AdsSFTLoRA_Raw8` 输出，未重跑 |
| `RandomPiP8` | 与证据PiP完全相同的题目、帧位置与PiP数量，局部框为确定性随机控制 |
| `AsrOcrPiP8` | OCR置信度≥0.90且与问题/ASR词法重合；最多替换2个原视图像素，保留全帧背景 |
| 触发覆盖 | `221/500`题、`56/100`视频、`333`个PiP；answer-free清单覆盖门禁通过 |
| 输入隔离 | PiP清单读取问题、ASR、OCR与帧索引，不读取答案、groundtruth、标签或裁判结果 |
| 审计 | 20题双arm smoke + 5折完整视觉审计 + 三臂协议审计均`passed=true` |
| 裁判 | 冻结历史DeepSeek answer-only；复用一致Raw8分数，仅新增207个唯一请求；`not_human_gold=true`；10,000次视频聚类Bootstrap |

| 方法 | Strict | Relaxed |
|---|---:|---:|
| `AdsSFTLoRA_Raw8` | 21.4% | 40.1% |
| `AdsSFTLoRA_RandomPiP8` | 21.2% | 40.2% |
| `AdsSFTLoRA_AsrOcrPiP8` | 20.4% | 39.3% |

| 配对比较 | Strict差值 | Relaxed差值 | Relaxed 95% CI | 结论 |
|---|---:|---:|---|---|
| `RandomPiP8 - Raw8` | `-0.2 pp` | `+0.1 pp` | `[-1.1,+1.3] pp` | 无可辨别效应 |
| `AsrOcrPiP8 - Raw8` | `-1.0 pp` | `-0.8 pp` | `[-2.1,+0.4] pp` | 无增益，轻微负向点估计 |
| `AsrOcrPiP8 - RandomPiP8` | `-0.8 pp` | `-0.9 pp` | `[-2.3,+0.4] pp` | 证据门控未超过随机局部控制 |

裁决：`candidate_failed_no_pip_scan`。不再扫描PiP阈值、位置、比例或词法权重，也不使用Confirm-3000/E-VAds Test补救。本实验是创新点一最初“全帧+局部”的公平证据呈现检验，不属于创新点二验证器训练，也不影响直接答案LoRA本身的Relaxed训练基线增益。远端根目录：`evaluation/runs/adsqa_sft_lora_groupcv500_v1/pip8_oof500_v1/`；最终三臂审计为`groupcv_three_arm_protocol_audit.json`，裁判为`judge_deepseek_legacy_pip8_oof_v1/{dry_run_audit.json,results.jsonl,summary.json,SHA256SUMS}`。

### 训练匹配 Context-Detail PiP8 LoRA 三臂 OOF（2026-07-22，正式负结果）

| 字段 | 内容 |
|---|---|
| 要检验的问题 | 前一轮PiP失败是否仅由“全帧训练、PiP推理”的视觉表示失配造成 |
| 基座 | 每折从干净 `Qwen2.5-VL-7B-Instruct` 开始，非AdsQA/ReAd-R模型 |
| 数据 | AdsQA Train-500，100视频，视频级五折；每折训练400题/80视频、验证100题/20视频 |
| 训练公平性 | 与Raw8逐折相同split、seed、LoRA模块/秩、学习率、1 epoch、梯度累积、Prompt和ASR |
| 视觉协议 | 训练和推理均为8个448视图、实际`1,024`视觉Token（上限`4,096`）、无padding、二次采样关闭 |
| 训练期激活 | 训练清单与推理清单相同；每折PiP训练覆盖超过100题，权重差异与PiP训练审计均通过 |
| 输出完整性 | 两个新臂各`500/500`预测，5折训练、推理和三臂联合审计全部通过 |
| 裁判 | 冻结历史DeepSeek answer-only；复用Raw8历史分数，仅新增488个唯一请求；`not_human_gold=true`；10,000次视频聚类Bootstrap |

| 方法 | Strict | Relaxed |
|---|---:|---:|
| 冻结 `AdsSFTLoRA_Raw8` | 21.4% | 40.1% |
| 训练匹配 `RandomPiP8` | 20.0% | 38.7% |
| 训练匹配 `ASR/OCR-PiP8` | 19.6% | 39.4% |

| 配对比较 | Strict差值 | Relaxed差值 | Relaxed 95% CI | 结论 |
|---|---:|---:|---|---|
| `RandomPiP8 - Raw8` | `-1.4 pp` | `-1.4 pp` | `[-3.1,+0.4] pp` | PiP训练增强未带来收益 |
| `ASR/OCR-PiP8 - Raw8` | `-1.8 pp` | `-0.7 pp` | `[-2.7,+1.2] pp` | 训练匹配后仍未超过Raw8 |
| `ASR/OCR-PiP8 - RandomPiP8` | `-0.4 pp` | `+0.7 pp` | `[-1.3,+2.6] pp` | 证据内容弱于稳定性门槛 |

裁决：`candidate_failed_train_matched_pip`。该实验排除了“只因PiP没有按同样格式训练”的主要替代解释；禁止继续训练混合PiP、改变叠加样式或在Confirm/E-VAds Test补救。远端根目录：`evaluation/runs/adsqa_sft_lora_groupcv500_v1/train_matched_pip8_v1/`；关键文件为`oof500_v1/fold_{0..4}/{asr_ocr_train,random_train}/`、`oof500_v1/groupcv_train_matched_protocol_audit.json`、`judge_deepseek_legacy_v1/{dry_run_audit.json,results.jsonl,summary.json,SHA256SUMS}`。

### 训练匹配 Independent RegionToken8 LoRA 三臂 OOF（2026-07-22，正式负结果）

| 字段 | 内容 |
|---|---|
| 要检验的问题 | 在PiP失败后，独立完整区域图像Token能否比同图叠加局部像素更有效地传递局部证据 |
| 数据与基座 | AdsQA Train-500、100视频、视频级五折OOF；干净 `Qwen2.5-VL-7B-Instruct`，每折从头训练语言侧LoRA，非AdsQA/ReAd-R权重 |
| 共同协议 | 每折400题/80视频训练、100题/20视频验证；训练与推理均为8个448视图、实际`1,024`视觉Token（上限`4,096`）、无padding、关闭二次采样、冻结视觉编码器 |
| 干预与控制 | 保持Raw8时间位置；将answer-free ASR/OCR清单中的至多2个位置替换为全尺寸局部图像。随机臂与证据臂严格共享题目、帧位置和区域数量，仅替换区域内容 |
| 输入隔离 | 清单仅读取问题、ASR、OCR和帧索引；不读取答案、groundtruth、标签或裁判结果 |
| 审计 | 两个新臂各`500/500`预测、错误`0`；5折权重、帧对齐、8视图/Token、无二次采样和三臂联合审计均`passed=true` |
| 裁判 | 冻结历史DeepSeek answer-only；复用Raw8历史分数，新增`525`个唯一请求；`not_human_gold=true`；10,000次视频聚类Bootstrap |

| 方法 | Strict | Relaxed |
|---|---:|---:|
| 冻结 `AdsSFTLoRA_Raw8` | 21.4% | 40.1% |
| 训练匹配 `RandomRegionToken8` | 21.2% | 40.4% |
| 训练匹配 `ASR/OCR-RegionToken8` | 20.8% | 40.5% |

| 配对比较 | Strict差值 | Relaxed差值 | Relaxed 95% CI | 结论 |
|---|---:|---:|---|---|
| `RandomRegionToken8 - Raw8` | `-0.2 pp` | `+0.3 pp` | `[-1.7,+2.3] pp` | 无可辨别效应 |
| `ASR/OCR-RegionToken8 - Raw8` | `-0.6 pp` | `+0.4 pp` | `[-1.9,+2.7] pp` | 点估计微弱、无稳定增益 |
| `ASR/OCR-RegionToken8 - RandomRegionToken8` | `-0.4 pp` | `+0.1 pp` | `[-2.1,+2.4] pp` | 证据区域未超过随机区域控制 |

裁决：`candidate_failed_independent_region_token`。这条结果排除了“PiP叠加遮挡上下文”与“PiP训练/推理表示失配”两种主要替代解释，但不支持当前ASR/OCR局部区域在固定8视图预算下带来稳定QA增益。禁止继续扫描裁剪框、区域数量、训练轮数或LoRA超参数，也不进入Confirm-3000/E-VAds Test补救。远端根目录：`evaluation/runs/adsqa_sft_lora_groupcv500_v1/train_matched_region8_v1/`；关键文件为`oof500_v1/groupcv_train_matched_protocol_audit.json`及`judge_deepseek_legacy_v1/{dry_run_audit.json,results.jsonl,summary.json,SHA256SUMS}`。

### 预注册：`AV-Funnel8 v1` 四臂工程 Smoke（2026-07-22，未出结果）

| 字段 | 冻结内容 |
|---|---|
| 状态 | 实现中；只运行20题工程 smoke，尚未调用裁判或作准确率选择 |
| 理论来源 | Visual Funnel 的层级上下文组合思想；不是其内部注意力模块的直接复现 |
| 共同协议 | 干净 `Qwen2.5-VL-7B-Instruct`，32共享全局帧 + 8新增视图，896，40视图，20,480视觉Token，固定Prompt，无RAG/反思/二次采样 |
| 对照臂 | `Shared32_ExtraGlobal8`、`Shared32_Local8`、`Shared32_RandomFunnel8`、`Shared32_AVFunnel8` |
| Funnel结构 | 共享32帧中保留两个完整锚点；新增2个不重复的邻近时序上下文全局帧，另为每个锚点加入焦点/中尺度/广尺度三个嵌套裁剪 |
| 随机控制 | 与证据Funnel逐题共享两个锚点、2个时序上下文帧和6个裁剪尺度；仅裁剪中心替换为确定性随机中心 |
| 定位输入 | 仅问题、视频、既有CLIP响应、OCR/ASR及帧索引；禁止答案、标签、预测与裁判结果进入清单 |
| smoke门禁 | 四臂20条完整、错误0、共享32帧一致、40视图/20,480 Token、嵌套关系/非重复帧/随机控制逐题审计均通过 |
| 后续 | smoke只验证工程与公平性；通过后再单独冻结正式开发/确认数据与统计方案 |

#### 工程 smoke 结果（2026-07-23）

| 字段 | 结果 |
|---|---|
| 首次实现检查 | `smoke20_v2` 发现随机 Funnel 三尺度使用不同中心，19/20 不满足嵌套；作为工程失败产物保留，未进入答案评测 |
| 修正 | 每个锚点固定一个确定性随机中心，焦点/中尺度/广尺度共享该中心 |
| 最终运行 | `smoke20_v3`，四臂均 `20/20`，错误均 `0` |
| 视图与 Token | 四臂逐题均为 `40` 视图、`20,480` 视觉 Token；共享32帧逐题一致 |
| 公平性审计 | 配置签名一致；AV/随机臂锚点、上下文帧和尺度一致、中心不同；嵌套与非重复帧检查全通过 |
| 审计文件 | `evaluation/runs/innovation1_avfunnel8_groupcv500_v1/smoke20_v3/protocol_audit_v1.json`，`passed=true` |
| 清单 SHA256 | `b4e79150a72084a05ad080b11f0c13ced62c390ab1cf3037576c0b345f8194de` |
| 裁判与结论 | 未调用答案裁判；仅完成工程/视觉协议验证，不能报告准确率或选择最优臂 |
| 后续门禁 | 仅能在未使用、视频隔离的 E-VAds SFT 开发集冻结候选；已用 Test-500 不得用于调参或筛选 |

### E-VAds SFT-Dev100：AV-Funnel8 工程验证（2026-07-23）

| 字段 | 冻结内容/结果 |
|---|---|
| 开发来源 | 官方 E-VAds SFT；不使用已暴露的 Test-500，RL 保留不参与当前选择 |
| 可用规模 | SFT `1,880` 题、`376` 视频，每视频恰 `5` 题 |
| 冻结开发集 | `100` 视频、`500` 题，8 类按比例确定性抽样 |
| 视频隔离 | 与官方 Test `3,389` 视频重叠 `0`；64 帧/Raw32 缓存覆盖 `100/100` |
| 输入隔离 | 构建仅读取 `data_source/videos/prompt/ability/extra_info`；不读取 `answer`、reward、ground truth 或历史预测 |
| 数据审计 | `data/external/evads_v1/experiments/avfunnel8_sftdev100_v1/dataset/audit.json`，`passed=true`；问题 SHA256=`07027634cab5824e84fc7a01271702395b1eca74585291ccf694b4ff46ca2503` |
| Smoke 候选 | 20题/4视频的 SigLIP 与 AV-Funnel 清单均通过 answer-free 结构审计 |
| Smoke 四臂 | `Shared32_ExtraGlobal8`、`Shared32_Local8`、`Shared32_RandomFunnel8`、`Shared32_AVFunnel8` |
| 推理协议 | 四臂各20题完成、错误0、40视图、20,480 Token、共享Raw32一致、关闭二次采样；`qwen_smoke20/protocol_audit.json` 为 `passed=true` |
| 裁判与结论 | 未读参考答案、未调用DeepSeek；仅证明工程和公平性，尚无准确率结论 |
| 后续 | 在冻结 Dev100 完成500题四臂推理与协议审计后，才可用私有参考侧作一次开发评测；不得回到旧 Test-500 挑方法 |

### E-VAds SFT-Dev100：AV-Funnel8 冻结开发评测（2026-07-23，负结果）

| 字段 | 冻结内容/结果 |
|---|---|
| 评测范围 | 同一 SFT-Dev100 的 `500` 题/`100` 视频；该开发集与官方 Test 视频零重叠 |
| 40视图方法 | `Shared32_ExtraGlobal8`、`Shared32_Local8`、`Shared32_RandomFunnel8`、`Shared32_AVFunnel8`；每臂 `500/500`、错误 `0` |
| 共同协议 | 干净 `Qwen2.5-VL-7B-Instruct`、官方 Prompt、40实际视图、`20,480` 视觉Token、无二次采样；主推理审计 `passed=true` |
| 裁判隔离 | 推理审计通过后才从官方SFT Parquet生成 `500` 条私有参考；回答输入未读取答案，裁判结果均标记 `not_human_gold=true` |
| 裁判恢复 | 原DeepSeek裁判缓存后遇到一条非标准格式响应停止；保留 `1,039` 条缓存后，以同Prompt/模型补 `420` 次，其中严格格式 `417`、唯一合法分数回退 `3`；不保存原始响应或密钥 |
| `ExtraGlobal8` | R5/R3/R2=`56.05/43.90/17.20%` |
| `Local8` | R5/R3/R2=`55.05/42.30/16.60%` |
| `RandomFunnel8` | R5/R3/R2=`54.90/42.00/16.20%` |
| `AVFunnel8` | R5/R3/R2=`55.05/42.70/15.40%` |
| 关键配对结果 | `AVFunnel8 - ExtraGlobal8`：R5=`-1.00 pp`，视频聚类10,000次Bootstrap 95% CI=`[-2.35,+0.35] pp`；R3=`-1.20 pp`，CI=`[-3.00,+0.50] pp`；R2=`-1.80 pp`，CI=`[-3.00,-0.60] pp` |
| Funnel内容性 | `AVFunnel8 - RandomFunnel8`：R5=`+0.15 pp`，CI=`[-1.05,+1.35] pp`；R3=`+0.70 pp`，CI=`[-0.80,+2.20] pp`；R2=`-0.80 pp`，CI=`[-1.80,0.00] pp`，未超过随机中心控制 |
| 裁决 | `candidate_failed_evad_sftdev100_avfunnel_v1`：不进入 Test-500B；不在此开发集扫描裁剪尺度、ASR/OCR权重、锚点数或Prompt |
| 标准32视图表 | 两臂各`500/500`、错误`0`，32视图/16,384视觉Token审计通过；`Uniform32` R5/R3/R2=`55.40/43.40/16.00%`，`SigLIPTopK32`=`55.45/43.10/16.00%` |
| 标准表配对结果 | `SigLIPTopK32 - Uniform32`：R5=`+0.05 pp`，95% CI=`[-1.85,+1.95] pp`；R3=`-0.30 pp`，CI=`[-2.60,+2.00] pp`；R2=`0.00 pp`，CI=`[-2.20,+2.20] pp`，无稳定检索增益 |

远端复现根目录：`data/external/evads_v1/experiments/avfunnel8_sftdev100_v1/`。主审计为`qwen_full500/protocol_audit.json`；私有参考审计为`private_references/audit.json`；40视图裁判为`qwen_full500/judge_deepseek_v1/{results.jsonl,summary.json,judge_cache.jsonl,parser_repair_audit.json,wrapper_sha256.txt,repair_parser_sha256.txt}`。32视图裁判为`standard_full500/{protocol_audit.json,judge_deepseek_standard_pair_v1/results.jsonl,judge_deepseek_standard_pair_v1/summary_v2.json}`；`summary_v2.json`从冻结逐题结果重算，不新增API调用，仅修正初版摘要中R3/R2比较字段名。

### Candidate F：LLM 替代复核 smoke（2026-07-23，停止，不是正式评测）

| 字段 | 内容 |
|---|---|
| 目的 | 验证两个隔离本地视觉模型能否作为 Candidate F 人工双复核的前置可行性检查；不训练、不评测QA准确率 |
| 输入 | Calibration240 人工模板的确定性 5 条子集；仅问题、Raw32答案、ASR、32帧联系表和原子声明；无参考答案、标签、历史裁判或交叉输出 |
| 模型 | Qwen3-VL-8B（GPU1）与干净 `Qwen2.5-VL-7B-Instruct`（GPU2）；各自独立输出 |
| 结构审计 | 两臂均 `5/5` 有效；帧号、ASR 原文锚点、联系表、模板哈希与输出字段通过；原人工模板未改写 |
| 标签分布 | Qwen3：supported/refuted/insufficient=`5/0/0`；Qwen2.5=`0/0/5` |
| 一致性 | 相同5条 claim ID 完整对齐，三分类 agreement=`0.00`；不具备扩展至240条的可用一致性 |
| 裁决 | 停止于 smoke；不做240条扩展、不计算伪人工一致性、不做阈值校准、不跑 Development244 |
| 口径 | 全部为 `machine_only=true`、`not_human_gold=true`，不能替代双人工金标；Candidate F 仍需原定人工一致性门槛后才可进入下一步 |
| 远端路径 | `evaluation/runs/innovation2_stage2_modality_cf_v1/candidate_F_answer_conditioned_calibration_v1/llm_substitute_smoke_v3.md`；`candidate_F_llm_substitute_qwen3_smoke5_v3/`；`candidate_F_llm_substitute_qwen25_smoke5_v3/` |

同一盲包的 GPT-5/Codex 独立复核相对Qwen3得到 `4/5=0.80` observed agreement，优于 Qwen2.5；但Qwen3五条均为 supported，Codex 为 `4 supported/1 insufficient`，导致三分类 Cohen's kappa=`0.00`且无负向共识。该结果仅说明 Qwen3+Codex 比 Qwen3+Qwen2.5 更适合作为探索性双模型审阅；不得替代人工标注或作为 Candidate F 的开发门禁。复现：`candidate_F_llm_substitute_codex_smoke5_v1/{llm_substitute_review.jsonl,qwen3_comparison.json}`。

### Candidate F：GPT-5/Codex 机器替代盲审 80/80（2026-07-23，仅覆盖审计）

| 字段 | 内容 |
|---|---|
| 复核范围 | `Calibration240` 预定义盲包的 `80` 条 pilot；`31` 个视频；盲包 SHA256=`97fa1f141955e6ed31e30f85cb57ed56e29a6a4e6c9d653e3bb38901e4772487` |
| 可见输入 | 仅问题、Raw32候选答案、ASR、帧索引、联系表和原子声明；不读取私有选择清单、参考答案或Qwen3逐题标签 |
| 完整性 | `80/80` 位置唯一且全部覆盖；批次 `01–16` 哈希写入审计；输出结构、盲包映射、`machine_only/not_human_gold` 和禁用校准/Development字段均通过 |
| 本轮标签分布 | `supported=60`、`insufficient=20`；无 `refuted`。这只是本助手的机器替代判断，不代表真实类别分布 |
| 审计 | 远端 `evaluation/runs/innovation2_stage2_modality_cf_v1/candidate_F_qwen3_codex_pilot80_v1/codex_machine_review_audit.json`，SHA256=`87ae8df58b9025f22063d28b5b9484bb8be2cf9267fb703b6a64ebdf24b0db4f`，`passed=true`，并明确 `private_manifest_read=false` |
| 约束 | 所有输出固定为 `machine_only=true`、`not_human_gold=true`、`threshold_calibration_allowed=false`、`development_evaluation_allowed=false` |
| 裁决 | 不可用来训练验证器、校准阈值、选择模型或放行 `Development244`；Candidate F 仍需两位独立人工复核、agreement>=0.80、Cohen's kappa>=0.60且至少20条负向共识 |

### Candidate F：GPT-5/Codex 第二轮机器替代复核（2026-07-23，仅覆盖审计）

| 字段 | 内容 |
|---|---|
| 复核范围 | 同一盲包预定义 `80` 条 pilot；第二轮不读取第一轮逐题标签、私有选择清单或参考答案 |
| 完整性 | `16` 批次、`80/80` 唯一位置、盲包 SHA256 一致；早期批次残留的8条旧哈希已修正并重新审计 |
| 本轮标签分布 | `supported=71`、`insufficient=9`、`refuted=0`；仅为机器替代判断，不代表人工类别分布 |
| 与第一轮比较 | 逐题一致 `65/80=81.25%`，差异 `15` 条；不能换算为人工 agreement 或 Cohen's kappa |
| 协议字段 | `machine_only=true`、`not_human_gold=true`、`threshold_calibration_allowed=false`、`development_evaluation_allowed=false`；坏标记 `0` |
| 远端产物 | `evaluation/runs/innovation2_stage2_modality_cf_v1/candidate_F_qwen3_codex_pilot80_v1/codex_pass2_batches/`；审计 `codex_machine_review_pass2_audit.json` |
| 规范化结果 SHA256 | `c4dcbf21d92c486c113ea659b11572b4b76d595faafcd8a76e2a2762ecde84cc` |
| 结论 | 只能用于探索性错误分析或人工复核优先级提示；不能训练验证器、校准阈值、选择模型或放行 `Development244` |

### ReAd-R Qwen2.5 本地历史预测的统一 answer-tag-only 重评 v2（2026-07-24）

| 字段 | 内容 |
|---|---|
| 模型 | AdsQA 官方 GRPO 训练 checkpoint：`Qwen2.5-7B-VL-ReAd-R`；不是本文干净 `Qwen2.5-VL-7B-Instruct` 或 Qwen3 主方法 |
| 预测来源 | 历史 archive 的 ReAd-R 预测；构建阶段只取非空 `<answer>...</answer>` 内容作为候选答案 |
| 裁判 | 已完成的 DeepSeek answer-only 裁判输出；实际响应模型 `deepseek-v4-flash`，`not_human_gold=true` |
| 新 API 调用 | `0`。v2 只对已完成逐题评分做去重、标签资格过滤、审计和视频簇统计，不修改 v1 原始结果 |
| 原始 GT | `7,859` 行、`7,846` 个唯一 question ID；其中 `13` 个重复 ID 的 question/answer/video/question_type 等核心字段完全一致，按历史评测器语义保留最后一行 |
| 源预测覆盖 | `7,829` 个唯一题目有已裁判预测；相对唯一 GT 缺失 `17` 题 |
| 严格候选资格 | 另排除 `5` 条未抽到非空 `<answer>` 的历史预测；最终有效 `7,824/7,846=99.72%` |
| Score 分布 | `0/0.5/1 = 1784/3707/2333` |
| Strict / Relaxed | `29.82% / 53.51%` |
| 视频簇 Bootstrap | `1,539` 视频、`10,000` 次、seed `42`；Strict 95% CI=`[28.63%,31.02%]`，Relaxed 95% CI=`[52.45%,54.55%]` |
| 审计 | `passed=true`；result/staging ID 对齐、评分重复行同分、GT 重复核心字段无冲突、所有有效行均有视频且分数合法 |
| 复现产物 | `evaluation/runs/rejudge_readr_answeronly_v1/full/judge_deepseek_legacy_answer_tag_only_v2/`；脚本 `evaluation/tools/postprocess_readr_answer_tag_only_v2.py` |

**使用边界：** 此表是“AdsQA 已有训练方法的本地、当前裁判参考”，可进入跨模型参考表；它与本文主方法的模型底座、输入（历史 8 图 + ASR）、训练状态和视觉预算不同，不能与同底座固定预算主表混排后宣称公平领先。此前的 `34.60%/48.10%` 属于历史自有评测/候选口径，不能与本条严格 `<answer>`、当前 DeepSeek 裁判数字互换或直接比较。

### AdsSFTLoRA_Raw8 OOF 错误来源审计（2026-07-24，未启动新推理）

| 字段 | 结果 |
|---|---|
| 范围 | 干净 Qwen2.5 直接答案 LoRA 的 Train-500 视频级五折 OOF；冻结 A0 预测与历史 answer-only 裁判 |
| 执行 | 只读 GT、预测、裁判、视频、ASR 与 OCR；GPU/API 调用均为 `0`，历史结果未修改 |
| 错题 | `393/500` 非完全正确：0分 `206`、0.5分 `187`，跨100视频 |
| 分层样本 | `180` 条；score×fold 确定性抽样，seed `20260724`，最多2题/视频，覆盖97视频 |
| 来源覆盖 | 样本与全量错题均100%有视频、成功分段ASR和OCR cache；这只证明缓存存在，不证明证据可解题 |
| 新证据候选 | OCR答案内容词强重合 `84/393`；ASR强重合仅 `37/393`，而所有问题已内嵌完整 Voiceover，ASR-RAG不构成独立知识 |
| 外部/背景风险 | `143/393` 只在审计用 meta_info 出现强词重合；禁止将 meta_info、网页或 campaign 文案直接作为回答证据 |
| 决策 | 暂不做泛化 RAG；唯一允许的新候选是带可回指 OCR 引用的选择性反思，先50题工程 smoke，再300题开发门禁 |

详细来源、样本、代表错误和预注册停止规则原见《错误来源审计与选择性反思决策》（历史来源，未收入本去重归档）。语义类别尚待独立视觉/人工复核，所有当前统计均不是人工金标。

### OCR 约束反思 Smoke-50（2026-07-24，负结果，不扩展）

| 字段 | 内容 |
|---|---|
| 目的 | 检验“视频内 OCR 证据 + 选择性反思”能否纠正 `AdsSFTLoRA_Raw8` 的答案错误；不使用网页/RAG/`meta_info` 或外部知识 |
| 范围 | 10个视频、50个 Train-500 五折 OOF题目；每折2个完整视频包，选择仅依赖 OCR cache 质量与确定性哈希，属 OCR-enriched exploratory smoke，不是确认集 |
| A0 | 冻结 `AdsSFTLoRA_Raw8` 既有逐题预测，未重跑 |
| A1 | 同一干净 `Qwen2.5-VL-7B-Instruct` + 对应fold LoRA；8实际视图、448、4,096视觉Token、关闭二次采样；输入仅冻结问题/视频帧/A0/OCR文字及其帧号时间戳框，不读单独ASR、`meta_info`、答案或历史分数 |
| A2 | 不额外推理；仅当A1给出有效OCR索引且改答与引用OCR有非停用词内容词直接重合才接受，否则保留A0 |
| A1 完整性 | 五折50/50，错误0；A1改答4条，解析回退保持A0的条目已计入 |
| A0 Strict / Relaxed | 18.00% / 40.00% |
| A1 Strict / Relaxed | 14.00% / 38.00%；相对A0 Strict=-4.00pp，视频簇10,000次Bootstrap CI=[-10.00,0.00]pp；Relaxed=-2.00pp，CI=[-7.00,+2.00]pp |
| A1 纠错/伤害 | wrong→right=0，right→wrong=2，correction precision=0，trigger rate=8.00%，harm rate=22.22%；一条0→0.5的部分改善不构成完整纠正 |
| A2 Strict / Relaxed | 18.00% / 40.00%，与A0逐题完全一致；trigger=0，wrong→right=0，right→wrong=0 |
| 裁判 | 冻结历史 answer-only DeepSeek Prompt/解析；实际响应模型 `deepseek-v4-flash`；150方法记录按同题同答去重为54请求，54/54成功、重试0，返回34,701 prompt +264 completion =34,965 total tokens；服务响应未报告货币费用；`not_human_gold=true` |
| 裁决 | `candidate_failed_ocr_constrained_reflection_smoke50_v1`；禁止扩到300开发集、禁止放宽门控/Prompt扫描，不能写为创新点二的已验证精度贡献 |
| 远端复现 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/ocr_constrained_reflection_smoke50_v3/{dataset,a1_ungated,a2_evidence_gated,judge_legacy_answeronly_v1}`；历史失败预检v1/v2保留且未覆写 |

### 候选答案 Oracle 与 E-VAds→AdsQA 课程适配 Fold-0（2026-07-26，Fold-0门禁失败）

| 字段 | 内容 |
|---|---|
| Oracle 主结论 | 同一冻结 LoRA 8视图池仅 `+2.20/+2.80 pp` Strict/Relaxed，门禁失败；同预算多 LoRA 适配器池 `+8.80/+10.40 pp`，条件性通过 |
| 最小通过候选 | A0 + `TrainMatched_AsrOcrRegionToken8`；Strict `+3.60 pp`、Relaxed `+5.10 pp` 理论上限 |
| Oracle 路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/candidate_answer_oracle_audit_v2/` |
| E-VAds 预检 | SFT `1880题/376视频`；预适配 `1380题/276视频`；冻结开发 `500题/100视频`；与Test/AdsQA视频及精确文本泄漏均为0 |
| 预检路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/evads_adsqa_curriculum_precheck_v2/`；`audit.json passed=true` |
| Fold-0 训练 | E-VAds 1380步 + AdsQA 400步；干净Qwen2.5、Raw8、448、4096视觉Token、原Prompt、1 epoch、冻结视觉编码器 |
| Fold-0 推理 | `100/100`，错误0；实际/表示视图均为8，无padding，关闭二次采样；与AdsQA-only Fold-0协议匹配 |
| Fold-0 路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/evads_adsqa_curriculum_fold0_v2/` |
| 兼容性校准 | 用户授权20条校准后，当前 `deepseek-v4-flash` 成功解析20/20、重试0，但仅12/20与历史分数一致（60%）；历史/当前 `0/0.5/1` 分布为 `7/7/6` 与 `8/9/3` |
| 调用与用量 | 实际仅调用20条校准；授权范围内82条新样本调用为0；prompt/completion/total Token=`13,399/5,380/18,779` |
| 校准路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/evads_adsqa_curriculum_fold0_v2/judge_compatibility_calibration_v3/`；summary SHA256=`f4e0a169dc4d81642af8d96c36c8b6e0ab351f440bfe8e3c45e622fedbebfdb0` |
| 当前统一重评 | 复用20条当前校准分数；新增80条基线+82条课程独有答案=`162`次调用；18条同题同答案跨方法复用 |
| AdsQA-only Fold-0 | Strict/Relaxed=`17.00/37.50%`；`0/0.5/1=42/41/17` |
| 课程适配 Fold-0 | Strict/Relaxed=`12.00/34.00%`；`0/0.5/1=44/44/12` |
| 配对结果 | 课程胜/平/基线胜=`11/70/19`；Strict/Relaxed差=`-5.0/-3.5 pp`；wrong→right/right→wrong=`4/9` |
| Bootstrap | 20视频、10,000次；Strict差95% CI=`[-12.0,+1.0] pp`，Relaxed差=`[-9.0,+1.5] pp` |
| 调用与用量 | 当前裁判合计182个唯一答案（含20条校准），新增调用162、重试1；prompt/completion/total Token=`121,182/41,928/163,110`，未报告货币费用 |
| 当前评分路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/evads_adsqa_curriculum_fold0_v2/judge_current_paired_v1/`；summary SHA256=`5edf2db2cb0319815602380033924cdaff0c328c0bd4469c79cca74529493b21` |
| 裁决 | `candidate_failed_no_five_fold`；课程适配训练可行，但准确率门禁失败，不启动其余四折 |
| 唯一下一步 | 同预算多适配器候选排序器的CPU可行性、泄漏和成本预检；通过后才设计50题smoke |
| 禁止事项 | 不得把当前分数与历史分数混用；不得启动课程适配其余四折、FreshQ、3000题、RAG/自由反思或新视觉候选 |

详细门禁、失败审计和唯一下一步原见《AdsQA 候选答案与跨数据集课程适配门禁》（历史来源，未收入本去重归档）。

### 同预算多LoRA候选排序器CPU预检（2026-07-26，未放行Smoke）

| 字段 | 内容 |
|---|---|
| 候选 | `AdsSFTLoRA_Raw8` 与 `TrainMatched_AsrOcrRegionToken8`；均为8视图、448、4096视觉Token、同一Prompt，不同折内LoRA |
| 执行 | 500题/100视频；GPU/API调用0；历史预测和分数只读 |
| 泄漏审计 | 输入/标签物理分离；输入不含参考答案、`meta_info`、历史分数或裁判输出；视频级五折train/test交集均为0 |
| 候选关系 | 答案相同202、不同298；Region胜/平/Raw胜=`46/412/42` |
| Raw8 | Strict/Relaxed=`21.40/40.10%` |
| RegionToken8 | Strict/Relaxed=`20.80/40.50%` |
| 两候选Oracle | Strict/Relaxed=`25.00/45.20%`，相对Raw=`+3.60/+5.10 pp` |
| 固定OOF排序器 | Strict/Relaxed=`20.60/40.60%`，相对Raw=`-0.80/+0.50 pp` |
| 转移 | 触发161/500；wrong→right/right→wrong=`8/12`；纠正精度=`40%` |
| Bootstrap | 100视频、10,000次；Strict差95% CI=`[-2.6,+1.0] pp`，Relaxed差=`[-1.3,+2.3] pp` |
| 成本 | 每个额外LoRA约38.54 MiB；回答生成理论约2倍；无可靠实测时延字段 |
| 路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/multiadapter_ranker_cpu_precheck_v1/`；summary SHA256=`7b6c7f252ae124bc1ec2aa0606ebb69fe841348ff2b2451601268dc18d47019d` |
| 裁决 | `freeze_learned_ranker_no_smoke`；不运行50题GPU smoke，Oracle仅作为互补性上限 |

### 结构化证据链与反事实反思 Smoke-50（2026-07-27，未放行Dev300）

| 字段 | 内容 |
|---|---|
| 目的 | 检验自由反思与“原子声明—模态—可追溯引文—E+/E-反事实”结构化证据链能否安全纠正冻结初答 |
| 数据 | 50题、10视频、视频级五折各2视频；排除旧OCR Prompt开发视频；选择过程answer-free |
| 模型与协议 | 干净 `Qwen2.5-VL-7B-Instruct` + 对应折 LoRA；8视图、448、视觉Token不超过4,096、关闭二次采样 |
| 四臂 | A0=`AdsSFTLoRA_Raw8`冻结初答；A1=自由反思；A2=结构化证据链；A3=确定性选择门控 |
| 协议审计 | A1/A2/A3/chain均50条、错误0；E+解析49/50、E-解析50/50；实际证据变化50/50；原始及解析后引用可追溯率100%；`passed=true` |
| 反事实方向 | E+支持且E-不再支持为14/50=28%，低于预注册70%门槛 |
| A0 | Strict/Relaxed=`18/31%` |
| A1 | Strict/Relaxed=`18/31%`；改答19；wrong→right/right→wrong=`1/1`；全部改答完整纠正精度=`5.26%` |
| A2 | Strict/Relaxed=`20/29%`；改答20；wrong→right/right→wrong=`2/1`；相对A0 Strict/Relaxed=`+2/-2 pp` |
| A2 Bootstrap | 10视频、10,000次；Strict差95% CI=`[0,+6] pp`，Relaxed差=`[-7,+3] pp` |
| A3 | 触发0；Strict/Relaxed=`18/31%`，与A0逐题一致；安全但没有纠正收益 |
| 推理成本 | 150次模型调用；平均语言输入约1,751.16 Token，平均输出66.59 Token，平均延迟2.87秒/次，峰值显存16,507.92 MiB |
| 统一裁判 | 用户授权87个唯一答案；`deepseek-v4-flash`，实际87次调用、重试1次、总Token=71,506；`not_human_gold=true` |
| 裁决 | `candidate_failed_no_dev300`；结构化与可追溯工程目标成立，但精度、纠正和反事实方向门禁失败，不扩展Dev300 |
| 远端路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/evidence_chain_cot_smoke50_v2_engineering/` |
| 关键产物 | `protocol_audit.json`、`judge_current_uniform_v1/{summary.json,results.jsonl,paired_results.jsonl,manifest.json}`、`failure_attribution.{json,md}`、`CANDIDATE_FAILED`、`FINAL_SHA256SUMS` |

**论文使用边界：** 可以报告“结构化证据链实现了100%引用回指和可审计反事实输入”，但不能声称其提高QA精度；A2的Strict `+2 pp`必须与Relaxed `-2 pp`及置信区间同时报告。A3零触发说明当前门控过于缺乏可满足的候选声明证据，而不是一个有效的无伤纠错器。

### CF-EPO反事实奖励证据策略（2026-07-27，正式失败）

| 字段 | 内容 |
|---|---|
| 目的 | 将反事实充分性作为固定预算证据选择训练奖励，而不是回答后反思 |
| 数据 | AdsQA Train-500、100视频、视频隔离五折；每折100题 |
| 候选与动作 | 每题64帧候选，8个时间八分区各选1帧；8组冻结E+轨迹，每组2个同八分区E- |
| 奖励模型 | 干净Qwen2.5对应折`AdsSFTLoRA_Raw8`；该LoRA未见当前题及视频 |
| 策略 | 两层64维Temporal Transformer；`CEPO-QA8`与`CEPO-QACF8`；每折3固定seed集成 |
| 轨迹审计 | 500题、4000组E+、8000组E-；输入/目标物理分离；视频交集0；全部E-真实替换 |
| Fold修复 | 旧CP-AVR fold字段与LoRA折425/500不一致；以LoRA验证文件所在目录作为唯一折归属 |
| Smoke-20 | 160组轨迹、480次视觉输入、错误0；20/20题反事实信号非零；协议通过 |
| 全量奖励缓存 | 4000组轨迹、12000次视觉输入、错误0；每次8视图、1024视觉Token、无二次采样 |
| 全量反事实信号 | `counterfactual_drop`均值=`-0.0002593`；正向比例=`48.90%`，尚不支持E-总体稳定有效 |
| OOF推理 | 两方法各500/500，错误0；协议各500/500通过 |
| 裁判去重 | 两种CEPO的1000行→871个唯一对；与Raw8三方法同批重评共1269个唯一调用（102个跨方法同答复用） |
| 禁止历史复用 | 当前端点与历史批次20条校准仅60%一致，本轮历史分数复用0 |
| 发送字段 | 冻结裁判Prompt包含`meta_info`、题目、参考答案和候选答案；不发送视频、图像、OCR/ASR缓存或模型 |
| 裁判执行 | 用户授权1269次；实际1269/1269成功，均为`deepseek-v4-flash`；总Token=`876,263`；`not_human_gold=true` |
| Raw8 | Strict/Relaxed=`21.6/40.4%` |
| CEPO-QA8 | Strict/Relaxed=`19.8/41.1%`；相对Raw=`-1.8/+0.7 pp` |
| CEPO-QACF8 | Strict/Relaxed=`20.0/41.2%`；相对Raw=`-1.6/+0.8 pp` |
| QACF vs Raw Bootstrap | Strict差95% CI=`[-4.6,+1.4] pp`；Relaxed差=`[-1.9,+3.5] pp` |
| QACF vs Raw 转移 | `wrong→right/right→wrong=28/36`，伤害多于完整纠正 |
| QACF vs QA | Strict/Relaxed=`+0.2/+0.1 pp`；区间均跨0 |
| 最终E+/E- | QA/QACF反事实下降均值=`0.00346/0.00544`，正向率=`51.2/53.6%` |
| 反事实差Bootstrap | QACF- QA=`+0.00198`，95% CI=`[-0.00321,+0.00738]` |
| 裁决 | `candidate_failed_no_confirm_no_parameter_scan`；不进确认集，不扫描奖励或模型参数 |
| 远端路径 | `evaluation/runs/innovation1_cfepo_groupcv500_v1/` |
| 关键文件 | `reward_full500_v1/audit.json`、`judge_deepseek_current_batch_v1/summary.json`、`final_policy_reward_eval_v1/{reward_audit.json,analysis.json}` |

### Anchor6+CEPO2风险约束证据重分配（2026-07-27，Dev-100门禁失败）

| 字段 | 内容 |
|---|---|
| 目的 | 修复全量CEPO替换破坏Raw8时间覆盖的问题；保留8个Raw锚点，仅在高共识时最多替换2槽 |
| Dev划分 | 20视频、100题；每折对验证视频按`SHA256(anchor6-dev100-v1:video_id)`排序取前4视频，每折20题 |
| Smoke | 每折前4题，共20题；三候选60/60有效、错误0，协议通过 |
| 模型 | 干净`Qwen2.5-VL-7B-Instruct` + 对应折冻结`AdsSFTLoRA_Raw8` |
| 公平协议 | 8个448全帧视图、实际1,024视觉Token、最多4,096、同Prompt、关闭二次采样 |
| CLIP2清单 | 100题均替换2槽，平均2.00 |
| CEPO-QA2清单 | 平均替换0.92槽；0/1/2替换题数=`36/36/28` |
| CEPO-QACF2清单 | 平均替换1.03槽；0/1/2替换题数=`24/49/27` |
| Dev推理 | 三候选各100/100、错误0；逐题帧号、未替换锚点、视图和Token审计通过 |
| Raw8 | Strict/Relaxed=`21.0/38.0%` |
| Anchor6+CLIP2 | Strict/Relaxed=`15.0/37.5%`；相对Raw=`-6.0/-0.5 pp` |
| Anchor6+CEPO-QA2 | Strict/Relaxed=`21.0/38.0%`；相对Raw=`0.0/0.0 pp` |
| Anchor6+CEPO-QACF2 | Strict/Relaxed=`21.0/42.0%`；相对Raw=`0.0/+4.0 pp` |
| QACF vs Raw Bootstrap | 20视频、10,000次；Strict差95% CI=`[-5.0,+5.0] pp`，Relaxed差=`[-0.5,+8.5] pp` |
| QACF vs Raw转移 | Relaxed胜/平/负=`11/84/5`；Strict wrong→right/right→wrong=`3/3` |
| QACF vs CLIP | Strict/Relaxed=`+6.0/+4.5 pp`；Strict CI=`[+1.0,+11.0] pp`，Relaxed CI=`[-1.0,+9.5] pp` |
| 当前批裁判 | 四方法400行按同题同答去重为236调用；实际236/236；`deepseek-v4-flash`；总Token=`158,971`；历史分数复用0；`not_human_gold=true` |
| 预注册门禁 | 仅`wrong→right > right→wrong`失败，其他四项通过；不得事后放宽 |
| 正式裁决 | `candidate_failed_no_confirm_no_parameter_scan`；当前候选不进入Confirm-300 |
| 开发期归因 | 0替换24题完全同Raw；1替换49题Relaxed `+1.02 pp`、5胜5负；2替换27题Relaxed/Strict=`+12.96/+7.41 pp`、6胜21平0负 |
| 下一假设边界 | 可新预注册`DualConsensus2-or-Raw8`：只有恰有两个三seed共识槽位才替换，否则Raw8；该规则由Dev产生，只能在独立确认集验证 |
| 远端路径 | `evaluation/runs/innovation1_anchor6_cepo2_dev100_v1/` |
| 关键文件 | `dataset/audit.json`、`dev100/protocol_audit.json`、`judge_deepseek_current_batch_v1/summary.json`、`final_analysis_v1/{diagnostics.json,FINAL_DECISION.json,failure_attribution.md}` |

### DualConsensus2-or-Raw8 独立 Confirm-D300（2026-07-27，确认失败）

| 字段 | 内容 |
|---|---|
| 假设来源 | Dev-100 中双共识替换 27 题为 6胜/21平/0负；作为事后发现重新预注册，未回填旧实验 |
| 训练 | Train-500、100视频；最终答案 LoRA 为干净 Qwen2.5、Uniform8、448、实际1,024 Token、1 epoch；三个 QACF selector seed=`2026072711/12/13` |
| 确认集 | 冻结 Confirm-D300，300题/300视频；五个主类型各60；与 Train-500 视频重叠0 |
| 冻结规则 | 至少两个槽位获得三 seed 一致且平均 logit top-1 的非Raw、非重复候选时，只替换 margin 最高两槽；否则精确 Raw8 |
| 清单审计 | 触发97、回退203；替换数0/1/2题数=`203/0/97`；8视图、唯一帧和回退逐帧一致全部通过 |
| 最终模型 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct` + `full_answer_lora_v2/adapter` |
| 推理协议 | 两方法各300/300，错误0；同模型/LoRA/Prompt；8个448全帧；实际视觉Token恒为1,024；关闭二次采样 |
| Raw8 | Strict/Relaxed=`19.33/39.50%`；`0/0.5/1=121/121/58` |
| Dual | Strict/Relaxed=`19.00/37.83%`；`0/0.5/1=130/113/57` |
| 配对结果 | Dual−Raw Strict/Relaxed=`-0.33/-1.67 pp`；胜/平/负=`10/272/18`；wrong→right/right→wrong=`8/9` |
| Bootstrap | 300视频、10,000次；Relaxed差95% CI=`[-3.83,+0.50] pp`；Strict差=`[-3.00,+2.33] pp` |
| 触发子集 | 97题；胜/平/负=`10/69/18`；Relaxed=`-5.15 pp`，Strict=`-1.03 pp` |
| 类型分层 | Type1–5 Relaxed点差=`-3.33/-0.83/-1.67/-1.67/-0.83 pp`；没有类型低于-5 pp，但总体主门禁失败 |
| 裁判 | 当前批 DeepSeek answer-only；600行去重为365调用；实际365/365；总Token=`226,916`；历史分数复用0；`not_human_gold=true` |
| 裁决 | `candidate_failed_no_confirmd_tuning`；Relaxed增益和Strict安全门禁失败，禁止在Confirm-D继续调参 |
| 远端路径 | `evaluation/runs/innovation1_dualconsensus_confirmd300_v1/` |
| 关键文件 | `dataset_v3/audit.json`、`manifests_v1/audit.json`、`confirm300_v1/protocol_audit.json`、`judge_deepseek_current_batch_v1/summary.json`、`final_analysis_v1/FINAL_DECISION.json` |
| 哈希 | summary SHA256=`88198b0e79ae33d3532988f8ce3f4a64d36a9db26a809600e4ab6ec310cf54dd` |

### Qwen3-VL 直接答案 LoRA 五折 GroupCV-500（2026-07-27，混合结果，门禁失败）

| 字段 | 内容 |
|---|---|
| 目的 | 检验Qwen3直接答案LoRA是否同时优于干净Qwen3和既有Qwen2.5直接答案LoRA |
| 数据 | AdsQA Train500，100视频；视频隔离五折，每折400题/80视频训练、100题/20视频验证 |
| Qwen3基座 | 干净`<MODEL_ROOT>/Qwen3Vl-8B`，原生`Qwen3VLForConditionalGeneration` |
| 训练 | 语言侧q/k/v/o LoRA，rank/alpha/dropout=`16/32/0.05`，lr=`5e-5`，1 epoch，seed=`2026072202`；视觉编码器冻结 |
| Qwen3公平协议 | Clean与LoRA均8个Raw视图、512输入、实际1,024视觉Token、同Prompt、关闭二次采样 |
| Qwen2.5对照口径 | 同为8视图和实际1,024视觉Token；模型架构与输入分辨率不同，属于Token公平而非像素同构比较 |
| 工程结果 | Clean Qwen3和Qwen3-LoRA各500/500、错误0；五折视频隔离、权重变化、输入和Token审计全部通过 |
| Clean Qwen3 | Strict/Relaxed=`26.0/41.2%`；`0/0.5/1=218/152/130` |
| Qwen3-LoRA | Strict/Relaxed=`24.0/42.3%`；`0/0.5/1=197/183/120` |
| Qwen2.5-LoRA | Strict/Relaxed=`21.4/40.2%`；`0/0.5/1=205/188/107` |
| Qwen3-LoRA vs Clean Qwen3 | Strict/Relaxed=`-2.0/+1.1 pp`；95% CI=`[-6.8,+2.8]/[-2.8,+5.1] pp` |
| Qwen3-LoRA vs Clean 转移 | 胜/平/负=`128/261/111`；Strict wrong→right/right→wrong=`63/73`；纠正精度=`46.32%` |
| Qwen3-LoRA vs Qwen2.5-LoRA | Strict/Relaxed=`+2.6/+2.1 pp`；95% CI=`[-1.2,+6.4]/[-0.7,+4.9] pp` |
| Clean Qwen3 vs Qwen2.5-LoRA | Strict/Relaxed=`+4.6/+1.0 pp`；95% CI=`[-0.4,+9.6]/[-3.0,+5.1] pp` |
| 裁判 | 三方法1500行按同题同答去重为1494调用；实际1494/1494；`deepseek-v4-flash`；总Token=`1,142,053`；历史分数复用0；`not_human_gold=true` |
| 裁决 | `freeze_qwen3_lora_result_no_hyperparameter_scan`；Relaxed略升但Strict下降，不采用Qwen3-LoRA为新的已验证最佳基座 |
| 论文解释 | Qwen3基座提高完整正确率的信号强于LoRA收益；当前直接答案LoRA把部分0分推至0.5分，但损失更多满分答案 |
| 远端路径 | `evaluation/runs/qwen3_adsqa_lora_groupcv500_v1/` |
| 关键文件 | `oof500_v1_audit/groupcv_oof_protocol_audit.json`、`judge_deepseek_current_batch_v1/{dry_run_audit.json,api_results_partial.jsonl,results.jsonl,summary.json,SHA256SUMS}` |
| 哈希 | summary SHA256=`f4cff26692fdcb4abf515be744833e9a747c9231024cbf3fdac9984b7c01b2b6` |

### 四模型当前批次基座决策（2026-07-27）

| 字段 | 内容 |
|---|---|
| 目的 | 在同一当前DeepSeek批次下复核Qwen2.5内部LoRA增量，并冻结Qwen2.5/Qwen3基座分工 |
| 新增评分 | 只评分Clean Qwen2.5的500条；Qwen2.5-LoRA精确复用刚完成的当前批500条；新增500/500成功 |
| Clean Qwen2.5 | Strict/Relaxed=`20.4/36.6%` |
| Qwen2.5-LoRA | Strict/Relaxed=`21.4/40.2%` |
| Qwen2.5 LoRA增量 | Strict/Relaxed=`+1.0/+3.6 pp`；95% CI=`[-3.2,+5.2]/[+0.1,+7.1] pp` |
| Qwen2.5转移 | wrong→right/right→wrong=`57/52`；Relaxed胜/平/负=`112/295/93` |
| Clean Qwen3 | Strict/Relaxed=`26.0/41.2%` |
| Qwen3-LoRA | Strict/Relaxed=`24.0/42.3%`；相对Clean Qwen3=`-2.0/+1.1 pp` |
| Clean Qwen3 vs Clean Qwen2.5 | Strict/Relaxed=`+5.6/+4.6 pp`；95% CI=`[+1.2,+10.0]/[+1.0,+8.3] pp` |
| 基座裁决 | Qwen2.5-LoRA作为主要可训练回答基线；Clean Qwen3作为强冻结基线；Qwen3-LoRA不替换主基座 |
| 双模型Oracle | Clean Qwen3 + Qwen2.5-LoRA的Strict/Relaxed上限=`36.4/54.7%`；仅为私有分数事后上限 |
| 四模型Oracle | Strict/Relaxed=`47.2/64.4%`；仅作互补诊断，不是可部署结果 |
| 远端路径 | `evaluation/runs/base_model_decision_current_batch_v1/` |
| Qwen2.5重评路径 | `evaluation/runs/adsqa_sft_lora_groupcv500_v1/judge_deepseek_current_batch_v2/` |
| 哈希 | 决策summary=`ce666a75735548c8dd054fd96391169de43294b80f6c73a376fc0f4c018aa694`；Qwen2.5当前批summary=`ab45a253f8e2d15e62d0828ca2ec6fcefbc39ebe8ef2a4808eb6ff53ac4e940a` |

### Qwen3/Qwen2.5跨基座答案选择器CPU预检（2026-07-27，失败）

| 字段 | 内容 |
|---|---|
| 动机 | Clean Qwen3 + Qwen2.5-LoRA双模型Oracle为`36.4/54.7%`，检验互补是否可由推理可见特征学习 |
| 数据 | 同一Train-500五折OOF；100视频；每折80视频训练选择器、20视频验证；视频交集0 |
| 特征 | 31个问题/Voiceover/两响应结构与词汇特征；不读取参考答案、`meta_info`、视频、外部知识或逐题分数特征 |
| 监督 | 当前批`deepseek-v4-flash`胜负，仅训练两模型分数不相同的样本；`not_human_gold=true` |
| 冻结模型 | `StandardScaler + LogisticRegression`，C=1，balanced，阈值0.5，seed=20260727；无参数扫描 |
| Clean Qwen3 | Strict/Relaxed=`26.0/41.2%` |
| CPU选择器 | Strict/Relaxed=`23.4/40.6%` |
| 相对Qwen3 | Strict/Relaxed=`-2.6/-0.6 pp`；95% CI=`[-6.0,+0.6]/[-3.4,+2.1] pp` |
| 触发 | 选择Qwen2.5-LoRA=`224/500=44.8%` |
| 配对 | Relaxed胜/平/负=`51/387/62`；wrong→right/right→wrong=`23/36`；纠正精度=`38.98%` |
| 裁决 | `freeze_crossbase_selector_cpu_failed`；不调阈值、不换分类器、不进确认集、不启动GPU |
| 解释 | Oracle互补很大，但表面输出结构和词汇特征不能安全判断哪个答案正确 |
| 远端路径 | `evaluation/runs/crossbase_answer_selector_cpu_precheck_v1/` |
| 关键文件 | `selector_predictions_answer_free.jsonl`、`private_analysis.jsonl`、`summary.json` |
| 哈希 | summary SHA256=`fd490c764408ffd0ac953a3a0c2ea1330c9d769247be1b1f264857a493d0945d` |

### Qwen3 RealClaim985 声明—证据验证器（2026-07-27，核心门禁通过）

| 字段 | 内容 |
|---|---|
| 目的 | 只更换验证器基座，检验 Qwen3 是否能改善独立声明—证据支持判别；不是直接答案 LoRA |
| 训练数据 | RealClaim985，139视频，supported/not-supported=`642/343`，`not_human_gold=true` |
| 数据来源边界 | Evidence-300 的预冻结自定义训练侧；源自 AdsQA testset，不属于官方训练协议 |
| 训练/标签哈希 | `78789c288138235a7026d916775e74bbb7d05714f5647f19c8ba71d4526d85ac` / `58bda82a11b3e4c21a6801e1f977fc1ce45a36ddce422a86634c5f32872444d4` |
| 基座 | 干净 `<MODEL_ROOT>/Qwen3Vl-8B` |
| LoRA | q/v，rank/alpha/dropout=`8/16/0.05`，`lr=1e-4`，1 epoch，视觉编码器冻结 |
| 输入协议 | 8视图、448上限、视觉Token不超过4096、关闭二次采样；无参考答案/标签/`meta_info`/裁判分数 |
| Smoke-20 | 训练10/内部验证10；两侧正负类齐全、视频交集0；协议审计全部通过 |
| 内部验证 | 201条；AUROC=`0.6746`，AUPRC=`0.7784` |
| Calibration | 240条、35视频，supported/not-supported=`154/86`；Development244未访问 |
| 冻结 Qwen3 | AUROC=`0.5409`；AUPRC=`0.6665`；BA=`0.5573`；ECE=`0.3780`；Brier=`0.3857` |
| Qwen3 RealClaim LoRA | AUROC=`0.6599`；AUPRC=`0.7789`；BA=`0.6335`；ECE=`0.2120`；Brier=`0.2630` |
| Qwen2.5 incumbent | AUROC=`0.6345`；AUPRC=`0.7348`；BA=`0.6349`；ECE=`0.2767`；Brier=`0.3037` |
| Qwen3 LoRA vs base | AUROC点差=`+0.1190`；视频Bootstrap均值=`+0.1202`，95% CI=`[+0.0456,+0.1988]` |
| Qwen3 LoRA vs Qwen2.5 | AUROC点差=`+0.0254`；视频Bootstrap均值=`+0.0250`，95% CI=`[-0.0378,+0.0914]` |
| 视觉协议 | Calibration实际视觉Token 784–1232；训练全过程560–1568；8视图和关闭二次采样审计通过 |
| OCR门禁修正 | Calibration的`ocr_present`为240/240均false；v1误把单分层当通过，v2已修正为不可评估 |
| 最终状态 | 核心性能门禁通过；全部预注册门禁未通过；禁止自动访问Development244 |
| 下一步 | 独立OCR-present补充校准，或用户明确批准协议修订后，才可一次性评测Development244 |
| 远端路径 | `evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/` |
| 关键文件 | `protocol_audit.json`、`calibration_analysis_v2.json`、`train/adapter/adapter_model.safetensors` |
| 哈希 | protocol=`5f1f50dfc565a216ded29b90b4a01ec7a67e3d2633e1a7141eed0993e8b034e7`；analysis v2=`c76b7bb32747b45c518cb8c0b3d28f50bf6b4320117aa65b031d6490e83fb3f2`；adapter=`665d0d945e55cdb08e9c7874a5b6184351e9160b2e85730732b38d13cfe24d6d` |

### Qwen3 RealClaim985 OCR 补充校准（2026-07-27，专项门禁失败）

| 字段 | 内容 |
|---|---|
| 目的 | 补测 Calibration240 缺失的 `ocr_present=true` 能力；不是 QA 精度实验 |
| 数据 | 80 对/160 条/80 视频；answer-free 构造；`weak_ocr_labels=true`、`not_human_gold=true` |
| 隔离 | 排除 Pilot50、Confirm-A/B/C/D、RealClaim985 训练、Calibration240 和 Development244 视频 |
| E+ / E- | E+ 为目标视频跨帧稳定 OCR 文字；E- 为另一视频的匹配短语且不在目标 OCR 缓存中 |
| 输入审计 | 正负共享同视频、同8帧；至少含1个OCR证据帧；无答案/标签/分数/`meta_info`/负来源泄漏 |
| 模型 | 冻结 `<MODEL_ROOT>/Qwen3Vl-8B` 与同基座 + RealClaim985 LoRA |
| 视觉协议 | 8视图、448上限、实际672–1,568视觉Token、上限4,096、关闭二次采样 |
| 冻结 Qwen3 视觉 | AUROC/AUPRC=`0.99539/0.99624`；配对=`80/80=100%`；margin=`0.93996` |
| Qwen3 LoRA 视觉 | AUROC/AUPRC=`0.99531/0.99533`；配对=`78胜/1平/1负=98.13%`；margin=`0.64639` |
| 冻结 Qwen3 text-only | AUROC=`0.46867`；配对=`45.63%` |
| Qwen3 LoRA text-only | AUROC=`0.46742`；配对=`48.13%` |
| LoRA vs base | AUROC点差=`-0.000078`；80视频Bootstrap 95% CI=`[-0.00828,+0.00821]` |
| 视觉依赖 | LoRA视觉配对准确率比LoRA text-only高`+50.0 pp` |
| 门禁 | 数据、绝对能力、Bootstrap下界、视觉依赖和协议通过；“LoRA AUROC增量为正”失败 |
| 裁决 | `ocr_supplement_gate_failed_no_parameter_scan`；不访问Development244，不在该集调参 |
| 解释 | 精确OCR字符串匹配对冻结Qwen3已饱和；RealClaim LoRA整体收益不来自简单文字识别增强 |
| 远端路径 | `evaluation/runs/innovation2_qwen3_ocr_supplement_v1/` |
| 关键文件 | `dataset_v1/{audit.json,manifest.json}`、`{base,lora}_{visual,text}_v1/`、`analysis_v1/analysis.json`、`SHA256SUMS` |
| 哈希 | analysis=`bd6e62b6822f2d873a221e2376ac2ec60b215a70074252405c74b6ec5d026a3f`；audit=`9975619000794dce28380f39b5ee5c49907dee7da35d1487f3ebe181479d2b37`；SHA256SUMS=`f0529855d5719c17c98159a1e72e6d739163b917e226c0a30e47e0f14ea81978` |

### RealClaim 验证器跨基座答案重排序 Smoke-50（2026-07-27，正向信号但门禁失败）

| 字段 | 内容 |
|---|---|
| 目的 | 用冻结 Qwen3 RealClaim985 支持度，在 Clean Qwen3 A0 与 Qwen2.5 AdsSFTLoRA A1 之间做答案重排序 |
| 数据 | 50题、36视频；历史 OOF 中两个答案均可精确抽取且答案不同；格式预检后、GPU与私有评分前完成预注册修订 |
| 选择规则 | A1支持度`>=0.8933094144`、A0低于阈值且支持度差`>=0.25`才切换 |
| 防泄漏 | 选择阶段不读取GT、`meta_info`、裁判分数或私有评分；选择清单先冻结再匹配历史同批分数 |
| 模型与协议 | 冻结Qwen3 RealClaim985；8个Raw视图；实际896–1,232视觉Token；关闭二次采样 |
| Clean Qwen3 | Strict/Relaxed=`20.0/30.0%`；0/0.5/1=`30/10/10` |
| 门控重排序 | Strict/Relaxed=`20.0/33.0%`；0/0.5/1=`27/13/10` |
| 触发与转移 | 触发`5/50=10%`；胜/平/负=`3/47/0`；收益均为`0→0.5`；wrong→right/right→wrong=`0/0` |
| Bootstrap | 36视频簇、10,000次；Strict差CI=`[0,0]`；Relaxed差CI=`[0,+6.86] pp` |
| 裁判 | 精确复用同一`deepseek-v4-flash`历史批次；新增API调用0；`not_human_gold=true` |
| 裁决 | 预注册`wrong→right > right→wrong`未满足；`candidate_failed_no_parameter_scan`；不扩展OOF-500 |
| 解释 | 支持度门控可安全筛出部分得分收益，但尚未产生完整答案纠正；下一候选应是独立预注册的证据约束重写，而非事后调阈值 |
| 远端路径 | `evaluation/runs/crossbase_realclaim_rerank_smoke50_v1/` |
| 关键文件 | `dataset_v1/{audit.json,manifest.json}`、`verifier_scores_v1/scores.jsonl`、`analysis_v1/{choice_manifest.json,analysis.json}`、`source_snapshot/`、`SHA256SUMS` |
| 哈希 | analysis=`5257e0610514eee9d1857515912250e58e2e0a8933293f284d63b0212fc94e29`；choice=`44ce12379a6095c46a1c69e86d46fb55fd2ae48fa2cc1f000e7e9bc3eb11d8b3`；SHA256SUMS=`4bb2a191beb7b0f8baf2acdd3c911cc25dc8a4add75d25c42ad7768f02b2169f` |

### Qwen3视觉Token预算与证据分配Smoke-50（2026-07-27，门禁失败）

| 字段 | 内容 |
|---|---|
| 目的 | 检验Raw8增加视觉Token是否增精，以及同Token的ASR/OCR证据PiP是否优于高分辨率Raw8 |
| 数据 | 50题、50视频；五折`10/8/11/10/11`；全部具有既有合法PiP证据；answer-free冻结 |
| 共同协议 | 干净Qwen3；同8个源帧；相同ASR/Prompt；确定性解码；关闭二次采样 |
| 实测Token | Raw1K=`1,024`；Raw2K=`1,764`；Raw4K=`3,136`；EvidenceMix4K=`3,136` |
| Raw1K | Strict/Relaxed=`30/48%`；0/0.5/1=`17/18/15` |
| Raw2K | Strict/Relaxed=`24/43%`；相对Raw1K=`-6/-5 pp`；胜/平/负=`7/33/10` |
| Raw4K | Strict/Relaxed=`28/45%`；相对Raw1K=`-2/-3 pp`；胜/平/负=`8/32/10` |
| EvidenceMix4K | Strict/Relaxed=`24/40%`；0/0.5/1=`22/16/12` |
| 主比较 | EvidenceMix4K vs Raw4K Strict/Relaxed=`-4/-5 pp`；胜/平/负=`7/31/12` |
| 主比较转移 | wrong→right/right→wrong=`3/5`；Relaxed Bootstrap 95% CI=`[-14,+3] pp` |
| 推理审计 | 三条新臂各50/50、错误0；帧号一致；Raw4K与EvidenceMix逐题同Token；协议通过 |
| 裁判 | 1K精确复用当前批50条；新增150/150；`deepseek-v4-flash`；总Token=`137,841`；`not_human_gold=true` |
| 裁决 | `freeze_smoke_result_no_parameter_scan`；不扩展300，不在本Smoke调尺寸/PiP/Prompt |
| 解释 | 更多全帧Token没有单调收益；当前PiP可能放大非决定性区域并改变构图，不能作为增精方案 |
| 后续 | 保留1K Raw8默认预算；新增预算只允许由独立不确定性/充分性门控选择性触发 |
| 远端路径 | `evaluation/runs/adsqa_qwen3_token_budget_smoke50_v1/` |
| 关键文件 | `dataset_v1/`、`protocol_audit_v1.json`、`{raw2k,raw4k,evidence4k}_v1/`、`judge_v1/{results.jsonl,summary.json,SHA256SUMS}` |
| 哈希 | protocol=`9c19970cb2f3e0e9efe27026686d73683e32e0dd737a3373b792c7cd7cb2180a`；summary=`da4cc8aff6d79e0fea5cf21d0d5479cfc2a0ad1eb4286bd740416b05104a3a18`；run SHA256SUMS=`9f0a49047bd2ddacd8558e22aefca7a618ab2785af66f332f912c6466b008694` |

### ReAd-R裁剪Token效率诊断（2026-08-04，评分完成）

| 字段 | 内容 |
|---|---|
| 目的 | 不再证明裁剪绝对优于高清整帧；检验低分辨率裁剪能否以更少视觉Token保持答案质量 |
| 数据 | Fresh-500既有触发池中的123题/75视频实际裁剪子集；67题1个crop、56题2个crop；事后效率诊断 |
| 四臂 | `RouteCrop896`、`Full896`、`RouteCrop672`、`RouteCrop512` |
| 共同协议 | ReAd-R；MMR8初答；同两个锚点、OCR/ASR、12视图、通用提示和生成配置；关闭二次采样 |
| 推理 | 四臂各123/123；错误0；完整协议审计通过 |
| 平均视觉Token | 3992.00 / 3992.00 / 3340.03 / 2973.30 |
| Token节省 | 672裁剪相对Full896 `-16.33%`；512裁剪 `-25.52%` |
| R5/R3/R2 | Route896=`41.87/23.98/15.45%`；Full896=`42.28/25.20/15.45%`；Route672=`43.29/26.02/15.45%`；Route512=`42.28/24.80/15.45%` |
| 672 vs 896裁剪 | 6胜/116平/1负；R5 `+1.42 pp`，CI=`[+0.20,+2.91] pp`；R3 `+2.03 pp`，CI=`[+0.43,+3.85] pp` |
| 672 vs Full896 | 6胜/116平/1负；R5 `+1.02 pp`，CI=`[-0.40,+2.48] pp`；R3 `+0.81 pp`，CI=`[-0.77,+2.50] pp` |
| 512 vs Full896 | 6胜/113平/4负；R5差0，CI=`[-1.64,+1.57] pp`；R3 `-0.41 pp`，CI=`[-2.16,+1.32] pp` |
| 裁判 | 492槽去重183候选；复用同批历史128；新增55/55；零重试、零失败；总Token 152,573；`not_human_gold=true` |
| 结论边界 | 672是推荐效率点：少16.33% Token、显著优于896裁剪、与高清整帧相当；不能写成对高清整帧显著增精；需新视频确认 |
| 远端路径 | `data/external/evads_v1/experiments/readr_crop_efficiency_fresh500_posthoc_v1/` |
| 本机记录 | `docs/ReAd-R裁剪Token效率诊断_20260804.md` |

### Qwen3选择性视听证据补看与答案重写（2026-07-27，OOF开发门禁通过）

| 字段 | 内容 |
|---|---|
| 目的 | 用 RealClaim985 识别低支持初答，只对少量问题补看关键帧、独立局部裁剪、OCR和分段ASR，再保守决定是否采用重写答案 |
| 基础池 | `CleanQwen3_Raw8` OOF-500；500题、100视频、五折各100 |
| 触发集 | 每视频最低支持题、每折最低10个视频；共50题、50视频；选择不读GT、`meta_info`或裁判分数 |
| A0 | Clean Qwen3 Raw8；8视图、1,024视觉Token |
| A1 | 相同8帧和ASR的一次普通复思；8视图、1,024视觉Token |
| A2 | 原8帧 + 两个冻结证据时刻各1张全帧和1张mid独立裁剪 + OCR/分段ASR；12视图、3,104视觉Token |
| A3门控 | `P(A2)>=0.8933094144`、`P(A0)<阈值`且差值`>=0.25`才接受A2，否则回退A0 |
| 协议 | A0 500/500；A1/A2各50/50；错误与解析失败0；帧与锚点对齐；关闭二次采样；审计通过 |
| 冻结选择 | A3接受25/50，实际改变答案25/50；选择发生在读取GT与新裁判分数之前 |
| 触发集A0 | Strict/Relaxed=`2/7%`；0/0.5/1=`44/5/1` |
| 触发集A1 | Strict/Relaxed=`18/27%`；0/0.5/1=`32/9/9` |
| 触发集A2 | Strict/Relaxed=`30/41%`；0/0.5/1=`24/11/15` |
| A2对照 | A2 vs A0胜/平/负=`22/28/0`；A2 vs A1=`11/36/3`，Relaxed差`+14 pp` |
| 触发集A3 | Strict/Relaxed=`22/32%`；相对A0胜/平/负=`17/33/0`；wrong→right/right→wrong=`10/0` |
| OOF-500 A0 | Strict/Relaxed=`26.0/41.2%`；0/0.5/1=`218/152/130` |
| OOF-500 A3 | Strict/Relaxed=`28.0/43.7%`；0/0.5/1=`203/157/140` |
| 完整增量 | Strict/Relaxed=`+2.0/+2.5 pp`；胜/平/负=`17/483/0`；纠正精度100% |
| Bootstrap | 100视频簇、10,000次；Relaxed差95% CI=`[+1.4,+3.7] pp`；Strict差CI=`[+1.0,+3.2] pp` |
| 平均成本 | 10%触发、5%实际切换；完整策略平均回答视觉Token=`1,334.4`，验证器Token另计 |
| 裁判 | A0复用500条同批哈希一致分数；新增去重调用88/88；`deepseek-v4-flash`；总Token=`62,924`；`not_human_gold=true` |
| 裁决 | 九项预注册扩展门禁全部通过；`eligible_for_independent_confirm300`；不得在OOF-500调参 |
| 论文意义 | 第一次证明视听证据补看优于普通复思，且证据充分性门控可将其转化为无观测伤害的完整QA增益；仍需独立Confirm-300 |
| 远端路径 | `evaluation/runs/qwen3_selective_evidence_rewrite_smoke50_v1/` |
| 关键文件 | `a0_verifier_merged_v1/`、`dataset_v1/`、`rewrite_inference_v1/`、`a2_verifier_merged_v1/`、`frozen_choices_v1/`、`judge_deepseek_v1/` |
| 哈希 | protocol=`6a1b855fea8ba266557d0f9fc9ce5f14059399ebfa82b0a8827d7643f224cafb`；choices=`9d235ffc1a64f8fae6a552aa05ae39dfca010f3e4369b781dd1ef81c78420789`；summary=`089f25d9f0406f874a6ba32019f2fa3cef6f384a98599211b14827969b279c4d`；SHA256SUMS=`6778db569d00a7ebf8b5c9adae999f967f0bae11b0ce5cc3ad5a11b5db7432ea` |

## Qwen3选择性视听证据补看 Confirm-D300（方法级确认，2026-07-27）

| 字段 | 内容 |
|---|---|
| 状态 | `confirm_passed_freeze_for_thesis`；十项预注册门禁全部通过 |
| 独立性 | 300题、300视频、Type1–5各60；与Train-500视频交集0；Confirm-D曾供另一候选使用，故属于方法级确认而非全局盲测 |
| 模型 | 干净`<MODEL_ROOT>/Qwen3Vl-8B`；冻结Qwen3 RealClaim985验证器 |
| A0 | Raw8 + 分段ASR；8视图、1,024视觉Token |
| 触发规则 | 300个A0支持度全量排序，全局最低30题；固定10%覆盖率 |
| A1 | 同8帧与ASR的一次普通复思；1,024视觉Token |
| A2 | 原8帧 + 2个证据时刻 ×（全帧 + mid裁剪）+ OCR/分段ASR；12视图、3,104视觉Token |
| A3门控 | 阈值`0.8933094143867493`、margin`0.25`；冻结切换14/30 |
| 协议 | A0 300/300；A0验证器300/300；A1/A2各30/30；A2验证器30/30；错误0；关闭二次采样；审计通过 |
| 解码修复 | OpenCV在2条末帧随机定位失败；保留失败记录后改用Decord精确索引，仅重跑失败分片 |
| 触发30 A0 | Strict/Relaxed=`0.00/3.33%`；0/0.5/1=`28/2/0` |
| 触发30 A1 | Strict/Relaxed=`3.33/16.67%`；相对A0胜/平/负=`7/23/0` |
| 触发30 A2 | Strict/Relaxed=`30.00/35.00%`；相对A0=`12/17/1`；相对A1=`10/17/3` |
| 触发30 A3 | Strict/Relaxed=`26.67/33.33%`；相对A0=`10/20/0`；wrong→right/right→wrong=`8/0` |
| 完整300 A0 | Strict/Relaxed=`29.33/45.33%`；0/0.5/1=`116/96/88` |
| 完整300 A3 | Strict/Relaxed=`32.00/48.33%`；0/0.5/1=`106/98/96` |
| 完整增量 | Strict/Relaxed=`+2.67/+3.00 pp`；胜/平/负=`10/290/0`；纠正精度100% |
| Bootstrap | 300视频、10,000次；Relaxed差95% CI=`[+1.33,+5.00] pp`；Strict差=`[+1.00,+4.67] pp` |
| 类型分层 | Type1–5 Relaxed差=`+0.83/+3.33/+1.67/+3.33/+5.83 pp`，无类型退化 |
| 平均成本 | 10%触发；平均回答视觉Token=`1,334.4`；A0平均8.52秒，A2触发额外4.29秒；验证器延迟与Token另计 |
| 裁判 | `deepseek-v4-flash`；350/350唯一调用；失败0、重试0；总Token=`282,546`；`not_human_gold=true` |
| 论文结论 | 创新点一的证据定位作为按需补看工具，与创新点二的充分性识别、验证和保守回退结合后，在开发与方法级独立确认上稳定增精；不能归因为裁剪单模块 |
| 远端路径 | `evaluation/runs/qwen3_selective_evidence_rewrite_confirmd300_v1/` |
| 关键文件 | `prepared_answer_free_v1/`、`av_manifest_v1/`、`a0_inference_v1/`、`a0_verifier_merged_v2_decord/`、`trigger30_dataset_v1/`、`rewrite_inference_v1/`、`frozen_choices_v1/`、`judge_deepseek_v1/` |
| 哈希 | protocol=`a480eea5507fa9a8e6508de22081f8a3d8bd626c2d64ae9ca29d2dbfea8e017c`；choices=`db0a6210e92335270dca42a0ee10d55a85cc652d8b565a96f109208b1c62ef31`；summary=`94c1fd278ab10e9ae8b873ae532709b8d0e3220a5695701c2b84bc2c41179a2d`；complete_rows=`d4f5da35706d5ac79b27cb97f194a434b90d1dbd11bef92e103f3ae9e1cc3194`；SHA256SUMS=`382d9e4df4bd27b964116a61a4b6ed81c8c4fcc8be19a1aded5b01d11fe3c58c` |

## Confirm-D300随机触发对照（2026-07-27，支持低支持触发机制）

| 字段 | 内容 |
|---|---|
| 目的 | 排除“随机选择30题进行证据重写也会获得同等提升”的替代解释 |
| 随机规则 | 固定seed=`20260728`；30题/30视频；每折6题；不读取支持度、GT、`meta_info`或裁判分数 |
| 与目标触发重叠 | 随机30与低支持30重叠4题 |
| 协议 | A1/A2为8/12视图、1,024/3,104视觉Token；二次采样关闭；协议审计通过 |
| 去重调用 | 300个A0 + 60个A1/A2槽位去重为356个唯一候选；历史精确复用307；实际新增49 |
| 裁判 | `deepseek-v4-flash` answer-only；49/49成功；失败0、重试0；总Token=`30,885`；授权上限50；`not_human_gold=true` |
| A0 | Strict/Relaxed=`29.33/45.33%` |
| 随机强制A1 | Strict/Relaxed=`29.00/46.33%`；相对A0=`9/287/4`；wrong→right/right→wrong=`3/4` |
| 随机强制A2 | Strict/Relaxed=`30.00/46.83%`；相对A0=`10/286/4`；wrong→right/right→wrong=`5/3` |
| 随机A3 | Strict/Relaxed=`30.00/46.00%`；相对A0=`+0.67/+0.67 pp`；`2/298/0`；wrong→right/right→wrong=`2/0` |
| 随机A3 Bootstrap | 300视频、10,000次；Strict/Relaxed差CI均=`[0,+1.67] pp` |
| 低支持A3 vs 随机A3 | Strict/Relaxed=`+2.00/+2.33 pp`；`8/292/0`；wrong→right/right→wrong=`6/0` |
| 目标触发 Bootstrap | 低支持减随机的Strict CI=`[+0.67,+3.67] pp`；Relaxed CI=`[+0.83,+4.17] pp` |
| 裁决 | `targeted_trigger_has_positive_increment_over_random=true`；低支持触发是联合方法的必要机制证据 |
| 论文解释 | 随机反思和随机补看会伤害正确答案；收益来自风险识别、按需取证及冻结门控的组合 |
| 远端路径 | `evaluation/runs/qwen3_selective_evidence_rewrite_random30_confirmd300_v1/` |
| 关键文件 | `frozen_choices_v2_recovered/`、`judge_deepseek_incremental_v1/{preflight_audit.json,new_api_results_partial.jsonl,complete_confirmd300_random_policy_rows.jsonl,summary.json,SHA256SUMS}` |
| 哈希 | summary=`27592d8cb1a432d59cf24664409bfcff795e397115e36496c3966d82529083de`；complete_rows=`20ed4dfa6c5fddf9d43b212d359cc81d56448a56c54dbab0e76b328b946bb4c8`；SHA256SUMS=`dfb35f2c9475b2e3167456f6ac578735a525f5db0d6bffab34bee441ddebe684` |

## Qwen3 RealClaim985三Seed稳定性（2026-07-27，排序能力稳定）

| 字段 | 内容 |
|---|---|
| 目的 | 检查Qwen3声明—证据LoRA的Calibration正向结果是否依赖单一训练seed |
| 固定协议 | 同RealClaim985、同Calibration240、冻结视觉编码器、8视图、1 epoch、`lr=1e-4`；不扫描超参数 |
| Seed AUROC | `0.6599 / 0.6830 / 0.6823`；均值±样本标准差=`0.6751±0.0131` |
| Seed AUPRC | `0.7789 / 0.7750 / 0.7945`；均值±样本标准差=`0.7828±0.0103` |
| Seed BA | `0.6335 / 0.6441 / 0.6583`；均值±样本标准差=`0.6453±0.0125` |
| Seed ECE | `0.2120 / 0.1074 / 0.2427`；校准误差波动较大 |
| 对照 | 三seed AUROC均高于`0.65`且点估计均高于Qwen2.5 incumbent `0.6345` |
| 边界 | 同一Calibration的训练稳定性，不是三次独立外部确认；不得据此挑seed或自动访问Development244 |
| 冻结策略 | Confirm-D继续使用原始seed及既有阈值`0.8933094144`，不事后替换为Calibration最佳seed |
| 远端路径 | 原始`evaluation/runs/innovation2_qwen3_realclaim985_v1/full985_v1/`；补充`evaluation/runs/innovation2_qwen3_realclaim985_stability_v1/` |
| 哈希 | 三个Calibration summary=`e765617b8b4cb32cb0630074428c9ab5891ca7ecfccb6b19456a2f97b3ddbc89 / a22cadbc086c64bbab5f03426d500effd3f178b5cae9c7c1a087ca15e257a611 / 5b5d87d114ed486e0173d1d2ed360cdf56eb5e5a1aa456835a81464b2bfd5ce4` |

## Qwen3选择性证据重写组件消融（2026-07-27，探索性）

| 字段 | 内容 |
|---|---|
| 目的 | 区分联合方法中 OCR、分段 ASR 与局部裁剪的独立贡献 |
| 数据 | 冻结 OOF 低支持 50 题、50 视频；与完整方法逐题一致 |
| 共同协议 | A0/A1、触发集、Prompt、阈值、margin 不变；A2 均为 12 视图、3,104 Token；关闭二次采样 |
| NoOCR | A3 Strict/Relaxed=`16/28%`；相对A0=`15/35/0`；门控接受23 |
| NoSegmentedASR | A3 Strict/Relaxed=`18/27%`；相对A0=`14/35/1`；门控接受22 |
| NoLocalCrop | A3 Strict/Relaxed=`26/35%`；相对A0=`18/32/0`；门控接受23 |
| 完整方法 | 同50题 A3 Strict/Relaxed=`22/32%` |
| OCR贡献 | 完整减NoOCR Strict/Relaxed=`+6/+4 pp`；Relaxed CI=`[-3,+11] pp` |
| 分段ASR贡献 | 完整减NoSegmentedASR=`+4/+5 pp`；Relaxed CI=`[-2,+12] pp` |
| 局部裁剪贡献 | 完整减NoLocalCrop=`-4/-3 pp`；Relaxed CI=`[-12,+5] pp` |
| 裁判 | 历史精确复用119个候选；新增81/81；`deepseek-v4-flash`；失败/重试0；总Token=`58,895`；`not_human_gold=true` |
| 裁决 | OCR/分段ASR方向为正但未显著；局部裁剪未证明必要，NoLocalCrop成为Fresh Confirm-E待确认候选 |
| 论文边界 | 不得写“局部裁剪单独增精”；完整方法的Confirm-D正结果仍保留，NoLocalCrop确认前不得替换 |
| 远端路径 | `evaluation/runs/qwen3_selective_evidence_rewrite_ablation_oof50_v1/` |
| 关键文件 | `{no_ocr,no_segmented_asr,no_local_crop}/frozen_choices_v1/`、`judge_deepseek_v1/{preflight_audit.json,results_v1/}` |
| 哈希 | preflight=`c898b98fccc240c60f5e3de840a691993eb49e5d5a718fcf23ebd47019411233`；summary=`e11605f011acec264db095efaa776717c3752d09bf26249b646a48d0e90f45df`；SHA256SUMS=`524d187f4c1c278496a531c05c1f3df0733d73b8e295e12e220b91b73e2f3578` |

## Qwen3同预算强选帧基线（2026-07-28，GroupCV-500）

| 字段 | 内容 |
|---|---|
| 目的 | 在Clean Qwen3同一回答模型和严格同预算下，补齐CLIP、MMR与VideoITG强选帧基线 |
| 数据 | AdsQA GroupCV-500，500题、100视频；与Clean Qwen3 Uniform8历史OOF逐题对齐 |
| 共同协议 | 8视图、1,024实际视觉Token、相同Prompt与ASR、确定性解码、关闭二次采样 |
| Uniform8 | Strict/Relaxed=`26.0/41.2%`；0/0.5/1=`218/152/130` |
| CLIPTopK8 | Strict/Relaxed=`25.0/40.3%`；相对Uniform=`-1.0/-0.9 pp`；Relaxed CI=`[-4.8,+3.0] pp` |
| MMR8 | Strict/Relaxed=`26.2/42.7%`；相对Uniform=`+0.2/+1.5 pp`；Relaxed CI=`[-3.0,+5.7] pp` |
| VideoITG8 | Strict/Relaxed=`24.8/41.9%`；相对Uniform=`-1.2/+0.7 pp`；Relaxed CI=`[-3.6,+4.9] pp` |
| MMR转移 | 相对Uniform胜/平/负=`114/285/101`；wrong→right/right→wrong=`56/55` |
| 推理审计 | 三方法各500/500，错误0；视图、帧号、Token与关闭二次采样审计全部通过 |
| 裁判 | 1条精确复用Uniform历史分数；新增1,499/1,499次`deepseek-v4-flash` answer-only调用；重试/失败0；总Token=`1,364,241`；`not_human_gold=true` |
| 裁决 | MMR8为最佳点估计静态选帧基线，但三方法相对Uniform的Bootstrap区间均跨0；不扫描参数、不宣称稳定增精 |
| 论文用途 | 主表强基线；支持“全量静态换帧不稳定，低支持触发的按需补看闭环更有效”的机制解释 |
| 远端路径 | `evaluation/runs/qwen3_selected8_baselines_groupcv500_v1/` |
| 关键文件 | `full500/{CLIPTopK8,MMR8,VideoITG8}/`、`judge_deepseek_answeronly_v1/{dry_run_audit.json,api_results_partial.jsonl,results.jsonl,summary.json,SHA256SUMS}` |
| 哈希 | summary=`c51791e1223d84262493e0d70ad55ac2299bd187ea749a22fa40d245cb5c92d3`；results=`e50bd22a9c40a4a14f0780f790aa3dc2dabf1521ec57505b2cabc3d9d55a7de6`；SHA256SUMS=`535f106da021f1321a7cebc9ed5e531a679dda7d268621082260ffe850279ea5` |

## Qwen3联合方法Confirm-1000冻结确认集（2026-07-28）

| 字段 | 内容 |
|---|---|
| 目的 | 为选择性视听证据补看联合方法建立第二个大规模方法级冻结确认集 |
| 源数据 | AdsQA test 7,859行；7,846个唯一问题ID；13行完全重复记录确定性合并 |
| 无效参考 | 1,532个私有参考为空的问题排除；不使用答案语义筛选 |
| 方法专属排除 | `train.json`、RealClaim985训练、Calibration240、Development244、Confirm-D300 |
| 排除规模 | 共609个唯一视频，其中509个属于测试问题源 |
| 抽样 | 固定seed=`20260728`；题型—视频确定性最大流；全局一视频一题 |
| 确认集规模 | 1,000题、1,000视频；Type1–5各200 |
| 分片 | 5片各200题；每片每类40题 |
| 隔离审计 | 与方法专属排除视频交集0；answer-free文件禁用字段0 |
| 私有参考 | 1,000/1,000，权限目录`700`、文件`600` |
| 视频与缓存 | 视频/CLIP/OCR均1,000/1,000 |
| 分段ASR | 现有930/1,000；缺失70，补齐前不得启动完整联合推理 |
| 边界 | 是当前方法的第二方法级冻结确认集，不是相对全部历史实验的全局盲集 |
| 使用限制 | 不得调阈值、触发率、margin、Prompt、锚点、OCR/ASR权重、裁剪或Token；不得看结果后换题 |
| 远端路径 | `data/qwen3_joint_confirm1000_v1/` |
| 关键文件 | `questions_answer_free.json`、`shards/`、`private_references/groundtruth.json`、`audit.json`、`manifest.json`、`FROZEN` |
| 哈希 | manifest=`ac3cd2978c5003ffdb1f10dc83db4ef2db4c9d7be3f6c766349419e7bd8e951a`；audit=`75693e74d7ec83c6cedf3356bc746414e8ee218e65558e9bb2490b115a7f5e9f`；questions=`87344f000942eba1c9c03d0b43ef70a82e30c809a52ac4ebfed26c8377e5050a`；private=`e2efccb11bc0f6ebeb01572596f8b2177b640b7c451c94eb54d2b564df564e88` |

## Qwen3联合方法Confirm-1000分段ASR与最终四臂预注册（2026-07-28）

| 字段 | 内容 |
|---|---|
| ASR补充范围 | 原覆盖930/1000；独立补充70个视频，不修改冻结确认集 |
| ASR smoke | 5/5；`success=4`、`no_speech=1`；时间戳和状态审计通过 |
| ASR联合覆盖 | 1000/1000；`success=988`、`no_speech=11`、`no_audio=1`、失败0 |
| ASR内容规模 | 9,481个句段、75,689个词 |
| ASR路径 | `evaluation/runs/qwen3_joint_confirm1000_v1/asr_supplement_v1/` |
| ASR哈希 | aggregate=`084446e1f685647d402115d3284ab368c95b121387ae7880d41b07024e9ebbd6`；union audit=`927e3ee650c4f84c1cadc0d0d2a9af87d5283b533f296903db51144840841a53` |
| 四臂 | `Uniform8`、`MMR8`、同触发同Token的`ExtraGlobalControl`、`FullJointMethod` |
| Uniform/MMR协议 | 各8视图、1,024视觉Token；MMR固定64候选与`lambda=0.70` |
| 联合方法触发 | A0支持度最低100/1000；按支持度升序、再按question ID |
| 联合方法预算 | 触发题12视图、3,104视觉Token；关闭二次采样 |
| ExtraGlobal控制 | 与完整方法共享触发、锚点、OCR/ASR和Token；仅以896未裁剪全帧替代局部裁剪 |
| 冻结门控 | threshold=`0.8933094143867493`；margin=`0.25`；不满足则回退A0 |
| 主要比较 | Full vs Uniform；次要Full vs MMR、Full vs ExtraGlobal |
| 预注册协议 | `evaluation/runs/qwen3_joint_confirm1000_v1/PREREGISTERED_PROTOCOL.json` |
| 协议SHA256 | `0ed03079b1f6816c3ab33654ff930e8a86205166badf7f47781c76314a823cb8` |
| 运行准备 | answer-free五片各200题；视频/OCR/CLIP/ASR均1000/1000；审计通过 |
| 当前状态 | GPU1–5后台流水线已启动；DeepSeek裁判待完成协议审计并另行授权 |
| 使用限制 | 不在Confirm-1000调阈值、触发率、MMR、Prompt、锚点、OCR/ASR、裁剪或Token；不事后择优 |

## Qwen3联合方法Confirm-1000最终结果（2026-07-28）

| 字段 | 内容 |
|---|---|
| 状态 | 四臂推理、answer-free协议审计、统一裁判和10,000次视频级Bootstrap全部完成 |
| 数据 | 1,000题、1,000视频；冻结`primary_type`的Type1–5各200 |
| 推理完整性 | Uniform8/MMR8/ExtraGlobal/FullJoint各1,000题；失败0 |
| 解码恢复 | 3条Decord不稳定视频仅以OpenCV读取冻结帧位；错误method补题归档且不进入正式结果 |
| Uniform8 | Strict/Relaxed=`28.80/45.20%`；0/0.5/1=`384/328/288` |
| MMR8 | Strict/Relaxed=`32.20/47.70%`；相对Uniform=`+3.40/+2.50 pp` |
| ExtraGlobalControl | Strict/Relaxed=`30.60/47.70%`；相对Uniform=`+1.80/+2.50 pp` |
| FullJointMethod | Strict/Relaxed=`30.90/48.05%`；相对Uniform=`+2.10/+2.85 pp` |
| Full vs Uniform | 胜/平/负=`44/955/1`；wrong→right/right→wrong=`21/0`；纠正精度100% |
| Full vs Uniform Bootstrap | Strict差CI=`[+1.30,+3.00] pp`；Relaxed差CI=`[+2.00,+3.75] pp` |
| MMR vs Uniform Bootstrap | Strict差CI=`[+0.20,+6.50] pp`；Relaxed差CI=`[-0.10,+5.15] pp` |
| Full vs MMR | Strict/Relaxed=`-1.30/+0.35 pp`；Relaxed CI=`[-2.35,+3.05] pp`；未稳定胜出 |
| Full vs ExtraGlobal | Strict/Relaxed=`+0.30/+0.35 pp`；`8/989/3`；Relaxed CI=`[-0.05,+0.80] pp`；未证明局部裁剪必要 |
| 触发子集 | 100题；Uniform=`2.0/9.0%`，ExtraGlobal=`20.0/34.0%`，Full=`23.0/37.5%` |
| 实际切换 | FullJoint=`58/1000`；ExtraGlobal=`54/1000` |
| 类型分层 | Full相对Uniform的Type1–5 Relaxed增量=`+1.00/+3.25/+4.00/+2.00/+4.00 pp`，无退化 |
| Token | Uniform/MMR=`1,024`；触发题Full/Control=`3,104`；Full完整策略平均=`1,334.4` |
| 裁判去重 | 四臂4,000槽位去重为2,093个同题唯一答案；减少1,907次重复调用 |
| 裁判 | `deepseek-v4-flash` answer-only；2,093/2,093成功；失败0、重试0；总Token=`1,740,562`；`not_human_gold=true` |
| 主要裁决 | 联合方法相对Uniform在第二个大规模方法级冻结集上稳定增精；支持“低支持触发—按需取证—充分性复核—保守回退”闭环 |
| 重要边界 | Full未稳定超过MMR，局部裁剪未稳定超过同锚点ExtraGlobal；不得宣称完整方法是所有基线中的显著最优 |
| 后续限制 | Confirm-1000永久停止调参；新机制只能在新冻结集或外部数据集验证 |
| 远端路径 | `evaluation/runs/qwen3_joint_confirm1000_v1/` |
| 关键文件 | `final_protocol_audit_v1/{candidates_answer_free.jsonl,protocol_audit.json}`、`judge_deepseek_v1/{dry_run_audit.json,api_results_partial.jsonl,expanded_four_arm_scores.jsonl,summary.json}` |
| 哈希 | candidates=`1d141f8cdfe967f9b77227f4faf4f78d7f9e7ab5db283786517380bffbdd7182`；dry-run=`c2832636172e16ae9a4fc46d47779e1bcefd72b0d17a47b24b7aafecdf95c413`；API=`aa91456b99defaf1fb07ab6c1f176014cfc1c6abd600cbc821890a2845add64b`；rows=`f0e530dfd298d72689fccd2babc526e3de0569b70f59632c4f4ce7a04cde347e`；summary=`61170ec3519697877295ce0ee0ef505271308c9e9b9284e36c47b3225ec94d40`；SHA256SUMS=`772e6b53fd8a134e3c5fc6e9777b17d8a3f3a2773fbe3a21cb3115ebb0dbc144` |

## MMR-SelectRescue OOF-500（2026-07-28）

| 字段 | 内容 |
|---|---|
| 状态 | `development_candidate_passed_needs_independent_confirm` |
| 数据 | GroupCV-500，500题/100视频；五折视频级隔离 |
| A0 | 冻结`CleanQwen3_MMR8`；64候选、MMR `lambda=0.70`、8视图、1,024视觉Token |
| 触发规则 | 对500个MMR8初答全量做RealClaim985支持度评分；每折最低10题，共50题/50视频 |
| A1 | 同MMR8基础帧普通复思；8视图、1,024视觉Token |
| A2 | MMR8基础帧 + 2个证据时刻×（512全帧+896中尺度裁剪）+ OCR/分段ASR；12视图、3,104视觉Token |
| A3门控 | `P(A2)>=0.8933094143867493`、`P(A2)-P(A0)>=0.25`；冻结接受23/50 |
| 协议 | A0验证器500/500；A1/A2各50/50；A2验证器50/50；二次采样关闭；GT/裁判/外部知识未用于选择；审计通过 |
| 触发50 A0 | Strict/Relaxed=`4.00/10.00%` |
| 触发50 A1 | Strict/Relaxed=`18.00/33.00%`；相对A0=`20/28/2` |
| 触发50 A2 | Strict/Relaxed=`22.00/38.00%`；相对A0=`22/27/1` |
| 触发50 A3 | Strict/Relaxed=`14.00/27.00%`；相对A0=`13/37/0` |
| 完整500 A0 | Strict/Relaxed=`26.20/42.70%`；0/0.5/1=`204/165/131` |
| 完整500 A3 | Strict/Relaxed=`27.20/44.40%`；0/0.5/1=`192/172/136` |
| 完整增量 | Strict/Relaxed=`+1.00/+1.70 pp`；胜/平/负=`13/487/0`；wrong→right/right→wrong=`5/0` |
| Bootstrap | 500视频、10,000次；Strict差CI=`[+0.20,+2.00] pp`；Relaxed差CI=`[+0.80,+2.70] pp` |
| 平均成本 | 10%触发；完整策略平均回答视觉Token=`1,334.4`；验证器成本另计 |
| 裁判复用 | 历史MMR8 500条全部按题号和候选哈希精确复用 |
| 新裁判 | `deepseek-v4-flash` answer-only；92/92成功；失败0、自动重试0；总Token=`66,615`；`not_human_gold=true` |
| 当前结论 | 在MMR8强静态基线上，低支持触发、证据补看与保守门控取得开发期稳定正增益 |
| 重要边界 | 尚非独立确认；不得在GroupCV-500或Confirm-1000继续调参 |
| 下一门禁 | 固定全部设置，在新AdsQA确认集或E-VAds外部集直接验证 |
| 远端路径 | `evaluation/runs/qwen3_mmr_selectrescue_oof500_v1/` |
| 关键文件 | `frozen_choices_v1/{frozen_choices_answer_free.jsonl,protocol_audit.json}`、`judge_deepseek_v1/{dry_run_audit.json,api_results_partial.jsonl,complete_oof500_policy_rows.jsonl,summary.json}` |
| 哈希 | choices=`8ee8a7976862b2e70b43ea5eefe66853a4a657e985e7ba962fc357e31890ad4b`；dry-run=`0c9ac92c4b4d300279b33111e628601957d86ca719bea48c9ecdff6654f7aba6`；API=`d6ebe393ee5d4369f9a1b5220d5d088884c9eb27410f5179f870c276d663c679`；rows=`05a48e2d67225669b0406f9e22931f687ae83c09f322d03cbc36c15f28db0e21`；summary=`f8ed8bc5045bd13df15612687033e73f76d2b30d24ccefde9c38241a3a3ff73d`；SHA256SUMS=`6f8062a9c97b5311676d1c9dcf4243bf182c94caf34a5a5b66da04503cbf374f` |

## MMR-SelectRescue E-VAds External-1000B（2026-07-28，已完成）

| 字段 | 内容 |
|---|---|
| 状态 | `inference_running_answer_free`；不得提前写精度结论 |
| 目的 | 在未参与AdsQA候选开发的新外部视频上独立确认MMR-SelectRescue |
| 数据 | E-VAds Test新选200视频×5题=1,000题；旧External-500视频重叠0 |
| 分折 | 五折各40视频、200题 |
| A0 | clean Qwen3-VL；multilingual SigLIP-MMR8；64候选、`lambda=0.70`、8视图、1,024视觉Token |
| 触发 | RealClaim985全量评分；每折不同视频的最低支持20题，共100题/100视频 |
| A1 | 同MMR8基础帧普通复思；8视图、1,024视觉Token |
| A2 | 2个问题相关证据时刻×（512全帧+896固定中尺度上下文）+ 官方时间对齐OCR/ASR；12视图、Token上限4,096 |
| 外部适配 | 无OCR框时固定裁剪`[0.12,0.12,0.88,0.88]`；OCR置信度1.0仅表示官方文本存在，不作检测概率 |
| 门控 | threshold=`0.8933094143867493`；margin=`0.25`；不满足则回退A0 |
| MMR审计 | 1,000题/200视频；每题64候选、8帧唯一且时间排序；答案字段未使用；通过 |
| Smoke-50 | 50题/10视频；五折各10/10；错误0；8视图、1,024 Token、关闭二次采样审计通过 |
| 全量运行 | GPU1–5各一折；断线无关后台续跑；GPU0未使用 |
| 裁判限制 | 当前禁止读取私有参考和调用DeepSeek；最终协议审计后另行核算并授权 |
| 远端路径 | `data/external/evads_v1/experiments/mmr_selectrescue_external1000b_v1/` |
| 后台入口 | `evaluation/scripts/run_evads_mmr_selectrescue_external1000b_continue_v1.sh` |
| 哈希 | questions=`0049fa808a3c8f03b84ca9cc2e4b0e1a47ca49bd20710a13822e67cdc6bef027`；MMR manifest=`f7b3646d450cfda9cedad473535db648f5544b7ab661207a7d7373026dfeefcb`；Smoke manifest=`e51f6f067df9543acf572b867a34f941811bba87fbedd623f1c58a5885342340` |

### External-1000B最终结果

| 字段 | 内容 |
|---|---|
| 状态 | 推理、私有参考物化、统一裁判与10,000次视频聚类Bootstrap全部完成 |
| 推理完整性 | A0=`1000/1000`；A0验证器=`1000/1000`；A1/A2各`100/100`；A2验证器=`100/100`；错误0 |
| 门控 | 接受并实际改变`35/100`题 |
| A0完整集 | R5/R3/R2=`51.925/35.25/11.30%` |
| A3完整集 | R5/R3/R2=`53.625/37.35/12.90%` |
| 完整增量 | R5/R3/R2=`+1.70/+2.10/+1.60 pp` |
| R5胜平负 | `28/972/0` |
| R2纠正 | wrong→right/right→wrong=`16/0`；纠正精度100% |
| Bootstrap | R5 CI=`[+1.10,+2.35] pp`；R3=`[+1.35,+2.90] pp`；R2=`[+0.90,+2.40] pp` |
| 触发100 A0 | R5/R3/R2=`31.5/9.0/3.0%` |
| 触发100 A1 | R5/R3/R2=`53.5/37.0/24.0%` |
| 触发100 A2 | R5/R3/R2=`55.25/39.0/27.0%` |
| 触发100 A3 | R5/R3/R2=`48.5/30.0/19.0%` |
| 裁判 | E-VAds官方五级口径；`deepseek-chat`；1,112/1,112成功；失败0、重试0；总Token=`2,486,594`；`not_human_gold=true` |
| 裁决 | MMR强基线上的低支持触发、视频内证据补看、充分性复核与保守回退，在独立外部数据上稳定增精且零伤害 |
| 论文边界 | 验证完整闭环，不单独证明局部裁剪优于全帧上下文，也不证明验证器单模块直接增精 |
| 关键文件 | `full1000/{a0_protocol_audit.json,frozen_choices/protocol_audit.json}`、`full1000/judge_deepseek_v1/{preflight/dry_run_audit.json,results/api_results_partial.jsonl,results/policy_rows.jsonl,results/summary.json,SHA256SUMS}` |
| 哈希 | dry-run=`648be8a7403f32f30dd650375b11e05b4efc9aab341bd2887bab40b5ffc4bf04`；API=`46d99ef926712e08798ba04cac855d903023183b63b17dfe7799aac3ffcc5e5a`；rows=`66914ad42b109b4251a95c4c01a601f4b1c706214ad70672ed34b3ffdf3c5a08` |

### External-1000B补充Uniform8统一对照

| 字段 | 内容 |
|---|---|
| 目的 | 在同一External-1000B、同模型、同8视图与1,024视觉Token下补齐Uniform8，分离MMR静态选帧与完整选择性补看的收益 |
| Uniform8协议 | 64帧候选中的固定位置`[0,9,18,27,36,45,54,63]`；8视图；1,024视觉Token；关闭二次采样 |
| 推理完整性 | 五折各200题，共1,000题/200视频；错误0；answer-free协议审计通过 |
| Uniform8 | R5/R3/R2=`51.025/33.30/9.70%` |
| MMR8 | R5/R3/R2=`51.925/35.25/11.30%` |
| MMR8相对Uniform8 | `+0.90/+1.95/+1.60 pp`；95% CI分别为`[-0.80,+2.625]`、`[-0.15,+4.00]`、`[-0.40,+3.60] pp`，均跨0 |
| MMR-SelectRescue A3 | R5/R3/R2=`53.625/37.35/12.90%` |
| A3相对Uniform8 | `+2.60/+4.05/+3.20 pp`；95% CI分别为`[+0.825,+4.35]`、`[+1.85,+6.25]`、`[+1.10,+5.30] pp` |
| A3 vs Uniform R5 | 胜/平/负=`198/628/174` |
| A3 vs Uniform R2 | wrong→right/right→wrong=`72/40`；净增32题 |
| A3相对MMR8 | `+1.70/+2.10/+1.60 pp`；三个Bootstrap区间均完全大于0 |
| 裁判 | 官方E-VAds R5/R3/R2；`deepseek-chat`；复用旧评分28条，新增972/972次；重试0、失败0；新增Token=`2,211,723`；`not_human_gold=true` |
| 结论 | MMR8单独只有正向点估计，尚不能声称稳定优于Uniform8；完整A3同时稳定超过Uniform8与MMR8，增益应归因于“冗余受控初始证据 + 低支持触发 + 视频内补看 + 充分性门控”的联合闭环 |
| 远端路径 | `data/external/evads_v1/experiments/mmr_selectrescue_external1000b_v1/uniform8_v1/` |
| 哈希 | manifest=`935338318b5e013bde59a6aef9d06433c136e3876c913d0339304dcb4b8cf0d6`；dry-run=`ea664d70448188c952d5079c4c0f87c98d8e2e5d29599c6d0fe11a296f3e94ec`；API=`a224cee201dfba9fc84877e7071e1dc88d3599935be2685a222f5df54374d0b2`；rows=`2da0ea2c4200035c890834c8698973ab380e65ff4d57be462f7f0b992b098cde` |

## 自适应裁剪三臂同预算归因（2026-07-28）

| 字段 | 内容 |
|---|---|
| 状态 | `development_component_ablation_complete` |
| 目的 | 分离空间响应中心与不确定性自适应尺度的独立作用，确认创新点一不只是时间选帧 |
| 数据 | GroupCV-500中的冻结MMR低支持50题/50视频；其余450题保持MMR8 |
| 公平协议 | 同MMR8、同两个证据时刻、同OCR/ASR、同Qwen3与Prompt、同12视图、同3,104视觉Token、同冻结门控；关闭二次采样 |
| FixedCenter68 | 固定图像中心、固定边长0.68；完整500 Strict/Relaxed=`26.80/43.90%` |
| ResponseCenter68 | 问题条件视听响应中心、固定边长0.68；完整500=`27.00/44.00%` |
| AdaptiveScale | 响应中心 + 响应熵控制上下文尺度；完整500=`27.20/44.40%` |
| Response vs Fixed | Strict/Relaxed=`+0.20/+0.10 pp`；胜/平/负=`1/499/0`；Relaxed CI=`[0,+0.30] pp` |
| Adaptive vs Response | `+0.20/+0.40 pp`；`3/497/0`；Relaxed CI=`[0,+0.90] pp` |
| Adaptive vs Fixed | `+0.40/+0.50 pp`；`4/496/0`；Relaxed CI=`[+0.10,+1.10] pp` |
| 触发50 A2 | Fixed/Response/Adaptive Strict/Relaxed=`18/32`、`20/33`、`22/38%` |
| 触发50 A3 | Fixed/Response/Adaptive=`10/22`、`12/23`、`14/27%` |
| 风险 | 三项直接比较均无loss；Adaptive vs Fixed触发集=`4/46/0` |
| 裁判 | `deepseek-v4-flash` answer-only；复用旧同题同答案缓存；新增46/46次成功；失败0、重试0；新增Token=`32,615`；`not_human_gold=true` |
| 结论 | 响应中心有小幅正向作用，不确定性自适应尺度贡献更明显；完整自适应裁剪优于固定中心固定尺度，可作为创新点一的组件证据 |
| 边界 | 开发集归因而非新独立确认；不能声称紧裁剪普遍有效或带来大幅增精；外部集尚未单独确认自适应空间尺度 |
| 远端路径 | `evaluation/runs/qwen3_adaptive_crop_ablation_groupcv50_v1/` |
| 关键文件 | `dataset_v1/dataset_audit.json`、`full50_protocol_audit.json`、`frozen_choices_v1/*/protocol_audit.json`、`judge_deepseek_v1/{dry_run_audit.json,api_results_partial.jsonl,cross_arm_oof500.jsonl,summary.json}` |
| 哈希 | dry-run=`720b571979c4334dd929a13afbfff9689a8b985e635f17f26258f7d160c9d025`；pending=`a4aed77b7991eae1ae6d007c1e4a8f819e623f88a2126c57f9254f0af290a47a`；API=`2e9985b08f7285cc9276f329784173ccb8418b9d1e80053f18e742e0b9feb17a`；rows=`f24203ece79d66fedfad0d36cd1d303a32f1de56d82a52a765aa45d101ec9ebe`；summary=`a08b28891bbf264e6c0109ea5014a8dcbbee2ca7df3396093ebb3ec6663e776b` |

## 自适应裁剪Fresh-499独立确认（2026-07-28启动）

| 字段 | 内容 |
|---|---|
| 状态 | `answer_free_pipeline_running`；尚未裁判 |
| 目的 | 在与GroupCV-500、Confirm-D300、Confirm-1000视频均不重叠的新集合上，独立确认响应中心与不确定性自适应尺度 |
| 数据 | AdsQA测试集去重并移除空参考答案后499题/221视频；五折=`100/100/99/100/100` |
| 覆盖审计 | 视频/CLIP/OCR/分段ASR均`221/221`；ASR=`success 218 / no_audio 1 / no_speech 2` |
| A0 | clean Qwen3-VL；MMR8；8视图；1,024视觉Token |
| 触发 | 每折最低支持且视频不同的10题；合计50题/50视频 |
| 四臂 | `ExtraGlobal12`、`FixedCenter68`、`ResponseCenter68`、`AdaptiveScale` |
| 公平协议 | 同两个证据时刻、同OCR/ASR、同Prompt、同12视图与3,104视觉Token；关闭二次采样 |
| 门控 | threshold=`0.8933094143867493`；margin=`0.25`；Fresh-499禁止调参 |
| answer-free哈希 | questions=`3ea53d7736663c1d3a208ca10875fe4837c921fab1ff5b501c298377cd4042fd`；ASR combined=`ff06acd70757350bab91f4d67f724892fabd6dd17a62b8af0ffc96b97cfae15c`；MMR manifest=`9474f78c7ce97816c68f6fdb89b680b38cdb82698a8e8c3b89b6dcfea16f4d28` |
| 当前限制 | 不读取私有参考、不调用DeepSeek；最终协议审计后另行核算并授权 |
| 远端路径 | `evaluation/runs/qwen3_adaptive_crop_fresh499_v1/` |
| 后台入口 | `evaluation/scripts/run_qwen3_adaptive_crop_fresh499_v1.sh` |

### Fresh-499最终结果

| 字段 | 内容 |
|---|---|
| 状态 | `complete`；推理、充分性门控、统一裁判与10,000次视频聚类Bootstrap全部完成 |
| 完整性 | A0=`499/499`；A0验证器=`499/499`；四臂Smoke=`40/40`；四臂Full=`200/200`；A2验证器=`200/200`；错误0 |
| MMR8 A0 | Strict/Relaxed=`28.26/45.59%` |
| ExtraGlobal12 A3 | `28.66/46.49%`；相对A0=`+0.40/+0.90 pp`；胜/平/负=`7/491/1` |
| FixedCenter68 A3 | `28.66/46.59%`；`+0.40/+1.00 pp`；`8/490/1` |
| ResponseCenter68 A3 | `29.06/46.79%`；`+0.80/+1.20 pp`；`10/488/1` |
| AdaptiveScale A3 | `29.06/46.79%`；`+0.80/+1.20 pp`；`10/488/1` |
| Adaptive vs A0 Bootstrap | Relaxed CI=`[+0.40,+2.13] pp`；Strict约=`[0,+1.81] pp` |
| Adaptive纠错 | wrong→right/right→wrong=`5/1`；Strict纠正精度=`83.33%` |
| 触发50 A2 | ExtraGlobal/Fixed/Response/Adaptive Strict/Relaxed=`20/36`、`20/34`、`24/39`、`26/41%` |
| A2 Response vs Fixed | Relaxed=`+5 pp`；`5/45/0`；CI=`[+1,+9] pp` |
| A2 Adaptive vs Response | `+2 pp`；`2/48/0`；CI=`[0,+5] pp` |
| A2 Adaptive vs Fixed | `+7 pp`；`7/43/0`；CI=`[+3,+12] pp` |
| A2 Adaptive vs ExtraGlobal | `+5 pp`；`7/41/2`；CI=`[-1,+11] pp`，未稳定超过同锚点全帧 |
| 门控替换数 | ExtraGlobal=`20`；Fixed=`19`；Response=`20`；Adaptive=`20` |
| 裁判 | `deepseek-v4-flash`；answer-only；613/613成功；失败0、重试0；总Token=`484,317`；`not_human_gold=true` |
| 结论 | 完整联合策略在独立Fresh-499上稳定提高Relaxed；响应中心贡献可重复，自适应尺度为小幅辅助贡献，不能单独夸大；部分收益来自额外高分辨率上下文 |
| 远端结果 | `evaluation/runs/qwen3_adaptive_crop_fresh499_v1/judge_deepseek_v1/results_v1/` |
| 关键文件 | `summary.json`、`a2_cross_arm_selected50.json`、`api_results_partial.jsonl`、`complete499_*.jsonl`、`cross_arm_complete499.jsonl` |
| 哈希 | preflight=`1015d8a0d7b77a2e01d162650bad3d133946b256b899a48333c53774af650b8a`；pending=`628ae1cc107889b3a5b3a069c60046f433d81abf5872b0af19b1a7e7e994af9e`；API=`3f91d537627469371e92e4bd0051499f167fd3c2fc8f1210f9804baf6bfb23ed`；summary=`51bf62b309dd2a28f80581d0a2f4a81e0d2d8479364e6ba5894f59647a73c491`；A2 cross=`a85da86e7bed9aefcaeaa7d7eacdd4a1d8ca8192c6acd3ce7e630a268e81753e` |

## 支持度阈值校准与Full-5320冻结应用（2026-07-29）

| 字段 | 内容 |
|---|---|
| 状态 | `provisional_5319_complete`；唯一无法解析题明确排除，不冒充完整5320 |
| 校准数据 | 视频级隔离OOF-500；与Full-5320视频零重叠 |
| 阈值目标 | 依次最大化Relaxed、Strict，减少right-to-wrong，再减少触发率 |
| 冻结阈值 | `tau=0.9602926671504974`；A0支持度低于阈值才使用AdaptiveScale A2 |
| 校准嵌套OOF | MMR8=`26.20/42.70%`；阈值策略Strict/Relaxed=`39.00/56.80%` |
| 校准配对 | 触发417/500；胜/平/负=`140/331/29`；wrong→right/right→wrong=`31/14` |
| 校准Bootstrap | Relaxed差CI=`[+11.10,+17.10] pp`；Strict=`[+9.40,+16.20] pp` |
| Full触发 | `4905/5320=92.20%`；未触发415 |
| Full A2推理 | 旧产物精确复用530，新推理4375；12视图、3,104视觉Token、关闭二次采样；审计失败0 |
| Full评测数 | 5319；唯一题初次与一次授权补评均无法解析，停止继续重试 |
| MMR8 | Strict/Relaxed=`31.89/47.71%` |
| 阈值AdaptiveScale | `38.05/57.41%` |
| 相对MMR8 | Strict/Relaxed=`+6.17/+9.70 pp`；胜/平/负=`1417/3267/635` |
| 纠错 | wrong→right/right→wrong=`747/419`；Strict纠正精度=`64.07%` |
| Full Bootstrap | 1,521视频簇、10,000次；Relaxed差CI=`[+8.69,+10.74] pp`；Strict=`[+4.93,+7.46] pp` |
| Token成本 | MMR8=`1,024`；触发A2=`3,104`；阈值策略平均约`2,941.74` |
| 裁判调用 | 精确预检4304个新候选；4303成功；初次失败1、授权补评失败1、自动重试0；新增成功调用总Token=`2,788,812` |
| 裁判属性 | 旧answer-only DeepSeek口径；机器裁判；`not_human_gold=true` |
| 结论 | 冻结支持度阈值能把视听证据补看稳定转化为明显QA增益；但92.2%触发属于准确率优先，不得宣称低成本 |
| 边界 | Full-5320不得回看结果调阈值；成本受限版本只能在新确认集预注册，不能事后替换主策略 |
| 远端根目录 | `evaluation/runs/qwen3_threshold_full5320_v1/` |
| 关键结果 | `judge_deepseek_v1/provisional_excluding_one_v1/{summary.json,expanded_threshold_scores_5319.jsonl,excluded_unparseable.jsonl}` |
| 关键审计 | `adaptive_scale_protocol_audit_v1/audit.json`、`judge_deepseek_v1/preflight_v1/dry_run_audit.json`、`judge_deepseek_v1/results_v1/api_failures*.jsonl` |
| 哈希 | preflight=`392b6aa484aa50aecd001cd24c2d36789d57a113c23a3e1a652d6fa8d89417f2`；API=`591530ab9090eac0a4639ac24ec1b04a19f47b331c9392d9206bc6d99d3f599b`；summary=`c362029f75574227764cd86a89bcf5c4142e580aa8afa79dcf54cc44c18e6627`；rows=`2d2f9f7a1f4bfc2d6a58278367841cd42db7bdfaf8e16991fdd4ba2785dcfaea` |

## Full触发集固定尺度归因（2026-07-29）

| 字段 | 内容 |
|---|---|
| 状态 | `provisional_4904_complete`；一次性裁判1条失败后未重试，严格配对排除该题 |
| 目的 | 在Full阈值策略实际触发的4,905题上，检验响应熵驱动的自适应尺度是否优于固定边长0.68 |
| 对照 | `AdaptiveScale12` vs `ResponseCenter68` |
| 公平协议 | 同触发题、MMR基础帧、证据时刻、裁剪响应峰、OCR/ASR、Qwen3、Prompt、12视图和3,104视觉Token；仅尺度规则不同；关闭二次采样 |
| AdaptiveScale12 | Strict/Relaxed=`36.562/56.219%` |
| ResponseCenter68 | Strict/Relaxed=`36.970/56.342%` |
| Response相对Adaptive | Strict/Relaxed=`+0.408/+0.122 pp`；胜/平/负=`200/4512/192` |
| 纠错 | wrong→right/right→wrong=`121/101`；Strict纠正精度=`54.50%` |
| Bootstrap | 1,509视频簇、10,000次；Relaxed差95% CI=`[-0.269,+0.512] pp`；Strict=`[-0.164,+1.007] pp` |
| 裁判 | 预检新增1,575项、复用5,526项；1,574成功、1失败、自动重试0；旧answer-only DeepSeek口径；`not_human_gold=true` |
| 结论 | 固定尺度点估计略高但区间跨0，无法证明其稳定优于自适应尺度，也无法证明自适应尺度在Full触发集有独立增益；自适应尺度应降为机制完整性与开发集辅助组件，响应中心、视听证据组织和充分性门控才是更稳的主贡献 |
| 远端根目录 | `evaluation/runs/qwen3_threshold_response_center68_full_v1/` |
| 关键结果 | `judge_responsecenter68_vs_adaptive_v1/provisional_excluding_one_v1/{summary.json,expanded_scores_4904.jsonl}` |
| 哈希 | protocol=`d836ffd41bfe5d73ce2c6be5d973b26bc6597134866ad8cf089b68d681a23b34`；preflight=`39fc8571f616a045a7995683da1ee08faf26ce6d5c7acb13a2981e735f9214f7`；API=`29f17b05c8e0e6f4c1228050b8c19df0eccb1a63cf75bf33ee11f537a9f71089`；summary=`4c16ae8793cd5677caaa652cb9b6a5b5ffd4b5280a280da4785b16d74f377689`；rows=`382cc158435008ff7063a08d4775018fa7d35d0041eeec5ec6c117bd19749c79` |

## 支持度阈值准确率—成本前沿复算（2026-07-29）

| 字段 | 内容 |
|---|---|
| 状态 | `complete_no_gpu_no_api` |
| 选择数据 | 仅使用视频级OOF-500校准结果；Full-5319标签不参与阈值选择 |
| 触发规则 | `A0 support_probability < threshold`时执行AdaptiveScale12补看 |
| 准确率最优阈值 | `0.9602926671504974` |
| 校准表现 | 触发`464/500=92.8%`；Strict/Relaxed=`39.8/57.7%` |
| 成本型阈值定义 | 在校准Strict和Relaxed均距各自最优不超过`0.5 pp`的候选中，选择触发最少者 |
| 成本型最优阈值 | `0.9361833035945892` |
| 成本型校准表现 | 触发`353/500=70.6%`；Strict/Relaxed=`40.0/57.3%`；right-to-wrong=`7`，低于准确率点的`14` |
| Full-5319准确率点 | 触发`4904/5319=92.20%`；Strict/Relaxed=`38.052/57.407%` |
| Full-5319成本点 | 触发`3624/5319=68.13%`；Strict/Relaxed=`37.902/56.947%` |
| Full成本 | 触发率减少`24.07 pp`；Strict/Relaxed仅减少`0.150/0.461 pp` |
| 平均选中答案Token | `2941.71 → 2441.17`，减少`500.55`，约`17.0%` |
| 平均实际执行答案Token | `3885.82 → 3138.85`，减少`746.97`，约`19.2%`；不含验证器成本 |
| Full成本点 vs MMR8 | Strict/Relaxed=`+6.02/+9.24 pp`；视频簇Bootstrap区间均完全大于0 |
| 使用边界 | `0.96029`仍是已预注册并独立应用的准确率主结果；`0.93618`是校准集导出的成本型次要工作点，Full结果只能标为事后敏感性分析，若要作为唯一部署阈值还需新独立确认 |
| Token说明 | AdaptiveScale与ResponseCenter68均为12视图、3,104视觉Token；自适应尺度本身不省Token，Token节省来自阈值减少A2触发 |
| 远端路径 | `evaluation/runs/qwen3_threshold_calibration500_v1/threshold_accuracy_cost_analysis_v1/` |
| 输入哈希 | calibration=`3a63da1de2b41fd82350f770974a45c3a4e688adf05bee60b2e0dd00e3c2874b`；Full scores=`2d2f9f7a1f4bfc2d6a58278367841cd42db7bdfaf8e16991fdd4ba2785dcfaea`；Full support=`fdb19e07b00f9f8781683438857b72768c345231e7f2a49025a15c2aa432ece4` |

## 支持度阈值Pareto膝点与风险审计（2026-07-29）

| 字段 | 内容 |
|---|---|
| 目的 | 在不人工指定触发比例的前提下，从OOF校准曲线自动选择成本—精度均衡点 |
| 选择数据 | 视频级OOF-500；500题/100视频；Full标签未参与阈值选择 |
| 选择算法 | 最大化`标准化Relaxed增益 - 触发率`；并列时依次比较Relaxed、Strict、right-to-wrong和触发数 |
| 自动阈值 | `tau_knee=0.9195213913917542` |
| OOF触发 | `280/500=56.0%` |
| OOF结果 | Strict/Relaxed=`37.0/55.2%`；MMR8=`26.2/42.7%` |
| OOF配对 | 胜/平/负=`111/374/15`；wrong-to-right/right-to-wrong=`29/7` |
| OOF Bootstrap | 100视频簇、10,000次；Strict增量CI=`[+8.0,+13.8] pp`；Relaxed=`[+9.8,+15.3] pp` |
| OOF风险审计 | right-to-wrong率=`1.4%`；95% CI=`[0.4,2.4]%`；探索性3%风险线上通过 |
| OOF Token | 平均选中答案=`2,188.8`；A0后按需执行A2=`2,762.24`；验证器成本未计 |
| Full角色 | 仅事后敏感性，不能作为阈值独立确认或重新调参依据 |
| Full-5319触发 | `2,887/5,319=54.28%` |
| Full-5319结果 | Strict/Relaxed=`37.507/56.336%`；相对MMR8=`+5.621/+8.629 pp` |
| Full Bootstrap | 1,521视频簇、10,000次；Strict增量CI=`[+4.652,+6.602] pp`；Relaxed=`[+7.778,+9.507] pp` |
| Full Token | 平均选中答案=`2,152.96`；实际执行口径=`2,708.76`；验证器成本未计 |
| 风险边界 | Full right-to-wrong率=`3.65%`，95%上界约`4.17%`，未保持探索性3%风险线 |
| 推荐定位 | 作为“Pareto膝点/均衡工作点”；不宣称严格共形风险保证 |
| 远端路径 | `evaluation/runs/qwen3_threshold_calibration500_v1/threshold_risk_knee_analysis_v1/` |
| 分析脚本 | `evaluation/tools/analyze_threshold_risk_knee_v1.py` |
| 运行边界 | API调用0、GPU推理0、历史结果未覆盖 |

## AdsQA补充分区与Full-7844合并结果（2026-07-30）

| 字段 | 内容 |
|---|---|
| 状态 | `provisional_7844_complete`；原始7,846题中两个不同候选连续两次无法解析，明确排除 |
| 数据修复 | 原5,320题来自`answer`；补充2,526道`_modify`题来自`gt_answer`；两分区题号互斥 |
| 冻结协议 | clean Qwen3-VL-8B；固定Prompt；关闭二次采样；Uniform/CLIP/MMR均8视图、1,024 Token |
| MMR | 64候选帧；问题相关性与时间冗余联合排序；`lambda=0.70` |
| AdaptiveScale | MMR8初答；RealClaim支持度阈值`0.9602926671504974`；低支持时执行两个证据时刻的全帧+上下文裁剪并加入OCR/分段ASR；12视图、3,104 Token |
| 补集触发 | 原始`2270/2526=89.87%`；排除题后`2269/2525=89.86%` |
| 补集裁判 | 10,104槽去重为9,807唯一候选；首轮5,857成功；余额不足3,949与格式失败1；授权后仅重试3,950，最终9,806唯一分数，1条连续两次无法解析 |
| 补集Uniform8 | Strict/Relaxed=`30.85/48.26%` |
| 补集CLIPTopK8 | `32.08/49.68%`；相对Uniform=`+1.23/+1.43 pp`，Bootstrap区间跨0 |
| 补集MMR8 | `36.32/54.06%`；相对Uniform=`+5.47/+5.80 pp` |
| 补集AdaptiveScale | `45.07/65.05%`；相对MMR=`+8.75/+10.99 pp` |
| 补集Adaptive vs MMR | 胜/平/负=`700/1564/261`；wrong→right/right→wrong=`406/185`；Strict CI=`[+6.90,+10.70] pp`；Relaxed CI=`[+9.59,+12.40] pp` |
| Full-7844 Uniform8 | `29.70/45.86%` |
| Full-7844 MMR8 | `33.31/49.75%`；相对Uniform=`+3.61/+3.89 pp` |
| Full-7844 AdaptiveScale | `40.31/59.87%`；相对MMR=`+7.00/+10.12 pp`；相对Uniform=`+10.61/+14.00 pp` |
| Full Adaptive vs MMR | 胜/平/负=`2117/4831/896`；wrong→right/right→wrong=`1153/604`；Strict CI=`[+5.96,+8.09] pp`；Relaxed CI=`[+9.28,+10.98] pp` |
| Full触发与成本 | `7173/7844=91.45%`；平均选中答案视觉Token=`2926.07`；准确率优先 |
| 裁判属性 | 统一answer-only DeepSeek机器裁判；`not_human_gold=true`；补集成功调用总Token=`7,741,160` |
| 论文结论 | MMR8稳定优于Uniform8；支持度触发的视听证据补看在MMR8上进一步稳定增精；两个答案字段分区方向一致 |
| 写作边界 | 不把自适应尺度写成独立显著增精；不把91.45%触发写成低成本；CLIP只在补集2,525题报告，未用不完整旧CLIP评分拼Full表 |
| 补集路径 | `evaluation/runs/qwen3_adsqa_supplement2526_v1/judge_deepseek_v1/supplement2526_v1/provisional_excluding_one_v1/` |
| Full路径 | `evaluation/runs/qwen3_adsqa_full7846_merged_v1/provisional_excluding_two_v1/` |
| 补集哈希 | summary=`a8c0af11f76bdfaf73a502e399f14a1da699aad2ab7831eb12856dc5fcc592b5`；rows=`c0a6fe81c03f84fa4eb46749ca06b18e0e6548349fd36c9557de6f359dd744ce` |
| Full哈希 | summary=`106d67567939c96dbceae45b7f11a2cf2b4865ad9edc3ce8065e591bb53baa6e`；rows=`09acab4c748ef5e718898904cd79952314fada5ed987a65bb456485cb21a22e1` |

论文分层结果、实验设置与写作边界原整理于《AdsQA 论文定稿实验结果总表》（历史来源，未收入本去重归档）；本归档以《AdsQA 论文实验收尾与最终结果交付》为准。

## ReAd-R统一重评及与Full-7844同题比较（2026-07-30）

| 字段 | 内容 |
|---|---|
| 状态 | `complete_no_new_api`；复用2026-07-24已经完成的统一DeepSeek重评，未重复付费调用 |
| ReAd-R身份 | AdsQA官方GRPO训练的`Qwen2.5-7B-VL-ReAd-R`；8个均匀采样图像+ASR |
| 候选抽取 | 只使用非空`<answer>...</answer>`内容；不把`<think>`送入裁判；5条缺少合法标签的预测排除 |
| 裁判协议 | 与本文主实验相同的冻结legacy answer-only DeepSeek Prompt；Prompt SHA256=`898a28fac10dd14458289409e163370197d43573316f3cc341c5489f8ccb6d19`；`not_human_gold=true` |
| ReAd-R重评覆盖 | 7,846个唯一GT题；7,829条来源预测；7,824条合法answer-tag结果；Strict/Relaxed=`29.82/53.51%` |
| 同题配对池 | 与本文Full-7,844交集为7,822题、1,539视频；ReAd-R独有2题，本文独有22题 |
| 配对ReAd-R | Strict/Relaxed=`29.81/53.50%` |
| 配对Uniform8 | `29.79/45.97%`；相对ReAd-R=`-0.03/-7.54 pp` |
| 配对MMR8 | `33.39/49.82%`；相对ReAd-R=`+3.58/-3.68 pp` |
| 配对AdaptiveScale | `40.39/59.92%`；相对ReAd-R=`+10.57/+6.42 pp` |
| Adaptive配对统计 | 胜/平/负=`2288/4069/1465`；wrong→right/right→wrong=`1684/857`；Strict纠正精度=`66.27%` |
| Adaptive Bootstrap | 10,000次视频聚类；Strict差CI=`[+9.23,+11.93] pp`；Relaxed差CI=`[+5.40,+7.42] pp` |
| 解释边界 | 同题统一裁判支持本文最终系统稳定超过本地ReAd-R；但两者基座、训练方式和视觉预算不同，只能作跨系统总体比较，组件因果增益仍看同Qwen3主表 |
| ReAd-R重评路径 | `evaluation/runs/rejudge_readr_answeronly_v1/full/judge_deepseek_legacy_answer_tag_only_v2/` |
| 配对结果路径 | `evaluation/runs/rejudge_readr_answeronly_v1/full/paired_vs_qwen3_full7844_v1/` |
| 配对哈希 | summary=`5bdda8760b0894577314d65e07bb47406ab4b01efb69bc07375ea2b0c29f2329`；rows=`efa09edf19776931fa2f983f7f7e54dc5dc84ab9be1d167439ce9d1a104f3049`；audit=`0fb4f374f23567776f40be136b916356c78206e2d45393829f92f2a66ca8ee61` |

## Clean Qwen2.5四臂跨基座复现（2026-07-30）

| 字段 | 内容 |
|---|---|
| 状态 | `complete_groupcv500_calibration_only`；未读取Confirm或Full标签 |
| 数据 | 视频级隔离GroupCV-500；500题、100视频、五折 |
| 模型 | clean `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-VL-7B-Instruct`；不是ReAd-R |
| A0协议 | Uniform8/MMR8；8视图、512分辨率、原生1,296视觉Token、关闭二次采样 |
| A2协议 | Adaptive12/ExtraGlobal12；12视图、实际3,992视觉Token，预算上限4,096 |
| Uniform8 | Strict/Relaxed=`26.8/42.4%` |
| MMR8 | `27.4/45.0%`；相对Uniform点估计=`+0.6/+2.6 pp`，配对CI跨0 |
| Adaptive12原始候选 | `27.2/44.7%`；相对MMR Relaxed CI=`[-1.4,+0.8] pp` |
| ExtraGlobal12原始候选 | `27.0/44.8%`；相对MMR Relaxed CI=`[-1.3,+0.9] pp` |
| 固定充分性规则 | A2支持度须至少比A0高`0.25`；只从GroupCV-500学习A0阈值 |
| Qwen2.5准确率/膝点阈值 | `tau=0.39243705570697784`；不得复用Qwen3阈值 |
| 全500门控Adaptive | 触发16、替换4；Strict/Relaxed=`28.0/45.7%`；相对MMR=`+0.6/+0.7 pp`；4胜0负 |
| 全500Bootstrap | 100视频簇、10,000次；Strict差CI=`[0,+1.4] pp`；Relaxed=`[+0.1,+1.5] pp` |
| 五折嵌套折外Adaptive | Strict/Relaxed=`27.8/45.5%`；相对MMR=`+0.4/+0.5 pp`；3胜0负；触发16、替换3 |
| 嵌套Bootstrap | Strict差CI=`[0,+1.0] pp`；Relaxed=`[0,+1.2] pp` |
| 同门控ExtraGlobal控制 | 全500=`27.8/45.6%`；4胜0负；与Adaptive差异极小 |
| 成本点 | `tau=0.3075181394815445`；触发2.0%、替换0.4%；全500=`27.6/45.3%` |
| Token成本 | 准确率点平均选中答案约1,317.57；按A0后按需执行A2约1,423.74；不含验证器 |
| 裁判预检 | 2,000方法槽；answer-only去重后1,081次新调用；四臂相同答案复用919条 |
| 裁判执行 | `deepseek-v4-flash`；1,081成功、失败0、重试0；总Token=`826,391`；`not_human_gold=true` |
| 结论 | 跨基座只有弱正向、无负向证据；证明门控可迁移，但不足以支持Qwen2.5 Full扩展；自适应裁剪仍未优于同预算全帧控制 |
| 远端根目录 | `evaluation/runs/qwen25_final_arch_groupcv500_v1/` |
| 结果目录 | `judge_deepseek_answeronly_v1/` |
| 脚本 | `evaluation/tools/judge_qwen25_final_arch_groupcv500_v1.py`；`evaluation/scripts/run_qwen25_final_arch_groupcv500_judge_v1.sh` |
| 哈希 | dry-run=`b0d2da216802394b23a6c97aa8715fb6b7ec9cbf2af5875ab2c4549a890e8cd5`；API=`9196e848c41f7f3532fe997747eef4d7a0b96c63d1065f04173c45f1436e8335`；paired=`dfd2cf951dc1f6c4a16adf99c19bb42c80a5b0727a6af062378fc81340bc8ddf`；threshold=`193acbc0ecc1efeac104ec5a98776fdfa9af5e26fb58535e90ba038d3930ac81`；summary=`71db976d940d996884d85435d30e98ba7919a6b284b7fb446db8c7ffe3102507` |

### Qwen2.5门控阈值与充分性边际的离线诊断（2026-07-30）

仅使用上述视频级GroupCV-500的既有逐题预测、支持度和统一裁判分数；未读取Confirm/Full标签，未重跑模型或调用API。目的不是事后挑选Full结果，而是判断“Qwen2.5触发率过低”能否仅靠调整A0支持度阈值解决。

| 工作点 | A0阈值 | A2-A0边际 | 触发/替换 | 相对MMR Strict/Relaxed | 胜/负 |
|---|---:|---:|---:|---:|---:|
| 已冻结准确率点 | `0.392437` | `0.25` | `16/4`（3.2%/0.8%） | `+0.6/+0.7 pp` | `4/0` |
| 约5%触发 | `0.500000` | `0.25` | `25/5`（5.0%/1.0%） | `+0.6/+0.7 pp` | `4/0` |
| 约50%触发 | `0.952574` | `0.25` | `234/7`（46.8%/1.4%） | `+0.6/+0.6 pp` | `4/1` |
| 100%触发 | `0.984094` | `0.25` | `500/7`（100%/1.4%） | `+0.6/+0.6 pp` | `4/1` |
| 联合放宽的嵌套折外探索 | 平均`0.937046` | `0.002980` | `279/27`（55.8%/5.4%） | `+0.6/+0.8 pp` | `6/1` |

结论：提高A0触发阈值会显著增加补看，但固定边际`0.25`下最多只新增3次实际换答且引入1次损失；联合放宽边际虽增加替换，却在折外数据出现损失。因此Qwen2.5的瓶颈是A2与A0支持度的可分性，而不是阈值取值本身。论文不应为了提高触发率人为提高阈值；保留`0.392437`作为Qwen2.5的安全工作点，并将该跨基座实验定位为弱迁移证据。若要让Qwen2.5成为主结果，后续需改进验证器或A2候选质量，并在独立确认集验证。

补充候选诊断：500题中A2文本与A0不同的有`461`题，但统一裁判仅见A2优于A0=`7`题、相同=`442`题、低于=`12`题；其中`456`题的A2-A0支持度差在`[0,0.03)`，说明大量改写没有形成可辨认的证据增益。下一候选应从“全文重写”改为“证据约束的最小编辑”：先由问题类型路由OCR/ASR/视觉证据，再仅在可引用的决定性事实与A0冲突或补足时改答；门控也应学习A2相对A0的配对收益，而非继续只调两个绝对支持度阈值。

### Qwen2.5证据约束最小编辑Smoke-50（2026-07-30）

从GroupCV-500中按折各取10条A0支持度最低且视频不重复的困难样本，共50题、
50视频。该选择只用于方向门禁，不代表总体分布。输入仍为clean Qwen2.5，
MMR8初答后补充4个AdaptiveScale证据视图；A2固定12视图、实际视觉Token不超过
4,096、关闭二次采样。新Prompt要求模型只在引用的视觉、OCR或ASR证据直接否定
或补足A0决定性事实时做最小修改，否则原样保留A0。

协议审计结果：18题形成合法且有证据ID回指的改答，32题保留A0；23个不满足
输出契约的生成全部安全回退A0，非法答案替换为0。统一answer-only DeepSeek
裁判复用34条历史结果，仅新增16次调用，成功16、失败0、重试0，总Token
`11,925`，`not_human_gold=true`。

| 方法（同一困难50题） | Strict | Relaxed |
|---|---:|---:|
| MMR8 A0 | 6.0% | 17.0% |
| 旧Adaptive12全文候选 | **12.0%** | **23.0%** |
| EvidenceMinimalEdit12 | 10.0% | 22.0% |

MinimalEdit12相对MMR8为5胜/43平/2负，Strict/Relaxed=`+4/+5 pp`，
wrong→right/right→wrong=`2/0`，纠正精度`71.43%`；Relaxed差Bootstrap
CI=`[-1,+12] pp`。在真正改答的18题中为5胜/11平/2负，Relaxed=`+13.89 pp`。
但相对旧Adaptive12仅1胜/47平/2负，Strict/Relaxed=`-2/-1 pp`，且出现
1个right→wrong。因此它通过“优于A0”的方向门禁，却没有超过现有A2候选，
不扩到300题，也不替换论文最终方法。

这一负结果支持的后续方向不是继续调A0阈值，而是训练或校准“候选相对收益”
门控：在旧Adaptive12与MinimalEdit12之间预测哪个候选真正提高裁判分数，或
把最小编辑约束作为旧A2的保守回退规则。不得用本困难50题直接选择最终阈值。

远端根目录：
`evaluation/runs/qwen25_evidence_minimal_edit_smoke50_v1/`。协议审计SHA256=
`91abcc1b8a363a13b45180035d799c76cb4032e6c4921521041ad955e9177c22`；
预检SHA256=`f3f18cf540f833d31a3c261cf2c015744bc4aa78986e5814064da7b4faacfd43`；
逐题配对SHA256=`adeef9162153f604acdcad09a7568054e8d027d4d0642b11d3834260f06f631a`；
summary SHA256=`9c71b5afbb9c77cdbe20d2ca6d68554790c146e7cad73e1315810a341512c63a`。

### Qwen2.5 Pairwise收益门控五折OOF（2026-07-30）

为替代手工`A0阈值+A2支持度边际`，仅使用GroupCV-500既有answer-free
特征和统一裁判标签，训练双逻辑门控分别估计`P(A2>A0)`与`P(A2<A0)`。
特征包括A0/A2支持度、答案差异、数字变化、OCR/ASR覆盖、问题类型和证据锚点，
不读取参考答案文本。采用视频级五折外层评估，并在每个外层训练池内再次进行
四折OOF阈值校准；Confirm和Full标签均未读取。

标签极度稀疏：500题中Adaptive12相对MMR8仅`7`个gain、`481`个tie、
`12`个harm。v1只约束内层纠正精度，造成部分折放行大量平局候选：

| 版本 | 触发/替换 | 胜/负 | Strict/Relaxed | 相对MMR |
|---|---:|---:|---:|---:|
| Pairwise v1 | `279/151`（55.8%/30.2%） | `4/5` | `27.4/45.0%` | `0/0 pp` |
| Pairwise v2（内层替换率≤10%） | `279/11`（55.8%/2.2%） | `1/1` | `27.6/45.1%` | `+0.2/+0.1 pp` |
| 冻结`tau+margin`嵌套OOF | `16/3`（3.2%/0.6%） | `3/0` | **`27.8/45.5%`** | **`+0.4/+0.5 pp`** |

v2纠正精度仅50%，Bootstrap相对A0的Relaxed差CI=`[-0.3,+0.6] pp`；
相对冻结门控CI=`[-0.9,0] pp`，未通过预设门禁。结论是当前候选收益标签数量
不足以训练稳定的pairwise门控；不继续扫描分类器、特征或阈值，也不将
MinimalEdit并入三候选正式系统。Qwen2.5若要明显提高绝对精度，下一优先级应
转向提高生成基座的广告证据利用能力，例如已验证有效的AdsSFTLoRA，再在新的
视频隔离确认集检验证据补看增量。

远端结果：
`evaluation/runs/qwen25_pairwise_gain_gate_groupcv500_v1/`与
`evaluation/runs/qwen25_pairwise_gain_gate_groupcv500_v2/`。v1 summary/
OOF SHA256=`2275302710b972a512f44bdf93bc6da67b9f7193d9c66b0eb397a9f063cc49e1`/
`386fd6f7d9d8b28b9769c013b86bdb85b075a1946f323c60d0b74d321ba29463`；
v2=`3ee06a18ba244801d0ed4eaba9a5be4c8813aa96c6dc60c5b274dfbecd6933ff`/
`20dc323e6fc11b57bba7559ad184b5e33450a2a90e08d4d916bc7958fd1f5ebe`。

### AdsSFTLoRA + MMR8方向门禁与Adaptive12预检（2026-07-30）

| 项目 | 结果 |
|---|---|
| 数据与隔离 | GroupCV-500；5折×100题；100视频；沿用原AdsSFTLoRA视频隔离 |
| 基座与适配器 | clean `Qwen2.5-VL-7B-Instruct` + 各外层折独立`AdsSFTLoRA_Raw8`适配器 |
| Raw8/MMR8协议 | 8视图、448、实际1,024视觉Token、相同Prompt、关闭二次采样 |
| `AdsSFTLoRA_Raw8` | Strict/Relaxed=`21.40/40.10%` |
| `AdsSFTLoRA_MMR8` | Strict/Relaxed=`21.40/42.00%` |
| MMR8配对结果 | 83胜/349平/68负；Strict/Relaxed=`0/+1.90 pp`；纠正精度54.97% |
| MMR8 Bootstrap | 100视频簇、10,000次；Strict差CI=`[-3.20,+3.20] pp`；Relaxed=`[-0.60,+4.40] pp` |
| MMR8裁判 | 历史唯一请求复用500；新调用436/436成功；失败0；同题同答案共享64条 |
| 方向门禁 | 点估计正向，通过继续生成A2；CI跨0，不能单独宣称稳定增益 |
| A2生成 | `AdsSFTLoRA_Adaptive12`与`AdsSFTLoRA_ExtraGlobal12`各500/500，错误0 |
| A2协议 | 12视图、512全帧+896补看、实际3,992视觉Token；同折LoRA；关闭二次采样 |
| 验证器 | 冻结Qwen3 RealClaim985；A0与两组A2支持度各500条完整 |
| A2原始Adaptive12 | Strict/Relaxed=`23.20/43.20%`；相对MMR=`+1.80/+1.20 pp`；30胜23负 |
| A2原始ExtraGlobal12 | Strict/Relaxed=`23.40/43.20%`；相对MMR=`+2.00/+1.20 pp`；33胜25负 |
| 原始臂Bootstrap | Adaptive Strict/Relaxed差CI=`[-0.20,+3.80]/[-0.70,+3.10] pp`；ExtraGlobal=`[0,+4.20]/[-0.60,+3.10] pp` |
| 全500准确率阈值 | `tau=0.6652668118`、margin=`0.25`；触发34、替换5；3胜0负；最终=`21.60/42.40%` |
| 五折嵌套折外门控 | 触发27、替换4；2胜0负；最终=`21.60/42.30%`；相对MMR=`+0.20/+0.30 pp` |
| 嵌套Bootstrap | Strict差CI=`[0,+0.60] pp`；Relaxed=`[0,+0.80] pp` |
| A2裁判执行 | 1,500方法槽；708个唯一候选；历史精确复用500；新增208/208成功；失败0；总Token=`141,243` |
| 结论 | LoRA后A2点估计改善，但门控仍只安全替换极少数；Adaptive未优于ExtraGlobal；下一优先级为512/1,296 Token的LoRA-MMR8公平复现 |
| MMR8远端根 | `evaluation/runs/adsqa_sft_lora_mmr8_groupcv500_v1/` |
| A2远端根 | `evaluation/runs/adsqa_sft_lora_adaptive12_groupcv500_v1/` |
| A2结果哈希 | summary=`482231a3456dbd0a2fa82393c62fa4894aa779a14731f1d98966010652e5dc36`；threshold=`2e3780d0f3954ffe8bc4d272c88fcf626c53e5eef6f378397765396a6a870b50` |

### AdsSFTLoRA + MMR8 512/1,296 Token公平复现（2026-07-30）

| 项目 | 结果 |
|---|---|
| 状态 | `complete_branch_closed`；500/500，错误0，协议审计通过 |
| 唯一变量 | 旧LoRA-MMR8的448/1,024改为512/1,296；LoRA、MMR帧、Prompt、数据划分均不变 |
| 视觉协议 | 8视图、512、实际1,296视觉Token、预算4,096、关闭二次采样 |
| 候选变化 | 相对448版本相同181题、变化319题 |
| LoRA-MMR8 448 | Strict/Relaxed=`21.40/42.00%` |
| LoRA-MMR8 512 | Strict/Relaxed=`21.40/41.30%` |
| 512 vs 448 | 50胜/393平/57负；Strict/Relaxed=`0/-0.70 pp` |
| 配对Bootstrap | 100视频簇、10,000次；Strict差CI=`[-2.60,+2.60] pp`；Relaxed=`[-2.80,+1.50] pp` |
| 同协议clean Qwen2.5 MMR8 | `27.40/45.00%`；比LoRA512高`+6.00/+3.70 pp` |
| LoRA512 vs clean配对 | 91胜/280平/129负；Strict差CI=`[-10.60,-1.20] pp`；Relaxed差CI=`[-7.30,-0.10] pp` |
| 裁判缓存 | 819个唯一请求；四份同Prompt历史缓存复用525；新增294 |
| 裁判执行 | 294/294成功，失败0；`deepseek-v4-flash`；总Token=`199,505`；`not_human_gold=true` |
| 结论 | 提高分辨率不能挽救AdsSFTLoRA；LoRA内部MMR增益不等于超过clean基座；停止LoRA-512 Adaptive12、阈值扫描和Full扩展 |
| 远端根 | `evaluation/runs/adsqa_sft_lora_mmr8_512_groupcv500_v1/` |
| 脚本 | `evaluation/tools/audit_adsqa_selected8_inference_v2.py`；`evaluation/tools/preflight_adsqa_sft_lora_mmr8_512_judge_v1.py`；`evaluation/tools/judge_adsqa_sft_lora_mmr8_512_v1.py` |
| 哈希 | inference protocol=`73aeb8931217a3eaf8125b84c74fd5687a15d4ccffb8bfb8fcaa77b690575805`；judge summary=`dfd2cc554adb2cd2bd28d4b7d8b497f0b69e7ea980ea1a352c326c6ea73274a6`；vs-clean summary=`8830ad84a02622b7a08afa2fa8727fccaac5362ebd3eb6992eecb56eb4855056` |

### Clean Qwen2.5最终系统 vs ReAd-R Full同题诊断（2026-07-30）

| 项目 | 结果 |
|---|---|
| 配对池 | 7,824题、1,539视频；统一legacy answer-only DeepSeek历史分数；本轮API调用0 |
| clean Qwen2.5最终系统 | Strict/Relaxed=`27.81/48.94%`；0/0.5/1=`2342/3306/2176` |
| ReAd-R Qwen2.5 | Strict/Relaxed=`29.82/53.51%`；0/0.5/1=`1784/3707/2333` |
| 配对差 | 本文−ReAd-R=`-2.01/-4.57 pp`；胜/平/负=`1569/4098/2157` |
| Bootstrap | 1,539视频簇、10,000次；Strict差CI=`[-3.29,-0.72] pp`；Relaxed差CI=`[-5.62,-3.51] pp` |
| 缺口构成 | 本文多558个0分、少401个0.5分和157个1分；核心是答案覆盖/训练能力，不是门控阈值 |
| 当前门控上限 | Full只触发159、替换25、10胜1负；Relaxed仅净增`0.076 pp`，无法填补4.57 pp |
| 停止路线 | AdsSFTLoRA、分辨率增加、自由/结构化反思、DualConsensus和继续扫描阈值 |
| 下一候选 | 以同一ReAd-R checkpoint为共同回答器，测试`原始Uniform8→MMR8→Adaptive12→充分性门控`的增量 |
| 远端路径 | `evaluation/runs/qwen25_adsqa_full7846_v1/paired_vs_readr_v1/` |
| 哈希 | paired=`ca4f6af4ae2cf0977b80037a96978f20e99f45dd9522cddde359ce93df17b42b`；summary=`b9d478dad6ee01e2928c0ec7edcd60827bc1f47fd0c49ea0ae7d6ba9a7820695` |

### ReAd-R共同基座增量Pilot-300（2026-07-30，已完成）

| 项目 | 冻结口径 |
|---|---|
| 目的 | 判断本文证据定位与充分性门控能否在ReAd-R训练收益上继续增精 |
| 共同回答器 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-7B-VL-ReAd-R`；所有方法使用同一checkpoint |
| 划分 | 按视频ID哈希确定；Calibration100=20视频，Confirm200=40视频，视频重叠0 |
| 排除 | Train-500、Confirm-D300及既有Confirm300/300B/300C视频；选择不读取答案或历史分数 |
| 四臂 | `Uniform8`、`MMR8`、`ExtraGlobal12`、`Adaptive12`；后两者同为3,992视觉Token |
| 最终系统 | 只在Calibration100确定ReAd-R专属阈值和margin，冻结后一次性评测Confirm200 |
| Smoke-5 | Uniform/MMR均5/5、答案解析100%、1,296 Token；Adaptive/Extra均5/5、无回退、3,992 Token |
| 推理与协议 | 四臂各300题，所有推理审计通过；Uniform/MMR=`1,296` Token，Adaptive/Extra=`3,992` Token；无解析回退 |
| 统一裁判 | legacy answer-only `deepseek-v4-flash`；1200槽位按同题同答案去重为650次，650成功、0失败、0自动重试；`not_human_gold=true` |
| 原始全300 | Uniform=`28.67/52.33%`；MMR=`30.33/54.17%`；Adaptive12=`30.33/54.83%`；ExtraGlobal12=`30.33/54.17%`（Strict/Relaxed） |
| 选择规则 | Calibration100专用固定网格选择`tau=0.9241418242`、`margin=0`；仅当A0支持度低于tau、A2改答且A2支持度不低于A0时替换；Confirm200未参与选择 |
| Calibration100 | 门控=`32.0/55.0%`，相对MMR=`+0/+0.5 pp`；复核26%、换答4% |
| Confirm200 | MMR=`29.5/54.0%`；门控=`30.0/54.5%`；相对=`+0.5/+0.5 pp`；胜/平/负=`2/198/0`，wrong→right/right→wrong=`1/0` |
| Confirm Bootstrap | 40视频簇、10,000次；Strict差CI=`[0,+1.5] pp`，Relaxed差CI=`[0,+1.25] pp`，区间含零，不能声称稳定显著提升 |
| 推理代价 | Confirm200复核49/200=`24.5%`、实际换答11/200=`5.5%`；按需补看平均回答视觉Token=`1,956.52` |
| 结论 | 在相同ReAd-R checkpoint上获得无负向的微弱正向信号，说明模块与ReAd-R训练可叠加，但Pilot规模小且CI含零；应扩至独立确认集后才作为论文的同基座增益结论 |
| 远端根 | `evaluation/runs/readr_increment_pilot300_v1/` |
| Smoke根 | `evaluation/runs/readr_increment_pilot300_smoke5_v1/` |
| 结果 | `judge_deepseek_legacy_answeronly_v1/results_v1/`；门控分析=`gate_analysis_calibration100_confirm200_v1/` |
| 哈希 | raw summary=`df2543d0439b761df2b955c8708b2893bd93f05d9005d1de8dc1a1abf28c0864`；gate summary=`16a1dfa991c5067c063f0275350d6175bb09e411777677c25787f30175fca839` |

### ReAd-R共同基座独立Confirm-600（2026-07-31，已完成）

| 项目 | 冻结口径与结果 |
|---|---|
| 目的 | 对Pilot-300冻结的证据定位与充分性门控作一次独立确认；Confirm-600不参与阈值、margin、Prompt、裁剪或模型选择 |
| 共同回答器 | `<REMOTE_PROJECT_ROOT>/models/Qwen2.5-7B-VL-ReAd-R`；四臂同一checkpoint、同一提示和同一视频级五折折分 |
| 数据 | 600题、120个新视频；视频ID和问题ID通过无标签SHA256规则选择，每视频5题；与Train-500、Confirm-D300、既有Confirm300系列及Pilot-300视频均不重叠 |
| A0 / A2协议 | `Uniform8`、`MMR8`为8视图、512、1,296视觉Token；Adaptive/Extra仅在触发题使用12视图、3,992 Token；关闭二次采样 |
| 冻结门控 | 仅使用Pilot Calibration100的`tau=0.9241418242454529`与`margin=0`；A0支持度低于tau才补看，且A2改答并满足`support(A2) >= support(A0)`才替换 |
| 触发与代价 | 触发`152/600=25.33%`；Adaptive实际换答21题、ExtraGlobal实际换答19题；Adaptive平均回答视觉Token=`1,978.99` |
| 统一裁判 | legacy answer-only `deepseek-v4-flash`；2400槽位按同题同答案去重为1232次，1232成功、0失败、0自动重试；prompt/completion/total token=`822135/5882/828017`；`not_human_gold=true` |
| Uniform8 | Strict/Relaxed=`29.50/49.83%` |
| MMR8 | Strict/Relaxed=`31.17/52.08%`；相对Uniform=`+1.67/+2.25 pp`，但两项视频级CI均含零 |
| Adaptive12Gated（本文完整策略） | Strict/Relaxed=`32.00/52.75%`；相对MMR=`+0.83/+0.67 pp`；胜/平/负=`6/593/1`，wrong-to-right/right-to-wrong=`5/0` |
| Adaptive vs MMR Bootstrap | 120视频簇、10,000次；Strict差CI=`[+0.17,+1.67] pp`，Relaxed差CI=`[+0.08,+1.33] pp`，均完全为正 |
| ExtraGlobal12Gated | Strict/Relaxed=`31.83/52.75%`；相对MMR=`+0.67/+0.67 pp`；但相对Adaptive为Strict=`-0.17 pp`、Relaxed=`0 pp`，无稳定差异 |
| 结论 | 在同一ReAd-R checkpoint及独立视频集上，`MMR8 + Adaptive12补看 + 充分性门控`相对MMR8取得小而稳定的正向增益；它支持两个模块可叠加，不意味着仅靠裁剪显著优于同Token的额外全局帧 |
| 远端根 | `evaluation/runs/readr_increment_confirm600_v1/`；结果=`judge_deepseek_legacy_answeronly_v1/results_v1/` |
| 哈希 | summary=`e6654ed8f5f6cf51e8b00e6226009d28654d74512c53c721ac0f17fe7954e037`；materialize audit=`decba52ccd82cec1a103d03e6c610a2b41b50e5b35280aa40cfd7d0163e50530`；preflight=`352272bcfcb0c839acd3d200438b444d26d76a5b0d59a2b2385e999b73a0a6e3` |

### ReAd-R残余证据回看Calibration-100（2026-07-31）

| 项目 | 结果 |
|---|---|
| 目的 | 排除MMR8已用帧后重新选择残余证据时刻，检验回看内容是否比原有锚点更有效 |
| 候选 | `ResidualMid12`：残余时刻+固定中尺度；`ResidualAVFunnel12`：残余时刻+证据来源/不确定性感知多尺度 |
| 共同协议 | ReAd-R；MMR8为8视图/1,296 Token；A2为12视图/4096 Token上限；Calibration100=20视频；answer-free |
| 门控 | 沿用冻结`tau=0.9241418242454529`、`margin=0`；触发26/100，两组均替换4题 |
| 裁判 | 5个去重候选，DeepSeek成功5/5，失败0、重试0，`not_human_gold=true` |
| ResidualMid12 | Strict/Relaxed=`34.0/56.5%`；相对MMR8=`+2.0/+2.0 pp`；3胜/97平/0负；wrong→right/right→wrong=`2/0` |
| ResidualAVFunnel12 | Strict/Relaxed=`33.0/56.0%`；相对MMR8=`+1.0/+1.5 pp`；3胜/97平/0负；wrong→right/right→wrong=`1/0` |
| Bootstrap | 20视频簇、10,000次；Mid Relaxed差=`[0,+4.5] pp`；AVFunnel Relaxed差=`[0,+3.0] pp`；下界为零 |
| 结论 | 残余证据时刻优于原先重复锚点的方向得到支持；固定中尺度优于当前Adaptive Funnel，但Calibration100仍不足以形成最终稳定结论 |
| 远端根 | `evaluation/runs/readr_residual_avfunnel_calibration100_v1/`；结果=`residual_judge_v1/summary.json` |

### ReAd-R ResidualMid12 独立 Confirm-600（2026-07-31）

| 项目 | 设置与结果 |
|---|---|
| 目的 | 独立确认Calibration-100中残余证据回看信号；不参与阈值、Prompt或方法选择 |
| 数据 | Confirm-600，600题/120视频；仅对既有MMR8低支持度池中的152题生成A2 |
| A2方法 | 排除MMR8已用帧，选两个时间分散残余时刻；每个时刻为512全帧+896固定中尺度裁剪 |
| 协议 | ReAd-R checkpoint；A2最多12视图、4096 Token上限；Qwen3冻结验证器8视图；关闭二次采样 |
| Gate统计 | 生成答案变化30题；实际支持度门控替换22题；触发池152/600，不重新调阈值 |
| 统一裁判 | DeepSeek answer-only；22/22成功，失败0，自动重试0；新Token=`14792/112/14904`；其余578题复用 |
| MMR8 | Strict/Relaxed=`31.17/52.08%` |
| 原Adaptive12Gated | Strict/Relaxed=`32.00/52.75%` |
| ResidualMid12Gated | Strict/Relaxed=`31.67/52.67%` |
| ResidualMid vs MMR8 | `+0.50/+0.58 pp`；胜/平/负=`6/593/1`；wrong→right/right→wrong=`4/1`；纠正精度80% |
| ResidualMid Bootstrap | 120视频簇、10,000次；Strict=`[-0.17,+1.33] pp`；Relaxed=`[+0.08,+1.17] pp` |
| ResidualMid vs Adaptive | `-0.33/-0.08 pp`；胜/平/负=`3/594/3`；wrong→right/right→wrong=`1/3` |
| 结论 | 残余中尺度回看相对MMR8有微弱正向，但未超过原Adaptive12Gated；作为支持性消融保留，主方法不变 |
| 远端根与哈希 | `evaluation/runs/readr_increment_confirm600_v1/residual_mid_confirm600_v1/`；judge=`9490f38d0b7b975f989dfac59d87bd820e017030eb3a5a7d6dce5816257a614e`；gate=`2e37baa964136abb75dcf95f3311a82c9ce50c6984f5af996086fe169e6b08f8` |

---

## 实验收尾与最终结果冻结（2026-07-31，只读核对完成）

### 当前冻结方法

| 字段 | Qwen3 主方法 | ReAd-R 共同基座 | Qwen2.5 跨基座 |
|---|---|---|---|
| 阈值 | `tau=0.9602926671504974` | `tau=0.9241418242454529, margin=0` | `tau=0.39243705570697784, margin=0.25` |
| 校准来源 | OOF-500（视频隔离） | Pilot Calibration100 | GroupCV-500（视频隔离） |
| Full 标签参与选择 | 否 | 否 | 否 |

### 主实验结果（Full-7844，本次远端 SHA256 核对通过）

| 方法 | Strict | Relaxed | 相对 Uniform | 相对 MMR |
|---|---:|---:|---:|---:|
| Uniform8 | 29.70% | 45.86% | — | — |
| MMR8 | 33.31% | 49.75% | +3.61/+3.89 pp | — |
| **AdaptiveScale** | **40.31%** | **59.87%** | **+10.61/+14.00 pp** | **+7.00/+10.12 pp** |

- 触发率：`7,173/7,844 = 91.45%`；平均回答视觉 Token：`2,926.07`
- 配对统计：Adaptive vs MMR 胜/平/负=`2,117/4,831/896`；wrong→right/right→wrong=`1,153/604`；纠正精度 65.62%
- Bootstrap：Strict CI `[+5.96,+8.09]`、Relaxed CI `[+9.28,+10.98]`，均完全为正
- 哈希核对：Full summary=`106d6756...`、rows=`09acab4c...`（与 SHA256SUMS 一致）

### ReAd-R Confirm-600（本次远端 SHA256 核对通过）

- MMR8=`31.17/52.08%`；Adaptive12Gated=`32.00/52.75%`；ExtraGlobal12Gated=`31.83/52.75%`
- Adaptive 相对 MMR：`+0.83/+0.67 pp`；胜/平/负=`6/593/1`；wrong→right/right→wrong=`5/0`
- Bootstrap：Strict `[+0.17,+1.67]`、Relaxed `[+0.08,+1.33]`，均完全为正
- 触发 `152/600=25.33%`、Adaptive 换答 21 题；平均视觉 Token `1,978.99`
- 哈希：summary=`e6654ed8...`；协议审计=`decba52c...`；preflight=`352272bc...`

### ResidualMid12 Confirm-600（本次远端 SHA256 核对通过）

- `31.67/52.67%`；相对 MMR `+0.50/+0.58 pp`，但低于 Adaptive12Gated `-0.33/-0.08 pp`
- 支持性消融，不替换主方法；judge=`9490f38d...`；gate=`2e37baa9...`

### Qwen2.5 跨基座（本次远端 SHA256 核对通过）

- MMR8=`27.4/45.0%`；冻结门控=`27.8/45.5%`（+0.4/+0.5 pp，CI 下界为 0）
- 弱正向信号，只能作为弱迁移证据；threshold=`193acbc0...`；summary=`71db976d...`

### 方案 B：多中心裁剪消融（2026-07-31）

**目的**：检验"多中心裁剪"（每证据时刻 2 个候选中心）是否有独立增益。**结论：无独立增益，略低于同预算整帧（不显著）**，与 ExtraGlobal 消融一致。

| 版本 | 数据 | 视图 | 预算 | 方法 | Strict/Relaxed | 相对整帧/普通帧 |
|---|---|---|---|---|---|---|
| 512 低成本 | 600 题/192 视频 | 8×512+4×512 | 1,536 | multicenter_512 | 42.62/61.99% | -1.56/-1.35 pp（CI 跨 0） |
| | | | | uniform_extra4 | 44.18/63.32% | -- |
| 896 聚焦 | 600 题/192 视频 | 8×512+4×896 | 同预算 | multicenter_896（小框 0.35） | 43.34/62.06% | -1.76/-1.28 pp（CI 跨 0） |
| | | | | fullframe_896 | 45.10/63.34% | -- |

- A0 基线：32.18/49.57%（512 版）、32.42/49.66%（896 版）
- 两臂相对 A0 均 +10~13 pp（显著）——补看动作是增益主体
- 修正尺度（512→896、大框→聚焦小框）后结论不变，确认是机制层面结论
- **多中心裁剪不进入主方法**，作为支持性消融/负结果
- 路径：`evaluation/runs/scheme_b_multicenter600_v1/`；512 裁判 `judge_deepseek_v2/`、896 裁判 `judge_deepseek_v3/`
- 完整记录见 `docs/方案B_多中心裁剪消融结果_20260731.md`

### 效率指标（全部来自已有日志/审计产物）

| 指标 | 数值 | 来源 |
|---|---|---:|---|
| Full-7844 平均视觉 Token | 2,926.07 | summary.json `deployment` |
| A2 回答延迟（Full 原始分区 4,905 题） | 平均 3.12s / 中位 3.07s / p95 4.39s | `a2_trace.json.latency_seconds` |
| A2 回答延迟（补充分区 2,270 题） | 平均 3.15s / 中位 3.10s | `a2_trace.json` |
| A0 延迟 | 文档记录约 8.52s/题（Confirm-D300） | 历史记录，无逐题字段 |
| 显存峰值（Full A2 回答器） | 约 18.0-18.1 GiB | 推理日志 `gpu_peak_memory_mb` |
| 显存峰值（Full 验证器） | 约 17.2-17.4 GiB | 推理日志 |
| 实际替换率（Full-7844） | ~89.86%（原始 90.55%、补充 88.36%） | 门控后最终答案文本 ≠ A0 |

### 人工一致性抽检（准备就绪）

抽检表 `adsqa_human_review_sample_20260731.csv` 已生成（88 条）：wrong→right 40、right→wrong 25、A0≠A2 未替换 20、Adaptive vs ExtraGlobal 分歧 3。若由 LLM 复核必须标记 `LLM_substitute=true, not_human_gold=true`。

### 完整交付

详见 `AdsQA最终结果交付_20260731.md`（含主表、三张辅助表、路径哈希、写作边界、缺口判断）。

### ReAd-R OCR框裁剪同Token消融（2026-08-03）

| 项目 | 设置与结果 |
|---|---|
| 目的 | 检验可靠OCR框上下文裁剪能否独立优于同一证据时刻的高清整帧 |
| 数据 | ReAd-R Confirm-600冻结触发池152题；answer-free OCR规则筛选后35题/35视频；机制诊断集，不是Fresh确认集 |
| 共同协议 | ReAd-R checkpoint；MMR8基础帧；两个相同OCR证据时刻；相同OCR/ASR与Prompt；12视图；实际3992视觉Token；关闭二次采样 |
| OCRBoxCrop12 | 每个时刻512整帧+OCR框中心896上下文裁剪；Strict/Relaxed=`17.14/31.43%` |
| OCRMomentFull12 | 每个时刻512整帧+同帧896整图；Strict/Relaxed=`17.14/32.86%` |
| 配对结果 | Crop vs Full=`0胜/34平/1负`；Strict差0；Relaxed差`-1.43 pp` |
| Bootstrap | 35视频、10,000次；Strict差=`[0,0]`；Relaxed差=`[-4.29,0.00] pp` |
| 裁判 | 66个臂级分数复用，新增DeepSeek调用4次；`not_human_gold=true` |
| 结论 | OCR框直接裁剪未优于同Token同证据时刻整帧，停止扩展；不得写成独立增精来源 |
| 远端根 | `evaluation/runs/readr_ocrbox_routed_confirm_v2/`；裁判=`judge_deepseek_v1/summary.json` |

### ReAd-R CropOrFull12按锚点空间路由诊断（2026-08-03）

| 项目 | 设置与结果 |
|---|---|
| 目的 | 避免所有证据锚点统一裁剪；按问题局部性与锚点可靠性，在中尺度裁剪和同帧高清整图之间路由 |
| 数据 | ReAd-R Confirm-600冻结触发池152题/81视频；机制诊断，不是Fresh确认集 |
| 路由 | 每个锚点固定保留512整帧；第二张896视图由问题局部性、熵、响应排名、框面积与OCR来源决定crop/full |
| 路由分布 | 64题0裁剪、62题1裁剪、26题2裁剪；88/152至少裁剪一次，占完整600题14.67% |
| 共同协议 | 相同MMR8 A0、两个证据时刻、OCR/ASR、Prompt、ReAd-R；12视图、3992 Token；关闭二次采样 |
| 推理与验证 | A2 152/152；冻结Qwen3验证器152/152；0错误；`tau=0.9241418242454529, margin=0` |
| 门控 | 25题答案变化，22题最终替换；其中12题实际使用裁剪 |
| 裁判 | DeepSeek answer-only；新增10/10成功、0重试，精确复用12；新Token=`7035/48/7083`；`not_human_gold=true` |
| MMR8 | Strict/Relaxed=`31.17/52.08%` |
| Adaptive12Gated | `32.00/52.75%` |
| ExtraGlobal12Gated | `31.83/52.75%` |
| CropOrFull12Gated | `32.00/52.83%`；相对MMR=`+0.83/+0.75 pp`；6胜/594平/0负；wrong-to-right/right-to-wrong=`5/0` |
| Bootstrap vs MMR | 120视频簇、10,000次；Strict=`[+0.17,+1.67] pp`，Relaxed=`[+0.25,+1.42] pp` |
| 与旧12视图策略 | vs Adaptive=`0.00/+0.08 pp`；vs ExtraGlobal=`+0.17/+0.08 pp`；两者CI均跨零，不能宣称显著胜出 |
| 裁剪切换子群 | 12题5胜/7平/0负，Strict/Relaxed=`+41.67/+33.33 pp`；该子群经门控选择，不能外推到全部裁剪题 |
| 结论 | 裁剪适合作为局部条件满足且通过充分性验证后的按需工具，不是普遍优于整帧的替代；需Fresh集合确认后才能升级主方法 |
| 远端根与哈希 | `evaluation/runs/readr_crop_or_full_confirm600_v1/`；summary=`0e75756105b2a56b0462dbe76eb852abd82190c49ad81556cf810b11e662af5b`；gate=`baee5b2be4c4fa33d3c4a0fc34103ae7393c5268751c65e5bfbaa14b4dc3bdbb`；dataset audit=`ae5671d6113f3c2a5a69d952129aad5d3a8a97ef256ae52687db882a29e7134e` |

### 创新点一多模态证据覆盖选择 Smoke-20（2026-08-04）

| 项目 | 设置与结果 |
|---|---|
| 重新定义 | 创新点一改为固定预算下的多模态证据覆盖选择；裁剪不再作为独立增精主张 |
| 开发数据 | 已观察的E-VAds Fresh-500低支持触发池257题/99视频，只作机制开发，不作新独立确认 |
| 三臂 | `SlotCoverage12`、旧固定加权`FusionFull12`、确定性`RandomResidual12` |
| 公平协议 | 相同ReAd-R MMR8 A0、OCR/ASR、Prompt；每臂12视图、3992 Token；两个补看时刻均为512+896高清全帧 |
| CPU审计 | v2 257/257通过；227题锚点不同于旧方法；不复用MMR8原帧；两锚点Raw32秩间隔至少4 |
| Smoke推理 | 三臂均20/20、错误0；视图/Token/关闭二次采样审计通过 |
| 格式回退 | 同一题三臂同步1次漏写前缀，均保守回退A0；不重跑、不改Prompt |
| 候选复用 | 60个臂级候选合并为32个唯一题目—答案；18个已有统一裁判分数，最多新增14次DeepSeek调用 |
| 裁判 | 18个历史评分精确复用，新增14次DeepSeek调用且全部成功；新增Token=`36501/84/36585`；`not_human_gold=true` |
| 三臂R5/R3/R2 | Slot=`43.75/25.00/20.00%`；Fusion=`45.00/27.50/25.00%`；Random=`43.75/25.00/20.00%` |
| Slot vs Fusion | `2胜/16平/2负`；R5差`-1.25 pp`；14视频簇Bootstrap CI=`[-10.71,+7.89] pp` |
| Slot vs Random | `2胜/16平/2负`；R5差`0 pp`；Bootstrap CI=`[-7.50,+7.89] pp` |
| 门禁结论 | 失败；已生成`CANDIDATE_FAILED_AFTER_SMOKE`，未启动Full-257，不在Fresh-500回调规则 |
| 远端根 | `data/external/evads_v1/experiments/readr_slot_coverage_fresh500_dev_v2/`；v1为文本模态过度占槽的失败预检 |

### ReAd-R裁剪Token效率 Held-out-500 独立确认（2026-08-04）

| 字段 | 内容 |
|---|---|
| 数据 | E-VAds Test 独立500题候选池；排除四个既有外部/开发集合的1,000个视频后冻结。空间路由产生99题/68视频，参考答案直到推理、路由和最终协议审计通过后才读取。 |
| 模型与共同协议 | `Qwen2.5-7B-VL-ReAd-R`、MMR8初答、两个冻结证据锚点、OCR/ASR、12视图、同Prompt/生成配置、无二次采样。 |
| 对照 | `Route896`（路由裁剪或896整帧）、`Full896`（同锚点均896整帧）、`Route672`（仅裁剪细节降至672）。 |
| 完整性 | 三臂各99/99，错误0，answer-free协议审计通过。297答案槽去重为131个候选；DeepSeek 131/131成功，零自动重试，`not_human_gold=true`。 |
| R5/R3/R2 | Route896=`43.43/25.25/12.12%`；Full896=`43.18/25.25/12.12%`；Route672=`44.19/26.26/13.13%`。 |
| 成本 | Route896/Full896均`3992.00`视觉Token；Route672平均`3376.57`，相对Full896少`615.43`（`-15.42%`）。 |
| 配对结论 | Route672−Full896：3胜/95平/1负，R5 `+1.01 pp`，68视频簇CI=`[-0.27,+3.00] pp`；Route672−Route896：2胜/96平/1负，R5 `+0.76 pp`，CI=`[-0.52,+2.70] pp`。 |
| 论文结论 | 与Fresh-500效率诊断同方向，但独立99题的R5区间仍跨0。可写“问题条件裁剪以约15%更低视觉Token达到与高清整帧相当的精度、并有正向点估计”；不可写“裁剪准确率显著优于高清整帧”。 |

远端复现根：`data/external/evads_v1/experiments/readr_crop_efficiency_heldout500_v1/`；裁判产物：`judge_deepseek_official_v1/results/{summary.json,scores99.jsonl,JUDGE_COMPLETE.json}`。

### 最新相关方向检索（2026-08-04）

| 方向 | 对本项目的启发 | 采用边界 |
|---|---|---|
| 问题引导连续片段检索 | 将孤立关键帧升级为包含动作连续性的短片段，并联合检索与边界确定 | 作为创新点一唯一值得做的新候选 |
| 因果/时间关系感知定位 | 显式处理先后、变化、动作-结果，而非只按词面相似度选帧 | 作为片段边界评分信号 |
| 阶段自适应视听Token分配 | 视觉和音频预算随阶段变化 | 仅作效率参考，当前基座不直接实现层内剪枝 |
| 置信度校准与增量提交 | 用风险覆盖率决定是否继续补看 | 已并入创新点二，不另起第三创新点 |
| 原生Omni联合建模 | 视觉、音频、视频统一输入 | 作为跨基座上限，不与主表直接混排 |

建议的下一候选名称：`Query-guided Evidence Clip Construction`。最低实验矩阵：`MMR8`、`FixedResidualClip12`、`QueryClip12`、`RandomClip12`；所有方法固定Token、视图数和模型，先做CPU边界审计与20题Smoke。

### Query-guided Evidence Clip Smoke-20（2026-08-04）

| 项目 | 结果 |
|---|---|
| 独立根 | `data/external/evads_v1/experiments/readr_evidence_clip_fresh500_dev_v4/` |
| 三臂 | `FixedClip12`、`QueryClip12`、`RandomClip12` |
| 公平协议 | 12视图、3992视觉Token、起点512+终点896、关闭二次采样 |
| 推理 | 三臂20/20，错误0 |
| 统一评分 | 60个臂级候选，28个跨方法复用，32次唯一DeepSeek调用；最终32/32有效 |
| FixedClip12 | Strict/Relaxed=`5.00/10.00%` |
| QueryClip12 | Strict/Relaxed=`5.00/12.50%` |
| RandomClip12 | Strict/Relaxed=`5.00/12.50%` |
| Query vs Fixed | 1胜/19平/0负；Relaxed=`+2.5 pp`；视频Bootstrap `[0,+8.82] pp`；Strict不变 |
| Query vs Random | 0胜/20平/0负；差异0 |
| 门禁 | 失败；不扩展257题，不进入正式主表 |
| 解释 | 连续片段协议可行，但当前简单问题引导边界没有证明优于固定或随机片段 |

### ReAd-R 三裁剪精确同预算 Smoke-50（2026-08-04）

| 字段 | 内容 |
|---|---|
| 数据与定位 | Held-out裁剪池中按题号哈希冻结50题/50视频；机制诊断，不是新的正式确认集 |
| 三臂 | `Crop3`=`784/700/672`三个裁剪；`Full3`=相同三个时刻、相同尺寸整帧；`Full2`=前两个时刻`896/868`整帧 |
| 公平协议 | 同ReAd-R、MMR8、OCR/ASR、Prompt；三臂均精确`3281`视觉Token；关闭二次采样 |
| 完整性 | 三臂各50/50、错误0、协议审计通过；50题覆盖50个视频 |
| 裁判 | 复用39个同题同答历史评分，新增DeepSeek 33/33成功、0重试；`not_human_gold=true` |
| R5/R3/R2 | Crop3=`37.50/20.00/10.00%`；Full3=`42.50/25.00/16.00%`；Full2=`39.00/22.00/12.00%` |
| Crop3 vs Full3 | 1胜/42平/7负；R5 `-5.00 pp`，视频Bootstrap CI=`[-9.50,-1.00] pp` |
| Crop3 vs Full2 | 2胜/45平/3负；R5 `-1.50 pp`，CI=`[-6.50,+3.50] pp` |
| Full3 vs Full2 | 6胜/43平/1负；R5 `+3.50 pp`，CI=`[+0.50,+7.50] pp` |
| 决策 | 三裁剪失败；第三证据时刻的完整上下文有效。停止裁剪数量扫描，不把多中心裁剪写成增精创新 |
| 远端根 | `data/external/evads_v1/experiments/readr_crop3_budgetmatch_smoke50_v1/` |

### Luna SPEC：复用盘点与 LogicEvidence8 CPU 预检（2026-08-04）

| 项目 | 状态 |
|---|---|
| SPEC | `docs/Luna_问题驱动证据选择与证据缺口工具补证实验SPEC_20260804.md`；执行约束含`ponytail:ponytail` full模式 |
| 远端新工具 | `evaluation/tools/build_luna_reuse_inventory_v1.py`、`evaluation/tools/generate_luna_logic_trees_qwen3_v1.py`、`evaluation/tools/build_luna_logic_evidence8_v1.py`；Qwen3入口复用现有文本接口，仅输出白名单逻辑树 |
| 复用盘点 | `evaluation/runs/luna_logic_evidence_tool_loop_v1/reuse/reuse_inventory.json`；只保存元数据、字段名和哈希，不保存答案值 |
| CPU预检 | `data/innovation1_evidence300_v1/question.json` + VideoITG 64候选缓存；新版300/300，错误0，8帧，1296 Token，关闭二次采样；SEQ/RIGHT_AFTER叶级顺序和递归字段审计通过 |
| 解析状态 | 300题均为明确标注的`rule_fallback`，尚未生成正式Qwen3逻辑树；标记为`LOGIC_TREE_SMOKE_COMPLETE`，不进入正式结果表 |
| 下一门禁 | 用冻结Qwen3纯文本生成逻辑树，完成Evidence-300 answer-free审计；通过后再做Smoke-50 QA |

正式运行环境为`<REMOTE_HOME>/ana3/envs/ReadR/bin/python`（Python 3.10.19、PyTorch 2.8.0+cu128、Transformers 4.57.1）；默认Python3.8环境不兼容`qwen3_vl`。当前Qwen3逻辑树门禁独立根为`evaluation/runs/luna_logic_evidence_tool_loop_v1/logic_trees_qwen3_300_v4_readr/`，已启动并断点保存。

### Luna Qwen3 逻辑树与 Smoke-50（2026-08-04）

| 项目 | 结果 |
|---|---|
| 正式逻辑树 | ReadR + 干净Qwen3，300/300成功，0解析错误；仅保存白名单逻辑树，不保存原始输出 |
| Evidence-300离线选择 | 300/300、每题8个位置、`SEQ/RIGHT_AFTER`顺序审计通过、answer-free |
| Smoke-50数据 | 50题、43视频；`SMOKE50_DATASET_COMPLETE` |
| Smoke-50推理 | `Qwen3_LogicEvidence8` 50/50，错误0；8视图，关闭二次采样 |
| 视觉Token | 实际1024/题，协议上限1296；不是1296固定占用 |
| 协议审计 | `passed=true`，answer-free=true，未读取裁判分数；`inference_protocol_audit.json` |
| 统一评分 | 50/50唯一候选成功；`deepseek-v4-flash` 50次，重试6次；Token=`44,258/15,282/59,540`；`not_human_gold=true` |
| LogicEvidence8结果 | Strict/Relaxed=`26.0/42.0%`；视频Bootstrap 95% CI=`[13.73,39.29]/[30.19,54.26]%` |
| 当前结论 | 当前没有同题同协议A0、无门控反思和证据门控候选；本轮只能作为可行性诊断，不能宣称QA提升 |
| 远端根 | `data/external/evads_v1/experiments/luna_logic_evidence_tool_loop_v1/smoke50_logic_qwen3_v1/` |

### Luna Smoke-50 同协议反思对照（2026-08-04，修正版已完成）

| 项目 | 结果 |
|---|---|
| 三臂 | A0=`Qwen3_LogicEvidence8`直接回答；NoGate=同帧自由复核；EvidenceGated=结构化证据门控复核 |
| 共同协议 | 同一50题/43视频、同一8个LogicEvidence帧、512尺寸、实际1024视觉Token、关闭二次采样；OCR/ASR仅作视频内证据文本 |
| v2失败原因 | NoGate非空输出50/50但标签解析0/50；Gated的claim target被写成字面量`a0\|candidate`；两臂均回退A0，旧同分结论作废 |
| v3推理完整性 | NoGate解析50/50、Gated JSON解析50/50、错误0；门控接受24/50；协议审计通过 |
| A0 | Strict/Relaxed=`26.0/42.0%` |
| v3候选变化 | NoGate改答50/50；EvidenceGated改答24/50；合计74个唯一新裁判请求 |
| NoGate | Strict/Relaxed=`14.0/34.0%`，相对A0=`-12/-8 pp`；胜/平/负=`8/29/13`；wrong→right/right→wrong=`3/9` |
| EvidenceGated | Strict/Relaxed=`26.0/45.0%`，相对A0=`0/+3 pp`；胜/平/负=`5/43/2`；wrong→right/right→wrong=`1/1`；触发率48% |
| 配对Bootstrap | 43视频、10,000次；Gated Strict差CI=`[-5.77,+5.88] pp`，Relaxed差CI=`[-2.08,+9.18] pp`，均跨0 |
| 裁判 | 新增74/74成功，失败0、重试8；`deepseek-v4-flash`；Token=`49,465/26,785/76,250`；`not_human_gold=true` |
| 当前决策 | 无门控反思有害；证据门控有效抑制伤害并呈Relaxed正向趋势，但尚未证明稳定增精。下一步仅做冻结规则Dev-300确认 |
| 远端根 | 旧失败`evaluation/runs/luna_logic_evidence_tool_loop_v1/smoke50_logic_qwen3_v1/reflection_candidates_v2/`；修正版`evaluation/runs/luna_logic_evidence_tool_loop_v1/smoke50_logic_qwen3_v1/reflection_candidates_v3/`；评分`judge_reflection_compare_v2/` |

### Luna Dev-300冻结同协议扩展（2026-08-04，answer-only v2）

| 项目 | 结果 |
|---|---|
| 数据 | 300题/209视频；Fresh-250；严格视频不重叠233题/166视频 |
| 共同协议 | A0/NoGate/EvidenceGated共享LogicEvidence8；8视图、512尺寸、实际1024视觉Token；关闭二次采样；三臂各300/300、错误0 |
| 候选变化 | NoGate改答300/300；EvidenceGated改答131/300，触发率43.67% |
| 正式评分口径 | answer-only v2；725个唯一候选，717个历史精确复用，授权新增8次得到1个有效结果；总覆盖718/725，7个持续空响应不填补 |
| A0 | 完整案例Strict/Relaxed=`31.53/48.81%`；边界=`[31.00,32.67]/[48.00,49.67]%` |
| NoGate | 完整案例=`22.15/41.78%`；已知配对差=`-8.87/-6.66 pp`；保守边界=`[-11.00,-6.33]/[-8.83,-4.17] pp`；稳定有害 |
| EvidenceGated | 完整案例=`31.76/48.65%`；已知配对差=`0/-0.34 pp`；胜/平/负=`21/249/25`；wrong→right/right→wrong=`12/12` |
| Gated Bootstrap | 209视频、10,000次；Strict差CI=`[-3.25,+3.37] pp`，Relaxed差CI=`[-3.10,+2.60] pp`，均跨0 |
| 严格视频不重叠233 | NoGate差值边界=`[-9.01,-3.00]/[-7.51,-1.50] pp`；Gated已知差=`+0.44/-0.88 pp`，边界=`[-1.72,+2.58]/[-3.00,+1.29] pp` |
| 口径修正 | 旧v1把58条A0整段响应混入answer-only评分，正式结论禁用；v2按冻结评测器抽取`[Answer]`内容 |
| 决策 | Smoke-50的Relaxed `+3 pp`未复现。门控可作为风险控制/充分性诊断，但当前反思版本不能宣称稳定增精；后续应测试主动获取新视觉证据 |
| 远端结果 | `evaluation/runs/luna_logic_evidence_tool_loop_v1/dev300_logic_qwen3_v1/judge_reflection_compare_dev300_v1/sensitivity_v1_answeronly/` |
| 完整性 | `summary.json` SHA256=`e35f4f14372ed2fa4de4027307c9dadcaad04dab6da67de081ded331e1dfc2cd`；`not_human_gold=true` |

### ReAd-R 单时刻多尺度裁剪拼图 Fresh-49（2026-08-04）

| 字段 | 内容 |
|---|---|
| 数据 | 上一轮未评测的剩余49题/41视频，题目重叠0 |
| 两臂 | `FunnelMosaic1`=同一时刻focal/mid/broad三个672裁剪拼图；`FullCanvas1`=同一时刻完整帧 |
| 公平协议 | 两臂均1张`2016×672`额外图、9视图、精确3024视觉Token；同MMR8、OCR/ASR和Prompt |
| 完整性 | 两臂各49/49、错误0、answer-free审计通过 |
| 裁判 | 复用35个历史评分；新增DeepSeek 25/25成功、0重试；`not_human_gold=true` |
| R5/R3/R2 | Mosaic=`42.86/24.49/12.24%`；Full=`46.43/28.57/16.33%` |
| 配对 | 1胜/44平/4负；R5 `-3.57 pp`，视频Bootstrap CI=`[-8.16,0] pp`；R2纠正/伤害=`0/2` |
| 决策 | 多尺度裁剪拼图失败；停止裁剪增精路线，672裁剪只作Token效率组件 |
| 远端根 | `data/external/evads_v1/experiments/readr_funnel_mosaic_fresh49_v1/` |

### Qwen2.5 主动证据补看预注册（2026-08-04，执行中）

| 项目 | 内容 |
|---|---|
| 诊断 | Qwen2.5的主要瓶颈是A2证据质量和支持度分离，不是单纯触发率；停止继续扫描阈值 |
| 方法 | ReAd-R + MMR8 A0；规则控制器选择`DIRECT/LOOK_TIME/LOOK_REGION`；每题最多一次工具调用 |
| 论文启发 | LFPC、AdaptVision、VisionLeaf、Active-Look、LENS、OmniReasoner；详见`docs/Qwen2.5主动证据补看_2026论文启发与实验预注册_20260804.md` |
| 首轮矩阵 | A0、相同触发数RandomLook、同Token FullOnly、ActiveLook；Smoke-20 |
| 约束 | answer-free构造；独立run；不覆盖历史；不调用DeepSeek；不做GRPO或阈值扫描 |
| 远端计划根 | `evaluation/runs/qwen25_active_evidence_look_v1/` |
| 扩量门禁 | 工具轨迹合法、证据实际变化、相对随机/整帧出现正向信号、`right->wrong <= wrong->right` |

#### 首轮 Smoke 执行状态

| 项目 | 结果 |
|---|---|
| 逻辑树 | Pilot-300中299/300成功；1条确定性解析失败，重试仍失败并排除，不人工补写 |
| Smoke清单 | 20题/20视频；`LOOK_REGION/LOOK_TIME/DIRECT=7/7/6`；选择前未读裁判；非DIRECT均有证据锚点 |
| 旧候选复用诊断 | 14个触发中仅2题改写；A0/Active/Random/FullOnly均Strict/Relaxed=`20.0/37.5%`，说明重新路由旧候选无效 |
| 新A2推理 | ReAd-R证据约束最小改写14/14，错误0；GPU1/4/5；12视图、3992 Token、关闭二次采样 |
| 新A2格式 | 11条有效；3条非法REVISE安全回退；2条有效改答 |
| 待裁判 | 2条新候选均不匹配历史A0/Adaptive/ExtraGlobal，需要2次DeepSeek统一评分授权 |
| 远端根 | `evaluation/runs/qwen25_active_evidence_look_v1/`；复用诊断`smoke20_reuse_v1/`；新A2`toolaware_minimal_edit_smoke14_v1/` |

评分已完成：2个新候选为`1胜/1平/0负`，零right-to-wrong；DeepSeek 2/2成功、零重试、Token=`1217/12/1229`。完整20题A0 Strict/Relaxed=`20.0/37.5%`，证据约束最小改写后=`20.0/40.0%`，差值=`0/+2.5 pp`，胜/平/负=`1/19/0`。该结果只通过方向门禁，仍是诊断性小样本；下一阶段为冻结100题三臂确认，不直接扩到全量或训练RL。

#### Confirm-100结果

| 项目 | 结果 |
|---|---|
| 数据 | Pilot `confirm200`中100题/28视频；排除Smoke全部视频；动作`DIRECT/TIME/REGION=21/26/53` |
| 推理 | Active/FullOnly/Random各79题，总237次；GPU0/1/4/5；错误0；12视图、3992 Token、无二次采样 |
| 裁判 | 400槽位、107唯一答案、历史复用101、新调用6/6；零重试零失败；Token=`3654/30/3684` |
| A0 | Strict/Relaxed=`29.0/54.0%` |
| ActiveLook | `30.0/55.0%`；相对A0=`+1/+1 pp`；`1/99/0`；w2r/r2w=`1/0`；CI=`[0,+3.125] pp` |
| FullOnly | 与Active相同 |
| RandomLook | 与Active相同 |
| 重合诊断 | Active=FullOnly `96/100`；Active=Random `98/100`；唯一成功纠正题三臂答案相同 |
| 结论 | 最小改写有小幅无伤害收益；主动路由未超过随机/整帧。下一步必须让TIME工具获取新时间帧，不得宣称当前路由有效 |
| 远端根 | `evaluation/runs/qwen25_active_evidence_look_v1/confirm100_v1/` |

#### LOOK_TIME差异门禁与证据先行候选

| 候选 | 20题结果 | 结论 |
|---|---|---|
| 锚点前后固定偏移 + 最小改写 | 20/20、错误0、12视图/3992 Token；答案变化`0/20`；格式回退12 | 不裁判 |
| ASR段首/段尾 + 最小改写 | 20/20、错误0、同协议；答案变化`0/20`；格式回退17 | 不裁判 |
| ASR段首/段尾 + 证据先行独立作答 | 20/20、错误0、同协议；答案变化`12/20` | 通过差异门禁；预检需12次新DeepSeek评分，尚未调用 |

远端根：`evaluation/runs/qwen25_active_evidence_look_v1/temporal_difference_smoke20_v1/`、`temporal_asr_smoke20_v1/`、`temporal_asr_regenerate_smoke20_v1/`。两组失败候选保留且不覆盖；新候选预检位于`temporal_asr_regenerate_smoke20_v1/judge_preflight_v1/`。

评分完成：12/12新调用成功，零重试零失败，Token=`7258/62/7320`。A0 Strict/Relaxed=`5.0/45.0%`，ASRTemporal=`15.0/52.5%`，差值=`+10.0/+7.5 pp`；胜/平/负=`4/14/2`，w2r/r2w=`1/0`；16视频聚类Bootstrap CI为Strict `[0,+23.81] pp`、Relaxed `[-5.88,+21.43] pp`。结果目录：`temporal_asr_regenerate_smoke20_v1/judge_results_v1/`。该结果仅支持扩展到新的冻结确认集，不作为正式稳定增益。

Confirm-60B扩大推理已完成：60题/12视频，与前两批视频重叠0；动作`DIRECT/TIME/REGION=10/13/37`。50个触发题在GPU0/1完成、错误0，39题产生新答案。裁判预检为120槽位、99唯一答案、历史复用60、待新增39次DeepSeek；未调用API。远端根：`evaluation/runs/qwen25_active_evidence_look_v1/confirm60b_v1/`。该集来自旧`calibration100`，仅作内部扩大验证。

评分完成：39/39新调用成功、零重试零失败，Token=`25463/200/25663`。A0 Strict/Relaxed=`35.0/57.5%`，ActiveLook=`38.33/62.5%`，差值=`+3.33/+5.0 pp`；胜/平/负=`12/41/7`，纠正精度=`63.16%`，w2r/r2w=`1/5`；Bootstrap CI为Strict `[-6.67,+13.33] pp`、Relaxed `[-4.17,+15.0] pp`。分层：TIME 13题净增益0（2/9/2），REGION 37题Strict `21.62→27.03%`、Relaxed `48.65→56.76%`（10/22/5）。说明区域补看是主要收益来源，但无门控替换风险过高；下一步为候选相对A0充分性margin门控。

门控更新：历史`p2>=0.893309, margin>=0.25`在Confirm-60B为0替换；校准分区粗网格冻结区域专用`p2>=0.95, margin>=0.03`，校准结果5换/5胜/0负/Relaxed `+5 pp`。该参数无修改应用到Confirm-100，53个新区域候选和充分性评分完成、错误0，最终门控8/100题。预检复用100个A0评分，待新增8次DeepSeek；远端根`evaluation/runs/qwen25_active_evidence_look_v1/region_gate_confirm100_v1/`。

Confirm-100评分完成：8/8新调用成功，零重试零失败，Token=`4479/44/4523`。A0 Strict/Relaxed=`29.0/54.0%`，冻结门控=`28.0/55.0%`，差值=`-1/+1 pp`；胜/平/负=`4/93/3`，纠正精度=`57.14%`，w2r/r2w=`1/2`；Bootstrap CI为Strict `[-4.76,+2.04] pp`、Relaxed `[-1.98,+4.17] pp`。结论：区域候选有收益信号，但绝对支持度margin门控未跨分区复现，标记`candidate_failed`，不得在Confirm-100继续调阈值。

#### 对称Pairwise区域候选选举（Confirm-100，失败）

| 项目 | 结果 |
|---|---|
| 输入 | 53个区域候选中49题A2与A0不同；其余4题无需比较 |
| 选举协议 | 同一12视图/3992 Token证据；分别运行A0-first与A2-first；仅两次都选择A2才替换 |
| 推理完整性 | 两臂各49/49、错误0；98次均12视图、3992 Token、无二次采样 |
| 顺序结果 | A0-first `A/B/TIE=27/17/5`；A2-first `B/A/TIE=33/10/6` |
| 冻结选择 | 7/100替换；13个顺序冲突与11次格式失败全部保留A0 |
| 统一评分 | 历史复用101；新增DeepSeek 6/6成功，零重试零失败；Token=`3785/32/3817` |
| A0 / Pairwise | A0 Strict/Relaxed=`29.0/54.0%`；Pairwise=`27.0/53.0%`；差=`-2/-1 pp` |
| 配对结果 | `0胜/98平/2负`；w2r/r2w=`0/2`；纠正精度0 |
| Bootstrap | 28视频、10,000次；Strict CI=`[-5,0] pp`，Relaxed CI=`[-2.5,0] pp` |
| 决策 | 同模型双顺序选举失败；冻结为`candidate_failed`，禁止在Confirm-100继续调规则 |
| 远端根 | `evaluation/runs/qwen25_active_evidence_look_v1/pairwise_region_confirm100_v1/` |

## CropOnly10相对AnchorGlobal10长期实验闭环（2026-08-06）

| 阶段 | 结果 | 决策 |
|---|---|---|
| AdsQA Confirm-1000同Token，981完整配对 | CropOnly10−AnchorGlobal10：Strict `+0.71 pp`，Relaxed `+0.05 pp`，`57/866/58`；两项视频级CI均跨0 | 仅是点估计，不构成稳定优势 |
| DeepSeek独立重复评分200题 | Strict `-0.50 pp`，Relaxed `-0.75 pp`；两项CI均跨0 | 原小幅优势未复现 |
| 固定尺度有限搜索 | 开发集MidMid10 `+0.40/+0.50 pp`；AdsQA Fresh-63确认变为`-3.17/-4.76 pp`，`1/57/5` | 独立证伪 |
| 文献启发ContextBlend10 | 开发集R5方向最优；E-VAds全新Fresh-500中R5 `-0.15 pp`，CI=`[-0.85,+0.55] pp`；R2 `+0.80 pp`；w2r/r2w=`6/2` | 主门槛失败；不能用R2局部改善包装成成功 |
| 空间定位视图SFT Screen-100 | CropMinimap10 R5 `-0.50 pp`；LocatorInset10 `-0.25 pp`；R2均持平 | 两候选均不进入确认集 |
| Evidence-First统一Prompt SFT Screen-100 | MidCrop10 R5/R2=`-1.25/-2.00 pp`；CropMinimap10=`+0.25/-1.00 pp` | 补看利用率提高，但风险门槛失败 |
| answer-free高视觉+时间多样性路由 | 校准35题R5 `+2.86 pp`、R2不变、`3/32/0`；独立140题/66视频确认R5 `0 pp`、CI=`[-1.71,+1.77] pp`，R2 `-0.71 pp`，w2r/r2w=`0/1` | 校准信号未复现，不进入Fresh |
| LocateAnything-3B学习式grounding SFT Screen-100 | 200锚点中99个返回有效框、101个按预注册回退；LocateFirst10与LocateUnion10均R5 `-0.50 pp`、R2 `-1.00 pp`，w2r/r2w=`0/1` | 学习式框定位仍未产生候选 |
| AwaRes联合何时/何处裁剪 SFT Screen-45 | 固定revision `4c4c1a...`；200锚点中64个数字裁剪，形成45题/19视频触发集；AwaResFirst10−AnchorGlobal10的R5/R3/R2均为`0 pp`，R5 CI=`[-3.00,+3.13] pp`，`3/40/2`，w2r/r2w=`0/0` | 预注册筛选失败，不进入SFT确认或Fresh |
| AdaptVision连续bbox策略 | Screen-58中R5 `+1.72 pp`、R2持平，`4/53/1`，仅通过方向门槛；全新视频隔离SFT确认264题/80视频中R5 `-0.95 pp`，CI=`[-2.38,+0.46] pp`，R2 `-0.38 pp`，CI=`[-1.61,+0.78] pp`，`7/246/11`，w2r/r2w=`1/2` | 独立确认失败，不进入Fresh；禁止按确认集调整bbox面积阈值 |
| DeepEyes多轮Zoom策略 SFT Screen-99 | 固定revision `3b31e4...`与源码commit `11d20c...`；新100题/20视频与既有已评分SFT视频及E-VAds Test视频均无重叠，200锚点中186个有效框，形成99题触发集；DeepEyesFirstZoom10−AnchorGlobal10的R5 `-0.76 pp`，CI=`[-1.55,0] pp`，R2持平，`0/96/3`，w2r/r2w=`0/0` | 方向门槛失败，不进入SFT确认或Fresh；禁止按该Screen调整Prompt、面积阈值或回退规则 |
| ZoomEye上下文并集树搜索 SFT Screen-53 | 固定源码commit `6762d79...`与Qwen2.5-VL-7B revision `cc5948...`；新100题/20视频继续排除前600题/120视频及E-VAds Test，200锚点中80个选中bbox，但63个为整帧并集、仅17个为非整帧；ZoomEyeUnion10−AnchorGlobal10的R5 `-0.94 pp`，CI=`[-2.31,0] pp`，R3 `-1.89 pp`，R2持平，`0/51/2` | 方向门槛失败，不进入SFT确认或Fresh；禁止按该Screen调整cue Prompt、0.95门槛或筛除整帧并集 |
| VLM-R3交错区域细化策略 | 固定源码commit `5e8fb0b...`与ModelScope revision `bc34d28...`。新Screen-95中R5/R2=`+1.32/+2.11 pp`，`3/92/0`，仅通过方向门；全新视频隔离SFT Confirmation-394/80视频中R5 `+0.13 pp`，CI=`[-0.38,+0.64] pp`，R2 `-0.25 pp`，CI=`[-1.03,+0.51] pp`，`8/380/6`，w2r/r2w=`1/2` | 独立确认失败，不进入Fresh；Screen正向未复现，禁止按确认集筛整帧、微小框或no-call |

统一边界：

- 所有比较保持相同MMR8初答、触发集、锚点时间、OCR/ASR、10视图、2,592视觉Token和统一五级裁判；参考答案均在推理及answer-free协议审计后读取。
- E-VAds Fresh-500是外部高功效确认，不覆盖AdsQA Fresh-63失败；SFT Screen属于调优数据，不能当独立证据。
- 上述候选全部未通过冻结成功门槛，因此人工成功案例抽检与论文/PPT“增精结论”均未启动。
- 截至本次冻结，不能写“两个裁剪锚点稳定优于两个同锚点高清全景”；可写“裁剪节省Token，但在多轮独立确认中未证明稳定增精”。

主要远端复现根：

- `evaluation/runs/qwen3_croponly10_anchorglobal10_confirm1000_v1/`
- `evaluation/runs/qwen3_crop_fresh63_v1/`
- `data/external/evads_v1/experiments/qwen3_contextblend_fresh500_v1/`
- `data/external/evads_v1/experiments/qwen3_locator_crop_sftdev500_v1/`
- `data/external/evads_v1/experiments/qwen3_evidencefirst_crop_sftdev500_v1/`
- `data/external/evads_v1/experiments/qwen3_cropminimap_highvisualdiverse_sftconfirm_v1/`
- `data/external/evads_v1/experiments/qwen3_locateanything_crop_sftscreen100_v1/`
- `data/external/evads_v1/experiments/qwen3_awaresfirst_crop_sftscreen45_v1/`
- `data/external/evads_v1/experiments/qwen3_adaptvision_bbox_sftscreen58_v1/`
- `data/external/evads_v1/experiments/qwen3_adaptvision_bbox_sftconfirm_v1/`
- `data/external/evads_v1/experiments/qwen3_deepeyes_firstzoom_sftscreen100_v1/`
- `data/external/evads_v1/experiments/qwen3_zoomeye_union_sftscreen100_v1/`
- `data/external/evads_v1/experiments/qwen3_vlmr3_lastbbox_sftscreen100_v1/`
- `data/external/evads_v1/experiments/qwen3_vlmr3_lastbbox_sftconfirm400_v1/`

AwaRes权重已完成本机6/6和远端21/21 SHA256回验，真实接口烟测与完整策略推理均通过；但同Token筛选点估计为零，不能作为胜出候选。该实验目录405个文件全量回验通过，`SHA256SUMS`哈希为`59b80e93ad10d0e3b431f83616ee952c35f5b767ae03705b0acdd55269a95182`。

AdaptVision固定revision `f3a98cbc...`和源码commit `1b53728f...`已完成双端SHA回验。Screen目录497个文件、Confirmation目录2,980个文件均全量回验通过，`SHA256SUMS`哈希分别为`4dacff5942028728179ff7bc9f515417f3848b44d06d714e3dedf9112af91b19`和`5a5d4b66dc52870029d995137e69dc73f4e558ba0b345c286cb5b6175c73c604`。后续只允许选择实质不同且重新预注册的文献机制，禁止在已评分的AwaRes或AdaptVision确认集上调整Prompt、尺度、区域规则或面积阈值。

DeepEyes固定revision `3b31e4b...`和源码commit `11d20c6...`已完成权重、官方工具语义与双端SHA回验。策略推理200/200、Qwen成对推理198/198均为零错误；统一裁判127个唯一候选中126个初次成功，1个经显式format-only授权恢复，自动重试为0。Screen目录1,306个文件全量回验通过，`SHA256SUMS`哈希为`f769697dce34812c0e695a01cf3a92e91b7dccfeef3406f8e9e62c40bbd6b6ef`。该候选框面积中位数仅7.45%，说明策略确实产生紧框，但精度为0胜3负，因此“框更紧”不能替代效果证据。

ZoomEye固定源码commit `6762d79...`和Qwen2.5-VL-7B revision `cc5948...`，5个权重分片均与Hugging Face LFS SHA256一致。官方V* cue接口在AdsQA 10锚点Smoke中0触发；在不读reference的前提下，仅将cue提取替换一次为冻结JSON格式后通过语义Smoke。正式策略200/200、Qwen成对推理106/106、DeepSeek 61/61均完成，自动重试为0。策略总时延为6,022.9秒，远高于单次Qwen回答成本；Screen目录943个文件全量回验通过，`SHA256SUMS`哈希为`790582bfd3fc6ee107787f9a698d02e86d51635582e5b674d68899bc155ac4ac`。该候选仍为0胜2负，说明上下文并集与回退搜索没有转化为准确率优势。

VLM-R3固定源码commit `5e8fb0b...`和ModelScope revision `bc34d28...`，4个权重分片及20个顶层文件均通过SHA256回验。answer-free单锚点与10锚点Smoke通过后，新Screen冻结100题/20视频；200次policy、190次Qwen、112次DeepSeek均完成且零自动重试。Screen在95个触发题上为`3/92/0`，但全部主指标CI下界仍为0。随后唯一一次独立Confirmation冻结400题/80视频，与此前160个已评分SFT视频及E-VAds Test均零重叠；800次policy、788次Qwen均零错误，472个唯一裁判候选中471个初次成功，1个经显式format-only授权恢复。Confirmation为`8/380/6`，R5仅`+0.13 pp`且CI跨0，R2下降`0.25 pp`，因此停止Fresh。Screen与Confirmation目录的`SHA256SUMS`哈希分别为`dbad5135870e823c835aa552bb024f38d914186c85ccf94fcc9e0adf0352ff8a`和`cefb027cdfe0cfbf10c7e08b0ca0df1aa2b376305377b6e79cb39084bb36ddea`。
