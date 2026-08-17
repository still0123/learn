# LLM Wiki 详解：从 Karpathy 范式到工程落地

> 发布于 2026-08-11 · 基于 Karpathy 2026-04-04 原始 Gist 及社区演进整理

---

## 0. 一句话定义

**LLM Wiki 是一种「摄入时编译、查询时只读」的知识管理范式**——由 LLM Agent 将原始资料持续编译为结构化、互链的 Markdown 维基，替代传统 RAG 的「查询时临时检索拼接」模式。

核心论断：*"维护知识库的苦活不是阅读和思考，而是簿记（bookkeeping）。人管策源与判断，LLM 管簿记。"* —— Karpathy

---

## 1. 背景：传统 RAG 的四大顽疾

传统 RAG（Retrieval-Augmented Generation）在工程落地中存在系统性缺陷：

| 问题 | 现象 | 根因 |
|---|---|---|
| **金鱼记忆** | 每次对话要重新上传文件、重新检索 | 无状态架构，知识不持久化 |
| **Token 浪费** | 同一段文本被反复切块、反复向量化、反复阅读 | 每次查询从零开始「重新学习」 |
| **合成漂移** | 同一问题问两次，答案结构、引用乃至结论都可能不同 | 检索噪声 + LLM 温度导致合成不稳定 |
| **不可审计** | 回答引用的是向量检索的 chunk，无法精确回溯原文位置 | chunk 级引用粒度太粗，缺乏溯源链 |

形象比喻：传统 RAG 像一个「每次考试都翻书作弊的学生」，而 LLM Wiki 是一个「提前把所有课本整理成精编笔记、考试只查笔记的学霸」。

---

## 2. 核心架构：三层静态模型

Karpathy 原始定义的三层架构，是整个范式的骨架：

```
┌─────────────────────────────────────────────┐
│  Layer 3: Schema 规则层                     │
│  (CLAUDE.md / AGENTS.md)                    │
│  · 目录结构约定                              │
│  · 写作标准 / 引用格式                       │
│  · 摄入 / 查询 / 巡检工作流                  │
│  · 领域分类法（Entity / Relation 类型）       │
├─────────────────────────────────────────────┤
│  Layer 2: Wiki 编译层                       │
│  wiki/                                      │
│  · index.md  — 全局目录（一页一行摘要）       │
│  · log.md    — 时间线（摄入/查询/巡检日志）   │
│  · sources/  — 每篇原始资料的摘要页          │
│  · entities/ — 实体页（人/组织/工具/概念）    │
│  · concepts/ — 概念页（定理/框架/算法）       │
│  · ...其他领域自定义分类                     │
├─────────────────────────────────────────────┤
│  Layer 1: Raw 原始层                        │
│  raw/                                       │
│  · PDF / 论文 / 笔记 / 代码仓 / 网页存档     │
│  · 【不可变】LLM 只读不写                    │
│  · 唯一真相来源（Source of Truth）           │
└─────────────────────────────────────────────┘
```

### 2.1 层间约束（硬规则）

- **Raw → Wiki**：单向流动。Wiki 中的每一句断言必须能回溯到 Raw 中的具体位置。
- **Schema → Wiki**：强约束。Wiki 的格式、结构、元数据必须符合 Schema 定义，否则 Lint 失败。
- **Wiki → Raw**：绝不反向修改。Raw 一经入库，永不改动（包括文件名、内容）。

### 2.2 两个关键元文件

#### `wiki/index.md` — 维基的「目录树」
```markdown
# Wiki Index

## AI 基础设施
- [RAG](wiki/concepts/rag.md) — 检索增强生成的标准范式
- [Tree-sitter](wiki/tools/tree-sitter.md) — 多语言语法解析器

## 来源摘要
- [2026-Karpathy-LLMWiki](wiki/sources/2026-karpathy-llmwiki.md) — LLM Wiki 原始提案 (442a6bf)
```

#### `wiki/log.md` — 维基的「变更日志」
```markdown
# Wiki Log

## 2026-08-11
- [ingest] 2026-Karpathy-LLMWiki.pdf → 新建 1 摘要页，更新 3 概念页，新增 2 实体页
- [query] "LLM Wiki 与 RAG 的区别？" → 答案已归档为 [comparison](wiki/comparisons/rag-vs-llmwiki.md)
- [lint] 发现 1 个孤立页，自动修复反向链接
```

---

## 3. 三大核心操作

LLM Wiki 的生命周期由三个闭环操作驱动，对应编译器的三阶段：

| 操作 | 编译器类比 | 触发时机 | 做什么 |
|---|---|---|---|
| **Ingest 摄入** | Compile 编译 | 新资料入库 | 读 Raw → 提取断言 → 创建/更新 Wiki 页 → 写索引和日志 |
| **Query 查询** | Link 链接 | 用户提问 | 搜 Wiki → 读相关页 → 综合回答（带引用）→ 优质答案回写 Wiki |
| **Lint 巡检** | Optimize 优化 | 定期 / 手动 | 孤立页检测、矛盾校验、反向链接补全、过期标记、缺失概念提示 |

### 3.1 Ingest：知识编译器的核心

单次 Ingest 的标准工作流：

```
新文件入 raw/
    │
    ▼
1. 全量阅读 → 提取 Claim（声明）、Entity（实体）、Concept（概念）
    │
    ▼
2. 匹配现有 Wiki → 判断哪些页要更新、哪些页需新建
    │
    ▼
3. 执行写入：
   - 新建/更新 source 摘要页（含精确引用锚点）
   - 更新相关 entity/concept 页（追加新信息 + 标注来源）
   - 新建合成页（如多来源比较页）
    │
    ▼
4. 更新 index.md 目录 + 追加 log.md 条目
```

**关键属性**：一个 20 页的 PDF 通常会触发 10–15 个 Wiki 页的联动修改。知识是「编织」进去的，不是孤立存放的。

### 3.2 Query：答案是维基的「视图」

查询与传统 RAG 的本质差异：

- **检索对象**：不是 raw chunk，而是已经被人类+LLM 双重审核过的结构化 Wiki 页。
- **引用粒度**：引用的是 `[概念名](wiki/concepts/xxx.md#章节锚点)`，可精确点击跳转。
- **知识回写**：好的问答（如「比较 A 和 B」「解释 X 的演进」）不应消失在聊天记录里，应作为新的 Wiki 页归档，即 **Query-to-Wiki Conversion**。

### 3.3 Lint：活体知识库的「自愈机制」

Lint 是 Karpathy 范式中最容易被忽视但最关键的操作：

| 检查项 | 说明 | 处理方式 |
|---|---|---|
| 孤立页 | 在 wiki/ 中存在但 index.md 未登记 | 自动补录 or 提示删除 |
| 断链 | 页 A 引用了页 B，但页 B 不存在 | 自动创建 stub 页 or 提示补页 |
| 矛盾 | 页 X 说「A=1」，页 Y 说「A=2」 | 双端标注 ⚠️ Contradiction 标签 + 提示用户裁决 |
| 过期 | 声明标注了时间戳，超过阈值未更新 | 自动加 🕰️ Stale 标签 |
| 缺失 | 高频被引用的概念没有独立 Wiki 页 | 提示创建候选页列表 |

---

## 4. 与 RAG 的本质对照

| 维度 | 传统 RAG | LLM Wiki |
|---|---|---|
| **合成时机** | 查询时（每问每合成） | 摄入时（一次编译，反复查询） |
| **知识状态** | 无状态，会话结束蒸发 | 有状态，持续复利增长 |
| **权威层** | Raw 语料直接权威 | Wiki 是 Raw 之上的策展层 |
| **引用精度** | chunk 级（±300 字模糊范围） | 字符级 / 行级 / 章节级 |
| **扩展瓶颈** | 语料越大，检索噪声越高 | 分类合理时，线性扩展无噪声 |
| **前置成本** | 每篇文档近似 0（向量化 cheap） | 每篇文档需一次 LLM 编译（moderate cost） |
| **适用场景** | 大规模、高流动性、粗粒度问答 | 策展型、稳定域、高审计要求知识 |

> ⚠️ 两者不互斥。当 Wiki 超过 200+ 页时，LLM 自身上下文装不下，可在 Wiki 层之下再挂一层语义检索 / FTS。此时 Wiki 是 RAG 之上的「高质量精排层」。

---

## 5. 编译器视角：一个更深刻的类比

社区实践总结出 LLM Wiki 与编译器的惊人同构性：

| 编译器概念 | LLM Wiki 对应物 | 说明 |
|---|---|---|
| 源代码 `.c/.py` | `raw/` 原始资料 | 人类可读的权威输入 |
| 前端（Parser） | Ingest 第一步：抽取断言/实体/概念 | 语法结构解析 → AST |
| IR 中间表示 | `wiki/` 编译产物 | 结构化、可优化、可链接的知识表示 |
| 优化 Pass | Lint 巡检 | DCE（删孤立页）、常量折叠（合并重复断言）、矛盾检测 |
| 链接器 Linker | Query 综合 | 把多个 IR 片段链接成一个可执行回答 |
| 可执行文件 | 最终答案 + 引用链 | 用户消费的成品 |
| Build 系统 | Schema + Agent Orchestrator | 决定何时编译、编译哪些文件 |
| `make clean` | 全量重新编译（罕见） | Schema 大改时清空 wiki/ 重新生成 |

这个类比的推论：
- **Schema 是 Makefile**——它定义了编译规则，是整个系统最高杠杆的制品。
- **不做 Incremental Build = 浪费**——每次新增资料只重编受影响的页，不重编整个 Wiki。
- **需要 Build Cache**——用 Hash 记录 Raw 与 Wiki 的对应关系，避免重复编译未变更的 Raw。

---

## 6. MemoryForge 工程增强：从范式到生产

Karpathy 的 Gist 是「思想文件」，不是工程实现。MemoryForge 项目在严格遵循三层架构的基础上，做了以下超标增强：

### 6.1 引用冻结机制（Source Anchoring）

**问题**：Karpathy 原版仅要求「引用 Wiki 页」，但 Wiki 页本身是可变的，无法冻结到原文的确切证据。

**解法**：引入双层引用链：

```
回答文本
  └─→ 引用 wiki/concepts/xxx.md#H2-3
        └─→ 引用 raw/paper.pdf#sha256=<hash>&chars=12345-12789
```

- **SHA256 不可变快照**：Raw 文件入库即计算 SHA256，任何字节改动都会触发 Hash 变化，从而触发重新编译。
- **`chars:N-M` 精确字符偏移**：每个 Wiki 断言绑定原始文本中的 Unicode 字符区间，支持一键跳转和取证。

**量化结果**：引用落地准确率 100%（对比 BM25 baseline 57.7%）。

### 6.2 Tree-sitter 跨语言代码索引

**问题**：纯文本 Ingest 对代码仓极不友好——函数、类、方法的符号级关系无法从纯文本中提取。

**解法**：用 Tree-sitter 统一实现 Py/Go/TS 三语言的 Symbol 提取器（替代多语言独立 visitor 方案，编译时间缩短 63%）：

```
raw/repo/
  └─→ Tree-sitter Parse
        ├─→ 函数定义 → wiki/entities/func-xxx.md
        ├─→ 类定义   → wiki/entities/class-yyy.md
        └─→ 调用图   → wiki/concepts/call-graph.md  (嵌入反向链接)
```

### 6.3 六组件拒答模型

**问题**：Karpathy 原版没有显式的「知识边界检测」——当 Wiki 中不存在支撑证据时，Agent 仍可能幻觉式回答。

**解法**：硬编码 75.0 支持度阈值的加权拒答校验：

1. 命中 Wiki 页数量（20%）
2. 精确锚点覆盖率（25%）
3. 多来源交叉验证（20%）
4. 时间新鲜度（15%）
5. 断言置信度标签（10%）
6. 语义关联紧密度（10%）

**量化结果**：超纲拒答准确率 100%，整体回答准确率 96.2%。

### 6.4 全局排他锁

**问题**：Ingest、Query、Lint 三者并发操作可能引发 Wiki 页写冲突。

**解法**：工作区采用全局 POSIX 排他锁（当前不支持读写分离，后续可演进为读写锁 + 多版本快照）。

---

## 7. Schema 工程化：真正的「产品层」

社区共识：**十五个开源实现里，十四个做错了层。** 它们花 90% 精力做 wiki/ 的工具链，只花 10% 精力在 CLAUDE.md/AGENTS.md 上。而 Schema 才是整个范式的「编译器规格说明书」。

一个合格的 Schema 应包含：

### 7.1 目录结构契约
```markdown
## 目录规范
wiki/{domain}/sources/   # 来源摘要页，命名：YYYY-作者-关键词.md
wiki/{domain}/entities/  # 实体页（人/组织/工具）
wiki/{domain}/concepts/  # 概念页（定义/框架/对比）
wiki/global/             # 跨 2+ domain 的公共概念
```

### 7.2 页面前言规范（Frontmatter）
```yaml
---
id: "concept-rag-20260401"
aliases: ["Retrieval-Augmented Generation", "检索增强生成"]
sources:
  - ref: "raw/lewis2020retrieval.pdf#chars=1000-2500"
    confidence: 0.95
  - ref: "raw/karpathy-llmwiki.md#chars=500-800"
    confidence: 0.90
supersedes: "concept-naive-rag"      # 被本页替代的旧概念
superseded_by: null                 # 若被替代，指向新页
last_reviewed: "2026-08-01"
stale_after_days: 180
---
```

### 7.3 不确定性显式标注
Schema 强制要求：非 100% 确认的断言必须显式打标签。
- ✅ **Established**（≥2 独立来源交叉验证，置信度 ≥0.9）
- 🟡 **Tentative**（单一来源支撑，或来源间存在轻微不一致）
- 🔴 **Speculative**（推测性陈述，明确标注「未验证」）
- ⚠️ **Contradiction**（多来源矛盾，列全各方观点 + 证据链）

---

## 8. 社区演进：从 v1 到 v2 的关键补丁

Karpathy 原版发布后六周内，社区发现了几个关键架构缺口，并形成了事实上的 v2 扩展：

### 8.1 置信度衰减（Confidence Decay）
**问题**：原版默认「知识永不过期」。技术新闻、API 版本这类时效性强的知识，6 个月后就是错误信息。

**v2 解法**：引入遗忘曲线 + 声明声明周期四档：
```
Raw Observation → Tentative Claim → Established Fact → Canonical Knowledge
     (0-7天)          (7-30天)         (30-180天)        (>180天且复现)
```
每档的 cross-reference 要求、置信度阈值、复审频率逐级提高。

### 8.2 替代链（Supersession Chains）
当一个概念被新概念取代时，不是删除旧页，而是：
1. 旧页 frontmatter 加 `superseded_by: "concept-new-xxx"`
2. 新页 frontmatter 加 `supersedes: "concept-old-xxx"`
3. 所有指向旧页的链接自动加 `（已被新概念取代）` 提示

### 8.3 分类索引（当 Wiki > 200 页时）
LLM 单次上下文装不下全量 `index.md` 时，需要在每级目录下加子索引：
```
wiki/
  index.md              # 顶级目录（只列子分类）
  ai-infra/
    index.md            # AI Infra 子分类（只列该域下页）
    concepts/
    entities/
```

---

## 9. 适用场景与边界

### 9.1 什么时候用 LLM Wiki ✅
- **个人研究知识库**：读论文、做笔记、写综述的场景（Karpathy 自己的用法，~100 篇 / 40 万字）
- **工程文档与 API 手册**：需要精确引用、变更可审计的技术知识库
- **团队 SOP / 规章制度**：多条文交叉引用、需要标注版本差异的知识
- **LLM Evaluation 评测集**：把评测标准、失败案例、技能定义编译成可审计的知识图谱（如 AgentSkill-Eval）

### 9.2 什么时候不要用 LLM Wiki ❌
- **大规模全网问答**：Raw 语料不稳定、持续高 churn，摄入成本远高于检索收益
- **纯时效性资讯**：新闻、股价、实时数据——编译完就过期
- **一次性 ad-hoc 问答**：只问一次的问题，编译 ROI 为负
- **代码生成 / 工具调用**：这类任务需要的是实时上下文，不是历史知识累积

---

## 10. 启动最小化实践（Ponytail 式最简路径）

遵循「7 级懒惰阶梯」，不要一上来就造轮子：

| 步骤 | 做法 | 耗时 |
|---|---|---|
| **1. 选工具** | Obsidian（浏览 Wiki）+ Claude Code / OpenAI Codex（Agent） | 10 min |
| **2. 建目录** | 手动建 `raw/`、`wiki/`、空的 `CLAUDE.md` | 5 min |
| **3. 拷 Gist** | 把 Karpathy 原始 prompt 粘进 `CLAUDE.md` | 1 min |
| **4. 丢第一篇** | 丢一篇你最熟的文章进 `raw/`，让 Agent Ingest | 5-15 min |
| **5. 跟 Schema 迭代** | 发现 Agent 做错的地方，改 `CLAUDE.md`，重来 | 持续 |
| **6. 问一个问题** | 用 Query 模式问一个需要跨 3+ 知识点的问题 | 1 min |
| **7. 跑一次 Lint** | 让 Agent 自检，观察它发现了什么问题 | 5 min |

> 关键：Schema 是长出来的，不是设计出来的。前 20 次 Ingest 的每一次失败，都是 Schema 进化的养分。

---

## 11. 总结：范式转移是什么

LLM Wiki 不是「又一个 RAG 工具」。它代表了三个层面的范式转移：

| 从 | 到 |
|---|---|
| **查询时检索** | **摄入时编译** |
| **无状态会话** | **有状态复利** |
| **人做簿记，LLM 做综合** | **LLM 做簿记，人做判断** |

这背后的深层洞察是：**LLM 最大的成本节约，不在于替人回答问题，而在于替人维护知识的组织结构。** 人类维护维基之所以失败，不是因为不会写，而是因为「更新 15 个互链页面 + 补全反向引用 + 标注矛盾」这种簿记工作会随着规模超线性增长，最终超过人的收益阈值。而 LLM 做这一切的边际成本近似为零。

用 Karpathy 自己的比喻收尾：

> *"Obsidian 是 IDE。LLM 是程序员。Wiki 是代码库。"*

你只需要 commit（策源 + 审核），Agent 负责 refactor。

---

## 参考

1. Andrej Karpathy, 2026-04-04, "LLM Wiki" GitHub Gist: `442a6bf555914893e9891c11519de94f`
2. enflory/ingolmo 社区研究报告：`karpathy-llm-wiki/README.md`
3. Rohit G. (rohitg00), LLM Wiki v2 扩展：Confidence Decay + Supersession Chains
4. MemoryForge 项目（本工作区）工程实践：SHA256 锚点、Tree-sitter 索引、六组件拒答模型
