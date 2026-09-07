# P4 新申请方向矩阵（相对旧案与当前已知公开风险）

> 本矩阵当前不是逐篇完整 prior art 精读矩阵，而是“新申请方向 × 已知公开风险/旧案暴露风险”的筛选矩阵。后续可再补外部公开全文核查。

| 新方向 ID | 新主线方向 | 与旧案重复度 | 当前已知公开/风险来源 | 潜在组合风险 | 初步判断 |
|---|---|---|---|---|---|
| NR-01 | 知识污染/泄漏风险感知检索 | 低 | 当前看到的公开线索更多打在 video QA / OCR / verification，而非 leakage-aware retrieval governance | 中 | 值得重点保留 |
| NR-02 | supporting_evidence_ids 驱动的检索 provenance 结构 | 低 | FEVER 一类 evidence-backed verification 有类比，但未必直接覆盖“检索结果携带支撑证据ID”这种结构 | 中 | 值得保留 |
| NR-03 | claim_type → required_evidence 路由校验 | 中低 | FEVER / verification 方向会构成抽象层风险，但当前方案更偏多模态声明路由控制 | 中 | 值得保留 |
| NR-04 | lexical / embedding / hybrid retrieval orchestration | 中 | hybrid retrieval 本身容易被认为常规升级 | 高 | 不能单独主打，只能作为从属控制机制 |
| NR-05 | traceable_to_raw + raw frame path 贯通 | 中低 | 与一般 provenance / lineage 思路会有抽象重合，但旧案未充分覆盖 | 中 | 可保留，但需避免写得过工程化 |
| NR-06 | evidence-permitted knowledge prompt control | 中 | 单独看像 prompt engineering | 高 | 不能单独主打，需依附于 provenance/risk-aware 主线 |
| NR-07 | knowledge risk + claim routing + retrieval orchestration 联合控制 | 低 | 当前最像新系统主线；尚未见其被旧案或已知公开直接覆盖 | 中 | 最值得作为新申请核心候选 |

## 结论

### 最适合新申请独权主线的方向

1. **NR-07：知识风险感知 + 证据可追溯 + 声明类型路由的联合控制框架**
2. **NR-01：知识污染/泄漏风险感知检索机制**
3. **NR-02：supporting_evidence_ids 驱动的检索 provenance 结构**

### 只适合作为从属或实施例的方向

1. **NR-04：lexical / embedding / hybrid retrieval orchestration**
2. **NR-06：evidence-permitted knowledge prompt control**

### 新标题应尽量避开的词

- 广告视频问答方法（过宽）
- 链式校验（旧案味道太重）
- 视觉特征压缩（旧案味道太重）
- RAG 增强（过于常规）