# 05｜代码实施映射

| V4.4 要素 | 本地依据 | 当前状态 |
|---|---|---|
| 证据 ID、帧号、时间戳、时间窗、全局/局部视图、OCR/ASR | `code_refactor/evidence/evidence_package.py:17-37` | 已有字段基础 |
| 声明拆分及价格、文字、数字、语音、视觉的模态需求 | `code_refactor/reflection/claim_checker.py:18-34` | 轻量实现 |
| 支持证据 ID | `code_refactor/rag/retriever.py:15-24`、`:59-74` | 知识检索侧已有 |
| OCR 文本、置信度、帧号、时间戳、bbox、跨帧次数 | `.remote_threshold_work/build_selective_evidence_rewrite_calibration500_v1.py:92-142` | 已有实验字段 |
| ASR 文本、起止时间和质量信息 | 同文件 `:145-178` | 已有实验字段 |
| `SlotSchema` 的规范化值、限定字段、基数和排他规则 | 无 | 未实现 |
| `VideoObservationPermit` | 无 | 未实现 |
| 候选值盲化的 A2 前冻结 | 无 | 未实现 |
| 同上下文值簇及竞争状态机 | 无 | 未实现 |
| 迁移对观测的槽—上下文—值匹配 | 无 | 未实现 |
| 闭包暂存、快照校验和失效传播 | 无 | 未实现 |
| A2 严格不输入 A0 的冻结实验 | 旧主实验反向输入 A0 | 未完成 |

## 结论

底层证据的时空、区域和模态字段足以支撑一个可实施示例，但 V4.4 的主控制机制尚不存在。专利初稿可写数据结构、伪代码和分支实施例；不得写“已经实现”“已证明提高准确率”，也不得沿用 Full‑7844 作为 V4.4 效果数据。

