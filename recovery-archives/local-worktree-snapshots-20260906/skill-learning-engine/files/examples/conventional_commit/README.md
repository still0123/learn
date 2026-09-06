# Conventional Commit 真实 Skill 基准

该基准使用 GitHub 官方 `github/awesome-copilot` 仓库中的公开
`conventional-commit` Skill，验证 Skill Learning Engine 对真实第三方 Skill 的收益、回退和
不必要修改，而不是继续使用为实验专门编写的合成 Skill。

## 来源与变体

| 变体 | 用途 | 修改 |
|---|---|---|
| `skills/original/SKILL.md` | 原版防回退实验 | 无；与固定上游文件逐字节一致 |
| `skills/ablated/SKILL.md` | 可控缺陷恢复实验 | 仅移除 breaking change 与 footer 指导 |

固定来源：

- Repository: `https://github.com/github/awesome-copilot`
- Commit: `32f32c9809efca35d54c9c5b37210e307aa8645f`
- Path: `skills/conventional-commit/SKILL.md`
- Upstream SHA-256: `250235f71b8c501a7744ded911281292324bcd1a2d014e34b25041e2d2c8bf73`
- License: MIT，见 `THIRD_PARTY_LICENSE.txt`

每个变体旁的 `SOURCE.json` 记录来源、版本、哈希和修改清单；正式 Experiment 会将它复制到
`inputs/skill-source.json` 并写入 Manifest。若 `variant_sha256` 与实际 Seed Skill 不一致，实验
直接失败。

## 数据与评分

`tasks.jsonl` 包含 30 条互不重复的任务：

| Split | 数量 | 用途 |
|---|---:|---|
| Train | 12 | 提供执行轨迹，只用于知识与候选生成 |
| Validation | 8 | 决定候选是否发布 |
| Test | 10 | 演化结束后执行三条件最终评测 |

任务覆盖 feature、bugfix、documentation、test、refactor、performance、build、CI、style、
maintenance、revert、breaking change 和 issue footer。`pilot-tasks.jsonl` 是 3/2/2 的最小链路
冒烟集，不用于统计结论。

`conventional-commit` Adapter 不要求整句与标准答案完全一致，而是分别评分：

- Conventional Commit Header 是否合法；
- type、scope 和祈使动词是否正确；
- 描述是否覆盖任务要求的关键语义；
- breaking change 与迁移说明是否完整；
- issue reference 与必要 body 信息是否保留。

任务输入会明确要求只返回 Commit Message 且不执行 Git。Executor 仍只有
`submit_result`；任何 Shell、文件修改或其他 TraeX 原生工具调用都会 Fail Closed。

## 已完成的真实模型 Pilot

2026-08-31 使用本地 TraeX 和 `gpt-5.5`，在同一份 3/2/2 Pilot 数据上分别运行了固定上游
原版和可控缺陷版。两次运行均冻结了数据、Prompt、Seed Skill、来源元数据、Git 状态与运行时
配置；结果如下：

| Seed Skill | Validation baseline | no_skill | seed_skill | evolved_skill | 最终版本 |
|---|---:|---:|---:|---:|---:|
| 上游原版 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | v0 |
| 可控缺陷版 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | v0 |

两次实验都没有生成或接受提案，因为初始 Validation 已达到满分，提前停止是门禁的预期行为。
这个 Pilot 只证明真实调用链、来源快照、三条件评测和“无必要修改”路径可以工作。它不能证明
Skill 有增益，也不能证明演化能够修复缺陷：当前任务对 `gpt-5.5` 过于熟悉，无 Skill 条件
已经达到能力天花板；Test 也只有 2 个唯一任务，不满足统计结论要求。

因此暂不继续消耗额度运行 30 条完整实验。若要检验自学习增量，应改用模型先验较弱、但可由
Skill 提供明确程序性知识的真实任务；本基准继续作为公开来源接入、无回退和天花板检测用例。

## 运行原版 Pilot

```bash
skill-learning experiment \
  --runtime traex \
  --traex-model gpt-5.5 \
  --output ./experiments/conventional-original-pilot \
  --experiment-id conventional-original-pilot \
  --tasks ./examples/conventional_commit/pilot-tasks.jsonl \
  --adapter conventional-commit \
  --skill-name conventional-commit \
  --skill-file ./examples/conventional_commit/skills/original/SKILL.md \
  --iterations 1 \
  --repeats 1 \
  --bootstrap-samples 100
```

## 运行完整双实验

先运行未修改原版，再以相同模型和参数运行可控缺陷版。两次实验必须使用不同输出目录。

```bash
skill-learning experiment \
  --runtime traex \
  --traex-model gpt-5.5 \
  --output ./experiments/conventional-original-v1 \
  --experiment-id conventional-original-v1 \
  --tasks ./examples/conventional_commit/tasks.jsonl \
  --adapter conventional-commit \
  --skill-name conventional-commit \
  --skill-file ./examples/conventional_commit/skills/original/SKILL.md \
  --iterations 2 \
  --repeats 3 \
  --bootstrap-samples 1000

skill-learning experiment \
  --runtime traex \
  --traex-model gpt-5.5 \
  --output ./experiments/conventional-ablated-v1 \
  --experiment-id conventional-ablated-v1 \
  --tasks ./examples/conventional_commit/tasks.jsonl \
  --adapter conventional-commit \
  --skill-name conventional-commit \
  --skill-file ./examples/conventional_commit/skills/ablated/SKILL.md \
  --iterations 2 \
  --repeats 3 \
  --bootstrap-samples 1000
```

原版实验的成功不等于必须产生新版本：如果 Seed Skill 已经足够好，候选被门禁拒绝或演化提前
停止也是正确结果。可控缺陷版只有在隐藏 Test 上恢复 breaking/footer 行为且没有显著回退时，
才能支持“系统修复了缺失程序性知识”的结论。
