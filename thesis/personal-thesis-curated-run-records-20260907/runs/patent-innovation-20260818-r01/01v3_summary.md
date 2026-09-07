# I1-V3 正文核验汇总（Rank 81-120）

## 结果

- 处理记录：40
- 正文核验成功：32
  - 官方全文：30
  - 作者公开版回接：2（Rank 88、117）
- 复用既有全文：0
- 正文不可用：8
- 论文池合格：40

## 不可用记录

| Rank | 失败原因 |
|---:|---|
| 91 | Elsevier 受限，未找到 arXiv 或作者公开版 |
| 94 | IEEE、PubMed、作者页面均未提供可读正文 |
| 96 | Elsevier、OpenReview、机构仓库均被访问验证阻断 |
| 98 | AAAI 页面仅有摘要；正式 PDF 多次超时且下载不完整 |
| 106 | IEEE 页面仅有摘要、关键词和参考文献 |
| 110 | Closed access，未找到作者公开版 |
| 116 | Springer 仅返回参考文献，未找到开放正文 |
| 120 | Springer 仅返回参考文献，未找到开放正文 |

以上记录均写入：

```text
verification_status = FULL_TEXT_UNAVAILABLE
error_code = FULL_TEXT_UNAVAILABLE
```

## 日期纠正

| Rank | 队列日期 | 正文/官方元数据核验日期 | 说明 |
|---:|---|---|---|
| 88 | 2026-01-01 | 2025-06-16 | arXiv:2506.13654 首次公开；2026 正式发表，仍满足论文池政策 |
| 117 | 2026-03-14 | 2025-11-15 | arXiv:2511.12140 首次公开；2026 正式发表，仍满足论文池政策 |
| 118 | 2026-01-01 | 2026-01-08 | arXiv:2601.04891 首次公开 |

## 完整性校验

- Rank 连续范围：81-120
- JSONL 行数：40
- 缺失字段：0
- 重复 Rank：0
- `verified_from_full_text=true` 且章节为空：0
- 非全文记录未标记 `FULL_TEXT_UNAVAILABLE`：0

## SHA256

| 文件/快照 | SHA256 |
|---|---|
| `01v3_verified_081_120.jsonl` | `7dc11191de7f9da4c8a0744a3226c317aff5cc6ded24d84ccec7b532eae8d76f` |
| Rank 81-120 输入快照 | `69a376650b768e64606b39d70b1444e580569e042a0d3aedeefb737e86d0cf29` |

本批次未执行专利构思、正式稿修改或 Git 操作。
