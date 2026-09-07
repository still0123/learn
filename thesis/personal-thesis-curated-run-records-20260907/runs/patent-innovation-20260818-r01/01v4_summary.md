# I1-V4 topup_rank 001-012 官方正文核验汇总

## 执行范围

- 权威输入：`01i_topup_queue.jsonl`
- 处理范围：仅 `topup_rank=1-12`
- 输出：`01v4_topup_001_012.jsonl`
- 未执行专利构思、正式稿修改或 Git 操作。

## 结果计数

| 指标 | 数量 |
|---|---:|
| 总记录 | 12 |
| 正文核验成功 | 12 |
| `FULL_TEXT_UNAVAILABLE` | 0 |
| arXiv 官方 HTML 主文 | 10 |
| arXiv 官方 PDF 后备 | 2 |
| `reverse_evidence=true` | 4 |

rank 2 的 arXiv HTML 主文转换不完整，改用官方 PDF；rank 4 的 arXiv
HTML 返回 404，改用官方 PDF。两篇 PDF 均能解析标题、方法、实验和限制
正文。其余十篇使用官方 arXiv HTML。

## 正文证据门禁

| topup_rank | 标题简称 | 方法证据 | 实验证据 | 限制证据 |
|---:|---|---|---|---|
| 1 | FocusGraph | §3.1-3.5 | §4.1-4.2 | §3.3-3.5 的适用假设、§4.2 消融和 §5 范围 |
| 2 | HiMu | §3.1-3.3、Appendix C | §4、Appendix D/E | §5 Discussion 的 Limitations 段 |
| 3 | SVAgent | §3、Algorithm 1 | §4.1-4.6 | Algorithm 1 的轮次回退及 §4.3 延迟分析 |
| 4 | MEC | §3.2-3.4 | §4.1-4.3 | Appendix D Limitations |
| 5 | GCR | Ground/Cover/Refine | Overall、Ablation、Sensitivity | Conclusion 的 Limitations 段 |
| 6 | HORNet | §3.1-3.4 | §4.3-4.5 | §5 Conclusion 的 Limitations 段 |
| 7 | NEST | §3.1-3.2 | §4-5 | §7 Limitations |
| 8 | GenEvA | §3.1-3.5 | §4、§7.2-7.3 | §3.1 适用边界、§4.1 实验范围和 §5 |
| 9 | CADER | Method Stage 1/2、RGR | Ablation、Routing Analysis | Appendix D 的预算耗尽和递减收益 |
| 10 | Perception First | §1-2 | §4-5.1 | §6 Limitations |
| 11 | Reflect-R1 | §3.1-3.4 | §4.2-4.3 | §6 Limitations |
| 12 | REVEAL | §3.1-3.3 | §4.2-4.4、Appendix C.1 | §5 Conclusion 的 limitation 段 |

无独立 `Limitations` 标题的论文，仅从正文的方法假设、实验范围、消融、
失败回退或结论中的明确约束提取限制，未使用摘要推断机制。

## 元数据核验

- 12 条 `title` 与输入队列逐字一致。
- arXiv API/abs 页标题、标识符和首次公开日期逐条核对通过。
- rank 3 的 arXiv comment 标明 `CVPR 2026`。
- rank 10 正文标明 `VRR Challenge @ CVPR 2026`。
- rank 11 的 arXiv comment 标明 `ECCV 2026`。

## 完整性校验

- JSONL 行数：12
- `topup_rank`：1-12 连续且唯一
- 字段：23/23，顺序与 V1/V2 机制字段一致，并保留 `topup_rank`
- JSON 解析：通过
- 标题、arXiv 标识、官方 URL、日期、检索层和相关级别与队列逐条一致
- 成功记录的方法、实验、限制及机制字段均非空
- `verification_status=VERIFIED_FULL_TEXT`：12
- `error_code != null`：0

## SHA256

| 文件 | SHA256 |
|---|---|
| `01i_topup_queue.jsonl` | `50e2ae45ca3be9daff812d7ae768f9f300d9df535afbc332e760ede1dccf7d7e` |
| `01v4_topup_001_012.jsonl` | `7a1a3e73cebf3475922e1c44d4660572f1136f0d11717a73a5e402d3794b7876` |
