# P1 材料清单

## 本地材料

| ID | 路径 | 类型 | 用途 | 可靠性 | 备注 |
|---|---|---|---|---|---|
| M1 | `source_texts/patent_office_action_pdf_extract.txt` | 驳回决定/审查意见 | 识别原案被拆解为功能组合的风险 | 高 | 本轮需避免重复“广告场景 + RAG + CoT + 自验证” |
| M2 | `runs/patent-analysis-20260624-round03-reapply-design/10_final_recommendation.md` | 前轮总报告 | 作为证据图谱方向的基础和风险输入 | 高 | round03 推荐证据图谱，但本轮进一步压缩为状态机 |
| M3 | `runs/patent-analysis-20260624-round03-reapply-design/07_examiner_critic_review.md` | 前轮审查员批判 | 识别图谱、路由、仲裁被打成常规组合的风险 | 高 | 本轮需避免四模块并列堆叠 |
| M4 | `code_refactor/reflection/claim_checker.py` | 代码实现 | 声明类型到证据需求的已有雏形 | 高 | 可演化为声明级证据许可状态机 |
| M5 | `code_refactor/evidence/evidence_package.py` | 代码实现 | 证据包字段基础 | 高 | 可作为 EvidenceUnit / PermissionRecord 的数据来源 |
| M6 | `code_refactor/reasoning/prompt_builder.py` | 代码实现 | 证据约束生成 prompt 基础 | 中高 | 可改为只允许许可声明输出 |
| E1 | Web: PhD visual hallucination benchmark | 外部论文趋势 | 视觉幻觉来源拆分：视觉模糊、输入冲突、反常识冲突 | 中 | 作为热点参考，不直接作为本地事实 |
| E2 | Web: PREHAL/evidential conflict | 外部论文趋势 | 用证据冲突检测视觉幻觉 | 中 | 与“冲突状态”相关 |
| E3 | Web: MagiC grounded visual reasoning | 外部论文趋势 | 评估推理步骤与视觉 grounding 的一致性 | 中 | 适合做图像实验 |
| E4 | Web: VLR-Bench / MRAG-Suite | 外部论文趋势 | Visual RAG 证据利用、干扰项、声明级诊断 | 中 | 适合快速实验 |
| E5 | Web: calibration / conformal prediction for VLM | 外部论文趋势 | 不确定性、选择性回答、拒答 | 中 | 与“证据不足状态”相关 |

## 本轮材料判断

- 原案和 round03 的“证据图谱”方向有价值，但如果同时写路由、图谱、仲裁、可信包，仍有被认定为功能组合的风险。
- 更适合新案的压缩表达是“声明级证据许可状态机”，把路由、冲突、降级都收敛为同一个状态转移机制。
- 图像任务数据集优先，因为可以快速构造证据许可记录和可视化实施例。
