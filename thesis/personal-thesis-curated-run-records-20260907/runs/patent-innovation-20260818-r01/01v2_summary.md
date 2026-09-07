# I1-V2 rank 41-80 官方正文核验汇总

## 执行范围

- 输入：`01g_fulltext_verification_queue.jsonl`
- 输入队列 SHA256：`309fd5ce5c8af3075132dabf25f092f769d174866f86b14d90f0b3faadbbc032`
- 排名范围：41-80
- 总记录数：40
- 已有全文复用：0（本范围 `existing_full_text_verified` 均为 `false`）
- 正文核验成功：30
- 正文复用成功：0
- 正文不可用：10

## 访问结果

- arXiv 官方 HTML：25 篇。
- 官方/关联 PDF：3 篇（rank 56、58、72）。
- ACM 官方会议全文 HTML：1 篇（rank 52）。
- 同题 arXiv 正文降级入口：1 篇（rank 73，`arXiv:2312.04931`）。
- `FULL_TEXT_UNAVAILABLE`：rank 46、51、53、57、62、63、67、74、76、78。

失败记录已依次检查可用的会议/出版社 HTML、arXiv HTML/PDF、作者或项目仓库、开放获取位置和 DOI 页面。仅摘要、元数据、代码仓库 README 或付费预览均未升级为全文核验。

## 关键核验事项

- rank 73 的正式版本为 IEEE TMM 2026，但同题 arXiv 首次公开于 `2023-12-08`；输出已纠正 `earliest_public_date`，其 `pool_eligible=true` 仍由正式 venue 2026 支撑。
- rank 76 的 Springer 页面仅有摘要和付费提示，不含方法正文，明确标记 `FULL_TEXT_UNAVAILABLE`。
- 所有成功记录均通过标题-标识符一致性检查，并从方法、实验/分析及结论/限制章节提取机制；失败记录未用摘要补写正文字段。

## 输出校验

- `01v2_verified_041_080.jsonl`：40 行，rank 连续且唯一。
- JSONL SHA256：`622766e406b8935a179019236abf248467b591af40d98ae8766497ab5764f597`
- 字段集合与顺序符合任务合同。
