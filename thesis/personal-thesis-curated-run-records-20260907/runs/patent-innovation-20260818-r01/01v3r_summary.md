# I1-V3R rank 81-120 官方正文核验恢复汇总

## 执行范围

- 权威输入：`01g_fulltext_verification_queue.jsonl`
- 输入队列 SHA256：`309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032`
- 处理范围：仅 `rank=81-120`
- 输出：`01v3r_verified_081_120.jsonl`
- 未覆盖旧 `01v3`；未执行专利构思、正式稿修改或 Git 操作。

## 结果计数

| 指标 | 数量 |
|---|---:|
| 总记录 | 40 |
| 正文核验成功 | 32 |
| 官方正文 | 31 |
| 同工作作者 arXiv 后备正文 | 1 |
| `FULL_TEXT_UNAVAILABLE` | 8 |
| `pool_eligible=true` | 40 |

## 正文入口

- arXiv 官方 HTML：25 篇。
- AAAI 官方 PDF：rank 93、117。
- MDPI 官方资源 PDF：rank 102、111、114。
- ACL Anthology 官方 PDF：rank 118。
- 同工作作者 arXiv 后备正文：rank 88（`arXiv:2506.13654`）。

所有成功记录均先核对正文标题或同工作作者版本、方法/分析章节和结论/限制，再写入机制字段。

## 不可用记录

| rank | 失败原因 |
|---:|---|
| 91 | Elsevier 正文受限，API 仅返回元数据；无开放后备正文。 |
| 94 | IEEE/Crossref PDF 返回挑战页；PubMed和作者页面仅有摘要。 |
| 96 | Elsevier 受限，OpenReview 正文入口返回 403；无开放后备正文。 |
| 98 | AAAI PDF 多次超时且下载不完整，PDF 尾部缺失、无法解析；无后备正文。 |
| 106 | IEEE/AAM PDF 返回挑战页，Computer Society 仅有摘要和参考文献。 |
| 110 | Elsevier 受限且 DBLP 标记 closed access；无开放后备正文。 |
| 116 | Springer 仅提供订阅预览，PDF 回落到付费摘要页。 |
| 120 | Springer 仅提供订阅预览，未发现开放 PDF 或作者正文。 |

失败记录未用摘要补写正文机制字段，统一标记：

```text
verification_status = FULL_TEXT_UNAVAILABLE
error_code = FULL_TEXT_UNAVAILABLE
```

## 日期纠正

| rank | 队列日期 | 核验日期 | 依据 |
|---:|---|---|---|
| 88 | 2026-01-01 | 2025-06-16 | 同工作 `arXiv:2506.13654` 首次公开；2026 正式发表。 |
| 117 | 2026-03-14 | 2025-11-15 | 同题 `arXiv:2511.12140` 首次公开；AAAI 2026 正式发表。 |
| 118 | 2026-01-01 | 2026-01-08 | `arXiv:2601.04891` 首次公开；ALVR 2026 正式发表。 |

## 完整性校验

- JSONL 行数：40
- rank 连续且唯一：81-120
- 字段：23/23，顺序与 V1/V2 一致
- JSON 解析：通过
- rank/title 与当前权威队列逐条一致：通过
- 成功记录正文章节和机制字段非空：通过
- 失败记录正文机制字段为空且错误码一致：通过

## SHA256

| 文件 | SHA256 |
|---|---|
| `01g_fulltext_verification_queue.jsonl` | `309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032` |
| `01v3r_verified_081_120.jsonl` | `bbe3630d0168fdae1d67cc73c71eccf8d15b23f485d86664c3cae61bb22552b2` |
