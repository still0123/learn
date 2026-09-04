# MemoryForge 7 天理解计划与高频追问

> 目标：7 天后能够独立完成 5 分钟项目介绍、10 分钟技术展开、核心源码定位和常见追问回答。  
> 建议投入：每天 2.5～3 小时，总计约 18～21 小时。  
> 说明：代码主要由 AI 辅助生成，不以“逐行手写”为目标；以能解释、运行、验证和修改为掌握标准。

## 一、真实贡献口径

不建议直接写：

> 独立设计并实现 4 万行知识编译系统。

除非确实能证明全部设计和实现由本人完成。更稳妥的说法：

> 使用 AI 编程工具完成 MemoryForge 的需求拆解、方案约束、功能迭代与验证，构建本地优先、
> 可审核、可追溯的技术知识编译系统；能够独立解释核心链路、复现测试并完成针对性修改。

只有确实做过时，才能认领“需求拆解、方案约束、验收、测试和迭代决策”。无法说明具体决策时，
改成“基于 AI 编程工具搭建并持续迭代”。

## 二、7 天总览

| 天数 | 主题 | 当天必须产出 |
| --- | --- | --- |
| Day 1 | 产品定位与整体架构 | 90 秒介绍、手绘六层架构 |
| Day 2 | Source、版本与 Citation | 数据模型图、一次原文回放 |
| Day 3 | ChangeSet 与发布一致性 | 写链路时序图、三个失败场景 |
| Day 4 | 检索、证据状态与预算 | 查询链路图、三态示例 |
| Day 5 | Code Wiki 与 Tree-sitter | 代码索引流程、静态分析边界 |
| Day 6 | MCP、隐私与产品入口 | 客户端调用链、安全边界表 |
| Day 7 | 完整演示与模拟追问 | 5 分钟 Demo、两轮录音复盘 |

每天遵循同一方法：

1. 读解读文档对应章节，30～45 分钟。
2. 对照关键源码，45～60 分钟。
3. 亲手运行或修改一个最小案例，45～60 分钟。
4. 脱稿回答当天问题，30 分钟。

不要逐行阅读全部源码。先掌握主路径，再按追问进入具体函数。

---

## Day 1：讲清它是什么

### 学习目标

- 能用一句话说明 MemoryForge。
- 能解释它解决的问题和普通 RAG 的差异。
- 能画出来源、证据、编译、发布、查询、接入六层架构。

### 阅读范围

- 源码解读：第 0、1、2、18、20 章。
- README：项目定位、与普通 RAG 的区别、核心设计决策。

### 动手任务

从源码安装并启动：

```bash
git clone https://github.com/still0123/MemoryForge.git
cd MemoryForge
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install .
memoryforge init /tmp/memoryforge-study
memoryforge start --workspace /tmp/memoryforge-study
```

### 当天输出

90 秒介绍：

> MemoryForge 是面向 AI 编程助手的本地知识编译系统。它不直接把原始文档切片后交给模型，
> 而是先将 Git、文档、网页和 AI 会话转换为带版本与引用的 Markdown Wiki。更新先生成
> ChangeSet，经过审核和授权后才写入正式 Wiki；查询时只加载少量相关页面，证据不足则限制
> 回答或拒答。核心价值是让项目知识可维护、可追溯，而不只是完成一次问答。

### 过关标准

- 不看稿讲满 90 秒。
- 能回答“它不是普通 RAG 的原因”。
- 能画出写链路和读链路。

---

## Day 2：理解 Source、版本与 Citation

### 学习目标

- 分清 Source、SourceVersion、Blob、Wiki Page、Wiki Fact 和 Citation。
- 明白路径、版本号、内容哈希分别解决什么问题。
- 能从一个 Citation 找回固定版本的原文。

### 阅读范围

- 源码解读：第 4、5、7 章。
- 重点源码：
  - `src/memoryforge/core/models.py`
  - `src/memoryforge/storage/workspace.py`
  - `src/memoryforge/storage/blob_store.py`
  - `src/memoryforge/compiler/wiki_facts.py`

### 动手任务

1. 导入一份十行左右的 Markdown。
2. 找到生成的 Blob 和 SourceVersionManifest。
3. 修改原文件，再次导入。
4. 对比两个版本的哈希和 current pointer。
5. 从 Wiki 脚注定位 `chars:start-end` 对应原文。

### 必须讲清

```text
Source：一份逻辑资料的稳定身份
SourceVersion：这份资料某次导入时的固定版本
Blob：按内容哈希保存的原文
Wiki Page：已发布的可读知识
Wiki Fact：页面中可检索的事实
Citation：事实到固定来源版本和原文区间的指针
```

### 过关标准

- 能解释为什么只保存文件路径不够。
- 能解释 SourceVersion 内容身份不可变，但 current pointer 可变。
- 能现场指出 Citation 如何防止来源更新后引用漂移。

---

## Day 3：理解知识发布链

### 学习目标

- 掌握 `ingest → review → approve → apply`。
- 理解 Proposal Hash、ReviewReceipt、ApprovalReceipt。
- 理解并发冲突和中断恢复。

### 阅读范围

- 源码解读：第 6、8、9、10 章。
- 重点源码：
  - `src/memoryforge/storage/changesets.py`
  - `src/memoryforge/compiler/lifecycle.py`
  - `src/memoryforge/storage/apply_journal.py`
  - `src/memoryforge/storage/version_store.py`

### 动手任务

```bash
memoryforge import README.md \
  --workspace /tmp/memoryforge-study \
  --source-root .
memoryforge ingest --pending --workspace /tmp/memoryforge-study
memoryforge changeset-list --workspace /tmp/memoryforge-study
memoryforge review <changeset-id> --workspace /tmp/memoryforge-study
memoryforge approve <changeset-id> --workspace /tmp/memoryforge-study
memoryforge apply <changeset-id> --workspace /tmp/memoryforge-study
```

观察：

- `changeset.json` 是否仍为 `PROPOSED`。
- Review 和 Approval 如何绑定 Proposal Hash。
- Apply 前如何检查 `base_commit` 和 SourceVersion。
- Apply 后 Wiki、Git 和 SQLite 分别发生什么变化。

### 三个失败场景

1. 审核期间 Git HEAD 改变：旧 ChangeSet 因 `base_commit` 失效。
2. 审核期间来源又更新：旧 ChangeSet 因 SourceVersion 过期被拒绝。
3. Apply 中途崩溃：下次打开 Workspace 时根据 Journal 和 Git 状态回滚或补齐。

### 过关标准

- 能解释 Approve 为什么不直接写文件。
- 能解释系统不是跨介质 ACID 事务。
- 能解释无法证明一致时为什么必须 fail closed。

---

## Day 4：理解检索和证据边界

### 学习目标

- 掌握 CLI/Portal 直接回答链与 MCP map-first 链。
- 理解 FTS5、Exact Symbol、Multi-query RRF、Support Score。
- 能用自然语言解释三态证据，不依赖背英文名。

### 阅读范围

- 源码解读：第 11 章。
- 重点源码：
  - `src/memoryforge/query/query.py`
  - `src/memoryforge/query/context_map.py`
  - `src/memoryforge/query/route_rules.py`
  - `src/memoryforge/query/retrieval_v2.py`
  - `src/memoryforge/query/support.py`
  - `src/memoryforge/query/agent_access.py`

### 两条查询路径

普通问题：

```text
Question
→ FTS / Exact Symbol / Retrieval V2
→ Wiki Fact
→ Citation
→ Support Score
→ grounded / partial / no_local_evidence
```

全局问题：

```text
Question
→ 4,000 字符以内的 navigation map
→ AI 选择 page_paths
→ 二次查询
→ 8,000 字符以内的证据上下文
→ 回答
```

### 三态证据的人话解释

- `grounded`：证据充分，可以回答并附引用。
- `partial`：只支持部分结论，只回答已证实部分。
- `no_local_evidence`：知识库没有足够项目事实，不能把通用知识伪装成项目结论。

### 动手任务

准备三类问题：

1. Wiki 中有完整答案的问题。
2. 只有一部分资料的问题。
3. Wiki 完全没有答案的问题。

分别观察状态、Citation、输出边界和 `--verify` 原文。

### 过关标准

- 能解释检索相关为什么不等于证据充分。
- 能解释为什么不用向量数据库。
- 能解释 RRF 的作用，不需要推导复杂公式。
- 能说出 4,000 / 8,000 / 2,000 / 6,000 四个预算分别约束什么。

---

## Day 5：理解 Code Wiki

### 学习目标

- 理解固定 Git 快照如何进入代码索引。
- 分清 Symbol、Relation、ModulePlan、ArchitectureGraph。
- 明白 Tree-sitter 能做什么、不能做什么。

### 阅读范围

- 源码解读：第 12 章。
- 重点源码：
  - `src/memoryforge/code/code_index.py`
  - `src/memoryforge/code/go_index.py`
  - `src/memoryforge/code/typescript_index.py`
  - `src/memoryforge/compiler/module_planner.py`
  - `src/memoryforge/compiler/code_wiki_compiler.py`

### 动手任务

```bash
memoryforge git-add /path/to/repository --workspace /tmp/memoryforge-study
memoryforge code-add <repository-id> src --workspace /tmp/memoryforge-study
memoryforge git-sync <repository-id> --workspace /tmp/memoryforge-study
```

找一个函数，回答：

1. 符号在哪里定义？
2. 哪些关系来自 AST？
3. 架构图中的边如何回到源码？
4. 动态分派或反射为什么可能漏掉？

### 过关标准

- 不把 Tree-sitter 说成完整编译器或运行时调用追踪。
- 不把固定夹具 100% 外推到任意真实仓库。
- 能解释模型叙事为什么不能修改确定性 Symbol 和 Relation。

---

## Day 6：理解 MCP、隐私与产品入口

### 学习目标

- 分清全局 Router 和项目级 Server。
- 理解 Codex、Claude Code、Gemini、DeepSeek Harness 接入方式。
- 理解 `public`、`local_only`、出站授权和桌面端特殊行为。

### 阅读范围

- 源码解读：第 13、14、15 章。
- 重点源码：
  - `src/memoryforge/interface/mcp_server.py`
  - `src/memoryforge/interface/codex_connect.py`
  - `src/memoryforge/interface/harness_connect.py`
  - `src/memoryforge/portal/local_portal.py`
  - `src/memoryforge/portal/desktop.py`
  - `src/memoryforge/compiler/egress_policy.py`

### 必须讲清

- 全局 Router 默认只读；项目级 Server 才能提出 ChangeSet。
- 两种服务都不暴露 Approve 和 Apply。
- `local_only` 不等于永不出站；显式授权模型后，有限证据可能发送给 Provider。
- Portal 只绑定本机，不是公网 Web 服务。
- 网页导入需要防 SSRF 和 DNS 重绑定。

### 动手任务

至少完成一个客户端连接：

```bash
memoryforge connect codex --workspace /tmp/memoryforge-study
```

在新对话中验证：

```text
先查 MemoryForge，说明这个项目的发布链。
这条结论对应哪个来源版本和原文位置？
```

### 过关标准

- 能说出全局 Router 和项目级 Server 的工具差异。
- 能解释为什么 Agent 可以提案但不能发布。
- 能准确回答“Local-first 是否意味着任何内容都不出本机”。

---

## Day 7：完整演示和压力测试

### 上午：完成 5 分钟 Demo

1. 30 秒讲项目问题。
2. 展示 SourceVersion 与 Blob。
3. 导入新资料并生成 ChangeSet。
4. 展示 Review、Approve、Apply。
5. 展示 Git Commit。
6. 提问并展开 Citation 原文。
7. 用无答案问题展示拒答。
8. 用一句话说明 Benchmark 边界。

### 下午：两轮模拟

第一轮允许看提纲，第二轮完全脱稿。每个答案控制在 30～60 秒。

录音后检查：

- 是否频繁使用自己解释不了的术语。
- 是否把固定题集指标说成通用效果。
- 是否把 AI 生成代码说成自己逐行编写。
- 是否能说清一个真实失败和一次修正。
- 是否能在白板上画出读写两条链路。

### 最终过关标准

- 90 秒项目介绍不卡顿。
- 5 分钟 Demo 能从空 Workspace 跑通。
- 下列高频题至少 20 题能脱稿回答。
- 能现场定位并解释 5 个核心源码文件。
- 能诚实说明个人工作方式和 AI 辅助边界。

---

## 三、高频追问与参考答案

### 1. 这个项目解决什么问题？

MemoryForge 解决项目知识分散、持续过期和回答无法回源的问题。它先把多来源资料编译成
可审核的 Markdown Wiki，再向 AI 提供有限、带引用的上下文。重点是知识生命周期和证据治理，
不只是一次问答。

### 2. 这不就是 RAG 吗？

查询阶段属于检索增强，但系统在 RAG 前增加了知识编译和发布链。原文先形成固定
SourceVersion，候选知识经过 ChangeSet、Review、Approval 和 Apply 后才成为正式 Wiki。
因此模型不能直接污染长期知识，历史结论也能回到固定原文。

### 3. 为什么不直接把所有文档放进上下文？

整库注入会重复消耗上下文，还会混合新旧版本。MemoryForge 先定位少量页面，再按需读取
Citation 对应的原文片段；这样能控制上下文体积，并明确每个结论来自哪一版资料。

### 4. Source、SourceVersion 和 Blob 有什么区别？

Source 是逻辑资料身份；SourceVersion 是一次导入形成的固定版本；Blob 是按内容哈希保存的
原文对象。同一 Source 可以有多个版本，相同内容可以复用同一 Blob。

### 5. 为什么需要内容寻址？

路径和 URL 会变化，内容哈希不会随命名变化。通过 SHA-256 固定 Blob，系统能验证读取内容是否
仍与当时引用一致，也能避免相同内容重复保存。

### 6. Citation 如何保证可追溯？

Citation 绑定来源身份、内容哈希或数值版本、字符区间和引用文本。发布和读取时程序重新检查
范围与文本是否匹配，而不是相信模型生成的引用描述。

### 7. 为什么 ChangeSet 必须不可变？

审核必须针对固定对象。如果审核后还能修改候选内容，Approval 就失去意义。MemoryForge 用
Proposal Hash 固定候选，再让 ReviewReceipt 和 ApprovalReceipt 逐层绑定该哈希。

### 8. Review、Approve、Apply 为什么分开？

Review 表示看过哪个候选，Approve 表示授权发布，Apply 才产生文件、数据库和 Git 副作用。
分离后审核决定可以独立审计，执行失败也不需要伪造一次新审核。Portal 可以把三步组合成一次
用户操作，但底层凭证仍分离。

### 9. 如何防止旧草稿覆盖新知识？

ChangeSet 同时绑定生成时的 Git `base_commit` 和来源版本。审核期间只要 Wiki HEAD 或来源版本
发生变化，Apply 就拒绝旧候选，避免最后写入者直接覆盖新状态。

### 10. Apply 是原子事务吗？

不是跨 SQLite、文件系统和 Git 的 ACID 事务。实现采用单机排他锁、提交前重验、双重 Lint、
Apply Journal 和补偿恢复；无法证明状态一致时 fail closed。

### 11. 进程在 Apply 中途崩溃怎么办？

下次可写打开 Workspace 时读取 Journal。如果 Git HEAD 仍是旧基线，就恢复旧文件和投影；
如果 HEAD 已是目标 Commit，就补齐投影和归档；状态无法对应时停止自动恢复。

### 12. SQLite 是唯一真相吗？

不是。Blob 固定原文，Git 固定正式 Wiki 历史，SQLite 保存来源元数据、运行状态和查询投影。
只有 Wiki 投影能在来源元数据完整时重建；数据库整体损坏仍需要恢复备份。

### 13. 为什么选择 SQLite FTS5，不先用向量数据库？

当前数据以技术标题、模块名和代码标识符为主，FTS5 部署成本低、完全本地、结果可解释，也便于
冻结和重放实验。它不是永远优于向量检索；真实数据若持续暴露同义召回问题，可以增加语义通道，
再与现有排序融合。

### 14. RRF 有什么作用？

原问题和补充查询会产生不同排序，分数尺度不一定一致。RRF 只根据候选名次融合结果，使多个
查询中都靠前的事实获得更高排名，避免直接比较不可比的原始分数。

### 15. Support Score 解决什么问题？

检索只说明内容相关，不说明证据足够。Support Score 检查标识符、核心词、事实共现、否定关系、
来源覆盖和版本有效性，并结合 Hard Gates 决定能否作为项目答案。

### 16. 三态证据是什么意思？

证据充分时正常回答并引用；只支持部分内容时仅陈述已证实部分；没有本地证据时明确拒绝项目结论。
它的价值是把“不知道”和“工具调用失败”分开，也不让通用知识冒充项目事实。

### 17. map-first 是什么？

面对“整体架构是什么”这类全局问题，MCP 第一次只返回 4,000 字符以内的页面地图。AI 选择
`page_paths` 后再二次查询事实和 Citation。地图只负责导航，不能直接作为回答证据。

### 18. 为什么限制 8,000 字符？

这是 MCP 回答上下文的硬预算，避免一个工具调用挤占整个模型上下文。系统还限制 map 为
4,000 字符、单条 Evidence 为 2,000 字符、Session Capsule 默认 6,000 字符。

### 19. Code Wiki 如何生成？

系统从固定 Git Commit 读取代码，用 Tree-sitter 抽取 Symbol 和 Relation，再确定性生成
ModulePlan、模块页面和 Mermaid 架构图。模型只能补充有 Citation 的自然语言说明，不能修改
确定性代码事实。

### 20. Tree-sitter 分析有哪些限制？

它擅长语法结构和静态关系，但不能完整识别反射、动态分派、运行时依赖注入、字符串调用和跨进程
关系。因此架构图是带源码证据的静态近似，不是运行时全知图。

### 21. MCP 全局 Router 与项目级 Server 有什么区别？

全局 Router 查询整个已应用 Workspace，当前项目只影响排序，且工具面只读。项目级 Server
严格绑定已登记仓库，还可以生成待审核 Proposal；两者都不暴露 Approve 和 Apply。

### 22. Agent 为什么不能直接发布？

长期知识一旦被错误写入，会持续污染之后的回答。Agent 只能读取证据和提出 ChangeSet，正式
发布仍经过独立审核、授权和 Apply；这比依赖提示词要求模型“谨慎”更可靠。

### 23. Local-first 是否代表数据绝不出本机？

不是。核心持久化默认在本机，确定性路径可以完全本地运行；启用外部模型并显式授权后，经过
筛选、脱敏和字符限制的证据可能发送给 Provider。应表述为本地优先，而不是绝不出站。

### 24. 网页导入如何防 SSRF？

只允许 HTTP/HTTPS，拒绝带凭据 URL，解析并校验目标地址，阻止私网和保留地址，并把请求固定到
已验证地址以降低 DNS 重绑定风险；同时限制跳转次数和响应大小。

### 25. 96.7% 回答准确率能证明什么？

只证明固定公开仓库、固定 30 题和冻结评测规则下的结果。它适合验证设计和防回归，不能外推为
任意仓库效果或生产 SLA。

### 26. Citation grounding 100% 是否代表回答正确？

不代表。Citation grounding 只说明引用可以回到原文；答案是否正确还取决于事实是否完整、
来源是否满足题目要求以及结论是否与证据一致。项目保留了引用正确但严格答案判错的样例。

### 27. 为什么保留 Click 外部评测的负结果？

它暴露了规则和词法检索的跨领域泛化限制，防止把固定题集高分包装成通用能力。保留失败结果也让
后续改进能使用新确认集，而不是反复针对已揭盲数据调参。

### 28. 656 个测试能证明什么？

它证明 `v0.4.0` 在声明的 macOS 环境通过了当时的测试及发布门禁，不证明系统没有 Bug，也不覆盖
该 Release 之后的主线提交。更重要的是能说明关键不变量和失败路径被哪些测试覆盖。

### 29. 代码主要由 AI 生成，你个人做了什么？

仅在符合事实时使用下面回答：

> 代码实现大量使用 AI 编程工具，我不把它描述成逐行手写。我的贡献集中在需求定义、架构约束、
> 验收标准、测试门禁、失败样例复盘和迭代决策；对简历中保留的核心链路，我能够独立解释、
> 运行、定位问题并完成修改。无法解释或没有验证过的部分，我不会作为个人能力认领。

回答后应主动举一个自己真实参与的例子，例如发现并要求修复 SSRF、证据状态迁移遗漏或
8,000 字符预算失效。没有亲自做过的例子不得使用。

### 30. 如果重新设计，你会先删掉什么？

先保留 SourceVersion、ChangeSet、Citation、Git 发布和最小 FTS 查询闭环。Portal、桌面端、
多客户端、自动策略和高级 Code Wiki 都应在核心闭环稳定后再增加，避免能力面扩大快于验证能力。

### 31. 项目最难的取舍是什么？

不是模型选择，而是自动化效率和知识可信度之间的平衡。系统允许 AI 编译和提案，但把正式发布
留给可审计凭证与确定性校验；代价是流程更长，收益是长期知识不会被一次错误回答直接污染。

---

## 四、快速自测

每题按 0～2 分计分：

- 0 分：不知道或只能背关键词。
- 1 分：能解释概念，但不能联系源码或 Demo。
- 2 分：能解释、指出代码入口，并举出失败场景。

必测题：

1. 画出写链路。
2. 画出普通查询和 map-first 查询。
3. 解释 SourceVersion 与 Blob。
4. 解释 Review、Approve、Apply。
5. 解释 `base_commit`。
6. 解释 Apply Journal。
7. 解释三态证据。
8. 解释为什么不用向量数据库。
9. 解释 Tree-sitter 的边界。
10. 解释 Global Router 和 Project Server。
11. 解释 `local_only`。
12. 解释 96.7% 的适用范围。
13. 说明一个公开负结果。
14. 说明 AI 编码和个人贡献边界。
15. 现场跑通一次端到端 Demo。

评分：

- 0～14：暂时不要放进核心项目经历。
- 15～22：可以放简历，但只保留两条稳妥描述。
- 23～26：可以应对常规技术面。
- 27～30：可以作为重点项目展开。

## 五、7 天后建议使用的简历表述

前提：你已完成上面的 Demo、源码定位和模拟问答。

> 基于 AI 编程工具搭建并持续迭代本地优先的知识编译系统，将 Git、技术文档、网页和 AI 会话
> 统一为版本化来源与可追溯 Wiki；通过不可变 ChangeSet、审核凭证和 Git Commit 管理知识发布。

> 构建 FTS5、精确符号匹配与多查询融合的渐进式检索链，并设计分级证据评估和上下文预算；
> 固定公开 30 题集上达到 96.7% 回答准确率、96.2% Top-3 来源召回率，引用与拒答准确率为 100%。

> 基于 Tree-sitter 生成 Python、Go、TypeScript/TSX 的 Symbol、Relation、模块页面和带源码引用的
> Mermaid 架构图，并通过 MCP 接入主流 AI 编程客户端。

禁止写“独立手写全部系统”“通用准确率 96.7%”“生产级零故障”“所有数据永不出站”。

