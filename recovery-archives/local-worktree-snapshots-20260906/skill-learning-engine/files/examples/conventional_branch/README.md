# Conventional Branch 真实 Skill 预检

本预检固定 GitHub `github/awesome-copilot` 的公开 `conventional-branch` Skill，考察它能否将带有
大写、空格、下划线和重复连字符的分支名请求规范化为 Conventional Branch 名称。原版与删减版均有
独立 `SOURCE.json`，保存固定 commit、许可证和哈希；许可证见 `THIRD_PARTY_LICENSE.txt`。

| 变体 | 用途 | 修改 |
|---|---|---|
| `skills/original/SKILL.md` | 上游对照 | 与 commit `c956566…e8b1` 的原文件逐字节一致 |
| `skills/ablated/SKILL.md` | 可控缺陷预检 | 删除命名规则、示例、描述指南与具体规范化动作 |

`pilot-tasks.jsonl` 是独立的 3/3/3 预检集，不与 Pester 或 Conventional Commit 的任务复用。它只
评测输出的分支名，不执行 `git checkout`、拉取远端或创建分支。

继续扩展为完整 12/8/10 基准的前提是：删减版在三次独立预检中存在可重复的 Validation 失败，但
分数不接近 0 或 1；若模型先验已使删减版接近满分，也会如实归档为能力天花板，不以修改测试集
追求自学习正结果。

## 已完成的真实模型预检

2026-08-31 使用本地 TraeX 与 `gpt-5.5` 对删减版运行 `pilot-tasks.jsonl`：3 次独立 Repeat、每次
3 条 Train / 3 条 Validation / 3 条 Test、1 轮演化、1 个原子候选上限。三条件 Test 均为 1.0000，
Seed 相对 no_skill 的差值为 0，且只有 3 个唯一 Test task，不能也不应标注统计显著性。

前两次删减版 Validation 均为 1.0000；第 3 次为 0.8889，但其候选引用了不在分配 Pattern 中的
evidence ID，协议校验失败关闭，最终仍保持 v0。该失败事件说明证据校验生效，不是候选收益。

结论：`conventional-branch` 在当前模型和这组任务上属于能力天花板样本，**不扩展**为完整
12/8/10 自学习基准。后续会保留它作为“无学习余量时提前停止”的反例；下一候选需要是模型先验
更弱、但仍能确定性评分的真实 Skill。
