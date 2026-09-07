# 05｜代码实施映射

| V4.3 要素 | 本地依据 | 状态 |
|---|---|---|
| 证据 ID、帧号、时间戳、时间窗、全局/局部视图、OCR/ASR | `code_refactor/evidence/evidence_package.py:17` | 已有字段基础 |
| 声明拆分及不同声明所需模态 | `code_refactor/reflection/claim_checker.py:18`、`:29` | 轻量实现 |
| 支撑证据 ID | `code_refactor/rag/retriever.py:15`、`:59` | 已实现知识检索侧关联 |
| OCR 帧号、时间戳、bbox、置信信息 | `.remote_threshold_work/build_selective_evidence_rewrite_calibration500_v1.py:92` | 已有实验字段 |
| ASR 起止时间和质量信息 | 同文件 `:145` | 已有实验字段 |
| `CoverageCell` / `CoverageDeltaRecord` | 无 | 未实现 |
| `delta_id` 对迁移授权 | 无 | 未实现 |
| 闭包暂存、快照 CAS、失效标记 | 无 | 未实现 |
| A2 严格不输入 A0 的对应实验 | 旧主实验反向输入 A0 | 未冻结 |

## 结论

现有代码足以说明证据单元如何落到视频时空和模态字段，但不足以证明 V4.3 主机制已实现。申请稿可给出伪代码和实施例，不得写“代码已实现”或沿用 Full‑7844 证明 V4.3 效果。

