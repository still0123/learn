# I1-V5 topup_rank 013-024 arXiv 正文核验汇总

## 执行范围

- 输入：`01i_topup_queue.jsonl`
- 处理范围：仅 `topup_rank=13-24`
- 正文真源：官方 arXiv HTML；本批 12 篇均首次抓取成功，未触发 PDF 降级。
- 输出：`01v5_topup_013_024.jsonl`
- 未执行专利构思、正式稿修改或 Git 操作。

## 结果计数

| 指标 | 数量 |
|---|---:|
| 总记录 | 12 |
| 官方 arXiv HTML 核验成功 | 12 |
| PDF 降级 | 0 |
| `VERIFIED_FULL_TEXT` | 12 |
| `FULL_TEXT_UNAVAILABLE` | 0 |
| `pool_eligible=true` | 12 |

所有成功记录均同时保留方法、实验和限制边界证据。rank 16、22 有独立
Limitations 小节；其余论文的限制证据来自 Analysis/Discussion、Ablation、
Failure、Cost、Future Work 或结论中的明确边界，未用摘要推断限制。

## 逐条核验

| topup_rank | title | 方法证据 | 实验证据 | 限制证据 |
|---:|---|---|---|---|
| 13 | VisualRouter: Query-Grounded Visual Sampling for Long Video Understanding | §III | §IV-A–IV-C | §III-C、§IV-C3 |
| 14 | EG-VQA: Benchmarking Verifiable Video Question Answering with Grounded Temporal Evidence | §4.1–4.4 | §5.1–5.4 | §5.3、§5.5 |
| 15 | Knowing When to Answer: Adaptive Confidence Refinement for Reliable Audio-Visual Question Answering | §3.4 | §4.1–4.4 | Appendix P |
| 16 | Event-Anchored Frame Selection for Effective Long-Video Understanding | §3.1–3.3 | §4.1–4.3 | §6.1 |
| 17 | Where to Focus: Query-Modulated Multimodal Keyframe Selection for Long Video Understanding | §3.1–3.3 | §4.1–5.2 | §5.3–5.8 |
| 18 | Reflective Dialogue between Teacher and Solver Agents for Video Question Answering | §3.1–3.4 | §4.1–4.6 | §5 |
| 19 | Symphony: A Cognitively-Inspired Multi-Agent System for Long-Video Understanding | §3.1–3.3 | §4.3–4.4 | §4.4.2、Appendix C |
| 20 | MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering | §3.1–3.5 | §4.1–4.3 | §4.2、§7.2 |
| 21 | Narrative Aligned Long Form Video Question Answering | §4.1–4.3 | §5.1–6.1 | §5.1、§6.2–6.3 |
| 22 | Semantic Event Graphs for Long-Form Video Question Answering | §2.1–2.4 | §4.1–4.5 | §5.2–5.3 |
| 23 | MarkIt: Training-Free Visual Markers for Precise Video Temporal Grounding | §III-A–III-F | §IV-D–IV-E | §IV-E、Appendix B/C |
| 24 | A Cost-Aware, Paired Protocol for Auditing Dynamic Tool Synthesis in Agentic Video Question Answering | §3.2–3.6 | §5.1–5.3 | §5.4–5.5、§6 |

## 主要机制

- rank 13、16、17：问题条件路由、事件锚定和多模态门控的关键帧选择。
- rank 14、15：时间证据联合匹配与音视频选择性回答。
- rank 18、19、24：反思对话、多 Agent 动态协作及可审计复合工具。
- rank 20、21、22：多粒度 KV、叙事记忆和时间事件图。
- rank 23：查询到实例 mask 的显式视频时间标记。

## 完整性校验

- JSONL 行数：12。
- `topup_rank`：13-24 连续且唯一。
- 字段：23/23 全部存在，顺序与 V1/V2 一致，以 `topup_rank` 替代 `rank`。
- JSON 解析：通过。
- 输入标题、标识符、URL、日期、检索层和相关级别逐条一致：通过。
- 方法、实验、限制证据及机制字段非空：通过。
- `error_code != null`：0。

## SHA256

| 文件 | SHA256 |
|---|---|
| `00_brief.md` | `48113d5c3e9680ffeadc489c6174828c9c8aa1c5f61f75532883001c9ec3705d` |
| `01i_topup_queue.jsonl` | `50e2ae45ca3be9daff812d7ae768f9f300d9df535afbc332e760ede1dccf7d7e` |
| `01v5_topup_013_024.jsonl` | `6efb7eab8cccb81c7b6d24542c69ce893730a4f99d15b24fed1b37a984803af2` |
