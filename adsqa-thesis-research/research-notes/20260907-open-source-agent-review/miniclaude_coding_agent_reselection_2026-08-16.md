# MiniClaude 类 Coding Agent 项目重新评选

> 目标：构建一个独立、轻量、可读、可运行的 Claude Code 风格 Coding Agent。  
> 本轮评分不考虑 AdsQA、视频分析、专利或多模态业务相关性。

## 结论

最适合你的路线不是修改 DSH 桌面壳，也不是直接 fork 体量较大的 Agent，而是：

1. 用 [bcefghj/miniClaudeCode](https://github.com/bcefghj/miniClaudeCode) 理解约 800 行核心 Agent Loop。
2. 用 [hey-Chloe/MiniClaudeCode](https://github.com/hey-Chloe/MiniClaudeCode) 设计权限、安全运行时、会话恢复和评测。
3. 用 [flysheep-ai/learn_deepseek_harness](https://github.com/flysheep-ai/learn_deepseek_harness) 学习事件日志、工具流水线和插件边界。
4. 用 [zmylol/MiniClaude](https://github.com/zmylol/MiniClaude) 参考完整产品结构与 TUI。
5. 自己重新实现一个 Python 单进程版本，控制在 2000-4000 行，而不是拼装上述代码。

**首选代码架构参考：`zmylol/MiniClaude`。**  
它具有 MIT 许可证，已经包含 Agent Loop、TUI、事件流、权限、MCP、会话和压缩，且仓库规模仍适合单人阅读。

**首选核心原理参考：`bcefghj/miniClaudeCode`。**  
它把 Agent Loop、工具、权限和上下文压缩到约 800 行，但仓库没有可识别许可证，只能学习设计，不能直接复制代码。

## 评分标准

| 维度 | 权重 |
|---|---:|
| MiniClaude 目标匹配度 | 30 |
| 核心代码可读性与规模 | 20 |
| 文件、Shell、编辑等编码能力 | 15 |
| 权限、安全和工作区边界 | 15 |
| 会话、上下文和恢复能力 | 10 |
| 测试、许可证和维护性 | 10 |

## 候选 Agent 排名

| 排名 | 项目 | 分数 | 建议 |
|---:|---|---:|---|
| 1 | [zmylol/MiniClaude](https://github.com/zmylol/MiniClaude) | 96 | 最适合参考整体产品结构：Python daemon、CLI/TUI、JSON-RPC 事件流、权限、MCP、会话和压缩；MIT |
| 2 | [flysheep-ai/learn_deepseek_harness](https://github.com/flysheep-ai/learn_deepseek_harness) | 95 | 最好的 Harness 教程：从 60 行循环逐步增加工具、权限、事件日志、压缩、Skill 和插件；MIT |
| 3 | [bcefghj/miniClaudeCode](https://github.com/bcefghj/miniClaudeCode) | 93 | 约 800 行 Python，最适合理解最小 Agent Loop、6 个工具和两层权限；无许可证，只学不抄 |
| 4 | [hey-Chloe/MiniClaudeCode](https://github.com/hey-Chloe/MiniClaudeCode) | 92 | 安全和评测设计最好：ALLOW/ASK/DENY、Docker 隔离、checkpoint、26 项 coding benchmark；无许可证 |
| 5 | [e10nMa2k/cc-mini](https://github.com/e10nMa2k/cc-mini) | 91 | 约 1000 行核心，已具备 9 个工具、Plan、会话、压缩、Skill 和 bwrap sandbox；无许可证 |
| 6 | [ZZKeepCurious/mini-deepseek-harness-python](https://github.com/ZZKeepCurious/mini-deepseek-harness-python) | 91 | 事件溯源、插件总线、工具流水线和崩溃恢复最严谨，555 项测试、零第三方依赖；MIT |
| 7 | [thevibeworks/deepseek-code](https://github.com/thevibeworks/deepseek-code) | 89 | TypeScript/Bun、零运行时依赖；上下文、会话、Skill、子 Agent 均受测试或评测门控制；MIT，仍为 WIP |
| 8 | [agi-fans/oh-my-dsh](https://github.com/agi-fans/oh-my-dsh) | 88 | 学习如何把 Runtime 与 TUI 分层，支持恢复、回退、审批、Skill、MCP 和遥测；MIT，但依赖 DSH |
| 9 | [catyans/cathead-coding](https://github.com/catyans/cathead-coding) | 88 | DSH 上较完整的小型 Coding Agent 产品：输入队列、steering、sandbox、resume、plan 和 subagent；MIT |
| 10 | [pulseaiclub/phi](https://github.com/pulseaiclub/phi) | 87 | Go 生产级参考：hashline 编辑、权限门、按需 MCP、Skill、会话和 TUI；MIT，但约 22K LOC，不宜直接仿写 |
| 11 | [Louisym/MiniCC](https://github.com/Louisym/MiniCC) | 86 | 19 个教学 Demo 与 13 个模块，适合按 Session→Tool→Permission→Storage 顺序学习；MIT |
| 12 | [minorcell/mini-claude-code](https://github.com/minorcell/mini-claude-code) | 85 | Go + Bubble Tea 小型 TUI Agent，工具注册、工作区约束和事件广播边界清楚；MIT |
| 13 | [UNLINEARITY/dsh-code](https://github.com/UNLINEARITY/dsh-code) | 84 | Claude Code 风格终端体验、会话恢复和审批交互参考；MIT，但只是 DSH TUI，不包含独立 Agent Loop |
| 14 | [huiliyi37/dsh-tianshu-tui](https://github.com/huiliyi37/dsh-tianshu-tui) | 83 | TUI、diff 审批、命令面板和状态派生较成熟；Apache-2.0，但功能较重 |
| 15 | [sandbaseai/sandbase-harness](https://github.com/sandbaseai/sandbase-harness) | 82 | Docker/Kubernetes sandbox、审计、回放和权限策略参考；Apache-2.0，属于平台而非 Mini Agent |
| 16 | [ljw1004/mini_agent](https://github.com/ljw1004/mini_agent) | 81 | 约 280 行循环 + 400 行工具，MCP 化工具边界清晰；MIT，但明确缺少权限与安全 |
| 17 | [DerekYRC/mini-claude-code](https://github.com/DerekYRC/mini-claude-code) | 79 | Java 分阶段教学覆盖 Agent Loop 到 MCP/多 Agent；内容全面但已偏离“Mini”，且无许可证 |
| 18 | [txl16095/MiniClaude](https://github.com/txl16095/MiniClaude) | 72 | 功能完整、Star 较多，但 README 自称由 Claude Code 删除 92000 行得到，存在上游代码来源风险，不建议 fork |
| 19 | [Sikao-Engine/KimiX](https://github.com/Sikao-Engine/KimiX) | 70 | 上下文检索、防循环和多 Provider 有参考价值，但体量大、来自 Kimi CLI 分支且无许可证 |
| 20 | [OkinoYu/DeepSeek-Coding-Agent-Harness](https://github.com/OkinoYu/DeepSeek-Coding-Agent-Harness) | 58 | 当前仍需手工 `/tool`，自动工具选择、循环、编辑、权限和 sandbox 都在 Roadmap，不适合作为基底 |

## 六个值得单独借鉴的子系统

这些不是完整 Agent，不应单独作为项目，但适合实现 MiniClaude 的关键模块。

| 子系统 | 项目 | 借鉴点 |
|---|---|---|
| 权限 | [PerryLink/dsh-permission-rules](https://github.com/PerryLink/dsh-permission-rules) | 有序 `allow/deny/ask`、工具与参数匹配、路径规则、审计和 dry-run；139 测试，Apache-2.0 |
| 回滚 | [PerryLink/dsh-checkpoint-rewind](https://github.com/PerryLink/dsh-checkpoint-rewind) | 修改前 Git 快照、预览、文件恢复与会话分叉保持一致；Apache-2.0 |
| 上下文 | [TT-Wang/dsh-slice-agent-loop](https://github.com/TT-Wang/dsh-slice-agent-loop) | 有界上下文切片、持久 tape 和按需原文召回；BSD-3-Clause |
| Skill | [Jesse-njx/dsh-skillport](https://github.com/Jesse-njx/dsh-skillport) | 只注入 Skill 索引，正文按需加载；格式兼容和触发诊断；MIT |
| MCP | [NexusAgentX/dsh-mcp-adapter](https://github.com/NexusAgentX/dsh-mcp-adapter) | 不把所有 MCP Schema 塞入上下文，只暴露 `search/describe/call` 代理工具；MIT |
| 会话检索 | [Tieboyh/dsh-session-search](https://github.com/Tieboyh/dsh-session-search) | 只读扫描多种 Agent 会话，按需读取窗口，不强制建立派生数据库；许可证需再次核验 |

## 推荐的个人项目方案

### 技术选择

- Python 3.12
- `uv` 管理环境
- `httpx` 或官方模型 SDK
- 第一版使用普通 REPL；稳定后再引入 Textual/Rich
- JSONL 追加事件日志
- `pytest + Ruff + mypy`

### 核心架构

```text
CLI/TUI
  -> AgentController
     -> LLMProvider
     -> ToolRegistry
        -> PermissionPolicy
        -> Runtime
     -> SessionEventLog
     -> ContextBuilder
```

### V0.1 必做

1. 有最大步数的 Agent Loop。
2. `read/edit/write/glob/grep/bash` 六个工具。
3. 所有参数先通过 JSON Schema 或类型校验。
4. `ALLOW/ASK/DENY` 权限决策。
5. 路径限制在 workspace 内。
6. 命令使用 argv、`shell=False`、超时和输出截断。
7. JSONL 会话日志与 resume。
8. 流式输出和工具调用展示。
9. 10-20 个离线循环、工具和权限测试。

### V0.2 再做

- `AGENTS.md` / 项目规则加载
- Skill 索引与按需正文加载
- 上下文压缩
- Git diff 与修改前 checkpoint
- MCP `search/describe/call`
- 基础 Coding Benchmark

### 暂时不要做

- 多 Agent 团队
- 长期向量记忆
- daemon 与多客户端协议
- 桌面端
- 插件市场
- 浏览器自动化
- 自动进化

这些功能会显著扩大范围，却不会证明你的核心 Agent Loop、工具可靠性和权限边界是正确的。

## 最终选择

如果想**最快做出能用的个人项目**：

> 以 `zmylol/MiniClaude` 的模块边界为产品参考，以 `bcefghj/miniClaudeCode` 的最小循环为实现起点，以 `hey-Chloe/MiniClaudeCode` 的权限和评测设计作为质量标准。

如果想**基于 DSH 快速做一个发行版**：

> 参考 `agi-fans/oh-my-dsh` 或 `catyans/cathead-coding`，只实现 TUI、预设和少量插件；这条路线开发更快，但项目的核心 Runtime 所有权较弱。

如果想**真正形成自己的 Coding Agent 项目**：

> 从零实现单进程 Python Runtime。先完成 V0.1，再逐步加入 Skill、压缩、checkpoint 和 MCP；不要 fork `txl16095/MiniClaude` 的上游代码。
