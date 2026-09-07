# I3 总门禁：候选综合裁决

生成时间：`2026-08-18T01:51:40+08:00`

## 1. 最终结论

```text
PASS_TO_I4 = []
HOLD_EXPERIMENT = [I2B-P02, I2B-P03]
RETAIN_DEPENDENT_ONLY = [I2B-P01, I2B-P05, I2B-P08]
HARD_REJECT = [I2B-P04, I2B-P06, I2B-P07]
```

零候选通过是有效门禁结果。没有候选同时满足：

- 总分至少 `80/100`；
- 技术问题 `>=6/10`；
- 数据流 `>=9/15`；
- 非平凡耦合 `>=14/20`；
- 本地支持 `>=10/15`；
- 技术效果 `>=9/15`；
- 实现可行性 `>=6/10`；
- 权项表达 `>=9/15`；
- 无硬失败。

本轮最高分为 **I2B-P08 的 75 分**。该候选仍低于 80 分，且其独立训练方法与**自家权利要求 8**关于决定性证据最小破坏、背景保留和排序训练的边界实质重叠，命中硬失败，不得进入 I4。

I2B-P02 和 I2B-P03 明确为**实验先行**：两者均无当前硬失败，但总分和分项门槛不达标，只能在完成预注册、等预算删除实验后重新提交 I3，不能先做专利检索。

## 2. 合并规则

两路独立评审按以下规则合并：

1. `03a_evidence_gate` 是分数与硬失败的唯一来源，所有分数原样继承，不取平均、不加分。
2. `03b_paper_attack` 只补充论文拥挤度、最强单篇和两篇组合攻击，不抵消硬失败。
3. 任一硬失败直接阻断 I4；总分达到 80 也不能覆盖硬失败。
4. 总分、任一分项最低分、硬失败三类条件必须同时通过。
5. “论文集合尚未覆盖”不等于具备专利新颖性或创造性。

## 3. 候选汇总

分数顺序：技术问题/数据流/非平凡耦合/本地支持/技术效果/实现/权项表达。

| 候选 | scores | total | hard_failures | paper_crowding | final_decision |
|---|---|---:|---|---|---|
| I2B-P01 | 9/13/13/12/4/3/5 | 59 | 自家在先实质重叠 | HIGH | 独权硬淘汰，仅留窄从属实验 |
| I2B-P02 | 9/13/15/10/3/2/9 | 61 | 无 | HIGH | 实验先行，不进 I4 |
| I2B-P03 | 8/12/11/11/3/3/5 | 53 | 无 | CRITICAL | 实验先行，不进 I4 |
| I2B-P04 | 9/12/10/6/2/1/8 | 48 | 无核心本地支持；模块并列 | HIGH | 硬淘汰 |
| I2B-P05 | 9/13/14/13/4/4/6 | 63 | 自家在先实质重叠 | HIGH | 独权硬淘汰，仅留窄从属实验 |
| I2B-P06 | 7/12/10/6/2/1/5 | 43 | 无核心本地支持；业务规则核心 | CRITICAL | 硬淘汰 |
| I2B-P07 | 8/12/13/5/2/1/7 | 48 | 无核心本地支持；业务规则核心 | HIGH | 硬淘汰 |
| I2B-P08 | 10/15/17/15/7/5/6 | **75** | **与自家权利要求 8 实质重叠** | CRITICAL | **独权硬淘汰，优先从属实现** |

## 4. 逐候选记录

### I2B-P01

- `scores`: `9/13/13/12/4/3/5`
- `total`: `59`
- `hard_failures`: `HF_SELF_PRIOR_SUBSTANTIAL_OVERLAP`
- `paper_crowding`: `HIGH`；CREST + Reading or Guessing
- `strongest_attack`: 自家已披露跨帧文字事件、问题逻辑树、高分辨率补看和预算控制；论文组合又覆盖短峰采样与 OCR 视觉落地，新增内容主要是字段和取帧时刻细化。
- `final_decision`: `REJECT_HARD_AS_INDEPENDENT_RETAIN_DEPENDENT_EXPERIMENT_ONLY`
- `reason`: 命中自家在先硬失败；耦合、技术效果、实现、权项表达及总分均不达标。
- `next_action`: 仅保留权利要求 2/4/6 的窄从属实验；修复 V3 引用 ID；完成槽位、生命周期、首末帧和预算回收独立消融。

### I2B-P02

- `scores`: `9/13/15/10/3/2/9`
- `total`: `61`
- `hard_failures`: `[]`
- `paper_crowding`: `HIGH`；Unified Object-Centric AV Graph + Scene-RAG
- `strongest_attack`: 多峰互相关、正负时延和问题选边可能是成熟构件组合；现有本地 AV 结果未真实激活联合模态。
- `final_decision`: `HOLD_EXPERIMENT_BEFORE_I4`
- `reason`: 无硬失败，但技术效果、实现和总分不达标。
- `next_action`: **实验先行**；建立双审 lag 数据，完成无互斥、无符号、无槽位独立消融，并在等事件、ASR、视图和 Token 下正面对照零时延、固定滑窗和 Scene-RAG 式对齐。

### I2B-P03

- `scores`: `8/12/11/11/3/3/5`
- `total`: `53`
- `hard_failures`: `[]`
- `paper_crowding`: `CRITICAL`；EcoFrame + CREST
- `strongest_attack`: 曝光欠账尚可还原为加权采样分数加已有预算约束；EcoFrame 与 CREST 已覆盖闭环预算、短事件增配和低价值帧回收。
- `final_decision`: `HOLD_EXPERIMENT_BEFORE_I4`
- `reason`: 无硬失败，但耦合、技术效果、实现、权项表达及总分不达标。
- `next_action`: **实验先行**；冻结状态转移与预算守恒公式，做 Uniform/MMR/EcoFrame/CREST/Exposure 五臂等 Token 对照；任一核心关系无独立效应即停止独权方向。

### I2B-P04

- `scores`: `9/12/10/6/2/1/8`
- `total`: `48`
- `hard_failures`: `HF_NO_LOCAL_SUPPORT_FOR_CORE_FAILURE`、`HF_PARALLEL_MODULES_AS_WRITTEN`
- `paper_crowding`: `HIGH`；Hierarchical AV Entity Cohesion + E-VQA
- `strongest_attack`: 没有本地属性串绑事实，当前处理链只是 re-ID、属性抽取、槽表和问题解析串联，反向反馈没有进入权项。
- `final_decision`: `REJECT_HARD`
- `reason`: 两项硬失败且耦合、本地支持、技术效果、实现、权项表达及总分不达标。
- `next_action`: 停止进入 I4；只有先建立串绑失败集、实现冲突反向身份状态转移并通过实体 ID 置乱消融，才可重新立项。

### I2B-P05

- `scores`: `9/13/14/13/4/4/6`
- `total`: `63`
- `hard_failures`: `HF_SELF_PRIOR_SUBSTANTIAL_OVERLAP`
- `paper_crowding`: `HIGH`；Scene-RAG + SIEVES
- `strongest_attack`: 自家申请已披露声明三态、多源冲突和时间关系；五态张量与禁抵消可能只是状态表扩维和聚合规则，OCR 分支当前不可辨识。
- `final_decision`: `REJECT_HARD_AS_INDEPENDENT_RETAIN_DEPENDENT_EXPERIMENT_ONLY`
- `reason`: 命中自家在先硬失败；技术效果、实现、权项表达及总分不达标。
- `next_action`: 仅留窄从属实验；先通过各模态单调性门禁，再做无时间维、无禁抵消和完整张量的正交删除测试。

### I2B-P06

- `scores`: `7/12/10/6/2/1/5`
- `total`: `43`
- `hard_failures`: `HF_NO_LOCAL_SUPPORT_FOR_CORE_MECHANISM`、`HF_SCENARIO_OR_BUSINESS_RULE_CORE`
- `paper_crowding`: `CRITICAL`；MemDreamer + CaST-Bench
- `strongest_attack`: 候选是营销阶段规则叠加通用事件图；论文池已密集覆盖层级事件图、时间因果边和多跳证据链。
- `final_decision`: `REJECT_HARD`
- `reason`: 两项硬失败且多数分项不达标。
- `next_action`: 停止进入 I4；若重开，边必须完全由可计算视听状态变化定义，并先通过保持节点和预算不变的受限边置换实验。

### I2B-P07

- `scores`: `8/12/13/5/2/1/7`
- `total`: `48`
- `hard_failures`: `HF_NO_LOCAL_SUPPORT_FOR_CORE_FAILURE`、`HF_SCENARIO_OR_BUSINESS_RULE_CORE`
- `paper_crowding`: `HIGH`；Hierarchical AV Entity Cohesion + Reading or Guessing
- `strongest_attack`: 删除报价业务语义后只剩 OCR/ASR、实体键、条件键和版本数据库；本地没有版本错误证据，且现有构件存在 answer 泄漏边界。
- `final_decision`: `REJECT_HARD`
- `reason`: 两项硬失败且耦合、本地支持、技术效果、实现、权项表达及总分不达标。
- `next_action`: 停止进入 I4；先盘点专项题量并修复或隔离 answer 泄漏；不能给出非促销业务规则的版本判定算法时永久放弃。

### I2B-P08

- `scores`: `10/15/17/15/7/5/6`
- `total`: **`75`**
- `hard_failures`: **`HF_SELF_PRIOR_SUBSTANTIAL_OVERLAP`，与自家权利要求 8 实质重叠**
- `paper_crowding`: `CRITICAL`；CaST-Bench + VideoSEAL
- `strongest_attack`: 自家权利要求 8 已要求决定性证据最小破坏、背景保留和排序训练；副本图、集合覆盖、隔离复验和训练拒用属于该要求的质量控制细化。论文组合又覆盖全证据干预和独立充分性复验。
- `final_decision`: `REJECT_HARD_AS_INDEPENDENT_PRIORITIZE_DEPENDENT_IMPLEMENTATION`
- `reason`: 75 分仍低于 80，命中自家权利要求 8 重叠硬失败，技术效果、实现和权项表达不达标；不得进入 I4。
- `next_action`: 仅作为权利要求 8 从属实施限定或继续申请备选；将证书限定为“对已发现路径及冻结复验协议的条件充分回执”；按等修改像素、时长和模态预算完成消融。

## 5. I4 输入

```yaml
PASS_TO_I4: []
reason: "无候选同时满足总分、全部分项最低分和无硬失败三类条件。"
patent_search_authorized: false
```

本阶段未执行专利检索，未修改正式稿，未执行 Git 操作。

## 6. SHA256

| 文件 | SHA256 |
|---|---|
| `02_candidate_cards.jsonl` | `da5c0904f0783368f0b4facb88488e5b9605856b0403039f9f1ffbc447686cdc` |
| `02_candidate_cards.md` | `79b4e55a482759a6789747cabb0ac37fac88b0d8848956e2b818128413c11356` |
| `03a_evidence_gate.jsonl` | `6a8c1354873bba6136d9b6861c7eac25cfd4d00dfa75a5f5a601e4bd1b9987c7` |
| `03a_evidence_gate.md` | `a05668acc73672a215d04e5878480b1148ebc457fd5e2bea72007178f6415594` |
| `03b_paper_attack.jsonl` | `7ad06a8de127f65c841fc58ef2842766c29df878406d825fb915a2ac9dac449a` |
| `03b_paper_attack.md` | `052d1f834d8b01032952b3db31971bc332487a819abc6632534b8cd95bbdaea8` |
| `gates.yaml` | `73abfb44f1454cfbaa92c06a3c1fcce053a323fb9256b11116d19cdd0e40a5fc` |
| `GOAL_OVERNIGHT_V2.md` | `6fc29151984ab1b2bd01ce820f4aea10e38f9a52c42de40bb6cc57eb45298092` |
| `03_candidate_gate.jsonl` | `41f0361d41457c6de54b93a4108b920dc2e0f471aed61ff35d9e4e2521ab8c18` |
