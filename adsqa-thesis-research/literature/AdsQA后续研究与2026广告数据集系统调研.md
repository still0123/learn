# AdsQA 后续研究与 2026 年广告数据集系统调研

- **检索截止日期：** 2026-07-16
- **检索对象：** AdsQA 原论文、公开引用链、MARS2 VR-Ads、2026 年广告数据集及其论文、代码和模型
- **数字口径：** 除非特别说明，提升均指同一论文、同一协议内的绝对百分点（pp），不把相对提升率写成百分点

## 1. 执行摘要

### 1.1 最重要结论

1. 截至检索日，能够确认在 **AdsQA 完整基准**上提出并报告新方法结果的工作主要有两项：
   - AdsQA 原论文的 `ReAd-R`；
   - 2026 年预印本 `AD-MIR`。
2. `MARS2 2025` 的 VR-Ads Track 使用 AdsQA 的竞赛子集，包含 555 个视频和 3000 余道问题。其 Hi-CoT、TFA、T-STAR、QAAF 和 GLM4ads 是重要后续方案，但挑战赛分数不能与 AdsQA 完整集 strict/relaxed 结果直接混排。
3. `GRACE` 在 AdsQA 的 998 道情绪问题子集上做跨数据集泛化，使用归一化情绪标签准确率，也不能与完整 AdsQA 总榜混排。
4. Semantic Scholar 当前列出的 13 篇 AdsQA 引用文献中，除 MARS2、AD-MIR 和 GRACE 外，其余论文主要将 AdsQA 用作相关工作、数据集比较或方法背景，没有在 AdsQA 上报告可比提升。
5. 2026 年广告相关数据集中，**E-VAds 是与 AdsQA 唯一高度同构的数据集**：二者均为广告视频开放式问答，均涉及商业意图、受众、营销逻辑，并同时依赖视觉、ASR 和 OCR。
6. E-VAds 已有作者提出的 `E-VAds-R1`，但截至检索日未发现独立团队在 E-VAds 上发布新的优化方法。官方公开了数据、评测脚本和两套模型权重，但没有公开 SFT/MG-GRPO 训练代码。

### 1.2 当前 AdsQA 结果应如何引用

- **AdsQA 官方完整集：** 以 AdsQA 原论文表 1 和 AD-MIR 表 2 为来源，但 AD-MIR 存在评测口径与算力公平性风险，需在论文中加注。
- **MARS2：** 单列为“AdsQA 竞赛子集上的方法”，只在 MARS2 内部比较。
- **GRACE：** 单列为“AdsQA 情绪子集迁移实验”。
- **本地复现实验：** 不得与上述官方数字混入同一列，必须注明本地筛选样本、Judge、Prompt 和视觉输入协议。

## 2. 检索与纳入标准

### 2.1 来源层级

本次优先使用以下来源：

1. arXiv/IEEE/ICML/ACL 官方论文页面和论文 LaTeX 源文件；
2. 官方 GitHub、Hugging Face 数据集与模型仓库；
3. Semantic Scholar 引用接口，用于建立引用候选集；
4. Web 搜索仅用于发现候选，最终数字必须回到论文表格或官方仓库核验。

### 2.2 “在 AdsQA 上进行了性能提升”的判定

只有满足以下条件之一才计入性能表：

- 在 AdsQA 完整集上报告了 strict/relaxed 等结果；
- 在明确声明的 AdsQA 子集上报告了同协议基线与新方法；
- 在 MARS2 官方 AdsQA 子集排行榜中获得委员会验证结果。

仅在引言、相关工作、数据集对比表或参考文献中出现 AdsQA，不计为 AdsQA 性能研究。

## 3. AdsQA 原论文与官方基线

### 3.1 数据集与评测

AdsQA 包含：

| 项目 | 数值 |
|---|---:|
| 独立广告视频 | 1,544 |
| 场景片段 | 10,962 |
| 总时长 | 22.7 小时 |
| 原始 QA 对 | 7,859 |
| 多标签展开后的评估项 | 10,154 |
| 平均视频时长 | 52.9 秒 |

五类任务为：

- `VU`：Visual Concept Understanding；
- `ER`：Emotion Recognition；
- `TE`：Theme and Core Message Extraction；
- `PS`：Persuasion Strategy Mining；
- `AM`：Potential Audience Modeling。

AdsQA 是开放式问答。官方使用 GPT-4o Judge 输出完全正确、部分正确和错误，并报告：

- Strict Accuracy：仅完全正确计 1；
- Relaxed Accuracy：部分正确按 `0.5` 计分。

### 3.2 官方完整集主要基线

| 模型 | Strict Overall | Relaxed Overall |
|---|---:|---:|
| Human | 51.3 | 71.4 |
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
| VOT（Qwen2-VL-7B） | 17.0 | 40.2 |
| EvolAgent（Qwen2-VL-7B） | 18.3 | 42.6 |
| MCTSr（Qwen2-VL-7B） | 17.1 | 43.4 |
| Qwen2-VL-7B SFT | 14.1 | 38.8 |
| ReAd-R（Qwen2-VL-7B） | 18.6 | 44.9 |
| ReAd-R（Qwen2.5-VL-7B） | 25.0 | 51.5 |

来源：AdsQA 论文表 1。

## 4. AdsQA 上的性能提升工作

### 4.1 完整基准：ReAd-R

#### 性能提升

| 基座 | 基座 Strict/Relaxed | ReAd-R Strict/Relaxed | 绝对提升 |
|---|---:|---:|---:|
| Qwen2-VL-7B | 17.2 / 41.0 | 18.6 / 44.9 | `+1.4 / +3.9 pp` |
| Qwen2.5-VL-7B | 23.0 / 48.9 | 25.0 / 51.5 | `+2.0 / +2.6 pp` |

相对 Qwen2-VL-7B SFT 的 14.1/38.8，ReAd-R（Qwen2-VL-7B）提高 `+4.5/+6.1 pp`，但这是 RL 与特定 SFT 配置之间的比较，不应替代同基座零样本对比。

#### 核心方法

ReAd-R 是面向广告启发式推理的 GRPO 强化学习方法：

1. 输入广告视频和问题；
2. Policy Model 为同一问题采样多个 `<think>...<answer>...` 响应；
3. GPT-4o 按答案完整性和幻觉情况给出 `0/0.5/1` 奖励；
4. 答案奖励与格式奖励加权；
5. 使用组内相对优势和 KL 约束更新策略模型。

其创新点在于：

- 不依赖人工 CoT 监督；
- 使用部分正确奖励缓解开放式广告问答的奖励稀疏；
- 用少量精选广告问答进行领域强化学习；
- 通过输出格式约束稳定推理训练。

#### 关键消融

ReAd-R（Qwen2-VL-7B）为 18.6/44.9；使用未清洗数据降至 13.2/36.2，严格二元奖励降至 15.1/41.7，去除 Prompt 约束降至 16.8/42.9。这说明数据质量、部分正确奖励和输出约束均是必要组件。

#### 代码

- 论文：https://arxiv.org/abs/2509.08621
- DOI：https://doi.org/10.1109/ICCV51701.2025.02172
- 代码与数据：https://github.com/TsinghuaC3I/AdsQA

仓库包含 GRPO 训练配置和评测代码，是目前 AdsQA 相关工作中训练代码公开最完整的一项。

### 4.2 完整基准：AD-MIR

`AD-MIR` 是 2026 年面向 AdsQA 的训练免费结构化代理方法。

#### 同基座提升

| 对比 | Baseline | AD-MIR | 绝对提升 |
|---|---:|---:|---:|
| Qwen2.5-VL-7B Strict | 26.2 | 30.7 | `+4.5 pp` |
| Qwen2.5-VL-7B Relaxed | 49.0 | 52.1 | `+3.1 pp` |
| o1 Strict | 33.1 | 38.1 | `+5.0 pp` |
| o1 Relaxed | 52.4 | 60.0 | `+7.6 pp` |

#### 相对推理方法

| 对比对象 | Baseline | AD-MIR | 绝对提升 |
|---|---:|---:|---:|
| ReAd-R（Qwen2.5-VL-7B）Strict | 25.0 | 30.7 | `+5.7 pp` |
| ReAd-R（Qwen2.5-VL-7B）Relaxed | 51.5 | 52.1 | `+0.6 pp` |
| DVD（o1）Strict | 36.3 | 38.1 | `+1.8 pp` |
| DVD（o1）Relaxed | 50.5 | 60.0 | `+9.5 pp` |

#### 核心方法

AD-MIR 包含两个阶段：

1. **Structure-Aware Memory Construction**
   - 以 1 FPS 解码视频；
   - 构建场景描述、ASR、OCR、主体注册表和向量索引；
   - 联合语义检索与关键词精确匹配，避免品牌、Logo、价格等细节被稠密语义检索淹没。
2. **Structured Reasoning Agent**
   - ReAct 控制器执行 `Think-Act-Observe`；
   - 调用 Global Browse、Communication Expert、Clip Search、Frame Inspect；
   - 针对营销问题调用传播学/广告专家；
   - 将抽象说服策略重新回查到具体帧；
   - 证据不足时回退并重新检索；
   - 最后用精炼模型将答案限制在 30 词内。

其主要技术贡献是把广告意图推理显式拆为“全局叙事建模—营销假设—局部证据验证—答案精炼”，而不是仅依赖端到端生成或 RL 隐式拟合。

#### 代码与复现边界

- 论文：https://arxiv.org/abs/2602.07625
- 代码：https://github.com/Little-Fridge/AD-MIR

代码公开了核心代理、数据库构建、ASR/OCR 和自定义视频入口，但 README 明确说明没有公开：

- AdsQA 下载器；
- 官方评测脚本；
- 原始评测输出；
- 论文使用的模型权重和私有 API 配置。

因此它属于“核心推理代码公开、论文数字不能一键复现”。

#### 可比性风险

1. AD-MIR 当前是 arXiv v1，尚未核验正式会议录用。
2. 论文把 relaxed accuracy 描述为 `s >= 0.5` 的样本比例，而 AdsQA 原论文将部分正确按 `0.5` 加权；两者文字定义存在冲突。
3. AD-MIR 是多模型代理：除基座外还使用 Caption VLM、Controller、Communication Expert、Frame Inspector 和 GPT-4o-mini 精炼，推理成本高于单次基座和 ReAd-R。
4. AD-MIR 表中的 Qwen2.5-VL-7B 基线为 26.2/49.0，与 AdsQA 原论文的 23.0/48.9 不完全一致，说明其重评协议或输入配置发生变化。
5. 论文报告了五类任务及总体结果，但没有明确给出实际完成评测的 AdsQA 样本数，不能仅凭表格断言与官方 7,859 条记录完全一一对应。

因此，AD-MIR 可以写为“当前报告的 AdsQA 五类总体最高结果”，但不能无条件称为严格公平的新 SOTA。

### 4.3 MARS2 VR-Ads：AdsQA 竞赛子集

MARS2 从 AdsQA 抽取 555 个视频和 3000 余道问题作为 VR-Ads 测试集。官方最佳基线是 Qwen2.5-VL-7B，分数 48.04。

| 排名 | 方法 | 分数 | 相对 48.04 的榜单差 | 核心技术 |
|---:|---|---:|---:|---|
| 1 | Hi-CoT | 56.35 | `+8.31 pp` | ASR、分镜、全局理解、问题相关镜头、分层 CoT |
| 2 | TFA | 54.62 | `+6.58 pp` | Qwen2.5-VL-72B、1 FPS、简洁推理 Prompt |
| 3 | T-STAR | 53.13 | `+5.09 pp` | FPS/分辨率调优、30词拒绝采样 |
| 4 | QAAF | 52.77 | `+4.73 pp` | 2 FPS、ASR翻译、结构化 Voiceover Prompt |
| 5 | GLM4ads | 52.74 | `+4.70 pp` | GLM-4.1V-9B、Video-Holmes SFT、think-then-answer |

#### 方法要点

**Hi-CoT**

```text
Whisper ASR + PySceneDetect
→ 广告主题/情绪/说服意图/叙事的全局分析
→ 带时间戳的镜头描述
→ 问题驱动镜头对齐
→ 全局与局部证据上的因果/常识推理
→ 最终答案
```

**TFA**

- 不训练；
- 对 Qwen2.5-VL-72B 使用 1 FPS；
- Prompt 强制基于视觉与推理回答，并限制 30 词；
- 论文内部观察到 72B、32B、7B 得分约为 0.55、0.51、0.46，说明榜单提升中包含显著模型规模因素。

**T-STAR**

- 系统扫描 2/3/5 FPS 和分辨率；
- 最优配置为 2 FPS、高空间分辨率；
- 超过 30 词即拒绝并重新生成。

**QAAF**

- 提取语音并翻译为英文；
- 使用 `Voiceover:` 显式分隔旁白；
- 视觉帧与旁白共同输入 Qwen2.5-VL-72B。

**GLM4ads**

- 在 Video-Holmes 的 270 个悬疑短片、1837 个问题上构造“思考后回答”样本；
- 对 GLM-4.1V-Thinking-9B 做 SFT；
- 通过跨域多跳视频推理训练迁移到广告问答。

#### 代码状态

- 论文：https://arxiv.org/abs/2509.14142
- MARS2 组织：https://github.com/mars2workshop

MARS2 论文声称公开 15+ 参赛方法，但截至检索日，官方组织当前可见仓库主要是 Track 1/2 基线与比赛页面，未找到上述五个 Track 3 方法的独立完整仓库。网络检索也未定位到 Hi-CoT、TFA、T-STAR、QAAF 或 GLM4ads 的官方实现。因此这些方法目前以论文描述为主要复现依据。

#### 可比性说明

榜单差值不是纯算法消融：

- 官方对照是 7B，而前四名使用 72B；
- 各方法的 FPS、分辨率、ASR 和生成约束不同；
- 使用的是 AdsQA 子集而非完整 7859 QA。

### 4.4 AdsQA 情绪子集：GRACE

GRACE 的主任务是广告观众情绪预测。其主训练集是 Pitts，AdsQA 仅用于零样本跨数据集泛化。

#### AdsQA 子集结果

GRACE 从 AdsQA 取 998 条情绪问题，将开放式答案归一化到 Pitts 情绪标签空间：

| 基座 | Baseline Acc_raw | +GRACE | 提升 |
|---|---:|---:|---:|
| Qwen2.5-VL | 44.7 | 50.0 | `+5.3 pp` |
| Qwen3-VL | 47.2 | 50.7 | `+3.5 pp` |

#### 核心方法

- 从动作中心描述中提取按时间排列的 SVO 三元组；
- 提取可见文本线索；
- 对主语和宾语生成局部实体裁剪；
- 将“发生了什么”的事件结构和“谁参与”的视觉裁剪共同输入 MLLM；
- 通过结构化动作证据推断观众情绪。

#### 状态

- 论文：https://arxiv.org/abs/2606.16198
- 截至检索日，论文和公开搜索未给出官方代码仓库。

该结果只能说明情绪子任务迁移，不代表 AdsQA 五类任务整体提升。

## 5. AdsQA 引用链审计

Semantic Scholar 在检索日返回 13 篇引用 AdsQA 的论文。逐篇检查后的分类如下：

| 工作 | 年份 | 是否在 AdsQA 上实验 | 处理方式 |
|---|---:|---|---|
| MARS2 2025 Challenge | 2025 | 是，竞赛子集 | 纳入子集榜单 |
| AD-MIR | 2026 | 是，完整五类任务 | 纳入完整集方法 |
| GRACE | 2026 | 是，998条情绪子集 | 纳入任务子集 |
| E-VAds | 2026 | 否 | 数据集背景与密度比较 |
| EG-VQA | 2026 | 否 | 仅数据集比较 |
| VidMsg | 2026 | 否 | 仅高层语义相关工作 |
| MetaphorVU | 2026 | 否 | 在自有数据集测试 ReAd-R |
| VTAgent | 2026 | 否 | RL/证据定位背景 |
| Nüwa | 2026 | 否 | Token pruning 背景引用 |
| TimeBlind | 2026 | 否 | 时空组合基准背景 |
| Video-LMM Post-Training Survey | 2025 | 否 | 综述条目 |
| BrandFusion | 2026 | 否 | 广告视频生成背景 |
| Evaluating Design Video Generation | 2026 | 否 | 生成评测背景 |

这说明目前 AdsQA 的公开方法生态仍较小，不能把“引用 AdsQA”直接等同于“在 AdsQA 上形成性能竞争”。

## 6. 2026 年广告相关数据集与 AdsQA 的相关性

### 6.1 判断维度

相关性按以下五项判断：

1. 是否是广告视频而非广告图片；
2. 是否评价理解/问答而非生成/编辑；
3. 是否包含视觉、ASR、OCR 等多模态信息；
4. 是否涉及营销逻辑、受众、说服或隐含意图；
5. 是否公开数据和可执行评测。

### 6.2 候选数据集

| 数据集/基准 | 年份 | 任务 | 与 AdsQA 相关性 | 判断 |
|---|---:|---|---|---|
| **E-VAds** | 2026 | 电商广告视频开放式 QA | **高** | 五项均高度匹配，是首选外部数据集 |
| DistractionBench / NaturalAds | 2026 | 插播广告下的主体-事件混淆与幻觉 | 中 | 可验证时间绑定和抗干扰，但不理解广告意图 |
| VidMsg | 2026 | 短视频隐含信息推断与检索 | 中 | 高层语义相近，但不是广告数据集 |
| A³-Dataset / A³-Bench | 2026 | 广告图片美学评价 | 低至中 | 有说服力/欲望评价，但无视频时序和 ASR |
| EAVSD | 2026 | 电商广告分镜生成 | 低 | 面向多图生成和叙事一致性，不是问答 |
| NextAds Benchmarks | 2026 | 个性化广告生成与集成 | 低 | 生成/推荐任务，目标与 AdsQA 不同 |
| AutoCut 数据 | 2026 | 广告视频自动剪辑 | 低 | 选择、排序、脚本和 BGM 生成，不是理解评测 |
| MCSC-Bench | 2026 | 多模态材料到制作脚本 | 低 | 面向内容生产，输出是可执行脚本 |
| GenAd-Bench | 2026 | 个性化广告视频生成 | 低 | 评价资产保持、对齐与视觉质量 |

### 6.3 筛选结论

最合理的数据集组合是：

```text
AdsQA：主数据集，验证品牌广告中的主题、情绪、说服策略和受众
E-VAds：外部验证，测试高密度 OCR/ASR、电商营销逻辑和监管问题
VideoAds（2025，可选）：时间推理与高 FPS 诊断
DistractionBench（可选）：主体—事件时间绑定和抗干扰鲁棒性
```

不建议为了增加数据集数量，把广告生成、编辑或图片美学数据集混入问答主结果。

## 7. E-VAds 深入调研

### 7.1 数据规模与任务

| Split | 视频 | QA |
|---|---:|---:|
| SFT Train | 376 | 1,880 |
| RL Train | 196 | 980 |
| Test | 3,389 | 16,925 |
| 合计 | 3,961 | 19,785 |

平均视频时长为 28.4 秒。五类任务为：

- `BP` Basic Perception；
- `CM` Cross-Modal Detection；
- `ML` Marketing Logic；
- `CI` Consumer Insight；
- `RC` Regulatory Compliance。

与 AdsQA 的对应关系：

| AdsQA | E-VAds 对应任务 |
|---|---|
| VU | BP、CM |
| ER、AM | CI |
| TE、PS | ML |
| 无直接对应 | RC |

E-VAds 更偏即时转化，AdsQA 更偏品牌叙事与抽象说服，因此适合外部验证，不适合直接合并训练后宣称同分布提升。

### 7.2 多模态密度

官方报告：

| 数据集 | Vden | Aden | Oden |
|---|---:|---:|---:|
| AdsQA | 50.13 | 0.85 | 5.05 |
| E-VAds | 60.44 | 5.08 | 18.66 |

E-VAds 在视觉变化、语音密度和屏幕文字密度上均更高，尤其适合检验：

- 固定视觉 Token 预算；
- OCR/价格/CTA 证据定位；
- ASR 与视觉的跨模态对齐；
- 证据缺失和选择性补证。

### 7.3 E-VAds-R1

#### 方法

E-VAds-R1 使用两阶段训练：

1. SFT：对齐输出格式并注入基本电商知识；
2. MG-GRPO：通过多粒度奖励训练商业推理。

Judge 给出 `x ∈ {0, 0.25, 0.5, 0.75, 1}`，定义：

```text
G(x) = [S(x) + R3(x) + R5(x)] / 3
R = 0.8 × G(answer) + 0.2 × G(reasoning) + format penalty
```

其作用是：

- 用 R5 为部分正确回答提供稠密奖励；
- 用 Strict 对满分回答提供非线性跃升；
- 同时约束推理证据与最终答案；
- 在开放式商业问题上减轻零奖励和近似正确停滞。

#### 同基座结果

| 基座 | Baseline S/R3/R5 | E-VAds-R1 S/R3/R5 | 绝对提升 |
|---|---:|---:|---:|
| Qwen2.5-VL-7B | 11.1 / 36.9 / 48.9 | 19.3 / 50.1 / 68.0 | `+8.2 / +13.2 / +19.1 pp` |
| Qwen3-VL-8B | 15.3 / 48.4 / 62.3 | 32.0 / 57.7 / 73.6 | `+16.7 / +9.3 / +11.3 pp` |

论文所称 `109.2%` 是 Qwen3-VL-8B Strict Overall 从 0.153 到 0.320 的**相对提升率**：

```text
(0.320 - 0.153) / 0.153 = 109.2%
```

不能写成“提高109.2个百分点”。

#### 与其他模型的关系

- E-VAds-R1（Qwen3-VL-8B）的 Strict Overall 为 0.320，低于 Gemini3-Flash 的 0.350；
- R5 Overall 为 0.736，低于 Gemini3-Flash 的 0.761；
- 因此其最强结论是“大幅提高同基座和同规模开源模型”，而不是所有模型中的绝对最高分。

### 7.4 是否已有独立后续优化

截至 2026-07-16：

- Semantic Scholar 仅返回一篇引用 E-VAds 的生成评测论文；
- 未发现独立团队在 E-VAds 上报告新的模型优化成绩；
- 当前可核验的性能提升主要来自 E-VAds 原论文自身的 E-VAds-R1。

### 7.5 公开代码与模型

- 数据与评测：https://github.com/TaobaoTmall-AlgorithmProducts/E-VAds_Benchmark
- 数据集：https://huggingface.co/datasets/TaobaoTmall-AlgorithmProducts/E-VAds_Benchmark
- Qwen2.5 权重：https://huggingface.co/TaobaoTmall-AlgorithmProducts/E-VAds-R1-Qwen2.5VL
- Qwen3 权重：https://huggingface.co/TaobaoTmall-AlgorithmProducts/E-VAds-R1-Qwen3VL

当前仓库包含：

- SFT、RL、Test 三个 Parquet 标注文件；
- Qwen3-VL 推理和 Judge 脚本；
- 两套完整 safetensors 模型权重。

当前仓库不包含：

- SFT 训练代码；
- MG-GRPO/ROLL 训练代码；
- 论文完整训练配置入口。

此外，README 示例包含 `--use_llm_judge`，但当前 `eval_qwen3vl_8b.py` 的参数解析器没有注册该参数；实际脚本直接创建 Judge 客户端。复现前需要修正文档或脚本。

## 8. 代码成熟度总表

| 工作 | 数据 | 推理/评测 | 训练 | 权重 | 结论 |
|---|---|---|---|---|---|
| AdsQA / ReAd-R | 有 | 有 | 有 | 外部基座/训练产物视仓库说明 | 最完整 |
| AD-MIR | 复用 AdsQA | 自定义视频入口有，论文评测无 | 无需训练 | 无 | 核心代理可运行，论文表难一键复现 |
| MARS2 Track 3 | 竞赛数据 | 论文描述 | 大多无 | 无 | 五个方案未找到独立完整仓库 |
| GRACE | 复用 Pitts/AdsQA | 未发现 | 未发现 | 未发现 | 目前主要依赖论文 |
| E-VAds / E-VAds-R1 | 有 | 有 | 无 | 有，两套 | 可直接推理，不能复现 MG-GRPO 训练 |

## 9. 对当前论文的直接建议

### 9.1 数据集选择

推荐：

```text
主实验：AdsQA 完整集
证据实验：Evidence-300
外部冻结验证：E-VAds
可选鲁棒性：VideoAds 或 DistractionBench
```

不建议更换 AdsQA，也不建议把 E-VAds 与 AdsQA 混合后只报告一个平均分。

### 9.2 必须新增的对比

当前创新点与以下方法高度相关：

- Hi-CoT：全局理解 + 镜头证据 + 分层回答；
- AD-MIR：结构化记忆 + 局部证据验证 + 回退；
- GRACE：结构化事件 + 局部视觉裁剪；
- E-VAds-R1：多粒度奖励与证据约束。

论文中至少需要解释：

1. 相对 Hi-CoT，本文为何不是普通“全局+局部”分层 Prompt；
2. 相对 AD-MIR，本文如何用固定视觉 Token 和单次补证控制代理成本；
3. 相对 GRACE，本文为何不局限于情绪任务和 SVO 证据；
4. 相对 E-VAds-R1，本文为何选择冻结大模型的证据分配/验证，而不是重型 RL。

### 9.3 外部验证设计

建议冻结 AdsQA 上的选择器、阈值和 Prompt，在 E-VAds 上比较：

- Uniform；
- 问题相关帧选择；
- 完整固定预算方法；
- 去 ASR；
- 去 OCR；
- 去声明验证或补证。

报告 BP/CM/ML/CI/RC 分项，不只报告总体平均。重点观察 CM、ML、CI 是否重复出现 AdsQA 中“定位改善但 QA 不涨”的现象。

## 10. 局限与持续更新

1. 文献和仓库状态截止于 2026-07-16，预印本与仓库会持续更新。
2. Semantic Scholar 的引用索引可能漏收刚发布论文，因此本报告同时使用精确标题搜索和 arXiv 全文检索。
3. AD-MIR 和 GRACE 均为预印本状态，结果尚未经过正式同行评审核验。
4. MARS2 Track 3 方法的公开代码状态与论文“15+ participant methods”声明不完全一致，本报告按当前可见仓库记录。
5. E-VAds v4 已标注 ICML 2026 接收；本文使用 v4 论文表和官方模型仓库核验结果。

## 11. 主要来源

1. AdsQA: https://arxiv.org/abs/2509.08621
2. AdsQA code: https://github.com/TsinghuaC3I/AdsQA
3. MARS2 2025: https://arxiv.org/abs/2509.14142
4. MARS2 GitHub: https://github.com/mars2workshop
5. AD-MIR: https://arxiv.org/abs/2602.07625
6. AD-MIR code: https://github.com/Little-Fridge/AD-MIR
7. GRACE: https://arxiv.org/abs/2606.16198
8. E-VAds: https://arxiv.org/abs/2602.08355
9. E-VAds ICML page: https://icml.cc/virtual/2026/poster/64911
10. E-VAds code/data: https://github.com/TaobaoTmall-AlgorithmProducts/E-VAds_Benchmark
11. VideoAds: https://arxiv.org/abs/2504.09282
12. DistractionBench: https://arxiv.org/abs/2605.27101
13. VidMsg: https://arxiv.org/abs/2606.03635
14. A³: https://arxiv.org/abs/2603.24037
15. Narrative Weaver/EAVSD: https://arxiv.org/abs/2603.06688
16. NextAds: https://arxiv.org/abs/2603.02137
17. AutoCut: https://arxiv.org/abs/2603.28366
18. MCSC-Bench: https://arxiv.org/abs/2604.15127
19. Co-Director/GenAd-Bench: https://arxiv.org/abs/2604.24842
