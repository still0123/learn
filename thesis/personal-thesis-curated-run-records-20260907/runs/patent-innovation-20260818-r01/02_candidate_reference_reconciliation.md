# I2 候选论文引用对账

生成时间：`2026-08-18T02:12:06+08:00`

## 1. 对账结论

I3 在 `03a_evidence_gate.md` 第 4.1 节发现，候选卡沿用的旧 V3 rank
标识来自已被拒绝的队列快照，无法稳定定位当前权威记录。V3R 已完成恢复，
后续引用一律以 `01_sources_papers.jsonl` 中唯一的 `paper_record_id` 和完整
标题为准；`rank` 仅保留为当前队列内的辅助追踪字段，不再作为跨产物主键。

权威来源：

- `01_sources_papers.jsonl`
- SHA256：`58934393e8f64861203e401fe868fb366a122d351a18cf9100333c1539de3950`
- 144 条记录均有唯一 `paper_record_id`
- V3R 的 40 条 rank/title 与权威队列逐条一致

## 2. 受影响引用映射

| 候选 | 旧 V3 别名 | 稳定 paper_record_id | 当前 rank | 权威标题 |
|---|---|---|---:|---|
| P01 | `01V3-R99` | `PAPER-VERIFIED-138` | 89 | Visual Token Compression Enhances Robustness of MLLMs |
| P04 | `01V3-R112` | `PAPER-VERIFIED-116` | 107 | SPARROW: Learning Spatial Precision and Temporal Referential Consistency in Pixel-Grounded Video MLLMs |
| P05 | `01V3-R85` | `PAPER-VERIFIED-031` | 81 | Entropy Alone is Insufficient for Safe Selective Prediction in LLMs |
| P05 | `01V3-R86` | `PAPER-VERIFIED-039` | 83 | FaithSCAN: Model-Driven Single-Pass Hallucination Detection for Faithful Visual Question Answering |
| P08 | `01V3-R88` | `PAPER-VERIFIED-017` | 95 | CounterVid: Counterfactual Video Generation for Mitigating Action and Temporal Hallucinations in Video-Language Models |
| P08 | `01V3-R104` | `PAPER-VERIFIED-067` | 100 | Learning from Fine-Grained Visual Discrepancies: Mitigating Multimodal Hallucinations via In-Context Visual Contrastive Optimization |
| P08 | `01V3-R119` | `PAPER-VERIFIED-109` | 117 | Seeing Is Believing: Rich-Context Hallucination Detection for MLLMs via Backward Visual Grounding |

受影响候选仅为 `P01`、`P04`、`P05`、`P08`。旧别名保留作历史审计，
不得继续用于定位论文正文。

## 3. 处置边界

- 本文件只校正引用身份与后续引用规则。
- 不修改 `02_candidate_cards.md/jsonl` 的候选内容。
- 不修改 I3 分数、硬失败、分类或处置。
- 不重开任何候选，不改变空 `PASS_TO_I4`。
- 不改变 `I4 = NOT_APPLICABLE_NO_SURVIVOR`。
- 不修改正式申请稿，不执行 Git 操作。

V3R 恢复补足论文证据的可审计定位，但不追溯改写已冻结的候选判断和门禁
结论。
