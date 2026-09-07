# I1-Q 官方正文核验队列合并排序摘要

## 1. 范围

- 仅生成 120 条官方正文核验队列；本任务未执行任何全文抓取。
- 输入仅使用最新版 `00_brief.md`、`01a/01b` 来源、`01d`、`01e`、`01f` 和 `02a2`。
- 未开展候选构思，未修改正式申请稿，未执行 Git 操作。
- Exa 仅对可按 DOI/arXiv/规范标题回接 `01d/01e` 的论文增加语义分；Exa 独有记录不入队，也不用于日期、venue 或全文事实判断。

## 2. 数量

| 项目 | 数量 |
|---|---:|
| 队列总数 | 120 |
| `01a/01b` 原始已核验记录 | 37 |
| 去重后已核验论文族 | 34 |
| 待官方正文核验 | 86 |
| 2026 论文池合格 | 102 |
| 2026 论文池不合格但因已核验置顶保留 | 18 |
| 强反向/近邻反向证据 | 28 |
| 待核验记录中标记“可完整替换基线” | 46 |
| Exa 精确回接并获得语义加分 | 32 |

## 3. 层配额

已核验重复族按 `01a` 优先保留主层；跨层来源仍在单条记录的 `search_layer` 和 `source_pools` 中保留。

| 搜索层 | 目标 | 实际 |
|---|---:|---:|
| A | 48 | 48 |
| B | 20 | 20 |
| C | 32 | 32 |
| D | 20 | 20 |

## 4. 相关性层级

| 层级 | 数量 |
|---|---:|
| R1 | 38 |
| R2 | 49 |
| R3 | 31 |
| R4 | 2 |

## 5. M01-M10 覆盖

同一论文可以服务多个本地机制目标，因此本表不与 120 求和。最低覆盖线只用于选队列，不代表正文已经证明对应机制。

| 本地机制 | 队列覆盖 | 最低覆盖线 |
|---|---:|---:|
| M01 | 9 | 8 |
| M02 | 10 | 10 |
| M03 | 12 | 8 |
| M04 | 45 | 14 |
| M05 | 32 | 10 |
| M06 | 43 | 16 |
| M07 | 40 | 14 |
| M08 | 59 | 12 |
| M09 | 8 | 8 |
| M10 | 14 | 10 |

## 6. 排序与去重

1. 已核验置顶：合并 `01a/01b` 的 37 条记录，按 arXiv、DOI、规范标题归并为 34 个论文族，全部置于前 34 名。
2. 2026 资格：待核验项必须命中 `01d` 且 `research_pool_eligible=true`；已核验项逐条写入资格判断，不合格项仅因恢复规则保留。
3. 层内基础分：`R1/R2/R3/R4 = 500/400/300/200`，叠加 `01e.mechanism_relevance_score`。
4. 专项目标：强反向证据加 135 分，可完整替换基线加 95 分，`NEW_APPLICATION` 加 30 分。
5. 覆盖约束：按 M01-M10 欠覆盖度和机制簇稀缺度做动态加分；不把题名推断当作已验证全文结论。
6. Exa 约束：仅精确回接时每次命中加 7 分、最高 35 分；不采信 Exa 的估计日期、非官方 URL 或全文片段作为正式事实。
7. 排除：缺少 DOI/arXiv/规范标题、缺少官方 URL、无法回接 `01d`、2026 资格不成立或仅有 ResearchGate/Zenodo/SSRN 仓储型 DOI 的待核验项不入队。

## 7. 主要机制簇

| 机制簇 | 数量 |
|---|---:|
| `EVIDENCE_SUFFICIENCY_VERIFICATION` | 15 |
| `VISUAL_TOKEN_BUDGETING` | 14 |
| `DETAIL_INFORMATION_GATING` | 12 |
| `EVENT_CAUSAL_REASONING` | 11 |
| `FINE_GRAINED_REGION_GROUNDING` | 11 |
| `FRAME_EVIDENCE_SELECTION` | 11 |
| `LONG_VIDEO_MEMORY_RETRIEVAL` | 11 |
| `ACTIVE_EVIDENCE_SEEKING` | 10 |
| `AUDIO_VISUAL_ALIGNMENT` | 9 |
| `TRANSIENT_TEXT_OCR` | 7 |
| `HALLUCINATION_DETECTION` | 4 |
| `ROLE_ACTION_CAUSAL_REASONING` | 3 |
| `VERSIONED_TEXT_FACTS` | 3 |
| `AGENT_TOOL_ROUTING` | 3 |
| `SELF_CORRECTION_REFLECTION` | 3 |

## 8. SHA256

| 文件 | SHA256 |
|---|---|
| `00_brief.md` | `48113d5c3e9680ffeadc489c6174828c9c8aa1c5f61f75532883001c9ec3705d` |
| `01a_sources_papers.jsonl` | `4a42d3c4bd8a1522b7efd8f2ec8fc444695ea4fb63f6c289bf38cf43f90b5f24` |
| `01b_sources_papers.jsonl` | `a3b10aa3259773b34dcdf7e77aebb242f73aad887d1e3425818854c3e073a847` |
| `01d_2026_eligible_pool.jsonl` | `eb8c629bfbefcaf1e0d467f3ec0a48605b0c62a04fffc3833ba33959fe11578e` |
| `01e_abstract_screened_pool.jsonl` | `e778c9be1c0383c093b19b4c94ad0bfdc06e384f0ed9fb925cc470f7b367696f` |
| `01f_exa_semantic_pool.jsonl` | `308ea4820231f65bfed3e3b8b0ea5133a0064efa026ecba6da4be3c6fc5ea7eb` |
| `02a2_broad_isolated_mechanisms.md` | `f3fc3bd103148eeddc9efd349a70ca9287105f08d4fa1b843e547c2d855c6b42` |
| `01g_fulltext_verification_queue.jsonl` | `309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032` |

说明：摘要文件自身的 SHA256 在文件落盘后由交付回执给出，避免自引用哈希。
