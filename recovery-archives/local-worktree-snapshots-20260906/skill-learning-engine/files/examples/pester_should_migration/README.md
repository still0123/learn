# Pester Should Migration 真实 Skill 基准

本基准采用 GitHub `github/awesome-copilot` 的公开 `pester-should-migration` Skill，测试
Pester v5 断言迁移到 v6 的程序性规则能否被 Skill 传达、评测和从失败轨迹中恢复。

## 固定来源与边界

| 变体 | 用途 | 修改 |
|---|---|---|
| `skills/original/SKILL.md` | 上游原版对照 | 无；与固定上游文件逐字节一致 |
| `skills/ablated/SKILL.md` | 可控缺陷恢复 | 仅移除 truthy/falsy、`BeNullOrEmpty`、集合/管道解包、`BeIn` 方向的语义指导 |

- Repository: `https://github.com/github/awesome-copilot`
- Commit: `32f32c9809efca35d54c9c5b37210e307aa8645f`
- Path: `skills/pester-should-migration/SKILL.md`
- Upstream SHA-256: `d80c47ed3cda083f6411da12d0251a136608eada05c846eeba361e3168c9f14f`
- License: MIT，见 `THIRD_PARTY_LICENSE.txt`

该 Skill 声明其规则面向 Pester 6.0.0-rc2，属于 preview。实验固定的是上述公开版本，**不把
它当作当前 Pester 行为的权威结论**。`references/assertion-map.md` 也按上游原文保存，用于来源
审计；由于当前引擎的 Executor 只注入一个 `SKILL.md`，本数据集只考察主文件已明确写出的规则，
不会把未注入的参考表当作模型可见知识。

每个变体的 `SOURCE.json` 都保存 commit、许可证、哈希与修改说明。Experiment 会快照并校验
`variant_sha256`，防止改写后的文件被误标为上游原版。

## 数据与评分

`tasks.jsonl` 包含 30 条互不重复的 PowerShell 迁移任务：

| Split | 数量 | 作用 |
|---|---:|---|
| Train | 12 | 产生原始成功/失败轨迹与候选规则 |
| Validation | 8 | 决定候选是否可发布 |
| Test | 10 | 演化结束后的三条件盲测 |

覆盖简单重命名、否定命令、大小写、truthy/falsy、null/empty、集合、`BeIn` 操作数方向、异常、
类型与 mock 断言。`pilot-tasks.jsonl` 是其中严格一致的 3/2/2 子集，只用于确认真实模型是否
在无 Skill 条件下存在可学习空间，不能用于统计结论。

`pester-should-migration` Adapter 采用确定性检查：

- 必需的 v6 重写是否存在；
- 不允许保留的旧语法是否消失；
- 变量初始化等非断言上下文是否被保留；
- 输出是否只包含 PowerShell 代码，而非解释文字。

模型不运行 PowerShell 或安装 Pester；本实验衡量的是给定迁移说明后生成正确迁移片段的能力，
不会把外部运行环境、包版本或网络状态混入分数。

## 运行原版 Pilot

```bash
skill-learning experiment \
  --runtime traex \
  --traex-model gpt-5.5 \
  --output ./experiments/pester-original-pilot \
  --experiment-id pester-original-pilot \
  --tasks ./examples/pester_should_migration/pilot-tasks.jsonl \
  --adapter pester-should-migration \
  --skill-name pester-should-migration \
  --skill-file ./examples/pester_should_migration/skills/original/SKILL.md \
  --iterations 1 \
  --repeats 1 \
  --bootstrap-samples 100
```

在原版完成后，以完全相同参数替换为 `skills/ablated/SKILL.md`，并使用不同的输出目录运行。
若原版或无 Skill 已在 Pilot 满分，必须先记录能力天花板，不应继续将完整实验伪装成有意义的
自学习增量；若存在稳定失败，再扩展为完整 12/8/10 数据集和多次重复实验。

## 恢复 Pilot 的独立划分

首次删减版 Pilot 表明，原 3/2/2 子集的 Validation 恰好被模型先验覆盖，即使隐藏 Test 已暴露
falsy 与 `BeIn` 的失败，门禁仍会在训练之前停止。这是划分不敏感，而不是“系统已经恢复”的
证据。

`learning-pilot-tasks.jsonl` 因而提供独立的 3/2/2 恢复冒烟集：Train 是 truthy、空集合和
`BeIn`；Validation 是不同变量下的 falsy 与 `BeIn`；隐藏 Test 是未在训练中出现的空字符串与
非空字符串语义。它不复用正式 30 条数据集的 task ID 或 split，只用于验证一次“失败 → 提案 →
Validation 门禁 → 隐藏 Test”的完整链路。

`learning-pilot-v2-tasks.jsonl` 是第二个独立恢复 Pilot（4/3/4）。它在 Train 中显式加入空字符串，
并把 null sentinel、falsy 和另一组 `BeIn` 置于 Validation；隐藏 Test 使用不同变量与上下文来
测试空字符串、非空字符串、空集合及 `BeIn`。这检验的是规则跨代码实例的复用，而不是完整
12/8/10 基准中的统计泛化。

## 已完成的真实模型运行

2026-08-31 使用本地 TraeX 与 `gpt-5.5` 完成以下运行。所有结果都固定了数据、Prompt、Seed
Skill、来源元数据、Git 状态和运行时配置；每个 Pilot 只有 2 个唯一 Test task，因此不会标记
统计显著性。

| 运行 | no_skill | seed_skill | evolved_skill | 演化状态 |
|---|---:|---:|---:|---|
| 上游原版，`pilot-tasks.jsonl` | 0.6250 | 1.0000 | 1.0000 | Validation 初始满分，保持 v0 |
| 删减版，`pilot-tasks.jsonl` | 0.7500 | 0.7500 | 0.7500 | Validation 不敏感，保持 v0 |
| 删减版，`learning-pilot-tasks.jsonl` | 0.6250 | 0.7500 | 0.7500 | v1 通过 Validation，但未提升隐藏 Test |
| 删减版，`learning-pilot-v2-tasks.jsonl` | 0.7500 | 0.8125 | 1.0000 | v1 通过 Validation，并提升 4 条隐藏 Test |

原版结果说明该公开 Skill 对这组 Pester 语义任务有可观察的帮助：无 Skill 时模型分别把
`Should-BeFalsy` 写成保留空格的旧风格命令、并虚构了 `Should-BeIn`；原版则通过两题。它仍只是
2 条 Test 的 Pilot，不是统计显著结论。

恢复 Pilot 中，删减版的 Validation 从 0.7500 提升到 1.0000，候选 v1 被接受。候选根据 Train
补回 loose truthy/falsy、空集合和 `BeIn` 方向的规则；但隐藏 Test 的空字符串与非空字符串分别
仍生成 `Should-BeString ''` 和 `Should-BeTruthy`，两者都不满足预期的专用断言。因此该运行只能
证明“失败轨迹可驱动一个经 Validation 门禁的原子 Skill 修改”，**不能**证明该修改已泛化到未见的
null-or-empty 子类型。

v2 在 Train 中补充了空字符串示例。初始 Validation 为 0.9167，候选 v1 为 1.0000；该候选新增了
truthy/falsy、按类型选择 null-or-empty 断言，以及 `BeIn` 的集合在左侧规则。它在 4 条不同变量和
上下文的隐藏 Test 上从 Seed 的 0.8125 提升到 1.0000，包含非空字符串、空字符串、空集合和 `BeIn`。
这构成一次**有限的形式泛化证据**：候选能在未见代码实例中复用已学规则。

该 v2 运行只有 4 个唯一 Test task、1 次重复，`evolved_vs_seed_skill` 的精确 sign-flip p 值为
0.25，仍不满足统计显著性阈值。它不证明跨项目、跨模型或完整 Pester 规则集的泛化；v1 的未泛化
结果也保留在上表中，说明训练覆盖不足时，Validation 通过不等于 Test 收益。

## 已完成的完整 12/8/10 实验

同日使用相同的本地 TraeX 与 `gpt-5.5`，对删减版运行了完整 `tasks.jsonl`：12 条 Train、8 条
Validation、10 条 Test、3 次相互独立的 Repeat、每次 1 轮演化。每个 Repeat 都从全新的工作区和
删减版 v0 开始；候选只能在 Validation **严格优于** v0 时接受，全部三种 Test 条件均在演化结束后
才运行。原始报告位于运行输出目录的 `report.md`，其中保存 Prompt、输入、每条原始回答、候选差异和
门禁事件。

| Condition | Test 均分 | 相对 Seed 的差值 | 95% CI | 双侧精确 sign-flip p 值 | 结论 |
|---|---:|---:|---:|---:|---|
| no_skill | 0.6750 | -0.2583 | [-0.3583, -0.1667] | 0.0039 | 删减版 Skill 显著优于无 Skill |
| seed_skill | 0.9333 | — | — | — | 删减版 v0 基线 |
| evolved_skill | 0.9500 | +0.0167 | [0.0000, 0.0335] | 0.5000 | 未证明优于 Seed |

三次候选均被拒绝：第 1 次 Validation 从 0.9375 降至 0.9063；第 2、3 次均与 0.9375 的基线持平。
最终版本均为 v0。`evolved_skill` 的均分略高于 `seed_skill`，是对同一 v0 进行独立模型采样造成的
数值波动，不是已合入候选带来的收益；配对统计的 p=0.5000 和包含零的置信区间也不支持把它称为
显著改进。

因此，当前可以严谨主张的是：该引擎在这个公开 Skill 快照和固定任务集上，能以 Validation 门禁拒绝
退化或无收益的候选，并且删减版 Skill 相比无 Skill 有显著帮助；**不能**主张单轮自学习已经在完整
数据集上取得稳定、统计显著的增益。下一阶段需要改进提案策略、增加多轮独立候选，或选择有更大
Validation 余量的规则族后再验证学习效果。
