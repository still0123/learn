# P8 代码实现难度评审

| 创新点/特征 | 现有代码路径 | 已实现程度 | 缺失实现 | 难度 | 风险 |
|---|---|---|---|---|---|
| evidence package / evidence id 统一结构 | `code_refactor/evidence/evidence_package.py` | 已实现（文本级） | 真实视频帧、OCR、logo 检测与原始追溯仍未接通 | 低 | 当前更多是 text-level bridge，不是完整视觉证据链 |
| 证据约束广告知识检索 | `code_refactor/rag/retriever.py` | 部分实现 | 仍缺真实视觉证据 embedding、广告知识维度精炼、外部检索对接 | 中 | 现有实现偏轻量 lexical/semantic hybrid，尚未证明是强专利点 |
| 结构化观察-分析-答案协议 | `code_refactor/reasoning/prompt_builder.py` | 已实现（提示词层） | 缺更细粒度的约束解码执行层 | 低 | 单独作为创新点风险较高，更像 prompt 协议 |
| 声明级证据回溯校验 | `code_refactor/reflection/claim_checker.py` | 部分实现（规则路由雏形） | 缺真实多模态证据回查、修正闭环、反馈 token 解析 | 中 | 目前更像 prototype，而非完整 pipeline |
| 三模态协同响应图 | 无直接实现 | 未实现 | 需视频帧特征、ASR/OCR/文本向量、跨模态相似度与热力图融合 | 高 | 这是最核心但也最重的视觉算法实现缺口 |
| 响应密度自适应锚定 + 多尺度锚框 | 无直接实现 | 未实现 | 需语义重心、多尺度候选框、局部裁剪和评分逻辑 | 高 | 如果没有实验/可运行实现，易被看作纸面设计 |
| 高风险触发 + 确认/修正令牌闭环 | `code_refactor/reflection/claim_checker.py`（可复用思路） | scaffold | 缺运行态的 verifier、token parser、条件触发器 | 中 | 容易被 D2 类文本自验证吸收，需要更强多模态绑定 |

## 代码证据摘录

- 路径：`code_refactor/evidence/evidence_package.py`
  - 对象：`EvidencePackage`, `EvidenceField`, `evidence_text()`
  - 可支撑内容：
    - 已有统一 evidence 容器；
    - 字段中同时保留 `asr`、`ocr_text`、`logo_text`、`global_view`、`local_high_resolution_evidence_view`、`ad_evidence_types`；
    - 说明项目里已经把“证据组织”为独立对象，而非散乱 prompt 文本。

- 路径：`code_refactor/rag/retriever.py`
  - 对象：`retrieve()`, `evidence_match()`, `RetrievedKnowledge.supporting_evidence_ids`
  - 可支撑内容：
    - 检索分数中已有 `evidence_score`；
    - 结果中已有 `supporting_evidence_ids`；
    - 说明知识检索已经不是纯问题驱动，而是尝试被 evidence package 约束。

- 路径：`code_refactor/reasoning/prompt_builder.py`
  - 对象：`build_structured_prompt()`
  - 可支撑内容：
    - 已把回答流程显式写成 `Observation / Knowledge Matching / Analysis / Answer`；
    - 可支撑“结构化语义约束协议”已有工程原型。

- 路径：`code_refactor/reflection/claim_checker.py`
  - 对象：`infer_claim_type()`, `build_check_plan()`
  - 可支撑内容：
    - 已经把声明分成 `ocr_or_logo_claim`、`asr_claim`、`marketing_claim`、`visual_claim`；
    - 可支撑“按声明类型回溯不同证据类型”的后续扩展。

## 结论

### 当前最有代码支撑的方向

1. **证据约束知识检索**
2. **结构化观察-分析-答案协议**
3. **声明类型路由的证据回溯雏形**

### 当前最缺实现但最有潜力的方向

1. **三模态协同响应图**
2. **响应密度自适应锚定 + 双流视觉表征**

### 对专利分析的含义

- 若目标是**当前答复**，应优先强调“已有描述 + 已有工程方向 + 明确技术问题”的特征，不宜夸大未实现的视觉模块。
- 若目标是**继续申请/新申请**，则可把“协同响应图 + 自适应锚定 + evidence id 全链路追踪”作为下一代系统路线。